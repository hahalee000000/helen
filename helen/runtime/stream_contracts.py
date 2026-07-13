"""Stream LLM output contracts for Helen language (Phase 2).

This module defines the interface contracts for streaming LLM output.
Implementation will follow TDD after tests are written.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Iterator


@runtime_checkable
class StreamChunk(Protocol):
    """A single chunk from a streaming LLM response."""

    content: str
    """The text content of this chunk."""

    finish_reason: str | None
    """Reason for finishing (e.g., 'stop', 'length', None if not finished)."""


@runtime_checkable
class StreamingLLMRuntime(Protocol):
    """Contract for streaming LLM runtime.

    Provides methods for streaming LLM responses chunk by chunk.
    """

    def act_stream(self, prompt: str, model: str | None = None,
                   temperature: float = 1.0, system_prompt: str | None = None) -> Iterator[StreamChunk]:
        """Execute LLM action with streaming response (sync).

        Args:
            prompt: The prompt text
            model: Optional model override
            temperature: Sampling temperature
            system_prompt: Optional system prompt

        Yields:
            StreamChunk objects with incremental content
        """
        ...


@runtime_checkable
class LlmStreamCallback(Protocol):
    """Contract for stream callback function.

    Called for each chunk received from streaming LLM.
    """

    def __call__(self, chunk: str) -> None:
        """Process a stream chunk.

        Args:
            chunk: The text content of the chunk
        """
        ...
