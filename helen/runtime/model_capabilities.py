"""Model-level capability detection for LLM models.

While PlatformProtocol handles protocol FORMAT differences (determined by base_url),
ModelCapabilities handles feature AVAILABILITY differences (determined by model_id).

Key differences:
- Thinking mode support (some models don't support it)
- Forced thinking (some models always think, cannot disable)
- reasoning_content streaming behavior (incremental/cumulative/mutually_exclusive)
- tool_choice support (some platforms only support "auto")
- Special fields (encrypted_content, reasoning_details)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model Capabilities Dataclass
# ---------------------------------------------------------------------------


@dataclass
class ModelCapabilities:
    """Model-level feature detection.

    Determined by model_id. Handles feature AVAILABILITY differences.
    """

    # Thinking/reasoning
    supports_thinking: bool = True
    thinking_enabled_by_default: bool = False
    forced_thinking: bool = False  # GLM-4.7: always thinks, cannot disable

    # Tool calling
    supports_tool_choice_required: bool = True  # GLM: only "auto"
    supports_tool_choice_none: bool = True
    supports_parallel_tools: bool = True

    # Streaming behavior for reasoning_content
    # "incremental": standard incremental streaming (most providers)
    # "cumulative": MiniMax — reasoning_details is cumulative, must compute delta
    # "mutually_exclusive": DeepSeek — reasoning_content and content are exclusive per chunk
    reasoning_content_streaming: str = "incremental"

    # Special response fields
    has_encrypted_content: bool = False  # Doubao
    has_reasoning_details: bool = False  # MiniMax

    # Default parameters
    default_temperature: float = 1.0
    default_top_p: float = 1.0


# ---------------------------------------------------------------------------
# Model Capability Registry
# ---------------------------------------------------------------------------


_MODEL_CAPABILITIES: dict[str, ModelCapabilities] = {
    # --- DashScope (Qwen) ---
    "qwen3-max": ModelCapabilities(
        supports_thinking=True,
        thinking_enabled_by_default=False,
        reasoning_content_streaming="incremental",
    ),
    "qwen3.7-plus": ModelCapabilities(
        supports_thinking=True,
        thinking_enabled_by_default=False,
    ),
    "qwen3.8-max": ModelCapabilities(
        supports_thinking=True,
        thinking_enabled_by_default=False,
    ),
    "qwen-max": ModelCapabilities(
        supports_thinking=False,  # Not Qwen3 series
        reasoning_content_streaming="incremental",
    ),
    "qwen-plus": ModelCapabilities(
        supports_thinking=False,
    ),
    "qwen-turbo": ModelCapabilities(
        supports_thinking=False,
    ),

    # --- Zhipu (GLM) ---
    "glm-5.2": ModelCapabilities(
        supports_thinking=True,
        supports_tool_choice_required=False,  # Only "auto"
        supports_tool_choice_none=False,
        default_temperature=1.0,
    ),
    "glm-5.1": ModelCapabilities(
        supports_thinking=True,
        supports_tool_choice_required=False,
        supports_tool_choice_none=False,
    ),
    "glm-5": ModelCapabilities(
        supports_thinking=True,
        supports_tool_choice_required=False,
        supports_tool_choice_none=False,
    ),
    "glm-4.7": ModelCapabilities(
        supports_thinking=True,
        forced_thinking=True,  # Cannot disable
        supports_tool_choice_required=False,
        supports_tool_choice_none=False,
        default_temperature=1.0,
    ),
    "glm-4.6": ModelCapabilities(
        supports_thinking=True,
        supports_tool_choice_required=False,
        supports_tool_choice_none=False,
    ),
    "glm-4.5": ModelCapabilities(
        supports_thinking=True,
        supports_tool_choice_required=False,
        supports_tool_choice_none=False,
        default_temperature=0.6,
    ),

    # --- DeepSeek ---
    "deepseek-v4-flash": ModelCapabilities(
        supports_thinking=True,
        reasoning_content_streaming="mutually_exclusive",  # Critical!
    ),
    "deepseek-v4-pro": ModelCapabilities(
        supports_thinking=True,
        reasoning_content_streaming="mutually_exclusive",
    ),
    "deepseek-reasoner": ModelCapabilities(
        supports_thinking=True,
        forced_thinking=True,  # R1 always thinks
        reasoning_content_streaming="mutually_exclusive",
    ),
    "deepseek-chat": ModelCapabilities(
        supports_thinking=False,  # Legacy model name
    ),

    # --- Minimax ---
    "MiniMax-M3": ModelCapabilities(
        supports_thinking=True,
        has_reasoning_details=True,
        reasoning_content_streaming="cumulative",  # Critical!
        default_temperature=1.0,
    ),
    "MiniMax-M2.7": ModelCapabilities(
        supports_thinking=True,
        forced_thinking=True,  # M2.x always thinks
        reasoning_content_streaming="cumulative",
        default_temperature=1.0,
    ),
    "MiniMax-M2.5": ModelCapabilities(
        supports_thinking=True,
        forced_thinking=True,
        reasoning_content_streaming="cumulative",
        default_temperature=1.0,
    ),
    "MiniMax-M2.1": ModelCapabilities(
        supports_thinking=True,
        forced_thinking=True,
        reasoning_content_streaming="cumulative",
        default_temperature=1.0,
    ),

    # --- Kimi/Moonshot ---
    "kimi-k3": ModelCapabilities(
        supports_thinking=True,
        thinking_enabled_by_default=True,
    ),
    "kimi-k2.7-code": ModelCapabilities(
        supports_thinking=True,
        forced_thinking=True,  # Always thinks
    ),
    "kimi-k2.6": ModelCapabilities(
        supports_thinking=True,
        thinking_enabled_by_default=True,
    ),
    "moonshot-v1-8k": ModelCapabilities(
        supports_thinking=False,  # Legacy model
        default_temperature=0.0,
    ),
    "moonshot-v1-32k": ModelCapabilities(
        supports_thinking=False,
        default_temperature=0.0,
    ),
    "moonshot-v1-128k": ModelCapabilities(
        supports_thinking=False,
        default_temperature=0.0,
    ),

    # --- Doubao (Volcengine) ---
    "doubao-seed-2.1-pro": ModelCapabilities(
        supports_thinking=True,
        has_encrypted_content=True,
    ),
    "doubao-seed-1.6": ModelCapabilities(
        supports_thinking=True,
        has_encrypted_content=True,
    ),
    "doubao-seed-1.6-thinking": ModelCapabilities(
        supports_thinking=True,
        forced_thinking=True,
        has_encrypted_content=True,
    ),
    "doubao-1.5-pro-256k": ModelCapabilities(
        supports_thinking=True,
    ),
    "doubao-pro-128k": ModelCapabilities(
        supports_thinking=False,  # Classic model
    ),
    "doubao-pro-32k": ModelCapabilities(
        supports_thinking=False,
    ),
    "doubao-lite-128k": ModelCapabilities(
        supports_thinking=False,
    ),
}


# ---------------------------------------------------------------------------
# Lookup Function
# ---------------------------------------------------------------------------


def get_model_capabilities(model_id: str | None) -> ModelCapabilities:
    """Get capabilities for a specific model.

    Falls back to sensible defaults if model not in registry.

    Lookup order:
    1. Exact match in registry
    2. Prefix match (e.g., "qwen3-max-2024" → "qwen3-max")
    3. Default: standard OpenAI-compatible capabilities
    """
    if not model_id:
        return ModelCapabilities()

    # Exact match
    if model_id in _MODEL_CAPABILITIES:
        return _MODEL_CAPABILITIES[model_id]

    # Prefix match (e.g., "qwen3-max-2024" → "qwen3-max")
    for registered_id, caps in _MODEL_CAPABILITIES.items():
        if model_id.startswith(registered_id):
            logger.debug(f"Model {model_id} matched prefix {registered_id}")
            return caps

    # Default: standard OpenAI-compatible capabilities
    logger.debug(f"Model {model_id} not in registry, using defaults")
    return ModelCapabilities()


def list_registered_models() -> list[str]:
    """List all registered model IDs."""
    return sorted(_MODEL_CAPABILITIES.keys())
