"""Tests for v1.19: Context management API enhancements.

Covers:
- context_stats() / context_usage() — inspection
- get_message(uuid) / delete_message(uuid) — message access
- pin_message(uuid) / unpin_message(uuid) — pinning (compression immunity)
- Pinned messages are skipped by all 5 graduated compression layers
"""

import pytest
from helen.stdlib.context import (
    _context_stats,
    _context_usage,
    _get_message,
    _delete_message,
    _pin_message,
    _unpin_message,
    _set_interpreter_context,
)
from helen.runtime.history import Message
from helen.runtime.graduated_compression import (
    _budget_reduction,
    _snip,
    _microcompact,
    _context_collapse,
    _auto_compact,
    BUDGET_REDUCTION_MAX_CHARS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_msg(role="user", content="hello", uuid="", pinned=False,
              tool_calls=None, tool_call_id=None, compressed=False,
              token_count=10):
    msg = Message(
        role=role,
        content=content,
        tool_calls=tool_calls or [],
        tool_call_id=tool_call_id,
        _token_count=token_count,
        uuid=uuid,
        pinned=pinned,
        compressed=compressed,
    )
    return msg


def _setup_context(messages, max_tokens=1000):
    """Inject a history list + a mock history_manager into stdlib context."""
    history_manager = type("HM", (), {"MAX_TOKENS": max_tokens})()
    _set_interpreter_context(messages, history_manager, None)


def _teardown_context():
    _set_interpreter_context([], None, None)


# ---------------------------------------------------------------------------
# context_stats
# ---------------------------------------------------------------------------

class TestContextStats:
    def test_empty_context(self):
        _setup_context([])
        try:
            stats = _context_stats()
            assert stats["status"] == "ok"
            assert stats["message_count"] == 0
            assert stats["total_tokens"] == 0
            assert stats["usage_ratio"] == 0.0
            assert stats["by_role"] == {"system": 0, "user": 0, "assistant": 0, "tool": 0}
            assert stats["compressed_count"] == 0
            assert stats["pinned_count"] == 0
        finally:
            _teardown_context()

    def test_counts_by_role(self):
        history = [
            _make_msg(role="system", content="sys"),
            _make_msg(role="user", content="u1"),
            _make_msg(role="user", content="u2"),
            _make_msg(role="assistant", content="a1"),
            _make_msg(role="tool", content="t1"),
        ]
        _setup_context(history)
        try:
            stats = _context_stats()
            assert stats["message_count"] == 5
            assert stats["by_role"]["system"] == 1
            assert stats["by_role"]["user"] == 2
            assert stats["by_role"]["assistant"] == 1
            assert stats["by_role"]["tool"] == 1
        finally:
            _teardown_context()

    def test_pinned_and_compressed_counts(self):
        history = [
            _make_msg(pinned=True),
            _make_msg(pinned=True),
            _make_msg(compressed=True),
            _make_msg(compressed=True, pinned=True),  # both
        ]
        _setup_context(history)
        try:
            stats = _context_stats()
            assert stats["pinned_count"] == 3
            assert stats["compressed_count"] == 2
        finally:
            _teardown_context()

    def test_usage_ratio(self):
        history = [_make_msg(token_count=100), _make_msg(token_count=200)]
        _setup_context(history, max_tokens=1000)
        try:
            stats = _context_stats()
            assert stats["total_tokens"] == 300
            assert abs(stats["usage_ratio"] - 0.3) < 1e-6
        finally:
            _teardown_context()

    def test_no_interpreter_context(self):
        _set_interpreter_context(None, None, None)
        stats = _context_stats()
        assert stats["status"] == "error"


# ---------------------------------------------------------------------------
# context_usage
# ---------------------------------------------------------------------------

class TestContextUsage:
    def test_usage_ratio(self):
        history = [_make_msg(token_count=250), _make_msg(token_count=250)]
        _setup_context(history, max_tokens=1000)
        try:
            assert abs(_context_usage() - 0.5) < 1e-6
        finally:
            _teardown_context()

    def test_no_history(self):
        _set_interpreter_context(None, None, None)
        assert _context_usage() == 0.0


# ---------------------------------------------------------------------------
# get_message / delete_message / pin_message / unpin_message
# ---------------------------------------------------------------------------

class TestMessageAccess:
    def test_get_message_by_uuid(self):
        msg = _make_msg(role="user", content="hello world", uuid="abc-123")
        _setup_context([msg])
        try:
            result = _get_message("abc-123")
            assert result["status"] == "ok"
            assert result["uuid"] == "abc-123"
            assert result["role"] == "user"
            assert result["content"] == "hello world"
        finally:
            _teardown_context()

    def test_get_message_not_found(self):
        _setup_context([])
        try:
            result = _get_message("does-not-exist")
            assert result["status"] == "error"
            assert "not found" in result["error"]
        finally:
            _teardown_context()

    def test_get_message_empty_uuid(self):
        _setup_context([])
        result = _get_message("")
        assert result["status"] == "error"

    def test_delete_message(self):
        msg = _make_msg(uuid="del-1", token_count=42)
        history = [_make_msg(uuid="keep-1"), msg, _make_msg(uuid="keep-2")]
        _setup_context(history)
        try:
            result = _delete_message("del-1")
            assert result["status"] == "ok"
            assert result["uuid"] == "del-1"
            assert result["deleted_tokens"] == 42
            assert len(history) == 2
            assert all(m.uuid != "del-1" for m in history)
        finally:
            _teardown_context()

    def test_delete_message_not_found(self):
        _setup_context([])
        try:
            result = _delete_message("missing")
            assert result["status"] == "error"
        finally:
            _teardown_context()

    def test_pin_and_unpin(self):
        msg = _make_msg(uuid="pin-1", pinned=False)
        _setup_context([msg])
        try:
            r1 = _pin_message("pin-1")
            assert r1["status"] == "ok"
            assert r1["pinned"] is True
            assert msg.pinned is True

            r2 = _unpin_message("pin-1")
            assert r2["status"] == "ok"
            assert r2["pinned"] is False
            assert msg.pinned is False
        finally:
            _teardown_context()

    def test_pin_not_found(self):
        _setup_context([])
        result = _pin_message("nope")
        assert result["status"] == "error"

    def test_get_message_reflects_pin_state(self):
        msg = _make_msg(uuid="x", pinned=False)
        _setup_context([msg])
        try:
            assert _get_message("x")["pinned"] is False
            _pin_message("x")
            assert _get_message("x")["pinned"] is True
        finally:
            _teardown_context()


# ---------------------------------------------------------------------------
# Pinned messages survive graduated compression layers
# ---------------------------------------------------------------------------

class TestPinnedSurvivesCompression:
    def test_layer1_budget_reduction_preserves_pinned_tool_result(self):
        big_content = "x" * (BUDGET_REDUCTION_MAX_CHARS + 100)
        pinned = _make_msg(role="tool", content=big_content, pinned=True,
                           tool_call_id="tc-1")
        history = [pinned]
        result = _budget_reduction(history)
        assert len(result) == 1
        assert result[0].content == big_content  # not replaced

    def test_layer1_budget_reduction_compresses_unpinned(self):
        big_content = "x" * (BUDGET_REDUCTION_MAX_CHARS + 100)
        unpinned = _make_msg(role="tool", content=big_content, pinned=False,
                             tool_call_id="tc-1")
        result = _budget_reduction([unpinned])
        assert "[Tool result cleared" in result[0].content

    def test_layer2_snip_preserves_pinned_stale_message(self):
        # Build a history with a pinned "stale" message
        old_pinned = _make_msg(role="user", content="important decision",
                               pinned=True, uuid="pin")
        history = [old_pinned] + [
            _make_msg(role="user", content=f"msg-{i}") for i in range(20)
        ]
        result = _snip(history, keep_recent=4)
        # pinned message must still be present
        assert any(getattr(m, 'uuid', '') == "pin" for m in result)

    def test_layer3_microcompact_preserves_pinned_tool_result(self):
        pinned = _make_msg(role="tool", content="critical data",
                           pinned=True, tool_call_id="tc-pin", compressed=False)
        old_unpinned = _make_msg(role="tool", content="old data",
                                 pinned=False, tool_call_id="tc-old", compressed=False)
        recent = [_make_msg(role="tool", content=f"r-{i}", tool_call_id=f"r-{i}")
                  for i in range(5)]
        history = [pinned, old_unpinned] + recent
        result = _microcompact(history, keep_recent=2)
        # pinned preserved
        pinned_result = [m for m in result if getattr(m, 'tool_call_id', '') == "tc-pin"]
        assert len(pinned_result) == 1
        assert pinned_result[0].content == "critical data"
        # unpinned old cleared
        old_result = [m for m in result if getattr(m, 'tool_call_id', '') == "tc-old"]
        assert len(old_result) == 1
        assert "[Tool result cleared" in old_result[0].content

    def test_layer4_context_collapse_preserves_pinned(self):
        old_pinned = _make_msg(role="user", content="important", pinned=True,
                               uuid="pin-4")
        # Build enough history to trigger collapse (> CONTEXT_COLLAPSE_THRESHOLD=20)
        old_msgs = [old_pinned] + [
            _make_msg(role="user" if i % 2 == 0 else "assistant",
                      content=f"turn-{i}")
            for i in range(30)
        ]
        result = _context_collapse(old_msgs)
        # pinned must be in the result (not archived into summary)
        assert any(getattr(m, 'uuid', '') == "pin-4" for m in result)
        # and its content should be unchanged
        pinned_msg = next(m for m in result if getattr(m, 'uuid', '') == "pin-4")
        assert pinned_msg.content == "important"

    def test_layer5_auto_compact_preserves_pinned(self):
        old_pinned = _make_msg(role="user", content="must-keep", pinned=True,
                               uuid="pin-5")
        history = [old_pinned] + [
            _make_msg(role="user" if i % 2 == 0 else "assistant",
                      content=f"turn-{i}")
            for i in range(10)
        ]
        # No LLM client → structural fallback
        result = _auto_compact(history, keep_recent=2, llm_client=None)
        assert any(getattr(m, 'uuid', '') == "pin-5" for m in result)
        pinned_msg = next(m for m in result if getattr(m, 'uuid', '') == "pin-5")
        assert pinned_msg.content == "must-keep"
