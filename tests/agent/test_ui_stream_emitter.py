"""Tests for helen/agent/ui/stream_emitter.py"""

import sys
from unittest.mock import MagicMock

from helen.agent.ui import stream_emitter


class TestStreamCallback:
    def setup_method(self):
        stream_emitter.clear_stream_callback()
        stream_emitter.clear_cancel()

    def teardown_method(self):
        stream_emitter.clear_stream_callback()
        stream_emitter.clear_cancel()

    def test_register_and_emit(self):
        cb = MagicMock()
        stream_emitter.register_stream_callback(cb)
        stream_emitter.emit_stream_event("llm_chunk", "hello")
        cb.assert_called_once_with("llm_chunk", "hello")

    def test_emit_without_callback_no_error(self):
        # No callback registered — should not raise
        stream_emitter.emit_stream_event("llm_chunk", "data")

    def test_clear_stream_callback(self):
        cb = MagicMock()
        stream_emitter.register_stream_callback(cb)
        stream_emitter.clear_stream_callback()
        stream_emitter.emit_stream_event("test", "data")
        cb.assert_not_called()

    def test_callback_exception_does_not_propagate(self, capsys):
        def bad_callback(event_type, data):
            raise ValueError("boom")

        stream_emitter.register_stream_callback(bad_callback)
        # Should not raise
        stream_emitter.emit_stream_event("test", "data")
        captured = capsys.readouterr()
        assert "失败" in captured.err or "boom" in captured.err

    def test_multiple_event_types(self):
        cb = MagicMock()
        stream_emitter.register_stream_callback(cb)
        for evt in ["llm_chunk", "llm_complete", "agent_start", "agent_end", "phase_start", "status"]:
            stream_emitter.emit_stream_event(evt, f"data_{evt}")
        assert cb.call_count == 6

    def test_register_replaces_previous_callback(self):
        cb1 = MagicMock()
        cb2 = MagicMock()
        stream_emitter.register_stream_callback(cb1)
        stream_emitter.register_stream_callback(cb2)
        stream_emitter.emit_stream_event("test", "data")
        cb1.assert_not_called()
        cb2.assert_called_once()


class TestCancelFlag:
    def setup_method(self):
        stream_emitter.clear_cancel()

    def teardown_method(self):
        stream_emitter.clear_cancel()

    def test_initial_state_not_requested(self):
        assert stream_emitter.is_cancel_requested() is False

    def test_request_cancel(self):
        stream_emitter.request_cancel()
        assert stream_emitter.is_cancel_requested() is True

    def test_clear_cancel(self):
        stream_emitter.request_cancel()
        stream_emitter.clear_cancel()
        assert stream_emitter.is_cancel_requested() is False

    def test_request_cancel_idempotent(self):
        stream_emitter.request_cancel()
        stream_emitter.request_cancel()
        assert stream_emitter.is_cancel_requested() is True

    def test_clear_cancel_idempotent(self):
        stream_emitter.clear_cancel()
        stream_emitter.clear_cancel()
        assert stream_emitter.is_cancel_requested() is False
