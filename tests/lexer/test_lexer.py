"""Tests for helen.core.lexer module.

Covers:
- Empty input, whitespace-only input
- All 42 keyword recognitions
- Identifier parsing
- Number literals (integer, float, exponent, underscore separators)
- String literals (regular and triple-quoted, with escapes)
- Operators (single- and multi-character)
- Comments (line and block, including nested)
- Hyphenated keyword disambiguation
- Template delimiters
- Error cases (unterminated strings, illegal characters, etc.)
- Source span accuracy on tokens
- scan_one streaming mode
"""

from helen.core.lexer import Scanner
from helen.core.tokens import Token, TokenType
from helen.core.errors import ErrorCode


def _scan(source: str, file: str = "<test>") -> list[Token]:
    """Helper: create a Scanner and run scan_all()."""
    s = Scanner(source=source, file=file)
    return s.scan_all()


def _token_types(tokens: list[Token]) -> list[TokenType]:
    """Extract token types from a token list."""
    return [t.type for t in tokens]


# ── Basic / edge cases ───────────────────────────────────────────────────


class TestEmptyAndWhitespace:
    """Tests for empty and whitespace-only input."""

    def test_empty_input(self) -> None:
        """Empty input should return [EOF]."""
        tokens = _scan("")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.EOF

    def test_single_whitespace(self) -> None:
        """Pure whitespace should return [EOF]."""
        tokens = _scan("   ")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.EOF

    def test_newlines_only(self) -> None:
        """Newlines-only input should return [EOF]."""
        tokens = _scan("\n\n\n")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.EOF

    def test_mixed_whitespace(self) -> None:
        """Mixed whitespace (spaces, tabs, newlines) should return [EOF]."""
        tokens = _scan("  \t \n \r  \n")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.EOF


# ── Keywords ─────────────────────────────────────────────────────────────


class TestKeywords:
    """Tests for keyword recognition."""

    def test_keywords_recognition(self) -> None:
        """All 42 keywords should be correctly identified."""
        all_kws = [
            "agent", "description", "model", "tools", "skills",
            "sub-agents", "memory", "temperature", "max-turns",
            "prompt", "llm", "import", "let", "const", "if", "else",
            "for", "while", "break", "continue", "return", "call",
            "await", "async", "match", "case", "branch", "option",
            "default", "choose", "act", "try", "catch", "finally",
            "fn", "as", "in", "functions", "main", "true", "false",
            "null",
        ]
        for kw in all_kws:
            tokens = _scan(kw)
            # Should be keyword + EOF
            assert len(tokens) == 2, f"keyword '{kw}' produced {len(tokens)} tokens"
            assert tokens[0].type != TokenType.IDENTIFIER, (
                f"'{kw}' was parsed as IDENTIFIER, not a keyword"
            )
            assert tokens[0].lexeme == kw, f"lexeme mismatch for '{kw}'"
            assert tokens[1].type == TokenType.EOF

    def test_keyword_case_sensitive(self) -> None:
        """Keywords are case-sensitive; 'IF' should be IDENTIFIER."""
        tokens = _scan("IF")
        assert tokens[0].type == TokenType.IDENTIFIER
        assert tokens[0].lexeme == "IF"

    def test_keyword_adjacent_to_punctuation(self) -> None:
        """'if(' should produce IF + LEFT_PAREN."""
        tokens = _scan("if(")
        assert tokens[0].type == TokenType.IF
        assert tokens[1].type == TokenType.LEFT_PAREN
        assert tokens[2].type == TokenType.EOF

    def test_hyphen_keyword_sub_agents(self) -> None:
        """'sub-agents' should be recognised as the SUB_AGENTS keyword."""
        tokens = _scan("sub-agents")
        assert tokens[0].type == TokenType.SUB_AGENTS
        assert tokens[0].lexeme == "sub-agents"
        assert tokens[1].type == TokenType.EOF

    def test_hyphen_keyword_max_turns(self) -> None:
        """'max-turns' should be recognised as the MAX_TURNS keyword."""
        tokens = _scan("max-turns")
        assert tokens[0].type == TokenType.MAX_TURNS
        assert tokens[0].lexeme == "max-turns"
        assert tokens[1].type == TokenType.EOF

    def test_hyphen_not_keyword(self) -> None:
        """'x - y' should be IDENTIFIER MINUS IDENTIFIER (three tokens)."""
        tokens = _scan("x - y")
        types = _token_types(tokens)
        assert types == [TokenType.IDENTIFIER, TokenType.MINUS, TokenType.IDENTIFIER, TokenType.EOF]
        assert tokens[0].lexeme == "x"
        assert tokens[1].lexeme == "-"
        assert tokens[2].lexeme == "y"

    def test_hyphen_at_end_of_word(self) -> None:
        """'foo-' should be IDENTIFIER MINUS (hyphen without trailing alpha)."""
        tokens = _scan("foo-")
        types = _token_types(tokens)
        assert TokenType.IDENTIFIER in types
        assert TokenType.MINUS in types

    def test_true_false_null(self) -> None:
        """'true false null' should be TRUE FALSE NULL_KW."""
        tokens = _scan("true false null")
        assert tokens[0].type == TokenType.TRUE
        assert tokens[1].type == TokenType.FALSE
        assert tokens[2].type == TokenType.NULL_KW


