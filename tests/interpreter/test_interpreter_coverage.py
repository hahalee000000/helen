"""Comprehensive coverage tests for helen.interpreter.interpreter.

Targets uncovered lines in interpreter.py (currently 43% coverage).
Focus areas:
- REPL management (undefine_function, undefine_agent, list_definitions, reset_definitions)
- for loop execution
- while loop execution
- match statement execution
- try/catch/finally execution
- throw statement
- import statement
- index access
- agent call with named args
- binary operators (division by zero, modulo by zero, AND/OR)
- visit methods
"""

import pytest

from helen.core.ast import (
    AccessNode,
    AgentDeclNode,
    AgentParamNode,
    BinaryOpNode,
    BreakStmtNode,
    CallArgNode,
    CallNode,
    CaseNode,
    CatchAllNode,
    CatchClauseNode,
    ContinueStmtNode,
    DeclarationNode,
    ExprStmtNode,
    FinallyBlockNode,
    FnBlockNode,
    ForStmtNode,
    FunctionDeclNode,
    GroupingNode,
    IfStmtNode,
    ImportStmtNode,
    IndexNode,
    ListLiteralNode,
    LiteralNode,
    LiteralTypeNode,
    MainBlockNode,
    MapEntryNode,
    MapLiteralNode,
    MatchStmtNode,
    OptionalTypeNode,
    ProgramNode,
    ReturnStmtNode,
    ThrowStmtNode,
    TryStmtNode,
    TypeNode,
    UnaryOpNode,
    UnionTypeNode,
    VarDeclNode,
    VariableNode,
    WhileStmtNode,
)
from helen.core.errors import ErrorReporter
from helen.core.source import SourceSpan
from helen.core.tokens import Token, TokenType
from helen.interpreter.exceptions import (
    BreakSentinel,
    ContinueSentinel,
    HelenRuntimeError,
    ReturnSentinel,
    RuntimeError as HelenRuntimeExc,
    TimeoutError as HelenTimeoutError,
    ToolError,
)
from helen.interpreter.interpreter import Interpreter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _span(line: int = 1) -> SourceSpan:
    return SourceSpan("<test>", line, 1, line, 5)


def _lit(value, line: int = 1) -> LiteralNode:
    return LiteralNode(value=value, span=_span(line))


def _var(name: str, line: int = 1) -> VariableNode:
    return VariableNode(name=name, span=_span(line))


def _tok(name: str = "PLUS", lexeme: str = "+") -> Token:
    tt = getattr(TokenType, name, TokenType.PLUS)
    return Token(tt, lexeme, None, 1, 1, 1, len(lexeme) + 1)


def _run(*stmts, llm_runtime=None, import_resolver=None) -> tuple:
    """Run statements through the interpreter and return (result, interp, errors)."""
    prog = ProgramNode(statements=list(stmts), span=_span())
    errors = ErrorReporter()
    interp = Interpreter(errors, llm_runtime=llm_runtime, import_resolver=import_resolver)
    try:
        result = interp.interpret(prog)
    except (HelenRuntimeExc, HelenRuntimeError):
        result = None
    return result, interp, errors


# ===========================================================================
# REPL Management Tests
# ===========================================================================


class TestUndefineFunction:
    def test_undefine_existing_function(self):
        """undefine_function returns True for existing function."""
        interp = Interpreter()
        fn = FunctionDeclNode(
            name="my_func",
            params=[],
            return_type=None,
            body=FnBlockNode(body=[], span=_span()),
            span=_span(),
        )
        interp._functions["my_func"] = fn
        assert interp.undefine_function("my_func") is True
        assert "my_func" not in interp._functions

    def test_undefine_nonexistent_function(self):
        """undefine_function returns False for nonexistent function."""
        interp = Interpreter()
        assert interp.undefine_function("nonexistent") is False

    def test_undefine_function_twice(self):
        """Second undefine returns False."""
        interp = Interpreter()
        fn = FunctionDeclNode(
            name="f", params=[], return_type=None,
            body=FnBlockNode(body=[], span=_span()), span=_span(),
        )
        interp._functions["f"] = fn
        assert interp.undefine_function("f") is True
        assert interp.undefine_function("f") is False


class TestUndefineAgent:
    def test_undefine_existing_agent(self):
        """undefine_agent returns True for existing agent."""
        interp = Interpreter()
        agent = AgentDeclNode(
            name="MyAgent", params=[], declarations=[],
            prompt=None, logic=None, span=_span(),
        )
        interp._agents["MyAgent"] = agent
        assert interp.undefine_agent("MyAgent") is True
        assert "MyAgent" not in interp._agents

    def test_undefine_nonexistent_agent(self):
        """undefine_agent returns False for nonexistent agent."""
        interp = Interpreter()
        assert interp.undefine_agent("Ghost") is False


class TestListDefinitions:
    def test_empty_definitions(self):
        """list_definitions returns empty lists initially."""
        interp = Interpreter()
        defs = interp.list_definitions()
        assert defs["functions"] == []
        assert defs["agents"] == []

    def test_list_with_functions_and_agents(self):
        """list_definitions returns sorted names."""
        interp = Interpreter()
        fn1 = FunctionDeclNode(name="beta", params=[], return_type=None,
                               body=FnBlockNode(body=[], span=_span()), span=_span())
        fn2 = FunctionDeclNode(name="alpha", params=[], return_type=None,
                               body=FnBlockNode(body=[], span=_span()), span=_span())
        agent = AgentDeclNode(name="Zeta", params=[], declarations=[],
                              prompt=None, logic=None, span=_span())
        interp._functions["beta"] = fn1
        interp._functions["alpha"] = fn2
        interp._agents["Zeta"] = agent
        defs = interp.list_definitions()
        assert defs["functions"] == ["alpha", "beta"]
        assert defs["agents"] == ["Zeta"]


