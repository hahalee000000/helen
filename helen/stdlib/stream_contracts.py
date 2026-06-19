"""Stream output contracts for Helen standard library (Phase 1).

This module defines the interface contracts for stream output functions.
Implementation will follow TDD after tests are written.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class StreamPrintFunction(Protocol):
    """Contract for stream_print function.

    Prints text without newline, enabling incremental output.
    Returns the printed text for chaining.
    """

    def __call__(self, text: str) -> str:
        """Print text without newline.

        Args:
            text: Text to print (no newline appended)

        Returns:
            The printed text
        """
        ...


@runtime_checkable
class StreamClearFunction(Protocol):
    """Contract for stream_clear function.

    Clears the current line using ANSI escape codes.
    """

    def __call__(self) -> str:
        """Clear current line.

        Returns:
            Empty string
        """
        ...


@runtime_checkable
class ProgressBarFunction(Protocol):
    """Contract for progress_bar function.

    Displays a progress bar with percentage.
    """

    def __call__(self, current: int, total: int, width: int = 40) -> str:
        """Display progress bar.

        Args:
            current: Current progress value
            total: Total value (100% = total)
            width: Width of progress bar in characters (default 40)

        Returns:
            The progress bar string
        """
        ...


@runtime_checkable
class StreamCursorUpFunction(Protocol):
    """Contract for stream_cursor_up function.

    Moves cursor up n lines.
    """

    def __call__(self, n: int = 1) -> str:
        """Move cursor up n lines.

        Args:
            n: Number of lines to move up (default 1)

        Returns:
            Empty string
        """
        ...


@runtime_checkable
class StreamCursorDownFunction(Protocol):
    """Contract for stream_cursor_down function.

    Moves cursor down n lines.
    """

    def __call__(self, n: int = 1) -> str:
        """Move cursor down n lines.

        Args:
            n: Number of lines to move down (default 1)

        Returns:
            Empty string
        """
        ...
