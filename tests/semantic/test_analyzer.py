"""Tests for helen.semantic.analyzer — complete semantic analysis flow."""

import pytest

from helen.core.ast import (
    CallArgNode,
    CallNode,
    CatchAllNode,
    CatchClauseNode,
    ExprStmtNode,
    FinallyBlockNode,
    FnBlockNode,
    MainBlockNode,
    ProgramNode,
    PromptDefNode,
    TryStmtNode,
    VarDeclNode,
    VariableNode,
)
from helen.core.errors import ErrorCode, ErrorReporter
from helen.core.source import SourceSpan
from helen.core.tokens import Token, TokenType
from helen.semantic.analyzer import SemanticAnalyzer


def _span(line: int = 1, col: int = 1) -> SourceSpan:
    return SourceSpan("<test>", line, col, line, col + 4)


def _token(tt: TokenType = TokenType.IDENTIFIER, lexeme: str = "x") -> Token:
    return Token(tt, lexeme, None, 1, 1, 1, 5)


def _literal(value, line: int = 1) -> "LiteralNode":
    from helen.core.ast import LiteralNode
    return LiteralNode(value=value, span=_span(line))


def _var(name: str, line: int = 1) -> VariableNode:
    return VariableNode(name=name, span=_span(line))


# ---------------------------------------------------------------------------
# Helper: run analyzer on a list of statements wrapped in a program
# ---------------------------------------------------------------------------


def _analyze(*stmts) -> tuple[ErrorReporter, SemanticAnalyzer]:
    """Build a ProgramNode from statements and run the analyzer."""
    prog = ProgramNode(statements=list(stmts), span=_span())
    errors = ErrorReporter()
    analyzer = SemanticAnalyzer(errors)
    analyzer.analyze(prog)
    return errors, analyzer


# ---------------------------------------------------------------------------
# Variable declaration & reference
# ---------------------------------------------------------------------------


class TestVarDecl:
    def test_declare_and_resolve(self):
        stmt = VarDeclNode(name="x", type_annotation=None, initializer=_literal(42), mutable=True, span=_span())
        errors, _ = _analyze(stmt)
        assert not errors.has_errors

    def test_undeclared_variable(self):
        stmt = _var("unknown")
        errors, _ = _analyze(stmt)
        assert errors.has_errors
        assert any(e.code == ErrorCode.UNDECLARED_VARIABLE for e in errors.errors)

    def test_declared_variable_resolved(self):
        decl = VarDeclNode(name="x", type_annotation=None, initializer=_literal(42), mutable=True, span=_span())
        use = _var("x")
        errors, _ = _analyze(decl, use)
        assert not errors.has_errors

    def test_duplicate_declaration(self):
        d1 = VarDeclNode(name="x", type_annotation=None, initializer=_literal(1), mutable=True, span=_span(1))
        d2 = VarDeclNode(name="x", type_annotation=None, initializer=_literal(2), mutable=True, span=_span(2))
        errors, _ = _analyze(d1, d2)
        assert errors.has_errors
        assert any(e.code == ErrorCode.DUPLICATE_SYMBOL for e in errors.errors)


# ---------------------------------------------------------------------------
# Type checking (annotation mode)
# ---------------------------------------------------------------------------


class TestTypeCheck:
    def test_type_compatible(self):
        from helen.core.ast import TypeNode
        tn = TypeNode(name="int", span=_span())
        stmt = VarDeclNode(name="x", type_annotation=tn, initializer=_literal(42), mutable=True, span=_span())
        errors, _ = _analyze(stmt)
        assert not errors.has_errors

    def test_type_incompatible(self):
        from helen.core.ast import TypeNode
        tn = TypeNode(name="int", span=_span())
        stmt = VarDeclNode(name="x", type_annotation=tn, initializer=_literal("hello"), mutable=True, span=_span())
        errors, _ = _analyze(stmt)
        assert errors.has_errors
        assert any(e.code == ErrorCode.SEMANTIC_TYPE_ERROR for e in errors.errors)

    def test_no_annotation_no_check(self):
        stmt = VarDeclNode(name="x", type_annotation=None, initializer=_literal("hello"), mutable=True, span=_span())
        errors, _ = _analyze(stmt)
        assert not errors.has_errors


# ---------------------------------------------------------------------------
# Const protection
# ---------------------------------------------------------------------------


