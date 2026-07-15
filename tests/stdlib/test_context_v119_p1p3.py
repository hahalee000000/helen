"""Tests for v1.19 P1-P3: Complete context management API.

Covers:
- P1: working_memory_get/set/remove/clear, on_compression hook
- P2: insert_message, replace_message, runtime config (5 setters/getters),
      export_context, import_context, fork_context
- P3: search_context, context_slice
"""

import pytest
from helen.stdlib.context import (
    _working_memory_get,
    _working_memory_set,
    _working_memory_remove,
    _working_memory_clear,
    _set_compression_strategy,
    _set_context_window,
    _set_working_memory_enabled,
    _set_cache_aware,
    _get_context_config,
    _insert_message,
    _replace_message,
    _search_context,
    _context_slice,
    _export_context,
    _import_context,
    _fork_context,
    _on_compression,
    _on_context_overflow,
    _set_interpreter_context,
)
from helen.runtime.history import Message
from helen.interpreter.agent_context import AgentContextManager
from helen.runtime.working_memory import WorkingMemory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_msg(role="user", content="hello", uuid="", pinned=False,
              token_count=10):
    return Message(
        role=role, content=content, uuid=uuid, pinned=pinned,
        _token_count=token_count,
    )


def _setup_context(messages=None, max_tokens=1000, with_agent_ctx=False):
    """Inject context for tests."""
    if messages is None:
        messages = []
    history_manager = type("HM", (), {"MAX_TOKENS": max_tokens})()
    agent_ctx = None
    if with_agent_ctx:
        agent_ctx = AgentContextManager(
            working_memory_tokens=5000,
            compression_strategy="graduated",
            working_memory_enabled=True,
            cache_aware_enabled=True,
        )
    _set_interpreter_context(messages, history_manager, agent_ctx)
    return agent_ctx


def _teardown_context():
    _set_interpreter_context([], None, None)


# ---------------------------------------------------------------------------
# P1: Working Memory
# ---------------------------------------------------------------------------

class TestWorkingMemory:
    def test_get_returns_error_when_disabled(self):
        _setup_context()
        try:
            r = _working_memory_get()
            assert r["status"] == "error"
        finally:
            _teardown_context()

    def test_get_set_task(self):
        _setup_context(with_agent_ctx=True)
        try:
            r = _working_memory_set("task", "Build feature X")
            assert r["status"] == "ok"
            r = _working_memory_get("task")
            assert r["status"] == "ok"
            assert r["data"] == "Build feature X"
        finally:
            _teardown_context()

    def test_get_all_keys(self):
        _setup_context(with_agent_ctx=True)
        try:
            _working_memory_set("task", "my task")
            _working_memory_set("active_files", "a.py")
            _working_memory_set("decisions", "chose A over B")
            _working_memory_set("todos", "finish doc")
            r = _working_memory_get()
            assert r["status"] == "ok"
            data = r["data"]
            assert data["task"] == "my task"
            assert "a.py" in data["active_files"]
            assert "chose A over B" in data["decisions"]
            assert "finish doc" in data["todos"]
        finally:
            _teardown_context()

    def test_set_list_replaces(self):
        _setup_context(with_agent_ctx=True)
        try:
            _working_memory_set("active_files", "old.py")
            _working_memory_set("active_files", ["new1.py", "new2.py"])
            r = _working_memory_get("active_files")
            assert r["data"] == ["new1.py", "new2.py"]
        finally:
            _teardown_context()

    def test_remove_specific_item(self):
        _setup_context(with_agent_ctx=True)
        try:
            _working_memory_set("active_files", ["a.py", "b.py", "c.py"])
            _working_memory_remove("active_files", "b.py")
            r = _working_memory_get("active_files")
            assert r["data"] == ["a.py", "c.py"]
        finally:
            _teardown_context()

    def test_remove_clears_list(self):
        _setup_context(with_agent_ctx=True)
        try:
            _working_memory_set("active_files", ["a.py"])
            _working_memory_remove("active_files")
            r = _working_memory_get("active_files")
            assert r["data"] == []
        finally:
            _teardown_context()

    def test_remove_task(self):
        _setup_context(with_agent_ctx=True)
        try:
            _working_memory_set("task", "do something")
            _working_memory_remove("task")
            r = _working_memory_get("task")
            assert r["data"] == ""
        finally:
            _teardown_context()

    def test_clear_all(self):
        _setup_context(with_agent_ctx=True)
        try:
            _working_memory_set("task", "t")
            _working_memory_set("active_files", "f")
            _working_memory_set("todos", "td")
            r = _working_memory_clear()
            assert r["status"] == "ok"
            r = _working_memory_get()
            assert r["data"]["task"] == ""
            assert r["data"]["active_files"] == []
            assert r["data"]["todos"] == []
        finally:
            _teardown_context()

    def test_invalid_key(self):
        _setup_context(with_agent_ctx=True)
        try:
            r = _working_memory_get("bogus")
            assert r["status"] == "error"
            assert "Unknown working memory key" in r["error"]
        finally:
            _teardown_context()

    def test_errors_append_dict(self):
        _setup_context(with_agent_ctx=True)
        try:
            _working_memory_set("errors", {"command": "build", "error": "fail"})
            r = _working_memory_get("errors")
            assert len(r["data"]) == 1
            assert r["data"][0]["command"] == "build"
        finally:
            _teardown_context()


