"""Tests for Phase 1: Message classification and selective compression.

Tests the new message classification features that enable selective compression:
- Message type inference (system/user/assistant/assistant_tool_call/tool)
- Priority assignment based on message type
- Selective compression by target type (tool_results/stale_turns)
"""

import pytest
from unittest.mock import MagicMock
from helen.stdlib.context import (
    _classify_message,
    _compress_context_target,
    _set_interpreter_context,
)
from helen.runtime.history import Message


class TestMessageClassification:
    """Tests for message classification (Phase 1)."""

    def test_classify_system_message(self):
        """Test that system messages are classified correctly."""
        msg = Message(
            role="system",
            content="You are a helpful assistant.",
            tool_calls=[],
            tool_call_id=None,
            _token_count=10,
            _model="qwen3.7-plus",
        )

        result = _classify_message(msg)

        assert result["message_type"] == "system"
        assert result["priority"] == 100
        assert result["compressed"] is False

    def test_classify_user_message(self):
        """Test that user messages are classified correctly."""
        msg = Message(
            role="user",
            content="Hello, how are you?",
            tool_calls=[],
            tool_call_id=None,
            _token_count=8,
            _model="qwen3.7-plus",
        )

        result = _classify_message(msg)

        assert result["message_type"] == "user"
        assert result["priority"] == 90
        assert result["compressed"] is False

    def test_classify_assistant_text_message(self):
        """Test that assistant text responses are classified correctly."""
        msg = Message(
            role="assistant",
            content="I'm doing well, thank you!",
            tool_calls=[],
            tool_call_id=None,
            _token_count=10,
            _model="qwen3.7-plus",
        )

        result = _classify_message(msg)

        assert result["message_type"] == "assistant"
        assert result["priority"] == 80
        assert result["compressed"] is False

    def test_classify_assistant_tool_call(self):
        """Test that assistant tool call decisions are classified correctly."""
        msg = Message(
            role="assistant",
            content="",
            tool_calls=[{"id": "call_123", "name": "read_file", "args": {"path": "test.py"}}],
            tool_call_id=None,
            _token_count=15,
            _model="qwen3.7-plus",
        )

        result = _classify_message(msg)

        assert result["message_type"] == "assistant_tool_call"
        assert result["priority"] == 70
        assert result["compressed"] is False

    def test_classify_tool_result(self):
        """Test that tool results are classified correctly."""
        msg = Message(
            role="tool",
            content="File contents here...",
            tool_calls=[],
            tool_call_id="call_123",
            _token_count=500,
            _model="qwen3.7-plus",
        )

        result = _classify_message(msg)

        assert result["message_type"] == "tool"
        assert result["priority"] == 20
        assert result["compressed"] is False

    def test_classify_message_without_attributes(self):
        """Test that messages without classification attributes are handled."""
        # Create a simple object without Message attributes
        class SimpleMsg:
            def __init__(self):
                self.role = "user"
                self.content = "test"

        msg = SimpleMsg()
        result = _classify_message(msg)

        assert result["message_type"] == "unknown"
        assert result["priority"] == 50


