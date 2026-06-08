"""Tests for helen.core.errors module.

Covers:
- ErrorCode enum values
- HelenError / HelenWarning creation and string representation
- ErrorReporter: error/warning/has_errors/reset/errors/warnings
"""

import pytest

from helen.core.errors import (
    ErrorCode,
    ErrorReporter,
    HelenError,
    HelenWarning,
)
from helen.core.source import SourceSpan


class TestErrorCode:
    """Tests for the ErrorCode enumeration."""

    def test_all_codes_exist(self) -> None:
        """All expected error codes should be present."""
        expected = [
            "SCANNER_ERROR",
            "PARSER_ERROR",
            "UNEXPECTED_TOKEN",
            "MISSING_TOKEN",
            "INVALID_LITERAL",
            "INVALID_ESCAPE",
            "UNTERMINATED_STRING",
            "INVALID_IDENTIFIER",
            "DEPRECATED_SYNTAX",
            "RESERVED_KEYWORD",
        ]
        for name in expected:
            assert hasattr(ErrorCode, name), f"Missing: {name}"

    def test_code_values(self) -> None:
        """ErrorCode values should start at 300 and be sequential."""
        assert ErrorCode.SCANNER_ERROR.value == 300
        assert ErrorCode.PARSER_ERROR.value == 301
        assert ErrorCode.UNEXPECTED_TOKEN.value == 302
        assert ErrorCode.MISSING_TOKEN.value == 303
        assert ErrorCode.INVALID_LITERAL.value == 304
        assert ErrorCode.INVALID_ESCAPE.value == 305
        assert ErrorCode.UNTERMINATED_STRING.value == 306
        assert ErrorCode.INVALID_IDENTIFIER.value == 307
        assert ErrorCode.DEPRECATED_SYNTAX.value == 308
        assert ErrorCode.RESERVED_KEYWORD.value == 309

    def test_unique_values(self) -> None:
        """All ErrorCode members should have distinct values."""
        values = [e.value for e in ErrorCode]
        assert len(values) == len(set(values))


class TestHelenError:
    """Tests for HelenError."""

    def test_creation_minimal(self) -> None:
        """HelenError should be creatable with code and message only."""
        err = HelenError(ErrorCode.SCANNER_ERROR, "bad token")
        assert err.code == ErrorCode.SCANNER_ERROR
        assert err.message == "bad token"
        assert err.span is None

    def test_creation_with_span(self) -> None:
        """HelenError should accept an optional span."""
        span = SourceSpan("test.hl", 1, 1, 1, 5)
        err = HelenError(ErrorCode.PARSER_ERROR, "expected ')'", span)
        assert err.span is span

    def test_str_without_span(self) -> None:
        """__str__ should use '<unknown>' when span is absent."""
        err = HelenError(ErrorCode.SCANNER_ERROR, "oops")
        s = str(err)
        assert "E0300" in s
        assert "<unknown>" in s
        assert "oops" in s

    def test_str_with_span(self) -> None:
        """__str__ should include span string when present."""
        span = SourceSpan("main.hl", 3, 5, 3, 10)
        err = HelenError(ErrorCode.UNEXPECTED_TOKEN, "got 'foo'", span)
        s = str(err)
        assert "E0302" in s
        assert "main.hl:3:5-10" in s
        assert "got 'foo'" in s

    def test_is_exception(self) -> None:
        """HelenError should be a subclass of Exception."""
        err = HelenError(ErrorCode.SCANNER_ERROR, "x")
        assert isinstance(err, Exception)


