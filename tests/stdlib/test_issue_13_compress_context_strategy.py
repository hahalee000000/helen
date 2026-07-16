"""Test for issue #13: compress_context(strategy) should respect strategy parameter with TranscriptStore enabled."""
import pytest
from unittest.mock import Mock, MagicMock
from helen.stdlib.context import _compress_context, _set_interpreter_context
from helen.runtime.history import Message


class TestIssue13CompressContextStrategyRespected:
    """Test that compress_context(strategy) respects the strategy parameter when TranscriptStore is enabled."""

    def test_compress_context_summarize_forces_compression(self):
        """Test that 'summarize' strategy forces LLM semantic compression even with low usage ratio."""
        # Setup mock agent context with transcript store
        mock_agent_context = Mock()
        mock_transcript_store = Mock()
        mock_agent_context.transcript_store = mock_transcript_store
        mock_agent_context._record_compression_ssot = Mock()

        # Create mock messages with low token count (8% of 131072 = ~10485 tokens)
        mock_messages = [
            Mock(spec=Message, role="user", content="Hello", token_count=1000, uuid="uuid-1"),
            Mock(spec=Message, role="assistant", content="Hi there!", token_count=2000, uuid="uuid-2"),
            Mock(spec=Message, role="user", content="How are you?", token_count=1500, uuid="uuid-3"),
            Mock(spec=Message, role="assistant", content="I'm good!", token_count=1800, uuid="uuid-4"),
        ]
        mock_transcript_store.read_view.return_value = mock_messages

        # Mock history manager with _summarize_compress method
        mock_history_manager = Mock()
        compressed_messages = [
            Mock(spec=Message, role="user", content="Summary of conversation", token_count=500, uuid="uuid-summary"),
        ]
        mock_history_manager._summarize_compress.return_value = compressed_messages

        # Set up the global context
        _set_interpreter_context([], mock_history_manager, mock_agent_context)

        # Call compress_context with "summarize" strategy
        result = _compress_context("summarize")

        # Verify the result
        assert result["status"] == "ok"
        assert result["strategy"] == "summarize"
        assert result["original_messages"] == 4
        assert result["compressed_messages"] == 1
        assert result["original_tokens"] == 6300  # 1000+2000+1500+1800
        assert result["compressed_tokens"] == 500

        # Verify _summarize_compress was called with correct budget
        # Budget should be 50% of original tokens to force actual compression
        expected_budget = int(6300 * 0.5)  # 50% of 6300 tokens
        mock_history_manager._summarize_compress.assert_called_once()
        call_args = mock_history_manager._summarize_compress.call_args
        # Positional arguments: (history, budget)
        assert call_args[0][1] == expected_budget

        # Verify compression was recorded in TranscriptStore
        mock_agent_context._record_compression_ssot.assert_called_once()

    def test_compress_context_truncate_forces_compression(self):
        """Test that 'truncate' strategy forces truncation even with low usage ratio."""
        # Setup mock agent context with transcript store
        mock_agent_context = Mock()
        mock_transcript_store = Mock()
        mock_agent_context.transcript_store = mock_transcript_store
        mock_agent_context._record_compression_ssot = Mock()

        # Create mock messages
        mock_messages = [
            Mock(spec=Message, role="user", content="Message 1", token_count=1000, uuid="uuid-1"),
            Mock(spec=Message, role="assistant", content="Message 2", token_count=1000, uuid="uuid-2"),
            Mock(spec=Message, role="user", content="Message 3", token_count=1000, uuid="uuid-3"),
        ]
        mock_transcript_store.read_view.return_value = mock_messages

        # Mock history manager with _truncate_compress method
        mock_history_manager = Mock()
        compressed_messages = [
            Mock(spec=Message, role="user", content="Message 3", token_count=1000, uuid="uuid-3"),
        ]
        mock_history_manager._truncate_compress.return_value = compressed_messages

        # Set up the global context
        _set_interpreter_context([], mock_history_manager, mock_agent_context)

        # Call compress_context with "truncate" strategy
        result = _compress_context("truncate")

        # Verify the result
        assert result["status"] == "ok"
        assert result["strategy"] == "truncate"
        assert result["original_messages"] == 3
        assert result["compressed_messages"] == 1

        # Verify _truncate_compress was called
        mock_history_manager._truncate_compress.assert_called_once()

        # Verify compression was recorded in TranscriptStore
        mock_agent_context._record_compression_ssot.assert_called_once()

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
