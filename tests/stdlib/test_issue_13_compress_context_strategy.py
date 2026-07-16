"""Test for issue #13: compress_context(strategy) should respect strategy parameter with TranscriptStore enabled."""
import pytest
from unittest.mock import Mock, MagicMock
from helen.stdlib.context import _compress_context, _set_interpreter_context
from helen.runtime.history import Message


class TestIssue13CompressContextStrategyRespected:
    """Test that compress_context(strategy) respects the strategy parameter when TranscriptStore is enabled."""

    def test_compress_context_summarize_forces_compression(self):
        """Test that 'summarize' strategy uses Layer 5 (auto_compact) for LLM semantic compression."""
        # Setup mock agent context with transcript store
        mock_agent_context = Mock()
        mock_transcript_store = Mock()
        mock_agent_context.transcript_store = mock_transcript_store
        mock_agent_context._record_compression_ssot = Mock()
        mock_agent_context.llm_client = None  # No LLM, will use structural fallback

        # Create real Message objects (not mocks) for graduated_compress
        # Need > keep_recent + 2 = 6 messages for compression to occur
        from helen.runtime.history import Message
        mock_messages = [
            Message(role="user", content="Hello " * 50, uuid="uuid-1"),
            Message(role="assistant", content="Hi there! " * 50, uuid="uuid-2"),
            Message(role="user", content="How are you? " * 50, uuid="uuid-3"),
            Message(role="assistant", content="I'm good! " * 50, uuid="uuid-4"),
            Message(role="user", content="What's up? " * 50, uuid="uuid-5"),
            Message(role="assistant", content="Not much " * 50, uuid="uuid-6"),
            Message(role="user", content="Anything new? " * 50, uuid="uuid-7"),
            Message(role="assistant", content="Just working " * 50, uuid="uuid-8"),
        ]
        mock_transcript_store.read_view.return_value = mock_messages

        # Mock history manager
        mock_history_manager = Mock()
        mock_history_manager.MAX_TOKENS = 131072

        # Set up the global context
        _set_interpreter_context([], mock_history_manager, mock_agent_context)

        # Call compress_context with "summarize" strategy
        result = _compress_context("summarize")

        # Verify the result - should compress to fewer messages
        assert result["status"] == "ok"
        assert result["strategy"] == "summarize"
        assert result["original_messages"] == 8
        # Should compress (Layer 5 keeps recent 4 messages + summary)
        assert result["compressed_messages"] < result["original_messages"]

        # Verify _record_compression_ssot was called (BoundaryMarker created)
        assert mock_agent_context._record_compression_ssot.called

    def test_compress_context_truncate_forces_compression(self):
        """Test that 'truncate' strategy uses Layer 4 (context_collapse) for truncation."""
        # Setup mock agent context with transcript store
        mock_agent_context = Mock()
        mock_transcript_store = Mock()
        mock_agent_context.transcript_store = mock_transcript_store
        mock_agent_context._record_compression_ssot = Mock()

        # Create real Message objects - need > CONTEXT_COLLAPSE_THRESHOLD (20) messages
        from helen.runtime.history import Message
        mock_messages = [
            Message(role="user" if i % 2 == 0 else "assistant",
                   content=f"Message {i} " * 50,
                   uuid=f"uuid-{i}")
            for i in range(25)  # 25 messages to trigger context_collapse
        ]
        mock_transcript_store.read_view.return_value = mock_messages

        # Mock history manager
        mock_history_manager = Mock()
        mock_history_manager.MAX_TOKENS = 131072

        # Set up the global context
        _set_interpreter_context([], mock_history_manager, mock_agent_context)

        # Call compress_context with "truncate" strategy
        result = _compress_context("truncate")

        # Verify the result
        assert result["status"] == "ok"
        assert result["strategy"] == "truncate"
        assert result["original_messages"] == 25
        # Layer 4 should compress
        assert result["compressed_messages"] < result["original_messages"]

        # Verify _record_compression_ssot was called
        assert mock_agent_context._record_compression_ssot.called

    def test_compress_context_auto_uses_thresholds(self):
        """Test that 'auto' strategy still uses graduated compression with thresholds."""
        # Setup mock agent context with transcript store
        mock_agent_context = Mock()
        mock_transcript_store = Mock()
        mock_agent_context.transcript_store = mock_transcript_store

        # Create mock messages (need more than 1 to avoid early return)
        mock_messages = [
            Mock(spec=Message, role="user", content="Hello", token_count=100, uuid="uuid-1"),
            Mock(spec=Message, role="assistant", content="Hi", token_count=100, uuid="uuid-2"),
        ]
        mock_transcript_store.read_view.return_value = mock_messages

        # Mock _compress_history to return the same messages (low usage, no compression)
        mock_agent_context._compress_history.return_value = mock_messages

        # Mock history manager (not used for "auto" in TranscriptStore path)
        mock_history_manager = Mock()

        # Set up the global context
        _set_interpreter_context([], mock_history_manager, mock_agent_context)

        # Call compress_context with "auto" strategy
        result = _compress_context("auto")

        # Verify the result
        assert result["status"] == "ok"
        assert result["strategy"] == "auto"

        # Verify _compress_history was called (not _summarize_compress or _truncate_compress)
        mock_agent_context._compress_history.assert_called_once()
        mock_history_manager._summarize_compress.assert_not_called()
        mock_history_manager._truncate_compress.assert_not_called()

    def test_compress_context_unknown_strategy_returns_error(self):
        """Test that unknown strategy returns error."""
        # Setup mock agent context with transcript store
        mock_agent_context = Mock()
        mock_transcript_store = Mock()
        mock_agent_context.transcript_store = mock_transcript_store

        # Create mock messages (need more than 1 to avoid early return)
        mock_messages = [
            Mock(spec=Message, role="user", content="Hello", token_count=100, uuid="uuid-1"),
            Mock(spec=Message, role="assistant", content="Hi", token_count=100, uuid="uuid-2"),
        ]
        mock_transcript_store.read_view.return_value = mock_messages

        # Mock history manager
        mock_history_manager = Mock()

        # Set up the global context
        _set_interpreter_context([], mock_history_manager, mock_agent_context)

        # Call compress_context with unknown strategy
        result = _compress_context("unknown_strategy")

        # Verify the result is an error
        assert result["status"] == "error"
        assert "Unknown compression strategy" in result["error"]
