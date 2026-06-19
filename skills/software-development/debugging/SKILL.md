---
name: debugging
description: "Debugging methodology and language-specific debugger tools. Covers systematic root-cause investigation, Python (pdb/debugpy), and Node.js (--inspect/CDP)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [debugging, troubleshooting, root-cause, python, pdb, debugpy, nodejs, inspect, CDP]
---

# Debugging — Methodology & Tools

Umbrella skill for all debugging work. Covers the systematic investigation methodology plus language-specific debugger tools.

---

## 1. Systematic Debugging Methodology

**Iron Law: NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST.**

### Phase 1: Root Cause Investigation
1. **Read error messages carefully** — stack traces contain the solution
2. **Reproduce consistently** — `pytest tests/test_module.py::test_name -v`
3. **Check recent changes** — `git log --oneline -10`, `git diff`
4. **Gather evidence in multi-component systems** — instrument at each boundary
5. **Trace data flow** — where does the bad value originate?

### Phase 2: Pattern Analysis
- Find working examples in the same codebase
- Compare against references (read COMPLETELY, don't skim)
- Identify every difference, however small

### Phase 3: Hypothesis and Testing
- Form ONE hypothesis: "I think X is the root cause because Y"
- Make the SMALLEST possible change to test it
- One variable at a time

### Phase 4: Implementation
- Create failing test case FIRST
- Implement single fix addressing root cause
- Verify: `pytest tests/test_regression -v && pytest tests/ -q`
- **Rule of Three**: If 3+ fixes failed, STOP and question the architecture

### Red Flags — STOP and Return to Phase 1
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "I don't fully understand but this might work"
- "One more fix attempt" (when already tried 2+)

---

## 2. Python Debugging (pdb + debugpy)

### Tool Selection

| Tool | When |
|------|------|
| `breakpoint()` + pdb | Local, interactive, simplest |
| `python -m pdb script.py` | Launch under pdb without source edits |
| `debugpy` | Remote/headless/attach to running process |

### pdb Quick Reference

| Command | Action |
|---------|--------|
| `n` | next line (step over) |
| `s` | step into |
| `r` | return from function |
| `c` | continue |
| `l` / `ll` | list source / full function |
| `w` | where (stack trace) |
| `u` / `d` | up / down in stack |
| `p expr` | print expression |
| `b file:line` | set breakpoint |
| `!stmt` | execute arbitrary Python |
| `interact` | full Python REPL in current scope |

### Recipe: Local breakpoint
```python
def compute(x, y):
    breakpoint()  # drops into pdb here
    return result
```
Remember to remove before committing: `rg -n 'breakpoint\(\)' --type py`

### Recipe: pytest debugging
```bash
pytest tests/foo.py::test_bar --pdb -p no:xdist  # xdist breaks pdb!
pytest tests/foo.py::test_bar --showlocals --tb=long  # without pdb
```

### Recipe: Remote debug with debugpy
```bash
# Launch with debugpy
python -m debugpy --listen 127.0.0.1:5678 --wait-for-client script.py

# Or attach to running process
python -m debugpy --listen 127.0.0.1:5678 --pid <PID>
```

### Recipe: remote-pdb (simplest for terminal agents)
```bash
pip install remote-pdb
```
```python
from remote_pdb import set_trace
set_trace(host="127.0.0.1", port=4444)  # blocks until connection
```
Then: `nc 127.0.0.1 4444` → get a (Pdb) prompt

### Common Pitfalls
- pdb under pytest-xdist silently does nothing → use `-p no:xdist`
- `breakpoint()` in CI/non-TTY hangs → never commit it
- `PYTHONBREAKPOINT=0` disables all breakpoints
- `debugpy.listen` doesn't block without `wait_for_client()`
- ptrace may fail on hardened kernels → `echo 0 > /proc/sys/kernel/yama/ptrace_scope`
- **Stale `.pyc` cache**: Code changes don't seem to take effect → `find . -name "*.pyc" -delete && find . -name "__pycache__" -type d -exec rm -rf {} +`. Always clear cache after modifying source if behavior seems unchanged.
- **`asyncio.get_running_loop()` is unreliable for "am I in a loop?" checks**: It raises `RuntimeError` when no loop is running, but in some contexts (mixed sync/async code, REPL environments, nested interpreters) the `except RuntimeError` clause may not catch it as expected — the exception propagates despite the try/except. **Use `asyncio.get_event_loop()` + `.is_running()` instead**, which is safer across all contexts:
  ```python
  # ❌ Unreliable — may not catch properly in all contexts
  try:
      asyncio.get_running_loop()
      in_event_loop = True
  except RuntimeError:
      in_event_loop = False
  
  # ✅ Reliable — works in REPL, scripts, tests, nested contexts
  in_event_loop = False
  try:
      _loop = asyncio.get_event_loop()
      if _loop.is_running():
          in_event_loop = True
  except Exception:
      in_event_loop = False
  ```
  **Symptom**: Code works in standalone scripts but fails in REPL/interactive environments with `RuntimeError: no running event loop` even though you have a try/except around `get_running_loop()`.

---

## 3. Node.js Debugging (--inspect + CDP)

### Tool Selection
- **`node inspect`** — built-in, zero install, CLI REPL. Best for quick poking.
- **CDP via `chrome-remote-interface`** — scriptable, automate many breakpoints.

### Launch with Inspector
```bash
node --inspect script.js           # listen on 127.0.0.1:9229
node --inspect-brk script.js       # listen AND pause on first line
node --inspect=0.0.0.0:9230 script.js  # custom port
```

### Attach to Running Process
```bash
kill -SIGUSR1 <pid>    # enables inspector on existing process
node inspect -p <pid>  # attach debugger CLI
```

### `node inspect` REPL Commands

| Command | Action |
|---------|--------|
| `c` / `cont` | continue |
| `n` / `next` | step over |
| `s` / `step` | step into |
| `o` / `out` | step out |
| `sb('file.js', 42)` | set breakpoint |
| `cb('file.js', 42)` | clear breakpoint |
| `bt` | backtrace |
| `repl` | drop into REPL in current scope |
| `watch('expr')` | evaluate on every pause |

### Programmatic CDP (automation)
```javascript
const CDP = require('chrome-remote-interface');
const client = await CDP({ port: 9229 });
const { Debugger, Runtime } = client;
// Set breakpoints, capture scope, evaluate expressions...
```

### Common Pitfalls
- Wrong line numbers in TS → break in built `dist/*.js` or enable sourcemaps
- `--inspect` vs `--inspect-brk` — the latter pauses on first line
- Port collisions → use `--inspect=0` (random port), check `/json/list`
- Child processes not inherited → use `NODE_OPTIONS='--inspect-brk'`
- Background kills: `Ctrl+C` out of inspect leaves target paused → `cont` first
- Always bind to `127.0.0.1` (security)

### Heap Snapshots & CPU Profiles
```javascript
// CPU profile
await client.Profiler.enable();
await client.Profiler.start();
await new Promise(r => setTimeout(r, 5000));
const { profile } = await client.Profiler.stop();
```

---

## 4. Helen AI-Native Observability

Helen provides **AI-native observability** instead of traditional interactive debuggers. AI agents need structured, machine-consumable context — not breakpoints and single-stepping.

### Core Concepts

| Traditional Debugger | Helen Observability |
|---------------------|---------------------|
| Breakpoints | `assert` statements |
| Single-step execution | Execution tracing (`trace_on/off`) |
| Variable watch | `debug()` structured output |
| Call stack panel | Programmatic call stack tracking |
| No LLM logging | LLM call audit log |

### assert Statement

```helen
# Runtime assertion with optional message
assert x > 0, "x must be positive"

# Catchable — throws AssertionError
try {
    assert false, "test"
} catch AssertionError as e {
    print("Caught: " + e.message)
}
```

### debug() Function

```helen
# Structured debug output to stderr (JSON format)
let x = 42
debug("variable value", x)
# Output: [DEBUG] variable value {"value": 42}
```

### Execution Tracing

```helen
# Programmatic control
trace_on()
let result = compute()
trace_off()
let trace = get_trace(10)
```

**REPL commands**:
```
:trace on          # Enable tracing
:trace off         # Disable tracing
:trace show [n]    # Show last n trace entries
:last_error        # Show structured error context (JSON)
:llm_log [n]       # Show LLM call audit log
```

### Error Snapshot Format (JSON)

```json
{
  "error": {"type": "RuntimeError", "message": "...", "location": "..."},
  "call_stack": [{"function": "...", "args": {...}}],
  "scope": {"var": "value"},
  "trace": [...]
}
```

### LLM Audit Log

All `llm act` / `llm stream` calls are automatically logged:
- timestamp, call_type, agent_name, model
- prompt, response, tokens_in/out, duration_ms
- tool_calls list (for stream mode)
- error (if any)

### Key Design Decisions

1. **Zero overhead when disabled**: Tracing is opt-in
2. **Ring buffers**: Trace (10000), LLM log (1000), call stack (100)
3. **JSON structured**: AI can parse directly
4. **Auto-capture**: Errors/assertions capture full context

---

## Quick Decision Guide

| Situation | Use |
|-----------|-----|
| Test fails, need to see intermediate state | `breakpoint()` (Python) or `--inspect-brk` (Node) |
| Long-running process misbehaving | `remote-pdb` (Python) or `kill -SIGUSR1` (Node) |
| Need to understand WHY something fails | Systematic debugging Phase 1-3 first |
| 3+ fixes failed | Question the architecture (Phase 4, step 5) |
| Need to automate many breakpoints | CDP driver (Node) or debugpy (Python) |
