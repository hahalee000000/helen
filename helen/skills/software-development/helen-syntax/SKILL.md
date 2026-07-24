---
name: helen-syntax
description: "Helen language syntax quick reference — keywords, types, expressions, statements"
version: 1.16.0
author: Helen Team
license: MIT
tags: [helen, syntax, reference, language, chinese-punctuation, chinese-quotes]
---

# Helen Syntax Reference

## Keywords (89 total: 44 English + 45 Chinese)

Bilingual keywords map to the same TokenType and can be freely mixed. The parser/interpreter requires no changes.

### Keyword Mapping Table

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

### Chinese Identifiers

CJK Unified Ideographs (U+4E00–U+9FFF, etc.) can be used as identifier characters.

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

### Predefined Variables

| Variable | Type | Description |
|----------|------|-------------|
| `argv` | `const list<str>` | Command-line arguments (all arguments after `helen <file> [args...]`) |

`argv` is `const`, automatically visible (read-only) in agent isolated scope, and cannot be reassigned.

```helen
// Command line: helen tool.helen --verbose --output=json input.txt
print(argv)          // ["--verbose", "--output=json", "input.txt"]
print(len(argv))     // 3
let config = parse_cli_args()  // {verbose: true, output: "json", _positional: ["input.txt"]}
```

## Data Types

| Type | Examples | Description |
|------|----------|-------------|
| `int` | `42`, `-7` | Integer |
| `float` | `3.14`, `-0.5` | Floating-point number |
| `str` | `"hello"`, `'world'` | String |
| `bool` | `true`, `false` | Boolean |
| `null` | `null` | Null value |
| `list` / `列表` | `[1, 2, 3]` | List |
| `map` / `映射` | `{"key": "value"}` | Map |
| `str?` | `null`, `"x"` | Optional type |
| `int \| str` | `42`, `"x"` | Union type |

```helen
let name: str? = null           # Optional string
let value: int | str = "hello"  # Union type
```

## Expressions

### Arithmetic Operators
```helen
let sum = a + b      # Addition
let diff = a - b     # Subtraction
let prod = a * b     # Multiplication
let quot = a / b     # Division
let remainder = a % b # Modulo
let power = a ** b   # Exponentiation
```

### Comparison and Logical Operators
```helen
let eq = a == b       # Equal to
let ne = a != b       # Not equal to
let lt = a < b        # Less than
let le = a <= b       # Less than or equal to
let and = a && b      # Logical AND (short-circuit)
let or = a || b       # Logical OR (short-circuit)
let not = !a          # Logical NOT
```

### Member Access
```helen
let item = list[0]         # List index
let value = map["key"]     # Map lookup
let length = len(str)      # Function call
```

### Chinese Fullwidth Operators (v1.10)

Chinese fullwidth punctuation marks are equivalent alternatives to ASCII operators — no need to switch input methods:

| ASCII | Fullwidth | | ASCII | Fullwidth |
|-------|-----------|-|-------|-----------|
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

### Chinese Quotes (v1.10)

| Quote | Unicode | Example |
|-------|---------|---------|
| `""` | U+201C / U+201D | `"你好世界"` |
| `''` | U+2018 / U+2019 | `'你好世界'` |
| `「」` | U+300C / U+300D | `「你好世界」` |
| `『』` | U+300E / U+300F | `『你好世界』` |
| `＂` | U+FF02 | `＂你好世界＂` |

Escape sequences (`\n`, `\t`, `\\`, etc.) are supported; unclosed quotes raise an error. Multi-line strings still use ASCII `"""..."""`.

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

## Statements

### Variable Declarations
```helen
let x = 42                    # Mutable variable
const PI = 3.14159            # Constant
let name: str = "Helen"       # Type annotation
```

### Function Declarations
```helen
fn add(a: int, b: int): int {     # Return type uses : syntax (v1.10, -> removed)
    return a + b
}
fn greet(name: str) {
    print("Hello, " + name)
}
```

