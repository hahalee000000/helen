"""Default implementation of PythonRuntime for Helen FFI.

Manages Python module loading and execution context.
"""

import importlib
from typing import Any

from helen.ffi.contracts import PythonRuntime, PythonModule, TypeConverter
from helen.ffi.python_module import WrappedPythonModule
from helen.ffi.type_converter import DefaultTypeConverter


class DefaultPythonRuntime:
    """Default Python runtime implementation.
    
    Manages Python module imports and provides an execution context
    for evaluating Python expressions and statements.
    """
    
    def __init__(self):
        """Initialize the Python runtime."""
        self._modules: dict[str, WrappedPythonModule] = {}
        self._converter = DefaultTypeConverter()
        # Execution context for eval/exec
        self._context: dict[str, Any] = {}
    
    def import_module(self, module_name: str) -> PythonModule:
        """Import a Python module.
        
        Args:
            module_name: Module name (e.g., 'numpy', 'os.path')
            
        Returns:
            PythonModule wrapper
            
        Raises:
            ImportError: If module cannot be imported
        """
        # Check cache
        if module_name in self._modules:
            return self._modules[module_name]
        
        # Import the module
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            raise ImportError(f"Cannot import module '{module_name}': {e}")
        
        # Wrap and cache
        wrapped = WrappedPythonModule(module_name, module)
        self._modules[module_name] = wrapped
        
        # Add to execution context
        # For nested modules like 'os.path', use the last part as the variable name
        var_name = module_name.split('.')[-1]
        self._context[var_name] = module
        
        return wrapped
    
    def eval_expression(self, expression: str) -> Any:
        """Evaluate a Python expression.
        
        Args:
            expression: Python expression string
            
        Returns:
            Result (wrapped if needed)
        """
        result = eval(expression, self._context)
        return self._converter.python_to_helen(result)
    
    def exec_statement(self, statement: str) -> None:
        """Execute a Python statement.
        
        Args:
            statement: Python statement string
        """
        exec(statement, self._context)
    
    def get_converter(self) -> TypeConverter:
        """Get the type converter for this runtime.
        
        Returns:
            TypeConverter instance
        """
        return self._converter
