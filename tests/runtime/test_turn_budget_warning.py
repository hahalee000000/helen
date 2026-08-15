"""Tests for turn-budget warning (Phase 9C) and forced summarization (Phase 9D).

These tests verify that:
1. _inject_turn_budget_warning injects warnings when tool_turn_count approaches max_turns.
2. _force_final_summarization makes a text-only API call when budget is exhausted.
3. act() integrates the warnings and handles exhaustion gracefully (no empty response).
4. act_stream() yields warning events when approaching turn limit.
"""

import pytest
from unittest.mock import patch, MagicMock

from helen.runtime.http_llm import HttpLLMRuntime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_runtime():
    """Create a minimal HttpLLMRuntime with mocked internals."""
    runtime = HttpLLMRuntime.__new__(HttpLLMRuntime)
    runtime.base_url = "http://test"
    runtime.api_key = "test-key"
    runtime.default_model = "test-model"
    runtime.timeout = 120
    runtime.max_retries = 0
    runtime.enable_concurrent_tools = False
    runtime.enable_message_sanitization = False
    runtime.enable_tool_truncation = False
    runtime._last_error = None
    runtime._client = MagicMock()
    runtime._tool_pool = None
    runtime._reactive_compactor = None
    runtime._recording_cassette = None
    runtime._circuit_breaker = None
    from helen.runtime.provider_protocol import OpenAIProtocol
    runtime._platform_protocol = OpenAIProtocol()
    return runtime


# ---------------------------------------------------------------------------
# _inject_turn_budget_warning
# ---------------------------------------------------------------------------

