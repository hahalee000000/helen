"""Tests for shared token_utils module."""

import pytest
from helen.runtime.token_utils import (
    is_cjk,
    is_cjk_codepoint,
    estimate_tokens_simple,
    estimate_messages_tokens,
    calculate_usage_ratio_from_dicts,
    FILE_EXTENSION_PATTERN,
)


class TestIsCjk:
    """Test CJK character detection."""

    def test_chinese(self):
        assert is_cjk("中") is True
        assert is_cjk("国") is True

    def test_japanese(self):
        assert is_cjk("あ") is True  # Hiragana
        assert is_cjk("カ") is True  # Katakana

    def test_korean(self):
        assert is_cjk("한") is True

    def test_english(self):
        assert is_cjk("a") is False
        assert is_cjk("Z") is False

    def test_punctuation(self):
        assert is_cjk("。") is True  # CJK period
        assert is_cjk(".") is False

    def test_cjk_compatibility(self):
        # 0xF900-0xFAFF: CJK Compatibility Ideographs
        assert is_cjk(chr(0xF900)) is True
        assert is_cjk(chr(0xFAFF)) is True


class TestIsCjkCodepoint:
    """Test CJK codepoint detection (integer version)."""

    def test_chinese(self):
        assert is_cjk_codepoint(0x4E2D) is True  # 中

    def test_english(self):
        assert is_cjk_codepoint(ord('a')) is False


class TestEstimateTokensSimple:
    """Test simple token estimation."""

    def test_empty_string(self):
        assert estimate_tokens_simple("") == 0

    def test_english_text(self):
        tokens = estimate_tokens_simple("hello world")
        assert tokens >= 1

    def test_cjk_text(self):
        tokens = estimate_tokens_simple("你好世界")
        assert tokens >= 1

    def test_mixed_text(self):
        tokens = estimate_tokens_simple("hello 你好 world")
        assert tokens >= 1

    def test_longer_text(self):
        tokens = estimate_tokens_simple("x" * 1000)
        # ~250 tokens for 1000 English chars
        assert 200 <= tokens <= 300


class TestEstimateMessagesTokens:
    """Test message-level token estimation."""

    def test_empty_list(self):
        assert estimate_messages_tokens([]) == 0

    def test_single_message(self):
        messages = [{"role": "user", "content": "hello"}]
        tokens = estimate_messages_tokens(messages)
        assert tokens > 0

    def test_multiple_messages(self):
        messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ]
        tokens = estimate_messages_tokens(messages)
        # 2 messages + 4 overhead each
        assert tokens > 0

    def test_message_without_content(self):
        messages = [{"role": "user"}]  # No content key
        tokens = estimate_messages_tokens(messages)
        assert tokens == 0


class TestCalculateUsageRatio:
    """Test usage ratio calculation."""

    def test_empty_messages(self):
        assert calculate_usage_ratio_from_dicts([], 100000) == 0.0

    def test_zero_max_tokens(self):
        messages = [{"role": "user", "content": "hello"}]
        assert calculate_usage_ratio_from_dicts(messages, 0) == 0.0

    def test_small_usage(self):
        messages = [{"role": "user", "content": "hello"}]
        ratio = calculate_usage_ratio_from_dicts(messages, 1_000_000)
        assert 0 < ratio < 0.01  # Very small usage

    def test_larger_usage(self):
        messages = [{"role": "user", "content": "x" * 10000}]
        ratio = calculate_usage_ratio_from_dicts(messages, 10000)
        # 10000 chars / 4 = ~2500 tokens + 4 overhead = ~2504 / 10000 = ~0.25
        assert 0.1 < ratio < 0.5


class TestFileExtensionPattern:
    """Test file extension regex pattern."""

    def test_python_file(self):
        import re
        pattern = FILE_EXTENSION_PATTERN
        assert re.search(pattern, "path/to/file.py")
        assert re.search(pattern, "main.py")

    def test_json_file(self):
        import re
        assert re.search(FILE_EXTENSION_PATTERN, "config.json")

    def test_helen_file(self):
        import re
        assert re.search(FILE_EXTENSION_PATTERN, "program.helen")

    def test_multiple_extensions(self):
        import re
        text = "Files: main.py, config.json, data.yaml"
        matches = re.findall(FILE_EXTENSION_PATTERN, text)
        assert len(matches) == 3
