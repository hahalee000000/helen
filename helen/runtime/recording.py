"""LLM interaction recording and replay for deterministic debugging.

v1.40: Provides infrastructure to record LLM interactions (requests and responses)
to cassette files, and replay them for deterministic debugging.

Key Components:
- RecordingHook: Protocol for recording LLM interactions
- CassetteWriter: Writes recorded interactions to JSONL cassette files
- ReplayLLMRuntime: LLM runtime that replays from cassette files
- RecordingLLMRuntimeWrapper: Wraps existing runtime to record interactions

Usage:
    # Recording
    from helen.runtime.recording import CassetteWriter, RecordingLLMRuntimeWrapper

    cassette = CassetteWriter("session.jsonl")
    runtime = RecordingLLMRuntimeWrapper(original_runtime, cassette)

    # Use runtime normally - all interactions are recorded
    response = runtime.act("prompt", ...)

    # Replay
    from helen.runtime.recording import ReplayLLMRuntime

    replay_runtime = ReplayLLMRuntime("session.jsonl")
    response = replay_runtime.act("prompt", ...)  # Returns recorded response
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from helen.runtime.llm_runtime import LLMRuntime, LLMResponse


# ---------------------------------------------------------------------------
# Recording Hook Protocol
# ---------------------------------------------------------------------------

class RecordingHook(Protocol):
    """Protocol for recording LLM interactions.

    Implementations can write to files, databases, or in-memory structures.
    """

    def on_request(
        self,
        messages: list[dict],
        payload: dict,
        metadata: dict,
    ) -> None:
        """Called before LLM request is sent.

        Args:
            messages: Full messages array (system + history + user)
            payload: HTTP request payload
            metadata: Additional metadata (model, temperature, etc.)
        """
        ...

    def on_response(
        self,
        response_message: dict,
        usage: dict,
        duration_ms: float,
    ) -> None:
        """Called after LLM response is received.

        Args:
            response_message: Response message dict (content, tool_calls, etc.)
            usage: Token usage dict (prompt_tokens, completion_tokens)
            duration_ms: Request duration in milliseconds
        """
        ...

    def on_tool(self, tool_call: dict, result: Any) -> None:
        """Called after a tool is executed.

        Args:
            tool_call: Tool call dict (name, arguments)
            result: Tool execution result
        """
        ...

    def on_turn_complete(
        self,
        full_messages: list[dict],
        final_response: dict,
    ) -> None:
        """Called when a complete LLM turn finishes.

        Args:
            full_messages: All messages in this turn (including tool calls)
            final_response: Final response message
        """
        ...


# ---------------------------------------------------------------------------
# Cassette Writer
# ---------------------------------------------------------------------------

@dataclass
class CassetteEntry:
    """Single LLM interaction recorded in a cassette."""

    seq: int                           # Sequence number (for ordering)
    timestamp: float                   # Unix timestamp
    agent_name: str | None             # Agent that made the call (if any)
    model: str                         # Model used
    request: dict                      # Full request payload
    response: dict                     # Full response
    usage: dict                        # Token usage
    duration_ms: float                 # Request duration
    tool_calls: list[dict] = field(default_factory=list)  # Tool calls made
    metadata: dict = field(default_factory=dict)          # Additional metadata

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "type": "llm_call",
            "seq": self.seq,
            "timestamp": self.timestamp,
            "agent_name": self.agent_name,
            "model": self.model,
            "request": self.request,
            "response": self.response,
            "usage": self.usage,
            "duration_ms": self.duration_ms,
            "tool_calls": self.tool_calls,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> CassetteEntry:
        """Reconstruct from dict."""
        return cls(
            seq=data["seq"],
            timestamp=data["timestamp"],
            agent_name=data.get("agent_name"),
            model=data["model"],
            request=data["request"],
            response=data["response"],
            usage=data.get("usage", {}),
            duration_ms=data.get("duration_ms", 0.0),
            tool_calls=data.get("tool_calls", []),
            metadata=data.get("metadata", {}),
        )


class CassetteWriter:
    """Writes LLM interactions to a JSONL cassette file.

    Each line in the file is a complete LLM interaction (request + response).
    Format is human-readable and can be inspected/edited manually.
    """

    def __init__(self, path: Path | str):
        """Initialize cassette writer.

        Args:
            path: Path to cassette file. Parent directories will be created.
        """
        self.path = Path(path) if isinstance(path, str) else path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = None
        self._seq = 0

    def __enter__(self):
        """Context manager entry."""
        self._file = open(self.path, "a", encoding="utf-8")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._file:
            self._file.close()
            self._file = None

    def write_entry(
        self,
        messages: list[dict],
        payload: dict,
        response: dict,
        usage: dict,
        duration_ms: float,
        agent_name: str | None = None,
        model: str = "",
        tool_calls: list[dict] | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Write a single LLM interaction to the cassette.

        Args:
            messages: Full messages array
            payload: HTTP request payload
            response: Response message dict
            usage: Token usage dict
            duration_ms: Request duration
            agent_name: Agent that made the call (if any)
            model: Model used
            tool_calls: Tool calls made during this interaction
            metadata: Additional metadata
        """
        if self._file is None:
            self._file = open(self.path, "a", encoding="utf-8")

        entry = CassetteEntry(
            seq=self._seq,
            timestamp=time.time(),
            agent_name=agent_name,
            model=model,
            request=payload,
            response=response,
            usage=usage,
            duration_ms=duration_ms,
            tool_calls=tool_calls or [],
            metadata=metadata or {},
        )

        line = json.dumps(entry.to_dict(), ensure_ascii=False)
        self._file.write(line + "\n")
        self._file.flush()
        self._seq += 1

    def close(self) -> None:
        """Close the cassette file."""
        if self._file:
            self._file.close()
            self._file = None


