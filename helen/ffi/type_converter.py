"""Default implementation of TypeConverter for Python FFI.

Handles automatic type conversion between Helen and Python types.
"""

from typing import Any

from helen.runtime.media import MediaPart


class DefaultTypeConverter:
    """Default type converter implementation.

    Converts between Helen types (int, float, str, bool, list, dict, null)
    and Python types. Complex objects are wrapped as PythonObject.
    """

    # Types that should be wrapped (not converted)
    COMPLEX_TYPES = (
        type,  # classes
        object,  # custom objects
    )

    def helen_to_python(self, value: Any) -> Any:
        """Convert a Helen value to Python.

        Args:
            value: Helen value (int, float, str, bool, list, dict, null)

        Returns:
            Python-compatible value
        """
        match value:
            case None:
                return None
            case int() | float() | str() | bool():
                return value
            case MediaPart():
                # MediaPart passes through natively
                return value
            case list():
                return [self.helen_to_python(item) for item in value]
            case dict():
                return {k: self.helen_to_python(v) for k, v in value.items()}
            case _:
                # Wrapped objects unwrap
                if hasattr(value, 'unwrap'):
                    return value.unwrap()
                # Everything else passes through
                return value

    def python_to_helen(self, value: Any) -> Any:
        """Convert a Python value to Helen.

        Args:
            value: Python value

        Returns:
            Helen-compatible value (wraps complex objects as PythonObject)
        """
        match value:
            case None:
                return None
            case int() | float() | str() | bool():
                return value
            case MediaPart():
                # MediaPart passes through natively
                return value
            case tuple():
                return [self.python_to_helen(item) for item in value]
            case list():
                return [self.python_to_helen(item) for item in value]
            case dict():
                return {k: self.python_to_helen(v) for k, v in value.items()}
            case _:
                # Complex objects are wrapped
                # Import here to avoid circular dependency
                from helen.ffi.python_object import WrappedPythonObject
                return WrappedPythonObject(value)