class TestResetDefinitions:
    def test_reset_clears_all(self):
        """reset_definitions clears functions and agents."""
        interp = Interpreter()
        fn = FunctionDeclNode(name="f", params=[], return_type=None,
                              body=FnBlockNode(body=[], span=_span()), span=_span())
        agent = AgentDeclNode(name="A", params=[], declarations=[],
                              prompt=None, logic=None, span=_span())
        interp._functions["f"] = fn
        interp._agents["A"] = agent
        interp._current_agent = agent
        interp.reset_definitions()
        assert interp._functions == {}
        assert interp._agents == {}
        assert interp._current_agent is None

    def test_reset_preserves_stdlib(self):
        """reset_definitions re-registers stdlib builtins."""
        interp = Interpreter()
        interp.reset_definitions()
        # stdlib functions should still be available in environment
        # (they are defined in the environment, not in _functions)
        assert interp.environment.lookup("print") is not None


# ===========================================================================
# For Loop Execution Tests
# ===========================================================================


class TestForLoopExecution:
    def test_for_empty_iterable(self):
        """for over empty list returns None."""
        lst = ListLiteralNode(elements=[], span=_span())
        body = ExprStmtNode(expression=_var("x"), span=_span())
        stmt = ForStmtNode(iterator=_var("x"), iterable=lst, body=body, span=_span())
        result, interp, errors = _run(stmt)
        assert result is None
        assert not errors.has_errors

    def test_for_single_element(self):
        """for over single-element list."""
        lst = ListLiteralNode(elements=[_lit(42)], span=_span())
        body = ExprStmtNode(expression=_var("x"), span=_span())
        stmt = ForStmtNode(iterator=_var("x"), iterable=lst, body=body, span=_span())
        result, interp, errors = _run(stmt)
        assert result == 42

    def test_for_with_strings(self):
        """for over string list."""
        lst = ListLiteralNode(elements=[_lit("a"), _lit("b"), _lit("c")], span=_span())
        body = ExprStmtNode(expression=_var("s"), span=_span())
        stmt = ForStmtNode(iterator=_var("s"), iterable=lst, body=body, span=_span())
        result, interp, errors = _run(stmt)
        assert result == "c"

    def test_for_non_iterable_error(self):
        """for over non-iterable reports error."""
        stmt = ForStmtNode(iterator=_var("x"), iterable=_lit(42), body=ExprStmtNode(expression=_var("x"), span=_span()), span=_span())
        result, interp, errors = _run(stmt)
        assert errors.has_errors

    def test_for_with_return(self):
        """for loop with early return."""
        lst = ListLiteralNode(elements=[_lit(1), _lit(2), _lit(3)], span=_span())
        ret = ReturnStmtNode(value=_var("x"), span=_span())
        body = MainBlockNode(body=[ret], span=_span())
        stmt = ForStmtNode(iterator=_var("x"), iterable=lst, body=body, span=_span())
        result, interp, errors = _run(stmt)
        assert result == 1  # returns on first iteration

    def test_for_nested(self):
        """Nested for loops."""
        # for x in [1, 2] { for y in [10, 20] { x + y } }
        inner_lst = ListLiteralNode(elements=[_lit(10), _lit(20)], span=_span())
        add = BinaryOpNode(left=_var("x", 2), operator=_tok("PLUS", "+"), right=_var("y", 2), span=_span(2))
        inner_body = ExprStmtNode(expression=add, span=_span(2))
        inner_for = ForStmtNode(iterator=_var("y"), iterable=inner_lst, body=inner_body, span=_span(2))

        outer_lst = ListLiteralNode(elements=[_lit(1), _lit(2)], span=_span())
        outer_body = MainBlockNode(body=[inner_for], span=_span())
        outer_for = ForStmtNode(iterator=_var("x"), iterable=outer_lst, body=outer_body, span=_span())

        result, interp, errors = _run(outer_for)
        # Last iteration: x=2, y=20 -> 22
        assert result == 22


# ===========================================================================
# While Loop Execution Tests
# ===========================================================================


class TestWhileLoopExecution:
    def test_while_false_condition(self):
        """while with false condition doesn't execute body."""
        cond = _lit(False)
        body = MainBlockNode(body=[ExprStmtNode(expression=_lit(99), span=_span())], span=_span())
        stmt = WhileStmtNode(condition=cond, body=body, span=_span())
        result, interp, errors = _run(stmt)
        assert result is None

    def test_while_continue(self):
        """while loop with continue."""
        # let i = 0; while (i < 5) { i = i + 1; if (i == 3) continue; }
        i_decl = VarDeclNode(name="i", type_annotation=None, initializer=_lit(0), mutable=True, span=_span())

        cond = BinaryOpNode(left=_var("i", 2), operator=_tok("LESS", "<"), right=_lit(5), span=_span(2))

        # i = i + 1
        add = BinaryOpNode(left=_var("i", 3), operator=_tok("PLUS", "+"), right=_lit(1), span=_span(3))
        assign = BinaryOpNode(left=_var("i", 3), operator=_tok("ASSIGN", "="), right=add, span=_span(3))

        # if (i == 3) continue
        eq = BinaryOpNode(left=_var("i", 4), operator=_tok("EQUAL_EQUAL", "=="), right=_lit(3), span=_span(4))
        cont = ContinueStmtNode(span=_span(4))
        if_then = MainBlockNode(body=[cont], span=_span())
        if_stmt = IfStmtNode(condition=eq, then_branch=if_then, else_branch=None, span=_span(4))

        body = MainBlockNode(body=[ExprStmtNode(expression=assign, span=_span(3)), if_stmt], span=_span())
        while_stmt = WhileStmtNode(condition=cond, body=body, span=_span(2))

        final = ExprStmtNode(expression=_var("i", 5), span=_span(5))
        result, interp, errors = _run(i_decl, while_stmt, final)
        assert result == 5  # loop runs to completion

    def test_while_with_return(self):
        """while loop with return statement."""
        i_decl = VarDeclNode(name="i", type_annotation=None, initializer=_lit(0), mutable=True, span=_span())
        cond = _lit(True)  # infinite loop
        ret = ReturnStmtNode(value=_lit(42), span=_span())
        body = MainBlockNode(body=[ret], span=_span())
        while_stmt = WhileStmtNode(condition=cond, body=body, span=_span())
        result, interp, errors = _run(i_decl, while_stmt)
        assert result == 42


