"""Tests for REPL survival on Ctrl+C during streaming (Phase 4)."""

import pytest


class TestReplInterrupt:
    """Phase 4: REPL survives Ctrl+C during streaming."""

    def test_repl_has_keyboard_interrupt_handler(self):
        """REPL execution sites catch KeyboardInterrupt."""
        import inspect
        from helen.cli.repl import repl_command
        source = inspect.getsource(repl_command)
        assert "KeyboardInterrupt" in source
        assert "cancel_all_streaming_calls" in source

    def test_repl_interrupt_message(self):
        """REPL prints interrupt message on Ctrl+C."""
        import inspect
        from helen.cli.repl import repl_command
        source = inspect.getsource(repl_command)
        assert "已中断" in source
        assert "状态已保留" in source
