"""Security sandbox utilities for Helen runtime.

Provides path validation, URL filtering, and resource limits
to prevent common attack vectors (path traversal, SSRF, etc.).
"""

from __future__ import annotations

import ipaddress
import os
import socket
from typing import Final
from urllib.parse import urlparse

# ── Path Safety ────────────────────────────────────────────────

# Directories that should never be accessible
_BLOCKED_PATHS: Final[frozenset[str]] = frozenset({
    "/etc/shadow", "/etc/passwd", "/etc/sudoers",
    "/proc", "/sys", "/dev",
})

# Maximum file size for read operations (16 MB)
MAX_READ_SIZE: Final[int] = 16 * 1024 * 1024

# Maximum file size for write operations (64 MB)
MAX_WRITE_SIZE: Final[int] = 64 * 1024 * 1024

# Maximum download size (100 MB)
MAX_DOWNLOAD_SIZE: Final[int] = 100 * 1024 * 1024


def validate_path(
    path: str,
    *,
    base_dir: str | None = None,
    must_exist: bool = False,
    allow_absolute: bool = False,
) -> str:
    """Validate and resolve a file path with security checks.

    Args:
        path: The path to validate.
        base_dir: If set, the resolved path must be within this directory.
        must_exist: If True, raise if the path does not exist.
        allow_absolute: If True, allow absolute paths outside base_dir.

    Returns:
        The resolved absolute path.

    Raises:
        SecurityError: If the path violates security constraints.
    """
    resolved = os.path.realpath(os.path.abspath(path))

    # Check blocked paths
    for blocked in _BLOCKED_PATHS:
        if resolved == blocked or resolved.startswith(blocked + os.sep):
            raise SecurityError(f"Access denied: path is in a blocked directory: {path}")

    # Check base_dir containment
    if base_dir is not None:
        abs_base = os.path.realpath(os.path.abspath(base_dir))
        if not (resolved.startswith(abs_base + os.sep) or resolved == abs_base):
            if not allow_absolute:
                raise SecurityError(
                    f"Path traversal detected: '{path}' resolves outside "
                    f"base directory '{base_dir}'"
                )

    if must_exist and not os.path.exists(resolved):
        raise SecurityError(f"Path does not exist: {path}")

    return resolved


def validate_path_exists(path: str, *, base_dir: str | None = None) -> str:
    """Validate that a path exists and is accessible.

    Returns:
        The resolved absolute path.

    Raises:
        SecurityError: If the path doesn't exist or is blocked.
    """
    return validate_path(path, base_dir=base_dir, must_exist=True)


# ── URL Safety (SSRF Protection) ──────────────────────────────

# Private/reserved IP ranges that should not be accessible
_BLOCKED_NETWORKS: Final[list] = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
]

# Allowed URL schemes
_ALLOWED_SCHEMES: Final[frozenset[str]] = frozenset({"http", "https"})

# Default request timeout (seconds)
DEFAULT_REQUEST_TIMEOUT: Final[int] = 30

# Maximum response body size (8 MB)
MAX_RESPONSE_SIZE: Final[int] = 8 * 1024 * 1024


def validate_url(url: str, *, allow_private: bool = False) -> str:
    """Validate a URL for safety (SSRF protection).

    Args:
        url: The URL to validate.
        allow_private: If True, allow private/internal IP addresses.

    Returns:
        The validated URL.

    Raises:
        SecurityError: If the URL is unsafe.
    """
    parsed = urlparse(url)

    # Check scheme
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise SecurityError(
            f"URL scheme '{parsed.scheme}' is not allowed. "
            f"Only {sorted(_ALLOWED_SCHEMES)} are permitted."
        )

    # Check hostname exists
    hostname = parsed.hostname
    if not hostname:
        raise SecurityError(f"URL has no hostname: {url}")

    # Block localhost variants
    blocked_hosts = {"localhost", "0.0.0.0", "127.0.0.1", "::1", "[::1]"}
    if hostname.lower() in blocked_hosts:
        raise SecurityError(f"Access to localhost is not allowed: {url}")

    # Resolve hostname and check against private networks
    if not allow_private:
        try:
            addr_infos = socket.getaddrinfo(hostname, None)
            for family, _type, _proto, _canonname, sockaddr in addr_infos:
                ip_str = sockaddr[0]
                try:
                    ip_addr = ipaddress.ip_address(ip_str)
                    for network in _BLOCKED_NETWORKS:
                        if ip_addr in network:
                            raise SecurityError(
                                f"URL resolves to private/reserved IP "
                                f"{ip_str}: {url}"
                            )
                except ValueError:
                    pass  # Not a valid IP, skip
        except socket.gaierror:
            raise SecurityError(f"Cannot resolve hostname: {hostname}")

    return url


