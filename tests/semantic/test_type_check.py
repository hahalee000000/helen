"""Tests for type checking — annotated assignment, return type, optional type null check."""

import pytest

from helen.core.ast import (
    ProgramNode,
    TypeNode,
    VarDeclNode,
)
from helen.core.errors import ErrorCode, ErrorReporter
from helen.core.source import SourceSpan
from helen.semantic.analyzer import SemanticAnalyzer


def _span(line: int = 1) -> SourceSpan:
    return SourceSpan("<test>", line, 1, line, 5)


def _literal(value, line: int = 1):
    from helen.core.ast import LiteralNode
    return LiteralNode(value=value, span=_span(line))


class TestTypeAnnotatedAssignment:
    def test_int_assignment_ok(self):
        tn = TypeNode(name="int", span=_span())
        stmt = VarDeclNode(name="x", type_annotation=tn, initializer=_literal(42), mutable=True, span=_span())
        prog = ProgramNode(statements=[stmt], span=_span())
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        assert not errors.has_errors

    def test_int_assignment_string_fails(self):
        tn = TypeNode(name="int", span=_span())
        stmt = VarDeclNode(name="x", type_annotation=tn, initializer=_literal("hello"), mutable=True, span=_span())
        prog = ProgramNode(statements=[stmt], span=_span())
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        assert errors.has_errors
        assert any(e.code == ErrorCode.SEMANTIC_TYPE_ERROR for e in errors.errors)

    def test_string_assignment_ok(self):
        tn = TypeNode(name="str", span=_span())
        stmt = VarDeclNode(name="msg", type_annotation=tn, initializer=_literal("hello"), mutable=True, span=_span())
        prog = ProgramNode(statements=[stmt], span=_span())
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        assert not errors.has_errors

    def test_bool_assignment_ok(self):
        tn = TypeNode(name="bool", span=_span())
        stmt = VarDeclNode(name="flag", type_annotation=tn, initializer=_literal(True), mutable=True, span=_span())
        prog = ProgramNode(statements=[stmt], span=_span())
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        assert not errors.has_errors

    def test_bool_assignment_number_fails(self):
        tn = TypeNode(name="bool", span=_span())
        stmt = VarDeclNode(name="flag", type_annotation=tn, initializer=_literal(1), mutable=True, span=_span())
        prog = ProgramNode(statements=[stmt], span=_span())
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        assert errors.has_errors
        assert any(e.code == ErrorCode.SEMANTIC_TYPE_ERROR for e in errors.errors)


class TestOptionalType:
    def test_null_to_optional(self):
        """NullType is compatible with OptionalType[T]."""
        from helen.semantic.types import NullType, OptionalType, StringType, type_compatible

        assert type_compatible(NullType(), OptionalType(StringType())) is True

    def test_value_to_optional(self):
        """T is compatible with OptionalType[T]."""
        from helen.semantic.types import OptionalType, StringType, type_compatible

        assert type_compatible(StringType(), OptionalType(StringType())) is True

    def test_wrong_type_to_optional(self):
        """T is not compatible with OptionalType[U] when T != U."""
        from helen.semantic.types import BoolType, OptionalType, StringType, type_compatible

        assert type_compatible(BoolType(), OptionalType(StringType())) is False


class TestUnionTypeAssignment:
    def test_member_of_union(self):
        """A value matching one union member is compatible."""
        from helen.semantic.types import IntType, StringType, UnionType, type_compatible

        u = UnionType([StringType(), IntType()])
        assert type_compatible(StringType(), u) is True

    def test_not_in_union(self):
        """A value not matching any union member is incompatible."""
        from helen.semantic.types import BoolType, StringType, UnionType, type_compatible

        u = UnionType([StringType()])
        assert type_compatible(BoolType(), u) is False


