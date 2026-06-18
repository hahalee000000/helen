"""Tests for Python FFI object wrapping.

Tests the PythonObject contract implementation.
"""

import pytest
from helen.ffi.python_object import WrappedPythonObject


class TestPythonObject:
    """Test Python object wrapping and access."""
    
    def test_wrapper_exists(self):
        """PythonObject wrapper should be instantiable."""
        obj = WrappedPythonObject(42)
        assert obj is not None
    
    def test_unwrap_returns_original(self):
        """unwrap() should return the original Python object."""
        original = [1, 2, 3]
        wrapper = WrappedPythonObject(original)
        assert wrapper.unwrap() is original
    
    def test_str_representation(self):
        """__str__ should return string representation."""
        wrapper = WrappedPythonObject(42)
        assert str(wrapper) == "42"
        
        wrapper = WrappedPythonObject("hello")
        assert str(wrapper) == "hello"
    
    def test_get_attribute(self):
        """get_attribute should access object attributes."""
        class TestClass:
            def __init__(self):
                self.value = 42
                self.name = "test"
        
        obj = TestClass()
        wrapper = WrappedPythonObject(obj)
        
        assert wrapper.get_attribute("value") == 42
        assert wrapper.get_attribute("name") == "test"
    
    def test_get_attribute_missing_raises(self):
        """get_attribute should raise for missing attributes."""
        wrapper = WrappedPythonObject(42)
        
        with pytest.raises(AttributeError):
            wrapper.get_attribute("nonexistent")
    
    def test_call_function(self):
        """call() should invoke callable objects."""
        def add(a, b):
            return a + b
        
        wrapper = WrappedPythonObject(add)
        result = wrapper.call(2, 3)
        assert result == 5
    
    def test_call_with_kwargs(self):
        """call() should support keyword arguments."""
        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"
        
        wrapper = WrappedPythonObject(greet)
        result = wrapper.call("Alice", greeting="Hi")
        assert result == "Hi, Alice!"
    
    def test_call_non_callable_raises(self):
        """call() on non-callable should raise TypeError."""
        wrapper = WrappedPythonObject(42)
        
        with pytest.raises(TypeError):
            wrapper.call()
    
    def test_getitem_list(self):
        """__getitem__ should work with lists."""
        wrapper = WrappedPythonObject([10, 20, 30])
        assert wrapper[0] == 10
        assert wrapper[2] == 30
    
    def test_getitem_dict(self):
        """__getitem__ should work with dicts."""
        wrapper = WrappedPythonObject({"a": 1, "b": 2})
        assert wrapper["a"] == 1
        assert wrapper["b"] == 2
    
    def test_getitem_missing_key_raises(self):
        """__getitem__ should raise for missing keys."""
        wrapper = WrappedPythonObject({"a": 1})
        
        with pytest.raises(KeyError):
            _ = wrapper["nonexistent"]
    
    def test_nested_attribute_access(self):
        """Nested attributes should be wrapped."""
        class Inner:
            def __init__(self):
                self.value = 42
        
        class Outer:
            def __init__(self):
                self.inner = Inner()
        
        wrapper = WrappedPythonObject(Outer())
        inner_wrapper = wrapper.get_attribute("inner")
        
        # Should be wrapped
        assert hasattr(inner_wrapper, 'unwrap')
        assert inner_wrapper.get_attribute("value") == 42
    
    def test_method_call(self):
        """Methods should be callable."""
        class Calculator:
            def add(self, a, b):
                return a + b
            
            def multiply(self, a, b):
                return a * b
        
        calc = Calculator()
        wrapper = WrappedPythonObject(calc)
        
        add_method = wrapper.get_attribute("add")
        result = add_method.call(2, 3)
        assert result == 5
