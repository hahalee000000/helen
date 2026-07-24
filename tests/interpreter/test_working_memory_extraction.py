"""Tests for v1.25 system prompt-based working memory extraction.

Validates the ``<working_memory>`` block parsing and the
``AgentContextManager.update_from_llm_summary`` merge logic.
"""

import pytest

from helen.interpreter import Interpreter
from helen.interpreter.agent_context import AgentContextManager


# ---------------------------------------------------------------------------
# _extract_working_memory_update
# ---------------------------------------------------------------------------

def _make_interpreter() -> Interpreter:
    """Build a bare Interpreter (no agent context) for extraction tests."""
    return Interpreter()


def test_extract_basic():
    """A well-formed block with all four fields is fully parsed."""
    interp = _make_interpreter()
    response = (
        "I've completed the task.\n\n"
        "<working_memory>\n"
        "active_files: [src/main.py, tests/test_main.py]\n"
        "decisions: [Use async/await for better performance]\n"
        "todos: [Add error handling, Write documentation]\n"
        "errors: [Fixed null pointer exception in line 42]\n"
        "</working_memory>"
    )
    result = interp._extract_working_memory_update(response)

    assert result is not None
    assert result["active_files"] == ["src/main.py", "tests/test_main.py"]
    assert result["decisions"] == ["Use async/await for better performance"]
    assert result["todos"] == ["Add error handling", "Write documentation"]
    assert result["errors"] == ["Fixed null pointer exception in line 42"]


def test_extract_missing_block_returns_none():
    """No <working_memory> block -> None (no crash)."""
    interp = _make_interpreter()
    result = interp._extract_working_memory_update("Just a normal response.")
    assert result is None


def test_extract_empty_response_returns_none():
    interp = _make_interpreter()
    assert interp._extract_working_memory_update("") is None


def test_extract_partial_fields():
    """Only some fields present -> only those keys appear."""
    interp = _make_interpreter()
    response = (
        "<working_memory>\n"
        "active_files: [src/auth.py]\n"
        "todos: [Add 2FA]\n"
        "</working_memory>"
    )
    result = interp._extract_working_memory_update(response)

    assert result is not None
    assert result["active_files"] == ["src/auth.py"]
    assert result["todos"] == ["Add 2FA"]
    assert "decisions" not in result
    assert "errors" not in result


def test_extract_chinese_content():
    """Chinese items inside the arrays are preserved verbatim."""
    interp = _make_interpreter()
    response = (
        "任务已完成。\n\n"
        "<working_memory>\n"
        "active_files: [src/认证.py, tests/test_认证.py]\n"
        "decisions: [使用 JWT 令牌以支持跨设备登录]\n"
        "todos: [添加密码强度验证, 实现双因素认证]\n"
        "</working_memory>"
    )
    result = interp._extract_working_memory_update(response)

    assert result is not None
    assert "src/认证.py" in result["active_files"]
    assert "使用 JWT 令牌以支持跨设备登录" in result["decisions"]


def test_extract_case_insensitive_tag():
    """Tag name matching is case-insensitive."""
    interp = _make_interpreter()
    response = (
        "<Working_Memory>\n"
        "todos: [task one]\n"
        "</Working_Memory>"
    )
    result = interp._extract_working_memory_update(response)
    assert result is not None
    assert result["todos"] == ["task one"]


def test_extract_quoted_items():
    """Items wrapped in quotes are unquoted."""
    interp = _make_interpreter()
    response = (
        '<working_memory>\n'
        'active_files: ["src/a.py", \'tests/b.py\']\n'
        '</working_memory>'
    )
    result = interp._extract_working_memory_update(response)
    assert result["active_files"] == ["src/a.py", "tests/b.py"]


def test_extract_empty_arrays_yield_no_key():
    """An empty array produces no key (filtered out)."""
    interp = _make_interpreter()
    response = (
        "<working_memory>\n"
        "active_files: []\n"
        "todos: [real task]\n"
        "</working_memory>"
    )
    result = interp._extract_working_memory_update(response)
    assert "active_files" not in result
    assert result["todos"] == ["real task"]


# ---------------------------------------------------------------------------
# AgentContextManager.update_from_llm_summary
# ---------------------------------------------------------------------------

def _make_ctx(enabled: bool = True) -> AgentContextManager:
    return AgentContextManager(
        working_memory_enabled=enabled,
        working_memory_tokens=5000,
    )


def test_update_all_fields():
    ctx = _make_ctx()
    ctx.update_from_llm_summary({
        "active_files": ["src/main.py"],
        "decisions": ["Use JWT"],
        "todos": ["Add tests"],
        "errors": ["Fixed null pointer"],
    })
    wm = ctx.working_memory
    assert wm.active_files == ["src/main.py"]
    assert "Use JWT" in wm.recent_decisions
    assert "Add tests" in wm.pending_todos
    assert len(wm.error_history) == 1


