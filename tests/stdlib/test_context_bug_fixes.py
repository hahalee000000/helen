"""Tests for context management bug fixes.

Tests the fix for two bugs in clear_context() and compress_context():
1. clear_context() token estimation used msg.get() on Message objects
2. compress_context() passed list[Message] to estimate_tokens(str)
"""

import pytest
from unittest.mock import MagicMock
from helen.stdlib.context import (
    _clear_context,
    _compress_context,
    _set_interpreter_context,
)
from helen.runtime.history import Message


class TestClearContextBugFix:
    """Tests for clear_context() bug fix (Phase 5, Bug 1)."""

    def setup_method(self):
        """Reset interpreter context before each test."""
        _set_interpreter_context([], MagicMock())

    def test_clear_context_returns_correct_token_count(self):
        """Test that clear_context returns accurate token count."""
        # Create messages with known token counts
        msg1 = Message(
            role="user",
            content="Hello world",
            tool_calls=[],
            tool_call_id=None,
            _token_count=100,
            _model="qwen3.7-plus",
        )
        msg2 = Message(
            role="assistant",
            content="Hi there",
            tool_calls=[],
            tool_call_id=None,
            _token_count=50,
            _model="qwen3.7-plus",
        )
        msg3 = Message(
            role="tool",
            content="Tool result",
            tool_calls=[],
            tool_call_id="tool_123",
            _token_count=30,
            _model="qwen3.7-plus",
        )

        history = [msg1, msg2, msg3]
        _set_interpreter_context(history, MagicMock())

        result = _clear_context()

        assert result["status"] == "ok"
        assert result["cleared_messages"] == 3
        # Token count should be sum of all message token_counts
        assert result["cleared_tokens"] == 180  # 100 + 50 + 30

    def test_clear_context_with_message_objects(self):
        """Test that clear_context handles Message objects (not dicts)."""
        # This test specifically checks that we don't use msg.get()
        msg = Message(
            role="user",
            content="Test message",
            tool_calls=[],
            tool_call_id=None,
            _token_count=25,
            _model="qwen3.7-plus",
        )

        history = [msg]
        _set_interpreter_context(history, MagicMock())

        # Should not raise AttributeError
        result = _clear_context()

        assert result["status"] == "ok"
        assert result["cleared_messages"] == 1
        assert result["cleared_tokens"] == 25

    def test_clear_context_with_empty_history(self):
        """Test clear_context with empty history."""
        _set_interpreter_context([], MagicMock())

        result = _clear_context()

        assert result["status"] == "ok"
        assert result["cleared_messages"] == 0
        assert result["cleared_tokens"] == 0

    def test_clear_context_without_interpreter_context(self):
        """Test clear_context when interpreter context is not set."""
        _set_interpreter_context(None, None)

        result = _clear_context()

        assert result["status"] == "error"
        assert "No interpreter context" in result["error"]


class TestCompressContextBugFix:
    """Tests for compress_context() bug fix (Phase 5, Bug 2)."""

    def setup_method(self):
        """Reset interpreter context before each test."""
        _set_interpreter_context([], MagicMock())

    def test_compress_context_returns_correct_token_count(self):
        """Test that compress_context returns accurate token counts."""
        # Create messages with known token counts
        msg1 = Message(
            role="user",
            content="Hello",
            tool_calls=[],
            tool_call_id=None,
            _token_count=50,
            _model="qwen3.7-plus",
        )
        msg2 = Message(
            role="assistant",
            content="Hi",
            tool_calls=[],
            tool_call_id=None,
            _token_count=30,
            _model="qwen3.7-plus",
        )

        history = [msg1, msg2]

        # Mock history manager
        mock_manager = MagicMock()
        mock_manager.enforce_limit = MagicMock()

        _set_interpreter_context(history, mock_manager)

        result = _compress_context(strategy="auto")

        assert result["status"] == "ok"
        assert result["original_messages"] == 2
        # Token count should be sum of message token_counts
        assert result["original_tokens"] == 80  # 50 + 30

    def test_compress_context_with_message_objects(self):
        """Test that compress_context handles Message objects correctly."""
        msg = Message(
            role="user",
            content="Test",
            tool_calls=[],
            tool_call_id=None,
            _token_count=40,
            _model="qwen3.7-plus",
        )

        history = [msg]
        mock_manager = MagicMock()
        mock_manager.enforce_limit = MagicMock()

        _set_interpreter_context(history, mock_manager)

        # Should not raise TypeError
        result = _compress_context(strategy="auto")

        assert result["status"] == "ok"
        assert result["original_tokens"] == 40

    def test_compress_context_with_empty_history(self):
        """Test compress_context with empty history."""
        history = []
        mock_manager = MagicMock()
        mock_manager.enforce_limit = MagicMock()

        _set_interpreter_context(history, mock_manager)

        result = _compress_context(strategy="auto")

        assert result["status"] == "ok"
        assert result["original_messages"] == 0
        assert result["original_tokens"] == 0

    def test_compress_context_none_strategy(self):
        """Test compress_context with 'none' strategy."""
        msg = Message(
            role="user",
            content="Test",
            tool_calls=[],
            tool_call_id=None,
            _token_count=20,
            _model="qwen3.7-plus",
        )

        history = [msg]
        _set_interpreter_context(history, MagicMock())

        result = _compress_context(strategy="none")

        assert result["status"] == "ok"
        assert result["strategy"] == "none"
        assert result["original_messages"] == 1
        assert result["compressed_messages"] == 1

    def test_compress_context_invalid_strategy(self):
        """Test compress_context with invalid strategy."""
        history = []
        _set_interpreter_context(history, MagicMock())

        result = _compress_context(strategy="invalid_strategy")

        assert result["status"] == "error"
        assert "Unknown compression strategy" in result["error"]
