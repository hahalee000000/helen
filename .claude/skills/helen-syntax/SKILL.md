---
name: helen-syntax
description: "Helen 语言语法快速参考 — 关键字、类型、表达式、语句"
version: 1.14.0
author: Helen Team
license: MIT
tags: [helen, syntax, reference, language, chinese-punctuation, chinese-quotes]
---

# Helen 语法参考

## 关键字（89 个：44 英文 + 45 中文）

Helen 支持中英双语关键字，中文关键字与英文关键字映射到相同的 TokenType，可以自由混用。解析器和解释器无需任何改动。

### 中文关键字映射表

| 英文 | 中文 | 说明 |
|------|------|------|
| `let` | `设` / `定义` | 可变变量 |
| `const` | `常量` | 常量 |
| `shared` | `共享` | 跨 agent 可见变量 (v1.10) |
| `store` | `仓库` | 共享仓库声明 (v1.12) |
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
| `spawn` | `分生` | 启动并发 Agent (v1.18) |
| `prompt` | `提示词` | 系统提示 |
| `description` | `描述` | Agent 描述 |
| `model` | `模型` | 指定模型 |
| `tools` | `工具` | 可用工具 |
| `streaming` | `流式输出` | 启用流式 |
| `temperature` | `温度` | 温度参数 |
| `max-turns` | `最大轮次` | 最大轮次 |
| `functions` | `函数区` | 函数定义区 |
| `main` | `主函` | 入口 |
| `import` / `as` | `导入` / `作为` | 模块导入 |
| `protocol` / `impl` | `协议` / `实现` | 协议声明 |
| `branch` | `分支` | 分支 |
| `alias` | `别名` | 函数/变量别名 (v1.10) |

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
定义 结果 = 斐波那契(10)
常量 LIMIT = 100
如果 结果 < LIMIT {
    print("OK")
}

// v1.10: 共享变量
共享 let counter = 0
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
- `act` — 自主执行（调用 LLM，支持 `on_chunk`/`on_complete`/`on_tool_end` 回调）
- `if` — LLM 路由（分类分支）

### 控制流
- `if` / `else` — 条件分支
- `for` / `in` — 循环
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
- `shared let` / `shared const` — 跨 Agent 可见变量（v1.10）
- `fn` — 函数声明
- `import` — 模块导入
- `as` — 导入别名
- `alias` / `别名` — 函数/变量别名（v1.10）

### 预定义变量

| 变量 | 类型 | 说明 |
|------|------|------|
| `argv` | `const list<str>` | 命令行参数（`helen <file> [args...]` 后的所有参数） |

`argv` 是预定义的 `const`，由解释器在初始化时注入全局作用域。因为是 `const`，它在 agent 隔离作用域中自动可见（只读共享），且不可重新赋值。

```helen
// 命令行: helen tool.helen --verbose --output=json input.txt
print(argv)          // ["--verbose", "--output=json", "input.txt"]
print(len(argv))     // 3
print(argv[0])       // "--verbose"

// 也可用 get_cli_args() / parse_cli_args() 进行结构化解析
let config = parse_cli_args()
// {verbose: true, output: "json", _positional: ["input.txt"]}

// argv = []          // ❌ 语义错误: cannot assign to const variable
```

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
| `list` / `列表` | `[1, 2, 3]` | 列表 |
| `map` / `映射` | `{"key": "value"}` | 映射 |

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

### 中文全角操作符（v1.10）

Helen 支持中文全角标点符号作为 ASCII 操作符的等价替代，编程时无需切换中英文输入法：

| ASCII | 全角 | 说明 |
|-------|------|------|
| `(` `)` | `（` `）` | 圆括号 |
| `{` `}` | `｛` `｝` | 花括号 |
| `[` `]` | `［` `］` | 方括号 |
| `,` | `，` | 逗号 |
| `.` | `．` | 点号 |
| `:` | `：` | 冒号 |
| `;` | `；` | 分号 |
| `?` | `？` | 问号 |
| `+` | `＋` | 加号 |
| `-` | `－` | 减号 |
| `*` | `＊` | 乘号 |
| `/` | `／` | 除号 |
| `%` | `％` | 取模 |
| `!` | `！` | 逻辑非 / 不等 |
| `=` | `＝` | 赋值 / 相等 |
| `>` | `＞` | 大于 |
| `<` | `＜` | 小于 |
| `\|` | `｜` | 管道 |
| `!=` | `！＝` | 不等于 |
| `==` | `＝＝` | 等于 |
| `>=` | `＞＝` | 大于等于 |
| `<=` | `＜＝` | 小于等于 |
| `&&` | `＆＆` | 逻辑与 |
| `\|\|` | `｜｜` | 逻辑或 |
| `\|>` | `｜＞` | 管道操作符 |
| `->` | `－＞` | 箭头（返回类型） |
| `..` | `．．` | 范围 |

