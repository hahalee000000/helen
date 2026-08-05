"""Tests for model capabilities detection."""

import pytest

from helen.runtime.model_capabilities import (
    ModelCapabilities,
    get_model_capabilities,
    list_registered_models,
)


class TestModelCapabilities:
    """Test model capabilities detection."""

    def test_get_qwen3_max_capabilities(self):
        """Qwen3-max should support thinking."""
        caps = get_model_capabilities("qwen3-max")
        assert caps.supports_thinking is True
        assert caps.thinking_enabled_by_default is False
        assert caps.reasoning_content_streaming == "incremental"

    def test_get_deepseek_v4_capabilities(self):
        """DeepSeek V4 should have mutually_exclusive streaming."""
        caps = get_model_capabilities("deepseek-v4-pro")
        assert caps.supports_thinking is True
        assert caps.reasoning_content_streaming == "mutually_exclusive"

    def test_get_glm_47_forced_thinking(self):
        """GLM-4.7 has forced thinking."""
        caps = get_model_capabilities("glm-4.7")
        assert caps.supports_thinking is True
        assert caps.forced_thinking is True
        assert caps.supports_tool_choice_required is False

    def test_get_minimax_m3_cumulative_streaming(self):
        """MiniMax M3 has cumulative reasoning_details streaming."""
        caps = get_model_capabilities("MiniMax-M3")
        assert caps.supports_thinking is True
        assert caps.has_reasoning_details is True
        assert caps.reasoning_content_streaming == "cumulative"

    def test_get_doubao_encrypted_content(self):
        """Doubao has encrypted_content field."""
        caps = get_model_capabilities("doubao-seed-1.6-thinking")
        assert caps.supports_thinking is True
        assert caps.has_encrypted_content is True

    def test_prefix_matching(self):
        """Model ID prefix should match registered model."""
        # "qwen3-max-2024" should match "qwen3-max"
        caps = get_model_capabilities("qwen3-max-2024")
        assert caps.supports_thinking is True

    def test_unknown_model_defaults(self):
        """Unknown model should return sensible defaults."""
        caps = get_model_capabilities("unknown-model-xyz")
        assert caps.supports_thinking is True  # Default: assume supported
        assert caps.reasoning_content_streaming == "incremental"

    def test_none_model_defaults(self):
        """None model should return defaults."""
        caps = get_model_capabilities(None)
        assert caps.supports_thinking is True
        assert caps.reasoning_content_streaming == "incremental"

    def test_list_registered_models(self):
        """Should return list of registered model IDs."""
        models = list_registered_models()
        assert isinstance(models, list)
        assert len(models) > 0
        assert "qwen3-max" in models
        assert "deepseek-v4-pro" in models
        assert "glm-5.2" in models


class TestModelCapabilitiesDataclass:
    """Test ModelCapabilities dataclass."""

    def test_default_values(self):
        """Default values should be sensible."""
        caps = ModelCapabilities()
        assert caps.supports_thinking is True
        assert caps.thinking_enabled_by_default is False
        assert caps.forced_thinking is False
        assert caps.supports_tool_choice_required is True
        assert caps.supports_tool_choice_none is True
        assert caps.reasoning_content_streaming == "incremental"
        assert caps.has_encrypted_content is False
        assert caps.has_reasoning_details is False
        assert caps.default_temperature == 1.0

    def test_custom_values(self):
        """Should accept custom values."""
        caps = ModelCapabilities(
            supports_thinking=False,
            forced_thinking=True,
            reasoning_content_streaming="cumulative",
            default_temperature=0.7,
        )
        assert caps.supports_thinking is False
        assert caps.forced_thinking is True
        assert caps.reasoning_content_streaming == "cumulative"
        assert caps.default_temperature == 0.7