# ── Identifiers ──────────────────────────────────────────────────────────


class TestIdentifiers:
    """Tests for identifier parsing."""

    def test_simple_identifier(self) -> None:
        """A simple identifier should be recognised."""
        tokens = _scan("foo")
        assert tokens[0].type == TokenType.IDENTIFIER
        assert tokens[0].lexeme == "foo"

    def test_underscore_start(self) -> None:
        """Identifiers may start with underscore."""
        tokens = _scan("_private")
        assert tokens[0].type == TokenType.IDENTIFIER
        assert tokens[0].lexeme == "_private"

    def test_mixed_case(self) -> None:
        """CamelCase identifiers should work."""
        tokens = _scan("myVariable")
        assert tokens[0].type == TokenType.IDENTIFIER
        assert tokens[0].lexeme == "myVariable"

    def test_identifier_with_digits(self) -> None:
        """Identifiers may contain digits (not at start)."""
        tokens = _scan("var123")
        assert tokens[0].type == TokenType.IDENTIFIER
        assert tokens[0].lexeme == "var123"

    def test_multiple_identifiers(self) -> None:
        """Multiple identifiers separated by spaces."""
        tokens = _scan("foo bar baz")
        assert tokens[0].type == TokenType.IDENTIFIER
        assert tokens[1].type == TokenType.IDENTIFIER
        assert tokens[2].type == TokenType.IDENTIFIER


# ── Numbers ──────────────────────────────────────────────────────────────


class TestNumbers:
    """Tests for numeric literal parsing."""

    def test_integer(self) -> None:
        """Integer literals should produce NUMBER tokens with int literal."""
        tokens = _scan("42")
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].lexeme == "42"
        assert tokens[0].literal == 42

    def test_zero(self) -> None:
        """Zero should parse correctly."""
        tokens = _scan("0")
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].literal == 0

    def test_float(self) -> None:
        """Floating-point literals should produce float literal."""
        tokens = _scan("3.14")
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].lexeme == "3.14"
        assert tokens[0].literal == 3.14

    def test_float_no_int_part(self) -> None:
        """'.5' should parse as 0.5."""
        tokens = _scan(".5")
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].literal == 0.5

    def test_integer_trailing_dot(self) -> None:
        """'42.' should parse as float 42.0."""
        tokens = _scan("42.")
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].literal == 42.0

    def test_exponent(self) -> None:
        """Exponential notation should parse correctly."""
        tokens = _scan("1e10")
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].literal == 1e10

    def test_exponent_negative(self) -> None:
        """Negative exponent should parse correctly."""
        tokens = _scan("1e-5")
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].literal == 1e-5

    def test_exponent_positive(self) -> None:
        """Positive exponent should parse correctly."""
        tokens = _scan("2E+3")
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].literal == 2000.0

    def test_underscore_separators(self) -> None:
        """Underscore separators in numbers should be ignored in value."""
        tokens = _scan("1_000_000")
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].literal == 1000000

    def test_float_underscore(self) -> None:
        """Underscore separators in floats."""
        tokens = _scan("1_000.5")
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].literal == 1000.5

    def test_multiple_numbers(self) -> None:
        """Multiple numbers separated by commas."""
        tokens = _scan("1, 2, 3")
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].literal == 1
        assert tokens[1].type == TokenType.COMMA
        assert tokens[2].type == TokenType.NUMBER
        assert tokens[2].literal == 2
        assert tokens[3].type == TokenType.COMMA
        assert tokens[4].type == TokenType.NUMBER
        assert tokens[4].literal == 3


