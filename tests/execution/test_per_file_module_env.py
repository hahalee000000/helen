"""Regression test for v1.39.2: per-file module_env mapping.

Bug: _function_module_envs mapped functions from transitively-imported
files to the DIRECTLY-imported file's module_env (because the resolver's
flat `functions` dict accumulates across imports). A transitive function
that used a stdlib import from its OWN file (not imported by the direct
file) failed because it ran in the wrong module environment.

Scenario: main -> middle -> helper
  helper.helen imports std.str.* and defines shout() which calls upper()
  middle.helen imports helper.helen (NOT std.str) and defines announce()
  main imports middle.helen (NOT std.str) and calls announce()

Before fix: shout() runs in middle's module_env (wrong) -> upper() not found.
After fix:  shout() runs in helper's module_env (correct) -> upper() works.
"""

import os
import tempfile

from helen.core.errors import ErrorReporter
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.semantic.analyzer import SemanticAnalyzer
from helen.interpreter.interpreter import Interpreter
from helen.runtime.llm_runtime import MockLLMRuntime
from helen.runtime.import_resolver import ImportResolver


def _run(main_source: str, module_files: dict[str, str]) -> object:
    tmpdir = tempfile.mkdtemp()
    try:
        for fname, source in module_files.items():
            with open(os.path.join(tmpdir, fname), "w") as f:
                f.write(source)
        main_path = os.path.join(tmpdir, "main.helen")
        with open(main_path, "w") as f:
            f.write(main_source)

        errors = ErrorReporter()
        import_resolver = ImportResolver(base_dir=tmpdir)
        scanner = Scanner(source=main_source, file=main_path)
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
        assert not errors.has_errors, [e.message for e in errors.errors]
        analyzer = SemanticAnalyzer(errors, base_dir=tmpdir)
        analyzer.analyze(program)
        assert not errors.has_errors, [e.message for e in errors.errors]
        interp = Interpreter(
            errors=errors, llm_runtime=MockLLMRuntime(),
            import_resolver=import_resolver,
        )
        return interp.interpret(program)
    finally:
        import shutil
        shutil.rmtree(tmpdir)


class TestPerFileModuleEnv:
    """Each imported function must run in its own file's module_env."""

    def test_transitive_function_uses_own_stdlib(self):
        """helper's shout() needs std.str.upper; middle/main don't import std.str."""
        helper = (
            "import std.str.*\n"
            "fn shout(s: str): str { return upper(s) }\n"
        )
        middle = (
            "import \"helper.helen\"\n"
            "fn announce(s: str): str { return shout(s) }\n"
        )
        main = (
            "import \"middle.helen\"\n"
            "main {\n"
            "    announce(\"hi\")\n"
            "}\n"
        )
        result = _run(main, {"helper.helen": helper, "middle.helen": middle})
        assert result == "HI"

    def test_two_files_different_stdlib(self):
        """Two directly-imported files each use their own stdlib imports."""
        a = (
            "import std.str.*\n"
            "fn up(s: str): str { return upper(s) }\n"
        )
        b = (
            "import std.list.*\n"
            "fn total(xs: list): int { return sum(xs) }\n"
        )
        main = (
            "import \"a.helen\"\n"
            "import \"b.helen\"\n"
            "main {\n"
            "    up(\"hi\")\n"
            "}\n"
        )
        result = _run(main, {"a.helen": a, "b.helen": b})
        assert result == "HI"

    def test_transitive_function_uses_own_stdlib_aliased(self):
        """Aliased import: helper's shout() still uses its own stdlib."""
        helper = (
            "import std.str.*\n"
            "fn shout(s: str): str { return upper(s) }\n"
        )
        main = (
            "import \"helper.helen\" as H\n"
            "main {\n"
            "    H.shout(\"hi\")\n"
            "}\n"
        )
        result = _run(main, {"helper.helen": helper})
        assert result == "HI"
