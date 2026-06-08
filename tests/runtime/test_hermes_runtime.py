"""Tests for HelenHermesRuntime skill and tool loading (HLD §3.8.3).

Tests cover:
- list_skills: scanning skill directories, parsing frontmatter
- load_skill: loading SKILL.md content
- load_tool: returning ToolSchema stubs
- Memory provider integration
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from helen.runtime import (
    CancelledError,
    HelenHermesRuntime,
    Message,
    SkillMeta,
    ToolSchema,
)
from helen.runtime.memory import FileMemoryProvider, InMemoryProvider


class TestHelenHermesRuntimeSkills:
    """Test skill listing and loading."""

    def test_list_skills_returns_list(self) -> None:
        runtime = HelenHermesRuntime()
        skills = runtime.list_skills()
        assert isinstance(skills, list)
        # Should find at least some skills from ~/.hermes/skills
        assert len(skills) > 0

    def test_list_skills_returns_skill_meta(self) -> None:
        runtime = HelenHermesRuntime()
        skills = runtime.list_skills()
        for skill in skills:
            assert isinstance(skill, SkillMeta)
            assert isinstance(skill.name, str)
            assert isinstance(skill.description, str)
            assert len(skill.name) > 0

    def test_load_existing_skill(self) -> None:
        runtime = HelenHermesRuntime()
        skills = runtime.list_skills()
        if not skills:
            pytest.skip("No skills available for testing")

        # Try to load the first skill
        content = runtime.load_skill(skills[0].name)
        assert isinstance(content, str)
        assert len(content) > 0
        # Should contain YAML frontmatter
        assert content.startswith("---")

    def test_load_nonexistent_skill_raises(self) -> None:
        runtime = HelenHermesRuntime()
        with pytest.raises(FileNotFoundError):
            runtime.load_skill("__nonexistent_skill_xyz__")

    def test_load_hellen_language_skill(self) -> None:
        """Test loading a known skill that should exist."""
        runtime = HelenHermesRuntime()
        try:
            content = runtime.load_skill("helen-language")
            assert isinstance(content, str)
            assert len(content) > 0
        except FileNotFoundError:
            pytest.skip("helen-language skill not installed")


class TestHelenHermesRuntimeTools:
    """Test tool loading."""

    def test_load_tool_returns_tool_schema(self) -> None:
        runtime = HelenHermesRuntime()
        tool = runtime.load_tool("search")
        assert isinstance(tool, ToolSchema)
        assert tool.name == "search"

    def test_load_tool_has_description(self) -> None:
        runtime = HelenHermesRuntime()
        tool = runtime.load_tool("calculator")
        assert isinstance(tool.description, str)
        assert len(tool.description) > 0


class TestHelenHermesRuntimeMemory:
    """Test memory operations."""

    def setup_method(self) -> None:
        self.runtime = HelenHermesRuntime()

    def test_get_memory_returns_none_initially(self) -> None:
        assert self.runtime.get_memory("nonexistent") is None

    def test_set_and_get_memory(self) -> None:
        self.runtime.set_memory("name", "Alice")
        assert self.runtime.get_memory("name") == "Alice"

    def test_overwrite_memory(self) -> None:
        self.runtime.set_memory("name", "Alice")
        self.runtime.set_memory("name", "Bob")
        assert self.runtime.get_memory("name") == "Bob"

    def test_register_memory_provider(self) -> None:
        provider = InMemoryProvider()
        self.runtime.register_memory_provider("test", provider)
        assert "test" in self.runtime._memory_providers


class TestHelenHermesRuntimeHistory:
    """Test conversation history management."""

    def setup_method(self) -> None:
        self.runtime = HelenHermesRuntime()

    def test_history_empty_initially(self) -> None:
        history = self.runtime.get_conversation_history()
        assert history == []

    def test_set_and_get_history(self) -> None:
        messages = [
            Message(role="system", content="You are helpful"),
            Message(role="user", content="Hello"),
        ]
        self.runtime.set_conversation_history(messages)
        history = self.runtime.get_conversation_history()
        assert len(history) == 2
        assert history[0].role == "system"
        assert history[1].content == "Hello"

    def test_history_is_copy(self) -> None:
        """get_conversation_history should return a copy."""
        self.runtime.set_conversation_history([
            Message(role="user", content="test"),
        ])
        history = self.runtime.get_conversation_history()
        history.append(Message(role="user", content="extra"))
        # Original should not be modified
        assert len(self.runtime.get_conversation_history()) == 1


class TestHelenHermesRuntimeTokenCount:
    """Test token counting."""

    def test_token_count_approximation(self) -> None:
        runtime = HelenHermesRuntime()
        count = runtime.get_token_count("Hello world")
        assert isinstance(count, int)
        assert count > 0

    def test_token_count_scales_with_text(self) -> None:
        runtime = HelenHermesRuntime()
        short = runtime.get_token_count("hi")
        long = runtime.get_token_count("hello world " * 100)
        assert long > short


class TestHelenHermesRuntimeCancellation:
    """Test LLM call cancellation."""

    def test_cancel_nonexistent_call_returns_false(self) -> None:
        runtime = HelenHermesRuntime()
        assert runtime.cancel_llm_call("fake-id") is False

    def test_cancelled_error_has_call_id(self) -> None:
        err = CancelledError("test-123")
        assert err.call_id == "test-123"
        assert "test-123" in str(err)

    def test_cancelled_error_message(self) -> None:
        err = CancelledError("abc")
        assert "abc" in str(err)
        assert "cancelled" in str(err).lower()


class TestHelenHermesRuntimeNoLLM:
    """Test behavior when no LLM runtime is configured."""

    def test_call_llm_without_runtime_raises(self) -> None:
        runtime = HelenHermesRuntime()
        with pytest.raises(RuntimeError, match="No LLM runtime configured"):
            runtime.call_llm([Message(role="user", content="test")])
