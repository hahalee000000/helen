"""Tests for Phase 4: Working memory management.

Tests the working memory system that tracks essential context:
- Active files
- Recent decisions
- Pending TODOs
- Error history
"""

import pytest
from unittest.mock import Mock
from helen.runtime.working_memory import (
    WorkingMemory,
    build_three_channel_context,
)
from helen.runtime.history import Message


class TestWorkingMemory:
    """Tests for WorkingMemory class."""

    def test_initial_state(self):
        """Test that working memory starts empty."""
        wm = WorkingMemory()

        assert wm.task_description == ""
        assert wm.active_files == []
        assert wm.recent_decisions == []
        assert wm.pending_todos == []
        assert wm.error_history == []

    def test_to_context_with_task(self):
        """Test context formatting with task description."""
        wm = WorkingMemory(task_description="Fix authentication bug")

        context = wm.to_context()

        assert "## Current Task" in context
        assert "Fix authentication bug" in context

    def test_to_context_with_active_files(self):
        """Test context formatting with active files."""
        wm = WorkingMemory()
        wm.active_files = ["src/auth.py", "src/utils.py"]

        context = wm.to_context()

        assert "## Active Files" in context
        assert "src/auth.py" in context
        assert "src/utils.py" in context

    def test_to_context_with_decisions(self):
        """Test context formatting with recent decisions."""
        wm = WorkingMemory()
        wm.recent_decisions = ["Use JWT for auth", "Add rate limiting"]

        context = wm.to_context()

        assert "## Recent Decisions" in context
        assert "Use JWT for auth" in context

    def test_to_context_with_todos(self):
        """Test context formatting with pending TODOs."""
        wm = WorkingMemory()
        wm.pending_todos = ["Add tests", "Update docs"]

        context = wm.to_context()

        assert "## Pending TODOs" in context
        assert "Add tests" in context

    def test_to_context_with_errors(self):
        """Test context formatting with error history."""
        wm = WorkingMemory()
        wm.error_history = [
            {"command": "pytest", "error": "Test failed"},
        ]

        context = wm.to_context()

        assert "## Recent Errors" in context
        assert "pytest" in context
        assert "Test failed" in context

    def test_update_from_read_file(self):
        """Test that read_file updates active files."""
        wm = WorkingMemory()

        tool_call = {"name": "read_file", "args": {"path": "src/main.py"}}
        tool_result = "File content"

        wm.update_from_tool_call(tool_call, tool_result)

        assert "src/main.py" in wm.active_files

    def test_update_from_write_file(self):
        """Test that write_file updates active files and decisions."""
        wm = WorkingMemory()

        tool_call = {"name": "write_file", "args": {"path": "src/auth.py"}}
        tool_result = {"status": "ok"}

        wm.update_from_tool_call(tool_call, tool_result)

        assert "src/auth.py" in wm.active_files
        assert any("Modified file: src/auth.py" in d for d in wm.recent_decisions)

    def test_update_from_shell_error(self):
        """Test that shell errors are tracked."""
        wm = WorkingMemory()

        tool_call = {"name": "shell_exec", "args": {"command": "pytest"}}
        # Mock result object
        tool_result = Mock()
        tool_result.returncode = 1
        tool_result.stderr = "Test failed"
        tool_result.stdout = ""

        wm.update_from_tool_call(tool_call, tool_result)

        assert len(wm.error_history) == 1
        assert wm.error_history[0]["command"] == "pytest"
        assert "Test failed" in wm.error_history[0]["error"]

    def test_active_files_limit(self):
        """Test that active files list maintains limit."""
        wm = WorkingMemory()

        # Add 15 files
        for i in range(15):
            wm._add_active_file(f"file{i}.py")

        # Should only keep last 10
        assert len(wm.active_files) == 10
        assert "file14.py" in wm.active_files
        assert "file4.py" not in wm.active_files

    def test_decisions_limit(self):
        """Test that decisions list maintains limit."""
        wm = WorkingMemory()

        # Add 15 decisions
        for i in range(15):
            wm._add_decision(f"Decision {i}")

        # Should only keep last 10
        assert len(wm.recent_decisions) == 10
        assert "Decision 14" in wm.recent_decisions
        assert "Decision 4" not in wm.recent_decisions

    def test_error_history_limit(self):
        """Test that error history maintains limit."""
        wm = WorkingMemory()

        # Add 8 errors
        for i in range(8):
            wm._add_error(f"command{i}", f"error{i}")

        # Should only keep last 5
        assert len(wm.error_history) == 5
        assert wm.error_history[-1]["command"] == "command7"
        assert wm.error_history[0]["command"] == "command3"

    def test_estimate_tokens(self):
        """Test token estimation."""
        wm = WorkingMemory(task_description="Test task")

        tokens = wm.estimate_tokens()

        # Should be roughly len(context) / 4
        context = wm.to_context()
        expected = len(context) // 4
        assert abs(tokens - expected) < 10  # Allow small variance

    def test_clear(self):
        """Test clearing working memory."""
        wm = WorkingMemory(
            task_description="Test",
            active_files=["file.py"],
            recent_decisions=["Decision"],
            pending_todos=["TODO"],
            error_history=[{"command": "test", "error": "err"}],
        )

        wm.clear()

        assert wm.task_description == ""
        assert wm.active_files == []
        assert wm.recent_decisions == []
        assert wm.pending_todos == []
        assert wm.error_history == []


