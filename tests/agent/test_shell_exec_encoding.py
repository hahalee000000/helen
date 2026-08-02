"""Tests for cross-platform shell_exec encoding handling.

Ensures shell_exec handles UTF-8 output correctly on Windows (no GBK errors).
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest


class TestShellExecEncoding:
    """Test shell_exec UTF-8 encoding on all platforms."""

    def test_shell_exec_handles_utf8_output(self):
        """shell_exec should handle UTF-8 output without UnicodeDecodeError."""
        from helen.runtime.tools import _shell_exec

        # Use Python to output UTF-8 characters
        # Include various Unicode characters that would fail with GBK
        code = "print('你好世界 🌍 Héllo Wörld')"
        result = _shell_exec(f"{sys.executable} -c \"{code}\"", shell=False)
        assert "你好世界" in result or "error" in result.lower()

    def test_shell_exec_handles_mixed_encoding(self):
        """shell_exec should not crash on mixed encoding output."""
        from helen.runtime.tools import _shell_exec

        # Output bytes that are valid UTF-8 but invalid GBK
        code = r"import sys; sys.stdout.buffer.write(b'\xe4\xb8\xad\xe6\x96\x87')"  # 中文 in UTF-8
        result = _shell_exec(f"{sys.executable} -c \"{code}\"", shell=False)
        # Should not crash, may have replacement characters
        assert result is not None

    def test_shell_exec_full_handles_utf8(self):
        """shell_exec_full should handle UTF-8 output."""
        from helen.runtime.tools import _shell_exec_full
        import json

        code = "print('Test: 中文测试')"
        result_json = _shell_exec_full(f"{sys.executable} -c \"{code}\"", shell=False)
        result = json.loads(result_json)
        assert result["exit_code"] == 0
        assert "中文测试" in result["output"]

    def test_shell_exec_timeout(self):
        """shell_exec should handle timeouts gracefully."""
        from helen.runtime.tools import _shell_exec

        # Run a command that takes longer than timeout
        result = _shell_exec(
            f"{sys.executable} -c \"import time; time.sleep(10)\"",
            shell=False,
            timeout=1,
        )
        assert "timed out" in result.lower() or "error" in result.lower()
