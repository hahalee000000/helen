"""Tests for hellen.interpreter — function definition and call."""

from hellen.core.ast import (
    ExprStmtNode,
    FnBlockNode,
    FunctionDeclNode,
    LiteralNode,
    ProgramNode,
    ReturnStmtNode,
    VarDeclNode,
    VariableNode,
)
from hellen.core.errors import ErrorReporter
from hellen.core.source import SourceSpan
from hellen.interpreter.interpreter import Interpreter


def _span(line: int = 1) -> SourceSpan:
    return SourceSpan("<test>", line, 1, line, 5)


def _lit(value, line: int = 1) -> LiteralNode:
    return LiteralNode(value=value, span=_span(line))


def _var(name: str, line: int = 1) -> VariableNode:
    return VariableNode(name=name, span=_span(line))


def _run(*stmts) -> tuple:
    prog = ProgramNode(statements=list(stmts), span=_span())
    errors = ErrorReporter()
    interp = Interpreter(errors)
    result = interp.interpret(prog)
    return result, errors


class TestFunctionDefinition:
    def test_fn_register(self):
        """fn definition registers but doesn't execute."""
        fn = FunctionDeclNode(
            name="greet",
            params=[],
            return_type=None,
            body=FnBlockNode(body=[ExprStmtNode(expression=_lit(42), span=_span())], span=_span()),
            span=_span(),
        )
        result, errors = _run(fn)
        assert result is None  # function def returns None
        assert not errors.has_errors


class TestFunctionCall:
    def test_call_no_params(self):
        """fn hello() { return 42 }"""
        fn = FunctionDeclNode(
            name="hello",
            params=[],
            return_type=None,
            body=FnBlockNode(body=[ReturnStmtNode(value=_lit(42), span=_span())], span=_span()),
            span=_span(),
        )
        from hellen.core.ast import CallNode

        call = CallNode(callee=_var("hello"), arguments=[], span=_span(2))
        result, errors = _run(fn, ExprStmtNode(expression=call, span=_span(2)))
        assert result == 42
        assert not errors.has_errors

    def test_call_with_params(self):
        """fn add(a, b) { return a + b }"""
        from hellen.core.ast import AgentParamNode, BinaryOpNode, CallArgNode, CallNode
        from hellen.core.tokens import Token, TokenType

        pa = AgentParamNode(name="a", type_annotation=None, default_value=None, span=_span())
        pb = AgentParamNode(name="b", type_annotation=None, default_value=None, span=_span())

        op_tok = Token(TokenType.PLUS, "+", None, 2, 1, 2, 2)
        add_expr = BinaryOpNode(left=_var("a", 2), operator=op_tok, right=_var("b", 2), span=_span(2))

        fn = FunctionDeclNode(
            name="add",
            params=[pa, pb],
            return_type=None,
            body=FnBlockNode(body=[ReturnStmtNode(value=add_expr, span=_span(2))], span=_span()),
            span=_span(),
        )

        call = CallNode(
            callee=_var("add"),
            arguments=[
                CallArgNode(name=None, value=_lit(3)),
                CallArgNode(name=None, value=_lit(4)),
            ],
            span=_span(3),
        )
        result, errors = _run(fn, ExprStmtNode(expression=call, span=_span(3)))
        assert result == 7
        assert not errors.has_errors

    def test_call_with_defaults(self):
        """fn greet(name="world") { return name }"""
        from hellen.core.ast import AgentParamNode, CallNode

        pa = AgentParamNode(name="name", type_annotation=None, default_value=_lit("world"), span=_span())
        fn = FunctionDeclNode(
            name="greet",
            params=[pa],
            return_type=None,
            body=FnBlockNode(body=[ReturnStmtNode(value=_var("name", 2), span=_span())], span=_span()),
            span=_span(),
        )

        # Call with no args — uses default
        call = CallNode(callee=_var("greet"), arguments=[], span=_span(3))
        result, errors = _run(fn, ExprStmtNode(expression=call, span=_span(3)))
        assert result == "world"
        assert not errors.has_errors


class TestRecursion:
    def test_factorial(self):
        """fn fact(n) { if (n <= 1) return 1; return n * fact(n-1) }"""
        from hellen.core.ast import AgentParamNode, BinaryOpNode, CallArgNode, CallNode, IfStmtNode, MainBlockNode
        from hellen.core.tokens import Token, TokenType

        pn = AgentParamNode(name="n", type_annotation=None, default_value=None, span=_span())

        # n <= 1
        le = BinaryOpNode(left=_var("n", 2), operator=Token(TokenType.LESS_EQUAL, "<=", None, 2, 1, 2, 3), right=_lit(1), span=_span(2))
        # return 1
        ret1 = ReturnStmtNode(value=_lit(1), span=_span(3))
        if_then = MainBlockNode(body=[ret1], span=_span())
        if_stmt = IfStmtNode(condition=le, then_branch=if_then, else_branch=None, span=_span(2))

        # fact(n-1)
        sub = BinaryOpNode(left=_var("n", 4), operator=Token(TokenType.MINUS, "-", None, 4, 1, 4, 2), right=_lit(1), span=_span(4))
        fact_call = CallNode(callee=_var("fact"), arguments=[CallArgNode(name=None, value=sub)], span=_span(4))
        # n * fact(n-1)
        mul = BinaryOpNode(left=_var("n", 4), operator=Token(TokenType.STAR, "*", None, 4, 1, 4, 2), right=fact_call, span=_span(4))
        ret2 = ReturnStmtNode(value=mul, span=_span(4))

        fn = FunctionDeclNode(
            name="fact",
            params=[pn],
            return_type=None,
            body=FnBlockNode(body=[if_stmt, ret2], span=_span()),
            span=_span(),
        )

        call = CallNode(callee=_var("fact"), arguments=[CallArgNode(name=None, value=_lit(5))], span=_span(5))
        result, errors = _run(fn, ExprStmtNode(expression=call, span=_span(5)))
        assert result == 120  # 5!
        assert not errors.has_errors
