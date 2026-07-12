"""Tests for Python FFI nested imports.

Regression tests: when a .helen file imports a Python module, and that
.helen file is then imported by another .helen file, the Python module
must be actually imported (not just validated). Previously, the import
was only path-validated by ImportResolver, so at runtime the Python
module name resolved to None, raising "'NoneType' has no property ...".

Covers:
1. Non-aliased import: helper.helen imports 'json', main imports helper.helen
2. Aliased import: helper.helen imports 'json', main imports helper.helen as H
3. Nested Python module: helper.helen imports 'math', uses math.pi/math.floor
4. Multiple Python modules in helper
5. Direct access still works (baseline)
6. ImportResolver collects Python imports
"""

import os
import tempfile

import pytest

from helen.core.errors import ErrorReporter
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.semantic.analyzer import SemanticAnalyzer
from helen.interpreter.interpreter import Interpreter
from helen.runtime.llm_runtime import MockLLMRuntime
from helen.runtime.import_resolver import ImportResolver


def _run_file(main_source: str, module_files: dict[str, str],
              main_filename: str = "main.helen") -> tuple:
    """Run a Helen program with helper modules."""
    tmpdir = tempfile.mkdtemp()
    try:
        for fname, source in module_files.items():
            with open(os.path.join(tmpdir, fname), "w") as f:
                f.write(source)

        main_path = os.path.join(tmpdir, main_filename)
        with open(main_path, "w") as f:
            f.write(main_source)

        errors = ErrorReporter()
        import_resolver = ImportResolver(base_dir=tmpdir)

        scanner = Scanner(source=main_source, file=main_path)
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
        if errors.has_errors:
            raise RuntimeError(f"Parse errors: {[e.message for e in errors.errors]}")

        analyzer = SemanticAnalyzer(errors, base_dir=tmpdir)
        analyzer.analyze(program)
        if errors.has_errors:
            raise RuntimeError(f"Semantic errors: {[e.message for e in errors.errors]}")

        interp = Interpreter(
            errors=errors,
            llm_runtime=MockLLMRuntime(),
            import_resolver=import_resolver,
        )
        result = interp.interpret(program)
        return result, interp
    finally:
        import shutil
        shutil.rmtree(tmpdir)


class TestImportResolverPythonImports:
    """Tests for import_resolver collecting Python module imports."""

    def test_python_import_collected(self):
        """Python imports in a .helen file are collected for cross-module execution."""
        tmpdir = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmpdir, "helper.helen"), "w") as f:
                f.write('import "json"\nfn to_json(): str { return json.dumps({}) }\n')

            resolver = ImportResolver(base_dir=tmpdir)
            resolver.resolve("helper.helen")
            assert ("json", None) in resolver.python_imports
        finally:
            import shutil
            shutil.rmtree(tmpdir)

    def test_python_import_deduplicated(self):
        """Multiple imports of the same Python module are deduplicated."""
        tmpdir = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmpdir, "a.helen"), "w") as f:
                f.write('import "json"\nfn f() {}\n')
            with open(os.path.join(tmpdir, "b.helen"), "w") as f:
                f.write('import "json"\nimport "a.helen"\nfn g() {}\n')

            resolver = ImportResolver(base_dir=tmpdir)
            resolver.resolve("b.helen")
            assert resolver.python_imports.count(("json", None)) == 1
        finally:
            import shutil
            shutil.rmtree(tmpdir)


# ─── Cross-module Python import tests ─────────────────────────────────────────


HELPER_JSON = """
import "json"
fn to_json(d: map): str {
    return json.dumps(d)
}
"""

HELPER_MATH = """
import "math"
fn circle_area(r: int): int {
    return math.floor(math.pi * r * r)
}
"""


