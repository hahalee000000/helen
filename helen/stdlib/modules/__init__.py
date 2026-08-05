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
# Existing (v1.34): string / collection subsets / math / time / file / system / io
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

# New modules (v1.38): core / data / network / path / tools / debug / context
# / transcript / media / test / quality / llm / crypto / concurrency
CoreModule = _create_module("core")
DataModule = _create_module("data")
NetworkModule = _create_module("network")
PathModule = _create_module("path")
ToolsModule = _create_module("tools")
DebugModule = _create_module("debug")
ContextModule = _create_module("context")
TranscriptModule = _create_module("transcript")
MediaModule = _create_module("media")
TestModule = _create_module("test")
QualityModule = _create_module("quality")
LLMModule = _create_module("llm")
CryptoModule = _create_module("crypto")
ConcurrencyModule = _create_module("concurrency")


__all__ = [
    # v1.34
    "StrModule",
    "ListModule",
    "DictModule",
    "MathModule",
    "TimeModule",
    "FileModule",
    "SystemModule",
    "IOModule",
    # v1.38
    "CoreModule",
    "DataModule",
    "NetworkModule",
    "PathModule",
    "ToolsModule",
    "DebugModule",
    "ContextModule",
    "TranscriptModule",
    "MediaModule",
    "TestModule",
    "QualityModule",
    "LLMModule",
    "CryptoModule",
    "ConcurrencyModule",
]
