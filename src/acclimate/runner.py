import argparse
import json
import os
from typing import Dict, Any, Optional, Union, Callable, TypeVar

from acclimate.adapter import AdapterProtocol, ImportLibAdapter
from acclimate.yaml import YamlLoader, YamlLoaderProtocol

T = TypeVar('T', bound=Callable)

class CommandRunner:
    """
    A CLI command runner that uses a YAML configuration file to define commands and subcommands,
    and resolves targets using pluggable resolution strategies.
    """
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the CommandRunner with configuration.
        
        Args:
            config: Dictionary containing configuration options:
                - commands_file: Path to the commands YAML file (required)
                - resolvers: Dictionary mapping resolution types to adapter instances
                  Each adapter must implement the AdapterProtocol interface
                - yaml_loader: Optional YamlLoader instance (defaults to acclimate.yaml.YamlLoader)
        """
        self.commands_file = config.get("commands_file")
        if not self.commands_file:
            raise ValueError("commands_file must be specified in the configuration")
        
        # Get resolvers map or initialize with default import resolver
        self.resolvers = config.get("resolvers", {})
        
        # Ensure we have the default import resolver
        if "import" not in self.resolvers:
            self.resolvers["import"] = ImportLibAdapter()
            
        # Ensure we have at least one resolver
        if not self.resolvers:
            self.resolvers = {"import": ImportLibAdapter()}
        
        # Get or create yaml loader
        self.yaml_loader = config.get("yaml_loader")
        if not self.yaml_loader:
            self.yaml_loader = YamlLoader()
        elif not isinstance(self.yaml_loader, YamlLoaderProtocol):
            raise TypeError(f"yaml_loader must implement YamlLoaderProtocol")
            
        self.commands_dict = self._load_commands()
        self.defaults = self.commands_dict.get("defaults", {})

    def _load_commands(self):
        """Load commands from the YAML file."""
        return self.yaml_loader.load_yaml(self.commands_file, "commands")

    def _resolve_target(self, target: str, resolution_type: Optional[str] = None) -> Callable:
        """
        Resolve a target string using the specified resolution strategy.
        
        Args:
            target: Target string to resolve
            resolution_type: The resolution strategy to use (must be a key in self.resolvers)
            
        Returns:
            The resolved callable
        """
        # Use command-specific resolution type, fall back to defaults
        if not resolution_type:
            resolution_type = self.defaults.get("resolution")
        
        # If still no resolution type, use "import" as the default
        if not resolution_type:
            resolution_type = "import"
            
        # Get the resolver adapter
        resolver = self.resolvers.get(resolution_type)
        if not resolver:
            available_resolvers = ', '.join(self.resolvers.keys())
            raise ValueError(f"Unknown resolution type: {resolution_type}. Available types: {available_resolvers}")
            
        # Verify the resolver implements the adapter protocol
        if not isinstance(resolver, AdapterProtocol):
            raise TypeError(f"Resolver for {resolution_type} does not implement AdapterProtocol")
            
        # Resolve the target using the adapter
        return resolver(target)

    def build_subcommands(self, subparsers, commands_dict):
        """Build subcommand parsers recursively from the command configuration."""
        for cmd_name, cmd_info in commands_dict.items():
            # Skip the "defaults" key as it's not a command
            if cmd_name == "defaults":
                continue
                
            help_text = cmd_info.get("help", "")
            aliases = cmd_info.get("aliases", [])
            subparser = subparsers.add_parser(cmd_name, help=help_text, aliases=aliases)

            if "target" in cmd_info:
                subparser.set_defaults(target=cmd_info["target"])
                # Store resolution type if specified
                if "resolution" in cmd_info:
                    subparser.set_defaults(resolution=cmd_info["resolution"])

            # Optional flags
            if "print_result" in cmd_info:
                subparser.set_defaults(print_result=cmd_info["print_result"])
            if "print_map" in cmd_info:
                subparser.set_defaults(print_map=cmd_info["print_map"])

            # Add known arguments (positional or optional)
            for arg_name, arg_value in cmd_info.get("arguments", {}).items():
                if isinstance(arg_value, dict):
                    # New logic to support positional arguments with 'nargs'
                    if arg_value.get("flag", False):
                        subparser.add_argument(f"--{arg_name}", help=arg_value.get("help", ""), action="store_true", default=False)
                    elif arg_value.get("positional", False):
                        subparser.add_argument(arg_name, help=arg_value.get("help", ""), nargs=arg_value.get("nargs", None), default=arg_value.get("default"))
                    else:
                        subparser.add_argument(f"--{arg_name}", help=arg_value.get("help", ""), default=arg_value.get("default"), nargs=arg_value.get("nargs", None))
                else:
                    # Treat as a required positional argument
                    subparser.add_argument(arg_name, help=arg_value)

            # Nested subcommands
            if "subcommands" in cmd_info:
                nested_subparsers = subparser.add_subparsers(dest=f"{cmd_name}_subcommand")
                self.build_subcommands(nested_subparsers, cmd_info["subcommands"])

    def parse_unknown_as_kwargs(self, unknown_args):
        """
        Convert leftover unknown args of the form:
          --key value
          --key=value
        into a dict: {'key': 'value'}.

        Also treats a flag like --flag with no value as True.
        """
        kwargs = {}
        idx = 0
        while idx < len(unknown_args):
            token = unknown_args[idx]
            # Only process if it starts with --
            if token.startswith("--"):
                if "=" in token:
                    # e.g. --foo=bar
                    key, value = token.lstrip("-").split("=", 1)
                    kwargs[key] = value
                else:
                    # e.g. --foo bar or just --foo
                    key = token.lstrip("-")
                    # Look ahead if there's another arg
                    if idx + 1 < len(unknown_args):
                        next_token = unknown_args[idx + 1]
                        if next_token.startswith("--"):
                            # The next token is another flag, so interpret this one as bool
                            kwargs[key] = True
                        else:
                            # next token is a value for this key
                            kwargs[key] = next_token
                            idx += 1
                    else:
                        # no next token, treat as True
                        kwargs[key] = True
            else:
                # Some unknown positional leftover. Decide how to handle it (ignore or collect).
                pass
            idx += 1

        return kwargs

    def format_result(self, result, print_map):
        """ Formatting logic for the results. """
        fmt = print_map.get("format", "table")
        columns = print_map.get("columns", [])
        order_by = print_map.get("order_by", None)
        print_header = print_map.get("header", "true") == "true"

        if hasattr(result, "data"):
            data = result.data
        elif isinstance(result, list):
            data = result
        else:
            return str(result)

        if order_by:
            def get_key_value(item):
                if isinstance(item, dict):
                    return item.get(order_by)
                else:
                    return getattr(item, order_by, None)
            data = sorted(data, key=get_key_value)

        if fmt == "json":
            return json.dumps(data, indent=2, default=str)
        elif fmt == "table":
            if not columns:
                return str(data)
            lines = []
            header = " | ".join(columns)
            separator = "-" * len(header)
            if print_header:
                lines.append(header)
                lines.append(separator)

            for item in data:
                row_cells = []
                for col in columns:
                    # handle dict vs. object
                    val = item.get(col) if isinstance(item, dict) else getattr(item, col, None)
                    row_cells.append(str(val))
                lines.append(" | ".join(row_cells))
            return "\n".join(lines)

        return str(result)

    def run(self):
        """Parse arguments and execute the requested command."""
        parser = argparse.ArgumentParser(description="Command line interface.")
        subparsers = parser.add_subparsers(dest="top_command")

        self.build_subcommands(subparsers, self.commands_dict)

        # 1) parse_known_args to separate recognized vs. leftover
        args, unknown_args = parser.parse_known_args()

        # Generalized nargs handling: for any argument defined with nargs '+' or '*'
        for action in parser._actions:
            if hasattr(action, 'nargs') and action.nargs in ("+", "*"):
                value = getattr(args, action.dest, None)
                if isinstance(value, list) and all(isinstance(v, str) for v in value):
                    setattr(args, action.dest, " ".join(value))

        if not args.top_command:
            parser.print_help()
            return

        target = getattr(args, "target", None)
        if not target:
            parser.print_help()
            return

        # Get resolution type if specified, otherwise use None to fallback to defaults
        resolution = getattr(args, "resolution", None)
            
        # Resolve the function based on target and resolution type
        func = self._resolve_target(target, resolution)

        # 3) Build a dictionary from the known argparse results
        args_dict = vars(args).copy()
        print_result = args_dict.pop("print_result", False)
        print_map = args_dict.pop("print_map", None)
        args_dict.pop("target", None)
        args_dict.pop("top_command", None)
        args_dict.pop("resolution", None)  # Remove resolution if it exists

        # Remove any subcommand placeholders
        for key in list(args_dict.keys()):
            if key.endswith("_subcommand"):
                args_dict.pop(key)

        # 4) Parse leftover unknown args as **kwargs
        dynamic_kwargs = self.parse_unknown_as_kwargs(unknown_args)

        # 5) Merge them into the final arg dict
        args_dict.update(dynamic_kwargs)

        # 6) Call the function with known + dynamic arguments
        result = func(**args_dict)

        # 7) Print result if requested
        if print_result:
            if print_map:
                print(self.format_result(result, print_map))
            else:
                print(result)
        
        return result


def load_and_run(config: Dict[str, Any]):
    """
    Legacy convenience function to create and run a CommandRunner instance.
    
    Args:
        config: Dictionary containing configuration options
    """
    runner = CommandRunner(config)
    return runner.run()


if __name__ == "__main__":
    import os
    
    # Example usage with custom resolvers
    config = {
        "commands_file": os.path.join(os.getcwd(), "examples", "commands.yaml"),
        "resolvers": {
            "import": ImportLibAdapter(),
            # Example: If you had a DI container
            # "di": DIAdapter(my_container)
        }
    }
    
    load_and_run(config)
