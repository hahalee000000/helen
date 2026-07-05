"""Tests for helen.core.tokens module.

Covers:
- TokenType enum completeness (≥50 types)
- keywords() mapping coverage (43 entries)
- Token creation, string representation, attribute access, span property
"""

from helen.core.tokens import Token, TokenType, keywords
from helen.core.source import SourceSpan


class TestTokenType:
    """Tests for the TokenType enumeration."""

    def test_total_count(self) -> None:
        """TokenType should have at least 50 distinct members."""
        assert len(TokenType) >= 50

    def test_delimiters_present(self) -> None:
        """All delimiter token types should exist."""
        for name in [
            "LEFT_PAREN",
            "RIGHT_PAREN",
            "LEFT_BRACE",
            "RIGHT_BRACE",
            "LEFT_BRACKET",
            "RIGHT_BRACKET",
            "COMMA",
            "DOT",
            "COLON",
            "SEMICOLON",
            "QUESTION",
            "PIPE",
        ]:
            assert hasattr(TokenType, name), f"Missing delimiter: {name}"

    def test_operators_present(self) -> None:
        """All operator token types should exist."""
        for name in [
            "MINUS",
            "PLUS",
            "SLASH",
            "STAR",
            "PERCENT",
            "ARROW",
            "BANG",
            "BANG_EQUAL",
            "ASSIGN",
            "EQUAL_EQUAL",
            "GREATER",
            "GREATER_EQUAL",
            "LESS",
            "LESS_EQUAL",
            "AND",
            "OR",
        ]:
            assert hasattr(TokenType, name), f"Missing operator: {name}"

    def test_literals_present(self) -> None:
        """All literal token types should exist."""
        for name in [
            "IDENTIFIER",
            "STRING",
            "TRIPLE_QUOTE_STRING",
            "NUMBER",
            "TRUE",
            "FALSE",
            "NULL_KW",
        ]:
            assert hasattr(TokenType, name), f"Missing literal: {name}"

    def test_templates_present(self) -> None:
        """Template token types should exist."""
        assert hasattr(TokenType, "TEMPLATE_OPEN")
        assert hasattr(TokenType, "TEMPLATE_CLOSE")

    def test_keywords_present(self) -> None:
        """All keyword token types should exist."""
        for name in [
            "AGENT",
            "DESCRIPTION",
            "MODEL",
            "TOOLS",
            "MEMORY",
            "TEMPERATURE",
            "MAX_TURNS",
            "PROMPT",
            "LLM",
            "IMPORT",
            "LET",
            "CONST",
            "IF",
            "ELSE",
            "FOR",
            "WHILE",
            "BREAK",
            "CONTINUE",
            "RETURN",
            "AWAIT",
            "ASYNC",
            "MATCH",
            "CASE",
            "BRANCH",
            "DEFAULT",
            "ACT",
            "TRY",
            "CATCH",
            "FINALLY",
            "FN",
            "AS",
            "IN",
            "FUNCTIONS",
            "MAIN",
            "STORE",
            "CHANNEL",
        ]:
            assert hasattr(TokenType, name), f"Missing keyword: {name}"

    def test_eof_present(self) -> None:
        """EOF special token type should exist."""
        assert hasattr(TokenType, "EOF")

    def test_unique_values(self) -> None:
        """All TokenType members should have unique auto() values."""
        values = [t.value for t in TokenType]
        assert len(values) == len(set(values))


