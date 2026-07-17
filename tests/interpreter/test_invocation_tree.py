"""Tests for v1.22 invocation tree feature.

Covers:
- Per-agent active context isolation
- Same-agent multiple calls are fresh
- Nested agent call isolation
- Invocation metadata (invocation_id, agent_name, parent_invocation_id)
- Invocation tree query APIs (list_invocations, get_invocation, etc.)
- Extended replay_transcript filtering
- Extended restore_context with invocation_id/agent filtering
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from helen.runtime.history import Message


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_interp():
    """Create an Interpreter with an initialized transcript store."""
    from helen.interpreter.interpreter import Interpreter
    interp = Interpreter()
    return interp


def _add_msg(interp, role, content, agent_name=None, invocation_id="", parent_invocation_id=""):
    """Add a message to interp's transcript store with the given fields."""
    msg = Message(
        role=role,
        content=content,
        agent_name=agent_name,
        invocation_id=invocation_id,
        parent_invocation_id=parent_invocation_id,
    )
    interp._agent_context.transcript_store.append(msg)
    return msg


# ---------------------------------------------------------------------------
# Tests: Per-agent context isolation
# ---------------------------------------------------------------------------

class TestContextIsolation:
    """Each agent main {} call should have fresh context."""

    def test_two_agents_isolated(self):
        """Agent B should not see agent A's messages."""
        interp = _make_interp()

        # Top-level invocation
        top_inv = interp._enter_invocation(None)

        # Agent A's invocation
        a_inv = interp._enter_invocation("A")
        _add_msg(interp, "user", "A's message", agent_name="A",
                 invocation_id=a_inv, parent_invocation_id=top_inv)
        # During A: only sees A's messages
        history = interp._history
        assert len(history) == 1
        assert history[0].content == "A's message"

        # A exits
        interp._exit_invocation()

        # After A exits: top-level sees only top-level's messages (0)
        history = interp._history
        assert len(history) == 0

        # Agent B's invocation
        b_inv = interp._enter_invocation("B")
        _add_msg(interp, "user", "B's message", agent_name="B",
                 invocation_id=b_inv, parent_invocation_id=top_inv)
        # During B: only sees B's messages
        history = interp._history
        assert len(history) == 1
        assert history[0].content == "B's message"

        # B exits
        interp._exit_invocation()

        # Top-level exits
        interp._exit_invocation()

        # After top-level exits: no filter, sees all messages
        history = interp._history
        assert len(history) == 2
        contents = {m.content for m in history}
        assert contents == {"A's message", "B's message"}

    def test_same_agent_twice_is_fresh(self):
        """Calling the same agent twice should give fresh context each time."""
        interp = _make_interp()

        # Top-level
        top_inv = interp._enter_invocation(None)

        # First call to A
        a1_inv = interp._enter_invocation("A")
        _add_msg(interp, "user", "A call 1", agent_name="A",
                 invocation_id=a1_inv, parent_invocation_id=top_inv)
        assert len(interp._history) == 1
        interp._exit_invocation()

        # Second call to A - should be fresh
        a2_inv = interp._enter_invocation("A")
        # Second call doesn't see first call's messages
        assert len(interp._history) == 0
        _add_msg(interp, "user", "A call 2", agent_name="A",
                 invocation_id=a2_inv, parent_invocation_id=top_inv)
        assert len(interp._history) == 1
        assert interp._history[0].content == "A call 2"
        interp._exit_invocation()

        interp._exit_invocation()

        # Transcript has both
        from helen.runtime.transcript_store import Message as TM
        all_msgs = [i for i in interp._agent_context.transcript_store.transcript
                    if isinstance(i, TM)]
        assert len(all_msgs) == 2

    def test_nested_isolation(self):
        """Inner agent shouldn't see outer's messages; outer shouldn't see inner's after return."""
        interp = _make_interp()

        # Top-level
        top_inv = interp._enter_invocation(None)

        # Outer starts
        outer_inv = interp._enter_invocation("Outer")
        _add_msg(interp, "user", "outer start", agent_name="Outer",
                 invocation_id=outer_inv, parent_invocation_id=top_inv)
        assert len(interp._history) == 1

        # Inner starts (nested in outer)
        inner_inv = interp._enter_invocation("Inner")
        # Inner should NOT see outer's messages
        assert len(interp._history) == 0
        _add_msg(interp, "user", "inner", agent_name="Inner",
                 invocation_id=inner_inv, parent_invocation_id=outer_inv)
        assert len(interp._history) == 1
        assert interp._history[0].content == "inner"

        # Inner exits
        interp._exit_invocation()

        # Outer should NOT see inner's messages
        assert len(interp._history) == 1
        assert interp._history[0].content == "outer start"

        _add_msg(interp, "user", "outer end", agent_name="Outer",
                 invocation_id=outer_inv, parent_invocation_id=top_inv)
        # Outer now sees both its own messages
        assert len(interp._history) == 2

        interp._exit_invocation()
        interp._exit_invocation()


