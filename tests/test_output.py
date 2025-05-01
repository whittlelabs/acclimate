"""
Tests for the acclimate.formatters module.
"""
import sys
import io
import json
import pytest
from typing import IO, Any, Optional

from acclimate.output import OutputAdapterProtocol, TableOutputAdapter, JsonOutputAdapter, ModelsOutputAdapter, DEFAULT_FORMATTERS


class TestFormatterProtocol:
    """Tests for the FormatterProtocol interface."""
    
    def test_custom_formatter_implements_protocol(self):
        """Test that a custom formatter implementing FormatterProtocol works."""
        # Create a custom formatter
        class CustomFormatter:
            def format(self, result: Any, output: Optional[IO] = None) -> Optional[str]:
                result_str = f"Custom formatted: {result}"
                if output:
                    output.write(result_str)
                    return None
                return result_str
        
        # Verify it works with the protocol
        formatter = CustomFormatter()
        assert isinstance(formatter, OutputAdapterProtocol)
        
        # Test with return value
        result = formatter.format("test")
        assert result == "Custom formatted: test"
        
        # Test with output stream
        output = io.StringIO()
        result = formatter.format("test", output)
        assert result is None
        assert output.getvalue() == "Custom formatted: test"


class TestTableFormatter:
    """Tests for the TableFormatter."""
    
    def test_table_formatter_with_dict_list(self):
        """Test formatting a list of dictionaries as a table."""
        formatter = TableOutputAdapter(columns=["id", "name"], header=True)
        data = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
        ]
        
        result = formatter.format(data)
        
        # Verify format
        assert "id | name" in result
        assert "1 | Item 1" in result
        assert "2 | Item 2" in result
    
    def test_table_formatter_with_object_list(self):
        """Test formatting a list of objects as a table."""
        class TestItem:
            def __init__(self, id, name):
                self.id = id
                self.name = name
        
        formatter = TableOutputAdapter(columns=["id", "name"], header=True)
        data = [
            TestItem(1, "Item 1"),
            TestItem(2, "Item 2"),
        ]
        
        result = formatter.format(data)
        
        # Verify format
        assert "id | name" in result
        assert "1 | Item 1" in result
        assert "2 | Item 2" in result
    
    def test_table_formatter_with_output_stream(self):
        """Test formatting to an output stream."""
        formatter = TableOutputAdapter(columns=["id", "name"])
        data = [{"id": 1, "name": "Item 1"}]
        
        output = io.StringIO()
        result = formatter.format(data, output)
        
        # Should return None when using output stream
        assert result is None
        # Output should be written to the stream
        assert "id | name" in output.getvalue()
        assert "1 | Item 1" in output.getvalue()
    
    def test_table_formatter_with_sorting(self):
        """Test sorting table rows by a column."""
        formatter = TableOutputAdapter(columns=["id", "name"], order_by="name")
        data = [
            {"id": 2, "name": "B Item"},
            {"id": 1, "name": "A Item"},
            {"id": 3, "name": "C Item"},
        ]
        
        result = formatter.format(data)
        lines = result.strip().split("\n")
        
        # Should be sorted by name
        assert "1 | A Item" in lines[2]  # First data row after header and separator
        assert "2 | B Item" in lines[3]
        assert "3 | C Item" in lines[4]


class TestJsonFormatter:
    """Tests for the JsonFormatter."""
    
    def test_json_formatter_with_dict(self):
        """Test formatting a dictionary as JSON."""
        formatter = JsonOutputAdapter()
        data = {"id": 1, "name": "Test Item"}
        
        result = formatter.format(data)
        parsed = json.loads(result)
        
        assert parsed["id"] == 1
        assert parsed["name"] == "Test Item"
    
    def test_json_formatter_with_list(self):
        """Test formatting a list as JSON."""
        formatter = JsonOutputAdapter()
        data = [{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}]
        
        result = formatter.format(data)
        parsed = json.loads(result)
        
        assert len(parsed) == 2
        assert parsed[0]["id"] == 1
        assert parsed[1]["name"] == "Item 2"
    
    def test_json_formatter_with_output_stream(self):
        """Test formatting to an output stream."""
        formatter = JsonOutputAdapter()
        data = {"id": 1, "name": "Test Item"}
        
        output = io.StringIO()
        result = formatter.format(data, output)
        
        # Should return None when using output stream
        assert result is None
        # Output should be written to the stream
        parsed = json.loads(output.getvalue())
        assert parsed["id"] == 1
        assert parsed["name"] == "Test Item"


class TestModelsFormatter:
    """Tests for the ModelsFormatter."""
    
    def test_models_formatter_with_list(self):
        """Test formatting a list of models."""
        formatter = ModelsOutputAdapter()
        data = [
            {"id": "gpt-4", "details": "Latest model"},
            {"id": "gpt-3.5", "details": "Older model"}
        ]
        
        result = formatter.format(data)
        
        # Verify format includes model IDs
        assert "Available Models:" in result
        assert "- gpt-4" in result
        assert "- gpt-3.5" in result
    
    def test_models_formatter_with_objects(self):
        """Test formatting a list of model objects."""
        class Model:
            def __init__(self, id, details):
                self.id = id
                self.details = details
        
        formatter = ModelsOutputAdapter()
        data = [
            Model("gpt-4", "Latest model"),
            Model("gpt-3.5", "Older model")
        ]
        
        result = formatter.format(data)
        
        # Verify format includes model IDs
        assert "Available Models:" in result
        assert "- gpt-4" in result
        assert "- gpt-3.5" in result
    
    def test_models_formatter_with_data_dict(self):
        """Test formatting when the result has a data field."""
        formatter = ModelsOutputAdapter()
        data = {
            "data": [
                {"id": "gpt-4"},
                {"id": "gpt-3.5"}
            ]
        }
        
        result = formatter.format(data)
        
        # Verify format includes model IDs
        assert "Available Models:" in result
        assert "- gpt-4" in result
        assert "- gpt-3.5" in result


class TestDefaultFormatters:
    """Tests for the DEFAULT_FORMATTERS registry."""
    
    def test_default_formatters_registry(self):
        """Test that the DEFAULT_FORMATTERS registry contains all expected formatters."""
        assert "table" in DEFAULT_FORMATTERS
        assert "json" in DEFAULT_FORMATTERS
        assert "models" in DEFAULT_FORMATTERS
        
        # Verify the types are correct
        assert DEFAULT_FORMATTERS["table"] is TableOutputAdapter
        assert DEFAULT_FORMATTERS["json"] is JsonOutputAdapter
        assert DEFAULT_FORMATTERS["models"] is ModelsOutputAdapter