# ── Strings ──────────────────────────────────────────────────────────────


class TestStrings:
    """Tests for string literal parsing."""

    def test_empty_string(self) -> None:
        """Empty string literal should produce empty literal."""
        tokens = _scan('""')
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].literal == ""

    def test_simple_string(self) -> None:
        """Simple string literal."""
        tokens = _scan('"hello"')
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].literal == "hello"

    def test_escape_n(self) -> None:
        """\\n escape should produce newline."""
        tokens = _scan('"line1\\nline2"')
        assert tokens[0].literal == "line1\nline2"

    def test_escape_t(self) -> None:
        """\\t escape should produce tab."""
        tokens = _scan('"col1\\tcol2"')
        assert tokens[0].literal == "col1\tcol2"

    def test_escape_backslash(self) -> None:
        """\\\\ escape should produce single backslash."""
        tokens = _scan('"a\\\\b"')
        assert tokens[0].literal == "a\\b"

    def test_escape_quote(self) -> None:
        """\\" escape should produce double quote."""
        tokens = _scan('"say \\"hi\\""')
        assert tokens[0].literal == 'say "hi"'

    def test_multiple_escapes(self) -> None:
        """Multiple escape sequences in one string."""
        tokens = _scan('"tab\\there\\n"')
        assert tokens[0].literal == "tab\there\n"

    def test_unterminated_string(self) -> None:
        """Unterminated string should report an error."""
        s = Scanner('"hello')
        s.scan_all()
        assert s.has_errors
        assert any(e.code == ErrorCode.UNTERMINATED_STRING for e in s.errors)

    def test_string_with_special_chars(self) -> None:
        """String with various printable characters."""
        tokens = _scan('"hello world!"')
        assert tokens[0].literal == "hello world!"


# ── Triple-quoted strings ────────────────────────────────────────────────


class TestTripleQuotedStrings:
    """Tests for triple-quoted string parsing."""

    def test_triple_quoted_simple(self) -> None:
        """Triple-quoted string on single line."""
        tokens = _scan('"""hello"""')
        assert tokens[0].type == TokenType.TRIPLE_QUOTE_STRING
        assert tokens[0].literal == "hello"

    def test_triple_quoted_multiline(self) -> None:
        """Triple-quoted string spanning multiple lines."""
        tokens = _scan('"""line1\nline2\nline3"""')
        assert tokens[0].type == TokenType.TRIPLE_QUOTE_STRING
        assert tokens[0].literal == "line1\nline2\nline3"

    def test_triple_quoted_with_escapes(self) -> None:
        """Triple-quoted strings support escape sequences."""
        tokens = _scan('"""hello\\nworld"""')
        assert tokens[0].literal == "hello\nworld"

    def test_triple_quoted_empty(self) -> None:
        """Empty triple-quoted string."""
        tokens = _scan('""""""')
        assert tokens[0].type == TokenType.TRIPLE_QUOTE_STRING
        assert tokens[0].literal == ""


# ── Operators ────────────────────────────────────────────────────────────