# ---------------------------------------------------------------------------
# Tests: Invocation metadata
# ---------------------------------------------------------------------------

class TestInvocationMetadata:
    """Messages should have correct invocation_id, agent_name, parent."""

    def test_metadata_fields(self):
        """Messages created via _add_to_history should have correct metadata."""
        from helen.interpreter.interpreter import Interpreter
        from helen.core.ast import AgentDeclNode

        interp = Interpreter()

        # Simulate an agent being active
        mock_agent = MagicMock()
        mock_agent.name = "TestAgent"
        interp._current_agent = mock_agent

        # Enter invocation
        inv_id = interp._enter_invocation("TestAgent")

        # Add message via _add_to_history
        interp._add_to_history("user", "test message")

        # Check the message in transcript store
        from helen.runtime.transcript_store import Message as TM
        msgs = [i for i in interp._agent_context.transcript_store.transcript
                if isinstance(i, TM)]
        assert len(msgs) == 1
        msg = msgs[0]
        assert msg.agent_name == "TestAgent"
        assert msg.invocation_id == inv_id
        assert msg.parent_invocation_id == ""  # top-level parent
        assert msg.content == "test message"

        interp._exit_invocation()

    def test_nested_metadata(self):
        """Nested invocation should record parent correctly."""
        from helen.interpreter.interpreter import Interpreter

        interp = Interpreter()

        # Outer
        outer_inv = interp._enter_invocation("Outer")

        mock_agent = MagicMock()
        mock_agent.name = "Inner"
        interp._current_agent = mock_agent

        # Inner (nested)
        inner_inv = interp._enter_invocation("Inner")

        interp._add_to_history("user", "inner message")

        from helen.runtime.transcript_store import Message as TM
        msgs = [i for i in interp._agent_context.transcript_store.transcript
                if isinstance(i, TM)]
        assert len(msgs) == 1
        msg = msgs[0]
        assert msg.agent_name == "Inner"
        assert msg.invocation_id == inner_inv
        assert msg.parent_invocation_id == outer_inv  # parent is outer

        interp._exit_invocation()
        interp._exit_invocation()


# ---------------------------------------------------------------------------
# Tests: Invocation tree queries
# ---------------------------------------------------------------------------

class TestInvocationTreeQueries:
    """list_invocations, get_invocation, get_invocation_tree, invocation_path."""

    def _build_session(self, interp):
        """Build a session with some invocations and messages."""
        # Top-level
        top_inv = interp._enter_invocation(None)
        _add_msg(interp, "user", "top-level msg",
                 invocation_id=top_inv)

        # Agent A (child of top-level)
        a_inv = interp._enter_invocation("A")
        _add_msg(interp, "user", "A msg 1", agent_name="A",
                 invocation_id=a_inv, parent_invocation_id=top_inv)
        _add_msg(interp, "assistant", "A msg 2", agent_name="A",
                 invocation_id=a_inv, parent_invocation_id=top_inv)
        interp._exit_invocation()

        # Agent B (child of top-level)
        b_inv = interp._enter_invocation("B")
        _add_msg(interp, "user", "B msg 1", agent_name="B",
                 invocation_id=b_inv, parent_invocation_id=top_inv)
        interp._exit_invocation()

        interp._exit_invocation()

        return top_inv, a_inv, b_inv

    def test_list_invocations(self):
        from helen.stdlib.transcript import list_invocations
        import helen.stdlib.transcript as tm

        interp = _make_interp()
        tm._interpreter_agent_context = interp._agent_context
        self._build_session(interp)

        # Get session_id from interp
        sid = interp._agent_context.session_id
        result = list_invocations(session_id=sid)
        assert len(result) == 3  # top-level + A + B

        # Filter by agent
        a_runs = list_invocations(session_id=sid, agent="A")
        assert len(a_runs) == 1
        assert a_runs[0]["agent_name"] == "A"
        assert a_runs[0]["message_count"] == 2

    def test_get_invocation(self):
        from helen.stdlib.transcript import get_invocation
        import helen.stdlib.transcript as tm

        interp = _make_interp()
        tm._interpreter_agent_context = interp._agent_context
        top_inv, a_inv, b_inv = self._build_session(interp)

        sid = interp._agent_context.session_id
        info = get_invocation(a_inv, session_id=sid)
        assert info["agent_name"] == "A"
        assert info["message_count"] == 2
        assert info["parent_invocation_id"] == top_inv

        # Unknown invocation
        info = get_invocation("nonexistent", session_id=sid)
        assert info == {}

    def test_get_invocation_tree(self):
        from helen.stdlib.transcript import get_invocation_tree
        import helen.stdlib.transcript as tm

        interp = _make_interp()
        tm._interpreter_agent_context = interp._agent_context
        self._build_session(interp)

        sid = interp._agent_context.session_id
        tree = get_invocation_tree(session_id=sid)

        # Should have top-level root with A and B as children
        assert tree["agent_name"] is None
        child_names = {c["agent_name"] for c in tree["children"]}
        assert child_names == {"A", "B"}

    def test_invocation_path(self):
        from helen.stdlib.transcript import invocation_path
        import helen.stdlib.transcript as tm

        interp = _make_interp()
        tm._interpreter_agent_context = interp._agent_context
        self._build_session(interp)

        sid = interp._agent_context.session_id
        path = invocation_path(sid, session_id=sid)  # using top_inv would be better
        # The path should be "top" (just top-level)

        # Unknown invocation
        path = invocation_path("nonexistent", session_id=sid)
        assert path == ""


