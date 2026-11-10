"""Tests for context overflow prevention (v1.46.24).

These tests verify that the context management system prevents context
from exceeding 100% usage, addressing the issues found in the analysis:

1. DEFAULT_CONTEXT_WINDOW consistency across modules
2. Hard limit check after adding messages to history
3. Reactive compaction is enabled by default
4. Pre-tool execution size estimation

Related: v1.46.22 finish_reason tracking, five-layer graduated compression.
"""

import pytest


class TestDefaultContextWindowConsistency:
    """Test that DEFAULT_CONTEXT_WINDOW is consistent across modules."""

    def test_history_and_token_utils_have_same_default(self):
        """history.py and token_utils.py should use the same DEFAULT_CONTEXT_WINDOW."""
        from helen.runtime.history import DEFAULT_CONTEXT_WINDOW as history_default
        from helen.runtime.token_utils import DEFAULT_CONTEXT_WINDOW as token_utils_default

        assert history_default == token_utils_default, (
            f"DEFAULT_CONTEXT_WINDOW mismatch: history.py={history_default}, "
            f"token_utils.py={token_utils_default}. "
            f"Should use single source of truth from token_utils."
        )

    def test_all_modules_import_from_token_utils(self):
        """All modules should import DEFAULT_CONTEXT_WINDOW from token_utils."""
        # These modules should NOT define their own DEFAULT_CONTEXT_WINDOW
        # They should import from token_utils
        import helen.runtime.history as history_module
        import helen.runtime.token_utils as token_utils_module

        # Check that history module uses token_utils's value
        # (after fix, history should not have its own definition)
        expected = token_utils_module.DEFAULT_CONTEXT_WINDOW
        actual = history_module.DEFAULT_CONTEXT_WINDOW

        assert actual == expected, (
            f"history.py should use token_utils.DEFAULT_CONTEXT_WINDOW ({expected}), "
            f"but has its own value ({actual})"
        )


class TestContextOverflowPrevention:
    """Test that context cannot exceed 100% without triggering compression."""

    def test_hard_limit_triggers_compression_at_100_percent(self):
        """Adding messages that push usage over 100% should trigger compression."""
        from helen.runtime.history import Message
        from helen.runtime.graduated_compression import graduated_compress

        # Create messages that together exceed 100% of a small context window
        # Context window: 1000 tokens
        # Messages total: 1100 tokens (110% usage)
        messages = [
            Message(role="user", content="Hello", _token_count=100, _model="test"),
            Message(role="assistant", content="Hi there", _token_count=100, _model="test"),
            Message(role="user", content="Read this file", _token_count=100, _model="test"),
            Message(role="tool", content="x" * 3200, _token_count=800, _model="test"),  # Large tool output
        ]
        # Total: 100 + 100 + 100 + 800 = 1100 tokens
        # Usage ratio: 1100 / 1000 = 1.1 (110%)

        max_tokens = 1000
        compressed, layer = graduated_compress(messages, usage_ratio=1.1, max_tokens=max_tokens)

        # After compression, usage should be reduced
        total_tokens = sum(m.token_count for m in compressed)
        new_ratio = total_tokens / max_tokens

        # The compression should have been applied (layer should not be "none")
        # OR the usage should be reduced to below 100%
        assert layer != "none" or new_ratio <= 1.0, (
            f"At 110% usage, compression should trigger. "
            f"Layer: {layer}, New ratio: {new_ratio:.2%}"
        )

    def test_graduated_compression_handles_over_100_percent(self):
        """Graduated compression should handle usage > 100%."""
        from helen.runtime.history import Message
        from helen.runtime.graduated_compression import graduated_compress

        # Create messages at 106% usage (the reported issue)
        messages = [
            Message(role="user", content="Task description", _token_count=500, _model="test"),
            Message(role="assistant", content="Working on it", _token_count=200, _model="test"),
            Message(role="tool", content="y" * 4000, _token_count=1000, _model="test"),
            Message(role="assistant", content="More work", _token_count=300, _model="test"),
            Message(role="tool", content="z" * 4000, _token_count=1000, _model="test"),
            Message(role="assistant", content="Almost done", _token_count=200, _model="test"),
        ]
        # Total: 500 + 200 + 1000 + 300 + 1000 + 200 = 3200 tokens
        # Context: 3000 tokens → 106.7% usage

        max_tokens = 3000
        usage_ratio = 3200 / 3000  # 1.067

        compressed, layer = graduated_compress(messages, usage_ratio=usage_ratio, max_tokens=max_tokens)

        # Should trigger compression
        assert layer != "none", "Should trigger compression at 106% usage"

        # After compression, should be under 100%
        total_tokens = sum(m.token_count for m in compressed)
        new_ratio = total_tokens / max_tokens
        assert new_ratio <= 1.0, (
            f"After compression at 106% usage, should be under 100%. "
            f"Got: {new_ratio:.2%}"
        )


