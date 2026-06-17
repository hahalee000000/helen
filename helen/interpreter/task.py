"""Task and AggregateError for async/await semantics (HLD 3.6.7).

Task wraps an async agent call and provides Promise-like semantics.
AggregateError is defined in helen.interpreter.exceptions and imported here
for convenience.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from helen.interpreter.exceptions import AggregateError  # noqa: F401 — re-exported


@dataclass
class Task:
    """Represents an async agent call (HLD 3.6.7).

    Wraps the result or exception of an async operation.
    Supports Promise.all semantics via await [list].
    """

    result_value: Any = None
    exception: Exception | None = None
    _done: bool = False

    @classmethod
    def completed(cls, result: Any) -> "Task":
        """Create a completed task with a result."""
        return cls(result_value=result, exception=None, _done=True)

    @classmethod
    def failed(cls, exc: Exception) -> "Task":
        """Create a completed task with an exception."""
        return cls(result_value=None, exception=exc, _done=True)

    @property
    def is_done(self) -> bool:
        """Whether the task has completed (success or failure)."""
        return self._done

    @property
    def has_error(self) -> bool:
        """Whether the task completed with an exception."""
        return self.exception is not None

    def result(self) -> Any:
        """Get the result or raise the exception.

        Returns:
            The task result if successful.

        Raises:
            The stored exception if the task failed.
        """
        if not self._done:
            raise RuntimeError("Task is not yet complete")
        if self.exception is not None:
            raise self.exception
        return self.result_value


@dataclass
class AwaitExpression:
    """Represents await task or await [task1, task2, ...] (HLD 3.6.7).

    Used to distinguish await on a single task vs await on a list.
    """

    targets: list[Task] | Task

    @property
    def is_list(self) -> bool:
        """Whether this is await [list]."""
        return isinstance(self.targets, list)