### Function Aliases (v1.10)
```helen
alias len as 我的长度          # stdlib alias
alias print as 输出
fn greet(name: str): str { return "Hello, " + name }
alias greet as 打招呼          # User function alias
别名 sort as 排序              # Chinese keyword equivalent
```

The stdlib includes 230+ built-in Chinese aliases, all loaded at startup (unaffected by `locale` configuration):
```helen
fn 数据处理() {
    let 数据 = [3, 1, 4, 1, 5, 9]
    return 长度(排序(去重(数据)))   # 长度=len, 排序=sort, 去重=unique
}
```

### Agent Declarations
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

// tools references module-level const (statically auditable, clear security boundary)
const FILE_TOOLS = ["read_file", "write_file", "path_exists"]
agent Builder {
    tools = FILE_TOOLS           # Module-level const reference
    main { ... }
}
// Prohibited: mutable variables, fn, agent, undefined identifiers, expression concatenation

// functions block supports variable definitions, accessible by internal fn
agent MyAgent {
    functions {
        let config = "default"
        const MAX_RETRIES = 3
        fn get_config(): str { return config }
    }
    main { print(get_config()) }
}

// Streaming agent (returns StreamingResponse)
agent Streamer(topic: str) {
    description "Stream a long response"
    streaming true
    prompt "Write a detailed essay about: {{topic}}"
}
```

Agents are first-class citizens — called like functions:
```helen
let result = Translator("Hello")
MyAgent("test")                # Statement position
let x = some_fn(Translator("test"))
```

### Agent Scope Isolation

Agent `main {}` runs in an isolated environment and **cannot** directly access module-level `let` (compile-time `SCOPE_VIOLATION` error).

**Scope rules**:
- Module-level `let` — **not visible** in agent main
- Module-level `const` — automatically visible (read-only)
- `shared let` — explicitly visible across agents (v1.12: value types only: int/float/str/bool)
- `shared store` — structured shared state (v1.12, supports reference types)

**Cross-Agent data sharing** (in recommended order):

```helen
// 1. Closure callbacks (best — buffer fully internalized)
agent Streamer {
    main {
        let buf = ""
        let cb = fn(chunk) { buf = buf + chunk }
        llm act "..." on_chunk cb
    }
}

// 2. shared let (explicit cross-agent, v1.12: value types only)
shared let counter = 0
agent Worker {
    main { counter += 1; let x = counter }
}

// 3. const (read-only shared configuration)
const LIMIT = 100
agent Worker {
    main { let x = LIMIT }  // Automatically shared read-only
}

// 4. Reference types passed via parameters (v1.12: parameters auto-wrapped in read-only view)
agent Worker(items: list) {
    main {
        let copy = list(items)  # Create a copy before modifying
        copy.append(4)
    }
}
```

Module-level `fn` can access module-level `let` normally, and agent main can call module-level `fn` — the isolation boundary only applies to direct variable access.

### Agent Isolation Levels (v1.12)

`@` decorators control agent isolation level:

```helen
agent Normal() { main { ... } }              # L1: Standard isolation (default)
@open agent Debug() { main { ... } }         # L0: Open — can access module-level let
@strict agent Safe(data: list) { main { ... } }  # L2: Strict — deep copy parameters/return values
@sandbox agent Untrusted(input: str) {       # L3: Sandbox — deep copy + restricted tools
    tools []
    main { return process(input) }
}
// Chinese: @开放、@严格、@沙箱
```

| Level | Decorator | Parameters/Returns | Module let | Tools |
|-------|-----------|-------------------|------------|-------|
| L0 | `@open` | Shared reference | ✅ Visible | Unrestricted |
| L1 | Default | Read-only view | ❌ Not visible | Unrestricted |
| L2 | `@strict` | Deep copy | ❌ Not visible | Unrestricted |
| L3 | `@sandbox` | Deep copy | ❌ Not visible | Restricted to empty |

### Shared Store (v1.12)

Structured shared mutable state (fields can be value or reference types, thread-safe):

```helen
shared store Counter {
    count: int = 0
    fn increment() { count += 1 }
    fn get(): int { return count }
    fn reset() { count = 0 }
}
// Chinese
共享 store 计数器 { 数量: int = 0; fn 增加() { 数量 += 1 } }

