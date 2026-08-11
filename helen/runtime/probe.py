"""Provider connectivity probing for Helen init.

Three-layer probe architecture:
- Layer 1: Basic connectivity (single chat completion request)
- Layer 2: Protocol variant detection (try known protocol formats)
- Layer 3: Capability detection (vision, tool_choice, streaming)

All probes use real HTTP requests (via httpx) to the provider API.
Each probe call costs real API tokens — minimize probe count.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# 1x1 transparent PNG for vision probing (base64)
_1X1_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
    "nGP4z8BQDwAEgAJ/wNOCqAcAAAAASUVORK5CYII="
)


@dataclass
class ProbeResult:
    """Result of provider connectivity probing."""

    success: bool
    error_type: str | None = None  # "connection" | "auth" | "model_not_found" | "protocol" | None
    error_message: str | None = None
    protocol_name: str | None = None  # matched protocol name, e.g. "openai", "deepseek"
    capabilities: dict[str, bool] = field(default_factory=dict)
    # capabilities keys: "thinking", "streaming", "vision", "tool_choice_required"


def _make_request(
    base_url: str,
    api_key: str,
    payload: dict[str, Any],
    timeout: int = 15,
) -> tuple[int, dict[str, Any] | None, str | None]:
    """Send a chat completion request and return (status_code, response_json, error_body_text).

    Returns:
        (status_code, response_data, error_text)
        - On HTTP success: (200, parsed_json, None)
        - On HTTP error: (status_code, error_json_or_None, error_text)
        - On connection error: (-1, None, error_description)
    """
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=httpx.Timeout(timeout, connect=10.0)) as client:
            response = client.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                try:
                    return (200, response.json(), None)
                except Exception:
                    return (200, None, "Response is not valid JSON")
            else:
                try:
                    error_data = response.json()
                except Exception:
                    error_data = None
                error_text = response.text[:500] if response.text else f"HTTP {response.status_code}"
                return (response.status_code, error_data, error_text)

    except (httpx.ConnectError, httpx.RemoteProtocolError) as e:
        return (-1, None, f"Connection error: {e}")
    except httpx.TimeoutException:
        return (-1, None, f"Connection timed out after {timeout}s")
    except Exception as e:
        return (-1, None, f"Unexpected error: {e}")


def _classify_error(status_code: int, error_data: dict | None, error_text: str | None) -> tuple[str, str]:
    """Classify an HTTP error into (error_type, human_readable_message).

    Returns:
        (error_type, message) where error_type is one of:
        "connection", "auth", "model_not_found", "protocol"
    """
    if status_code == -1:
        return ("connection", error_text or "Cannot connect to server")

    if status_code in (401, 403):
        return ("auth", f"Authentication failed (HTTP {status_code})")

    if status_code == 404:
        msg = ""
        if error_data and isinstance(error_data, dict):
            error = error_data.get("error", {})
            if isinstance(error, dict):
                msg = error.get("message", "")
            elif isinstance(error, str):
                msg = error
        if "model" in msg.lower() or "not found" in msg.lower():
            return ("model_not_found", msg or "Model not found")
        return ("model_not_found", msg or "Not found (HTTP 404)")

    if status_code >= 400:
        msg = ""
        if error_data and isinstance(error_data, dict):
            error = error_data.get("error", {})
            if isinstance(error, dict):
                msg = error.get("message", "")
        return ("protocol", msg or error_text or f"HTTP error {status_code}")

    return ("protocol", error_text or "Unknown error")


def _parse_standard_response(response_data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Try to parse response as standard OpenAI format.

    Returns parsed {content, reasoning_content, tool_calls} or None if unparseable.
    """
    if not response_data:
        return None
    try:
        choices = response_data.get("choices", [])
        if not choices:
            return None
        message = choices[0].get("message", {})
        return {
            "content": message.get("content", "") or "",
            "reasoning_content": message.get("reasoning_content", "") or "",
            "tool_calls": message.get("tool_calls", []) or [],
        }
    except (KeyError, TypeError, IndexError):
        return None


def probe_connectivity(
    base_url: str,
    api_key: str,
    model: str,
    timeout: int = 15,
) -> ProbeResult:
    """Layer 1: Basic connectivity probe.

    Sends a minimal chat completion request ("hi") and classifies the result.

    Returns:
        ProbeResult with success/error info. On success, protocol_name is
        determined by URL pattern matching (imported from provider_protocol).
    """
    from helen.runtime.provider_protocol import detect_protocol

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 10,
    }

    status_code, response_data, error_text = _make_request(base_url, api_key, payload, timeout)

    if status_code == 200:
        parsed = _parse_standard_response(response_data)
        if parsed is not None:
            # Success — detect protocol from URL
            protocol = detect_protocol(base_url)
            return ProbeResult(
                success=True,
                protocol_name=protocol.name,
                capabilities={"streaming": True},  # basic connectivity confirmed
            )
        else:
            # Got 200 but can't parse — protocol mismatch
            return ProbeResult(
                success=False,
                error_type="protocol",
                error_message="Received 200 OK but response format is not recognized",
            )

    # Error case
    error_type, error_msg = _classify_error(status_code, response_data, error_text)
    return ProbeResult(
        success=False,
        error_type=error_type,
        error_message=error_msg,
    )