# ===========================================================================
# Match Statement Execution Tests
# ===========================================================================


class TestMatchExecution:
    def test_match_integer_subject(self):
        """match with integer subject."""
        stmt = MatchStmtNode(
            subject=_lit(2),
            cases=[
                CaseNode(pattern=_lit(1), body=[ExprStmtNode(expression=_lit(10), span=_span())], span=_span()),
                CaseNode(pattern=_lit(2), body=[ExprStmtNode(expression=_lit(20), span=_span())], span=_span()),
                CaseNode(pattern=_lit(3), body=[ExprStmtNode(expression=_lit(30), span=_span())], span=_span()),
            ],
            default=[ExprStmtNode(expression=_lit(0), span=_span())],
            span=_span(),
        )
        result, interp, errors = _run(stmt)
        assert result == 20

    def test_match_no_default(self):
        """match with no matching case and no default returns None."""
        stmt = MatchStmtNode(
            subject=_lit("z"),
            cases=[
                CaseNode(pattern=_lit("a"), body=[ExprStmtNode(expression=_lit(1), span=_span())], span=_span()),
            ],
            default=None,
            span=_span(),
        )
        result, interp, errors = _run(stmt)
        assert result is None

    def test_match_boolean_subject(self):
        """match with boolean subject."""
        stmt = MatchStmtNode(
            subject=_lit(True),
            cases=[
                CaseNode(pattern=_lit(False), body=[ExprStmtNode(expression=_lit(0), span=_span())], span=_span()),
                CaseNode(pattern=_lit(True), body=[ExprStmtNode(expression=_lit(1), span=_span())], span=_span()),
            ],
            default=None,
            span=_span(),
        )
        result, interp, errors = _run(stmt)
        assert result == 1

    def test_match_with_multiple_body_stmts(self):
        """match case with multiple statements in body."""
        stmt = MatchStmtNode(
            subject=_lit("x"),
            cases=[
                CaseNode(pattern=_lit("x"), body=[
                    ExprStmtNode(expression=_lit(1), span=_span()),
                    ExprStmtNode(expression=_lit(2), span=_span()),
                    ExprStmtNode(expression=_lit(3), span=_span()),
                ], span=_span()),
            ],
            default=None,
            span=_span(),
        )
        result, interp, errors = _run(stmt)
        assert result == 3  # last statement result


# ===========================================================================
# Try/Catch/Finally Execution Tests
# ===========================================================================


class TestTryCatchExecution:
    def test_try_no_exception(self):
        """try block with no exception returns body result."""
        ts = TryStmtNode(
            body=[ExprStmtNode(expression=_lit(42), span=_span())],
            catch_clauses=[],
            catch_all=None,
            finally_block=None,
            span=_span(),
        )
        result, interp, errors = _run(ts)
        assert result == 42

    def test_try_multiple_catch_clauses(self):
        """Multiple catch clauses - second one matches."""
        interp = Interpreter(ErrorReporter())

        class RaiseExc:
            def accept(self, visitor):
                raise ToolError("tool failed", _span(2))

        clause1 = CatchClauseNode(
            error_type=TypeNode(name="TimeoutError", span=_span()),
            error_name="e",
            body=[ExprStmtNode(expression=_lit("timeout"), span=_span())],
            span=_span(),
        )
        clause2 = CatchClauseNode(
            error_type=TypeNode(name="ToolError", span=_span()),
            error_name="e",
            body=[ExprStmtNode(expression=_lit("tool"), span=_span())],
            span=_span(),
        )
        ts = TryStmtNode(
            body=[RaiseExc()],
            catch_clauses=[clause1, clause2],
            catch_all=None,
            finally_block=None,
            span=_span(),
        )
        result = interp._execute(ts)
        assert result == "tool"

    def test_try_catch_all_no_typed_catches(self):
        """catch-all with no typed catches."""
        interp = Interpreter(ErrorReporter())

        class RaiseExc:
            def accept(self, visitor):
                raise HelenTimeoutError("timeout", _span())

        catch_all = CatchAllNode(
            body=[ExprStmtNode(expression=_lit("caught_all"), span=_span())],
            span=_span(),
        )
        ts = TryStmtNode(
            body=[RaiseExc()],
            catch_clauses=[],
            catch_all=catch_all,
            finally_block=None,
            span=_span(),
        )
        result = interp._execute(ts)
        assert result == "caught_all"

    def test_finally_with_no_catch(self):
        """finally executes even with no catch clauses."""
        interp = Interpreter(ErrorReporter())
        results = []

        class SetFlag:
            def __init__(self, label):
                self.label = label
            def accept(self, visitor):
                results.append(self.label)
                return self.label

        finally_block = FinallyBlockNode(body=[SetFlag("finally")], span=_span())
        ts = TryStmtNode(
            body=[SetFlag("try_body")],
            catch_clauses=[],
            catch_all=None,
            finally_block=finally_block,
            span=_span(),
        )
        result = interp._execute(ts)
        assert "try_body" in results
        assert "finally" in results


# ===========================================================================
# Throw Statement Tests
# ===========================================================================