class TestOperators:
    """Tests for operator token recognition."""

    def test_single_char_operators(self) -> None:
        """Single-character operators: +, -, *, /, %, !, |."""
        tokens = _scan("+ - * / % ! |")
        types = _token_types(tokens)[:-1]  # drop EOF
        expected = [
            TokenType.PLUS, TokenType.MINUS, TokenType.STAR,
            TokenType.SLASH, TokenType.PERCENT, TokenType.BANG,
            TokenType.PIPE,
        ]
        assert types == expected

    def test_double_char_equality(self) -> None:
        """== and != operators."""
        tokens = _scan("== !=")
        assert tokens[0].type == TokenType.EQUAL_EQUAL
        assert tokens[1].type == TokenType.BANG_EQUAL

    def test_comparison_operators(self) -> None:
        """<, >, <=, >= operators."""
        tokens = _scan("< > <= >=")
        assert tokens[0].type == TokenType.LESS
        assert tokens[1].type == TokenType.GREATER
        assert tokens[2].type == TokenType.LESS_EQUAL
        assert tokens[3].type == TokenType.GREATER_EQUAL

    def test_logical_operators(self) -> None:
        """&& and || operators."""
        tokens = _scan("&& ||")
        assert tokens[0].type == TokenType.AND
        assert tokens[1].type == TokenType.OR

    def test_assignment(self) -> None:
        """= should produce ASSIGN."""
        tokens = _scan("=")
        assert tokens[0].type == TokenType.ASSIGN

    def test_arrow(self) -> None:
        """-> should produce ARROW."""
        tokens = _scan("->")
        assert tokens[0].type == TokenType.ARROW

    def test_punctuation(self) -> None:
        """Punctuation tokens: ( ) { } [ ] , . : ; ?."""
        tokens = _scan("( ) { } [ ] , . : ; ?")
        types = _token_types(tokens)[:-1]
        expected = [
            TokenType.LEFT_PAREN, TokenType.RIGHT_PAREN,
            TokenType.LEFT_BRACE, TokenType.RIGHT_BRACE,
            TokenType.LEFT_BRACKET, TokenType.RIGHT_BRACKET,
            TokenType.COMMA, TokenType.DOT, TokenType.COLON,
            TokenType.SEMICOLON, TokenType.QUESTION,
        ]
        assert types == expected


# ── Comments ─────────────────────────────────────────────────────────────


class TestComments:
    """Tests for comment handling."""

    def test_line_comment(self) -> None:
        """Line comment should be skipped."""
        tokens = _scan("// this is a comment\n42")
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].literal == 42

    def test_line_comment_at_end(self) -> None:
        """Line comment at end of file (no trailing newline)."""
        tokens = _scan("// comment")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.EOF

    def test_block_comment(self) -> None:
        """Block comment should be skipped."""
        tokens = _scan("/* comment */ 42")
        assert tokens[0].type == TokenType.NUMBER

    def test_block_comment_multiline(self) -> None:
        """Block comment spanning multiple lines."""
        tokens = _scan("/* line1\nline2 */ 42")
        assert tokens[0].type == TokenType.NUMBER

    def test_nested_block_comment(self) -> None:
        """Nested block comments should be handled."""
        tokens = _scan("/* outer /* inner */ */ 42")
        assert tokens[0].type == TokenType.NUMBER

    def test_unterminated_block_comment(self) -> None:
        """Unterminated block comment should report an error."""
        s = Scanner("/* unterminated")
        s.scan_all()
        assert s.has_errors
        assert any(
            e.code == ErrorCode.SCANNER_ERROR and "Unterminated" in e.message
            for e in s.errors
        )

    def test_comment_between_tokens(self) -> None:
        """Comments between tokens should not affect parsing."""
        tokens = _scan("foo /* skip */ bar")
        assert tokens[0].type == TokenType.IDENTIFIER
        assert tokens[0].lexeme == "foo"
        assert tokens[1].type == TokenType.IDENTIFIER
        assert tokens[1].lexeme == "bar"


# ── Whitespace ───────────────────────────────────────────────────────────


class TestWhitespace:
    """Tests for whitespace skipping."""

    def test_whitespace_skipped(self) -> None:
        """Whitespace between tokens should be ignored."""
        tokens = _scan("foo   bar")
        assert tokens[0].lexeme == "foo"
        assert tokens[1].lexeme == "bar"

    def test_tabs_and_newlines(self) -> None:
        """Tabs and newlines should be treated as whitespace."""
        tokens = _scan("foo\t\nbar")
        assert tokens[0].lexeme == "foo"
        assert tokens[1].lexeme == "bar"

    def test_leading_whitespace(self) -> None:
        """Leading whitespace should not affect parsing."""
        tokens = _scan("  \n  foo")
        assert tokens[0].lexeme == "foo"


