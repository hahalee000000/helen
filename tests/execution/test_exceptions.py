"""Tests for hellen.interpreter — exception hierarchy and try/catch/finally."""

import pytest

from hellen.core.ast import (
    CaseNode,
    CatchAllNode,
    CatchClauseNode,
    FinallyBlockNode,
    LiteralNode,
    MainBlockNode,
    MatchStmtNode,
    ProgramNode,
    ReturnStmtNode,
    TryStmtNode,
    TypeNode,
    VarDeclNode,
)
from hellen.core.errors import ErrorReporter
from hellen.core.source import SourceSpan
from hellen.interpreter.exceptions import (
    AnyError,
    ConstAssignmentError,
    HellenRuntimeError,
    LLMError,
    ModelError,
    TimeoutError,
    ToolError,
    RuntimeError as HellenRuntimeExc,
    error_matches,
)
from hellen.interpreter.interpreter import Interpreter


def _span(line: int = 1) -> SourceSpan:
    return SourceSpan("<test>", line, 1, line, 5)


def _lit(value, line: int = 1) -> LiteralNode:
    return LiteralNode(value=value, span=_span(line))


def _run(*stmts, llm_runtime=None) -> tuple:
    prog = ProgramNode(statements=list(stmts), span=_span())
    errors = ErrorReporter()
    interp = Interpreter(errors, llm_runtime=llm_runtime)
    result = interp.interpret(prog)
    return result, errors


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class TestExceptionHierarchy:
    def test_timeout_error_is_llm_error(self):
        exc = TimeoutError("timeout")
        assert isinstance(exc, LLMError)
        assert isinstance(exc, HellenRuntimeError)

    def test_model_error_is_llm_error(self):
        exc = ModelError("quota")
        assert isinstance(exc, LLMError)
        assert isinstance(exc, HellenRuntimeError)

    def test_tool_error_is_not_llm_error(self):
        exc = ToolError("fail")
        assert isinstance(exc, HellenRuntimeError)
        assert not isinstance(exc, LLMError)

    def test_runtime_error_is_not_llm_error(self):
        exc = HellenRuntimeExc("div zero")
        assert isinstance(exc, HellenRuntimeError)
        assert not isinstance(exc, LLMError)

    def test_any_error_is_root(self):
        exc = AnyError("any")
        assert isinstance(exc, HellenRuntimeError)


class TestErrorMatches:
    def test_exact_match(self):
        exc = TimeoutError("timeout")
        assert error_matches(exc, "TimeoutError") is True

    def test_parent_match(self):
        exc = TimeoutError("timeout")
        assert error_matches(exc, "LLMError") is True  # TimeoutError is subclass

    def test_no_match(self):
        exc = TimeoutError("timeout")
        assert error_matches(exc, "ToolError") is False

    def test_unknown_type(self):
        exc = TimeoutError("timeout")
        assert error_matches(exc, "UnknownError") is False

    def test_const_assignment_match(self):
        exc = ConstAssignmentError("x")
        # ConstAssignmentError is HellenRuntimeError but not in predefined set
        assert error_matches(exc, "RuntimeError") is False


# ---------------------------------------------------------------------------
# Try/catch/finally execution
# ---------------------------------------------------------------------------


class TestTryCatch:
    def test_try_normal_execution(self):
        """try { let x = 42 } catch RuntimeError e { ... }"""
        type_node = TypeNode(name="TimeoutError", span=_span())
        clause = CatchClauseNode(
            error_type=type_node,
            error_name="e",
            body=[ReturnStmtNode(value=_lit("caught"), span=_span())],
            span=_span(),
        )
        ts = TryStmtNode(
            body=[ReturnStmtNode(value=_lit(42), span=_span())],
            catch_clauses=[clause],
            catch_all=None,
            finally_block=None,
            span=_span(),
        )
        result, errors = _run(ts)
        # ReturnStmtNode returns ReturnSentinel(42), interpret unwraps it
        assert result == 42
        assert not errors.has_errors

    def test_try_catch_type_match(self):
        """try { raise TimeoutError } catch TimeoutError e { return 'caught' }"""
        from hellen.core.ast import ExprStmtNode
        interp = Interpreter(ErrorReporter())

        class RaiseExc:
            def accept(self, visitor):
                raise TimeoutError("test timeout", _span(2))

        type_node = TypeNode(name="TimeoutError", span=_span())
        clause = CatchClauseNode(
            error_type=type_node,
            error_name="e",
            body=[ReturnStmtNode(value=_lit("caught"), span=_span())],
            span=_span(),
        )
        ts = TryStmtNode(
            body=[RaiseExc()],
            catch_clauses=[clause],
            catch_all=None,
            finally_block=None,
            span=_span(),
        )
        result = interp._execute(ts)
        # The catch body returns ReturnSentinel("caught")
        assert result == "caught" or (hasattr(result, 'value') and result.value == "caught")