class TestThrowExecution:
    def test_throw_runtime_error(self):
        """throw RuntimeError raises RuntimeError."""
        throw = ThrowStmtNode(
            exception_type=TypeNode(name="RuntimeError", span=_span()),
            message=_lit("test error"),
            span=_span(),
        )
        interp = Interpreter(ErrorReporter())
        with pytest.raises(HelenRuntimeExc):
            interp._execute(throw)

    def test_throw_timeout_error(self):
        """throw TimeoutError raises TimeoutError."""
        throw = ThrowStmtNode(
            exception_type=TypeNode(name="TimeoutError", span=_span()),
            message=_lit("timed out"),
            span=_span(),
        )
        interp = Interpreter(ErrorReporter())
        with pytest.raises(HelenTimeoutError):
            interp._execute(throw)

    def test_throw_without_message(self):
        """throw without message uses default."""
        throw = ThrowStmtNode(
            exception_type=TypeNode(name="RuntimeError", span=_span()),
            message=None,
            span=_span(),
        )
        interp = Interpreter(ErrorReporter())
        with pytest.raises(HelenRuntimeExc):
            interp._execute(throw)

    def test_throw_with_non_string_message(self):
        """throw with non-string message converts to string."""
        throw = ThrowStmtNode(
            exception_type=TypeNode(name="RuntimeError", span=_span()),
            message=_lit(42),
            span=_span(),
        )
        interp = Interpreter(ErrorReporter())
        with pytest.raises(HelenRuntimeExc) as exc_info:
            interp._execute(throw)
        assert "42" in str(exc_info.value)

    def test_throw_caught_by_try(self):
        """throw inside try is caught by matching catch."""
        throw = ThrowStmtNode(
            exception_type=TypeNode(name="ToolError", span=_span()),
            message=_lit("tool fail"),
            span=_span(),
        )
        clause = CatchClauseNode(
            error_type=TypeNode(name="ToolError", span=_span()),
            error_name="e",
            body=[ExprStmtNode(expression=_lit("recovered"), span=_span())],
            span=_span(),
        )
        ts = TryStmtNode(
            body=[throw],
            catch_clauses=[clause],
            catch_all=None,
            finally_block=None,
            span=_span(),
        )
        interp = Interpreter(ErrorReporter())
        result = interp._execute(ts)
        assert result == "recovered"


# ===========================================================================
# Import Statement Tests
# ===========================================================================


class TestImportExecution:
    def test_import_python_module(self):
        """import os as os_module registers module."""
        imp = ImportStmtNode(module_path="os", alias="os_mod", span=_span())
        interp = Interpreter(ErrorReporter())
        interp._execute(imp)
        # Should be defined in environment
        mod = interp.environment.lookup("os_mod")
        assert mod is not None

    def test_import_python_module_no_alias(self):
        """import without alias uses module name."""
        imp = ImportStmtNode(module_path="json", alias=None, span=_span())
        interp = Interpreter(ErrorReporter())
        interp._execute(imp)
        mod = interp.environment.lookup("json")
        assert mod is not None

    def test_import_nonexistent_python_module(self):
        """import nonexistent module reports error."""
        imp = ImportStmtNode(module_path="nonexistent_module_xyz", alias=None, span=_span())
        interp = Interpreter(ErrorReporter())
        # The import may raise an exception or report an error
        try:
            interp._execute(imp)
        except (HelenRuntimeExc, HelenRuntimeError):
            pass
        assert interp.errors.has_errors


# ===========================================================================
# Index Access Tests
# ===========================================================================


class TestIndexAccess:
    def test_index_list_negative(self):
        """Negative index access on list."""
        lst = ListLiteralNode(elements=[_lit(10), _lit(20), _lit(30)], span=_span())
        idx = IndexNode(target=lst, index=_lit(-1), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=idx, span=_span()))
        assert result == 30

    def test_index_map_missing_key(self):
        """Indexing map with missing key reports error."""
        e = MapEntryNode(key=_lit("a"), value=_lit(1), span=_span())
        mp = MapLiteralNode(entries=[e], span=_span())
        idx = IndexNode(target=mp, index=_lit("b"), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=idx, span=_span()))
        assert errors.has_errors

    def test_index_non_indexable_type(self):
        """Indexing a non-indexable type reports error."""
        idx = IndexNode(target=_lit(42), index=_lit(0), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=idx, span=_span()))
        assert errors.has_errors

    def test_index_list_with_non_int(self):
        """Indexing list with non-integer reports error."""
        lst = ListLiteralNode(elements=[_lit(1)], span=_span())
        idx = IndexNode(target=lst, index=_lit("key"), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=idx, span=_span()))
        assert errors.has_errors

    def test_index_tuple(self):
        """Index access on tuple (via variable)."""
        interp = Interpreter(ErrorReporter())
        interp.environment.define("tup", (10, 20, 30))
        idx = IndexNode(target=_var("tup"), index=_lit(1), span=_span())
        result = interp._execute(ExprStmtNode(expression=idx, span=_span()))
        assert result == 20


# ===========================================================================
# Agent Call with Named Args Tests
# ===========================================================================


