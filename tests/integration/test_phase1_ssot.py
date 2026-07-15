"""Integration tests for Phase 1 SSOT implementation."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from helen.interpreter.agent_context import AgentContextManager
from helen.runtime.history import Message
from helen.runtime.session_manager import SessionManager
from helen.runtime.transcript_store import (
    BoundaryMarker,
    JSONLBackend,
    TranscriptStore,
)


class TestPhase1SSOT:
    """Integration tests for Phase 1 SSOT features."""

    def test_transcript_store_enabled_by_default(self, tmp_path):
        """Test that TranscriptStore is enabled by default."""
        # Create AgentContext with default settings
        ctx = AgentContextManager()

        # TranscriptStore should be enabled
        assert ctx.transcript_store is not None
        assert ctx.session_id is not None

    def test_transcript_store_can_be_disabled(self):
        """Test that TranscriptStore can be disabled."""
        ctx = AgentContextManager(transcript_store_enabled=False)

        assert ctx.transcript_store is None
        assert ctx.session_id is None

    def test_agent_context_creates_session(self, tmp_path):
        """Test that AgentContext creates a session automatically."""
        # Override session directory
        import helen.runtime.config as config_module
        original_get_config = config_module.get_transcript_config

        def mock_config():
            return {
                "enabled": True,
                "backend": "jsonl",
                "session_dir": str(tmp_path),
                "session_scope": "global",  # v1.20: explicit global scope
                "project_session_dir": ".helen/sessions",
                "max_memory_items": 1000,
            }

        config_module.get_transcript_config = mock_config

        try:
            ctx = AgentContextManager()

            assert ctx.session_id is not None
            assert ctx.transcript_store is not None

            # Verify session directory was created
            session_dir = tmp_path / ctx.session_id
            assert session_dir.exists()

            # Append a message to trigger file creation
            msg = Message(role="user", content="Test")
            ctx.transcript_store.append(msg)
            ctx.transcript_store.close()

            # Verify transcript file exists after write
            transcript_path = session_dir / "transcript.jsonl"
            assert transcript_path.exists()
        finally:
            config_module.get_transcript_config = original_get_config

    def test_messages_are_persisted(self, tmp_path):
        """Test that messages are persisted to disk."""
        import helen.runtime.config as config_module
        original_get_config = config_module.get_transcript_config

        def mock_config():
            return {
                "enabled": True,
                "backend": "jsonl",
                "session_dir": str(tmp_path),
                "session_scope": "global",  # v1.20: explicit global scope
                "project_session_dir": ".helen/sessions",
                "max_memory_items": 1000,
            }

        config_module.get_transcript_config = mock_config

        try:
            ctx = AgentContextManager()
            store = ctx.transcript_store

            # Append messages
            msg1 = Message(role="user", content="Hello")
            msg2 = Message(role="assistant", content="Hi there")

            store.append(msg1)
            store.append(msg2)

            # Close to flush
            store.close()

            # Verify transcript file has content
            transcript_path = tmp_path / ctx.session_id / "transcript.jsonl"
            assert transcript_path.exists()

            content = transcript_path.read_text(encoding="utf-8")
            lines = content.strip().split("\n")
            assert len(lines) == 2
        finally:
            config_module.get_transcript_config = original_get_config

    def test_compression_is_recorded(self, tmp_path):
        """Test that compression events are recorded in transcript."""
        import helen.runtime.config as config_module
        original_get_config = config_module.get_transcript_config

        def mock_config():
            return {
                "enabled": True,
                "backend": "jsonl",
                "session_dir": str(tmp_path),
                "session_scope": "global",  # v1.20: explicit global scope
                "project_session_dir": ".helen/sessions",
                "max_memory_items": 1000,
            }

        config_module.get_transcript_config = mock_config

        try:
            ctx = AgentContextManager()
            store = ctx.transcript_store

            # Append messages
            msg1 = Message(role="user", content="Message 1")
            msg2 = Message(role="assistant", content="Message 2")
            msg3 = Message(role="user", content="Message 3")

            store.append(msg1)
            store.append(msg2)
            store.append(msg3)

            # Record compression
            marker = store.record_compression(
                head_uuid=msg1.uuid,
                tail_uuid=msg2.uuid,
                anchor_uuid=msg3.uuid,
                summary="Compressed",
                layer="test",
            )

            # Verify boundary marker was added
            assert store.get_boundary_count() == 1
            audit = store.get_compression_audit()
            assert len(audit) == 1
            assert audit[0]["uuid"] == marker.uuid

            # Close to flush
            store.close()

            # Verify transcript file has all items
            transcript_path = tmp_path / ctx.session_id / "transcript.jsonl"
            content = transcript_path.read_text(encoding="utf-8")
            lines = content.strip().split("\n")
            assert len(lines) == 4  # 3 messages + 1 boundary marker
        finally:
            config_module.get_transcript_config = original_get_config

    def test_view_cache_works(self):
        """Test that view caching works correctly."""
        store = TranscriptStore()

        # Append messages
        msg1 = Message(role="user", content="Hello")
        msg2 = Message(role="assistant", content="Hi")

        store.append(msg1)

        # Get view (caches it)
        view1 = store.read_view()
        assert len(view1) == 1
        assert store._dirty is False

        # Append another message (invalidates cache)
        store.append(msg2)
        assert store._dirty is True

        # Get view again (recomputes and caches)
        view2 = store.read_view()
        assert len(view2) == 2
        assert store._dirty is False

        # Third call should use cache
        view3 = store.read_view()
        assert view3 == view2
        assert store._dirty is False

    def test_session_manager_integration(self, tmp_path):
        """Test SessionManager integration with TranscriptStore."""
        manager = SessionManager(base_dir=tmp_path)

        # Create a session
        session_id = manager.create_session()
        transcript_path = manager.get_session_path(session_id)

        # Create a store with the session's backend
        backend = JSONLBackend(transcript_path)
        store = TranscriptStore(backend=backend)

        # Append messages
        msg1 = Message(role="user", content="Hello")
        msg2 = Message(role="assistant", content="Hi")

        store.append(msg1)
        store.append(msg2)
        store.close()

        # Verify session is listed
        sessions = manager.list_sessions()
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == session_id

        # Load the session back
        backend2 = JSONLBackend(transcript_path)
        store2 = TranscriptStore.load_from_backend(backend2)

        assert store2.get_message_count() == 2
        view = store2.read_view()
        assert len(view) == 2
        assert view[0].content == "Hello"
        assert view[1].content == "Hi"

        store2.close()

    def test_backward_compatibility_without_backend(self):
        """Test that TranscriptStore works without backend (backward compat)."""
        store = TranscriptStore()  # No backend

        msg1 = Message(role="user", content="Hello")
        msg2 = Message(role="assistant", content="Hi")

        store.append(msg1)
        store.append(msg2)

        assert store.get_message_count() == 2
        view = store.read_view()
        assert len(view) == 2

    def test_multiple_compression_boundaries(self):
        """Test multiple compression boundaries in transcript."""
        store = TranscriptStore()

        # Create message sequence
        messages = []
        for i in range(10):
            msg = Message(role="user" if i % 2 == 0 else "assistant", content=f"Message {i}")
            store.append(msg)
            messages.append(msg)

        # Record multiple compressions
        store.record_compression(
            head_uuid=messages[0].uuid,
            tail_uuid=messages[1].uuid,
            anchor_uuid=messages[2].uuid,
            summary="First compression",
            layer="layer1",
        )

        store.record_compression(
            head_uuid=messages[3].uuid,
            tail_uuid=messages[4].uuid,
            anchor_uuid=messages[5].uuid,
            summary="Second compression",
            layer="layer2",
        )

        # Verify audit trail
        audit = store.get_compression_audit()
        assert len(audit) == 2
        assert audit[0]["summary"] == "First compression"
        assert audit[1]["summary"] == "Second compression"

        # Verify view excludes compressed messages
        view = store.read_view()
        # Should have 10 messages - 4 compressed + 2 summary messages = 8
        assert len(view) == 8

        # Verify boundaries
        assert store.get_boundary_count() == 2
        assert store.get_message_count() == 10  # Original messages still counted
