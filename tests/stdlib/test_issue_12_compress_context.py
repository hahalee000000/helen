"""Test for issue #12: compress_context with non-auto strategies and TranscriptStore enabled."""
import pytest
from unittest.mock import Mock, MagicMock
from helen.stdlib.context import _compress_context, _set_interpreter_context


class TestIssue12CompressContextTranscriptStore:
    """Test that compress_context works with TranscriptStore enabled for all strategies."""

    def test_compress_context_summarize_with_transcript_store(self):
        """Test summarize strategy with TranscriptStore enabled (issue #12)."""
        # Setup mock agent context with transcript store
        mock_agent_context = Mock()
        mock_transcript_store = Mock()
        mock_agent_context.transcript_store = mock_transcript_store

        # Mock the read_view to return some messages
        mock_messages = [
            Mock(role="user", content="Hello", token_count=10),
            Mock(role="assistant", content="Hi there!", token_count=15),
        ]
        mock_transcript_store.read_view.return_value = mock_messages

        # Mock _compress_history to return compressed messages
        compressed_messages = [
            Mock(role="user", content="Hello", token_count=10),
        ]
        mock_agent_context._compress_history.return_value = compressed_messages

        # Mock history (should not be used when TranscriptStore is enabled)
        mock_history = []
        mock_manager = Mock()

        _set_interpreter_context(mock_history, mock_manager)

        # Import and set agent context
        from helen.stdlib import context
        context._interpreter_agent_context = mock_agent_context

        # Test summarize strategy - should not raise ImportError
        result = _compress_context("summarize")

        # Verify result
        assert result["status"] == "ok"
        assert result["strategy"] == "summarize"
        assert result["original_messages"] == 2
        assert result["compressed_messages"] == 1

        # Verify _compress_history was called with correct max_tokens
        mock_agent_context._compress_history.assert_called_once()
        call_args = mock_agent_context._compress_history.call_args
        assert call_args[0][0] == mock_messages  # history
        assert call_args[0][1] == 131072  # max_tokens (DEFAULT_CONTEXT_WINDOW)

    def test_compress_context_truncate_with_transcript_store(self):
        """Test truncate strategy with TranscriptStore enabled (issue #12)."""
        # Setup mock agent context with transcript store
        mock_agent_context = Mock()
        mock_transcript_store = Mock()
        mock_agent_context.transcript_store = mock_transcript_store

        # Mock the read_view to return some messages
        mock_messages = [
            Mock(role="user", content="Hello", token_count=10),
            Mock(role="assistant", content="Hi there!", token_count=15),
            Mock(role="user", content="How are you?", token_count=12),
        ]
        mock_transcript_store.read_view.return_value = mock_messages

        # Mock _compress_history to return compressed messages
        compressed_messages = [
            Mock(role="user", content="How are you?", token_count=12),
        ]
        mock_agent_context._compress_history.return_value = compressed_messages

        # Mock history (should not be used when TranscriptStore is enabled)
        mock_history = []
        mock_manager = Mock()

        _set_interpreter_context(mock_history, mock_manager)

        # Import and set agent context
        from helen.stdlib import context
        context._interpreter_agent_context = mock_agent_context

        # Test truncate strategy - should not raise ImportError
        result = _compress_context("truncate")

        # Verify result
        assert result["status"] == "ok"
        assert result["strategy"] == "truncate"
        assert result["original_messages"] == 3
        assert result["compressed_messages"] == 1

    def test_compress_context_none_with_transcript_store(self):
        """Test none strategy with TranscriptStore enabled (issue #12)."""
        # Setup mock agent context with transcript store
        mock_agent_context = Mock()
        mock_transcript_store = Mock()
        mock_agent_context.transcript_store = mock_transcript_store

        # Mock the read_view to return some messages
        mock_messages = [
            Mock(role="user", content="Hello", token_count=10),
        ]
        mock_transcript_store.read_view.return_value = mock_messages

        # Mock _compress_history to return same messages (none strategy)
        mock_agent_context._compress_history.return_value = mock_messages

        # Mock history (should not be used when TranscriptStore is enabled)
        mock_history = []
        mock_manager = Mock()

        _set_interpreter_context(mock_history, mock_manager)

        # Import and set agent context
        from helen.stdlib import context
        context._interpreter_agent_context = mock_agent_context

        # Test none strategy - should not raise ImportError
        result = _compress_context("none")

        # Verify result
        assert result["status"] == "ok"
        assert result["strategy"] == "none"
