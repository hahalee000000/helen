"""Helen core module — token types, source management, and error reporting."""

from helen.core.errors import ErrorCode, ErrorReporter, HelenError, HelenWarning
from helen.core.source import SourceFile, SourceSpan
from helen.core.tokens import Token, TokenType, keywords

__all__ = [
    "ErrorCode",
    "ErrorReporter",
    "HelenError",
    "HelenWarning",
    "SourceFile",
    "SourceSpan",
    "Token",
    "TokenType",
    "keywords",
    "is_helen_data_file",
]

# Helen data file extensions recognized by the import resolver
_HELEN_DATA_EXTS = ('.helen', '.json', '.md', '.txt', '.yaml', '.yml')


def is_helen_data_file(path: str) -> bool:
    """Check if a module path refers to a Helen data file (not a Python module)."""
    return any(path.endswith(ext) for ext in _HELEN_DATA_EXTS)
