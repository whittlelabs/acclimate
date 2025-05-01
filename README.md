# Acclimate 🌡️

[![PyPI version](https://img.shields.io/pypi/v/acclimate.svg)](https://pypi.org/project/acclimate/)
[![Python Versions](https://img.shields.io/pypi/pyversions/acclimate.svg)](https://pypi.org/project/acclimate/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Acclimate is a flexible CLI configuration utility that pairs YAML configuration files with a customizable resolution system. It allows you to define commands and subcommands in YAML along with target service or function calls, and acclimate will resolve these commands to the correct implementation.

## Features

- **YAML-based Command Configuration**: Define your CLI structure, help text, and arguments in a clean YAML format
- **Flexible Target Resolution**: Resolve targets via dependency injection containers or direct imports
- **Pluggable Adapter System**: Create custom resolution strategies with the adapter protocol
- **Nested Subcommands**: Support for complex command hierarchies
- **Output Formatting**: Format command results as tables or JSON
- **Dynamic Command Arguments**: Support for flags, positional arguments, and more

## Installation

```bash
pip install acclimate
```

## Quick Start

### 1. Create a commands.yaml file

```yaml
defaults:
  # Default resolution type (optional)
  resolution: "import"

commands:
  hello:
    help: "Say hello to someone"
    target: "my_app.greeter.HelloService.greet"
    arguments:
      name:
        help: "Name of the person to greet"
        positional: true
  
  config:
    help: "Configuration commands"
    subcommands:
      list:
        help: "List configuration values"
        target: "my_app.config.list_config"
        print_result: true
        print_map:
          format: table
          columns:
            - key
            - value
```

### 2. Create a simple runner script

```python
from acclimate.runner import CommandRunner
from acclimate.adapter import ImportLibAdapter

# Configure the CommandRunner
config = {
    "commands_file": "path/to/commands.yaml",
    "resolvers": {
        "import": ImportLibAdapter(),
    }
}

# Create and run the CommandRunner
runner = CommandRunner(config)
runner.run()
```

## Target Resolution

Acclimate supports multiple ways to resolve command targets:

### Import-based Resolution

By default, Acclimate uses Python's import system to resolve targets like `module.path.Class.method`. The `ImportLibAdapter` will:

1. Import the specified module
2. Instantiate the class 
3. Return the bound method

Example YAML configuration:
```yaml
commands:
  example:
    help: "Example command"
    target: "my_module.MyClass.my_method"
    resolution: "import"  # Optional, "import" is the default
```

### Dependency Injection Resolution

When using a DI container, you can specify the `di` resolution type and provide a `DIAdapter`. The `DIAdapter` will:

1. Get the service from your container
2. Return the specified method

Example YAML configuration:
```yaml
commands:
  example:
    help: "Example command"
    target: "@my_service.my_method"
    resolution: "di"
```

Example runner setup:
```python
from acclimate.runner import CommandRunner
from acclimate.adapter import ImportLibAdapter, DIAdapter
from my_di_library import Container

# Set up your DI container
container = Container()
container.register(...)

# Configure the CommandRunner with multiple resolvers
config = {
    "commands_file": "path/to/commands.yaml",
    "resolvers": {
        "import": ImportLibAdapter(),
        "di": DIAdapter(container),
    }
}

runner = CommandRunner(config)
runner.run()
```

## Custom Resolution Adapters

You can create custom resolution strategies by implementing the `AdapterProtocol`:

```python
from acclimate.adapter import AdapterProtocol

class MyCustomAdapter:
    def __call__(self, target: str) -> Callable:
        # Your custom resolution logic here
        # Must return a callable function
        ...

# Use your custom adapter
config = {
    "commands_file": "path/to/commands.yaml",
    "resolvers": {
        "import": ImportLibAdapter(),
        "di": DIAdapter(container),
        "custom": MyCustomAdapter(),
    }
}
```

## Advanced YAML Configuration

### Subcommands

```yaml
commands:
  parent:
    help: "Parent command"
    subcommands:
      child1:
        help: "First child command"
        target: "module.Class.method1"
      child2:
        help: "Second child command"
        target: "module.Class.method2"
```

### Command Aliases

```yaml
commands:
  commit:
    aliases: ["c", "com"]
    help: "Commit changes"
    target: "module.commit"
```

### Output Formatting

```yaml
commands:
  list:
    help: "List items"
    target: "module.list_items"
    print_result: true
    print_map:
      format: table  # or "json"
      columns:
        - id
        - name
        - status
      order_by: name
```

## Examples

Check the `examples/` directory for complete usage examples.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the license file for details.