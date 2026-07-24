# Execution Engine (Interpreter)

> Module M5 | `helen/interpreter/` (Mixin architecture) | Tests: `tests/execution/`

---

## Overview

The Interpreter is the second visitor for ASTs, responsible for **executing Helen programs**. It adopts a Mixin architecture that splits different responsibilities into independent modules:

```python
class Interpreter(LlmMixin, StreamingMixin, PatternMixin,
                  ExceptionMixin, ImportMixin, Visitor[object]):
    """Each visit method returns the computed value of the node, or a control-flow Sentinel."""
```

### Mixin Architecture

| Module | Responsibility | Core Methods |
|--------|---------------|--------------|
| `interpreter.py` | Core execution engine: variables/functions/control flow/agents | `visit_program`, `_execute_stmts`, `_call_agent` |
| `llm_mixin.py` | LLM integration: act/if, tool building, history management | `visit_llm_act_expr`, `visit_llm_if_stmt` |
| `pattern_mixin.py` | Pattern matching: match/case statements and expressions | `visit_match_stmt`, `visit_match_expr` |
| `exception_mixin.py` | Exception handling: try/catch/throw/assert | `visit_try_stmt`, `visit_throw_stmt` |
| `import_mixin.py` | Import mechanism: multi-format imports (.helen/.py/.json etc.) | `visit_import_stmt`, `_create_module_object` |
| `streaming_mixin.py` | Streaming call management and cancellation | `cancel_streaming_call`, `_register_streaming_call` |
| `closure.py` | Closure class + free variable analysis | `Closure`, `_compute_free_variables` |
| `readonly_view.py` | ReadOnlyView (agent parameter isolation) | `ReadOnlyView` |
| `shared_store.py` | SharedStore (thread-safe shared state) | `SharedStore`, `SharedStoreMethod` |

### Constructor

```python
def __init__(self, errors=None, llm_runtime=None,
             import_resolver=None, program_args=None)
```

The `program_args` parameter receives the argument list passed from the CLI (from `helen <file> [args...]`), and is defined as a predefined `const argv` in the global Environment.

### Predefined Variables

| Variable | Type | Description |
|----------|------|-------------|
| `argv` | `const list<str>` | Command-line arguments (all arguments after `helen <file>`) |

`argv` is injected into the global scope at Interpreter initialization via `environment.define("argv", program_args, is_const=True)`. Because it is `const`, it is automatically propagated into agent isolated scopes via `_call_agent()`'s const injection mechanism.

The semantic analyzer registers `argv` as a symbol with `kind="const"` in `_register_stdlib()`, so using `argv` in programs does not trigger a `UNDECLARED_VARIABLE` error. Reassigning `argv` will produce a "cannot assign to const variable" error during semantic analysis.

```helen
// Command line: helen tool.helen --verbose --output=json
print(argv)          // ["--verbose", "--output=json"]
print(len(argv))     // 2
print(argv[0])       // "--verbose"

// argv = []          // ❌ Semantic error: cannot assign to const variable
```

---

## Environment Scope Chain

```python
class Environment:
    def __init__(self, parent: Environment | None = None)
    def lookup(self, name: str) -> Any       # Look up variable (walk up the chain)
    def assign(self, name: str, value: Any)  # Modify variable (must already exist)
    def define(self, name: str, value: Any)  # Declare a new variable
    def enter_scope(self) -> Environment     # Create a child scope
```

### Lookup Rules

```
env_A (x=1, y=2)
  └── env_B (z=3)
        lookup("z") → 3 (current level)
        lookup("x") → 1 (parent level)
        lookup("w") → NameError (not found)
```

### Agent Call Isolation

Each `call Agent()` creates a **completely independent root Environment**:

```python
def _call_agent(self, node: AgentDeclNode, args: dict) -> object:
    isolated_env = Environment()  # No parent, fully isolated
    # ... execute Agent logic in isolated_env
```

### v1.10 Agent Main Scope Isolation

`agent main {}` executes in a fully isolated environment; module-level `let` is not visible:

```python
def visit_agent_main(self, node: MainBlockNode):
    # Create a new root environment (no parent)
    main_env = Environment()
    
    # Only import module-level const (read-only)
    for name, symbol in self.global_env.constants.items():
        main_env.define(name, symbol.value)
    
    # Import shared let (read-write)
    for name, symbol in self.global_env.shared_vars.items():
        main_env.define(name, symbol)
    
    # Note: module-level let is NOT imported
    
    # Execute main block in main_env
    for stmt in node.statements:
        stmt.accept(self, env=main_env)
```

**Example**:

