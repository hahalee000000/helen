"""Tests for platform protocol abstraction and auto-detection."""

import pytest

from helen.runtime.provider_protocol import (
    DashScopeProtocol,
    DeepSeekProtocol,
    KimiProtocol,
    MinimaxProtocol,
    OpenAIProtocol,
    PlatformProtocol,
    VolcengineProtocol,
    ZhipuProtocol,
    detect_protocol,
)


class TestProtocolDetection:
    """Test auto-detection of platform protocol from base_url."""

    def test_detect_dashscope(self):
        """DashScope should be detected from URL."""
        protocol = detect_protocol("https://dashscope.aliyuncs.com/compatible-mode/v1")
        assert isinstance(protocol, DashScopeProtocol)
        assert protocol.name == "dashscope"

    def test_detect_volcengine(self):
        """Volcengine Ark should be detected from URL."""
        protocol = detect_protocol("https://ark.cn-beijing.volces.com/api/v3")
        assert isinstance(protocol, VolcengineProtocol)
        assert protocol.name == "volcengine"

    def test_detect_zhipu(self):
        """Zhipu should be detected from URL."""
        protocol = detect_protocol("https://open.bigmodel.cn/api/paas/v4")
        assert isinstance(protocol, ZhipuProtocol)
        assert protocol.name == "zhipu"

    def test_detect_deepseek(self):
        """DeepSeek should be detected from URL."""
        protocol = detect_protocol("https://api.deepseek.com")
        assert isinstance(protocol, DeepSeekProtocol)
        assert protocol.name == "deepseek"

    def test_detect_minimax_china(self):
        """MiniMax China should be detected from URL."""
        protocol = detect_protocol("https://api.minimaxi.com/v1")
        assert isinstance(protocol, MinimaxProtocol)
        assert protocol.name == "minimax"

    def test_detect_minimax_international(self):
        """MiniMax International should be detected from URL."""
        protocol = detect_protocol("https://api.minimax.io/v1")
        assert isinstance(protocol, MinimaxProtocol)
        assert protocol.name == "minimax"

    def test_detect_kimi(self):
        """Kimi should be detected from URL."""
        protocol = detect_protocol("https://api.moonshot.ai/v1")
        assert isinstance(protocol, KimiProtocol)
        assert protocol.name == "kimi"

    def test_detect_openai_default(self):
        """Unknown URL should default to OpenAI protocol."""
        protocol = detect_protocol("https://api.openai.com/v1")
        assert isinstance(protocol, OpenAIProtocol)
        assert protocol.name == "openai"

    def test_detect_unknown_provider(self):
        """Unknown provider should default to OpenAI protocol."""
        protocol = detect_protocol("https://some-unknown-api.com/v1")
        assert isinstance(protocol, OpenAIProtocol)


class TestDashScopeProtocol:
    """Test DashScope protocol specifics."""

    def test_build_payload_with_thinking(self):
        """DashScope uses enable_thinking parameter."""
        protocol = DashScopeProtocol()
        payload = {"model": "qwen-plus", "messages": []}
        result = protocol.build_request_payload(
            payload,
            model_id="qwen-plus",
            thinking_enabled=True,
            reasoning_effort="high",
        )
        assert result["enable_thinking"] is True
        assert result["thinking_budget"] == 16384  # high = 16384

    def test_build_payload_without_thinking(self):
        """Without thinking, no extra fields added."""
        protocol = DashScopeProtocol()
        payload = {"model": "qwen-plus", "messages": []}
        result = protocol.build_request_payload(
            payload,
            model_id="qwen-plus",
            thinking_enabled=False,
        )
        assert "enable_thinking" not in result


class TestZhipuProtocol:
    """Test Zhipu protocol specifics."""

    def test_tool_choice_auto_only(self):
        """Zhipu only supports tool_choice='auto'."""
        protocol = ZhipuProtocol()
        assert protocol.supports_tool_choice("auto") is True
        assert protocol.supports_tool_choice("required") is False
        assert protocol.supports_tool_choice("none") is False

    def test_build_payload_with_thinking(self):
        """Zhipu uses thinking.type parameter."""
        protocol = ZhipuProtocol()
        payload = {"model": "glm-5.2", "messages": []}
        result = protocol.build_request_payload(
            payload,
            model_id="glm-5.2",
            thinking_enabled=True,
            reasoning_effort="max",
        )
        assert result["thinking"] == {"type": "enabled"}
        assert result["reasoning_effort"] == "max"


class TestDeepSeekProtocol:
    """Test DeepSeek protocol specifics."""

    def test_build_payload_with_thinking(self):
        """DeepSeek uses thinking.type parameter."""
        protocol = DeepSeekProtocol()
        payload = {"model": "deepseek-v4-pro", "messages": []}
        result = protocol.build_request_payload(
            payload,
            model_id="deepseek-v4-pro",
            thinking_enabled=True,
            reasoning_effort="high",
        )
        assert result["thinking"] == {"type": "enabled"}
        assert result["reasoning_effort"] == "high"


class TestMinimaxProtocol:
    """Test MiniMax protocol specifics."""

    def test_build_payload_always_sets_reasoning_split(self):
        """MiniMax always sets reasoning_split=true."""
        protocol = MinimaxProtocol()
        payload = {"model": "MiniMax-M3", "messages": []}
        result = protocol.build_request_payload(
            payload,
            model_id="MiniMax-M3",
            thinking_enabled=False,
        )
        assert result["reasoning_split"] is True

    def test_parse_response_with_reasoning_details(self):
        """MiniMax returns reasoning_details in response."""
        protocol = MinimaxProtocol()
        response_data = {
            "choices": [{
                "message": {
                    "content": "Answer",
                    "reasoning_content": "Thinking",
                    "reasoning_details": [{"type": "reasoning", "text": "..."}],
                },
                "finish_reason": "stop",
            }],
        }
        result = protocol.parse_response(response_data)
        assert result["content"] == "Answer"
        assert result["reasoning_content"] == "Thinking"
        assert "reasoning_details" in result


