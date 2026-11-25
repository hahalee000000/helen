"""Default implementation of PythonRuntime for Helen FFI.

Manages Python module loading and execution context.
"""

from __future__ import annotations

import importlib
import os
import sys
from typing import Any

from helen.ffi.contracts import PythonModule, TypeConverter
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
        # v1.46.35: Ensure helen/agent directory is in sys.path for ui module imports.
        # This fixes the issue where running Helen from a non-helen project directory
        # (e.g., helen-rust) causes ui.stream_emitter import to fail.
        self._ensure_helen_agent_path()

    def _ensure_helen_agent_path(self):
        """Ensure helen/agent directory is in sys.path.

        v1.46.35: When Helen runs from a non-helen project directory (e.g., helen-rust),
        sys.path may not include the helen/agent directory where ui modules live.
        This method finds the helen/agent directory and adds it to sys.path if needed.
        """
        # Method 1: Try to find via chat_tui_web module (set by WebUI backend)
        try:
            import chat_tui_web
            agent_dir = chat_tui_web.HELEN_AGENT_DIR
            if agent_dir and agent_dir not in sys.path:
                sys.path.insert(0, agent_dir)
                return
        except ImportError:
            pass

        # Method 2: Infer from this file's location
        # python_runtime.py is at <helen_root>/helen/ffi/python_runtime.py
        # So helen/agent is at ../agent relative to ffi/
        try:
            this_dir = os.path.dirname(os.path.abspath(__file__))  # <helen_root>/helen/ffi
            helen_pkg = os.path.dirname(this_dir)  # <helen_root>/helen
            agent_dir = os.path.join(helen_pkg, 'agent')  # <helen_root>/helen/agent
            if os.path.isdir(agent_dir) and agent_dir not in sys.path:
                sys.path.insert(0, agent_dir)
                return
        except Exception:
            pass

        # Method 3: Try via helen package (if __file__ exists)
        try:
            import helen
            helen_file = getattr(helen, '__file__', None)
            if helen_file:
                # helen.__file__ = <helen_pkg>/helen/__init__.py
                helen_root = os.path.dirname(os.path.dirname(os.path.abspath(helen_file)))
                agent_dir = os.path.join(helen_root, 'helen', 'agent')
                if os.path.isdir(agent_dir) and agent_dir not in sys.path:
                    sys.path.insert(0, agent_dir)
        except ImportError:
            pass

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