class TestPythonFFINestedImports:
    """Python FFI nested import tests (the main bug)."""

    def test_non_aliased_helper_with_python(self):
        """helper.helen imports 'json', main imports helper.helen.

        Before fix: RuntimeError 'NoneType' has no property 'dumps'.
        After fix: json is imported and available to helper.helen's functions.
        """
        main = """
        import "helper.helen"
        main {
            to_json({"x": 1, "y": 2})
        }
        """
        result, _ = _run_file(main, {"helper.helen": HELPER_JSON})
        # Result is a JSON string; verify it contains expected content
        assert '"x": 1' in result or '"x":1' in result

    def test_aliased_helper_with_python(self):
        """Aliased import: main imports helper.helen as H."""
        main = """
        import "helper.helen" as H
        main {
            H.to_json({"a": 1})
        }
        """
        result, _ = _run_file(main, {"helper.helen": HELPER_JSON})
        assert '"a": 1' in result or '"a":1' in result

    def test_nested_python_math(self):
        """helper.helen imports 'math' and uses math.pi/math.floor."""
        main = """
        import "helper.helen"
        main {
            circle_area(5)
        }
        """
        result, _ = _run_file(main, {"helper.helen": HELPER_MATH})
        # pi * 5 * 5 = 78.53... -> floor = 78
        assert result == 78

    def test_aliased_nested_python_math(self):
        """Aliased import with nested math module."""
        main = """
        import "helper.helen" as HM
        main {
            HM.circle_area(10)
        }
        """
        result, _ = _run_file(main, {"helper.helen": HELPER_MATH})
        # pi * 10 * 10 = 314.15... -> floor = 314
        assert result == 314

    def test_multiple_python_modules_in_helper(self):
        """Helper imports multiple Python modules."""
        helper = """
        import "json"
        import "math"
        fn describe(x: int): str {
            let s = "sqrt=" + str(math.sqrt(x))
            return json.dumps({"info": s})
        }
        """
        main = """
        import "helper.helen"
        main {
            describe(16)
        }
        """
        result, _ = _run_file(main, {"helper.helen": helper})
        assert "sqrt" in result

    def test_direct_python_import_still_works(self):
        """Baseline: direct Python import in main still works."""
        main = """
        import "math"
        main {
            math.sqrt(25)
        }
        """
        result, _ = _run_file(main, {})
        assert result == 5.0


class TestPythonFFITransitiveImports:
    """Deeper nesting: A imports B imports Python C."""

    def test_three_level_nesting(self):
        """main -> middle.helen -> helper.helen (imports 'json')."""
        helper = """
        import "json"
        fn j(): str { return json.dumps({"level": "helper"}) }
        """
        middle = """
        import "helper.helen"
        fn m(): str { return j() }
        """
        main = """
        import "middle.helen"
        main {
            m()
        }
        """
        result, _ = _run_file(main, {
            "helper.helen": helper,
            "middle.helen": middle,
        })
        assert "helper" in result


class TestPythonFFIAliasedNestedImports:
    """Aliased Python imports in transitively-imported .helen files.

    Regression: before the fix, `import "ui.renderer" as PyUIRenderer`
    in a .helen module that was imported by another .helen file would
    lose the alias — PyUIRenderer was defined as `renderer` instead.
    """

    def test_aliased_python_import_in_helper(self):
        """helper.helen: `import "json" as J`, main imports helper.helen.

        Before fix: 'J' is NoneType (actually defined as 'json').
        After fix: 'J' is the json module.
        """
        helper = """
        import "json" as J
        fn to_json(d: map): str {
            return J.dumps(d)
        }
        """
        main = """
        import "helper.helen"
        main {
            to_json({"k": "v"})
        }
        """
        result, _ = _run_file(main, {"helper.helen": helper})
        assert '"k": "v"' in result or '"k":"v"' in result or '"k":' in result

    def test_aliased_python_import_in_aliased_helper(self):
        """Same as above but main uses aliased import for helper too."""
        helper = """
        import "json" as J
        fn to_json(d: map): str {
            return J.dumps(d)
        }
        """
        main = """
        import "helper.helen" as H
        main {
            H.to_json({"a": 1})
        }
        """
        result, _ = _run_file(main, {"helper.helen": helper})
        assert '"a": 1' in result or '"a":1' in result or '"a":' in result

    def test_dotted_python_module_with_alias(self):
        """Test dotted Python module path with alias (like ui.renderer)."""
        # Use os.path as a readily-available dotted module
        helper = """
        import "os.path" as P
        fn join_parts(): str {
            return P.join("a", "b")
        }
        """
        main = """
        import "helper.helen"
        main {
            join_parts()
        }
        """
        result, _ = _run_file(main, {"helper.helen": helper})
        assert result == "a/b" or "a" in str(result)

    def test_multiple_aliased_python_imports(self):
        """Multiple aliased Python imports in one helper module."""
        helper = """
        import "json" as J
        import "math" as M
        fn describe(): str {
            let pi_str = str(M.floor(M.pi))
            return J.dumps({"pi_floor": pi_str})
        }
        """
        main = """
        import "helper.helen"
        main {
            describe()
        }
        """
        result, _ = _run_file(main, {"helper.helen": helper})
        assert "3" in str(result)
