"""Streaming call management mixin for the Helen interpreter.

Extracted from interpreter.py to improve code organization.
Manages lifecycle of streaming LLM calls for cancellation support.
"""

from __future__ import annotations

import threading
import uuid
from typing import Any


class _StreamingHandle:
    """Tracks an in-flight streaming LLM call for cancellation.

    Phase 3 of streaming interrupt proposal: allows programmatic cancel
    and Ctrl+C handling during llm act streaming.
    """

    def __init__(self) -> None:
        self.call_id: str = str(uuid.uuid4())
        self.cancelled: "threading.Event" = threading.Event()
        self.done: "threading.Event" = threading.Event()


class StreamingMixin:
    """Mixin providing streaming call management methods.

    Host class must provide:
    - _streaming_lock: threading.Lock
    - _streaming_calls: dict[str, _StreamingHandle]
    """

    # Declare attributes expected from host class
    _streaming_lock: Any
    _streaming_calls: Any

    def _register_streaming_call(self) -> _StreamingHandle:
        """Register a new in-flight streaming LLM call."""
        handle = _StreamingHandle()
        with self._streaming_lock:
            self._streaming_calls[handle.call_id] = handle
        return handle

    def _unregister_streaming_call(self, call_id: str) -> None:
        """Unregister a completed streaming call."""
        with self._streaming_lock:
            self._streaming_calls.pop(call_id, None)

    def cancel_streaming_call(self, call_id: str) -> bool:
        """Cancel a specific streaming call by ID. Returns True if found."""
        with self._streaming_lock:
            handle = self._streaming_calls.get(call_id)
        if handle is None:
            return False
        handle.cancelled.set()
        return True

    def get_current_streaming_call_id(self) -> str | None:
        """Return the ID of the current active streaming call, or None."""
        with self._streaming_lock:
            for cid, h in self._streaming_calls.items():
                if not h.done.is_set():
                    return cid
        return None

    def cancel_all_streaming_calls(self) -> int:
        """Cancel all active streaming calls. Returns count cancelled."""
        count = 0
        with self._streaming_lock:
            for handle in self._streaming_calls.values():
                if not handle.done.is_set():
                    handle.cancelled.set()
                    count += 1
        return count
