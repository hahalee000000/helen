"""Test Chinese fullwidth punctuation support in the Helen lexer and parser.

Fullwidth (U+FF00) punctuation characters are the Chinese IME equivalents
of ASCII operators and delimiters.  They map to the same TokenType values
so that users can write Helen code entirely in Chinese without switching
IME modes for operators, parentheses, braces, etc.
"""

import pytest
from helen.core.lexer import Scanner
from helen.core.tokens import TokenType


class TestChinesePunctuationLexer:
    """Verify the lexer recognizes fullwidth punctuation as correct token types."""

    # ── Single-character delimiters ────────────────────────────────────

    def test_fullwidth_parens(self):
        source = "（x）"
        tokens = self._scan(source)
        assert tokens[0].type == TokenType.LEFT_PAREN
        assert tokens[0].lexeme == "（"
        assert tokens[1].type == TokenType.IDENTIFIER
        assert tokens[2].type == TokenType.RIGHT_PAREN
        assert tokens[2].lexeme == "）"

    def test_fullwidth_braces(self):
        source = "｛ x ｝"
        tokens = self._scan(source)
        assert tokens[0].type == TokenType.LEFT_BRACE
        assert tokens[0].lexeme == "｛"
        assert tokens[2].type == TokenType.RIGHT_BRACE
        assert tokens[2].lexeme == "｝"

    def test_fullwidth_brackets(self):
        source = "［1， 2， 3］"
        tokens = self._scan(source)
        assert tokens[0].type == TokenType.LEFT_BRACKET
        assert tokens[0].lexeme == "［"
        assert tokens[-1].type == TokenType.RIGHT_BRACKET
        assert tokens[-1].lexeme == "］"

    def test_fullwidth_comma(self):
        source = "f（a， b）"
        tokens = self._scan(source)
        comma = next(t for t in tokens if t.type == TokenType.COMMA)
        assert comma.lexeme == "，"

    def test_fullwidth_colon(self):
        source = "x： int"
        tokens = self._scan(source)
        colon = next(t for t in tokens if t.type == TokenType.COLON)
        assert colon.lexeme == "："

    def test_fullwidth_semicolon(self):
        source = "x ＝ 1； y ＝ 2"
        tokens = self._scan(source)
        semi = next(t for t in tokens if t.type == TokenType.SEMICOLON)
        assert semi.lexeme == "；"

    def test_fullwidth_question(self):
        source = "x： int？"
        tokens = self._scan(source)
        q = next(t for t in tokens if t.type == TokenType.QUESTION)
        assert q.lexeme == "？"

    def test_fullwidth_dot(self):
        source = "obj．prop"
        tokens = self._scan(source)
        dot = next(t for t in tokens if t.type == TokenType.DOT)
        assert dot.lexeme == "．"

    # ── Single-character operators ─────────────────────────────────────

    def test_fullwidth_plus(self):
        source = "a ＋ b"
        tokens = self._scan(source)
        plus = next(t for t in tokens if t.type == TokenType.PLUS)
        assert plus.lexeme == "＋"

    def test_fullwidth_minus(self):
        source = "a － b"
        tokens = self._scan(source)
        minus = next(t for t in tokens if t.type == TokenType.MINUS)
        assert minus.lexeme == "－"

    def test_fullwidth_star(self):
        source = "a ＊ b"
        tokens = self._scan(source)
        star = next(t for t in tokens if t.type == TokenType.STAR)
        assert star.lexeme == "＊"

    def test_fullwidth_slash(self):
        source = "a ／ b"
        tokens = self._scan(source)
        slash = next(t for t in tokens if t.type == TokenType.SLASH)
        assert slash.lexeme == "／"

    def test_fullwidth_percent(self):
        source = "a ％ b"
        tokens = self._scan(source)
        pct = next(t for t in tokens if t.type == TokenType.PERCENT)
        assert pct.lexeme == "％"

    def test_fullwidth_bang(self):
        source = "！a"
        tokens = self._scan(source)
        assert tokens[0].type == TokenType.BANG
        assert tokens[0].lexeme == "！"

    def test_fullwidth_assign(self):
        source = "x ＝ 42"
        tokens = self._scan(source)
        assert tokens[1].type == TokenType.ASSIGN
        assert tokens[1].lexeme == "＝"

    def test_fullwidth_greater(self):
        source = "x ＞ 0"
        tokens = self._scan(source)
        gt = next(t for t in tokens if t.type == TokenType.GREATER)
        assert gt.lexeme == "＞"

    def test_fullwidth_less(self):
        source = "x ＜ 10"
        tokens = self._scan(source)
        lt = next(t for t in tokens if t.type == TokenType.LESS)
        assert lt.lexeme == "＜"

    def test_fullwidth_pipe(self):
        source = "a ｜ b"
        tokens = self._scan(source)
        pipe = next(t for t in tokens if t.type == TokenType.PIPE)
        assert pipe.lexeme == "｜"

    # ── Two-character operators ────────────────────────────────────────

    def test_fullwidth_bang_equal(self):
        source = "x ！＝ 0"
        tokens = self._scan(source)
        ne = next(t for t in tokens if t.type == TokenType.BANG_EQUAL)
        assert ne.lexeme == "！＝"

    def test_fullwidth_equal_equal(self):
        source = "x ＝＝ 0"
        tokens = self._scan(source)
        eq = next(t for t in tokens if t.type == TokenType.EQUAL_EQUAL)
        assert eq.lexeme == "＝＝"

    def test_fullwidth_greater_equal(self):
        source = "x ＞＝ 0"
        tokens = self._scan(source)
        ge = next(t for t in tokens if t.type == TokenType.GREATER_EQUAL)
        assert ge.lexeme == "＞＝"

    def test_fullwidth_less_equal(self):
        source = "x ＜＝ 0"
        tokens = self._scan(source)
        le = next(t for t in tokens if t.type == TokenType.LESS_EQUAL)
        assert le.lexeme == "＜＝"

    def test_fullwidth_and(self):
        source = "a ＆＆ b"
        tokens = self._scan(source)
        and_op = next(t for t in tokens if t.type == TokenType.AND)
        assert and_op.lexeme == "＆＆"

    def test_fullwidth_or(self):
        source = "a ｜｜ b"
        tokens = self._scan(source)
        or_op = next(t for t in tokens if t.type == TokenType.OR)
        assert or_op.lexeme == "｜｜"

    def test_fullwidth_pipe_right(self):
        source = "x ｜＞ f"
        tokens = self._scan(source)
        pr = next(t for t in tokens if t.type == TokenType.PIPE_RIGHT)
        assert pr.lexeme == "｜＞"

    def test_fullwidth_arrow(self):
        source = "－＞ int"
        tokens = self._scan(source)
        arrow = next(t for t in tokens if t.type == TokenType.ARROW)
        assert arrow.lexeme == "－＞"

    def test_fullwidth_dotdot(self):
        source = "1．．10"
        tokens = self._scan(source)
        dd = next(t for t in tokens if t.type == TokenType.DOTDOT)
        assert dd.lexeme == "．．"

    # ── Mixed ASCII and fullwidth ──────────────────────────────────────

    def test_mixed_parens(self):
        """ASCII and fullwidth parens can be mixed (though unusual)."""
        source = "f（a， b)"
        tokens = self._scan(source)
        assert tokens[1].type == TokenType.LEFT_PAREN
        assert tokens[1].lexeme == "（"
        assert tokens[-1].type == TokenType.RIGHT_PAREN
        assert tokens[-1].lexeme == ")"

    def test_mixed_operators(self):
        """ASCII and fullwidth operators can be mixed."""
        source = "x ＝ y ＋ z * w"
        tokens = self._scan(source)
        types = [t.type for t in tokens]
        assert TokenType.ASSIGN in types
        assert TokenType.PLUS in types
        assert TokenType.STAR in types

    # ── Full program tests ─────────────────────────────────────────────

    def test_full_chinese_program_no_errors(self):
        """A complete Chinese program with fullwidth punctuation should lex cleanly."""
        source = """\
定义 x ＝ 10
常量 Y ＝ 20
函数 加（甲： int， 乙： int）： int ｛
    返回 甲 ＋ 乙
｝
如果 x ＞ 0 ｛
    定义 结果 ＝ 加（x， Y）
｝ 否则 ｛
    定义 结果 ＝ 0
｝
"""
        scanner = Scanner(source=source, file="<test>")
        scanner.scan_all()
        assert not scanner.has_errors, f"Unexpected errors: {scanner.errors}"

    def test_full_chinese_with_two_char_ops(self):
        """Two-character fullwidth operators in a real program."""
        source = """\
定义 a ＝ 5
定义 b ＝ 10
如果 a ＜＝ b ＆＆ b ＞＝ a ｛
    定义 c ＝ a ＋ b
｝
定义 eq ＝ a ＝＝ 5
定义 ne ＝ a ！＝ 10
"""
        scanner = Scanner(source=source, file="<test>")
        scanner.scan_all()
        assert not scanner.has_errors, f"Unexpected errors: {scanner.errors}"

    def test_fullwidth_pipe_expression(self):
        """Fullwidth pipe operator in expression."""
        source = "定义 result ＝ 5 ｜＞ double"
        scanner = Scanner(source=source, file="<test>")
        scanner.scan_all()
        assert not scanner.has_errors, f"Unexpected errors: {scanner.errors}"

    def test_fullwidth_arrow_return_type(self):
        """Fullwidth arrow in function return type."""
        source = """\
函数 加（a： int， b： int） －＞ int ｛
    返回 a ＋ b
｝
"""
        scanner = Scanner(source=source, file="<test>")
        scanner.scan_all()
        assert not scanner.has_errors, f"Unexpected errors: {scanner.errors}"

    def test_fullwidth_range_pattern(self):
        """Fullwidth dotdot in range pattern."""
        source = """\
匹配 score ｛
    情况 90．．100 ｛ print（\"A\"） ｝
    默认 ｛ print（\"F\"） ｝
｝
"""
        scanner = Scanner(source=source, file="<test>")
        scanner.scan_all()
        assert not scanner.has_errors, f"Unexpected errors: {scanner.errors}"

    # ── Edge cases ─────────────────────────────────────────────────────

    def test_fullwidth_bang_as_prefix(self):
        """Fullwidth ！ as logical NOT prefix."""
        source = "！真"
        tokens = self._scan(source)
        assert tokens[0].type == TokenType.BANG
        assert tokens[0].lexeme == "！"
        assert tokens[1].type == TokenType.TRUE

    def test_fullwidth_minus_as_prefix(self):
        """Fullwidth － as unary negation."""
        source = "－5"
        tokens = self._scan(source)
        assert tokens[0].type == TokenType.MINUS
        assert tokens[0].lexeme == "－"

    def test_fullwidth_lone_ampersand_error(self):
        """Lone fullwidth ＆ should produce a helpful error."""
        source = "a ＆ b"
        scanner = Scanner(source=source, file="<test>")
        scanner.scan_all()
        assert scanner.has_errors
        assert any("＆＆" in str(e) for e in scanner.errors)

    # ── Chinese quotation marks ─────────────────────────────────────────

    def test_chinese_double_quotes(self):
        """\u201c...\u201d should produce a STRING token."""
        source = "\u201c你好世界\u201d"
        tokens = self._scan(source)
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].literal == "你好世界"

    def test_chinese_single_quotes(self):
        """\u2018...\u2019 should produce a STRING token."""
        source = "\u2018你好世界\u2019"
        tokens = self._scan(source)
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].literal == "你好世界"

    def test_corner_brackets(self):
        """\u300c...\u300d should produce a STRING token."""
        source = "\u300c你好世界\u300d"
        tokens = self._scan(source)
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].literal == "你好世界"

    def test_white_corner_brackets(self):
        """\u300e...\u300f should produce a STRING token."""
        source = "\u300e你好世界\u300f"
        tokens = self._scan(source)
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].literal == "你好世界"

    def test_fullwidth_quote(self):
        """\uff02...\uff02 (symmetric) should produce a STRING token."""
        source = "\uff02你好世界\uff02"
        tokens = self._scan(source)
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].literal == "你好世界"

    def test_chinese_quote_escapes(self):
        """Escape sequences work inside Chinese quotes."""
        source = "\u201c你好\\n世界\\t！\u201d"
        tokens = self._scan(source)
        assert tokens[0].literal == "你好\n世界\t！"

    def test_chinese_quote_unterminated(self):
        """Unterminated Chinese quote should produce an error."""
        source = "\u201c未闭合"
        scanner = Scanner(source=source, file="<test>")
        scanner.scan_all()
        assert scanner.has_errors

    def test_chinese_quote_in_program(self):
        """Chinese quotes in a full program with variables."""
        source = '定义 问候 ＝ \u201c你好，世界！\u201d'
        tokens = self._scan(source)
        str_token = next(t for t in tokens if t.type == TokenType.STRING)
        assert str_token.literal == "你好，世界！"

    def test_chinese_quote_with_agent_prompt(self):
        """Chinese corner brackets for agent prompts (common AI use case)."""
        source = """\
智能体 翻译器 ｛
    描述 \u300c翻译文本\u300d
    提示词 \u300c你是专业翻译，请将输入翻译成中文\u300d
    主函 ｛
        返回 \u300c完成\u300d
    ｝
｝
"""
        scanner = Scanner(source=source, file="<test>")
        scanner.scan_all()
        assert not scanner.has_errors, f"Unexpected errors: {scanner.errors}"

    # ── helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _scan(source: str):
        scanner = Scanner(source=source, file="<test>")
        tokens = scanner.scan_all()
        return [t for t in tokens if t.type != TokenType.EOF]


