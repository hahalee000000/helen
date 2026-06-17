"""Streaming response wrapper for async iteration (Phase 3).

Wraps a streaming LLM response as an async iterable for use with 'for await'.
"""

from __future__ import annotations

from typing import Any, AsyncIterator


class StreamingResponse:
    """Async iterable wrapper for streaming LLM responses.
    
    Usage:
        response = llm.stream("prompt")
        async for chunk in response:
            print(chunk)
    """
    
    def __init__(self, stream_iterator: Any):
        """Initialize with a stream iterator.
        
        Args:
            stream_iterator: An iterator yielding dicts with 'content' key
        """
        self._iterator = stream_iterator
    
    def __aiter__(self) -> AsyncIterator[str]:
        """Return an async iterator over response chunks."""
        return self._async_iter()
    
    async def _async_iter(self) -> AsyncIterator[str]:
        """Async generator that yields chunks."""
        for chunk in self._iterator:
            if isinstance(chunk, dict) and 'content' in chunk:
                yield chunk['content']
            elif hasattr(chunk, 'content'):
                yield chunk.content
            else:
                yield str(chunk)
