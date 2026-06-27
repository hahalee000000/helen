---
name: helen-syntax
description: "Helen 语言语法快速参考 — 关键字、类型、表达式、语句"
version: 1.9.0
author: Helen Team
license: MIT
tags: [helen, syntax, reference, language]
---

# Helen 语法参考

## 关键字（89 个：45 英文 + 44 中文）

Helen 支持中英双语关键字，中文关键字与英文关键字映射到相同的 TokenType，可以自由混用。解析器和解释器无需任何改动。

### 中文关键字映射表

| 英文 | 中文 | 说明 |
|------|------|------|
| `let` | `让` | 可变变量 |
| `const` | `常量` | 常量 |
| `fn` | `函数` | 函数声明 |
| `return` | `返回` | 函数返回 |
| `if` / `else` | `如果` / `否则` | 条件分支 |
| `for` / `in` | `对于` / `属于` | 循环 |
| `while` | `当` | 条件循环 |
| `break` / `continue` | `中断` / `继续` | 循环控制 |
| `match` / `case` / `default` | `匹配` / `情况` / `默认` | 模式匹配 |
| `try` / `catch` / `finally` | `尝试` / `捕获` / `最终` | 异常处理 |
| `throw` | `抛出` | 抛出异常 |
| `assert` | `断言` | 运行时断言 |
| `true` / `false` | `真` / `假` | 布尔值 |
| `null` | `空` | 空值 |
| `is` | `是` | 类型判断 |
| `agent` | `智能体` | 声明 Agent |
| `llm` | `大模型` | LLM 操作 |
| `act` | `执行` | 自主执行 |
| `stream` | `流式执行` | 流式输出 |
| `async` / `await` | `异步` / `等待` | 异步执行 |
| `prompt` | `提示` | 系统提示 |
| `description` | `描述` | Agent 描述 |
| `model` | `模型` | 指定模型 |
| `tools` | `工具` | 可用工具 |
| `streaming` | `流式输出` | 启用流式 |
| `temperature` | `温度` | 温度参数 |
| `max-turns` | `最大轮次` | 最大轮次 |
| `functions` | `函数区` | 函数定义区 |
| `main` | `主` | 入口 |
| `import` / `as` | `导入` / `作为` | 模块导入 |
| `protocol` / `impl` | `协议` / `实现` | 协议声明 |
| `call` | `调用` | 调用 |
| `branch` | `分支` | 分支 |

中文标识符（变量名、函数名）也完全支持，CJK 统一表意文字（U+4E00–U+9FFF 等）均可作为标识符字符。

```helen
// 纯中文
函数 斐波那契(n: int): int {
    如果 n <= 1 {
        返回 n
    } 否则 {
        返回 斐波那契(n - 1) + 斐波那契(n - 2)
    }
}

// 中英混合
让 结果 = 斐波那契(10)
const LIMIT = 100
如果 结果 < LIMIT {
    print("OK")
}
```

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
fn add(a: int, b: int): int {
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

// Agent functions 块支持变量定义
agent MyAgent {
    description "Example agent"
    prompt "..."
    
    functions {
        let config = "default"
        const MAX_RETRIES = 3
        
        fn get_config(): str {
            return config  // 可以访问 functions 块变量
        }
    }
    
    main {
        print(get_config())
    }
}

// 流式 Agent（返回 StreamingResponse，可用 for await 迭代）
agent Streamer(topic: str) {
    description "Stream a long response"
    streaming true
    prompt "Write a detailed essay about: {{topic}}"
}
```

### Agent 调用
```helen
// ✅ 正确：函数式调用（Agent 是一等公民）
let result = Translator("Hello")
return MyAgent("test")
let x = some_fn(Translator("test"))

// ❌ 错误：使用 call 关键字（表达式位置）
let result = call Translator("Hello")  // 解析错误：Expected expression, got CALL

// ✅ 语句位置：两种方式都可以
call MyAgent("test")  // 可以，但不推荐
MyAgent("test")       // 推荐，更简洁
```

**重要**：Helen 中 Agent 是一等公民，可以像函数一样调用。`call` 关键字在表达式位置（赋值、参数、返回值）会导致解析错误，仅用于语句位置（不接收返回值时）。

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
llm stream "Write a poem"

# llm stream 带回调
fn handle_chunk(chunk) {
    print(chunk, end="")
}

fn on_complete() {
    print("\n✅ 完成")
}

llm stream "Write a story" on_chunk handle_chunk on_complete on_complete
```

### 异步语句
```helen
# 异步表达式（延迟执行）
let task = async fetch_data()

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
// 基本匹配
match status {
    case 200 { print("OK") }
    case 404 { print("Not Found") }
    case 500 { print("Server Error") }
    default { print("Unknown") }
}

// 范围匹配（.. 运算符，包含边界）
let score = 85
match score {
    case 90..100 { print("A") }
    case 80..89 { print("B") }
    case 70..79 { print("C") }
    default { print("F") }
}

// 守卫条件（if 表达式）
match x {
    case 1..100 if x == 42 { print("the answer") }
    case 1..100 { print("in range") }
    default { print("out of range") }
}

// v1.8: 通配符模式（可作为默认分支）
match value {
    case 1 { print("one") }
    case _ { print("other") }  // 匹配任何值
}

// v1.8: 变量绑定
match value {
    case n if n > 0 { print("positive: " + str(n)) }
    case n if n < 0 { print("negative: " + str(n)) }
    case _ { print("zero") }
}

// v1.8: 类型模式
match value {
    case is String { print("it's a string") }
    case is Int { print("it's an int") }
    case _ { print("unknown type") }
}

// v1.8: 类型模式带绑定
match value {
    case is String s { print("string: " + s) }
    case _ { print("not a string") }
}
```

### 管道操作符（v1.8）
```helen
// 基本用法
let result = 5 |> double  // 等价于 double(5)

// 链式调用
let result = "hello" |> upper |> strip  // 等价于 strip(upper("hello"))

// 与内置函数
let len = [1, 2, 3] |> len  // 3

// 与自定义函数
fn add_one(x) { return x + 1 }
let result = 10 |> add_one  // 11
```

### 闭包与匿名函数（v1.7）
```helen
// 匿名函数
let add = fn(x, y) { return x + y }
print(add(1, 2))  // 3

// 闭包（词法作用域）
fn make_counter() {
    let count = 0
    return fn() {
        count = count + 1
        return count
    }
}

let counter = make_counter()
print(counter())  // 1
print(counter())  // 2
```

### 协议（v1.7）
```helen
// 协议声明
protocol Printable {
    fn to_string(self): String
}

// 协议实现（鸭子类型）
struct Point {
    x: Int
    y: Int
}

impl Printable for Point {
    fn to_string(self): String {
        return "Point(" + str(self.x) + ", " + str(self.y) + ")"
    }
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
