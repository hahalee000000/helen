"""Tests for agent semantics — param declaration, call param validation, import verification."""

import os
import tempfile

import pytest

from hellen.core.ast import (
    AgentDeclNode,
    AgentParamNode,
    CallArgNode,
    CallNode,
    ProgramNode,
    PromptDefNode,
    VariableNode,
)
from hellen.core.errors import ErrorCode, ErrorReporter
from hellen.core.source import SourceSpan
from hellen.semantic.analyzer import SemanticAnalyzer


def _span(line: int = 1) -> SourceSpan:
    return SourceSpan("<test>", line, 1, line, 5)


def _var(name: str, line: int = 1):
    return VariableNode(name=name, span=_span(line))


def _literal(value, line: int = 1):
    from hellen.core.ast import LiteralNode
    return LiteralNode(value=value, span=_span(line))


def _make_param(name: str, type_name: str | None = None):
    from hellen.core.ast import TypeNode
    tn = TypeNode(name=type_name, span=_span()) if type_name else None
    return AgentParamNode(name=name, type_annotation=tn, default_value=None, span=_span())


class TestAgentParamDecl:
    def test_agent_with_params(self):
        param = _make_param("input_data")
        prompt = PromptDefNode(content="process {{input_data}}", span=_span())
        agent = AgentDeclNode(name="Processor", params=[param], declarations=[], prompt=prompt, logic=None, span=_span())
        prog = ProgramNode(statements=[agent], span=_span())
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        assert not errors.has_errors

    def test_duplicate_param_names(self):
        from hellen.core.ast import FnBlockNode, FunctionDeclNode

        p1 = _make_param("x")
        p2 = _make_param("x")
        fn_body = FnBlockNode(body=[], span=_span())
        fn = FunctionDeclNode(name="dup", params=[p1, p2], return_type=None, body=fn_body, span=_span())
        prog = ProgramNode(statements=[fn], span=_span())
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        assert errors.has_errors
        assert any(e.code == ErrorCode.DUPLICATE_PARAM for e in errors.errors)

    def test_agent_duplicate_param_names(self):
        p1 = _make_param("data")
        p2 = _make_param("data")
        prompt = PromptDefNode(content="test", span=_span())
        agent = AgentDeclNode(name="TestAgent", params=[p1, p2], declarations=[], prompt=prompt, logic=None, span=_span())
        prog = ProgramNode(statements=[agent], span=_span())
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        assert errors.has_errors
        assert any(e.code == ErrorCode.DUPLICATE_PARAM for e in errors.errors)


class TestAgentParamMismatch:
    """call Agent with mismatched param names."""

    def test_call_unknown_param_errors(self):
        """Calling agent with unknown param name should error."""
        p1 = _make_param("input_data")
        prompt = PromptDefNode(content="test", span=_span())
        agent = AgentDeclNode(name="TestAgent", params=[p1], declarations=[], prompt=prompt, logic=None, span=_span())
        # call TestAgent(unknown=42)
        call = CallNode(
            callee=VariableNode(name="TestAgent", span=_span()),
            arguments=[CallArgNode(name="unknown", value=_literal(42))],
            span=_span(),
        )
        prog = ProgramNode(statements=[agent, call], span=_span())
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        assert errors.has_errors
        assert any(e.code == ErrorCode.AGENT_PARAM_MISMATCH for e in errors.errors)

    def test_call_known_param_ok(self):
        """Calling agent with known param name should not error."""
        p1 = _make_param("input_data")
        prompt = PromptDefNode(content="test", span=_span())
        agent = AgentDeclNode(name="TestAgent", params=[p1], declarations=[], prompt=prompt, logic=None, span=_span())
        call = CallNode(
            callee=VariableNode(name="TestAgent", span=_span()),
            arguments=[CallArgNode(name="input_data", value=_literal(42))],
            span=_span(),
        )
        prog = ProgramNode(statements=[agent, call], span=_span())
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        # input_data is declared in agent, not in global scope → undeclared in call arg value
        # but the param name match should NOT produce AGENT_PARAM_MISMATCH
        assert not any(e.code == ErrorCode.AGENT_PARAM_MISMATCH for e in errors.errors)


class TestImportPathValidation:
    def test_import_existing_file(self):
        """Import of a file that exists should not error."""
        from hellen.core.ast import ImportStmtNode

        # Create a temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".hellen", delete=False) as f:
            f.write("// empty")
            tmp_path = f.name

        try:
            base_dir = os.path.dirname(tmp_path)
            file_name = os.path.basename(tmp_path)
            stmt = ImportStmtNode(module_path=file_name, alias=None, span=_span())
            prog = ProgramNode(statements=[stmt], span=_span())
            errors = ErrorReporter()
            SemanticAnalyzer(errors, base_dir=base_dir).analyze(prog)
            assert not errors.has_errors
        finally:
            os.unlink(tmp_path)

    def test_import_nonexistent_relative(self):
        from hellen.core.ast import ImportStmtNode
        stmt = ImportStmtNode(module_path="./missing.hellen", alias=None, span=_span())
        prog = ProgramNode(statements=[stmt], span=_span())
        errors = ErrorReporter()
        SemanticAnalyzer(errors, base_dir="/tmp").analyze(prog)
        assert errors.has_errors
        assert any(e.code == ErrorCode.IMPORT_NOT_FOUND for e in errors.errors)


class TestSubAgentReference:
    def test_call_undeclared_agent_warns(self):
        """Calling an undeclared agent should flag the callee as undeclared variable."""
        call = CallNode(
            callee=_var("UnknownAgent"),
            arguments=[],
            span=_span(),
        )
        prog = ProgramNode(statements=[call], span=_span())
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        assert errors.has_errors
        assert any(e.code == ErrorCode.UNDECLARED_VARIABLE for e in errors.errors)
