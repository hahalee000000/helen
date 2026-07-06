"""Tests for cross-function calls within aliased imported modules.

Bug: `import "mod.helen" as math` followed by `math.quadruple(5)` where
quadruple internally calls double() failed with "'double' is not callable".

Root cause: _create_module_object() created module_env with only
consts/shared let, but no function references. Cross-function calls
within the same aliased module couldn't resolve.

Fix: register module functions as callable wrappers in module_env.

Covers:
1. Basic cross-function call (A calls B)
2. Multi-level call chain (A calls B calls C)
3. Recursive function
4. Cross-function call with const access
5. Cross-function call with stdlib function
6. Non-aliased import still works (regression)
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
        if errors.has_errors:
            raise RuntimeError(f"Lexer errors: {[e.message for e in errors.errors]}")

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


class TestAliasedImportCrossFunctionCall:
    """Tests for cross-function calls within aliased imported modules."""

    def test_basic_cross_function_call(self):
        """fn A calls fn B within the same aliased module."""
        module = """
        fn double(x: int): int { return x * 2 }
        fn quadruple(x: int): int { return double(double(x)) }
        """
        main = """
        import "mod.helen" as math
        main {
            math.quadruple(5)
        }
        """
        result, _ = _run_file(main, {"mod.helen": module})
        assert result == 20

    def test_multi_level_call_chain(self):
        """A calls B calls C within the same aliased module."""
        module = """
        fn add_one(x: int): int { return x + 1 }
        fn double(x: int): int { return x * 2 }
        fn transform(x: int): int { return double(add_one(x)) }
        """
        main = """
        import "mod.helen" as m
        main {
            m.transform(5)
        }
        """
        result, _ = _run_file(main, {"mod.helen": module})
        assert result == 12  # (5+1)*2

    def test_recursive_function(self):
        """Recursive function within an aliased module."""
        module = """
        fn factorial(n: int): int {
            if n <= 1 { return 1 }
            return n * factorial(n - 1)
        }
        """
        main = """
        import "mod.helen" as m
        main {
            m.factorial(5)
        }
        """
        result, _ = _run_file(main, {"mod.helen": module})
        assert result == 120

    def test_cross_function_with_const_access(self):
        """Cross-function call also accesses module const."""
        module = """
        const MULTIPLIER = 3
        fn scale(x: int): int { return x * MULTIPLIER }
        fn scale_double(x: int): int { return scale(double(x)) }
        fn double(x: int): int { return x * 2 }
        """
        main = """
        import "mod.helen" as m
        main {
            m.scale_double(5)
        }
        """
        result, _ = _run_file(main, {"mod.helen": module})
        assert result == 30  # (5*2)*3

    def test_cross_function_calls_stdlib(self):
        """Module function calls stdlib function while also calling sibling."""
        module = """
        fn greet(name: str): str { return "hello " + name }
        fn greet_upper(name: str): str {
            return upper(greet(name))
        }
        """
        main = """
        import "mod.helen" as m
        main {
            m.greet_upper("world")
        }
        """
        result, _ = _run_file(main, {"mod.helen": module})
        assert result == "HELLO WORLD"

    def test_non_aliased_import_still_works(self):
        """Non-aliased import with cross-function calls (regression)."""
        module = """
        fn double(x: int): int { return x * 2 }
        fn quadruple(x: int): int { return double(double(x)) }
        """
        main = """
        import "mod.helen"
        main {
            quadruple(5)
        }
        """
        result, _ = _run_file(main, {"mod.helen": module})
        assert result == 20

    def test_multiple_calls_via_alias(self):
        """Multiple different functions called via alias."""
        module = """
        fn add(a: int, b: int): int { return a + b }
        fn mul(a: int, b: int): int { return a * b }
        fn combined(a: int, b: int): int { return mul(add(a, b), add(a, b)) }
        """
        main = """
        import "mod.helen" as m
        main {
            m.combined(3, 4)
        }
        """
        result, _ = _run_file(main, {"mod.helen": module})
        assert result == 49  # (3+4)*(3+4)
