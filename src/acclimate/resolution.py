"""
Adapter module for acclimate.

This module defines the adapter protocol and provides concrete implementations for common
resolution strategies. Adapters are used by the CommandRunner to resolve target strings to actual callables.
"""

import importlib
import sys
from typing import Any, Callable, Protocol, TypeVar, runtime_checkable, Optional, Union, IO

T = TypeVar('T', bound=Callable)


@runtime_checkable
class ResolutionAdapterProtocol(Protocol):
    """
    Protocol defining the interface for target resolution adapters.
    
    Adapters are responsible for resolving a string target (like a module path or service ID)
    to a callable function or method. Implementations must be callable with a string parameter.
    """
    
    def __call__(self, target: str) -> Callable:
        """
        Resolve a target string to a callable.
        
        Args:
            target: A string identifier for the target to resolve
            
        Returns:
            The resolved callable
            
        Raises:
            ValueError: If the target cannot be resolved
        """
        ...

class ImportLibAdapter(ResolutionAdapterProtocol):
    """
    Adapter that resolves targets using Python's importlib.
    
    This adapter takes a string in the format "module.path.Class.method" and
    imports the module, instantiates the class, and returns the specified method.
    It also supports "module.path.function" for standalone functions.
    """
    
    def __call__(self, target: str) -> Callable:
        """
        Resolve a target using Python's import mechanism.
        
        Args:
            target: Target string in the format "module.path.Class.method"
                or "module.path.function" for standalone functions
                
        Returns:
            The resolved method (bound to a class instance) or function
            
        Raises:
            ValueError: If the target format is invalid
            ImportError: If the module cannot be imported
            AttributeError: If the attribute doesn't exist in the module
        """
        # Remove @ prefix if present (though this should be handled by DIAdapter)
        clean_target = target.lstrip('@')

        # Handle module.path.Class.method format first (most complex case)
        try:
            # Start by trying to split into module.path.Class and method
            parts = clean_target.split('.')
            if len(parts) < 2:
                raise ValueError(f"Invalid target format: {target}. Expected at least module.function")
            
            # First try a direct module.function approach
            # This is needed for standalone_function case
            try:
                # Try importing the module path directly (all but the last part)
                module_path = '.'.join(parts[:-1])
                function_name = parts[-1]
                
                module = importlib.import_module(module_path)
                attr = getattr(module, function_name)
                
                # If it's a class, instantiate it
                if isinstance(attr, type):
                    return attr()
                # Otherwise return the function or other callable directly
                return attr
                
            except (ImportError, AttributeError):
                # If that fails, try the Class.method approach
                if len(parts) >= 3:
                    # The module path is everything except the last two segments
                    module_path = '.'.join(parts[:-2])
                    class_name = parts[-2]
                    method_name = parts[-1]
                    
                    # Import the module
                    module = importlib.import_module(module_path)
                    
                    # Get the class
                    cls = getattr(module, class_name)
                    
                    # Instantiate the class
                    instance = cls()
                    
                    # Get the method
                    func = getattr(instance, method_name)
                    
                    return func
                else:
                    # Re-raise if we can't handle it as either approach
                    raise
                    
        except ImportError as e:
            raise ImportError(f"Could not import module: {e}")
        except AttributeError as e:
            raise AttributeError(f"Attribute not found: {e}")
        except TypeError as e:
            raise TypeError(f"Type error during resolution: {e}")
        except Exception as e:
            raise ValueError(f"Could not resolve target {target}: {e}")


class DIAdapter(ResolutionAdapterProtocol):
    """
    Adapter for Dependency Injection containers.
    
    This adapter wraps a DI container instance and uses it to resolve services.
    It handles targets in the format "@service.method".
    """
    
    def __init__(self, container: Any):
        """
        Initialize the DIAdapter with a container instance.
        
        Args:
            container: A DI container instance with a 'get' method
            
        Raises:
            ValueError: If the container doesn't have a get method
        """
        if not hasattr(container, "get"):
            raise ValueError("DI container must have a 'get' method")
            
        self.container = container
    
    def __call__(self, target: str) -> Callable:
        """
        Resolve a target using the DI container.
        
        Args:
            target: Service ID to resolve from the container in the format "@service.method"
                
        Returns:
            The resolved method bound to the service instance
            
        Raises:
            ValueError: If the target format is invalid
        """
        # Check if the target starts with @
        if not target.startswith('@'):
            raise ValueError(f"DI container target must start with @ symbol: {target}")
            
        # Remove @ prefix
        clean_target = target[1:]
        
        try:
            # Extract the service name and method name
            service_name, method_name = clean_target.rsplit(".", 1)
            
            # Get the service from the container
            service = self.container.get(service_name)
            
            # Get the method from the service
            try:
                return getattr(service, method_name)
            except AttributeError:
                raise AttributeError(f"Service {service_name} has no method {method_name}")
                
        except ValueError:
            # If no dot in the target, just get the service directly
            return self.container.get(clean_target)