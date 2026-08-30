"""Tests for stream_emitter cancel flag auto-timeout (v1.46.12)."""
import time
import pytest


class TestCancelFlagAutoTimeout:
    """v1.46.12: Cancel flag auto-clears after 30s if stuck."""

    def test_cancel_flag_basic_flow(self):
        """Normal cancel flow: request → check → clear."""
        from helen.agent.ui.stream_emitter import (
            request_cancel, is_cancel_requested, clear_cancel
        )
        try:
            assert is_cancel_requested() is False
            request_cancel()
            assert is_cancel_requested() is True
            clear_cancel()
            assert is_cancel_requested() is False
        finally:
            clear_cancel()

    def test_cancel_flag_auto_timeout(self):
        """Cancel flag auto-clears after timeout."""
        from helen.agent.ui import stream_emitter
        original_timeout = stream_emitter._CANCEL_FLAG_TIMEOUT
        try:
            # Use a very short timeout for testing
            stream_emitter._CANCEL_FLAG_TIMEOUT = 0.1
            stream_emitter.request_cancel()
            assert stream_emitter.is_cancel_requested() is True
            # Wait for timeout
            time.sleep(0.2)
            # Flag should be auto-cleared
            assert stream_emitter.is_cancel_requested() is False
        finally:
            stream_emitter._CANCEL_FLAG_TIMEOUT = original_timeout
            stream_emitter.clear_cancel()

    def test_cancel_flag_not_expired_within_timeout(self):
        """Cancel flag stays True within timeout period."""
        from helen.agent.ui import stream_emitter
        original_timeout = stream_emitter._CANCEL_FLAG_TIMEOUT
        try:
            stream_emitter._CANCEL_FLAG_TIMEOUT = 10.0  # Long timeout
            stream_emitter.request_cancel()
            # Check immediately — should still be True
            assert stream_emitter.is_cancel_requested() is True
        finally:
            stream_emitter._CANCEL_FLAG_TIMEOUT = original_timeout
            stream_emitter.clear_cancel()

    def test_cancel_flag_cleared_before_timeout(self):
        """Explicit clear works even before timeout."""
        from helen.agent.ui import stream_emitter
        original_timeout = stream_emitter._CANCEL_FLAG_TIMEOUT
        try:
            stream_emitter._CANCEL_FLAG_TIMEOUT = 10.0
            stream_emitter.request_cancel()
            assert stream_emitter.is_cancel_requested() is True
            stream_emitter.clear_cancel()
            assert stream_emitter.is_cancel_requested() is False
        finally:
            stream_emitter._CANCEL_FLAG_TIMEOUT = original_timeout
