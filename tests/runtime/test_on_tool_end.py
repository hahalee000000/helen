"""Tests for on_tool_end callback in http_llm.py act() and act_stream().

v1.21: on_tool_end callback allows injecting hints into the agentic loop
after each tool execution. Returns str (user hint), dict (full message),
or None (no injection).
"""
import json
from unittest.mock import MagicMock, AsyncMock
from helen.runtime.http_llm import HttpLLMRuntime


def _make_runtime():
    """Create HttpLLMRuntime with mocked httpx client (no real HTTP calls)."""
    runtime = HttpLLMRuntime.__new__(HttpLLMRuntime)
    runtime.base_url = "http://test"
    runtime.api_key = "test-key"
    runtime.default_model = "test-model"
    runtime.timeout = 120
    runtime.max_retries = 0
    runtime.enable_concurrent_tools = False
    runtime.enable_message_sanitization = True
    runtime.enable_tool_truncation = False
    runtime.enable_reactive_compaction = False
    runtime._reactive_compactor = None
    runtime._last_error = None
    runtime._client = MagicMock()
    runtime._async_client = AsyncMock()
    runtime._tool_pool = MagicMock()
    return runtime


def _mock_dispatch(name: str, args: dict) -> str:
    """Mock dispatch function that returns predictable results."""
    return f"result_of_{name}"


def _make_tool_call_response(tool_name: str, tool_args: dict, call_id: str = "call_1"):
    """Create a mock LLM response that contains a tool call."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(tool_args),
                    },
                }],
            },
            "finish_reason": "tool_calls",
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }
    return response


def _make_text_response(text: str):
    """Create a mock LLM response with plain text content."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": text,
            },
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }
    return response


TEST_TOOLS = [{"type": "function", "function": {
    "name": "read_file",
    "parameters": {"type": "object", "properties": {}},
}}]


