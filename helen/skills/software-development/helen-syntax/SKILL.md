---
name: helen-syntax
description: "Helen 语言语法快速参考 — 关键字、类型、表达式、语句"
version: 1.16.0
author: Helen Team
license: MIT
tags: [helen, syntax, reference, language, chinese-punctuation, chinese-quotes]
---

# Helen 语法参考

## 关键字（89 个：44 英文 + 45 中文）

中英双语关键字映射到相同 TokenType，可自由混用，解析器/解释器无需改动。

### 关键字映射表

| 英文 | 中文 | 说明 |
|------|------|------|
| `let` | `设` / `定义` | 可变变量 |
| `const` | `常量` | 常量 |
| `shared` | `共享` | 跨 agent 可见 (v1.10) |
| `store` | `仓库` | 共享仓库声明 (v1.12) |
| `fn` | `函数` | 函数声明 |
| `return` | `返回` | 函数返回 |
| `if` / `else` | `如果` / `否则` | 条件分支 / match 分支 |
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
| `agent` | `智能体` | Agent 声明 |
| `llm` | `大模型` | LLM 操作关键字 |
| `act` | `执行` | 自主执行（支持 `on_chunk`/`on_complete`/`on_tool_end` 回调） |
| `spawn` | `分生` | 启动并发 Agent，返回 Channel (v1.18) |
| `prompt` | `提示词` | Agent 系统提示 |
| `description` | `描述` | Agent 描述 |
| `model` | `模型` | 指定模型 |
| `tools` | `工具` | 可用工具列表 |
| `streaming` | `流式输出` | 启用流式 |
| `temperature` | `温度` | 温度参数 |
| `max-turns` | `最大轮次` | 最大工具调用轮次 |
| `functions` | `函数区` | Agent 内函数定义区 |
| `main` | `主函` | 入口块 |
| `import` / `as` | `导入` / `作为` | 模块导入 |
| `protocol` / `impl` | `协议` / `实现` | 协议声明 |
| `branch` | `分支` | 分支 |
| `alias` | `别名` | 函数/变量别名 (v1.10) |

### 中文标识符

CJK 统一表意文字（U+4E00–U+9FFF 等）均可作为标识符字符。

```helen
// 纯中文
函数 斐波那契(n: int): int {
    如果 n <= 1 { 返回 n }
    否则 { 返回 斐波那契(n - 1) + 斐波那契(n - 2) }
}
定义 结果 = 斐波那契(10)
常量 LIMIT = 100
如果 结果 < LIMIT { 打印("OK") }

// v1.10: 共享变量
共享 定义 counter = 0
```

### 预定义变量

| 变量 | 类型 | 说明 |
|------|------|------|
| `argv` | `const list<str>` | 命令行参数（`helen <file> [args...]` 后的所有参数） |

`argv` 是 `const`，agent 隔离作用域中自动可见（只读），不可重新赋值。

```helen
// 命令行: helen tool.helen --verbose --output=json input.txt
print(argv)          // ["--verbose", "--output=json", "input.txt"]
print(len(argv))     // 3
let config = parse_cli_args()  // {verbose: true, output: "json", _positional: ["input.txt"]}
```

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
| `str?` | `null`, `"x"` | 可选类型 |
| `int \| str` | `42`, `"x"` | 联合类型 |

```helen
let name: str? = null           # 可选字符串
let value: int | str = "hello"  # 联合类型
```

## 表达式

### 算术运算
```helen
let sum = a + b      # 加
let diff = a - b     # 减
let prod = a * b     # 乘
let quot = a / b     # 除
let remainder = a % b # 取模
let power = a ** b   # 幂
```

### 比较与逻辑运算
```helen
let eq = a == b       # 等于
let ne = a != b       # 不等于
let lt = a < b        # 小于
let le = a <= b       # 小于等于
let and = a && b      # 逻辑与（短路）
let or = a || b       # 逻辑或（短路）
let not = !a          # 逻辑非
```

### 成员访问
```helen
let item = list[0]         # 列表索引
let value = map["key"]     # 映射取值
let length = len(str)      # 函数调用
```

### 中文全角操作符（v1.10）

中文全角标点是 ASCII 操作符的等价替代，无需切换中英文输入法：