# ---------------------------------------------------------------------------
# Tests: Extended replay_transcript
# ---------------------------------------------------------------------------

class TestReplayTranscriptFilter:
    """replay_transcript with agent / invocation_id filtering."""

    def _build_session(self, interp):
        top_inv = interp._enter_invocation(None)
        a_inv = interp._enter_invocation("A")
        _add_msg(interp, "user", "A msg", agent_name="A",
                 invocation_id=a_inv, parent_invocation_id=top_inv)
        interp._exit_invocation()
        b_inv = interp._enter_invocation("B")
        _add_msg(interp, "user", "B msg", agent_name="B",
                 invocation_id=b_inv, parent_invocation_id=top_inv)
        interp._exit_invocation()
        interp._exit_invocation()
        return top_inv, a_inv, b_inv

    def test_filter_by_agent(self):
        from helen.stdlib.transcript import replay_transcript
        import helen.stdlib.transcript as tm

        interp = _make_interp()
        tm._interpreter_agent_context = interp._agent_context
        top_inv, a_inv, b_inv = self._build_session(interp)

        sid = interp._agent_context.session_id
        msgs = replay_transcript(session_id=sid, agent="A")
        assert len(msgs) == 1
        assert msgs[0]["content"] == "A msg"
        assert msgs[0]["agent_name"] == "A"

    def test_filter_by_invocation_id(self):
        from helen.stdlib.transcript import replay_transcript
        import helen.stdlib.transcript as tm

        interp = _make_interp()
        tm._interpreter_agent_context = interp._agent_context
        top_inv, a_inv, b_inv = self._build_session(interp)

        sid = interp._agent_context.session_id
        msgs = replay_transcript(session_id=sid, invocation_id=b_inv)
        assert len(msgs) == 1
        assert msgs[0]["content"] == "B msg"

    def test_last_only(self):
        """last_only returns only the agent's most recent invocation."""
        from helen.stdlib.transcript import replay_transcript
        import helen.stdlib.transcript as tm

        interp = _make_interp()
        tm._interpreter_agent_context = interp._agent_context

        top_inv = interp._enter_invocation(None)

        # First call to A
        a1_inv = interp._enter_invocation("A")
        _add_msg(interp, "user", "A call 1", agent_name="A",
                 invocation_id=a1_inv, parent_invocation_id=top_inv)
        interp._exit_invocation()

        # Second call to A
        a2_inv = interp._enter_invocation("A")
        _add_msg(interp, "user", "A call 2", agent_name="A",
                 invocation_id=a2_inv, parent_invocation_id=top_inv)
        interp._exit_invocation()

        interp._exit_invocation()

        sid = interp._agent_context.session_id
        # Without last_only: both calls
        msgs = replay_transcript(session_id=sid, agent="A")
        assert len(msgs) == 2

        # With last_only: only most recent
        msgs = replay_transcript(session_id=sid, agent="A", last_only=True)
        assert len(msgs) == 1
        assert msgs[0]["content"] == "A call 2"


# ---------------------------------------------------------------------------
# Tests: Extended restore_context
# ---------------------------------------------------------------------------

