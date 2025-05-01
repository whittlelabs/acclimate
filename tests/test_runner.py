"""
Tests for the acclimate.runner module.
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock, call
from argparse import Namespace

from acclimate.runner import CommandRunner
from acclimate.adapter import ImportLibAdapter, DIAdapter
from acclimate.yaml import YamlLoader
from tests.resources.test_module import MockContainer, SampleService


def test_command_runner_init_requires_commands_file():
    """Test that CommandRunner initialization requires a commands_file."""
    # Should raise ValueError if no commands_file is provided
    with pytest.raises(ValueError):
        CommandRunner({})


def test_command_runner_init_with_defaults():
    """Test that CommandRunner initializes with default values."""
    with patch('acclimate.yaml.YamlLoader.load_yaml', return_value={"commands": {}}):
        runner = CommandRunner({"commands_file": "dummy.yaml"})
        
        # Should create default resolver
        assert "import" in runner.resolvers
        assert isinstance(runner.resolvers["import"], ImportLibAdapter)
        
        # Should use the provided YamlLoader
        assert isinstance(runner.yaml_loader, YamlLoader)


def test_command_runner_init_with_custom_resolvers():
    """Test that CommandRunner initializes with custom resolvers."""
    custom_resolver = MagicMock()
    custom_resolver.__call__ = MagicMock(return_value=lambda: "Hello")
    
    with patch('acclimate.yaml.YamlLoader.load_yaml', return_value={"commands": {}}):
        runner = CommandRunner({
            "commands_file": "dummy.yaml",
            "resolvers": {
                "custom": custom_resolver
            }
        })
        
        # Should include the custom resolver
        assert "custom" in runner.resolvers
        assert runner.resolvers["custom"] is custom_resolver
        
        # Should still have the default resolver
        assert "import" in runner.resolvers


def test_command_runner_init_with_custom_yaml_loader():
    """Test that CommandRunner initializes with a custom YAML loader."""
    custom_loader = MagicMock()
    custom_loader.load_yaml = MagicMock(return_value={"commands": {}})
    
    runner = CommandRunner({
        "commands_file": "dummy.yaml",
        "yaml_loader": custom_loader
    })
    
    # Should use the custom loader
    assert runner.yaml_loader is custom_loader
    custom_loader.load_yaml.assert_called_once_with("dummy.yaml", "commands")


def test_command_runner_validates_yaml_loader_protocol():
    """Test that CommandRunner validates that the yaml_loader implements YamlLoaderProtocol."""
    # Create an object that doesn't implement the protocol
    invalid_loader = MagicMock()
    delattr(invalid_loader, "load_yaml")
    
    with pytest.raises(TypeError):
        CommandRunner({
            "commands_file": "dummy.yaml",
            "yaml_loader": invalid_loader
        })


def test_command_runner_resolve_target_uses_specified_resolution():
    """Test that _resolve_target uses the specified resolution type."""
    with patch('acclimate.yaml.YamlLoader.load_yaml', return_value={"commands": {}}):
        runner = CommandRunner({"commands_file": "dummy.yaml"})
        
        # Create mock resolvers
        runner.resolvers = {
            "import": MagicMock(),
            "custom": MagicMock()
        }
        
        # Test with specified resolution
        runner._resolve_target("test.target", "custom")
        runner.resolvers["custom"].assert_called_once_with("test.target")
        runner.resolvers["import"].assert_not_called()


def test_command_runner_resolve_target_falls_back_to_defaults():
    """Test that _resolve_target falls back to defaults if no resolution is specified."""
    with patch('acclimate.yaml.YamlLoader.load_yaml', return_value={"commands": {}, "defaults": {"resolution": "custom"}}):
        runner = CommandRunner({"commands_file": "dummy.yaml"})
        
        # Create mock resolvers
        runner.resolvers = {
            "import": MagicMock(),
            "custom": MagicMock()
        }
        
        # Test fallback to defaults
        runner._resolve_target("test.target")
        runner.resolvers["custom"].assert_called_once_with("test.target")
        runner.resolvers["import"].assert_not_called()


def test_command_runner_resolve_target_falls_back_to_import():
    """Test that _resolve_target falls back to "import" if no resolution or default is specified."""
    with patch('acclimate.yaml.YamlLoader.load_yaml', return_value={"commands": {}}):
        runner = CommandRunner({"commands_file": "dummy.yaml"})
        
        # Create mock resolvers
        runner.resolvers = {
            "import": MagicMock(),
            "custom": MagicMock()
        }
        
        # Test fallback to import
        runner._resolve_target("test.target")
        runner.resolvers["import"].assert_called_once_with("test.target")
        runner.resolvers["custom"].assert_not_called()


def test_command_runner_integration_with_tempfile(temp_yaml_file):
    """Integration test using a real temporary YAML file."""
    yaml_file, yaml_content = temp_yaml_file
    
    # Create a mock function that we'll have our ImportLibAdapter return
    mock_function = MagicMock(return_value={"result": "success", "arg1": "test_arg"})
    
    # Create a mock for our ImportLibAdapter that will return our mock_function
    mock_adapter = MagicMock()
    mock_adapter.return_value = mock_function
    
    # Create a mock for the sys.argv to simulate command-line arguments
    with patch('sys.argv', ['acclimate', 'test', 'test_arg']), \
         patch('acclimate.adapter.ImportLibAdapter.__call__', mock_adapter):
        
        # Create the runner and run it
        runner = CommandRunner({
            "commands_file": yaml_file
        })
        
        # Explicitly check that our commands are loaded correctly
        assert "test" in runner.commands_dict, f"'test' command not in loaded commands: {list(runner.commands_dict.keys())}"
        assert runner.commands_dict["test"]["target"] == "tests.resources.test_module.SampleClass.test_method"
        
        # Run the CommandRunner - this should use our mocked adapter
        result = runner.run()
        
        # Verify the adapter was called with the right target
        mock_adapter.assert_called_with("tests.resources.test_module.SampleClass.test_method")
        
        # Verify the returned function was called with the right arguments
        mock_function.assert_called_once_with(arg1="test_arg")
        
        # Verify the result
        assert result == {"result": "success", "arg1": "test_arg"}


def test_command_runner_with_di_container(temp_yaml_file):
    """Test CommandRunner with a DI container for resolution."""
    yaml_file, yaml_content = temp_yaml_file
    
    # Create a mock container and service
    container = MockContainer()
    test_service = SampleService()
    container.register("test_service", test_service)
    
    # Mock the test method
    test_service.test_method = MagicMock(return_value={"result": "from di", "arg1": "test_arg"})
    
    # Create the runner with DI container
    with patch('sys.argv', ['acclimate', 'di_test', '--arg1', 'test_arg']):
        runner = CommandRunner({
            "commands_file": yaml_file,
            "resolvers": {
                "import": ImportLibAdapter(),
                "di": DIAdapter(container)
            }
        })
        result = runner.run()
        
        # Verify the correct method was called with the right arguments
        test_service.test_method.assert_called_once_with(arg1="test_arg")
        assert result == {"result": "from di", "arg1": "test_arg"}


def test_format_result_table():
    """Test the format_result method with table format."""
    with patch('acclimate.yaml.YamlLoader.load_yaml', return_value={"commands": {}}):
        runner = CommandRunner({"commands_file": "dummy.yaml"})
        
        # Test with list of dictionaries
        data = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
        ]
        
        print_map = {
            "format": "table",
            "columns": ["id", "name"],
            "header": "true"
        }
        
        result = runner.format_result(data, print_map)
        expected = "id | name\n---------\n1 | Item 1\n2 | Item 2"
        
        # Normalize whitespace for comparison
        result = result.replace(" ", "")
        expected = expected.replace(" ", "")
        
        assert result == expected


def test_format_result_json():
    """Test the format_result method with JSON format."""
    with patch('acclimate.yaml.YamlLoader.load_yaml', return_value={"commands": {}}):
        runner = CommandRunner({"commands_file": "dummy.yaml"})
        
        # Test with list of dictionaries
        data = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
        ]
        
        print_map = {
            "format": "json"
        }
        
        result = runner.format_result(data, print_map)
        assert '"id": 1' in result
        assert '"name": "Item 1"' in result
        assert '"id": 2' in result
        assert '"name": "Item 2"' in result