class TestReassignmentTypeCheck:
    """Type checking on reassignment (visit_binary_op ASSIGN path)."""

    def _assign_token(self):
        from helen.core.tokens import Token, TokenType
        from helen.core.source import SourceSpan
        return Token(
            type=TokenType.ASSIGN, lexeme="=", literal=None,
            line=2, col=6, end_line=2, end_col=7, file="<test>",
        )

    def _span(self, line: int = 1) -> SourceSpan:
        return SourceSpan("<test>", line, 1, line, 20)

    def _literal(self, value, line: int = 2):
        from helen.core.ast import LiteralNode
        return LiteralNode(value=value, span=self._span(line))

    def _var(self, name: str, line: int = 2):
        from helen.core.ast import VariableNode
        return VariableNode(name=name, span=self._span(line))

    def _reassign_expr(self, name: str, value):
        """Build an ExprStmtNode for: name = value."""
        from helen.core.ast import BinaryOpNode, ExprStmtNode
        binop = BinaryOpNode(
            left=self._var(name),
            operator=self._assign_token(),
            right=self._literal(value),
            span=self._span(2),
        )
        return ExprStmtNode(expression=binop, span=self._span(2))

    def _program_with_decl_and_reassign(self, type_name: str, init_value, reassign_value, line: int = 1):
        """Build a ProgramNode with: let x: type = init; x = reassign."""
        from helen.core.ast import ProgramNode, TypeNode, VarDeclNode
        tn = TypeNode(name=type_name, span=self._span(line))
        init = self._literal(init_value, line)
        decl = VarDeclNode(
            name="x", type_annotation=tn, initializer=init,
            mutable=True, span=self._span(line),
        )
        reassign = self._reassign_expr("x", reassign_value)
        return ProgramNode(statements=[decl, reassign], span=self._span(line))

    def test_str_reassign_str_ok(self):
        """let x: str = 'a'; x = 'b' — same type, should pass."""
        prog = self._program_with_decl_and_reassign("str", "a", "b")
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        assert not errors.has_errors

    def test_str_reassign_number_fails(self):
        """let x: str = 'a'; x = 3.7 — type mismatch, should fail."""
        prog = self._program_with_decl_and_reassign("str", "a", 3.7)
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        assert errors.has_errors
        assert any(e.code == ErrorCode.SEMANTIC_TYPE_ERROR for e in errors.errors)

    def test_str_reassign_bool_fails(self):
        """let x: str? = null; x = true — type mismatch, should fail."""
        prog = self._program_with_decl_and_reassign("str", "a", True)
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        assert errors.has_errors
        assert any(e.code == ErrorCode.SEMANTIC_TYPE_ERROR for e in errors.errors)

    def test_int_reassign_int_ok(self):
        """let x: int = 1; x = 2 — same type, should pass."""
        prog = self._program_with_decl_and_reassign("int", 1, 2)
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        assert not errors.has_errors

    def test_int_reassign_str_fails(self):
        """let x: int = 1; x = 'hello' — type mismatch, should fail."""
        prog = self._program_with_decl_and_reassign("int", 1, "hello")
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        assert errors.has_errors
        assert any(e.code == ErrorCode.SEMANTIC_TYPE_ERROR for e in errors.errors)

    def test_optional_str_reassign_null_ok(self):
        """let x: str? = null; x = null — null to optional, should pass."""
        from helen.core.ast import OptionalTypeNode, ProgramNode, TypeNode, VarDeclNode
        inner = TypeNode(name="str", span=self._span())
        opt = OptionalTypeNode(inner=inner, span=self._span())
        decl = VarDeclNode(
            name="x", type_annotation=opt, initializer=self._literal(None),
            mutable=True, span=self._span(),
        )
        reassign = self._reassign_expr("x", None)
        prog = ProgramNode(statements=[decl, reassign], span=self._span())
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        assert not errors.has_errors

    def test_untyped_var_reassign_any_ok(self):
        """let x = 'a'; x = 3.7 — no type annotation, no type check."""
        from helen.core.ast import ProgramNode, VarDeclNode
        decl = VarDeclNode(
            name="x", type_annotation=None, initializer=self._literal("a"),
            mutable=True, span=self._span(),
        )
        reassign = self._reassign_expr("x", 3.7)
        prog = ProgramNode(statements=[decl, reassign], span=self._span())
        errors = ErrorReporter()
        SemanticAnalyzer(errors).analyze(prog)
        assert not errors.has_errors
