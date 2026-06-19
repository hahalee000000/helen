"""Python FFI contracts for Helen language.

Defines interface contracts for calling Python libraries from Helen.
Implementation follows TDD after tests are written.
"""

from typing import Protocol, runtime_checkable, Any


@runtime_checkable
class PythonObject(Protocol):
    """Contract for a Python object accessible from Helen.

    Wraps a Python object and provides Helen-compatible access.
    """

    def get_attribute(self, name: str) -> Any:
        """Get an attribute from the Python object.

        Args:
            name: Attribute name

        Returns:
            The attribute value (wrapped if it's a complex object)
        """
        ...

    def call(self, *args: Any, **kwargs: Any) -> Any:
        """Call the Python object as a function.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            The return value (wrapped if it's a complex object)
        """
        ...

    def __getitem__(self, key: Any) -> Any:
        """Get item by key (for dict/list access).

        Args:
            key: The key or index

        Returns:
            The value (wrapped if it's a complex object)
        """
        ...

    def __str__(self) -> str:
        """String representation."""
        ...

    def unwrap(self) -> Any:
        """Get the underlying Python object.

        Returns:
            The raw Python object
        """
        ...


@runtime_checkable
class PythonModule(Protocol):
    """Contract for a Python module loaded from Helen.

    Represents an imported Python module with attribute access.
    """

    name: str
    """Module name (e.g., 'numpy', 'requests')"""

    def __getattr__(self, name: str) -> Any:
        """Get a module attribute (function, class, constant).

        Args:
            name: Attribute name

        Returns:
            The attribute (wrapped as PythonObject if needed)
        """
        ...

    def get_module(self) -> Any:
        """Get the underlying Python module object.

        Returns:
            The raw Python module
        """
        ...


@runtime_checkable
class TypeConverter(Protocol):
    """Contract for converting between Helen and Python types.

    Handles automatic type conversion in both directions.
    """

    def helen_to_python(self, value: Any) -> Any:
        """Convert a Helen value to Python.

        Args:
            value: Helen value (int, float, str, bool, list, dict, null)

        Returns:
            Python-compatible value
        """
        ...

    def python_to_helen(self, value: Any) -> Any:
        """Convert a Python value to Helen.

        Args:
            value: Python value

        Returns:
            Helen-compatible value (wraps complex objects as PythonObject)
        """
        ...


@runtime_checkable
class PythonRuntime(Protocol):
    """Contract for Python runtime management.

    Manages Python module loading and execution context.
    """

    def import_module(self, module_name: str) -> PythonModule:
        """Import a Python module.

        Args:
            module_name: Module name (e.g., 'numpy', 'os.path')

        Returns:
            PythonModule wrapper

        Raises:
            ImportError: If module cannot be imported
        """
        ...

    def eval_expression(self, expression: str) -> Any:
        """Evaluate a Python expression.

        Args:
            expression: Python expression string

        Returns:
            Result (wrapped if needed)
        """
        ...

    def exec_statement(self, statement: str) -> None:
        """Execute a Python statement.

        Args:
            statement: Python statement string
        """
        ...

    def get_converter(self) -> TypeConverter:
        """Get the type converter for this runtime.

        Returns:
            TypeConverter instance
        """
        ...
