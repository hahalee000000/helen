"""Tests for goal_handler module."""

import pytest
from helen.agent.webui.backend.app.goal_handler import (
    parse_goal_status,
    goal_appears_complete,
    build_goal_prompt,
    build_continuation_prompt,
    GOAL_SYSTEM_PROMPT_INJECTION,
)


class TestParseGoalStatus:
    """Test goal status marker parsing."""

    def test_complete_marker_with_summary(self):
        """Parse [GOAL_COMPLETE] with summary text."""
        response = """
        我完成了所有任务。

        [GOAL_COMPLETE] 最终总结：已实现 HTTP 服务器，包含路由和测试。
        """
        result = parse_goal_status(response)
        assert result["status"] == "complete"
        assert "HTTP 服务器" in result["summary"]

    def test_complete_marker_without_label(self):
        """Parse [GOAL_COMPLETE] without '最终总结' label."""
        response = """
        完成了。

        [GOAL_COMPLETE] 所有功能已实现。
        """
        result = parse_goal_status(response)
        assert result["status"] == "complete"
        assert "所有功能" in result["summary"]

    def test_in_progress_marker_with_remaining(self):
        """Parse [GOAL_IN_PROGRESS] with remaining work."""
        response = """
        已完成路由部分。

        [GOAL_IN_PROGRESS] 还需要做什么：实现错误处理和测试。
        """
        result = parse_goal_status(response)
        assert result["status"] == "in_progress"
        assert "错误处理" in result["summary"]

    def test_in_progress_marker_without_label(self):
        """Parse [GOAL_IN_PROGRESS] without '还需要做什么' label."""
        response = """
        继续工作。

        [GOAL_IN_PROGRESS] 还剩测试部分未完成。
        """
        result = parse_goal_status(response)
        assert result["status"] == "in_progress"
        assert "测试" in result["summary"]

    def test_no_marker(self):
        """Response without any goal marker."""
        response = "我正在处理任务。"
        result = parse_goal_status(response)
        assert result["status"] == "unknown"
        assert result["summary"] == ""

    def test_case_insensitive(self):
        """Markers should be case-insensitive."""
        response = "[goal_complete] Done."
        result = parse_goal_status(response)
        assert result["status"] == "complete"


class TestGoalAppearsComplete:
    """Test goal completion detection."""

    def test_complete_marker(self):
        """[GOAL_COMPLETE] marker indicates completion."""
        response = "完成。\n\n[GOAL_COMPLETE] 全部完成。"
        assert goal_appears_complete(response) is True

    def test_in_progress_marker(self):
        """[GOAL_IN_PROGRESS] marker indicates not complete."""
        response = "继续。\n\n[GOAL_IN_PROGRESS] 还需要工作。"
        assert goal_appears_complete(response) is False

    def test_heuristic_complete_chinese(self):
        """Fallback heuristic: '目标已完成' indicates completion."""
        response = "我已经完成了所有任务，目标已完成。"
        assert goal_appears_complete(response) is True

    def test_heuristic_complete_english(self):
        """Fallback heuristic: 'goal completed' indicates completion."""
        response = "All tasks done, goal completed successfully."
        assert goal_appears_complete(response) is True

    def test_heuristic_in_progress(self):
        """Response without completion markers is not complete."""
        response = "我正在处理任务，还需要一些时间。"
        assert goal_appears_complete(response) is False

    def test_marker_takes_precedence(self):
        """Explicit marker overrides heuristic."""
        # Even if text contains "完成", [GOAL_IN_PROGRESS] means not done
        response = "完成了一部分。\n\n[GOAL_IN_PROGRESS] 继续工作。"
        assert goal_appears_complete(response) is False


class TestBuildGoalPrompt:
    """Test initial goal prompt construction."""

    def test_includes_goal_text(self):
        """Prompt should include the goal text."""
        goal = "实现一个 HTTP 服务器"
        prompt = build_goal_prompt(goal)
        assert goal in prompt

    def test_includes_system_injection(self):
        """Prompt should include the goal system prompt injection."""
        prompt = build_goal_prompt("test goal")
        assert GOAL_SYSTEM_PROMPT_INJECTION in prompt

    def test_includes_completion_instruction(self):
        """Prompt should instruct LLM to mark completion."""
        prompt = build_goal_prompt("test")
        assert "[GOAL_COMPLETE]" in prompt


class TestBuildContinuationPrompt:
    """Test continuation prompt construction."""

    def test_includes_original_goal(self):
        """Continuation prompt should include the original goal."""
        goal = "实现 HTTP 服务器"
        last_response = "已完成路由部分。"
        prompt = build_continuation_prompt(goal, last_response)
        assert goal in prompt

    def test_includes_last_response_summary(self):
        """Continuation prompt should include truncated last response."""
        goal = "test"
        last_response = "A" * 1000  # Long response
        prompt = build_continuation_prompt(goal, last_response)
        # Should be truncated to ~800 chars
        assert len(prompt) < 1500

    def test_includes_continue_instruction(self):
        """Continuation prompt should instruct to continue."""
        prompt = build_continuation_prompt("goal", "last")
        assert "继续工作" in prompt or "continue" in prompt.lower()

    def test_includes_both_markers(self):
        """Continuation prompt should mention both markers."""
        prompt = build_continuation_prompt("goal", "last")
        assert "[GOAL_COMPLETE]" in prompt
        assert "[GOAL_IN_PROGRESS]" in prompt
