"""Tests for context window overflow protection (HLD 3.12).

Tests cover:
- P0: MAX_TOOL_RESULTS_PER_TURN enforcement
- P0: History trimmed and passed to LLM
- P1: Model-aware token estimation
- P1: Context overflow auto-recovery
- P2: History size limit enforcement
- P2: Model-aware MAX_TOKENS
"""

import pytest

from helen.runtime.history import (
    DEFAULT_CONTEXT_WINDOW,
    HISTORY_BUDGET_RATIO,
    MODEL_CONTEXT_WINDOWS,
    HistoryManager,
    Message,
    estimate_tokens,
    get_model_context_window,
)
from helen.runtime.http_llm import (
    MAX_TOOL_RESULTS_PER_TURN,
    _enforce_tool_results_per_turn,
    _is_context_length_error,
    _trim_messages_for_recovery,
)


class TestModelContextWindow:
    """Test model-aware context window lookup."""

    def test_exact_match(self):
        assert get_model_context_window("qwen3.7-plus") == 131072

    def test_prefix_match(self):
        # Date-suffixed model names should match
        assert get_model_context_window("qwen3.7-plus-2024-08") == 131072
        assert get_model_context_window("gpt-4o-mini-2024-07-18") == 128000

    def test_unknown_model_fallback(self):
        assert get_model_context_window("some-unknown-model") == DEFAULT_CONTEXT_WINDOW

    def test_none_model_fallback(self):
        assert get_model_context_window(None) == DEFAULT_CONTEXT_WINDOW

    def test_empty_model_fallback(self):
        assert get_model_context_window("") == DEFAULT_CONTEXT_WINDOW


class TestTokenEstimation:
    """Test character-type-aware token estimation."""

    def test_empty_text(self):
        assert estimate_tokens("") == 0

    def test_english_text(self):
        # ~4 chars per token for English
        tokens = estimate_tokens("hello world")
        assert 2 <= tokens <= 5  # len=11, expect ~3 tokens

    def test_chinese_text(self):
        # ~1.2 chars per token for CJK
        tokens = estimate_tokens("你好世界")
        assert 3 <= tokens <= 5  # 4 CJK chars, expect ~3-4 tokens

    def test_mixed_text(self):
        # Mixed should be between pure English and pure CJK
        mixed = estimate_tokens("hello 你好 world 世界")
        english = estimate_tokens("hello  world ")
        chinese = estimate_tokens("你好世界你好世界你好")
        assert mixed > english
        assert mixed < chinese * 2  # Allow some margin

    def test_minimum_one_token(self):
        # Non-empty text should be at least 1 token
        assert estimate_tokens("a") >= 1
        assert estimate_tokens("你") >= 1


class TestHistoryManagerModelAware:
    """Test HistoryManager with model-aware context window."""

    def test_init_with_model(self):
        hm = HistoryManager(model="qwen3.7-plus")
        assert hm.MAX_TOKENS == 131072

    def test_init_with_gpt4(self):
        hm = HistoryManager(model="gpt-4")
        assert hm.MAX_TOKENS == 8192

    def test_init_with_unknown_model(self):
        hm = HistoryManager(model="unknown")
        assert hm.MAX_TOKENS == DEFAULT_CONTEXT_WINDOW

    def test_init_with_explicit_context_window(self):
        hm = HistoryManager(context_window=50000)
        assert hm.MAX_TOKENS == 50000

    def test_explicit_overrides_model(self):
        hm = HistoryManager(model="gpt-4", context_window=50000)
        assert hm.MAX_TOKENS == 50000

    def test_set_model_updates_context_window(self):
        hm = HistoryManager(model="gpt-4")
        assert hm.MAX_TOKENS == 8192
        hm.set_model("qwen3.7-plus")
        assert hm.MAX_TOKENS == 131072

    def test_estimate_tokens_method(self):
        hm = HistoryManager()
        # Method should work (backward compat)
        tokens = hm.estimate_tokens("hello world")
        assert tokens > 0


class TestHistoryBudget:
    """Test check_budget and trim_history."""

    def test_check_budget_basic(self):
        hm = HistoryManager(context_window=10000)
        budget = hm.check_budget(system_tokens=500, instruction_tokens=300)
        # budget = 10000 - 500 - 300 - 1000 (buffer) = 8200
        assert budget == 8200

    def test_check_budget_no_negative(self):
        hm = HistoryManager(context_window=100)
        budget = hm.check_budget(system_tokens=500, instruction_tokens=300)
        assert budget == 0  # Clamped to 0

    def test_trim_history_under_budget(self):
        hm = HistoryManager(context_window=10000)
        msgs = [Message(role="user", content="hello")]
        trimmed = hm.trim_history(msgs, budget=5000)
        assert len(trimmed) == 1

    def test_trim_history_over_budget(self):
        hm = HistoryManager(context_window=10000)
        # Create 10 messages, each ~50 tokens
        msgs = [Message(role="user", content="x" * 200) for _ in range(10)]
        # Budget for only 3 messages
        trimmed = hm.trim_history(msgs, budget=200)
        assert len(trimmed) < 10
        assert len(trimmed) >= 1

    def test_trim_history_keeps_system_messages(self):
        hm = HistoryManager(context_window=10000)
        msgs = [
            Message(role="system", content="system prompt"),
            Message(role="user", content="x" * 200),
            Message(role="assistant", content="y" * 200),
            Message(role="user", content="z" * 200),
        ]
        # Budget for only 2 messages (~100 tokens)
        trimmed = hm.trim_history(msgs, budget=100)
        # System message should be preserved
        assert any(m.role == "system" for m in trimmed)


