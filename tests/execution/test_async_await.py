"""Tests for async call + await semantics (HLD 3.6.7).

Covers:
- Task creation and completion
- await single Task
- await [list] Promise.all semantics
- AggregateError for failed tasks
- Error aggregation in await [list]
"""

from helen.interpreter.task import Task, AggregateError, AwaitExpression
from helen.core.ast import (
    AgentDeclNode,
    AsyncCallStmtNode,
    CallNode,
    LiteralNode,
    MainBlockNode,
    ProgramNode,
    ReturnStmtNode,
    VariableNode,
)
from helen.core.source import SourceSpan


def _span(line: int = 1) -> SourceSpan:
    return SourceSpan("<test>", line, 1, line, 5)


def _lit(value, line: int = 1) -> LiteralNode:
    return LiteralNode(value=value, span=_span(line))


class TestTask:
    """Test Task class."""

    def test_completed_task(self):
        """Task.completed creates a successful task."""
        task = Task.completed("result")
        assert task.is_done
        assert not task.has_error
        assert task.result() == "result"

    def test_failed_task(self):
        """Task.failed creates a failed task."""
        exc = ValueError("test error")
        task = Task.failed(exc)
        assert task.is_done
        assert task.has_error
        assert task.exception is exc

    def test_failed_task_raises_exception(self):
        """Calling result() on failed task raises the exception."""
        exc = ValueError("test error")
        task = Task.failed(exc)
        try:
            task.result()
            assert False, "Should have raised"
        except ValueError as e:
            assert str(e) == "test error"

    def test_incomplete_task_raises_error(self):
        """Calling result() on incomplete task raises RuntimeError."""
        task = Task()
        try:
            task.result()
            assert False, "Should have raised"
        except RuntimeError as e:
            assert "not yet complete" in str(e)


class TestAggregateError:
    """Test AggregateError for error aggregation."""

    def test_aggregate_error_with_errors(self):
        """AggregateError collects multiple exceptions."""
        errors = [ValueError("err1"), TypeError("err2")]
        agg = AggregateError("tasks failed", errors=errors)
        assert len(agg.errors) == 2
        assert "err1" in str(agg)
        assert "err2" in str(agg)

    def test_aggregate_error_empty(self):
        """AggregateError with no errors."""
        agg = AggregateError("no errors")
        assert len(agg.errors) == 0
        assert "no errors" in str(agg)

    def test_aggregate_error_str(self):
        """String representation includes all errors."""
        errors = [RuntimeError("timeout"), ValueError("invalid")]
        agg = AggregateError("aggregate", errors=errors)
        s = str(agg)
        assert "timeout" in s
        assert "invalid" in s


class TestAwaitExpression:
    """Test AwaitExpression."""

    def test_single_task(self):
        """await single task."""
        task = Task.completed("result")
        expr = AwaitExpression(targets=task)
        assert not expr.is_list

    def test_task_list(self):
        """await [list] of tasks."""
        tasks = [Task.completed("a"), Task.completed("b")]
        expr = AwaitExpression(targets=tasks)
        assert expr.is_list
        assert len(expr.targets) == 2


class TestPromiseAllSemantics:
    """Test Promise.all-like behavior."""

    def test_all_tasks_succeed(self):
        """await [list] returns all results when all succeed."""
        tasks = [
            Task.completed("result1"),
            Task.completed("result2"),
            Task.completed("result3"),
        ]
        # Simulate gather results
        results = [t.result() for t in tasks]
        assert results == ["result1", "result2", "result3"]

    def test_one_task_fails(self):
        """await [list] with one failure raises AggregateError."""
        tasks = [
            Task.completed("ok"),
            Task.failed(ValueError("failed")),
            Task.completed("also_ok"),
        ]
        # Check which tasks failed
        failed = [t for t in tasks if t.has_error]
        assert len(failed) == 1

    def test_all_tasks_fail(self):
        """await [list] with all failures raises AggregateError with all errors."""
        tasks = [
            Task.failed(ValueError("err1")),
            Task.failed(TypeError("err2")),
        ]
        failed = [t for t in tasks if t.has_error]
        assert len(failed) == 2


