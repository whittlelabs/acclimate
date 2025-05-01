"""
Tests for the acclimate.yaml module.
"""
import os
import pytest
import tempfile

from acclimate.yaml import YamlLoader, YamlLoaderProtocol


@pytest.fixture
def yaml_with_nested_data():
    """Creates a temporary YAML file with nested data for testing."""
    with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as temp:
        content = """
        top_level:
          nested:
            key1: value1
            key2: value2
          array:
            - item1
            - item2
            - item3
        another_section:
          key: value
        """
        temp.write(content.encode('utf-8'))
        temp_path = temp.name
        
    yield temp_path
    
    # Clean up the temporary file
    os.unlink(temp_path)


def test_yamlloader_loads_yaml_file(yaml_with_nested_data):
    """Test that YamlLoader can load a YAML file."""
    loader = YamlLoader()
    content = loader.load_yaml(yaml_with_nested_data)
    
    # Verify the content was loaded correctly
    assert 'top_level' in content
    assert 'another_section' in content
    assert content['top_level']['nested']['key1'] == 'value1'
    assert content['top_level']['array'][0] == 'item1'
    assert len(content['top_level']['array']) == 3


def test_yamlloader_loads_subpath_string(yaml_with_nested_data):
    """Test that YamlLoader can load a subpath using a string."""
    loader = YamlLoader()
    content = loader.load_yaml(yaml_with_nested_data, 'top_level')
    
    # Verify we got the correct subpath
    assert 'nested' in content
    assert 'array' in content
    assert content['nested']['key2'] == 'value2'


def test_yamlloader_loads_subpath_list(yaml_with_nested_data):
    """Test that YamlLoader can load a subpath using a list."""
    loader = YamlLoader()
    content = loader.load_yaml(yaml_with_nested_data, ['top_level', 'nested'])
    
    # Verify we got the correct subpath
    assert 'key1' in content
    assert 'key2' in content
    assert content['key1'] == 'value1'


def test_yamlloader_handles_nonexistent_subpath(yaml_with_nested_data):
    """Test that YamlLoader returns None for nonexistent subpaths."""
    loader = YamlLoader()
    content = loader.load_yaml(yaml_with_nested_data, 'nonexistent')
    
    # Should return None for a nonexistent path
    assert content is None


def test_yamlloader_validates_file_extension():
    """Test that YamlLoader validates file extensions."""
    loader = YamlLoader()
    
    # Create a temporary file with an invalid extension
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp:
        temp.write(b'Not a YAML file')
        temp_path = temp.name
        
    try:
        # Should raise ValueError for non-YAML file
        with pytest.raises(ValueError):
            loader.load_yaml(temp_path)
    finally:
        # Clean up
        os.unlink(temp_path)


def test_yamlloader_validates_subpath_type():
    """Test that YamlLoader validates subpath types."""
    loader = YamlLoader()
    
    # Create a valid YAML file
    with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as temp:
        temp.write(b'key: value')
        temp_path = temp.name
        
    try:
        # Should raise ValueError for invalid subpath type
        with pytest.raises(ValueError):
            loader.load_yaml(temp_path, subpath=123)  # Integer is invalid type
    finally:
        # Clean up
        os.unlink(temp_path)


def test_custom_yamlloader_protocol():
    """Test that a custom loader implementing YamlLoaderProtocol works."""
    # Create a custom loader
    class CustomLoader:
        def load_yaml(self, file_path, subpath=None):
            return {"custom": True, "file": file_path, "subpath": subpath}
    
    # Verify it works with the protocol
    loader = CustomLoader()
    assert isinstance(loader, YamlLoaderProtocol)
    
    # Test loading
    result = loader.load_yaml("dummy.yaml", "test")
    assert result["custom"] is True
    assert result["file"] == "dummy.yaml"
    assert result["subpath"] == "test"