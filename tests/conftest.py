"""
Shared fixtures and configuration for acclimate tests.
"""
import os
import pytest
import tempfile
import yaml
from typing import Dict, Any

@pytest.fixture
def temp_yaml_file():
    """
    Creates a temporary YAML file for testing.
    
    Returns a tuple of (file_path, content) where content is the dict that was written to the file.
    """
    with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as temp:
        # Create a basic commands structure
        content = {
            "defaults": {
                "resolution": "import"
            },
            "commands": {
                "test": {
                    "help": "Test command",
                    "target": "tests.resources.test_module.SampleClass.test_method",
                    "arguments": {
                        "arg1": {
                            "help": "Test argument",
                            "positional": True
                        }
                    }
                },
                "di_test": {
                    "help": "DI test command",
                    "target": "@test_service.test_method",
                    "resolution": "di"
                }
            }
        }
        
        # Write to the temporary file - convert to binary for Python 3
        yaml_content = yaml.dump(content)
        temp.write(yaml_content.encode('utf-8'))
        temp_path = temp.name
        
    yield temp_path, content
    
    # Clean up the temporary file
    os.unlink(temp_path)