class TestHelenWarning:
    """Tests for HelenWarning."""

    def test_creation(self) -> None:
        """HelenWarning should be creatable with code and message."""
        w = HelenWarning(ErrorCode.DEPRECATED_SYNTAX, "old syntax")
        assert w.code == ErrorCode.DEPRECATED_SYNTAX
        assert w.message == "old syntax"
        assert w.span is None

    def test_str_without_span(self) -> None:
        """__str__ should use '<unknown>' when span is absent."""
        w = HelenWarning(ErrorCode.DEPRECATED_SYNTAX, "use new form")
        s = str(w)
        assert "W0308" in s
        assert "<unknown>" in s
        assert "use new form" in s

    def test_str_with_span(self) -> None:
        """__str__ should include span string when present."""
        span = SourceSpan("old.hl", 10, 1, 10, 20)
        w = HelenWarning(ErrorCode.DEPRECATED_SYNTAX, "deprecated", span)
        s = str(w)
        assert "W0308" in s
        assert "old.hl:10:1-20" in s
        assert "deprecated" in s


class TestErrorReporter:
    """Tests for ErrorReporter."""

    def test_initial_state(self) -> None:
        """New ErrorReporter should have no errors or warnings."""
        r = ErrorReporter()
        assert r.has_errors is False
        assert r.errors == []
        assert r.warnings == []

    def test_error_adds_to_list(self) -> None:
        """error() should append a HelenError to errors."""
        r = ErrorReporter()
        r.error(ErrorCode.SCANNER_ERROR, "bad")
        assert len(r.errors) == 1
        assert r.errors[0].code == ErrorCode.SCANNER_ERROR
        assert r.errors[0].message == "bad"

    def test_warning_adds_to_list(self) -> None:
        """warning() should append a HelenWarning to warnings."""
        r = ErrorReporter()
        r.warning(ErrorCode.DEPRECATED_SYNTAX, "old")
        assert len(r.warnings) == 1
        assert r.warnings[0].code == ErrorCode.DEPRECATED_SYNTAX

    def test_has_errors_true(self) -> None:
        """has_errors should be True after at least one error."""
        r = ErrorReporter()
        assert r.has_errors is False
        r.error(ErrorCode.PARSER_ERROR, "parse fail")
        assert r.has_errors is True

    def test_has_errors_ignores_warnings(self) -> None:
        """has_errors should remain False if only warnings exist."""
        r = ErrorReporter()
        r.warning(ErrorCode.DEPRECATED_SYNTAX, "old")
        assert r.has_errors is False

    def test_reset_clears_all(self) -> None:
        """reset() should clear both errors and warnings."""
        r = ErrorReporter()
        r.error(ErrorCode.SCANNER_ERROR, "a")
        r.warning(ErrorCode.DEPRECATED_SYNTAX, "b")
        r.reset()
        assert r.errors == []
        assert r.warnings == []
        assert r.has_errors is False

    def test_errors_returns_copy(self) -> None:
        """errors property should return a copy, not the internal list."""
        r = ErrorReporter()
        r.error(ErrorCode.SCANNER_ERROR, "a")
        errs = r.errors
        errs.clear()
        assert len(r.errors) == 1

    def test_warnings_returns_copy(self) -> None:
        """warnings property should return a copy, not the internal list."""
        r = ErrorReporter()
        r.warning(ErrorCode.DEPRECATED_SYNTAX, "b")
        warns = r.warnings
        warns.clear()
        assert len(r.warnings) == 1

    def test_multiple_errors(self) -> None:
        """Multiple errors should accumulate correctly."""
        r = ErrorReporter()
        r.error(ErrorCode.SCANNER_ERROR, "first")
        r.error(ErrorCode.PARSER_ERROR, "second")
        r.error(ErrorCode.UNEXPECTED_TOKEN, "third")
        assert len(r.errors) == 3
        assert r.errors[0].message == "first"
        assert r.errors[1].message == "second"
        assert r.errors[2].message == "third"

    def test_error_with_span(self) -> None:
        """error() should accept and store a span."""
        r = ErrorReporter()
        span = SourceSpan("test.hl", 1, 1, 1, 5)
        r.error(ErrorCode.SCANNER_ERROR, "bad", span)
        assert r.errors[0].span is span

    def test_warning_with_span(self) -> None:
        """warning() should accept and store a span."""
        r = ErrorReporter()
        span = SourceSpan("test.hl", 2, 1, 2, 10)
        r.warning(ErrorCode.DEPRECATED_SYNTAX, "old", span)
        assert r.warnings[0].span is span
