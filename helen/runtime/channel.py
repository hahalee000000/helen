"""Channel — agent 通信的通用消息队列。

在 spawnagent 跨线程场景和普通 agent 隔离场景中设计一致。
内部两个队列，支持双向通信。

提供：
- Channel: 底层双向消息通道
- ChannelEndpoint: Channel 的一个端点（主线程端或 spawned agent 端）
"""

from __future__ import annotations

import queue
import threading
from typing import Any


class Channel:
    """双向消息通道。agent 通信的通用工具。

    在 spawnagent 跨线程场景和普通 agent 隔离场景中设计一致。
    内部两个队列，支持双向通信。

    不要直接使用 Channel 的 send/receive —— 应通过 ChannelEndpoint 操作。
    Channel 本身只是两个队列和状态标志的容器。
    """

    def __init__(self, name: str = ""):
        self._name = name
        # 主线程 → spawned agent 方向
        self._to_spawned: queue.Queue = queue.Queue()
        # spawned agent → 主线程方向
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
        """取消信号。spawned agent 内部可检查此 Event 以响应取消请求。"""
        return self._cancel_event

    @property
    def is_closed(self) -> bool:
        return self._closed.is_set()

    def mark_closed(self) -> None:
        """标记通道已关闭。"""
        self._closed.set()

    def mark_cancelled(self) -> None:
        """标记通道已取消。"""
        self._cancel_event.set()
        self._closed.set()

    def __deepcopy__(self, memo):
        """深复制创建独立的空 Channel。

        队列内容不复制——新 Channel 是空的、未关闭的独立实例。
        锁对象无法 pickle，必须重建。
        """
        new_ch = Channel(self._name)
        memo[id(self)] = new_ch
        return new_ch


class ChannelEndpoint:
    """Channel 的一个端点。

    每个 Channel 有两个端点：
    - 主线程端（is_main_thread=True）：outbox → _to_spawned, inbox ← _from_spawned
    - spawned agent 端（is_main_thread=False）：outbox → _from_spawned, inbox ← _to_spawned

    send() 放入自己的 outbox，receive() 从自己的 inbox 取出。
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
        """底层 Channel 实例。"""
        return self._channel

    @property
    def is_main_thread(self) -> bool:
        return self._is_main

    @property
    def cancel_event(self) -> threading.Event:
        """取消信号（仅对 spawned agent 端有意义）。"""
        return self._channel.cancel_event

    # ── 消息操作 ──

    def send(self, msg: Any = None) -> None:
        """发送消息到对端。

        可传递任意 Python 对象，包括 SharedStore 引用。
        通道关闭后 send 静默忽略。
        """
        if self._channel.is_closed:
            return
        self._outbox.put(msg)

    def receive(self, timeout: float | None = None) -> Any:
        """阻塞接收消息。

        Args:
            timeout: 超时秒数。None 表示无限等待。

        Returns:
            收到的消息。通道关闭或超时时返回 None。
        """
        try:
            return self._inbox.get(timeout=timeout)
        except queue.Empty:
            return None

    def try_receive(self) -> Any:
        """非阻塞接收。

        Returns:
            收到的消息。无消息时返回 None。
        """
        try:
            return self._inbox.get_nowait()
        except queue.Empty:
            return None

    # ── 生命周期控制 ──

    def cancel(self) -> None:
        """取消对端 agent 并关闭通道。

        设置 cancel_event（spawned agent 可检查此信号中断流式操作），
        然后关闭通道。

        通常仅主线程端调用。
        """
        self._channel.mark_cancelled()
        # 唤醒阻塞的 receive()
        self._send_sentinel()

    def close(self) -> None:
        """关闭通道。

        对端的 receive() 将收到 None（表示通道已关闭）。
        """
        self._channel.mark_closed()
        self._send_sentinel()

    def is_channel_closed(self) -> bool:
        """检查通道是否已关闭。"""
        return self._channel.is_closed

    def _send_sentinel(self) -> None:
        """向 outbox 放入 None 哨兵，唤醒对端阻塞的 receive()。"""
        try:
            self._outbox.put_nowait(None)
        except Exception:
            pass

    # ── Helen 方法调用支持 ──

    def call_method(self, name: str, args: list) -> Any:
        """支持 channel.send(...) 等 Helen 语法。"""
        methods = {
            # 英文
            "send": self.send,
            "receive": self.receive,
            "try_receive": self.try_receive,
            "cancel": self.cancel,
            "close": self.close,
            "is_closed": self.is_channel_closed,
            # 中文别名
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
        """深复制创建独立的端点。

        底层 Channel 深复制为空独立实例，此端点指向新的 Channel。
        """
        import copy
        new_ch = copy.deepcopy(self._channel, memo)
        new_ep = ChannelEndpoint(new_ch, is_main_thread=self._is_main)
        memo[id(self)] = new_ep
        return new_ep
