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
        # Use custom tool_thresholds to set low threshold for testing
        detector = ToolCallLoopDetector(
            tool_thresholds={"test_tool": 3, "default": 3}
        )

        tc = {"function": {"name": "test_tool", "arguments": '{"command": "ls"}'}}
        detector.record([tc])
        detector.record([tc])

        result = detector.check()
        assert not result.is_looping

    def test_exact_repeat_detection(self):
        """Detect when same call repeats N times."""
        # Use custom threshold for testing
        detector = ToolCallLoopDetector(
            tool_thresholds={"test_tool": 3, "default": 3}
        )

        tc = {"function": {"name": "test_tool", "arguments": '{"command": "ls"}'}}

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
        assert "test_tool" in result.hint_message

    def test_different_calls_no_loop(self):
        """Alternating different calls shouldn't trigger exact loop.

        Note: tool-name-repeat will still trigger if same tool is used repeatedly.
        This test uses different tools to avoid that.
        """
        detector = ToolCallLoopDetector(
            tool_thresholds={"tool_a": 5, "tool_b": 5, "default": 5}
        )

        tc1 = {"function": {"name": "tool_a", "arguments": '{"command": "ls"}'}}
        tc2 = {"function": {"name": "tool_b", "arguments": '{"command": "pwd"}'}}

        detector.record([tc1])
        detector.record([tc2])
        detector.record([tc1])
        detector.record([tc2])

        result = detector.check()
        assert not result.is_looping

    def test_window_pattern_detection(self):
        """Detect repeating pattern in sliding window."""
        detector = ToolCallLoopDetector(
            tool_thresholds={"ls_cmd": 15, "pwd_cmd": 15, "default": 15},
            window_size=10,
            window_repeat_threshold=3,  # Lower for testing
        )

        # Repeat the same call multiple times with occasional different calls
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
        assert result.repeated_count >= 3

    def test_reset_clears_history(self):
        """Reset should clear detection state."""
        detector = ToolCallLoopDetector(
            tool_thresholds={"test_tool": 2, "default": 2}
        )

        tc = {"function": {"name": "test_tool", "arguments": '{}'}}
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
        detector = ToolCallLoopDetector(
            tool_thresholds={"test_tool": 2, "default": 2}
        )

        tc = {"function": {"name": "test_tool", "arguments": '{"path": "/etc/passwd"}'}}
        detector.record([tc])
        detector.record([tc])

        result = detector.check()
        assert result.is_looping
        assert result.hint_message
        assert "test_tool" in result.hint_message
        assert "Loop Detection" in result.hint_message
        # v1.46.35: Informative hints don't say "same arguments" directly
        assert "called" in result.hint_message.lower() or "times" in result.hint_message.lower()

    def test_parallel_tool_calls_recorded(self):
        """Multiple tool calls in one turn should all be recorded."""
        # Use high thresholds to avoid triggering loop detection
        detector = ToolCallLoopDetector(
            tool_thresholds={"ls": 20, "pwd": 20, "default": 20},
            window_repeat_threshold=10,  # Very high threshold
        )

        tc1 = {"function": {"name": "ls", "arguments": '{}'}}
        tc2 = {"function": {"name": "pwd", "arguments": '{}'}}

        # One turn with 2 calls
        detector.record([tc1, tc2])
        detector.record([tc1, tc2])

        # History is now [ls, pwd, ls, pwd] — last 2 are [ls, pwd], not identical
        # So exact repeat won't trigger. And with high thresholds, no detection.
        result = detector.check()
        assert not result.is_looping

        # Add more rounds
        detector.record([tc1, tc2])  # Now 6 items: 3 ls + 3 pwd
        result = detector.check()
        # Still not enough for threshold=10
        assert not result.is_looping

        # Verify history was recorded correctly
        assert len(detector._history) == 6


