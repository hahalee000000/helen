"""Tests for spawn + Channel cancel interrupt (Phase 6)."""

import threading
import pytest
from helen.interpreter.interpreter import Interpreter
from helen.runtime.llm_runtime import MockLLMRuntime
from helen.runtime.channel import Channel, ChannelEndpoint


class TestSpawnCancel:
    """Phase 6: endpoint.cancel() interrupts spawned agent streaming."""

    def test_cancel_event_propagates_to_spawned_interpreter(self):
        """endpoint.cancel() sets cancel_event that spawned interp can check."""
        channel = Channel(name="test")
        main_ep = ChannelEndpoint(channel, is_main_thread=True)
        spawned_ep = ChannelEndpoint(channel, is_main_thread=False)

        # Before cancel: cancel_event not set
        assert not spawned_ep.cancel_event.is_set()

        # After cancel: cancel_event is set
        main_ep.cancel()
        assert spawned_ep.cancel_event.is_set()

    def test_cancel_event_is_shared(self):
        """Both endpoints see the same cancel_event."""
        channel = Channel(name="test")
        main_ep = ChannelEndpoint(channel, is_main_thread=True)
        spawned_ep = ChannelEndpoint(channel, is_main_thread=False)

        assert main_ep.cancel_event is spawned_ep.cancel_event

    def test_cancel_closes_channel(self):
        """cancel() closes the channel, receive() returns None."""
        channel = Channel(name="test")
        main_ep = ChannelEndpoint(channel, is_main_thread=True)
        spawned_ep = ChannelEndpoint(channel, is_main_thread=False)

        main_ep.cancel()
        assert channel.is_closed
        assert spawned_ep.is_channel_closed()

    def test_agent_cancel_event_attribute_injection(self):
        """Spawned interpreter gets _agent_cancel_event attribute."""
        interp = Interpreter(llm_runtime=MockLLMRuntime())
        cancel = threading.Event()

        # Simulate what visit_spawn_expr does
        interp._agent_cancel_event = cancel

        assert hasattr(interp, '_agent_cancel_event')
        assert interp._agent_cancel_event is cancel
        assert not interp._agent_cancel_event.is_set()

        cancel.set()
        assert interp._agent_cancel_event.is_set()

    def test_spawn_keyword_renamed(self):
        """spawn is the keyword, not spawnagent."""
        from helen.core.tokens import keywords, TokenType
        kw = keywords()
        assert "spawn" in kw
        assert kw["spawn"] == TokenType.SPAWN
        assert "spawnagent" not in kw

    def test_fensheng_keyword(self):
        """分生 is the Chinese keyword for spawn."""
        from helen.core.tokens import keywords, TokenType
        kw = keywords()
        assert "分生" in kw
        assert kw["分生"] == TokenType.SPAWN
        # 生成 is no longer mapped to SPAWN (it's used for on_generate)
        assert "生成" not in kw or kw.get("生成") != TokenType.SPAWN
