"""Runtime exceptions for the Helen interpreter.

Defines the base HelenRuntimeError and specific sentinel objects
used for control flow (break, continue, return).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from helen.core.source import SourceSpan


@dataclass
class HelenRuntimeError(Exception):
    """Base class for Helen runtime errors.

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
class ConstAssignmentError(HelenRuntimeError):
    """Raised when code attempts to reassign a const variable."""

    def __init__(self, name: str, span: SourceSpan | None = None) -> None:
        super().__init__(f"cannot assign to const variable '{name}'", span)
        self.name = name


@dataclass
class ScopeViolationError(HelenRuntimeError):
    """Raised when code violates scope isolation rules.

    v1.12: Agent isolation improvement. This error is raised when:
    - An agent tries to modify a read-only parameter
    - An agent tries to access module-level variables
    - Any other scope boundary violation
    """

    def __init__(self, message: str, span: SourceSpan | None = None) -> None:
        super().__init__(message, span)


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
# │   ├── ModelError          (model unavailable, quota exhausted, etc.)
# │   └── AgentError          (agent call failure — wraps underlying cause)
# ├── ToolError               (tool call failure)
# └── RuntimeError            (interpreter runtime errors)
# ---------------------------------------------------------------------------


@dataclass
class AnyError(HelenRuntimeError):
    """Root exception for the Helen type hierarchy.

    Used internally by catch-all clauses. Not intended for direct use.
    """

    def __init__(self, message: str = "any error", span: SourceSpan | None = None) -> None:
        super().__init__(message, span)


@dataclass
class LLMError(AnyError):
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
class AgentError(LLMError):
    """Agent call failed — wraps underlying cause with agent context.

    Inherits from LLMError so that ``catch LLMError`` also catches agent
    failures (most agent failures are LLM failures under the hood).

    Attributes:
        agent_name: Name of the agent that failed.
        agent_args: Arguments passed to the agent call.
        cause: The underlying exception that triggered this failure.
    """

    agent_name: str = ""
    agent_args: dict[str, Any] | None = None
    cause: Exception | None = None

    def __init__(
        self,
        agent_name: str = "",
        agent_args: dict[str, Any] | None = None,
        cause: Exception | None = None,
        message: str | None = None,
        span: SourceSpan | None = None,
    ) -> None:
        self.agent_name = agent_name
        self.agent_args = agent_args or {}
        self.cause = cause
        if message is None:
            cause_desc = f": {cause}" if cause is not None else ""
            message = f"Agent '{agent_name}' failed{cause_desc}"
        super().__init__(message, span)

    def __str__(self) -> str:
        loc = f" at {self.span}" if self.span else ""
        return f"AgentError:{loc} {self.message}"


@dataclass
class ToolError(AnyError):
    """Tool call failed."""

    def __init__(self, message: str = "tool error", span: SourceSpan | None = None) -> None:
        super().__init__(message, span)


@dataclass
class RuntimeError(AnyError):
    """Interpreter runtime error (division by zero, type errors, etc.)."""

    def __init__(self, message: str = "runtime error", span: SourceSpan | None = None) -> None:
        super().__init__(message, span)


@dataclass
class AssertionError(AnyError):
    """Assertion failed (P3: AI-native observability).

    Raised when an assert statement's condition evaluates to false.
    Captures structured error context for AI debugging.
    """

    def __init__(self, message: str = "assertion failed", span: SourceSpan | None = None) -> None:
        super().__init__(message, span)


@dataclass
class AggregateError(AnyError):
    """Collects multiple exceptions from await [list] (HLD 3.6.7).

    When await [task1, task2, ...] has multiple failures, this error
    contains all failed task exceptions in the `errors` attribute.
    """

    errors: list[Exception] | None = None

    def __init__(self, message: str = "aggregate error",
                 errors: list[Exception] | None = None,
                 span: SourceSpan | None = None) -> None:
        super().__init__(message, span)
        self.errors = errors or []

    def __str__(self) -> str:
        if self.errors:
            parts = [str(e) for e in self.errors]
            return f"AggregateError({len(self.errors)} task(s) failed): {', '.join(parts)}"
        return f"AggregateError: {self.message}"


# Mapping from Helen exception type names to classes (HLD 3.6.4)
_PREDEFINED_EXCEPTIONS: dict[str, type[HelenRuntimeError]] = {
    "AnyError": AnyError,
    "LLMError": LLMError,
    "TimeoutError": TimeoutError,
    "ModelError": ModelError,
    "AgentError": AgentError,
    "ToolError": ToolError,
    "RuntimeError": RuntimeError,
    "AssertionError": AssertionError,
    "AggregateError": AggregateError,
}


def resolve_exception(type_name: str) -> type[HelenRuntimeError] | None:
    """Resolve a Helen exception type name to its Python class.

    Supports inheritance matching: if the exact name is not found,
    returns the closest parent class.

    Args:
        type_name: The Helen exception type name (e.g., 'TimeoutError').

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
        type_name: The Helen exception type name from the catch clause.

    Returns:
        True if the exception matches the catch type.
    """
    exc_class = _PREDEFINED_EXCEPTIONS.get(type_name)
    if exc_class is None:
        return False
    return isinstance(exc, exc_class)
