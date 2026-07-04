# 异常层次

> 模块 M5 | `helen/interpreter/exceptions.py` | 测试: `tests/execution/test_exceptions.py`

---

## 异常继承树

```
Exception
├── HelenRuntimeError           # 运行时错误基类
│   ├── LLMError                 # LLM 相关错误基类
│   │   ├── TimeoutError          # LLM 超时 (HLD 3.6.4)
│   │   ├── ModelError            # LLM 模型错误
│   │   └── AgentError            # Agent 调用失败（携带 agent_name/agent_args/cause）
│   ├── ToolError                # 工具调用错误
│   ├── RuntimeError             # 通用运行时错误
│   └── AssertionError           # assert 语句失败 (Phase 10)
└── AnyError                     # 异常基类（catch-all）
```

---

## 控制流 Sentinel

```python
class BreakSentinel(Exception): pass
class ContinueSentinel(Exception): pass

class ReturnSentinel(Exception):
    def __init__(self, value: Any):
        self.value = value
```

这些不是错误，而是**控制流信号**，通过异常机制传递。

---

## 编译期错误

```python
class ConstAssignmentError(HelenRuntimeError):
    """常量被重新赋值。"""

class AgentRuntimeError(HelenRuntimeError):
    """Agent 运行时错误。"""
```

---

## AggregateError

```python
class AggregateError(Exception):
    """并发调用中多个 Task 失败。"""
    def __init__(self, errors: list[tuple[int, Exception]]):
        self.errors = errors  # [(index, exception), ...]

    def __str__(self):
        parts = [f"Task {i}: {e}" for i, e in self.errors]
        return "AggregateError: " + "; ".join(parts)
```

---

## error_matches()

用于 catch 类型匹配：

```python
def error_matches(exc: Exception, type_name: str) -> bool:
    """检查异常是否匹配 catch 类型名。"""
    if type_name == "AnyError":
        return True
    exc_class = type(exc).__name__
    return exc_class == type_name
```

---

## 使用示例

```helen
// assert 语句 (Phase 10)
assert x > 0, "x must be positive"

try {
    assert false, "test assertion"
} catch AssertionError(err) {
    print("Assertion failed: " + err.message)
}

// try-catch
try {
    call RiskyAgent()
} catch TimeoutError(err) {
    print("Operation timed out")
} catch ModelError(err) {
    print("Model error: " + str(err))
} catch {
    // catch-all: 处理其他任何错误
    print("Unknown error")
} finally {
    cleanup()
}
```

### 捕获标准库异常 (v1.9+)

标准库函数抛出的 Python 异常（如 `TypeError`、`ValueError`、`FileNotFoundError` 等）会被自动包装为 `RuntimeError`，消息格式为 `"Python <类型名>: <原始消息>"`：

```helen
try {
    let x = len(42)        // Python TypeError: object of type 'int' has no len()
} catch RuntimeError err {
    print(err.message)     // "Python TypeError: object of type 'int' has no len()"
}

try {
    let data = read_file("/nonexistent/path")  // Python FileNotFoundError
} catch RuntimeError err {
    // 通过 err.message 中的 "Python FileNotFoundError" 前缀区分异常类型
    print("File error: " + err.message)
}
```

**注意**：标准库异常统一包装为 `RuntimeError`，可通过 `err.message` 中的 `Python <类型名>` 前缀区分具体类型。已存在的 Helen 异常（如 `TimeoutError`）保持原有类型不变。

---

## 错误码与异常映射

| ErrorCode | 对应异常 | 触发场景 |
|---|---|---|
| E0334 AGENT_RUNTIME_ERROR | AgentRuntimeError | Agent 执行失败 |
| E0342 INVALID_CATCH_TYPE | — | catch 类型非预定义 |
| E0343 CATCH_ALL_NOT_LAST | — | catch-all 不在最后 |
| E0346 CONST_ASSIGNMENT | ConstAssignmentError | 常量重新赋值 |

---

## v1.10 异常增强

### RuntimeError 包装 stdlib 异常

v1.10 增强了异常处理，将 Python 标准库异常包装为 Helen 的 `RuntimeError`，使得在 Helen 代码中可以统一处理所有异常。

#### 包装机制

```python
def _wrap_python_exception(self, exc: Exception) -> RuntimeError:
    """将 Python stdlib 异常包装为 Helen RuntimeError"""
    return RuntimeError(
        message=f"{type(exc).__name__}: {str(exc)}",
        original_exception=exc
    )
```

#### 示例

