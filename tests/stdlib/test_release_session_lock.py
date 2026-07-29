"""Tests for v1.30.2: release_session_lock stdlib function.

Verifies that:
- release_session_lock() removes the session.lock file
- release_session_lock() is safe to call when no lock exists
- release_session_lock() is safe to call when lock is held by another process
"""

import os
import tempfile

import pytest


class TestReleaseSessionLock:
    """Test release_session_lock stdlib function."""

    def test_release_existing_lock(self, tmp_path, monkeypatch):
        """release_session_lock removes an existing lock file."""
        # Set up session directory
        session_dir = tmp_path / "sessions"
        session_dir.mkdir()
        monkeypatch.setenv("HELEN_SESSION_DIR", str(session_dir))

        session_id = "test_session_123"
        # Lock file is at: session_dir / session_id / "session.lock"
        session_subdir = session_dir / session_id
        session_subdir.mkdir()
        lock_path = session_subdir / "session.lock"

        # Create a lock file with current process's PID
        current_pid = os.getpid()
        lock_path.write_text(str(current_pid))
        assert lock_path.exists()

        # Release the lock
        from helen.stdlib.transcript import release_session_lock
        result = release_session_lock(session_id)

        assert result["status"] == "ok"
        assert result["session_id"] == session_id
        # Lock file should be removed (holder PID matches current PID)
        assert not lock_path.exists()

    def test_release_nonexistent_lock(self, tmp_path, monkeypatch):
        """release_session_lock is safe when no lock exists."""
        session_dir = tmp_path / "sessions"
        session_dir.mkdir()
        monkeypatch.setenv("HELEN_SESSION_DIR", str(session_dir))

        session_id = "nonexistent_session"

        from helen.stdlib.transcript import release_session_lock
        result = release_session_lock(session_id)

        # Should succeed (no-op)
        assert result["status"] == "ok"

    def test_release_lock_empty_session_id(self):
        """release_session_lock returns error for empty session_id."""
        from helen.stdlib.transcript import release_session_lock
        result = release_session_lock("")

        assert result["status"] == "error"
        assert "session_id is required" in result["error"]

    def test_release_lock_other_process(self, tmp_path, monkeypatch):
        """release_session_lock does NOT remove lock held by another process."""
        session_dir = tmp_path / "sessions"
        session_dir.mkdir()
        monkeypatch.setenv("HELEN_SESSION_DIR", str(session_dir))

        session_id = "test_session_other"
        # Lock file is at: session_dir / session_id / "session.lock"
        session_subdir = session_dir / session_id
        session_subdir.mkdir()
        lock_path = session_subdir / "session.lock"

        # Create a lock file with a different PID
        # Use PID 1 (init) which is always running but not us
        lock_path.write_text("1")

        from helen.stdlib.transcript import release_session_lock
        result = release_session_lock(session_id)

        # Should succeed (no-op for other process's lock)
        assert result["status"] == "ok"
        # Lock file should NOT be removed (held by another process)
        assert lock_path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
