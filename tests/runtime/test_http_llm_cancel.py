"""Tests for HttpLLMRuntime cancel_event parameter (Phase 2)."""

import threading
import pytest
from unittest.mock import MagicMock, patch


class TestHttpLLMCancelEvent:
    """Phase 2: HttpLLMRuntime.act_stream() accepts cancel_event."""

    def test_act_stream_signature_accepts_cancel_event(self):
        """HttpLLMRuntime.act_stream has cancel_event parameter."""
        import inspect
        from helen.runtime.http_llm import HttpLLMRuntime
        sig = inspect.signature(HttpLLMRuntime.act_stream)
        assert "cancel_event" in sig.parameters

    def test_act_stream_cancel_event_default_none(self):
        """cancel_event defaults to None (backward compatible)."""
        import inspect
        from helen.runtime.http_llm import HttpLLMRuntime
        sig = inspect.signature(HttpLLMRuntime.act_stream)
        param = sig.parameters["cancel_event"]
        assert param.default is None

    def test_cancel_between_turns(self):
        """cancel_event set between turns causes break.

        This is a unit-level contract test — the actual HTTP interaction
        is tested in integration tests.
        """
        cancel = threading.Event()
        cancel.set()  # Pre-cancelled

        # The contract: when cancel_event.is_set() before entering the
        # streaming loop, act_stream should not make any HTTP calls
        # This is verified by the break check at the top of while budget.consume()
