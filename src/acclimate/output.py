"""
Formatter implementations for acclimate.

This module provides concrete implementations of the FormatterProtocol for
formatting command outputs in various ways.
"""

import json
from typing import Any, Optional, List, IO, Protocol, runtime_checkable

@runtime_checkable
class OutputAdapterProtocol(Protocol):
    """
    Protocol defining the interface for output formatters.
    
    Formatters are responsible for handling the output of a command execution.
    They can either return a formatted string representation of the result
    or handle the output directly (e.g., by printing or streaming to a file).
    """
    
    def format(self, result: Any, output: Optional[IO] = None) -> Optional[str]:
        """
        Format the result of a command execution.
        
        Args:
            result: The result object to format
            output: Optional output stream to write to (defaults to sys.stdout)
                
        Returns:
            If output is None, returns the formatted string representation.
            If output is provided, writes to the output stream and returns None.
        """
        ...

class TableOutputAdapter(OutputAdapterProtocol):
    """
    Format results as a text-based table.
    
    This formatter takes a list of items (dicts or objects) and formats them as a text table.
    """
    
    def __init__(self, columns: Optional[List[str]] = None, order_by: Optional[str] = None,
                 header: bool = True):
        """
        Initialize the TableFormatter.
        
        Args:
            columns: List of column names to include. If None, all keys will be included.
            order_by: Optional key to sort results by.
            header: Whether to include a header row.
        """
        self.columns = columns
        self.order_by = order_by
        self.header = header
    
    def format(self, result: Any, output: Optional[IO] = None) -> Optional[str]:
        """
        Format the result as a table.
        
        Args:
            result: The result to format (should be a list of items)
            output: Optional output stream to write to
                
        Returns:
            Formatted table as string if output is None, otherwise None
        """
        # Extract data from result if needed
        if hasattr(result, "data"):
            data = result.data
        elif isinstance(result, list):
            data = result
        else:
            data = [result]
            
        # Sort if order_by is specified
        if self.order_by:
            def get_key_value(item):
                if isinstance(item, dict):
                    return item.get(self.order_by)
                else:
                    return getattr(item, self.order_by, None)
            data = sorted(data, key=get_key_value)
            
        # Auto-detect columns if none were specified
        columns = self.columns
        if not columns and data:
            # Use keys from first item
            if isinstance(data[0], dict):
                columns = list(data[0].keys())
            else:
                # Try to get all attribute names excluding private ones
                columns = [attr for attr in dir(data[0]) 
                          if not attr.startswith('_') and not callable(getattr(data[0], attr))]
                
        if not columns:
            # If we still don't have columns, just convert to string
            result_str = str(data)
            if output:
                output.write(result_str)
                output.write("\n")
                return None
            return result_str
            
        # Build the table
        lines = []
        
        # Add header
        if self.header:
            header = " | ".join(columns)
            separator = "-" * len(header)
            lines.append(header)
            lines.append(separator)
            
        # Add data rows
        for item in data:
            row_cells = []
            for col in columns:
                # Handle dict vs. object
                val = item.get(col) if isinstance(item, dict) else getattr(item, col, None)
                row_cells.append(str(val))
            lines.append(" | ".join(row_cells))
            
        # Join and return or write to output
        result_str = "\n".join(lines)
        if output:
            output.write(result_str)
            output.write("\n")
            return None
        return result_str


class JsonOutputAdapter(OutputAdapterProtocol):
    """Format results as JSON."""
    
    def __init__(self, indent: int = 2):
        """
        Initialize the JsonFormatter.
        
        Args:
            indent: Number of spaces to use for indentation.
        """
        self.indent = indent
    
    def format(self, result: Any, output: Optional[IO] = None) -> Optional[str]:
        """
        Format the result as JSON.
        
        Args:
            result: The result to format
            output: Optional output stream to write to
                
        Returns:
            Formatted JSON as string if output is None, otherwise None
        """
        result_str = json.dumps(result, indent=self.indent, default=str)
        if output:
            output.write(result_str)
            output.write("\n")
            return None
        return result_str


class ModelsOutputAdapter(OutputAdapterProtocol):
    """
    Format models list output specifically for the get models command.
    
    This is an example of a specialized formatter tailored for a particular output type.
    """
    
    def format(self, result: Any, output: Optional[IO] = None) -> Optional[str]:
        """
        Format a models list result.
        
        Args:
            result: The result to format (should be a list of model objects with an 'id' field)
            output: Optional output stream to write to
                
        Returns:
            Formatted model list as string if output is None, otherwise None
        """
        # Extract models list from various possible result structures
        models = []
        if hasattr(result, "data"):
            models = result.data
        elif isinstance(result, list):
            models = result
        elif isinstance(result, dict) and "data" in result:
            models = result["data"]
        else:
            models = [result]
        
        # Format as a list of model IDs with a header
        lines = ["Available Models:", "----------------"]
        
        # Sort models by ID
        models_sorted = sorted(models, key=lambda m: m.get("id") if isinstance(m, dict) else getattr(m, "id", ""))
        
        # Add each model to the output
        for model in models_sorted:
            model_id = model.get("id") if isinstance(model, dict) else getattr(model, "id", str(model))
            lines.append(f"- {model_id}")
                
        # Join and return or write to output
        result_str = "\n".join(lines)
        if output:
            output.write(result_str)
            output.write("\n")
            return None
        return result_str


# Create a registry of default formatters
DEFAULT_FORMATTERS = {
    "table": TableOutputAdapter,
    "json": JsonOutputAdapter,
    "models": ModelsOutputAdapter,
}