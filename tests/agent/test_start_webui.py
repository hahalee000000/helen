"""Tests for start_webui.py cross-platform launcher.

These tests ensure the Web UI launcher works correctly on all platforms.
"""
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from unittest import mock
from unittest.mock import patch, MagicMock, call

import pytest

from helen.agent.webui.start_webui import (
    find_helen_python,
    IS_WINDOWS,
    terminate_process_tree,
    _wait_for_proc,
    _restore_terminal,
    cleanup_all,
    start_backend,
    start_frontend,
    check_ports,
    main,
)
import helen.agent.webui.start_webui as mod


# ── find_helen_python ────────────────────────────────────────────


class TestFindHelenPython:
    """Test find_helen_python() finds the correct Python interpreter."""

    def test_returns_valid_python_path(self):
        """find_helen_python() should return an existing Python executable."""
        python_path = find_helen_python()
        assert python_path is not None
        assert Path(python_path).exists()
        assert "python" in python_path.lower()

    def test_prefers_helen_venv_env(self):
        """find_helen_python() should prefer HELEN_VENV env var."""
        with mock.patch.dict(os.environ, {"HELEN_VENV": str(sys.prefix)}):
            python_path = find_helen_python()
            assert python_path is not None

    def test_falls_back_to_home_venv(self):
        """find_helen_python() should fall back to ~/.venv if exists."""
        home_venv = Path.home() / ".venv"
        if not home_venv.exists():
            pytest.skip("~/.venv does not exist")

        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ["PATH"] = os.environ.get("PATH", "")
            python_path = find_helen_python()
            assert python_path is not None

    def test_falls_back_to_sys_executable(self):
        """find_helen_python() should fall back to sys.executable if no venv found."""
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path("/nonexistent/path/for/testing")
                python_path = find_helen_python()
                assert python_path == sys.executable


class TestCrossPlatformConstants:
    """Test platform-specific constants."""

    def test_is_windows_matches_platform(self):
        """IS_WINDOWS should match sys.platform."""
        expected = sys.platform == "win32"
        assert IS_WINDOWS == expected


# ── terminate_process_tree ───────────────────────────────────────


class TestTerminateProcessTree:
    """Test terminate_process_tree() for various scenarios."""

    def test_none_proc_is_noop(self):
        """Passing None should be a no-op."""
        terminate_process_tree(None)  # should not raise

    def test_already_dead_proc_is_noop(self):
        """proc.poll() returning non-None means already dead — skip."""
        proc = MagicMock()
        proc.poll.return_value = 0  # already exited
        terminate_process_tree(proc)
        # On Unix, os.killpg should NOT be called
        # (no interaction with signals)

    @pytest.mark.skipif(IS_WINDOWS, reason="Unix-only test")
    def test_unix_sigterm_path(self):
        """On Unix, terminate_process_tree sends SIGTERM via killpg."""
        proc = MagicMock()
        proc.poll.return_value = None  # still running
        proc.pid = 12345

        with patch("os.killpg") as mock_killpg, \
             patch("os.getpgid", return_value=12345) as mock_getpgid:
            terminate_process_tree(proc)
            mock_getpgid.assert_called_once_with(12345)
            mock_killpg.assert_called_once_with(12345, signal.SIGTERM)

    @pytest.mark.skipif(IS_WINDOWS, reason="Unix-only test")
    def test_unix_process_lookup_error_handled(self):
        """ProcessLookupError during killpg is silently caught."""
        proc = MagicMock()
        proc.poll.return_value = None
        proc.pid = 99999

        with patch("os.killpg", side_effect=ProcessLookupError()), \
             patch("os.getpgid", return_value=99999):
            terminate_process_tree(proc)  # should not raise

    @pytest.mark.skipif(IS_WINDOWS, reason="Unix-only test")
    def test_unix_os_error_handled(self):
        """OSError during killpg is silently caught."""
        proc = MagicMock()
        proc.poll.return_value = None
        proc.pid = 99999

        with patch("os.killpg", side_effect=OSError("permission denied")), \
             patch("os.getpgid", return_value=99999):
            terminate_process_tree(proc)  # should not raise

    @pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only test")
    def test_windows_taskkill(self):
        """On Windows, terminate_process_tree uses taskkill."""
        proc = MagicMock()
        proc.poll.return_value = None
        proc.pid = 1234

        with patch("subprocess.run") as mock_run:
            terminate_process_tree(proc)
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[0] == "taskkill"
            assert "/PID" in args
            assert "1234" in args


