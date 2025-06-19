"""
Test utilities for the application.
"""

def test_function():
    """A simple test function."""
    print("This is a test function")
    return True

class TestClass:
    """A simple test class."""
    
    def __init__(self, name):
        """Initialize the test class."""
        self.name = name
        
    def get_name(self):
        """Get the name of the test class."""
        return self.name
        
    def set_name(self, name):
        """Set the name of the test class."""
        self.name = name
        return self
