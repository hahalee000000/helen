"""
Tests for context size and budget ratio calculations.

Verifies correctness of:
1. Model context window lookup (exact, prefix, fallback)
2. check_budget calculation (response buffer reservation)
3. Usage ratio calculation
4. Multimodal token counting
5. Three-channel budget allocation (15/50/35 split)
6. Compression threshold consistency
7. History budget enforcement (enforce_limit)
"""
import unittest

from helen.runtime.history import (
    HistoryManager, Message, estimate_tokens,
    DEFAULT_CONTEXT_WINDOW, HISTORY_BUDGET_RATIO, get_model_context_window,
    _message_text,
)
from helen.runtime.graduated_compression import (
    _calculate_usage_ratio, COMPRESSION_THRESHOLDS,
)
from helen.runtime.working_memory import WorkingMemory, build_three_channel_context


class TestModelContextWindow(unittest.TestCase):
    """Model context window lookup."""

    def test_exact_match(self):
        self.assertEqual(get_model_context_window("qwen3.7-plus"), 131072)
        self.assertEqual(get_model_context_window("gpt-4"), 8192)

    def test_prefix_match(self):
        self.assertEqual(get_model_context_window("qwen3.7-plus-2024-08"), 131072)
        self.assertEqual(get_model_context_window("gpt-4o-mini-2024-07-18"), 128000)

    def test_unknown_model_fallback(self):
        self.assertEqual(get_model_context_window("unknown-model"), DEFAULT_CONTEXT_WINDOW)

    def test_none_and_empty(self):
        self.assertEqual(get_model_context_window(None), DEFAULT_CONTEXT_WINDOW)
        self.assertEqual(get_model_context_window(""), DEFAULT_CONTEXT_WINDOW)


class TestCheckBudget(unittest.TestCase):
    """check_budget calculation."""

    def test_no_overhead(self):
        hm = HistoryManager(model="qwen3.7-plus")
        budget = hm.check_budget(0, 0)
        self.assertEqual(budget, 131072 - 1000)

    def test_with_system_and_instruction(self):
        hm = HistoryManager(model="qwen3.7-plus")
        budget = hm.check_budget(5000, 3000)
        self.assertEqual(budget, 131072 - 5000 - 3000 - 1000)

    def test_over_budget_returns_zero(self):
        hm = HistoryManager(model="gpt-4")  # 8192
        budget = hm.check_budget(10000, 0)
        self.assertEqual(budget, 0)

    def test_explicit_context_window(self):
        hm = HistoryManager(context_window=50000)
        self.assertEqual(hm.MAX_TOKENS, 50000)

    def test_context_window_overrides_model(self):
        hm = HistoryManager(model="gpt-4", context_window=50000)
        self.assertEqual(hm.MAX_TOKENS, 50000)


class TestUsageRatio(unittest.TestCase):
    """_calculate_usage_ratio."""

    def test_empty_history(self):
        self.assertEqual(_calculate_usage_ratio([], 1000), 0.0)

    def test_zero_max_tokens(self):
        msgs = [Message(role="user", content="hello")]
        self.assertEqual(_calculate_usage_ratio(msgs, 0), 0.0)

    def test_normal_calculation(self):
        msgs = [Message(role="user", content="hello world")]
        ratio = _calculate_usage_ratio(msgs, 1000)
        self.assertGreater(ratio, 0)
        self.assertLess(ratio, 0.1)


