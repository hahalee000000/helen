"""Wrapped Python object for Helen FFI.

Provides Helen-compatible access to Python objects.
"""

from typing import Any


class WrappedPythonObject:
    """Wrapper for Python objects accessible from Helen.

    Wraps a Python object and provides methods for attribute access,
    function calls, and item access that work with Helen's type system.
    """

    def __init__(self, obj: Any):
        """Initialize wrapper with a Python object.

        Args:
            obj: The Python object to wrap
        """
        self._obj = obj
        # Import here to avoid circular dependency
        from helen.ffi.type_converter import DefaultTypeConverter
        self._converter = DefaultTypeConverter()

    def get_attribute(self, name: str) -> Any:
        """Get an attribute from the Python object.

        Args:
            name: Attribute name

        Returns:
            The attribute value (wrapped if it's a complex object)

        Raises:
            AttributeError: If attribute doesn't exist
        """
        value = getattr(self._obj, name)
        return self._converter.python_to_helen(value)

    def call(self, *args: Any, **kwargs: Any) -> Any:
        """Call the Python object as a function.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            The return value (wrapped if it's a complex object)

        Raises:
            TypeError: If object is not callable
        """
        if not callable(self._obj):
            raise TypeError(f"'{type(self._obj).__name__}' object is not callable")

        # Convert Helen arguments to Python
        py_args = [self._converter.helen_to_python(arg) for arg in args]
        py_kwargs = {k: self._converter.helen_to_python(v) for k, v in kwargs.items()}

        # Call the object
        result = self._obj(*py_args, **py_kwargs)

        # Convert result back to Helen
        return self._converter.python_to_helen(result)

    def __getitem__(self, key: Any) -> Any:
        """Get item by key (for dict/list access).

        Args:
            key: The key or index

        Returns:
            The value (wrapped if it's a complex object)

        Raises:
            KeyError: If key doesn't exist (for dicts)
            IndexError: If index is out of range (for lists)
        """
        py_key = self._converter.helen_to_python(key)
        value = self._obj[py_key]
        return self._converter.python_to_helen(value)

    def __str__(self) -> str:
        """String representation."""
        return str(self._obj)

    def __repr__(self) -> str:
        """Developer representation."""
        return f"WrappedPythonObject({self._obj!r})"

    def unwrap(self) -> Any:
        """Get the underlying Python object.

        Returns:
            The raw Python object
        """
        return self._obj

    def __getattr__(self, name: str) -> Any:
        """Allow direct attribute access (for convenience).

        This allows wrapper.attr instead of wrapper.get_attribute('attr').
        """
        # Avoid infinite recursion for internal attributes
        if name.startswith('_'):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        return self.get_attribute(name)