class CassetteReader:
    """Reads LLM interactions from a cassette file.

    Supports sequential reading and lookup by sequence number.
    """

    def __init__(self, path: Path | str):
        """Initialize cassette reader.

        Args:
            path: Path to cassette file.
        """
        self.path = Path(path) if isinstance(path, str) else path
        self._entries: list[CassetteEntry] = []
        self._load()

    def _load(self) -> None:
        """Load all entries from the cassette file."""
        if not self.path.exists():
            return

        with open(self.path, encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entry = CassetteEntry.from_dict(data)
                    self._entries.append(entry)
                except (json.JSONDecodeError, KeyError) as e:
                    # Skip corrupted lines
                    import logging
                    logging.warning(
                        "CassetteReader: corrupted line %d in %s: %s",
                        line_num, self.path, e,
                    )

    def get_entry(self, seq: int) -> CassetteEntry | None:
        """Get entry by sequence number.

        Args:
            seq: Sequence number.

        Returns:
            CassetteEntry if found, None otherwise.
        """
        for entry in self._entries:
            if entry.seq == seq:
                return entry
        return None

    def get_next_entry(self, current_seq: int = -1) -> CassetteEntry | None:
        """Get the next entry after current_seq.

        Args:
            current_seq: Current sequence number (-1 for first entry).

        Returns:
            Next CassetteEntry if available, None otherwise.
        """
        for entry in self._entries:
            if entry.seq > current_seq:
                return entry
        return None

    def __len__(self) -> int:
        """Return number of entries in cassette."""
        return len(self._entries)

    def __iter__(self):
        """Iterate over all entries."""
        return iter(self._entries)


# ---------------------------------------------------------------------------
# Replay LLM Runtime
# ---------------------------------------------------------------------------

class ReplayLLMRuntime(LLMRuntime):
    """LLM runtime that replays interactions from a cassette file.

    For each act() call, returns the corresponding recorded response.
    Useful for deterministic debugging and testing.
    """

    def __init__(self, cassette_path: Path | str):
        """Initialize replay runtime.

        Args:
            cassette_path: Path to cassette file to replay from.
        """
        self.cassette = CassetteReader(cassette_path)
        self._current_seq = -1

    def act(
        self,
        prompt: str,
        history: list | None = None,
        system_prompt: str | None = None,
        tools: list | None = None,
        dispatch_fn=None,
        **kwargs,
    ) -> LLMResponse:
        """Replay a recorded LLM interaction.

        Args:
            prompt: User prompt (ignored, uses recorded response)
            history: Conversation history (ignored)
            system_prompt: System prompt (ignored)
            tools: Available tools (ignored)
            dispatch_fn: Tool dispatch function (ignored)
            **kwargs: Additional arguments (ignored)

        Returns:
            LLMResponse from the cassette.

        Raises:
            RuntimeError: If no more recorded interactions available.
        """
        entry = self.cassette.get_next_entry(self._current_seq)
        if entry is None:
            raise RuntimeError(
                f"No more recorded interactions in cassette. "
                f"Used {self._current_seq + 1} of {len(self.cassette)} entries."
            )

        self._current_seq = entry.seq

        # Convert recorded response to LLMResponse
        response_data = entry.response
        text = response_data.get("content", "")
        tool_calls = response_data.get("tool_calls", [])

        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
        )

    def route(self, prompt: str, options: list[str]) -> str:
        """Replay a recorded routing decision.

        Note: Routing is not currently recorded separately, so this
        raises NotImplementedError. Future versions may record routing.
        """
        raise NotImplementedError(
            "ReplayLLMRuntime does not support route(). "
            "Routing decisions are not recorded in cassettes."
        )


