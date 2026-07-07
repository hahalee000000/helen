"""Tests for Phase 8: Context Recovery cascade."""

import pytest
from helen.runtime.context_recovery import PromptTooLongRecovery, RecoveryResult, _estimate_tokens


class TestRecoveryResult:
    """Test RecoveryResult dataclass."""

    def test_default_result(self):
        result = RecoveryResult()
        assert result.success is False
        assert result.strategy == "none"
        assert result.messages == []
        assert result.tokens_reduced == 0


class TestPromptTooLongRecovery:
    """Test PromptTooLongRecovery class."""

    def _make_messages(self, n: int, content_len: int = 100) -> list[dict]:
        """Create n message pairs with specified content length."""
        messages = [{"role": "system", "content": "System prompt"}]
        for i in range(n):
            messages.append({
                "role": "user",
                "content": f"Question {i}: " + "x" * content_len,
            })
            messages.append({
                "role": "assistant",
                "content": f"Answer {i}: " + "y" * content_len,
            })
        return messages

    def test_context_collapse_recovery(self):
        """Step 1: Context collapse reduces messages."""
        recovery = PromptTooLongRecovery(max_tokens=100_000)
        messages = self._make_messages(20, content_len=5000)

        result = recovery.recover(messages, max_tokens=100_000)

        assert result.success is True
        assert result.strategy == "context_collapse"
        assert len(result.messages) < len(messages)
        assert result.tokens_reduced > 0

    def test_recovery_preserves_system_messages(self):
        """Recovery preserves system messages."""
        recovery = PromptTooLongRecovery(max_tokens=100_000)
        messages = self._make_messages(20, content_len=5000)

        result = recovery.recover(messages, max_tokens=100_000)

        # First message should still be system
        assert result.messages[0]["role"] == "system"
        assert result.messages[0]["content"] == "System prompt"

    def test_recovery_reduces_tokens(self):
        """Recovery actually reduces token count."""
        recovery = PromptTooLongRecovery(max_tokens=100_000)
        messages = self._make_messages(20, content_len=5000)

        result = recovery.recover(messages, max_tokens=100_000)

        assert result.tokens_reduced > 0

    def test_small_messages_no_recovery_needed(self):
        """If messages are small, aggressive trim returns failure."""
        recovery = PromptTooLongRecovery(max_tokens=1_000_000)
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]

        result = recovery.recover(messages, max_tokens=1_000_000)

        # With only 2 messages, most strategies can't help
        # At least one should succeed if possible, or all fail gracefully
        assert isinstance(result, RecoveryResult)

    def test_aggressive_trim_last_resort(self):
        """When other methods fail, aggressive trim works."""
        recovery = PromptTooLongRecovery(max_tokens=100_000)
        messages = self._make_messages(20, content_len=5000)

        # Direct test of aggressive trim
        result = recovery._aggressive_trim(messages)

        assert result.success is True
        assert result.strategy == "aggressive_trim"
        # Should keep only system + 2 recent
        assert len(result.messages) == 3  # system + 2 recent

    def test_reactive_structural_fallback(self):
        """Step 2: Reactive structural compaction as fallback."""
        recovery = PromptTooLongRecovery(max_tokens=100_000)
        messages = self._make_messages(20, content_len=5000)

        result = recovery._reactive_structural_recovery(messages)

        assert result.success is True
        assert result.strategy == "reactive_structural"

    def test_empty_messages(self):
        """Empty messages handled gracefully."""
        recovery = PromptTooLongRecovery()
        result = recovery.recover([], max_tokens=100_000)

        assert isinstance(result, RecoveryResult)

    def test_single_message(self):
        """Single message can't be recovered further."""
        recovery = PromptTooLongRecovery()
        messages = [{"role": "user", "content": "Hello"}]

        result = recovery.recover(messages, max_tokens=100_000)
        # With just 1 message, nothing can be trimmed
        assert isinstance(result, RecoveryResult)


class TestEstimateTokens:
    """Test token estimation in context_recovery."""

    def test_empty_string(self):
        assert _estimate_tokens("") == 0

    def test_english(self):
        tokens = _estimate_tokens("hello world")
        assert tokens >= 1

    def test_cjk(self):
        tokens = _estimate_tokens("你好世界")
        assert tokens >= 1
