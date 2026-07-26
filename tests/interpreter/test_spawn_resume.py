"""Tests for spawn resume("<session_id>") clause (v1.27).

v1.27 lets a spawned agent resume a previously saved child-session
transcript instead of starting fresh:

    let mb = spawn Worker("input") resume("session_1783492628_d9d9c0aa")

These tests cover:
- Parser: the resume clause and its Chinese alias 恢复会话(...)
- End-to-end: the spawned agent receives the resumed session_id
- History loading: resumed transcripts are populated with past messages
- Graceful fallback: a non-existent session_id creates a fresh session
- Cross-process locking: SessionManager.acquire_session_lock
"""

import json
import os
from typing import Tuple, List, Any

import pytest

from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.core.errors import ErrorReporter
from helen.core.ast import SpawnExprNode
from helen.interpreter.interpreter import Interpreter
from helen.runtime.llm_runtime import MockLLMRuntime
from helen.runtime.session_manager import SessionManager
from helen.runtime.transcript_store import TranscriptStore, JSONLBackend
from helen.runtime.history import Message


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_spawn(source: str) -> SpawnExprNode | None:
    """Parse ``source`` and return the first SpawnExprNode, or None."""
    tokens = Scanner(source=source, file='<test>').scan_all()
    errors = ErrorReporter()
    program = Parser(tokens, errors).parse()
    assert not errors.has_errors, f"Parse errors: {errors._errors}"
    for stmt in program.statements:
        init = getattr(stmt, 'initializer', None)
        if isinstance(init, SpawnExprNode):
            return init
    return None


def run_helen(source: str) -> Tuple[List[str], List[str], Any]:
    """Run Helen source, returning (stdout_lines, errors, result)."""
    import io
    import sys

    errors = ErrorReporter()
    scanner = Scanner(source=source, file='<test>')
    tokens = scanner.scan_all()
    parser = Parser(tokens, errors)
    program = parser.parse()

    if errors.has_errors:
        return [], [str(e) for e in errors._errors], None

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    result = None
    try:
        interp = Interpreter(errors=errors, llm_runtime=MockLLMRuntime())
        result = interp.interpret(program)
        output = sys.stdout.getvalue().strip().split('\n') if sys.stdout.getvalue().strip() else []
    finally:
        sys.stdout = old_stdout

    return output, [], result


def run_helen_with_session(source: str, session_id: str | None = None,
                           mock: MockLLMRuntime | None = None):
    """Run Helen source with an optional resumed session_id and mock runtime.

    Returns (stdout_lines, mock) so the caller can inspect ``mock.act_history``
    to verify what history ``llm act`` actually received.
    """
    import io
    import sys

    errors = ErrorReporter()
    tokens = Scanner(source=source, file='<test>').scan_all()
    program = Parser(tokens, errors).parse()
    if errors.has_errors:
        return [], mock or MockLLMRuntime()

    runtime = mock or MockLLMRuntime(act_return="ok")
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        interp = Interpreter(errors=errors, llm_runtime=runtime, session_id=session_id)
        interp.interpret(program)
        output = sys.stdout.getvalue().strip().split('\n') if sys.stdout.getvalue().strip() else []
    finally:
        sys.stdout = old_stdout
    return output, runtime


def _force_jsonl_config(monkeypatch, tmp_path):
    """Force JSONL backend + isolated session dir for deterministic tests."""
    import helen.runtime.config as cfg
    monkeypatch.setenv("HELEN_SESSION_DIR", str(tmp_path))
    monkeypatch.setattr(cfg, "get_transcript_config", lambda: {
        "enabled": True,
        "backend": "jsonl",
        "session_scope": "global",
        "session_dir": str(tmp_path),
        "project_session_dir": str(tmp_path),
        "max_memory_items": 100,
    })


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

class TestSpawnResumeParser:
    """v1.27: the resume clause parses correctly."""

    def test_resume_clause_parsed(self):
        sp = _parse_spawn('let mb = spawn Worker("x") resume("session_abc")')
        assert sp is not None
        assert sp.resume_session is not None

    def test_no_resume_backward_compat(self):
        sp = _parse_spawn('let mb = spawn Worker("x")')
        assert sp is not None
        assert sp.resume_session is None

    def test_resume_chinese_alias(self):
        sp = _parse_spawn('let mb = spawn Worker("x") 恢复会话("session_abc")')
        assert sp is not None
        assert sp.resume_session is not None

    def test_resume_bare_string(self):
        sp = _parse_spawn('let mb = spawn Worker("x") resume "session_abc"')
        assert sp is not None
        assert sp.resume_session is not None

    def test_resume_with_variable_expression(self):
        sp = _parse_spawn('let mb = spawn Worker("x") resume(saved_id)')
        assert sp is not None
        assert sp.resume_session is not None

    def test_keyword_count_unchanged_at_89(self):
        """resume is an identifier clause, not a keyword token."""
        from helen.core.tokens import keywords
        assert len(keywords()) == 89


