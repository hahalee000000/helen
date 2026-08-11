"""LLM call runtime control — stdlib functions for streaming interrupt.

Phase 5 of streaming interrupt proposal:
- cancel_llm_call(call_id): Cancel a specific in-flight LLM call
- current_llm_call_id(): Get the current active streaming call ID
- cancel_all_llm_calls(): Cancel all active streaming calls
"""

from __future__ import annotations

import threading
from typing import Any

_interpreter_ref: Any = None
_ref_lock = threading.Lock()


def _set_interpreter_ref(interp: Any) -> None:
    """Set the interpreter reference for runtime control functions."""
    global _interpreter_ref
    with _ref_lock:
        _interpreter_ref = interp


def _cancel_llm_call(call_id: str) -> bool:
    """Cancel a specific in-flight LLM streaming call.

    Args:
        call_id: The call ID returned by current_llm_call_id().

    Returns:
        True if the call was found and cancelled, False otherwise.
    """
    if _interpreter_ref is None:
        return False
    return _interpreter_ref.cancel_streaming_call(call_id)


def _current_llm_call_id() -> str | None:
    """Return the ID of the current active streaming LLM call, or None."""
    if _interpreter_ref is None:
        return None
    return _interpreter_ref.get_current_streaming_call_id()


def _cancel_all_llm_calls() -> int:
    """Cancel all active streaming LLM calls.

    Returns:
        The number of calls that were cancelled.
    """
    if _interpreter_ref is None:
        return 0
    return _interpreter_ref.cancel_all_streaming_calls()


# ---------------------------------------------------------------------------
# v1.39.8: Runtime LLM parameter overrides (stdlib functions)
# ---------------------------------------------------------------------------
# set_*() writes to interpreter._runtime_overrides; get_*() reads effective
# value (override > agent declaration > default).
# identity params (model/description/provider) are get-only.

def _get_effective(key: str, default: Any = None) -> Any:
    """Resolve effective value: runtime override > agent setting > runtime default > default."""
    if _interpreter_ref is None:
        return default
    overrides = getattr(_interpreter_ref, '_runtime_overrides', {})
    if key in overrides:
        return overrides[key]
    # Map override key to agent setting name
    setting_map = {
        "temperature": "temperature",
        "max_turns": "max-turns",
        "max_tokens": "max-tokens",
        "thinking_mode": "thinking-mode",
        "reasoning_effort": "reasoning-effort",
        "model": "model",
        "description": "description",
        "provider": "provider",
    }
    setting_name = setting_map.get(key)
    if setting_name is not None and hasattr(_interpreter_ref, '_get_agent_setting'):
        val = _interpreter_ref._get_agent_setting(setting_name)
        if val is not None:
            return val
    # v1.40.1 fix: For model, also check LLM runtime's default_model (from config.yaml)
    if key == "model":
        llm_runtime = getattr(_interpreter_ref, 'llm_runtime', None)
        if llm_runtime is not None:
            runtime_model = getattr(llm_runtime, 'default_model', None)
            if runtime_model:
                return runtime_model
    return default


# --- Writable operational parameters ---

def _set_temperature(t: float) -> None:
    """Set temperature for subsequent llm act calls (overrides agent declaration)."""
    if _interpreter_ref is None:
        return
    _interpreter_ref._runtime_overrides["temperature"] = float(t)


def _get_temperature() -> float:
    """Get effective temperature (override > agent declaration > default 1.0)."""
    return float(_get_effective("temperature", 1.0))


def _set_max_turns(n: int) -> None:
    """Set max tool-calling turns for subsequent llm act calls."""
    if _interpreter_ref is None:
        return
    _interpreter_ref._runtime_overrides["max_turns"] = int(n)


def _get_max_turns() -> int:
    """Get effective max-turns (override > agent declaration > default 1)."""
    return int(_get_effective("max_turns", 1))


def _set_max_tokens(n: int) -> None:
    """Set max output tokens for subsequent llm act calls."""
    if _interpreter_ref is None:
        return
    _interpreter_ref._runtime_overrides["max_tokens"] = int(n)


def _get_max_tokens():
    """Get effective max-tokens (override > agent declaration > None)."""
    return _get_effective("max_tokens")


def _set_thinking_mode(enabled: bool) -> None:
    """Enable or disable thinking/reasoning mode for subsequent llm act calls."""
    if _interpreter_ref is None:
        return
    _interpreter_ref._runtime_overrides["thinking_mode"] = bool(enabled)


def _get_thinking_mode():
    """Get effective thinking-mode (override > agent declaration > None)."""
    return _get_effective("thinking_mode")


def _set_reasoning_effort(effort: str) -> None:
    """Set reasoning effort level (e.g. 'low', 'medium', 'high') for subsequent calls."""
    if _interpreter_ref is None:
        return
    _interpreter_ref._runtime_overrides["reasoning_effort"] = str(effort)


def _get_reasoning_effort():
    """Get effective reasoning-effort (override > agent declaration > None)."""
    return _get_effective("reasoning_effort")


# --- Read-only identity parameters ---

def _get_model() -> str | None:
    """Get the current model (from agent declaration, read-only)."""
    return _get_effective("model")


def _get_description() -> str | None:
    """Get the agent description (read-only)."""
    return _get_effective("description")


def _get_provider() -> str | None:
    """Get the current provider (from agent declaration, read-only)."""
    return _get_effective("provider")