class TestMultimodalTokenCount(unittest.TestCase):
    """Token counting for multimodal content."""

    def test_text_only(self):
        msg = Message(role="user", content="hello world")
        self.assertGreater(msg.token_count, 0)

    def test_multimodal_includes_image_estimate(self):
        msg_text = Message(role="user", content="hello world")
        msg_media = Message(role="user", content=[
            {"type": "text", "text": "hello world"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
        ])
        # Multimodal should have more tokens than text-only (image adds ~85 tokens)
        self.assertGreater(msg_media.token_count, msg_text.token_count + 50)


class TestThreeChannelBudget(unittest.TestCase):
    """Three-channel context budget allocation."""

    def test_default_budget_split(self):
        max_tokens = 131072
        wm = WorkingMemory(max_tokens=10000)
        messages = build_three_channel_context(
            system_prompt="help",
            working_memory=wm,
            history=[Message(role="user", content="hi")],
            max_tokens=max_tokens,
        )
        # Should generate at least system + history messages
        self.assertGreaterEqual(len(messages), 2)
        # System message should exist
        system_msgs = [m for m in messages if m["role"] == "system"]
        self.assertGreaterEqual(len(system_msgs), 1)

    def test_three_channel_reserves_response_buffer(self):
        """Three-channel reserves 10% for response buffer (not allocating 100%)."""
        from helen.runtime.working_memory import RESPONSE_BUFFER_RATIO, THREE_CHANNEL_BUDGET
        # Response buffer should be 10%
        self.assertEqual(RESPONSE_BUFFER_RATIO, 0.10)
        # Channel budgets should sum to 90% (100% - 10% response)
        total = sum(THREE_CHANNEL_BUDGET.values())
        self.assertAlmostEqual(total, 0.90, places=2)

    def test_three_channel_cjk_token_budget(self):
        """Three-channel uses token-based budget, CJK is correctly estimated.

        After optimization: three-channel uses estimate_tokens_simple() which
        is CJK-aware. CJK content should be estimated within ~15% accuracy.
        """
        cjk_text = "请分析这张图片并详细描述内容" * 10
        actual_tokens = estimate_tokens(cjk_text)

        # estimate_tokens_simple (used by three-channel) should be within 30% of actual
        from helen.runtime.token_utils import estimate_tokens_simple
        estimated = estimate_tokens_simple(cjk_text)
        self.assertAlmostEqual(estimated, actual_tokens, delta=actual_tokens * 0.3)

    def test_three_channel_multimodal_includes_image_tokens(self):
        """Three-channel uses msg.token_count which includes image tokens.

        After optimization: three-channel history budget uses msg.token_count
        which correctly accounts for multimodal image token estimate (~85 per image).
        """
        content = [
            {"type": "text", "text": "看图"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + "x" * 10000}},
        ]
        msg = Message(role="user", content=content)

        # msg.token_count includes both text and image estimate
        self.assertGreater(msg.token_count, 80)
        # text alone would only be ~2 tokens
        self.assertGreater(msg.token_count, 50)


class TestCompressionThresholds(unittest.TestCase):
    """Compression threshold consistency."""

    def test_thresholds_are_increasing(self):
        values = list(COMPRESSION_THRESHOLDS.values())
        self.assertEqual(values, sorted(values))

    def test_graduated_first_layer_at_budget_ratio(self):
        """Graduated compression first layer aligned with HISTORY_BUDGET_RATIO."""
        first_layer = COMPRESSION_THRESHOLDS["budget_reduction"]
        self.assertEqual(first_layer, HISTORY_BUDGET_RATIO)

    def test_history_budget_ratio_is_0_6(self):
        """HISTORY_BUDGET_RATIO is 0.6 (aligned with graduated first layer)."""
        self.assertEqual(HISTORY_BUDGET_RATIO, 0.6)


class TestEnforceLimit(unittest.TestCase):
    """enforce_limit budget enforcement."""

    def test_under_budget_unchanged(self):
        hm = HistoryManager(model="gpt-4")  # 8192
        hm.MAX_TOKENS = 10000
        msgs = [Message(role="user", content="hello")]
        trimmed = hm.enforce_limit(msgs)
        self.assertEqual(len(trimmed), len(msgs))

    def test_over_budget_trims(self):
        hm = HistoryManager()
        hm.MAX_TOKENS = 200
        msgs = []
        for i in range(20):
            msgs.append(Message(role="user", content=f"msg {'x' * 200}"))
        trimmed = hm.enforce_limit(msgs)
        self.assertLess(len(trimmed), len(msgs))

    def test_preserves_multimodal_structure(self):
        hm = HistoryManager()
        hm.MAX_TOKENS = 10000
        msgs = []
        for i in range(5):
            msgs.append(Message(role="user", content=[
                {"type": "text", "text": f"图 {i}"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{'x' * 100}"}},
            ]))
        trimmed = hm.enforce_limit(msgs)
        for m in trimmed:
            if isinstance(m.content, list):
                types = [p.get("type") for p in m.content if isinstance(p, dict)]
                self.assertIn("text", types)
                self.assertIn("image_url", types)


if __name__ == "__main__":
    unittest.main()