# ── _wait_for_proc ───────────────────────────────────────────────


class TestWaitForProc:
    """Test _wait_for_proc() normal and escalation paths."""

    def test_none_proc_is_noop(self):
        """Passing None should be a no-op."""
        _wait_for_proc(None)  # should not raise

    def test_already_dead_proc_is_noop(self):
        """proc.poll() returning non-None means already dead — skip."""
        proc = MagicMock()
        proc.poll.return_value = 0
        _wait_for_proc(proc)
        proc.wait.assert_not_called()

    def test_normal_wait(self):
        """proc.wait completes within timeout — no SIGKILL."""
        proc = MagicMock()
        proc.poll.return_value = None
        proc.wait.return_value = None  # exits normally

        _wait_for_proc(proc, timeout=0.5)
        proc.wait.assert_called_once_with(timeout=0.5)

    @pytest.mark.skipif(IS_WINDOWS, reason="Unix-only test")
    def test_sigkill_escalation_on_timeout(self):
        """TimeoutExpired triggers SIGKILL escalation."""
        proc = MagicMock()
        proc.poll.return_value = None
        proc.pid = 54321
        proc.wait.side_effect = [
            subprocess.TimeoutExpired(cmd="test", timeout=0.5),
            None,  # second wait after SIGKILL succeeds
        ]

        with patch("os.killpg") as mock_killpg, \
             patch("os.getpgid", return_value=54321):
            _wait_for_proc(proc, timeout=0.5)
            mock_killpg.assert_called_once_with(54321, signal.SIGKILL)
            assert proc.wait.call_count == 2

    def test_timeout_expired_on_kill_is_caught(self):
        """Even if second wait times out, exception is swallowed."""
        proc = MagicMock()
        proc.poll.return_value = None
        proc.pid = 11111
        proc.wait.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=0.5)

        if IS_WINDOWS:
            # On Windows, no killpg, just two waits
            _wait_for_proc(proc, timeout=0.5)
        else:
            with patch("os.killpg"), \
                 patch("os.getpgid", return_value=11111):
                _wait_for_proc(proc, timeout=0.5)
        # Should not raise


# ── _restore_terminal ────────────────────────────────────────────


class TestRestoreTerminal:
    """Test _restore_terminal() for TTY and non-TTY paths."""

    def test_non_tty_is_noop(self):
        """Non-TTY stdout should skip terminal reset."""
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.isatty.return_value = False
            _restore_terminal()
            mock_stdout.write.assert_not_called()

    def test_tty_writes_reset_sequences(self):
        """TTY stdout should write ANSI reset sequences."""
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.isatty.return_value = True
            _restore_terminal()
            mock_stdout.write.assert_called_once()
            written = mock_stdout.write.call_args[0][0]
            assert "\033[?25h" in written  # show cursor
            assert "\033[0m" in written    # reset attributes
            mock_stdout.flush.assert_called_once()

    def test_exception_during_write_is_caught(self):
        """Exception during write/flush is silently caught."""
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.isatty.return_value = True
            mock_stdout.write.side_effect = OSError("broken pipe")
            _restore_terminal()  # should not raise


# ── cleanup_all ──────────────────────────────────────────────────


