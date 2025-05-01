"""
Test module containing classes and functions for testing acclimate.
"""

class SampleClass:
    """A simple test class for testing the ImportLibAdapter."""
    def __init__(self):
        self.initialized = True
        
    def test_method(self, arg1=None):
        """A test method that returns information about itself."""
        return {
            "class": self.__class__.__name__,
            "method": "test_method",
            "arg1": arg1,
            "initialized": self.initialized
        }

def standalone_function(arg1=None):
    """A standalone function for testing."""
    return {
        "function": "standalone_function",
        "arg1": arg1
    }

class SampleService:
    """A test service for DI testing."""
    def __init__(self, name="SampleService"):
        self.name = name
        
    def test_method(self, arg1=None):
        """A test method that returns information about the service."""
        return {
            "service": self.name,
            "method": "test_method",
            "arg1": arg1
        }

# Simple DI container for testing
class MockContainer:
    def __init__(self):
        self.services = {
            "test_service": SampleService()
        }
    
    def get(self, service_id):
        if service_id not in self.services:
            raise ValueError(f"Service not registered: {service_id}")
        return self.services[service_id]
    
    def register(self, service_id, service):
        self.services[service_id] = service