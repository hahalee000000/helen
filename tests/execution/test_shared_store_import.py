"""Tests for shared store scope across imports.

Regression tests for Issue #35: `shared store` declared in an imported
module was silently dropped by ImportResolver (which only collected
AgentDeclNode, FunctionDeclNode, and VarDeclNode). The container name
resolved to None when the module's own functions were called cross-module,
raising "'NoneType' has no property '<method>'".

Root cause:
  - helen/runtime/import_resolver.py: _extract_definitions had no case for
    SharedStoreDeclNode -> it fell through silently.
  - helen/interpreter/interpreter.py: visit_import_stmt (both aliased and
    non-aliased paths) never executed the declaration, so the container
    was never instantiated.
  - helen/semantic/analyzer.py: visit_import_stmt had no case for
    SharedStoreDeclNode -> direct cross-module access
    failed at semantic analysis with "undeclared variable".

Fix (v1.17): collect and execute shared store declarations during
import, defining the container in BOTH the module env (so the module's own
functions see it) AND the importing environment (so direct cross-module
access works), matching shared let semantics.

Covers:
1. shared store accessible from importing module's function call (the
   exact Issue #35 reproduction)
2. shared store direct cross-module access (MyStore.method() in main)
3. shared store via aliased import
4. shared store state persists across cross-module calls
5. import_resolver registers shared store in data
6. semantic analyzer registers imported shared store (no undeclared error)
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
    """Run a Helen program with helper modules.

    Args:
        main_source: The main file's source code.
        module_files: Dict of filename -> source for helper modules.
        main_filename: Name of the main file (for error messages).

    Returns:
        (result, interpreter) tuple.
    """
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


# ─── Import resolver tests ────────────────────────────────────────────────────


class TestImportResolverSharedStore:
    """Tests for import_resolver handling of shared store."""

    def test_shared_store_registered_in_data(self):
        """shared store SharedStoreDeclNode is registered in resolver.data."""
        tmpdir = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmpdir, "mod.helen"), "w") as f:
                f.write(
                    "shared store S { let v = 0; fn get(): int { return v } }\n"
                    "fn get_s(): int { return S.get() }\n"
                )

            resolver = ImportResolver(base_dir=tmpdir)
            resolver.resolve("mod.helen")
            assert "S" in resolver.data
        finally:
            import shutil
            shutil.rmtree(tmpdir)


# ─── Cross-module access tests ────────────────────────────────────────────────


# The exact Issue #35 reproduction: module declares shared store + a function
# that uses it; main imports the module and calls the function.
STORE_MOD = """
shared store MyStore {
    let val: int = 0
    fn set_val(v: int) { val = v }
    fn get_val(): int { return val }
}