class TestConstProtection:
    def test_const_declared(self):
        stmt = VarDeclNode(name="MAX", type_annotation=None, initializer=_literal(100), mutable=False, span=_span())
        errors, _ = _analyze(stmt)
        assert not errors.has_errors

    def test_const_assignment_detected(self):
        """x = 5 where x is const should trigger CONST_ASSIGNMENT."""
        from helen.core.ast import BinaryOpNode
        from helen.core.tokens import Token, TokenType

        const_decl = VarDeclNode(name="MAX", type_annotation=None, initializer=_literal(100), mutable=False, span=_span(1))
        # Build: MAX = 5 (binary op with ASSIGN)
        assign_tok = Token(TokenType.ASSIGN, "=", None, 2, 5, 2, 6)
        # For BinaryOpNode span, we need a SourceSpan
        from helen.core.source import SourceSpan
        assign_span = SourceSpan("<test>", 2, 5, 2, 6)
        assignment = BinaryOpNode(
            left=_var("MAX", 2),
            operator=assign_tok,
            right=_literal(5, 2),
            span=assign_span,
        )
        errors, _ = _analyze(const_decl, ExprStmtNode(expression=assignment, span=assign_span))
        assert errors.has_errors
        assert any(e.code == ErrorCode.CONST_ASSIGNMENT for e in errors.errors)

    def test_let_assignment_ok(self):
        """x = 5 where x is let should NOT error."""
        from helen.core.ast import BinaryOpNode
        from helen.core.tokens import Token, TokenType
        from helen.core.source import SourceSpan

        let_decl = VarDeclNode(name="x", type_annotation=None, initializer=_literal(1), mutable=True, span=_span(1))
        assign_tok = Token(TokenType.ASSIGN, "=", None, 2, 3, 2, 4)
        assign_span = SourceSpan("<test>", 2, 3, 2, 4)
        assignment = BinaryOpNode(
            left=_var("x", 2),
            operator=assign_tok,
            right=_literal(5, 2),
            span=assign_span,
        )
        errors, _ = _analyze(let_decl, ExprStmtNode(expression=assignment, span=assign_span))
        assert not errors.has_errors


# ---------------------------------------------------------------------------
# Agent declaration
# ---------------------------------------------------------------------------


class TestAgentSemantics:
    def test_agent_with_prompt(self):
        from helen.core.ast import AgentDeclNode
        prompt = PromptDefNode(content="Hello", span=_span())
        agent = AgentDeclNode(name="MyAgent", params=[], declarations=[], prompt=prompt, logic=None, span=_span())
        errors, _ = _analyze(agent)
        assert not errors.has_errors

    def test_agent_without_prompt(self):
        from helen.core.ast import AgentDeclNode
        agent = AgentDeclNode(name="BadAgent", params=[], declarations=[], prompt=None, logic=None, span=_span())
        errors, _ = _analyze(agent)
        assert errors.has_errors
        assert any(e.code == ErrorCode.MISSING_PROMPT for e in errors.errors)

    def test_duplicate_agent_name(self):
        from helen.core.ast import AgentDeclNode
        p1 = PromptDefNode(content="a", span=_span(1))
        p2 = PromptDefNode(content="b", span=_span(2))
        a1 = AgentDeclNode(name="MyAgent", params=[], declarations=[], prompt=p1, logic=None, span=_span(1))
        a2 = AgentDeclNode(name="MyAgent", params=[], declarations=[], prompt=p2, logic=None, span=_span(2))
        errors, _ = _analyze(a1, a2)
        assert errors.has_errors
        assert any(e.code == ErrorCode.DUPLICATE_AGENT_NAME for e in errors.errors)

    def test_agent_name_lowercase_warning(self):
        from helen.core.ast import AgentDeclNode
        prompt = PromptDefNode(content="hi", span=_span())
        agent = AgentDeclNode(name="myagent", params=[], declarations=[], prompt=prompt, logic=None, span=_span())
        errors, _ = _analyze(agent)
        assert any(w.code == ErrorCode.INVALID_AGENT_NAME for w in errors.warnings)


# ---------------------------------------------------------------------------
# break / continue position
# ---------------------------------------------------------------------------


class TestControlFlowSemantics:
    def test_break_outside_loop(self):
        from helen.core.ast import BreakStmtNode
        stmt = BreakStmtNode(span=_span())
        errors, _ = _analyze(stmt)
        assert errors.has_errors
        assert any(e.code == ErrorCode.BREAK_OUTSIDE_LOOP for e in errors.errors)

    def test_continue_outside_loop(self):
        from helen.core.ast import ContinueStmtNode
        stmt = ContinueStmtNode(span=_span())
        errors, _ = _analyze(stmt)
        assert errors.has_errors
        assert any(e.code == ErrorCode.CONTINUE_OUTSIDE_LOOP for e in errors.errors)


