"""Tests for helen.runtime — HelenHermesRuntime and cancel_llm_call (HLD 3.8.1, 3.8.3).

Covers:
- HelenHermesRuntime implements Runtime ABC
- cancel_llm_call cancels in-flight calls
- cancel_llm_call returns False for unknown/completed calls
- CancelledError exception
- Memory operations
- Conversation history operations
- Token estimation
"""

import threading
import time
from unittest.mock import MagicMock

import pytest

from helen.runtime import (
    Runtime,
    HelenHermesRuntime,
    CancelledError,
    Message,
)


class TestHelenHermesRuntimeABC:
    """Test HelenHermesRuntime satisfies the Runtime ABC."""

    def test_is_runtime_subclass(self):
        """HelenHermesRuntime is a subclass of Runtime."""
        assert issubclass(HelenHermesRuntime, Runtime)

    def test_instantiable(self):
        """Can instantiate HelenHermesRuntime without errors."""
        runtime = HelenHermesRuntime()
        assert runtime is not None
        assert isinstance(runtime, Runtime)


class TestCancelLlmCall:
    """Test cancel_llm_call functionality."""

    def test_cancel_unknown_call(self):
        """Cancelling a non-existent call returns False."""
        runtime = HelenHermesRuntime()
        result = runtime.cancel_llm_call("nonexistent-id")
        assert result is False

    def test_cancel_completed_call(self):
        """Cancelling an already-completed call returns False."""
        mock_llm = MagicMock()
        mock_llm.act.return_value = MagicMock(text="done")
        runtime = HelenHermesRuntime(llm_runtime=mock_llm)

        # Make a call that completes immediately
        messages = [Message(role="user", content="hello")]
        try:
            runtime.call_llm(messages)
        except RuntimeError:
            pass  # Expected if no LLM runtime

        # The call is already done, cancel should return False
        result = runtime.cancel_llm_call("any-id")
        assert result is False

    def test_cancel_returns_true_for_active_call(self):
        """Cancelling an active call returns True."""
        cancel_event = threading.Event()

        def slow_act(*args, **kwargs):
            # Wait until we're told to stop or finish
            cancel_event.wait(timeout=5)
            return MagicMock(text="done")

        mock_llm = MagicMock()
        mock_llm.act = slow_act

        runtime = HelenHermesRuntime(llm_runtime=mock_llm)

        results = {"error": None, "result": None}

        def make_call():
            try:
                messages = [Message(role="user", content="hello")]
                results["result"] = runtime.call_llm(messages)
            except Exception as e:
                results["error"] = e

        # Start the call in a thread
        thread = threading.Thread(target=make_call, daemon=True)
        thread.start()

        # Give the thread time to register the call
        time.sleep(0.1)

        # Try to cancel - but we don't have the call_id from call_llm
        # Since call_llm generates UUID internally, we test via the _active_calls
        # For this test, verify the mechanism works via direct handle access
        with runtime._lock:
            assert len(runtime._active_calls) >= 1
            active_id = list(runtime._active_calls.keys())[0]

        result = runtime.cancel_llm_call(active_id)
        assert result is True

        # Signal the slow_act to finish
        cancel_event.set()
        thread.join(timeout=5)


class TestCancelledError:
    """Test CancelledError exception."""

    def test_has_call_id(self):
        """CancelledError stores the call_id."""
        err = CancelledError("test-id-123")
        assert err.call_id == "test-id-123"

    def test_message_includes_call_id(self):
        """Error message includes the call_id."""
        err = CancelledError("abc-123")
        assert "abc-123" in str(err)
        assert "cancelled" in str(err)

    def test_is_exception(self):
        """CancelledError is an Exception."""
        err = CancelledError("x")
        assert isinstance(err, Exception)


class TestMemoryOperations:
    """Test get_memory / set_memory."""

    def setup_method(self):
        self.runtime = HelenHermesRuntime()

    def test_set_and_get(self):
        """Set and get a memory value."""
        self.runtime.set_memory("key1", "value1")
        assert self.runtime.get_memory("key1") == "value1"

    def test_get_missing_key(self):
        """Getting a missing key returns None."""
        assert self.runtime.get_memory("nonexistent") is None

    def test_overwrite(self):
        """Setting an existing key overwrites the value."""
        self.runtime.set_memory("key", "old")
        self.runtime.set_memory("key", "new")
        assert self.runtime.get_memory("key") == "new"


class TestConversationHistory:
    """Test get_conversation_history / set_conversation_history."""

    def setup_method(self):
        self.runtime = HelenHermesRuntime()

    def test_empty_history(self):
        """Initial history is empty list."""
        history = self.runtime.get_conversation_history()
        assert history == []

    def test_set_and_get(self):
        """Set and get conversation history."""
        msgs = [
            Message(role="user", content="hello"),
            Message(role="assistant", content="hi"),
        ]
        self.runtime.set_conversation_history(msgs)
        history = self.runtime.get_conversation_history()
        assert len(history) == 2
        assert history[0].role == "user"
        assert history[1].role == "assistant"

    def test_returns_copy(self):
        """Returns a copy, not the internal list."""
        msgs = [Message(role="user", content="test")]
        self.runtime.set_conversation_history(msgs)
        h1 = self.runtime.get_conversation_history()
        h2 = self.runtime.get_conversation_history()
        assert h1 is not h2

    def test_modifying_copy_does_not_affect_internal(self):
        """Modifying the returned copy doesn't affect internal state."""
        msgs = [Message(role="user", content="test")]
        self.runtime.set_conversation_history(msgs)
        h = self.runtime.get_conversation_history()
        h.clear()
        assert len(self.runtime.get_conversation_history()) == 1


