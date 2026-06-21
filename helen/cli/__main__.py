"""CLI entry point for the Helen language (HLD 5.2 Phase 6).

Commands:
    helen run <file>      — Full compile + execute
    helen check <file>    — Frontend validation only (lex + parse + analyze)
    helen repl            — Interactive read-eval-print loop
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

from helen.cli.repl import repl_command
from helen.cli.formatter import format_error, format_warning
from helen.cli.docgen import generate_cli as docgen_cli
from helen.runtime.http_llm import HttpLLMRuntime


def run_command(file: str) -> int:
    """Run a Helen program (HLD 5.2 Phase 6).

    Pipeline: Lexer → Parser → Analyzer → Interpreter

    Returns:
        0 on success, 1 on syntax error, 2 on semantic error, 3 on runtime error.
    """
    source_path = Path(file)
    if not source_path.exists():
        print(f"Error: file not found: {file}", file=sys.stderr)
        return 1

    source_text = source_path.read_text(encoding="utf-8")

    from helen.core.errors import ErrorCode, ErrorReporter  # noqa: PLC0415
    from helen.core.lexer import Scanner  # noqa: PLC0415
    from helen.core.parser import Parser  # noqa: PLC0415
    from helen.semantic.analyzer import SemanticAnalyzer  # noqa: PLC0415
    from helen.interpreter.interpreter import Interpreter  # noqa: PLC0415

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
    llm_runtime = HttpLLMRuntime()
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
    """Check a Helen program without executing (HLD 5.2 Phase 6).

    Pipeline: Lexer → Parser → Analyzer

    Returns:
        0 if no errors, 1 on syntax error, 2 on semantic error.
    """
    source_path = Path(file)
    if not source_path.exists():
        print(f"Error: file not found: {file}", file=sys.stderr)
        return 1

    source_text = source_path.read_text(encoding="utf-8")

    from helen.core.errors import ErrorCode, ErrorReporter  # noqa: PLC0415
    from helen.core.lexer import Scanner  # noqa: PLC0415
    from helen.core.parser import Parser  # noqa: PLC0415
    from helen.semantic.analyzer import SemanticAnalyzer  # noqa: PLC0415

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
    subcommands = {"check", "repl", "doc", "init", "test", "quality"}
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
        elif first == "init":
            return init_command()
        elif first == "test":
            return test_command(argv[1:])
        elif first == "quality":
            return quality_command(argv[1:])
    elif first in ("-h", "--help", "help"):
        _print_help()
        return 0
    else:
        # Default: treat first argument as a file to run
        return run_command(first)

    _print_help()
    return 1


def init_command() -> int:
    """Initialize Helen configuration directory.

    Creates ~/.helen/ with:
    - config.yaml (LLM API configuration)
    - skills/ directory

    Returns:
        0 on success, 1 on error.
    """
    from helen.runtime.config import get_helen_home, save_config

    # Create Helen home directory
    helen_home = get_helen_home()
    print(f"Helen home: {helen_home}")

    # Create skills directory
    skills_dir = helen_home / "skills"
    skills_dir.mkdir(exist_ok=True)
    print(f"Skills directory: {skills_dir}")

    # Check if config already exists
    config_path = helen_home / "config.yaml"
    if config_path.exists():
        print(f"Config already exists: {config_path}")
        print("Edit it directly to update settings.")
        return 0

    # Create default config
    default_config = {
        "base_url": "https://api.openai.com/v1",
        "api_key": "YOUR_API_KEY_HERE",
        "model": "gpt-4",
        "temperature": 0.7,
        "timeout": 60,
    }

    config_path = save_config(default_config)
    print(f"Config created: {config_path}")
    print()
    print("Next steps:")
    print(f"  1. Edit {config_path}")
    print("  2. Set your API key")
    print("  3. Run a Helen program: helen <file.helen>")

    return 0


def test_command(argv: list[str]) -> int:
    """Run Helen test file(s) and report results.

    Usage:
        helen test <file> [file2 ...] [options]

    Options:
        --json              Output results as JSON
        --watch             Watch mode (re-run on file changes)
        --verbose           Show detailed output
        --only <name>       Run only the test with this exact name
        --suite <name>      Run only tests in this suite
        --filter <pattern>  Run only tests matching this pattern (regex)
        --coverage          Show code coverage (requires pytest-cov)

    Returns:
        0 if all tests pass, 1 if any fail, 2 on error.
    """
    import time

    # Parse arguments
    files: list[str] = []
    json_output = False
    watch_mode = False
    verbose = False
    only_test: str | None = None
    only_suite: str | None = None
    filter_pattern: str | None = None
    coverage = False

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--json":
            json_output = True
        elif arg == "--watch":
            watch_mode = True
        elif arg == "--verbose" or arg == "-v":
            verbose = True
        elif arg == "--only":
            if i + 1 >= len(argv):
                print("Error: --only requires a test name argument", file=sys.stderr)
                return 2
            i += 1
            only_test = argv[i]
        elif arg == "--suite":
            if i + 1 >= len(argv):
                print("Error: --suite requires a suite name argument", file=sys.stderr)
                return 2
            i += 1
            only_suite = argv[i]
        elif arg == "--filter":
            if i + 1 >= len(argv):
                print("Error: --filter requires a pattern argument", file=sys.stderr)
                return 2
            i += 1
            filter_pattern = argv[i]
        elif arg == "--coverage":
            coverage = True
        elif not arg.startswith("-"):
            files.append(arg)
        else:
            print(f"Unknown option: {arg}", file=sys.stderr)
            return 2
        i += 1

    if not files:
        print("Error: 'test' requires at least one file argument", file=sys.stderr)
        print("Usage: helen test <file> [file2 ...] [options]", file=sys.stderr)
        return 1

    # Validate files exist
    for f in files:
        p = Path(f)
        if not p.exists():
            print(f"Error: file not found: {f}", file=sys.stderr)
            return 1

    def run_test_files() -> int:
        """Execute test files and return exit code."""
        from helen.core.errors import ErrorCode, ErrorReporter
        from helen.core.lexer import Scanner
        from helen.core.parser import Parser
        from helen.semantic.analyzer import SemanticAnalyzer
        from helen.interpreter.interpreter import Interpreter
        from helen.runtime.http_llm import HttpLLMRuntime
        from helen.stdlib.test import _registry

        # Reset test registry
        _registry.reset()

        total_start = time.monotonic()

        for file in files:
            source_path = Path(file)
            source_text = source_path.read_text(encoding="utf-8")

            errors = ErrorReporter()

            # Lex
            scanner = Scanner(source=source_text, file=file)
            try:
                tokens = scanner.scan_all()
            except Exception as e:
                errors.error(ErrorCode.SCANNER_ERROR, str(e))
                _report_errors(errors, source_text.splitlines())
                return 2

            # Parse
            parser = Parser(tokens, errors=errors)
            program = parser.parse()

            if errors.has_errors:
                _report_errors(errors, source_text.splitlines())
                return 2

            # Analyze
            analyzer = SemanticAnalyzer(errors)
            analyzer.analyze(program)

            if errors.has_errors:
                _report_errors(errors, source_text.splitlines())
                return 2

            # Interpret (registers tests)
            llm_runtime = HttpLLMRuntime()
            interp = Interpreter(errors=errors, llm_runtime=llm_runtime)
            try:
                interp.interpret(program)
            except Exception as e:
                print(f"RuntimeError: {e}", file=sys.stderr)
                return 2

            if errors.has_errors:
                _report_errors(errors, source_text.splitlines())
                return 2

        # Run tests with filters
        report = _registry.run_all(
            only=only_test,
            suite=only_suite,
            filter_pattern=filter_pattern,
        )
        total_elapsed = (time.monotonic() - total_start) * 1000

        # Show filter info if filtering
        if only_test or only_suite or filter_pattern:
            filters = []
            if only_test:
                filters.append(f"test='{only_test}'")
            if only_suite:
                filters.append(f"suite='{only_suite}'")
            if filter_pattern:
                filters.append(f"pattern='{filter_pattern}'")
            print(f"🔍 Filtered by: {', '.join(filters)}")
            print()

        if json_output:
            import json
            data = {
                "total": report.total,
                "passed": report.passed,
                "failed": report.failed,
                "skipped": report.skipped,
                "duration_ms": round(total_elapsed, 2),
                "suites": [{"name": s.name, "tests": len(s.tests)} for s in report.suites],
                "results": [
                    {
                        "name": r.name,
                        "suite": r.suite,
                        "passed": r.passed,
                        "error": r.error,
                        "duration_ms": r.duration_ms,
                    }
                    for r in report.results
                ],
            }
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            # Print formatted report
            from helen.stdlib.test import _format_report
            print(_format_report(report))

        # Show coverage info
        if coverage:
            print("\n📊 Coverage:")
            print("   To measure coverage of your Helen code, run tests with pytest:")
            print("   python -m pytest tests/ --cov=helen --cov-report=term-missing")
            print()
            print("   For Helen program coverage, add debug() calls to track execution.")

        return 0 if report.failed == 0 else 1

    if watch_mode:
        # Watch mode: re-run on file changes
        import os
        print(f"👀 Watching {len(files)} file(s) for changes... (Ctrl+C to stop)")
        if only_test or only_suite or filter_pattern:
            filters = []
            if only_test:
                filters.append(f"test='{only_test}'")
            if only_suite:
                filters.append(f"suite='{only_suite}'")
            if filter_pattern:
                filters.append(f"pattern='{filter_pattern}'")
            print(f"🔍 Filter: {', '.join(filters)}")
        print()

        last_mtimes: dict[str, float] = {}
        try:
            while True:
                changed = False
                for f in files:
                    try:
                        mtime = os.path.getmtime(f)
                    except OSError:
                        continue
                    if f not in last_mtimes or last_mtimes[f] < mtime:
                        last_mtimes[f] = mtime
                        changed = True

                if changed:
                    print(f"\n🔄 Changes detected, re-running tests...\n")
                    exit_code = run_test_files()
                    print(f"\n(exit code: {exit_code})")

                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nStopped watching.")
            return 0
    else:
        return run_test_files()


def quality_command(argv: list[str]) -> int:
    """Run 7-dimension quality assessment on Helen file(s).

    Usage:
        helen quality <file> [file2 ...] [options]

    Options:
        --json              Output results as JSON
        --dimension <name>  Assess only one dimension
        --threshold <n>     Fail if total score below threshold

    Dimensions: architecture, code_quality, security, test_coverage,
                documentation, maintainability, engineering

    Returns:
        0 if score meets threshold, 1 if below, 2 on error.
    """
    import json as json_module

    # Parse arguments
    files: list[str] = []
    json_output = False
    dimension: str | None = None
    threshold: float = 0.0

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--json":
            json_output = True
        elif arg == "--dimension":
            if i + 1 >= len(argv):
                print("Error: --dimension requires a name argument", file=sys.stderr)
                return 2
            i += 1
            dimension = argv[i]
            valid_dims = [
                "architecture", "code_quality", "security", "test_coverage",
                "documentation", "maintainability", "engineering",
            ]
            if dimension not in valid_dims:
                print(f"Error: invalid dimension '{dimension}'", file=sys.stderr)
                print(f"Valid dimensions: {', '.join(valid_dims)}", file=sys.stderr)
                return 2
        elif arg == "--threshold":
            if i + 1 >= len(argv):
                print("Error: --threshold requires a number argument", file=sys.stderr)
                return 2
            i += 1
            try:
                threshold = float(argv[i])
            except ValueError:
                print(f"Error: invalid threshold '{argv[i]}'", file=sys.stderr)
                return 2
        elif not arg.startswith("-"):
            files.append(arg)
        else:
            print(f"Unknown option: {arg}", file=sys.stderr)
            return 2
        i += 1

    if not files:
        print("Error: 'quality' requires at least one file argument", file=sys.stderr)
        print("Usage: helen quality <file> [file2 ...] [--json] [--dimension <name>]", file=sys.stderr)
        return 1

    # Validate files exist
    for f in files:
        p = Path(f)
        if not p.exists():
            print(f"Error: file not found: {f}", file=sys.stderr)
            return 1

    all_results = []
    min_score = 10.0

    for file in files:
        source_path = Path(file)
        source_text = source_path.read_text(encoding="utf-8")

        from helen.stdlib.quality import (
            HelenCodeAnalyzer, SecurityAnalyzer, QualityScorer,
            QualityScore,
        )

        code_analyzer = HelenCodeAnalyzer(source_text, file)
        metrics = code_analyzer.analyze()

        security_analyzer = SecurityAnalyzer(source_text)
        security_issues = security_analyzer.analyze()

        scorer = QualityScorer()

        score = QualityScore(
            architecture=scorer.score_architecture(metrics),
            code_quality=scorer.score_code_quality(metrics),
            security=scorer.score_security(security_issues),
            test_coverage=scorer.score_test_coverage(file),
            documentation=scorer.score_documentation(metrics),
            maintainability=scorer.score_maintainability(metrics),
            engineering=scorer.score_engineering(metrics),
        )

        score.total = scorer.calculate_total(score)
        score.grade = scorer.assign_grade(score.total)
        min_score = min(min_score, score.total)

        if json_output:
            result = {
                "file": file,
                "metrics": {
                    "total_lines": metrics.total_lines,
                    "code_lines": metrics.code_lines,
                    "comment_lines": metrics.comment_lines,
                    "comment_ratio": round(metrics.comment_ratio, 3),
                    "function_count": metrics.function_count,
                    "agent_count": metrics.agent_count,
                    "avg_function_length": round(metrics.avg_function_length, 1),
                    "max_function_length": metrics.max_function_length,
                    "avg_complexity": round(metrics.avg_complexity, 1),
                    "max_complexity": metrics.max_complexity,
                },
                "security_issues": [
                    {"line": iss.line, "severity": iss.severity, "message": iss.message}
                    for iss in security_issues
                ],
                "scores": {
                    "architecture": round(score.architecture, 2),
                    "code_quality": round(score.code_quality, 2),
                    "security": round(score.security, 2),
                    "test_coverage": round(score.test_coverage, 2),
                    "documentation": round(score.documentation, 2),
                    "maintainability": round(score.maintainability, 2),
                    "engineering": round(score.engineering, 2),
                    "total": score.total,
                    "grade": score.grade,
                },
            }

            if dimension:
                result["scores"] = {
                    dimension: result["scores"][dimension],
                    "total": result["scores"]["total"],
                    "grade": result["scores"]["grade"],
                }

            all_results.append(result)
        else:
            from helen.stdlib.quality import _quality_report
            print(_quality_report(source_text, file))

    if json_output:
        if len(all_results) == 1:
            print(json_module.dumps(all_results[0], ensure_ascii=False, indent=2))
        else:
            print(json_module.dumps(all_results, ensure_ascii=False, indent=2))

    # Check threshold
    if threshold > 0 and min_score < threshold:
        print(f"\n❌ Score {min_score:.2f} is below threshold {threshold:.2f}", file=sys.stderr)
        return 1

    return 0


def _print_help() -> None:
    """Print CLI help."""
    print("""helen — Helen Agent Programming Language

Usage:
  helen                     Interactive REPL (default)
  helen <file>              Run a Helen program
  helen check <file>        Check without executing
  helen test <file> [opts]  Run Helen test file(s)
  helen quality <file>      Run 7-dimension quality assessment
  helen doc [files]         Generate API documentation
  helen init                Initialize Helen configuration

Test Options:
  --json                    Output results as JSON
  --watch                   Watch mode (re-run on file changes)
  --verbose                 Show detailed output
  --only <name>             Run only the test with this exact name
  --suite <name>            Run only tests in this suite
  --filter <pattern>        Run only tests matching this pattern (regex)
  --coverage                Show code coverage hints

Quality Options:
  --json                    Output results as JSON
  --dimension <name>        Assess only one dimension
  --threshold <n>           Fail if total score below threshold

Options:
  -h, --help                 Show this help message""")


if __name__ == "__main__":
    sys.exit(main())
