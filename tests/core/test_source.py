"""Tests for helen.core.source module.

Covers:
- SourceSpan creation, contains(), __str__, __repr__
- SourceFile creation, line_count, get_line
"""

import pytest

from helen.core.source import SourceFile, SourceSpan


class TestSourceSpan:
    """Tests for the SourceSpan dataclass."""

    def test_creation(self) -> None:
        """SourceSpan should be creatable with all fields."""
        span = SourceSpan("test.hl", 1, 1, 1, 10)
        assert span.file == "test.hl"
        assert span.start_line == 1
        assert span.start_col == 1
        assert span.end_line == 1
        assert span.end_col == 10

    def test_frozen(self) -> None:
        """SourceSpan should be immutable."""
        span = SourceSpan("test.hl", 1, 1, 1, 10)
        with pytest.raises((AttributeError, Exception)):
            span.file = "other.hl"  # type: ignore

    def test_contains_inside(self) -> None:
        """contains() should return True for positions within the span."""
        span = SourceSpan("test.hl", 2, 5, 2, 15)
        assert span.contains(2, 5) is True
        assert span.contains(2, 10) is True
        assert span.contains(2, 14) is True

    def test_contains_before_start(self) -> None:
        """contains() should return False for positions before start."""
        span = SourceSpan("test.hl", 2, 5, 2, 15)
        assert span.contains(2, 4) is False
        assert span.contains(2, 1) is False

    def test_contains_at_end(self) -> None:
        """contains() should return False at end_col (exclusive)."""
        span = SourceSpan("test.hl", 2, 5, 2, 15)
        assert span.contains(2, 15) is False
        assert span.contains(2, 16) is False

    def test_contains_before_line(self) -> None:
        """contains() should return False for lines before start."""
        span = SourceSpan("test.hl", 5, 1, 10, 1)
        assert span.contains(4, 5) is False

    def test_contains_after_line(self) -> None:
        """contains() should return False for lines after end."""
        span = SourceSpan("test.hl", 5, 1, 10, 1)
        assert span.contains(11, 1) is False

    def test_contains_multiline(self) -> None:
        """contains() should work across multiple lines."""
        span = SourceSpan("test.hl", 1, 1, 3, 10)
        assert span.contains(2, 1) is True
        assert span.contains(1, 1) is True
        assert span.contains(3, 9) is True
        assert span.contains(3, 10) is False

    def test_str_single_line(self) -> None:
        """__str__ should produce compact form for single-line spans."""
        span = SourceSpan("main.hl", 5, 3, 5, 12)
        assert str(span) == "main.hl:5:3-12"

    def test_str_multiline(self) -> None:
        """__str__ should produce full form for multi-line spans."""
        span = SourceSpan("main.hl", 1, 1, 3, 10)
        assert str(span) == "main.hl:1:1-3:10"

    def test_repr(self) -> None:
        """__repr__ should contain all field values."""
        span = SourceSpan("test.hl", 1, 1, 2, 5)
        r = repr(span)
        assert "SourceSpan" in r
        assert "test.hl" in r
        assert "start_line=1" in r


class TestSourceFile:
    """Tests for the SourceFile dataclass."""

    def test_creation(self) -> None:
        """SourceFile should be creatable with filename and source."""
        sf = SourceFile("test.hl", "hello\nworld")
        assert sf.filename == "test.hl"
        assert sf.source == "hello\nworld"

    def test_line_count(self) -> None:
        """line_count should reflect the number of lines."""
        sf = SourceFile("test.hl", "line1\nline2\nline3")
        assert sf.line_count == 3

    def test_line_count_empty(self) -> None:
        """line_count for empty source should be 0."""
        sf = SourceFile("empty.hl", "")
        assert sf.line_count == 0

    def test_get_line_valid(self) -> None:
        """get_line should return correct content for valid line numbers."""
        sf = SourceFile("test.hl", "alpha\nbeta\ngamma")
        assert sf.get_line(1) == "alpha"
        assert sf.get_line(2) == "beta"
        assert sf.get_line(3) == "gamma"

    def test_get_line_out_of_range(self) -> None:
        """get_line should return None for out-of-range line numbers."""
        sf = SourceFile("test.hl", "alpha\nbeta")
        assert sf.get_line(0) is None
        assert sf.get_line(3) is None
        assert sf.get_line(-1) is None

    def test_get_line_single_line(self) -> None:
        """get_line should work for a single-line file."""
        sf = SourceFile("one.hl", "only line")
        assert sf.get_line(1) == "only line"
        assert sf.get_line(2) is None