### 中文引号（v1.10）

Helen 支持中文引号作为字符串分隔符，与 ASCII `"..."` 等价：

| 引号 | Unicode | 类型 | 示例 |
|------|---------|------|------|
| `""` | U+201C / U+201D | 弯双引号 | `"你好世界"` |
| `''` | U+2018 / U+2019 | 弯单引号 | `'你好世界'` |
| `「」` | U+300C / U+300D | 直角引号 | `「你好世界」` |
| `『』` | U+300E / U+300F | 双直角引号 | `『你好世界』` |
| `＂` | U+FF02 | 全宽引号（对称） | `＂你好世界＂` |

中文引号支持转义序列（`\n`、`\t`、`\\` 等），未闭合会报错。多行字符串仍使用 ASCII `"""..."""`。

```helen
// 纯中文代码，全程中文输入法
设 x ＝ 10
常量 Y ＝ 20
函数 加（甲： int， 乙： int）： int ｛
    返回 甲 ＋ 乙
｝
如果 x ＞ 0 ｛
    设 结果 ＝ 加（x， Y）
｝ 否则 ｛
    设 结果 ＝ 0
｝

// 全角比较和逻辑
如果 a ＞＝ 0 ＆＆ a ＜＝ 100 ｛
    print（"在范围内"）
｝

// 全角管道
设 result ＝ 5 ｜＞ double
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

### 函数别名（v1.10）
```helen
// 给 stdlib 起自定义别名
alias len as 我的长度
alias print as 输出

// 给用户函数起别名
fn greet(name: str): str { return "Hello, " + name }
alias greet as 打招呼

// 中文关键字 `别名` 等价
别名 sort as 排序
```

Helen 的 stdlib 内置 230+ 个中文别名，启动时自动加载：

```helen
函数 数据处理() {
    定义 数据 = [3, 1, 4, 1, 5, 9]
    返回 长度(排序(去重(数据)))   // 长度=len, 排序=sort, 去重=unique
}
```

所有 locale 的别名表启动时全量加载，无论 locale 设置。`locale` 配置只影响 docs/LSP/错误消息的展示语言。

### Agent 声明
```helen
agent Translator {
    description "Translate text between languages"
    prompt "You are a professional translator."
    model "gpt-4"
    temperature 0.3
    tools = ["web_search"]
    
    main {
        return llm act "Translate: Hello"
    }
}

// tools = CONST_NAME — 复用工具集（静态可审计，安全边界清晰）
const FILE_TOOLS = ["read_file", "write_file", "path_exists"]
agent Builder {
    tools = FILE_TOOLS           // 引用模块级 const
    main { ... }
}

// 严格校验：
// ✅ 模块级 const 引用 + 字面量列表
// ❌ 可变变量、函数、agent、未定义标识符、重复声明、表达式拼接

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
// ✅ Agent 是一等公民，像函数一样调用
let result = Translator("Hello")
return MyAgent("test")
let x = some_fn(Translator("test"))

// ✅ 语句位置
MyAgent("test")
```

**重要**：Helen 中 Agent 是一等公民，可以像函数一样调用。不需要 `call` 关键字。

### Agent 作用域隔离（v1.10）

Agent `main {}` 运行在完全隔离的环境中（HLD 3.5.2），**不能**直接访问模块级的普通 `let` 变量。`helen check` 会在编译期检测并报 `SCOPE_VIOLATION` 错误。

**三种跨 Agent 数据共享方式**（按推荐顺序）：

#### 1. 闭包回调（最佳 — buffer 完全内部化）
```helen
agent Streamer {
    main {
        let buf = ""
        let cb = fn(chunk) {
            buf = buf + chunk   // ✅ 闭包捕获 agent 环境
        }
        llm act "..." on_chunk cb
    }
}
```

#### 2. shared let（显式跨 Agent）
```helen
shared let _buf = ""    // 或：共享 定义 _buf = ""
agent Worker {
    main {
        _buf = "new"    // ✅ 读写都允许
        let x = _buf    // ✅
    }
}
```

#### 3. const（只读共享配置）
```helen
const LIMIT = 100
agent Worker {
    main {
        let x = LIMIT   // ✅ const 自动只读共享
        LIMIT = 200     // ❌ 编译期错误：const is read-only
    }
}
```

**旧式规避方式**（仍可用）：通过 getter/setter 函数间接访问：
```helen
let _buf = ""
fn _buf_reset() { _buf = "" }
fn _buf_get(): str { return _buf }

