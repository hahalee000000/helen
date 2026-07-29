"""Tests for E0355 TOP_LEVEL_STATEMENT — bare top-level code is forbidden.

v1.30: Only declarations (fn, agent, const, import, alias, shared, protocol,
impl) and at most one main {} block are allowed at the module level.
All executable code must be inside main {} or a function.
"""

import tempfile
import os

from helen.core.errors import ErrorCode


def _check(source: str) -> list[ErrorCode]:
    """Parse and analyze Helen source, return list of error codes."""
    from helen.core.lexer import Scanner
    from helen.core.parser import Parser
    from helen.core.errors import ErrorReporter
    from helen.semantic.analyzer import SemanticAnalyzer

    # Use a real filename so the top-level check applies (not skipped for <test>)
    scanner = Scanner(source=source, file="test.helen")
    tokens = scanner.scan_all()
    errors = ErrorReporter()
    parser = Parser(tokens, errors=errors)
    program = parser.parse()
    if errors.has_errors:
        return [e.code for e in errors.errors]
    analyzer = SemanticAnalyzer(errors)
    analyzer.analyze(program)
    return [e.code for e in errors.errors]


class TestTopLevelAllowed:
    """These constructs ARE allowed at the top level."""

    def test_fn_at_top_level(self):
        codes = _check("fn hello() { print(\"hi\") }")
        assert ErrorCode.TOP_LEVEL_STATEMENT not in codes

    def test_agent_at_top_level(self):
        codes = _check('agent A { main { return 42 } }')
        assert ErrorCode.TOP_LEVEL_STATEMENT not in codes

    def test_const_at_top_level(self):
        codes = _check("const X = 42")
        assert ErrorCode.TOP_LEVEL_STATEMENT not in codes

    def test_import_at_top_level(self):
        codes = _check('import "./nonexistent.helen"')
        # May have IMPORT_NOT_FOUND but not TOP_LEVEL_STATEMENT
        assert ErrorCode.TOP_LEVEL_STATEMENT not in codes

    def test_alias_at_top_level(self):
        codes = _check("alias len as my_len")
        assert ErrorCode.TOP_LEVEL_STATEMENT not in codes

    def test_shared_let_at_top_level(self):
        codes = _check('shared let counter = 0')
        assert ErrorCode.TOP_LEVEL_STATEMENT not in codes

    def test_shared_const_at_top_level(self):
        codes = _check('shared const LIMIT = 100')
        assert ErrorCode.TOP_LEVEL_STATEMENT not in codes

    def test_main_block_at_top_level(self):
        codes = _check('main { print("hello") }')
        assert ErrorCode.TOP_LEVEL_STATEMENT not in codes

    def test_complete_program(self):
        source = '''
const LIMIT = 100
fn helper(): int { return 42 }
main {
    let x = helper()
    print(x)
}
'''
        codes = _check(source)
        assert ErrorCode.TOP_LEVEL_STATEMENT not in codes


class TestTopLevelForbidden:
    """These constructs are NOT allowed at the top level."""

    def test_bare_let(self):
        codes = _check("let x = 42")
        assert ErrorCode.TOP_LEVEL_STATEMENT in codes

    def test_bare_let_with_expression(self):
        codes = _check("let x = 1 + 2")
        assert ErrorCode.TOP_LEVEL_STATEMENT in codes

    def test_bare_if(self):
        codes = _check('if true { print("hi") }')
        assert ErrorCode.TOP_LEVEL_STATEMENT in codes

    def test_bare_for(self):
        codes = _check('for i in [1, 2, 3] { print(i) }')
        assert ErrorCode.TOP_LEVEL_STATEMENT in codes

    def test_bare_while(self):
        codes = _check('let x = 0\nwhile x < 10 { x = x + 1 }')
        assert ErrorCode.TOP_LEVEL_STATEMENT in codes

    def test_bare_function_call(self):
        codes = _check('print("hello")')
        assert ErrorCode.TOP_LEVEL_STATEMENT in codes

    def test_bare_try(self):
        codes = _check('try { print("x") } catch RuntimeError e { print(e.message) }')
        assert ErrorCode.TOP_LEVEL_STATEMENT in codes

    def test_bare_match(self):
        codes = _check('let x = 1\nmatch x { case 1 { print("one") } default { print("other") } }')
        assert ErrorCode.TOP_LEVEL_STATEMENT in codes

    def test_bare_assert(self):
        codes = _check('assert true')
        assert ErrorCode.TOP_LEVEL_STATEMENT in codes

    def test_bare_throw(self):
        codes = _check('throw RuntimeError("error")')
        assert ErrorCode.TOP_LEVEL_STATEMENT in codes


class TestDuplicateMain:
    """Only one main {} block is allowed per file."""

    def test_duplicate_main_block(self):
        source = 'main { print("a") }\nmain { print("b") }'
        codes = _check(source)
        assert ErrorCode.DUPLICATE_DECLARATION in codes


class TestChineseKeywords:
    """Chinese keywords are also subject to the restriction."""

    def test_chinese_let_forbidden(self):
        codes = _check("设 x ＝ 42")
        assert ErrorCode.TOP_LEVEL_STATEMENT in codes

    def test_chinese_if_forbidden(self):
        codes = _check("如果 真 { 打印(\"hi\") }")
        assert ErrorCode.TOP_LEVEL_STATEMENT in codes

    def test_chinese_const_allowed(self):
        codes = _check("常量 X ＝ 42")
        assert ErrorCode.TOP_LEVEL_STATEMENT not in codes

    def test_chinese_fn_allowed(self):
        codes = _check("函数 你好（） ｛ 打印（\"hi\"） ｝")
        assert ErrorCode.TOP_LEVEL_STATEMENT not in codes


class TestErrorMessage:
    """Error messages are helpful."""

    def test_let_error_message_mentions_const(self):
        from helen.core.lexer import Scanner
        from helen.core.parser import Parser
        from helen.core.errors import ErrorReporter
        from helen.semantic.analyzer import SemanticAnalyzer

        scanner = Scanner(source="let x = 42", file="test.helen")
        tokens = scanner.scan_all()
        errors = ErrorReporter()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
        analyzer = SemanticAnalyzer(errors)
        analyzer.analyze(program)

        e0355_errors = [e for e in errors.errors if e.code == ErrorCode.TOP_LEVEL_STATEMENT]
        assert len(e0355_errors) == 1
        assert "const" in e0355_errors[0].message
        assert "main" in e0355_errors[0].message
