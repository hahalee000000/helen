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
    
    Phase 1b: Tasks can be pending (deferred execution) or completed.
    """

    result_value: Any = None
    exception: Exception | None = None
    _done: bool = False
    _pending: bool = False
    _call_node: Any = None  # CallNode to execute
    _interpreter: Any = None  # Interpreter instance for execution
    _env_snapshot: Any = None  # Environment snapshot for isolation

    @classmethod
    def completed(cls, result: Any) -> "Task":
        """Create a completed task with a result."""
        return cls(result_value=result, exception=None, _done=True)

    @classmethod
    def failed(cls, exc: Exception) -> "Task":
        """Create a completed task with an exception."""
        return cls(result_value=None, exception=exc, _done=True)

    @classmethod
    def pending(cls, call_node: Any, interpreter: Any, env_snapshot: Any) -> "Task":
        """Create a pending task that will execute on await."""
        return cls(_pending=True, _call_node=call_node, 
                   _interpreter=interpreter, _env_snapshot=env_snapshot)

    @property
    def is_done(self) -> bool:
        """Whether the task has completed (success or failure)."""
        return self._done

    @property
    def is_pending(self) -> bool:
        """Whether the task is waiting to be executed."""
        return self._pending

    @property
    def has_error(self) -> bool:
        """Whether the task completed with an exception."""
        return self.exception is not None

    async def execute_async(self) -> None:
        """Async version of execute() for true concurrent execution.
        
        Phase 1b: If interpreter is AsyncLLMInterpreter, uses async execution
        directly (no thread pool). Otherwise, falls back to asyncio.to_thread().
        
        Memory: When using AsyncLLMInterpreter, no threads are created.
        All async tasks run in a single thread with asyncio event loop.
        """
        import asyncio
        
        if not self._pending:
            return
        
        try:
            # Check if interpreter supports async execution
            from helen.interpreter.async_interpreter import AsyncLLMInterpreter
            if isinstance(self._interpreter, AsyncLLMInterpreter):
                # True async execution - no thread pool
                result = await self._execute_async()
            else:
                # Fallback to thread pool for sync interpreters
                # Use run_in_executor for Python 3.7+ compatibility
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, self._execute_sync)
            
            self.result_value = result
            self._done = True
        except Exception as e:
            self.exception = e
            self._done = True
        finally:
            self._pending = False
    
    async def _execute_async(self) -> Any:
        """Async execution helper for AsyncLLMInterpreter."""
        # Restore environment snapshot for isolation
        old_env = self._interpreter.environment
        self._interpreter.environment = self._env_snapshot
        
        try:
            # Check if the call node is an LLM expression
            from helen.core.ast import LlmActExprNode, LlmIfStmtNode
            if isinstance(self._call_node, LlmActExprNode):
                result = await self._interpreter.visit_llm_act_expr_async(self._call_node)
            elif isinstance(self._call_node, LlmIfStmtNode):
                result = await self._interpreter.visit_llm_if_stmt_async(self._call_node)
            else:
                # Non-LLM nodes execute synchronously
                result = self._call_node.accept(self._interpreter)
            return result
        finally:
            # Restore original environment
            self._interpreter.environment = old_env
    
    def _execute_sync(self) -> Any:
        """Synchronous execution helper for execute_async()."""
        # Restore environment snapshot for isolation
        old_env = self._interpreter.environment
        self._interpreter.environment = self._env_snapshot
        
        try:
            # Execute the call
            result = self._call_node.accept(self._interpreter)
            return result
        finally:
            # Restore original environment
            self._interpreter.environment = old_env

    def execute(self) -> None:
        """Execute the pending task (sync version, for backward compatibility)."""
        if not self._pending:
            return
        
        try:
            result = self._execute_sync()
            self.result_value = result
            self._done = True
        except Exception as e:
            self.exception = e
            self._done = True
        finally:
            self._pending = False

    def result(self) -> Any:
        """Get the result or raise the exception.

        Returns:
            The task result if successful.

        Raises:
            The stored exception if the task failed.
        """
        if self._pending:
            raise RuntimeError("Task is still pending, call await first")
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