// Usage
agent Worker {
    main { Counter.increment(); let val = Counter.get() }
}
```

Store rules: fields can be value/reference types, methods can modify fields, all agents can access, thread-safe (internal RLock).
Fields with `_` prefix are private (inaccessible from agent code).

**shared let vs shared store**:

| | shared let | shared store |
|--|-----------|--------------|
| Type | Value types only | Value + reference types |
| Structure | Single variable | Fields + methods |
| Use case | Counters, flags | Queues, caches, state machines |

### Channel Message Queue (v1.18)

`spawn Agent(...)` launches a concurrent agent and returns a Channel (mailbox) for message passing:

```helen
let ch = spawn Worker("task")

// Channel methods
ch.send("message")            # Send message
let msg = ch.receive()        # Receive (blocking)
let ok = ch.try_receive()     # Try receive (non-blocking, returns null or message)
ch.cancel()                   # Cancel (can interrupt streaming)
ch.close()                    # Close

// Multi-channel select (first-ready wins)
let ready = mailbox_select([ch1, ch2, ch3])
// Chinese: 发送()、接收()、尝试接收()、取消()、关闭()
```

Spawned agents run in an isolated environment with a deep-copied snapshot of all variables. Inter-agent data sharing is done explicitly by passing SharedStore references through Channel messages.

> **Note**: The `channel Name { ... }` declaration syntax (equivalent to shared store) was removed in v1.18. In v1.18, Channel specifically refers to the message channel returned by spawn.

### LLM Statements
```helen
# llm act — autonomous execution (usable as expression since v1.10)
let result = llm act "What is 2+2?"

# llm if — routing classification
llm if input {
    case "positive" { print("Good!") }
    case "negative" { print("Bad!") }
    default { print("Neutral") }
}

# llm act with streaming callbacks
fn handle_chunk(chunk) { print(chunk, end="") }
fn done() { print("\n✅ Done") }
llm act "Write a story" on_chunk handle_chunk on_complete done

# v1.21: on_tool_end — inject hint after tool execution to guide LLM
fn after_tool(name, result) {
    if name == "read_file" { return "File read, please analyze the content" }
    return null  # No injection
}
llm act "Analyze the code" on_tool_end after_tool
```

### LLM Multimodal (v1.17)

Callbacks as adapters — protocol differences are handled by user callbacks, Helen core does not hardcode provider formats:

```helen
# media() — ordinary stdlib function, returns MediaPart object
let img = media("photo.jpg")
llm act "Describe this image" media(img)

# on_media — multimodal input adapter (MediaPart → provider format)
llm act "Analyze" media(img) on_media fn(parts, provider) {
    return [{"type": "image_url", "image_url": {"url": parts[0].source}}]
}

# on_generate — register generation capability as a tool (text-to-image/video, etc.)
llm act "Create" on_generate fn(params) {
    # params: {prompt, size, model, ...}
    return generate_image(params.prompt)
}

# provider — specify provider adapter
llm act "..." provider("claude")
```

`MediaPart` is a first-class data type (fields: `source`/`content`/`mime`/`media_type`/`metadata`), assignable, passable as argument, and storable in lists.
When `on_media` is not specified, the default OpenAI-compatible adapter is used. Chinese aliases: `媒体()`, `处理媒体 fn(...)`, `生成 fn(...)`.

### Exception Handling
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

// Agent call failure → AgentError (v1.10, carries agent_name/agent_args/cause)
try {
    let result = Contractor(req, dir)
} catch AgentError e {
    print("Agent failed: " + e.agent_name + " — " + e.message)
}
// AgentError inherits from LLMError; catching LLMError also catches it

// Stdlib Python exceptions are automatically wrapped as RuntimeError
try {
    let x = len(42)
} catch RuntimeError e {
    print(e.message)  # "Python TypeError: object of type 'int' has no len()"
}
```