class TestReactiveCompactionDefault:
    """Test that reactive compaction is enabled by default."""

    def test_reactive_compaction_enabled_by_default(self):
        """HttpLLMRuntime should have reactive compaction enabled by default."""
        from helen.runtime.http_llm import HttpLLMRuntime

        # Create runtime with minimal config
        runtime = HttpLLMRuntime(base_url="http://test", api_key="test")

        assert runtime.enable_reactive_compaction is True, (
            "Reactive compaction should be enabled by default to prevent "
            "context overflow during tool execution loops"
        )

    def test_reactive_compactor_initialized(self):
        """HttpLLMRuntime should initialize _reactive_compactor when enabled."""
        from helen.runtime.http_llm import HttpLLMRuntime

        runtime = HttpLLMRuntime(base_url="http://test", api_key="test")

        assert runtime._reactive_compactor is not None, (
            "_reactive_compactor should be initialized when enable_reactive_compaction=True"
        )


class TestPreToolSizeEstimation:
    """Test pre-tool execution size estimation to prevent overflow."""

    def test_estimate_tool_result_size(self):
        """Should be able to estimate tool result size before adding to history."""
        from helen.runtime.token_utils import estimate_tokens_simple

        # Simulate a large file read result
        large_content = "x" * 40000  # ~10000 tokens
        estimated = estimate_tokens_simple(large_content)

        assert estimated > 0, "Should estimate non-zero tokens for large content"
        assert 5000 <= estimated <= 15000, (
            f"Estimate {estimated} should be reasonable for 40000 chars"
        )

    def test_can_predict_overflow_before_adding(self):
        """Should be able to predict if adding a message would cause overflow."""
        from helen.runtime.token_utils import estimate_tokens_simple
        from helen.runtime.history import Message

        # Current history at 85% usage
        current_tokens = 8500
        max_tokens = 10000
        current_ratio = current_tokens / max_tokens  # 85%

        # Simulated large tool result
        tool_content = "x" * 8000  # ~2000 tokens
        tool_tokens = estimate_tokens_simple(tool_content)

        # Predict new usage
        predicted_total = current_tokens + tool_tokens
        predicted_ratio = predicted_total / max_tokens

        # Should be able to predict overflow
        would_overflow = predicted_ratio > 1.0

        assert would_overflow is True, (
            f"Should predict overflow: current={current_ratio:.0%}, "
            f"tool={tool_tokens}, predicted={predicted_ratio:.0%}"
        )


class TestHardLimitTrim:
    """Test the _hard_limit_trim safety net function (v1.46.24)."""

    def test_hard_limit_preserves_system_messages(self):
        """Hard limit trim preserves all system messages."""
        from helen.runtime.history import Message
        from helen.runtime.graduated_compression import _hard_limit_trim

        messages = [
            Message(role="system", content="You are helpful", _token_count=100, _model="test"),
            Message(role="user", content="Hello", _token_count=500, _model="test"),
            Message(role="assistant", content="Hi", _token_count=500, _model="test"),
            Message(role="user", content="More", _token_count=500, _model="test"),
        ]
        # Total: 1600 tokens, max_tokens: 1000 (160% usage)

        result = _hard_limit_trim(messages, max_tokens=1000)

        # System message must be preserved
        system_msgs = [m for m in result if m.role == "system"]
        assert len(system_msgs) == 1
        assert system_msgs[0].content == "You are helpful"

    def test_hard_limit_keeps_recent_messages(self):
        """Hard limit trim keeps the most recent conversation messages."""
        from helen.runtime.history import Message
        from helen.runtime.graduated_compression import _hard_limit_trim

        messages = [
            Message(role="user", content="First", _token_count=300, _model="test"),
            Message(role="assistant", content="Response 1", _token_count=300, _model="test"),
            Message(role="user", content="Second", _token_count=300, _model="test"),
            Message(role="assistant", content="Response 2", _token_count=300, _model="test"),
            Message(role="user", content="Third", _token_count=300, _model="test"),
            Message(role="assistant", content="Response 3", _token_count=300, _model="test"),
        ]
        # Total: 1800 tokens, max_tokens: 1000 (180% usage)

        result = _hard_limit_trim(messages, max_tokens=1000)

        # Should keep only last 2 conversation messages
        assert len(result) <= 2
        # The most recent should be preserved
        assert any("Response 3" in m.content for m in result)

    def test_hard_limit_handles_empty_history(self):
        """Hard limit trim handles empty history gracefully."""
        from helen.runtime.graduated_compression import _hard_limit_trim

        result = _hard_limit_trim([], max_tokens=1000)
        assert result == []

    def test_hard_limit_respects_pinned_messages(self):
        """Hard limit trim preserves pinned messages."""
        from helen.runtime.history import Message
        from helen.runtime.graduated_compression import _hard_limit_trim

        pinned_msg = Message(
            role="user", content="Important pinned", _token_count=200, _model="test"
        )
        pinned_msg.pinned = True

        messages = [
            pinned_msg,
            Message(role="user", content="Normal 1", _token_count=400, _model="test"),
            Message(role="assistant", content="Normal 2", _token_count=400, _model="test"),
            Message(role="user", content="Normal 3", _token_count=400, _model="test"),
        ]

        result = _hard_limit_trim(messages, max_tokens=1000)

        # Pinned message should be preserved
        pinned_in_result = [m for m in result if getattr(m, 'pinned', False)]
        assert len(pinned_in_result) == 1
        assert pinned_in_result[0].content == "Important pinned"
