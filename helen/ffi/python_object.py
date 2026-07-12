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

        Supports two patterns:
        1. Direct call: when the wrapped object is callable (function/class),
           ``wrapped.call(arg1, arg2)`` invokes it directly.
        2. Method-by-name call: when the wrapped object is NOT callable
           (instance) and the first argument is a string,
           ``wrapped.call("method_name", arg1)`` calls the named method
           with the remaining arguments. This is a convenience that
           avoids the more verbose ``wrapped.get_attribute("method")()``.

        Args:
            *args: Positional arguments (or method name + args for pattern 2)
            **kwargs: Keyword arguments

        Returns:
            The return value (wrapped if it's a complex object)

        Raises:
            TypeError: If object is not callable and no method match found
        """
        if callable(self._obj):
            # Pattern 1: direct call (wrapped function/class)
            py_args = [self._converter.helen_to_python(arg) for arg in args]
            py_kwargs = {k: self._converter.helen_to_python(v) for k, v in kwargs.items()}
            result = self._obj(*py_args, **py_kwargs)
            return self._converter.python_to_helen(result)

        # Pattern 2: method-by-name dispatch for non-callable instances
        # ``instance.call("method", arg1, arg2)`` → ``instance.method(arg1, arg2)``
        if args and isinstance(args[0], str):
            method_name = args[0]
            method = getattr(self._obj, method_name, None)
            if method is not None and callable(method):
                remaining_args = args[1:]
                py_args = [self._converter.helen_to_python(arg) for arg in remaining_args]
                py_kwargs = {k: self._converter.helen_to_python(v) for k, v in kwargs.items()}
                result = method(*py_args, **py_kwargs)
                return self._converter.python_to_helen(result)

        raise TypeError(f"'{type(self._obj).__name__}' object is not callable")

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
