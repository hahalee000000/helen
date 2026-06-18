"""Tests for HttpLLMRuntime.act_stream streaming support."""

import pytest
from unittest.mock import patch, MagicMock
from helen.runtime.http_llm import HttpLLMRuntime


class TestHttpLLMRuntimeStream:
    """Test streaming support in HttpLLMRuntime."""

    def test_act_stream_exists(self):
        """HttpLLMRuntime should have act_stream method."""
        runtime = HttpLLMRuntime(base_url="http://test", api_key="test-key")
        assert hasattr(runtime, "act_stream")
        assert callable(runtime.act_stream)

    def test_act_stream_yields_content_events(self):
        """act_stream should yield content events from SSE response."""
        runtime = HttpLLMRuntime(base_url="http://test", api_key="test-key")
        
        # Mock SSE response
        sse_lines = [
            b'data: {"choices": [{"delta": {"content": "Hello"}}]}\n',
            b'data: {"choices": [{"delta": {"content": " World"}}]}\n',
            b'data: [DONE]\n',
        ]
        
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=iter(sse_lines))
        mock_response.__exit__ = MagicMock(return_value=False)
        
        with patch('urllib.request.urlopen', return_value=mock_response):
            events = list(runtime.act_stream("test prompt"))
        
        assert len(events) == 2
        assert events[0] == {"type": "content", "content": "Hello"}
        assert events[1] == {"type": "content", "content": " World"}

    def test_act_stream_handles_empty_content(self):
        """act_stream should skip chunks with empty content."""
        runtime = HttpLLMRuntime(base_url="http://test", api_key="test-key")
        
        sse_lines = [
            b'data: {"choices": [{"delta": {"content": ""}}]}\n',
            b'data: {"choices": [{"delta": {"content": "Hello"}}]}\n',
            b'data: [DONE]\n',
        ]
        
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=iter(sse_lines))
        mock_response.__exit__ = MagicMock(return_value=False)
        
        with patch('urllib.request.urlopen', return_value=mock_response):
            events = list(runtime.act_stream("test prompt"))
        
        assert len(events) == 1
        assert events[0] == {"type": "content", "content": "Hello"}

    def test_act_stream_handles_malformed_json(self):
        """act_stream should skip malformed JSON lines."""
        runtime = HttpLLMRuntime(base_url="http://test", api_key="test-key")
        
        sse_lines = [
            b'data: {invalid json}\n',
            b'data: {"choices": [{"delta": {"content": "Hello"}}]}\n',
            b'data: [DONE]\n',
        ]
        
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=iter(sse_lines))
        mock_response.__exit__ = MagicMock(return_value=False)
        
        with patch('urllib.request.urlopen', return_value=mock_response):
            events = list(runtime.act_stream("test prompt"))
        
        assert len(events) == 1
        assert events[0] == {"type": "content", "content": "Hello"}

    def test_act_stream_tool_calls(self):
        """act_stream should accumulate and yield tool call events."""
        runtime = HttpLLMRuntime(base_url="http://test", api_key="test-key")
        
        # Mock SSE with tool call deltas then a final text response
        sse_lines_turn1 = [
            b'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_1", "function": {"name": "web_search", "arguments": ""}}]}}]}\n',
            b'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": "{\\"query\\""}}]}}]}\n',
            b'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": ":\\"test\\"}"}}]}}]}\n',
            b'data: [DONE]\n',
        ]
        # After tool execution, second turn returns text
        sse_lines_turn2 = [
            b'data: {"choices": [{"delta": {"content": "Final answer"}}]}\n',
            b'data: [DONE]\n',
        ]
        
        responses = [iter(sse_lines_turn1), iter(sse_lines_turn2)]
        call_count = [0]
        
        def mock_urlopen(*args, **kwargs):
            mock_resp = MagicMock()
            mock_resp.__enter__ = MagicMock(return_value=responses[call_count[0]])
            mock_resp.__exit__ = MagicMock(return_value=False)
            call_count[0] += 1
            return mock_resp
        
        with patch('urllib.request.urlopen', side_effect=mock_urlopen):
            with patch('helen.runtime.tools.dispatch_tool', return_value="search result"):
                events = list(runtime.act_stream("test prompt", tools=[{"type": "function"}]))
        
        # Should have: tool_call, tool_result, content
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
