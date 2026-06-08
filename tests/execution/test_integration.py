"""Integration tests for hellen.interpreter — full programs combining features."""

from hellen.core.ast import (
    AgentParamNode,
    BinaryOpNode,
    CallArgNode,
    CallNode,
    ExprStmtNode,
    FnBlockNode,
    FunctionDeclNode,
    IfStmtNode,
    LiteralNode,
    MainBlockNode,
    MatchStmtNode,
    ProgramNode,
    ReturnStmtNode,
    VarDeclNode,
    VariableNode,
    WhileStmtNode,
)
from hellen.core.errors import ErrorReporter
from hellen.core.source import SourceSpan
from hellen.core.tokens import Token, TokenType
from hellen.interpreter.interpreter import Interpreter


def _span(line: int = 1) -> SourceSpan:
    return SourceSpan("<test>", line, 1, line, 5)


def _lit(value, line: int = 1) -> LiteralNode:
    return LiteralNode(value=value, span=_span(line))


def _var(name: str, line: int = 1) -> VariableNode:
    return VariableNode(name=name, span=_span(line))


def _make_tok(tt: TokenType, lexeme: str, line: int = 1) -> Token:
    return Token(tt, lexeme, None, line, 1, line, len(lexeme) + 1)


def _run(*stmts) -> tuple:
    prog = ProgramNode(statements=list(stmts), span=_span())
    errors = ErrorReporter()
    interp = Interpreter(errors)
    result = interp.interpret(prog)
    return result, errors


class TestIntegration:
    def test_sum_with_loop_and_function(self):
        """
        fn sum(n) {
            let total = 0
            let i = 1
            while (i <= n) {
                total = total + i
                i = i + 1
            }
            return total
        }
        sum(10)  # 55
        """
        pn = AgentParamNode(name="n", type_annotation=None, default_value=None, span=_span())

        total_decl = VarDeclNode(name="total", type_annotation=None, initializer=_lit(0), mutable=True, span=_span(2))
        i_decl = VarDeclNode(name="i", type_annotation=None, initializer=_lit(1), mutable=True, span=_span(3))

        # i <= n
        cond = BinaryOpNode(left=_var("i", 4), operator=_make_tok(TokenType.LESS_EQUAL, "<=", 4), right=_var("n", 4), span=_span(4))

        # total = total + i
        add = BinaryOpNode(left=_var("total", 5), operator=_make_tok(TokenType.PLUS, "+", 5), right=_var("i", 5), span=_span(5))
        total_assign = BinaryOpNode(left=_var("total", 5), operator=_make_tok(TokenType.ASSIGN, "=", 5), right=add, span=_span(5))

        # i = i + 1
        add2 = BinaryOpNode(left=_var("i", 6), operator=_make_tok(TokenType.PLUS, "+", 6), right=_lit(1, 6), span=_span(6))
        i_assign = BinaryOpNode(left=_var("i", 6), operator=_make_tok(TokenType.ASSIGN, "=", 6), right=add2, span=_span(6))

        while_body = MainBlockNode(body=[
            ExprStmtNode(expression=total_assign, span=_span(5)),
            ExprStmtNode(expression=i_assign, span=_span(6)),
        ], span=_span())
        while_stmt = WhileStmtNode(condition=cond, body=while_body, span=_span(4))

        fn_body = FnBlockNode(body=[total_decl, i_decl, while_stmt, ReturnStmtNode(value=_var("total", 8), span=_span())], span=_span())
        fn = FunctionDeclNode(name="sum", params=[pn], return_type=None, body=fn_body, span=_span())

        # Call sum(10)
        call = CallNode(callee=_var("sum"), arguments=[CallArgNode(name=None, value=_lit(10))], span=_span(9))
        result, errors = _run(fn, ExprStmtNode(expression=call, span=_span(9)))
        assert result == 55
        assert not errors.has_errors

    def test_match_with_function_call(self):
        """
        fn label(x) {
            match x {
                case 1 { return "one" }
                case 2 { return "two" }
                default { return "other" }
            }
        }
        label(1)  # "one"
        label(3)  # "other"
        """
        pn = AgentParamNode(name="x", type_annotation=None, default_value=None, span=_span())

        match_stmt = MatchStmtNode(
            subject=_var("x", 2),
            cases=[
                MatchStmtNode.__dataclass_fields__
                # We'll build cases manually
            ],
            default=[],
            span=_span(),
        )
        # Actually, let's use the CaseNode constructor directly
        from hellen.core.ast import CaseNode

        case1 = CaseNode(pattern=_lit(1, 3), body=[ReturnStmtNode(value=_lit("one"), span=_span())], span=_span())
        case2 = CaseNode(pattern=_lit(2, 4), body=[ReturnStmtNode(value=_lit("two"), span=_span())], span=_span())

        match_stmt = MatchStmtNode(
            subject=_var("x", 2),
            cases=[case1, case2],
            default=[ReturnStmtNode(value=_lit("other"), span=_span())],
            span=_span(),
        )

        fn_body = FnBlockNode(body=[match_stmt], span=_span())
        fn = FunctionDeclNode(name="label", params=[pn], return_type=None, body=fn_body, span=_span())

        # Call label(1)
        call1 = CallNode(callee=_var("label"), arguments=[CallArgNode(name=None, value=_lit(1))], span=_span())
        result1, _ = _run(fn, ExprStmtNode(expression=call1, span=_span()))
        assert result1 == "one"

        # Call label(3)
        call2 = CallNode(callee=_var("label"), arguments=[CallArgNode(name=None, value=_lit(3))], span=_span())
        result2, _ = _run(fn, ExprStmtNode(expression=call2, span=_span()))
        assert result2 == "other"

    def test_const_protection_in_loop(self):
        """let MAX = 10; MAX = 5 should raise ConstAssignmentError"""
        from hellen.interpreter.exceptions import ConstAssignmentError

        decl = VarDeclNode(name="MAX", type_annotation=None, initializer=_lit(10), mutable=False, span=_span())
        op_tok = _make_tok(TokenType.ASSIGN, "=")
        assign = BinaryOpNode(left=_var("MAX", 2), operator=op_tok, right=_lit(5, 2), span=_span(2))
        try:
            _run(decl, ExprStmtNode(expression=assign, span=_span(2)))
            assert False, "Should have raised ConstAssignmentError"
        except ConstAssignmentError:
            pass  # Expected