```helen
let moduleVar = "module-level"   // ❌ Not visible in main
const MODULE_CONST = "constant"  // ✅ Read-only visible
shared let sharedVar = 0         // ✅ Read-write

agent MyAgent {
  main {
    // moduleVar              // ❌ NameError
    let x = MODULE_CONST      // ✅ "constant"
    sharedVar += 1            // ✅ 1
  }
}
```

### v1.10 Module Function Scope Resolution

When calling a function from an imported module, the module-level `Environment` is used as the parent scope, ensuring access to the module's own `const` and `shared let`:

```python
def _create_module_object(self, result):
    module = { "__type__": "module", ... }
    # Create module-level Environment, parent is caller's env (can access stdlib)
    module_env = Environment(parent=self.environment)
    for name, data in self.import_resolver.data.items():
        if isinstance(data, VarDeclNode) and (not data.mutable or data.shared):
            value = data.initializer.accept(self)
            module_env.define(name, value, is_const=not data.mutable)
    module["__env__"] = module_env
    return module

def _call_function(self, func, args, parent_env=None):
    # For module functions, pass parent_env = module["__env__"]
    if parent_env is not None:
        call_env = Environment(parent=parent_env)  # Module scope
    else:
        call_env = self.environment.enter_scope()  # Normal call
    # ... bind parameters, execute function body
```

**Scope chain**:

```
Function local scope
    └─ Module Environment (const + shared let)
        └─ Caller's global Environment (stdlib + other global variables)
```

### v1.10 Subscript/Field Assignment Execution

Assignment statements now support index and field access:

```python
def visit_assignment(self, node: AssignmentNode):
    if isinstance(node.target, IndexNode):
        # arr[i] = value
        obj = node.target.object.accept(self)
        index = node.target.index.accept(self)
        value = node.value.accept(self)
        obj[index] = value
        return value
    
    elif isinstance(node.target, AccessNode):
        # obj.field = value
        obj = node.target.object.accept(self)
        field = node.target.field
        value = node.value.accept(self)
        setattr(obj, field, value)
        return value
    
    else:
        # IDENTIFIER = value
        value = node.value.accept(self)
        self.env.assign(node.target.name, value)
        return value
```

**Example**:

```helen
let arr = [1, 2, 3]
arr[0] = 10  // ✅ arr becomes [10, 2, 3]

let obj = { name: "Alice", age: 30 }
obj.name = "Bob"  // ✅ obj becomes {name: "Bob", age: 30}
```

### v1.12 Shared Store Execution Semantics

`shared store` creates a `SharedStore` instance at runtime:

```python
class SharedStore:
    """Controlled shared mutable state."""
    def __init__(self, name, fields, methods):
        self._name = name
        self._fields = dict(fields)      # Private fields
        self._methods = dict(methods)    # Method closures
        self._lock = threading.RLock()   # Thread safety
```

**Execution rules**:
- `visit_shared_store_decl`: Evaluates all field initial values, creates a `SharedStore` instance, registers it in the current environment
- Field access `store.field` → `SharedStore.__getattr__()`, automatically acquires RLock
- Field assignment `store.field = x` → `SharedStore.__setattr__()`, automatically acquires RLock
- Method call `store.method(args)` → Returns a `SharedStoreMethod` wrapper; execution is serialized through the store's RLock
- `_`-prefixed fields/methods are private; accessing them from within an agent raises `AttributeError`
- Internal properties (`_name`/`_fields`/`_methods`/`_lock`) are not accessible from Helen code

**Thread safety**:
- Field read/write operations are protected by RLock
- The lock is held during method execution, preventing concurrent field modifications
- Multiple agents can safely access the same SharedStore concurrently

```helen
shared store Cache {
    data: dict = {}
    _hits: int = 0  // Private, not accessible from agents

    fn get(key): any {
        _hits += 1   // ✅ Store's own method can access private fields
        return data[key]
    }
}

agent Worker(cache: Cache) {
    main {
        cache.get("key")    // ✅ Access via public method
        cache._hits = 0     // ❌ ScopeViolationError
    }
}
```

### v1.12 Agent Isolation Enhancements

**Closure value capture**:
```python
def visit_lambda(self, node: LambdaNode) -> object:
    # v1.12: Value snapshot instead of environment reference capture
    captured = {}
    for var_name in node.free_variables:
        captured[var_name] = self.environment.lookup(var_name)
    captured_env = Environment()
    for name, value in captured.items():
        captured_env.define(name, value)
    return Closure(lambda_node=node, captured_env=captured_env)
```

**Parameter default value evaluation environment fix**:
- v1.11 and earlier: Default values evaluated in caller env (could leak module variables)
- v1.12+: Switch to agent `call_env` first, then evaluate default values

