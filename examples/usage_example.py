#!/usr/bin/env python3
"""
Example usage of Acclimate's CommandRunner with custom resolution adapters.
This demonstrates how to configure different resolver strategies.
"""

import os
import sys
from typing import Dict, Any, Callable

# Add src directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from acclimate.runner import CommandRunner
from acclimate.adapter import AdapterProtocol, ImportLibAdapter, DIAdapter


# Example class that we'll use for demonstration purposes
class ExampleService:
    def __init__(self, name="DefaultService"):
        self.name = name
    
    def greet(self):
        return f"Hello from {self.name}!"


# Example of a simple DI container
class SimpleContainer:
    def __init__(self):
        self.services = {}
    
    def register(self, service_id: str, service):
        self.services[service_id] = service
    
    def get(self, service_id: str):
        if service_id not in self.services:
            raise ValueError(f"Service not registered: {service_id}")
        return self.services[service_id]


# Example of a custom adapter that implements the AdapterProtocol
class CustomAdapter:
    """
    A custom adapter that demonstrates how to implement the AdapterProtocol.
    This example always returns a fixed function regardless of the target.
    """
    
    def __call__(self, target: str) -> Callable:
        """
        Always returns a fixed function for demonstration purposes.
        
        Args:
            target: Target string (ignored in this implementation)
        
        Returns:
            A fixed function that returns a message
        """
        def fixed_func(*args, **kwargs):
            return f"Custom adapter called with target: {target}, args: {args}, kwargs: {kwargs}"
        
        return fixed_func


def setup_di_container():
    """Set up a simple DI container with some services."""
    container = SimpleContainer()
    
    # Register some services
    container.register("greeter", ExampleService("GreeterService"))
    container.register("example_service", ExampleService("ExampleService"))
    
    return container


def main():
    """Demonstrate how to use CommandRunner with different resolution strategies."""
    # Get paths relative to this file
    base_dir = os.path.dirname(os.path.abspath(__file__))
    commands_file = os.path.join(base_dir, "commands.yaml")
    
    # Set up a container for DI resolution
    container = setup_di_container()
    
    # Configure CommandRunner with multiple resolvers
    config = {
        "commands_file": commands_file,
        "resolvers": {
            # Standard import-based resolver
            "import": ImportLibAdapter(),
            
            # DI container-based resolver
            "di": DIAdapter(container),
            
            # Custom resolver for demonstration
            "custom": CustomAdapter()
        }
    }
    
    # Create the CommandRunner
    runner = CommandRunner(config)
    
    print("\n=== Acclimate Usage Example ===")
    print("This example demonstrates different resolution strategies.")
    print("You can specify the resolution type in commands.yaml or as defaults.")
    print("Available resolvers in this example: import, di, custom")
    print("\nRunning CommandRunner with the configured adapters...")
    
    # Run the CommandRunner
    result = runner.run()
    
    print("\nExample complete!")
    return result


if __name__ == "__main__":
    main()