class TestKeywords:
    """Tests for the keywords() mapping."""

    def test_returns_mapping(self) -> None:
        """keywords() should return a Mapping (dict or MappingProxyType)."""
        from typing import Mapping
        kw = keywords()
        assert isinstance(kw, Mapping)

    def test_keyword_count(self):
        """Test that the keyword map contains the expected number of entries."""
        kw = keywords()
        assert len(kw) == 94  # 47 English + 47 Chinese keywords (v1.13: added 'channel', '仓库', '通道')

    def test_all_keywords_map_to_token_types(self) -> None:
        """Every keyword value should be a TokenType member."""
        kw = keywords()
        for key, val in kw.items():
            assert isinstance(val, TokenType), f"{key} -> {val}"

    def test_specific_mappings(self) -> None:
        """Spot-check known keyword → TokenType mappings."""
        kw = keywords()
        assert kw["agent"] == TokenType.AGENT
        assert kw["let"] == TokenType.LET
        assert kw["if"] == TokenType.IF
        assert kw["return"] == TokenType.RETURN
        assert kw["true"] == TokenType.TRUE
        assert kw["false"] == TokenType.FALSE
        assert kw["null"] == TokenType.NULL_KW
        assert kw["max-turns"] == TokenType.MAX_TURNS

    def test_immutability(self) -> None:
        """Returned mapping should be immutable (MappingProxyType)."""
        kw1 = keywords()
        # Should raise TypeError when trying to modify
        try:
            kw1["agent"] = TokenType.EOF
            assert False, "Should have raised TypeError"
        except TypeError:
            pass  # Expected
        # Verify original value unchanged
        kw2 = keywords()
        assert kw2["agent"] == TokenType.AGENT


class TestToken:
    """Tests for the Token dataclass."""

    def _make_token(self, **kwargs) -> Token:
        """Create a Token with sensible defaults, overridden by kwargs."""
        defaults = {
            "type": TokenType.IDENTIFIER,
            "lexeme": "foo",
            "literal": None,
            "line": 1,
            "col": 1,
            "end_line": 1,
            "end_col": 4,
            "file": "test.hl",
        }
        defaults.update(kwargs)
        return Token(**defaults)  # type: ignore

    def test_creation(self) -> None:
        """A Token should be creatable with all required fields."""
        t = self._make_token()
        assert t.type == TokenType.IDENTIFIER
        assert t.lexeme == "foo"
        assert t.literal is None
        assert t.line == 1
        assert t.col == 1
        assert t.end_line == 1
        assert t.end_col == 4
        assert t.file == "test.hl"

    def test_default_file(self) -> None:
        """Token.file should default to '<unknown>'."""
        t = Token(
            type=TokenType.EOF,
            lexeme="",
            literal=None,
            line=0,
            col=0,
            end_line=0,
            end_col=0,
        )
        assert t.file == "<unknown>"

    def test_str_with_literal(self) -> None:
        """__str__ should include literal value when present."""
        t = self._make_token(
            type=TokenType.NUMBER, lexeme="42", literal=42
        )
        s = str(t)
        assert "NUMBER" in s
        assert "42" in s

    def test_str_without_literal(self) -> None:
        """__str__ should include lexeme when no literal."""
        t = self._make_token(type=TokenType.LEFT_PAREN, lexeme="(")
        s = str(t)
        assert "LEFT_PAREN" in s
        assert "(" in s

    def test_repr_contains_type(self) -> None:
        """__repr__ should contain the token type name."""
        t = self._make_token()
        r = repr(t)
        assert "IDENTIFIER" in r

    def test_frozen(self) -> None:
        """Token should be immutable (frozen dataclass)."""
        t = self._make_token()
        import dataclasses

        assert dataclasses.is_dataclass(t)
        # frozen dataclasses raise on attribute assignment
        try:
            t.lexeme = "bar"  # type: ignore
            raise AssertionError("Expected FrozenInstanceError")
        except (AttributeError, dataclasses.FrozenInstanceError):
            pass  # expected

    def test_span_property(self) -> None:
        """Token.span should return a correct SourceSpan."""
        t = self._make_token(
            type=TokenType.STRING,
            lexeme='"hello"',
            literal="hello",
            line=5,
            col=10,
            end_line=5,
            end_col=17,
            file="main.hl",
        )
        span = t.span
        assert isinstance(span, SourceSpan)
        assert span.file == "main.hl"
        assert span.start_line == 5
        assert span.start_col == 10
        assert span.end_line == 5
        assert span.end_col == 17
