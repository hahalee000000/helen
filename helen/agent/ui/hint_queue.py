"""Thread-safe hint queue for mid-processing user hints.

Cross-thread communication: Python async event loop (WebSocket) writes,
Helen runtime thread (on_tool_end callback) reads.
"""
import threading
import time
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Hint:
    text: str
    timestamp: float
    client_id: str  # for UI dedup / ack


class HintQueue:
    """Per-session FIFO queue of pending user hints."""

    def __init__(self):
        self._lock = threading.Lock()
        self._queues: Dict[str, List[Hint]] = {}

    def add_hint(self, session_id: str, text: str, client_id: str = "") -> Hint:
        with self._lock:
            hint = Hint(text=text, timestamp=time.time(), client_id=client_id)
            self._queues.setdefault(session_id, []).append(hint)
            return hint

    def pop_all_hints(self, session_id: str) -> List[Hint]:
        """Atomically pop all pending hints for a session.

        Called from Helen's on_tool_end callback thread. Returns [] if empty.
        """
        with self._lock:
            return self._queues.pop(session_id, [])

    def has_pending(self, session_id: str) -> bool:
        with self._lock:
            return bool(self._queues.get(session_id))

    def clear_session(self, session_id: str) -> None:
        """Drop all pending hints (called on WS disconnect / session cleanup)."""
        with self._lock:
            self._queues.pop(session_id, None)

    def clear_all(self) -> None:
        with self._lock:
            self._queues.clear()


_instance = HintQueue()


def get_hint_queue() -> HintQueue:
    return _instance
