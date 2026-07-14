"""Regression tests for Helen Python Bridge import resolution & error reporting.

Covers two issues uncovered while driving Helen agents from a Web UI backend:

1. **CWD-based import resolution (Issue #1):** ``HelenAgentWrapper`` used to
   build a bare ``Interpreter()`` whose ``ImportResolver`` defaulted
   ``base_dir`` to the current working directory. Loading ``agent.helen``
   from another directory (e.g. ``webui/backend``) made its top-level
   ``import "sibling.helen"`` resolve against CWD and fail to find the
   sibling sitting next to it.

2. **Misleading deferred error (Issue #2):** when a ``.helen`` import failed
   to resolve, the interpreter silently registered nothing and the failure
   surfaced much later as ``'X' is not callable`` / ``'NoneType' has no
   property ...``. The Python bridge skipped the SemanticAnalyzer, so the
   clear ``import file not found`` error it collected was never surfaced.

Fixes (v1.18.2):
- ``visit_import_stmt`` raises a clear ``Failed to import '...'`` error when
  ``ImportResolver.resolve`` returns ``None`` (matches ``_import_python_module``).
- ``ImportResolver._register_helen`` raises on a failed *nested* Helen/data-file
  import (Python-module imports legitimately resolve to ``None``).
- ``HelenAgentWrapper._load_agent`` now sets ``base_dir`` to the ``.helen``
  file's directory, passes the file path to the ``Scanner``, runs the
  ``SemanticAnalyzer``, and checks ``errors.has_errors``.
"""

import pytest

from helen.core.errors import ErrorReporter
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.interpreter.exceptions import HelenRuntimeError
from helen.interpreter.interpreter import Interpreter
from helen.python_bridge.agent_wrapper import HelenAgentWrapper
from helen.runtime.import_resolver import ImportResolver


# ─── Helpers ────────────────────────────────────────────────────────────────


def _write(tmp_path, name, source):
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return str(path)


def _run_without_semantic_analysis(main_source, tmp_path, main_name="main.helen"):
    """Interpret a program directly, bypassing the SemanticAnalyzer.

    This mirrors what the Python bridge used to do (and what any direct
    interpreter user does), so it exercises the runtime import-error path
    rather than the analyzer's pre-execution ``IMPORT_NOT_FOUND`` check.
    """
    main_path = _write(tmp_path, main_name, main_source)
    errors = ErrorReporter()
    scanner = Scanner(source=main_source, file=main_path)
    tokens = scanner.scan_all()
    program = Parser(tokens, errors=errors).parse()
    assert not errors.has_errors, [e.message for e in errors.errors]

    interp = Interpreter(
        errors=errors,
        import_resolver=ImportResolver(base_dir=str(tmp_path)),
    )
    return interp, program, errors


# ─── Issue #2: clear runtime error on failed .helen import ─────────────────


class TestImportFailureRaisesClearError:
    """A failed .helen import must fail fast with a clear message, not defer."""

    def test_top_level_missing_import_raises_clear_error(self, tmp_path):
        """Top-level ``import "missing.helen"`` raises 'Failed to import'."""
        _run_without_semantic_analysis('import "missing.helen"', tmp_path)
        interp, program, _ = _run_without_semantic_analysis(
            'import "missing.helen"', tmp_path
        )
        with pytest.raises(HelenRuntimeError) as exc:
            interp.interpret(program)
        msg = str(exc.value)
        assert "Failed to import" in msg
        assert "missing.helen" in msg
        # The whole point: no deferred, misleading callable error.
        assert "is not callable" not in msg

    def test_nested_missing_import_raises_clear_error(self, tmp_path):
        """A missing import *inside* an imported file raises, naming the parent."""
        _write(
            tmp_path,
            "middle.helen",
            'import "missing.helen"\nfn m(): str { return "m" }\n',
        )
        interp, program, _ = _run_without_semantic_analysis(
            'import "middle.helen"', tmp_path
        )
        with pytest.raises(HelenRuntimeError) as exc:
            interp.interpret(program)
        msg = str(exc.value)
        assert "Failed to import" in msg
        assert "missing.helen" in msg
        # The error should point at the file that referenced the missing import.
        assert "middle" in msg
        assert "is not callable" not in msg

    def test_python_module_import_still_returns_none_in_resolver(self, tmp_path):
        """Python-module imports (no .helen/.json/... ext) still resolve to None.

        ``_register_helen`` must NOT raise for these: they are handled via
        ``_python_imports`` + the interpreter's FFI path, and ``resolve``
        returning ``None`` for ``import "json"`` is expected, not an error.
        """
        _write(tmp_path, "helper.helen", 'import "json"\nfn f(): str { return "" }\n')
        resolver = ImportResolver(base_dir=str(tmp_path))
        # Must not raise, even though resolve("json") returns None internally.
        result = resolver.resolve("helper.helen")
        assert result is not None
        assert ("json", None) in resolver.python_imports


