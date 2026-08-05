"""Helen stdlib modules.

Provides modular access to stdlib functions via explicit imports.
"""

from helen.stdlib import stdlib


def _create_module(category, filter_names=None):
    """Create a module class for a stdlib category."""

    class Module:
        pass

    # Load functions
    for func in stdlib.list_all():
        if func.category == category:
            if filter_names is None or func.name in filter_names:
                setattr(Module, func.name, staticmethod(func.fn))

    # Create __exports__ dict
    exports = {}
    for name in dir(Module):
        if not name.startswith('_'):
            exports[name] = getattr(Module, name)
    Module.__exports__ = exports

    return Module


# Create modules
StrModule = _create_module("string")
ListModule = _create_module("collection", [
    'map', 'filter', 'reduce', 'find_if', 'every', 'some',
    'sort', 'unique', 'flatten', 'chunk', 'zip'
])
DictModule = _create_module("collection", [
    'keys', 'values', 'entries', 'merge', 'pick', 'omit',
    'remove_key', 'get', 'set_key', 'has_key'
])
MathModule = _create_module("math")
TimeModule = _create_module("time")
FileModule = _create_module("file")
SystemModule = _create_module("system")
IOModule = _create_module("io")


__all__ = [
    "StrModule",
    "ListModule",
    "DictModule",
    "MathModule",
    "TimeModule",
    "FileModule",
    "SystemModule",
    "IOModule",
]
