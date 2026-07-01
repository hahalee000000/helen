# 异常层次

> 模块 M5 | `helen/interpreter/exceptions.py` | 测试: `tests/execution/test_exceptions.py`

---

## 异常继承树

```
Exception
├── HelenRuntimeError           # 运行时错误基类
│   ├── TimeoutError             # LLM 超时 (HLD 3.6.4)
│   ├── ModelError               # LLM 模型错误
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