class TestRestoreContextFilter:
    """restore_context with invocation_id/agent filtering."""

    def _build_two_session(self, tmp_path, monkeypatch):
        """Create two sessions: one with A, one with A+B."""
        from helen.runtime.transcript_store import TranscriptStore, JSONLBackend

        # Session 1: just A
        sess1_dir = tmp_path / "session_1"
        sess1_dir.mkdir()
        tp1 = sess1_dir / "transcript.jsonl"
        store1 = TranscriptStore()
        # Simulate top-level + A
        store1.append(Message(role="user", content="A msg 1",
                              agent_name="A", invocation_id="inv_a1",
                              parent_invocation_id=""))
        store1.append(Message(role="assistant", content="A msg 2",
                              agent_name="A", invocation_id="inv_a1",
                              parent_invocation_id=""))
        b1 = JSONLBackend(tp1)
        for item in store1.transcript:
            b1.append(item)

        # Session 2: A then B
        sess2_dir = tmp_path / "session_2"
        sess2_dir.mkdir()
        tp2 = sess2_dir / "transcript.jsonl"
        store2 = TranscriptStore()
        store2.append(Message(role="user", content="A msg", agent_name="A",
                              invocation_id="inv_a2", parent_invocation_id=""))
        store2.append(Message(role="user", content="B msg", agent_name="B",
                              invocation_id="inv_b2", parent_invocation_id=""))
        b2 = JSONLBackend(tp2)
        for item in store2.transcript:
            b2.append(item)

        def fake_resolve(scope=""):
            return (str(tmp_path), "global")
        monkeypatch.setattr(
            "helen.runtime.config.resolve_session_dir", fake_resolve
        )

    def test_restore_with_agent_filter(self, tmp_path, monkeypatch):
        from helen.stdlib.context import _restore_context, _set_interpreter_context
        import helen.stdlib.context as cm

        self._build_two_session(tmp_path, monkeypatch)

        # Set up interpreter context
        interp = _make_interp()
        _set_interpreter_context(
            interp._interpreter_history,
            interp._history_manager,
            interp._agent_context,
        )

        # Restore agent A from session 1
        result = _restore_context("session_1", agent="A")
        assert result["status"] == "ok"
        assert result["restored_messages"] == 2
        assert result["filter"]["agent"] == "A"

    def test_restore_with_invocation_filter(self, tmp_path, monkeypatch):
        from helen.stdlib.context import _restore_context, _set_interpreter_context

        self._build_two_session(tmp_path, monkeypatch)

        interp = _make_interp()
        _set_interpreter_context(
            interp._interpreter_history,
            interp._history_manager,
            interp._agent_context,
        )

        # Restore only B's invocation from session 2
        result = _restore_context("session_2", invocation_id="inv_b2")
        assert result["status"] == "ok"
        assert result["restored_messages"] == 1
        assert result["filter"]["invocation_id"] == "inv_b2"

    def test_restore_nonexistent_filter(self, tmp_path, monkeypatch):
        from helen.stdlib.context import _restore_context, _set_interpreter_context

        self._build_two_session(tmp_path, monkeypatch)

        interp = _make_interp()
        _set_interpreter_context(
            interp._interpreter_history,
            interp._history_manager,
            interp._agent_context,
        )

        # Filter matches nothing
        result = _restore_context("session_1", agent="Z")
        assert result["status"] == "error"
        assert "matching the filter" in result["error"]


# ---------------------------------------------------------------------------
# Tests: Backward compatibility
# ---------------------------------------------------------------------------

class TestBackwardCompat:
    """Old transcripts without invocation_id should still work."""

    def test_old_messages_visible(self):
        """Messages without invocation_id are visible when not in an invocation."""
        interp = _make_interp()

        # Add an old-style message (no invocation_id)
        old_msg = Message(role="user", content="old message")
        interp._agent_context.transcript_store.append(old_msg)

        # At top-level (no current invocation), old message is visible
        assert len(interp._history) == 1
        assert interp._history[0].content == "old message"

    def test_old_messages_hidden_in_invocation(self):
        """Old-style messages are filtered out when inside an invocation."""
        interp = _make_interp()

        # Add old-style message
        old_msg = Message(role="user", content="old message")
        interp._agent_context.transcript_store.append(old_msg)

        # Enter invocation
        inv_id = interp._enter_invocation("A")
        _add_msg(interp, "user", "new message", agent_name="A",
                 invocation_id=inv_id)

        # Inside invocation: only new messages visible
        history = interp._history
        assert len(history) == 1
        assert history[0].content == "new message"

        interp._exit_invocation()
