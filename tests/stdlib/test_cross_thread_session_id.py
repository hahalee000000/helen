"""Tests for cross-thread session ID visibility (v1.29.14 fix).

Root cause: get_session_id() returns "" in executor threads because agent context
is thread-local and only set in the main thread. spawn_chat_actor() runs in
executor thread (via run_in_executor), so sid = get_session_id() = "".

This test verifies the fix: process-level _main_session_id fallback.
"""

from __future__ import annotations

import threading
import tempfile
from pathlib import Path

import pytest

import helen.stdlib.transcript as transcript_module
from helen.stdlib.transcript import get_session_id, delete_current_session
from helen.interpreter.agent_context import AgentContextManager


class TestCrossThreadSessionID:
    """Test that session ID is visible across threads."""

    @pytest.fixture(autouse=True)
    def reset_global_state(self, tmp_path):
        """Reset global state before each test."""
        # Save original state
        original_context = transcript_module._get_agent_context()
        original_main_sid = getattr(transcript_module, '_main_session_id', None)

        # Reset to clean state
        transcript_module._set_transcript_context(None)
        transcript_module._main_session_id = None

        # Set up temp session dir
        import os
        old_env = os.environ.get('HELEN_SESSION_DIR')
        os.environ['HELEN_SESSION_DIR'] = str(tmp_path)

        yield

        # Restore original state
        transcript_module._set_transcript_context(original_context)
        transcript_module._main_session_id = original_main_sid

        if old_env is None:
            os.environ.pop('HELEN_SESSION_DIR', None)
        else:
            os.environ['HELEN_SESSION_DIR'] = old_env

    def test_main_thread_session_id(self):
        """Test get_session_id() in main thread."""
        # Set up agent context in main thread
        ctx = AgentContextManager(
            session_id='session_main_123',
            transcript_store_enabled=True
        )
        transcript_module._set_transcript_context(ctx)

        # Should return the session ID
        result = get_session_id()
        assert result == 'session_main_123'

    def test_executor_thread_session_id(self):
        """Test get_session_id() in executor thread (the bug)."""
        # Set up agent context in main thread
        ctx = AgentContextManager(
            session_id='session_main_456',
            transcript_store_enabled=True
        )
        transcript_module._set_transcript_context(ctx)

        # Simulate executor thread
        result = {}
        def worker():
            result['session_id'] = get_session_id()

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        # BUG: Currently returns "" because agent context is thread-local
        # FIX: Should return the main thread's session ID
        assert result['session_id'] == 'session_main_456', \
            f"Expected 'session_main_456', got {result['session_id']!r}"

    def test_main_session_id_fallback(self):
        """Test _main_session_id fallback mechanism."""
        # Set _main_session_id directly
        transcript_module._main_session_id = 'session_fallback_789'

        # No agent context
        transcript_module._set_transcript_context(None)

        # Should fall back to _main_session_id
        result = get_session_id()
        assert result == 'session_fallback_789'

    def test_main_session_id_set_by_interpreter(self):
        """Test that _main_session_id is set when agent context is initialized."""
        # Simulate Interpreter init with session_id
        ctx = AgentContextManager(
            session_id='session_interp_012',
            transcript_store_enabled=True
        )

        # This should set _main_session_id
        transcript_module._set_transcript_context(ctx)

        # Verify _main_session_id is set
        assert transcript_module._main_session_id == 'session_interp_012'

    def test_delete_current_session_clears_main_session_id(self, tmp_path):
        """Test that delete_current_session() clears _main_session_id."""
        # Set up agent context
        ctx = AgentContextManager(
            session_id='session_delete_345',
            transcript_store_enabled=True
        )
        transcript_module._set_transcript_context(ctx)

        # Trigger lazy init to create session
        old_sid = get_session_id()
        assert old_sid == 'session_delete_345'

        # Verify _main_session_id is set
        assert transcript_module._main_session_id == 'session_delete_345'

        # Delete the session
        result = delete_current_session(confirm=True, cascade=True)
        assert result['status'] == 'ok'

        # Verify _main_session_id is cleared
        assert transcript_module._main_session_id is None

        # After deletion, next get_session_id() creates a NEW session
        # (not the old deleted one). This is the expected behavior:
        # lazy init with no _pending_session_id creates a fresh session.
        new_sid = get_session_id()
        assert new_sid != 'session_delete_345', \
            "New session ID should differ from deleted one"
        assert new_sid.startswith('session_'), \
            f"New session ID should have session_ prefix, got {new_sid!r}"

        # Verify the new session ID is also visible in executor threads
        result = {}
        def worker():
            result['session_id'] = get_session_id()

        t = threading.Thread(target=worker)
        t.start()
        t.join()
        assert result['session_id'] == new_sid

    def test_cross_thread_after_delete(self, tmp_path):
        """Test that a new session is created after delete, visible in all threads."""
        # Set up agent context
        ctx = AgentContextManager(
            session_id='session_cross_678',
            transcript_store_enabled=True
        )
        transcript_module._set_transcript_context(ctx)

        # Trigger lazy init
        old_sid = get_session_id()
        assert old_sid == 'session_cross_678'

        # Verify session ID in executor thread
        result_before = {}
        def worker_before():
            result_before['session_id'] = get_session_id()

        t1 = threading.Thread(target=worker_before)
        t1.start()
        t1.join()
        assert result_before['session_id'] == 'session_cross_678'

        # Delete the session
        delete_current_session(confirm=True, cascade=True)

        # After deletion, a new session is lazily created
        new_sid = get_session_id()
        assert new_sid != 'session_cross_678'
        assert new_sid.startswith('session_')

        # Verify the new session ID is visible in executor thread
        result_after = {}
        def worker_after():
            result_after['session_id'] = get_session_id()

        t2 = threading.Thread(target=worker_after)
        t2.start()
        t2.join()
        assert result_after['session_id'] == new_sid


class TestPythonBridgeIntegration:
    """Test Python bridge session ID synchronization."""

    @pytest.fixture(autouse=True)
    def reset_bridge_state(self):
        """Reset Python bridge state."""
        from helen.python_bridge import import_hook
        original_override = import_hook._session_id_override
        import_hook._session_id_override = None

        yield

        import_hook._session_id_override = original_override

    def test_bridge_override_cleared_on_delete(self, tmp_path):
        """Test that Python bridge override is cleared when session is deleted."""
        from helen.python_bridge.import_hook import (
            set_session_id,
            _session_id_override
        )

        # Set bridge override
        set_session_id('session_bridge_901')

        # Set up agent context
        ctx = AgentContextManager(
            session_id='session_bridge_901',
            transcript_store_enabled=True
        )
        transcript_module._set_transcript_context(ctx)

        # Trigger lazy init
        _ = get_session_id()

        # Delete the session
        delete_current_session(confirm=True, cascade=True)

        # Verify bridge override is cleared
        from helen.python_bridge import import_hook
        assert import_hook._session_id_override is None