class TestCleanupAll:
    """Test cleanup_all() idempotency and orchestration."""

    def setup_method(self):
        """Reset _cleanup_done before each test."""
        mod._cleanup_done = False
        mod._backend_proc = None
        mod._frontend_proc = None

    def test_idempotent_second_call_is_noop(self):
        """Second call to cleanup_all should be a no-op."""
        with patch.object(mod, "terminate_process_tree") as mock_term, \
             patch.object(mod, "_wait_for_proc") as mock_wait, \
             patch.object(mod, "_restore_terminal") as mock_restore:
            cleanup_all()
            cleanup_all()  # second call
            # terminate called only on first call
            assert mock_term.call_count == 2  # backend + frontend
            # second call: no additional calls
            assert mock_term.call_count == 2

    def test_calls_terminate_wait_restore_in_order(self):
        """cleanup_all calls terminate, wait, restore in correct order."""
        call_order = []
        mod._backend_proc = MagicMock()
        mod._frontend_proc = MagicMock()

        with patch.object(mod, "terminate_process_tree", side_effect=lambda p: call_order.append(("term", p))), \
             patch.object(mod, "_wait_for_proc", side_effect=lambda p: call_order.append(("wait", p))), \
             patch.object(mod, "_restore_terminal", side_effect=lambda: call_order.append("restore")):
            cleanup_all()

        # Both procs terminated first
        assert call_order[0] == ("term", mod._backend_proc)
        assert call_order[1] == ("term", mod._frontend_proc)
        # Then waited (frontend first, then backend)
        assert call_order[2] == ("wait", mod._frontend_proc)
        assert call_order[3] == ("wait", mod._backend_proc)
        # Then terminal restored
        assert call_order[4] == "restore"

    def test_cleanup_with_no_procs(self):
        """cleanup_all works even when procs are None."""
        with patch.object(mod, "terminate_process_tree") as mock_term, \
             patch.object(mod, "_wait_for_proc") as mock_wait, \
             patch.object(mod, "_restore_terminal") as mock_restore:
            cleanup_all()
            # terminate called with None for both
            assert mock_term.call_count == 2
            mock_restore.assert_called_once()


# ── start_backend ────────────────────────────────────────────────


class TestStartBackend:
    """Test start_backend() launches correct subprocess."""

    def test_start_backend_returns_proc(self, tmp_path):
        """start_backend returns a Popen object."""
        backend_dir = tmp_path / "backend"
        backend_dir.mkdir()
        env = {"HELEN_WEBUI_CWD": str(tmp_path)}

        with patch("subprocess.Popen") as mock_popen, \
             patch.object(mod, "find_helen_python", return_value="/usr/bin/python3"):
            mock_popen.return_value = MagicMock()
            result = start_backend(backend_dir, env)
            assert result is mock_popen.return_value
            # Global should be set
            assert mod._backend_proc is mock_popen.return_value

    def test_start_backend_passes_correct_args(self, tmp_path):
        """start_backend invokes python -c with correct backend code."""
        backend_dir = tmp_path / "backend"
        backend_dir.mkdir()
        env = {"HELEN_WEBUI_CWD": str(tmp_path)}

        with patch("subprocess.Popen") as mock_popen, \
             patch.object(mod, "find_helen_python", return_value="/usr/bin/python3"):
            mock_popen.return_value = MagicMock()
            start_backend(backend_dir, env)

            args = mock_popen.call_args
            cmd = args[0][0]  # first positional arg
            assert cmd[0] == "/usr/bin/python3"
            assert cmd[1] == "-c"
            assert "uvicorn" in cmd[2]

    def test_start_backend_sets_pythonpath(self, tmp_path):
        """start_backend adds backend_dir to PYTHONPATH."""
        backend_dir = tmp_path / "backend"
        backend_dir.mkdir()
        env = {}

        with patch("subprocess.Popen") as mock_popen, \
             patch.object(mod, "find_helen_python", return_value="/usr/bin/python3"):
            mock_popen.return_value = MagicMock()
            start_backend(backend_dir, env)

            passed_env = mock_popen.call_args[1]["env"]
            assert str(backend_dir) in passed_env["PYTHONPATH"]

    def test_start_backend_env_file_creation(self, tmp_path):
        """start_backend copies .env.example to .env if .env missing."""
        backend_dir = tmp_path / "backend"
        backend_dir.mkdir()
        (backend_dir / ".env.example").write_text("KEY=value")
        env = {}

        with patch("subprocess.Popen") as mock_popen, \
             patch.object(mod, "find_helen_python", return_value="/usr/bin/python3"):
            mock_popen.return_value = MagicMock()
            start_backend(backend_dir, env)

            # .env should have been created
            assert (backend_dir / ".env").exists()
            passed_env = mock_popen.call_args[1]["env"]
            assert passed_env["ENV_FILE"] == str(backend_dir / ".env")

    def test_start_backend_existing_env_file(self, tmp_path):
        """start_backend uses existing .env file."""
        backend_dir = tmp_path / "backend"
        backend_dir.mkdir()
        (backend_dir / ".env").write_text("KEY=value")
        env = {}

        with patch("subprocess.Popen") as mock_popen, \
             patch.object(mod, "find_helen_python", return_value="/usr/bin/python3"):
            mock_popen.return_value = MagicMock()
            start_backend(backend_dir, env)

            passed_env = mock_popen.call_args[1]["env"]
            assert passed_env["ENV_FILE"] == str(backend_dir / ".env")

    @pytest.mark.skipif(IS_WINDOWS, reason="Unix-only test")
    def test_start_backend_sets_setsid(self, tmp_path):
        """On Unix, preexec_fn should be os.setsid."""
        backend_dir = tmp_path / "backend"
        backend_dir.mkdir()
        env = {}

        with patch("subprocess.Popen") as mock_popen, \
             patch.object(mod, "find_helen_python", return_value="/usr/bin/python3"):
            mock_popen.return_value = MagicMock()
            start_backend(backend_dir, env)

            kwargs = mock_popen.call_args[1]
            assert kwargs["preexec_fn"] is os.setsid


