"""Integration tests for /goal command in WebUI.

Tests the goal handler integration with chat router.
"""
import os
import unittest
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from helen.agent.webui.backend.app.goal_handler import (
    parse_goal_status,
    goal_appears_complete,
    build_goal_prompt,
    build_continuation_prompt,
    DEFAULT_MAX_ITERATIONS,
)


class TestGoalCommandIntegration(unittest.TestCase):
    """Test /goal command integration."""

    def setUp(self):
        """Set language to Chinese for tests that use Chinese content."""
        os.environ["HELEN_WEBUI_LANG"] = "zh"

    def tearDown(self):
        """Clean up environment variable."""
        os.environ.pop("HELEN_WEBUI_LANG", None)

    def test_goal_prompt_includes_completion_instruction(self):
        """Initial goal prompt instructs LLM to use completion markers."""
        prompt = build_goal_prompt("写一个计算器")
        self.assertIn("[GOAL_COMPLETE]", prompt)
        self.assertIn("[GOAL_IN_PROGRESS]", prompt)
        self.assertIn("写一个计算器", prompt)

    def test_continuation_prompt_preserves_goal(self):
        """Continuation prompt preserves original goal and adds progress."""
        goal = "实现 HTTP 服务器"
        last_response = "已完成路由部分。\n\n[GOAL_IN_PROGRESS] 还需要实现错误处理。"

        prompt = build_continuation_prompt(goal, last_response)

        # Should include original goal
        self.assertIn(goal, prompt)
        # Should include last progress
        self.assertIn("路由部分", prompt)
        # Should instruct to continue
        self.assertIn("继续工作", prompt)
        # Should remind about markers
        self.assertIn("[GOAL_COMPLETE]", prompt)
        self.assertIn("[GOAL_IN_PROGRESS]", prompt)

    def test_goal_completion_detection_complete(self):
        """Detect [GOAL_COMPLETE] marker correctly."""
        response = """
        我已经完成了所有任务。

        [GOAL_COMPLETE] 最终总结：HTTP 服务器已实现，包含路由和测试。
        """
        self.assertTrue(goal_appears_complete(response))
        status = parse_goal_status(response)
        self.assertEqual(status["status"], "complete")
        self.assertIn("HTTP 服务器", status["summary"])

    def test_goal_completion_detection_in_progress(self):
        """Detect [GOAL_IN_PROGRESS] marker correctly."""
        response = """
        已完成路由部分。

        [GOAL_IN_PROGRESS] 还需要做什么：实现错误处理和测试。
        """
        self.assertFalse(goal_appears_complete(response))
        status = parse_goal_status(response)
        self.assertEqual(status["status"], "in_progress")
        self.assertIn("错误处理", status["summary"])

    def test_goal_completion_fallback_heuristic(self):
        """Fallback to heuristic when no marker present."""
        # Strong completion markers
        self.assertTrue(goal_appears_complete("目标已完成"))
        self.assertTrue(goal_appears_complete("task completed successfully"))

        # No completion markers
        self.assertFalse(goal_appears_complete("我正在处理任务"))
        self.assertFalse(goal_appears_complete("继续工作中"))

    def test_default_max_iterations(self):
        """Default max iterations is 10."""
        self.assertEqual(DEFAULT_MAX_ITERATIONS, 10)


class TestGoalCommandFlow(unittest.TestCase):
    """Test the /goal command flow logic."""

    def test_goal_command_parsing(self):
        """Parse /goal command from user message."""
        message = "/goal 写一个 Python 计算器"

        # Extract goal text (simulating chat.py logic)
        self.assertTrue(message.startswith("/goal "))
        goal_text = message[6:].strip()
        self.assertEqual(goal_text, "写一个 Python 计算器")

    def test_goal_command_empty_args(self):
        """Handle /goal without arguments."""
        message = "/goal"

        # Should detect missing arguments
        self.assertTrue(message.startswith("/goal"))
        goal_text = message[5:].strip() if len(message) > 5 else ""
        self.assertEqual(goal_text, "")

    def test_goal_iteration_tracking(self):
        """Track goal iterations correctly."""
        max_iterations = DEFAULT_MAX_ITERATIONS
        iteration = 0

        # Simulate iteration loop
        while iteration < max_iterations:
            iteration += 1
            # In real code, would check goal_appears_complete() here
            if iteration == 3:
                break  # Simulate goal completion on iteration 3

        self.assertEqual(iteration, 3)


class TestGoalHandlerEdgeCases(unittest.TestCase):
    """Test edge cases in goal handler."""

    def test_empty_response(self):
        """Handle empty response gracefully."""
        self.assertFalse(goal_appears_complete(""))
        status = parse_goal_status("")
        self.assertEqual(status["status"], "unknown")

    def test_response_without_markers(self):
        """Handle response without any markers."""
        response = "这是一段普通的回复，没有任何标记。"
        self.assertFalse(goal_appears_complete(response))
        status = parse_goal_status(response)
        self.assertEqual(status["status"], "unknown")

    def test_multiple_markers(self):
        """Handle response with multiple markers (use first one)."""
        response = """
        [GOAL_IN_PROGRESS] 还需要做什么：测试

        但是实际上...

        [GOAL_COMPLETE] 最终总结：已完成
        """
        # Should detect the first marker
        status = parse_goal_status(response)
        # parse_goal_status checks complete first, so it should find complete
        self.assertEqual(status["status"], "complete")

    def test_case_insensitive_markers(self):
        """Markers are case-insensitive."""
        response1 = "[goal_complete] done"
        response2 = "[GOAL_COMPLETE] done"
        response3 = "[Goal_Complete] done"

        # All should be detected as complete
        self.assertEqual(parse_goal_status(response1)["status"], "complete")
        self.assertEqual(parse_goal_status(response2)["status"], "complete")
        self.assertEqual(parse_goal_status(response3)["status"], "complete")

    def test_long_response_truncation(self):
        """Long responses are truncated in continuation prompt."""
        goal = "测试目标"
        long_response = "A" * 2000  # Very long response

        prompt = build_continuation_prompt(goal, long_response)

        # Prompt should not be excessively long
        self.assertLess(len(prompt), 2000)
        # But should still include goal
        self.assertIn(goal, prompt)


if __name__ == "__main__":
    unittest.main()
