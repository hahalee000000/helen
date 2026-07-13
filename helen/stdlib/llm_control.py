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
