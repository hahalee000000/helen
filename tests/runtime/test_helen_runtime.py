"""Tests for helen.runtime — HelenRuntime (HLD 3.8.1, 3.8.3).

Covers:
- HelenRuntime implements Runtime ABC
- cancel_llm_call cancels in-flight calls
- CancelledError exception
- Skill listing and loading
- Tool loading
- Memory operations
- Conversation history operations
- Token estimation
- Memory provider registration
- call_llm delegation to LLMRuntime
- resolve_import delegation
"""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

import pytest

from helen.runtime import (
    Runtime,
    HelenRuntime,
    CancelledError,
    Message,
    SkillMeta,
    ToolSchema,
)
from helen.runtime.memory import InMemoryProvider


# ── ABC ──────────────────────────────────────────────────────────────────────


class TestHelenRuntimeABC:
    """Test HelenRuntime satisfies the Runtime ABC."""

    def test_is_runtime_subclass(self):
        """HelenRuntime is a subclass of Runtime."""
        assert issubclass(HelenRuntime, Runtime)

    def test_instantiable(self):
        """Can instantiate HelenRuntime without errors."""
        runtime = HelenRuntime()
        assert runtime is not None
        assert isinstance(runtime, Runtime)

    def test_backward_compat_alias(self):
        """Legacy HelenHermesRuntime alias still works."""
        from helen.runtime import HelenHermesRuntime
        assert HelenHermesRuntime is HelenRuntime


# ── cancel_llm_call ─────────────────────────────────────────────────────────


class TestCancelLlmCall:
    """Test cancel_llm_call functionality."""

    def test_cancel_unknown_call(self):
        """Cancelling a non-existent call returns False."""
        runtime = HelenRuntime()
        result = runtime.cancel_llm_call("nonexistent-id")
        assert result is False

    def test_cancel_completed_call(self):
        """Cancelling an already-completed call returns False."""
        mock_llm = MagicMock()
        mock_llm.act.return_value = MagicMock(text="done")
        runtime = HelenRuntime(llm_runtime=mock_llm)

        messages = [Message(role="user", content="hello")]
        runtime.call_llm(messages)

        # Call is already done, cancel should return False
        result = runtime.cancel_llm_call("any-id")
        assert result is False

    def test_cancel_returns_true_for_active_call(self):
        """Cancelling an active call returns True."""
        cancel_event = threading.Event()

        def slow_act(*args, **kwargs):
            cancel_event.wait(timeout=5)
            return MagicMock(text="done")

        mock_llm = MagicMock()
        mock_llm.act = slow_act
        runtime = HelenRuntime(llm_runtime=mock_llm)

        results = {"error": None, "result": None}

        def make_call():
            try:
                messages = [Message(role="user", content="hello")]
                results["result"] = runtime.call_llm(messages)
            except Exception as e:
                results["error"] = e

        thread = threading.Thread(target=make_call, daemon=True)
        thread.start()
        time.sleep(0.1)

        with runtime._lock:
            assert len(runtime._active_calls) >= 1
            active_id = list(runtime._active_calls.keys())[0]

        result = runtime.cancel_llm_call(active_id)
        assert result is True

        cancel_event.set()
        thread.join(timeout=5)


# ── CancelledError ───────────────────────────────────────────────────────────


class TestCancelledError:
    """Test CancelledError exception."""

    def test_has_call_id(self):
        err = CancelledError("test-id-123")
        assert err.call_id == "test-id-123"

    def test_message_includes_call_id(self):
        err = CancelledError("abc-123")
        assert "abc-123" in str(err)
        assert "cancelled" in str(err)

    def test_is_exception(self):
        err = CancelledError("x")
        assert isinstance(err, Exception)


# ── Skills ───────────────────────────────────────────────────────────────────


class TestSkills:
    """Test skill listing and loading."""

    def test_list_skills_returns_list(self) -> None:
        runtime = HelenRuntime()
        skills = runtime.list_skills()
        assert isinstance(skills, list)

    def test_list_skills_returns_skill_meta(self) -> None:
        runtime = HelenRuntime()
        skills = runtime.list_skills()
        for skill in skills:
            assert isinstance(skill, SkillMeta)
            assert isinstance(skill.name, str)
            assert isinstance(skill.description, str)
            assert len(skill.name) > 0

    def test_load_existing_skill(self) -> None:
        runtime = HelenRuntime()
        skills = runtime.list_skills()
        if not skills:
            pytest.skip("No skills available for testing")
        content = runtime.load_skill(skills[0].name)
        assert isinstance(content, str)
        assert len(content) > 0
        assert content.startswith("---")

    def test_load_nonexistent_skill_raises(self) -> None:
        runtime = HelenRuntime()
        with pytest.raises(FileNotFoundError):
            runtime.load_skill("__nonexistent_skill_xyz__")

    def test_load_helen_language_development_skill(self) -> None:
        runtime = HelenRuntime()
        try:
            content = runtime.load_skill("helen-language-development")
            assert isinstance(content, str)
            assert len(content) > 0
        except FileNotFoundError:
            pytest.skip("helen-language-development skill not installed")


# ── Tools ────────────────────────────────────────────────────────────────────


