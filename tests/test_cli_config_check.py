"""Integration tests for CLI config preflight check."""
import subprocess
import sys
import tempfile
from pathlib import Path


# Get the helen executable path
HELEN_CMD = [sys.executable, "-c", "from helen.cli.__main__ import main; import sys; sys.exit(main())"]


def test_cli_prompts_wizard_when_not_configured():
    """Test that CLI shows error when not configured in non-TTY mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Run helen with empty HOME
        env = {
            "HOME": tmpdir,
            "PATH": "/usr/bin:/bin",
        }

        result = subprocess.run(
            HELEN_CMD,
            env=env,
            input="\n\n\n",  # Accept defaults
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Should show error in non-TTY mode
        assert result.returncode != 0
        assert "not configured" in result.stderr


def test_cli_skips_config_for_init():
    """Test that init command skips config check."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env = {
            "HOME": tmpdir,
            "PATH": "/usr/bin:/bin",
        }

        result = subprocess.run(
            HELEN_CMD + ["init"],
            env=env,
            input="\n\n\n",  # Provide input for wizard
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Should create Helen home and skills directory
        assert "Helen home:" in result.stdout
        assert "Skills directory:" in result.stdout
        # Wizard will fail in non-TTY mode, but that's expected
        assert "Helen Setup Wizard" in result.stdout or result.returncode == 0


def test_cli_skips_config_for_check():
    """Test that check command skips config check."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test file
        test_file = Path(tmpdir) / "test.helen"
        test_file.write_text('print("hello");')

        env = {
            "HOME": tmpdir,
            "PATH": "/usr/bin:/bin",
        }

        result = subprocess.run(
            HELEN_CMD + ["check", str(test_file)],
            env=env,
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Should not error about missing config
        assert "not configured" not in result.stderr


def test_cli_skips_config_for_version():
    """Test that --version skips config check."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env = {
            "HOME": tmpdir,
            "PATH": "/usr/bin:/bin",
        }

        result = subprocess.run(
            HELEN_CMD + ["--version"],
            env=env,
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Should show version without config error
        assert result.returncode == 0
        assert "Helen" in result.stdout
        assert "not configured" not in result.stderr


def test_cli_skips_config_for_help():
    """Test that --help skips config check."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env = {
            "HOME": tmpdir,
            "PATH": "/usr/bin:/bin",
        }

        result = subprocess.run(
            HELEN_CMD + ["--help"],
            env=env,
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Should show help without config error
        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "helen" in result.stdout.lower()
        assert "not configured" not in result.stderr


def test_cli_errors_when_not_configured_non_tty():
    """Test that CLI errors in non-TTY mode when not configured."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env = {
            "HOME": tmpdir,
            "PATH": "/usr/bin:/bin",
        }

        # Run without TTY (subprocess default)
        result = subprocess.run(
            HELEN_CMD + ["repl"],
            env=env,
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Should error about missing config
        assert result.returncode != 0
        assert "not configured" in result.stderr


def test_cli_works_with_env_var():
    """Test that CLI works when HELEN_API_KEY is set."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env = {
            "HOME": tmpdir,
            "PATH": "/usr/bin:/bin",
            "HELEN_API_KEY": "test-key-123",
        }

        # Create a simple Helen file
        test_file = Path(tmpdir) / "test.helen"
        test_file.write_text('let x = 42;')

        # Run check (doesn't need LLM, but should not error about config)
        result = subprocess.run(
            HELEN_CMD + ["check", str(test_file)],
            env=env,
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Should not error about missing config
        assert "not configured" not in result.stderr


def test_cli_config_check_for_file_run():
    """Test that running a file triggers config check."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a simple Helen file
        test_file = Path(tmpdir) / "test.helen"
        test_file.write_text('print("hello");')

        env = {
            "HOME": tmpdir,
            "PATH": "/usr/bin:/bin",
        }

        # Run without TTY - should error about config
        result = subprocess.run(
            HELEN_CMD + [str(test_file)],
            env=env,
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Should error about missing config (non-TTY)
        assert result.returncode != 0
        assert "not configured" in result.stderr


def test_cli_config_check_for_test_command():
    """Test that test command triggers config check."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env = {
            "HOME": tmpdir,
            "PATH": "/usr/bin:/bin",
        }

        # Run test without TTY - should error about config
        result = subprocess.run(
            HELEN_CMD + ["test", "nonexistent.helen"],
            env=env,
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Should error about missing config (non-TTY)
        assert result.returncode != 0
        assert "not configured" in result.stderr
