"""Tests for helen.core.ast module.

Covers:
- AST node creation and attribute access
- accept / Visitor pattern dispatch
- ASTPrinter serialization for all node types
- SourceSpan propagation on nodes
- Node immutability (frozen dataclasses)
"""

from __future__ import annotations

import dataclasses

import pytest

from helen.core.ast import (
    ASTNode,
    ASTPrinter,
    AgentDeclNode,
    BinaryOpNode,
    CallArgNode,
    CallNode,
    ExpressionNode,
    GroupingNode,
    IfStmtNode,
    LiteralNode,
    MainBlockNode,
    PipeExprNode,
    ProgramNode,
    PromptDefNode,
    StatementNode,
    UnaryOpNode,
    VariableNode,
    VarDeclNode,
    Visitor,
)
from helen.core.source import SourceSpan
from helen.core.tokens import Token, TokenType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_SPAN = SourceSpan("test.hl", 1, 1, 1, 10)


def _make_token(
    *,
    type: TokenType = TokenType.IDENTIFIER,
    lexeme: str = "foo",
    literal=None,
    line: int = 1,
    col: int = 1,
    end_line: int = 1,
    end_col: int = 4,
    file: str = "test.hl",
) -> Token:
    """Create a Token with sensible defaults overridden by kwargs."""
    return Token(
        type=type,
        lexeme=lexeme,
        literal=literal,
        line=line,
        col=col,
        end_line=end_line,
        end_col=end_col,
        file=file,
    )


