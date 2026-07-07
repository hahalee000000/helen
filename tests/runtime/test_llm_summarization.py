"""Tests for Phase 3: LLM-based semantic compression.

Tests the LLMSummarizer class that uses LLM to generate intelligent summaries.
Note: auto_compact() was removed as dead code - its functionality is now in
graduated_compression._auto_compact().
"""

import pytest
from unittest.mock import Mock, MagicMock
from helen.runtime.history import Message
from helen.runtime.llm_summarizer import LLMSummarizer


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
