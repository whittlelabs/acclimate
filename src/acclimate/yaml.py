import yaml
from typing import Any, Optional, Protocol, runtime_checkable

@runtime_checkable
class YamlLoaderProtocol(Protocol):
    """Protocol defining the interface for YAML loaders."""
    def load_yaml(self, file_path: str, subpath: Optional[Any] = None) -> Any:
        """
        Load a YAML file and optionally navigate to a subpath.
        
        Args:
            file_path: Path to the YAML file to load
            subpath: Either a string or list of strings representing nested keys to access
                
        Returns:
            The loaded YAML content, potentially narrowed to a specific path
        """
        ...

class YamlLoader(YamlLoaderProtocol):
    def load_yaml(self, file_path: str, subpath: Optional[Any] = None) -> Any:
        if not file_path.endswith('.yml') and not file_path.endswith('.yaml'):
            raise ValueError(f"File must be a YAML file. Got: {file_path}")
        
        if subpath and not isinstance(subpath, (str, list)):
            raise ValueError('Subpath must be a string or a list of strings')
        
        if isinstance(subpath, str):
            subpath = [subpath]

        with open(file_path, 'r') as file:
            all_content = yaml.safe_load(file)
            if subpath:
                content = all_content
                for key in subpath:
                    content = content.get(key)
                    if content is None:
                        return None
                return content
            else:
                return all_content
