"""Tests for helen.agent.chat_tui_web module.

This module depends on Helen FFI runtime (helen.python_bridge, chat_actor).
We mock those before importing to test the module-level code.
"""
import sys
import types
import json
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


def _install_fake_helen_modules():
    """Install fake helen.python_bridge and chat_actor into sys.modules."""
    # Fake helen package
    if "helen" not in sys.modules:
        helen_mod = types.ModuleType("helen")
        helen_mod.__path__ = []
        sys.modules["helen"] = helen_mod

    # Fake helen.python_bridge
    mock_bridge = types.ModuleType("helen.python_bridge")
    mock_bridge.install_import_hook = MagicMock()
    mock_bridge.set_session_id = MagicMock()
    sys.modules["helen.python_bridge"] = mock_bridge

    # Fake chat_actor module
    mock_actor = types.ModuleType("chat_actor")
    mock_actor.spawn_chat_actor = MagicMock(return_value={"status": "started"})
    mock_actor.tui_chat_handler_actor = MagicMock(return_value="response")
    mock_actor.TUIChatAgent = MagicMock()
    mock_actor.exit_chat_actor = MagicMock()
    mock_actor.is_chat_actor_running = MagicMock(return_value=True)
    mock_actor.send_heartbeat = MagicMock()
    sys.modules["chat_actor"] = mock_actor

    return mock_bridge, mock_actor


def _remove_chat_tui_web():
    """Remove chat_tui_web from sys.modules to force re-import."""
    for key in list(sys.modules.keys()):
        if key == "chat_tui_web" or key.startswith("chat_tui_web."):
            del sys.modules[key]


@pytest.fixture
def fake_env(tmp_path, monkeypatch):
    """Set up fake Helen environment for importing chat_tui_web."""
    _remove_chat_tui_web()

    # Save original modules so we can restore them after the test.
    # Without this, the fake helen.python_bridge leaks into sys.modules and
    # breaks later tests that import the real module (e.g.
    # tests/execution/test_python_bridge_session_id.py).
    saved_modules = {}
    for key in ("helen", "helen.python_bridge", "chat_actor"):
        if key in sys.modules:
            saved_modules[key] = sys.modules[key]

    mock_bridge, mock_actor = _install_fake_helen_modules()

    # Set HELEN_AGENT_DIR to the actual agent dir
    agent_dir = str(Path(__file__).resolve().parents[2] / "helen" / "agent")
    monkeypatch.syspath_prepend(agent_dir)

    yield mock_bridge, mock_actor

    _remove_chat_tui_web()

    # Restore original modules (or remove the fakes if originals never existed)
    for key, mod in saved_modules.items():
        sys.modules[key] = mod
    for key in ("helen", "helen.python_bridge", "chat_actor"):
        if key not in saved_modules and key in sys.modules:
            del sys.modules[key]


class TestModuleImport:
    def test_import_succeeds_with_mocks(self, fake_env):
        """chat_tui_web imports when helen.python_bridge and chat_actor are mocked."""
        import chat_tui_web
        assert hasattr(chat_tui_web, "is_actor_mode_available")
        assert hasattr(chat_tui_web, "get_saved_child_sid")

    def test_helen_agent_dir_set(self, fake_env):
        """HELEN_AGENT_DIR is set to the agent directory."""
        import chat_tui_web
        assert Path(chat_tui_web.HELEN_AGENT_DIR).is_dir()

    def test_all_exports(self, fake_env):
        """__all__ contains expected exports."""
        import chat_tui_web
        expected = [
            'spawn_chat_actor', 'tui_chat_handler_actor', 'TUIChatAgent',
            'exit_chat_actor', 'is_chat_actor_running', 'is_actor_mode_available',
            'get_saved_child_sid', 'send_heartbeat',
        ]
        for name in expected:
            assert name in chat_tui_web.__all__, f"{name} missing from __all__"


class TestIsActorModeAvailable:
    def test_returns_true(self, fake_env):
        import chat_tui_web
        assert chat_tui_web.is_actor_mode_available() is True


class TestGetSavedChildSid:
    def test_returns_empty_when_no_memento(self, fake_env, tmp_path, monkeypatch):
        """No memento file -> empty child SID."""
        monkeypatch.chdir(tmp_path)
        _remove_chat_tui_web()
        import chat_tui_web
        assert chat_tui_web.get_saved_child_sid() == ""

    def test_returns_child_sid_from_memento(self, fake_env, tmp_path, monkeypatch):
        """Memento with child SID -> returns it."""
        helen_dir = tmp_path / ".helen"
        helen_dir.mkdir()
        memento = helen_dir / "current_session_id"
        memento.write_text(json.dumps({"main": "main-sid-123", "child": "child-sid-456"}))
        monkeypatch.chdir(tmp_path)

        _remove_chat_tui_web()
        mock_bridge, _ = fake_env
        import chat_tui_web
        # set_session_id should have been called with main SID
        mock_bridge.set_session_id.assert_called_with("main-sid-123")
        assert chat_tui_web.get_saved_child_sid() == "child-sid-456"

    def test_handles_malformed_memento(self, fake_env, tmp_path, monkeypatch):
        """Malformed JSON memento -> doesn't crash, returns empty."""
        helen_dir = tmp_path / ".helen"
        helen_dir.mkdir()
        memento = helen_dir / "current_session_id"
        memento.write_text("not valid json{{{")
        monkeypatch.chdir(tmp_path)

        _remove_chat_tui_web()
        import chat_tui_web
        assert chat_tui_web.get_saved_child_sid() == ""

    def test_handles_empty_main_sid(self, fake_env, tmp_path, monkeypatch):
        """Memento with empty main SID -> doesn't call set_session_id."""
        helen_dir = tmp_path / ".helen"
        helen_dir.mkdir()
        memento = helen_dir / "current_session_id"
        memento.write_text(json.dumps({"main": "", "child": "child-1"}))
        monkeypatch.chdir(tmp_path)

        _remove_chat_tui_web()
        mock_bridge, _ = fake_env
        import chat_tui_web
        mock_bridge.set_session_id.assert_not_called()
        assert chat_tui_web.get_saved_child_sid() == "child-1"


class TestImportFailure:
    def test_exits_when_bridge_unavailable(self, tmp_path, monkeypatch):
        """When helen.python_bridge can't be imported, module calls sys.exit(1)."""
        _remove_chat_tui_web()
        # Save and remove any fake helen modules — must restore on teardown
        # so subsequent tests see the original import_hook module (otherwise
        # the import_hook gets reloaded as a new module instance, creating a
        # second HelenMetaPathFinder and breaking session_id override tests).
        saved_bridge_modules = {}
        for key in list(sys.modules.keys()):
            if key.startswith("helen.python_bridge"):
                saved_bridge_modules[key] = sys.modules.pop(key)

        # Make helen.python_bridge raise ImportError
        import builtins
        original_import = builtins.__import__

        def failing_import(name, *args, **kwargs):
            if name == "helen.python_bridge":
                raise ImportError("no bridge")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", failing_import)

        agent_dir = str(Path(__file__).resolve().parents[2] / "helen" / "agent")
        monkeypatch.syspath_prepend(agent_dir)

        try:
            with pytest.raises(SystemExit) as exc_info:
                import chat_tui_web  # noqa: F401

            assert exc_info.value.code == 1
        finally:
            _remove_chat_tui_web()
            # Restore the original helen.python_bridge* modules so the import
            # hook's set_session_id() and the loader's _detect_session_id()
            # continue to refer to the SAME module instance.
            for key, mod in saved_bridge_modules.items():
                sys.modules[key] = mod