# ---------------------------------------------------------------------------
# P2: Runtime Config
# ---------------------------------------------------------------------------

class TestRuntimeConfig:
    def test_set_compression_strategy(self):
        _setup_context(with_agent_ctx=True)
        try:
            r = _set_compression_strategy("traditional")
            assert r["status"] == "ok"
            assert r["strategy"] == "traditional"
            r = _get_context_config()
            assert r["compression_strategy"] == "traditional"
        finally:
            _teardown_context()

    def test_set_compression_strategy_invalid(self):
        _setup_context(with_agent_ctx=True)
        try:
            r = _set_compression_strategy("bogus")
            assert r["status"] == "error"
        finally:
            _teardown_context()

    def test_set_context_window(self):
        _setup_context(with_agent_ctx=True)
        try:
            r = _set_context_window(64000)
            assert r["status"] == "ok"
            assert r["max_tokens"] == 64000
        finally:
            _teardown_context()

    def test_set_context_window_invalid(self):
        _setup_context()
        try:
            r = _set_context_window(-100)
            assert r["status"] == "error"
        finally:
            _teardown_context()

    def test_set_working_memory_enabled(self):
        _setup_context(with_agent_ctx=True)
        try:
            r = _set_working_memory_enabled(False)
            assert r["status"] == "ok"
            assert r["enabled"] is False
            # working memory should now be unavailable
            r2 = _working_memory_get()
            assert r2["status"] == "error"
        finally:
            _teardown_context()

    def test_set_cache_aware(self):
        _setup_context(with_agent_ctx=True)
        try:
            r = _set_cache_aware(False)
            assert r["status"] == "ok"
            assert r["cache_aware"] is False
            r = _get_context_config()
            assert r["cache_aware_enabled"] is False
        finally:
            _teardown_context()

    def test_get_context_config_fields(self):
        _setup_context(with_agent_ctx=True)
        try:
            r = _get_context_config()
            assert r["status"] == "ok"
            assert "compression_strategy" in r
            assert "max_tokens" in r
            assert "working_memory_enabled" in r
            assert "cache_aware_enabled" in r
            assert "working_memory_max_tokens" in r
        finally:
            _teardown_context()


# ---------------------------------------------------------------------------
# P2: insert_message / replace_message
# ---------------------------------------------------------------------------

class TestMessageMutation:
    def test_insert_message_at_end(self):
        history = [_make_msg(role="user", content="first", uuid="m1")]
        _setup_context(history)
        try:
            r = _insert_message("assistant", "second")
            assert r["status"] == "ok"
            assert r["index"] == 1
            assert len(history) == 2
            assert history[1].role == "assistant"
            assert history[1].content == "second"
        finally:
            _teardown_context()

    def test_insert_message_at_start(self):
        history = [_make_msg(role="user", content="second", uuid="m1")]
        _setup_context(history)
        try:
            r = _insert_message("system", "first", position="start")
            assert r["status"] == "ok"
            assert r["index"] == 0
            assert history[0].role == "system"
        finally:
            _teardown_context()

    def test_insert_message_invalid_role(self):
        _setup_context([])
        try:
            r = _insert_message("invalid_role", "content")
            assert r["status"] == "error"
        finally:
            _teardown_context()

    def test_replace_message_content(self):
        msg = _make_msg(role="user", content="old content", uuid="rep-1", token_count=50)
        _setup_context([msg])
        try:
            r = _replace_message("rep-1", "new content")
            assert r["status"] == "ok"
            assert msg.content == "new content"
            assert r["old_tokens"] == 50
        finally:
            _teardown_context()

    def test_replace_message_not_found(self):
        _setup_context([])
        try:
            r = _replace_message("missing", "content")
            assert r["status"] == "error"
        finally:
            _teardown_context()


# ---------------------------------------------------------------------------
# P3: search_context / context_slice
# ---------------------------------------------------------------------------