class TestAgentCallNamedArgs:
    def test_agent_call_positional_args(self):
        """Agent call with positional arguments."""
        param = AgentParamNode(name="text", type_annotation=None, default_value=None, span=_span())
        agent = AgentDeclNode(
            name="Worker",
            params=[param],
            declarations=[],
            prompt=None,
            logic=MainBlockNode(
                body=[ReturnStmtNode(value=_var("text"), span=_span())],
                span=_span(),
            ),
            span=_span(),
        )
        call = CallNode(
            callee=_var("Worker"),
            arguments=[CallArgNode(name=None, value=_lit("hello"))],
            span=_span(),
        )
        result, interp, errors = _run(agent, ExprStmtNode(expression=call, span=_span()))
        assert result == "hello"

    def test_agent_call_named_args(self):
        """Agent call with named arguments."""
        param1 = AgentParamNode(name="text", type_annotation=None, default_value=None, span=_span())
        param2 = AgentParamNode(name="count", type_annotation=None, default_value=None, span=_span())
        agent = AgentDeclNode(
            name="Formatter",
            params=[param1, param2],
            declarations=[],
            prompt=None,
            logic=MainBlockNode(
                body=[ReturnStmtNode(value=_var("text"), span=_span())],
                span=_span(),
            ),
            span=_span(),
        )
        call = CallNode(
            callee=_var("Formatter"),
            arguments=[
                CallArgNode(name="text", value=_lit("world")),
                CallArgNode(name="count", value=_lit(3)),
            ],
            span=_span(),
        )
        result, interp, errors = _run(agent, ExprStmtNode(expression=call, span=_span()))
        assert result == "world"

    def test_agent_call_with_default_param(self):
        """Agent call uses default when arg not provided."""
        param = AgentParamNode(name="msg", type_annotation=None, default_value=_lit("default"), span=_span())
        agent = AgentDeclNode(
            name="Echo",
            params=[param],
            declarations=[],
            prompt=None,
            logic=MainBlockNode(
                body=[ReturnStmtNode(value=_var("msg"), span=_span())],
                span=_span(),
            ),
            span=_span(),
        )
        call = CallNode(
            callee=_var("Echo"),
            arguments=[],
            span=_span(),
        )
        result, interp, errors = _run(agent, ExprStmtNode(expression=call, span=_span()))
        assert result == "default"

    def test_agent_call_too_many_positional(self):
        """Agent call with too many positional args reports error."""
        param = AgentParamNode(name="x", type_annotation=None, default_value=None, span=_span())
        agent = AgentDeclNode(
            name="One",
            params=[param],
            declarations=[],
            prompt=None,
            logic=MainBlockNode(body=[], span=_span()),
            span=_span(),
        )
        call = CallNode(
            callee=_var("One"),
            arguments=[
                CallArgNode(name=None, value=_lit(1)),
                CallArgNode(name=None, value=_lit(2)),
            ],
            span=_span(),
        )
        result, interp, errors = _run(agent, ExprStmtNode(expression=call, span=_span()))
        assert errors.has_errors

    def test_agent_call_no_logic(self):
        """Agent with no logic returns None."""
        agent = AgentDeclNode(
            name="Empty",
            params=[],
            declarations=[],
            prompt=None,
            logic=None,
            span=_span(),
        )
        call = CallNode(callee=_var("Empty"), arguments=[], span=_span())
        result, interp, errors = _run(agent, ExprStmtNode(expression=call, span=_span()))
        assert result is None


# ===========================================================================
# Binary Operator Tests
# ===========================================================================


class TestDivisionByZero:
    def test_integer_division_by_zero(self):
        """1 / 0 reports division by zero error."""
        div = BinaryOpNode(left=_lit(1), operator=_tok("SLASH", "/"), right=_lit(0), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=div, span=_span()))
        assert errors.has_errors

    def test_float_division_by_zero(self):
        """1.0 / 0 reports division by zero error."""
        div = BinaryOpNode(left=_lit(1.0), operator=_tok("SLASH", "/"), right=_lit(0), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=div, span=_span()))
        assert errors.has_errors

    def test_normal_division(self):
        """10 / 3 returns correct result."""
        div = BinaryOpNode(left=_lit(10), operator=_tok("SLASH", "/"), right=_lit(3), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=div, span=_span()))
        assert abs(result - 3.333333) < 0.001


class TestModuloByZero:
    def test_modulo_by_zero(self):
        """10 % 0 reports modulo by zero error."""
        mod = BinaryOpNode(left=_lit(10), operator=_tok("PERCENT", "%"), right=_lit(0), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=mod, span=_span()))
        assert errors.has_errors

    def test_normal_modulo(self):
        """10 % 3 returns 1."""
        mod = BinaryOpNode(left=_lit(10), operator=_tok("PERCENT", "%"), right=_lit(3), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=mod, span=_span()))
        assert result == 1


class TestLogicalOperators:
    def test_and_true_true(self):
        """true and true returns True."""
        op = BinaryOpNode(left=_lit(True), operator=_tok("AND", "and"), right=_lit(True), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=op, span=_span()))
        assert result is True

    def test_and_true_false(self):
        """true and false returns False."""
        op = BinaryOpNode(left=_lit(True), operator=_tok("AND", "and"), right=_lit(False), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=op, span=_span()))
        assert result is False

    def test_and_false_short_circuit(self):
        """false and X returns False (short-circuit)."""
        op = BinaryOpNode(left=_lit(False), operator=_tok("AND", "and"), right=_lit(True), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=op, span=_span()))
        assert result is False

    def test_or_true_false(self):
        """true or false returns True."""
        op = BinaryOpNode(left=_lit(True), operator=_tok("OR", "or"), right=_lit(False), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=op, span=_span()))
        assert result is True

    def test_or_false_false(self):
        """false or false returns False."""
        op = BinaryOpNode(left=_lit(False), operator=_tok("OR", "or"), right=_lit(False), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=op, span=_span()))
        assert result is False

    def test_or_short_circuit(self):
        """true or X returns True (short-circuit)."""
        op = BinaryOpNode(left=_lit(True), operator=_tok("OR", "or"), right=_lit(False), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=op, span=_span()))
        assert result is True

    def test_and_with_truthy_values(self):
        """non-empty string and number returns truthy boolean result."""
        op = BinaryOpNode(left=_lit("hello"), operator=_tok("AND", "and"), right=_lit(42), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=op, span=_span()))
        # AND returns _truthy(left) and _truthy(right) -> True and True -> True
        assert result is True

    def test_or_with_truthy_values(self):
        """non-empty string or false returns truthy boolean value."""
        op = BinaryOpNode(left=_lit("hello"), operator=_tok("OR", "or"), right=_lit(False), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=op, span=_span()))
        # OR returns _truthy(left) or _truthy(right) -> True or False -> True
        assert result is True


