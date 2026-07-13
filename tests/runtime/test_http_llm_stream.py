"""Tests for HttpLLMRuntime.act_stream streaming support (httpx-based)."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from helen.runtime.http_llm import HttpLLMRuntime


class TestHttpLLMRuntimeStream:
    """Test streaming support in HttpLLMRuntime."""

    def _make_runtime(self):
        """Create a runtime with mocked httpx client to avoid real HTTP calls."""
        runtime = HttpLLMRuntime.__new__(HttpLLMRuntime)
        runtime.base_url = "http://test"
        runtime.api_key = "test-key"
        runtime.default_model = "test-model"
        runtime.timeout = 120
        runtime.max_retries = 0
        runtime.enable_concurrent_tools = True
        runtime.enable_message_sanitization = True
        runtime.enable_tool_truncation = True
        runtime._last_error = None
        runtime._client = MagicMock()
        runtime._async_client = AsyncMock()
        runtime._tool_pool = MagicMock()
        return runtime

    def test_act_stream_exists(self):
        """HttpLLMRuntime should have act_stream method."""
        runtime = HttpLLMRuntime(base_url="http://test", api_key="test-key")
        assert hasattr(runtime, "act_stream")
        assert callable(runtime.act_stream)

    def test_act_stream_yields_content_events(self):
        """act_stream should yield content events from SSE response."""
        runtime = self._make_runtime()

        # Mock SSE response via httpx client.stream()
        sse_lines = [
            'data: {"choices": [{"delta": {"content": "Hello"}}]}',
            'data: {"choices": [{"delta": {"content": " World"}}]}',
            'data: [DONE]',
        ]

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_stream.iter_lines = MagicMock(return_value=iter(sse_lines))
        mock_stream.raise_for_status = MagicMock()
        runtime._client.stream.return_value = mock_stream

        events = list(runtime.act_stream("test prompt"))
        assert len(events) == 2
        assert events[0] == {"type": "content", "content": "Hello"}
        assert events[1] == {"type": "content", "content": " World"}

    def test_act_stream_handles_empty_content(self):
        """act_stream should skip chunks with empty content."""
        runtime = self._make_runtime()

        sse_lines = [
            'data: {"choices": [{"delta": {"content": ""}}]}',
            'data: {"choices": [{"delta": {"content": "Hello"}}]}',
            'data: [DONE]',
        ]

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_stream.iter_lines = MagicMock(return_value=iter(sse_lines))
        mock_stream.raise_for_status = MagicMock()
        runtime._client.stream.return_value = mock_stream

        events = list(runtime.act_stream("test prompt"))
        assert len(events) == 1
        assert events[0] == {"type": "content", "content": "Hello"}

    def test_act_stream_handles_malformed_json(self):
        """act_stream should skip malformed JSON lines."""
        runtime = self._make_runtime()

        sse_lines = [
            'data: {invalid json}',
            'data: {"choices": [{"delta": {"content": "Hello"}}]}',
            'data: [DONE]',
        ]

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_stream.iter_lines = MagicMock(return_value=iter(sse_lines))
        mock_stream.raise_for_status = MagicMock()
        runtime._client.stream.return_value = mock_stream

        events = list(runtime.act_stream("test prompt"))
        assert len(events) == 1
        assert events[0] == {"type": "content", "content": "Hello"}

    def test_act_stream_tool_calls(self):
        """act_stream should accumulate and yield tool call events."""
        runtime = self._make_runtime()

        # Mock SSE with tool call deltas then a final text response
        sse_lines_turn1 = [
            'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_1", "function": {"name": "web_search", "arguments": ""}}]}}]}',
            'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": "{\\"query\\""}}]}}]}',
            'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": ":\\"test\\"}"}}]}}]}',
            'data: [DONE]',
        ]
        sse_lines_turn2 = [
            'data: {"choices": [{"delta": {"content": "Final answer"}}]}',
            'data: [DONE]',
        ]

        responses = [iter(sse_lines_turn1), iter(sse_lines_turn2)]

        def make_stream(*args, **kwargs):
            mock_stream = MagicMock()
            mock_stream.__enter__ = MagicMock(return_value=mock_stream)
            mock_stream.__exit__ = MagicMock(return_value=False)
            mock_stream.iter_lines = MagicMock(return_value=responses.pop(0))
            mock_stream.raise_for_status = MagicMock()
            return mock_stream

        runtime._client.stream.side_effect = make_stream

        with patch('helen.runtime.tools.dispatch_tool', return_value="search result"):
            events = list(runtime.act_stream("test prompt", tools=[{"type": "function"}]))

        tool_calls = [e for e in events if e["type"] == "tool_call"]
        tool_results = [e for e in events if e["type"] == "tool_result"]
        contents = [e for e in events if e["type"] == "content"]

        assert len(tool_calls) == 1
        assert tool_calls[0]["name"] == "web_search"
        assert tool_calls[0]["args"] == {"query": "test"}

        assert len(tool_results) == 1
        assert tool_results[0]["name"] == "web_search"
        assert tool_results[0]["result"] == "search result"

        assert len(contents) == 1
        assert contents[0]["content"] == "Final answer"


class TestHttpLLMRuntimePool:
    """Test persistent pool and client lifecycle."""

    def test_close_cleans_up_resources(self):
        """close() should shutdown clients and pool."""
        runtime = HttpLLMRuntime(base_url="http://test", api_key="test-key")
        runtime._client = MagicMock()
        runtime._async_client = MagicMock()
        runtime._tool_pool = MagicMock()

        runtime.close()

        runtime._client.close.assert_called_once()
        runtime._async_client.aclose.assert_called_once()
        runtime._tool_pool.shutdown.assert_called_once_with(wait=False)
