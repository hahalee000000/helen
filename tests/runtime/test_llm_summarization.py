"""Tests for Phase 3: LLM-based semantic compression.

Tests the Auto-Compact layer that uses LLM to generate intelligent summaries.
"""

import pytest
from unittest.mock import Mock, MagicMock
from helen.runtime.history import Message
from helen.runtime.llm_summarizer import (
    LLMSummarizer,
    auto_compact,
    calculate_next_compaction_threshold,
)


class TestLLMSummarizer:
    """Tests for LLMSummarizer class."""

    def test_summarize_with_mock_llm(self):
        """Test summarization with a mock LLM client."""
        # Create mock LLM client
        mock_llm = Mock(return_value="## Task Objective\nFix authentication bug\n\n## Completed\n- Updated auth.py")

        summarizer = LLMSummarizer(mock_llm)

        history = [
            Message(role="user", content="Fix the auth bug", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
            Message(role="assistant", content="I'll fix it", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
        ]

        result = summarizer.summarize(history, target_tokens=1000)

        assert "Task Objective" in result
        assert "authentication" in result.lower()
        mock_llm.assert_called_once()

    def test_summarize_handles_empty_history(self):
        """Test that summarization handles empty history."""
        mock_llm = Mock()
        summarizer = LLMSummarizer(mock_llm)

        result = summarizer.summarize([], target_tokens=1000)

        assert result == ""
        mock_llm.assert_not_called()

    def test_summarize_fallback_on_error(self):
        """Test that summarization falls back on LLM error."""
        # Mock LLM that raises an exception
        mock_llm = Mock(side_effect=Exception("LLM error"))

        summarizer = LLMSummarizer(mock_llm)

        history = [
            Message(role="user", content="Test", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
        ]

        result = summarizer.summarize(history, target_tokens=1000)

        # Should return fallback summary
        assert "fallback" in result.lower() or "summary" in result.lower()

    def test_summarize_skips_system_messages(self):
        """Test that system messages are skipped in summary."""
        mock_llm = Mock(return_value="Summary")

        summarizer = LLMSummarizer(mock_llm)

        history = [
            Message(role="system", content="System prompt", tool_calls=[], tool_call_id=None, _token_count=50, _model="qwen3.7-plus"),
            Message(role="user", content="User message", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
        ]

        summarizer.summarize(history, target_tokens=1000)

        # Verify that the prompt was built
        call_args = mock_llm.call_args[0][0]
        messages = call_args

        # The user message should contain the conversation but not the system prompt
        user_msg = messages[1]["content"]
        assert "User message" in user_msg
        # System prompt should not be in the conversation text
        assert "System prompt" not in user_msg or user_msg.count("System prompt") == 0


class TestAutoCompact:
    """Tests for auto_compact function."""

    def test_auto_compact_creates_summary(self):
        """Test that auto_compact creates a summary message."""
        mock_llm = Mock(return_value="## Summary\nTest summary")

        history = [
            Message(role="user", content="Hello", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
            Message(role="assistant", content="Hi", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
        ]

        result = auto_compact(history, mock_llm, target_tokens=1000)

        # Should have summary message at the start
        assert len(result) > 0
        assert result[0].role == "system"
        assert "summary" in result[0].content.lower()

    def test_auto_compact_marks_old_messages(self):
        """Test that auto_compact marks old messages as compressed."""
        mock_llm = Mock(return_value="## Summary\nTest summary")

        history = [
            Message(role="user", content="Hello", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
            Message(role="assistant", content="Hi", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
        ]

        result = auto_compact(history, mock_llm, target_tokens=1000)

        # Old messages should be marked as compressed
        for msg in result[1:]:  # Skip the summary message
            assert msg.compressed is True

    def test_auto_compact_handles_empty_history(self):
        """Test that auto_compact handles empty history."""
        mock_llm = Mock()

        result = auto_compact([], mock_llm, target_tokens=1000)

        assert result == []
        mock_llm.assert_not_called()


class TestSixtyPercentRule:
    """Tests for the 60% rule calculation."""

    def test_calculate_next_threshold(self):
        """Test that next threshold is calculated correctly."""
        # After compaction at 30%, next threshold should be ~72%
        # 30% + 60% × 70% = 30% + 42% = 72%
        max_tokens = 100000
        current_usage = 30000  # 30% after compaction

        next_threshold = calculate_next_compaction_threshold(current_usage, max_tokens)

        # Expected: 30000 + 0.60 * (100000 - 30000) = 30000 + 42000 = 72000
        expected = 72000
        assert abs(next_threshold - expected) < 100  # Allow small floating point error

    def test_calculate_next_threshold_with_different_usage(self):
        """Test threshold calculation with different usage levels."""
        max_tokens = 131072  # Standard Qwen window

        # The function always assumes post-compaction usage is 30%
        # regardless of current_usage parameter
        current_usage = 0.40 * max_tokens
        next_threshold = calculate_next_compaction_threshold(current_usage, max_tokens)

        # Expected: always based on 30% post-compaction
        # 30% + 60% × 70% = 30% + 42% = 72%
        expected = 0.72 * max_tokens
        assert abs(next_threshold - expected) < 100