class TestKimiProtocol:
    """Test Kimi protocol specifics."""

    def test_extract_streaming_usage_from_choices(self):
        """Kimi: usage at choices[0].usage, not top-level."""
        protocol = KimiProtocol()
        chunk = {
            "choices": [{
                "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            }],
        }
        usage = protocol.extract_streaming_usage(chunk)
        assert usage == {"prompt_tokens": 10, "completion_tokens": 20}

    def test_extract_streaming_usage_fallback(self):
        """Kimi: fallback to top-level usage if not in choices."""
        protocol = KimiProtocol()
        chunk = {
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            "choices": [],
        }
        usage = protocol.extract_streaming_usage(chunk)
        assert usage == {"prompt_tokens": 10, "completion_tokens": 20}


class TestVolcengineProtocol:
    """Test Volcengine protocol specifics."""

    def test_build_payload_with_thinking(self):
        """Volcengine uses thinking.type parameter."""
        protocol = VolcengineProtocol()
        payload = {"model": "doubao-pro", "messages": []}
        result = protocol.build_request_payload(
            payload,
            model_id="doubao-pro",
            thinking_enabled=True,
        )
        assert result["thinking"] == {"type": "enabled"}

    def test_parse_response_with_encrypted_content(self):
        """Volcengine: encrypted_content takes priority."""
        protocol = VolcengineProtocol()
        response_data = {
            "choices": [{
                "message": {
                    "content": "Answer",
                    "reasoning_content": "Normal thinking",
                    "encrypted_content": "Encrypted thinking",
                },
                "finish_reason": "stop",
            }],
        }
        result = protocol.parse_response(response_data)
        assert result["reasoning_content"] == "Encrypted thinking"


class TestBaseProtocol:
    """Test base protocol default behavior."""

    def test_parse_response_standard(self):
        """Standard response parsing."""
        protocol = PlatformProtocol()
        response_data = {
            "choices": [{
                "message": {
                    "content": "Hello",
                    "reasoning_content": "",
                    "tool_calls": [],
                },
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }
        result = protocol.parse_response(response_data)
        assert result["content"] == "Hello"
        assert result["reasoning_content"] == ""
        assert result["tool_calls"] == []
        assert result["finish_reason"] == "stop"
        assert result["usage"] == {"prompt_tokens": 10, "completion_tokens": 20}

    def test_parse_error_standard(self):
        """Standard error parsing."""
        protocol = PlatformProtocol()
        response_body = {
            "error": {
                "message": "Invalid API key",
                "type": "authentication_error",
            }
        }
        error_msg = protocol.parse_error(401, response_body)
        assert error_msg == "Invalid API key"

    def test_is_context_overflow_error(self):
        """Context overflow detection."""
        protocol = PlatformProtocol()
        assert protocol.is_context_overflow_error("context length exceeded") is True
        assert protocol.is_context_overflow_error("maximum context length") is True
        assert protocol.is_context_overflow_error("too many tokens") is True
        assert protocol.is_context_overflow_error("normal error") is False


class TestBackwardCompatibility:
    """Ensure protocol abstraction doesn't break existing behavior."""

    def test_default_protocol_is_openai(self):
        """Unknown providers should use OpenAI protocol."""
        protocol = detect_protocol("https://unknown-api.com/v1")
        assert isinstance(protocol, OpenAIProtocol)

    def test_payload_building_preserves_existing_fields(self):
        """Protocol should not remove existing payload fields."""
        protocol = OpenAIProtocol()
        payload = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello"}],
            "temperature": 0.7,
            "tools": [{"type": "function", "function": {"name": "test"}}],
            "max_tokens": 100,
        }
        result = protocol.build_request_payload(
            payload,
            model_id="gpt-4",
            thinking_enabled=False,
        )
        # All original fields should be preserved
        assert result["model"] == "gpt-4"
        assert result["messages"] == payload["messages"]
        assert result["temperature"] == 0.7
        assert result["tools"] == payload["tools"]
        assert result["max_tokens"] == 100


class TestVolcengineEndpointIdValidation:
    """Test Doubao Endpoint ID validation (v1.37)."""

    def test_endpoint_id_accepted_without_warning(self, caplog):
        """Valid endpoint ID (ep-XXXXX) should not log warning."""
        import logging
        protocol = VolcengineProtocol()
        with caplog.at_level(logging.DEBUG, logger='helen.runtime.provider_protocol'):
            payload = protocol.build_request_payload(
                {"model": "ep-20240918xxxxx-xxxxx", "messages": []},
                model_id="ep-20240918xxxxx-xxxxx",
            )
        # No warning about endpoint ID should be logged
        assert not any("instead of Endpoint ID" in r.message for r in caplog.records)

    def test_model_name_logs_debug_warning(self, caplog):
        """Direct model name should log debug warning for production usage."""
        import logging
        protocol = VolcengineProtocol()
        with caplog.at_level(logging.DEBUG, logger='helen.runtime.provider_protocol'):
            protocol.build_request_payload(
                {"model": "doubao-pro-128k", "messages": []},
                model_id="doubao-pro-128k",
            )
        # Debug warning should be logged
        assert any("instead of Endpoint ID" in r.message for r in caplog.records)

    def test_empty_model_id_no_validation(self):
        """Empty model ID should skip validation."""
        protocol = VolcengineProtocol()
        # Should not raise
        payload = protocol.build_request_payload(
            {"model": "", "messages": []},
            model_id="",
        )
        assert payload["model"] == ""
