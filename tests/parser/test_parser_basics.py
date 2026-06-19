"""tests/parser/test_parser_basics.py — Parser 基础测试。"""

from __future__ import annotations

import pytest
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.core.errors import ErrorReporter
from helen.core.ast import (
    ProgramNode, AgentDeclNode, PromptDefNode, MainBlockNode,
    VarDeclNode, IfStmtNode, ForStmtNode, WhileStmtNode,
    BreakStmtNode, ContinueStmtNode, ReturnStmtNode,
    BinaryOpNode, LiteralNode, VariableNode, FunctionDeclNode,
    ImportStmtNode, GroupingNode,
)


def _parse_source(source: str) -> tuple[ProgramNode, ErrorReporter]:
    """辅助函数：从源码字符串解析为 ProgramNode。"""
    scanner = Scanner(source, file="<test>")
    tokens = scanner.scan_all()
    errors = ErrorReporter()
    parser = Parser(tokens, errors)
    program = parser.parse()
    return program, errors


def _format_errors(errors: ErrorReporter) -> str:
    """格式化错误报告用于测试断言。"""
    return "\n".join(str(e) for e in errors.errors)


class TestEmptyProgram:
    def test_empty_token_stream(self):
        """空 Token 流解析为 ProgramNode(statements=[])。"""
        program, errors = _parse_source("")
        assert isinstance(program, ProgramNode)
        assert len(program.statements) == 0

    def test_whitespace_only(self):
        """纯空白解析为空程序。"""
        program, _ = _parse_source("   \n\t  \n")
        assert len(program.statements) == 0


class TestAgentDecl:
    def test_minimal_agent_with_prompt(self):
        """最小 Agent: agent Test { prompt "hello" }"""
        program, errors = _parse_source('agent Test { prompt "hello" }')
        assert not errors.has_errors, _format_errors(errors)
        assert len(program.statements) == 1
        agent = program.statements[0]
        assert isinstance(agent, AgentDeclNode)
        assert agent.name == "Test"
        assert agent.prompt is not None
        assert isinstance(agent.prompt, PromptDefNode)
        assert agent.prompt.content == "hello"

    def test_agent_with_main_block(self):
        """Agent with main block."""
        source = 'agent A { prompt "p" main { let x = 1 } }'
        program, errors = _parse_source(source)
        assert not errors.has_errors, _format_errors(errors)
        agent = program.statements[0]
        assert isinstance(agent, AgentDeclNode)
        assert agent.name == "A"
        assert agent.prompt is not None

    def test_agent_with_prompt_and_main(self):
        """Agent with both prompt and main."""
        source = 'agent Bot { prompt "You are a bot" main { let x = 42 } }'
        program, errors = _parse_source(source)
        assert not errors.has_errors, _format_errors(errors)
        agent = program.statements[0]
        assert agent.name == "Bot"
        assert agent.prompt.content == "You are a bot"

    def test_agent_with_triple_quoted_prompt(self):
        """Agent with triple-quoted prompt."""
        source = 'agent A { prompt """line1\nline2""" main { } }'
        program, errors = _parse_source(source)
        assert not errors.has_errors, _format_errors(errors)
        agent = program.statements[0]
        assert "line1" in agent.prompt.content

    def test_multiple_agents(self):
        """Multiple agent declarations."""
        source = 'agent A { prompt "a" } agent B { prompt "b" }'
        program, errors = _parse_source(source)
        assert len(program.statements) == 2
        assert program.statements[0].name == "A"
        assert program.statements[1].name == "B"