# ── Templates ────────────────────────────────────────────────────────────


class TestTemplates:
    """Tests for template delimiter parsing."""

    def test_template_open_close(self) -> None:
        """{{var}} should produce TEMPLATE_OPEN + IDENTIFIER + TEMPLATE_CLOSE."""
        tokens = _scan("{{var}}")
        assert tokens[0].type == TokenType.TEMPLATE_OPEN
        assert tokens[1].type == TokenType.IDENTIFIER
        assert tokens[1].lexeme == "var"
        assert tokens[2].type == TokenType.TEMPLATE_CLOSE

    def test_template_vars(self) -> None:
        """{{name}} produces TEMPLATE_OPEN, IDENTIFIER, TEMPLATE_CLOSE."""
        tokens = _scan("{{name}}")
        types = _token_types(tokens)
        assert TokenType.TEMPLATE_OPEN in types
        assert TokenType.TEMPLATE_CLOSE in types

    def test_template_in_string(self) -> None:
        """Template delimiters appearing in non-template context."""
        tokens = _scan("{{}}")
        assert tokens[0].type == TokenType.TEMPLATE_OPEN
        assert tokens[1].type == TokenType.TEMPLATE_CLOSE


# ── Error cases ──────────────────────────────────────────────────────────


class TestErrorCases:
    """Tests for error reporting."""

    def test_illegal_character(self) -> None:
        """Illegal character '@' should report an error."""
        s = Scanner("@")
        s.scan_all()
        assert s.has_errors
        assert any(
            e.code == ErrorCode.SCANNER_ERROR and "@" in e.message
            for e in s.errors
        )

    def test_multiple_illegal_chars(self) -> None:
        """Multiple illegal characters should each be reported."""
        s = Scanner("@#$")
        s.scan_all()
        assert len(s.errors) == 3

    def test_illegal_char_does_not_stop_scanning(self) -> None:
        """Scanning should continue after an illegal character."""
        tokens = _scan("@ foo")
        # Should still get the identifier after the error
        types = _token_types(tokens)
        assert TokenType.IDENTIFIER in types
        assert TokenType.EOF in types


# ── Source span accuracy ─────────────────────────────────────────────────


class TestSourceSpan:
    """Tests for line/col/end_line/end_col accuracy on tokens."""

    def test_first_token_position(self) -> None:
        """First token should start at line=1, col=1."""
        tokens = _scan("foo")
        assert tokens[0].line == 1
        assert tokens[0].col == 1

    def test_token_after_newline(self) -> None:
        """Token after newline should have correct line number."""
        tokens = _scan("foo\nbar")
        assert tokens[0].line == 1
        assert tokens[1].line == 2
        assert tokens[1].col == 1

    def test_token_with_offset(self) -> None:
        """Token at column offset should have correct col."""
        tokens = _scan("  foo")
        assert tokens[0].col == 3
        assert tokens[0].lexeme == "foo"

    def test_string_span(self) -> None:
        """String token should span from opening to closing quote."""
        tokens = _scan('"hello"')
        t = tokens[0]
        assert t.line == 1
        assert t.col == 1
        assert t.end_col == 8  # 1-based, exclusive end

    def test_multiline_token_span(self) -> None:
        """Multi-line triple-quoted string should span multiple lines."""
        tokens = _scan('"""line1\nline2"""')
        t = tokens[0]
        assert t.start_line == 1 if hasattr(t, 'start_line') else t.line == 1
        assert t.end_line == 2

    def test_number_span(self) -> None:
        """Number token span should match lexeme length."""
        tokens = _scan("12345")
        t = tokens[0]
        assert t.col == 1
        assert t.end_col == 6  # 1-based exclusive: positions 1-5


# ── Agent minimal program ────────────────────────────────────────────────