# ---------------------------------------------------------------------------
# Recording LLM Runtime Wrapper
# ---------------------------------------------------------------------------

class RecordingLLMRuntimeWrapper(LLMRuntime):
    """Wraps an existing LLM runtime to record all interactions.

    All calls are forwarded to the wrapped runtime, and interactions
    are recorded to a cassette file.
    """

    def __init__(
        self,
        wrapped: LLMRuntime,
        cassette: CassetteWriter,
        agent_name: str | None = None,
    ):
        """Initialize recording wrapper.

        Args:
            wrapped: Underlying LLM runtime to wrap.
            cassette: CassetteWriter to record interactions.
            agent_name: Name of agent using this runtime (for metadata).
        """
        self.wrapped = wrapped
        self.cassette = cassette
        self.agent_name = agent_name

    def act(
        self,
        prompt: str,
        history: list | None = None,
        system_prompt: str | None = None,
        tools: list | None = None,
        dispatch_fn=None,
        **kwargs,
    ) -> LLMResponse:
        """Forward to wrapped runtime and record the interaction.

        Args:
            prompt: User prompt
            history: Conversation history
            system_prompt: System prompt
            tools: Available tools
            dispatch_fn: Tool dispatch function
            **kwargs: Additional arguments

        Returns:
            LLMResponse from wrapped runtime.
        """
        start_time = time.time()

        # Forward to wrapped runtime
        response = self.wrapped.act(
            prompt=prompt,
            history=history,
            system_prompt=system_prompt,
            tools=tools,
            dispatch_fn=dispatch_fn,
            **kwargs,
        )

        duration_ms = (time.time() - start_time) * 1000

        # Record the interaction
        # Note: We don't have access to the full messages array here,
        # so we record just the prompt and response.
        # The actual messages array is constructed inside the wrapped runtime.
        request_payload = {
            "prompt": prompt,
            "system_prompt": system_prompt,
            "tools": [t.__dict__ if hasattr(t, "__dict__") else str(t) for t in (tools or [])],
        }

        response_dict = {
            "content": response.content,
            "tool_calls": response.tool_calls,
        }

        self.cassette.write_entry(
            messages=[],  # Not available here
            payload=request_payload,
            response=response_dict,
            usage=response.usage if hasattr(response, "usage") else {},
            duration_ms=duration_ms,
            agent_name=self.agent_name,
            model=kwargs.get("model", "unknown"),
            metadata=kwargs,
        )

        return response

    def route(self, prompt: str, options: list[str]) -> str:
        """Forward routing to wrapped runtime.

        Note: Routing is not recorded in cassettes.
        """
        return self.wrapped.route(prompt, options)