class TestOnToolEndInAct:
    """Test on_tool_end callback in act() (synchronous)."""

    def test_callback_called_after_tool_execution(self):
        """on_tool_end_fn is invoked with (tool_name, tool_result) after each tool."""
        runtime = _make_runtime()
        callback = MagicMock(return_value=None)

        runtime._client.post.side_effect = [
            _make_tool_call_response("read_file", {"path": "/test.py"}),
            _make_text_response("done"),
        ]

        runtime.act(
            "read /test.py",
            tools=TEST_TOOLS,
            max_turns=3,
            dispatch_fn=_mock_dispatch,
            on_tool_end_fn=callback,
        )

        callback.assert_called_once_with("read_file", "result_of_read_file")

    def test_string_return_injects_user_message(self):
        """Returning a string injects a user message with [System Hint] prefix."""
        runtime = _make_runtime()
        hint_fn = MagicMock(return_value="file was written, run tests next")

        runtime._client.post.side_effect = [
            _make_tool_call_response("write_file", {"path": "/x.py"}),
            _make_text_response("ok"),
        ]

        runtime.act(
            "write x.py",
            tools=[{"type": "function", "function": {
                "name": "write_file",
                "parameters": {"type": "object", "properties": {}},
            }}],
            max_turns=3,
            dispatch_fn=_mock_dispatch,
            on_tool_end_fn=hint_fn,
        )

        # Check second post call — should include the injected user message
        second_call = runtime._client.post.call_args_list[1]
        body = second_call.kwargs.get("json", {})
        messages = body.get("messages", [])
        hint_msgs = [m for m in messages if m.get("role") == "user"
                     and "[System Hint" in m.get("content", "")]
        assert len(hint_msgs) == 1
        assert "write_file" in hint_msgs[0]["content"]
        assert "run tests next" in hint_msgs[0]["content"]

    def test_dict_return_injects_with_role_and_content(self):
        """Returning a dict injects with role/content from the dict."""
        runtime = _make_runtime()
        hint_fn = MagicMock(return_value={
            "role": "system",
            "content": "CRITICAL: do not delete files",
        })

        runtime._client.post.side_effect = [
            _make_tool_call_response("shell_exec", {"command": "ls"}),
            _make_text_response("ok"),
        ]

        runtime.act(
            "list files",
            tools=[{"type": "function", "function": {
                "name": "shell_exec",
                "parameters": {"type": "object", "properties": {}},
            }}],
            max_turns=3,
            dispatch_fn=_mock_dispatch,
            on_tool_end_fn=hint_fn,
        )

        second_call = runtime._client.post.call_args_list[1]
        body = second_call.kwargs.get("json", {})
        messages = body.get("messages", [])
        system_hints = [m for m in messages
                        if m.get("role") == "system"
                        and "CRITICAL" in m.get("content", "")]
        assert len(system_hints) == 1

    def test_none_return_does_not_inject(self):
        """Returning None does not add any extra messages."""
        runtime = _make_runtime()
        hint_fn = MagicMock(return_value=None)

        runtime._client.post.side_effect = [
            _make_tool_call_response("read_file", {"path": "/x"}),
            _make_text_response("done"),
        ]

        runtime.act(
            "read x",
            tools=TEST_TOOLS,
            max_turns=3,
            dispatch_fn=_mock_dispatch,
            on_tool_end_fn=hint_fn,
        )

        second_call = runtime._client.post.call_args_list[1]
        body = second_call.kwargs.get("json", {})
        messages = body.get("messages", [])
        hint_msgs = [m for m in messages
                     if m.get("content") and "[System Hint" in m["content"]]
        assert len(hint_msgs) == 0

    def test_callback_exception_does_not_break_loop(self):
        """Exception in on_tool_end_fn does not break the agentic loop."""
        runtime = _make_runtime()

        def bad_callback(name, result):
            raise ValueError("boom")

        runtime._client.post.side_effect = [
            _make_tool_call_response("read_file", {"path": "/x"}),
            _make_text_response("done"),
        ]

        response = runtime.act(
            "read x",
            tools=TEST_TOOLS,
            max_turns=3,
            dispatch_fn=_mock_dispatch,
            on_tool_end_fn=bad_callback,
        )

        assert response is not None
        assert response.text == "done"

    def test_no_callback_no_injection(self):
        """Without on_tool_end_fn, no extra messages are injected."""
        runtime = _make_runtime()

        runtime._client.post.side_effect = [
            _make_tool_call_response("read_file", {"path": "/x"}),
            _make_text_response("done"),
        ]

        runtime.act(
            "read x",
            tools=TEST_TOOLS,
            max_turns=3,
            dispatch_fn=_mock_dispatch,
            # No on_tool_end_fn
        )

        second_call = runtime._client.post.call_args_list[1]
        body = second_call.kwargs.get("json", {})
        messages = body.get("messages", [])
        hint_msgs = [m for m in messages
                     if m.get("content") and "[System Hint" in m["content"]]
        assert len(hint_msgs) == 0

    def test_dict_return_empty_content_not_injected(self):
        """Dict return with empty content is skipped."""
        runtime = _make_runtime()
        hint_fn = MagicMock(return_value={"role": "user", "content": ""})

        runtime._client.post.side_effect = [
            _make_tool_call_response("read_file", {"path": "/x"}),
            _make_text_response("done"),
        ]

        runtime.act(
            "read x",
            tools=TEST_TOOLS,
            max_turns=3,
            dispatch_fn=_mock_dispatch,
            on_tool_end_fn=hint_fn,
        )

        second_call = runtime._client.post.call_args_list[1]
        body = second_call.kwargs.get("json", {})
        messages = body.get("messages", [])
        # No extra messages should be injected (empty content skipped)
        hint_msgs = [m for m in messages
                     if (m.get("content") and "[System Hint" in m["content"])
                     or m.get("role") == "system"]
        assert len(hint_msgs) == 0


