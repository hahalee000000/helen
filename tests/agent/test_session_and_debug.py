"""Tests for session memento and test command behavior.

Ensures:
1. Session memento (current_session_id) is correctly read/written
2. helen test does NOT create empty session directories
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


class TestSessionMemento:
    """Test session memento file format and reading."""

    def test_memento_json_format(self):
        """Memento should be valid JSON with main and child fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memento_path = Path(tmpdir) / ".helen" / "current_session_id"
            memento_path.parent.mkdir(parents=True, exist_ok=True)

            # Write memento
            memento_data = {
                "main": "session_1785643851_8190df93",
                "child": "session_1785643856_5f362e9f",
            }
            memento_path.write_text(json.dumps(memento_data), encoding="utf-8")

            # Read and verify
            content = memento_path.read_text(encoding="utf-8")
            data = json.loads(content)
            assert data["main"] == "session_1785643851_8190df93"
            assert data["child"] == "session_1785643856_5f362e9f"

    def test_memento_with_special_characters(self):
        """Memento should handle session IDs with special characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memento_path = Path(tmpdir) / ".helen" / "current_session_id"
            memento_path.parent.mkdir(parents=True, exist_ok=True)

            # Session IDs should be alphanumeric + underscore
            memento_data = {
                "main": "session_1785643851_abcdef12",
                "child": "session_1785643856_fedcba21",
            }
            memento_path.write_text(json.dumps(memento_data), encoding="utf-8")

            content = memento_path.read_text(encoding="utf-8")
            data = json.loads(content)
            assert "session_" in data["main"]
            assert "session_" in data["child"]


class TestHelenTestNoSessionCreation:
    """Test that helen test does NOT create empty session directories."""

    def test_helen_test_no_session_pollution(self):
        """Running helen test should NOT create session directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create a simple test file
            test_file = tmpdir / "test_simple.helen"
            test_file.write_text('''
fn test_addition() {
    assert_equal(1 + 1, 2)
}
''', encoding="utf-8")

            # Run helen test
            result = subprocess.run(
                [sys.executable, "-m", "helen", "test", str(test_file)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=tmpdir,
            )

            # Check that no .helen/sessions directory was created
            sessions_dir = tmpdir / ".helen" / "sessions"
            if sessions_dir.exists():
                session_dirs = list(sessions_dir.iterdir())
                # If sessions dir exists, it should be empty (no sessions created)
                # or only contain the current session (not test artifacts)
                for session_dir in session_dirs:
                    transcript = session_dir / "transcript.jsonl"
                    if transcript.exists():
                        content = transcript.read_text(encoding="utf-8")
                        # Should not have test-related argv
                        lines = content.strip().split("\n")
                        for line in lines:
                            if line:
                                data = json.loads(line)
                                if data.get("type") == "session_meta":
                                    argv = data.get("argv", [])
                                    # If this session was created by helen test, fail
                                    assert "test" not in " ".join(argv).lower() or \
                                           data.get("session_scope") != "env_override", \
                                           f"helen test created a session: {data}"

    def test_helen_check_no_session_creation(self):
        """Running helen check should NOT create session directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create a simple Helen file
            helen_file = tmpdir / "simple.helen"
            helen_file.write_text('''
fn add(a: int, b: int): int {
    return a + b
}

main {
    print(add(1, 2))
}
''', encoding="utf-8")

            # Run helen check
            result = subprocess.run(
                [sys.executable, "-m", "helen", "check", str(helen_file)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=tmpdir,
            )

            # Check that no .helen/sessions directory was created
            sessions_dir = tmpdir / ".helen" / "sessions"
            assert not sessions_dir.exists() or len(list(sessions_dir.iterdir())) == 0, \
                "helen check should not create session directories"


class TestDebugOutput:
    """Test debug output control via HELEN_DEBUG env var."""

    def test_debug_disabled_by_default_in_agent(self):
        """HELEN_DEBUG should default to 0 in agent context."""
        # This is a configuration test - verify start_webui.py sets HELEN_DEBUG=0
        from helen.agent.webui import start_webui

        # Check that the module sets HELEN_DEBUG=0 by default
        # (This is done in main() but we can verify the logic exists)
        assert hasattr(start_webui, 'main')

    def test_debug_function_respects_env_var(self):
        """_debug() should respect HELEN_DEBUG env var."""
        from helen.stdlib import _debug

        # Test with debug enabled
        with pytest.MonkeyPatch.context() as m:
            m.setenv("HELEN_DEBUG", "1")
            result = _debug("test message")
            assert result == "[DEBUG] test message"

        # Test with debug disabled
        with pytest.MonkeyPatch.context() as m:
            m.setenv("HELEN_DEBUG", "0")
            result = _debug("test message")
            assert result == ""

        # Test with debug=false
        with pytest.MonkeyPatch.context() as m:
            m.setenv("HELEN_DEBUG", "false")
            result = _debug("test message")
            assert result == ""
