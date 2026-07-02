"""Tests for shared let variable scope across imports.

Fixes: shared let variables from imported modules were not accessible
from the imported module's own functions (causing "Undefined variable"
at runtime), because import_resolver._register_helen() only registered
const (immutable) VarDeclNodes and skipped shared let (mutable=True).

Covers:
1. shared let accessible from functions in same module (baseline)
2. shared let accessible from functions after non-aliased import
3. shared let accessible from functions after aliased import
4. shared let mutable via imported functions
5. const accessible via module alias
6. shared let direct access via module alias
7. Multiple shared let variables
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


FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "runtime", "fixtures")


def _run_file(main_source: str, module_files: dict[str, str],
              main_filename: str = "main.helen") -> tuple:
    """Run a Helen program with helper modules.

    Args:
        main_source: The main file's source code.
        module_files: Dict of filename -> source for helper modules.
        main_filename: Name of the main file (for error messages).

    Returns:
        (result, interpreter) tuple.
    """
    # Write module files to a temp directory
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


# ─── Import resolver tests ─────────────────────────────────────────────────────


class TestImportResolverSharedLet:
    """Tests for import_resolver handling of shared let."""

    def test_shared_let_registered_in_data(self):
        """shared let VarDeclNode is registered in resolver.data."""
        tmpdir = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmpdir, "mod.helen"), "w") as f:
                f.write("shared let counter = 0\nfn inc() { counter = counter + 1 }\n")

            resolver = ImportResolver(base_dir=tmpdir)
            resolver.resolve("mod.helen")
            assert "counter" in resolver.data
            assert resolver.data["counter"].shared is True
        finally:
            import shutil
            shutil.rmtree(tmpdir)

    def test_const_registered_in_data(self):
        """const VarDeclNode is registered in resolver.data."""
        tmpdir = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmpdir, "mod.helen"), "w") as f:
                f.write("const MAX = 100\nfn get_max(): int { return MAX }\n")

            resolver = ImportResolver(base_dir=tmpdir)
            resolver.resolve("mod.helen")
            assert "MAX" in resolver.data
            assert resolver.data["MAX"].mutable is False
        finally:
            import shutil
            shutil.rmtree(tmpdir)

    def test_regular_let_not_registered(self):
        """Regular let (mutable, not shared) is NOT registered in data."""
        tmpdir = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmpdir, "mod.helen"), "w") as f:
                f.write("let local = 0\nfn get(): int { return local }\n")

            resolver = ImportResolver(base_dir=tmpdir)
            resolver.resolve("mod.helen")
            assert "local" not in resolver.data
        finally:
            import shutil
            shutil.rmtree(tmpdir)


# ─── Same-module function access (baseline) ────────────────────────────────────


class TestSharedLetSameModule:
    """Baseline: shared let accessible from functions in the same module."""

    def test_function_reads_shared_let(self):
        source = """
        shared let counter = 0
        fn get(): int { return counter }
        main { get() }
        """
        result, _ = _run_file(source, {})
        assert result == 0

    def test_function_writes_shared_let(self):
        source = """
        shared let counter = 0
        fn inc() { counter = counter + 1 }
        main {
            inc()
            counter
        }
        """
        result, _ = _run_file(source, {})
        assert result == 1

    def test_function_reads_then_writes(self):
        source = """
        shared let msg = "initial"
        fn set_msg(m: str) { msg = m }
        fn get_msg(): str { return msg }
        main {
            set_msg("changed")
            get_msg()
        }
        """
        result, _ = _run_file(source, {})
        assert result == "changed"


# ─── Non-aliased import ────────────────────────────────────────────────────────


class TestSharedLetNonAliasedImport:
    """shared let accessible after non-aliased import."""

    def test_function_reads_shared_let_via_import(self):
        module = """
        shared let counter = 0
        fn inc() { counter = counter + 1 }
        fn get(): int { return counter }
        """
        main = """
        import "mod.helen"
        main {
            inc()
            inc()
            get()
        }
        """
        result, _ = _run_file(main, {"mod.helen": module})
        assert result == 2

    def test_function_writes_shared_let_via_import(self):
        module = """
        shared let buffer = ""
        fn append(s: str) { buffer = buffer + s }
        fn get(): str { return buffer }
        """
        main = """
        import "mod.helen"
        main {
            append("hello")
            append(" ")
            append("world")
            get()
        }
        """
        result, _ = _run_file(main, {"mod.helen": module})
        assert result == "hello world"

    def test_shared_let_direct_access_via_import(self):
        """Module-level main can access imported shared let directly."""
        module = """
        shared let value = 42
        """
        main = """
        import "mod.helen"
        main { value }
        """
        result, _ = _run_file(main, {"mod.helen": module})
        assert result == 42


# ─── Aliased import ────────────────────────────────────────────────────────────


class TestSharedLetAliasedImport:
    """shared let accessible after aliased import (output.helen pattern)."""

    def test_function_reads_shared_let_via_aliased_import(self):
        module = """
        shared let _use_colors = true
        fn get_use_colors(): bool { return _use_colors }
        fn set_use_colors(enabled: bool) { _use_colors = enabled }
        """
        main = """
        import "mod.helen" as output
        main {
            output.set_use_colors(false)
            output.get_use_colors()
        }
        """
        result, _ = _run_file(main, {"mod.helen": module})
        assert result is False

    def test_shared_let_direct_access_via_alias(self):
        """Access shared let directly via module alias (output._use_colors)."""
        module = """
        shared let _use_colors = true
        fn set_use_colors(enabled: bool) { _use_colors = enabled }
        """
        main = """
        import "mod.helen" as output
        main {
            output._use_colors
        }
        """
        result, _ = _run_file(main, {"mod.helen": module})
        assert result is True

    def test_const_access_via_alias(self):
        """const values accessible via module alias (output.MAX)."""
        module = """
        const MAX = 100
        fn get_max(): int { return MAX }
        """
        main = """
        import "mod.helen" as mod
        main {
            mod.MAX
        }
        """
        result, _ = _run_file(main, {"mod.helen": module})
        assert result == 100

    def test_output_helen_pattern(self):
        """Full pattern from helenagent output.helen."""
        module = """
        const OUTPUT_NORMAL = 1
        const OUTPUT_QUIET = 2

        shared let _output_level = OUTPUT_NORMAL
        shared let _use_colors = true

        fn _colorize(text: str): str {
            if _use_colors {
                return "[C]" + text
            }
            return text
        }

        fn set_use_colors(enabled: bool) {
            _use_colors = enabled
        }

        fn init_output() {
            _use_colors = false
        }
        """
        main = """
        import "output.helen" as output
        main {
            output.init_output()
            let result = output._colorize("test")
            result
        }
        """
        result, _ = _run_file(main, {"output.helen": module})
        assert result == "test"  # no color prefix since colors disabled


# ─── Multiple shared let ───────────────────────────────────────────────────────


class TestMultipleSharedLet:
    """Tests with multiple shared let variables."""

    def test_multiple_shared_let_via_import(self):
        module = """
        shared let a = 1
        shared let b = 2
        fn sum(): int { return a + b }
        fn set_a(v: int) { a = v }
        """
        main = """
        import "mod.helen"
        main {
            set_a(10)
            sum()
        }
        """
        result, _ = _run_file(main, {"mod.helen": module})
        assert result == 12

    def test_shared_let_and_const_mixed(self):
        module = """
        const BASE = 100
        shared let offset = 0
        fn set_offset(v: int) { offset = v }
        fn total(): int { return BASE + offset }
        """
        main = """
        import "mod.helen" as mod
        main {
            mod.set_offset(42)
            mod.total()
        }
        """
        result, _ = _run_file(main, {"mod.helen": module})
        assert result == 142


# ─── shared let initialization with const reference (Issue #10) ────────────────


class TestSharedLetInitWithConst:
    """Issue #10: shared let can reference const during initialization.

    When a shared let variable is initialized with an expression that references
    a const from the same module, the const must be resolvable during import.
    """

    def test_shared_let_init_with_const_non_aliased(self):
        """shared let can reference const in non-aliased import."""
        module = """
        const MY_CONST = 42
        shared let my_var = MY_CONST
        fn get_var(): int { return my_var }
        """
        main = """
        import "mod.helen"
        main {
            get_var()
        }
        """
        result, _ = _run_file(main, {"mod.helen": module})
        assert result == 42

    def test_shared_let_init_with_const_aliased(self):
        """shared let can reference const in aliased import."""
        module = """
        const OUTPUT_NORMAL = 1
        const OUTPUT_VERBOSE = 2
        shared let _output_level = OUTPUT_NORMAL
        fn get_level(): int { return _output_level }
        """
        main = """
        import "output.helen" as output
        main {
            output.get_level()
        }
        """
        result, _ = _run_file(main, {"output.helen": module})
        assert result == 1

    def test_shared_let_init_with_const_expression(self):
        """shared let can use expression with multiple consts."""
        module = """
        const BASE = 10
        const OFFSET = 5
        shared let total = BASE + OFFSET
        fn get_total(): int { return total }
        """
        main = """
        import "mod.helen"
        main {
            get_total()
        }
        """
        result, _ = _run_file(main, {"mod.helen": module})
        assert result == 15

    def test_shared_let_init_chain(self):
        """shared let can reference another shared let initialized with const."""
        module = """
        const BASE = 100
        shared let level1 = BASE
        shared let level2 = level1 + 10
        fn get_level2(): int { return level2 }
        """
        main = """
        import "mod.helen"
        main {
            get_level2()
        }
        """
        result, _ = _run_file(main, {"mod.helen": module})
        assert result == 110
