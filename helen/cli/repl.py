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
from helen.runtime.http_llm import HttpLLMRuntime
from helen.semantic.analyzer import SemanticAnalyzer
from helen.cli.formatter import format_error


def _create_llm_runtime():
    """Create the best available LLM runtime.
    
    Uses HTTP-based runtime (fast, direct API calls) instead of CLI-based (slow).
    """
    return HttpLLMRuntime()


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


def _execute_input(source: str, interp: Interpreter, analyzer: SemanticAnalyzer) -> tuple[bool, Any]:
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

    # Analyze (semantic checks: types, scope, etc.)
    try:
        analyzer.analyze(program)
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


def _run_helen_assistant(question: str) -> bool:
    """Run the Helen assistant program to answer a question.
    
    Args:
        question: User's question about Helen.
    
    Returns:
        True if execution succeeded, False on error.
        Output is streamed directly to stdout.
    """
    from pathlib import Path
    from helen.core.lexer import Scanner
    from helen.core.parser import Parser
    from helen.core.errors import ErrorReporter
    from helen.interpreter.interpreter import Interpreter
    from helen.runtime.http_llm import HttpLLMRuntime
    
    # Load the Helen assistant program (use absolute path based on module location)
    import helen.cli.repl as repl_module
    module_dir = Path(repl_module.__file__).parent.parent  # helen/cli -> helen/
    assistant_path = module_dir / "agent" / "helen_assistant.helen"
    docs_path = module_dir.parent / "docs" / "tutorial.md"  # helen/ -> repo root -> docs/
    source_dir = module_dir  # helen/ directory containing source code
    
    if not assistant_path.exists():
        print(f"Error: Helen assistant program not found at {assistant_path}", file=sys.stderr)
        return False
    
    if not docs_path.exists():
        print(f"Error: Helen documentation not found at {docs_path}", file=sys.stderr)
        return False
    
    if not source_dir.exists():
        print(f"Error: Helen source directory not found at {source_dir}", file=sys.stderr)
        return False
    
    source = assistant_path.read_text(encoding="utf-8")
    
    # Parse and execute
    errors = ErrorReporter()
    scanner = Scanner(source=source, file=str(assistant_path))
    tokens = scanner.scan_all()
    parser = Parser(tokens, errors=errors)
    program = parser.parse()
    
    if errors.has_errors:
        print(f"Parse error: {errors.format_report()}", file=sys.stderr)
        return False
    
    # Create interpreter with modified main block that uses the question
    llm_runtime = HttpLLMRuntime()
    interp = Interpreter(errors=errors, llm_runtime=llm_runtime)
    
    # Modify the program to pass the question, docs path, and source dir to HelenAssistant
    # We'll create a wrapper that injects the parameters
    modified_source = source.replace(
        'let question = "How do I define an agent in Helen?"',
        f'let question = "{question}"'
    ).replace(
        'let docs_path = "docs/tutorial.md"  // Relative path for development',
        f'let docs_path = "{docs_path}"  // Absolute path from REPL'
    ).replace(
        'let source_dir = "helen/"  // Relative path for development',
        f'let source_dir = "{source_dir}/"  // Absolute path from REPL'
    )
    
    # Re-parse with modified source
    scanner = Scanner(source=modified_source, file=str(assistant_path))
    tokens = scanner.scan_all()
    parser = Parser(tokens, errors=errors)
    program = parser.parse()
    
    if errors.has_errors:
        print(f"Parse error: {errors.format_report()}", file=sys.stderr)
        return False
    
    try:
        result = interp.interpret(program)
        # With llm stream, output is already printed to stdout.
        # If there were errors during execution, report them.
        if errors.has_errors:
            print(f"\nError: {errors.format_report()}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"Runtime error: {e}", file=sys.stderr)
        return False


def _handle_repl_command(line: str, interp: Interpreter, analyzer: SemanticAnalyzer) -> bool:
    """Handle REPL colon-commands. Returns True if the line was a command."""
    stripped = line.strip()
    if not stripped.startswith(":"):
        return False

    parts = stripped.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd == ":help":
        print("REPL commands:")
        print("  :help             Show this help message")
        print("  :reset            Clear all definitions (functions, agents)")
        print("  :list             List all defined functions and agents")
        print("  :undefine <name>  Remove a function or agent definition")
        print("  :ask <question>   Ask the Helen language assistant")
        print("  exit              Exit the REPL")
        return True

    if cmd == ":reset":
        analyzer.reset()
        interp.reset_definitions()
        print("All definitions cleared.")
        return True

    if cmd == ":list":
        defs = interp.list_definitions()
        if defs["functions"]:
            print(f"Functions: {', '.join(defs['functions'])}")
        else:
            print("Functions: (none)")
        if defs["agents"]:
            print(f"Agents:    {', '.join(defs['agents'])}")
        else:
            print("Agents:    (none)")
        return True

    if cmd == ":undefine":
        if not arg:
            print("Usage: :undefine <name>")
            return True
        removed_fn = interp.undefine_function(arg)
        removed_agent = interp.undefine_agent(arg)
        removed_sym = analyzer.undefine(arg)
        if removed_fn or removed_agent or removed_sym:
            print(f"Removed '{arg}'.")
        else:
            print(f"'{arg}' not found.")
        return True

    if cmd == ":ask":
        if not arg:
            print("Usage: :ask <question>")
            return True
        
        print("\n🤔 Thinking...\n")
        _run_helen_assistant(arg)
        # Output is streamed directly to stdout by llm stream
        print()  # Final newline after streaming completes
        return True

    print(f"Unknown command: {cmd}. Type :help for available commands.")
    return True


def repl_command() -> int:
    """Run the REPL interactive loop.

    Returns:
        0 on normal exit.
    """
    # Enable readline for cursor movement and history
    try:
        import readline
        readline.parse_and_bind("tab: complete")
    except ImportError:
        pass  # readline not available on all platforms

    print("Helen REPL v1.2")
    print("Type 'exit' or Ctrl+D to quit, ':help' for commands")
    print("In multi-line mode (...), press Enter on empty line or Ctrl+C to cancel")
    print()

    # Persistent interpreter state across REPL iterations
    errors = ErrorReporter()
    llm_runtime = _create_llm_runtime()
    interp = Interpreter(errors=errors, llm_runtime=llm_runtime)
    analyzer = SemanticAnalyzer(errors, base_dir=".")

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
            except UnicodeDecodeError as e:
                # Handle terminal encoding issues (e.g., with CJK characters)
                print(f"Input encoding error: {e}. Please try again.", file=sys.stderr)
                buffer_lines.clear()
                continue
            except KeyboardInterrupt:
                # Ctrl+C in multi-line mode: cancel current input
                if buffer_lines:
                    print("\n(multi-line input cancelled)")
                    buffer_lines.clear()
                    continue
                # Ctrl+C at top level: exit REPL
                print("\nInterrupted")
                break

            if line.strip() == "exit":
                break

            # Handle REPL commands (:help, :reset, :list, :undefine)
            if not buffer_lines and _handle_repl_command(line, interp, analyzer):
                continue

            # In multi-line mode, empty line means "execute what we have"
            if buffer_lines and not line.strip():
                buffer = "\n".join(buffer_lines)
                # Force execution even if braces are unbalanced
                if buffer.strip():
                    try:
                        success, result = _execute_input(buffer, interp, analyzer)
                        if success:
                            if result is not None:
                                print(repr(result))
                        else:
                            print(f"Error: {result}", file=sys.stderr)
                    except Exception as e:
                        print(f"Internal Error: {e}", file=sys.stderr)
                buffer_lines = []
                continue

            buffer_lines.append(line)

            # Check if we need more input
            buffer = "\n".join(buffer_lines)
            if _needs_continuation(buffer):
                continue

            # Try to execute
            if buffer.strip():
                try:
                    success, result = _execute_input(buffer, interp, analyzer)
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
