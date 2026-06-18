"""Tests for Python FFI module loading.

Tests the PythonModule and PythonRuntime contract implementations.
"""

import pytest
from helen.ffi.python_runtime import DefaultPythonRuntime
from helen.ffi.python_module import WrappedPythonModule


class TestPythonModule:
    """Test Python module wrapping."""
    
    def test_module_wrapper_exists(self):
        """PythonModule wrapper should be instantiable."""
        import math
        module = WrappedPythonModule("math", math)
        assert module is not None
        assert module.name == "math"
    
    def test_get_module_returns_original(self):
        """get_module() should return the original module."""
        import math
        module = WrappedPythonModule("math", math)
        assert module.get_module() is math
    
    def test_getattr_function(self):
        """__getattr__ should access module functions."""
        import math
        module = WrappedPythonModule("math", math)
        
        sqrt = module.sqrt
        assert hasattr(sqrt, 'call')
        result = sqrt.call(16)
        assert result == 4.0
    
    def test_getattr_constant(self):
        """__getattr__ should access module constants."""
        import math
        module = WrappedPythonModule("math", math)
        
        pi = module.pi
        assert pi == pytest.approx(3.14159, rel=1e-4)
    
    def test_getattr_missing_raises(self):
        """__getattr__ should raise for missing attributes."""
        import math
        module = WrappedPythonModule("math", math)
        
        with pytest.raises(AttributeError):
            _ = module.nonexistent_function


class TestPythonRuntime:
    """Test Python runtime management."""
    
    def test_runtime_exists(self):
        """PythonRuntime should be instantiable."""
        runtime = DefaultPythonRuntime()
        assert runtime is not None
    
    def test_import_builtin_module(self):
        """import_module should load built-in modules."""
        runtime = DefaultPythonRuntime()
        module = runtime.import_module("math")
        
        assert module is not None
        assert module.name == "math"
    
    def test_import_module_function_call(self):
        """Imported module functions should be callable."""
        runtime = DefaultPythonRuntime()
        math = runtime.import_module("math")
        
        result = math.sqrt.call(25)
        assert result == 5.0
    
    def test_import_module_constant_access(self):
        """Imported module constants should be accessible."""
        runtime = DefaultPythonRuntime()
        math = runtime.import_module("math")
        
        assert math.pi == pytest.approx(3.14159, rel=1e-4)
    
    def test_import_nonexistent_module_raises(self):
        """import_module should raise for nonexistent modules."""
        runtime = DefaultPythonRuntime()
        
        with pytest.raises(ImportError):
            runtime.import_module("nonexistent_module_xyz123")
    
    def test_import_nested_module(self):
        """import_module should handle nested modules."""
        runtime = DefaultPythonRuntime()
        module = runtime.import_module("os.path")
        
        assert module is not None
        # os.path.join should be accessible
        join = module.join
        assert hasattr(join, 'call')
    
    def test_import_json_module(self):
        """json module should be importable."""
        runtime = DefaultPythonRuntime()
        json = runtime.import_module("json")
        
        # Test dumps
        result = json.dumps.call({"a": 1, "b": 2})
        assert '"a"' in result
        assert '"b"' in result
    
    def test_eval_expression(self):
        """eval_expression should evaluate Python expressions."""
        runtime = DefaultPythonRuntime()
        
        result = runtime.eval_expression("2 + 3")
        assert result == 5
        
        result = runtime.eval_expression("'hello' + ' ' + 'world'")
        assert result == "hello world"
    
    def test_eval_expression_with_imports(self):
        """eval_expression should access imported modules."""
        runtime = DefaultPythonRuntime()
        runtime.import_module("math")
        
        result = runtime.eval_expression("math.sqrt(16)")
        assert result == 4.0
    
    def test_exec_statement(self):
        """exec_statement should execute Python statements."""
        runtime = DefaultPythonRuntime()
        
        runtime.exec_statement("x = 42")
        result = runtime.eval_expression("x")
        assert result == 42
    
    def test_get_converter(self):
        """get_converter should return a TypeConverter."""
        runtime = DefaultPythonRuntime()
        converter = runtime.get_converter()
        
        assert converter is not None
        assert hasattr(converter, 'helen_to_python')
        assert hasattr(converter, 'python_to_helen')
    
    def test_module_caching(self):
        """Importing the same module twice should return cached version."""
        runtime = DefaultPythonRuntime()
        
        math1 = runtime.import_module("math")
        math2 = runtime.import_module("math")
        
        # Should be the same wrapper or at least reference the same module
        assert math1.get_module() is math2.get_module()


class TestIntegration:
    """Integration tests for Python FFI."""
    
    def test_math_operations(self):
        """Test various math operations."""
        runtime = DefaultPythonRuntime()
        math = runtime.import_module("math")
        
        assert math.sqrt.call(16) == 4.0
        assert math.pow.call(2, 10) == 1024.0
        assert math.floor.call(3.7) == 3
        assert math.ceil.call(3.2) == 4
    
    def test_json_roundtrip(self):
        """Test JSON serialization/deserialization."""
        runtime = DefaultPythonRuntime()
        json = runtime.import_module("json")
        
        data = {"name": "Alice", "age": 30, "active": True}
        json_str = json.dumps.call(data)
        parsed = json.loads.call(json_str)
        
        assert parsed == data
    
    def test_list_operations(self):
        """Test Python list operations."""
        runtime = DefaultPythonRuntime()
        
        # Create a list and use Python's sorted
        runtime.exec_statement("data = [3, 1, 4, 1, 5, 9, 2, 6]")
        result = runtime.eval_expression("sorted(data)")
        
        assert result == [1, 1, 2, 3, 4, 5, 6, 9]
    
    def test_string_operations(self):
        """Test Python string operations."""
        runtime = DefaultPythonRuntime()
        
        result = runtime.eval_expression("'hello world'.upper()")
        assert result == "HELLO WORLD"
        
        result = runtime.eval_expression("'hello world'.split()")
        assert result == ["hello", "world"]