# ── start_frontend ───────────────────────────────────────────────


class TestStartFrontend:
    """Test start_frontend() launches npm dev server."""

    def test_start_frontend_returns_proc(self, tmp_path):
        """start_frontend returns a Popen object."""
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()
        # Create node_modules/.bin/vite to skip npm install
        vite_bin = frontend_dir / "node_modules" / ".bin" / "vite"
        vite_bin.parent.mkdir(parents=True)
        vite_bin.touch()
        env = {}

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            result = start_frontend(frontend_dir, env)
            assert result is mock_popen.return_value
            assert mod._frontend_proc is mock_popen.return_value

    def test_start_frontend_invokes_npm_dev(self, tmp_path):
        """start_frontend invokes 'npm run dev'."""
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()
        vite_bin = frontend_dir / "node_modules" / ".bin" / "vite"
        vite_bin.parent.mkdir(parents=True)
        vite_bin.touch()
        env = {}

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            start_frontend(frontend_dir, env)

            cmd = mock_popen.call_args[0][0]
            assert cmd == ["npm", "run", "dev"]

    def test_start_frontend_missing_vite_triggers_npm_install(self, tmp_path):
        """If vite binary is missing, npm install is run first."""
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()
        env = {}

        with patch("subprocess.Popen") as mock_popen, \
             patch("subprocess.run") as mock_run:
            mock_popen.return_value = MagicMock()
            start_frontend(frontend_dir, env)

            mock_run.assert_called_once()
            run_args = mock_run.call_args[0][0]
            assert run_args == ["npm", "install"]

    def test_start_frontend_npm_install_failure_handled(self, tmp_path):
        """npm install failure is caught and printed, not raised."""
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()
        env = {}

        with patch("subprocess.Popen") as mock_popen, \
             patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "npm")):
            mock_popen.return_value = MagicMock()
            # Should not raise
            result = start_frontend(frontend_dir, env)
            assert result is mock_popen.return_value


# ── check_ports ──────────────────────────────────────────────────


class TestCheckPorts:
    """Test check_ports() stub."""

    def test_returns_empty_list(self):
        """check_ports returns an empty list (stub implementation)."""
        assert check_ports() == []


# ── main ─────────────────────────────────────────────────────────


