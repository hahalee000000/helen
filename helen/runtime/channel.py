"""Channel — General-purpose message queue for agent communication.

Designed for consistency across both spawn (cross-thread) and standard agent
isolation scenarios. Internally uses two queues to support bidirectional
communication.

Provides:
- Channel: Low-level bidirectional message channel
- ChannelEndpoint: An endpoint of a Channel (main thread side or spawned agent side)
"""

from __future__ import annotations

import queue
import threading
from typing import Any


class Channel:
    """Bidirectional message channel. General-purpose tool for agent communication.

    Designed for consistency across both spawn (cross-thread) and standard agent
    isolation scenarios. Internally uses two queues to support bidirectional
    communication.

    Do not use Channel's send/receive directly — operate through ChannelEndpoint.
    Channel itself is merely a container for two queues and state flags.
    """

    def __init__(self, name: str = ""):
        self._name = name
        # Main thread → spawned agent direction
        self._to_spawned: queue.Queue = queue.Queue()
        # Spawned agent → main thread direction
        self._from_spawned: queue.Queue = queue.Queue()
        self._cancel_event = threading.Event()
        self._closed = threading.Event()

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_closed(self) -> bool:
        return self._closed.is_set()

    @property
    def cancel_event(self) -> threading.Event:
        """Cancellation signal. Spawned agents can check this Event to respond to cancel requests."""
        return self._cancel_event

    @property
    def is_closed(self) -> bool:
        return self._closed.is_set()

    def mark_closed(self) -> None:
        """Mark the channel as closed."""
        self._closed.set()

    def mark_cancelled(self) -> None:
        """Mark the channel as cancelled."""
        self._cancel_event.set()
        self._closed.set()

    def __deepcopy__(self, memo):
        """Deep copy creates an independent empty Channel.

        Queue contents are not copied — the new Channel is an empty, unclosed
        independent instance. Lock objects cannot be pickled and must be rebuilt.
        """
        new_ch = Channel(self._name)
        memo[id(self)] = new_ch
        return new_ch


class ChannelEndpoint:
    """An endpoint of a Channel.

    Each Channel has two endpoints:
    - Main thread endpoint (is_main_thread=True): outbox → _to_spawned, inbox ← _from_spawned
    - Spawned agent endpoint (is_main_thread=False): outbox → _from_spawned, inbox ← _to_spawned

    send() puts into its own outbox, receive() takes from its own inbox.
    """

    def __init__(self, channel: Channel, is_main_thread: bool):
        self._channel = channel
        self._is_main = is_main_thread
        if is_main_thread:
            self._outbox = channel._to_spawned
            self._inbox = channel._from_spawned
        else:
            self._outbox = channel._from_spawned
            self._inbox = channel._to_spawned

    @property
    def channel(self) -> Channel:
        """The underlying Channel instance."""
        return self._channel

    @property
    def is_main_thread(self) -> bool:
        return self._is_main

    @property
    def cancel_event(self) -> threading.Event:
        """Cancellation signal (only meaningful for the spawned agent endpoint)."""
        return self._channel.cancel_event

    # ── Message operations ──

    def send(self, msg: Any = None) -> None:
        """Send a message to the other endpoint.

        Can pass any Python object, including SharedStore references.
        send() is silently ignored after the channel is closed.
        """
        if self._channel.is_closed:
            return
        self._outbox.put(msg)

    def receive(self, timeout: float | None = None) -> Any:
        """Blocking message receive.

        Args:
            timeout: Timeout in seconds. None means wait indefinitely.

        Returns:
            The received message. Returns None if the channel is closed or times out.
        """
        try:
            return self._inbox.get(timeout=timeout)
        except queue.Empty:
            return None

    def try_receive(self) -> Any:
        """Non-blocking receive.

        Returns:
            The received message. Returns None if no message is available.
        """
        try:
            return self._inbox.get_nowait()
        except queue.Empty:
            return None

    # ── Lifecycle control ──

    def cancel(self) -> None:
        """Cancel the other endpoint's agent and close the channel.

        Sets cancel_event (spawned agents can check this signal to interrupt
        streaming operations), then closes the channel.

        Typically only called from the main thread endpoint.
        """
        self._channel.mark_cancelled()
        # Wake up blocked receive()
        self._send_sentinel()

    def close(self) -> None:
        """Close the channel.

        The other endpoint's receive() will get None (indicating the channel is closed).
        """
        self._channel.mark_closed()
        self._send_sentinel()

    def is_channel_closed(self) -> bool:
        """Check if the channel is closed."""
        return self._channel.is_closed

    def _send_sentinel(self) -> None:
        """Put a None sentinel into the outbox to wake up the other endpoint's blocked receive()."""
        try:
            self._outbox.put_nowait(None)
        except Exception:
            pass

    # ── Helen method call support ──

    def call_method(self, name: str, args: list) -> Any:
        """Supports channel.send(...) and similar Helen syntax."""
        methods = {
            # English
            "send": self.send,
            "receive": self.receive,
            "try_receive": self.try_receive,
            "cancel": self.cancel,
            "close": self.close,
            "is_closed": self.is_channel_closed,
            # Chinese aliases
            "发送": self.send,
            "接收": self.receive,
            "尝试接收": self.try_receive,
            "取消": self.cancel,
            "关闭": self.close,
            "已关闭": self.is_channel_closed,
        }
        fn = methods.get(name)
        if fn is None:
            raise AttributeError(f"Channel has no method '{name}'")
        return fn(*args)

    def __repr__(self) -> str:
        side = "main" if self._is_main else "spawned"
        return f"ChannelEndpoint({self._channel.name!r}, {side})"

    def __deepcopy__(self, memo):
        """Deep copy creates an independent endpoint.

        The underlying Channel is deep-copied to an empty independent instance,
        and this endpoint points to the new Channel.
        """
        import copy
        new_ch = copy.deepcopy(self._channel, memo)
        new_ep = ChannelEndpoint(new_ch, is_main_thread=self._is_main)
        memo[id(self)] = new_ep
        return new_ep
