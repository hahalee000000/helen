---
name: helen-language-development
description: Helen programming language implementation patterns, pitfalls, and development workflows. Covers AST/parser/interpreter extension, async/await implementation, exception hierarchy, streaming with tool calls, Python FFI integration, and testing patterns.
version: 1.4.0
author: Hermes Agent
tags: [helen, language-design, interpreter, async, parser, streaming, tool-calls, ffi, python-integration, contract-first, stdlib]
---

# Helen Language Development

Development patterns and pitfalls for the Helen programming language (~/helen/).

## Quick Start & Environment

- **System Python is 3.6** — do NOT use `python3` or `pip` for Helen work
- **Use Hermes venv Python 3.11**: `~/.hermes/hermes-agent/venv/bin/python`
- **Install**: `cd ~/helen && venv_python -m pip install -e ".[dev]"` (requires pip 21.3+)
- **CLI**: `helen` (no arguments = REPL), `helen <file>` = run, `helen check <file>` = lint
- **Tests**: `cd ~/helen && venv_python -m pytest`
- **Git remote**: `https://github.com/hahalee000000/helen.git`
- **Machine**: 1.8GB RAM + 8GB swap — parser operations can OOM
- **File extension**: `.helen` (not `.hellen`)
- **Python compatibility**: Helen requires Python 3.8+ (uses `from __future__ import annotations`)

## When to Use

- Extending Helen's AST, parser, interpreter, or semantic analyzer
- Implementing new language features (control flow, async, exceptions, etc.)
- Debugging parser/interpreter issues
- Adding new predefined exceptions or error types
- Working with the Pratt parser framework
- Implementing Python FFI for accessing Python libraries
- Using contract-first + TDD workflow for language features
- Integrating external systems or libraries with Helen

## Core Architecture

```
helen/
├── core/
│   ├── ast.py          # AST nodes (frozen dataclasses with Visitor pattern)
│   ├── parser.py       # Pratt parser (prefix/infix rules)
│   ├── lexer.py        # Scanner/tokenizer
│   └── tokens.py       # Token types
├── interpreter/
│   ├── interpreter.py  # Main visitor (Visitor[object])
│   ├── environment.py  # Scope chain with snapshot() for isolation
│   ├── exceptions.py   # Exception hierarchy (HelenRuntimeError base)
│   └── task.py         # Async Task + AggregateError
├── semantic/
│   ├── analyzer.py     # Semantic analysis (Visitor[None])
│   └── type_utils.py   # Shared type_from_typenode() utility
├── runtime/
│   ├── security.py     # Security sandbox (path/URL/command/PID validation)
│   ├── constants.py    # Centralized constants (URLs, thresholds, limits)
│   ├── llm_runtime.py  # LLMRuntime interface (sync + async)
│   └── hermes_cli_llm.py  # Hermes CLI-based LLM runtime
└── stdlib/
    ├── system.py       # System ops (shell=False default, PID/signal validation)
    └── network.py      # Network ops (URL validation, download size limits)
```

## Critical Patterns

### 1. Extending the AST

When adding a new node type (e.g., `AsyncCallExprNode`):

1. **Add to `ast.py`**: Frozen dataclass inheriting from `ExpressionNode` or `StatementNode`
2. **Add visitor method to `Visitor[R]`**: Abstract method `visit_<node_type>(self, node: NodeType) -> R`
3. **Add to `ASTPrinter`**: Concrete implementation returning S-expression string
4. **Update all Visitor implementations**:
   - `Interpreter` in `interpreter.py`
   - `SemanticAnalyzer` in `semantic/analyzer.py`
   - `MockVisitor` in `tests/core/test_ast.py`
5. **Run tests**: Missing visitor methods cause `TypeError: Can't instantiate abstract class`

**Pitfall**: AST nodes are `@dataclass(frozen=True)` — cannot modify attributes after creation. Use mock objects in tests instead of trying to override `accept()`.

### 2. Pratt Parser Extension

When adding a new prefix operator (e.g., `async`):

```python
# In Parser.__init__():
self._rules[TokenType.ASYNC].prefix = self._async_call_expr
self._rules[TokenType.ASYNC].precedence = Precedence.UNARY

# Prefix function:
def _async_call_expr(self) -> AsyncCallExprNode:
    start = self._previous()  # ← CRITICAL: token already consumed!
    call_expr = self._expression(Precedence.NONE)
    # ... build and return node
```

**CRITICAL PITFALL**: Pratt parser framework calls `self._advance()` BEFORE invoking the prefix function. The prefix function must use `self._previous()` to get the operator token, NOT `self._advance()`. Using `_advance()` consumes the NEXT token, causing parse errors.

### 3. Exception Hierarchy

All catchable exceptions must:

