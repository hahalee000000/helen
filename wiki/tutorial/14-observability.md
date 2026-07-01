# 教程 14: AI 原生可观测性

> 给 AI 一个它能读懂的"黑匣子"，而不是给人类一个 GDB。

---

## 为什么需要 AI 原生可观测性？

传统调试器（断点、单步执行、变量监视）是为**人类交互式调试**设计的。在 AI 编程场景下，消费调试信息的是 AI Agent，它需要的是**结构化的、可机器消费的上下文**——而不是交互式暂停/恢复。

| 传统 Debugger | Helen 可观测性 |
|--------------|---------------|
| 断点暂停 | 结构化错误快照 (JSON) |
| 单步执行 | 执行追踪日志 |
| 变量监视 | 调用栈 + 作用域变量 |
| 调用栈面板 | 程序化调用栈追踪 |
| 无 LLM 记录 | LLM 调用审计日志 |

## assert 语句

### 基本语法

```helen
assert x > 0
assert x > 0, "x must be positive"
```

### 断言失败

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

### 与可观测性集成

断言失败时自动捕获结构化错误上下文（JSON 格式），包含调用栈 + 作用域变量。

## debug() 函数

```helen
main {
    let x = 42
    debug("variable value", x)
    // 输出: [DEBUG] variable value {"value": 42}
}
```

| 特性 | `print()` | `debug()` |
|------|-----------|-----------|
| 输出目标 | stdout | stderr |
| 格式 | 纯文本 | JSON 结构化 |
| 用途 | 程序正常输出 | 开发调试 |

## 执行追踪

### REPL 命令

```
:trace on          # 开启执行追踪
:trace off         # 关闭执行追踪
:trace show [n]    # 显示最近 n 条追踪记录
```

### 程序化追踪

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

## 结构化错误上下文

```
:last_error        # 显示上次错误的完整上下文（人类可读格式）
:last_error -v     # 详细模式，包含执行追踪
```

REPL 中 `:last_error` 显示人类可读的文本格式，包含：
- 错误类型和消息
- 发生时间
- 调用栈（函数名、位置）
- 作用域变量

使用 `-v` 参数会额外显示执行追踪（execution trace）。

AI Agent 可通过编程方式获取 JSON 格式：`snapshot.to_json()`

> **注意**：REPL 中调用栈追踪和执行追踪默认开启，无需手动 `:trace on`。

## LLM 调用审计日志

```
:llm_log [n]       # 显示最近 n 次 LLM 调用（紧凑模式）
:llm_log [n] -v    # 详细模式，显示完整审计信息
```

每次记录：timestamp、call_type、agent_name、model、prompt、response、tokens_in/out、duration_ms、tool_calls、error。

紧凑模式显示一行摘要（含模型名称和工具调用数），详细模式显示所有字段。

## 架构

```
helen/runtime/observability.py
├── CallStackTracker       # 调用栈追踪
├── ExecutionTracer        # 执行追踪（环形缓冲区）
├── ErrorSnapshot          # 结构化错误上下文
├── LLMAuditLog            # LLM 审计日志
└── ObservabilityManager   # 统一管理器
```

### 零开销设计

- 追踪默认关闭（REPL 中默认开启）
- LLM 审计默认开启
- 环形缓冲区限制内存

## 练习

1. 使用 `assert` 验证输入参数
2. 在 REPL 中用 `:trace on` 追踪执行路径
3. 使用 `debug()` 输出中间结果
4. 用 `:last_error` 查看错误上下文
5. 用 `:llm_log` 查看 LLM 调用审计