# ─── Issue #1 + #2: HelenAgentWrapper robustness ───────────────────────────


class TestHelenAgentWrapperImports:
    """The bridge must resolve sibling imports from any CWD and report
    missing imports clearly instead of deferring to 'is not callable'."""

    AGENT_WITH_SIBLING = (
        'import "output.helen"\n'
        "agent Worker(x: int) {\n"
        '    description "uses an imported sibling function"\n'
        "    main {\n"
        "        return double(x)\n"
        "    }\n"
        "}\n"
    )
    AGENT_NO_IMPORTS = (
        "agent Adder(a: int, b: int) {\n"
        '    description "no imports"\n'
        "    main {\n"
        "        return a + b\n"
        "    }\n"
        "}\n"
    )

    def test_loads_agent_with_sibling_import_from_different_cwd(self, tmp_path, monkeypatch):
        """Loading from another CWD still resolves sibling output.helen."""
        _write(tmp_path, "output.helen", "fn double(n: int): int { return n * 2 }\n")
        agent_path = _write(tmp_path, "agent.helen", self.AGENT_WITH_SIBLING)

        # CWD is NOT the agent's directory -- this used to break resolution.
        other_dir = tmp_path / "elsewhere"
        other_dir.mkdir()
        monkeypatch.chdir(other_dir)

        wrapper = HelenAgentWrapper("Worker", agent_path)  # must not raise
        assert wrapper(21) == 42

    def test_baseline_agent_without_imports_still_works(self, tmp_path, monkeypatch):
        """Regression: the hardening must not break the no-import case."""
        agent_path = _write(tmp_path, "agent.helen", self.AGENT_NO_IMPORTS)
        other_dir = tmp_path / "elsewhere"
        other_dir.mkdir()
        monkeypatch.chdir(other_dir)
        wrapper = HelenAgentWrapper("Adder", agent_path)
        assert wrapper(2, 3) == 5

    def test_missing_sibling_raises_clear_error_not_deferred(self, tmp_path, monkeypatch):
        """A missing sibling import fails at load time with 'not found',
        not later as 'is not callable'."""
        agent_path = _write(
            tmp_path,
            "agent.helen",
            'import "missing.helen"\n'
            "agent Worker(x: int) {\n"
            '    description "imports a missing sibling"\n'
            "    main { return 1 }\n"
            "}\n",
        )
        other_dir = tmp_path / "elsewhere"
        other_dir.mkdir()
        monkeypatch.chdir(other_dir)

        with pytest.raises((RuntimeError, HelenRuntimeError)) as exc:
            HelenAgentWrapper("Worker", agent_path)
        msg = str(exc.value)
        assert "not found" in msg.lower()
        # The misleading deferred error must never appear.
        assert "is not callable" not in msg

    def test_missing_agent_raises_clear_error(self, tmp_path, monkeypatch):
        """Requesting an agent that doesn't exist raises clearly."""
        _write(tmp_path, "output.helen", "fn double(n: int): int { return n * 2 }\n")
        agent_path = _write(tmp_path, "agent.helen", self.AGENT_WITH_SIBLING)
        monkeypatch.chdir(tmp_path)

        with pytest.raises((ValueError, RuntimeError, HelenRuntimeError)):
            HelenAgentWrapper("NonexistentAgent", agent_path)
