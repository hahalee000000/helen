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


class TestCompressContextActuallyCompresses:
    """Regression: compress_context() must actually modify the history (BUG-1 fix).

    Previously, enforce_limit() / _summarize_compress() / _truncate_compress()
    return a new list but the return value was discarded. The history remained
    unchanged. The fix uses slice-assignment to mutate in place.
    """

    def test_auto_strategy_mutates_history(self):
        """'auto' strategy must replace history contents via slice assignment."""
        msg1 = Message("user", "old msg 1", _token_count=1000)
        msg2 = Message("user", "old msg 2", _token_count=1000)
        msg3 = Message("assistant", "recent", _token_count=50)
        history = [msg1, msg2, msg3]

        # Mock manager that returns a truncated list (simulating compression)
        compressed = [msg3]  # only the recent message survives
        mock_manager = MagicMock()
        mock_manager.enforce_limit = MagicMock(return_value=compressed)

        _set_interpreter_context(history, mock_manager)

        result = _compress_context(strategy="auto")

        # History must actually be modified in place
        assert len(history) == 1
        assert history[0] is msg3
        assert result["status"] == "ok"
        assert result["compressed_messages"] == 1

    def test_summarize_strategy_mutates_history(self):
        """'summarize' strategy must replace history contents using _force_compact."""
        msg1 = Message("user", "old message content " * 50, _token_count=1000)
        msg2 = Message("assistant", "recent message", _token_count=50)
        msg3 = Message("user", "latest user message", _token_count=100)
        history = [msg1, msg2, msg3]
        original_len = len(history)

        mock_manager = MagicMock()
        mock_manager.MAX_TOKENS = 131072

        _set_interpreter_context(history, mock_manager)

        result = _compress_context(strategy="summarize")

        # History should be compressed (fewer messages, less tokens)
        assert len(history) < original_len
        assert result["status"] == "ok"
        assert result["compressed_tokens"] < result["original_tokens"]

    def test_truncate_strategy_mutates_history(self):
        """'truncate' strategy must replace history contents using _context_collapse."""
        # Need enough messages for _context_collapse to work (> CONTEXT_COLLAPSE_THRESHOLD = 20)
        history = [
            Message("user" if i % 2 == 0 else "assistant", f"Message {i}", _token_count=100)
            for i in range(25)
        ]
        original_len = len(history)

        mock_manager = MagicMock()
        mock_manager.MAX_TOKENS = 131072

        _set_interpreter_context(history, mock_manager)

        result = _compress_context(strategy="truncate")

        # History should be compressed
        assert len(history) < original_len
        assert result["status"] == "ok"
        assert result["compressed_tokens"] < result["original_tokens"]


class TestClearContextClearsWorkingMemory:
    """Regression: clear_context() must clear working memory (BUG-2 fix)."""

    def test_clear_context_clears_working_memory(self):
        """After clear_context(), working memory should be empty."""
        from helen.interpreter.agent_context import AgentContextManager

        agent_ctx = AgentContextManager()
        agent_ctx.working_memory._add_active_file("test.py")
        agent_ctx.working_memory._add_decision("Use async")
        agent_ctx.working_memory._add_todo("Write tests")
        agent_ctx.working_memory._add_error("pytest", "failed")

        history = [Message("user", "test", _token_count=10)]
        _set_interpreter_context(history, MagicMock(), agent_ctx)

        result = _clear_context()

        assert result["status"] == "ok"
        assert len(history) == 0
        # Working memory must be cleared
        assert agent_ctx.working_memory.active_files == []
        assert agent_ctx.working_memory.recent_decisions == []
        assert agent_ctx.working_memory.pending_todos == []
        assert agent_ctx.working_memory.error_history == []

    def test_clear_context_works_without_agent_context(self):
        """clear_context() should still work when no agent_context is wired."""
        history = [Message("user", "test", _token_count=10)]
        _set_interpreter_context(history, MagicMock())  # no agent_context

        result = _clear_context()

        assert result["status"] == "ok"
        assert len(history) == 0


class TestTokenCountUsesProperty:
    """Regression: token estimation must use msg.token_count property (BUG-4 fix).

    msg._token_count is the raw backing field (default 0).
    msg.token_count is a lazy-computing property that returns accurate values.
    """

    def test_clear_context_uses_property(self):
        """clear_context should compute tokens via property, not raw field."""
        # Create a message where _token_count=0 but content suggests real tokens
        msg = Message("user", "x" * 100, _token_count=0)
        # Accessing token_count should compute and cache
        real_tokens = msg.token_count
        assert real_tokens > 0  # property computed something

        history = [msg]
        _set_interpreter_context(history, MagicMock())

        result = _clear_context()
        assert result["cleared_tokens"] == real_tokens

    def test_compress_context_reports_accurate_tokens(self):
        """compress_context stats should use property-computed tokens."""
        msg = Message("user", "x" * 100, _token_count=0)
        real_tokens = msg.token_count

        mock_manager = MagicMock()
        mock_manager.enforce_limit = MagicMock(return_value=[msg])

        history = [msg]
        _set_interpreter_context(history, mock_manager)

        result = _compress_context(strategy="auto")
        assert result["original_tokens"] == real_tokens