class TestHistoryEnforceLimit:
    """Test P2: enforce_limit keeps history bounded."""

    def test_under_limit_no_change(self):
        hm = HistoryManager(context_window=100000)
        msgs = [Message(role="user", content="hello")]
        result = hm.enforce_limit(msgs)
        assert len(result) == 1

    def test_over_limit_compression(self):
        hm = HistoryManager(context_window=1000)
        # Fill with messages that exceed 80% of context window
        msgs = [Message(role="user", content="x" * 200) for _ in range(20)]
        result = hm.enforce_limit(msgs)
        # Should compress: older messages summarized
        assert len(result) < len(msgs)
        # First message should be a summary
        assert result[0].role == "system"
        assert "summary" in result[0].content.lower() or "previous" in result[0].content.lower()

    def test_empty_history(self):
        hm = HistoryManager()
        assert hm.enforce_limit([]) == []


class TestPrepareForLLM:
    """Test prepare_for_llm end-to-end."""

    def test_empty_history(self):
        hm = HistoryManager()
        result = hm.prepare_for_llm([], "system prompt", "hello")
        assert result == []

    def test_basic_preparation(self):
        hm = HistoryManager(context_window=100000)
        msgs = [
            Message(role="user", content="hello"),
            Message(role="assistant", content="hi there"),
        ]
        result = hm.prepare_for_llm(msgs, "system prompt", "new question")
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"

    def test_respects_budget(self):
        hm = HistoryManager(context_window=500)
        # Many large messages
        msgs = [Message(role="user", content="x" * 200) for _ in range(10)]
        result = hm.prepare_for_llm(msgs, "system", "prompt")
        # Should trim to fit budget
        total_content = sum(len(m["content"]) for m in result)
        assert total_content < sum(len(m.content) for m in msgs)


class TestToolResultsPerTurn:
    """Test P0: MAX_TOOL_RESULTS_PER_TURN enforcement."""

    def test_enforcement_under_limit(self):
        calls = [{"function": {"name": f"fn{i}"}} for i in range(5)]
        result = _enforce_tool_results_per_turn(calls)
        assert len(result) == 5

    def test_enforcement_over_limit(self):
        calls = [{"function": {"name": f"fn{i}"}, "id": f"id{i}"} for i in range(20)]
        result = _enforce_tool_results_per_turn(calls)
        assert len(result) == MAX_TOOL_RESULTS_PER_TURN
        # Should keep the first N
        assert result[0]["id"] == "id0"
        assert result[-1]["id"] == f"id{MAX_TOOL_RESULTS_PER_TURN - 1}"

    def test_constant_value(self):
        # Verify the constant is set to a reasonable value
        assert MAX_TOOL_RESULTS_PER_TURN == 10


class TestContextLengthErrorDetection:
    """Test P1: Detecting context-too-large errors."""

    @pytest.mark.parametrize("error_msg", [
        "This model's maximum context length is 131072 tokens",
        "Error code: context_length_exceeded",
        "The request exceeds the model's context window",
        "Maximum context length exceeded",
        "Please reduce the length of your prompt",
        "400 error: too many tokens in request",
    ])
    def test_detects_context_errors(self, error_msg):
        assert _is_context_length_error(error_msg) is True

    @pytest.mark.parametrize("error_msg", [
        "Connection timeout",
        "API key invalid",
        "Rate limit exceeded",
        "Model not found",
        "",
        None,
    ])
    def test_does_not_detect_unrelated_errors(self, error_msg):
        assert _is_context_length_error(error_msg or "") is False


class TestTrimMessagesForRecovery:
    """Test P1: Trimming messages for context overflow recovery."""

    def test_basic_trimming(self):
        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "old1"},
            {"role": "assistant", "content": "old2"},
            {"role": "user", "content": "new1"},
            {"role": "assistant", "content": "new2"},
        ]
        result = _trim_messages_for_recovery(msgs, drop_count=2)
        # System + remaining messages
        assert result[0]["role"] == "system"
        assert len(result) == 3
        assert result[1]["content"] == "new1"

    def test_does_not_trim_too_short(self):
        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "msg"},
        ]
        result = _trim_messages_for_recovery(msgs, drop_count=2)
        assert len(result) == 2  # No change

    def test_keeps_system_message(self):
        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "old"},
            {"role": "user", "content": "new"},
        ]
        result = _trim_messages_for_recovery(msgs, drop_count=1)
        assert result[0]["role"] == "system"


class TestMessageTokenCount:
    """Test Message.token_count caching."""

    def test_lazy_computation(self):
        msg = Message(role="user", content="hello world")
        assert msg._token_count == 0  # Not yet computed
        count = msg.token_count
        assert count > 0
        assert msg._token_count == count  # Cached

    def test_includes_overhead(self):
        msg = Message(role="user", content="hello")
        # Should include 4 tokens overhead for message structure
        assert msg.token_count >= 5  # at least 1 for "hello" + 4 overhead