1. **Inherit from `HelenRuntimeError`** (not Python's `Exception`)
2. **Be added to `_PREDEFINED_EXCEPTIONS` dict** in `exceptions.py`
3. **Be added to `_PREDEFINED_EXCEPTIONS` frozenset** in `semantic/analyzer.py`

```python
# In exceptions.py:
@dataclass
class AggregateError(HelenRuntimeError):
    errors: list[Exception] | None = None
    # ...

_PREDEFINED_EXCEPTIONS: dict[str, type[HelenRuntimeError]] = {
    # ...
    "AggregateError": AggregateError,
}

# In semantic/analyzer.py:
_PREDEFINED_EXCEPTIONS = frozenset({
    # ...
    "AggregateError",
})
```

**Pitfall**: If an exception doesn't inherit `HelenRuntimeError`, `try-catch` cannot catch it (the interpreter only catches `HelenRuntimeError`). If it's not in the predefined sets, semantic analysis rejects it.

### 4. Async/Await Implementation (Phase 1b)

**Architecture**:
- `async Agent()` creates a **pending Task** (not executed immediately)
- `await [tasks]` executes all pending tasks concurrently using `asyncio`
- Each task gets an **environment snapshot** for isolation
- Uses `asyncio.to_thread()` for sync interpreter code (global thread pool, fixed memory)

**Key components**:

```python
# Task.pending() stores execution context
Task.pending(
    call_node=node.call,
    interpreter=self,
    env_snapshot=self.environment.snapshot()
)

# Environment.snapshot() deep-copies scope chain
def snapshot(self) -> Environment:
    parent_snapshot = self.parent.snapshot() if self.parent else None
    new_env = Environment(parent=parent_snapshot)
    new_env._store = copy.copy(self._store)
    new_env._consts = copy.copy(self._consts)
    return new_env

# Task.execute_async() uses asyncio.to_thread()
async def execute_async(self) -> None:
    result = await asyncio.to_thread(self._execute_sync)
    # ...

# _await_tasks() uses asyncio.gather()
async def execute_all():
    coros = [task.execute_async() for task in pending_tasks]
    await asyncio.gather(*coros)
asyncio.run(execute_all())
```

**Memory model**: `asyncio.to_thread()` uses Python's global thread pool (`min(32, cpu_count + 4)` threads), NOT one thread per task. This is critical for memory-constrained environments.

**LLM async support**: `HermesCLILLMRuntime._ask_async()` uses `asyncio.create_subprocess_exec()` for non-blocking subprocess execution.

### 5. Testing Patterns

**Parser tests**: Use `_parse()` helper, check AST structure
```python
def test_async_expr_in_let(self):
    p = _parse('let task = async Worker()')
    prog = p.parse()
    stmt = prog.statements[0]
    assert isinstance(stmt, VarDeclNode)
    assert isinstance(stmt.initializer, AsyncCallExprNode)
```

**Execution tests**: Use mock objects for frozen AST nodes
```python
class MockCall:
    def accept(self, visitor):
        return 42

task = Task.pending(MockCall(), interp, interp.environment.snapshot())
```

**Concurrency tests**: Verify timing
```python
start = time.time()
results = interp._await_tasks([task1, task2, task3])
elapsed = time.time() - start
assert elapsed < 0.25  # Concurrent, not sequential
```

**End-to-end tests**: Parse → Analyze → Interpret full pipeline
```python
def parse_and_run(source: str, interpreter=None):
    """Parse and execute Helen source code end-to-end."""
    errors = ErrorReporter()
    if interpreter is None:
        interpreter = Interpreter(errors=errors, llm_runtime=MockLLMRuntime())
    
    analyzer = SemanticAnalyzer(errors, base_dir=".")
    
    scanner = Scanner(source=source, file="<test>")
    tokens = scanner.scan_all()
    
    parser = Parser(tokens, errors=errors)
    program = parser.parse()
    
    if errors.has_errors:
        raise RuntimeError(f"Parse errors: {errors}")
    
    analyzer.analyze(program)
    
    if errors.has_errors:
        raise RuntimeError(f"Semantic errors: {errors}")
    
    result = interpreter.interpret(program)
    return result, interpreter

# Usage:
source = """
agent Worker() {
    main { return "done" }
}
main {
    let task = async Worker()
    let results = await [task]
    results[0]
}
"""
result, interp = parse_and_run(source)
assert result == "done"
```

**Comprehensive test categories for language features**:
1. **Syntax forms** - statement vs expression variants
2. **Semantic behavior** - state transitions, return values, error propagation
3. **Concurrent execution** - timing verification, resource usage
4. **Error handling** - single failure, multiple failures (AggregateError), try-catch
5. **Integration** - sync vs async interpreters, mock vs real runtime
6. **Edge cases** - no return (None), complex expressions, nested calls, mixed sync/async

**Async test with custom runtime**:
```python
@pytest.mark.asyncio  # Required for strict mode!
async def test_async_llm_calls():
    class TrackingAsyncRuntime(LLMRuntime):
        def __init__(self):
            self.async_calls = 0
        
        async def act_async(self, prompt, **kwargs):
            self.async_calls += 1
            return LLMResponse(text="response", model="mock")
        
        # ... implement other methods
    
    runtime = TrackingAsyncRuntime()
    interp = AsyncLLMInterpreter(llm_runtime=runtime)
    
    # Create pending tasks and verify async path is used
    task = Task.pending(node, interp, interp.environment.snapshot())
    asyncio.run(task.execute_async())
    
    assert runtime.async_calls == 1  # Used async, not sync
```

### 6. Streaming Features (Phase 1-3)

**Architecture**:
- `llm stream [<prompt>]` — Stream LLM response with full tool-calling loop
- `for await <var> in <expr>` — Async iteration over streaming responses
- IO stdlib functions: `stream_print`, `stream_clear`, `progress_bar`, `stream_cursor_up`, `stream_cursor_down`
- True SSE streaming: `HttpLLMRuntime.act_stream()` uses OpenAI streaming API (`stream: true`)
- **Event-based protocol**: Yields typed events (content/tool_call/tool_result/error)
- **Tool call delta accumulation**: Accumulates streaming tool call chunks before execution
- **Multi-turn loop**: Automatically loops through tool calls → results → next stream

**Event Protocol**:

```python
# act_stream() yields typed event dicts:
{"type": "content", "content": "..."}              # Text chunk (streaming)
{"type": "tool_call", "name": "...", "args": {}}   # Tool invocation
{"type": "tool_result", "name": "...", "result": "..."}  # Tool result
{"type": "error", "message": "..."}                # Error
```

**Key components**:

```python
# LlmStreamStmtNode in ast.py (supports bare form)
@dataclass(frozen=True)
class LlmStreamStmtNode(StatementNode):
    prompt: ExpressionNode | None  # None = bare form (use agent's rendered prompt)
    on_chunk: ExpressionNode | None  # Optional callback
    span: SourceSpan

# Interpreter handles streaming events in visit_llm_stream_stmt()
def visit_llm_stream_stmt(self, node: LlmStreamStmtNode) -> object:
    # Bare form: use rendered agent prompt
    if node.prompt is None:
        prompt = self._get_rendered_agent_prompt()
        system_prompt = self._get_agent_setting("description")
    else:
        prompt = node.prompt.accept(self)
        system_prompt = self._get_rendered_agent_prompt()
    
    # Build tools list from agent declarations
    tools = self._build_tools_list()
    max_turns = int(self._get_agent_setting("max-turns", 1))
    if tools and max_turns < 3:
        max_turns = 3
    
    for event in self.llm_runtime.act_stream(
        prompt, tools=tools, max_turns=max_turns, ...
    ):
        event_type = event.get("type", "content")
        
        if event_type == "content":
            # Stream text chunks
            content = event.get("content", "")
            if on_chunk_fn is not None:
                on_chunk_fn(content)
            else:
                stream_print_fn.fn(content)
        
        elif event_type == "tool_call":
            # Display tool call progress
            fn_name = event.get("name", "")
            fn_args = event.get("args", {})
            args_str = ", ".join(f"{k}={v!r}" for k, v in fn_args.items())
            print(f"\n🔧 Calling {fn_name}({args_str})...\n", end="", flush=True)
        
        elif event_type == "tool_result":
            # Display tool result (truncated)
            fn_name = event.get("name", "")
            result = event.get("result", "")
            display_result = result if len(result) <= 200 else result[:200] + "..."
            print(f"✅ {fn_name} returned: {display_result}\n", end="", flush=True)
        
        elif event_type == "error":
            # Report error
            error_msg = event.get("message", "Unknown error")
            self.errors.error(ErrorCode.RUNTIME_ERROR, f"Streaming error: {error_msg}", node.span)
            break

# HttpLLMRuntime.act_stream() with tool call delta accumulation
def act_stream(self, prompt, tools=None, max_turns=5, ...):
    for turn in range(max_turns + 1):
        # Stream SSE events
        full_content = ""
        tool_calls_acc: dict[int, dict] = {}  # index -> {id, name, args_str}
        
        with urllib.request.urlopen(req) as response:
            for line_bytes in response:
                line = line_bytes.decode("utf-8").strip()
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    
                    chunk_data = json.loads(data_str)
                    delta = chunk_data["choices"][0]["delta"]
                    
                    # Text content
                    content = delta.get("content", "")
                    if content:
                        yield {"type": "content", "content": content}
                    
                    # Tool call deltas (accumulate across chunks)
                    tc_deltas = delta.get("tool_calls")
                    if tc_deltas:
                        for tc_delta in tc_deltas:
                            idx = tc_delta.get("index", 0)
                            if idx not in tool_calls_acc:
                                tool_calls_acc[idx] = {"id": "", "name": "", "args_str": ""}
                            acc = tool_calls_acc[idx]
                            fn_delta = tc_delta.get("function", {})
                            if fn_delta.get("name"):
                                acc["name"] = fn_delta["name"]
                            if fn_delta.get("arguments"):
                                acc["args_str"] += fn_delta["arguments"]
                            if tc_delta.get("id"):
                                acc["id"] = tc_delta["id"]
        
        # After stream: execute tools if any
        if tool_calls_acc:
            for i in sorted(tool_calls_acc.keys()):
                tc = tool_calls_acc[i]
                fn_name = tc["name"]
                fn_args = json.loads(tc["args_str"]) if tc["args_str"] else {}
                
                yield {"type": "tool_call", "name": fn_name, "args": fn_args}
                result = dispatch_tool(fn_name, fn_args)
                yield {"type": "tool_result", "name": fn_name, "result": result}
                
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
            
            continue  # Next turn: stream again with tool results
        else:
            break  # No tool calls — done
```

**Parser extension**: `llm stream` uses `STREAM` token, parsed as statement (not expression). Supports bare form (no prompt) in agent contexts.

**Stdlib IO functions** (in `helen/stdlib/__init__.py`):
```python
def _stream_print(text: str) -> str:
    sys.stdout.write(text)
    sys.stdout.flush()
    return text

def _progress_bar(current: int, total: int, width: int = 40) -> str:
    percentage = min(100.0, (current / total) * 100)
    filled = int(width * percentage / 100)
    bar = "█" * filled + "░" * (width - filled)
    result = f"\r[{bar}] {percentage:.0f}%"
    sys.stdout.write(result)
    sys.stdout.flush()
    return result
```

**Testing streaming**:
```python
# Parser test
def test_llm_stream_basic(self):
    source = 'llm stream "Hello"'
    # ... parse and verify LlmStreamStmtNode

# Runtime test: content events
def test_act_stream_yields_content_events(self):
    sse_lines = [
        b'data: {"choices": [{"delta": {"content": "Hello"}}]}\n',
        b'data: [DONE]\n',
    ]
    # ... mock urlopen and verify events

# Runtime test: tool call streaming
def test_act_stream_tool_calls(self):
    # Mock SSE with tool call deltas
    sse_lines_turn1 = [
        b'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_1", "function": {"name": "web_search", "arguments": ""}}]}}]}\n',
        b'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": "{\\"query\\""}}]}}]}\n',
        b'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": ":\\"test\\"}"}}]}}]}\n',
        b'data: [DONE]\n',
    ]
    # ... verify tool_call, tool_result, and content events
```

**Pitfall**: `llm stream` is a statement, not an expression — cannot assign result to variable. Use `llm act` if you need the full response text. Tool calls are accumulated from streaming deltas before execution — cannot execute tools mid-stream.

### 7. Standard Library Implementation

**Architecture**:
- `helen/stdlib/` — Standard library modules
- Each module follows contract-first + TDD pattern
- Functions registered in `helen/stdlib/__init__.py` as `BuiltinFunction` objects
- Available to Helen programs as built-in functions

**File structure per module**:

```
helen/stdlib/
├── __init__.py              # Registry + core builtins
├── <module>_contracts.py    # Protocol contracts (interfaces only)
├── <module>.py              # Implementation
tests/stdlib/
└── test_<module>.py         # Tests
```

**Contract-first workflow**:

1. **Define contracts** (`<module>_contracts.py`):
   ```python
   class StringRegexContract:
       @staticmethod
       def regex_match(pattern: str, s: str) -> dict[str, Any] | None:
           """Match pattern at the beginning of string.
           
           Args:
               pattern: Regex pattern
               s: Input string
           
           Returns:
               Dict with 'match', 'groups', 'start', 'end' if matched, None otherwise
           
           Raises:
               ValueError: If pattern is invalid
           """
           ...
   ```

2. **Write tests** (RED phase):
   ```python
   def test_match_at_start(self):
       result = _regex_match(r"hello", "hello world")
       assert result is not None
       assert result["match"] == "hello"
   ```

3. **Implement** (GREEN phase):
   ```python
   def _regex_match(pattern: str, s: str) -> dict[str, Any] | None:
       try:
           m = re.match(pattern, s)
       except re.error as e:
           raise ValueError(f"Invalid regex pattern: {e}") from e
       
       if m is None:
           return None
       
       return {
           "match": m.group(0),
           "groups": m.groups() if m.groups() else (),
           "start": m.start(),
           "end": m.end(),
       }
   ```

4. **Register** in `__init__.py`:
   ```python
   # Import with underscore prefix
   from helen.stdlib.string import (
       _regex_match, _regex_search, _regex_replace, ...
   )
   
   # Register with public name
   BuiltinFunction("regex_match", "Regex match at start", 
                   "regex_match(pattern, s)", _regex_match, "string"),
   ```

**Category organization**:
- `core` — Type conversion, generic operations
- `string` — String manipulation, regex, text analysis
- `data` — JSON, HTML, CSV, Markdown parsing
- `collection` — List/dict/set operations, functional programming
- `network` — HTTP requests, URL handling
- `io` — File I/O, streaming output
- `path` — Path manipulation
- `math` — Mathematical operations

**Pitfalls**:

1. **Naming conflicts with Python builtins**: Cannot use `set` as function name (shadows Python's `set` type):
   - ❌ `def _set(items: list) -> set:` → Type annotation error
   - ✅ `def _make_set(items: list) -> set:` → Clear intent, no conflict
   - Use `make_set`, `create_set`, or similar prefixes

2. **Cross-module name collisions**: Same function name in different modules:
   - ❌ Both `string.py` and `collection.py` define `_find` → Import conflict
   - ✅ Rename to `_find_if` in collection module (predicate-based find)
   - Use descriptive suffixes: `_if`, `_by`, `_with` to disambiguate

3. **Import order in `__init__.py`**: Must import all module functions before registering:
   ```python
   # Import all modules first
   from helen.stdlib.string import _regex_match, ...
   from helen.stdlib.data import _json_parse, ...
   from helen.stdlib.collection import _map, _filter, ...
   
   # Then register in _register_builtins()
   def _register_builtins() -> None:
       builtins = [
           # String operations
           BuiltinFunction("regex_match", ..., _regex_match, "string"),
           # Data operations
           BuiltinFunction("json_parse", ..., _json_parse, "data"),
           # Collection operations
           BuiltinFunction("map", ..., _map, "collection"),
       ]
   ```

4. **Zero external dependencies**: Stdlib must use only Python standard library:
   - ✅ `import re`, `import json`, `import csv`, `import html`, `import base64`
   - ❌ `import requests`, `import numpy`, `import pandas`
   - Complex functionality belongs in Python FFI, not stdlib

5. **Error handling**: Use specific exception types:
   - `ValueError` for invalid input (bad regex pattern, invalid JSON)
   - `FileNotFoundError` for missing files
   - `TypeError` for type mismatches
   - `RuntimeError` for I/O errors, network failures

6. **Type annotations**: Always provide complete type hints:
   ```python
   def _json_parse(text: str) -> Any:  # Returns dict, list, str, int, float, bool, or None
   def _map(lst: list[Any], fn: Callable[[Any], Any]) -> list[Any]:
   def _filter(lst: list[Any], fn: Callable[[Any], bool]) -> list[Any]:
   ```

7. **Documentation**: Every function needs docstring with Args, Returns, Raises:
   ```python
   def _regex_match(pattern: str, s: str) -> dict[str, Any] | None:
       """Match pattern at the beginning of string.
       
       Args:
           pattern: Regex pattern
           s: Input string
       
       Returns:
           Dict with 'match', 'groups', 'start', 'end' if matched, None otherwise
       
       Raises:
           ValueError: If pattern is invalid
       """
   ```

8. **Core builtin conflicts**: Functions like `_min`, `_max`, `_sum` already exist in core. When adding stats versions:
   - ❌ `_min(numbers)` → Conflicts with core `_min(*args)`
   - ✅ `_stats_min(numbers)` → Clear intent, no conflict
   - Register as `stats_min`, `stats_max`, `stats_sum` to distinguish from core

9. **Type checker with Optional after guard**: After checking `if x is None`, Pyright may still complain:
   ```python
   def _datetime(year: int | None = None, ...) -> str:
       if any(v is None for v in [year, month, day]):
           return datetime.now().isoformat()
       # Pyright still thinks year could be None here
       dt = datetime(year, month, day)  # ❌ Type error
       dt = datetime(year, month, day)  # ✅ Add type: ignore
   ```
   Use `# type: ignore[arg-type]` after the None guard when logic guarantees non-None.

10. **Date format preservation**: When input is pure date (no time), output should be pure date:
    ```python
    def _date_add(date_str: str, days: int = 0, ...) -> str:
        is_date_only = "T" not in date_str
        if is_date_only:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        else:
            dt = datetime.fromisoformat(date_str)
        
        result = dt + timedelta(days=days)
        
        # Preserve input format
        if is_date_only and hours == 0 and minutes == 0 and seconds == 0:
            return result.strftime("%Y-%m-%d")  # ✅ Pure date
        return result.isoformat(timespec="seconds")  # ✅ Datetime
    ```

11. **Python str.center() behavior**: For odd widths, extra padding goes on the right:
    ```python
    # Test expectation
    assert _center("hi", 7, "-") == "---hi--"  # ✅ Extra on right
    # NOT "--hi---" (extra on left)
    ```
    Adjust test expectations to match Python's behavior.

**Testing patterns**:

```python
# Test all edge cases
class TestRegexMatch:
    def test_match_at_start(self):
        result = _regex_match(r"hello", "hello world")
        assert result is not None
        assert result["match"] == "hello"
    
    def test_no_match(self):
        result = _regex_match(r"world", "hello world")
        assert result is None
    
    def test_match_with_groups(self):
        result = _regex_match(r"(\w+)\s(\w+)", "hello world")
        assert result["groups"] == ("hello", "world")
    
    def test_invalid_pattern(self):
        with pytest.raises(ValueError):
            _regex_match(r"[invalid", "test")

# Test file I/O with temp directories
def test_save_and_load(self):
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.json")
        data = {"name": "Alice", "age": 30}
        
        _json_save(path, data)
        loaded = _json_load(path)
        
        assert loaded == data
```

**Current stdlib modules** (as of 2026-06-18):
- ✅ **Core** (11 functions): Type conversion, generic operations
- ✅ **String** (36 functions): Regex, text analysis, encoding, operations
- ✅ **Data** (25 functions): JSON, HTML, Markdown, CSV, YAML, TOML, XML
- ✅ **Collection** (22 functions): List/dict/set operations, functional programming
- ✅ **Network** (9 functions): HTTP requests, URL handling
- ✅ **Time** (13 functions): now, time, sleep, date, datetime, date_format, date_parse, date_add, date_diff, date_year/month/day/weekday
- ✅ **Math** (15 functions): Basic math + statistics (mean, median, mode, variance, stddev, correlation, percentile, sum, product, stats_min, stats_max)
- ✅ **File** (16 functions): Basic I/O + advanced (file_size, file_modified, list_dir, walk_dir, copy_file, move_file, delete_file, delete_dir, temp_file, temp_dir)
- ✅ **IO** (8 functions): Streaming output, progress bars
- ✅ **System** (16 functions): Environment variables (env_get/set/list/delete), process management (exec, exec_async, pid, exit, kill), logging (log_debug/info/warn/error/critical, log_set_level, log_to_file)
- ✅ **Crypto** (11 functions): Hash functions (md5, sha1, sha256, sha512, hmac_sha256, hash_file), random operations (random, randint, choice, shuffle, sample)

**Total**: 185 registered functions, 355 tests, 100% pass rate

**Conditional dependencies**: Some modules (YAML, TOML) require optional third-party libraries. Use `HAS_YAML`, `HAS_TOML_READ` flags with graceful degradation and clear error messages. See `references/stdlib-p2-p3-implementation.md` for patterns.

### 8. Security Sandbox (runtime/security.py)

**Architecture**:
- Central security module providing validation functions for all entry points
- Integrated at tools, stdlib, and import resolver level
- Prevents path traversal, SSRF, command injection, and privilege escalation

**Key functions**:

```python
# Path validation — prevents directory traversal
def validate_path(path: str, *, base_dir: str | None = None,
                  must_exist: bool = False, allow_absolute: bool = False) -> str:
    """Resolve and validate path. Blocks /proc, /sys, /etc/shadow."""
    resolved = os.path.realpath(os.path.abspath(path))
    # Check blocked paths, base_dir containment
    return resolved

# URL validation — SSRF protection
def validate_url(url: str, *, allow_private: bool = False) -> str:
    """Validate URL scheme, hostname, resolved IP. Blocks private IPs."""
    # Check scheme (http/https only), block localhost, resolve and check IP ranges
    return url

# Command validation — block dangerous patterns
def validate_command(command: str | list[str]) -> str | list[str]:
    """Block rm -rf /, fork bombs, chmod -R 777 /, etc."""

# PID/signal validation — prevent privilege escalation
def validate_pid(pid: int, current_pid: int | None = None) -> int:
    """Block PID 0, 1, and self."""
def validate_kill_signal(signal_num: int) -> int:
    """Only allow SIGTERM, SIGINT, SIGHUP, SIGUSR1, SIGUSR2."""

# Environment masking — prevent secret leakage
def safe_env_list() -> dict[str, str]:
    """Return env vars with PASSWORD/SECRET/TOKEN/API_KEY values masked."""
```

**Integration points** (all must call security functions):
- `runtime/tools.py`: `_web_fetch` → `validate_url()`, `_read_file`/`_write_file`/`_patch_file` → `validate_path()`, `_shell_exec` → `validate_command()` + `shell=False` default
- `stdlib/system.py`: `_exec`/`_exec_async` → `validate_command()` + `shell=False` default, `_kill` → `validate_pid()` + `validate_kill_signal()`, `_env_list` → `safe_env_list()`
- `stdlib/network.py`: `_http_request`/`_http_download` → `validate_url()` + download size limit
- `runtime/import_resolver.py`: `_is_safe_path()` uses `realpath()` (no absolute path bypass)

**Pitfalls**:
- `shell=False` is now the DEFAULT — uses `shlex.split()` to safely parse command strings into argument lists
- `os.path.abspath()` does NOT resolve symlinks — always use `os.path.realpath()` for security checks
- The old `_is_safe_path()` allowed ALL absolute paths (REPL convenience) — this was a security hole, now fixed
- `SecurityError` is the exception type for all security violations

### 9. Code Quality Infrastructure

**Constants module** (`runtime/constants.py`):
- Centralizes all hardcoded values: URLs, model names, thresholds, timeouts, size limits
- Prevents magic numbers scattered across files
- Import from here instead of defining locally

**Shared type utilities** (`semantic/type_utils.py`):
- `type_from_typenode()` — converts AST TypeNode to semantic Type
- Used by both `analyzer.py` and `interpreter.py` (eliminates duplication)

**CI/CD** (`.github/workflows/ci.yml`):
- Lint job: `flake8 helen/ --count --statistics`
- Test job: pytest matrix across Python 3.8-3.12
- Coverage job: `pytest --cov=helen --cov-fail-under=70`
- **Note**: Pushing workflow files requires GitHub PAT with `workflow` scope

**Security tests** (`tests/runtime/test_security.py`):
- 30+ test cases covering path traversal, SSRF, command injection, PID safety, env masking

### 10. Python FFI (Foreign Function Interface)

**Architecture**:
- Helen can import and use Python libraries via `import "module_name" as alias`
- FFI module (`helen/ffi/`) provides type conversion and object wrapping
- Semantic analyzer detects Python module imports vs Helen/data file imports
- Interpreter executes Python imports and wraps results

**Contract-First Design** (user-preferred workflow):

When adding FFI or similar integration features, follow contract-first + TDD:

1. **Define Protocol contracts** (`helen/ffi/contracts.py`):
   ```python
   @runtime_checkable
   class PythonObject(Protocol):
       def get_attribute(self, name: str) -> Any: ...
       def call(self, *args: Any, **kwargs: Any) -> Any: ...
       def unwrap(self) -> Any: ...
   
   @runtime_checkable
   class PythonModule(Protocol):
       name: str
       def __getattr__(self, name: str) -> Any: ...
       def get_module(self) -> Any: ...
   
   @runtime_checkable
   class TypeConverter(Protocol):
       def helen_to_python(self, value: Any) -> Any: ...
       def python_to_helen(self, value: Any) -> Any: ...
   
   @runtime_checkable
   class PythonRuntime(Protocol):
       def import_module(self, module_name: str) -> PythonModule: ...
       def get_converter(self) -> TypeConverter: ...
   ```

2. **Write tests** (RED phase):
   - Type conversion tests (Helen ↔ Python)
   - Object wrapping tests (attribute access, function calls)
   - Module loading tests (import, caching, nested modules)
   - Integration tests (Helen code using Python modules)

3. **Implement** (GREEN phase):
   - `type_converter.py` — Automatic type conversion
   - `python_object.py` — Wrap Python objects for Helen access
   - `python_module.py` — Wrap Python modules
   - `python_runtime.py` — Manage module loading and execution context

**Key components**:

```python
# Type conversion (type_converter.py)
class DefaultTypeConverter:
    def helen_to_python(self, value: Any) -> Any:
        # Primitives pass through, lists/dicts convert recursively
        # Wrapped objects unwrap via .unwrap()
        if hasattr(value, 'unwrap'):
            return value.unwrap()
        # ... handle list, dict recursively
    
    def python_to_helen(self, value: Any) -> Any:
        # Primitives pass through, tuples → lists
        # Complex objects wrapped as WrappedPythonObject
        if isinstance(value, (int, float, str, bool, type(None))):
            return value
        if isinstance(value, (list, dict)):
            # Convert recursively
            return [self.python_to_helen(item) for item in value]
        # Wrap complex objects
        from helen.ffi.python_object import WrappedPythonObject
        return WrappedPythonObject(value)

# Object wrapper (python_object.py)
class WrappedPythonObject:
    def __init__(self, obj: Any):
        self._obj = obj
        self._converter = DefaultTypeConverter()
    
    def get_attribute(self, name: str) -> Any:
        value = getattr(self._obj, name)
        return self._converter.python_to_helen(value)
    
    def call(self, *args: Any, **kwargs: Any) -> Any:
        if not callable(self._obj):
            raise TypeError(f"'{type(self._obj).__name__}' is not callable")
        py_args = [self._converter.helen_to_python(arg) for arg in args]
        py_kwargs = {k: self._converter.helen_to_python(v) for k, v in kwargs.items()}
        result = self._obj(*py_args, **py_kwargs)
        return self._converter.python_to_helen(result)
    
    def unwrap(self) -> Any:
        return self._obj

# Module wrapper (python_module.py)
class WrappedPythonModule:
    def __init__(self, name: str, module: Any):
        self.name = name
        self._module = module
        self._converter = DefaultTypeConverter()
    
    def __getattr__(self, name: str) -> Any:
        value = getattr(self._module, name)
        return self._converter.python_to_helen(value)

# Runtime (python_runtime.py)
class DefaultPythonRuntime:
    def __init__(self):
        self._modules: dict[str, WrappedPythonModule] = {}
        self._converter = DefaultTypeConverter()
    
    def import_module(self, module_name: str) -> PythonModule:
        if module_name in self._modules:
            return self._modules[module_name]
        module = importlib.import_module(module_name)
        wrapped = WrappedPythonModule(module_name, module)
        self._modules[module_name] = wrapped
        return wrapped
```

**Semantic analyzer integration** (`semantic/analyzer.py`):

```python
def visit_import_stmt(self, node: ImportStmtNode) -> None:
    path = node.module_path
    
    # Detect Python module vs Helen/data file
    # Python modules: no extension, or .py, or dotted names like "os.path"
    # Helen/data files: .helen, .json, .md, .txt, .yaml, .yml
    is_python_module = (
        path.endswith('.py') or
        not any(path.endswith(ext) for ext in ('.helen', '.json', '.md', '.txt', '.yaml', '.yml'))
    )
    
    if is_python_module:
        # Register alias as variable
        alias = node.alias if node.alias else path.split('.')[-1]
        from helen.semantic.symbols import Symbol
        sym = Symbol(alias, kind="import", is_const=False)
        self.symbols.define(alias, sym)
        return
    
    # ... handle Helen/data file imports
```

**Interpreter integration** (`interpreter/interpreter.py`):

```python
def visit_import_stmt(self, node: ImportStmtNode) -> object:
    path = node.module_path
    is_python_module = (
        path.endswith('.py') or
        not any(path.endswith(ext) for ext in ('.helen', '.json', '.md', '.txt', '.yaml', '.yml'))
    )
    
    if is_python_module:
        return self._import_python_module(node)
    
    # ... handle Helen/data file imports

def _import_python_module(self, node: ImportStmtNode) -> object:
    from helen.ffi.python_runtime import DefaultPythonRuntime
    
    if not hasattr(self, '_python_runtime'):
        self._python_runtime = DefaultPythonRuntime()
    
    module_name = node.module_path
    if module_name.endswith('.py'):
        module_name = module_name[:-3]
    
    try:
        module = self._python_runtime.import_module(module_name)
        alias = node.alias if node.alias else module_name.split('.')[-1]
        self.environment.define(alias, module)
    except ImportError as e:
        self._runtime_error(node.span, f"Cannot import Python module '{module_name}': {e}")
        return None

# In visit_call(), handle WrappedPythonObject:
def visit_call(self, node: CallNode) -> object:
    # ... existing code ...
    
    # Check if callee is a Python FFI object
    from helen.ffi.python_object import WrappedPythonObject
    if isinstance(callee, WrappedPythonObject):
        return callee.call(*args)
    
    # ... rest of call handling
```

**Usage in Helen**:

```helen
import "math" as math
import "json" as json
import "os.path" as path

main {
    // Call Python functions
    let sqrt_result = math.sqrt(16)
    print(sqrt_result)  // 4.0
    
    // Access Python constants
    let pi = math.pi
    print(pi)  // 3.141592653589793
    
    // Use Python libraries
    let data = {"name": "Alice", "age": 30}
    let json_str = json.dumps(data)
    print(json_str)
    
    // Nested modules
    let joined = path.join("a", "b", "c")
    print(joined)  // a/b/c
}
```

**Testing patterns**:

```python
# Type conversion tests
def test_helen_list_to_python(self):
    converter = DefaultTypeConverter()
    result = converter.helen_to_python([1, 2, 3])
    assert result == [1, 2, 3]
    assert isinstance(result, list)

def test_python_complex_object_wrapped(self):
    converter = DefaultTypeConverter()
    class CustomClass:
        def __init__(self):
            self.value = 42
    obj = CustomClass()
    result = converter.python_to_helen(obj)
    assert hasattr(result, 'unwrap')
    assert result.unwrap() is obj

# Object wrapper tests
def test_call_function(self):
    def add(a, b):
        return a + b
    wrapper = WrappedPythonObject(add)
    result = wrapper.call(2, 3)
    assert result == 5

def test_get_attribute(self):
    class TestClass:
        def __init__(self):
            self.value = 42
    obj = TestClass()
    wrapper = WrappedPythonObject(obj)
    assert wrapper.get_attribute("value") == 42

# Integration tests
def test_import_python_module(self):
    source = '''
    import "math" as math
    main {
        let result = math.sqrt(16)
        print(result)
    }
    '''
    errors = ErrorReporter()
    scanner = Scanner(source=source, file="<test>")
    tokens = scanner.scan_all()
    parser = Parser(tokens, errors=errors)
    program = parser.parse()
    
    analyzer = SemanticAnalyzer(errors)
    analyzer.analyze(program)
    
    interp = Interpreter(errors=errors)
    interp.interpret(program)
    
    assert not errors.has_errors
```

**Pitfalls**:

1. **Module detection logic**: Must distinguish Python modules from Helen/data files:
   - Python: no extension, `.py`, or dotted names like `"os.path"`
   - Helen/data: `.helen`, `.json`, `.md`, `.txt`, `.yaml`, `.yml`
   - Use negative check: `not any(path.endswith(ext) for ext in (...))`

2. **Type conversion recursion**: Lists and dicts must convert recursively:
   - `helen_to_python([1, [2, 3]])` → `[1, [2, 3]]` (nested lists)
   - `python_to_helen({"a": {"b": 1}})` → `{"a": {"b": 1}}` (nested dicts)

3. **Circular imports**: `type_converter.py` imports `WrappedPythonObject` lazily to avoid circular dependency:
   ```python
   def python_to_helen(self, value: Any) -> Any:
       # ... primitive handling ...
       from helen.ffi.python_object import WrappedPythonObject  # Lazy import
       return WrappedPythonObject(value)
   ```

4. **Module caching**: `DefaultPythonRuntime` caches imported modules to avoid re-importing:
   ```python
   def import_module(self, module_name: str) -> PythonModule:
       if module_name in self._modules:
           return self._modules[module_name]
       # ... import and cache ...
   ```

5. **Nested module aliases**: For `"os.path"`, use last part as default alias:
   ```python
   alias = node.alias if node.alias else module_name.split('.')[-1]
   # "os.path" → alias "path"
   ```

6. **Function call integration**: Interpreter's `visit_call()` must check for `WrappedPythonObject`:
   ```python
   from helen.ffi.python_object import WrappedPythonObject
   if isinstance(callee, WrappedPythonObject):
       return callee.call(*args)
   ```

7. **Contract-first workflow**: User explicitly requested this pattern for FFI:
   - Define Protocol contracts first (interfaces only, no implementation)
   - Write comprehensive tests (RED phase)
   - Implement to make tests pass (GREEN phase)
   - This ensures clean interfaces and complete test coverage

## Common Pitfalls

1. **Pratt parser prefix functions**: Must use `self._previous()`, not `self._advance()`
2. **Frozen dataclasses**: Cannot modify attributes; use mocks in tests
3. **Exception hierarchy**: Must inherit `HelenRuntimeError` AND be in predefined sets
4. **Visitor pattern**: Adding AST node requires updating ALL visitors (Interpreter, SemanticAnalyzer, ASTPrinter, test MockVisitors)
5. **Async execution**: `async` creates pending task; execution happens on `await`
6. **Environment isolation**: Each async task needs `environment.snapshot()` to avoid race conditions
7. **Memory constraints**: Use `asyncio.to_thread()` (global pool), not per-task threads
8. **Helen `throw` syntax**: Requires exception type name, not bare string
   - ❌ `throw "error message"` → Parse error: "Expected type name"
   - ✅ `throw RuntimeError("error message")` → Correct
9. **pytest-asyncio strict mode**: All async tests MUST have `@pytest.mark.asyncio` decorator
   - Without it: `async def functions are not natively supported` error
   - Helen uses `asyncio: mode=Mode.STRICT` in `pyproject.toml`
10. **Statement vs expression form semantics**:
    - `async Agent()` (statement) → executes IMMEDIATELY, returns `Task.completed`
    - `let task = async Agent()` (expression) → DEFERS execution, returns `Task.pending`
11. **MockLLMRuntime for async tests**: Doesn't override async methods
    - For testing async paths, create custom runtime with `act_async()` / `route_async()`
    - Otherwise falls back to sync `act()` / `route()` which blocks
12. **Streaming chunk format compatibility**: `act_stream()` yields dicts `{"content": ...}`, not objects
    - ❌ `chunk.content` → AttributeError: 'dict' object has no attribute 'content'
    - ✅ Must handle both formats: `isinstance(chunk, dict)` → `chunk.get("content")`, else `chunk.content`
    - `LLMRuntime.act_stream()` default implementation yields dicts; `StreamingResponse` yields strings
    - Always check chunk type before accessing content
13. **REPL streaming integration**: When converting from `llm act` to `llm stream` in agent main:
    - `llm act` returns value → REPL handler prints return value
    - `llm stream` prints to stdout → REPL handler must NOT print return value
    - Change handler from `response = _run_assistant(); print(response)` to `_run_assistant(); print()` (final newline)
    - Update return type from `str` to `bool` (success/failure) and print errors to stderr
14. **Bare form consistency for LLM statements**: When adding a new LLM statement variant (e.g., `llm stream`), ensure it supports bare form (no prompt) if it should work in agent contexts:
    - Parser: Check for statement terminators (`RIGHT_BRACE`, `SEMICOLON`, `EOF`, etc.) and newline boundaries → set `prompt_expr = None`
    - AST: Make `prompt` field optional (`ExpressionNode | None`)
    - Interpreter: Handle `None` prompt by using `_get_rendered_agent_prompt()` as user message, `_get_agent_setting("description")` as system prompt
    - Tests: Update "missing prompt should error" tests to "bare form should parse OK" when bare form is supported
    - Example: `llm act` supports bare form → `llm stream` must also support it for consistency in agent main blocks
15. **True streaming implementation**: `HttpLLMRuntime.act_stream()` must use OpenAI streaming API (`stream: true`), not fallback to `act()`:
    - Send POST with `"stream": true` in payload
    - Parse Server-Sent Events (SSE): lines starting with `data: ` followed by JSON or `[DONE]`
    - Extract `choices[0].delta.content` from each chunk
    - Yield typed events: `{"type": "content", "content": ...}`, `{"type": "tool_call", ...}`, etc.
    - Handle malformed JSON gracefully (skip and continue)
    - Handle empty content (skip chunks with `content == ""`)
    - Fallback to `act()` only if streaming API is not supported by the endpoint
16. **Tool call delta accumulation**: OpenAI streams tool calls incrementally across multiple SSE chunks:
    - Each chunk contains `delta.tool_calls[{index, function: {name, arguments}}]`
    - Must accumulate `function.name` and `function.arguments` strings across chunks
    - Only execute tool AFTER stream completes and all deltas accumulated
    - Use dict indexed by `index` to handle multiple parallel tool calls
    - Parse accumulated `arguments` string as JSON after accumulation completes
17. **Multi-turn tool calling loop**: After tool execution, must loop back and stream again:
    - Append assistant message with `tool_calls` array to messages
    - Append tool result messages with `role: "tool"` and `tool_call_id`
    - Continue loop: send new streaming request with updated messages
    - Break loop when no tool calls in response (final text answer)
    - Respect `max_turns` limit; inject nudge prompt on last turn
18. **Event-based streaming protocol**: `act_stream()` yields typed event dicts, not raw chunks:
    - `{"type": "content", "content": "..."}` — text chunk
    - `{"type": "tool_call", "name": "...", "args": {...}}` — tool invocation
    - `{"type": "tool_result", "name": "...", "result": "..."}` — tool result
    - `{"type": "error", "message": "..."}` — error
    - Interpreter must handle all event types, not just content
    - Display tool call progress with 🔧/✅ format for user feedback
19. **dispatch_tool import location**: In `HttpLLMRuntime.act_stream()`, import `dispatch_tool` inside the function:
    - `from helen.runtime.tools import dispatch_tool` (inside function body)
    - In tests, patch `helen.runtime.tools.dispatch_tool`, NOT `helen.runtime.http_llm.dispatch_tool`
    - Lazy import avoids circular dependencies at module load time
20. **Tool result truncation for display**: Long tool results can flood the terminal:
    - Truncate results to 200 chars for display: `result if len(result) <= 200 else result[:200] + "..."`
    - Full result still sent to LLM in messages (no truncation there)
    - Only truncate for human-readable terminal output
21. **Pip install in venv**: When installing optional dependencies (pyyaml, toml), use `python -m pip install` not bare `pip install`:
    - ❌ `pip install toml` → May install to system Python, not active venv
    - ✅ `python -m pip install toml` → Installs to active Python interpreter
    - Verify: `python -c "import toml"` after install
    - This ensures the dependency is available to the Helen runtime

## Verification Checklist

After implementing a new feature:

- [ ] All AST visitors updated (Interpreter, SemanticAnalyzer, ASTPrinter, test mocks)
- [ ] Exception types in both `_PREDEFINED_EXCEPTIONS` (exceptions.py + analyzer.py)
- [ ] Parser prefix/infix functions use correct token access (`_previous()` vs `_advance()`)
- [ ] Async features create pending tasks, execute on await
- [ ] Environment snapshots for async task isolation
- [ ] Tests cover: parsing, semantic analysis, execution, concurrency timing
- [ ] `throw` statements use exception type names (e.g., `throw RuntimeError("msg")`)
- [ ] Async tests have `@pytest.mark.asyncio` decorator (strict mode)
- [ ] Both statement and expression forms tested (if applicable)
- [ ] Streaming features: bare form parsing, content events, tool call events, multi-turn loop
- [ ] Tool call streaming: delta accumulation, execution, result display
- [ ] Python FFI: type conversion, object wrapping, module loading, semantic analyzer integration
- [ ] Python FFI: function call handling in interpreter, nested module aliases
- [ ] `python -m pytest tests/ -x -q` passes (1030+ tests)
- [ ] End-to-end test with `helen` CLI
- [ ] **Documentation updated** (wiki tutorial, git repo tutorial, wiki technical docs, wiki index)
- [ ] **Function counts consistent** across all documentation locations
- [ ] **Optional dependencies installed** with `python -m pip install` (not bare `pip`)

## Documentation & Wiki Sync

### Two Locations Must Stay in Sync

Helen documentation exists in two places:
1. **Wiki** (`~/wiki/helen/`) — Standalone wiki site
2. **Git repo** (`~/helen/docs/`) — Version-controlled with code

**Critical**: Both must be updated together when adding features.

### Files to Update

| Wiki Location | Git Repo Location | Content |
|---------------|-------------------|---------|
| `~/wiki/helen/tutorial/10-stdlib.md` | `~/helen/docs/tutorial.md` (section "教程 10") | Stdlib reference |
| `~/wiki/helen/toolchain/stdlib.md` | — | Technical stdlib docs |
| `~/wiki/helen/index.md` | — | Wiki index |

### Update Workflow

After implementing new stdlib modules:

1. **Update wiki tutorial** (`~/wiki/helen/tutorial/10-stdlib.md`):
   - Add new functions with examples
   - Update function count in header
   - Add comprehensive examples

2. **Update git repo tutorial** (`~/helen/docs/tutorial.md`):
   - Find section "# 教程 10: 标准库参考"
   - Update with same content as wiki
   - Update table of contents entry

3. **Update wiki technical docs** (`~/wiki/helen/toolchain/stdlib.md`):
   - Add function signatures in table format
   - Update function count statistics
   - Document categories

4. **Update wiki index** (`~/wiki/helen/index.md`):
   - Update stdlib entry with new function count
   - Keep description concise

5. **Commit and push**:
   ```bash
   cd ~/helen && git add -A && git commit -m "docs: update stdlib reference" && git push origin master
   ```

### Pitfall: Wiki is Not Git-Tracked

`~/wiki/helen/` is NOT a git repository. Changes there are local only. The git repo (`~/helen/docs/`) is the source of truth for version control.

**Workflow**:
- Edit wiki files for immediate visibility
- Sync same changes to git repo for version control
- Always commit+push git repo changes

## References

### Implementation Patterns
- `references/async-await-implementation.md` — Detailed async/await design decisions and code patterns
- `references/comprehensive-async-testing.md` — Comprehensive async testing patterns (32 tests, end-to-end approach)
- `references/streaming-implementation.md` — Phase 1-3 streaming: llm stream, for await, IO stdlib functions
- `references/true-sse-streaming.md` — True SSE streaming implementation with OpenAI API
- `references/python-ffi-implementation.md` — Python FFI: contract-first design, type conversion, module wrapping, integration patterns
- `references/stdlib-implementation-patterns.md` — Stdlib implementation: contract-first + TDD, registration patterns, naming pitfalls
- `references/stdlib-p1-implementation.md` — P1 modules: Time (13), Math Stats (11), File Advanced (10)
- `references/stdlib-p2-p3-implementation.md` — P2+P3 modules: System (16), Crypto (11), Data Formats (12)
- `references/documentation-workflow.md` — Wiki sync, tutorial updates, documentation patterns

### Pitfalls, Bugs & Semantic Analysis
- `references/environment-and-pitfalls.md` — Environment setup, type checking pitfalls, parser bugs, interpreter sentinel flow, naming conventions, SemanticAnalyzer patterns
- `references/interpreter-sentinels.md` — BreakSentinel/ContinueSentinel/ReturnSentinel flow through interpreter
- `references/parser-disambiguation.md` — Parser ambiguity resolution patterns
- `references/parser-optional-expression.md` — Optional expression parsing patterns
- `references/import-system-debugging.md` — Import system debugging guide
- `references/helen-config.md` — Helen configuration details
- `references/hld-implementation.md` — High-level design implementation notes
- `references/fuzzy-match.md` — Fuzzy matching implementation
- `references/async-interpreter.md` — Async interpreter patterns

### REPL Extension & Agent Patterns
- `references/repl-extension.md` — Extend Helen REPL with Helen programs: architecture, path resolution, parameter injection
- `references/helen-assistant-implementation.md` — Helen language assistant implementation details
- `references/ffi-and-agents.md` — Stdlib functions, Python FFI pitfalls & agent development patterns

### Quality Assessment & Code Improvement
- `references/quality-assessment-2026-06.md` — 7-dimension quality assessment framework, common issues found (silent exceptions, dead TYPE_CHECKING, coverage gaps), fix patterns, coverage improvement techniques, assessment results over 3 rounds

### Testing & Tutorials
- `references/tutorial-sync.md` — Tutorial synchronization between wiki and git repo
- `references/tutorial-testing.md` — Tutorial testing patterns
- `references/testing-helen-programs.md` — Integration test pattern for Helen programs from Python
- `references/python-asyncio-compatibility.md` — Python asyncio patterns for REPL vs script contexts
- `references/streaming-output-tdd.md` — Contract-first + TDD workflow for streaming output
- `references/streaming-output-tdd.md` — Contract-first + TDD workflow for streaming output