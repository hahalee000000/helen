"""Tests for stdlib multi-language aliases.

Helen's stdlib functions can be called by their canonical English names
(e.g. `len`) or by localized aliases (e.g. Chinese `长度`). All aliases
are loaded at startup regardless of user locale.
"""

import pytest

from helen.core.errors import ErrorReporter
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.semantic.analyzer import SemanticAnalyzer
from helen.interpreter.interpreter import Interpreter
from helen.runtime.llm_runtime import MockLLMRuntime
from helen.stdlib import stdlib


def _run(source: str, filename: str = "<test>") -> object:
    """Run a Helen program and return the result of main block."""
    errors = ErrorReporter()
    scanner = Scanner(source=source, file=filename)
    tokens = scanner.scan_all()
    parser = Parser(tokens, errors=errors)
    program = parser.parse()
    assert not errors.has_errors, f"Parse errors: {[e.message for e in errors.errors]}"

    analyzer = SemanticAnalyzer(errors)
    analyzer.analyze(program)
    assert not errors.has_errors, f"Semantic errors: {[e.message for e in errors.errors]}"

    interp = Interpreter(errors=errors, llm_runtime=MockLLMRuntime())
    return interp.interpret(program)


# ── Registry tests ────────────────────────────────────────────────────────


class TestStdlibAliasRegistry:
    """Tests for StdlibRegistry alias metadata."""

    def test_canonical_lookup(self):
        assert stdlib.lookup("len") is not None
        assert stdlib.lookup("print") is not None

    def test_chinese_alias_lookup(self):
        assert stdlib.lookup("长度") is not None
        assert stdlib.lookup("打印") is not None
        assert stdlib.lookup("排序") is not None

    def test_alias_same_callable(self):
        """Aliases must point to the exact same BuiltinFunction object."""
        len_fn = stdlib.lookup("len")
        长度_fn = stdlib.lookup("长度")
        assert len_fn is 长度_fn

    def test_canonical_names_set(self):
        assert "len" in stdlib.canonical_names
        assert "print" in stdlib.canonical_names
        # Aliases are NOT canonical
        assert "长度" not in stdlib.canonical_names

    def test_is_alias(self):
        assert not stdlib.is_alias("len")
        assert stdlib.is_alias("长度")

    def test_canonical_name_resolution(self):
        assert stdlib.canonical_name("长度") == "len"
        assert stdlib.canonical_name("len") == "len"
        assert stdlib.canonical_name("unknown") == "unknown"

    def test_alias_count(self):
        """We have 230+ Chinese aliases in zh.py."""
        assert len(stdlib.aliases) >= 200

    def test_alias_registration_idempotent(self):
        """Re-registering the same alias is a no-op (success)."""
        assert stdlib.register_alias("长度", "len") is True
        assert stdlib.register_alias("长度", "len") is True

    def test_alias_registration_conflict(self):
        """Registering an alias to a different canonical fails."""
        assert stdlib.register_alias("冲突测试别名", "len") is True
        assert stdlib.register_alias("冲突测试别名", "print") is False

    def test_alias_registration_unknown_canonical(self):
        """Registering an alias for an unknown canonical fails."""
        assert stdlib.register_alias("别名", "不存在的函数") is False


# ── End-to-end execution tests ────────────────────────────────────────────


class TestStdlibAliasExecution:
    """Tests for using stdlib aliases in Helen programs."""

    def test_length_alias(self):
        source = "主函 { 长度([1, 2, 3]) }"
        assert _run(source) == 3

    def test_print_alias(self):
        source = '主函 { 打印("hello"); 42 }'
        assert _run(source) == 42

    def test_sort_alias(self):
        source = "主函 { 排序([3, 1, 2]) }"
        assert _run(source) == [1, 2, 3]

    def test_json_parse_alias(self):
        source = r'主函 { json解析("{\"a\": 1}") }'
        result = _run(source)
        assert result == {"a": 1}

    def test_mixed_english_and_chinese(self):
        """Mixing English and Chinese stdlib names in the same program."""
        source = """
主函 {
    让 数据 = [3, 1, 4, 1, 5]
    让 排序后 = 排序(数据)
    len(排序后)
}
"""
        assert _run(source) == 5

    def test_all_chinese_program(self):
        """Full Chinese program with Chinese stdlib names and 主函."""
        source = """
函数 测试() {
    让 列表 = [5, 2, 8, 1, 9]
    返回 长度(排序(列表))
}

主函 {
    测试()
}
"""
        assert _run(source) == 5


# ── Alias statement tests ─────────────────────────────────────────────────


class TestAliasStatement:
    """Tests for the `alias <canonical> as <alias>` statement."""

    def test_alias_stdlib_function(self):
        source = """
alias len as mylen
主函 { mylen([1, 2, 3, 4]) }
"""
        assert _run(source) == 4

    def test_alias_user_function(self):
        source = """
函数 greet(name: str): str {
    返回 "Hello, " + name
}
alias greet as 打招呼
主函 { 打招呼("Helen") }
"""
        assert _run(source) == "Hello, Helen"

    def test_alias_with_chinese_keyword(self):
        """The Chinese keyword 别名 also works for alias statement."""
        source = """
别名 len as 我的长度
主函 { 我的长度([1, 2, 3, 4, 5]) }
"""
        assert _run(source) == 5

    def test_alias_nonexistent_errors(self):
        """Aliasing a non-existent name produces a semantic error."""
        source = """
alias nonexistent as foo
主函 { 1 }
"""
        errors = ErrorReporter()
        scanner = Scanner(source=source, file="<test>")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
        analyzer = SemanticAnalyzer(errors)
        analyzer.analyze(program)
        assert errors.has_errors
        assert any("not found" in e.message for e in errors.errors)

    def test_alias_preserves_callable(self):
        """Aliased functions should behave identically to the canonical."""
        source = """
函数 add(a: int, b: int): int { 返回 a + b }
alias add as plus
主函 { plus(3, 4) }
"""
        assert _run(source) == 7

    def test_multiple_aliases(self):
        """Multiple aliases for the same canonical are allowed."""
        source = """
函数 double(x: int): int { 返回 x * 2 }
alias double as 双倍
alias double as twice
主函 { 双倍(5) + twice(5) }
"""
        assert _run(source) == 20

    def test_alias_in_nested_scope(self):
        """Aliases defined inside blocks work within that scope."""
        source = """
函数 greet() { 返回 "hi" }
主函 {
    alias greet as 问好
    问好()
}
"""
        assert _run(source) == "hi"

    def test_redundant_alias_no_error(self):
        """Re-aliasing an already-aliased stdlib function is a no-op."""
        source = """
alias len as 长度
主函 { 长度([1, 2]) }
"""
        # 长度 is already a stdlib alias for len; this should not error
        assert _run(source) == 2


# ── Locale config tests ──────────────────────────────────────────────────


class TestLocaleConfig:
    """Tests for locale configuration."""

    def test_get_locale_returns_string(self):
        from helen.runtime.config import get_locale
        locale = get_locale()
        assert isinstance(locale, str)
        assert locale in ("zh", "en", "ja", "ko")

    def test_get_locale_aliases(self):
        from helen.runtime.config import get_locale_aliases
        aliases = get_locale_aliases()
        assert isinstance(aliases, dict)
        # zh locale should have 200+ aliases
        from helen.runtime.config import get_locale
        if get_locale() == "zh":
            assert len(aliases) >= 200
