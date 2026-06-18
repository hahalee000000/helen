"""Tests for Python FFI type conversion.

Tests the TypeConverter contract implementation.
"""

import pytest
from helen.ffi.type_converter import DefaultTypeConverter


class TestTypeConverter:
    """Test type conversion between Helen and Python."""
    
    def test_converter_exists(self):
        """TypeConverter should be instantiable."""
        converter = DefaultTypeConverter()
        assert converter is not None
    
    # Helen to Python conversion
    def test_helen_int_to_python(self):
        """Helen int should convert to Python int."""
        converter = DefaultTypeConverter()
        result = converter.helen_to_python(42)
        assert result == 42
        assert isinstance(result, int)
    
    def test_helen_float_to_python(self):
        """Helen float should convert to Python float."""
        converter = DefaultTypeConverter()
        result = converter.helen_to_python(3.14)
        assert result == 3.14
        assert isinstance(result, float)
    
    def test_helen_str_to_python(self):
        """Helen str should convert to Python str."""
        converter = DefaultTypeConverter()
        result = converter.helen_to_python("hello")
        assert result == "hello"
        assert isinstance(result, str)
    
    def test_helen_bool_to_python(self):
        """Helen bool should convert to Python bool."""
        converter = DefaultTypeConverter()
        assert converter.helen_to_python(True) is True
        assert converter.helen_to_python(False) is False
    
    def test_helen_null_to_python(self):
        """Helen null should convert to Python None."""
        converter = DefaultTypeConverter()
        result = converter.helen_to_python(None)
        assert result is None
    
    def test_helen_list_to_python(self):
        """Helen list should convert to Python list."""
        converter = DefaultTypeConverter()
        result = converter.helen_to_python([1, 2, 3])
        assert result == [1, 2, 3]
        assert isinstance(result, list)
    
    def test_helen_dict_to_python(self):
        """Helen dict should convert to Python dict."""
        converter = DefaultTypeConverter()
        result = converter.helen_to_python({"a": 1, "b": 2})
        assert result == {"a": 1, "b": 2}
        assert isinstance(result, dict)
    
    def test_helen_nested_list_to_python(self):
        """Helen nested list should convert recursively."""
        converter = DefaultTypeConverter()
        result = converter.helen_to_python([[1, 2], [3, 4]])
        assert result == [[1, 2], [3, 4]]
    
    def test_helen_nested_dict_to_python(self):
        """Helen nested dict should convert recursively."""
        converter = DefaultTypeConverter()
        result = converter.helen_to_python({"a": {"b": 1}})
        assert result == {"a": {"b": 1}}
    
    # Python to Helen conversion
    def test_python_int_to_helen(self):
        """Python int should convert to Helen int."""
        converter = DefaultTypeConverter()
        result = converter.python_to_helen(42)
        assert result == 42
        assert isinstance(result, int)
    
    def test_python_float_to_helen(self):
        """Python float should convert to Helen float."""
        converter = DefaultTypeConverter()
        result = converter.python_to_helen(3.14)
        assert result == 3.14
        assert isinstance(result, float)
    
    def test_python_str_to_helen(self):
        """Python str should convert to Helen str."""
        converter = DefaultTypeConverter()
        result = converter.python_to_helen("hello")
        assert result == "hello"
        assert isinstance(result, str)
    
    def test_python_bool_to_helen(self):
        """Python bool should convert to Helen bool."""
        converter = DefaultTypeConverter()
        assert converter.python_to_helen(True) is True
        assert converter.python_to_helen(False) is False
    
    def test_python_none_to_helen(self):
        """Python None should convert to Helen null."""
        converter = DefaultTypeConverter()
        result = converter.python_to_helen(None)
        assert result is None
    
    def test_python_list_to_helen(self):
        """Python list should convert to Helen list."""
        converter = DefaultTypeConverter()
        result = converter.python_to_helen([1, 2, 3])
        assert result == [1, 2, 3]
        assert isinstance(result, list)
    
    def test_python_dict_to_helen(self):
        """Python dict should convert to Helen dict."""
        converter = DefaultTypeConverter()
        result = converter.python_to_helen({"a": 1, "b": 2})
        assert result == {"a": 1, "b": 2}
        assert isinstance(result, dict)
    
    def test_python_tuple_to_helen(self):
        """Python tuple should convert to Helen list."""
        converter = DefaultTypeConverter()
        result = converter.python_to_helen((1, 2, 3))
        assert result == [1, 2, 3]
        assert isinstance(result, list)
    
    def test_python_complex_object_wrapped(self):
        """Complex Python objects should be wrapped as PythonObject."""
        converter = DefaultTypeConverter()
        
        class CustomClass:
            def __init__(self):
                self.value = 42
        
        obj = CustomClass()
        result = converter.python_to_helen(obj)
        
        # Should be wrapped, not converted
        assert hasattr(result, 'unwrap')
        assert result.unwrap() is obj
    
    def test_python_numpy_array_wrapped(self):
        """NumPy arrays should be wrapped (not converted to list)."""
        converter = DefaultTypeConverter()
        
        try:
            import numpy as np
            arr = np.array([1, 2, 3])
            result = converter.python_to_helen(arr)
            
            # Should be wrapped to preserve numpy functionality
            assert hasattr(result, 'unwrap')
            assert result.unwrap() is arr
        except ImportError:
            pytest.skip("NumPy not available")
    
    def test_roundtrip_simple_types(self):
        """Simple types should roundtrip correctly."""
        converter = DefaultTypeConverter()
        
        test_values = [42, 3.14, "hello", True, False, None]
        for value in test_values:
            result = converter.python_to_helen(converter.helen_to_python(value))
            assert result == value
