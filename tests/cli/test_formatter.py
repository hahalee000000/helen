"""Tests for helen CLI — error formatter."""

from helen.core.errors import ErrorCode, HelenError, HelenWarning
from helen.core.source import SourceSpan
from helen.cli.formatter import format_error, format_warning


class TestErrorFormatter:
    """Test error formatting per HLD 3.11.2."""

    def test_error_with_span(self):
        """Error with SourceSpan shows location and source."""
        span = SourceSpan("test.helen", 5, 10, 5, 15)
        error = HelenError(
            code=ErrorCode.PARSER_ERROR,
            message="unexpected token",
            span=span,
        )
        source_lines = [
            "agent Test {",
            "  main {",
            "    let x = 1;",
            "    let y = ;",  # line 4
            "    let z = ;",  # line 5
        ]

        result = format_error(error, source_lines)

        assert "Error:" in result
        assert "E0301" in result
        assert "unexpected token" in result
        assert "test.helen:5:10" in result
        assert "let z = ;" in result
        assert "^" in result

    def test_error_without_span(self):
        """Error without SourceSpan shows generic location."""
        error = HelenError(
            code=ErrorCode.SCANNER_ERROR,
            message="illegal character",
            span=None,
        )

        result = format_error(error)

        assert "Error:" in result
        assert "E0300" in result
        assert "illegal character" in result
        # No location line since span is None

    def test_error_includes_detail_line(self):
        """Error includes detail (= ...) line."""
        span = SourceSpan("test.helen", 1, 1, 1, 5)
        error = HelenError(
            code=ErrorCode.UNEXPECTED_TOKEN,
            message="expected identifier",
            span=span,
        )

        result = format_error(error)

        assert "= expected identifier" in result


class TestWarningFormatter:
    """Test warning formatting."""

    def test_warning_with_span(self):
        """Warning with SourceSpan shows location."""
        span = SourceSpan("test.helen", 3, 5, 3, 10)
        warning = HelenWarning(
            code=ErrorCode.DEPRECATED_SYNTAX,
            message="deprecated syntax",
            span=span,
        )
        source_lines = [
            "agent Test {",
            "  main {",
            "    let old = 1;",
        ]

        result = format_warning(warning, source_lines)

        assert "Warning:" in result
        assert "W0308" in result
        assert "deprecated syntax" in result
        assert "test.helen:3:5" in result
        assert "let old = 1;" in result


class TestPositionIndicator:
    """Test caret position accuracy."""

    def test_caret_underlines_error_position(self):
        """Caret line should underline the error location."""
        span = SourceSpan("test.helen", 1, 5, 1, 10)
        error = HelenError(
            code=ErrorCode.PARSER_ERROR,
            message="bad syntax",
            span=span,
        )
        source_lines = ["let abc = def;"]

        result = format_error(error, source_lines)

        # Should have ^ characters
        assert "^" in result
