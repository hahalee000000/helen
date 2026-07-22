"""Tests for v1.24 resume_session improvements."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from helen.runtime.history import Message
from helen.runtime.transcript_store import TranscriptStore, JSONLBackend
from helen.stdlib.transcript import resume_session


def _make_msg(
    role="user", content="test", uuid="", invocation_id="",
    parent_invocation_id="", agent_name=None, visible_to_invocation_ids=None,
):
    return Message(
        role=role, content=content, uuid=uuid, invocation_id=invocation_id,
        parent_invocation_id=parent_invocation_id, agent_name=agent_name,
        visible_to_invocation_ids=visible_to_invocation_ids or [],
    )


def _setup_context(messages, invocation_id="current_invocation"):
    from helen.stdlib import transcript as transcript_module
    store = TranscriptStore()
    for msg in messages:
        store.append(msg)
    agent_context = MagicMock()
    agent_context.transcript_store = store
    interpreter_ref = MagicMock()
    interpreter_ref._current_invocation_id = invocation_id
    patcher1 = patch.object(transcript_module, '_get_agent_context', return_value=agent_context)
    patcher2 = patch('helen.stdlib.llm_control._interpreter_ref', interpreter_ref)
    patcher1.start()
    patcher2.start()
    history = [msg for msg in store.transcript if isinstance(msg, Message)]
    return history, store, [patcher1, patcher2]


def _teardown_context(patchers):
    for p in patchers:
        p.stop()


def _build_session(tmp_path, messages, session_id):
    """Build session in the format expected by SessionManager."""
    session_dir = tmp_path / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    store = TranscriptStore()
    for msg in messages:
        store.append(msg)
    # SessionManager expects "transcript.jsonl"
    jsonl_path = session_dir / "transcript.jsonl"
    backend = JSONLBackend(jsonl_path)
    for item in store.transcript:
        backend.append(item)
    backend.close()


def test_resume_adds_visibility(tmp_path, monkeypatch):
    messages = [
        _make_msg(role="user", content="Q1", uuid="msg-1", invocation_id="inv_A"),
        _make_msg(role="assistant", content="A1", uuid="msg-2", invocation_id="inv_A"),
    ]
    _build_session(tmp_path, messages, "session_A")
    monkeypatch.setattr("helen.runtime.config.resolve_session_dir", lambda scope=None: (str(tmp_path), "global"))
    history, store, patchers = _setup_context([], invocation_id="inv_B")
    try:
        result = resume_session("session_A")
        assert result["status"] == "ok"
        assert result["imported_messages"] == 2
        for msg in store.transcript:
            if isinstance(msg, Message):
                assert msg.invocation_id == "inv_A"
                assert "inv_B" in msg.visible_to_invocation_ids
    finally:
        _teardown_context(patchers)


def test_resume_preserves_invocation_id(tmp_path, monkeypatch):
    messages = [_make_msg(role="user", content="Q1", uuid="msg-1", invocation_id="inv_A")]
    _build_session(tmp_path, messages, "session_A")
    monkeypatch.setattr("helen.runtime.config.resolve_session_dir", lambda scope=None: (str(tmp_path), "global"))
    history, store, patchers = _setup_context([], invocation_id="inv_B")
    try:
        result = resume_session("session_A")
        assert result["status"] == "ok"
        for msg in store.transcript:
            if isinstance(msg, Message):
                assert msg.invocation_id == "inv_A"
    finally:
        _teardown_context(patchers)


def test_resume_idempotent(tmp_path, monkeypatch):
    messages = [
        _make_msg(role="user", content="Q1", uuid="msg-1", invocation_id="inv_A"),
        _make_msg(role="assistant", content="A1", uuid="msg-2", invocation_id="inv_A"),
    ]
    _build_session(tmp_path, messages, "session_A")
    monkeypatch.setattr("helen.runtime.config.resolve_session_dir", lambda scope=None: (str(tmp_path), "global"))
    history, store, patchers = _setup_context([], invocation_id="inv_B")
    try:
        result1 = resume_session("session_A")
        assert result1["status"] == "ok"
        assert result1["imported_messages"] == 2
        assert result1["skipped_duplicates"] == 0
        result2 = resume_session("session_A")
        assert result2["status"] == "ok"
        assert result2["imported_messages"] == 0
        assert result2["skipped_duplicates"] == 2
        msg_count = sum(1 for item in store.transcript if isinstance(item, Message))
        assert msg_count == 2
    finally:
        _teardown_context(patchers)


def test_resume_returns_dict(tmp_path, monkeypatch):
    messages = [_make_msg(role="user", content="Q1", uuid="msg-1", invocation_id="inv_A")]
    _build_session(tmp_path, messages, "session_A")
    monkeypatch.setattr("helen.runtime.config.resolve_session_dir", lambda scope=None: (str(tmp_path), "global"))
    history, store, patchers = _setup_context([], invocation_id="inv_B")
    try:
        result = resume_session("session_A")
        assert isinstance(result, dict)
        assert "status" in result
        assert "imported_messages" in result
        assert "skipped_duplicates" in result
    finally:
        _teardown_context(patchers)
