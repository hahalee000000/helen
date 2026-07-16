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
