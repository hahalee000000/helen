"""Tests for helen/agent/ui/status_emitter.py"""

import json
import os
import socket
from unittest.mock import patch, MagicMock

from helen.agent.ui import status_emitter


class TestGetStatusSnapshot:
    def setup_method(self):
        status_emitter.reset_static_cache()

    def teardown_method(self):
        status_emitter.reset_static_cache()

    def test_returns_dict_with_required_keys(self):
        snap = status_emitter.get_status_snapshot()
        assert "hostname" in snap
        assert "cwd" in snap
        assert "user" in snap
        assert "usage_ratio" in snap
        assert "model" in snap

    def test_hostname_value(self):
        snap = status_emitter.get_status_snapshot()
        expected = socket.gethostname().split(".")[0] or "unknown"
        assert snap["hostname"] == expected

    def test_cwd_value(self):
        snap = status_emitter.get_status_snapshot()
        assert snap["cwd"] == os.getcwd()

    def test_usage_ratio_default(self):
        snap = status_emitter.get_status_snapshot()
        assert snap["usage_ratio"] == 0.0

    def test_usage_ratio_positive(self):
        snap = status_emitter.get_status_snapshot(usage_ratio=0.75)
        assert snap["usage_ratio"] == 0.75

    def test_usage_ratio_negative_becomes_zero(self):
        snap = status_emitter.get_status_snapshot(usage_ratio=-1.0)
        assert snap["usage_ratio"] == 0.0

    def test_model_default(self):
        snap = status_emitter.get_status_snapshot()
        assert snap["model"] == "unknown"

    def test_model_provided(self):
        snap = status_emitter.get_status_snapshot(model="qwen3.7-plus")
        assert snap["model"] == "qwen3.7-plus"

    def test_empty_model_becomes_unknown(self):
        snap = status_emitter.get_status_snapshot(model="")
        assert snap["model"] == "unknown"

    def test_static_cache_populated(self):
        assert status_emitter._static_cache is None
        status_emitter.get_status_snapshot()
        assert status_emitter._static_cache is not None

    def test_static_cache_reused(self):
        """Static fields should be cached after first call."""
        snap1 = status_emitter.get_status_snapshot()
        original_cwd = snap1["cwd"]
        # Even if cwd changes, cached value should be returned
        with patch.object(os, "getcwd", return_value="/fake/path"):
            snap2 = status_emitter.get_status_snapshot()
        assert snap2["cwd"] == original_cwd

    def test_reset_static_cache(self):
        status_emitter.get_status_snapshot()
        assert status_emitter._static_cache is not None
        status_emitter.reset_static_cache()
        assert status_emitter._static_cache is None

    def test_user_from_env(self):
        with patch.dict(os.environ, {"USER": "testuser"}, clear=False):
            status_emitter.reset_static_cache()
            snap = status_emitter.get_status_snapshot()
            assert snap["user"] == "testuser"

    def test_user_fallback_to_username(self):
        env = os.environ.copy()
        env.pop("USER", None)
        env["USERNAME"] = "winuser"
        with patch.dict(os.environ, env, clear=True):
            status_emitter.reset_static_cache()
            snap = status_emitter.get_status_snapshot()
            assert snap["user"] == "winuser"

    def test_user_empty_when_neither_set(self):
        env = os.environ.copy()
        env.pop("USER", None)
        env.pop("USERNAME", None)
        with patch.dict(os.environ, env, clear=True):
            status_emitter.reset_static_cache()
            snap = status_emitter.get_status_snapshot()
            assert snap["user"] == ""


class TestCollectStatic:
    def test_returns_dict(self):
        result = status_emitter._collect_static()
        assert isinstance(result, dict)
        assert "hostname" in result
        assert "cwd" in result
        assert "user" in result


class TestEmitStatus:
    def setup_method(self):
        status_emitter.reset_static_cache()

    def teardown_method(self):
        status_emitter.reset_static_cache()

    def test_emit_status_success(self):
        mock_emit = MagicMock()
        with patch.dict("sys.modules", {"ui": MagicMock(), "ui.stream_emitter": MagicMock(emit_stream_event=mock_emit)}):
            # Need to patch the import inside the function
            with patch("helen.agent.ui.status_emitter.emit_status") as mock_ffi:
                pass

        # Simpler: patch the import mechanism inside emit_status
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.emit_stream_event = mock_emit
            mock_import.return_value = mock_module
            # Actually, emit_status uses `from ui.stream_emitter import emit_stream_event`
            # Let's test differently

    def test_emit_status_returns_true_on_success(self):
        """emit_status calls FFI — test by mocking the import."""
        mock_emit = MagicMock()
        import sys
        # Create a fake ui.stream_emitter module
        fake_module = MagicMock()
        fake_module.emit_stream_event = mock_emit

        original_modules = dict(sys.modules)
        sys.modules["ui"] = MagicMock()
        sys.modules["ui.stream_emitter"] = fake_module
        try:
            result = status_emitter.emit_status(usage_ratio=0.5, model="test-model")
            assert result is True
            mock_emit.assert_called_once()
            # Verify the data passed is valid JSON
            call_args = mock_emit.call_args
            assert call_args[0][0] == "status_update"
            data = json.loads(call_args[0][1])
            assert data["usage_ratio"] == 0.5
            assert data["model"] == "test-model"
        finally:
            # Restore original modules
            for key in list(sys.modules.keys()):
                if key not in original_modules:
                    del sys.modules[key]
            for key, val in original_modules.items():
                if key in sys.modules and key not in ("ui", "ui.stream_emitter"):
                    sys.modules[key] = original_modules[key]

    def test_emit_status_returns_false_on_exception(self):
        """When stream_emitter is not available (CLI mode), returns False."""
        import sys
        original_modules = dict(sys.modules)
        # Remove any ui modules to force import error
        sys.modules.pop("ui", None)
        sys.modules.pop("ui.stream_emitter", None)
        # Block the import by setting to None
        sys.modules["ui.stream_emitter"] = None
        try:
            result = status_emitter.emit_status()
            assert result is False
        finally:
            # Restore
            sys.modules.pop("ui", None)
            sys.modules.pop("ui.stream_emitter", None)
            for key, val in original_modules.items():
                sys.modules[key] = val

    def test_emit_status_default_args(self):
        """emit_status with default args should also work."""
        mock_emit = MagicMock()
        import sys
        fake_module = MagicMock()
        fake_module.emit_stream_event = mock_emit
        original_modules = dict(sys.modules)
        sys.modules["ui"] = MagicMock()
        sys.modules["ui.stream_emitter"] = fake_module
        try:
            result = status_emitter.emit_status()
            assert result is True
            call_args = mock_emit.call_args
            data = json.loads(call_args[0][1])
            assert data["usage_ratio"] == 0.0
            assert data["model"] == "unknown"
        finally:
            sys.modules.pop("ui", None)
            sys.modules.pop("ui.stream_emitter", None)
            for key, val in original_modules.items():
                sys.modules[key] = val
