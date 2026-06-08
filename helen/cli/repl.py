"""REPL interactive loop for the Helen language (HLD 5.2 Phase 6).

Reads lines from stdin, lexes, parses, analyzes, and interprets each input.
Supports multi-line input with bracket/brace matching.
"""

from __future__ import annotations

import sys
from typing import Any

from helen.core.errors import ErrorReporter
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.interpreter.interpreter import Interpreter
from helen.runtime.llm_runtime import MockLLMRuntime
from helen.cli.formatter import format_error


def _needs_continuation(buffer: str) -> bool:
    """Check if the current buffer needs more input (unbalanced braces/parens/quotes)."""
    brace_count = 0
    paren_count = 0
    bracket_count = 0
    in_string = False
    escape_next = False

    for ch in buffer:
        if escape_next:
            escape_next = False
            continue
        if ch == '\\' and in_string:
            escape_next = True
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            brace_count += 1
        elif ch == '}':
            brace_count -= 1
        elif ch == '(':
            paren_count += 1
        elif ch == ')':
            paren_count -= 1
        elif ch == '[':
            bracket_count += 1
        elif ch == ']':
            bracket_count -= 1

    return brace_count > 0 or paren_count > 0 or bracket_count > 0


def _execute_input(source: str, interp: Interpreter) -> tuple[bool, Any]:
    """Lex, parse, analyze, and interpret a single input.

    Returns:
        (success, result_or_error)
    """
    # Clear previous errors for this REPL turn
    interp.errors.reset()
    errors = interp.errors

    # Lex
    try:
        scanner = Scanner(source=source, file="<repl>")
        tokens = scanner.scan_all()
    except Exception as e:
        return False, str(e)

    # Parse
    try:
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
    except Exception as e:
        return False, str(e)

    if errors.has_errors:
        msgs = [format_error(err) for err in errors.errors]
        return False, "\n".join(msgs)

    # Interpret
    try:
        result = interp.interpret(program)
    except Exception as e:
        return False, f"RuntimeError: {e}"

    if errors.has_errors:
        msgs = [format_error(err) for err in errors.errors]
        return False, "\n".join(msgs)

    return True, result


def repl_command() -> int:
    """Run the REPL interactive loop.

    Returns:
        0 on normal exit.
    """
    print("Helen REPL v1.2")
    print("Type 'exit' or Ctrl+D to quit")
    print()

    # Persistent interpreter state across REPL iterations
    errors = ErrorReporter()
    llm_runtime = MockLLMRuntime()
    interp = Interpreter(errors=errors, llm_runtime=llm_runtime)

    buffer_lines: list[str] = []

    try:
        while True:
            if buffer_lines:
                prompt = "... "
            else:
                prompt = ">>> "

            try:
                line = input(prompt)
            except EOFError:
                print()
                break

            if line.strip() == "exit":
                break

            buffer_lines.append(line)

            # Check if we need more input
            buffer = "\n".join(buffer_lines)
            if _needs_continuation(buffer):
                continue

            # Try to execute
            if buffer.strip():
                try:
                    success, result = _execute_input(buffer, interp)
                    if success:
                        if result is not None:
                            print(repr(result))
                    else:
                        print(f"Error: {result}", file=sys.stderr)
                except Exception as e:
                    print(f"Internal Error: {e}", file=sys.stderr)
                    # Don't crash the REPL

            buffer_lines = []

    except KeyboardInterrupt:
        print("\nInterrupted")
        buffer_lines.clear()

    return 0
