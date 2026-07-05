# 执行引擎 (Interpreter)

> 模块 M5 | `helen/interpreter/interpreter.py` + `environment.py` | 测试: `tests/execution/`

---

## 概述

Interpreter 是 AST 的第二个 visitor，负责**执行 Helen 程序**。

```python
class Interpreter(Visitor[object]):
    """每个 visit 方法返回节点的计算值，或控制流 Sentinel。"""
```

### 构造函数

```python
def __init__(self, errors=None, llm_runtime=None,
             import_resolver=None, program_args=None)
```

`program_args` 参数接收 CLI 传入的参数列表（来自 `helen <file> [args...]`），被定义为全局 Environment 中的预定义 `const argv`。

### 预定义变量

| 变量 | 类型 | 说明 |
|------|------|------|
| `argv` | `const list<str>` | 命令行参数（`helen <file>` 后的所有参数） |

`argv` 在 Interpreter 初始化时通过 `environment.define("argv", program_args, is_const=True)` 注入全局作用域。因为是 `const`，它会自动通过 `_call_agent()` 的 const 注入机制传播到 agent 隔离作用域中。

语义分析器在 `_register_stdlib()` 中将 `argv` 注册为 `kind="const"` 的符号，因此程序中使用 `argv` 不会触发 `UNDECLARED_VARIABLE` 错误。重新赋值 `argv` 会在语义分析阶段报 "cannot assign to const variable" 错误。

```helen
// 命令行: helen tool.helen --verbose --output=json
print(argv)          // ["--verbose", "--output=json"]
print(len(argv))     // 2
print(argv[0])       // "--verbose"

// argv = []          // ❌ 语义错误: cannot assign to const variable
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

### v1.10 Agent Main 作用域隔离

`agent main {}` 在完全隔离的环境中执行，模块级 `let` 不可见：

```python
def visit_agent_main(self, node: MainBlockNode):
    # 创建新的根环境（无 parent）
    main_env = Environment()
    
    # 只导入模块级 const（只读）
    for name, symbol in self.global_env.constants.items():
        main_env.define(name, symbol.value)
    
    # 导入 shared let（可读写）
    for name, symbol in self.global_env.shared_vars.items():
        main_env.define(name, symbol)
    
    # 注意：模块级 let 不会被导入
    
    # 在 main_env 中执行 main 块
    for stmt in node.statements:
        stmt.accept(self, env=main_env)
```

**示例**:

```helen
let moduleVar = "模块级"      // ❌ main 中不可见
const MODULE_CONST = "常量"   // ✅ 只读可见
shared let sharedVar = 0      // ✅ 可读写

agent MyAgent {
  main {
    // moduleVar              // ❌ NameError
    let x = MODULE_CONST      // ✅ "常量"
    sharedVar += 1            // ✅ 1
  }
}
```

### v1.10 模块函数作用域解析

导入模块的函数调用时，使用模块级 `Environment` 作为父作用域，确保能访问模块自身的 `const` 和 `shared let`：

```python
def _create_module_object(self, result):
    module = { "__type__": "module", ... }
    # 创建模块级 Environment，parent 为调用方环境（可访问 stdlib）
    module_env = Environment(parent=self.environment)
    for name, data in self.import_resolver.data.items():
        if isinstance(data, VarDeclNode) and (not data.mutable or data.shared):
            value = data.initializer.accept(self)
            module_env.define(name, value, is_const=not data.mutable)
    module["__env__"] = module_env
    return module

def _call_function(self, func, args, parent_env=None):
    # 模块函数传入 parent_env = module["__env__"]
    if parent_env is not None:
        call_env = Environment(parent=parent_env)  # 模块作用域
    else:
        call_env = self.environment.enter_scope()  # 普通调用
    # ... 绑定参数、执行函数体
```

**作用域链**：

```
函数局部作用域
    └─ 模块 Environment（const + shared let）
        └─ 调用方全局 Environment（stdlib + 其他全局变量）
```

### v1.10 子脚本/字段赋值执行

赋值语句现在支持索引和字段访问：

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

**示例**:

```helen
let arr = [1, 2, 3]
arr[0] = 10  // ✅ arr 变为 [10, 2, 3]

let obj = { name: "Alice", age: 30 }
obj.name = "Bob"  // ✅ obj 变为 {name: "Bob", age: 30}
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

### v1.10 短路求值

`&&` 和 `||` 运算符支持短路求值，避免不必要的计算：

```python
def visit_binary_op(self, node: BinaryOpNode) -> object:
    op = node.operator.type
    
    # && 短路求值
    if op == TokenType.AND:
        left = node.left.accept(self)
        if not self._truthy(left):
            return False  # 短路：不计算 right
        right = node.right.accept(self)
        return self._truthy(right)
    
    # || 短路求值
    if op == TokenType.OR:
        left = node.left.accept(self)
        if self._truthy(left):
            return True  # 短路：不计算 right
        right = node.right.accept(self)
        return self._truthy(right)
    
    # 其他运算符正常求值
    left = node.left.accept(self)
    right = node.right.accept(self)
    # ...
```

**示例**:

```helen
// && 短路
let x = false && expensiveCall()  // expensiveCall() 不会执行
let y = true && expensiveCall()   // expensiveCall() 会执行

// || 短路
let a = true || expensiveCall()   // expensiveCall() 不会执行
let b = false || expensiveCall()  // expensiveCall() 会执行

// 实际应用
let user = get_user() || create_default_user()
let valid = user != null && user.is_active()
```

**优先级**:
- `||` 优先级 3（左结合）
- `&&` 优先级 4（左结合）
- `&&` 优先级高于 `||`

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
| `visit_llm_act_expr()` | 记录 LLMAuditEntry（含流式 tool_calls） |
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
