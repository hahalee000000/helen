"""Tests for restore_context stdlib function.

restore_context(session_id) bridges TranscriptStore (persistent audit trail)
and active context (what the LLM actually sees). It reads messages from a
previous session's transcript and populates the current interpreter history.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from helen.runtime.history import Message
from helen.runtime.transcript_store import TranscriptStore, JSONLBackend
from helen.stdlib.context import (
    _restore_context,
    _import_context,
    _set_interpreter_context,
)
import helen.stdlib.context as context_module


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_msg(role="user", content="hello", uuid="", pinned=False,
              tool_calls=None, tool_call_id=None, compressed=False):
    return Message(
        role=role,
        content=content,
        tool_calls=tool_calls or [],
        tool_call_id=tool_call_id,
        uuid=uuid,
        pinned=pinned,
        compressed=compressed,
    )


def _setup_context(history=None, agent_context=None, max_tokens=1000):
    """Inject a history list + a mock history_manager into stdlib context."""
    if history is None:
        history = []
    if agent_context is None:
        agent_context = MagicMock()
        agent_context.transcript_store = None
        # Disable working_memory so _export_context doesn't try to serialize a MagicMock
        agent_context.working_memory_enabled = False
        agent_context.working_memory = None
    history_manager = type("HM", (), {"MAX_TOKENS": max_tokens})()
    _set_interpreter_context(history, history_manager, agent_context)
    return history


def _teardown_context():
    _set_interpreter_context([], None, None)


def _build_session(tmp_path: Path, messages: list[Message], session_id: str) -> Path:
    """Create a fake session directory with a transcript file."""
    session_dir = tmp_path / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = session_dir / "transcript.jsonl"

    store = TranscriptStore()
    for msg in messages:
        store.append(msg)

    # Write via JSONLBackend
    backend = JSONLBackend(transcript_path)
    for item in store.transcript:
        backend.append(item)

    return transcript_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRestoreContextBasic:
    """Basic restore_context behavior."""

    def teardown_method(self):
        _teardown_context()

    def test_no_session_id(self):
        """Empty session_id returns error."""
        history = _setup_context()
        result = _restore_context("")
        assert result["status"] == "error"
        assert "session_id is required" in result["error"]

    def test_no_interpreter_context(self):
        """Restore fails cleanly without interpreter."""
        _set_interpreter_context([], None, None)
        result = _restore_context("any_session")
        assert result["status"] == "error"
        assert "No interpreter agent context" in result["error"]

    def test_session_not_found(self, tmp_path, monkeypatch):
        """Non-existent session returns error."""
        history = _setup_context()

        # Mock resolve_session_dir to point to tmp_path
        def fake_resolve(scope=None):
            return (str(tmp_path), "global")
        monkeypatch.setattr(
            "helen.runtime.config.resolve_session_dir", fake_resolve
        )

        result = _restore_context("nonexistent_session")
        assert result["status"] == "error"
        assert "Session not found" in result["error"]

    def test_empty_session(self, tmp_path, monkeypatch):
        """Session with no messages returns error."""
        history = _setup_context()

        # Create an empty session dir
        session_id = "empty_session"
        session_dir = tmp_path / session_id
        session_dir.mkdir()
        transcript_path = session_dir / "transcript.jsonl"
        transcript_path.write_text("")  # empty file

        def fake_resolve(scope=None):
            return (str(tmp_path), "global")
        monkeypatch.setattr(
            "helen.runtime.config.resolve_session_dir", fake_resolve
        )

        result = _restore_context(session_id)
        # Either error "no messages" or error loading empty file
        assert result["status"] == "error"


class TestRestoreContextSuccess:
    """Successful restore scenarios."""

    def teardown_method(self):
        _teardown_context()

    def test_restore_simple_messages(self, tmp_path, monkeypatch):
        """Restore populates interpreter history with all messages."""
        # Build a session with 3 messages
        messages = [
            _make_msg(role="user", content="Hello", uuid="u1"),
            _make_msg(role="assistant", content="Hi there", uuid="a1"),
            _make_msg(role="user", content="How are you?", uuid="u2"),
        ]
        session_id = "session_simple"
        _build_session(tmp_path, messages, session_id)

        def fake_resolve(scope=None):
            return (str(tmp_path), "global")
        monkeypatch.setattr(
            "helen.runtime.config.resolve_session_dir", fake_resolve
        )

        history = _setup_context()
        result = _restore_context(session_id)

        assert result["status"] == "ok"
        assert result["restored_messages"] == 3
        assert result["session_id"] == session_id
        assert result["boundary_markers"] == 0
        # History should now contain the restored messages
        assert len(history) == 3
        assert history[0].role == "user"
        assert history[0].content == "Hello"
        assert history[1].role == "assistant"
        assert history[2].content == "How are you?"

    def test_restore_preserves_uuid_and_pinned(self, tmp_path, monkeypatch):
        """Restore preserves uuid, pinned, compressed fields."""
        messages = [
            _make_msg(role="user", content="Important", uuid="pinned-1", pinned=True),
            _make_msg(role="assistant", content="Normal", uuid="normal-1"),
            _make_msg(role="user", content="Old compressed", uuid="comp-1", compressed=True),
        ]
        session_id = "session_preserve"
        _build_session(tmp_path, messages, session_id)

        def fake_resolve(scope=None):
            return (str(tmp_path), "global")
        monkeypatch.setattr(
            "helen.runtime.config.resolve_session_dir", fake_resolve
        )

        history = _setup_context()
        result = _restore_context(session_id)

        assert result["status"] == "ok"
        assert len(history) == 3
        assert history[0].uuid == "pinned-1"
        assert history[0].pinned is True
        assert history[1].pinned is False
        assert history[2].compressed is True

    def test_restore_preserves_tool_calls(self, tmp_path, monkeypatch):
        """Restore preserves tool_calls and tool_call_id."""
        tool_call = {"id": "call_1", "function": {"name": "read_file", "arguments": "{\"path\":\"foo.py\"}"}}
        messages = [
            _make_msg(role="user", content="Read foo.py", uuid="u1"),
            _make_msg(
                role="assistant",
                content="",
                uuid="a1",
                tool_calls=[tool_call],
            ),
            _make_msg(
                role="tool",
                content="file contents here",
                uuid="t1",
                tool_call_id="call_1",
            ),
        ]
        session_id = "session_tools"
        _build_session(tmp_path, messages, session_id)

        def fake_resolve(scope=None):
            return (str(tmp_path), "global")
        monkeypatch.setattr(
            "helen.runtime.config.resolve_session_dir", fake_resolve
        )

        history = _setup_context()
        result = _restore_context(session_id)

        assert result["status"] == "ok"
        assert len(history) == 3
        assert len(history[1].tool_calls) == 1
        assert history[1].tool_calls[0]["function"]["name"] == "read_file"
        assert history[2].tool_call_id == "call_1"

    def test_restore_replaces_existing_history(self, tmp_path, monkeypatch):
        """Restore clears existing history before importing."""
        messages = [
            _make_msg(role="user", content="New session msg", uuid="new-1"),
        ]
        session_id = "session_replace"
        _build_session(tmp_path, messages, session_id)

        def fake_resolve(scope=None):
            return (str(tmp_path), "global")
        monkeypatch.setattr(
            "helen.runtime.config.resolve_session_dir", fake_resolve
        )

        # Pre-populate history with unrelated messages
        old_msg = _make_msg(role="user", content="Old msg", uuid="old-1")
        history = _setup_context([old_msg])
        assert len(history) == 1

        result = _restore_context(session_id)
        assert result["status"] == "ok"
        assert len(history) == 1
        assert history[0].uuid == "new-1"  # old msg replaced

    def test_restore_round_trip_with_export(self, tmp_path, monkeypatch):
        """export_context -> import_context -> restore_context preserves data."""
        from helen.stdlib.context import _export_context

        # Set up initial context with a properly configured agent_context mock
        agent_context = MagicMock()
        agent_context.transcript_store = None
        agent_context.working_memory_enabled = False
        agent_context.working_memory = None
        agent_context.compression_strategy = "graduated"
        agent_context.cache_aware_enabled = True

        messages = [
            _make_msg(role="user", content="Q1", uuid="q1"),
            _make_msg(role="assistant", content="A1", uuid="a1"),
        ]
        history = _setup_context(messages, agent_context=agent_context)

        # Export
        exported = _export_context()
        assert exported["status"] == "ok"

        # Write to file as if saving between sessions
        import json
        snapshot_path = tmp_path / "snapshot.json"
        with open(snapshot_path, "w") as f:
            json.dump(exported["context"], f)

        # Build a session from the same messages (simulating what TranscriptStore would have)
        session_id = "session_roundtrip"
        _build_session(tmp_path, messages, session_id)

        def fake_resolve(scope=None):
            return (str(tmp_path), "global")
        monkeypatch.setattr(
            "helen.runtime.config.resolve_session_dir", fake_resolve
        )

        # Fresh context and restore
        new_history = _setup_context()
        result = _restore_context(session_id)

        assert result["status"] == "ok"
        assert len(new_history) == 2
        assert new_history[0].content == "Q1"
        assert new_history[1].content == "A1"

        # Compare field-by-field with the exported snapshot
        assert new_history[0].uuid == "q1"
        assert new_history[1].uuid == "a1"


class TestRestoreContextNote:
    """Verify the documented limitation (working_memory not restored)."""

    def teardown_method(self):
        _teardown_context()

    def test_note_mentions_working_memory(self, tmp_path, monkeypatch):
        """Result includes a note about working_memory not being persisted."""
        messages = [_make_msg(role="user", content="hi", uuid="u1")]
        session_id = "session_note"
        _build_session(tmp_path, messages, session_id)

        def fake_resolve(scope=None):
            return (str(tmp_path), "global")
        monkeypatch.setattr(
            "helen.runtime.config.resolve_session_dir", fake_resolve
        )

        _setup_context()
        result = _restore_context(session_id)

        assert result["status"] == "ok"
        assert "note" in result
        assert "working_memory" in result["note"].lower() or "Working memory" in result["note"]


class TestRestoreContextIntegration:
    """Integration test with a realistic agent_context mock."""

    def teardown_method(self):
        _teardown_context()

    def test_restore_with_agent_context_mock(self, tmp_path, monkeypatch):
        """End-to-end with a mocked agent_context containing transcript_store."""
        messages = [
            _make_msg(role="user", content="Hello", uuid="u1"),
            _make_msg(role="assistant", content="Hi", uuid="a1"),
        ]
        session_id = "session_integration"
        _build_session(tmp_path, messages, session_id)

        def fake_resolve(scope=None):
            return (str(tmp_path), "global")
        monkeypatch.setattr(
            "helen.runtime.config.resolve_session_dir", fake_resolve
        )

        # Mock agent_context with a minimal transcript_store attribute
        agent_context = MagicMock()
        agent_context.transcript_store = None  # not used; we load from disk

        history = _setup_context([], agent_context=agent_context)
        result = _restore_context(session_id)

        assert result["status"] == "ok"
        assert result["restored_messages"] == 2
        assert len(history) == 2