agent MyAgent {
    main {
        _buf_reset()        // ✅ 通过函数
        let x = _buf_get()  // ✅ 通过函数
    }
}
```

模块级 `fn` 可以正常访问模块级 `let`，agent `main {}` 也可以调用模块级 `fn`——隔离边界只在变量直接访问。

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

# llm act 带流式回调
fn handle_chunk(chunk) {
    print(chunk, end="")
}

fn on_complete() {
    print("\n✅ 完成")
}

llm act "Write a story" on_chunk handle_chunk on_complete on_complete
```

### 异步并发（v1.18）
```helen
# spawn — 启动并发 Agent，返回 Channel
let ch = spawn Worker("task")

# Channel 方法
ch.send("message")      # 发送消息
let msg = ch.receive()  # 接收消息
let ok = ch.try_receive()  # 尝试接收（非阻塞）
ch.cancel()             # 取消
ch.close()              # 关闭

# mailbox_select — 多通道选择
let ready = mailbox_select([ch1, ch2, ch3])
```

### 异常处理
```helen
try {
    risky_operation()
} catch RuntimeError e {
    print("Runtime error: " + e.message)
} catch TimeoutError e {
    print("Timeout: " + e.message)
} finally {
    cleanup()
}

// Agent 调用失败 — AgentError (v1.10)
// 携带 agent_name、agent_args、cause 字段
try {
    let result = Contractor(req, dir)
} catch AgentError e {
    print("Agent failed: " + e.agent_name + " — " + e.message)
}
// AgentError 继承 LLMError，catch LLMError 也能捕获

// 捕获标准库异常 (v1.9+)
// 标准库函数抛出的 Python 异常自动包装为 RuntimeError
try {
    let x = len(42)        // Python TypeError
} catch RuntimeError e {
    print(e.message)       // "Python TypeError: object of type 'int' has no len()"
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

---

## v1.10 新特性

### 1. shared let — 跨 agent 可见变量

**v1.12 更新**: `shared let` 只允许值类型（int, float, str, bool）。

```helen
// 声明（v1.12: 只允许值类型）
shared let counter = 0
shared let SHARED_NAME = "default"
shared let rate = 3.14

// 中文
共享 let counter = 0

// 使用
agent Worker {
  main {
    counter += 1  // ✅ 可以访问和修改
  }
}

// ❌ v1.12 起禁止：引用类型不能放在 shared let 中
// shared let config = {"debug": true}  // 语义错误！
// shared let items = []               // 语义错误！
```

**作用域规则**:
- 模块级 `let` 在 agent main 中**不可见**（编译时错误）
- 模块级 `const` 自动可见（只读）
- `shared let` 显式声明跨 agent 可见的可变变量（v1.12: 只限值类型）

**引用类型共享**: 通过 agent 参数传递引用类型（v1.12 起参数自动只读）：

```helen
agent Worker(items: list) {
  main {
    // items 是只读视图
    let copy = list(items)  // 创建副本后可修改
    copy.append(4)
    return copy
  }
}
```

### 2. 子脚本/字段赋值

```helen
// 数组索引赋值
let arr = [1, 2, 3]
arr[0] = 10  // ✅ [10, 2, 3]

// 对象字段赋值
let obj = {"name": "Alice"}
obj.name = "Bob"  // ✅ {"name": "Bob"}
obj["age"] = 30   // ✅ {"name": "Bob", "age": 30}

// 嵌套
let matrix = [[1, 2], [3, 4]]
matrix[0][1] = 99  // ✅ [[1, 99], [3, 4]]
```

**错误**:
```helen
const arr = [1, 2, 3]
arr[0] = 10  // ❌ E0352 IMMUTABLE_ASSIGNMENT
```

### 3. 短路求值

```helen
// && 短路
let x = false && expensiveCall()  // expensiveCall() 不会执行

// || 短路
let y = true || expensiveCall()   // expensiveCall() 不会执行

// 安全访问
let user = getUser()
let name = user != null && user.getName()

// 默认值
let config = loadConfig() || defaultConfig()
```

**优先级**:
- `||` 优先级 3
- `&&` 优先级 4（高于 `||`）

### 4. 返回类型注解语法

```helen
// ✅ 新语法（仅支持）
fn add(a: int, b: int): int {
  return a + b
}

// ❌ 旧语法（已移除）
// fn add(a: int, b: int) -> int { ... }
```

### 5. 异步 HTTP 方法

```helen
// 单次异步
let result = await llm act_async Task "Task"

// 并发异步
let [r1, r2, r3] = await [
  llm act_async Task1 "First",
  llm act_async Task2 "Second",
  llm act_async Task3 "Third"
]