def test_update_active_files_replaces():
    """active_files reflects current state -> replace, not append."""
    ctx = _make_ctx()
    ctx.update_from_llm_summary({"active_files": ["a.py", "b.py"]})
    ctx.update_from_llm_summary({"active_files": ["c.py"]})
    assert ctx.working_memory.active_files == ["c.py"]


def test_update_todos_replaces():
    """todos reflect current task list -> replace, not append."""
    ctx = _make_ctx()
    ctx.update_from_llm_summary({"todos": ["old task"]})
    ctx.update_from_llm_summary({"todos": ["new task"]})
    assert ctx.working_memory.pending_todos == ["new task"]


def test_update_decisions_appends():
    """Decisions are historical -> append (capped to last 10)."""
    ctx = _make_ctx()
    ctx.update_from_llm_summary({"decisions": ["first"]})
    ctx.update_from_llm_summary({"decisions": ["second"]})
    assert ctx.working_memory.recent_decisions == ["first", "second"]


def test_update_decisions_capped_at_10():
    ctx = _make_ctx()
    decisions = [f"decision {i}" for i in range(15)]
    ctx.update_from_llm_summary({"decisions": decisions})
    assert len(ctx.working_memory.recent_decisions) == 10
    assert ctx.working_memory.recent_decisions[-1] == "decision 14"


def test_update_errors_appends_capped_at_5():
    ctx = _make_ctx()
    errors = [f"error {i}" for i in range(8)]
    ctx.update_from_llm_summary({"errors": errors})
    assert len(ctx.working_memory.error_history) == 5
    # Most recent 5 retained
    assert ctx.working_memory.error_history[-1]["error"] == "error 7"


def test_update_disabled_noop():
    """When working_memory_enabled is False, update is a no-op."""
    ctx = _make_ctx(enabled=False)
    ctx.update_from_llm_summary({"active_files": ["should_not_appear.py"]})
    assert ctx.working_memory.active_files == []


def test_update_empty_summary_noop():
    ctx = _make_ctx()
    ctx.update_from_llm_summary({})
    assert ctx.working_memory.active_files == []
    assert ctx.working_memory.recent_decisions == []


def test_update_partial_summary():
    """Only provided keys are updated; others untouched."""
    ctx = _make_ctx()
    ctx.update_from_llm_summary({"active_files": ["a.py"], "todos": ["t1"]})
    ctx.update_from_llm_summary({"todos": ["t2"]})
    # active_files preserved (not in second update)
    assert ctx.working_memory.active_files == ["a.py"]
    # todos replaced
    assert ctx.working_memory.pending_todos == ["t2"]


# ---------------------------------------------------------------------------
# _build_working_memory_instructions
# ---------------------------------------------------------------------------

def test_instructions_present_when_enabled():
    interp = _make_interpreter()
    instructions = interp._build_working_memory_instructions()
    assert instructions
    assert "<working_memory>" in instructions
    assert "active_files" in instructions


def test_instructions_absent_without_agent_context():
    """With no _agent_context, instructions are included by default (enabled)."""
    interp = _make_interpreter()
    # Interpreter may or may not have an _agent_context; either way, with no
    # explicit disable, instructions should be present.
    instructions = interp._build_working_memory_instructions()
    assert instructions  # default enabled


def test_instructions_absent_when_disabled():
    """When working_memory_enabled is False on the agent context, no instructions."""
    interp = _make_interpreter()
    ctx = _make_ctx(enabled=False)
    interp._agent_context = ctx
    instructions = interp._build_working_memory_instructions()
    assert instructions == ""


# ---------------------------------------------------------------------------
# Integration: extract -> update round-trip
# ---------------------------------------------------------------------------

def test_round_trip_extract_then_update():
    """Extracting from a response then updating the store matches expectations."""
    interp = _make_interpreter()
    ctx = _make_ctx()
    interp._agent_context = ctx  # wire up so _apply_working_memory_update finds it

    response = (
        "Done.\n\n"
        "<working_memory>\n"
        "active_files: [src/x.py]\n"
        "decisions: [pick approach A]\n"
        "todos: [write tests]\n"
        "</working_memory>"
    )
    interp._apply_working_memory_update(response)

    wm = ctx.working_memory
    assert wm.active_files == ["src/x.py"]
    assert "pick approach A" in wm.recent_decisions
    assert "write tests" in wm.pending_todos


def test_round_trip_no_block_no_change():
    interp = _make_interpreter()
    ctx = _make_ctx()
    interp._agent_context = ctx

    interp._apply_working_memory_update("no block here")
    assert ctx.working_memory.active_files == []
    assert ctx.working_memory.recent_decisions == []


def test_apply_respects_disabled_flag():
    interp = _make_interpreter()
    ctx = _make_ctx(enabled=False)
    interp._agent_context = ctx

    response = (
        "<working_memory>\n"
        "active_files: [should_not_appear.py]\n"
        "</working_memory>"
    )
    interp._apply_working_memory_update(response)
    assert ctx.working_memory.active_files == []