| ASCII | 全角 | | ASCII | 全角 |
|-------|------|-|-------|------|
| `()` | `（）` | | `+` | `＋` |
| `{}` | `｛｝` | | `-` | `－` |
| `[]` | `［］` | | `*` | `＊` |
| `,` | `，` | | `/` | `／` |
| `.` | `．` | | `%` | `％` |
| `:` | `：` | | `!` | `！` |
| `;` | `；` | | `=` | `＝` |
| `?` | `？` | | `>` | `＞` |
| | | | `<` | `＜` |
| `!=` | `！＝` | | `\|` | `｜` |
| `==` | `＝＝` | | `\|>` | `｜＞` |
| `>=` | `＞＝` | | `->` | `－＞` |
| `<=` | `＜＝` | | `..` | `．．` |
| `&&` | `＆＆` | | `\|\|` | `｜｜` |

### 中文引号（v1.10）

| 引号 | Unicode | 示例 |
|------|---------|------|
| `""` | U+201C / U+201D | `"你好世界"` |
| `''` | U+2018 / U+2019 | `'你好世界'` |
| `「」` | U+300C / U+300D | `「你好世界」` |
| `『』` | U+300E / U+300F | `『你好世界』` |
| `＂` | U+FF02 | `＂你好世界＂` |

支持转义序列（`\n`、`\t`、`\\` 等），未闭合报错。多行字符串仍用 ASCII `"""..."""`。

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
如果 a ＞＝ 0 ＆＆ a ＜＝ 100 ｛ 打印（"在范围内"） ｝
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
fn add(a: int, b: int): int {     # 返回类型用 : 语法（v1.10，-> 已移除）
    return a + b
}
fn greet(name: str) {
    print("Hello, " + name)
}
```

### 函数别名（v1.10）
```helen
alias len as 我的长度          # stdlib 别名
alias print as 输出
fn greet(name: str): str { return "Hello, " + name }
alias greet as 打招呼          # 用户函数别名
别名 sort as 排序              # 中文关键字等价
```

stdlib 内置 230+ 中文别名，启动时全量加载（不受 `locale` 配置影响）：
```helen
fn 数据处理() {
    let 数据 = [3, 1, 4, 1, 5, 9]
    return 长度(排序(去重(数据)))   # 长度=len, 排序=sort, 去重=unique
}
```

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

// tools 引用模块级 const（静态可审计，安全边界清晰）
const FILE_TOOLS = ["read_file", "write_file", "path_exists"]
agent Builder {
    tools = FILE_TOOLS           # ✅ 模块级 const 引用
    main { ... }
}
// ❌ 禁止：可变变量、fn、agent、未定义标识符、表达式拼接

// functions 块支持变量定义，可被内部 fn 访问
agent MyAgent {
    functions {
        let config = "default"
        const MAX_RETRIES = 3
        fn get_config(): str { return config }
    }
    main { print(get_config()) }
}

// 流式 Agent（return StreamingResponse）
agent Streamer(topic: str) {
    description "Stream a long response"
    streaming true
    prompt "Write a detailed essay about: {{topic}}"
}
```

Agent 是一等公民，像函数一样调用：
```helen
let result = Translator("Hello")
MyAgent("test")                # 语句位置
let x = some_fn(Translator("test"))
```

### Agent 作用域隔离

Agent `main {}` 运行在隔离环境中，**不能**直接访问模块级 `let`（编译期报 `SCOPE_VIOLATION`）。

**作用域规则**：
- 模块级 `let` — agent main 中**不可见**
- 模块级 `const` — 自动可见（只读）
- `shared let` — 显式跨 agent 可见（v1.12: 仅值类型 int/float/str/bool）
- `shared store` — 结构化共享状态（v1.12，支持引用类型）

**跨 Agent 数据共享**（按推荐顺序）：

```helen
// 1. 闭包回调（最佳 — buffer 完全内部化）
agent Streamer {
    main {
        let buf = ""
        let cb = fn(chunk) { buf = buf + chunk }
        llm act "..." on_chunk cb
    }
}

// 2. shared let（显式跨 Agent，v1.12: 仅值类型）
shared let counter = 0
agent Worker {
    main { counter += 1; let x = counter }
}

// 3. const（只读共享配置）
const LIMIT = 100
agent Worker {
    main { let x = LIMIT }  // ✅ 自动只读共享
}

// 4. 引用类型通过参数传递（v1.12: 参数自动只读视图）
agent Worker(items: list) {
    main {
        let copy = list(items)  # 创建副本后可修改
        copy.append(4)
    }
}
```

