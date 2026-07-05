---
name: helen-language-development
description: "Helen 语言实现模式 — AST/解析器/解释器扩展、async/await、异常层级、作用域隔离、共享变量、v1.10 特性"
version: 1.11.0
author: Helen Team
license: MIT
tags: [helen, language-design, interpreter, async, parser, streaming, tool-calls, ffi, python-integration, contract-first, stdlib, closures, protocols, pipe-operator, pattern-matching, chinese-keywords, scope-isolation, shared-let, v1.10, v1.11]
---

# Helen Language Development

Development patterns and pitfalls for the Helen programming language (~/helen/).

## Quick Start & Environment

- **Python**: 3.12+ (required)
- **Package Manager**: uv (推荐) 或 pip
- **Install**: `cd ~/helen && uv pip install -e ".[dev]"`
- **CLI**: `helen` (REPL), `helen <file>` (run), `helen check <file>` (lint)
- **Tests**: `cd ~/helen && pytest`
- **Git remote**: `https://github.com/hahalee000000/helen.git`
- **File extension**: `.helen` (not `.hellen`)
- **Current version**: v1.11 (includes v1.10 features: scope isolation, shared let, Chinese punctuation)

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
│   ├── tools.py        # Built-in tool registry (web_search, read_file, etc.)
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

### 4. Async/Await Implementation (v1.10)

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
    new_env.values = self.values.copy()  # shallow copy of current scope
    return new_env
```

**Pitfall**: Environment snapshot must be taken BEFORE `async` expression evaluates. Otherwise, mutations between `async` and `await` corrupt the snapshot.

### 5. Agent Scope Isolation (v1.10/v1.12)

**Rules**:
- Module-level `let` is NOT visible in `agent main {}`
- Module-level `const` is auto-visible (read-only)
- `shared let` is visible and writable in `agent main {}` (v1.12: **value types only**)
- Closures in `agent main {}` use value capture (v1.12)
- Parameters of reference type (list/dict) are wrapped in ReadOnlyView (v1.12)

**Implementation**:

```python
# In SemanticAnalyzer
def visit_agent_decl(self, node: AgentDeclNode):
    # Create isolated scope for agent main
    self.env.begin_scope()
    
    # Check: module-level let should not be accessible
    for name in used_names:
        if name in module_level_lets:
            raise SemanticError(f"'{name}' is not visible in agent main")
    
    # v1.12: Also check function_vars initializers
    for var in node.function_vars:
        self._check_initializer_in_agent_scope(var.initializer)
    
    # v1.12: shared let must be value type
    for var in shared_let_declarations:
        if not self._is_value_type(var.type):
            raise SemanticError(f"shared let must be value type")
    
    # Allow: const and shared let
    self._check_body(node.main_body)
    
    self.env.end_scope()

# In Interpreter._call_agent
def _call_agent(self, agent, args):
    call_env = Environment()
    
    # v1.12: Wrap mutable params in ReadOnlyView
    for param in agent.params:
        value = args.get(param.name)
        if isinstance(value, (list, dict)):
            value = ReadOnlyView(value)
        call_env.define(param.name, value)
    
    # v1.12: Evaluate defaults in agent env, not caller env
    old_env = self.environment
    self.environment = call_env
    try:
        # ... evaluate defaults and function_vars
    finally:
        self.environment = old_env
```

**Pitfalls**:
- Forgetting to isolate agent main scope causes module-level `let` to leak
- v1.11 bug: defaults evaluated in caller env (fixed in v1.12)
- v1.11 bug: closures captured entire env (fixed in v1.12 with value capture)

### 6. Shared Let Tracking (v1.10/v1.12)

**Implementation**:

```python
# In SemanticAnalyzer
shared_vars: set[str] = set()

def visit_shared_decl(self, node: SharedDeclNode):
    self.shared_vars.add(node.name)
    self.env.define(node.name, node.type)

def visit_agent_decl(self, node: AgentDeclNode):
    # Track which shared vars are accessed
    accessed_shared = self._find_shared_access(node.main_body)
    
    # Validate: all accessed vars must be declared as shared
    for name in accessed_shared:
        if name not in self.shared_vars:
            raise SemanticError(f"'{name}' is not a shared variable")
