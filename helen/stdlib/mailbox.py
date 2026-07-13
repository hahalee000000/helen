"""Mailbox utilities — stdlib functions for Channel-based agent communication.

Provides:
- mailbox_select: receive from multiple channels, return first available
"""

from __future__ import annotations

import time
from typing import Any


def _mailbox_select(channels: Any, timeout: Any = None) -> Any:
    """Receive the first available message from multiple channels.

    Polls each channel in order, returning the first message received.
    Useful for竞争模式 (race pattern) — whoever finishes first wins.

    Args:
        channels: List of ChannelEndpoint objects.
        timeout: Optional timeout in seconds. None = wait forever.

    Returns:
        Dict with keys "endpoint" and "message", or null if timeout expires.

    Example:
        let m1 = spawnagent StrategyA()
        let m2 = spawnagent StrategyB()
        let result = mailbox_select([m1, m2])
        print(result["message"])
    """
    if not isinstance(channels, list):
        return None

    deadline = None
    if timeout is not None:
        try:
            deadline = time.time() + float(timeout)
        except (TypeError, ValueError):
            return None

    while True:
        for endpoint in channels:
            if hasattr(endpoint, 'try_receive'):
                msg = endpoint.try_receive()
                if msg is not None:
                    return {"endpoint": endpoint, "message": msg}

        if deadline is not None and time.time() >= deadline:
            return None

        time.sleep(0.01)  # 10ms poll interval
