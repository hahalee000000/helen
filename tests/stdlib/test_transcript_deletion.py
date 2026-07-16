"""Tests for TranscriptStore session deletion functions (v1.21).

Tests delete_session(), delete_current_session(), and cleanup_sessions().
"""
import os
import tempfile
import shutil
from pathlib import Path

import pytest
from helen.stdlib.transcript import (
    delete_session,
    delete_current_session,
    cleanup_sessions,
    get_session_id,
)
from helen.runtime.session_manager import SessionManager
from helen.runtime.transcript_store import Message, TranscriptStore, JSONLBackend


@pytest.fixture
def temp_session_dir(monkeypatch):
    """Create a temporary session directory and set HELEN_SESSION_DIR."""
    temp_dir = tempfile.mkdtemp(prefix="helen_test_")
    monkeypatch.setenv("HELEN_SESSION_DIR", temp_dir)
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def populated_sessions(temp_session_dir):
    """Create several test sessions with messages."""
    manager = SessionManager(base_dir=temp_session_dir)
    session_ids = []

    for i in range(5):
        session_id = manager.create_session()
        session_ids.append(session_id)

        # Write some data
        transcript_path = manager.get_session_path(session_id)
        backend = JSONLBackend(transcript_path)
        store = TranscriptStore(backend=backend)

        for j in range(3):
            store.append(Message(
                role="user" if j % 2 == 0 else "assistant",
                content=f"Test message {j} in session {i}",
            ))
        for msg in store.transcript:
            backend.append(msg)

    return session_ids


class TestDeleteSession:
    """Test delete_session() function."""

    def test_delete_existing_session(self, populated_sessions, temp_session_dir):
        """delete_session removes an existing session."""
        session_id = populated_sessions[0]
        result = delete_session(session_id)

        assert result["status"] == "ok"
        assert result["session_id"] == session_id
        assert result["freed_bytes"] > 0
        assert "message" in result

        # Verify session is gone
        manager = SessionManager(base_dir=temp_session_dir)
        assert not manager.session_exists(session_id)

    def test_delete_nonexistent_session(self, temp_session_dir):
        """delete_session returns error for non-existent session."""
        result = delete_session("nonexistent_session_id")

        assert result["status"] == "error"
        assert "not found" in result["message"].lower() or "not found" in result.get("error", "").lower()

    def test_delete_empty_session_id(self, temp_session_dir):
        """delete_session rejects empty session_id."""
        result = delete_session("")

        assert result["status"] == "error"
        assert "required" in result["message"].lower()


class TestDeleteCurrentSession:
    """Test delete_current_session() function."""

    def test_without_confirm(self):
        """delete_current_session requires confirm=True."""
        result = delete_current_session()

        assert result["status"] == "error"
        assert "confirm=true" in result["message"].lower()
        assert result["session_id"] == get_session_id()

    def test_without_confirm_false(self):
        """delete_current_session with confirm=False also blocked."""
        result = delete_current_session(confirm=False)

        assert result["status"] == "error"
        assert "confirm=true" in result["message"].lower()


class TestCleanupSessions:
    """Test cleanup_sessions() function."""

    def test_cleanup_keep_count(self, populated_sessions, temp_session_dir):
        """cleanup_sessions keeps only N most recent sessions."""
        result = cleanup_sessions(keep_count=2)

        assert result["status"] == "ok"
        assert result["deleted_count"] >= 1
        assert result["freed_bytes"] > 0

        # Verify remaining sessions
        manager = SessionManager(base_dir=temp_session_dir)
        remaining = manager.list_sessions()
        # Should keep at most 2 non-current sessions (plus current if any)
        non_current = [s for s in remaining if s["session_id"] != get_session_id()]
        assert len(non_current) <= 2

    def test_cleanup_keep_all(self, populated_sessions):
        """cleanup_sessions with high keep_count deletes nothing."""
        result = cleanup_sessions(keep_count=1000)

        assert result["status"] == "ok"
        assert result["deleted_count"] == 0

    def test_cleanup_default(self, populated_sessions):
        """cleanup_sessions with no args uses default keep_count=100."""
        result = cleanup_sessions()

        assert result["status"] == "ok"
        # With 5 sessions and default keep_count=100, nothing should be deleted
        assert result["deleted_count"] == 0

    def test_cleanup_older_than_days(self, populated_sessions, temp_session_dir):
        """cleanup_sessions with older_than_days deletes old sessions."""
        # All sessions are fresh, so older_than_days=1 should delete nothing
        result = cleanup_sessions(older_than_days=1)

        assert result["status"] == "ok"
        assert result["deleted_count"] == 0

        # older_than_days=0 should delete all non-current sessions
        result = cleanup_sessions(older_than_days=0)

        assert result["status"] == "ok"
        assert result["deleted_count"] >= 1

    def test_cleanup_combined(self, populated_sessions):
        """cleanup_sessions with both keep_count and older_than_days."""
        result = cleanup_sessions(keep_count=1, older_than_days=0)

        assert result["status"] == "ok"
        assert result["deleted_count"] >= 1
