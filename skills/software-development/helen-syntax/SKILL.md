---
name: helen-syntax
description: "Helen 语言语法快速参考 — 关键字、类型、表达式、语句"
version: 1.0.0
author: Helen Team
license: MIT
tags: [helen, syntax, reference, language]
---

# Helen 语法参考

## 关键字（44 个）

### Agent 声明
- `agent` — 声明 Agent
- `description` — Agent 描述
- `prompt` — Agent 系统提示
- `model` — 指定 LLM 模型
- `temperature` — 温度参数
- `max-turns` — 最大工具调用轮次
- `tools` — 可用工具列表
- `streaming` — 启用流式响应（`streaming true`）

### LLM 语句
- `llm` — LLM 操作关键字
- `act` — 自主执行（调用 LLM）
- `if` — LLM 路由（分类分支）
- `stream` — 流式输出
- `async` — 异步执行
- `await` — 等待异步任务完成

### 控制流
- `if` / `else` — 条件分支
- `for` / `in` — 循环
- `for await` / `in` — 异步流式迭代
- `while` — 条件循环
- `break` / `continue` — 循环控制
- `match` / `case` / `default` — 模式匹配
- `return` — 函数返回
- `throw` — 抛出异常
- `try` / `catch` / `finally` — 异常处理
- `assert` — 运行时断言（条件为 false 时抛出 AssertionError）

### 变量与函数
- `let` — 可变变量
- `const` — 常量
- `fn` — 函数声明
- `import` — 模块导入
- `as` — 导入别名

### 字面量
- `true` / `false` — 布尔值
- `null` — 空值

## 数据类型

| 类型 | 示例 | 说明 |
|------|------|------|
| `int` | `42`, `-7` | 整数 |
| `float` | `3.14`, `-0.5` | 浮点数 |
| `str` | `"hello"`, `'world'` | 字符串 |
| `bool` | `true`, `false` | 布尔值 |
| `null` | `null` | 空值 |
| `list` | `[1, 2, 3]` | 列表 |
| `map` | `{"key": "value"}` | 映射 |

### 可选类型与联合类型
```helen
let name: str? = null           # 可选字符串
let value: int | str = "hello"  # 联合类型
```

## 表达式

### 算术运算
```helen
let sum = a + b
let diff = a - b
let prod = a * b
let quot = a / b
let remainder = a % b
let power = a ** b
```

### 比较运算
```helen
let eq = a == b
let ne = a != b
let lt = a < b
let le = a <= b
```

### 逻辑运算
```helen
let and = a && b
let or = a || b
let not = !a
```

### 成员访问
```helen
let item = list[0]
let value = map["key"]
let length = len(str)
```

## 语句

### 变量声明
```helen
let x = 42                    # 可变变量
const PI = 3.14159            # 常量
let name: str = "Helen"       # 类型注解
```

### 函数声明
```helen
fn add(a: int, b: int) -> int {
    return a + b
}

fn greet(name: str) {
    print("Hello, " + name)
}
```

### Agent 声明
```helen
agent Translator {
    description "Translate text between languages"
    prompt "You are a professional translator."
    model "gpt-4"
    temperature 0.3
    tools ["web_search"]
    
    main {
        return llm act "Translate: Hello"
    }
}

// 流式 Agent（返回 StreamingResponse，可用 for await 迭代）
agent Streamer(topic: str) {
    description "Stream a long response"
    streaming true
    prompt "Write a detailed essay about: {{topic}}"
}
```

### LLM 语句
```helen
# llm act — 自主执行
let result = llm act "What is 2+2?"

# llm if — 路由分类
llm if input {
    case "positive" { print("Good!") }
    case "negative" { print("Bad!") }
    default { print("Neutral") }
}

# llm stream — 流式输出
llm stream "Write a poem" {
    on_chunk(chunk) {
        print(chunk, end="")
    }
}
```

### 异步语句
```helen
# 异步表达式（延迟执行）
let task = async call fetch_data()

# 等待单个
let result = await task

# 等待多个（并发）
let results = await [task1, task2, task3]

# 流式迭代（for await）
agent Streamer(topic: str) {
    streaming true
    prompt "Write about: {{topic}}"
}

main {
    let response = async Streamer("coding")
    for await chunk in response {
        stream_print(chunk)
    }
}
```

### 异常处理
```helen
try {
    risky_operation()
} catch ValueError as e {
    print("Invalid value: " + e.message)
} catch NetworkError as e {
    print("Network failed: " + e.message)
} finally {
    cleanup()
}
```

### 断言
```helen
# 简单断言
assert x > 0

# 带消息的断言
assert x > 0, "x must be positive"

# 可捕获
try {
    assert false, "test"
} catch AssertionError as e {
    print("Caught: " + e.message)
}
```

### 模式匹配
```helen
match status {
    case 200 { print("OK") }
    case 404 { print("Not Found") }
    case 500 { print("Server Error") }
    default { print("Unknown") }
}
```

### 导入
```helen
import "utils.helen"              # 导入 Helen 模块
import "config.json" as config    # 导入 JSON
import "data.yaml" as data        # 导入 YAML
import "./python_module" as py    # 导入 Python 模块
```

## 注释
```helen
# 单行注释

"""
多行注释
可以跨行
"""
```

## 字符串插值
```helen
let name = "World"
let greeting = "Hello, {{name}}!"  # 模板变量替换
```