```helen
// Python stdlib 异常被包装为 RuntimeError
try {
  let result = int("not a number")  // Python ValueError
} catch RuntimeError as e {
  print("Error: " + e.message)
  // 输出: "Error: ValueError: invalid literal for int() with base 10: 'not a number'"
}

// 文件操作异常
try {
  let content = read_file("/nonexistent/file.txt")  // Python FileNotFoundError
} catch RuntimeError as e {
  print("File error: " + e.message)
  // 输出: "File error: FileNotFoundError: [Errno 2] No such file or directory..."
}

// 网络请求异常
try {
  let response = http_get("https://invalid-url.example")  // Python ConnectionError
} catch RuntimeError as e {
  print("Network error: " + e.message)
}
```

#### 异常层次更新

```
Exception
├── HelenRuntimeError           # 运行时错误基类
│   ├── TimeoutError             # LLM 超时
│   ├── ModelError               # LLM 模型错误
│   ├── ToolError                # 工具调用错误
│   ├── RuntimeError             # 通用运行时错误（v1.10: 包装 stdlib 异常）
│   ├── AssertionError           # assert 语句失败
│   └── ScopeViolationError      # v1.10: 作用域违规（新增）
└── AnyError                     # 异常基类（catch-all）
```

### v1.10 新增异常

#### ScopeViolationError

当 agent main 访问不可见的模块级 let 时抛出：

```python
class ScopeViolationError(HelenRuntimeError):
    """Agent main 试图访问不可见的模块级变量"""
    def __init__(self, var_name: str, agent_name: str):
        self.var_name = var_name
        self.agent_name = agent_name
        super().__init__(
            f"Module-level let '{var_name}' is not visible in agent '{agent_name}' main. "
            f"Use 'shared let' to make it accessible."
        )
```

**示例**:

```helen
let moduleVar = "模块级"

agent MyAgent {
  main {
    // 在语义分析阶段就会报错（E0350）
    // 如果绕过语义分析，运行时抛出 ScopeViolationError
    print(moduleVar)  // ❌ ScopeViolationError
  }
}

// ✅ 修正
shared let moduleVar = "模块级"

agent MyAgent {
  main {
    print(moduleVar)  // ✅ 可以访问
  }
}
```

### 异常处理最佳实践

#### 1. 捕获具体异常

```helen
// ❌ 过于宽泛
try {
  risky_operation()
} catch {
  print("Something went wrong")
}

// ✅ 具体异常
try {
  risky_operation()
} catch TimeoutError as e {
  print("Timeout: " + e.message)
} catch RuntimeError as e {
  print("Runtime error: " + e.message)
} catch {
  print("Unknown error")
}
```

#### 1.5. Agent 调用失败 — AgentError

Agent 调用失败时抛出 `AgentError`，携带 agent 名称、调用参数和原始异常：

```python
class AgentError(LLMError):
    """Agent 调用失败 — 包装底层异常，携带 agent 上下文。"""
    agent_name: str      # 失败的 agent 名称
    agent_args: dict     # 调用时传入的参数
    cause: Exception     # 底层异常
```

**继承 `LLMError`**：`catch LLMError` 能同时捕获 LLM 直调和 agent 调用的失败。

```helen
agent Contractor(req: str, dir: str) {
    main {
        // 如果 LLM 调用失败，或内部逻辑抛出异常，
        // 都会被包装为 AgentError 抛给调用方
        ...
    }
}

main {
    try {
        let result = Contractor("build auth module", "/tmp/project")
        // 这里 result 一定是成功值
    } catch AgentError err {
        // err.message    — "Agent 'Contractor' failed: ..."
        // err.agent_name — "Contractor"
        // err.agent_args — {"req": "build auth module", "dir": "/tmp/project"}
        // err.cause      — 底层异常
        error("契约设计失败: " + err.message)
    }
}
```

**嵌套 agent 调用**：如果 agent A 调用 agent B，B 失败抛出的 `AgentError` 会被 A 透传（不双层包装），保留最内层的完整上下文。

```helen
try {
    Planner("design system")   // 内部调用 Contractor 失败
} catch AgentError err {
    // err.agent_name 是失败的最内层 agent 名称
    print(err.agent_name + " failed: " + err.message)
}
```

#### 2. 处理 stdlib 异常

```helen
try {
  let num = int(user_input)
} catch RuntimeError as e {
  // 检查是否是 ValueError
  if "ValueError" in e.message {
    print("Invalid number format")
  } else {
    print("Other error: " + e.message)
  }
}
```

#### 3. 重新抛出异常

```helen
fn process_data(data: str) {
  try {
    let parsed = json_parse(data)
    validate(parsed)
  } catch RuntimeError as e {
    // 添加上下文信息
    throw RuntimeError("Failed to process data: " + e.message)
  }
}
```

### 错误消息改进

v1.10 改进了错误消息，包含更多信息：

```helen
try {
  let result = 1 / 0
} catch RuntimeError as e {
  print(e.message)
  // 输出: "ZeroDivisionError: division by zero"
  // 包含原始 Python 异常类型和消息
}
```

---

**最后更新**: 2026-07-01  
**版本**: v1.10
