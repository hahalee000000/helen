"""Runtime API interface and default Hermes implementation (HLD 3.8.1).

Runtime provides the abstraction layer between Hellen Core and external
services (LLM APIs, Memory, Skills, Tools). Core code never imports
Hermes directly — it only uses this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
import threading
import uuid


@dataclass
class Message:
    """A single message in a conversation (HLD 3.8.1)."""

    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_call_id: str | None = None


@dataclass
class ToolSchema:
    """Schema for a tool available to the LLM."""

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillMeta:
    """Lightweight skill metadata for Tier 1 Skill Index."""

    name: str
    description: str
    category: str = ""


class Runtime(ABC):
    """Hellen Runtime abstract interface (HLD 3.8.1).

    This interface defines all operations that Hellen Core needs from
    the runtime layer. The default implementation (HellenHermesRuntime)
    provides concrete adapters for the Hermes Agent infrastructure.
    """

    # --- Tool & Skill Management ---

    @abstractmethod
    def load_tool(self, name: str) -> Any:
        """Load a tool implementation by name."""
        ...

    @abstractmethod
    def list_skills(self) -> list[SkillMeta]:
        """Return lightweight Skill Index (Tier 1: name + description + category).

        Used by PromptBuilder to build <available_skills> section
        in System Prompt without loading full SKILL.md content.
        """
        ...

    @abstractmethod
    def load_skill(self, name: str) -> str:
        """Load a skill's full content (Tier 2: SKILL.md + linked files).

        Returns the complete SKILL.md text for injection into conversation
        history as a tool result.
        """
        ...

    # --- LLM Operations ---

    @abstractmethod
    def call_llm(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        temperature: float = 1.0,
        max_turns: int = 1,
    ) -> Any:
        """Call the LLM API with messages and optional tool schemas.

        Args:
            messages: Conversation messages (system + history + current).
            tools: Function calling schemas.
            model: Model override (uses agent's model if None).
            temperature: Sampling temperature.
            max_turns: Maximum interaction turns.

        Returns:
            LLM response object (text, tool_calls, model).
        """
        ...

    @abstractmethod
    def cancel_llm_call(self, call_id: str) -> bool:
        """Cancel an in-progress LLM call."""
        ...

    # --- Memory Operations ---

    @abstractmethod
    def get_memory(self, key: str) -> str | None:
        """Get a memory value by exact key."""
        ...

    @abstractmethod
    def set_memory(self, key: str, value: str) -> None:
        """Set a memory value by exact key."""
        ...

    # --- Import Resolution ---

    @abstractmethod
    def resolve_import(self, path: str, from_file: str) -> Any:
        """Resolve and load an import (code, text, or data).

        Args:
            path: Import path string.
            from_file: Path of the importing file (for relative resolution).

        Returns:
            Parsed content (AST for .hellen, str for text, dict/list for data).
        """
        ...

    # --- Token & History Management ---

    @abstractmethod
    def get_token_count(self, text: str) -> int:
        """Estimate the token count of text."""
        ...

    @abstractmethod
    def get_conversation_history(self) -> list[Message]:
        """Get the current conversation history."""
        ...

    @abstractmethod
    def set_conversation_history(self, history: list[Message]) -> None:
        """Set/replace the conversation history."""
        ...

    # --- Memory Provider Registration (HLD 3.8.2) ---

    @abstractmethod
    def register_memory_provider(self, protocol: str, provider: Any) -> None:
        """Register a custom MemoryProvider for a URI protocol.

        Args:
            protocol: URI scheme (e.g., "file", "vector", "markdown").
            provider: A MemoryProvider instance.
        """
        ...


# ---------------------------------------------------------------------------
# Concrete Implementation: HellenHermesRuntime (HLD 3.8.3)
# ---------------------------------------------------------------------------


class _CallHandle:
    """Tracks an in-flight LLM call for cancellation."""

    def __init__(self) -> None:
        self.cancelled = threading.Event()
        self.result: Any = None
        self.exception: Exception | None = None
        self.done = threading.Event()


class HellenHermesRuntime(Runtime):
    """Default Hermes-based implementation of the Hellen Runtime (HLD 3.8.3).

    Wraps an LLMRuntime (or similar provider) and adds:
    - Cancellable LLM calls via threading.Event
    - Memory key-value store
    - Import resolution delegation
    - Conversation history management
    """

    def __init__(
        self,
        llm_runtime: Any | None = None,
        import_resolver: Any | None = None,
    ) -> None:
        self._llm_runtime = llm_runtime
        self._import_resolver = import_resolver
        self._memory: dict[str, str] = {}
        self._conversation_history: list[Message] = []
        self._active_calls: dict[str, _CallHandle] = {}
        self._memory_providers: dict[str, Any] = {}
        self._lock = threading.Lock()

    # --- Tool & Skill Management ---

    def load_tool(self, name: str) -> Any:
        """Load a tool implementation by name."""
        raise NotImplementedError("Tool loading requires Hermes integration")

    def list_skills(self) -> list[SkillMeta]:
        """Return lightweight Skill Index."""
        raise NotImplementedError("Skill listing requires Hermes integration")

    def load_skill(self, name: str) -> str:
        """Load a skill's full content."""
        raise NotImplementedError("Skill loading requires Hermes integration")

    # --- LLM Operations ---

    def call_llm(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        temperature: float = 1.0,
        max_turns: int = 1,
    ) -> Any:
        """Call the LLM API with messages and optional tool schemas.

        Supports cancellation via cancel_llm_call().

        Args:
            messages: Conversation messages.
            tools: Function calling schemas.
            model: Model override.
            temperature: Sampling temperature.
            max_turns: Maximum interaction turns.

        Returns:
            LLM response object.

        Raises:
            CancelledError: If the call was cancelled.
        """
        call_id = str(uuid.uuid4())
        handle = _CallHandle()

        with self._lock:
            self._active_calls[call_id] = handle

        try:
            if self._llm_runtime is None:
                raise RuntimeError("No LLM runtime configured")

            # Build messages list for the LLM
            llm_messages = [
                {"role": m.role, "content": m.content, **({"tool_calls": m.tool_calls} if m.tool_calls else {})}
                for m in messages
            ]

            # Check cancellation before calling
            if handle.cancelled.is_set():
                raise CancelledError(call_id)

            # Call the underlying LLM runtime
            result = self._llm_runtime.act(
                prompt=llm_messages[-1]["content"] if llm_messages else "",
                tools=tools,
                model=model,
                temperature=temperature,
                max_turns=max_turns,
            )
            handle.result = result
            return result
        except CancelledError:
            raise
        except Exception as exc:
            handle.exception = exc
            raise
        finally:
            handle.done.set()
            with self._lock:
                self._active_calls.pop(call_id, None)

    def cancel_llm_call(self, call_id: str) -> bool:
        """Cancel an in-progress LLM call.

        Args:
            call_id: The UUID returned when the call was started.

        Returns:
            True if the call was found and cancelled, False if not found
            or already completed.
        """
        with self._lock:
            handle = self._active_calls.get(call_id)
        if handle is None:
            return False
        handle.cancelled.set()
        return True

    # --- Memory Operations ---

    def get_memory(self, key: str) -> str | None:
        """Get a memory value by exact key."""
        return self._memory.get(key)

    def set_memory(self, key: str, value: str) -> None:
        """Set a memory value by exact key."""
        self._memory[key] = value

    # --- Import Resolution ---

    def resolve_import(self, path: str, from_file: str) -> Any:
        """Resolve and load an import."""
        if self._import_resolver is None:
            raise RuntimeError("No import resolver configured")
        return self._import_resolver.resolve(path, from_file)

    # --- Token & History Management ---

    def get_token_count(self, text: str) -> int:
        """Estimate the token count of text."""
        return len(text) // 4

    def get_conversation_history(self) -> list[Message]:
        """Get the current conversation history."""
        return list(self._conversation_history)

    def set_conversation_history(self, history: list[Message]) -> None:
        """Set/replace the conversation history."""
        self._conversation_history = list(history)

    # --- Memory Provider Registration ---

    def register_memory_provider(self, protocol: str, provider: Any) -> None:
        """Register a custom MemoryProvider for a URI protocol."""
        self._memory_providers[protocol] = provider


class CancelledError(Exception):
    """Raised when an LLM call is cancelled."""

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id
        super().__init__(f"LLM call {call_id} was cancelled")