# ---------------------------------------------------------------------------
# End-to-end spawn tests
# ---------------------------------------------------------------------------

class TestSpawnResumeIntegration:
    """End-to-end: spawn resume passes the session_id to the spawned agent."""

    def test_resume_returns_same_session_id(self, monkeypatch, tmp_path):
        """Spawning twice -- first fresh, then resume(first sid) -- yields the
        same session_id in both agents, proving the id is threaded through."""
        _force_jsonl_config(monkeypatch, tmp_path)
        source = '''
agent Probe(reply: Channel) {
    main {
        let sid = get_session_id()
        reply.send({"sid": sid})
        reply.close()
    }
}

main {
    let mb1 = spawn Probe()
    let r1 = mb1.receive()
    let sid1 = r1["sid"]

    let mb2 = spawn Probe() resume(sid1)
    let r2 = mb2.receive()
    let sid2 = r2["sid"]

    print(sid1)
    print(sid2)
}
'''
        output, errors, _ = run_helen(source)
        assert not errors, errors
        assert len(output) >= 2
        assert output[0] == output[1], f"sid1={output[0]} != sid2={output[1]}"
        # session_id should be non-empty and look like a session
        assert output[0].startswith("session_")

    def test_resume_nonexistent_session_is_graceful(self, monkeypatch, tmp_path):
        """A non-existent session_id creates a fresh session with that id
        instead of crashing."""
        _force_jsonl_config(monkeypatch, tmp_path)
        source = '''
agent Probe(reply: Channel) {
    main {
        let sid = get_session_id()
        reply.send({"sid": sid})
        reply.close()
    }
}

main {
    let mb = spawn Probe() resume("session_does_not_exist_yet")
    let r = mb.receive()
    print(r["sid"])
}
'''
        output, errors, _ = run_helen(source)
        assert not errors, errors
        assert len(output) >= 1
        assert output[0] == "session_does_not_exist_yet"

    def test_resume_loads_history_end_to_end(self, monkeypatch, tmp_path):
        """First spawn writes a marker via insert_message; second spawn
        resumes that session and finds the marker via search_context."""
        _force_jsonl_config(monkeypatch, tmp_path)
        source = '''
agent Probe(mode: str, reply: Channel) {
    main {
        if mode == "write" {
            insert_message("user", "The secret code is BANANA_42")
            let sid = get_session_id()
            reply.send({"sid": sid})
            reply.close()
        } else {
            let sid = get_session_id()
            let found = search_context("BANANA_42")
            reply.send({"sid": sid, "matches": found["total_matches"]})
            reply.close()
        }
    }
}

main {
    let mb1 = spawn Probe("write")
    let r1 = mb1.receive()
    let sid1 = r1["sid"]

    let mb2 = spawn Probe("read") resume(sid1)
    let r2 = mb2.receive()

    print(sid1)
    print(r2["sid"])
    print(r2["matches"])
}
'''
        output, errors, _ = run_helen(source)
        assert not errors, errors
        assert len(output) >= 3
        assert output[0] == output[1], "resumed sid should match first sid"
        assert int(output[2]) >= 1, f"marker not found in resumed history (matches={output[2]})"


# ---------------------------------------------------------------------------
# Interpreter-level history loading
# ---------------------------------------------------------------------------

class TestResumeHistoryLoading:
    """Resuming a session loads its historical transcript messages."""

    def test_resume_loads_existing_messages(self, monkeypatch, tmp_path):
        _force_jsonl_config(monkeypatch, tmp_path)
        marker = "The secret code is BANANA_42"

        # Create a session and persist a marker message to its transcript.
        manager = SessionManager(base_dir=tmp_path)
        session_id = "session_test_marker"
        manager.create_session(session_id)
        transcript_path = manager.get_session_path(session_id)
        backend = JSONLBackend(transcript_path)
        store = TranscriptStore(backend=backend, max_memory_items=100)
        store.append(Message(role="user", content=marker))

        # Construct an Interpreter that resumes that session.
        interp = Interpreter(session_id=session_id)
        # Trigger lazy transcript initialization.
        resumed_sid = interp._agent_context.session_id
        assert resumed_sid == session_id

        # The historical marker must be present in the loaded transcript.
        loaded = interp._agent_context.transcript_store
        contents = []
        for m in loaded.transcript:
            c = m.content
            if isinstance(c, list):
                c = " ".join(p.get("text", "") for p in c if isinstance(p, dict))
            contents.append(str(c))
        assert any(marker in c for c in contents), \
            f"marker not loaded; transcript contents: {contents}"