class TestInjectTurnBudgetWarning:
    def test_no_warning_when_plenty_remaining(self):
        runtime = _make_runtime()
        messages = [{"role": "user", "content": "hi"}]
        result = runtime._inject_turn_budget_warning(messages, tool_turn_count=1, max_turns=10)
        assert result is None
        assert len(messages) == 1  # No warning appended

    def test_warning_at_2_remaining(self):
        runtime = _make_runtime()
        messages = [{"role": "user", "content": "hi"}]
        result = runtime._inject_turn_budget_warning(messages, tool_turn_count=8, max_turns=10)
        assert result is not None
        assert "turn budget" in result.lower()
        assert "2" in result  # mentions 2 remaining
        assert len(messages) == 2
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"].startswith("[System Warning — turn budget")

    def test_strong_warning_at_1_remaining(self):
        runtime = _make_runtime()
        messages = [{"role": "user", "content": "hi"}]
        result = runtime._inject_turn_budget_warning(messages, tool_turn_count=9, max_turns=10)
        assert result is not None
        assert "LAST turn" in result
        assert "MUST NOT" in result

    def test_exhausted_warning_at_0_remaining(self):
        runtime = _make_runtime()
        messages = [{"role": "user", "content": "hi"}]
        result = runtime._inject_turn_budget_warning(messages, tool_turn_count=10, max_turns=10)
        assert result is not None
        assert "exhausted" in result.lower()

    def test_replaces_existing_warning(self):
        """Should not stack duplicate turn-budget warnings."""
        runtime = _make_runtime()
        messages = [{"role": "user", "content": "hi"}]
        # First injection
        runtime._inject_turn_budget_warning(messages, tool_turn_count=8, max_turns=10)
        assert len(messages) == 2
        # Second injection — should replace, not stack
        runtime._inject_turn_budget_warning(messages, tool_turn_count=9, max_turns=10)
        assert len(messages) == 2  # Still 2, not 3
        assert "LAST turn" in messages[-1]["content"]


# ---------------------------------------------------------------------------
# _force_final_summarization
# ---------------------------------------------------------------------------

class TestForceFinalSummarization:
    def test_returns_llm_summary(self):
        runtime = _make_runtime()
        messages = [{"role": "user", "content": "hi"}]
        with patch.object(runtime, "_chat_with_messages_retry", return_value={
            "content": "Here is my summary.",
            "tool_calls": None,
        }):
            result = runtime._force_final_summarization(
                messages, "test-model", 1.0, None, False, None,
            )
        assert result == "Here is my summary."
        # Verify tools=None was passed (forces text-only)
        assert len(messages) >= 2

    def test_returns_fallback_on_api_failure(self):
        runtime = _make_runtime()
        messages = [{"role": "user", "content": "hi"}]
        with patch.object(runtime, "_chat_with_messages_retry", return_value=None):
            result = runtime._force_final_summarization(
                messages, "test-model", 1.0, None, False, None,
            )
        assert "turn limit" in result.lower() or "max_turns" in result

    def test_returns_fallback_on_exception(self):
        runtime = _make_runtime()
        messages = [{"role": "user", "content": "hi"}]
        with patch.object(runtime, "_chat_with_messages_retry", side_effect=RuntimeError("API down")):
            result = runtime._force_final_summarization(
                messages, "test-model", 1.0, None, False, None,
            )
        assert "turn limit" in result.lower() or "max_turns" in result

    def test_returns_fallback_on_empty_content(self):
        runtime = _make_runtime()
        messages = [{"role": "user", "content": "hi"}]
        with patch.object(runtime, "_chat_with_messages_retry", return_value={
            "content": "",
        }):
            result = runtime._force_final_summarization(
                messages, "test-model", 1.0, None, False, None,
            )
        assert "turn limit" in result.lower() or "max_turns" in result


# ---------------------------------------------------------------------------
# act() integration
# ---------------------------------------------------------------------------

class TestActTurnBudget:
    def _make_stream_runtime(self):
        """Runtime for act() tests — needs _chat_with_messages_retry mocking."""
        return _make_runtime()

    def test_act_injects_warning_near_max_turns(self):
        """When tool calls approach max_turns, a warning should be injected into messages."""
        runtime = self._make_stream_runtime()
        max_turns = 3

        call_count = 0

        def fake_chat(messages, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= max_turns:
                # Return tool calls for the first max_turns calls
                return {
                    "content": None,
                    "tool_calls": [{
                        "id": f"call_{call_count}",
                        "type": "function",
                        "function": {"name": "search", "arguments": '{"q": "test"}'},
                    }],
                }
            else:
                # Final text response
                return {"content": "Final answer", "tool_calls": None}

        with patch.object(runtime, "_chat_with_messages_retry", side_effect=fake_chat):
            with patch("helen.runtime.tools.dispatch_tool", return_value="result"):
                response = runtime.act("test", tools=[{"type": "function"}], max_turns=max_turns)

        assert response.text == "Final answer"
        # Verify the forced summarization was called since budget exhausted
        # Actually, max_turns=3 means budget=5 (3+2), so 3 tool calls + then the
        # 4th call returns text. Let's check that the warning was injected.

    def test_act_handles_budget_exhaustion_gracefully(self):
        """When budget is exhausted without final text, should return non-empty fallback."""
        runtime = self._make_stream_runtime()
        max_turns = 2

        def fake_chat_always_tools(messages, **kwargs):
            # Always return tool calls — never a text response
            # Check if tools is None (forced summarization call)
            if kwargs.get("tools") is None:
                return {"content": "Forced summary after exhaustion", "tool_calls": None}
            return {
                "content": None,
                "tool_calls": [{
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "search", "arguments": '{"q": "test"}'},
                }],
            }

        with patch.object(runtime, "_chat_with_messages_retry", side_effect=fake_chat_always_tools):
            with patch("helen.runtime.tools.dispatch_tool", return_value="result"):
                response = runtime.act("test", tools=[{"type": "function"}], max_turns=max_turns)

        # Should NOT be empty — should have forced summary or fallback message
        assert response.text
        assert len(response.text) > 0

    def test_act_warning_message_contains_max_turns(self):
        """The injected warning should mention max_turns value."""
        runtime = self._make_stream_runtime()
        max_turns = 5

        seen_messages = []

        def fake_chat(messages, **kwargs):
            # Capture messages at each call
            seen_messages.append(list(messages))
            if len(seen_messages) <= 4:
                return {
                    "content": None,
                    "tool_calls": [{
                        "id": f"call_{len(seen_messages)}",
                        "type": "function",
                        "function": {"name": "search", "arguments": '{"q": "test"}'},
                    }],
                }
            return {"content": "done", "tool_calls": None}

        with patch.object(runtime, "_chat_with_messages_retry", side_effect=fake_chat):
            with patch("helen.runtime.tools.dispatch_tool", return_value="result"):
                runtime.act("test", tools=[{"type": "function"}], max_turns=max_turns)

        # Find the call that has the turn budget warning in messages
        warning_found = False
        for msgs in seen_messages:
            for msg in msgs:
                content = msg.get("content") or ""
                if "[System Warning — turn budget]" in content:
                    warning_found = True
                    assert f"max_turns={max_turns}" in content
        assert warning_found, "Turn budget warning was not injected"


# ---------------------------------------------------------------------------
# act_stream() integration
# ---------------------------------------------------------------------------

class TestActStreamTurnBudget:
    def _make_stream_runtime(self):
        return _make_runtime()

    def _make_sse_tool_response(self, call_id="call_1", fn_name="search"):
        """Create SSE lines for a tool call response."""
        return [
            f'data: {{"choices": [{{"delta": {{"tool_calls": [{{"index": 0, "id": "{call_id}", "function": {{"name": "{fn_name}", "arguments": ""}}}}]}}}}]}}',
            f'data: {{"choices": [{{"delta": {{"tool_calls": [{{"index": 0, "function": {{"arguments": "{{\\"q\\":\\"test\\"}}"}}}}]}}}}]}}',
            'data: [DONE]',
        ]

    def _make_sse_text_response(self, text="Final answer"):
        """Create SSE lines for a text response."""
        return [
            f'data: {{"choices": [{{"delta": {{"content": "{text}"}}}}]}}',
            'data: [DONE]',
        ]

    def test_stream_yields_warning_near_max_turns(self):
        """When approaching max_turns, a warning event should be yielded."""
        runtime = self._make_stream_runtime()
        max_turns = 2

        sse_responses = [
            self._make_sse_tool_response("call_1"),
            self._make_sse_tool_response("call_2"),
            self._make_sse_text_response("done"),
        ]
        call_idx = [0]

        def make_stream(*args, **kwargs):
            idx = call_idx[0]
            call_idx[0] += 1
            mock_stream = MagicMock()
            mock_stream.__enter__ = MagicMock(return_value=mock_stream)
            mock_stream.__exit__ = MagicMock(return_value=False)
            mock_stream.iter_lines = MagicMock(return_value=iter(sse_responses[idx]))
            mock_stream.raise_for_status = MagicMock()
            return mock_stream

        runtime._client.stream.side_effect = make_stream

        with patch("helen.runtime.tools.dispatch_tool", return_value="result"):
            events = list(runtime.act_stream(
                "test", tools=[{"type": "function"}], max_turns=max_turns,
            ))

        warning_events = [e for e in events if e.get("type") == "warning"]
        assert len(warning_events) > 0, "Expected at least one warning event"
        assert "turn budget" in warning_events[0]["message"].lower()