**Reference-type parameter read-only wrapping**:
```python
# In _call_agent
for param in agent.params:
    if param.name in args:
        value = args[param.name]
        if isinstance(value, (list, dict)):
            value = ReadOnlyView(value)  # Read-only proxy
        call_env.define(param.name, value)
```

### v1.13 Channel Execution Semantics (updated in v1.18)

As of v1.18, the `channel X { fields }` declaration syntax has been removed. Channels are now created via the `Channel()` constructor or `spawn`, and are message queues (send/receive) rather than SharedStore aliases.

**New Channel runtime** (`helen/runtime/channel.py`):
- `Channel` + `ChannelEndpoint` dual-endpoint model
- Two internal `queue.Queue` instances, supporting bidirectional communication
- `send(msg)` / `receive(timeout?)` / `try_receive()` / `cancel()` / `close()` / `is_closed()`
- Chinese method aliases: `发送`/`接收`/`尝试接收`/`取消`/`关闭`/`已关闭`

See [[interpreter/spawn|Concurrency and spawn]] for details.

### v1.18 spawn Execution Semantics

`spawn` is a concurrency primitive introduced in v1.18, replacing the old `async/await/detach`:

```python
def visit_spawn_expr(self, node: SpawnExprNode) -> object:
    from helen.runtime.channel import Channel, ChannelEndpoint

    # 1. Create a Channel (double-ended queue)
    channel = Channel(name=f"spawn_{agent_name}")
    main_endpoint = ChannelEndpoint(channel, is_main_thread=True)
    spawned_endpoint = ChannelEndpoint(channel, is_main_thread=False)

    # 2. Snapshot the environment (deep copy everything, including SharedStore)
    env_snapshot = self.environment.snapshot()

    # 3. Execute the spawned agent in a new daemon thread
    def run_spawned():
        spawned_interpreter = Interpreter(...)
        spawned_interpreter.environment = env_snapshot
        try:
            call_node.accept(spawned_interpreter)
        except Exception as e:
            spawned_endpoint.send({"__error__": True, "message": str(e)})
        finally:
            spawned_endpoint.close()

    thread = threading.Thread(target=run_spawned, daemon=True)
    thread.start()

    # 4. Return the main-thread endpoint (Channel type)
    return main_endpoint
```

**Snapshot semantics change**: Full deep copy, no exceptions (including SharedStore).
**SharedStore.__deepcopy__**: Fields are deep-copied; methods are not copied (closures reference the old environment).
**Explicit sharing**: Pass SharedStore references through channels.

See [[interpreter/spawn|Concurrency and spawn]] for details.

---

## Statement Execution

### Variable Declarations

```helen
let x = 42           # mutable=True, can be reassigned
const PI = 3.14      # mutable=False, reassignment → E0346
```

### Control Flow

| Statement | Implementation Mechanism |
|-----------|-------------------------|
| `if/else` | Evaluate condition → `_truthy()` → execute corresponding branch |
| `for x in list` | Iterate list → bind each element to x → execute loop body |
| `while cond` | Evaluate condition → `_truthy()` → loop execution |
| `break` | Throw `BreakSentinel` → caught by loop |
| `continue` | Throw `ContinueSentinel` → caught by loop |

### `_truthy()` Rules

```python
def _truthy(value: object) -> bool:
    None     → False
    False    → False
    0, 0.0   → False
    ""       → False
    [] {}    → False
    Other    → True
```

### Pattern Matching

```helen
match x {
    case 1: print("one")
    case 2: print("two")
    default: print("other")
}
```

- Match `case` literal values in order
- Must have a `default` (checked during semantic analysis)

### Exception Handling

```helen
// Throw an exception
throw RuntimeError("something went wrong")
throw LLMError  // Use default message

// Catch exceptions
try {
    risky_operation()
} catch RuntimeError err {
    print("Error: " + err.message)
} catch LLMError err {
    print("LLM Error: " + err.message)
} catch {
    print("Unknown error")
} finally {
    cleanup()
}
```

- `throw` statement throws an instance of a predefined exception type
- Type-matching catch clauses execute first (supports inheritance: catch LLMError also catches TimeoutError)
- catch-all must be last
- finally always executes

**Predefined exception hierarchy**:
```
AnyError (root)
├── LLMError
│   ├── TimeoutError
│   └── ModelError
├── ToolError
└── RuntimeError
```

---

## Expression Evaluation

### v1.10 Short-Circuit Evaluation

`&&` and `||` operators support short-circuit evaluation, avoiding unnecessary computation:

