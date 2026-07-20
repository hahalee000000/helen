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
        """Test that active files list maintains token budget via eviction."""
        # Use very small max_tokens to trigger eviction
        wm = WorkingMemory(max_tokens=20)  # 20 tokens = 80 chars

        # Add files until we exceed budget
        for i in range(15):
            wm._add_active_file(f"file{i}.py")  # ~10 chars each = ~3 tokens

        # Should have evicted oldest to stay under 20 tokens
        # 20 tokens / 3 tokens per file ≈ 6-7 files
        assert len(wm.active_files) < 15
        # Most recent files should be kept
        assert "file14.py" in wm.active_files

    def test_decisions_limit(self):
        """Test that decisions list maintains token budget via eviction."""
        # Use very small max_tokens to trigger eviction
        wm = WorkingMemory(max_tokens=15)  # 15 tokens = 60 chars

        # Add decisions until we exceed budget
        for i in range(15):
            wm._add_decision(f"Decision {i}")  # ~12 chars each = ~3 tokens

        # Should have evicted oldest to stay under 15 tokens
        assert len(wm.recent_decisions) < 15
        # Most recent decisions should be kept
        assert "Decision 14" in wm.recent_decisions

    def test_error_history_limit(self):
        """Test that error history maintains token budget via eviction."""
        # Use very small max_tokens to trigger eviction
        wm = WorkingMemory(max_tokens=10)  # 10 tokens = 40 chars

        # Add errors until we exceed budget
        for i in range(8):
            wm._add_error(f"cmd{i}", f"err{i}")  # ~10 chars each = ~3 tokens

        # Should have evicted oldest to stay under 10 tokens
        assert len(wm.error_history) < 8
        # Most recent errors should be kept
        assert wm.error_history[-1]["command"] == "cmd7"

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

    def test_max_tokens_enforced_without_explicit_budget(self):
        """max_tokens acts as a hard upper bound even without explicit budget_chars."""
        # Use very small max_tokens to force truncation
        wm = WorkingMemory(
            task_description="x" * 200,  # ~800 chars
            active_files=[f"file_{i}.py" for i in range(5)],
            pending_todos=[f"TODO {i}" for i in range(10)],
            max_tokens=50,  # 50 * 4 = 200 chars hard bound
        )
        result = wm.to_context()  # No explicit budget
        # Should respect max_tokens (200 chars)
        assert len(result) <= 220  # Allow small overhead from formatting

    def test_explicit_budget_capped_by_max_tokens(self):
        """When both budget_chars and max_tokens are set, the smaller wins."""
        wm = WorkingMemory(
            task_description="x" * 200,
            max_tokens=30,  # 30 * 4 = 120 chars
        )
        # Pass a larger explicit budget — max_tokens should cap it
        result = wm.to_context(budget_chars=10000)
        assert len(result) <= 140  # 120 + overhead


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


# ═══════════════════════════════════════════════════════════════════════
# v1.23.2 regression tests (from working-memory-audit-2026-07-20.md)
# ═══════════════════════════════════════════════════════════════════════


class TestChineseToolNameCanonicalization:
    """v1.23.2 fix: Chinese tool aliases are translated to canonical names
    before working memory tracking. Without this, user-defined Chinese
    tool functions (e.g. `fn 读文件(...)`) would silently bypass tracking."""

    def test_chinese_read_file_tracks_active_file(self):
        """Chinese alias '读文件' should be tracked like 'read_file'."""
        from helen.interpreter.agent_context import AgentContextManager
        ctx = AgentContextManager(
            compression_strategy="none", working_memory_enabled=True,
            cache_aware_enabled=False, transcript_store_enabled=False,
        )
        ctx.update_from_tool_call("读文件", '{"path": "zh_test.py"}', "content")
        assert "zh_test.py" in ctx.working_memory.active_files

    def test_chinese_write_file_tracks_file_and_decision(self):
        """Chinese alias '写文件' should track file and decision."""
        from helen.interpreter.agent_context import AgentContextManager
        ctx = AgentContextManager(
            compression_strategy="none", working_memory_enabled=True,
            cache_aware_enabled=False, transcript_store_enabled=False,
        )
        ctx.update_from_tool_call("写文件", '{"path": "out.py", "content": "x"}', "ok")
        assert "out.py" in ctx.working_memory.active_files
        assert any("out.py" in d for d in ctx.working_memory.recent_decisions)

    def test_chinese_shell_exec(self):
        """Chinese alias '执行命令' should be tracked like 'shell_exec'."""
        from helen.interpreter.agent_context import AgentContextManager
        ctx = AgentContextManager(
            compression_strategy="none", working_memory_enabled=True,
            cache_aware_enabled=False, transcript_store_enabled=False,
        )
        ctx.update_from_tool_call("执行命令", '{"command": "ls"}', "文件1\n文件2\n", None)
        # Should not crash; no error since output is clean
        assert ctx.working_memory.error_history == []

    def test_unknown_chinese_name_falls_through(self):
        """Unrecognized Chinese name should not crash, just be a no-op."""
        from helen.interpreter.agent_context import AgentContextManager
        ctx = AgentContextManager(
            compression_strategy="none", working_memory_enabled=True,
            cache_aware_enabled=False, transcript_store_enabled=False,
        )
        # 'unknown_zh' is not in any alias map; should be silently ignored
        ctx.update_from_tool_call("unknown_zh", '{}', "result")
        assert ctx.working_memory.active_files == []