class TestHintCollector:
    """Test hint_collector_fn for persisting hints to TranscriptStore."""

    def test_hint_collector_called_for_string_hint(self):
        """hint_collector_fn is called with hint message dict when returning string."""
        runtime = _make_runtime()
        hint_fn = MagicMock(return_value="file written")
        collector = MagicMock()

        runtime._client.post.side_effect = [
            _make_tool_call_response("write_file", {"path": "/x.py"}),
            _make_text_response("done"),
        ]

        runtime.act(
            "write x.py",
            tools=[{"type": "function", "function": {
                "name": "write_file",
                "parameters": {"type": "object", "properties": {}},
            }}],
            max_turns=3,
            dispatch_fn=_mock_dispatch,
            on_tool_end_fn=hint_fn,
            hint_collector_fn=collector,
        )

        # Collector should be called once with the hint message
        collector.assert_called_once()
        hint_msg = collector.call_args[0][0]
        assert hint_msg["role"] == "user"
        assert "[System Hint" in hint_msg["content"]
        assert "file written" in hint_msg["content"]

    def test_hint_collector_called_for_dict_hint(self):
        """hint_collector_fn is called with hint message dict when returning dict."""
        runtime = _make_runtime()
        hint_fn = MagicMock(return_value={
            "role": "system",
            "content": "CRITICAL warning",
        })
        collector = MagicMock()

        runtime._client.post.side_effect = [
            _make_tool_call_response("shell_exec", {"command": "rm -rf /"}),
            _make_text_response("ok"),
        ]

        runtime.act(
            "run command",
            tools=[{"type": "function", "function": {
                "name": "shell_exec",
                "parameters": {"type": "object", "properties": {}},
            }}],
            max_turns=3,
            dispatch_fn=_mock_dispatch,
            on_tool_end_fn=hint_fn,
            hint_collector_fn=collector,
        )

        collector.assert_called_once()
        hint_msg = collector.call_args[0][0]
        assert hint_msg["role"] == "system"
        assert hint_msg["content"] == "CRITICAL warning"

    def test_hint_collector_not_called_when_no_hint(self):
        """hint_collector_fn is not called when on_tool_end returns None."""
        runtime = _make_runtime()
        hint_fn = MagicMock(return_value=None)
        collector = MagicMock()

        runtime._client.post.side_effect = [
            _make_tool_call_response("read_file", {"path": "/x"}),
            _make_text_response("done"),
        ]

        runtime.act(
            "read x",
            tools=TEST_TOOLS,
            max_turns=3,
            dispatch_fn=_mock_dispatch,
            on_tool_end_fn=hint_fn,
            hint_collector_fn=collector,
        )

        collector.assert_not_called()

    def test_hint_collector_called_multiple_times(self):
        """hint_collector_fn is called for each hint in multi-turn loop."""
        runtime = _make_runtime()

        # Return different hints based on tool name
        def hint_fn(name, result):
            if name == "tool_a":
                return "hint_a"
            elif name == "tool_b":
                return "hint_b"
            return None

        collector = MagicMock()

        runtime._client.post.side_effect = [
            _make_tool_call_response("tool_a", {}),
            _make_tool_call_response("tool_b", {}, "call_2"),
            _make_text_response("done"),
        ]

        runtime.act(
            "do stuff",
            tools=[
                {"type": "function", "function": {
                    "name": "tool_a",
                    "parameters": {"type": "object", "properties": {}},
                }},
                {"type": "function", "function": {
                    "name": "tool_b",
                    "parameters": {"type": "object", "properties": {}},
                }},
            ],
            max_turns=5,
            dispatch_fn=_mock_dispatch,
            on_tool_end_fn=hint_fn,
            hint_collector_fn=collector,
        )

        # Collector should be called twice
        assert collector.call_count == 2
        # First call: hint_a
        first_hint = collector.call_args_list[0][0][0]
        assert "hint_a" in first_hint["content"]
        # Second call: hint_b
        second_hint = collector.call_args_list[1][0][0]
        assert "hint_b" in second_hint["content"]
