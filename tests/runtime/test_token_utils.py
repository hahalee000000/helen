"""Tests for shared token_utils module."""

import pytest
from helen.runtime.token_utils import (
    is_cjk,
    estimate_tokens_simple,
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