# ---------------------------------------------------------------------------
# LLM-visible context after resume (v1.27: expose_resumed_messages_to)
# ---------------------------------------------------------------------------

class TestResumeContextVisibleToLLM:
    """Resuming a session must restore what ``llm act`` sees, not just the
    transcript file. v1.27 hooks ``_enter_invocation`` to add the new
    invocation_id to each resumed message's ``visible_to_invocation_ids``,
    so per-invocation isolation (v1.22) no longer hides the prior history."""

    @staticmethod
    def _seed_session(tmp_path, sid, marker="The secret code is BANANA_42"):
        """Create a session with a prior user/assistant exchange."""
        manager = SessionManager(base_dir=tmp_path)
        manager.create_session(sid)
        backend = JSONLBackend(manager.get_session_path(sid))
        store = TranscriptStore(backend=backend, max_memory_items=100)
        store.append(Message(role="user", content=marker, invocation_id="inv_prev_run"))
        store.append(Message(role="assistant", content="Noted: " + marker,
                             invocation_id="inv_prev_run"))

    def test_llm_act_sees_resumed_history_via_spawn_resume(self, monkeypatch, tmp_path):
        """spawn ... resume('sid'): the spawned agent's llm act receives the
        resumed history (not an empty context)."""
        _force_jsonl_config(monkeypatch, tmp_path)
        self._seed_session(tmp_path, "session_child_resume")

        source = '''
agent Worker(reply: Channel) {
    main {
        let r = llm act "what was the secret code?"
        reply.send(r)
        reply.close()
    }
}
main {
    let mb = spawn Worker() resume("session_child_resume")
    print(mb.receive())
}
'''
        mock = MockLLMRuntime(act_return="the code is BANANA_42")
        _, mock = run_helen_with_session(source, session_id=None, mock=mock)

        # The spawned Worker's llm act call must have received the resumed history.
        assert len(mock.act_history) >= 1, "llm act was not invoked"
        history = mock.act_history[-1]["history"] or []
        history_text = json.dumps(history)
        assert "BANANA_42" in history_text, \
            f"spawn resume: llm act did not see resumed history: {history_text}"

    def test_llm_act_sees_resumed_history_via_interpreter_session_id(self, monkeypatch, tmp_path):
        """Interpreter(session_id=X): an agent called DIRECTLY in main (same
        interpreter, so the resumed store is in effect) sees the resumed
        history via llm act. This is the main-session startup-resume path
        (``helen --session=X``)."""
        _force_jsonl_config(monkeypatch, tmp_path)
        self._seed_session(tmp_path, "session_main_resume")

        source = '''
agent Worker() {
    main {
        return llm act "what was the secret code?"
    }
}
main {
    print(Worker())
}
'''
        mock = MockLLMRuntime(act_return="the code is BANANA_42")
        _, mock = run_helen_with_session(source, session_id="session_main_resume", mock=mock)

        assert len(mock.act_history) >= 1, "llm act was not invoked"
        history = mock.act_history[-1]["history"] or []
        history_text = json.dumps(history)
        assert "BANANA_42" in history_text, \
            f"Interpreter(session_id=): llm act did not see resumed history: {history_text[:200]}"

    def test_resumed_history_visible_to_new_invocation(self, monkeypatch, tmp_path):
        """Directly verify _history visibility after _enter_invocation on a
        resumed interpreter (the mechanism behind the llm act visibility)."""
        _force_jsonl_config(monkeypatch, tmp_path)
        manager = SessionManager(base_dir=tmp_path)
        sid = "session_visibility"
        manager.create_session(sid)
        backend = JSONLBackend(manager.get_session_path(sid))
        store = TranscriptStore(backend=backend, max_memory_items=100)
        store.append(Message(role="user", content="REMEMBER_BANANA_42",
                             invocation_id="inv_old", visible_to_invocation_ids=[]))

        interp = Interpreter(session_id=sid)
        # Before entering an invocation: top-level sees all (no filter).
        interp._current_invocation_id = ""
        assert any("REMEMBER_BANANA_42" in str(m.content) for m in interp._history)

        # Enter an agent invocation -> resumed messages get exposed to it.
        new_inv = interp._enter_invocation("Worker")
        assert new_inv, "expected a non-empty invocation_id"
        seen = any("REMEMBER_BANANA_42" in str(m.content) for m in interp._history)
        assert seen, "resumed history not visible to new agent invocation"

        # The resumed message's visible_to_invocation_ids now includes new_inv.
        for m in interp._agent_context.transcript_store.transcript:
            if "REMEMBER_BANANA_42" in str(getattr(m, "content", "")):
                assert new_inv in m.visible_to_invocation_ids
        interp._exit_invocation()

    def test_new_messages_stay_isolated_after_resume(self, monkeypatch, tmp_path):
        """Resumed history is shared, but NEW messages created during the run
        still respect per-invocation isolation: agent B does not see agent A's
        new messages (only the resumed history)."""
        _force_jsonl_config(monkeypatch, tmp_path)
        manager = SessionManager(base_dir=tmp_path)
        sid = "session_isolation"
        manager.create_session(sid)
        backend = JSONLBackend(manager.get_session_path(sid))
        store = TranscriptStore(backend=backend, max_memory_items=100)
        store.append(Message(role="user", content="RESUMED_MARKER",
                             invocation_id="inv_old"))

        interp = Interpreter(session_id=sid)

        # Agent A invocation: writes a new message, sees resumed history.
        inv_a = interp._enter_invocation("AgentA")
        # Simulate Agent A producing a message.
        interp._add_to_history("user", "FROM_AGENT_A_ONLY")
        hist_a = interp._history
        assert any("RESUMED_MARKER" in str(m.content) for m in hist_a), "A should see resumed"
        assert any("FROM_AGENT_A_ONLY" in str(m.content) for m in hist_a), "A sees its own msg"
        interp._exit_invocation()

        # Agent B invocation: should see resumed history but NOT Agent A's message.
        inv_b = interp._enter_invocation("AgentB")
        hist_b = interp._history
        assert any("RESUMED_MARKER" in str(m.content) for m in hist_b), \
            "B should see resumed history (shared session context)"
        assert not any("FROM_AGENT_A_ONLY" in str(m.content) for m in hist_b), \
            "B must NOT see Agent A's new message (per-invocation isolation)"
        interp._exit_invocation()


