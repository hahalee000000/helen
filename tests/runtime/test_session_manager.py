"""Tests for SessionManager."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from helen.runtime.session_manager import SessionManager


class TestSessionManager:
    """Test session lifecycle management."""

    def test_create_session_manager(self, tmp_path):
        """Test creating a session manager."""
        manager = SessionManager(base_dir=tmp_path)
        assert manager.base_dir == tmp_path
        assert tmp_path.exists()

    def test_create_session_auto_id(self, tmp_path):
        """Test creating a session with auto-generated ID."""
        manager = SessionManager(base_dir=tmp_path)
        session_id = manager.create_session()

        assert session_id.startswith("session_")
        assert len(session_id) > 20  # session_ + timestamp + uuid

        # Verify directory was created
        session_dir = tmp_path / session_id
        assert session_dir.exists()
        assert session_dir.is_dir()

    def test_create_session_custom_id(self, tmp_path):
        """Test creating a session with custom ID."""
        manager = SessionManager(base_dir=tmp_path)
        session_id = manager.create_session("my_custom_session")

        assert session_id == "my_custom_session"

        # Verify directory was created
        session_dir = tmp_path / session_id
        assert session_dir.exists()

    def test_get_session_path(self, tmp_path):
        """Test getting session transcript path."""
        manager = SessionManager(base_dir=tmp_path)
        session_id = manager.create_session()
        path = manager.get_session_path(session_id)

        assert path == tmp_path / session_id / "transcript.jsonl"
        assert path.parent == tmp_path / session_id

    def test_session_exists(self, tmp_path):
        """Test checking if session exists."""
        manager = SessionManager(base_dir=tmp_path)
        session_id = manager.create_session()

        # Initially exists (directory created)
        assert manager.session_exists(session_id) is False  # No transcript file yet

        # Create transcript file
        transcript_path = manager.get_session_path(session_id)
        transcript_path.write_text("test", encoding="utf-8")

        # Now should exist
        assert manager.session_exists(session_id) is True

        # Non-existent session
        assert manager.session_exists("nonexistent") is False

    def test_list_sessions_empty(self, tmp_path):
        """Test listing sessions when none exist."""
        manager = SessionManager(base_dir=tmp_path)
        sessions = manager.list_sessions()
        assert sessions == []

    def test_list_sessions(self, tmp_path):
        """Test listing sessions."""
        manager = SessionManager(base_dir=tmp_path)

        # Create multiple sessions
        session1 = manager.create_session("session_1")
        session2 = manager.create_session("session_2")
        session3 = manager.create_session("session_3")

        # Create transcript files with different sizes
        for i, session_id in enumerate([session1, session2, session3]):
            path = manager.get_session_path(session_id)
            path.write_text("x" * (i * 100), encoding="utf-8")
            # Small delay to ensure different modification times
            time.sleep(0.01)

        sessions = manager.list_sessions()

        assert len(sessions) == 3
        # Should be sorted by modification time (newest first)
        assert sessions[0]["session_id"] == session3
        assert sessions[1]["session_id"] == session2
        assert sessions[2]["session_id"] == session1

        # Verify metadata
        for session in sessions:
            assert "session_id" in session
            assert "created_at" in session
            assert "modified_at" in session
            assert "size_bytes" in session
            assert "message_count" in session

    def test_delete_session(self, tmp_path):
        """Test deleting a session."""
        manager = SessionManager(base_dir=tmp_path)
        session_id = manager.create_session()

        # Create transcript file
        path = manager.get_session_path(session_id)
        path.write_text("test", encoding="utf-8")

        # Delete session
        result = manager.delete_session(session_id)
        assert result is True

        # Verify directory was removed
        session_dir = tmp_path / session_id
        assert not session_dir.exists()

        # Deleting non-existent session
        result = manager.delete_session("nonexistent")
        assert result is False

    def test_cleanup_old_sessions(self, tmp_path):
        """Test cleaning up old sessions."""
        manager = SessionManager(base_dir=tmp_path)

        # Create 10 sessions
        session_ids = []
        for i in range(10):
            session_id = manager.create_session(f"session_{i}")
            path = manager.get_session_path(session_id)
            path.write_text(f"test {i}", encoding="utf-8")
            session_ids.append(session_id)
            time.sleep(0.01)

        # Cleanup, keeping only 3 most recent
        deleted = manager.cleanup_old_sessions(keep_count=3)

        assert deleted == 7

        # Verify only 3 remain
        sessions = manager.list_sessions()
        assert len(sessions) == 3

        # Should keep the most recent ones
        remaining_ids = [s["session_id"] for s in sessions]
        assert "session_9" in remaining_ids
        assert "session_8" in remaining_ids
        assert "session_7" in remaining_ids

    def test_cleanup_noop_when_under_limit(self, tmp_path):
        """Test cleanup does nothing when under limit."""
        manager = SessionManager(base_dir=tmp_path)

        # Create 5 sessions
        for i in range(5):
            session_id = manager.create_session(f"session_{i}")
            path = manager.get_session_path(session_id)
            path.write_text(f"test {i}", encoding="utf-8")

        # Cleanup with limit of 10
        deleted = manager.cleanup_old_sessions(keep_count=10)

        assert deleted == 0

        # All sessions should remain
        sessions = manager.list_sessions()
        assert len(sessions) == 5
