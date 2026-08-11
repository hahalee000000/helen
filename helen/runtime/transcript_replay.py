"""Transcript post-mortem replay for interactive debugging.

v1.40: Provides interactive replay of transcript sessions, allowing users
to step through messages, inspect agent state, and debug complex interactions.

Key Features:
- Load transcript from session directory
- Step through messages (next/prev/jump)
- Inspect scope at each message
- Display data flow (if available)
- CLI and REPL integration

Usage:
    from helen.runtime.transcript_replay import TranscriptReplay

    replay = TranscriptReplay(session_id="abc123")
    replay.next()  # Move to next message
    replay.prev()  # Move to previous message
    replay.jump(10)  # Jump to message 10
    print(replay.current_scope())  # Inspect current scope
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from helen.runtime.transcript_store import TranscriptStore, JSONLBackend, SQLiteBackend


class TranscriptReplay:
    """Interactive transcript replay for debugging.

    Loads a transcript session and provides navigation and inspection
    capabilities for post-mortem debugging.
    """

    def __init__(self, session_id: str, session_dir: str | Path | None = None):
        """Initialize transcript replay.

        Args:
            session_id: Session ID to replay
            session_dir: Optional session directory (defaults to ~/.helen/sessions)
        """
        self.session_id = session_id

        # Determine session directory
        if session_dir is None:
            from helen.runtime.config import get_session_dir
            session_dir = get_session_dir()
        self.session_dir = Path(session_dir)

        # Load transcript
        self.store = self._load_transcript()
        self.messages = self.store.read_view()
        self.current_index = 0

    def _load_transcript(self) -> TranscriptStore:
        """Load transcript from session directory.

        Returns:
            TranscriptStore instance with loaded transcript

        Raises:
            FileNotFoundError: If session directory doesn't exist
            ValueError: If no transcript file found
        """
        session_path = self.session_dir / self.session_id
        if not session_path.exists():
            raise FileNotFoundError(f"Session directory not found: {session_path}")

        # Try SQLite first, then JSONL
        sqlite_path = session_path / "transcript.db"
        jsonl_path = session_path / "transcript.jsonl"

        if sqlite_path.exists():
            backend = SQLiteBackend(sqlite_path)
        elif jsonl_path.exists():
            backend = JSONLBackend(jsonl_path)
        else:
            raise ValueError(f"No transcript file found in {session_path}")

        return TranscriptStore.load_from_backend(backend)

    def __len__(self) -> int:
        """Return total number of messages."""
        return len(self.messages)

    @property
    def current_message(self) -> dict[str, Any] | None:
        """Get current message."""
        if 0 <= self.current_index < len(self.messages):
            return self.messages[self.current_index]
        return None

    def next(self) -> dict[str, Any] | None:
        """Move to next message.

        Returns:
            Next message dict, or None if at end
        """
        if self.current_index < len(self.messages) - 1:
            self.current_index += 1
        return self.current_message

    def prev(self) -> dict[str, Any] | None:
        """Move to previous message.

        Returns:
            Previous message dict, or None if at beginning
        """
        if self.current_index > 0:
            self.current_index -= 1
        return self.current_message

    def jump(self, index: int) -> dict[str, Any] | None:
        """Jump to specific message index.

        Args:
            index: Message index (0-based)

        Returns:
            Message dict at index, or None if out of range
        """
        if 0 <= index < len(self.messages):
            self.current_index = index
        return self.current_message

    def first(self) -> dict[str, Any] | None:
        """Jump to first message.

        Returns:
            First message dict
        """
        return self.jump(0)

    def last(self) -> dict[str, Any] | None:
        """Jump to last message.

        Returns:
            Last message dict
        """
        return self.jump(len(self.messages) - 1)

    def get_message_at(self, index: int) -> dict[str, Any] | None:
        """Get message at specific index without changing current position.

        Args:
            index: Message index (0-based)

        Returns:
            Message dict at index, or None if out of range
        """
        if 0 <= index < len(self.messages):
            return self.messages[index]
        return None

    def search(self, query: str, case_sensitive: bool = False) -> list[int]:
        """Search for messages containing query string.

        Args:
            query: Search string
            case_sensitive: Whether search is case-sensitive

        Returns:
            List of message indices containing the query
        """
        results = []
        search_query = query.lower() if not case_sensitive else query

        for i, msg in enumerate(self.messages):
            content = msg.content if hasattr(msg, 'content') else msg.get("content", "")
            if not case_sensitive:
                content = content.lower()
            if search_query in content:
                results.append(i)

        return results

    def get_summary(self) -> dict[str, Any]:
        """Get summary of the transcript.

        Returns:
            Dict with transcript statistics
        """
        from collections import Counter

        roles = Counter(
            msg.role if hasattr(msg, 'role') else msg.get("role", "unknown")
            for msg in self.messages
        )
        agents = Counter(
            msg.agent_name if hasattr(msg, 'agent_name') else msg.get("agent_name", "unknown")
            for msg in self.messages
            if (msg.agent_name if hasattr(msg, 'agent_name') else msg.get("agent_name"))
        )

        return {
            "session_id": self.session_id,
            "total_messages": len(self.messages),
            "roles": dict(roles),
            "agents": dict(agents),
            "current_index": self.current_index,
        }

    def format_message(self, msg: Any) -> str:
        """Format a message for display.

        Args:
            msg: Message object or dict

        Returns:
            Formatted string representation
        """
        role = msg.role if hasattr(msg, 'role') else msg.get("role", "unknown")
        agent = msg.agent_name if hasattr(msg, 'agent_name') else msg.get("agent_name", "")
        content = msg.content if hasattr(msg, 'content') else msg.get("content", "")
        uuid = msg.uuid if hasattr(msg, 'uuid') else msg.get("uuid", "")

        # Truncate long content
        if len(content) > 200:
            content = content[:200] + "..."

        agent_prefix = f"[{agent}] " if agent else ""
        return f"{agent_prefix}{role}: {content}"

    def print_current(self) -> None:
        """Print current message."""
        if self.current_message:
            print(f"[{self.current_index}/{len(self.messages)}] {self.format_message(self.current_message)}")
        else:
            print("No message at current position")

    def close(self) -> None:
        """Close the transcript store."""
        if self.store:
            self.store.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
