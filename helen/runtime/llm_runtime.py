"""LLM runtime interface and mock implementation for the Helen language.

Provides the abstract LLMRuntime interface (route/choose/act) and a
MockLLMRuntime for deterministic testing of llm if/choose/act statements.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterator


# ---------------------------------------------------------------------------
# LLM Response
# ---------------------------------------------------------------------------


@dataclass
class LLMResponse:
    """Response from an LLM call.

    Attributes:
        text: The text content returned by the LLM.
        tool_calls: Optional tool call requests (function calling).
        model: The model that generated this response.
    """

    text: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    model: str | None = None


# ---------------------------------------------------------------------------
# LLM Runtime Interface (HLD 3.6.5, 3.8.1)
# ---------------------------------------------------------------------------


class LLMRuntime(ABC):
    """Abstract interface for LLM operations in Helen.

    Two core methods map to Helen's llm statements:
    - route()  → llm if
    - act()    → llm act

    Phase 1b: Also provides async versions for concurrent execution.
    """

    @abstractmethod
    def route(self, description: str, branches: list[str], context: str | None = None) -> str | None:
        """Route input to one of the given branches via LLM (sync version)."""
        ...

    @abstractmethod
    def act(self, prompt: str, tools: list[dict[str, Any]] | None = None,
            model: str | None = None, temperature: float = 1.0,
            max_turns: int = 1, history: list[dict[str, Any]] | None = None,
            system_prompt: str | None = None,
            dispatch_fn: Any = None) -> LLMResponse:
        """Execute an autonomous LLM action (sync version).

        Args:
            dispatch_fn: Optional custom tool dispatch function.
                Signature: (name: str, args: dict) -> str
                If not provided, uses the default dispatch_tool from helen.runtime.tools.
        """
        ...

    # Phase 1b: Async versions for concurrent execution
    async def route_async(self, description: str, branches: list[str],
                          context: str | None = None) -> str | None:
        """Async version of route() for concurrent execution.

        Default implementation calls sync version. Override for true async.
        """
        return self.route(description, branches, context)

    async def act_async(self, prompt: str, tools: list[dict[str, Any]] | None = None,
                        model: str | None = None, temperature: float = 1.0,
                        max_turns: int = 1, history: list[dict[str, Any]] | None = None,
                        system_prompt: str | None = None,
                        dispatch_fn: Any = None) -> LLMResponse:
        """Async version of act() for concurrent execution.

        Default implementation calls sync version. Override for true async.
        """
        return self.act(prompt, tools, model, temperature, max_turns, history,
                        system_prompt, dispatch_fn)

    def act_stream(self, prompt: str, model: str | None = None,
                   temperature: float = 1.0, system_prompt: str | None = None,
                   tools: list[dict[str, Any]] | None = None,
                   max_turns: int = 5,
                   history: list[dict[str, Any]] | None = None,
                   dispatch_fn: Any = None) -> Iterator[dict[str, Any]]:
        """Stream LLM response with tool-calling support.

        Default implementation calls act() and yields the full response as a single content event.
        Override for true streaming support.

        Yields event dicts:
            {"type": "content", "content": "..."}     — text chunk
            {"type": "tool_call", "name": "...", "args": {...}}  — tool invocation
            {"type": "tool_result", "name": "...", "result": "..."}  — tool result
            {"type": "error", "message": "..."}       — error
        """
        response = self.act(prompt, tools=tools, model=model, temperature=temperature,
                            max_turns=max_turns, system_prompt=system_prompt,
                            dispatch_fn=dispatch_fn)
        if response and response.text:
            yield {"type": "content", "content": response.text}


# ---------------------------------------------------------------------------
# Mock LLM Runtime (for deterministic testing)
# ---------------------------------------------------------------------------


@dataclass
class MockLLMRuntime(LLMRuntime):
    """Mock LLM runtime with preset return values.

    Used for deterministic testing of llm if/choose/act without
    calling a real LLM API.

    Attributes:
        route_return: Preset branch name for route() calls.
        act_return: Preset text for act() calls.
        route_fail: If set, route() raises this exception instead.
        act_fail: If set, act() raises this exception instead.
    """

    route_return: str | None = None
    act_return: LLMResponse | str | None = None
    route_fail: Exception | None = None
    act_fail: Exception | None = None
    route_history: list[dict[str, Any]] = field(default_factory=list)
    act_history: list[dict[str, Any]] = field(default_factory=list)

    def route(self, description: str, branches: list[str], context: str | None = None) -> str | None:
        """Return the preset route_return value."""
        self.route_history.append({
            "description": description,
            "branches": branches,
            "context": context,
        })
        if self.route_fail is not None:
            raise self.route_fail
        return self.route_return

    def act(self, prompt: str, tools: list[dict[str, Any]] | None = None,
            model: str | None = None, temperature: float = 1.0,
            max_turns: int = 1, history: list[dict[str, Any]] | None = None,
            system_prompt: str | None = None,
            dispatch_fn: Any = None) -> LLMResponse:
        """Return the preset act_return value.

        Args:
            dispatch_fn: Accepted for interface compatibility with HttpLLMRuntime,
                but ignored (mock does not dispatch tool calls).
        """
        self.act_history.append({
            "prompt": prompt,
            "tools": tools,
            "model": model,
            "temperature": temperature,
            "max_turns": max_turns,
            "history": history,
            "system_prompt": system_prompt,
            "dispatch_fn": dispatch_fn,
        })
        if self.act_fail is not None:
            raise self.act_fail
        if isinstance(self.act_return, str):
            return LLMResponse(text=self.act_return)
        if self.act_return is None:
            return LLMResponse(text="")
        return self.act_return

    def reset(self) -> None:
        """Clear history and reset to defaults."""
        self.route_history.clear()
        self.act_history.clear()