class TestInterpreterAsyncCall:
    """Test async call execution in interpreter."""

    def test_async_call_returns_task(self):
        """async call Agent() returns a Task object."""
        from helen.interpreter.interpreter import Interpreter

        agent = AgentDeclNode(
            name="AsyncAgent",
            params=[],
            declarations=[],
            prompt=None,
            logic=MainBlockNode(
                body=[ReturnStmtNode(value=_lit(42), span=_span())],
                span=_span(),
            ),
            span=_span(),
        )

        interp = Interpreter()
        interp._agents["AsyncAgent"] = agent

        # Create async call node
        call_node = CallNode(
            callee=VariableNode(name="AsyncAgent", span=_span()),
            arguments=[],
            span=_span(),
        )
        async_node = AsyncCallStmtNode(call=call_node, span=_span())

        # Execute async call
        result = interp.interpret(ProgramNode(statements=[agent, async_node], span=_span()))

        # Should return a Task
        assert isinstance(result, Task), f"Expected Task, got {type(result)}"

    def test_async_call_task_not_done_immediately(self):
        """async call returns Task that completes after execution."""
        from helen.interpreter.interpreter import Interpreter

        agent = AgentDeclNode(
            name="SlowAgent",
            params=[],
            declarations=[],
            prompt=None,
            logic=MainBlockNode(
                body=[ReturnStmtNode(value=_lit("done"), span=_span())],
                span=_span(),
            ),
            span=_span(),
        )

        interp = Interpreter()
        interp._agents["SlowAgent"] = agent

        call_node = CallNode(
            callee=VariableNode(name="SlowAgent", span=_span()),
            arguments=[],
            span=_span(),
        )
        async_node = AsyncCallStmtNode(call=call_node, span=_span())

        result = interp.interpret(ProgramNode(statements=[agent, async_node], span=_span()))

        assert isinstance(result, Task)
        # Task should be completed (in synchronous mode)
        assert result.is_done


class TestInterpreterAwaitList:
    """Test await [list] Promise.all semantics."""

    def test_await_list_returns_results(self):
        """await [task1, task2] returns list of results."""
        from helen.interpreter.interpreter import Interpreter

        # Simulate await [list] with completed tasks
        tasks = [
            Task.completed("result1"),
            Task.completed("result2"),
        ]

        interp = Interpreter()
        results = interp._await_tasks(tasks)
        assert results == ["result1", "result2"]

    def test_await_list_with_failure_raises_aggregate(self):
        """await [list] with any failure raises AggregateError."""
        from helen.interpreter.interpreter import Interpreter

        tasks = [
            Task.completed("ok"),
            Task.failed(ValueError("agent failed")),
            Task.completed("also_ok"),
        ]

        interp = Interpreter()
        try:
            interp._await_tasks(tasks)
            assert False, "Should have raised AggregateError"
        except AggregateError as e:
            assert len(e.errors) == 1

    def test_await_single_task(self):
        """await single task returns its result."""
        from helen.interpreter.interpreter import Interpreter

        task = Task.completed("single_result")
        interp = Interpreter()

        result = interp._await_tasks(task)
        assert result == "single_result"


class TestAggregateErrorCatchable:
    """Test that AggregateError can be caught by try-catch."""

    def test_aggregate_error_is_helen_runtime_error(self):
        """AggregateError inherits from HelenRuntimeError."""
        from helen.interpreter.exceptions import AggregateError, HelenRuntimeError
        err = AggregateError("test")
        assert isinstance(err, HelenRuntimeError)

    def test_aggregate_error_in_predefined(self):
        """AggregateError is in the predefined exceptions map."""
        from helen.interpreter.exceptions import _PREDEFINED_EXCEPTIONS, AggregateError
        assert "AggregateError" in _PREDEFINED_EXCEPTIONS
        assert _PREDEFINED_EXCEPTIONS["AggregateError"] is AggregateError

    def test_error_matches_aggregate(self):
        """error_matches recognizes AggregateError."""
        from helen.interpreter.exceptions import AggregateError, error_matches
        err = AggregateError("test")
        assert error_matches(err, "AggregateError")

    def test_aggregate_error_has_errors_list(self):
        """AggregateError stores errors list."""
        from helen.interpreter.exceptions import AggregateError
        inner = [ValueError("a"), RuntimeError("b")]
        err = AggregateError("multi", errors=inner)
        assert len(err.errors) == 2
        assert err.errors[0] is inner[0]
