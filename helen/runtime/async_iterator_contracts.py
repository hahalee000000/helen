"""Async iterator contracts for Helen language (Phase 3).

This module defines the interface contracts for async iteration.
Implementation will follow TDD after tests are written.
"""

from typing import Protocol, runtime_checkable, AsyncIterator, Any


@runtime_checkable
class AsyncIterable(Protocol):
    """Contract for async iterable objects.
    
    Objects that can be iterated asynchronously using 'for await'.
    """
    
    def __aiter__(self) -> AsyncIterator[Any]:
        """Return an async iterator."""
        ...


@runtime_checkable
class StreamingResponse(Protocol):
    """Contract for streaming LLM response.
    
    Wraps a streaming LLM response as an async iterable.
    """
    
    def __aiter__(self) -> AsyncIterator[str]:
        """Return an async iterator over response chunks."""
        ...


@runtime_checkable
class AsyncGenerator(Protocol):
    """Contract for async generator functions.
    
    Functions that yield values asynchronously.
    """
    
    def __aiter__(self) -> AsyncIterator[Any]:
        """Return an async iterator."""
        ...
    
    async def __anext__(self) -> Any:
        """Return the next value or raise StopAsyncIteration."""
        ...