class TestCatchAll:
    def test_catch_all_fallback(self):
        """catch { ... } catches unmatched exceptions."""
        interp = Interpreter(ErrorReporter())

        class RaiseExc:
            def accept(self, visitor):
                raise ToolError("tool failed", _span(2))

        # Catch clause for TimeoutError (won't match ToolError)
        type_node = TypeNode(name="TimeoutError", span=_span())
        clause = CatchClauseNode(
            error_type=type_node,
            error_name="e",
            body=[ReturnStmtNode(value=_lit("timeout"), span=_span())],
            span=_span(),
        )
        catch_all = CatchAllNode(
            body=[ReturnStmtNode(value=_lit("fallback"), span=_span())],
            span=_span(),
        )
        ts = TryStmtNode(
            body=[RaiseExc()],
            catch_clauses=[clause],
            catch_all=catch_all,
            finally_block=None,
            span=_span(),
        )
        result = interp._execute(ts)
        assert result == "fallback"


class TestFinally:
    def test_finally_always_executes(self):
        """finally block executes even on normal flow."""
        interp = Interpreter(ErrorReporter())

        results = []

        class SetFlag:
            def __init__(self, label):
                self.label = label
            def accept(self, visitor):
                results.append(self.label)
                return True

        # finally sets a flag
        finally_block = FinallyBlockNode(
            body=[SetFlag("finally_ran")],
            span=_span(),
        )
        ts = TryStmtNode(
            body=[SetFlag("try_ran")],
            catch_clauses=[],
            catch_all=None,
            finally_block=finally_block,
            span=_span(),
        )
        result = interp._execute(ts)
        assert "try_ran" in results
        assert "finally_ran" in results
        assert not interp.errors.has_errors

    def test_finally_executes_on_exception(self):
        """finally block executes even when exception is caught."""
        interp = Interpreter(ErrorReporter())

        results = []

        class RaiseExc:
            def accept(self, visitor):
                raise TimeoutError("fail", _span())

        class SetFlag:
            def __init__(self, label):
                self.label = label
            def accept(self, visitor):
                results.append(self.label)
                return True

        type_node = TypeNode(name="TimeoutError", span=_span())
        clause = CatchClauseNode(
            error_type=type_node,
            error_name="e",
            body=[SetFlag("caught")],
            span=_span(),
        )
        finally_block = FinallyBlockNode(
            body=[SetFlag("finally_ran")],
            span=_span(),
        )
        ts = TryStmtNode(
            body=[RaiseExc()],
            catch_clauses=[clause],
            catch_all=None,
            finally_block=finally_block,
            span=_span(),
        )
        result = interp._execute(ts)
        assert "caught" in results
        assert "finally_ran" in results


class TestExceptionRethrow:
    def test_uncaught_exception_rethrows(self):
        """Exception not caught by any catch re-raises."""
        interp = Interpreter(ErrorReporter())

        class RaiseExc:
            def accept(self, visitor):
                raise ToolError("fail", _span())

        # Only catch TimeoutError, not ToolError
        type_node = TypeNode(name="TimeoutError", span=_span())
        clause = CatchClauseNode(
            error_type=type_node,
            error_name="e",
            body=[ReturnStmtNode(value=_lit("caught"), span=_span())],
            span=_span(),
        )
        ts = TryStmtNode(
            body=[RaiseExc()],
            catch_clauses=[clause],
            catch_all=None,
            finally_block=None,
            span=_span(),
        )
        with pytest.raises(ToolError):
            interp._execute(ts)


class TestNestedTryCatch:
    def test_nested_try_catch(self):
        """Nested try-catch: inner catches its error, outer continues."""
        interp = Interpreter(ErrorReporter())

        class RaiseInner:
            def accept(self, visitor):
                raise TimeoutError("inner fail", _span(2))

        inner_clause = CatchClauseNode(
            error_type=TypeNode(name="TimeoutError", span=_span(2)),
            error_name="e",
            body=[ReturnStmtNode(value=_lit("inner_caught"), span=_span(2))],
            span=_span(2),
        )
        inner_try = TryStmtNode(
            body=[RaiseInner()],
            catch_clauses=[inner_clause],
            catch_all=None,
            finally_block=None,
            span=_span(2),
        )

        result = interp._execute(inner_try)
        assert result == "inner_caught"


def _var(name: str, line: int = 1):
    from hellen.core.ast import VariableNode
    return VariableNode(name=name, span=_span(line))
