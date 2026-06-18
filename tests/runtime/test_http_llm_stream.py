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

    def test_act_stream_yields_chunks(self):
        """act_stream should yield chunks from SSE response."""
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
            chunks = list(runtime.act_stream("test prompt"))
        
        assert len(chunks) == 2
        assert chunks[0] == {"content": "Hello"}
        assert chunks[1] == {"content": " World"}

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
            chunks = list(runtime.act_stream("test prompt"))
        
        assert len(chunks) == 1
        assert chunks[0] == {"content": "Hello"}

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
            chunks = list(runtime.act_stream("test prompt"))
        
        assert len(chunks) == 1
        assert chunks[0] == {"content": "Hello"}
