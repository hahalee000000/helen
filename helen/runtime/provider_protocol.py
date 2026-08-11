"""Platform-level protocol abstraction for OpenAI-compatible LLM providers.

Protocol is determined by the PLATFORM (base_url), not the model.
- DashScope: ALL models use same protocol (Qwen + DeepSeek unified)
- Volcengine Ark: ALL models use same protocol (Doubao + third-party unified)
- Direct APIs: each provider has its own protocol

This module provides:
- PlatformProtocol: Base class for platform-specific protocol handling
- DashScopeProtocol, VolcengineProtocol, ZhipuProtocol, etc.
- detect_protocol(): Auto-detect protocol from base_url
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base Protocol
# ---------------------------------------------------------------------------


class PlatformProtocol:
    """Platform-level protocol handling.

    Determined by base_url. Handles protocol FORMAT differences.
    Default implementation = standard OpenAI protocol.
    """

    name: str = "openai"

    # --- Request Building ---

    def build_request_payload(
        self,
        base_payload: dict[str, Any],
        *,
        model_id: str,
        thinking_enabled: bool = False,
        reasoning_effort: str | None = None,
    ) -> dict[str, Any]:
        """Transform payload into platform-specific format.

        Default: return as-is (OpenAI compatible).
        Override: add provider-specific fields.
        """
        return base_payload

    def supports_tool_choice(self, value: str) -> bool:
        """Check if platform supports given tool_choice value.

        Zhipu: only "auto"
        Others: "auto", "none", "required", specific function
        """
        return True

    def sanitize_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transform messages into platform-specific format.

        Default: return as-is.
        Override: remove unsupported fields, transform formats.
        """
        return messages

    # --- Response Parsing ---

    def parse_response(self, response_data: dict[str, Any]) -> dict[str, Any]:
        """Parse platform-specific response into standard format.

        Standard: {content, reasoning_content, tool_calls, finish_reason, usage}
        Default: extract from choices[0].message (OpenAI standard).
        """
        choice = response_data.get("choices", [{}])[0]
        message = choice.get("message", {})
        return {
            "content": message.get("content", ""),
            "reasoning_content": message.get("reasoning_content", ""),
            "tool_calls": message.get("tool_calls", []),
            "finish_reason": choice.get("finish_reason", "stop"),
            "usage": response_data.get("usage", {}),
        }

    def parse_streaming_delta(
        self,
        delta: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Parse streaming delta into standard format.

        Standard: {content, reasoning_content, tool_calls, finish_reason}
        Default: extract from delta dict (OpenAI standard).

        Args:
            delta: Raw delta from SSE chunk
            context: Mutable dict for tracking state across chunks
        """
        return {
            "content": delta.get("content", ""),
            "reasoning_content": delta.get("reasoning_content", ""),
            "tool_calls": delta.get("tool_calls", []),
            "finish_reason": delta.get("finish_reason"),
        }

    def extract_streaming_usage(self, chunk: dict[str, Any]) -> dict[str, Any] | None:
        """Extract usage from streaming chunk.

        Kimi: usage at choices[0].usage (not top-level)
        Others: usage at top-level chunk["usage"]
        """
        return chunk.get("usage")

    # --- Error Handling ---

    def parse_error(self, status_code: int, response_body: dict[str, Any]) -> str:
        """Parse platform-specific error format into human-readable string.

        Default: extract from error.message (OpenAI standard).
        """
        error = response_body.get("error", {})
        if isinstance(error, dict):
            return error.get("message", str(response_body))
        return str(response_body)

    def is_context_overflow_error(self, error_msg: str) -> bool:
        """Check if error indicates context window overflow."""
        markers = (
            "context length",
            "maximum context",
            "too many tokens",
            "reduce your prompt",
            "context overflow",
            "max_tokens",
        )
        return any(m in error_msg.lower() for m in markers)


# ---------------------------------------------------------------------------
# Platform Implementations
# ---------------------------------------------------------------------------


class DashScopeProtocol(PlatformProtocol):
    """阿里云百炼 (DashScope) — unified protocol for all models.

    ALL models (Qwen + DeepSeek + third-party) use the same protocol.
    reasoning_content is always a separate field (not embedded in content).
    """

    name = "dashscope"

    def build_request_payload(
        self,
        base_payload: dict[str, Any],
        *,
        model_id: str,
        thinking_enabled: bool = False,
        reasoning_effort: str | None = None,
    ) -> dict[str, Any]:
        if thinking_enabled:
            base_payload["enable_thinking"] = True
            if reasoning_effort:
                # Map effort to thinking_budget
                budget_map = {"low": 1024, "medium": 4096, "high": 16384, "max": 32768}
                base_payload["thinking_budget"] = budget_map.get(reasoning_effort, 4096)
        return base_payload


class VolcengineProtocol(PlatformProtocol):
    """火山引擎方舟 (Volcengine Ark) — unified protocol for all models.

    ALL models (Doubao + DeepSeek + GLM + third-party) use the same protocol.
    Uses Endpoint ID (ep-XXXXX) in model field.
    """

    name = "volcengine"

    def build_request_payload(
        self,
        base_payload: dict[str, Any],
        *,
        model_id: str,
        thinking_enabled: bool = False,
        reasoning_effort: str | None = None,
    ) -> dict[str, Any]:
        # v1.37: Validate Endpoint ID format for production usage
        self._validate_endpoint_id(model_id)
        if thinking_enabled:
            base_payload["thinking"] = {"type": "enabled"}
        return base_payload

    def _validate_endpoint_id(self, model_id: str) -> None:
        """Validate Doubao Endpoint ID format (v1.37).

        Production usage should use Endpoint IDs (ep-XXXXX format).
        Direct model names (e.g., doubao-pro-128k) work for preset endpoints
        but are not recommended for production. Logs a warning if not an endpoint ID.
        """
        if not model_id:
            return
        # Endpoint IDs follow the pattern: ep-YYYYMMDDxxxxx-xxxxx
        if model_id.startswith("ep-"):
            return  # Valid endpoint ID
        # Direct model name - warn for production usage
        logger.debug(
            "Volcengine Ark: using model name '%s' instead of Endpoint ID. "
            "For production, create an endpoint in the Ark console and use "
            "its ID (ep-XXXXX) for better stability and version control.",
            model_id,
        )

    def parse_response(self, response_data: dict[str, Any]) -> dict[str, Any]:
        result = super().parse_response(response_data)
        # Doubao: encrypted_content takes priority over reasoning_content
        choice = response_data.get("choices", [{}])[0]
        message = choice.get("message", {})
        encrypted = message.get("encrypted_content")
        if encrypted:
            result["reasoning_content"] = encrypted
        return result


class ZhipuProtocol(PlatformProtocol):
    """智谱AI (Zhipu/GLM) — direct API protocol.

    Key limitations:
    - tool_choice only supports "auto"
    - GLM-4.7 has forced thinking (cannot disable)
    - Temperature range [0.0, 1.0] (narrower than OpenAI)
    """

    name = "zhipu"

    def build_request_payload(
        self,
        base_payload: dict[str, Any],
        *,
        model_id: str,
        thinking_enabled: bool = False,
        reasoning_effort: str | None = None,
    ) -> dict[str, Any]:
        if thinking_enabled:
            base_payload["thinking"] = {"type": "enabled"}
            if reasoning_effort:
                base_payload["reasoning_effort"] = reasoning_effort
        return base_payload

    def supports_tool_choice(self, value: str) -> bool:
        # Zhipu only supports "auto"
        return value == "auto"


class DeepSeekProtocol(PlatformProtocol):
    """DeepSeek — direct API protocol.

    Critical streaming behavior:
    - reasoning_content and content are MUTUALLY EXCLUSIVE per chunk
    - deepseek-reasoner (R1) always thinks, no toggle
    - Requires reasoning_content in multi-turn tool calls (400 error if missing)
    """

    name = "deepseek"

    def build_request_payload(
        self,
        base_payload: dict[str, Any],
        *,
        model_id: str,
        thinking_enabled: bool = False,
        reasoning_effort: str | None = None,
    ) -> dict[str, Any]:
        if thinking_enabled:
            base_payload["thinking"] = {"type": "enabled"}
        if reasoning_effort:
            base_payload["reasoning_effort"] = reasoning_effort
        return base_payload


class MinimaxProtocol(PlatformProtocol):
    """MiniMax — direct API protocol.

    Critical differences:
    - reasoning_split=true to get reasoning_content field
    - reasoning_details is CUMULATIVE in streaming (must compute delta)
    - M3 supports Interleaved Thinking (reason between tool calls)
    - M2.x always thinks via <think> tags (can leak into content)
    """

    name = "minimax"

    def build_request_payload(
        self,
        base_payload: dict[str, Any],
        *,
        model_id: str,
        thinking_enabled: bool = False,
        reasoning_effort: str | None = None,
    ) -> dict[str, Any]:
        # Always set reasoning_split=true to get reasoning_content field
        base_payload["reasoning_split"] = True
        if thinking_enabled:
            base_payload["thinking"] = {"type": "adaptive"}
        return base_payload

    def parse_response(self, response_data: dict[str, Any]) -> dict[str, Any]:
        result = super().parse_response(response_data)
        # MiniMax: reasoning_details is structured array
        choice = response_data.get("choices", [{}])[0]
        message = choice.get("message", {})
        if "reasoning_details" in message:
            result["reasoning_details"] = message["reasoning_details"]
        return result

    def parse_streaming_delta(
        self,
        delta: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """MiniMax: reasoning_details is cumulative, must compute delta."""
        result = {
            "content": delta.get("content", ""),
            "reasoning_content": delta.get("reasoning_content", ""),
            "tool_calls": delta.get("tool_calls", []),
            "finish_reason": delta.get("finish_reason"),
        }

        # Handle cumulative reasoning_details
        if "reasoning_details" in delta:
            prev_total = context.get("reasoning_details_total", "")
            current_total = delta["reasoning_details"]
            if isinstance(current_total, str) and current_total.startswith(prev_total):
                # Compute incremental delta
                result["reasoning_content"] = current_total[len(prev_total):]
            context["reasoning_details_total"] = current_total

        return result


class KimiProtocol(PlatformProtocol):
    """Kimi/Moonshot — direct API protocol.

    Key differences:
    - Usage in streaming at choices[0].usage (not top-level)
    - $web_search builtin tool (type: "builtin_function")
    - Partial Mode for prefill
    - prompt_cache_key for explicit caching
    """

    name = "kimi"

    def build_request_payload(
        self,
        base_payload: dict[str, Any],
        *,
        model_id: str,
        thinking_enabled: bool = False,
        reasoning_effort: str | None = None,
    ) -> dict[str, Any]:
        if reasoning_effort:
            base_payload["reasoning_effort"] = reasoning_effort
        return base_payload

    def extract_streaming_usage(self, chunk: dict[str, Any]) -> dict[str, Any] | None:
        # Kimi: usage at choices[0].usage, not top-level
        choices = chunk.get("choices", [])
        if choices:
            usage = choices[0].get("usage")
            if usage:
                return usage
        return chunk.get("usage")


class OpenAIProtocol(PlatformProtocol):
    """Standard OpenAI protocol (default).

    All methods use default implementation.
    """

    name = "openai"


# ---------------------------------------------------------------------------
# Auto-Detection
# ---------------------------------------------------------------------------


_PLATFORM_PATTERNS = [
    # --- Aggregator Platforms (统一协议，所有模型相同) ---
    ("dashscope.aliyuncs.com", DashScopeProtocol),
    ("ark.cn-beijing.volces.com", VolcengineProtocol),

    # --- Direct Provider APIs ---
    ("open.bigmodel.cn", ZhipuProtocol),
    ("api.deepseek.com", DeepSeekProtocol),
    ("api.minimaxi.com", MinimaxProtocol),
    ("api.minimax.io", MinimaxProtocol),
    ("api.moonshot.ai", KimiProtocol),
]

# Name → Protocol class lookup (includes "openai" fallback)
_PROTOCOL_NAME_MAP: dict[str, type[PlatformProtocol]] = {
    cls.name: cls for _, cls in _PLATFORM_PATTERNS
}
_PROTOCOL_NAME_MAP["openai"] = OpenAIProtocol


def detect_protocol(base_url: str, protocol_name: str | None = None) -> PlatformProtocol:
    """Detect platform protocol from base_url or explicit name.

    Detection priority:
    1. Explicit protocol_name (from config.yaml) — highest priority
    2. URL pattern matching (_PLATFORM_PATTERNS)
    3. Fallback to OpenAIProtocol

    Protocol is determined by the PLATFORM, not the model.
    - DashScope: ALL models use same protocol (Qwen + DeepSeek unified)
    - Volcengine Ark: ALL models use same protocol (Doubao + third-party unified)
    - Direct APIs: each provider has its own protocol

    Args:
        base_url: Provider API base URL for pattern matching
        protocol_name: Explicit protocol name from config (e.g. "deepseek")

    Examples:
    - detect_protocol("dashscope.aliyuncs.com") → DashScopeProtocol
    - detect_protocol("unknown.com", protocol_name="deepseek") → DeepSeekProtocol
    - detect_protocol("unknown.com") → OpenAIProtocol (fallback)
    """
    # Step 1: Check explicit protocol name from config
    if protocol_name:
        protocol_class = _PROTOCOL_NAME_MAP.get(protocol_name)
        if protocol_class:
            logger.debug(f"Using protocol from config: {protocol_name}")
            return protocol_class()
        else:
            logger.debug(f"Unknown protocol name {protocol_name!r}, falling back to URL detection")

    # Step 2: URL pattern matching
    for pattern, protocol_class in _PLATFORM_PATTERNS:
        if pattern in base_url:
            logger.debug(f"Detected platform protocol: {protocol_class.name} (from {pattern})")
            return protocol_class()

    logger.debug(f"No platform pattern matched for {base_url}, using OpenAIProtocol")
    return OpenAIProtocol()