class TestChinesePunctuationParser:
    """Verify the parser accepts fullwidth punctuation in full programs."""

    def test_parse_fullwidth_parens_in_call(self):
        source = "定义 result ＝ add（1， 2）"
        program = self._parse(source)
        assert len(program.statements) == 1

    def test_parse_fullwidth_braces_in_fn(self):
        source = """\
函数 加（a： int， b： int）： int ｛
    返回 a ＋ b
｝
"""
        program = self._parse(source)
        assert len(program.statements) == 1
        from helen.core.ast import FunctionDeclNode
        assert isinstance(program.statements[0], FunctionDeclNode)

    def test_parse_fullwidth_if_else(self):
        source = """\
如果 x ＞ 0 ｛
    返回 1
｝ 否则 ｛
    返回 0
｝
"""
        program = self._parse(source)
        assert len(program.statements) == 1
        from helen.core.ast import IfStmtNode
        assert isinstance(program.statements[0], IfStmtNode)

    def test_parse_fullwidth_comparison(self):
        source = "定义 ok ＝ x ＞＝ 0 ＆＆ x ＜＝ 100"
        program = self._parse(source)
        assert len(program.statements) == 1

    def test_parse_fullwidth_list(self):
        source = "定义 nums ＝ ［1， 2， 3］"
        program = self._parse(source)
        assert len(program.statements) == 1

    def test_parse_fullwidth_match(self):
        source = """\
匹配 score ｛
    情况 90．．100 ｛ print（\"A\"） ｝
    默认 ｛ print（\"F\"） ｝
｝
"""
        program = self._parse(source)
        assert len(program.statements) == 1
        from helen.core.ast import MatchStmtNode
        assert isinstance(program.statements[0], MatchStmtNode)

    def test_parse_fullwidth_pipe(self):
        source = "定义 result ＝ 5 ｜＞ double"
        program = self._parse(source)
        assert len(program.statements) == 1

    def test_parse_fullwidth_bang_not(self):
        source = "定义 flag ＝ ！真"
        program = self._parse(source)
        assert len(program.statements) == 1

    def test_parse_mixed_punctuation(self):
        """Mixed ASCII and fullwidth punctuation should parse correctly."""
        source = """\
定义 x ＝ 10
const y = 20
如果 x ＞ 0 {
    返回 x ＋ y
}
"""
        program = self._parse(source)
        assert len(program.statements) == 3

    # ── helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _parse(source: str):
        from helen.core.errors import ErrorReporter
        from helen.core.parser import Parser
        errors = ErrorReporter()
        scanner = Scanner(source=source, file="<test>")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
        if errors.has_errors:
            err_msgs = "; ".join(str(e) for e in errors.errors)
            pytest.fail(f"Parse errors: {err_msgs}")
        return program
