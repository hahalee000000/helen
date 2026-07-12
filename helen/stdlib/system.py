"""System module for Helen stdlib.

Provides environment, process, and logging operations.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from typing import Any


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
    """List all environment variables.

    Returns:
        Dict of environment variables.
    """
    return dict(os.environ)


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


# ── CLI argument operations ────────────────────────────────────

# Module-level storage for CLI arguments, set by the Interpreter on init.
_cli_args: list[str] = []


def _set_cli_args(args: list[str]) -> None:
    """Set the CLI arguments (called by the Interpreter during init).

    This is an internal function — not exposed as a Helen builtin.

    Args:
        args: List of CLI argument strings.
    """
    global _cli_args
    _cli_args = list(args)


def _get_cli_args() -> list[str]:
    """Get CLI arguments passed to the Helen program.

    Returns a list of string arguments that were passed after the
    filename on the command line.

    Returns:
        List of CLI argument strings (empty list if none).

    Example:
        // Given: helen my_tool.helen --verbose --output=json
        let args = get_cli_args()  // ["--verbose", "--output=json"]
    """
    return list(_cli_args)


def _parse_cli_args(spec: dict | None = None) -> dict[str, Any]:
    """Parse CLI arguments into a structured map.

    Without a spec, automatically parses arguments:
    - Flags (--verbose, -v) → true/false
    - Key-value (--output=json, --port=8080) → string values
    - Positional arguments → list under key "_positional"

    With a spec dict, validates and applies defaults:
    - {"verbose": {"type": "flag", "default": false}}
    - {"output": {"type": "string", "default": "text"}}
    - {"count": {"type": "int", "default": 1}}

    Args:
        spec: Optional specification for expected arguments.

    Returns:
        Dict mapping argument names to their parsed values.
        Always includes "_positional" key with list of positional args.
    """
    args = list(_cli_args)
    result: dict[str, Any] = {"_positional": []}

    if spec is None:
        # Auto-parse mode
        i = 0
        while i < len(args):
            arg = args[i]
            if arg.startswith("--"):
                if "=" in arg:
                    key, _, value = arg[2:].partition("=")
                    result[key] = value
                else:
                    key = arg[2:]
                    # Check if next arg is a value (not a flag)
                    if i + 1 < len(args) and not args[i + 1].startswith("-"):
                        result[key] = args[i + 1]
                        i += 1
                    else:
                        result[key] = True
            elif arg.startswith("-") and len(arg) == 2:
                # Short flag: -v, -q, etc.
                result[arg[1:]] = True
            else:
                result["_positional"].append(arg)
            i += 1
    else:
        # Spec-driven parse mode: apply defaults first
        for name, cfg in spec.items():
            if isinstance(cfg, dict):
                default = cfg.get("default", None)
            else:
                default = None
            result[name] = default

        i = 0
        while i < len(args):
            arg = args[i]
            if arg.startswith("--"):
                if "=" in arg:
                    key, _, value = arg[2:].partition("=")
                    if key in spec:
                        cfg = spec[key]
                        if isinstance(cfg, dict) and cfg.get("type") == "int":
                            try:
                                result[key] = int(value)
                            except ValueError:
                                result[key] = value
                        elif isinstance(cfg, dict) and cfg.get("type") == "float":
                            try:
                                result[key] = float(value)
                            except ValueError:
                                result[key] = value
                        else:
                            result[key] = value
                    else:
                        result[key] = value
                else:
                    key = arg[2:]
                    if key in spec:
                        cfg = spec[key]
                        if isinstance(cfg, dict) and cfg.get("type") == "flag":
                            result[key] = True
                        elif i + 1 < len(args) and not args[i + 1].startswith("-"):
                            i += 1
                            val = args[i]
                            if isinstance(cfg, dict) and cfg.get("type") == "int":
                                try:
                                    result[key] = int(val)
                                except ValueError:
                                    result[key] = val
                            elif isinstance(cfg, dict) and cfg.get("type") == "float":
                                try:
                                    result[key] = float(val)
                                except ValueError:
                                    result[key] = val
                            else:
                                result[key] = val
                        else:
                            result[key] = True if isinstance(cfg, dict) and cfg.get("type") == "flag" else None
                    else:
                        # Unknown flag — treat as flag
                        result[key] = True
            elif arg.startswith("-") and len(arg) >= 2:
                # Short flag(s): -v or -abc (multiple short flags)
                for ch in arg[1:]:
                    if ch in spec:
                        result[ch] = True
                    else:
                        result[ch] = True
            else:
                result["_positional"].append(arg)
            i += 1

    return result


# ── Process operations ─────────────────────────────────────────


def _exec(command: str, shell: bool = False, timeout: int | None = None) -> dict[str, Any]:
    """Execute command and wait for result.

    Args:
        command: Command to execute
        shell: Whether to use shell (default: False)
        timeout: Timeout in seconds

    Returns:
        Dict with keys: returncode, stdout, stderr

    Raises:
        TimeoutError: If command times out
    """
    import shlex
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
        shell: Whether to use shell (default: False)

    Returns:
        Process ID
    """
    import shlex
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
    """
    try:
        os.kill(pid, signal_num)
        return f"Sent signal {signal_num} to process {pid}"
    except ProcessLookupError:
        raise ProcessLookupError(f"Process {pid} not found")


# ── Logging operations ─────────────────────────────────────────


# Configure logging
_logger = logging.getLogger("helen")
_logger.setLevel(logging.INFO)

# Create console handler
_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.INFO)

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
