"""Tests for transcript replay functionality (Phase 6).

Tests the TranscriptReplay class and related functionality.
"""

import pytest
import tempfile
import json
from pathlib import Path
from helen.runtime.transcript_replay import TranscriptReplay
from helen.runtime.transcript_store import TranscriptStore, JSONLBackend


class TestTranscriptReplay:
    """Test TranscriptReplay class."""

    def _create_test_session(self, session_dir: Path, session_id: str, num_messages: int = 5):
        """Helper to create a test session with messages."""
        session_path = session_dir / session_id
        session_path.mkdir(parents=True, exist_ok=True)

        # Create transcript
        backend = JSONLBackend(session_path / "transcript.jsonl")
        store = TranscriptStore(backend=backend)

        for i in range(num_messages):
            role = "user" if i % 2 == 0 else "assistant"
            content = f"Message {i}"
            msg_dict = {
                "role": role,
                "content": content,
                "uuid": f"msg_{i:03d}",
            }
            if role == "assistant":
                msg_dict["agent_name"] = f"Agent{i % 2}"

            # Write directly to backend
            from helen.runtime.history import Message
            msg = Message(role=role, content=content)
            msg.uuid = msg_dict["uuid"]
            if "agent_name" in msg_dict:
                msg.agent_name = msg_dict["agent_name"]
            store.append(msg, persist=True)

        store.close()
        return session_path

    def test_load_transcript(self):
        """Test loading a transcript session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_dir = Path(tmpdir)
            self._create_test_session(session_dir, "test_session", 5)

            replay = TranscriptReplay("test_session", session_dir)
            assert len(replay) == 5
            assert replay.current_index == 0
            replay.close()

    def test_navigation(self):
        """Test navigation through transcript."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_dir = Path(tmpdir)
            self._create_test_session(session_dir, "test_session", 5)

            with TranscriptReplay("test_session", session_dir) as replay:
                # Test next
                assert replay.current_index == 0
                replay.next()
                assert replay.current_index == 1
                replay.next()
                assert replay.current_index == 2

                # Test prev
                replay.prev()
                assert replay.current_index == 1

                # Test jump
                replay.jump(4)
                assert replay.current_index == 4

                # Test first/last
                replay.first()
                assert replay.current_index == 0
                replay.last()
                assert replay.current_index == 4

    def test_navigation_boundaries(self):
        """Test navigation at boundaries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_dir = Path(tmpdir)
            self._create_test_session(session_dir, "test_session", 3)

            with TranscriptReplay("test_session", session_dir) as replay:
                # At beginning, prev should not crash
                replay.prev()
                assert replay.current_index == 0

                # At end, next should not crash
                replay.last()
                replay.next()
                assert replay.current_index == 2

    def test_search(self):
        """Test searching transcript."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_dir = Path(tmpdir)
            self._create_test_session(session_dir, "test_session", 10)

            with TranscriptReplay("test_session", session_dir) as replay:
                # Search for "Message 5"
                results = replay.search("Message 5")
                assert len(results) == 1
                assert results[0] == 5

                # Search for "Message" (should match all)
                results = replay.search("Message")
                assert len(results) == 10

                # Search for non-existent
                results = replay.search("nonexistent")
                assert len(results) == 0

    def test_search_case_sensitive(self):
        """Test case-sensitive search."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_dir = Path(tmpdir)
            self._create_test_session(session_dir, "test_session", 5)

            with TranscriptReplay("test_session", session_dir) as replay:
                # Case-insensitive (default)
                results = replay.search("message")
                assert len(results) == 5

                # Case-sensitive
                results = replay.search("message", case_sensitive=True)
                assert len(results) == 0

                results = replay.search("Message", case_sensitive=True)
                assert len(results) == 5

    def test_get_summary(self):
        """Test getting transcript summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_dir = Path(tmpdir)
            self._create_test_session(session_dir, "test_session", 10)

            with TranscriptReplay("test_session", session_dir) as replay:
                summary = replay.get_summary()
                assert summary["session_id"] == "test_session"
                assert summary["total_messages"] == 10
                assert "user" in summary["roles"]
                assert "assistant" in summary["roles"]
                assert summary["current_index"] == 0

    def test_get_message_at(self):
        """Test getting message at specific index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_dir = Path(tmpdir)
            self._create_test_session(session_dir, "test_session", 5)

            with TranscriptReplay("test_session", session_dir) as replay:
                # Get message without changing position
                assert replay.current_index == 0
                msg = replay.get_message_at(2)
                assert msg is not None
                assert replay.current_index == 0  # Position unchanged

                # Out of range
                msg = replay.get_message_at(10)
                assert msg is None

    def test_format_message(self):
        """Test message formatting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_dir = Path(tmpdir)
            self._create_test_session(session_dir, "test_session", 5)

            with TranscriptReplay("test_session", session_dir) as replay:
                msg = replay.current_message
                formatted = replay.format_message(msg)
                assert "user" in formatted or "assistant" in formatted
                assert "Message 0" in formatted

    def test_context_manager(self):
        """Test using replay as context manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_dir = Path(tmpdir)
            self._create_test_session(session_dir, "test_session", 5)

            # Should not raise
            with TranscriptReplay("test_session", session_dir) as replay:
                assert len(replay) == 5

    def test_session_not_found(self):
        """Test error when session not found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_dir = Path(tmpdir)

            with pytest.raises(FileNotFoundError):
                TranscriptReplay("nonexistent_session", session_dir)

    def test_current_message(self):
        """Test current_message property."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_dir = Path(tmpdir)
            self._create_test_session(session_dir, "test_session", 5)

            with TranscriptReplay("test_session", session_dir) as replay:
                msg = replay.current_message
                assert msg is not None
                # Message objects have attributes, not dict keys
                assert hasattr(msg, 'role')
                assert hasattr(msg, 'content')
