"""Tests for streaming response async iteration (Phase 3)."""

import pytest
import asyncio
from helen.runtime.streaming_response import StreamingResponse


class TestStreamingResponse:
    """Tests for StreamingResponse async iteration."""
    
    def test_streaming_response_basic(self):
        """StreamingResponse should wrap a stream iterator."""
        def mock_stream():
            yield {"content": "Hello"}
            yield {"content": " "}
            yield {"content": "World"}
        
        response = StreamingResponse(mock_stream())
        assert response is not None
    
    @pytest.mark.asyncio
    async def test_streaming_response_iteration(self):
        """StreamingResponse should be async iterable."""
        def mock_stream():
            yield {"content": "Hello"}
            yield {"content": " "}
            yield {"content": "World"}
        
        response = StreamingResponse(mock_stream())
        chunks = []
        async for chunk in response:
            chunks.append(chunk)
        
        assert chunks == ["Hello", " ", "World"]
    
    @pytest.mark.asyncio
    async def test_streaming_response_empty(self):
        """StreamingResponse should handle empty streams."""
        def mock_stream():
            return
            yield  # Make it a generator
        
        response = StreamingResponse(mock_stream())
        chunks = []
        async for chunk in response:
            chunks.append(chunk)
        
        assert chunks == []
    
    @pytest.mark.asyncio
    async def test_streaming_response_with_objects(self):
        """StreamingResponse should handle objects with content attribute."""
        class MockChunk:
            def __init__(self, content):
                self.content = content
        
        def mock_stream():
            yield MockChunk("Hello")
            yield MockChunk(" World")
        
        response = StreamingResponse(mock_stream())
        chunks = []
        async for chunk in response:
            chunks.append(chunk)
        
        assert chunks == ["Hello", " World"]
    
    @pytest.mark.asyncio
    async def test_streaming_response_concatenation(self):
        """StreamingResponse chunks should concatenate to full response."""
        def mock_stream():
            yield {"content": "The "}
            yield {"content": "quick "}
            yield {"content": "brown "}
            yield {"content": "fox"}
        
        response = StreamingResponse(mock_stream())
        full_text = ""
        async for chunk in response:
            full_text += chunk
        
        assert full_text == "The quick brown fox"