```python
def visit_binary_op(self, node: BinaryOpNode) -> object:
    op = node.operator.type
    
    # && short-circuit evaluation
    if op == TokenType.AND:
        left = node.left.accept(self)
        if not self._truthy(left):
            return False  # Short-circuit: don't evaluate right
        right = node.right.accept(self)
        return self._truthy(right)
    
    # || short-circuit evaluation
    if op == TokenType.OR:
        left = node.left.accept(self)
        if self._truthy(left):
            return True  # Short-circuit: don't evaluate right
        right = node.right.accept(self)
        return self._truthy(right)
    
    # Other operators evaluate normally
    left = node.left.accept(self)
    right = node.right.accept(self)
    # ...
```

**Example**:

```helen
// && short-circuit
let x = false && expensiveCall()  // expensiveCall() is not executed
let y = true && expensiveCall()   // expensiveCall() is executed

// || short-circuit
let a = true || expensiveCall()   // expensiveCall() is not executed
let b = false || expensiveCall()  // expensiveCall() is executed

// Practical usage
let user = get_user() || create_default_user()
let valid = user != null && user.is_active()
```

**Precedence**:
- `||` precedence 3 (left-associative)
- `&&` precedence 4 (left-associative)
- `&&` has higher precedence than `||`

### Binary Operations

```python
def visit_binary_op(self, node: BinaryOpNode) -> object:
    left = node.left.accept(self)
    right = node.right.accept(self)
    op = node.operator.type

    if op == TokenType.PLUS:
        return self._add(left, right)  # Numeric addition or string concatenation
    if op == TokenType.EQUAL_EQUAL:
        return self._equal(left, right)
    # ...
```

### `_add()` Supports String Concatenation

```helen
let greeting = "Hello, " + "World"   # → "Hello, World"
let result = "Score: " + 42          # → "Score: 42" (auto-converted to string)
```

### Function Calls

```helen
fn add(a, b) { return a + b }
let result = add(1, 2)   # → 3
```

- Look up function name → create new scope → bind parameters → execute function body

---

## _stringify()

Converts Helen values to string representation:

```python
None      → "null"
True      → "true"
False     → "false"
3.0       → "3"     (integers without decimal point)
3.14      → "3.14"
[1, 2]    → "[1, 2]"
{"a": 1}  → "{a: 1}"
```

---

## Control Flow Sentinel Mechanism

```python
class BreakSentinel(Exception): pass
class ContinueSentinel(Exception): pass
class ReturnSentinel(Exception):
    def __init__(self, value: Any):
        self.value = value
```

Loops and functions capture Sentinels via `try/except`:

```python
def visit_for_stmt(self, node):
    for item in iterable:
        self.environment.define(node.name, item)
        try:
            self._execute_stmts(node.body)
        except BreakSentinel:
            break
        except ContinueSentinel:
            continue
```

---

## AI-Native Observability

> Module `helen/runtime/observability.py`

The Interpreter integrates an AI-native observability system, providing structured debugging context for AI agents.

### ObservabilityManager

Each Interpreter instance holds an `ObservabilityManager`:

```python
class ObservabilityManager:
    call_stack: CallStackTracker    # Call stack tracking
    tracer: ExecutionTracer         # Execution trace (ring buffer)
    llm_audit: LLMAuditLog          # LLM call audit log
    last_error: ErrorSnapshot | None  # Last error snapshot
```

### Integration Points

| Location | Behavior |
|----------|----------|
| `_call_function()` | Push/pop call stack frames, trace call/return |
| `_call_agent()` | Push/pop call stack frames, trace call/return |
| Exception handling | `capture_error()` generates ErrorSnapshot |
| `visit_llm_act_expr()` | Records LLMAuditEntry (including streaming tool_calls) |
| `visit_assert_stmt()` | Captures error context when condition is false |

### Zero-Overhead Design

- Call stack and execution tracing are disabled by default (`enabled=False`)
- Only `trace_on()` or `:trace on` enables them
- **Enabled by default in REPL**: `helen repl` automatically enables call stack and execution tracing for easier debugging
- LLM audit is enabled by default (crucial for prompt-first programs)
- Ring buffer limits memory: 10000 trace entries, 1000 LLM log entries, 100 call stack levels

### ErrorSnapshot Format

```json
{
  "error": {"type": "RuntimeError", "message": "...", "location": "..."},
  "call_stack": [{"function": "...", "location": "...", "args": {...}}],
  "scope": {"var_name": "value"},
  "trace": [{"type": "call", "function": "...", "location": "..."}],
  "timestamp": 1718812800.0
}
```

### assert Statement

```helen
assert condition, "optional message"
```

- Throws `AssertionError` (inherits from `HelenRuntimeError`) when condition is false
- Automatically captures structured error context
- Can be caught via `try-catch AssertionError`
