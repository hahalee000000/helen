"""Tests for Python Bridge session_id support (Issue #16).

Covers the session_id detection chain in import_hook:
    1. Explicit set_session_id() (highest priority)
    2. Environment variable HELEN_SESSION_ID
    3. Memento file .helen/current_session_id (relative to cwd)
    4. None (default, creates new session)
"""

import sys
from pathlib import Path
from unittest import mock

import pytest

from helen.python_bridge.import_hook import (
    set_session_id,
    get_session_id,
    _detect_session_id,
)
import helen.python_bridge.import_hook as import_hook_module


# ─── Helpers ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_session_id_override():
    """Reset the module-level override before and after each test."""
    import_hook_module._session_id_override = None
    yield
    import_hook_module._session_id_override = None


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Remove HELEN_SESSION_ID from environment for each test."""
    monkeypatch.delenv("HELEN_SESSION_ID", raising=False)


# ─── Detection chain priority ────────────────────────────────────────────────


class TestSessionIdDetectionChain:
    """The detection chain must respect priority: explicit > env > memento > None."""

    def test_default_returns_none(self):
        """No override, no env, no memento -> None (new session)."""
        with mock.patch.object(Path, "exists", return_value=False):
            assert _detect_session_id() is None

    def test_environment_variable_detected(self, monkeypatch):
        """HELEN_SESSION_ID env var is picked up."""
        monkeypatch.setenv("HELEN_SESSION_ID", "env_session_123")
        with mock.patch.object(Path, "exists", return_value=False):
            assert _detect_session_id() == "env_session_123"

    def test_explicit_override_beats_environment(self, monkeypatch):
        """set_session_id() overrides environment variable."""
        monkeypatch.setenv("HELEN_SESSION_ID", "env_session_123")
        set_session_id("explicit_session_456")
        assert _detect_session_id() == "explicit_session_456"

    def test_clearing_override_falls_back_to_env(self, monkeypatch):
        """set_session_id(None) clears override, falls back to env."""
        monkeypatch.setenv("HELEN_SESSION_ID", "env_session_123")
        set_session_id("explicit_session_456")
        set_session_id(None)
        assert _detect_session_id() == "env_session_123"

    def test_memento_file_detected(self, tmp_path, monkeypatch):
        """Memento file .helen/current_session_id (relative to cwd) is picked up."""
        memento_dir = tmp_path / ".helen"
        memento_dir.mkdir()
        (memento_dir / "current_session_id").write_text(
            "memento_session_789", encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)
        assert _detect_session_id() == "memento_session_789"

    def test_memento_strips_whitespace(self, tmp_path, monkeypatch):
        """Memento file content is stripped of whitespace/newlines."""
        memento_dir = tmp_path / ".helen"
        memento_dir.mkdir()
        (memento_dir / "current_session_id").write_text(
            "  memento_session_789\n\n", encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)
        assert _detect_session_id() == "memento_session_789"

    def test_empty_memento_falls_back_to_none(self, tmp_path, monkeypatch):
        """Empty/whitespace-only memento file is ignored."""
        memento_dir = tmp_path / ".helen"
        memento_dir.mkdir()
        (memento_dir / "current_session_id").write_text(
            "   \n\n", encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)
        assert _detect_session_id() is None

    def test_env_beats_memento(self, tmp_path, monkeypatch):
        """Environment variable takes precedence over memento file."""
        memento_dir = tmp_path / ".helen"
        memento_dir.mkdir()
        (memento_dir / "current_session_id").write_text(
            "memento_session_789", encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HELEN_SESSION_ID", "env_session_123")
        assert _detect_session_id() == "env_session_123"

    def test_explicit_beats_memento(self, tmp_path, monkeypatch):
        """set_session_id() takes precedence over memento file."""
        memento_dir = tmp_path / ".helen"
        memento_dir.mkdir()
        (memento_dir / "current_session_id").write_text(
            "memento_session_789", encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)
        set_session_id("explicit_session_456")
        assert _detect_session_id() == "explicit_session_456"

    def test_missing_memento_file_is_none(self, tmp_path, monkeypatch):
        """No memento file present -> None (no error)."""
        monkeypatch.chdir(tmp_path)
        assert _detect_session_id() is None


# ─── Public API ──────────────────────────────────────────────────────────────


class TestPublicApi:
    """set_session_id / get_session_id public API."""

    def test_set_and_get_session_id(self):
        set_session_id("my_session")
        assert get_session_id() == "my_session"

    def test_get_session_id_returns_none_by_default(self):
        with mock.patch.object(Path, "exists", return_value=False):
            assert get_session_id() is None

    def test_set_none_clears_override(self, monkeypatch):
        monkeypatch.setenv("HELEN_SESSION_ID", "env_session")
        set_session_id("explicit")
        assert get_session_id() == "explicit"
        set_session_id(None)
        assert get_session_id() == "env_session"


# ─── Integration: import hook actually uses session_id ───────────────────────


class TestImportHookUsesSessionId:
    """The import hook must pass detected session_id to the Interpreter."""

    def test_import_hook_passes_explicit_session_id(self, tmp_path, monkeypatch):
        """When set_session_id() is called, the created Interpreter uses it."""
        # Create a simple .helen file with an agent
        helen_file = tmp_path / "agent_mod.helen"
        helen_file.write_text(
            'agent Greeter(name: str) {\n    main { return "hello " + name }\n}\n',
            encoding="utf-8",
        )
        # Add tmp_path to sys.path so the import hook can find agent_mod.helen
        monkeypatch.syspath_prepend(str(tmp_path))
        # Clear any cached module
        monkeypatch.delitem(sys.modules, "agent_mod", raising=False)

        set_session_id("test_session_explicit")
        try:
            import importlib
            mod = importlib.import_module("agent_mod")
            interp = mod.__interpreter__
            assert interp._agent_context.session_id == "test_session_explicit"
        finally:
            import_hook_module._session_id_override = None
            monkeypatch.delitem(sys.modules, "agent_mod", raising=False)

    def test_import_hook_creates_new_session_when_none(self, tmp_path, monkeypatch):
        """When no session_id is configured, a new session is created (not None)."""
        helen_file = tmp_path / "agent_new.helen"
        helen_file.write_text(
            'agent Greeter(name: str) {\n    main { return "hello " + name }\n}\n',
            encoding="utf-8",
        )
        monkeypatch.syspath_prepend(str(tmp_path))
        monkeypatch.delitem(sys.modules, "agent_new", raising=False)
        # Ensure no env/memento interferes
        monkeypatch.chdir(tmp_path)

        import importlib
        mod = importlib.import_module("agent_new")
        interp = mod.__interpreter__
        sid = interp._agent_context.session_id
        assert sid is not None
        assert sid.startswith("session_")
        monkeypatch.delitem(sys.modules, "agent_new", raising=False)


# Need sys import for the integration tests
