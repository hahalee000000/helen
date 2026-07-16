"""Behavior-driven tests for clear_context() — verify actual effects.

These tests verify that clear_context() actually clears the context,
not just that it returns a success status. This catches bugs like
empty UUIDs in BoundaryMarker that make read_view() return unchanged.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from helen.interpreter.agent_context import AgentContextManager
from helen.runtime.history import Message
from helen.runtime.transcript_store import TranscriptStore, JSONLBackend, BoundaryMarker


@pytest.fixture
def agent_context():
    """Create a real AgentContextManager with TranscriptStore."""
    import tempfile
    import os

    # Create temp file for backend
    temp_file = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
    temp_file.close()

    try:
        backend = JSONLBackend(temp_file.name)
        store = TranscriptStore(backend=backend, max_memory_items=1000)

        agent_ctx = AgentContextManager.__new__(AgentContextManager)
        agent_ctx._transcript_store = store
        agent_ctx.working_memory_enabled = True
        agent_ctx._last_usage_ratio = 0.5
        agent_ctx._last_cache_stats = {"test": 1}

        # Initialize working memory
        from helen.runtime.working_memory import WorkingMemory
        agent_ctx.working_memory = WorkingMemory()

        yield agent_ctx
    finally:
        os.unlink(temp_file.name)


class TestClearContextBehavior:
    """Behavior-driven tests for clear_context()."""

    def test_clear_context_actually_clears_view(self, agent_context):
        """clear_context() must make read_view() return empty list."""
        # Add messages
        messages = [
            Message(role="user", content="Hello", uuid="uuid-1"),
            Message(role="assistant", content="Hi!", uuid="uuid-2"),
            Message(role="user", content="How are you?", uuid="uuid-3"),
        ]
        for msg in messages:
            agent_context._transcript_store.append(msg)

        # Verify initial state
        assert len(agent_context._transcript_store.read_view()) == 3

        # Clear context
        result = agent_context.clear_context()

        # CRITICAL: Verify actual behavior
        view = agent_context._transcript_store.read_view()
        assert len(view) == 0, f"Expected empty view, got {len(view)} messages"

    def test_clear_context_new_messages_visible(self, agent_context):
        """Messages added after clear_context() must appear in read_view()."""
        # Add and clear
        agent_context._transcript_store.append(
            Message(role="user", content="Old message", uuid="uuid-old")
        )
        agent_context.clear_context()

        # Add new message
        agent_context._transcript_store.append(
            Message(role="user", content="New message", uuid="uuid-new")
        )

        # Verify only new message is visible
        view = agent_context._transcript_store.read_view()
        assert len(view) == 1
        assert view[0].content == "New message"

    def test_clear_context_boundary_marker_covers_all(self, agent_context):
        """BoundaryMarker must cover all messages before clearing."""
        # Add messages
        messages = [
            Message(role="user", content="Msg 1", uuid="uuid-1"),
            Message(role="assistant", content="Msg 2", uuid="uuid-2"),
            Message(role="user", content="Msg 3", uuid="uuid-3"),
        ]
        for msg in messages:
            agent_context._transcript_store.append(msg)

        # Clear
        agent_context.clear_context()

        # Find BoundaryMarker
        markers = [item for item in agent_context._transcript_store.transcript
                   if isinstance(item, BoundaryMarker)]
        assert len(markers) == 1

        marker = markers[0]
        # CRITICAL: UUIDs must not be empty
        assert marker.head_uuid != "", "head_uuid must not be empty"
        assert marker.tail_uuid != "", "tail_uuid must not be empty"
        assert marker.head_uuid == "uuid-1"
        assert marker.tail_uuid == "uuid-3"

    def test_clear_context_resets_compression_state(self, agent_context):
        """clear_context() must reset compression state."""
        agent_context._last_usage_ratio = 0.95
        agent_context._last_cache_stats = {"hit": 10, "miss": 5}

        agent_context.clear_context()

        assert agent_context._last_usage_ratio == 0.0
        assert agent_context._last_cache_stats is None

    def test_clear_context_clears_working_memory(self, agent_context):
        """clear_context() must clear working memory."""
        agent_ctx = agent_context
        agent_ctx.working_memory.task_description = "Test task"
        agent_ctx.working_memory.active_files.append("test.py")

        agent_ctx.clear_context()

        assert agent_ctx.working_memory.task_description == ""
        assert len(agent_ctx.working_memory.active_files) == 0

    def test_clear_context_empty_transcript(self, agent_context):
        """clear_context() on empty transcript should succeed."""
        result = agent_context.clear_context()

        assert result["status"] == "ok"
        assert result["cleared_message_count"] == 0

        # Should still be able to add messages after
        agent_context._transcript_store.append(
            Message(role="user", content="First message", uuid="uuid-first")
        )
        view = agent_context._transcript_store.read_view()
        assert len(view) == 1

    def test_clear_context_returns_cleared_count(self, agent_context):
        """clear_context() must return the number of cleared messages."""
        # Add 5 messages
        for i in range(5):
            agent_context._transcript_store.append(
                Message(role="user" if i % 2 == 0 else "assistant",
                       content=f"Message {i}", uuid=f"uuid-{i}")
            )

        result = agent_context.clear_context()

        assert result["status"] == "ok"
        assert result["cleared_message_count"] == 5

    def test_clear_context_multiple_times(self, agent_context):
        """Multiple clear_context() calls should be safe."""
        # Add and clear multiple times
        for i in range(3):
            agent_context._transcript_store.append(
                Message(role="user", content=f"Round {i}", uuid=f"uuid-{i}")
            )
            agent_context.clear_context()
            assert len(agent_context._transcript_store.read_view()) == 0

        # Final clear should still work
        result = agent_context.clear_context()
        assert result["status"] == "ok"

    def test_clear_context_preserves_transcript_history(self, agent_context):
        """clear_context() should not delete from transcript, just mark as cleared."""
        # Add messages
        for i in range(3):
            agent_context._transcript_store.append(
                Message(role="user", content=f"Message {i}", uuid=f"uuid-{i}")
            )

        initial_transcript_len = len(agent_context._transcript_store.transcript)

        # Clear
        agent_context.clear_context()

        # Transcript should have BoundaryMarker, not fewer messages
        assert len(agent_context._transcript_store.transcript) == initial_transcript_len + 1

        # But view should be empty
        assert len(agent_context._transcript_store.read_view()) == 0


class TestClearContextEdgeCases:
    """Edge case tests for clear_context()."""

    def test_clear_context_single_message(self, agent_context):
        """clear_context() with single message should work."""
        agent_context._transcript_store.append(
            Message(role="user", content="Only message", uuid="uuid-only")
        )

        result = agent_context.clear_context()

        assert result["status"] == "ok"
        assert result["cleared_message_count"] == 1
        assert len(agent_context._transcript_store.read_view()) == 0

    def test_clear_context_many_messages(self, agent_context):
        """clear_context() with many messages should work."""
        # Add 100 messages
        for i in range(100):
            agent_context._transcript_store.append(
                Message(role="user" if i % 2 == 0 else "assistant",
                       content=f"Message {i}", uuid=f"uuid-{i}")
            )

        result = agent_context.clear_context()

        assert result["status"] == "ok"
        assert result["cleared_message_count"] == 100
        assert len(agent_context._transcript_store.read_view()) == 0

    def test_clear_context_mixed_message_types(self, agent_context):
        """clear_context() with mixed message types should work."""
        messages = [
            Message(role="system", content="System prompt", uuid="uuid-sys"),
            Message(role="user", content="User message", uuid="uuid-user"),
            Message(role="assistant", content="Assistant reply", uuid="uuid-asst"),
            Message(role="tool", content="Tool result", uuid="uuid-tool",
                   tool_call_id="call-123"),
        ]
        for msg in messages:
            agent_context._transcript_store.append(msg)

        result = agent_context.clear_context()

        assert result["status"] == "ok"
        assert result["cleared_message_count"] == 4
        assert len(agent_context._transcript_store.read_view()) == 0