```

**Pitfall**: Imported `shared let` from modules must be tracked correctly. The analyzer needs to follow imports.

## v1.10 Features

### Chinese Punctuation Support

Helen v1.10 supports Chinese fullwidth punctuation:

| English | Chinese | Description |
|---------|---------|-------------|
| `(` / `)` | `（` / `）` | Parentheses |
| `[` / `]` | `【` / `】` | Brackets |
| `{` / `}` | `｛` / `｝` | Braces |
| `,` | `，` | Comma |
| `.` | `。` | Period |
| `:` | `：` | Colon |
| `;` | `；` | Semicolon |
| `=` | `＝` | Equals |
| `+` | `＋` | Plus |
| `-` | `－` | Minus |
| `*` | `＊` | Asterisk |
| `/` | `／` | Slash |

**Implementation**: Lexer converts fullwidth to ASCII before tokenization.

### Chinese Quotes

| English | Chinese |
|---------|---------|
| `"..."` | `"..."` or `"..."` |
| `'...'` | `'...'` or `'...'` |

### Short-Circuit Evaluation

```helen
// && and || short-circuit
let result = a && b  // b not evaluated if a is false
let result = a || b  // b not evaluated if a is true
```

### Subscript/Field Assignment

```helen
// v1.10: assignment targets
arr[i] = x           // subscript assignment
obj.field = x        // field assignment
map["key"] = value   // map key assignment
```

### 91 Bilingual Keywords

Helen supports 91 keywords in both English and Chinese. See `references/chinese-keyword-implementation.md` for the full mapping table.

## Testing Patterns

### Contract-First + TDD

1. **Write Python contract** (type hints, docstring)
2. **Write failing test** (Helen test file)
3. **Implement function** (minimal to pass)
4. **Refactor** (maintain green tests)

### Test Organization

```
tests/
├── core/           # Lexer, parser, AST
├── semantic/       # Semantic analyzer
├── interpreter/    # Interpreter, async
├── execution/      # End-to-end tests
├── runtime/        # LLM runtime, tools
├── stdlib/         # Standard library
└── integration/    # Full agent tests
```

### Running Tests

```bash
# All tests
pytest

# Specific module
pytest tests/core/

# Single test
pytest tests/execution/test_functions.py::test_function_call -v

# Helen's built-in test framework
helen test my_test.helen
helen test my_test.helen --only "test_name" --suite "suite_name"
```

## On-Demand References

For detailed implementation guides, read these reference files:

- **Parser patterns**: `references/parser-disambiguation.md`, `references/parser-optional-expression.md`
- **Interpreter patterns**: `references/interpreter-execution-patterns.md`, `references/interpreter-sentinels.md`
- **Async/await**: `references/v1.6-v1.7-v1.8-implementation.md`, `references/comprehensive-async-testing.md`
- **Python FFI**: `references/python-ffi-implementation.md`, `references/ffi-and-agents.md`
- **Stdlib implementation**: `references/stdlib-implementation-patterns.md`
- **Streaming**: `references/streaming-implementation.md`, `references/true-sse-streaming.md`
- **Chinese keywords**: `references/chinese-keyword-implementation.md`
- **Import system**: `references/import-system-debugging.md`
- **v1.6-v1.8**: `references/v1.6-v1.7-v1.8-implementation.md` (closures, protocols, pipe, pattern matching)

## Common Pitfalls

### 1. Sentinel Flow

Break/Continue/Return sentinels must propagate through all control flow:

```python
# In visit_while_stmt
while condition:
    result = self._eval(body)
    if isinstance(result, BreakSentinel):
        break
    if isinstance(result, ReturnSentinel):
        return result  # Must propagate!
```

### 2. Pratt Parser Ambiguity

When an expression can be parsed multiple ways, use precedence:

```python
# Example: `a ? b : c ? d : e`
# Should parse as: `a ? b : (c ? d : e)` (right-associative)
self._rules[TokenType.QUESTION].precedence = Precedence.TERNARY
self._rules[TokenType.QUESTION].right_associative = True
```

### 3. Environment Snapshot Timing

Always snapshot BEFORE async evaluation:

```python
# Correct
snapshot = self.env.snapshot()
task = Task.pending(snapshot=snapshot)

# Wrong (mutations between snapshot and task creation)
task = Task.pending()  # Too late!
snapshot = self.env.snapshot()
```

## Related Skills

- **helen-syntax** — Helen syntax reference (including v1.10 features)
- **helen-stdlib** — Standard library usage guide
- **helen-agent-patterns** — Agent design patterns
- **helen-testing** — Testing framework and TDD workflow