# ── Command Safety ─────────────────────────────────────────────

# Dangerous commands that should be blocked
_BLOCKED_COMMANDS: Final[frozenset[str]] = frozenset({
    "rm -rf /", "rm -rf /*", "mkfs", "dd if=/dev/zero",
    ":(){:|:&};:",  # fork bomb
    "chmod -R 777 /", "chown -R",
})

# Maximum command timeout (seconds)
MAX_COMMAND_TIMEOUT: Final[int] = 300


def validate_command(command: str | list[str]) -> str | list[str]:
    """Validate a command for safety.

    Args:
        command: The command string or list to validate.

    Returns:
        The validated command.

    Raises:
        SecurityError: If the command is dangerous.
    """
    cmd_str = command if isinstance(command, str) else " ".join(command)

    for blocked in _BLOCKED_COMMANDS:
        if blocked in cmd_str:
            raise SecurityError(f"Dangerous command blocked: {blocked}")

    return command


# ── Environment Safety ─────────────────────────────────────────

# Sensitive environment variable patterns that should be masked
_SENSITIVE_PATTERNS: Final[frozenset[str]] = frozenset({
    "PASSWORD", "SECRET", "TOKEN", "API_KEY", "PRIVATE_KEY",
    "CREDENTIAL", "AUTH", "SESSION",
})


def mask_env_value(key: str, value: str) -> str:
    """Mask sensitive environment variable values.

    Args:
        key: Environment variable name.
        value: Environment variable value.

    Returns:
        The value, or a masked version if the key is sensitive.
    """
    key_upper = key.upper()
    for pattern in _SENSITIVE_PATTERNS:
        if pattern in key_upper:
            if len(value) <= 4:
                return "****"
            return value[:2] + "****" + value[-2:]
    return value


def safe_env_list() -> dict[str, str]:
    """Return environment variables with sensitive values masked.

    Returns:
        Dict of environment variables with sensitive values masked.
    """
    result = {}
    for key, value in os.environ.items():
        result[key] = mask_env_value(key, value)
    return result


# ── Process Safety ─────────────────────────────────────────────

def validate_kill_signal(signal_num: int) -> int:
    """Validate that a signal number is safe to send.

    Only allows common safe signals (SIGTERM, SIGINT, SIGHUP, etc.).

    Args:
        signal_num: The signal number.

    Returns:
        The validated signal number.

    Raises:
        SecurityError: If the signal is dangerous.
    """
    import signal as sig_module
    allowed = {
        sig_module.SIGTERM, sig_module.SIGINT, sig_module.SIGHUP,
        sig_module.SIGUSR1, sig_module.SIGUSR2,
    }
    if signal_num not in allowed:
        raise SecurityError(
            f"Signal {signal_num} is not allowed. "
            f"Allowed signals: {sorted(s for s in allowed)}"
        )
    return signal_num


def validate_pid(pid: int, current_pid: int | None = None) -> int:
    """Validate that a PID is safe to operate on.

    Prevents killing the current process or system processes (PID 0, 1).

    Args:
        pid: The process ID.
        current_pid: The current process ID (defaults to os.getpid()).

    Returns:
        The validated PID.

    Raises:
        SecurityError: If the PID is protected.
    """
    if current_pid is None:
        current_pid = os.getpid()

    if pid <= 1:
        raise SecurityError(f"Cannot operate on system process: PID {pid}")
    if pid == current_pid:
        raise SecurityError("Cannot operate on the current process")

    return pid


# ── Exception ──────────────────────────────────────────────────


class SecurityError(Exception):
    """Raised when a security constraint is violated."""
    pass
