"""Test for issue #12: compress_context with non-auto strategies and TranscriptStore enabled."""
import pytest
from unittest.mock import Mock, MagicMock
from helen.stdlib.context import _compress_context, _set_interpreter_context
from helen.runtime.history import Message


def _make_messages(count: int) -> list[Message]:
    """Create real Message objects for compression tests."""
    return [
        Message(
            role="user" if i % 2 == 0 else "assistant",
            content=f"Message {i} with content " * 10,
            uuid=f"uuid-{i}",
        )
        for i in range(count)
    ]


class TestIssue12CompressContextTranscriptStore:
    """Test that compress_context works with TranscriptStore enabled for all strategies.

    Issue #12: non-auto strategies (summarize/truncate/none) used to raise
    ImportError when TranscriptStore was enabled. These tests verify they
    now work correctly.
    """

    def test_compress_context_summarize_with_transcript_store(self):
        """Test summarize strategy with TranscriptStore enabled (issue #12).

        summarize now uses _force_compact which keeps last message + summary.
        """
        mock_agent_context = Mock()
        mock_transcript_store = Mock()
        mock_agent_context.transcript_store = mock_transcript_store
        mock_agent_context._record_compression_ssot = Mock()
        mock_agent_context.llm_client = None

        messages = _make_messages(8)
        mock_transcript_store.read_view.return_value = messages

        mock_history = []
        mock_manager = Mock()
        mock_manager.MAX_TOKENS = 131072

        _set_interpreter_context(mock_history, mock_manager)
        from helen.stdlib import context
        context._interpreter_agent_context = mock_agent_context

        # summarize should not raise ImportError and should compress
        result = _compress_context("summarize")

        assert result["status"] == "ok"
        assert result["strategy"] == "summarize"
        assert result["original_messages"] == 8
        # _force_compact keeps summary + last message (fewer than original)
        assert result["compressed_messages"] < result["original_messages"]

    def test_compress_context_truncate_with_transcript_store(self):
        """Test truncate strategy with TranscriptStore enabled (issue #12).

        truncate now uses _context_collapse which requires > 20 messages.
        """
        mock_agent_context = Mock()
        mock_transcript_store = Mock()
        mock_agent_context.transcript_store = mock_transcript_store
        mock_agent_context._record_compression_ssot = Mock()

        # Need > CONTEXT_COLLAPSE_THRESHOLD (20) messages for _context_collapse
        messages = _make_messages(25)
        mock_transcript_store.read_view.return_value = messages

        mock_history = []
        mock_manager = Mock()
        mock_manager.MAX_TOKENS = 131072

        _set_interpreter_context(mock_history, mock_manager)
        from helen.stdlib import context
        context._interpreter_agent_context = mock_agent_context

        # truncate should not raise ImportError and should compress
        result = _compress_context("truncate")

        assert result["status"] == "ok"
        assert result["strategy"] == "truncate"
        assert result["original_messages"] == 25
        # _context_collapse compresses old messages
        assert result["compressed_messages"] < result["original_messages"]

    def test_compress_context_none_with_transcript_store(self):
        """Test none strategy with TranscriptStore enabled (issue #12)."""
        mock_agent_context = Mock()
        mock_transcript_store = Mock()
        mock_agent_context.transcript_store = mock_transcript_store

        messages = _make_messages(1)
        mock_transcript_store.read_view.return_value = messages

        mock_agent_context._compress_history.return_value = messages

        mock_history = []
        mock_manager = Mock()

        _set_interpreter_context(mock_history, mock_manager)
        from helen.stdlib import context
        context._interpreter_agent_context = mock_agent_context

        # none should not raise ImportError
        result = _compress_context("none")

        assert result["status"] == "ok"
        assert result["strategy"] == "none"