class TestLoopDetectorIntegration:
    """Integration tests simulating real agent scenarios."""

    def test_mv_loop_scenario(self):
        """Simulate the mv command loop from the bug report.

        Note: shell_exec has a default threshold of 25, so we override it for testing.
        """
        # Override shell_exec threshold for this test
        detector = ToolCallLoopDetector(
            tool_thresholds={"shell_exec": 3, "default": 3}
        )

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
        """Simulate the ls + git status check loop.

        Note: With per-tool thresholds, we need to trigger window pattern detection.
        """
        # Use low window threshold for this test
        detector = ToolCallLoopDetector(
            tool_thresholds={"shell_exec": 50, "default": 50},  # High exact threshold
            window_size=10,
            window_repeat_threshold=4,  # Need 4 occurrences in window
        )

        ls_cmd = {"function": {"name": "shell_exec", "arguments": '{"command": "ls wiki/rust/"}'}}
        appendix_cmd = {"function": {"name": "shell_exec", "arguments": '{"command": "ls wiki/appendix/"}'}}

        # Pattern: ls wiki/rust/ x4, ls wiki/appendix/ x4
        # Each identical call should appear 4 times in window
        for _ in range(4):
            detector.record([ls_cmd])
        for _ in range(4):
            detector.record([appendix_cmd])

        result = detector.check()
        # ls wiki/appendix/ appears 4 times in window, should trigger pattern
        assert result.is_looping
        assert result.loop_type == "pattern"

    def test_progress_breaks_loop(self):
        """Changing arguments should break exact loop detection.

        Note: tool-name-repeat may still trigger if same tool is used repeatedly.
        """
        detector = ToolCallLoopDetector(
            tool_thresholds={"shell_exec": 10, "default": 10}  # High threshold
        )

        # First attempt
        tc1 = {"function": {"name": "shell_exec", "arguments": '{"command": "ls /dir1"}'}}
        detector.record([tc1])
        detector.record([tc1])

        # Different command — progress!
        tc2 = {"function": {"name": "shell_exec", "arguments": '{"command": "ls /dir2"}'}}
        detector.record([tc2])

        result = detector.check()
        # With threshold=10, 3 calls shouldn't trigger exact repeat
        # But tool-name-repeat might trigger if threshold is low
        # Since we set threshold=10, it shouldn't trigger
        assert not result.is_looping

    def test_tool_name_repeat_sed_commands(self):
        """Simulate agent repeatedly calling sed with different line ranges.

        This is the exact scenario from v1.46.29 where agent was stuck reading
        different parts of a file without making progress.

        Note: shell_exec default threshold is 25, we override for testing.
        """
        # Override threshold for this test
        detector = ToolCallLoopDetector(
            tool_thresholds={"shell_exec": 5, "default": 5}
        )

        # Agent calls sed with different line ranges (different arguments!)
        sed_calls = [
            {"function": {"name": "shell_exec", "arguments": '{"command": "sed -n \'10,20p\' file.py"}'}},
            {"function": {"name": "shell_exec", "arguments": '{"command": "sed -n \'20,30p\' file.py"}'}},
            {"function": {"name": "shell_exec", "arguments": '{"command": "sed -n \'30,40p\' file.py"}'}},
            {"function": {"name": "shell_exec", "arguments": '{"command": "sed -n \'40,50p\' file.py"}'}},
            {"function": {"name": "shell_exec", "arguments": '{"command": "sed -n \'50,60p\' file.py"}'}},
        ]

        for sed_call in sed_calls:
            detector.record([sed_call])
            # Check after each call — should not trigger yet (need 5)

        # After 5 calls to shell_exec (even with different args), should detect
        result = detector.check()
        assert result.is_looping
        assert result.loop_type == "tool-name-repeat"
        assert result.repeated_count >= 5
        assert "shell_exec" in result.hint_message
        # v1.46.35: Updated hint format
        assert "varying arguments" in result.hint_message or "different arguments" in result.hint_message

    def test_tool_name_repeat_does_not_trigger_on_mixed_tools(self):
        """Verify tool-name-repeat doesn't trigger when tools are mixed."""
        detector = ToolCallLoopDetector(
            tool_thresholds={"shell_exec": 5, "read_file": 5, "write_file": 5, "default": 5}
        )

        # Mix of different tools
        mixed_calls = [
            {"function": {"name": "shell_exec", "arguments": '{"command": "ls"}'}},
            {"function": {"name": "read_file", "arguments": '{"path": "test.py"}'}},
            {"function": {"name": "shell_exec", "arguments": '{"command": "pwd"}'}},
            {"function": {"name": "write_file", "arguments": '{"path": "out.txt"}'}},
            {"function": {"name": "shell_exec", "arguments": '{"command": "cat out.txt"}'}},
        ]

        for call in mixed_calls:
            detector.record([call])

        result = detector.check()
        assert not result.is_looping  # Mixed tools, no pattern
