"""Tests for tool call loop detection."""

import pytest
from helen.runtime.loop_detector import (
    LoopDetectionResult,
    ToolCallLoopDetector,
    ToolCallSignature,
)


class TestToolCallSignature:
    """Tests for ToolCallSignature normalization."""

    def test_basic_signature(self):
        tc = {
            "function": {
                "name": "shell_exec",
                "arguments": '{"command": "ls"}',
            }
        }
        sig = ToolCallSignature.from_tool_call(tc)
        assert sig.name == "shell_exec"
        assert '"command"' in sig.args_key
        assert "ls" in sig.args_key

    def test_json_key_ordering(self):
        """Different JSON key orders should produce same signature."""
        tc1 = {"function": {"name": "foo", "arguments": '{"a": 1, "b": 2}'}}
        tc2 = {"function": {"name": "foo", "arguments": '{"b": 2, "a": 1}'}}

        sig1 = ToolCallSignature.from_tool_call(tc1)
        sig2 = ToolCallSignature.from_tool_call(tc2)

        assert sig1 == sig2
        assert hash(sig1) == hash(sig2)

    def test_whitespace_normalization(self):
        """Whitespace differences in JSON should normalize."""
        tc1 = {"function": {"name": "foo", "arguments": '{"a":1}'}}
        tc2 = {"function": {"name": "foo", "arguments": '{ "a" : 1 }'}}

        sig1 = ToolCallSignature.from_tool_call(tc1)
        sig2 = ToolCallSignature.from_tool_call(tc2)

        # Both should parse to same normalized form
        assert sig1.args_key == sig2.args_key

    def test_invalid_json_fallback(self):
        """Invalid JSON should fall back to raw string comparison."""
        tc = {"function": {"name": "foo", "arguments": "not valid json"}}
        sig = ToolCallSignature.from_tool_call(tc)
        assert sig.name == "foo"
        assert "not valid json" in sig.args_key


class TestToolCallLoopDetector:
    """Tests for loop detection logic."""

    def test_no_loop_short_history(self):
        """No loop detected with few calls."""
        detector = ToolCallLoopDetector(exact_repeat_threshold=3)

        tc = {"function": {"name": "shell_exec", "arguments": '{"command": "ls"}'}}
        detector.record([tc])
        detector.record([tc])

        result = detector.check()
        assert not result.is_looping

    def test_exact_repeat_detection(self):
        """Detect when same call repeats N times."""
        detector = ToolCallLoopDetector(exact_repeat_threshold=3)

        tc = {"function": {"name": "shell_exec", "arguments": '{"command": "ls"}'}}

        detector.record([tc])
        detector.record([tc])
        result = detector.check()
        assert not result.is_looping

        detector.record([tc])  # 3rd time
        result = detector.check()
        assert result.is_looping
        assert result.loop_type == "exact"
        assert result.repeated_count == 3
        assert result.hint_message is not None
        assert "shell_exec" in result.hint_message

    def test_different_calls_no_loop(self):
        """Alternating different calls shouldn't trigger exact loop."""
        detector = ToolCallLoopDetector(exact_repeat_threshold=3)

        tc1 = {"function": {"name": "shell_exec", "arguments": '{"command": "ls"}'}}
        tc2 = {"function": {"name": "shell_exec", "arguments": '{"command": "pwd"}'}}

        detector.record([tc1])
        detector.record([tc2])
        detector.record([tc1])
        detector.record([tc2])

        result = detector.check()
        assert not result.is_looping

    def test_window_pattern_detection(self):
        """Detect repeating pattern in sliding window."""
        detector = ToolCallLoopDetector(
            exact_repeat_threshold=5,  # High threshold
            window_size=10,
            window_repeat_threshold=5,
        )

        # Repeat the same call 5 times with occasional different calls
        repeated = {"function": {"name": "ls_cmd", "arguments": '{"command": "ls"}'}}
        other = {"function": {"name": "pwd_cmd", "arguments": '{"command": "pwd"}'}}

        # Pattern: ls, ls, pwd, ls, ls, pwd, ls, ls — 6 ls in 8 calls
        for _ in range(3):
            detector.record([repeated])
            detector.record([repeated])
            detector.record([other])
        detector.record([repeated])

        result = detector.check()
        assert result.is_looping
        assert result.loop_type == "pattern"
        assert result.repeated_count >= 5

    def test_reset_clears_history(self):
        """Reset should clear detection state."""
        detector = ToolCallLoopDetector(exact_repeat_threshold=2)

        tc = {"function": {"name": "test", "arguments": '{}'}}
        detector.record([tc])
        detector.record([tc])

        assert detector.check().is_looping

        detector.reset()
        assert not detector.check().is_looping

    def test_loop_detection_result_bool(self):
        """LoopDetectionResult should be truthy when looping."""
        assert not LoopDetectionResult(is_looping=False)
        assert LoopDetectionResult(is_looping=True)

    def test_hint_message_content(self):
        """Hint message should contain useful debugging info."""
        detector = ToolCallLoopDetector(exact_repeat_threshold=2)

        tc = {"function": {"name": "read_file", "arguments": '{"path": "/etc/passwd"}'}}
        detector.record([tc])
        detector.record([tc])

        result = detector.check()
        assert result.is_looping
        assert result.hint_message
        assert "read_file" in result.hint_message
        assert "Loop Detection" in result.hint_message
        assert "same arguments" in result.hint_message or "similar arguments" in result.hint_message

    def test_parallel_tool_calls_recorded(self):
        """Multiple tool calls in one turn should all be recorded."""
        detector = ToolCallLoopDetector(exact_repeat_threshold=2)

        tc1 = {"function": {"name": "ls", "arguments": '{}'}}
        tc2 = {"function": {"name": "pwd", "arguments": '{}'}}

        # One turn with 2 calls
        detector.record([tc1, tc2])
        detector.record([tc1, tc2])

        # History is now [ls, pwd, ls, pwd] — last 2 are [ls, pwd], not identical
        # So exact repeat won't trigger. But window pattern should with lower threshold.
        result = detector.check()
        # With default window settings (size=10, threshold=5), 4 items won't trigger
        assert not result.is_looping

        # Add one more round to hit window threshold
        detector.record([tc1, tc2])  # Now 6 items: 3 ls + 3 pwd
        result = detector.check()
        # Still not enough for default threshold=5
        assert not result.is_looping

        # Verify history was recorded correctly
        assert len(detector._history) == 6