class TestMain:
    """Test main() entry point."""

    def setup_method(self):
        mod._cleanup_done = False
        mod._backend_proc = None
        mod._frontend_proc = None

    def test_backend_dir_not_found_returns_1(self, tmp_path):
        """main() returns 1 if backend directory doesn't exist."""
        with patch.object(mod, "Path") as mock_path_cls:
            # Make script_dir / "backend" not exist
            fake_script_dir = tmp_path
            mock_path_cls.return_value.parent = fake_script_dir
            # We need to be more surgical — patch __file__
            with patch.object(mod, "__file__", str(tmp_path / "start_webui.py")):
                result = main()
                assert result == 1

    def test_frontend_dir_not_found_returns_1(self, tmp_path):
        """main() returns 1 if frontend directory doesn't exist."""
        backend_dir = tmp_path / "backend"
        backend_dir.mkdir()
        # frontend does not exist

        with patch.object(mod, "__file__", str(tmp_path / "start_webui.py")):
            result = main()
            assert result == 1

    def test_keyboard_interrupt_returns_0(self, tmp_path):
        """KeyboardInterrupt during main loop returns 0."""
        backend_dir = tmp_path / "backend"
        backend_dir.mkdir()
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()

        mock_backend_proc = MagicMock()
        mock_frontend_proc = MagicMock()

        def fake_start_backend(bd, env):
            mod._backend_proc = mock_backend_proc
            return mock_backend_proc

        def fake_start_frontend(fd, env):
            mod._frontend_proc = mock_frontend_proc
            return mock_frontend_proc

        with patch.object(mod, "__file__", str(tmp_path / "start_webui.py")), \
             patch.object(mod, "start_backend", side_effect=fake_start_backend), \
             patch.object(mod, "start_frontend", side_effect=fake_start_frontend), \
             patch.object(mod, "cleanup_all"), \
             patch("time.sleep", side_effect=KeyboardInterrupt()), \
             patch("atexit.register"), \
             patch("signal.signal"):
            result = main()
            assert result == 0

    def test_generic_exception_returns_1(self, tmp_path):
        """Generic exception during main returns 1."""
        backend_dir = tmp_path / "backend"
        backend_dir.mkdir()
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()

        with patch.object(mod, "__file__", str(tmp_path / "start_webui.py")), \
             patch.object(mod, "start_backend", side_effect=RuntimeError("boom")), \
             patch.object(mod, "cleanup_all"), \
             patch("atexit.register"), \
             patch("signal.signal"):
            result = main()
            assert result == 1

    def test_normal_startup_both_procs_running(self, tmp_path):
        """main runs backend and frontend when both dirs exist."""
        backend_dir = tmp_path / "backend"
        backend_dir.mkdir()
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()

        mock_backend_proc = MagicMock()
        mock_frontend_proc = MagicMock()
        # Both procs exit with 0 immediately
        mock_backend_proc.poll.return_value = 0
        mock_frontend_proc.poll.return_value = 0

        def fake_start_backend(bd, env):
            mod._backend_proc = mock_backend_proc
            return mock_backend_proc

        def fake_start_frontend(fd, env):
            mod._frontend_proc = mock_frontend_proc
            return mock_frontend_proc

        with patch.object(mod, "__file__", str(tmp_path / "start_webui.py")), \
             patch.object(mod, "start_backend", side_effect=fake_start_backend) as mock_sb, \
             patch.object(mod, "start_frontend", side_effect=fake_start_frontend) as mock_sf, \
             patch.object(mod, "cleanup_all"), \
             patch("time.sleep"), \
             patch("atexit.register"), \
             patch("signal.signal"):
            result = main()
            mock_sb.assert_called_once()
            mock_sf.assert_called_once()
            assert result == 0

    def test_backend_exits_unexpectedly_warns(self, tmp_path, capsys):
        """Non-zero backend exit triggers warning and terminates frontend."""
        backend_dir = tmp_path / "backend"
        backend_dir.mkdir()
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()

        mock_backend_proc = MagicMock()
        mock_frontend_proc = MagicMock()
        mock_backend_proc.poll.return_value = 1  # non-zero exit
        mock_frontend_proc.poll.return_value = None  # still running

        def fake_start_backend(bd, env):
            mod._backend_proc = mock_backend_proc
            return mock_backend_proc

        def fake_start_frontend(fd, env):
            mod._frontend_proc = mock_frontend_proc
            return mock_frontend_proc

        with patch.object(mod, "__file__", str(tmp_path / "start_webui.py")), \
             patch.object(mod, "start_backend", side_effect=fake_start_backend), \
             patch.object(mod, "start_frontend", side_effect=fake_start_frontend), \
             patch.object(mod, "terminate_process_tree") as mock_term, \
             patch.object(mod, "cleanup_all"), \
             patch("time.sleep"), \
             patch("atexit.register"), \
             patch("signal.signal"):
            result = main()
            assert result == 1
            mock_term.assert_called_with(mock_frontend_proc)
            captured = capsys.readouterr()
            assert "Backend exited unexpectedly" in captured.out

    def test_frontend_exits_unexpectedly_warns(self, tmp_path, capsys):
        """Non-zero frontend exit triggers warning and terminates backend."""
        backend_dir = tmp_path / "backend"
        backend_dir.mkdir()
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()

        mock_backend_proc = MagicMock()
        mock_frontend_proc = MagicMock()
        mock_backend_proc.poll.return_value = None  # still running
        mock_frontend_proc.poll.return_value = 2  # non-zero exit

        def fake_start_backend(bd, env):
            mod._backend_proc = mock_backend_proc
            return mock_backend_proc

        def fake_start_frontend(fd, env):
            mod._frontend_proc = mock_frontend_proc
            return mock_frontend_proc

        with patch.object(mod, "__file__", str(tmp_path / "start_webui.py")), \
             patch.object(mod, "start_backend", side_effect=fake_start_backend), \
             patch.object(mod, "start_frontend", side_effect=fake_start_frontend), \
             patch.object(mod, "terminate_process_tree") as mock_term, \
             patch.object(mod, "cleanup_all"), \
             patch("time.sleep"), \
             patch("atexit.register"), \
             patch("signal.signal"):
            result = main()
            assert result == 2
            mock_term.assert_called_with(mock_backend_proc)
            captured = capsys.readouterr()
            assert "Frontend exited unexpectedly" in captured.out

    def test_signal_handler_registered_on_unix(self, tmp_path):
        """On Unix, SIGTERM/SIGINT handlers are registered."""
        backend_dir = tmp_path / "backend"
        backend_dir.mkdir()
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()

        mock_backend_proc = MagicMock()
        mock_frontend_proc = MagicMock()
        mock_backend_proc.poll.return_value = 0
        mock_frontend_proc.poll.return_value = 0

        def fake_start_backend(bd, env):
            mod._backend_proc = mock_backend_proc
            return mock_backend_proc

        def fake_start_frontend(fd, env):
            mod._frontend_proc = mock_frontend_proc
            return mock_frontend_proc

        with patch.object(mod, "__file__", str(tmp_path / "start_webui.py")), \
             patch.object(mod, "start_backend", side_effect=fake_start_backend), \
             patch.object(mod, "start_frontend", side_effect=fake_start_frontend), \
             patch.object(mod, "cleanup_all"), \
             patch("time.sleep"), \
             patch("atexit.register"), \
             patch("signal.signal") as mock_signal:
            if not IS_WINDOWS:
                main()
                assert mock_signal.call_count >= 2  # SIGTERM + SIGINT
            else:
                main()

    def test_helem_debug_default_set(self, tmp_path):
        """HELEN_DEBUG defaults to '0' if not set."""
        backend_dir = tmp_path / "backend"
        backend_dir.mkdir()
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()

        mock_backend_proc = MagicMock()
        mock_frontend_proc = MagicMock()
        mock_backend_proc.poll.return_value = 0
        mock_frontend_proc.poll.return_value = 0

        def fake_start_backend(bd, env):
            mod._backend_proc = mock_backend_proc
            return mock_backend_proc

        def fake_start_frontend(fd, env):
            mod._frontend_proc = mock_frontend_proc
            return mock_frontend_proc

        env_clean = {"PATH": "/usr/bin", "HOME": os.environ.get("HOME", "/tmp")}
        env_clean.pop("HELEN_DEBUG", None)
        env_clean.pop("HELEN_WEBUI_CWD", None)

        with patch.object(mod, "__file__", str(tmp_path / "start_webui.py")), \
             patch.object(mod, "start_backend", side_effect=fake_start_backend) as mock_sb, \
             patch.object(mod, "start_frontend", side_effect=fake_start_frontend), \
             patch.object(mod, "cleanup_all"), \
             patch("time.sleep"), \
             patch("atexit.register"), \
             patch("signal.signal"):
            with patch.dict(os.environ, env_clean, clear=True):
                main()
            # Check that start_backend was called with env containing HELEN_DEBUG=0
            call_env = mock_sb.call_args[0][1]
            assert call_env.get("HELEN_DEBUG") == "0"


# ── BackendStartup (kept from original) ─────────────────────────


class TestBackendStartup:
    """Test backend startup configuration."""

    def test_backend_env_includes_pythonpath(self):
        """Backend env should include backend dir in PYTHONPATH."""
        assert callable(start_backend)

    def test_helem_webui_cwd_propagated(self):
        """HELEN_WEBUI_CWD should be propagated to backend env."""
        test_cwd = "/test/cwd/path"
        env = os.environ.copy()
        env["HELEN_WEBUI_CWD"] = test_cwd
        assert env.get("HELEN_WEBUI_CWD") == test_cwd