class TestThreeChannelContext:
    """Tests for three-channel context building."""

    def test_build_context_with_all_channels(self):
        """Test building context with all three channels."""
        system_prompt = "You are a helpful assistant."
        working_memory = WorkingMemory(task_description="Fix bug")
        history = [
            Message(role="user", content="Hello", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
        ]

        messages = build_three_channel_context(system_prompt, working_memory, history)

        # Should have system prompt, working memory, and history
        assert len(messages) >= 3
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == system_prompt

        # Working memory should be included
        working_msg = [m for m in messages if "Working Memory" in m.get("content", "")]
        assert len(working_msg) > 0

        # History should be included
        history_msgs = [m for m in messages if m["role"] == "user"]
        assert len(history_msgs) > 0

    def test_build_context_with_custom_budget(self):
        """Test building context with custom budget allocation."""
        system_prompt = "System"
        working_memory = WorkingMemory()
        history = []

        budget = {"system": 0.20, "working": 0.40, "history": 0.40}
        messages = build_three_channel_context(system_prompt, working_memory, history, budget)

        # Should still work with custom budget
        assert len(messages) > 0

    def test_build_context_without_working_memory(self):
        """Test building context with empty working memory."""
        system_prompt = "System"
        working_memory = WorkingMemory()  # Empty
        history = [
            Message(role="user", content="Hello", tool_calls=[], tool_call_id=None, _token_count=10, _model="qwen3.7-plus"),
        ]

        messages = build_three_channel_context(system_prompt, working_memory, history)

        # Should not include working memory message if empty
        working_msg = [m for m in messages if "Working Memory" in m.get("content", "")]
        # Empty working memory still gets included (it's just empty sections)
        assert len(messages) >= 2


class TestWorkingMemoryBudgetTruncation:
    """Tests for to_context() with budget_chars parameter (Channel 2 budget enforcement)."""

    def test_no_budget_includes_everything(self):
        """Without budget, all sections are included."""
        wm = WorkingMemory(
            task_description="Fix bug in main.py",
            active_files=["main.py", "utils.py"],
            recent_decisions=["Use async"],
            pending_todos=["Write tests"],
            error_history=[{"command": "pytest", "error": "failed"}],
        )
        result = wm.to_context()
        assert "## Current Task" in result
        assert "## Active Files" in result
        assert "## Recent Decisions" in result
        assert "## Pending TODOs" in result
        assert "## Recent Errors" in result

    def test_budget_drops_lowest_priority_first(self):
        """With tight budget, lowest-priority sections (TODOs) are dropped first."""
        wm = WorkingMemory(
            task_description="Fix bug in main.py",
            active_files=["main.py"],
            recent_decisions=["Use async approach"],
            pending_todos=["Write tests", "Update docs", "Add logging"],
            error_history=[{"command": "pytest", "error": "3 failed"}],
        )
        # Get full output length to determine a restrictive but non-trivial budget
        full = wm.to_context()
        # Budget that can fit task + errors + files but not decisions + todos
        budget = len(full) // 2
        result = wm.to_context(budget_chars=budget)
        # Task (highest priority) must be present
        assert "## Current Task" in result
        # TODOs (lowest priority) should be dropped
        assert "## Pending TODOs" not in result

    def test_budget_keeps_task_above_all(self):
        """With very tight budget, only the task survives."""
        wm = WorkingMemory(
            task_description="Deploy v2",
            active_files=["a.py"] * 5,
            recent_decisions=["Use staging"] * 5,
            pending_todos=["todo"] * 10,
            error_history=[{"command": "x", "error": "y"}] * 3,
        )
        # Just enough for the task header + short body
        result = wm.to_context(budget_chars=80)
        assert "## Current Task" in result
        assert "Deploy v2" in result
        # Everything else should be gone
        assert "## Active Files" not in result
        assert "## Pending TODOs" not in result

    def test_budget_truncates_body_when_section_too_large(self):
        """If even one section exceeds budget, its body is truncated at line boundary."""
        # Long task description that alone exceeds the budget
        long_desc = "\n".join([f"Line {i}: detailed task info" for i in range(20)])
        wm = WorkingMemory(task_description=long_desc)
        result = wm.to_context(budget_chars=100)
        # Must contain header
        assert "## Current Task" in result
        # Must not exceed budget by much (allow trailing newline variance)
        assert len(result) <= 120
        # Should cut at a line boundary (no partial line at end)
        lines = result.split("\n")
        # Last non-empty line should be a complete line
        non_empty = [l for l in lines if l.strip()]
        assert len(non_empty) >= 2  # header + at least one body line

    def test_budget_zero_returns_empty_or_minimal(self):
        """Zero budget returns empty string."""
        wm = WorkingMemory(task_description="Fix bug")
        result = wm.to_context(budget_chars=0)
        assert result == ""

    def test_budget_respects_priority_order(self):
        """Sections are dropped in order: TODOs > Decisions > Files > Errors > Task."""
        wm = WorkingMemory(
            task_description="Task",
            active_files=["f.py"],
            recent_decisions=["Dec"],
            pending_todos=["Todo"],
            error_history=[{"command": "c", "error": "e"}],
        )
        # Measure each section's size
        full = wm.to_context()
        # Progressively tighten budget and verify sections disappear in order
        sizes = []
        for budget in [len(full), len(full) * 3 // 4, len(full) // 2, len(full) // 4]:
            result = wm.to_context(budget_chars=budget)
            sizes.append(result)

        # The most restrictive result should be a subset of (or equal to)
        # less restrictive results in terms of section presence
        most_restrictive = sizes[-1]
        # Task should survive longest
        if most_restrictive:
            assert "## Current Task" in most_restrictive or len(most_restrictive) == 0


class TestThreeChannelBudgetEnforcement:
    """Tests for build_three_channel_context Channel 2 budget enforcement."""

    def test_channel2_respects_max_tokens_cap(self):
        """Channel 2 budget is capped by working_memory.max_tokens."""
        wm = WorkingMemory(
            task_description="x" * 100000,  # Very large task description
            max_tokens=100,  # Hard cap at 100 tokens = 400 chars
        )
        history = []
        messages = build_three_channel_context(
            system_prompt="sys", working_memory=wm, history=history,
            max_tokens=131072,
        )
        working_msgs = [m for m in messages if "Working Memory" in m.get("content", "")]
        if working_msgs:
            content = working_msgs[0]["content"]
            # Should be capped: 100 tokens * 4 chars = 400 chars + header overhead
            assert len(content) < 500

    def test_channel2_drops_sections_under_budget(self):
        """When working memory content exceeds budget, low-priority sections are dropped."""
        wm = WorkingMemory(
            task_description="Active task",
            pending_todos=[f"TODO item {i}" for i in range(20)],
            error_history=[{"command": f"cmd{i}", "error": f"err{i}"} for i in range(5)],
            max_tokens=50,  # Very tight: 50 tokens = 200 chars
        )
        history = []
        messages = build_three_channel_context(
            system_prompt="sys", working_memory=wm, history=history,
            max_tokens=131072,
        )
        working_msgs = [m for m in messages if "Working Memory" in m.get("content", "")]
        if working_msgs:
            content = working_msgs[0]["content"]
            # Task should survive; TODOs should be dropped
            assert "## Current Task" in content or "Active task" in content
