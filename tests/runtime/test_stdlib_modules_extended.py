"""Tests for v1.38 extended stdlib modules (std.core, std.data, std.path, etc.)."""

import io
import sys
import pytest

from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.core.errors import ErrorReporter
from helen.semantic.analyzer import SemanticAnalyzer
from helen.interpreter.interpreter import Interpreter


def _run(code: str) -> list:
    """Run Helen code and return captured prints."""
    errors = ErrorReporter()
    scanner = Scanner(source=code, file="test.helen")
    tokens = scanner.scan_all()
    parser = Parser(tokens, errors=errors)
    program = parser.parse()
    analyzer = SemanticAnalyzer(errors)
    analyzer.analyze(program)
    assert not errors.errors, f"Semantic errors: {errors.errors}"

    interp = Interpreter(errors=errors)

    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        interp.interpret(program)
    finally:
        sys.stdout = old
    return [line for line in buf.getvalue().splitlines() if line]


class TestStdCoreModule:
    def test_wildcard_import(self):
        out = _run('''
import std.core.*
main {
    let x = len([1, 2, 3])
    let s = str(42)
    print(x)
    print(s)
}
''')
        assert out == ["3", "42"]

    def test_selective_import(self):
        out = _run('''
import std.core.{len, str}
main {
    print(len("hello"))
    print(str(123))
}
''')
        assert out == ["5", "123"]

    def test_namespace_import(self):
        out = _run('''
import std.core as C
main {
    print(C.len([1, 2]))
    print(C.str(99))
}
''')
        assert out == ["2", "99"]


class TestStdDataModule:
    def test_toml_parse(self):
        out = _run('''
import std.data.{toml_parse}
main {
    let d = toml_parse("key = 42")
    print(d["key"])
}
''')
        assert out == ["42"]


class TestStdPathModule:
    def test_path_ops(self):
        out = _run('''
import std.path.*
main {
    print(path_basename("/a/b/c.txt"))
    print(path_dirname("/a/b/c.txt"))
    print(path_join("a", "b", "c"))
}
''')
        assert out == ["c.txt", "/a/b", "a/b/c"]


class TestStdTestModule:
    def test_assert_equal(self):
        out = _run('''
import std.test.*
main {
    assert_equal(2 + 2, 4)
    assert_true(1 < 2)
    print("ok")
}
''')
        assert out == ["ok"]


class TestStdNewModulesRecognized:
    """Verify all 14 new modules are recognized by semantic analyzer."""

    @pytest.mark.parametrize("module", [
        "std.core", "std.data", "std.network", "std.path",
        "std.tools", "std.debug", "std.context", "std.transcript",
        "std.media", "std.test", "std.quality", "std.llm",
        "std.crypto", "std.concurrency",
    ])
    def test_module_import_succeeds(self, module):
        code = f'''
import {module}.*
main {{
    print("ok")
}}
'''
        out = _run(code)
        assert out == ["ok"]
