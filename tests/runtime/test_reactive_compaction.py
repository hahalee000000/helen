"""Tests for Phase 9B: Reactive Compaction."""

import pytest
from helen.runtime.reactive_compaction import ReactiveCompactor, _estimate_tokens, _is_cjk


class TestReactiveCompactor:
    """Test ReactiveCompactor class."""

    def _make_messages(self, n: int, content_len: int = 100) -> list[dict]:
        """Create n messages with specified content length."""
        messages = []
        for i in range(n):
            messages.append({
                "role": "user",
                "content": f"Message {i}: " + "x" * content_len,
            })
            messages.append({
                "role": "assistant",
                "content": f"Response {i}: " + "y" * content_len,
            })
        return messages

    def test_no_compaction_when_below_threshold(self):
        """No compaction when usage is below threshold."""
        compactor = ReactiveCompactor(structural_threshold=0.90)
        messages = self._make_messages(3, content_len=50)
        max_tokens = 1_000_000  # Very large, usage will be tiny

        result, layer = compactor.check_and_compact(messages, max_tokens)

        assert layer is None
        assert result == messages

    def test_structural_compaction_at_threshold(self):
        """Structural compaction triggers at 90% threshold."""
        compactor = ReactiveCompactor(structural_threshold=0.90)
        # Create enough messages to exceed 90% usage
        messages = self._make_messages(30, content_len=10000)
        max_tokens = 100_000  # Small enough that messages exceed 90%

        result, layer = compactor.check_and_compact(messages, max_tokens)

        assert layer == "reactive_structural"
        assert len(result) < len(messages)

    def test_only_once_per_turn(self):
        """Structural compaction triggers at most once per turn."""
        compactor = ReactiveCompactor(structural_threshold=0.90)
        messages = self._make_messages(30, content_len=10000)
        max_tokens = 100_000

        # First call: should trigger
        result1, layer1 = compactor.check_and_compact(messages, max_tokens)
        assert layer1 == "reactive_structural"

        # Second call (same turn): should NOT trigger
        result2, layer2 = compactor.check_and_compact(result1, max_tokens)
        assert layer2 is None

    def test_reset_turn(self):
        """reset_turn() allows compaction again."""
        compactor = ReactiveCompactor(structural_threshold=0.90)
        messages = self._make_messages(30, content_len=10000)
        max_tokens = 100_000

        compactor.check_and_compact(messages, max_tokens)
        compactor.reset_turn()

        # After reset, should be able to trigger again
        result, layer = compactor.check_and_compact(messages, max_tokens)
        assert layer == "reactive_structural"

    def test_semantic_compaction_at_higher_threshold(self):
        """Semantic compaction triggers at 95% threshold."""
        # Mock LLM client
        def mock_llm(messages):
            return "This is a mock summary."

        compactor = ReactiveCompactor(
            structural_threshold=0.90,
            semantic_threshold=0.95,
            llm_client=mock_llm,
        )
        messages = self._make_messages(30, content_len=10000)
        max_tokens = 80_000  # Very small to exceed 95%

        result, layer = compactor.check_and_compact(messages, max_tokens)

        assert layer == "reactive_semantic"
        assert len(result) < len(messages)
        # Should have a summary message
        assert any("mock summary" in m.get("content", "").lower() for m in result if m.get("role") == "system")

    def test_preserves_system_messages(self):
        """System messages are preserved during compaction."""
        compactor = ReactiveCompactor(structural_threshold=0.90)
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
        ] + self._make_messages(30, content_len=10000)
        max_tokens = 100_000

        result, layer = compactor.check_and_compact(messages, max_tokens)

        assert layer is not None
        # System message should be preserved
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "You are a helpful assistant."

    def test_too_few_messages_no_compaction(self):
        """No compaction if too few messages to compact."""
        compactor = ReactiveCompactor(structural_threshold=0.0)  # Always trigger
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]

        result, layer = compactor.check_and_compact(messages, 100)

        assert layer is None  # Not enough to compact

    def test_empty_messages(self):
        """Empty messages list returns unchanged."""
        compactor = ReactiveCompactor()
        result, layer = compactor.check_and_compact([], 100)

        assert layer is None
        assert result == []


class TestEstimateTokens:
    """Test token estimation helper."""

    def test_empty_string(self):
        assert _estimate_tokens("") == 0

    def test_english_text(self):
        tokens = _estimate_tokens("hello world")
        assert tokens > 0
        # ~11 chars / 4 = ~2.75 -> 2 tokens
        assert 1 <= tokens <= 5

    def test_cjk_text(self):
        tokens = _estimate_tokens("你好世界")
        assert tokens > 0
        # 4 CJK chars / 1.2 = ~3.3 -> 3 tokens
        assert 2 <= tokens <= 6

    def test_mixed_text(self):
        tokens = _estimate_tokens("hello 你好 world 世界")
        assert tokens > 0


class TestIsCjk:
    """Test CJK character detection."""

    def test_chinese(self):
        assert _is_cjk("中") is True
        assert _is_cjk("国") is True

    def test_japanese(self):
        assert _is_cjk("あ") is True  # Hiragana
        assert _is_cjk("カ") is True  # Katakana

    def test_korean(self):
        assert _is_cjk("한") is True

    def test_english(self):
        assert _is_cjk("a") is False
        assert _is_cjk("Z") is False

    def test_punctuation(self):
        assert _is_cjk("。") is True  # CJK period
        assert _is_cjk(".") is False