def probe_protocol_variants(
    base_url: str,
    api_key: str,
    model: str,
    timeout: int = 15,
) -> tuple[str, dict[str, bool]] | None:
    """Layer 2: Try known protocol variants to find which one works.

    For each known protocol (excluding OpenAI, already tried in Layer 1):
    - Build request payload with provider-specific thinking format
    - Send the request
    - Parse response with that protocol's parser
    - If we get a valid response with reasoning_content → match found

    Returns:
        (protocol_name, capabilities) on first match, or None if no variant works.
    """
    from helen.runtime.provider_protocol import (
        DashScopeProtocol,
        DeepSeekProtocol,
        KimiProtocol,
        MinimaxProtocol,
        VolcengineProtocol,
        ZhipuProtocol,
    )

    # Protocols to try (exclude OpenAI — already tried in Layer 1)
    variants = [
        ("dashscope", DashScopeProtocol),
        ("deepseek", DeepSeekProtocol),
        ("volcengine", VolcengineProtocol),
        ("zhipu", ZhipuProtocol),
        ("minimax", MinimaxProtocol),
        ("kimi", KimiProtocol),
    ]

    for name, protocol_cls in variants:
        protocol = protocol_cls()

        # Build a payload with thinking enabled
        base_payload = {
            "model": model,
            "messages": [{"role": "user", "content": "What is 1+1? Answer briefly."}],
            "max_tokens": 50,
        }
        payload = protocol.build_request_payload(
            base_payload,
            model_id=model,
            thinking_enabled=True,
            reasoning_effort="low",
        )

        status_code, response_data, error_text = _make_request(base_url, api_key, payload, timeout)

        if status_code == 200 and response_data:
            # Try to parse with this protocol's parser
            try:
                parsed = protocol.parse_response(response_data)
                if parsed and parsed.get("content"):
                    capabilities: dict[str, bool] = {"streaming": True}
                    reasoning = parsed.get("reasoning_content", "")
                    if reasoning:
                        capabilities["thinking"] = True
                    return (name, capabilities)
            except Exception:
                continue

    return None


def probe_capabilities(
    base_url: str,
    api_key: str,
    model: str,
    protocol: Any = None,
    timeout: int = 15,
) -> dict[str, bool]:
    """Layer 3: Probe specific capabilities.

    Tests:
    - Vision: send a 1x1 transparent PNG as image_url
    - Tool choice "required": send with tool_choice="required" and a dummy tool

    Returns:
        Dict of capability booleans: {"vision": bool, "tool_choice_required": bool}
    """
    from helen.runtime.provider_protocol import detect_protocol

    if protocol is None:
        protocol = detect_protocol(base_url)

    caps: dict[str, bool] = {}

    # --- Vision probe ---
    vision_payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image in one word."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{_1X1_PNG_BASE64}",
                        },
                    },
                ],
            }
        ],
        "max_tokens": 20,
    }
    vision_payload = protocol.build_request_payload(vision_payload, model_id=model)
    status_code, response_data, _ = _make_request(base_url, api_key, vision_payload, timeout)
    if status_code == 200:
        parsed = _parse_standard_response(response_data)
        caps["vision"] = parsed is not None and bool(parsed.get("content"))
    else:
        caps["vision"] = False

    # --- Tool choice "required" probe ---
    tool_payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Search for something."}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "dummy_search",
                    "description": "A dummy search tool for testing.",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
        "tool_choice": "required",
        "max_tokens": 20,
    }
    tool_payload = protocol.build_request_payload(tool_payload, model_id=model)
    status_code, response_data, _ = _make_request(base_url, api_key, tool_payload, timeout)
    if status_code == 200:
        parsed = _parse_standard_response(response_data)
        caps["tool_choice_required"] = parsed is not None and bool(parsed.get("tool_calls"))
    else:
        caps["tool_choice_required"] = False

    return caps


def run_full_probe(
    base_url: str,
    api_key: str,
    model: str,
    deep: bool = False,
    timeout: int = 15,
) -> ProbeResult:
    """Orchestrate all probe layers.

    Args:
        base_url: Provider API base URL
        api_key: API key
        model: Model ID
        deep: If True, run Layer 2+3 probes on unknown providers.
              If False (default), only Layer 1.
        timeout: HTTP timeout in seconds

    Returns:
        ProbeResult with combined information from all layers.
    """
    # Layer 1: Basic connectivity
    result = probe_connectivity(base_url, api_key, model, timeout)

    if result.success:
        return result

    # If it's a hard error (connection/auth/model), don't bother with deeper probes
    if result.error_type in ("connection", "auth", "model_not_found"):
        return result

    # Layer 1 failed with protocol error — try deeper probes if requested
    if not deep:
        return result

    # Layer 2: Protocol variant detection
    variant_result = probe_protocol_variants(base_url, api_key, model, timeout)
    if variant_result:
        protocol_name, capabilities = variant_result
        return ProbeResult(
            success=True,
            protocol_name=protocol_name,
            capabilities=capabilities,
        )

    # Layer 3: Capability probing (using default OpenAI protocol)
    from helen.runtime.provider_protocol import OpenAIProtocol

    protocol = OpenAIProtocol()
    extra_caps = probe_capabilities(base_url, api_key, model, protocol, timeout)

    # Even if protocol variants didn't match, save capabilities
    return ProbeResult(
        success=False,
        error_type="protocol",
        error_message="No known protocol variant matched. Provider may need a custom adapter.",
        capabilities=extra_caps,
    )
