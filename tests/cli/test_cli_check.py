"""Tests for helen CLI — check command."""

import os
import tempfile

from helen.cli.__main__ import check_command


class TestCheckCommand:
    """Test helen check."""

    def test_check_valid_program(self):
        """helen check with valid program prints OK and returns 0."""
        code = "let x = 1"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".helen", delete=False) as f:
            f.write(code)
            f.flush()
            try:
                result = check_command(f.name)
                assert result == 0
            finally:
                os.unlink(f.name)

    def test_check_file_not_found(self):
        """helen check with nonexistent file returns 1."""
        result = check_command("/nonexistent/file.helen")
        assert result == 1

    def test_check_syntax_error(self):
        """helen check reports syntax errors."""
        code = "agent { main"  # Incomplete
        with tempfile.NamedTemporaryFile(mode="w", suffix=".helen", delete=False) as f:
            f.write(code)
            f.flush()
            try:
                result = check_command(f.name)
                assert result >= 1
            finally:
                os.unlink(f.name)

    def test_check_empty_file(self):
        """helen check with empty file returns 0."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".helen", delete=False) as f:
            f.write("")
            f.flush()
            try:
                result = check_command(f.name)
                assert result == 0
            finally:
                os.unlink(f.name)