class MockVisitor(Visitor[str]):
    """A minimal concrete visitor that records which visit_* was called."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def visit_literal(self, node: LiteralNode) -> str:
        self.calls.append("visit_literal")
        return f"<literal:{node.value!r}>"

    def visit_variable(self, node: VariableNode) -> str:
        self.calls.append("visit_variable")
        return f"<var:{node.name}>"

    def visit_binary_op(self, node: BinaryOpNode) -> str:
        self.calls.append("visit_binary_op")
        return "<binary>"

    def visit_pipe_expr(self, node: PipeExprNode) -> str:
        self.calls.append("visit_pipe_expr")
        return "<pipe>"

    def visit_unary_op(self, node: UnaryOpNode) -> str:
        self.calls.append("visit_unary_op")
        return "<unary>"

    def visit_grouping(self, node: GroupingNode) -> str:
        self.calls.append("visit_grouping")
        return "<group>"

    def visit_call(self, node: CallNode) -> str:
        self.calls.append("visit_call")
        return "<call>"

    def visit_call_arg(self, node: CallArgNode) -> str:
        self.calls.append("visit_call_arg")
        return "<call_arg>"

    def visit_var_decl(self, node: VarDeclNode) -> str:
        self.calls.append("visit_var_decl")
        return "<var_decl>"

    def visit_shared_store_decl(self, node) -> str:
        self.calls.append("visit_shared_store_decl")
        return "<shared_store>"

    def visit_channel_decl(self, node) -> str:
        self.calls.append("visit_channel_decl")
        return "<channel>"

    def visit_if_stmt(self, node: IfStmtNode) -> str:
        self.calls.append("visit_if_stmt")
        return "<if>"

    def visit_agent_decl(self, node: AgentDeclNode) -> str:
        self.calls.append("visit_agent_decl")
        return "<agent>"

    def visit_context_config(self, node) -> str:
        self.calls.append("visit_context_config")
        return "<context_config>"

    def visit_prompt_def(self, node: PromptDefNode) -> str:
        self.calls.append("visit_prompt_def")
        return "<prompt>"

    def visit_main_block(self, node: MainBlockNode) -> str:
        self.calls.append("visit_main_block")
        return "<main_block>"

    def visit_program(self, node: ProgramNode) -> str:
        self.calls.append("visit_program")
        return "<program>"

    # Additional visit methods required by the full Visitor interface
    def visit_for_stmt(self, node) -> str:
        self.calls.append("visit_for_stmt")
        return "<for>"

    def visit_for_await_stmt(self, node) -> str:
        self.calls.append("visit_for_await_stmt")
        return "<for-await>"

    def visit_while_stmt(self, node) -> str:
        self.calls.append("visit_while_stmt")
        return "<while>"

    def visit_break_stmt(self, node) -> str:
        self.calls.append("visit_break_stmt")
        return "<break>"

    def visit_continue_stmt(self, node) -> str:
        self.calls.append("visit_continue_stmt")
        return "<continue>"

    def visit_return_stmt(self, node) -> str:
        self.calls.append("visit_return_stmt")
        return "<return>"

    def visit_expr_stmt(self, node) -> str:
        self.calls.append("visit_expr_stmt")
        return "<expr_stmt>"

    def visit_function_decl(self, node) -> str:
        self.calls.append("visit_function_decl")
        return "<fn>"

    def visit_lambda(self, node) -> str:
        self.calls.append("visit_lambda")
        return "<lambda>"

    def visit_protocol_decl(self, node) -> str:
        self.calls.append("visit_protocol_decl")
        return "<protocol>"

    def visit_impl_decl(self, node) -> str:
        self.calls.append("visit_impl_decl")
        return "<impl>"

    def visit_import_stmt(self, node) -> str:
        self.calls.append("visit_import_stmt")
        return "<import>"

    def visit_alias_stmt(self, node) -> str:
        self.calls.append("visit_alias_stmt")
        return "<alias>"

    def visit_type(self, node) -> str:
        self.calls.append("visit_type")
        return "<type>"

    def visit_index(self, node) -> str:
        self.calls.append("visit_index")
        return "<index>"

    def visit_access(self, node) -> str:
        self.calls.append("visit_access")
        return "<access>"

    def visit_match_expr(self, node) -> str:
        self.calls.append("visit_match_expr")
        return "<match_expr>"

    # Additional visit methods for Phase 0+ nodes
    def visit_declaration(self, node) -> str:
        self.calls.append("visit_declaration")
        return "<declaration>"

    def visit_agent_param(self, node) -> str:
        self.calls.append("visit_agent_param")
        return "<agent_param>"

    def visit_async_call_stmt(self, node) -> str:
        self.calls.append("visit_async_call_stmt")
        return "<async_call>"

    def visit_async_call_expr(self, node) -> str:
        self.calls.append("visit_async_call_expr")
        return "<async_call_expr>"

    def visit_case(self, node) -> str:
        self.calls.append("visit_case")
        return "<case>"

    def visit_range_pattern(self, node) -> str:
        self.calls.append("visit_range_pattern")
        return "<range>"

    def visit_wildcard_pattern(self, node) -> str:
        self.calls.append("visit_wildcard_pattern")
        return "<wildcard>"

    def visit_variable_pattern(self, node) -> str:
        self.calls.append("visit_variable_pattern")
        return f"<var_pattern:{node.name}>"

    def visit_type_pattern(self, node) -> str:
        self.calls.append("visit_type_pattern")
        return f"<type_pattern:{node.type_name}>"

    def visit_catch_clause(self, node) -> str:
        self.calls.append("visit_catch_clause")
        return "<catch_clause>"

    def visit_catch_all(self, node) -> str:
        self.calls.append("visit_catch_all")
        return "<catch_all>"

    def visit_finally_block(self, node) -> str:
        self.calls.append("visit_finally_block")
        return "<finally>"

    def visit_try_stmt(self, node) -> str:
        self.calls.append("visit_try_stmt")
        return "<try>"

    def visit_throw_stmt(self, node) -> str:
        self.calls.append("visit_throw_stmt")
        return "<throw>"

    def visit_assert_stmt(self, node) -> str:
        self.calls.append("visit_assert_stmt")
        return "<assert>"

    def visit_llm_branch(self, node) -> str:
        self.calls.append("visit_llm_branch")
        return "<llm_branch>"

    def visit_llm_if_stmt(self, node) -> str:
        self.calls.append("visit_llm_if_stmt")
        return "<llm_if>"

    def visit_llm_act_stmt(self, node) -> str:
        self.calls.append("visit_llm_act_stmt")
        return "<llm_act>"

    def visit_llm_act_expr(self, node) -> str:
        self.calls.append("visit_llm_act_expr")
        return "<llm_act_expr>"

    def visit_match_stmt(self, node) -> str:
        self.calls.append("visit_match_stmt")
        return "<match>"

    def visit_optional_type(self, node) -> str:
        self.calls.append("visit_optional_type")
        return "<optional_type>"

    def visit_union_type(self, node) -> str:
        self.calls.append("visit_union_type")
        return "<union_type>"

    def visit_literal_type(self, node) -> str:
        self.calls.append("visit_literal_type")
        return "<literal_type>"

    def visit_list_literal(self, node) -> str:
        self.calls.append("visit_list_literal")
        return "<list_literal>"

    def visit_map_entry(self, node) -> str:
        self.calls.append("visit_map_entry")
        return "<map_entry>"

    def visit_map_literal(self, node) -> str:
        self.calls.append("visit_map_literal")
        return "<map_literal>"

    def visit_template_ref(self, node) -> str:
        self.calls.append("visit_template_ref")
        return "<template_ref>"

    def visit_fn_block(self, node) -> str:
        self.calls.append("visit_fn_block")
        return "<fn_block>"


# ---------------------------------------------------------------------------
# Node creation and accept dispatch
# ---------------------------------------------------------------------------

class TestLiteralNode:
    """Tests for LiteralNode creation and accept dispatch."""

    def test_literal_node_create_and_accept(self) -> None:
        """Create a LiteralNode and verify accept dispatches to visit_literal."""
        span = _DEFAULT_SPAN
        node = LiteralNode(value=42, span=span)
        assert node.value == 42
        assert node.span is span
        assert isinstance(node, ExpressionNode)
        assert isinstance(node, ASTNode)

        visitor = MockVisitor()
        result = node.accept(visitor)
        assert visitor.calls == ["visit_literal"]
        assert result == "<literal:42>"

    def test_literal_node_various_values(self) -> None:
        """LiteralNode should accept str, int, float, bool, None."""
        for val in ["hello", 42, 3.14, True, False, None]:
            node = LiteralNode(value=val, span=_DEFAULT_SPAN)
            assert node.value == val


class TestVariableNode:
    """Tests for VariableNode creation and accept dispatch."""

    def test_variable_node(self) -> None:
        """Create a VariableNode and verify accept dispatches to visit_variable."""
        node = VariableNode(name="my_var", span=_DEFAULT_SPAN)
        assert node.name == "my_var"
        assert node.span is _DEFAULT_SPAN
        assert isinstance(node, ExpressionNode)

        visitor = MockVisitor()
        result = node.accept(visitor)
        assert visitor.calls == ["visit_variable"]
        assert result == "<var:my_var>"


class TestBinaryOpNode:
    """Tests for BinaryOpNode creation and accept dispatch."""

    def test_binary_op_node(self) -> None:
        """Create BinaryOpNode(1 + 2) and verify accept dispatches correctly."""
        op = _make_token(type=TokenType.PLUS, lexeme="+")
        left = LiteralNode(value=1, span=_DEFAULT_SPAN)
        right = LiteralNode(value=2, span=_DEFAULT_SPAN)
        node = BinaryOpNode(left=left, operator=op, right=right, span=_DEFAULT_SPAN)

        assert isinstance(node, ExpressionNode)
        assert node.left is left
        assert node.right is right
        assert node.operator is op

        visitor = MockVisitor()
        result = node.accept(visitor)
        assert visitor.calls == ["visit_binary_op"]
        assert result == "<binary>"


class TestUnaryOpNode:
    """Tests for UnaryOpNode creation and accept dispatch."""

    def test_unary_op_node(self) -> None:
        """Create UnaryOpNode(!x) and verify accept dispatches correctly."""
        op = _make_token(type=TokenType.BANG, lexeme="!")
        operand = VariableNode(name="x", span=_DEFAULT_SPAN)
        node = UnaryOpNode(operator=op, operand=operand, span=_DEFAULT_SPAN)

        assert isinstance(node, ExpressionNode)
        assert node.operator is op
        assert node.operand is operand

        visitor = MockVisitor()
        result = node.accept(visitor)
        assert visitor.calls == ["visit_unary_op"]
        assert result == "<unary>"


class TestGroupingNode:
    """Tests for GroupingNode creation and accept dispatch."""

    def test_grouping_node(self) -> None:
        """Create GroupingNode and verify accept dispatches correctly."""
        inner = LiteralNode(value=3.14, span=_DEFAULT_SPAN)
        node = GroupingNode(expression=inner, span=_DEFAULT_SPAN)

        assert isinstance(node, ExpressionNode)
        assert node.expression is inner

        visitor = MockVisitor()
        result = node.accept(visitor)
        assert visitor.calls == ["visit_grouping"]
        assert result == "<group>"


class TestCallNode:
    """Tests for CallNode creation and accept dispatch."""

    def test_call_node(self) -> None:
        """Create CallNode(print(x)) and verify accept dispatches correctly."""
        callee = VariableNode(name="print", span=_DEFAULT_SPAN)
        arg = CallArgNode(name=None, value=VariableNode(name="x", span=_DEFAULT_SPAN))
        node = CallNode(callee=callee, arguments=[arg], span=_DEFAULT_SPAN)

        assert isinstance(node, ExpressionNode)
        assert node.callee is callee
        assert len(node.arguments) == 1

        visitor = MockVisitor()
        result = node.accept(visitor)
        assert visitor.calls == ["visit_call"]
        assert result == "<call>"

    def test_call_arg_node(self) -> None:
        """CallArgNode should dispatch to visit_call_arg."""
        arg = CallArgNode(name="msg", value=LiteralNode(value="hi", span=_DEFAULT_SPAN))
        visitor = MockVisitor()
        result = arg.accept(visitor)
        assert visitor.calls == ["visit_call_arg"]
        assert result == "<call_arg>"


class TestVarDeclNode:
    """Tests for VarDeclNode creation and accept dispatch."""

    def test_var_decl_node_let(self) -> None:
        """let x = 42 should have mutable=True."""
        init = LiteralNode(value=42, span=_DEFAULT_SPAN)
        node = VarDeclNode(
            name="x",
            type_annotation=None,
            initializer=init,
            mutable=True,
            span=_DEFAULT_SPAN,
        )

        assert node.name == "x"
        assert node.mutable is True
        assert node.type_annotation is None
        assert node.initializer is init
        assert isinstance(node, StatementNode)

        visitor = MockVisitor()
        result = node.accept(visitor)
        assert visitor.calls == ["visit_var_decl"]
        assert result == "<var_decl>"

    def test_var_decl_node_const(self) -> None:
        """const MAX = 100 should have mutable=False."""
        init = LiteralNode(value=100, span=_DEFAULT_SPAN)
        node = VarDeclNode(
            name="MAX",
            type_annotation=None,
            initializer=init,
            mutable=False,
            span=_DEFAULT_SPAN,
        )

        assert node.name == "MAX"
        assert node.mutable is False
        assert node.initializer.value == 100

        visitor = MockVisitor()
        result = node.accept(visitor)
        assert visitor.calls == ["visit_var_decl"]
        assert result == "<var_decl>"

    def test_var_decl_no_initializer(self) -> None:
        """VarDeclNode can have no initializer."""
        node = VarDeclNode(
            name="x",
            type_annotation=None,
            initializer=None,
            mutable=True,
            span=_DEFAULT_SPAN,
        )
        assert node.initializer is None


class TestIfStmtNode:
    """Tests for IfStmtNode creation and accept dispatch."""

    def test_if_stmt_node(self) -> None:
        """if cond { ... } else { ... } should build correctly."""
        cond = VariableNode(name="cond", span=_DEFAULT_SPAN)
        then_b = VarDeclNode(
            name="a", type_annotation=None, initializer=None, mutable=True, span=_DEFAULT_SPAN
        )
        else_b = VarDeclNode(
            name="b", type_annotation=None, initializer=None, mutable=False, span=_DEFAULT_SPAN
        )
        node = IfStmtNode(condition=cond, then_branch=then_b, else_branch=else_b, span=_DEFAULT_SPAN)

        assert node.condition is cond
        assert node.then_branch is then_b
        assert node.else_branch is else_b
        assert isinstance(node, StatementNode)

        visitor = MockVisitor()
        result = node.accept(visitor)
        assert visitor.calls == ["visit_if_stmt"]
        assert result == "<if>"

    def test_if_stmt_no_else(self) -> None:
        """IfStmtNode should allow else_branch=None."""
        cond = LiteralNode(value=True, span=_DEFAULT_SPAN)
        then_b = VarDeclNode(
            name="x", type_annotation=None, initializer=None, mutable=True, span=_DEFAULT_SPAN
        )
        node = IfStmtNode(condition=cond, then_branch=then_b, else_branch=None, span=_DEFAULT_SPAN)
        assert node.else_branch is None


class TestAgentDeclNode:
    """Tests for AgentDeclNode creation and accept dispatch."""

    def test_agent_decl_node(self) -> None:
        """agent Test { prompt "hello" } should build correctly."""
        prompt = PromptDefNode(content="hello", span=_DEFAULT_SPAN)
        node = AgentDeclNode(name="Test", params=[], declarations=[], prompt=prompt, logic=None, span=_DEFAULT_SPAN)

        assert node.name == "Test"
        assert node.prompt is prompt
        assert isinstance(node, StatementNode)

        visitor = MockVisitor()
        result = node.accept(visitor)
        assert visitor.calls == ["visit_agent_decl"]
        assert result == "<agent>"

    def test_agent_decl_no_prompt(self) -> None:
        """AgentDeclNode should allow prompt=None."""
        node = AgentDeclNode(name="Empty", params=[], declarations=[], prompt=None, logic=None, span=_DEFAULT_SPAN)
        assert node.prompt is None


class TestMainBlockNode:
    """Tests for MainBlockNode creation and accept dispatch."""

    def test_main_block_node(self) -> None:
        """main { } should build correctly."""
        node = MainBlockNode(body=[], span=_DEFAULT_SPAN)
        assert node.body == []
        assert isinstance(node, StatementNode)

        visitor = MockVisitor()
        result = node.accept(visitor)
        assert visitor.calls == ["visit_main_block"]
        assert result == "<main_block>"

    def test_main_block_with_statements(self) -> None:
        """main { let x = 1 } should have non-empty body."""
        stmt = VarDeclNode(
            name="x", type_annotation=None, initializer=None, mutable=True, span=_DEFAULT_SPAN
        )
        node = MainBlockNode(body=[stmt], span=_DEFAULT_SPAN)
        assert len(node.body) == 1
        assert node.body[0] is stmt


class TestProgramNode:
    """Tests for ProgramNode creation and accept dispatch."""

    def test_program_node(self) -> None:
        """ProgramNode with multiple statements should build correctly."""
        agent = AgentDeclNode(name="A", params=[], declarations=[], prompt=None, logic=None, span=_DEFAULT_SPAN)
        main = MainBlockNode(body=[], span=_DEFAULT_SPAN)
        node = ProgramNode(statements=[agent, main], span=_DEFAULT_SPAN)

        assert len(node.statements) == 2
        assert node.statements[0] is agent
        assert node.statements[1] is main
        assert isinstance(node, ASTNode)

        visitor = MockVisitor()
        result = node.accept(visitor)
        assert visitor.calls == ["visit_program"]
        assert result == "<program>"


# ---------------------------------------------------------------------------
# ASTPrinter serialization
# ---------------------------------------------------------------------------

class TestASTPrinter:
    """Tests for the ASTPrinter visitor."""

    def test_ast_printer_literal(self) -> None:
        """ASTPrinter should print literal values correctly."""
        printer = ASTPrinter()

        assert printer.print(LiteralNode(value=42, span=_DEFAULT_SPAN)) == "42"
        assert printer.print(LiteralNode(value=3.14, span=_DEFAULT_SPAN)) == "3.14"
        assert printer.print(LiteralNode(value="hello", span=_DEFAULT_SPAN)) == '"hello"'
        assert printer.print(LiteralNode(value=True, span=_DEFAULT_SPAN)) == "true"
        assert printer.print(LiteralNode(value=False, span=_DEFAULT_SPAN)) == "false"
        assert printer.print(LiteralNode(value=None, span=_DEFAULT_SPAN)) == "null"

    def test_ast_printer_variable(self) -> None:
        """ASTPrinter should print variable names."""
        printer = ASTPrinter()
        assert printer.print(VariableNode(name="x", span=_DEFAULT_SPAN)) == "x"

    def test_ast_printer_binary_op(self) -> None:
        """ASTPrinter should print binary operations as S-expressions."""
        printer = ASTPrinter()
        op = _make_token(type=TokenType.PLUS, lexeme="+")
        left = LiteralNode(value=1, span=_DEFAULT_SPAN)
        right = LiteralNode(value=2, span=_DEFAULT_SPAN)
        node = BinaryOpNode(left=left, operator=op, right=right, span=_DEFAULT_SPAN)

        assert printer.print(node) == "(+ 1 2)"

    def test_ast_printer_unary_op(self) -> None:
        """ASTPrinter should print unary operations."""
        printer = ASTPrinter()
        op = _make_token(type=TokenType.BANG, lexeme="!")
        operand = VariableNode(name="x", span=_DEFAULT_SPAN)
        node = UnaryOpNode(operator=op, operand=operand, span=_DEFAULT_SPAN)

        assert printer.print(node) == "(! x)"

    def test_ast_printer_grouping(self) -> None:
        """ASTPrinter should print grouping."""
        printer = ASTPrinter()
        inner = BinaryOpNode(
            left=LiteralNode(value=1, span=_DEFAULT_SPAN),
            operator=_make_token(type=TokenType.PLUS, lexeme="+"),
            right=LiteralNode(value=2, span=_DEFAULT_SPAN),
            span=_DEFAULT_SPAN,
        )
        node = GroupingNode(expression=inner, span=_DEFAULT_SPAN)
        assert printer.print(node) == "(group (+ 1 2))"

    def test_ast_printer_call(self) -> None:
        """ASTPrinter should print function calls."""
        printer = ASTPrinter()
        callee = VariableNode(name="print", span=_DEFAULT_SPAN)
        arg = CallArgNode(name=None, value=VariableNode(name="x", span=_DEFAULT_SPAN))
        node = CallNode(callee=callee, arguments=[arg], span=_DEFAULT_SPAN)

        assert printer.print(node) == "(call print x)"

    def test_ast_printer_call_named_arg(self) -> None:
        """ASTPrinter prints call args by value only (name not included in visit_call)."""
        printer = ASTPrinter()
        callee = VariableNode(name="greet", span=_DEFAULT_SPAN)
        arg = CallArgNode(name="msg", value=LiteralNode(value="hi", span=_DEFAULT_SPAN))
        node = CallNode(callee=callee, arguments=[arg], span=_DEFAULT_SPAN)

        # visit_call uses a.value.accept(self), not visit_call_arg
        assert printer.print(node) == '(call greet "hi")'

    def test_ast_printer_var_decl(self) -> None:
        """ASTPrinter should print variable declarations."""
        printer = ASTPrinter()
        init = LiteralNode(value=42, span=_DEFAULT_SPAN)
        node = VarDeclNode(
            name="x", type_annotation=None, initializer=init, mutable=True, span=_DEFAULT_SPAN
        )
        assert printer.print(node) == "(let x = 42)"

    def test_ast_printer_const_decl(self) -> None:
        """ASTPrinter should print const declarations."""
        printer = ASTPrinter()
        init = LiteralNode(value=100, span=_DEFAULT_SPAN)
        node = VarDeclNode(
            name="MAX", type_annotation=None, initializer=init, mutable=False, span=_DEFAULT_SPAN
        )
        assert printer.print(node) == "(const MAX = 100)"

    def test_ast_printer_if_stmt(self) -> None:
        """ASTPrinter should print if statements."""
        printer = ASTPrinter()
        cond = VariableNode(name="flag", span=_DEFAULT_SPAN)
        then_b = VarDeclNode(
            name="a", type_annotation=None, initializer=None, mutable=True, span=_DEFAULT_SPAN
        )
        else_b = VarDeclNode(
            name="b", type_annotation=None, initializer=None, mutable=False, span=_DEFAULT_SPAN
        )
        node = IfStmtNode(condition=cond, then_branch=then_b, else_branch=else_b, span=_DEFAULT_SPAN)

        output = printer.print(node)
        assert output.startswith("(if ")
        assert "flag" in output
        assert "let" in output
        assert "const" in output

    def test_ast_printer_agent_decl(self) -> None:
        """ASTPrinter should print agent declarations."""
        printer = ASTPrinter()
        prompt = PromptDefNode(content="hello world", span=_DEFAULT_SPAN)
        node = AgentDeclNode(name="MyAgent", params=[], declarations=[], prompt=prompt, logic=None, span=_DEFAULT_SPAN)

        assert printer.print(node) == '(agent MyAgent "hello world")'

    def test_ast_printer_agent_decl_no_prompt(self) -> None:
        """ASTPrinter should handle agent without prompt."""
        printer = ASTPrinter()
        node = AgentDeclNode(name="Empty", params=[], declarations=[], prompt=None, logic=None, span=_DEFAULT_SPAN)
        assert printer.print(node) == "(agent Empty)"

    def test_ast_printer_prompt_def(self) -> None:
        """ASTPrinter should print prompt content as quoted string."""
        printer = ASTPrinter()
        node = PromptDefNode(content="You are a helpful assistant.", span=_DEFAULT_SPAN)
        assert printer.print(node) == '"You are a helpful assistant."'

    def test_ast_printer_main_block(self) -> None:
        """ASTPrinter should print main block with body."""
        printer = ASTPrinter()
        stmt = VarDeclNode(
            name="x",
            type_annotation=None,
            initializer=LiteralNode(value=1, span=_DEFAULT_SPAN),
            mutable=True,
            span=_DEFAULT_SPAN,
        )
        node = MainBlockNode(body=[stmt], span=_DEFAULT_SPAN)
        assert printer.print(node) == "(main-block (let x = 1))"

    def test_ast_printer_program(self) -> None:
        """ASTPrinter should print a complete program."""
        printer = ASTPrinter()
        agent = AgentDeclNode(name="Greeter", params=[], declarations=[], prompt=None, logic=None, span=_DEFAULT_SPAN)
        main = MainBlockNode(
            body=[
                VarDeclNode(
                    name="msg",
                    type_annotation=None,
                    initializer=LiteralNode(value="hi", span=_DEFAULT_SPAN),
                    mutable=True,
                    span=_DEFAULT_SPAN,
                ),
            ],
            span=_DEFAULT_SPAN,
        )
        program = ProgramNode(statements=[agent, main], span=_DEFAULT_SPAN)

        output = printer.print(program)
        assert output.startswith("(program ")
        assert "agent" in output
        assert "Greeter" in output
        assert "main-block" in output
        assert "let" in output

    def test_ast_printer_complex_expression(self) -> None:
        """ASTPrinter should handle nested expressions."""
        printer = ASTPrinter()
        # (- x (* 2 y))
        mul = BinaryOpNode(
            left=LiteralNode(value=2, span=_DEFAULT_SPAN),
            operator=_make_token(type=TokenType.STAR, lexeme="*"),
            right=VariableNode(name="y", span=_DEFAULT_SPAN),
            span=_DEFAULT_SPAN,
        )
        node = BinaryOpNode(
            left=VariableNode(name="x", span=_DEFAULT_SPAN),
            operator=_make_token(type=TokenType.MINUS, lexeme="-"),
            right=mul,
            span=_DEFAULT_SPAN,
        )
        assert printer.print(node) == "(- x (* 2 y))"


# ---------------------------------------------------------------------------
# SourceSpan propagation
# ---------------------------------------------------------------------------

class TestSourceSpanOnNodes:
    """Verify AST nodes correctly carry SourceSpan information."""

    def test_source_span_on_nodes(self) -> None:
        """All AST nodes should carry their SourceSpan."""
        span = SourceSpan("demo.hl", 5, 10, 5, 20)

        literal = LiteralNode(value=42, span=span)
        assert literal.span is span

        var = VariableNode(name="x", span=span)
        assert var.span is span

        op = _make_token(type=TokenType.PLUS, lexeme="+")
        binary = BinaryOpNode(
            left=literal, operator=op, right=var, span=span
        )
        assert binary.span is span

        unary = UnaryOpNode(operator=op, operand=var, span=span)
        assert unary.span is span

        grouping = GroupingNode(expression=var, span=span)
        assert grouping.span is span

        arg = CallArgNode(name=None, value=var)
        call = CallNode(callee=var, arguments=[arg], span=span)
        assert call.span is span

        var_decl = VarDeclNode(
            name="x", type_annotation=None, initializer=literal, mutable=True, span=span
        )
        assert var_decl.span is span

        if_stmt = IfStmtNode(condition=var, then_branch=var_decl, else_branch=None, span=span)
        assert if_stmt.span is span

        prompt = PromptDefNode(content="hello", span=span)
        assert prompt.span is span

        agent = AgentDeclNode(name="A", params=[], declarations=[], prompt=prompt, logic=None, span=span)
        assert agent.span is span

        main = MainBlockNode(body=[var_decl], span=span)
        assert main.span is span

        program = ProgramNode(statements=[agent, main], span=span)
        assert program.span is span


# ---------------------------------------------------------------------------
# Node immutability
# ---------------------------------------------------------------------------

class TestNodeFrozen:
    """Verify AST nodes are immutable (frozen dataclasses)."""

    def test_node_frozen(self) -> None:
        """All dataclass-based AST nodes should be frozen."""
        span = _DEFAULT_SPAN
        nodes = [
            LiteralNode(value=42, span=span),
            VariableNode(name="x", span=span),
            BinaryOpNode(
                left=LiteralNode(value=1, span=span),
                operator=_make_token(type=TokenType.PLUS, lexeme="+"),
                right=LiteralNode(value=2, span=span),
                span=span,
            ),
            UnaryOpNode(
                operator=_make_token(type=TokenType.BANG, lexeme="!"),
                operand=VariableNode(name="x", span=span),
                span=span,
            ),
            GroupingNode(expression=VariableNode(name="x", span=span), span=span),
            CallArgNode(name=None, value=VariableNode(name="x", span=span)),
            CallNode(
                callee=VariableNode(name="print", span=span),
                arguments=[CallArgNode(name=None, value=VariableNode(name="x", span=span))],
                span=span,
            ),
            VarDeclNode(
                name="x", type_annotation=None, initializer=None, mutable=True, span=span
            ),
            IfStmtNode(
                condition=VariableNode(name="cond", span=span),
                then_branch=VarDeclNode(
                    name="a", type_annotation=None, initializer=None, mutable=True, span=span
                ),
                else_branch=None,
                span=span,
            ),
            PromptDefNode(content="hello", span=span),
            AgentDeclNode(name="A", params=[], declarations=[], prompt=None, logic=None, span=span),
            MainBlockNode(body=[], span=span),
            ProgramNode(statements=[], span=span),
        ]

        for node in nodes:
            assert dataclasses.is_dataclass(node), f"{type(node)} is not a dataclass"
            # frozen dataclasses raise FrozenInstanceError on attribute assignment
            try:
                node.span = SourceSpan("x", 1, 1, 1, 1)  # type: ignore[assignment]
                raise AssertionError(f"{type(node)} should be frozen but was not")
            except dataclasses.FrozenInstanceError:
                pass  # expected