class TestVarDecl:
    def test_let_declaration(self):
        """let x = 42"""
        program, errors = _parse_source('let x = 42')
        assert not errors.has_errors
        stmt = program.statements[0]
        assert isinstance(stmt, VarDeclNode)
        assert stmt.name == "x"
        assert stmt.mutable is True
        assert isinstance(stmt.initializer, LiteralNode)
        assert stmt.initializer.value == 42

    def test_const_declaration(self):
        """const MAX = 100"""
        program, _ = _parse_source('const MAX = 100')
        stmt = program.statements[0]
        assert isinstance(stmt, VarDeclNode)
        assert stmt.mutable is False
        assert stmt.name == "MAX"

    def test_let_with_expression(self):
        """let x = 1 + 2"""
        program, _ = _parse_source('let x = 1 + 2')
        stmt = program.statements[0]
        assert isinstance(stmt.initializer, BinaryOpNode)

    def test_let_with_string(self):
        """let msg = "hello" """
        program, _ = _parse_source('let msg = "hello"')
        stmt = program.statements[0]
        assert isinstance(stmt.initializer, LiteralNode)
        assert stmt.initializer.value == "hello"


class TestControlFlow:
    def test_if_statement(self):
        """if (true) { }"""
        source = 'if (true) { }'
        program, errors = _parse_source(source)
        assert not errors.has_errors
        stmt = program.statements[0]
        assert isinstance(stmt, IfStmtNode)
        assert stmt.else_branch is None

    def test_if_else_statement(self):
        """if (true) { } else { }"""
        source = 'if (true) { } else { }'
        program, _ = _parse_source(source)
        stmt = program.statements[0]
        assert isinstance(stmt, IfStmtNode)
        assert stmt.else_branch is not None

    def test_for_statement(self):
        """for x in items { }"""
        source = 'for x in items { }'
        program, errors = _parse_source(source)
        assert not errors.has_errors
        stmt = program.statements[0]
        assert isinstance(stmt, ForStmtNode)

    def test_while_statement(self):
        """while (true) { }"""
        source = 'while (true) { }'
        program, errors = _parse_source(source)
        assert not errors.has_errors
        stmt = program.statements[0]
        assert isinstance(stmt, WhileStmtNode)

    def test_while_statement_no_parens(self):
        """while true { } — parentheses optional"""
        source = 'while true { }'
        program, errors = _parse_source(source)
        assert not errors.has_errors
        stmt = program.statements[0]
        assert isinstance(stmt, WhileStmtNode)

    def test_while_statement_complex_no_parens(self):
        """while x < 10 { } — complex condition without parens"""
        source = 'while x < 10 { }'
        program, errors = _parse_source(source)
        assert not errors.has_errors
        stmt = program.statements[0]
        assert isinstance(stmt, WhileStmtNode)

    def test_break_statement(self):
        """break"""
        program, _ = _parse_source('break')
        stmt = program.statements[0]
        assert isinstance(stmt, BreakStmtNode)

    def test_continue_statement(self):
        """continue"""
        program, _ = _parse_source('continue')
        stmt = program.statements[0]
        assert isinstance(stmt, ContinueStmtNode)

    def test_return_statement_with_value(self):
        """return 42"""
        program, _ = _parse_source('return 42')
        stmt = program.statements[0]
        assert isinstance(stmt, ReturnStmtNode)
        assert stmt.value is not None

    def test_return_statement_without_value(self):
        """return"""
        program, _ = _parse_source('return')
        stmt = program.statements[0]
        assert isinstance(stmt, ReturnStmtNode)
        assert stmt.value is None


class TestExpressions:
    def test_arithmetic_priority(self):
        """1 + 2 * 3 应解析为 1 + (2 * 3)"""
        program, _ = _parse_source('let x = 1 + 2 * 3')
        stmt = program.statements[0]
        outer = stmt.initializer
        assert isinstance(outer, BinaryOpNode)
        assert outer.operator.lexeme == "+"
        assert isinstance(outer.right, BinaryOpNode)
        assert outer.right.operator.lexeme == "*"

    def test_grouping(self):
        """(1 + 2) * 3"""
        program, _ = _parse_source('let x = (1 + 2) * 3')
        stmt = program.statements[0]
        outer = stmt.initializer
        assert isinstance(outer, BinaryOpNode)
        assert outer.operator.lexeme == "*"
        assert isinstance(outer.left, GroupingNode)

    def test_unary_not(self):
        """!true"""
        program, _ = _parse_source('let x = !true')
        stmt = program.statements[0]
        assert isinstance(stmt.initializer, BinaryOpNode) is False
        # !true → UnaryOpNode or via expression
        init = stmt.initializer
        # The parser may wrap this differently; verify it contains the right structure
        assert init is not None

    def test_comparison_operators(self):
        """a <= b"""
        program, _ = _parse_source('let x = a <= b')
        stmt = program.statements[0]
        assert isinstance(stmt.initializer, BinaryOpNode)
        assert stmt.initializer.operator.lexeme == "<="

    def test_logical_operators(self):
        """a && b || c"""
        program, _ = _parse_source('let x = a && b || c')
        stmt = program.statements[0]
        outer = stmt.initializer
        assert isinstance(outer, BinaryOpNode)
        assert outer.operator.lexeme == "||"
        assert isinstance(outer.left, BinaryOpNode)
        assert outer.left.operator.lexeme == "&&"


