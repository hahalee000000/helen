"""Tests for v1.46 shell_exec self-preservation (anti-suicide) safety check.

Verifies that shell_exec blocks commands that would kill the agent process
itself (e.g., pkill -f "helen agent" that an LLM might generate).
"""

from __future__ import annotations

import os

import pytest

from helen.runtime.tools import _check_self_destruct, _shell_exec, _shell_exec_full


class TestCheckSelfDestruct:
    """Test the _check_self_destruct safety predicate."""

    def test_pkill_quoted_helen_agent(self):
        """pkill -f with quoted 'helen agent' is blocked."""
        assert _check_self_destruct('pkill -f "helen agent"') is not None
        assert _check_self_destruct("pkill -f 'helen agent'") is not None

    def test_pkill_escaped_space(self):
        """pkill -f with backslash-escaped space is blocked."""
        assert _check_self_destruct("pkill -f helen\\ agent") is not None

    def test_pkill_wildcard_dot(self):
        """pkill -f with dot wildcard matching 'helen<sep>agent' is blocked."""
        assert _check_self_destruct("pkill -f helen.agent") is not None

    def test_pkill_other_pattern_allowed(self):
        """pkill -f with non-helen patterns is allowed."""
        assert _check_self_destruct("pkill -f some_other_process") is None
        assert _check_self_destruct("pkill -f python") is None

    def test_pkill_without_f_flag_allowed(self):
        """pkill without -f flag is allowed (matches process name, less dangerous)."""
        assert _check_self_destruct("pkill helen") is None
        assert _check_self_destruct("pkill python") is None

    def test_killall_helen_blocked(self):
        """killall targeting helen is blocked."""
        assert _check_self_destruct("killall helen") is not None
        assert _check_self_destruct("killall -f helen") is not None
        assert _check_self_destruct('killall -f "helen agent"') is not None

    def test_kill_own_pid_blocked(self):
        """kill <own_pid> is blocked."""
        own_pid = os.getpid()
        assert _check_self_destruct(f"kill {own_pid}") is not None
        assert _check_self_destruct(f"kill -9 {own_pid}") is not None

    def test_kill_other_pid_allowed(self):
        """kill of unrelated PID is allowed."""
        assert _check_self_destruct("kill 1") is None  # init, not self
        assert _check_self_destruct("kill 99999999") is None

    def test_normal_commands_allowed(self):
        """Normal commands are allowed."""
        assert _check_self_destruct("echo hello") is None
        assert _check_self_destruct("ls -la") is None
        assert _check_self_destruct("cd /tmp && pwd") is None
        assert _check_self_destruct("grep -r pattern .") is None

    def test_chained_command_blocked(self):
        """Chained commands containing self-destruct are blocked."""
        assert _check_self_destruct('cd /home/rxx && pkill -f "helen agent"') is not None
        assert _check_self_destruct("echo bye ; killall helen") is not None

    # v1.46.14: Indirect kill pattern tests
    def test_xargs_kill_with_helen_grep_blocked(self):
        """ps | grep helen | xargs kill patterns are blocked."""
        # Basic pattern
        assert _check_self_destruct(
            'ps aux | grep "helen agent" | xargs kill'
        ) is not None
        # With single quotes
        assert _check_self_destruct(
            "ps aux | grep 'helen agent' | xargs kill"
        ) is not None
        # Without quotes
        assert _check_self_destruct(
            "ps aux | grep helen | xargs kill"
        ) is not None

    def test_xargs_kill_with_signal_blocked(self):
        """xargs kill -9 patterns are blocked."""
        assert _check_self_destruct(
            'ps aux | grep "helen agent" | xargs kill -9'
        ) is not None
        assert _check_self_destruct(
            'ps aux | grep helen | xargs kill -9'
        ) is not None

    def test_complex_indirect_kill_blocked(self):
        """Complex pipe chains with grep helen + xargs kill are blocked."""
        # With awk
        assert _check_self_destruct(
            'ps aux | grep "helen agent" | grep -v grep | awk \'{print $2}\' | xargs kill'
        ) is not None
        # With grep -E
        assert _check_self_destruct(
            'ps aux | grep -E "helen.*agent" | xargs kill'
        ) is not None
        # Real example from helen-rust transcript
        assert _check_self_destruct(
            'ps aux | grep "helen agent" | grep -v grep | grep -v "pts/1" | '
            'awk \'{print $2}\' | xargs kill 2>/dev/null'
        ) is not None

    def test_indirect_kill_without_helen_allowed(self):
        """xargs kill without helen grep is allowed."""
        assert _check_self_destruct(
            "ps aux | grep python | xargs kill"
        ) is None
        assert _check_self_destruct(
            "echo 123 | xargs kill"
        ) is None

    def test_grep_helen_without_xargs_allowed(self):
        """grep helen without xargs kill is allowed."""
        assert _check_self_destruct(
            'ps aux | grep "helen agent"'
        ) is None
        assert _check_self_destruct(
            "grep -r helen ."
        ) is None


class TestShellExecBlocking:
    """Test that _shell_exec and _shell_exec_full respect the safety check."""

    def test_shell_exec_returns_blocked_message(self):
        """_shell_exec returns a [blocked] message instead of executing."""
        result = _shell_exec('pkill -f "helen agent"')
        assert result.startswith("[blocked]")
        assert "self-preservation" in result

    def test_shell_exec_full_returns_blocked_json(self):
        """_shell_exec_full returns a JSON with blocked=True."""
        import json
        result = _shell_exec_full('pkill -f "helen agent"')
        data = json.loads(result)
        assert data.get("blocked") is True
        assert "error" in data

    def test_shell_exec_allows_safe_command(self):
        """_shell_exec still executes safe commands normally."""
        result = _shell_exec("echo test_safe_command_marker")
        assert "test_safe_command_marker" in result
        assert not result.startswith("[blocked]")
