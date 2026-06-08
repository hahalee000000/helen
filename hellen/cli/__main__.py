"""CLI entry point for the Hellen language (HLD 5.2 Phase 6).

Commands:
    hellen run <file>      — Full compile + execute
    hellen check <file>    — Frontend validation only (lex + parse + analyze)
    hellen repl            — Interactive read-eval-print loop
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

from hellen.cli.repl import repl_command
from hellen.cli.formatter import format_error, format_warning
from hellen.cli.docgen import generate_cli as docgen_cli


def run_command(file: str) -> int:
    """Run a Hellen program (HLD 5.2 Phase 6).

    Pipeline: Lexer → Parser → Analyzer → Interpreter

    Returns:
        0 on success, 1 on syntax error, 2 on semantic error, 3 on runtime error.
    """
    source_path = Path(file)
    if not source_path.exists():
        print(f"Error: file not found: {file}", file=sys.stderr)
        return 1

    source_text = source_path.read_text(encoding="utf-8")

    from hellen.core.errors import ErrorCode, ErrorReporter  # noqa: PLC0415
    from hellen.core.lexer import Scanner  # noqa: PLC0415
    from hellen.core.parser import Parser  # noqa: PLC0415
    from hellen.semantic.analyzer import SemanticAnalyzer  # noqa: PLC0415
    from hellen.interpreter.interpreter import Interpreter  # noqa: PLC0415
    from hellen.runtime.llm_runtime import MockLLMRuntime  # noqa: PLC0415

    errors = ErrorReporter()

    # Lex
    scanner = Scanner(source=source_text, file=file)
    try:
        tokens = scanner.scan_all()
    except Exception as e:
        errors.error(ErrorCode.SCANNER_ERROR, str(e))
        _report_errors(errors, source_text.splitlines())
        return 1

    # Parse
    parser = Parser(tokens, errors=errors)
    program = parser.parse()

    if errors.has_errors:
        _report_errors(errors, source_text.splitlines())
        return 1

    # Analyze
    analyzer = SemanticAnalyzer(errors)
    analyzer.analyze(program)

    if errors.has_errors:
        _report_errors(errors, source_text.splitlines())
        return 2

    # Interpret
    llm_runtime = MockLLMRuntime()
    interp = Interpreter(errors=errors, llm_runtime=llm_runtime)
    try:
        interp.interpret(program)
    except Exception as e:
        print(f"RuntimeError: {e}", file=sys.stderr)
        return 3

    if errors.has_errors:
        _report_errors(errors, source_text.splitlines())
        return 2

    return 0


def check_command(file: str) -> int:
    """Check a Hellen program without executing (HLD 5.2 Phase 6).

    Pipeline: Lexer → Parser → Analyzer

    Returns:
        0 if no errors, 1 on syntax error, 2 on semantic error.
    """
    source_path = Path(file)
    if not source_path.exists():
        print(f"Error: file not found: {file}", file=sys.stderr)
        return 1

    source_text = source_path.read_text(encoding="utf-8")

    from hellen.core.errors import ErrorCode, ErrorReporter  # noqa: PLC0415
    from hellen.core.lexer import Scanner  # noqa: PLC0415
    from hellen.core.parser import Parser  # noqa: PLC0415
    from hellen.semantic.analyzer import SemanticAnalyzer  # noqa: PLC0415

    errors = ErrorReporter()

    # Lex
    scanner = Scanner(source=source_text, file=file)
    try:
        tokens = scanner.scan_all()
    except Exception as e:
        errors.error(ErrorCode.SCANNER_ERROR, str(e))
        _report_errors(errors, source_text.splitlines())
        return 1

    # Parse
    parser = Parser(tokens, errors=errors)
    program = parser.parse()

    if errors.has_errors:
        _report_errors(errors, source_text.splitlines())
        return 1

    # Analyze
    analyzer = SemanticAnalyzer(errors)
    analyzer.analyze(program)

    if errors.has_errors:
        _report_errors(errors, source_text.splitlines())
        return 2

    # No errors
    print(f"✓ {file}: OK")
    return 0


def _report_errors(errors, source_lines: list[str]) -> None:
    """Format and print all collected errors."""
    for err in errors.errors:
        print(format_error(err, source_lines))
    for warn in errors.warnings:
        print(format_warning(warn, source_lines))


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    argv = list(argv) if argv is not None else sys.argv[1:]

    if not argv:
        return repl_command()

    # Check for known subcommands
    subcommands = {"check", "repl", "doc"}
    first = argv[0]

    if first in subcommands:
        # Subcommand mode
        if first == "check":
            if len(argv) < 2:
                print("Error: 'check' requires a file argument", file=sys.stderr)
                return 1
            return check_command(argv[1])
        elif first == "repl":
            return repl_command()
        elif first == "doc":
            return docgen_cli()
    elif first in ("-h", "--help", "help"):
        _print_help()
        return 0
    else:
        # Default: treat first argument as a file to run
        return run_command(first)

    _print_help()
    return 1


def _print_help() -> None:
    """Print CLI help."""
    print("""hellen — Hellen Agent Programming Language

Usage:
  hellen                     Interactive REPL (default)
  hellen <file>              Run a Hellen program
  hellen check <file>        Check without executing
  hellen doc [files]         Generate API documentation

Options:
  -h, --help                 Show this help message""")


if __name__ == "__main__":
    sys.exit(main())