模块级 `fn` 可正常访问模块级 `let`，agent main 也可调用模块级 `fn`——隔离边界只在变量直接访问。

### Agent 隔离级别（v1.12）

`@` 装饰器控制 agent 隔离级别：

```helen
agent Normal() { main { ... } }              # L1: 标准隔离（默认）
@open agent Debug() { main { ... } }         # L0: 开放 — 可访问模块级 let
@strict agent Safe(data: list) { main { ... } }  # L2: 严格 — 参数/返回值深拷贝
@sandbox agent Untrusted(input: str) {       # L3: 沙箱 — 深拷贝 + 限制工具
    tools []
    main { return process(input) }
}
// 中文: @开放、@严格、@沙箱
```

| 级别 | 装饰器 | 参数/返回值 | 模块 let | 工具 |
|------|--------|-------------|----------|------|
| L0 | `@open` | 共享引用 | ✅ 可见 | 无限制 |
| L1 | 默认 | 只读视图 | ❌ 不可见 | 无限制 |
| L2 | `@strict` | 深拷贝 | ❌ 不可见 | 无限制 |
| L3 | `@sandbox` | 深拷贝 | ❌ 不可见 | 限制为空 |

### Shared Store（v1.12）

结构化共享可变状态（字段可为值类型或引用类型，线程安全）：

```helen
shared store Counter {
    count: int = 0
    fn increment() { count += 1 }
    fn get(): int { return count }
    fn reset() { count = 0 }
}
// 中文
共享 store 计数器 { 数量: int = 0; fn 增加() { 数量 += 1 } }

// 使用
agent Worker {
    main { Counter.increment(); let val = Counter.get() }
}
```

store 规则：字段可为值/引用类型，方法可修改字段，所有 agent 可访问，线程安全（内部 RLock）。
`_` 前缀字段为私有（agent 代码不可访问）。

**shared let vs shared store**：

| | shared let | shared store |
|--|-----------|--------------|
| 类型 | 仅值类型 | 值 + 引用类型 |
| 结构 | 单一变量 | 字段 + 方法 |
| 适用 | 计数器、标志位 | 队列、缓存、状态机 |

### Channel 消息队列（v1.18）

`spawn Agent(...)` 启动并发 agent 并返回 Channel（mailbox），用于消息传递：

```helen
let ch = spawn Worker("task")

// Channel 方法
ch.send("message")            # 发送消息
let msg = ch.receive()        # 接收（阻塞）
let ok = ch.try_receive()     # 尝试接收（非阻塞，返回 null 或消息）
ch.cancel()                   # 取消（可中断 streaming）
ch.close()                    # 关闭

// 多通道选择（首个就绪者胜出）
let ready = mailbox_select([ch1, ch2, ch3])
// 中文: 发送()、接收()、尝试接收()、取消()、关闭()
```

spawn 的 agent 运行在隔离环境中，拥有所有变量的深拷贝快照。agent 间数据共享通过 Channel 消息显式传递 SharedStore 引用。

> **注意**：v1.18 之前 `channel Name { ... }` 声明语法（等价于 shared store）已移除。v1.18 Channel 专指 spawn 返回的消息通道。

### LLM 语句
```helen
# llm act — 自主执行（可用作表达式，v1.10 起）
let result = llm act "What is 2+2?"

# llm if — 路由分类
llm if input {
    case "positive" { print("Good!") }
    case "negative" { print("Bad!") }
    default { print("Neutral") }
}

# llm act 带流式回调
fn handle_chunk(chunk) { print(chunk, end="") }
fn done() { print("\n✅ 完成") }
llm act "Write a story" on_chunk handle_chunk on_complete done

# v1.21: on_tool_end — 工具执行后注入 hint 引导 LLM
fn after_tool(name, result) {
    if name == "read_file" { return "文件已读取，请分析内容" }
    return null  # 不注入
}
llm act "分析代码" on_tool_end after_tool
```

### LLM 多模态（v1.17）

回调即适配器——协议差异由用户回调处理，Helen 核心不固化 provider 格式：

```helen
# media() — 普通 stdlib 函数，返回 MediaPart 对象
let img = media("photo.jpg")
llm act "描述这张图片" media(img)

# on_media — 多模态输入适配器（MediaPart → provider 格式）
llm act "分析" media(img) on_media fn(parts, provider) {
    return [{"type": "image_url", "image_url": {"url": parts[0].source}}]
}

# on_generate — 将生成能力注册为工具（文生图/视频等）
llm act "创作" on_generate fn(params) {
    # params: {prompt, size, model, ...}
    return generate_image(params.prompt)
}

# provider — 指定 provider 适配器
llm act "..." provider("claude")
```