fn do_set(v: int) { MyStore.set_val(v) }
fn do_get(): int { return MyStore.get_val() }
"""


class TestSharedStoreCrossModule:
    """Issue #35: shared store accessible cross-module."""

    def test_module_function_accesses_store(self):
        """The exact Issue #35 repro: importing module's function uses store.

        Before fix: RuntimeError 'NoneType' has no property 'set_val'.
        After fix: store is instantiated and visible cross-module.
        """
        main = """
        import "store_mod.helen"
        main {
            do_set(99)
            do_get()
        }
        """
        result, _ = _run_file(main, {"store_mod.helen": STORE_MOD})
        assert result == 99

    def test_direct_cross_module_access(self):
        """Main module directly accesses MyStore by name (no wrapper fn)."""
        main = """
        import "store_mod.helen"
        main {
            MyStore.set_val(42)
            MyStore.get_val()
        }
        """
        result, _ = _run_file(main, {"store_mod.helen": STORE_MOD})
        assert result == 42

    def test_aliased_import_function_call(self):
        """Aliased import: module function accesses store via SM alias."""
        main = """
        import "store_mod.helen" as SM
        main {
            SM.do_set(77)
            SM.do_get()
        }
        """
        result, _ = _run_file(main, {"store_mod.helen": STORE_MOD})
        assert result == 77

    def test_state_persists_across_calls(self):
        """Store state persists across multiple cross-module function calls."""
        main = """
        import "store_mod.helen"
        main {
            do_set(10)
            do_set(do_get() + 5)
            do_get()
        }
        """
        result, _ = _run_file(main, {"store_mod.helen": STORE_MOD})
        assert result == 15

    def test_multiple_stores_same_module(self):
        """Multiple shared stores in one imported module all work."""
        mod = """
        shared store A { let v = 0; fn set(x: int) { v = x }; fn get(): int { return v } }
        shared store B { let v = 0; fn set(x: int) { v = x }; fn get(): int { return v } }
        fn set_a(x: int) { A.set(x) }
        fn set_b(x: int) { B.set(x) }
        fn get_a(): int { return A.get() }
        fn get_b(): int { return B.get() }
        """
        main = """
        import "mod.helen"
        main {
            set_a(100)
            set_b(200)
            get_a() + get_b()
        }
        """
        result, _ = _run_file(main, {"mod.helen": mod})
        assert result == 300

    def test_two_importers_share_same_store(self):
        """Two modules importing the same store module see the same instance.

        Regression test: before the _shared_store_instances cache fix,
        the second import would re-execute the SharedStoreDeclNode, creating
        a fresh SharedStore with default field values and orphaning the
        instance that main had already mutated.
        """
        ctx_mod = """
        shared store Ctx {
            let initialized: bool = false
            let session_dir: str = ""
            fn init(dir: str) {
                initialized = true
                session_dir = dir
            }
            fn is_init(): bool { return initialized }
            fn get_dir(): str { return session_dir }
        }
        """
        commands = """
        import "ctx.helen"
        fn check_init(): bool { return Ctx.is_init() }
        fn check_dir(): str { return Ctx.get_dir() }
        """
        main = """
        import "ctx.helen"
        import "commands.helen"
        main {
            Ctx.init(".helen/sessions")
            // commands.helen imported ctx.helen again — should see the same
            // Ctx instance that main just initialized, not a fresh default.
            if !check_init() { return false }
            if check_dir() != ".helen/sessions" { return false }
            true
        }
        """
        result, interp = _run_file(main, {
            "ctx.helen": ctx_mod,
            "commands.helen": commands,
        })
        assert result is True
        # Verify only one SharedStore instance was created for "Ctx"
        assert "Ctx" in interp._shared_store_instances

    def test_two_importers_aliased_share_same_store(self):
        """Aliased imports from two modules also share the same store instance."""
        counter_mod = """
        shared store Counter {
            let count: int = 0
            fn inc() { count = count + 1 }
            fn get(): int { return count }
        }
        """
        commands = """
        import "counter.helen" as C
        fn bump() { C.Counter.inc() }
        fn read(): int { return C.Counter.get() }
        """
        main = """
        import "counter.helen" as C
        import "commands.helen" as Cmd
        main {
            C.Counter.inc()
            C.Counter.inc()
            Cmd.bump()
            C.Counter.get()
        }
        """
        result, _ = _run_file(main, {
            "counter.helen": counter_mod,
            "commands.helen": commands,
        })
        assert result == 3


# ─── Semantic analyzer tests ──────────────────────────────────────────────────


class TestSemanticAnalyzerSharedStore:
    """Semantic analyzer must register imported shared store (no undeclared error)."""

    def test_direct_access_no_undeclared_error(self):
        """Direct cross-module access must pass semantic analysis.

        Before fix: 'undeclared variable: MyStore' at semantic analysis.
        """
        main = """
        import "store_mod.helen"
        main {
            MyStore.set_val(1)
            0
        }
        """
        # Should not raise; _run_file raises RuntimeError on semantic errors
        result, _ = _run_file(main, {"store_mod.helen": STORE_MOD})
        assert result == 0
