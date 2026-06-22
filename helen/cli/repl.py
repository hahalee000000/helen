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
        # Capture structured error context for :last_error
        # Only capture if not already captured by the interpreter (e.g., in function/agent calls)
        if interp.observability.last_error is None:
            span = getattr(e, 'span', None)
            interp.observability.capture_error(
                type(e).__name__, str(e), span, scope={}
            )
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
        msgs = [format_error(err) for err in errors.errors]
        print(f"Parse error:\n{chr(10).join(msgs)}", file=sys.stderr)
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
        msgs = [format_error(err) for err in errors.errors]
        print(f"Parse error:\n{chr(10).join(msgs)}", file=sys.stderr)
        return False

    try:
        interp.interpret(program)
        # With llm stream, output is already printed to stdout.
        # If there were errors during execution, report them.
        if errors.has_errors:
            msgs = [format_error(err) for err in errors.errors]
            print(f"\nError:\n{chr(10).join(msgs)}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"Runtime error: {e}", file=sys.stderr)
        return False


def _run_programming_agent(interp: Interpreter, analyzer: SemanticAnalyzer) -> None:
    """Run an interactive Helen programming agent session.
    
    Loads helen/agents/programming_agent.helen which has its own
    interactive loop (interactive_loop function).
    """
    from pathlib import Path
    import helen.cli.repl as repl_module
    import os
    
    # Use helen/agents/helen_programmer.helen (the main programming agent)
    module_dir = Path(repl_module.__file__).parent.parent
    agent_path = module_dir.parent / "agents" / "helen_programmer.helen"
    
    if not agent_path.exists():
        print(f"Error: Programming agent not found at {agent_path}", file=sys.stderr)
        return
    
    # Load agent source
    agent_source = agent_path.read_text(encoding="utf-8")
    
    # Set working directory to agents/ so imports work correctly
    old_cwd = os.getcwd()
    os.chdir(agent_path.parent)
    
    try:
        errors = ErrorReporter()
        llm_runtime = HttpLLMRuntime()
        agent_interp = Interpreter(errors=errors, llm_runtime=llm_runtime)
        
        scanner = Scanner(source=agent_source, file=str(agent_path))
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
        
        if errors.has_errors:
            msgs = [format_error(err) for err in errors.errors]
            print(f"Parse error: {msgs[0]}", file=sys.stderr)
            return
        
        # Execute agent (it will enter its own interactive loop)
        agent_interp.interpret(program)
    except KeyboardInterrupt:
        print("\n(Interrupted)")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
    finally:
        os.chdir(old_cwd)


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
        print("  :ask <question>   Ask the Helen language assistant (single question)")
        print("  :agent            Start interactive Helen programming agent")
        print("  :trace on|off     Enable/disable execution tracing")
        print("  :trace show [n]   Show last n trace entries (default 50)")
        print("  :last_error [-v]  Show structured context of last error (-v for trace)")
        print("  :llm_log [n] [-v] Show last n LLM calls (-v for verbose)")
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

    if cmd == ":agent":
        print("\n🤖 Starting Helen Programming Agent...")
        print("   Type 'exit' or ':quit' to return to REPL\n")
        _run_programming_agent(interp, analyzer)
        return True

    if cmd == ":trace":
        if arg == "on":
            interp.observability.tracer.enabled = True
            interp.observability.call_stack.enabled = True
            print("Execution tracing enabled.")
        elif arg == "off":
            interp.observability.tracer.enabled = False
            print("Execution tracing disabled.")
        elif arg == "show":
            n = 50
            if len(parts) > 2:
                try:
                    n = int(parts[2])
                except ValueError:
                    pass
            print(interp.observability.tracer.format_trace(last_n=n))
        else:
            print("Usage: :trace on|off|show [n]")
        return True

    if cmd == ":last_error":
        verbose = "-v" in arg or "--verbose" in arg
        last_err = interp.observability.last_error
        if last_err is None:
            print("No error captured yet.")
        else:
            print(last_err.format_text(verbose=verbose))
            if not verbose:
                print("\nTip: use :last_error -v to show execution trace")
        return True

    if cmd == ":llm_log":
        # Parse arguments: [n] [-v|--verbose]
        n = 10
        verbose = False
        if arg:
            parts = arg.split()
            for part in parts:
                if part in ("-v", "--verbose"):
                    verbose = True
                else:
                    try:
                        n = int(part)
                    except ValueError:
                        pass

        entries = interp.observability.llm_audit.entries[-n:]
        if not entries:
            print("No LLM calls recorded yet.")
        else:
            print(f"Last {len(entries)} LLM calls:")
            for i, entry in enumerate(entries, 1):
                status = "❌" if entry.error else "✅"
                if verbose:
                    # Verbose mode: show all fields
                    from datetime import datetime
                    ts = datetime.fromtimestamp(entry.timestamp).strftime("%Y-%m-%d %H:%M:%S")
                    print(f"\n  [{i}] {status} {ts}")
                    print(f"      Type: {entry.call_type}")
                    print(f"      Agent: {entry.agent_name or 'anonymous'}")
                    print(f"      Model: {entry.model or 'default'}")
                    print(f"      Prompt: {entry.prompt[:100]}{'...' if len(entry.prompt) > 100 else ''}")
                    if entry.response:
                        print(f"      Response: {entry.response[:100]}{'...' if len(entry.response) > 100 else ''}")
                    print(f"      Tokens: {entry.tokens_in} in / {entry.tokens_out} out")
                    print(f"      Duration: {entry.duration_ms:.0f}ms")
                    if entry.tool_calls:
                        print(f"      Tool calls: {len(entry.tool_calls)}")
                        for tc in entry.tool_calls[:3]:  # Show first 3
                            print(f"        - {tc.get('name', 'unknown')}")
                    if entry.error:
                        print(f"      Error: {entry.error}")
                else:
                    # Compact mode: one line per entry
                    model_str = f" @{entry.model}" if entry.model else ""
                    print(f"  {status} [{entry.call_type}] {entry.agent_name or 'anonymous'}{model_str} "
                          f"({entry.tokens_in}+{entry.tokens_out} tokens, {entry.duration_ms:.0f}ms)")
                    if entry.tool_calls:
                        print(f"      🔧 {len(entry.tool_calls)} tool call(s)")
                    if entry.error:
                        print(f"      ❗ {entry.error}")
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
    print("In multi-line mode (...), press Enter twice on empty line to execute, or Ctrl+C to cancel")
    print()

    # Persistent interpreter state across REPL iterations
    errors = ErrorReporter()
    llm_runtime = _create_llm_runtime()
    # Use current working directory as base_dir for imports
    import os
    cwd = os.getcwd()
    from helen.runtime.import_resolver import ImportResolver
    import_resolver = ImportResolver(base_dir=cwd, error_reporter=errors)
    interp = Interpreter(errors=errors, llm_runtime=llm_runtime, import_resolver=import_resolver)
    # Enable call stack and execution tracing by default in REPL for better error diagnostics
    interp.observability.call_stack.enabled = True
    interp.observability.tracer.enabled = True
    analyzer = SemanticAnalyzer(errors, base_dir=cwd)

    buffer_lines: list[str] = []
    empty_line_count = 0  # Track consecutive empty lines

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
                empty_line_count = 0
                continue
            except KeyboardInterrupt:
                # Ctrl+C in multi-line mode: cancel current input
                if buffer_lines:
                    print("\n(multi-line input cancelled)")
                    buffer_lines.clear()
                    empty_line_count = 0
                    continue
                # Ctrl+C at top level: exit REPL
                print("\nInterrupted")
                break

            if line.strip() == "exit":
                break

            # Handle REPL commands (:help, :reset, :list, :undefine)
            if not buffer_lines and _handle_repl_command(line, interp, analyzer):
                continue

            # Track empty lines
            if not line.strip():
                empty_line_count += 1
            else:
                empty_line_count = 0

            # In multi-line mode, two consecutive empty lines means "execute what we have"
            # This allows single empty lines in code (for spacing) without triggering execution
            if buffer_lines and empty_line_count >= 2:
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
                empty_line_count = 0
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
            empty_line_count = 0

    except KeyboardInterrupt:
        print("\nInterrupted")
        buffer_lines.clear()

    return 0
