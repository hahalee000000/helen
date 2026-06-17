"""LLM runtime interface and mock implementation for the Helen language.

Provides the abstract LLMRuntime interface (route/choose/act) and a
MockLLMRuntime for deterministic testing of llm if/choose/act statements.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


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
    """

    @abstractmethod
    def route(self, description: str, branches: list[str], context: str | None = None) -> str | None:
        """LLM routing: classify input into one of the given branches.

        Args:
            description: The routing description (from llm if "desc").
            branches: List of available branch names.
            context: Optional context string (conversation summary).

        Returns:
            The selected branch name, or None if classification failed.
        """
        ...

    @abstractmethod
    def act(self, prompt: str, tools: list[dict[str, Any]] | None = None,
            model: str | None = None, temperature: float = 1.0,
            max_turns: int = 1, history: list[dict[str, Any]] | None = None,
            system_prompt: str | None = None) -> LLMResponse:
        """LLM autonomous action.

        Args:
            prompt: The prompt text (from llm act target ... "desc").
            tools: Optional tool schemas for function calling.
            model: Optional model override.
            temperature: Sampling temperature.
            max_turns: Maximum interaction turns.
            history: Optional conversation history.
            system_prompt: Optional system prompt (e.g. from agent's prompt field).

        Returns:
            An LLMResponse with text and/or tool calls.
        """
        ...


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
            system_prompt: str | None = None) -> LLMResponse:
        """Return the preset act_return value."""
        self.act_history.append({
            "prompt": prompt,
            "tools": tools,
            "model": model,
            "temperature": temperature,
            "max_turns": max_turns,
            "history": history,
            "system_prompt": system_prompt,
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
