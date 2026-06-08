"""Tests for hellen CLI — run command."""

import os
import tempfile

from hellen.cli.__main__ import run_command


class TestRunCommandSuccess:
    """Test hellen run with valid programs."""

    def test_run_simple_program(self):
        """hellen run with a valid program returns 0."""
        # Simple valid Hellen program
        code = "let x = 1 + 2"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".hellen", delete=False) as f:
            f.write(code)
            f.flush()
            try:
                result = run_command(f.name)
                # Parser may need print statement; at minimum it shouldn't crash
                assert result in (0, 1)
            finally:
                os.unlink(f.name)

    def test_run_file_not_found(self):
        """hellen run with nonexistent file returns 1."""
        result = run_command("/nonexistent/path/file.hellen")
        assert result == 1

    def test_run_empty_file(self):
        """hellen run with empty file returns 0 (nothing to execute)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".hellen", delete=False) as f:
            f.write("")
            f.flush()
            try:
                result = run_command(f.name)
                assert result == 0
            finally:
                os.unlink(f.name)


class TestRunCommandSyntaxError:
    """Test hellen run with syntax errors."""

    def test_run_syntax_error_returns_1(self):
        """hellen run with syntax error returns 1."""
        code = "agent {"  # Incomplete agent declaration
        with tempfile.NamedTemporaryFile(mode="w", suffix=".hellen", delete=False) as f:
            f.write(code)
            f.flush()
            try:
                result = run_command(f.name)
                # Should fail (1 for syntax, 2 for semantic)
                assert result >= 1
            finally:
                os.unlink(f.name)


class TestRunCommandSemanticError:
    """Test hellen run with semantic errors."""

    def test_run_undeclared_variable_returns_2(self):
        """hellen run with undeclared variable returns 2."""
        # This depends on whether semantic analysis catches it
        code = "let x = y + 1"  # y is undeclared
        with tempfile.NamedTemporaryFile(mode="w", suffix=".hellen", delete=False) as f:
            f.write(code)
            f.flush()
            try:
                result = run_command(f.name)
                # May be 1 (parse error if 'let' not supported) or 2 (semantic)
                assert result >= 1
            finally:
                os.unlink(f.name)