class TestTools:
    """Test tool loading."""

    def test_load_tool_returns_tool_schema(self) -> None:
        runtime = HelenRuntime()
        tool = runtime.load_tool("search")
        assert isinstance(tool, ToolSchema)
        assert tool.name == "search"

    def test_load_tool_has_description(self) -> None:
        runtime = HelenRuntime()
        tool = runtime.load_tool("calculator")
        assert isinstance(tool.description, str)
        assert len(tool.description) > 0


# ── Memory ───────────────────────────────────────────────────────────────────


class TestMemoryOperations:
    """Test get_memory / set_memory."""

    def setup_method(self):
        self.runtime = HelenRuntime()

    def test_get_returns_none_initially(self) -> None:
        assert self.runtime.get_memory("nonexistent") is None

    def test_set_and_get(self) -> None:
        self.runtime.set_memory("name", "Alice")
        assert self.runtime.get_memory("name") == "Alice"

    def test_overwrite(self) -> None:
        self.runtime.set_memory("name", "Alice")
        self.runtime.set_memory("name", "Bob")
        assert self.runtime.get_memory("name") == "Bob"


class TestMemoryProviderRegistration:
    """Test register_memory_provider."""

    def setup_method(self):
        self.runtime = HelenRuntime()

    def test_register_provider(self):
        provider = InMemoryProvider()
        self.runtime.register_memory_provider("test", provider)
        assert "test" in self.runtime._memory_providers

    def test_register_multiple_providers(self):
        p1 = MagicMock()
        p2 = MagicMock()
        self.runtime.register_memory_provider("file", p1)
        self.runtime.register_memory_provider("vector", p2)
        assert self.runtime._memory_providers["file"] is p1
        assert self.runtime._memory_providers["vector"] is p2


# ── Conversation History ─────────────────────────────────────────────────────


class TestConversationHistory:
    """Test get_conversation_history / set_conversation_history."""

    def setup_method(self):
        self.runtime = HelenRuntime()

    def test_empty_history(self) -> None:
        history = self.runtime.get_conversation_history()
        assert history == []

    def test_set_and_get(self) -> None:
        messages = [
            Message(role="system", content="You are helpful"),
            Message(role="user", content="Hello"),
        ]
        self.runtime.set_conversation_history(messages)
        history = self.runtime.get_conversation_history()
        assert len(history) == 2
        assert history[0].role == "system"
        assert history[1].content == "Hello"

    def test_returns_copy(self) -> None:
        """get_conversation_history should return a copy."""
        self.runtime.set_conversation_history([
            Message(role="user", content="test"),
        ])
        history = self.runtime.get_conversation_history()
        history.append(Message(role="user", content="extra"))
        # Original should not be modified
        assert len(self.runtime.get_conversation_history()) == 1


# ── Token Count ──────────────────────────────────────────────────────────────


class TestTokenCount:
    """Test get_token_count."""

    def setup_method(self):
        self.runtime = HelenRuntime()

    def test_token_count_approximation(self) -> None:
        count = self.runtime.get_token_count("Hello world")
        assert isinstance(count, int)
        assert count > 0

    def test_token_count_scales_with_text(self) -> None:
        short = self.runtime.get_token_count("hi")
        long = self.runtime.get_token_count("hello world " * 100)
        assert long > short


# ── call_llm ─────────────────────────────────────────────────────────────────


class TestCallLlmWithLlmRuntime:
    """Test call_llm delegates to underlying LLMRuntime."""

    def test_delegates_to_act(self):
        mock_response = MagicMock()
        mock_llm = MagicMock()
        mock_llm.act.return_value = mock_response

        runtime = HelenRuntime(llm_runtime=mock_llm)
        messages = [Message(role="user", content="hello")]
        result = runtime.call_llm(messages)

        assert result is mock_response
        mock_llm.act.assert_called_once()

    def test_passes_temperature_and_model(self):
        mock_response = MagicMock()
        mock_llm = MagicMock()
        mock_llm.act.return_value = mock_response

        runtime = HelenRuntime(llm_runtime=mock_llm)
        messages = [Message(role="user", content="hello")]
        runtime.call_llm(messages, model="gpt-4", temperature=0.7)

        call_kwargs = mock_llm.act.call_args
        assert call_kwargs.kwargs["model"] == "gpt-4"
        assert call_kwargs.kwargs["temperature"] == 0.7

    def test_no_llm_runtime_raises(self) -> None:
        runtime = HelenRuntime()
        with pytest.raises(RuntimeError, match="No LLM runtime configured"):
            runtime.call_llm([Message(role="user", content="test")])


# ── resolve_import ───────────────────────────────────────────────────────────


class TestResolveImport:
    """Test resolve_import."""

    def test_no_resolver_raises(self):
        runtime = HelenRuntime()
        with pytest.raises(RuntimeError, match="No import resolver configured"):
            runtime.resolve_import("./module", "./main.helen")

    def test_delegates_to_resolver(self):
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = {"agents": {}}
        runtime = HelenRuntime(import_resolver=mock_resolver)
        result = runtime.resolve_import("./module", "./main.helen")
        mock_resolver.resolve.assert_called_once_with("./module", "./main.helen")
        assert result == {"agents": {}}
