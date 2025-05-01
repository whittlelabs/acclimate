"""
Tests for the acclimate.adapter module.
"""
import pytest
from unittest.mock import MagicMock
from typing import Callable

from acclimate.adapter import (
    AdapterProtocol,
    ImportLibAdapter,
    DIAdapter
)
from tests.resources.test_module import (
    SampleClass,
    standalone_function,
    MockContainer,
    SampleService
)


def test_import_lib_adapter_resolves_class_method():
    """Test that ImportLibAdapter can resolve a class method."""
    adapter = ImportLibAdapter()
    resolved = adapter("tests.resources.test_module.SampleClass.test_method")
    
    # Verify the function was resolved
    assert callable(resolved)
    
    # Call the function and verify results
    result = resolved(arg1="test")
    assert result["class"] == "SampleClass"
    assert result["method"] == "test_method"
    assert result["arg1"] == "test"
    assert result["initialized"] is True


def test_import_lib_adapter_resolves_standalone_function():
    """Test that ImportLibAdapter can resolve a standalone function."""
    adapter = ImportLibAdapter()
    resolved = adapter("tests.resources.test_module.standalone_function")
    
    # Verify the function was resolved
    assert callable(resolved)
    
    # Call the function and verify results
    result = resolved(arg1="test_value")
    assert result["function"] == "standalone_function"
    assert result["arg1"] == "test_value"


def test_import_lib_adapter_handles_errors():
    """Test that ImportLibAdapter handles various error conditions."""
    adapter = ImportLibAdapter()
    
    # Test invalid module
    with pytest.raises(ImportError):
        adapter("nonexistent_module.Class.method")
    
    # Test invalid class
    with pytest.raises(AttributeError):
        adapter("tests.resources.test_module.NonExistentClass.method")
    
    # Test invalid method
    with pytest.raises(AttributeError):
        adapter("tests.resources.test_module.SampleClass.nonexistent_method")


def test_di_adapter_resolves_service_method():
    """Test that DIAdapter can resolve a service method."""
    test_service = MagicMock()
    test_service.test_method = MagicMock(return_value={"service": "SampleService", "method": "test_method"})
    
    container = MagicMock()
    container.get = MagicMock(return_value=test_service)
    
    adapter = DIAdapter(container)
    resolved = adapter("@test_service.test_method")
    
    # Verify the function was resolved
    assert callable(resolved)
    
    # Call the function and verify results
    result = resolved()
    assert result["service"] == "SampleService"
    assert result["method"] == "test_method"
    
    # Check that the container.get was called with the right service name
    container.get.assert_called_once_with("test_service")


def test_di_adapter_requires_at_symbol():
    """Test that DIAdapter requires targets to start with @."""
    container = MockContainer()
    adapter = DIAdapter(container)
    
    # Test without @ prefix should raise an error
    with pytest.raises(ValueError):
        adapter("test_service.test_method")


def test_di_adapter_handles_errors():
    """Test that DIAdapter handles various error conditions."""
    container = MockContainer()
    adapter = DIAdapter(container)
    
    # Test non-existent service
    with pytest.raises(ValueError):
        adapter("@nonexistent_service.method")
    
    # Test non-existent method
    with pytest.raises(AttributeError):
        adapter("@test_service.nonexistent_method")


def test_custom_adapter_protocol():
    """Test that a custom adapter implementing AdapterProtocol works."""
    # Create a custom adapter
    class CustomAdapter:
        def __call__(self, target: str) -> Callable:
            def fixed_result(*args, **kwargs):
                return {"target": target, "args": args, "kwargs": kwargs}
            return fixed_result
    
    # Verify it works with the protocol
    adapter = CustomAdapter()
    assert isinstance(adapter, AdapterProtocol)
    
    # Test resolving a target
    resolved = adapter("anything")
    result = resolved(1, 2, key="value")
    
    assert result["target"] == "anything"
    assert result["args"] == (1, 2)
    assert result["kwargs"] == {"key": "value"}


def test_di_adapter_requires_get_method():
    """Test that DIAdapter requires a container with a get method."""
    # Create a mock container without a get method
    container = MagicMock()
    delattr(container, "get")
    
    # Attempting to create a DIAdapter with this should raise an error
    with pytest.raises(ValueError):
        DIAdapter(container)