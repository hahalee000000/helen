"""Tests for v1.46 incremental transcript save via transcript_fn callback.

Verifies that tool calls and tool results are persisted to transcript
incrementally as they happen during llm act, so tool call work survives
mid-turn crashes.
"""

from __future__ import annotations

import pytest

from helen.runtime.http_llm import HttpLLMRuntime
from helen.runtime.llm_runtime import LLMResponse, MockLLMRuntime


class TestTranscriptFnSignature:
    """Test transcript_fn parameter is accepted by act/act_stream."""

    def test_mock_act_accepts_transcript_fn(self):
        """MockLLMRuntime.act() accepts transcript_fn without error."""
        mock = MockLLMRuntime(act_return="hello")
        calls = []
        mock.act(
            "prompt",
            transcript_fn=lambda role, content, **kw: calls.append((role, content, kw)),
        )
        # Mock doesn't execute tool calls, so transcript_fn is never called
        assert calls == []

    def test_mock_act_stream_accepts_transcript_fn(self):
        """MockLLMRuntime default act_stream() accepts transcript_fn without error."""
        mock = MockLLMRuntime(act_return="hello")
        calls = []
        events = list(mock.act_stream(
            "prompt",
            transcript_fn=lambda role, content, **kw: calls.append((role, content, kw)),
        ))
        assert len(events) == 1
        assert events[0]["type"] == "content"
        assert calls == []


class TestTranscriptFnCallbackShape:
    """Test transcript_fn is called with correct arguments during tool execution."""

    def test_transcript_fn_called_for_assistant_with_tool_calls(self, monkeypatch):
        """When LLM returns tool_calls, transcript_fn is called with assistant role."""
        calls = []

        def fake_chat(self, messages, **kwargs):
            # First call: return tool_calls
            if not hasattr(self, "_test_call_count"):
                self._test_call_count = 0
            self._test_call_count += 1
            if self._test_call_count == 1:
                return {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "shell_exec",
                            "arguments": '{"command": "ls"}',
                        },
                    }],
                }
            # Second call: return final text
            return {"role": "assistant", "content": "Done."}

        monkeypatch.setattr(HttpLLMRuntime, "_chat_with_messages", fake_chat)

        llm = HttpLLMRuntime(base_url="http://test", api_key="test")

        def transcript_fn(role, content, **kwargs):
            calls.append({"role": role, "content": content, **kwargs})

        result = llm.act(
            "do something",
            tools=[{
                "type": "function",
                "function": {
                    "name": "shell_exec",
                    "description": "Run shell command",
                    "parameters": {"type": "object", "properties": {"command": {"type": "string"}}},
                },
            }],
            max_turns=2,
            transcript_fn=transcript_fn,
        )

        # Should have at least 2 calls: assistant with tool_calls + tool result
        assert len(calls) >= 2

        # First call: assistant message with tool_calls
        first = calls[0]
        assert first["role"] == "assistant"
        assert "tool_calls" in first
        assert len(first["tool_calls"]) == 1
        assert first["tool_calls"][0]["function"]["name"] == "shell_exec"

        # Second call: tool result
        second = calls[1]
        assert second["role"] == "tool"
        assert "tool_call_id" in second
        assert second["tool_call_id"] == "call_1"

    def test_transcript_fn_called_for_each_tool_result(self, monkeypatch):
        """When LLM returns multiple tool_calls, transcript_fn is called for each result."""
        calls = []

        def fake_chat(self, messages, **kwargs):
            if not hasattr(self, "_test_call_count"):
                self._test_call_count = 0
            self._test_call_count += 1
            if self._test_call_count == 1:
                return {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "read_file", "arguments": '{"path": "/a"}'},
                        },
                        {
                            "id": "call_2",
                            "type": "function",
                            "function": {"name": "read_file", "arguments": '{"path": "/b"}'},
                        },
                    ],
                }
            return {"role": "assistant", "content": "Done."}

        monkeypatch.setattr(HttpLLMRuntime, "_chat_with_messages", fake_chat)

        llm = HttpLLMRuntime(base_url="http://test", api_key="test")

        def transcript_fn(role, content, **kwargs):
            calls.append({"role": role, "content": content, **kwargs})

        llm.act(
            "read files",
            tools=[{
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read a file",
                    "parameters": {"type": "object", "properties": {"path": {"type": "string"}}},
                },
            }],
            max_turns=2,
            transcript_fn=transcript_fn,
        )

        # Should have: 1 assistant (with 2 tool_calls) + 2 tool results = 3 calls
        tool_results = [c for c in calls if c["role"] == "tool"]
        assert len(tool_results) == 2
        assert tool_results[0]["tool_call_id"] == "call_1"
        assert tool_results[1]["tool_call_id"] == "call_2"

    def test_transcript_fn_failure_does_not_break_loop(self, monkeypatch):
        """If transcript_fn raises, the agentic loop continues."""
        def fake_chat(self, messages, **kwargs):
            return {"role": "assistant", "content": "final"}

        monkeypatch.setattr(HttpLLMRuntime, "_chat_with_messages", fake_chat)

        llm = HttpLLMRuntime(base_url="http://test", api_key="test")

        def bad_transcript_fn(role, content, **kwargs):
            raise RuntimeError("transcript save failed!")

        # Should NOT raise
        result = llm.act("prompt", max_turns=1, transcript_fn=bad_transcript_fn)
        assert result is not None
        assert result.text == "final"


class TestTranscriptFnNone:
    """Test transcript_fn=None (default) works as before."""

    def test_act_without_transcript_fn(self, monkeypatch):
        """act() works normally when transcript_fn is not provided."""
        def fake_chat(self, messages, **kwargs):
            return {"role": "assistant", "content": "hi"}

        monkeypatch.setattr(HttpLLMRuntime, "_chat_with_messages", fake_chat)

        llm = HttpLLMRuntime(base_url="http://test", api_key="test")
        result = llm.act("hello", max_turns=1)
        assert result.text == "hi"
