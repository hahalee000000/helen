"""Wrapped Python module for Helen FFI.

Provides Helen-compatible access to Python modules.
"""

from typing import Any


class WrappedPythonModule:
    """Wrapper for Python modules accessible from Helen.

    Represents an imported Python module with attribute access
    that works with Helen's type system.
    """

    def __init__(self, name: str, module: Any):
        """Initialize wrapper with a Python module.

        Args:
            name: Module name (e.g., 'math', 'os.path')
            module: The Python module object
        """
        self.name = name
        self._module = module
        # Import here to avoid circular dependency
        from helen.ffi.type_converter import DefaultTypeConverter
        self._converter = DefaultTypeConverter()

    def __getattr__(self, name: str) -> Any:
        """Get a module attribute (function, class, constant).

        Args:
            name: Attribute name

        Returns:
            The attribute (wrapped as PythonObject if needed)

        Raises:
            AttributeError: If attribute doesn't exist
        """
        # Avoid infinite recursion for internal attributes
        if name.startswith('_'):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        value = getattr(self._module, name)
        return self._converter.python_to_helen(value)

    def get_module(self) -> Any:
        """Get the underlying Python module object.

        Returns:
            The raw Python module
        """
        return self._module

    def __repr__(self) -> str:
        """Developer representation."""
        return f"WrappedPythonModule({self.name!r})"

    def __deepcopy__(self, memo: dict) -> "WrappedPythonModule":
        """Deep copy returns self (modules are process-level singletons).

        Python modules cannot be pickled/deep-copied and are process-wide
        singletons anyway. When spawn snapshots the environment, return the
        same reference rather than attempting to copy the module.

        v1.25 fix for issue #22: Previously spawn would crash with
        'cannot pickle module object' when any Python FFI module was imported.
        """
        memo[id(self)] = self
        return self