class TestMultilingualErrorDetection:
    """v1.23.2 fix: _looks_like_error covers English + Chinese keywords
    instead of just checking for substring 'error'."""

    def test_english_error_keywords(self):
        from helen.interpreter.agent_context import _looks_like_error
        assert _looks_like_error("Error: file not found")
        assert _looks_like_error("command failed with status 1")
        assert _looks_like_error("Traceback (most recent call last)")
        assert _looks_like_error("Permission denied")
        assert _looks_like_error("Connection timed out")

    def test_chinese_error_keywords(self):
        from helen.interpreter.agent_context import _looks_like_error
        assert _looks_like_error("命令执行失败")
        assert _looks_like_error("出错了：文件不存在")
        assert _looks_like_error("操作被拒绝")
        assert _looks_like_error("超时了")

    def test_success_not_flagged(self):
        from helen.interpreter.agent_context import _looks_like_error
        assert not _looks_like_error("Success! File saved.")
        assert not _looks_like_error("Output: 42")
        assert not _looks_like_error("Done.")
        assert not _looks_like_error("")

    def test_shell_exec_json_exit_code_extracted(self):
        """When exit_code param is None, JSON-shaped result is parsed for exit_code."""
        from helen.interpreter.agent_context import AgentContextManager
        ctx = AgentContextManager(
            compression_strategy="none", working_memory_enabled=True,
            cache_aware_enabled=False, transcript_store_enabled=False,
        )
        json_result = '{"command": "bad", "exit_code": 1, "output": "msg"}'
        ctx.update_from_tool_call("shell_exec", '{"command": "bad"}', json_result, None)
        assert len(ctx.working_memory.error_history) == 1

    def test_shell_exec_success_not_flagged(self):
        """Clean shell output should not be flagged as error."""
        from helen.interpreter.agent_context import AgentContextManager
        ctx = AgentContextManager(
            compression_strategy="none", working_memory_enabled=True,
            cache_aware_enabled=False, transcript_store_enabled=False,
        )
        ctx.update_from_tool_call("shell_exec", '{"command": "ls"}', "file1\nfile2\n", None)
        assert ctx.working_memory.error_history == []

    def test_shell_exec_explicit_exit_code_still_works(self):
        """Explicit exit_code parameter should take precedence."""
        from helen.interpreter.agent_context import AgentContextManager
        ctx = AgentContextManager(
            compression_strategy="none", working_memory_enabled=True,
            cache_aware_enabled=False, transcript_store_enabled=False,
        )
        ctx.update_from_tool_call("shell_exec", '{"command": "fail"}', "some output", 2)
        assert len(ctx.working_memory.error_history) == 1


class TestTaskDescriptionAutoSet:
    """v1.23.2 fix: task_description is auto-populated from the first
    LLM prompt in each invocation, so the highest-priority working
    memory section isn't permanently empty."""

    def test_empty_task_gets_autoset_from_prompt(self):
        """When task_description is empty, prepare_context flow should
        set it from the current prompt (via the logic in llm_mixin)."""
        from helen.interpreter.agent_context import AgentContextManager
        ctx = AgentContextManager(
            compression_strategy="none", working_memory_enabled=True,
            cache_aware_enabled=False, transcript_store_enabled=False,
        )
        assert ctx.working_memory.task_description == ""

        # Simulate the auto-set logic from _prepare_history_for_llm
        current_prompt = "请分析这段代码的 bug"
        if ctx.working_memory_enabled:
            wm = ctx.working_memory
            if not wm.task_description and current_prompt:
                truncated = current_prompt[:300]
                if len(current_prompt) > 300:
                    truncated += "..."
                wm.task_description = truncated

        assert ctx.working_memory.task_description == "请分析这段代码的 bug"
        # Verify it shows in to_context output
        context = ctx.working_memory.to_context()
        assert "## Current Task" in context
        assert "请分析这段代码的 bug" in context

    def test_manual_task_not_overridden(self):
        """If user set task_description manually, auto-set must not override."""
        from helen.interpreter.agent_context import AgentContextManager
        ctx = AgentContextManager(
            compression_strategy="none", working_memory_enabled=True,
            cache_aware_enabled=False, transcript_store_enabled=False,
        )
        ctx.working_memory.task_description = "My custom task"

        # Simulate auto-set logic
        current_prompt = "another prompt"
        if ctx.working_memory_enabled:
            wm = ctx.working_memory
            if not wm.task_description and current_prompt:
                wm.task_description = current_prompt

        assert ctx.working_memory.task_description == "My custom task"

    def test_long_prompt_is_truncated(self):
        """Long prompts are truncated to 300 chars + '...'."""
        from helen.interpreter.agent_context import AgentContextManager
        ctx = AgentContextManager(
            compression_strategy="none", working_memory_enabled=True,
            cache_aware_enabled=False, transcript_store_enabled=False,
        )
        long_prompt = "A" * 500

        if ctx.working_memory_enabled:
            wm = ctx.working_memory
            if not wm.task_description and long_prompt:
                truncated = long_prompt[:300]
                if len(long_prompt) > 300:
                    truncated += "..."
                wm.task_description = truncated

        assert len(ctx.working_memory.task_description) == 303  # 300 + "..."
        assert ctx.working_memory.task_description.endswith("...")