class TestSelectiveCompression:
    """Tests for selective compression by target type (Phase 1)."""

    def setup_method(self):
        """Reset interpreter context before each test."""
        _set_interpreter_context([], MagicMock())

    def test_compress_tool_results_preserves_recent(self):
        """Test that tool result compression preserves recent results."""
        # Create a history with multiple tool results
        history = [
            Message(role="user", content="Read file 1", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
            Message(role="assistant", content="", tool_calls=[{"name": "read_file", "args": {}}], tool_call_id=None, _token_count=15, _model="qwen3.7-plus"),
            Message(role="tool", content="Content 1", tool_calls=[], tool_call_id="call_1", _token_count=100, _model="qwen3.7-plus"),
            Message(role="user", content="Read file 2", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
            Message(role="assistant", content="", tool_calls=[{"name": "read_file", "args": {}}], tool_call_id=None, _token_count=15, _model="qwen3.7-plus"),
            Message(role="tool", content="Content 2", tool_calls=[], tool_call_id="call_2", _token_count=100, _model="qwen3.7-plus"),
        ]

        _set_interpreter_context(history, MagicMock())

        # Compress tool results, keep 1 recent
        result = _compress_context_target(target="tool_results", keep_recent=1)

        assert result["status"] == "ok"
        assert result["target"] == "tool_results"
        assert result["compressed"] > 0  # At least one tool result compressed
        assert result["saved_tokens"] > 0  # Should save tokens

        # Verify the most recent tool result is preserved
        last_tool_result = history[-1]
        assert last_tool_result.content == "Content 2"
        assert last_tool_result.compressed is False

    def test_compress_tool_results_clears_old(self):
        """Test that old tool results are cleared."""
        history = [
            Message(role="user", content="Read file 1", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
            Message(role="assistant", content="", tool_calls=[{"name": "read_file", "args": {}}], tool_call_id=None, _token_count=15, _model="qwen3.7-plus"),
            Message(role="tool", content="Old content", tool_calls=[], tool_call_id="call_1", _token_count=500, _model="qwen3.7-plus"),
            Message(role="user", content="Read file 2", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
            Message(role="assistant", content="", tool_calls=[{"name": "read_file", "args": {}}], tool_call_id=None, _token_count=15, _model="qwen3.7-plus"),
            Message(role="tool", content="Recent content", tool_calls=[], tool_call_id="call_2", _token_count=500, _model="qwen3.7-plus"),
        ]

        _set_interpreter_context(history, MagicMock())

        # Compress tool results, keep 1 recent
        result = _compress_context_target(target="tool_results", keep_recent=1)

        assert result["status"] == "ok"
        assert result["compressed"] >= 1

        # Verify old tool result is cleared
        old_tool_result = history[2]
        assert old_tool_result.compressed is True
        assert "cleared" in old_tool_result.content.lower()

    def test_compress_stale_turns_keeps_recent(self):
        """Test that stale turn compression keeps recent turns."""
        # Create a long history
        history = []
        for i in range(20):
            history.append(Message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                tool_calls=[],
                tool_call_id=None,
                _token_count=20,
                _model="qwen3.7-plus",
            ))

        _set_interpreter_context(history, MagicMock())

        # Compress stale turns, keep 5 recent
        result = _compress_context_target(target="stale_turns", keep_recent=5)

        assert result["status"] == "ok"
        assert result["target"] == "stale_turns"
        assert result["compressed"] > 0
        assert result["saved_tokens"] > 0

    def test_compress_stale_turns_preserves_system(self):
        """Test that system messages are preserved during stale turn compression."""
        history = [
            Message(role="system", content="System prompt", tool_calls=[], tool_call_id=None, _token_count=50, _model="qwen3.7-plus"),
            Message(role="user", content="User 1", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
            Message(role="assistant", content="Assistant 1", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
            Message(role="user", content="User 2", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
            Message(role="assistant", content="Assistant 2", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
        ]

        # Add more messages to trigger compression
        for i in range(20):
            history.append(Message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                tool_calls=[],
                tool_call_id=None,
                _token_count=20,
                _model="qwen3.7-plus",
            ))

        _set_interpreter_context(history, MagicMock())

        result = _compress_context_target(target="stale_turns", keep_recent=5)

        assert result["status"] == "ok"

        # Verify system message is not compressed
        system_msg = history[0]
        assert system_msg.role == "system"
        assert system_msg.content == "System prompt"

    def test_compress_invalid_target(self):
        """Test that invalid compression target returns error."""
        history = [
            Message(role="user", content="Test", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
        ]
        _set_interpreter_context(history, MagicMock())

        result = _compress_context_target(target="invalid_target")

        assert result["status"] == "error"
        assert "Unknown compression target" in result["error"]

    def test_compress_without_context(self):
        """Test that compression without context returns error."""
        _set_interpreter_context(None, None)

        result = _compress_context_target(target="tool_results")

        assert result["status"] == "error"
        assert "No interpreter context" in result["error"]
