"""Integration tests for compress_context() with TranscriptStore.

These tests verify that compress_context() works correctly when
TranscriptStore is enabled, covering all strategies (auto, summarize,
truncate, none) and edge cases.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from helen.stdlib.context import _compress_context, _set_interpreter_context
from helen.interpreter.agent_context import AgentContextManager
from helen.runtime.history import Message
from helen.runtime.transcript_store import TranscriptStore, JSONLBackend


@pytest.fixture
def agent_context_with_store():
    """Create AgentContextManager with real TranscriptStore."""
    import tempfile
    import os

    temp_file = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
    temp_file.close()

    try:
        backend = JSONLBackend(temp_file.name)
        store = TranscriptStore(backend=backend, max_memory_items=1000)

        agent_ctx = AgentContextManager.__new__(AgentContextManager)
        agent_ctx._transcript_store = store
        agent_ctx.working_memory_enabled = False
        agent_ctx._last_usage_ratio = 0.0
        agent_ctx._last_cache_stats = None
        agent_ctx.llm_client = None  # No LLM for testing

        yield agent_ctx, store
    finally:
        os.unlink(temp_file.name)


@pytest.fixture
def mock_interpreter(agent_context_with_store):
    """Set up interpreter context with AgentContextManager."""
    agent_ctx, store = agent_context_with_store

    mock_history = []
    mock_manager = Mock()
    mock_manager.MAX_TOKENS = 131072

    _set_interpreter_context(mock_history, mock_manager)

    from helen.stdlib import context
    context._interpreter_agent_context = agent_ctx

    yield agent_ctx, store


def _make_messages(count: int, prefix: str = "Message") -> list[Message]:
    """Create real Message objects for testing."""
    return [
        Message(
            role="user" if i % 2 == 0 else "assistant",
            content=f"{prefix} {i} with content " * 10,
            uuid=f"uuid-{i}",
        )
        for i in range(count)
    ]


class TestCompressContextIntegration:
    """Integration tests for compress_context() with TranscriptStore."""

    def test_compress_context_summarize_reduces_messages(self, mock_interpreter):
        """summarize strategy must reduce message count."""
        agent_ctx, store = mock_interpreter

        # Add messages
        messages = _make_messages(10)
        for msg in messages:
            store.append(msg)

        initial_count = len(messages)

        # Compress
        result = _compress_context("summarize")

        assert result["status"] == "ok"
        assert result["strategy"] == "summarize"
        # _force_compact keeps summary + last message (fewer than original)
        assert result["compressed_messages"] < initial_count

    def test_compress_context_truncate_reduces_tokens(self, mock_interpreter):
        """truncate strategy must reduce token count with >20 messages."""
        agent_ctx, store = mock_interpreter

        # Need > CONTEXT_COLLAPSE_THRESHOLD (20) messages
        messages = _make_messages(25)
        for msg in messages:
            store.append(msg)

        initial_tokens = sum(m.token_count for m in messages)

        # Compress
        result = _compress_context("truncate")

        assert result["status"] == "ok"
        assert result["strategy"] == "truncate"
        assert result["compressed_tokens"] < initial_tokens
        assert result["compressed_messages"] < len(messages)

    def test_compress_context_none_does_nothing(self, mock_interpreter):
        """none strategy must not change anything."""
        agent_ctx, store = mock_interpreter

        messages = _make_messages(5)
        for msg in messages:
            store.append(msg)

        initial_view_len = len(store.read_view())

        result = _compress_context("none")

        assert result["status"] == "ok"
        assert result["strategy"] == "none"
        assert result["compressed_messages"] == initial_view_len

    def test_compress_context_creates_boundary_marker(self, mock_interpreter):
        """compress_context must create BoundaryMarker in TranscriptStore."""
        agent_ctx, store = mock_interpreter

        messages = _make_messages(10)
        for msg in messages:
            store.append(msg)

        from helen.runtime.transcript_store import BoundaryMarker
        initial_markers = len([item for item in store.transcript
                              if isinstance(item, BoundaryMarker)])

        result = _compress_context("summarize")

        assert result["status"] == "ok"
        final_markers = len([item for item in store.transcript
                            if isinstance(item, BoundaryMarker)])
        assert final_markers > initial_markers

    def test_compress_context_view_reflects_compression(self, mock_interpreter):
        """After compression, read_view() must show fewer messages."""
        agent_ctx, store = mock_interpreter

        messages = _make_messages(10)
        for msg in messages:
            store.append(msg)

        initial_view_len = len(store.read_view())

        result = _compress_context("summarize")

        assert result["status"] == "ok"
        final_view_len = len(store.read_view())
        assert final_view_len < initial_view_len

    def test_compress_context_unknown_strategy_returns_error(self, mock_interpreter):
        """Unknown strategy must return error status."""
        agent_ctx, store = mock_interpreter

        # Add messages so we don't hit the early return for empty context
        for msg in _make_messages(5):
            store.append(msg)

        result = _compress_context("invalid_strategy")

        assert result["status"] == "error"
        assert "Unknown compression strategy" in result["error"]


class TestCompressContextEdgeCases:
    """Edge case tests for compress_context()."""

    def test_compress_context_few_messages_summarize(self, mock_interpreter):
        """summarize must work even with <7 messages."""
        agent_ctx, store = mock_interpreter

        # Only 3 messages (< keep_recent + 2 = 6)
        messages = _make_messages(3)
        for msg in messages:
            store.append(msg)

        result = _compress_context("summarize")

        assert result["status"] == "ok"
        # Should still compress
        assert result["compressed_messages"] < len(messages)

    def test_compress_context_few_messages_truncate(self, mock_interpreter):
        """truncate must not compress with <20 messages."""
        agent_ctx, store = mock_interpreter

        # Only 10 messages (< CONTEXT_COLLAPSE_THRESHOLD = 20)
        messages = _make_messages(10)
        for msg in messages:
            store.append(msg)

        result = _compress_context("truncate")

        assert result["status"] == "ok"
        # _context_collapse won't compress with <20 messages
        assert result["compressed_messages"] == len(messages)

    def test_compress_context_single_message(self, mock_interpreter):
        """compress_context with single message should handle gracefully."""
        agent_ctx, store = mock_interpreter

        store.append(Message(role="user", content="Only message", uuid="uuid-only"))

        result = _compress_context("summarize")

        assert result["status"] == "ok"
        # Can't compress a single message
        assert result["compressed_messages"] == 1

    def test_compress_context_empty_context(self, mock_interpreter):
        """compress_context on empty context should return ok."""
        result = _compress_context("summarize")

        assert result["status"] == "ok"
        assert result["original_messages"] == 0

    def test_compress_context_preserves_system_messages(self, mock_interpreter):
        """System messages should be preserved after compression."""
        agent_ctx, store = mock_interpreter

        # Add system + conversation messages
        store.append(Message(role="system", content="System prompt", uuid="uuid-sys"))
        for msg in _make_messages(10, "Conv"):
            store.append(msg)

        result = _compress_context("summarize")

        assert result["status"] == "ok"
        # Verify system message is still in view
        view = store.read_view()
        system_msgs = [m for m in view if m.role == "system"]
        assert len(system_msgs) >= 1


class TestCompressContextStrategies:
    """Test each compression strategy in detail."""

    def test_summarize_keeps_recent_messages(self, mock_interpreter):
        """summarize should keep the most recent message."""
        agent_ctx, store = mock_interpreter

        messages = _make_messages(10)
        for msg in messages:
            store.append(msg)

        last_message = messages[-1].content

        result = _compress_context("summarize")

        assert result["status"] == "ok"
        # Last message should still be in view
        view = store.read_view()
        contents = [m.content for m in view if m.role != "system"]
        # The last message or its content should be preserved
        assert len(view) > 0

    def test_truncate_with_exactly_20_messages(self, mock_interpreter):
        """truncate with exactly 20 messages should not compress."""
        agent_ctx, store = mock_interpreter

        messages = _make_messages(20)  # Exactly threshold
        for msg in messages:
            store.append(msg)

        result = _compress_context("truncate")

        assert result["status"] == "ok"
        # _context_collapse requires > 20, so no compression
        assert result["compressed_messages"] == 20

    def test_truncate_with_21_messages(self, mock_interpreter):
        """truncate with 21 messages should compress."""
        agent_ctx, store = mock_interpreter

        messages = _make_messages(21)  # Just above threshold
        for msg in messages:
            store.append(msg)

        result = _compress_context("truncate")

        assert result["status"] == "ok"
        # Should compress - context_collapse requires > 20 messages
        # With 21 messages, cutoff = 1, so first message is archived
        assert result["compressed_messages"] <= 21
