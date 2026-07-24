# Tutorial 14: AI-Native Observability

> Give AI a "black box" it can read, not a GDB for humans.

---

## Why AI-Native Observability?

Traditional debuggers (breakpoints, stepping, variable watching) are designed for **human-interactive debugging**. In AI programming scenarios, the consumer of debug information is the AI Agent, which needs **structured, machine-consumable context** — not interactive pause/resume.

| Traditional Debugger | Helen Observability |
|---------------------|---------------------|
| Breakpoint pause | Structured error snapshot (JSON) |
| Step execution | Execution trace log |
| Variable watch | Call stack + scope variables |
| Call stack panel | Programmatic call stack trace |
| No LLM logging | LLM call audit log |

## assert Statement

### Basic Syntax

```helen
assert x > 0
assert x > 0, "x must be positive"
```

### Assertion Failure

```helen
fn divide(a, b) {
    assert b != 0, "divisor must not be zero"
    return a / b
}

main {
    try {
        divide(10, 0)
    } catch AssertionError e {
        print("Caught: " + e.message)
    }
}
```

### Integration with Observability

When an assertion fails, structured error context (JSON format) is automatically captured, including the call stack + scope variables.

## debug() Function

```helen
main {
    let x = 42
    debug("variable value", x)
    // Output: [DEBUG] variable value {"value": 42}
}
```

| Feature | `print()` | `debug()` |
|---------|-----------|-----------|
| Output target | stdout | stderr |
| Format | Plain text | JSON structured |
| Purpose | Normal program output | Development debugging |

## Execution Tracing

### REPL Commands

```
:trace on          # Enable execution tracing
:trace off         # Disable execution tracing
:trace show [n]    # Show the last n trace entries
```

### Programmatic Tracing

```helen
main {
    trace_on()
    let x = compute_value()
    let y = transform(x)
    trace_off()
    
    let trace = get_trace(10)
    print(trace)
}
```

## Structured Error Context

```
:last_error        # Show full context of the last error (human-readable format)
:last_error -v     # Verbose mode, includes execution trace
```

In the REPL, `:last_error` displays a human-readable text format containing:
- Error type and message
- Time of occurrence
- Call stack (function names, locations)
- Scope variables

Using the `-v` flag additionally shows the execution trace.

AI Agents can programmatically obtain the JSON format: `snapshot.to_json()`

> **Note**: Call stack tracing and execution tracing are enabled by default in the REPL; no manual `:trace on` is needed.

## LLM Call Audit Log

```
:llm_log [n]       # Show the last n LLM calls (compact mode)
:llm_log [n] -v    # Verbose mode, shows full audit information
```

Each entry records: timestamp, call_type, agent_name, model, prompt, response, tokens_in/out, duration_ms, tool_calls, error.

Compact mode shows a one-line summary (including model name and tool call count); verbose mode shows all fields.

## Context Management Observability (v1.15+)

Helen v1.15 introduced comprehensive context management enhancements with rich observability.

### Context Usage Statistics

```
:stats                 # Show context usage statistics
```

Displayed information:
- Token usage ratio and total count
- Current model
- Message count
- Working memory status (active files, recent decisions, pending TODOs, error history)

### Working Memory Inspection

```
:working_memory        # Show current working memory content
:working_memory files  # Show active files only
:working_memory decisions  # Show recent decisions only
:working_memory todos  # Show pending TODOs only
:working_memory errors # Show error history only
```

### Compression Status

```
:compression           # Show current compression status
```

Displayed information:
- Current compression state
- Usage ratio
- Cache hit status

### Programmatic Access

```helen
main {
    // Get context statistics
    let stats = context_stats()
    print("Token usage: " + stats["usage_ratio"])
    print("Active files: " + stats["active_files"])
    
    // Get working memory
    let wm = working_memory_snapshot()
    print("Recent decisions: " + wm["recent_decisions"])
    
    // Manually trigger compression
    compress_context("graduated")
    
    // Clear context
    clear_context()
}
```

### Context Management Debugging

```helen
// Helper function: fix code
fn fix_code(code: str): str {
    // Actual code fix logic
    return code  // Simplified example
}

agent DebugHelper {
    context {
        compression "graduated"
        working-memory true
    }
    
    tools ["read_file", "write_file"]
    
    functions {
        fn fix_code(code: str): str {
            // Actual code fix logic
            return code  // Simplified example
        }
    }
    
    main {
        // Working memory automatically tracks file operations
        let code = read_file("src/main.py")
        let fixed = fix_code(code)
        write_file("src/main.py", fixed)
        
        // Inspect working memory
        let wm = working_memory_snapshot()
        debug("Working memory after file operations", wm)
        
        return llm act "Review the changes"
    }
}
```

---

## Design Philosophy

- Tracing is off by default (on by default in the REPL)
- LLM audit logging is on by default
- Memory usage has an upper bound and does not grow with conversation length

## Exercises

1. Use `assert` to validate input parameters
2. Use `:trace on` in the REPL to trace execution paths
3. Use `debug()` to output intermediate results
4. Use `:last_error` to inspect error context
5. Use `:llm_log` to inspect the LLM call audit log