### Assertions
```helen
assert x > 0
assert x > 0, "x must be positive"
try { assert false, "test" } catch AssertionError as e { print("Caught: " + e.message) }
```

### Pattern Matching
```helen
// Basic matching
match status {
    case 200 { print("OK") }
    case 404 { print("Not Found") }
    case 500 { print("Server Error") }
    default { print("Unknown") }
}

// Range matching (.. is inclusive)
match score {
    case 90..100 { print("A") }
    case 80..89 { print("B") }
    case 70..79 { print("C") }
    default { print("F") }
}

// Guard conditions
match x {
    case 1..100 if x == 42 { print("the answer") }
    case 1..100 { print("in range") }
    default { print("out of range") }
}

// Wildcards, variable binding, type patterns
match value {
    case 1 { print("one") }
    case n if n > 0 { print("positive: " + str(n)) }
    case is String s { print("string: " + s) }
    case _ { print("other") }
}
```

### Pipe Operator
```helen
let result = 5 |> double                          # Equivalent to double(5)
let result = "hello" |> upper |> strip            # Chained: strip(upper("hello"))
let len = [1, 2, 3] |> len                        # 3
let result = 10 |> add_one                        # Custom function
```

### Closures and Anonymous Functions
```helen
let add = fn(x, y) { return x + y }    # Anonymous function
print(add(1, 2))                        # 3

fn make_counter() {                     # Closure (lexical scope, value capture)
    let count = 0
    return fn() { count = count + 1; return count }
}
let counter = make_counter()
print(counter())  # 1
print(counter())  # 2
```

> Closures capture a deep copy of reference-type variables (snapshot semantics, immune to subsequent modifications).

### Protocols
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

### Imports
```helen
import "utils.helen"              # Import Helen module
import "config.json" as config    # Import JSON
import "data.yaml" as data        # Import YAML
import "./python_module" as py    # Import Python module
```

Multi-format imports (`.helen`/`.json`/`.yaml`/`.md`/`.txt`/Python), with circular dependency detection.

### Subscript/Field Assignment (v1.10)
```helen
let arr = [1, 2, 3]
arr[0] = 10                       # [10, 2, 3]
let obj = {"name": "Alice"}
obj.name = "Bob"                  # {"name": "Bob"}
obj["age"] = 30                   # {"name": "Bob", "age": 30}
let matrix = [[1, 2], [3, 4]]
matrix[0][1] = 99                 # Nested assignment

// const cannot be assigned
const c = [1, 2, 3]
c[0] = 10                         # E0352 IMMUTABLE_ASSIGNMENT
```

### Short-Circuit Evaluation (v1.10)
```helen
let x = false && expensiveCall()  # expensiveCall() not executed
let y = true || expensiveCall()   # expensiveCall() not executed
let name = user != null && user.getName()    # Safe access
let config = loadConfig() || defaultConfig() # Default value
```

Precedence: `||` has precedence 3, `&&` has precedence 4 (higher than `||`).

## Comments
```helen
# Single-line comment

"""
Multi-line comment
can span multiple lines
"""
```

## String Interpolation
```helen
let name = "World"
let greeting = "Hello, {{name}}!"  # Template variable substitution
```

## Error Codes (v1.10+)

| Code | Name | Trigger Condition |
|------|------|-------------------|
| E0350 | `SCOPE_VIOLATION` | Module-level let not visible in agent main |
| E0351 | `SHARED_NOT_MODULE_LEVEL` | shared let not declared at module level |
| E0352 | `IMMUTABLE_ASSIGNMENT` | Subscript/field assignment target is immutable |

---

**Version**: v1.16
**Last updated**: 2026-07-24

## Related Skills

- **helen-stdlib** — Standard library function reference
- **helen-agent-patterns** — Agent design patterns
- **helen-quality** — Code quality assessment
