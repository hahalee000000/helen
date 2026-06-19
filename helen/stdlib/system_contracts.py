"""System module contracts for Helen stdlib.

Defines interfaces for environment, process, and logging operations.
"""

from __future__ import annotations

from typing import Any


class EnvContract:
    """Contract for environment variable operations."""

    @staticmethod
    def env_get(key: str, default: str | None = None) -> str | None:
        """Get environment variable.

        Args:
            key: Environment variable name
            default: Default value if not found

        Returns:
            Environment variable value or default
        """
        ...

    @staticmethod
    def env_set(key: str, value: str) -> str:
        """Set environment variable.

        Args:
            key: Environment variable name
            value: Value to set

        Returns:
            Success message
        """
        ...

    @staticmethod
    def env_list() -> dict[str, str]:
        """List all environment variables.

        Returns:
            Dict of environment variables
        """
        ...

    @staticmethod
    def env_delete(key: str) -> str:
        """Delete environment variable.

        Args:
            key: Environment variable name

        Returns:
            Success message
        """
        ...


class ProcessContract:
    """Contract for process operations."""

    @staticmethod
    def exec(command: str, shell: bool = True, timeout: int | None = None) -> dict[str, Any]:
        """Execute command and wait for result.

        Args:
            command: Command to execute
            shell: Whether to use shell
            timeout: Timeout in seconds

        Returns:
            Dict with keys: returncode, stdout, stderr

        Raises:
            TimeoutError: If command times out
        """
        ...

    @staticmethod
    def exec_async(command: str, shell: bool = True) -> int:
        """Execute command asynchronously.

        Args:
            command: Command to execute
            shell: Whether to use shell

        Returns:
            Process ID
        """
        ...

    @staticmethod
    def pid() -> int:
        """Get current process ID.

        Returns:
            Process ID
        """
        ...

    @staticmethod
    def exit(code: int = 0) -> None:
        """Exit program.

        Args:
            code: Exit code (default: 0)
        """
        ...

    @staticmethod
    def kill(pid: int, signal: int = 15) -> str:
        """Send signal to process.

        Args:
            pid: Process ID
            signal: Signal number (default: 15 = SIGTERM)

        Returns:
            Success message

        Raises:
            ProcessLookupError: If process doesn't exist
        """
        ...


class LogContract:
    """Contract for logging operations."""

    @staticmethod
    def log_debug(message: str) -> str:
        """Log debug message.

        Args:
            message: Message to log

        Returns:
            Formatted log message
        """
        ...

    @staticmethod
    def log_info(message: str) -> str:
        """Log info message.

        Args:
            message: Message to log

        Returns:
            Formatted log message
        """
        ...

    @staticmethod
    def log_warn(message: str) -> str:
        """Log warning message.

        Args:
            message: Message to log

        Returns:
            Formatted log message
        """
        ...

    @staticmethod
    def log_error(message: str) -> str:
        """Log error message.

        Args:
            message: Message to log

        Returns:
            Formatted log message
        """
        ...

    @staticmethod
    def log_critical(message: str) -> str:
        """Log critical message.

        Args:
            message: Message to log

        Returns:
            Formatted log message
        """
        ...

    @staticmethod
    def log_set_level(level: str) -> str:
        """Set logging level.

        Args:
            level: Log level (DEBUG, INFO, WARN, ERROR, CRITICAL)

        Returns:
            Success message
        """
        ...

    @staticmethod
    def log_to_file(path: str) -> str:
        """Set log output to file.

        Args:
            path: Log file path

        Returns:
            Success message
        """
        ...
