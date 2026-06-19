"""System module for Helen stdlib.

Provides environment, process, and logging operations.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from typing import Any

from helen.runtime.security import (
    validate_command, validate_pid, validate_kill_signal,
    safe_env_list,
)


# ── Environment operations ─────────────────────────────────────


def _env_get(key: str, default: str | None = None) -> str | None:
    """Get environment variable.

    Args:
        key: Environment variable name
        default: Default value if not found

    Returns:
        Environment variable value or default
    """
    return os.environ.get(key, default)


def _env_set(key: str, value: str) -> str:
    """Set environment variable.

    Args:
        key: Environment variable name
        value: Value to set

    Returns:
        Success message
    """
    os.environ[key] = value
    return f"Set {key}={value}"


def _env_list() -> dict[str, str]:
    """List all environment variables (sensitive values masked).

    Returns:
        Dict of environment variables with sensitive values masked.
    """
    return safe_env_list()


def _env_delete(key: str) -> str:
    """Delete environment variable.

    Args:
        key: Environment variable name

    Returns:
        Success message
    """
    if key in os.environ:
        del os.environ[key]
        return f"Deleted {key}"
    return f"Variable {key} not found"


# ── Process operations ─────────────────────────────────────────


def _exec(command: str, shell: bool = False, timeout: int | None = None) -> dict[str, Any]:
    """Execute command and wait for result.

    Args:
        command: Command to execute
        shell: Whether to use shell (default: False for safety)
        timeout: Timeout in seconds

    Returns:
        Dict with keys: returncode, stdout, stderr

    Raises:
        TimeoutError: If command times out
        SecurityError: If command is blocked
    """
    import shlex
    validate_command(command)
    cmd = command if shell else shlex.split(command)
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired as e:
        raise TimeoutError(f"Command timed out after {timeout}s") from e


def _exec_async(command: str, shell: bool = False) -> int:
    """Execute command asynchronously.

    Args:
        command: Command to execute
        shell: Whether to use shell (default: False for safety)

    Returns:
        Process ID
    """
    import shlex
    validate_command(command)
    cmd = command if shell else shlex.split(command)
    process = subprocess.Popen(
        cmd,
        shell=shell,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return process.pid


def _pid() -> int:
    """Get current process ID.

    Returns:
        Process ID
    """
    return os.getpid()


def _exit(code: int = 0) -> None:
    """Exit program.

    Args:
        code: Exit code (default: 0)
    """
    sys.exit(code)


def _kill(pid: int, signal_num: int = 15) -> str:
    """Send signal to process.

    Args:
        pid: Process ID
        signal_num: Signal number (default: 15 = SIGTERM)

    Returns:
        Success message

    Raises:
        ProcessLookupError: If process doesn't exist
        SecurityError: If pid or signal is not allowed
    """
    validate_pid(pid)
    validate_kill_signal(signal_num)
    try:
        os.kill(pid, signal_num)
        return f"Sent signal {signal_num} to process {pid}"
    except ProcessLookupError:
        raise ProcessLookupError(f"Process {pid} not found")


# ── Logging operations ─────────────────────────────────────────


# Configure logging
_logger = logging.getLogger("helen")
_logger.setLevel(logging.DEBUG)

# Create console handler
_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.DEBUG)

# Create formatter
_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_console_handler.setFormatter(_formatter)

# Add handler to logger
if not _logger.handlers:
    _logger.addHandler(_console_handler)


def _log_debug(message: str) -> str:
    """Log debug message.

    Args:
        message: Message to log

    Returns:
        Formatted log message
    """
    _logger.debug(message)
    return f"[DEBUG] {message}"


def _log_info(message: str) -> str:
    """Log info message.

    Args:
        message: Message to log

    Returns:
        Formatted log message
    """
    _logger.info(message)
    return f"[INFO] {message}"


def _log_warn(message: str) -> str:
    """Log warning message.

    Args:
        message: Message to log

    Returns:
        Formatted log message
    """
    _logger.warning(message)
    return f"[WARNING] {message}"


def _log_error(message: str) -> str:
    """Log error message.

    Args:
        message: Message to log

    Returns:
        Formatted log message
    """
    _logger.error(message)
    return f"[ERROR] {message}"


def _log_critical(message: str) -> str:
    """Log critical message.

    Args:
        message: Message to log

    Returns:
        Formatted log message
    """
    _logger.critical(message)
    return f"[CRITICAL] {message}"


def _log_set_level(level: str) -> str:
    """Set logging level.

    Args:
        level: Log level (DEBUG, INFO, WARN, ERROR, CRITICAL)

    Returns:
        Success message

    Raises:
        ValueError: If level is invalid
    """
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARN": logging.WARNING,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    level_upper = level.upper()
    if level_upper not in level_map:
        raise ValueError(f"Invalid log level: {level}. Must be one of {list(level_map.keys())}")

    _logger.setLevel(level_map[level_upper])
    _console_handler.setLevel(level_map[level_upper])
    return f"Log level set to {level_upper}"


def _log_to_file(path: str) -> str:
    """Set log output to file.

    Args:
        path: Log file path

    Returns:
        Success message
    """
    file_handler = logging.FileHandler(path)
    file_handler.setLevel(_logger.level)
    file_handler.setFormatter(_formatter)
    _logger.addHandler(file_handler)
    return f"Logging to file: {path}"
