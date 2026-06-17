"""Tests for stream output standard library functions (Phase 1)."""

import pytest
import sys
from io import StringIO
from helen.stdlib import stdlib


class TestStreamPrint:
    """Tests for stream_print function."""
    
    def test_stream_print_exists(self):
        """stream_print should be registered in stdlib."""
        func = stdlib.lookup("stream_print")
        assert func is not None, "stream_print should be registered"
        assert func.name == "stream_print"
        assert func.category == "io"
    
    def test_stream_print_returns_text(self):
        """stream_print should return the printed text."""
        func = stdlib.lookup("stream_print")
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            result = func.fn("hello")
            assert result == "hello"
        finally:
            sys.stdout = old_stdout
    
    def test_stream_print_no_newline(self):
        """stream_print should not append newline."""
        func = stdlib.lookup("stream_print")
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            func.fn("hello")
            output = sys.stdout.getvalue()
            assert output == "hello", f"Expected 'hello', got {repr(output)}"
            assert not output.endswith("\n"), "stream_print should not add newline"
        finally:
            sys.stdout = old_stdout
    
    def test_stream_print_multiple_calls(self):
        """Multiple stream_print calls should append on same line."""
        func = stdlib.lookup("stream_print")
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            func.fn("hello")
            func.fn(" ")
            func.fn("world")
            output = sys.stdout.getvalue()
            assert output == "hello world"
        finally:
            sys.stdout = old_stdout
    
    def test_stream_print_empty_string(self):
        """stream_print with empty string should print nothing."""
        func = stdlib.lookup("stream_print")
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            result = func.fn("")
            assert result == ""
            output = sys.stdout.getvalue()
            assert output == ""
        finally:
            sys.stdout = old_stdout


class TestStreamClear:
    """Tests for stream_clear function."""
    
    def test_stream_clear_exists(self):
        """stream_clear should be registered in stdlib."""
        func = stdlib.lookup("stream_clear")
        assert func is not None, "stream_clear should be registered"
        assert func.name == "stream_clear"
        assert func.category == "io"
    
    def test_stream_clear_returns_empty(self):
        """stream_clear should return empty string."""
        func = stdlib.lookup("stream_clear")
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            result = func.fn()
            assert result == ""
        finally:
            sys.stdout = old_stdout
    
    def test_stream_clear_outputs_ansi_code(self):
        """stream_clear should output ANSI escape code."""
        func = stdlib.lookup("stream_clear")
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            func.fn()
            output = sys.stdout.getvalue()
            # ANSI escape code for clearing line
            assert "\x1b[2K" in output or "\033[2K" in output or "\r" in output
        finally:
            sys.stdout = old_stdout


class TestProgressBar:
    """Tests for progress_bar function."""
    
    def test_progress_bar_exists(self):
        """progress_bar should be registered in stdlib."""
        func = stdlib.lookup("progress_bar")
        assert func is not None, "progress_bar should be registered"
        assert func.name == "progress_bar"
        assert func.category == "io"
    
    def test_progress_bar_zero_percent(self):
        """progress_bar at 0% should show empty bar."""
        func = stdlib.lookup("progress_bar")
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            result = func.fn(0, 100, 40)
            assert "0%" in result
            assert "[" in result and "]" in result
        finally:
            sys.stdout = old_stdout
    
    def test_progress_bar_fifty_percent(self):
        """progress_bar at 50% should show half-filled bar."""
        func = stdlib.lookup("progress_bar")
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            result = func.fn(50, 100, 40)
            assert "50%" in result
        finally:
            sys.stdout = old_stdout
    
    def test_progress_bar_hundred_percent(self):
        """progress_bar at 100% should show full bar."""
        func = stdlib.lookup("progress_bar")
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            result = func.fn(100, 100, 40)
            assert "100%" in result
        finally:
            sys.stdout = old_stdout
    
    def test_progress_bar_default_width(self):
        """progress_bar should use default width of 40."""
        func = stdlib.lookup("progress_bar")
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            result = func.fn(50, 100)
            # Should work without width parameter
            assert "50%" in result
        finally:
            sys.stdout = old_stdout
    
    def test_progress_bar_custom_width(self):
        """progress_bar should respect custom width."""
        func = stdlib.lookup("progress_bar")
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            result = func.fn(50, 100, 20)
            assert "50%" in result
        finally:
            sys.stdout = old_stdout


class TestStreamCursorUp:
    """Tests for stream_cursor_up function."""
    
    def test_stream_cursor_up_exists(self):
        """stream_cursor_up should be registered in stdlib."""
        func = stdlib.lookup("stream_cursor_up")
        assert func is not None, "stream_cursor_up should be registered"
        assert func.name == "stream_cursor_up"
        assert func.category == "io"
    
    def test_stream_cursor_up_default(self):
        """stream_cursor_up should move up 1 line by default."""
        func = stdlib.lookup("stream_cursor_up")
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            result = func.fn()
            assert result == ""
            output = sys.stdout.getvalue()
            # ANSI escape code for moving cursor up
            assert "\x1b[1A" in output or "\033[1A" in output
        finally:
            sys.stdout = old_stdout
    
    def test_stream_cursor_up_custom(self):
        """stream_cursor_up should move up n lines."""
        func = stdlib.lookup("stream_cursor_up")
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            result = func.fn(3)
            assert result == ""
            output = sys.stdout.getvalue()
            assert "\x1b[3A" in output or "\033[3A" in output
        finally:
            sys.stdout = old_stdout


class TestStreamCursorDown:
    """Tests for stream_cursor_down function."""
    
    def test_stream_cursor_down_exists(self):
        """stream_cursor_down should be registered in stdlib."""
        func = stdlib.lookup("stream_cursor_down")
        assert func is not None, "stream_cursor_down should be registered"
        assert func.name == "stream_cursor_down"
        assert func.category == "io"
    
    def test_stream_cursor_down_default(self):
        """stream_cursor_down should move down 1 line by default."""
        func = stdlib.lookup("stream_cursor_down")
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            result = func.fn()
            assert result == ""
            output = sys.stdout.getvalue()
            # ANSI escape code for moving cursor down
            assert "\x1b[1B" in output or "\033[1B" in output
        finally:
            sys.stdout = old_stdout
    
    def test_stream_cursor_down_custom(self):
        """stream_cursor_down should move down n lines."""
        func = stdlib.lookup("stream_cursor_down")
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            result = func.fn(2)
            assert result == ""
            output = sys.stdout.getvalue()
            assert "\x1b[2B" in output or "\033[2B" in output
        finally:
            sys.stdout = old_stdout


class TestStreamIntegration:
    """Integration tests for stream functions."""
    
    def test_stream_print_and_clear(self):
        """stream_print followed by stream_clear should work together."""
        stream_print = stdlib.lookup("stream_print")
        stream_clear = stdlib.lookup("stream_clear")
        
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            stream_print.fn("Loading...")
            stream_clear.fn()
            stream_print.fn("Done!")
            output = sys.stdout.getvalue()
            assert "Loading..." in output
            assert "Done!" in output
        finally:
            sys.stdout = old_stdout
    
    def test_progress_bar_animation(self):
        """progress_bar should work in a loop simulation."""
        progress_bar = stdlib.lookup("progress_bar")
        
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            for i in range(0, 101, 25):
                progress_bar.fn(i, 100, 20)
            output = sys.stdout.getvalue()
            assert "0%" in output
            assert "25%" in output
            assert "50%" in output
            assert "75%" in output
            assert "100%" in output
        finally:
            sys.stdout = old_stdout
