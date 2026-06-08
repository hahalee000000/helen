"""Runtime exceptions for the Hellen interpreter.

Defines the base HellenRuntimeError and specific sentinel objects
used for control flow (break, continue, return).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hellen.core.source import SourceSpan


@dataclass
class HellenRuntimeError(Exception):
    """Base class for Hellen runtime errors.

    Attributes:
        message: Human-readable error description.
        span: Source location where the error occurred.
    """

    message: str
    span: SourceSpan | None = None

    def __str__(self) -> str:
        loc = f" at {self.span}" if self.span else ""
        return f"RuntimeError:{loc} {self.message}"


@dataclass
class ConstAssignmentError(HellenRuntimeError):
    """Raised when code attempts to reassign a const variable."""

    def __init__(self, name: str, span: SourceSpan | None = None) -> None:
        super().__init__(f"cannot assign to const variable '{name}'", span)
        self.name = name


@dataclass
class BreakSentinel:
    """Signal object returned from body execution to break out of a loop."""

    span: SourceSpan | None = None

    def __repr__(self) -> str:
        return "BreakSentinel"


@dataclass
class ContinueSentinel:
    """Signal object returned from body execution to continue a loop."""

    span: SourceSpan | None = None

    def __repr__(self) -> str:
        return "ContinueSentinel"


@dataclass
class ReturnSentinel:
    """Signal object returned from function body to return a value.

    Attributes:
        value: The value being returned from the function.
    """

    value: Any = None

    def __repr__(self) -> str:
        return f"ReturnSentinel({self.value!r})"


# ---------------------------------------------------------------------------
# Predefined exception hierarchy (HLD 3.6.4)
#
# AnyError (root, catch-all internal use)
# ├── LLMError
# │   ├── TimeoutError        (LLM call timeout)
# │   └── ModelError          (model unavailable, quota exhausted, etc.)
# ├── ToolError               (tool call failure)
# └── RuntimeError            (interpreter runtime errors)
# ---------------------------------------------------------------------------


@dataclass
class AnyError(HellenRuntimeError):
    """Root exception for the Hellen type hierarchy.

    Used internally by catch-all clauses. Not intended for direct use.
    """

    def __init__(self, message: str = "any error", span: SourceSpan | None = None) -> None:
        super().__init__(message, span)


@dataclass
class LLMError(HellenRuntimeError):
    """Base class for LLM-related runtime errors."""

    def __init__(self, message: str = "LLM error", span: SourceSpan | None = None) -> None:
        super().__init__(message, span)


@dataclass
class TimeoutError(LLMError):
    """LLM call timed out."""

    def __init__(self, message: str = "LLM call timed out", span: SourceSpan | None = None) -> None:
        super().__init__(message, span)


@dataclass
class ModelError(LLMError):
    """Model unavailable or quota exhausted."""

    def __init__(self, message: str = "model error", span: SourceSpan | None = None) -> None:
        super().__init__(message, span)


@dataclass
class ToolError(HellenRuntimeError):
    """Tool call failed."""

    def __init__(self, message: str = "tool error", span: SourceSpan | None = None) -> None:
        super().__init__(message, span)


@dataclass
class RuntimeError(HellenRuntimeError):
    """Interpreter runtime error (division by zero, type errors, etc.)."""

    def __init__(self, message: str = "runtime error", span: SourceSpan | None = None) -> None:
        super().__init__(message, span)


# Mapping from Hellen exception type names to classes (HLD 3.6.4)
_PREDEFINED_EXCEPTIONS: dict[str, type[HellenRuntimeError]] = {
    "AnyError": AnyError,
    "LLMError": LLMError,
    "TimeoutError": TimeoutError,
    "ModelError": ModelError,
    "ToolError": ToolError,
    "RuntimeError": RuntimeError,
}


def resolve_exception(type_name: str) -> type[HellenRuntimeError] | None:
    """Resolve a Hellen exception type name to its Python class.

    Supports inheritance matching: if the exact name is not found,
    returns the closest parent class.

    Args:
        type_name: The Hellen exception type name (e.g., 'TimeoutError').

    Returns:
        The corresponding Python exception class, or None if not found.
    """
    return _PREDEFINED_EXCEPTIONS.get(type_name)


def error_matches(exc: Exception, type_name: str) -> bool:
    """Check if a raised exception matches a catch type name.

    Supports inheritance: catching LLMError also catches TimeoutError
    and ModelError.

    Args:
        exc: The raised exception.
        type_name: The Hellen exception type name from the catch clause.

    Returns:
        True if the exception matches the catch type.
    """
    exc_class = _PREDEFINED_EXCEPTIONS.get(type_name)
    if exc_class is None:
        return False
    return isinstance(exc, exc_class)