`MediaPart` 是一等数据类型（字段: `source`/`content`/`mime`/`media_type`/`metadata`），可赋值、传参、存入列表。
不指定 `on_media` 时使用默认 OpenAI 兼容适配器。中文别名: `媒体()`、`处理媒体 fn(...)`、`生成 fn(...)`。

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

// Agent 调用失败 → AgentError（v1.10，携带 agent_name/agent_args/cause）
try {
    let result = Contractor(req, dir)
} catch AgentError e {
    print("Agent failed: " + e.agent_name + " — " + e.message)
}
// AgentError 继承 LLMError，catch LLMError 也能捕获

// 标准库 Python 异常自动包装为 RuntimeError
try {
    let x = len(42)
} catch RuntimeError e {
    print(e.message)  # "Python TypeError: object of type 'int' has no len()"
}
```

### 断言
```helen
assert x > 0
assert x > 0, "x must be positive"
try { assert false, "test" } catch AssertionError as e { print("Caught: " + e.message) }
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

// 范围匹配（.. 包含边界）
match score {
    case 90..100 { print("A") }
    case 80..89 { print("B") }
    case 70..79 { print("C") }
    default { print("F") }
}

// 守卫条件
match x {
    case 1..100 if x == 42 { print("the answer") }
    case 1..100 { print("in range") }
    default { print("out of range") }
}

// 通配符、变量绑定、类型模式
match value {
    case 1 { print("one") }
    case n if n > 0 { print("positive: " + str(n)) }
    case is String s { print("string: " + s) }
    case _ { print("other") }
}
```

### 管道操作符
```helen
let result = 5 |> double                          # 等价于 double(5)
let result = "hello" |> upper |> strip            # 链式: strip(upper("hello"))
let len = [1, 2, 3] |> len                        # 3
let result = 10 |> add_one                        # 自定义函数
```

### 闭包与匿名函数
```helen
let add = fn(x, y) { return x + y }    # 匿名函数
print(add(1, 2))                        # 3

fn make_counter() {                     # 闭包（词法作用域，值捕获）
    let count = 0
    return fn() { count = count + 1; return count }
}
let counter = make_counter()
print(counter())  # 1
print(counter())  # 2
```

> 闭包捕获引用类型变量的深拷贝（快照语义，不受后续修改影响）。

### 协议
```helen
protocol Printable {
    fn to_string(self): String
}
struct Point { x: Int; y: Int }
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

多格式导入（`.helen`/`.json`/`.yaml`/`.md`/`.txt`/Python），支持循环检测。

### 子脚本/字段赋值（v1.10）
```helen
let arr = [1, 2, 3]
arr[0] = 10                       # ✅ [10, 2, 3]
let obj = {"name": "Alice"}
obj.name = "Bob"                  # ✅ {"name": "Bob"}
obj["age"] = 30                   # ✅ {"name": "Bob", "age": 30}
let matrix = [[1, 2], [3, 4]]
matrix[0][1] = 99                 # ✅ 嵌套赋值

// const 不可赋值
const c = [1, 2, 3]
c[0] = 10                         # ❌ E0352 IMMUTABLE_ASSIGNMENT
```

### 短路求值（v1.10）
```helen
let x = false && expensiveCall()  # expensiveCall() 不执行
let y = true || expensiveCall()   # expensiveCall() 不执行
let name = user != null && user.getName()    # 安全访问
let config = loadConfig() || defaultConfig() # 默认值
```

优先级：`||` 优先级 3，`&&` 优先级 4（高于 `||`）。

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

## 错误码（v1.10+）

| 代码 | 名称 | 触发条件 |
|------|------|---------|
| E0350 | `SCOPE_VIOLATION` | 模块级 let 在 agent main 中不可见 |
| E0351 | `SHARED_NOT_MODULE_LEVEL` | shared let 不在模块级声明 |
| E0352 | `IMMUTABLE_ASSIGNMENT` | 子脚本/字段赋值目标不可变 |

---

**版本**: v1.16
**最后更新**: 2026-07-24

## 相关技能

- **helen-stdlib** — 标准库函数参考
- **helen-agent-patterns** — Agent 设计模式
- **helen-quality** — 代码质量评估
