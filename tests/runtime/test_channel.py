"""Tests for Channel runtime — Phase A of spawnagent proposal."""

import threading
import time
import pytest
from helen.runtime.channel import Channel, ChannelEndpoint


class TestChannel:
    """Channel 底层容器测试。"""

    def test_channel_creation(self):
        ch = Channel("test")
        assert ch.name == "test"
        assert not ch.is_closed
        assert not ch.cancel_event.is_set()

    def test_channel_default_name(self):
        ch = Channel()
        assert ch.name == ""

    def test_channel_mark_closed(self):
        ch = Channel()
        assert not ch.is_closed
        ch.mark_closed()
        assert ch.is_closed

    def test_channel_mark_cancelled(self):
        ch = Channel()
        ch.mark_cancelled()
        assert ch.is_closed
        assert ch.cancel_event.is_set()


class TestChannelEndpoint:
    """ChannelEndpoint 消息收发测试。"""

    def _make_pair(self):
        """创建一对互联的端点。"""
        ch = Channel("test")
        main_ep = ChannelEndpoint(ch, is_main_thread=True)
        spawned_ep = ChannelEndpoint(ch, is_main_thread=False)
        return main_ep, spawned_ep

    # ── 基本收发 ──

    def test_send_receive_main_to_spawned(self):
        main_ep, spawned_ep = self._make_pair()
        main_ep.send("hello")
        assert spawned_ep.receive(timeout=1) == "hello"

    def test_send_receive_spawned_to_main(self):
        main_ep, spawned_ep = self._make_pair()
        spawned_ep.send("world")
        assert main_ep.receive(timeout=1) == "world"

    def test_send_multiple_messages(self):
        main_ep, spawned_ep = self._make_pair()
        main_ep.send("a")
        main_ep.send("b")
        main_ep.send("c")
        assert spawned_ep.receive(timeout=1) == "a"
        assert spawned_ep.receive(timeout=1) == "b"
        assert spawned_ep.receive(timeout=1) == "c"

    def test_send_none_message(self):
        """发送 None 也是合法消息（但 close 后不再接受）。"""
        main_ep, spawned_ep = self._make_pair()
        main_ep.send(None)
        assert spawned_ep.receive(timeout=1) is None

    def test_send_complex_objects(self):
        """可传递 dict、list 等复杂对象。"""
        main_ep, spawned_ep = self._make_pair()
        msg = {"type": "progress", "data": [1, 2, 3]}
        main_ep.send(msg)
        result = spawned_ep.receive(timeout=1)
        assert result == msg
        assert result["data"] == [1, 2, 3]

    # ── 超时与阻塞 ──

    def test_receive_timeout_returns_none(self):
        main_ep, _ = self._make_pair()
        result = main_ep.receive(timeout=0.05)
        assert result is None

    def test_receive_blocks_until_send(self):
        main_ep, spawned_ep = self._make_pair()
        received = []

        def sender():
            time.sleep(0.05)
            spawned_ep.send("delayed")

        t = threading.Thread(target=sender)
        t.start()
        result = main_ep.receive(timeout=2)
        assert result == "delayed"
        t.join()

    def test_try_receive_empty(self):
        main_ep, _ = self._make_pair()
        assert main_ep.try_receive() is None

    def test_try_receive_with_message(self):
        main_ep, spawned_ep = self._make_pair()
        spawned_ep.send("quick")
        assert main_ep.try_receive() == "quick"
        assert main_ep.try_receive() is None  # 第二次为空

    # ── 关闭与取消 ──

    def test_close_unblocks_receive(self):
        """close 应唤醒阻塞的 receive()。"""
        main_ep, spawned_ep = self._make_pair()
        received = []

        def closer():
            time.sleep(0.05)
            spawned_ep.close()

        t = threading.Thread(target=closer)
        t.start()
        result = main_ep.receive(timeout=2)
        # close 放入 sentinel None
        assert result is None
        assert main_ep.is_channel_closed()
        t.join()

    def test_close_from_main_side(self):
        main_ep, spawned_ep = self._make_pair()
        main_ep.close()
        assert main_ep.is_channel_closed()
        assert spawned_ep.is_channel_closed()

    def test_cancel_sets_event(self):
        main_ep, spawned_ep = self._make_pair()
        assert not spawned_ep.cancel_event.is_set()
        main_ep.cancel()
        assert spawned_ep.cancel_event.is_set()
        assert main_ep.is_channel_closed()

    def test_send_after_close_is_silent(self):
        """通道关闭后 send 静默忽略。"""
        main_ep, spawned_ep = self._make_pair()
        main_ep.close()
        # 不应抛异常
        main_ep.send("ignored")
        spawned_ep.send("ignored")

    # ── 双向通信 ──

    def test_bidirectional_communication(self):
        main_ep, spawned_ep = self._make_pair()
        main_ep.send("request")
        assert spawned_ep.receive(timeout=1) == "request"
        spawned_ep.send("response")
        assert main_ep.receive(timeout=1) == "response"

    # ── call_method（Helen 方法调用支持）──

    def test_call_method_send(self):
        main_ep, spawned_ep = self._make_pair()
        main_ep.call_method("send", ["hello"])
        assert spawned_ep.receive(timeout=1) == "hello"

    def test_call_method_receive(self):
        main_ep, spawned_ep = self._make_pair()
        spawned_ep.send("test")
        result = main_ep.call_method("receive", [])
        assert result == "test"

    def test_call_method_chinese_aliases(self):
        main_ep, spawned_ep = self._make_pair()
        main_ep.call_method("发送", ["你好"])
        assert spawned_ep.call_method("接收", []) == "你好"

    def test_call_method_close(self):
        main_ep, _ = self._make_pair()
        main_ep.call_method("close", [])
        assert main_ep.call_method("已关闭", []) is True

    def test_call_method_cancel(self):
        main_ep, spawned_ep = self._make_pair()
        main_ep.call_method("取消", [])
        assert spawned_ep.cancel_event.is_set()

    def test_call_method_unknown(self):
        main_ep, _ = self._make_pair()
        with pytest.raises(AttributeError, match="no method"):
            main_ep.call_method("nonexistent", [])

    # ── repr ──

    def test_repr(self):
        ch = Channel("mychan")
        main_ep = ChannelEndpoint(ch, is_main_thread=True)
        spawned_ep = ChannelEndpoint(ch, is_main_thread=False)
        assert "main" in repr(main_ep)
        assert "spawned" in repr(spawned_ep)
        assert "mychan" in repr(main_ep)

    # ── 跨线程并发 ──

    def test_concurrent_send_receive(self):
        """多线程并发收发不丢消息。"""
        main_ep, spawned_ep = self._make_pair()
        n = 100
        received = []
        lock = threading.Lock()

        def sender():
            for i in range(n):
                spawned_ep.send(i)

        def receiver():
            for _ in range(n):
                msg = main_ep.receive(timeout=5)
                with lock:
                    received.append(msg)

        t1 = threading.Thread(target=sender)
        t2 = threading.Thread(target=receiver)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(received) == n
        assert sorted(received) == list(range(n))


class TestChannelIsolation:
    """测试 Channel 在深复制场景下的行为。"""

    def test_deepcopy_creates_independent_channel(self):
        """深复制的 Channel 应该创建独立的空 channel。"""
        import copy
        ch = Channel("original")
        main_ep = ChannelEndpoint(ch, is_main_thread=True)
        main_ep.send("data")

        ch_copy = copy.deepcopy(ch)
        # 副本是独立的
        assert ch_copy is not ch
        assert ch_copy.name == "original"
        assert not ch_copy.is_closed

    def test_deepcopy_endpoint(self):
        """深复制端点也应独立。"""
        import copy
        ch = Channel()
        ep = ChannelEndpoint(ch, is_main_thread=True)
        ep.send("data")

        ep_copy = copy.deepcopy(ep)
        assert ep_copy is not ep
