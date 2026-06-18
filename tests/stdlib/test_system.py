"""Tests for System stdlib module.

Tests environment, process, and logging operations.
"""

import pytest
import os
import tempfile
from helen.stdlib.system import (
    # Env
    _env_get, _env_set, _env_list, _env_delete,
    # Process
    _exec, _exec_async, _pid, _exit, _kill,
    # Log
    _log_debug, _log_info, _log_warn, _log_error, _log_critical,
    _log_set_level, _log_to_file,
)


# ── Environment Tests ──────────────────────────────────────────


class TestEnvGet:
    """Tests for env_get."""

    def test_existing_var(self):
        os.environ["TEST_VAR"] = "test_value"
        result = _env_get("TEST_VAR")
        assert result == "test_value"
        del os.environ["TEST_VAR"]

    def test_nonexistent_with_default(self):
        result = _env_get("NONEXISTENT_VAR", "default")
        assert result == "default"

    def test_nonexistent_no_default(self):
        result = _env_get("NONEXISTENT_VAR")
        assert result is None


class TestEnvSet:
    """Tests for env_set."""

    def test_set_new(self):
        result = _env_set("NEW_VAR", "new_value")
        assert "Set" in result
        assert os.environ["NEW_VAR"] == "new_value"
        del os.environ["NEW_VAR"]

    def test_set_existing(self):
        os.environ["EXISTING_VAR"] = "old"
        result = _env_set("EXISTING_VAR", "new")
        assert "Set" in result
        assert os.environ["EXISTING_VAR"] == "new"
        del os.environ["EXISTING_VAR"]


class TestEnvList:
    """Tests for env_list."""

    def test_basic(self):
        result = _env_list()
        assert isinstance(result, dict)
        assert len(result) > 0
        # PATH should exist on most systems
        assert "PATH" in result or "path" in result


class TestEnvDelete:
    """Tests for env_delete."""

    def test_delete_existing(self):
        os.environ["TO_DELETE"] = "value"
        result = _env_delete("TO_DELETE")
        assert "Deleted" in result
        assert "TO_DELETE" not in os.environ

    def test_delete_nonexistent(self):
        result = _env_delete("NONEXISTENT")
        assert "not found" in result.lower() or "Deleted" in result


# ── Process Tests ──────────────────────────────────────────────


class TestExec:
    """Tests for exec."""

    def test_simple_command(self):
        result = _exec("echo hello")
        assert result["returncode"] == 0
        assert "hello" in result["stdout"]

    def test_command_with_output(self):
        result = _exec("ls -la")
        assert result["returncode"] == 0
        assert len(result["stdout"]) > 0

    def test_command_with_error(self):
        result = _exec("ls /nonexistent_directory_12345")
        assert result["returncode"] != 0
        assert len(result["stderr"]) > 0

    def test_timeout(self):
        with pytest.raises(TimeoutError):
            _exec("sleep 10", timeout=1)


class TestExecAsync:
    """Tests for exec_async."""

    def test_basic(self):
        pid = _exec_async("sleep 0.1")
        assert isinstance(pid, int)
        assert pid > 0


class TestPid:
    """Tests for pid."""

    def test_basic(self):
        result = _pid()
        assert isinstance(result, int)
        assert result > 0


class TestExit:
    """Tests for exit."""

    def test_exit_zero(self):
        # We can't actually test exit() as it would terminate the test
        # Just verify the function exists and is callable
        assert callable(_exit)


class TestKill:
    """Tests for kill."""

    def test_kill_nonexistent(self):
        with pytest.raises(ProcessLookupError):
            _kill(999999)


# ── Log Tests ──────────────────────────────────────────────────


class TestLogDebug:
    """Tests for log_debug."""

    def test_basic(self):
        result = _log_debug("Debug message")
        assert "DEBUG" in result
        assert "Debug message" in result


class TestLogInfo:
    """Tests for log_info."""

    def test_basic(self):
        result = _log_info("Info message")
        assert "INFO" in result
        assert "Info message" in result


class TestLogWarn:
    """Tests for log_warn."""

    def test_basic(self):
        result = _log_warn("Warning message")
        assert "WARN" in result or "WARNING" in result
        assert "Warning message" in result


class TestLogError:
    """Tests for log_error."""

    def test_basic(self):
        result = _log_error("Error message")
        assert "ERROR" in result
        assert "Error message" in result


class TestLogCritical:
    """Tests for log_critical."""

    def test_basic(self):
        result = _log_critical("Critical message")
        assert "CRITICAL" in result
        assert "Critical message" in result


class TestLogSetLevel:
    """Tests for log_set_level."""

    def test_set_debug(self):
        result = _log_set_level("DEBUG")
        assert "DEBUG" in result or "set" in result.lower()

    def test_set_info(self):
        result = _log_set_level("INFO")
        assert "INFO" in result or "set" in result.lower()

    def test_invalid_level(self):
        with pytest.raises(ValueError):
            _log_set_level("INVALID")


class TestLogToFile:
    """Tests for log_to_file."""

    def test_basic(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            path = f.name
        
        try:
            result = _log_to_file(path)
            assert "file" in result.lower() or path in result
            
            # Write a log message
            _log_info("Test message to file")
            
            # Verify file exists
            assert os.path.exists(path)
        finally:
            if os.path.exists(path):
                os.unlink(path)
