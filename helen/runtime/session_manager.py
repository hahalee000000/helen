"""Session manager for Helen transcript persistence.

Manages transcript sessions and their lifecycle:
- Creating new sessions with unique IDs
- Listing existing sessions
- Getting session paths for transcript storage
- Session cleanup and deletion

Sessions are stored in ~/.helen/sessions/<session_id>/transcript.jsonl
"""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from helen.runtime.config import HELEN_HOME

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages transcript sessions and persistence.

    Each session has:
    - A unique session_id (e.g., "session_1720435200_a1b2c3d4")
    - A directory under ~/.helen/sessions/<session_id>/
    - A transcript.jsonl file containing the message log

    Attributes:
        base_dir: Base directory for all sessions (~/.helen/sessions)
    """

    def __init__(self, base_dir: Path | None = None):
        """Initialize session manager.

        Args:
            base_dir: Base directory for sessions. Defaults to ~/.helen/sessions
        """
        if base_dir is None:
            self.base_dir = HELEN_HOME / "sessions"
        else:
            self.base_dir = Path(base_dir)

        # Ensure base directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_session(self, session_id: str | None = None) -> str:
        """Create a new transcript session.

        Args:
            session_id: Optional custom session ID. If None, generates one.

        Returns:
            The session_id for the created session.

        Example:
            manager = SessionManager()
            session_id = manager.create_session()
            # Returns: "session_1720435200_a1b2c3d4"
        """
        if session_id is None:
            # Generate session ID: timestamp + short UUID
            timestamp = int(time.time())
            short_uuid = uuid4().hex[:8]
            session_id = f"session_{timestamp}_{short_uuid}"

        # Create session directory
        session_dir = self.base_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        logger.debug("Created session: %s", session_id)
        return session_id

    def get_session_path(self, session_id: str) -> Path:
        """Get transcript file path for a session.

        Args:
            session_id: Session identifier

        Returns:
            Path to transcript.jsonl file

        Example:
            path = manager.get_session_path("session_1720435200_a1b2c3d4")
            # Returns: ~/.helen/sessions/session_1720435200_a1b2c3d4/transcript.jsonl
        """
        return self.base_dir / session_id / "transcript.jsonl"

    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists.

        Args:
            session_id: Session identifier

        Returns:
            True if session directory and transcript file exist
        """
        session_dir = self.base_dir / session_id
        transcript_path = session_dir / "transcript.jsonl"
        return session_dir.exists() and transcript_path.exists()

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all sessions with metadata.

        Returns:
            List of dicts with session metadata, sorted by modification time (newest first).
            Each dict contains:
            - session_id: Session identifier
            - created_at: Creation timestamp (Unix epoch)
            - modified_at: Last modification timestamp (Unix epoch)
            - size_bytes: Transcript file size in bytes
            - message_count: Number of messages (if available)

        Example:
            sessions = manager.list_sessions()
            for session in sessions:
                print(f"{session['session_id']}: {session['size_bytes']} bytes")
        """
        sessions = []

        if not self.base_dir.exists():
            return sessions

        for session_dir in self.base_dir.iterdir():
            if not session_dir.is_dir():
                continue

            transcript_path = session_dir / "transcript.jsonl"
            if not transcript_path.exists():
                continue

            try:
                stat = transcript_path.stat()

                # Count messages (quick estimate by counting lines)
                message_count = 0
                try:
                    with open(transcript_path, encoding="utf-8") as f:
                        message_count = sum(1 for _ in f)
                except Exception:
                    pass  # Ignore read errors

                sessions.append({
                    "session_id": session_dir.name,
                    "created_at": stat.st_ctime,
                    "modified_at": stat.st_mtime,
                    "size_bytes": stat.st_size,
                    "message_count": message_count,
                })
            except OSError as e:
                logger.warning("Failed to read session %s: %s", session_dir.name, e)

        # Sort by modification time (newest first)
        return sorted(sessions, key=lambda s: s["modified_at"], reverse=True)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its transcript.

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted, False if it didn't exist

        Example:
            success = manager.delete_session("session_1720435200_a1b2c3d4")
        """
        session_dir = self.base_dir / session_id

        if not session_dir.exists():
            logger.warning("Session does not exist: %s", session_id)
            return False

        try:
            shutil.rmtree(session_dir)
            logger.debug("Deleted session: %s", session_id)
            return True
        except OSError as e:
            logger.error("Failed to delete session %s: %s", session_id, e)
            return False

    def get_session_dir(self, session_id: str) -> Path:
        """Get session directory path.

        Args:
            session_id: Session identifier

        Returns:
            Path to session directory
        """
        return self.base_dir / session_id

    def cleanup_old_sessions(self, keep_count: int = 100) -> int:
        """Clean up old sessions, keeping only the most recent N.

        Args:
            keep_count: Number of recent sessions to keep (default: 100)

        Returns:
            Number of sessions deleted

        Example:
            deleted = manager.cleanup_old_sessions(keep_count=50)
            print(f"Deleted {deleted} old sessions")
        """
        sessions = self.list_sessions()

        if len(sessions) <= keep_count:
            return 0

        # Sessions are already sorted by modified_at (newest first)
        to_delete = sessions[keep_count:]
        deleted_count = 0

        for session in to_delete:
            if self.delete_session(session["session_id"]):
                deleted_count += 1

        logger.debug("Cleaned up %d old sessions", deleted_count)
        return deleted_count
