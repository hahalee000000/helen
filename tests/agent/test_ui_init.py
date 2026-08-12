"""Tests for helen/agent/ui/__init__.py"""


class TestUiPackageImport:
    def test_ui_package_imports_successfully(self):
        import helen.agent.ui as ui
        assert ui is not None

    def test_stream_emitter_accessible(self):
        from helen.agent.ui import stream_emitter
        assert stream_emitter is not None
        assert hasattr(stream_emitter, "emit_stream_event")

    def test_status_emitter_accessible(self):
        from helen.agent.ui import status_emitter
        assert status_emitter is not None
        assert hasattr(status_emitter, "get_status_snapshot")

    def test_hint_queue_accessible(self):
        from helen.agent.ui import hint_queue
        assert hint_queue is not None
        assert hasattr(hint_queue, "get_hint_queue")

    def test_all_exports(self):
        from helen.agent.ui import __all__
        assert set(__all__) == {"stream_emitter", "status_emitter", "hint_queue"}

    def test_version(self):
        from helen.agent.ui import __version__
        assert isinstance(__version__, str)
        assert __version__ == "0.2.0"