class TestLoopDetectorIntegration:
    """Integration tests simulating real agent scenarios."""

    def test_mv_loop_scenario(self):
        """Simulate the mv command loop from the bug report."""
        detector = ToolCallLoopDetector(exact_repeat_threshold=3)

        # Agent keeps trying to mv same file (file already moved)
        mv_cmd = {
            "function": {
                "name": "shell_exec",
                "arguments": '{"command": "mv AGENT_ISOLATION_FEATURES.md wiki/rust/"}',
            }
        }

        for _ in range(3):
            detector.record([mv_cmd])

        result = detector.check()
        assert result.is_looping
        assert result.loop_type == "exact"
        assert "shell_exec" in result.hint_message

    def test_git_status_check_loop(self):
        """Simulate the ls + git status check loop."""
        detector = ToolCallLoopDetector(
            exact_repeat_threshold=5,
            window_size=10,
            window_repeat_threshold=4,
        )

        ls_cmd = {"function": {"name": "shell_exec", "arguments": '{"command": "ls wiki/rust/"}'}}
        appendix_cmd = {"function": {"name": "shell_exec", "arguments": '{"command": "ls wiki/appendix/"}'}}

        # Pattern: ls wiki/rust/, ls wiki/appendix/ repeated
        for _ in range(4):
            detector.record([ls_cmd])
            detector.record([appendix_cmd])

        result = detector.check()
        assert result.is_looping
        assert result.loop_type == "pattern"

    def test_progress_breaks_loop(self):
        """Changing arguments should break loop detection."""
        detector = ToolCallLoopDetector(exact_repeat_threshold=3)

        # First attempt
        tc1 = {"function": {"name": "shell_exec", "arguments": '{"command": "ls /dir1"}'}}
        detector.record([tc1])
        detector.record([tc1])

        # Different command — progress!
        tc2 = {"function": {"name": "shell_exec", "arguments": '{"command": "ls /dir2"}'}}
        detector.record([tc2])

        result = detector.check()
        assert not result.is_looping