class TestComparisonOperators:
    def test_greater_than(self):
        """5 > 3 returns True."""
        op = BinaryOpNode(left=_lit(5), operator=_tok("GREATER", ">"), right=_lit(3), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=op, span=_span()))
        assert result is True

    def test_greater_equal(self):
        """3 >= 3 returns True."""
        op = BinaryOpNode(left=_lit(3), operator=_tok("GREATER_EQUAL", ">="), right=_lit(3), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=op, span=_span()))
        assert result is True

    def test_less_than(self):
        """2 < 5 returns True."""
        op = BinaryOpNode(left=_lit(2), operator=_tok("LESS", "<"), right=_lit(5), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=op, span=_span()))
        assert result is True

    def test_less_equal(self):
        """5 <= 3 returns False."""
        op = BinaryOpNode(left=_lit(5), operator=_tok("LESS_EQUAL", "<="), right=_lit(3), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=op, span=_span()))
        assert result is False

    def test_not_equal(self):
        """1 != 2 returns True."""
        op = BinaryOpNode(left=_lit(1), operator=_tok("BANG_EQUAL", "!="), right=_lit(2), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=op, span=_span()))
        assert result is True

    def test_equal_null(self):
        """None == None returns True."""
        op = BinaryOpNode(left=_lit(None), operator=_tok("EQUAL_EQUAL", "=="), right=_lit(None), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=op, span=_span()))
        assert result is True

    def test_equal_null_vs_value(self):
        """None == 1 returns False."""
        op = BinaryOpNode(left=_lit(None), operator=_tok("EQUAL_EQUAL", "=="), right=_lit(1), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=op, span=_span()))
        assert result is False


# ===========================================================================
# Visit Methods Tests
# ===========================================================================


class TestVisitMethods:
    def test_visit_grouping(self):
        """GroupingNode evaluates inner expression."""
        grp = GroupingNode(expression=_lit(42), span=_span())
        interp = Interpreter(ErrorReporter())
        result = interp._execute(ExprStmtNode(expression=grp, span=_span()))
        assert result == 42

    def test_visit_unary_bang(self):
        """!true returns False."""
        op = UnaryOpNode(operator=_tok("BANG", "!"), operand=_lit(True), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=op, span=_span()))
        assert result is False

    def test_visit_unary_minus(self):
        """-5 returns -5."""
        op = UnaryOpNode(operator=_tok("MINUS", "-"), operand=_lit(5), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=op, span=_span()))
        assert result == -5

    def test_visit_type_noop(self):
        """TypeNode visit returns None."""
        type_node = TypeNode(name="int", span=_span())
        interp = Interpreter(ErrorReporter())
        result = interp.visit_type(type_node)
        assert result is None

    def test_visit_optional_type_noop(self):
        """OptionalTypeNode visit returns None."""
        opt = OptionalTypeNode(inner=TypeNode(name="int", span=_span()), span=_span())
        interp = Interpreter(ErrorReporter())
        result = interp.visit_optional_type(opt)
        assert result is None

    def test_visit_union_type_noop(self):
        """UnionTypeNode visit returns None."""
        union = UnionTypeNode(
            members=[TypeNode(name="int", span=_span()), TypeNode(name="str", span=_span())],
            span=_span(),
        )
        interp = Interpreter(ErrorReporter())
        result = interp.visit_union_type(union)
        assert result is None

    def test_visit_literal_type_noop(self):
        """LiteralTypeNode visit returns None."""
        lit_type = LiteralTypeNode(values=[_lit("x")], span=_span())
        interp = Interpreter(ErrorReporter())
        result = interp.visit_literal_type(lit_type)
        assert result is None

    def test_visit_case_returns_none(self):
        """CaseNode visit returns None (handled by match)."""
        case = CaseNode(pattern=_lit(1), body=[], span=_span())
        interp = Interpreter(ErrorReporter())
        result = interp.visit_case(case)
        assert result is None

    def test_visit_catch_clause_returns_none(self):
        """CatchClauseNode visit returns None."""
        clause = CatchClauseNode(
            error_type=TypeNode(name="RuntimeError", span=_span()),
            error_name="e", body=[], span=_span(),
        )
        interp = Interpreter(ErrorReporter())
        result = interp.visit_catch_clause(clause)
        assert result is None

    def test_visit_catch_all_returns_none(self):
        """CatchAllNode visit returns None."""
        catch_all = CatchAllNode(body=[], span=_span())
        interp = Interpreter(ErrorReporter())
        result = interp.visit_catch_all(catch_all)
        assert result is None

    def test_visit_finally_block_returns_none(self):
        """FinallyBlockNode visit returns None."""
        fb = FinallyBlockNode(body=[], span=_span())
        interp = Interpreter(ErrorReporter())
        result = interp.visit_finally_block(fb)
        assert result is None

    def test_visit_agent_param_returns_none(self):
        """AgentParamNode visit returns None."""
        param = AgentParamNode(name="x", type_annotation=None, default_value=None, span=_span())
        interp = Interpreter(ErrorReporter())
        result = interp.visit_agent_param(param)
        assert result is None

    def test_visit_declaration_returns_none(self):
        """DeclarationNode visit returns None."""
        decl = DeclarationNode(
            description=None, model=None, tools=None,
            memory=None, temperature=None, max_turns=None,
            span=_span(),
        )
        interp = Interpreter(ErrorReporter())
        result = interp.visit_declaration(decl)
        assert result is None

    def test_visit_prompt_def_returns_none(self):
        """PromptDefNode visit returns None."""
        from helen.core.ast import PromptDefNode
        prompt = PromptDefNode(content="hello", span=_span())
        interp = Interpreter(ErrorReporter())
        result = interp.visit_prompt_def(prompt)
        assert result is None


# ===========================================================================
# Helper Methods Tests
# ===========================================================================


