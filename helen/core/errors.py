"""Error types, warnings, and an error reporter for the Helen language.

Defines the ``ErrorCode`` enumeration, ``HelenError`` / ``HelenWarning``
data classes, and a stateful ``ErrorReporter`` for collecting diagnostics
during compilation phases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from helen.core.source import SourceSpan


class ErrorCode(Enum):
    """Numeric codes for Helen compilation diagnostics.

    Each code is grouped by category:
    - 300-309: lexical and syntax errors
    - 310-320: parser and semantic errors
    """

    # 300-309: lexical/syntax
    SCANNER_ERROR = 300
    PARSER_ERROR = 301
    UNEXPECTED_TOKEN = 302
    MISSING_TOKEN = 303
    INVALID_LITERAL = 304
    INVALID_ESCAPE = 305
    UNTERMINATED_STRING = 306
    INVALID_IDENTIFIER = 307
    DEPRECATED_SYNTAX = 308
    RESERVED_KEYWORD = 309

    # 310-320: parser/semantic (Phase 0/1)
    TYPE_MISMATCH = 310
    UNDEFINED_VARIABLE = 311
    UNDEFINED_FUNCTION = 312
    DUPLICATE_DECLARATION = 313
    MISSING_RETURN = 314
    INVALID_BREAK = 315
    INVALID_CONTINUE = 316
    MISSING_DEFAULT_CASE = 317
    ASYNC_ON_NON_CALL = 318
    INVALID_AGENT_PARAM = 319
    UNTERMINATED_BLOCK = 320

    # 330-350: semantic analysis (Phase 2)
    SEMANTIC_ERROR = 330
    SEMANTIC_TYPE_ERROR = 331
    UNDECLARED_VARIABLE = 332
    DUPLICATE_SYMBOL = 333
    AGENT_RUNTIME_ERROR = 334
    DUPLICATE_AGENT_NAME = 335
    DUPLICATE_PARAM = 336
    MISSING_PROMPT = 337
    BREAK_OUTSIDE_LOOP = 338
    CONTINUE_OUTSIDE_LOOP = 339
    RETURN_OUTSIDE_FUNCTION = 340
    IMPORT_NOT_FOUND = 341
    INVALID_CATCH_TYPE = 342
    CATCH_ALL_NOT_LAST = 343
    LLM_IF_NO_DEFAULT = 344
    MATCH_NO_DEFAULT = 345
    CONST_ASSIGNMENT = 346
    AGENT_PARAM_MISMATCH = 347
    INVALID_AGENT_NAME = 348
    MISSING_DEFAULT_BRANCH = 349
    SCOPE_VIOLATION = 350
    RUNTIME_ERROR = 351
    IMPORT_ERROR = 352
    INVALID_TOOLS_DECLARATION = 353
    BUILTIN_SHADOWED = 354


@dataclass
class HelenError(Exception):
    """A recoverable or fatal error encountered during Helen compilation.

    Attributes:
        code: The ``ErrorCode`` categorising this error.
        message: A human-readable description of the problem.
        span: Optional source location where the error occurred.
    """

    code: ErrorCode
    message: str
    span: "SourceSpan | None" = None

    def __str__(self) -> str:
        """Return a formatted error string with code, location, and message.

        Returns:
            A string like ``E0302 at <unknown>: unexpected token 'foo'``.
        """
        loc = f"{self.span}" if self.span else "<unknown>"
        return f"E{self.code.value:04d} at {loc}: {self.message}"


@dataclass
class HelenWarning:
    """A non-fatal warning encountered during Helen compilation.

    Attributes:
        code: The ``ErrorCode`` categorising this warning.
        message: A human-readable description.
        span: Optional source location where the warning applies.
    """

    code: ErrorCode
    message: str
    span: "SourceSpan | None" = None

    def __str__(self) -> str:
        """Return a formatted warning string with code, location, and message.

        Returns:
            A string like ``W0308 at main.hl:5:1-12: deprecated syntax``.
        """
        loc = f"{self.span}" if self.span else "<unknown>"
        return f"W{self.code.value:04d} at {loc}: {self.message}"


@dataclass
class ErrorReporter:
    """A collector for errors and warnings across compilation phases.

    Use ``error()`` and ``warning()`` to add diagnostics, then inspect
    ``errors``, ``warnings``, and ``has_errors`` to decide whether to
    proceed.
    """

    _errors: list[HelenError] = field(default_factory=list)
    _warnings: list[HelenWarning] = field(default_factory=list)

    def error(
        self,
        code: ErrorCode,
        message: str,
        span: "SourceSpan | None" = None,
    ) -> None:
        """Record a new error.

        Args:
            code: The ``ErrorCode`` for this error.
            message: Human-readable error description.
            span: Optional source location.
        """
        self._errors.append(HelenError(code, message, span))

    def warning(
        self,
        code: ErrorCode,
        message: str,
        span: "SourceSpan | None" = None,
    ) -> None:
        """Record a new warning.

        Args:
            code: The ``ErrorCode`` for this warning.
            message: Human-readable warning description.
            span: Optional source location.
        """
        self._warnings.append(HelenWarning(code, message, span))

    @property
    def errors(self) -> list[HelenError]:
        """Return a copy of the collected errors.

        Returns:
            A new list containing all ``HelenError`` instances recorded
            so far.
        """
        return list(self._errors)

    @property
    def warnings(self) -> list[HelenWarning]:
        """Return a copy of the collected warnings.

        Returns:
            A new list containing all ``HelenWarning`` instances recorded
            so far.
        """
        return list(self._warnings)

    @property
    def has_errors(self) -> bool:
        """Check whether any errors have been recorded.

        Returns:
            ``True`` if at least one error has been reported, ``False``
            otherwise.
        """
        return len(self._errors) > 0

    def reset(self) -> None:
        """Clear all recorded errors and warnings.

        After calling this method, ``errors``, ``warnings``, and
        ``has_errors`` will reflect an empty state.
        """
        self._errors.clear()
        self._warnings.clear()


# Compatibility alias
Error = HelenError
