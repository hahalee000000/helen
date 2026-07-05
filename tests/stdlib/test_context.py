"""Tests for context management stdlib functions.

Covers: clear_context(), compress_context()
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from helen.stdlib.context import (
    _clear_context,
    _compress_context,
    _set_interpreter_context,
)


class TestClearContext:
    """Tests for clear_context() function."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a mock history list
        self.mock_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]
        # Create a mock history manager
        self.mock_manager = MagicMock()
        self.mock_manager.estimate_tokens.return_value = 100

    def test_clear_context_success(self):
        """Test successful context clearing."""
        _set_interpreter_context(self.mock_history, self.mock_manager)
        result = _clear_context()

        assert result["status"] == "ok"
        assert result["cleared_messages"] == 3
        assert "cleared_tokens" in result
        assert "warning" in result
        assert len(self.mock_history) == 0

    def test_clear_context_empty(self):
        """Test clearing empty context."""
        _set_interpreter_context([], self.mock_manager)
        result = _clear_context()

        assert result["status"] == "ok"
        assert result["cleared_messages"] == 0
        assert result["cleared_tokens"] == 0

    def test_clear_context_no_interpreter(self):
        """Test clearing context when no interpreter is set."""
        _set_interpreter_context(None, None)
        result = _clear_context()

        assert result["status"] == "error"
        assert "No interpreter context" in result["error"]
        assert result["cleared_messages"] == 0


class TestCompressContext:
    """Tests for compress_context() function."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a mock history list with many messages
        self.mock_history = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(20)
        ]
        # Create a mock history manager
        self.mock_manager = MagicMock()
        self.mock_manager.estimate_tokens.side_effect = lambda h: len(h) * 10
        self.mock_manager.compress_if_needed.return_value = None
        self.mock_manager._compress_summarize.return_value = None
        self.mock_manager._compress_truncate.return_value = None

    def test_compress_context_auto(self):
        """Test auto compression strategy."""
        _set_interpreter_context(self.mock_history, self.mock_manager)
        result = _compress_context("auto")

        assert result["status"] == "ok"
        assert result["strategy"] == "auto"
        assert "original_messages" in result
        assert "compressed_messages" in result
        assert "original_tokens" in result
        assert "compressed_tokens" in result
        self.mock_manager.compress_if_needed.assert_called_once()

    def test_compress_context_summarize(self):
        """Test summarize compression strategy."""
        _set_interpreter_context(self.mock_history, self.mock_manager)
        result = _compress_context("summarize")

        assert result["status"] == "ok"
        assert result["strategy"] == "summarize"
        self.mock_manager._compress_summarize.assert_called_once()

    def test_compress_context_truncate(self):
        """Test truncate compression strategy."""
        _set_interpreter_context(self.mock_history, self.mock_manager)
        result = _compress_context("truncate")

        assert result["status"] == "ok"
        assert result["strategy"] == "truncate"
        self.mock_manager._compress_truncate.assert_called_once()

    def test_compress_context_none(self):
        """Test none compression strategy (no-op)."""
        _set_interpreter_context(self.mock_history, self.mock_manager)
        result = _compress_context("none")

        assert result["status"] == "ok"
        assert result["strategy"] == "none"
        assert result["original_messages"] == 20
        assert result["compressed_messages"] == 20

    def test_compress_context_unknown_strategy(self):
        """Test unknown compression strategy."""
        _set_interpreter_context(self.mock_history, self.mock_manager)
        result = _compress_context("unknown")

        assert result["status"] == "error"
        assert "Unknown compression strategy" in result["error"]

    def test_compress_context_no_interpreter(self):
        """Test compression when no interpreter is set."""
        _set_interpreter_context(None, None)
        result = _compress_context("auto")

        assert result["status"] == "error"
        assert "No interpreter context" in result["error"]


class TestContextIntegration:
    """Integration tests for context management."""

    def test_clear_then_compress(self):
        """Test that compressing after clear works correctly."""
        mock_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        mock_manager = MagicMock()
        mock_manager.estimate_tokens.return_value = 0

        _set_interpreter_context(mock_history, mock_manager)

        # Clear context
        clear_result = _clear_context()
        assert clear_result["status"] == "ok"
        assert len(mock_history) == 0

        # Compress empty context
        compress_result = _compress_context("auto")
        assert compress_result["status"] == "ok"
        assert compress_result["compressed_messages"] == 0

    def test_multiple_clears(self):
        """Test that multiple clears are idempotent."""
        mock_history = [{"role": "user", "content": "test"}]
        mock_manager = MagicMock()

        _set_interpreter_context(mock_history, mock_manager)

        # First clear
        result1 = _clear_context()
        assert result1["cleared_messages"] == 1

        # Second clear (should be 0)
        result2 = _clear_context()
        assert result2["cleared_messages"] == 0
