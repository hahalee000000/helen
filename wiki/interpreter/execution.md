# 执行引擎 (Interpreter)

> 模块 M5 | `helen/interpreter/interpreter.py` + `environment.py` | 测试: `tests/execution/`

---

## 概述

Interpreter 是 AST 的第二个 visitor，负责**执行 Helen 程序**。

```python
class Interpreter(Visitor[object]):
    """每个 visit 方法返回节点的计算值，或控制流 Sentinel。"""
```

---

## Environment 作用域链

```python
class Environment:
    def __init__(self, parent: Environment | None = None)
    def lookup(self, name: str) -> Any       # 查找变量（逐层向上）
    def assign(self, name: str, value: Any)  # 修改变量（必须已存在）
    def define(self, name: str, value: Any)  # 声明新变量
    def enter_scope(self) -> Environment     # 创建子作用域
```

### 查找规则

```
env_A (x=1, y=2)
  └── env_B (z=3)
        lookup("z") → 3 (当前层)
        lookup("x") → 1 (父层)
        lookup("w") → NameError (不存在)
```

### Agent 调用隔离

每次 `call Agent()` 创建**完全独立的根 Environment**：

```python
def _call_agent(self, node: AgentDeclNode, args: dict) -> object:
    isolated_env = Environment()  # 无 parent，完全隔离
    # ... 在 isolated_env 中执行 Agent 逻辑
```

---

## 语句执行

### 变量声明

```helen
let x = 42           # mutable=True, 可重新赋值
const PI = 3.14      # mutable=False, 重新赋值 → E0346
```

### 控制流

| 语句 | 实现机制 |
|---|---|
| `if/else` | 条件求值 → `_truthy()` → 执行对应分支 |
| `for x in list` | 遍历列表 → 每个元素绑定到 x → 执行循环体 |
| `while cond` | 条件求值 → `_truthy()` → 循环执行 |
| `break` | 抛出 `BreakSentinel` → 被循环捕获 |
| `continue` | 抛出 `ContinueSentinel` → 被循环捕获 |

### `_truthy()` 规则

```python
def _truthy(value: object) -> bool:
    None     → False
    False    → False
    0, 0.0   → False
    ""       → False
    [] {}    → False
    其他     → True
```

### 模式匹配

```helen
match x {
    case 1: print("one")
    case 2: print("two")
    default: print("other")
}
```

- 按顺序匹配 `case` 字面值
- 必须有 `default`（语义分析阶段检查）

### 异常处理

```helen
// 抛出异常
throw RuntimeError("something went wrong")
throw LLMError  // 使用默认消息

// 捕获异常
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

- `throw` 语句抛出预定义异常类型的实例
- 类型匹配的 catch 优先执行（支持继承：catch LLMError 也捕获 TimeoutError）
- catch-all 必须最后
- finally 始终执行

**预定义异常层次**：
```
AnyError (根)
├── LLMError
│   ├── TimeoutError
│   └── ModelError
├── ToolError
└── RuntimeError
```

---

## 表达式求值

### 二元运算

```python
def visit_binary_op(self, node: BinaryOpNode) -> object:
    left = node.left.accept(self)
    right = node.right.accept(self)
    op = node.operator.type

    if op == TokenType.PLUS:
        return self._add(left, right)  # 数字加法 或 字符串连接
    if op == TokenType.EQUAL_EQUAL:
        return self._equal(left, right)
    # ...
```

### `_add()` 支持字符串连接

```helen
let greeting = "Hello, " + "World"   # → "Hello, World"
let result = "Score: " + 42          # → "Score: 42" (自动转字符串)
```

### 函数调用

```helen
fn add(a, b) { return a + b }
let result = add(1, 2)   # → 3
```

- 查找函数名 → 创建新作用域 → 绑定参数 → 执行函数体

---

## _stringify()

将 Helen 值转换为字符串表示：

```python
None      → "null"
True      → "true"
False     → "false"
3.0       → "3"     (整数无小数点)
3.14      → "3.14"
[1, 2]    → "[1, 2]"
{"a": 1}  → "{a: 1}"
```

---

## 控制流 Sentinel 机制

```python
class BreakSentinel(Exception): pass
class ContinueSentinel(Exception): pass
class ReturnSentinel(Exception):
    def __init__(self, value: Any):
        self.value = value
```

循环和函数通过 `try/except` 捕获 Sentinel：

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

## AI 原生可观测性

> 模块 `helen/runtime/observability.py`

Interpreter 集成了 AI 原生可观测性系统，为 AI Agent 提供结构化的调试上下文。

### ObservabilityManager

每个 Interpreter 实例持有一个 `ObservabilityManager`：

```python
class ObservabilityManager:
    call_stack: CallStackTracker    # 调用栈追踪
    tracer: ExecutionTracer         # 执行追踪（环形缓冲区）
    llm_audit: LLMAuditLog          # LLM 调用审计日志
    last_error: ErrorSnapshot | None  # 上次错误快照
```

### 集成点

| 位置 | 行为 |
|------|------|
| `_call_function()` | push/pop 调用栈帧，trace call/return |
| `_call_agent()` | push/pop 调用栈帧，trace call/return |
| 异常处理 | `capture_error()` 生成 ErrorSnapshot |
| `visit_llm_act_expr()` | 记录 LLMAuditEntry |
| `visit_llm_stream_stmt()` | 记录 LLMAuditEntry（含 tool_calls） |
| `visit_assert_stmt()` | 条件为 false 时捕获错误上下文 |

### 零开销设计

- 调用栈和执行追踪默认关闭（`enabled=False`）
- 只有 `trace_on()` 或 `:trace on` 才启用
- **REPL 中默认开启**：`helen repl` 自动启用调用栈和执行追踪，便于调试
- LLM 审计默认开启（对 prompt-first 程序至关重要）
- 环形缓冲区限制内存：追踪 10000 条，LLM 日志 1000 条，调用栈 100 层

### ErrorSnapshot 格式

```json
{
  "error": {"type": "RuntimeError", "message": "...", "location": "..."},
  "call_stack": [{"function": "...", "location": "...", "args": {...}}],
  "scope": {"var_name": "value"},
  "trace": [{"type": "call", "function": "...", "location": "..."}],
  "timestamp": 1718812800.0
}
```

### assert 语句

```helen
assert condition, "optional message"
```

- 条件为 false 时抛出 `AssertionError`（继承 `HelenRuntimeError`）
- 自动捕获结构化错误上下文
- 可通过 `try-catch AssertionError` 捕获