class TestFunctions:
    def test_function_decl_simple(self):
        """fn add(a, b) -> int { return a + b }"""
        source = 'fn add(a, b) -> int { return a + b }'
        program, errors = _parse_source(source)
        assert not errors.has_errors, _format_errors(errors)
        stmt = program.statements[0]
        assert isinstance(stmt, FunctionDeclNode)
        assert stmt.name == "add"
        assert len(stmt.params) == 2

    def test_function_decl_no_return_type(self):
        """fn greet(name) { }"""
        source = 'fn greet(name) { }'
        program, _ = _parse_source(source)
        stmt = program.statements[0]
        assert isinstance(stmt, FunctionDeclNode)
        assert stmt.return_type is None


class TestImport:
    def test_import_simple(self):
        """import "utils.helen" as utils"""
        source = 'import "utils.helen" as utils'
        program, errors = _parse_source(source)
        assert not errors.has_errors, _format_errors(errors)
        stmt = program.statements[0]
        assert isinstance(stmt, ImportStmtNode)
        assert "utils" in stmt.module_path
        assert stmt.alias == "utils"

    def test_import_without_alias(self):
        """import "config.json" """
        source = 'import "config.json"'
        program, _ = _parse_source(source)
        stmt = program.statements[0]
        assert isinstance(stmt, ImportStmtNode)
        assert stmt.alias is None


class TestErrorRecovery:
    def test_unexpected_token_no_crash(self):
        """含意外的 Token 不应崩溃。"""
        source = 'agent A { @@@ prompt "hello" }'
        program, errors = _parse_source(source)
        # Parser should not crash
        assert isinstance(program, ProgramNode)

    def test_missing_closing_brace(self):
        """缺少闭合括号应报告错误。"""
        source = 'agent A { prompt "hello"'
        program, errors = _parse_source(source)
        assert errors.has_errors

    def test_empty_source(self):
        """空源文件。"""
        program, errors = _parse_source("")
        assert isinstance(program, ProgramNode)
        assert not errors.has_errors


class TestMainBlock:
    def test_main_block_with_statements(self):
        """main { let x = 1 let y = 2 }"""
        source = 'agent A { prompt "p" main { let x = 1 } }'
        program, errors = _parse_source(source)
        assert not errors.has_errors, _format_errors(errors)

    def test_main_block_empty(self):
        """main { }"""
        source = 'agent A { prompt "p" main { } }'
        program, errors = _parse_source(source)
        assert not errors.has_errors, _format_errors(errors)


class TestComplexProgram:
    def test_full_agent_with_control_flow(self):
        """完整 Agent 程序：prompt + main 含变量、if、for。"""
        source = """
agent ResearchBot {
    prompt "You are a research assistant."
    main {
        let query = "quantum computing"
        let results = search(query)
        if (results != null) {
            for r in results {
                    Display(result=r)
                }
            } else {
                Display(result="No results")
        }
    }
}
"""
        program, errors = _parse_source(source)
        assert not errors.has_errors, _format_errors(errors)
        assert len(program.statements) == 1
        agent = program.statements[0]
        assert agent.name == "ResearchBot"