class TestQueryHelpers:
    def test_search_basic(self):
        history = [
            _make_msg(role="user", content="Hello world"),
            _make_msg(role="assistant", content="Hi there!"),
            _make_msg(role="user", content="Tell me about HELLO again"),
        ]
        _setup_context(history)
        try:
            r = _search_context("hello")
            assert r["status"] == "ok"
            assert r["total_matches"] == 2
            assert len(r["matches"]) == 2
        finally:
            _teardown_context()

    def test_search_with_role_filter(self):
        history = [
            _make_msg(role="user", content="match in user"),
            _make_msg(role="assistant", content="match in assistant"),
        ]
        _setup_context(history)
        try:
            r = _search_context("match", role="user")
            assert r["status"] == "ok"
            assert r["total_matches"] == 1
            assert r["matches"][0]["role"] == "user"
        finally:
            _teardown_context()

    def test_search_limit(self):
        history = [_make_msg(role="user", content=f"match-{i}") for i in range(10)]
        _setup_context(history)
        try:
            r = _search_context("match", limit=3)
            assert r["status"] == "ok"
            assert len(r["matches"]) == 3
            assert r["total_matches"] == 10
        finally:
            _teardown_context()

    def test_search_no_results(self):
        history = [_make_msg(content="nothing here")]
        _setup_context(history)
        try:
            r = _search_context("xyz")
            assert r["status"] == "ok"
            assert r["total_matches"] == 0
        finally:
            _teardown_context()

    def test_context_slice_default(self):
        history = [_make_msg(role="user", content=f"m-{i}", uuid=f"u{i}")
                   for i in range(5)]
        _setup_context(history)
        try:
            r = _context_slice()
            assert r["status"] == "ok"
            assert r["count"] == 5
        finally:
            _teardown_context()

    def test_context_slice_range(self):
        history = [_make_msg(role="user", content=f"m-{i}", uuid=f"u{i}")
                   for i in range(10)]
        _setup_context(history)
        try:
            r = _context_slice(start=2, end=5)
            assert r["status"] == "ok"
            assert r["count"] == 3
            assert r["messages"][0]["content"] == "m-2"
            assert r["messages"][2]["content"] == "m-4"
        finally:
            _teardown_context()

    def test_context_slice_role_filter(self):
        history = [
            _make_msg(role="user", content="u1"),
            _make_msg(role="assistant", content="a1"),
            _make_msg(role="user", content="u2"),
        ]
        _setup_context(history)
        try:
            r = _context_slice(role="user")
            assert r["count"] == 2
        finally:
            _teardown_context()


# ---------------------------------------------------------------------------
# P2/P3: export_context / import_context / fork_context
# ---------------------------------------------------------------------------

class TestContextTransfer:
    def test_export_context_basic(self):
        history = [
            _make_msg(role="system", content="sys", uuid="s1"),
            _make_msg(role="user", content="hi", uuid="u1"),
        ]
        _setup_context(history)
        try:
            r = _export_context()
            assert r["status"] == "ok"
            ctx = r["context"]
            assert len(ctx["messages"]) == 2
            assert ctx["messages"][0]["role"] == "system"
            assert ctx["messages"][1]["content"] == "hi"
        finally:
            _teardown_context()

    def test_export_includes_working_memory(self):
        _setup_context(with_agent_ctx=True)
        try:
            _working_memory_set("task", "export test")
            r = _export_context()
            assert r["status"] == "ok"
            assert r["context"]["working_memory"] is not None
            assert r["context"]["working_memory"]["task"] == "export test"
        finally:
            _teardown_context()

    def test_import_context_replaces_history(self):
        original = [_make_msg(role="user", content="original")]
        _setup_context(original, with_agent_ctx=True)
        try:
            data = {
                "messages": [
                    {"role": "system", "content": "new system"},
                    {"role": "user", "content": "new user"},
                ],
                "working_memory": {
                    "task": "imported task",
                    "active_files": [],
                    "decisions": [],
                    "todos": [],
                    "errors": [],
                },
            }
            r = _import_context(data)
            assert r["status"] == "ok"
            assert r["imported_messages"] == 2
            assert r["imported_working_memory"] is True
            assert len(original) == 2
            assert original[0].content == "new system"
            r = _working_memory_get("task")
            assert r["data"] == "imported task"
        finally:
            _teardown_context()

    def test_import_context_invalid_data(self):
        _setup_context([])
        try:
            r = _import_context("not a dict")
            assert r["status"] == "error"
        finally:
            _teardown_context()

    def test_fork_context_returns_same_as_export(self):
        history = [_make_msg(role="user", content="fork test", uuid="f1")]
        _setup_context(history)
        try:
            fork = _fork_context()
            export = _export_context()
            assert fork["status"] == "ok"
            assert len(fork["context"]["messages"]) == len(export["context"]["messages"])
        finally:
            _teardown_context()


# ---------------------------------------------------------------------------
# P1: Lifecycle hooks
# ---------------------------------------------------------------------------

class TestHooks:
    def test_on_compression_register_and_clear(self):
        r1 = _on_compression(lambda stats: None)
        assert r1["status"] == "ok"
        assert r1["previous"] is None
        r2 = _on_compression(None)
        assert r2["status"] == "ok"
        assert callable(r2["previous"])

    def test_on_context_overflow_register(self):
        r = _on_context_overflow(lambda stats: None)
        assert r["status"] == "ok"
        _on_context_overflow(None)  # clean up