# ---------------------------------------------------------------------------
# Return outside function
# ---------------------------------------------------------------------------


class TestReturnSemantics:
    def test_return_outside_function(self):
        from helen.core.ast import ReturnStmtNode
        stmt = ReturnStmtNode(value=None, span=_span())
        errors, _ = _analyze(stmt)
        assert errors.has_errors
        assert any(e.code == ErrorCode.RETURN_OUTSIDE_FUNCTION for e in errors.errors)


# ---------------------------------------------------------------------------
# Import path validation
# ---------------------------------------------------------------------------


class TestImportSemantics:
    def test_import_nonexistent_file(self):
        from helen.core.ast import ImportStmtNode
        stmt = ImportStmtNode(module_path="nonexistent.helen", alias=None, span=_span())
        errors, _ = _analyze(stmt)
        assert errors.has_errors
        assert any(e.code == ErrorCode.IMPORT_NOT_FOUND for e in errors.errors)


# ---------------------------------------------------------------------------
# Catch type validation
# ---------------------------------------------------------------------------


class TestCatchSemantics:
    def test_valid_catch_type(self):
        from helen.core.ast import CatchClauseNode, TypeNode
        et = TypeNode(name="TimeoutError", span=_span())
        clause = CatchClauseNode(error_type=et, error_name="e", body=[], span=_span())
        ts = TryStmtNode(body=[], catch_clauses=[clause], catch_all=None, finally_block=None, span=_span())
        errors, _ = _analyze(ts)
        assert not errors.has_errors

    def test_invalid_catch_type(self):
        from helen.core.ast import CatchClauseNode, TypeNode
        et = TypeNode(name="CustomError", span=_span())
        clause = CatchClauseNode(error_type=et, error_name="e", body=[], span=_span())
        ts = TryStmtNode(body=[], catch_clauses=[clause], catch_all=None, finally_block=None, span=_span())
        errors, _ = _analyze(ts)
        assert errors.has_errors
        assert any(e.code == ErrorCode.INVALID_CATCH_TYPE for e in errors.errors)


# ---------------------------------------------------------------------------
# Match default completeness
# ---------------------------------------------------------------------------


class TestMatchSemantics:
    def test_match_with_default(self):
        from helen.core.ast import CaseNode, MatchStmtNode
        # Declare x first so it's not "undeclared"
        decl = VarDeclNode(name="x", type_annotation=None, initializer=_literal("a"), mutable=True, span=_span())
        case = CaseNode(pattern=_literal("a"), body=[], span=_span())
        stmt = MatchStmtNode(subject=_var("x"), cases=[case], default=[_literal("fallback")], span=_span())
        errors, _ = _analyze(decl, stmt)
        assert not errors.has_errors

    def test_match_without_default(self):
        from helen.core.ast import CaseNode, MatchStmtNode
        case = CaseNode(pattern=_literal("a"), body=[], span=_span())
        stmt = MatchStmtNode(subject=_var("x"), cases=[case], default=[], span=_span())
        # Remove default by passing empty list — the analyzer checks bool(node.default)
        # which is False for empty list
        errors, _ = _analyze(stmt)
        assert errors.has_errors
        assert any(e.code == ErrorCode.MATCH_NO_DEFAULT for e in errors.errors)


# ---------------------------------------------------------------------------
# LLM if default completeness
# ---------------------------------------------------------------------------


class TestLlmIfSemantics:
    def test_llm_if_with_default(self):
        from helen.core.ast import LlmBranchNode, LlmIfStmtNode
        # branch default has condition=None
        default_branch = LlmBranchNode(condition=None, body=[], span=_span())
        stmt = LlmIfStmtNode(description="test", branches=[default_branch], span=_span())
        errors, _ = _analyze(stmt)
        assert not errors.has_errors

    def test_llm_if_without_default(self):
        from helen.core.ast import LlmBranchNode, LlmIfStmtNode
        branch = LlmBranchNode(condition=_var("x"), body=[], span=_span())
        stmt = LlmIfStmtNode(description="test", branches=[branch], span=_span())
        errors, _ = _analyze(stmt)
        assert errors.has_errors
        assert any(e.code == ErrorCode.LLM_IF_NO_DEFAULT for e in errors.errors)