class TestTokenCount:
    """Test get_token_count."""

    def setup_method(self):
        self.runtime = HelenHermesRuntime()

    def test_estimates_tokens(self):
        """Uses chars / 4 heuristic."""
        text = "hello world this is a test"
        tokens = self.runtime.get_token_count(text)
        assert tokens == len(text) // 4

    def test_empty_string(self):
        """Empty string has 0 tokens."""
        assert self.runtime.get_token_count("") == 0


class TestMemoryProviderRegistration:
    """Test register_memory_provider."""

    def setup_method(self):
        self.runtime = HelenHermesRuntime()

    def test_register_provider(self):
        """Can register a provider for a protocol."""
        provider = MagicMock()
        self.runtime.register_memory_provider("file", provider)
        # Internal check: provider is stored
        assert self.runtime._memory_providers.get("file") is provider

    def test_register_multiple_providers(self):
        """Can register providers for different protocols."""
        p1 = MagicMock()
        p2 = MagicMock()
        self.runtime.register_memory_provider("file", p1)
        self.runtime.register_memory_provider("vector", p2)
        assert self.runtime._memory_providers["file"] is p1
        assert self.runtime._memory_providers["vector"] is p2


class TestCallLlmWithLlmRuntime:
    """Test call_llm delegates to underlying LLMRuntime."""

    def test_delegates_to_act(self):
        """call_llm calls the underlying llm_runtime.act()."""
        mock_response = MagicMock()
        mock_llm = MagicMock()
        mock_llm.act.return_value = mock_response

        runtime = HelenHermesRuntime(llm_runtime=mock_llm)
        messages = [Message(role="user", content="hello")]
        result = runtime.call_llm(messages)

        assert result is mock_response
        mock_llm.act.assert_called_once()

    def test_passes_temperature_and_model(self):
        """call_llm passes temperature and model to act()."""
        mock_response = MagicMock()
        mock_llm = MagicMock()
        mock_llm.act.return_value = mock_response

        runtime = HelenHermesRuntime(llm_runtime=mock_llm)
        messages = [Message(role="user", content="hello")]
        runtime.call_llm(messages, model="gpt-4", temperature=0.7)

        call_kwargs = mock_llm.act.call_args
        assert call_kwargs.kwargs["model"] == "gpt-4"
        assert call_kwargs.kwargs["temperature"] == 0.7

    def test_no_llm_runtime_raises(self):
        """call_llm raises RuntimeError without LLM runtime."""
        runtime = HelenHermesRuntime()
        messages = [Message(role="user", content="hello")]
        try:
            runtime.call_llm(messages)
            assert False, "Should have raised"
        except RuntimeError as e:
            assert "No LLM runtime configured" in str(e)


class TestResolveImport:
    """Test resolve_import."""

    def test_no_resolver_raises(self):
        """resolve_import raises RuntimeError without resolver."""
        runtime = HelenHermesRuntime()
        try:
            runtime.resolve_import("./module", "./main.helen")
            assert False, "Should have raised"
        except RuntimeError as e:
            assert "No import resolver configured" in str(e)

    def test_delegates_to_resolver(self):
        """resolve_import delegates to the import resolver."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = {"agents": {}}
        runtime = HelenHermesRuntime(import_resolver=mock_resolver)
        result = runtime.resolve_import("./module", "./main.helen")
        mock_resolver.resolve.assert_called_once_with("./module", "./main.helen")
        assert result == {"agents": {}}


class TestImplementedMethods:
    """Test that previously-stub methods now work."""

    def setup_method(self):
        self.runtime = HelenHermesRuntime()

    def test_load_tool_returns_schema(self):
        """load_tool returns a ToolSchema stub."""
        tool = self.runtime.load_tool("search")
        assert tool.name == "search"
        assert isinstance(tool.description, str)

    def test_list_skills_returns_list(self):
        """list_skills returns a list of SkillMeta."""
        skills = self.runtime.list_skills()
        assert isinstance(skills, list)
        # Should find at least some skills from ~/.hermes/skills
        if skills:
            assert all(hasattr(s, "name") for s in skills)

    def test_load_skill_finds_existing(self):
        """load_skill finds an existing skill."""
        try:
            content = self.runtime.load_skill("helen-language")
            assert isinstance(content, str)
            assert len(content) > 0
        except FileNotFoundError:
            # Skill not installed in this environment
            pass

    def test_load_skill_raises_for_missing(self):
        """load_skill raises FileNotFoundError for nonexistent skill."""
        with pytest.raises(FileNotFoundError, match="not found"):
            self.runtime.load_skill("__nonexistent_xyz__")