# ---------------------------------------------------------------------------
# Session lock unit tests
# ---------------------------------------------------------------------------

class TestSessionLock:
    """v1.27: cross-process session locking in SessionManager."""

    def test_acquire_fresh(self, tmp_path):
        m = SessionManager(base_dir=tmp_path)
        acquired, holder = m.acquire_session_lock("session_1")
        assert acquired is True
        assert holder is None
        assert m._lock_path("session_1").exists()

    def test_acquire_same_pid_reclaims(self, tmp_path):
        """In-process reuse (e.g. spawn resuming a sibling) reclaims the lock."""
        m = SessionManager(base_dir=tmp_path)
        m.acquire_session_lock("session_1")
        acquired, _ = m.acquire_session_lock("session_1")
        assert acquired is True

    def test_acquire_stale_lock_reclaimed(self, tmp_path):
        """A lock held by a dead PID is reclaimed."""
        m = SessionManager(base_dir=tmp_path)
        lock_path = m._lock_path("session_1")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text("99999999", encoding="utf-8")  # almost certainly dead
        acquired, holder = m.acquire_session_lock("session_1")
        assert acquired is True
        assert holder is None

    def test_acquire_refuses_live_holder(self, tmp_path, monkeypatch):
        """A lock held by another live process is refused."""
        m = SessionManager(base_dir=tmp_path)
        other_pid = os.getpid() + 1
        lock_path = m._lock_path("session_1")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text(str(other_pid), encoding="utf-8")
        # Pretend that PID is alive.
        monkeypatch.setattr(m, "_is_pid_alive", lambda pid: True)
        acquired, holder = m.acquire_session_lock("session_1")
        assert acquired is False
        assert holder == other_pid

    def test_release_removes_own_lock(self, tmp_path):
        m = SessionManager(base_dir=tmp_path)
        m.acquire_session_lock("session_1")
        assert m._lock_path("session_1").exists()
        m.release_session_lock("session_1")
        assert not m._lock_path("session_1").exists()

    def test_release_noop_when_not_holder(self, tmp_path):
        """release does not remove a lock held by another PID."""
        m = SessionManager(base_dir=tmp_path)
        lock_path = m._lock_path("session_1")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text("99999999", encoding="utf-8")  # not our PID
        m.release_session_lock("session_1")
        assert lock_path.exists()

    def test_corrupt_lock_file_treated_as_stale(self, tmp_path):
        """A malformed lock file is reclaimed (fail-open)."""
        m = SessionManager(base_dir=tmp_path)
        lock_path = m._lock_path("session_1")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text("not-a-number", encoding="utf-8")
        acquired, holder = m.acquire_session_lock("session_1")
        assert acquired is True
        assert holder is None