class TestAgentMinimal:
    """Tests for a minimal agent definition."""

    def test_agent_minimal(self) -> None:
        """'agent Test { prompt \"hello\" }' should produce correct tokens."""
        source = 'agent Test { prompt "hello" }'
        tokens = _scan(source)
        types = _token_types(tokens)[:-1]  # drop EOF
        expected = [
            TokenType.AGENT,
            TokenType.IDENTIFIER,
            TokenType.LEFT_BRACE,
            TokenType.PROMPT,
            TokenType.STRING,
            TokenType.RIGHT_BRACE,
        ]
        assert types == expected
        assert tokens[1].lexeme == "Test"
        assert tokens[4].literal == "hello"


# ── EOF token ────────────────────────────────────────────────────────────


class TestEOF:
    """Tests for EOF token generation."""

    def test_eof_token(self) -> None:
        """scan_all should always end with an EOF token."""
        tokens = _scan("foo")
        assert tokens[-1].type == TokenType.EOF

    def test_eof_on_empty(self) -> None:
        """Empty source should produce just EOF."""
        tokens = _scan("")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.EOF

    def test_eof_has_file(self) -> None:
        """EOF token should carry the file name."""
        tokens = _scan("x", file="test.hl")
        assert tokens[-1].file == "test.hl"


# ── scan_one (streaming mode) ────────────────────────────────────────────


class TestScanOne:
    """Tests for scan_one streaming mode."""

    def test_scan_one_returns_token(self) -> None:
        """scan_one should return the next token."""
        s = Scanner("foo bar")
        t = s.scan_one()
        assert t.type == TokenType.IDENTIFIER
        assert t.lexeme == "foo"

    def test_scan_one_multiple(self) -> None:
        """Multiple scan_one calls should return tokens in order.

        Note: whitespace is silently skipped, so use comma-separated
        tokens or call scan_one enough times to skip whitespace phases.
        """
        s = Scanner("foo,bar")
        t1 = s.scan_one()
        t2 = s.scan_one()
        t3 = s.scan_one()
        assert t1.lexeme == "foo"
        assert t2.lexeme == ","
        assert t3.lexeme == "bar"

    def test_scan_one_eof(self) -> None:
        """scan_one at end of source should return EOF."""
        s = Scanner("x")
        s.scan_one()  # consume 'x'
        t = s.scan_one()
        assert t.type == TokenType.EOF

    def test_scan_one_empty(self) -> None:
        """scan_one on empty source should return EOF."""
        s = Scanner("")
        t = s.scan_one()
        assert t.type == TokenType.EOF


# ── Edge cases ───────────────────────────────────────────────────────────


class TestEdgeCases:
    """Additional edge-case tests."""

    def test_dot_not_followed_by_digit(self) -> None:
        """'.foo' should produce DOT + IDENTIFIER."""
        tokens = _scan(".foo")
        assert tokens[0].type == TokenType.DOT
        assert tokens[1].type == TokenType.IDENTIFIER

    def test_negative_number_is_minus_plus_number(self) -> None:
        """'-5' should be MINUS NUMBER (unary minus is not a single token)."""
        tokens = _scan("-5")
        assert tokens[0].type == TokenType.MINUS
        assert tokens[1].type == TokenType.NUMBER

    def test_single_pipe_vs_double(self) -> None:
        """Single '|' is PIPE, '||' is OR."""
        tokens1 = _scan("|")
        tokens2 = _scan("||")
        assert tokens1[0].type == TokenType.PIPE
        assert tokens2[0].type == TokenType.OR

    def test_single_ampersand_error(self) -> None:
        """Single '&' should produce an error (not a valid token)."""
        s = Scanner("&")
        s.scan_all()
        assert s.has_errors

    def test_and_single_vs_double(self) -> None:
        """'&&' is AND, single '&' is an error."""
        s = Scanner("& &&")
        s.scan_all()
        assert s.has_errors  # from the single '&'
        # But should still parse the AND
        types = _token_types(s._tokens)
        assert TokenType.AND in types

    def test_scan_all_resets_state(self) -> None:
        """Calling scan_all twice should reset internal state."""
        s = Scanner("foo")
        t1 = s.scan_all()
        t2 = s.scan_all()
        assert len(t1) == len(t2)

    def test_errors_property_is_copy(self) -> None:
        """errors property should return a copy."""
        s = Scanner("@")
        s.scan_all()
        e1 = s.errors
        e1.clear()
        assert len(s.errors) > 0  # original should not be affected
