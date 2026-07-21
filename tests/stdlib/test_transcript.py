"""Tests for transcript stdlib functions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import helen.stdlib.transcript as transcript_module
from helen.stdlib.transcript import (
    export_transcript,
    get_compression_audit,
    get_session_id,
    list_sessions,
    replay_transcript,
)


class TestTranscriptStdlib:
    """Test transcript stdlib functions."""

    @pytest.fixture(autouse=True)
    def reset_global_state(self):
        """Reset global interpreter context before each test."""
        # Save original state (v1.23.4: use thread-local getter)
        original_context = transcript_module._get_agent_context()

        # Reset to None for clean test state
        transcript_module._set_transcript_context(None)

        yield

        # Restore original state after test
        transcript_module._set_transcript_context(original_context)

    def test_get_session_id_no_interpreter(self):
        """Test get_session_id with no active interpreter."""
        # Should return empty string when no interpreter
        result = get_session_id()
        assert result == ""

    def test_list_sessions_empty(self, tmp_path):
        """Test list_sessions with no sessions."""
        # This will use the default session directory
        # We can't easily test this without mocking, so just verify it doesn't crash
        sessions = list_sessions()
        assert isinstance(sessions, list)

    def test_replay_transcript_no_interpreter(self):
        """Test replay_transcript with no active interpreter."""
        # Should return empty list when no interpreter
        result = replay_transcript()
        assert result == []

    def test_get_compression_audit_no_interpreter(self):
        """Test get_compression_audit with no active interpreter."""
        # Should return empty list when no interpreter
        result = get_compression_audit()
        assert result == []

    def test_export_transcript_empty(self, tmp_path):
        """Test export_transcript with no messages."""
        output_path = tmp_path / "export.json"
        result = export_transcript(str(output_path), format="json")
        # Should return empty string when no messages
        assert result == ""

    def test_export_transcript_json_format(self, tmp_path):
        """Test export_transcript in JSON format."""
        output_path = tmp_path / "export.json"

        # Create some mock data by directly writing to the export function
        # (In real usage, this would come from the interpreter)
        messages = [
            {"type": "message", "role": "user", "content": "Hello", "uuid": "msg1"},
            {"type": "message", "role": "assistant", "content": "Hi", "uuid": "msg2"},
        ]

        # Mock the replay_transcript function to return our test data
        import helen.stdlib.transcript as transcript_module
        original_replay = transcript_module.replay_transcript

        def mock_replay(*args, **kwargs):
            return messages

        transcript_module.replay_transcript = mock_replay

        try:
            result = export_transcript(str(output_path), format="json")
            assert result == str(output_path)
            assert output_path.exists()

            # Verify JSON content
            with open(output_path, encoding="utf-8") as f:
                data = json.load(f)
            assert len(data) == 2
            assert data[0]["role"] == "user"
            assert data[1]["role"] == "assistant"
        finally:
            # Restore original function
            transcript_module.replay_transcript = original_replay

    def test_export_transcript_markdown_format(self, tmp_path):
        """Test export_transcript in Markdown format."""
        output_path = tmp_path / "export.md"

        messages = [
            {"type": "message", "role": "user", "content": "Hello", "uuid": "msg1"},
            {"type": "message", "role": "assistant", "content": "Hi there", "uuid": "msg2"},
        ]

        import helen.stdlib.transcript as transcript_module
        original_replay = transcript_module.replay_transcript

        def mock_replay(*args, **kwargs):
            return messages

        transcript_module.replay_transcript = mock_replay

        try:
            result = export_transcript(str(output_path), format="markdown")
            assert result == str(output_path)
            assert output_path.exists()

            # Verify Markdown content
            content = output_path.read_text(encoding="utf-8")
            assert "# Transcript Export" in content
            assert "## User" in content
            assert "## Assistant" in content
            assert "Hello" in content
            assert "Hi there" in content
        finally:
            transcript_module.replay_transcript = original_replay

    def test_export_transcript_text_format(self, tmp_path):
        """Test export_transcript in plain text format."""
        output_path = tmp_path / "export.txt"

        messages = [
            {"type": "message", "role": "user", "content": "Hello", "uuid": "msg1"},
            {"type": "message", "role": "assistant", "content": "Hi", "uuid": "msg2"},
        ]

        import helen.stdlib.transcript as transcript_module
        original_replay = transcript_module.replay_transcript

        def mock_replay(*args, **kwargs):
            return messages

        transcript_module.replay_transcript = mock_replay

        try:
            result = export_transcript(str(output_path), format="text")
            assert result == str(output_path)
            assert output_path.exists()

            # Verify text content
            content = output_path.read_text(encoding="utf-8")
            assert "[user] Hello" in content
            assert "[assistant] Hi" in content
        finally:
            transcript_module.replay_transcript = original_replay

    def test_export_transcript_invalid_format(self, tmp_path):
        """Test export_transcript with invalid format."""
        output_path = tmp_path / "export.xyz"

        messages = [
            {"type": "message", "role": "user", "content": "Hello", "uuid": "msg1"},
        ]

        import helen.stdlib.transcript as transcript_module
        original_replay = transcript_module.replay_transcript

        def mock_replay(*args, **kwargs):
            return messages

        transcript_module.replay_transcript = mock_replay

        try:
            result = export_transcript(str(output_path), format="invalid")
            assert result == ""  # Should return empty string on error
        finally:
            transcript_module.replay_transcript = original_replay


# ═══════════════════════════════════════════════════════════════════════
# v1.23.4 regression tests: Thread-local agent context isolation
# ═══════════════════════════════════════════════════════════════════════


class TestThreadLocalAgentContext:
    """v1.23.4 fix: agent context is thread-local to prevent spawn pollution.

    Before v1.23.4, _interpreter_agent_context was a module-level global.
    When spawn created a child Interpreter in a daemon thread, the child's
    _set_transcript_context() would overwrite the main thread's context,
    causing the main thread to see the spawned session's ID (or None)
    after spawn. These tests verify the fix.
    """

    def test_agent_context_is_thread_local(self):
        """Each thread sees its own agent context."""
        import threading
        from helen.stdlib.transcript import _set_transcript_context, _get_agent_context

        # Main thread sets a context
        class FakeCtx:
            session_id = "main_session"

        _set_transcript_context(FakeCtx())
        assert _get_agent_context().session_id == "main_session"

        # Child thread sets a different context
        results = {}

        def child():
            class ChildCtx:
                session_id = "child_session"
            _set_transcript_context(ChildCtx())
            results["child_sees"] = _get_agent_context().session_id

        t = threading.Thread(target=child)
        t.start()
        t.join()

        # Child thread saw its own context
        assert results["child_sees"] == "child_session"

        # Main thread STILL sees its own context (not polluted)
        assert _get_agent_context().session_id == "main_session"

        # Cleanup
        _set_transcript_context(None)

    def test_agent_context_default_none(self):
        """New thread with no context set returns None."""
        import threading
        from helen.stdlib.transcript import _get_agent_context

        results = {}

        def child():
            results["ctx"] = _get_agent_context()

        t = threading.Thread(target=child)
        t.start()
        t.join()

        assert results["ctx"] is None

    def test_get_session_id_unaffected_by_spawn(self):
        """get_session_id() in main thread is stable across spawn-like operations.

        Simulates the bug: before v1.23.4, spawning a thread that calls
        _set_transcript_context would change the main thread's session_id.
        """
        import threading
        from helen.stdlib.transcript import (
            _set_transcript_context, _get_agent_context,
        )

        class MainCtx:
            session_id = "main_session_123"

        class SpawnedCtx:
            session_id = "spawned_session_456"

        _set_transcript_context(MainCtx())
        main_before = _get_agent_context().session_id

        # Simulate spawn: child thread sets its own context
        def spawn_sim():
            _set_transcript_context(SpawnedCtx())

        t = threading.Thread(target=spawn_sim)
        t.start()
        t.join()

        main_after = _get_agent_context().session_id

        # Main thread's session_id must be unchanged
        assert main_before == "main_session_123"
        assert main_after == "main_session_123", (
            f"Main thread polluted by spawn! before={main_before}, after={main_after}"
        )

        # Cleanup
        _set_transcript_context(None)
