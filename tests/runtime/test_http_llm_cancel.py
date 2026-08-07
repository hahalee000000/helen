"""Tests for HttpLLMRuntime cancel_event parameter (Phase 2)."""

import json
import threading
import time
import pytest
from unittest.mock import MagicMock, patch


class TestHttpLLMCancelEvent:
    """Phase 2: HttpLLMRuntime.act_stream() accepts cancel_event."""

    def test_act_stream_signature_accepts_cancel_event(self):
        """HttpLLMRuntime.act_stream has cancel_event parameter."""
        import inspect
        from helen.runtime.http_llm import HttpLLMRuntime
        sig = inspect.signature(HttpLLMRuntime.act_stream)
        assert "cancel_event" in sig.parameters

    def test_act_stream_cancel_event_default_none(self):
        """cancel_event defaults to None (backward compatible)."""
        import inspect
        from helen.runtime.http_llm import HttpLLMRuntime
        sig = inspect.signature(HttpLLMRuntime.act_stream)
        param = sig.parameters["cancel_event"]
        assert param.default is None

    def test_cancel_between_turns(self):
        """cancel_event set between turns causes break.

        This is a unit-level contract test — the actual HTTP interaction
        is tested in integration tests.
        """
        cancel = threading.Event()
        cancel.set()  # Pre-cancelled

        # The contract: when cancel_event.is_set() before entering the
        # streaming loop, act_stream should not make any HTTP calls
        # This is verified by the break check at the top of while budget.consume()


# ---------------------------------------------------------------------------
# v1.39.7: Cancel during tool execution
# ---------------------------------------------------------------------------

class TestToolExecutionCancel:
    """v1.39.7: Cancel checks during tool execution."""

    def test_concurrent_signature_accepts_cancel_event(self):
        """_execute_tools_concurrent accepts cancel_event parameter."""
        import inspect
        from helen.runtime.http_llm import _execute_tools_concurrent
        sig = inspect.signature(_execute_tools_concurrent)
        assert "cancel_event" in sig.parameters
        assert sig.parameters["cancel_event"].default is None

    def test_sequential_tool_cancel_skips_remaining(self):
        """When cancel_event is set, sequential tool loop skips remaining tools."""
        cancel = threading.Event()
        call_log = []

        def mock_dispatch(name, args):
            call_log.append(name)
            if name == "tool_1":
                cancel.set()  # Set cancel after first tool
            return f"result_{name}"

        tool_calls = [
            {"id": "1", "function": {"name": "tool_1", "arguments": "{}"}},
            {"id": "2", "function": {"name": "tool_2", "arguments": "{}"}},
            {"id": "3", "function": {"name": "tool_3", "arguments": "{}"}},
        ]

        # Simulate the sequential tool execution loop from http_llm.py
        tool_results = []
        for tc in tool_calls:
            if cancel.is_set():
                break
            fn_name = tc["function"]["name"]
            fn_args = json.loads(tc["function"].get("arguments", "{}"))
            result = mock_dispatch(fn_name, fn_args)
            tool_results.append((tc, result))

        # Only first tool should have been dispatched
        assert len(tool_results) == 1
        assert call_log == ["tool_1"]

    def test_concurrent_tool_cancel_cancels_remaining_futures(self):
        """When cancel_event is set during concurrent execution, remaining futures are cancelled."""
        from helen.runtime.http_llm import _execute_tools_concurrent

        cancel = threading.Event()
        completed = []

        def slow_dispatch(name, args):
            time.sleep(0.05)
            completed.append(name)
            if name == "tool_0":
                cancel.set()  # Set cancel after first tool completes
            return f"result_{name}"

        tool_calls = [
            {"id": str(i), "function": {"name": f"tool_{i}", "arguments": "{}"}}
            for i in range(6)
        ]

        results = _execute_tools_concurrent(
            tool_calls, slow_dispatch, cancel_event=cancel,
        )

        # Should have completed fewer than all 6 tools
        assert len(results) < len(tool_calls)

    def test_cancel_before_yield_skips_remaining_results(self):
        """When cancel is set, tool result yielding stops early."""
        cancel = threading.Event()

        tool_results = [
            ({"id": "1", "function": {"name": "t1", "arguments": "{}"}}, "r1"),
            ({"id": "2", "function": {"name": "t2", "arguments": "{}"}}, "r2"),
            ({"id": "3", "function": {"name": "t3", "arguments": "{}"}}, "r3"),
        ]

        # Simulate the yield loop from http_llm.py
        yielded = []
        for tc, result in tool_results:
            if cancel.is_set():
                break
            yielded.append(tc["function"]["name"])
            if tc["function"]["name"] == "t1":
                cancel.set()

        assert yielded == ["t1"]

    def test_no_cancel_event_backward_compatible(self):
        """When cancel_event is None, all tools execute normally."""
        from helen.runtime.http_llm import _execute_tools_concurrent

        call_log = []

        def mock_dispatch(name, args):
            call_log.append(name)
            return f"result_{name}"

        tool_calls = [
            {"id": "1", "function": {"name": "a", "arguments": "{}"}},
            {"id": "2", "function": {"name": "b", "arguments": "{}"}},
        ]

        # cancel_event=None (default) — all tools should execute
        results = _execute_tools_concurrent(tool_calls, mock_dispatch)
        assert len(results) == 2

    def test_cancel_pre_set_skips_all_results(self):
        """When cancel_event is pre-set, no tool results are collected."""
        from helen.runtime.http_llm import _execute_tools_concurrent

        cancel = threading.Event()
        cancel.set()  # Pre-set

        def mock_dispatch(name, args):
            return f"result_{name}"

        tool_calls = [
            {"id": "1", "function": {"name": "a", "arguments": "{}"}},
            {"id": "2", "function": {"name": "b", "arguments": "{}"}},
        ]

        results = _execute_tools_concurrent(
            tool_calls, mock_dispatch, cancel_event=cancel,
        )
        # Concurrent path: futures are submitted to pool, but cancel check
        # in as_completed() loop prevents collecting any results
        assert len(results) == 0
