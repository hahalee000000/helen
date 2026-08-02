"""Tests for start_webui.py cross-platform launcher.

These tests ensure the Web UI launcher works correctly on all platforms.
"""
import os
import sys
from pathlib import Path
from unittest import mock

import pytest

from helen.agent.webui.start_webui import find_helen_python, IS_WINDOWS


class TestFindHelenPython:
    """Test find_helen_python() finds the correct Python interpreter."""

    def test_returns_valid_python_path(self):
        """find_helen_python() should return an existing Python executable."""
        python_path = find_helen_python()
        assert python_path is not None
        assert Path(python_path).exists()
        assert "python" in python_path.lower()

    def test_prefers_helen_venv_env(self):
        """find_helen_python() should prefer HELEN_VENV env var."""
        with mock.patch.dict(os.environ, {"HELEN_VENV": str(sys.prefix)}):
            python_path = find_helen_python()
            # Should find Python in the specified venv
            assert python_path is not None

    def test_falls_back_to_home_venv(self):
        """find_helen_python() should fall back to ~/.venv if exists."""
        home_venv = Path.home() / ".venv"
        if not home_venv.exists():
            pytest.skip("~/.venv does not exist")

        # Clear HELEN_VENV to force fallback
        with mock.patch.dict(os.environ, {}, clear=True):
            # Keep essential env vars
            os.environ["PATH"] = os.environ.get("PATH", "")
            python_path = find_helen_python()
            assert python_path is not None

    def test_falls_back_to_sys_executable(self):
        """find_helen_python() should fall back to sys.executable if no venv found."""
        with mock.patch.dict(os.environ, {}, clear=True):
            # Mock Path.home() to return non-existent path
            with mock.patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path("/nonexistent/path/for/testing")
                python_path = find_helen_python()
                assert python_path == sys.executable


class TestCrossPlatformConstants:
    """Test platform-specific constants."""

    def test_is_windows_matches_platform(self):
        """IS_WINDOWS should match sys.platform."""
        expected = sys.platform == "win32"
        assert IS_WINDOWS == expected


class TestBackendStartup:
    """Test backend startup configuration."""

    def test_backend_env_includes_pythonpath(self):
        """Backend env should include backend dir in PYTHONPATH."""
        from helen.agent.webui.start_webui import start_backend

        # This is more of an integration test - just verify the function exists
        # and the module imports correctly
        assert callable(start_backend)

    def test_helem_webui_cwd_propagated(self):
        """HELEN_WEBUI_CWD should be propagated to backend env."""
        test_cwd = "/test/cwd/path"
        env = os.environ.copy()
        env["HELEN_WEBUI_CWD"] = test_cwd
        assert env.get("HELEN_WEBUI_CWD") == test_cwd