class TestHelperMethods:
    def test_truthy_none(self):
        assert Interpreter._truthy(None) is False

    def test_truthy_false(self):
        assert Interpreter._truthy(False) is False

    def test_truthy_zero(self):
        assert Interpreter._truthy(0) is False

    def test_truthy_zero_float(self):
        assert Interpreter._truthy(0.0) is False

    def test_truthy_empty_string(self):
        assert Interpreter._truthy("") is False

    def test_truthy_empty_list(self):
        assert Interpreter._truthy([]) is False

    def test_truthy_empty_dict(self):
        assert Interpreter._truthy({}) is False

    def test_truthy_nonempty_string(self):
        assert Interpreter._truthy("hello") is True

    def test_truthy_nonzero(self):
        assert Interpreter._truthy(42) is True

    def test_truthy_true(self):
        assert Interpreter._truthy(True) is True

    def test_equal_both_none(self):
        assert Interpreter._equal(None, None) is True

    def test_equal_one_none(self):
        assert Interpreter._equal(None, 1) is False
        assert Interpreter._equal(1, None) is False

    def test_equal_same_values(self):
        assert Interpreter._equal(42, 42) is True
        assert Interpreter._equal("abc", "abc") is True

    def test_equal_different_values(self):
        assert Interpreter._equal(1, 2) is False

    def test_stringify_none(self):
        assert Interpreter._stringify(None) == "null"

    def test_stringify_bool(self):
        assert Interpreter._stringify(True) == "true"
        assert Interpreter._stringify(False) == "false"

    def test_stringify_float_integer(self):
        assert Interpreter._stringify(3.0) == "3"

    def test_stringify_float_decimal(self):
        assert Interpreter._stringify(3.14) == "3.14"

    def test_stringify_list(self):
        result = Interpreter._stringify([1, 2, 3])
        assert result == "[1, 2, 3]"

    def test_stringify_dict(self):
        result = Interpreter._stringify({"a": 1})
        assert "a" in result
        assert "1" in result


# ===========================================================================
# String Concatenation Tests
# ===========================================================================


class TestStringConcatenation:
    def test_string_plus_string(self):
        """'hello' + ' world' concatenation."""
        op = BinaryOpNode(left=_lit("hello"), operator=_tok("PLUS", "+"), right=_lit(" world"), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=op, span=_span()))
        assert result == "hello world"

    def test_string_plus_number(self):
        """'val: ' + 42 coerces number to string."""
        op = BinaryOpNode(left=_lit("val: "), operator=_tok("PLUS", "+"), right=_lit(42), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=op, span=_span()))
        assert result == "val: 42"

    def test_number_plus_string(self):
        """42 + ' items' coerces number to string."""
        op = BinaryOpNode(left=_lit(42), operator=_tok("PLUS", "+"), right=_lit(" items"), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=op, span=_span()))
        assert result == "42 items"


# ===========================================================================
# Variable and Assignment Tests
# ===========================================================================


class TestVariableAssignment:
    def test_assign_to_undefined_var(self):
        """Assigning to undefined variable reports error."""
        assign = BinaryOpNode(
            left=_var("undefined_var"),
            operator=_tok("ASSIGN", "="),
            right=_lit(42),
            span=_span(),
        )
        result, interp, errors = _run(ExprStmtNode(expression=assign, span=_span()))
        assert errors.has_errors

    def test_assign_to_invalid_target(self):
        """Assigning to non-variable target reports error."""
        # (1 + 2) = 3 -> invalid target
        add = BinaryOpNode(left=_lit(1), operator=_tok("PLUS", "+"), right=_lit(2), span=_span())
        assign = BinaryOpNode(left=add, operator=_tok("ASSIGN", "="), right=_lit(3), span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=assign, span=_span()))
        assert errors.has_errors

    def test_undeclared_variable_error(self):
        """Accessing undeclared variable reports error."""
        result, interp, errors = _run(ExprStmtNode(expression=_var("nonexistent"), span=_span()))
        assert errors.has_errors


# ===========================================================================
# Map Literal Tests
# ===========================================================================


class TestMapLiteral:
    def test_map_entry_visit(self):
        """MapEntryNode returns (key, value) tuple."""
        entry = MapEntryNode(key=_lit("k"), value=_lit(42), span=_span())
        interp = Interpreter(ErrorReporter())
        result = interp.visit_map_entry(entry)
        assert result == ("k", 42)


# ===========================================================================
# Access Node Tests
# ===========================================================================


class TestAccessNode:
    def test_access_object_attribute(self):
        """Access attribute on object with hasattr."""
        interp = Interpreter(ErrorReporter())

        class Obj:
            name = "test"

        interp.environment.define("obj", Obj())
        acc = AccessNode(target=_var("obj"), property="name", span=_span())
        result = interp._execute(ExprStmtNode(expression=acc, span=_span()))
        assert result == "test"

    def test_access_missing_attribute(self):
        """Access missing attribute reports error."""
        interp = Interpreter(ErrorReporter())

        class Obj:
            pass

        interp.environment.define("obj", Obj())
        acc = AccessNode(target=_var("obj"), property="missing", span=_span())
        try:
            result = interp._execute(ExprStmtNode(expression=acc, span=_span()))
        except (HelenRuntimeExc, HelenRuntimeError):
            pass
        assert interp.errors.has_errors

    def test_access_non_indexable_type(self):
        """Access on int reports error."""
        acc = AccessNode(target=_lit(42), property="x", span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=acc, span=_span()))
        assert errors.has_errors


# ===========================================================================
# Callable Tests
# ===========================================================================


class TestCallableEdgeCases:
    def test_call_non_callable(self):
        """Calling a non-callable value reports error."""
        call = CallNode(callee=_lit(42), arguments=[], span=_span())
        result, interp, errors = _run(ExprStmtNode(expression=call, span=_span()))
        assert errors.has_errors

    def test_call_stdlib_function(self):
        """Calling a stdlib builtin function works."""
        # len([1, 2, 3]) should return 3
        call = CallNode(
            callee=_var("len"),
            arguments=[CallArgNode(name=None, value=ListLiteralNode(elements=[_lit(1), _lit(2), _lit(3)], span=_span()))],
            span=_span(),
        )
        result, interp, errors = _run(ExprStmtNode(expression=call, span=_span()))
        assert result == 3


# ===========================================================================
# Break/Continue Sentinel Tests
# ===========================================================================