// 异步流式
let full_text = await llm act_stream_async WriteStory "A cat"
```

**性能**: 10 次并发提升 86%

### 6. 新增错误码

| 代码 | 名称 | 触发条件 |
|------|------|---------|
| E0350 | SCOPE_VIOLATION | 模块级 let 在 agent main 中不可见 |
| E0351 | SHARED_NOT_MODULE_LEVEL | shared let 不在模块级声明 |
| E0352 | IMMUTABLE_ASSIGNMENT | 子脚本/字段赋值目标不可变 |

---

## v1.12 新特性

### 1. Agent 隔离级别注解

使用 `@` 装饰器控制 agent 的隔离级别：

```helen
// L1: 标准隔离（默认）
agent Normal() {
  main { ... }
}

// L0: 开放隔离 — 可访问模块级 let
@open agent Debug() {
  main {
    // 可以访问模块级 let（用于调试）
    let data = moduleLevelLet
  }
}

// L2: 严格隔离 — 参数和返回值深拷贝
@strict agent Safe(data: list) {
  main {
    // data 是深拷贝，修改不影响调用者
    data.append(1)
    return data  // 返回值也是深拷贝
  }
}

// L3: 沙箱隔离 — 深拷贝 + 限制工具
@sandbox agent Untrusted(input: str) {
  tools []  // 只能用空工具列表
  main {
    return process(input)
  }
}

// 中文
@开放 agent 调试() { main { ... } }
@严格 agent 安全() { main { ... } }
@沙箱 agent 隔离() { main { ... } }
```

**隔离级别对比**:

| 级别 | 装饰器 | 参数 | 返回值 | 模块 let | 工具 |
|------|--------|------|--------|----------|------|
| L0 | `@open` | 共享引用 | 共享引用 | ✅ 可见 | 无限制 |
| L1 | 默认 | 只读视图 | 只读视图 | ❌ 不可见 | 无限制 |
| L2 | `@strict` | 深拷贝 | 深拷贝 | ❌ 不可见 | 无限制 |
| L3 | `@sandbox` | 深拷贝 | 深拷贝 | ❌ 不可见 | 限制为空 |

### 2. Shared Store — 结构化共享状态

`shared let` 只允许值类型。对于结构化的共享可变状态，使用 `shared store`：

```helen
// 声明 shared store
shared store Counter {
  // 私有字段
  count: int = 0
  
  // 公共方法
  fn increment() {
    count += 1
  }
  
  fn get(): int {
    return count
  }
  
  fn reset() {
    count = 0
  }
}

// 中文
共享 store 计数器 {
  数量: int = 0
  函数 增加() { 数量 += 1 }
  函数 获取(): int { 返回 数量 }
}

// 使用
agent Worker {
  main {
    Counter.increment()
    let val = Counter.get()
  }
}

// 多个 store 实例
shared store TaskQueue {
  items: list = []
  
  fn push(item) {
    items.append(item)
  }
  
  fn pop() {
    if len(items) > 0 {
      return items.remove(0)
    }
    return null
  }
  
  fn size(): int {
    return len(items)
  }
}
```

**store 规则**:
- 字段必须是值类型（int, float, str, bool）或引用类型（list, dict, struct）
- 方法内可以修改字段（字段不像 shared let 那样受限）
- 所有 agent 都可以访问 store 的方法
- store 是线程安全的（内部自动加锁）

**store vs shared let**:

| 特性 | shared let | shared store |
|------|-----------|--------------|
| 允许类型 | 仅值类型 | 值类型 + 引用类型 |
| 结构 | 单一变量 | 字段 + 方法 |
| 封装 | 无 | 方法封装字段 |
| 适用场景 | 计数器、标志位 | 队列、缓存、状态机 |

### 3. Channel 通道（v1.13）

Channel 是 agent 间通信的结构化方式，与 shared store 结构相同但语义不同：

```helen
// 声明
channel Counter {
  let count: int = 0
  fn increment() { count = count + 1 }
  fn get(): int { return count }
}

// 中文
通道 计数器 {
  定义 count: int = 0
  函数 increment() { count = count + 1 }
  函数 get(): int { 返回 count }
}

// 使用
Counter.increment()
let val = Counter.get()

// Agent 中访问
agent Worker() {
  main {
    Counter.increment()
    return Counter.get()
  }
}
```

**Channel vs Shared Store**:

| 特性 | Shared Store | Channel |
|------|-------------|---------|
| 声明 | `shared store Name { ... }` | `channel Name { ... }` |
| 中文 | `共享 仓库` | `通道` |
| 语义 | 共享可变状态 | Agent 间通信 |

---

**版本**: v1.14  
**最后更新**: 2026-07-05