class TestSentinels:
    def test_break_sentinel(self):
        """BreakStmtNode returns BreakSentinel."""
        brk = BreakStmtNode(span=_span())
        interp = Interpreter(ErrorReporter())
        result = interp.visit_break_stmt(brk)
        assert isinstance(result, BreakSentinel)

    def test_continue_sentinel(self):
        """ContinueStmtNode returns ContinueSentinel."""
        cont = ContinueStmtNode(span=_span())
        interp = Interpreter(ErrorReporter())
        result = interp.visit_continue_stmt(cont)
        assert isinstance(result, ContinueSentinel)

    def test_return_sentinel(self):
        """ReturnStmtNode returns ReturnSentinel."""
        ret = ReturnStmtNode(value=_lit(42), span=_span())
        interp = Interpreter(ErrorReporter())
        result = interp.visit_return_stmt(ret)
        assert isinstance(result, ReturnSentinel)
        assert result.value == 42

    def test_return_sentinel_no_value(self):
        """ReturnStmtNode with no value."""
        ret = ReturnStmtNode(value=None, span=_span())
        interp = Interpreter(ErrorReporter())
        result = interp.visit_return_stmt(ret)
        assert isinstance(result, ReturnSentinel)
        assert result.value is None


# ===========================================================================
# Interpret Top-Level Sentinel Unwrapping
# ===========================================================================


class TestInterpretUnwrap:
    def test_interpret_unwraps_return_sentinel(self):
        """interpret() unwraps ReturnSentinel at top level."""
        ret = ReturnStmtNode(value=_lit(99), span=_span())
        prog = ProgramNode(statements=[ret], span=_span())
        interp = Interpreter(ErrorReporter())
        result = interp.interpret(prog)
        assert result == 99

    def test_interpret_unwraps_break_sentinel(self):
        """interpret() unwraps BreakSentinel to None."""
        brk = BreakStmtNode(span=_span())
        prog = ProgramNode(statements=[brk], span=_span())
        interp = Interpreter(ErrorReporter())
        result = interp.interpret(prog)
        assert result is None

    def test_interpret_unwraps_continue_sentinel(self):
        """interpret() unwraps ContinueSentinel to None."""
        cont = ContinueStmtNode(span=_span())
        prog = ProgramNode(statements=[cont], span=_span())
        interp = Interpreter(ErrorReporter())
        result = interp.interpret(prog)
        assert result is None


# ===========================================================================
# Check Number Error Tests
# ===========================================================================


class TestCheckNumber:
    def test_subtract_non_number(self):
        """'a' - 1 raises runtime error."""
        op = BinaryOpNode(left=_lit("a"), operator=_tok("MINUS", "-"), right=_lit(1), span=_span())
        with pytest.raises(HelenRuntimeError):
            interp = Interpreter(ErrorReporter())
            interp._execute(ExprStmtNode(expression=op, span=_span()))

    def test_multiply_non_number(self):
        """'a' * 2 raises runtime error."""
        op = BinaryOpNode(left=_lit("a"), operator=_tok("STAR", "*"), right=_lit(2), span=_span())
        with pytest.raises(HelenRuntimeError):
            interp = Interpreter(ErrorReporter())
            interp._execute(ExprStmtNode(expression=op, span=_span()))

    def test_greater_non_number(self):
        """'a' > 1 raises runtime error."""
        op = BinaryOpNode(left=_lit("a"), operator=_tok("GREATER", ">"), right=_lit(1), span=_span())
        with pytest.raises(HelenRuntimeError):
            interp = Interpreter(ErrorReporter())
            interp._execute(ExprStmtNode(expression=op, span=_span()))

    def test_greater_equal_non_number(self):
        """'a' >= 1 raises runtime error."""
        op = BinaryOpNode(left=_lit("a"), operator=_tok("GREATER_EQUAL", ">="), right=_lit(1), span=_span())
        with pytest.raises(HelenRuntimeError):
            interp = Interpreter(ErrorReporter())
            interp._execute(ExprStmtNode(expression=op, span=_span()))

    def test_less_non_number(self):
        """'a' < 1 raises runtime error."""
        op = BinaryOpNode(left=_lit("a"), operator=_tok("LESS", "<"), right=_lit(1), span=_span())
        with pytest.raises(HelenRuntimeError):
            interp = Interpreter(ErrorReporter())
            interp._execute(ExprStmtNode(expression=op, span=_span()))

    def test_less_equal_non_number(self):
        """'a' <= 1 raises runtime error."""
        op = BinaryOpNode(left=_lit("a"), operator=_tok("LESS_EQUAL", "<="), right=_lit(1), span=_span())
        with pytest.raises(HelenRuntimeError):
            interp = Interpreter(ErrorReporter())
            interp._execute(ExprStmtNode(expression=op, span=_span()))


# ===========================================================================
# Const Assignment Error Tests
# ===========================================================================


class TestConstAssignment:
    def test_const_assignment_error(self):
        """Assigning to const variable raises ConstAssignmentError."""
        from helen.interpreter.exceptions import ConstAssignmentError

        const_decl = VarDeclNode(name="X", type_annotation=None, initializer=_lit(10), mutable=False, span=_span())
        assign = BinaryOpNode(
            left=_var("X", 2),
            operator=_tok("ASSIGN", "="),
            right=_lit(20),
            span=_span(2),
        )
        with pytest.raises(ConstAssignmentError):
            interp = Interpreter(ErrorReporter())
            interp.interpret(ProgramNode(statements=[const_decl, ExprStmtNode(expression=assign, span=_span(2))], span=_span()))


# ===========================================================================
# Template Ref Tests
# ===========================================================================


class TestTemplateRef:
    def test_template_ref_evaluates_expression(self):
        """TemplateRefNode evaluates inner expression."""
        from helen.core.ast import TemplateRefNode
        ref = TemplateRefNode(expression=_lit(42), span=_span())
        interp = Interpreter(ErrorReporter())
        result = interp.visit_template_ref(ref)
        assert result == 42


# ===========================================================================
# Main Block Tests
# ===========================================================================


class TestMainBlock:
    def test_main_block_creates_scope(self):
        """MainBlockNode creates new scope."""
        body = [
            VarDeclNode(name="local_var", type_annotation=None, initializer=_lit(99), mutable=True, span=_span()),
            ExprStmtNode(expression=_var("local_var"), span=_span()),
        ]
        main = MainBlockNode(body=body, span=_span())
        result, interp, errors = _run(main)
        assert result == 99
