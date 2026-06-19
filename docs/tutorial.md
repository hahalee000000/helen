# Helen 语言完整教程

> **Helen** — A Prompt-first Agent Programming Language
> 版本: v1.5 | 状态: Phase 0-9 全部实现 + 安全沙箱 + CI/CD | 测试: 1805 passed

---

<!-- TABLE OF CONTENTS -->

| 章节 | 主题 |
|------|------|
| [01](#教程-01-入门指南) | 安装、配置、Hello World、REPL、代码验证、文档生成 |
| [02](#教程-02-变量与类型) | let/const、数据类型、类型注解、运算、集合操作 |
| [03](#教程-03-函数) | fn 声明、参数、返回值、递归、Agent 内部函数、作用域 |
| [04](#教程-04-控制流) | if/for/while/match、break/continue、try-catch |
| [05](#教程-05-agent-编程) | agent 声明、配置、参数、调用 |
| [06](#教程-06-llm-语句) | llm act/if/stream、对话历史、流式输出 |
| [07](#教程-07-异步编程) | async、await、并发 Agent 调用 |
| [08](#教程-08-模块与导入) | import、多格式、跨文件复用、路径安全 |
| [09](#教程-09-python-ffi) | Python 库导入、类型转换、调用 Python 函数 |
| [10](#教程-10-标准库参考) | 185 个内置函数，覆盖 AI 应用开发所有核心需求 |
| [11](#教程-11-构建多-agent-系统) | 完整案例：智能客服系统 |
| [12](#教程-12-安全沙箱) | 路径验证、URL 过滤、命令安全、资源限制 |

---

# 教程 01: 入门指南

> 安装 Helen、配置环境、编写第一个程序、使用 REPL

## 系统要求

- **Python 3.7+**（推荐 3.9+）
- 操作系统：Linux、macOS、Windows

## 安装

```bash
# 克隆仓库
git clone https://github.com/hahalee000000/helen.git
cd helen

# 安装
pip install -e .

# 验证
$ helen --help
Usage: helen {run, check, repl, doc, init}
```

## 初始化配置

Helen 使用独立的配置目录 `~/.helen/`，不依赖 Hermes 安装：

```bash
$ helen init
Helen home: /home/user/.helen
Skills directory: /home/user/.helen/skills
Config created: /home/user/.helen/config.yaml

Next steps:
  1. Edit /home/user/.helen/config.yaml
  2. Set your API key
  3. Run a Helen program: helen <file.helen>
```

### 目录结构

```
~/.helen/
├── config.yaml    # LLM API 配置
└── skills/        # Helen 原生 skill 目录
```

### 配置文件

编辑 `~/.helen/config.yaml`：

```yaml
# Helen configuration

llm:
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  api_key: "your-api-key-here"
  model: "qwen3.7-plus"
  temperature: 0.7
  timeout: 60
```

也支持 `.env` 格式 (`~/.helen/.env`)：

```bash
HELEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
HELEN_API_KEY=your-api-key-here
HELEN_MODEL=qwen3.7-plus
```

### 配置加载优先级

配置从多个源加载，后面的覆盖前面的：

| 优先级 | 文件 | 说明 |
|--------|------|------|
| 1（最低） | `~/.hermes/.env` | Hermes 兼容回退 |
| 2 | `~/.helen/.env` | Helen .env 格式 |
| 3 | `~/.helen/config.yml` | Helen YAML |
| 4（最高） | `~/.helen/config.yaml` | Helen YAML |

### Skill 目录优先级

| 优先级 | 目录 | 说明 |
|--------|------|------|
| 1（最高） | `~/.helen/skills/` | Helen 原生 skill |
| 2 | `~/.hermes/skills/` | Hermes 回退 |
| 3 | `~/.hermes/hermes-agent/skills/` | Hermes agent skill |

## Hello, World!

创建 `hello.helen`:

```helen
main {
    print("Hello, World!")
}
```

运行:

```bash
$ helen run hello.helen
Hello, World!
```

## 代码验证

在不执行的情况下检查语法和语义:

```bash
$ helen check hello.helen
✓ hello.helen: OK
```

如果有错误:

```bash
$ helen check broken.helen
Error: [E0311] at broken.helen:2:9
  2 | let x = y
    |         ^
Undefined variable 'y'

Code: E0311 — UNDEFINED_VARIABLE

1 error found.
```

## 使用 REPL

```bash
$ helen repl
helen> print("Hello!")
Hello!
helen> let x = 42
helen> x
42
helen> let y = x * 2
helen> y
84
helen>
```

### 多行输入

当括号或引号未闭合时，REPL 自动等待更多输入:

```
helen> for i in [1, 2, 3] {
...     print(i)
... }
1
2
3
```

### 退出 REPL

按 `Ctrl+D` 或输入 `exit`。

### REPL 命令

REPL 支持以下管理命令（以 `:` 开头）：

| 命令 | 说明 |
|------|------|
| `:help` | 显示可用命令 |
| `:list` | 列出已定义的函数和 agent |
| `:undefine <name>` | 删除指定的函数或 agent |
| `:reset` | 清除所有定义（函数、agent），保留标准库 |
| `:ask <question>` | 向 Helen 语言助手提问 |

```bash
helen> fn add(a, b) { return a + b; }
helen> :list
Functions: add
Agents:    (none)
helen> add(1, 2)
3
helen> :undefine add
Removed 'add'.
helen> :list
Functions: (none)
Agents:    (none)
```

### Helen 语言助手

REPL 内置了 AI 语言助手（位于 `helen/agent/helen_assistant.helen`），可以回答关于 Helen 语言的问题、帮助编写代码、调试程序。

助手会加载：
- **Helen 文档**（`docs/tutorial.md`）— 语法、语义、示例
- **Helen 源码**（`helen/` 目录）— parser、interpreter、AST、lexer

这意味着助手不仅能回答语法问题，还能解释实现细节和内部机制。

使用 `:ask` 命令向助手提问：

```bash
helen> :ask How do I define an agent in Helen?

🤔 Thinking...

# Defining an Agent in Helen

An `agent` is a first-class language construct in Helen. Here's the basic structure:

## Basic Syntax

```helen
agent AgentName {
    description "What this agent does"
    prompt "Your system prompt here..."
}
```

## With Parameters

```helen
agent Translator(text: str, target: str) {
    description "Translate text"
    prompt "Translate to {{target}}: {{text}}"
}
```

## Calling an Agent

Agents are called like functions:

```helen
main {
    let result = Translator("Hello", "French")
    print(result)
}
```
```

助手会加载 Helen 文档并生成详细的回答，包括代码示例和语法说明。

**流式输出**：助手使用 `llm stream` 流式输出回答，内容逐 chunk 实时显示，无需等待完整响应。

**助手能力：**
- ✅ 解释 Helen 语法和语义
- ✅ 提供代码示例
- ✅ 帮助调试错误
- ✅ 回答关于 agent、function、LLM 集成的问题

### 函数重定义

如果函数定义时出现语义错误（如引用未定义变量），符号表会自动清理，允许修复后重新定义：

```bash
helen> fn greet(name) { return x; }
Error: undeclared variable 'x'
helen> fn greet(name) { return "Hello, " + name; }   // ✅ 可以直接重新定义
helen> greet("Helen")
"Hello, Helen"
```

如果函数已正确定义，再次定义会报重复错误，需先用 `:undefine` 删除：

```bash
helen> fn add(a, b) { return a + b; }
helen> fn add(a, b) { return a + b + 1; }
Error: duplicate declaration of 'add'
helen> :undefine add
Removed 'add'.
helen> fn add(a, b) { return a + b + 1; }   // ✅ 现在可以重新定义
```

## 生成文档

```bash
$ helen doc hello.helen
# Helen Program Documentation

## Agents

(No agents defined)

## Functions

(No functions defined)

## Built-in Functions
- print(*args) → str — 打印值
- len(value) → int — 长度
...
```

JSON 输出:

```bash
$ helen doc hello.helen --format json
{"agents": [], "functions": [], "builtins": [...]}
```

## 练习

1. 创建一个打印你名字的 Helen 程序
2. 在 REPL 中计算 `1 + 2 * 3`
3. 故意写一个有语法错误的程序，观察错误输出

---

# 教程 02: 变量与类型

> let / const / 类型注解 / 基本运算

## 变量声明

### `let` — 可变变量

```helen
let x = 42
x = 100       // ✅ 可以修改
print(x)      // 100
```

### `const` — 不可变常量

```helen
const PI = 3.14159
PI = 3        // ❌ E0346 CONST_ASSIGNMENT
```

## 数据类型

### 基本类型

```helen
let number = 42         // int
let float_num = 3.14    // float
let text = "hello"      // str
let flag = true         // bool
let nothing = null      // null
```

### 集合类型

```helen
let numbers = [1, 2, 3]                     // list<int>
let mixed = [1, "two", true]                // list<any>
let person = {"name": "Alice", "age": 30}   // map<str, any>
```

## 类型注解

```helen
let name: str = "Alice"
let age: int = 30
let score: float = 95.5
let active: bool = true
```

### 可选类型

```helen
let email: str? = null      // 可以为空
email = "alice@example.com" // ✅
email = null                // ✅

let name: str = null        // ❌ str 不接受 null
```

### 联合类型

```helen
let id: int | str = 42      // 可以是 int 或 str
id = "ABC-123"              // ✅
id = true                   // ❌
```

## 运算

### 算术运算

```helen
let a = 10 + 3      // 13
let b = 10 - 3      // 7
let c = 10 * 3      // 30
let d = 10 / 3      // 3.333...
let e = 10 % 3      // 1
```

### 比较运算

```helen
let eq = 5 == 5     // true
let ne = 5 != 3     // true
let gt = 5 > 3      // true
let ge = 5 >= 5     // true
let lt = 3 < 5      // true
let le = 5 <= 5     // true
```

### 逻辑运算

```helen
let and = true && false   // false
let or = true || false    // true
let not = !true           // false
```

### 字符串连接

```helen
let greeting = "Hello, " + "World!"    // "Hello, World!"
let message = "Score: " + 42           // "Score: 42"
```

## 列表操作

```helen
let nums = [1, 2, 3]
let first = nums[0]        // 1
let len = len(nums)        // 3
let range_nums = range(5)  // [0, 1, 2, 3, 4]
```

## 映射操作

```helen
let person = {"name": "Alice", "age": 30}
let name = person["name"]  // "Alice"
```

## 类型检查

```helen
let x = 42
let t = type(x)            // "int"
let is_int = isinstance(x, "int")    // true
let is_str = isinstance(x, "str")    // false
```

## 练习

1. 声明一个 `const` 常量保存你的出生年份
2. 创建一个包含你信息的 map (name, age, city)
3. 计算圆的面积 (PI * r * r)，r = 5
4. 使用类型注解声明一个可选字符串变量

---

# 教程 03: 函数

> fn 声明 / 参数 / 返回值 / 函数调用

## 基本函数

```helen
fn greet(name) {
    print("Hello, " + name + "!")
}

main {
    greet("Alice")    // Hello, Alice!
}
```

## 返回值

```helen
fn add(a, b) {
    return a + b
}

main {
    let result = add(3, 5)
    print(result)    // 8
}
```

### 无返回值

```helen
fn say_hello() {
    print("Hello!")
    // 隐式返回 null
}
```

## 参数类型注解

```helen
fn add(a: int, b: int): int {
    return a + b
}

fn greet(name: str): str {
    return "Hello, " + name
}
```

## 参数类型检查

当函数参数有类型注解时，Helen 会在调用时进行类型检查：

### 编译时检查（字面量）

如果调用时传递的是字面量，类型错误会在编译时被捕获：

```helen
fn add(a: int, b: int): int {
    return a + b
}

add(1.5, 2.7)    // ❌ 编译错误：argument 1 type 'FloatType' is not compatible with parameter type 'IntType'
add(1, 2)        // ✅ 正确
```

### 运行时检查（变量）

如果调用时传递的是变量，类型检查会在运行时进行：

```helen
fn add(a: int, b: int): int {
    return a + b
}

let x = 1.5
add(x, 2)        // ❌ 运行时错误：argument 1 type 'FloatType' is not compatible with parameter type 'IntType'

let y = 10
add(y, 2)        // ✅ 正确
```

### 类型兼容性规则

- `int` 可以传递给 `float` 参数（int 是 float 的子类型）
- `float` **不能**传递给 `int` 参数
- 任何类型可以传递给 `any` 参数

```helen
fn processFloat(x: float): float {
    return x * 2
}

processFloat(10)     // ✅ int 可以转换为 float
processFloat(10.5)   // ✅ float 直接匹配

fn processInt(x: int): int {
    return x + 1
}

processInt(10)       // ✅ int 直接匹配
processInt(10.5)     // ❌ float 不能转换为 int
```

## 递归

```helen
fn factorial(n: int): int {
    if n <= 1 {
        return 1
    }
    return n * factorial(n - 1)
}

main {
    print(factorial(5))    // 120
}
```

## 函数作为值

```helen
fn double(x) {
    return x * 2
}

fn apply(op, value) {
    // 在 v1 中，函数通过名称引用
    // 注意：不能用 'fn' 作为参数名（它是关键字）
    print(double(value))
}
```

## Agent 内部函数

Agent 可以在 `functions` 块中定义内部函数:

```helen
agent DataProcessor {
    description "Process and analyze data"

    functions {
        fn validate(data) {
            if len(data) == 0 {
                return false
            }
            return true
        }

        fn transform(data) {
            // 数据转换逻辑
            return data
        }
    }

    prompt """
    Process the given data after validation.
    """
}
```

## 作用域

```helen
let global_x = 100

fn test() {
    let local_x = 200
    print(global_x)    // ✅ 可以访问全局变量
    print(local_x)     // ✅ 可以访问局部变量
}

main {
    print(global_x)    // ✅ 100
    test()
}
```

**注意**: `local_x` 只在 `test()` 函数内部可见，在 `main` 中无法访问。

## 练习

1. 编写一个计算斐波那契数列的递归函数
2. 编写一个函数，接受列表并返回最大值
3. 编写一个函数，判断一个字符串是否为回文

---

# 教程 04: 控制流

> if / for / while / match / try-catch

## 条件分支

### if / else

```helen
let score = 85

if (score >= 90) {
    print("A")
} else if (score >= 80) {
    print("B")
} else if (score >= 70) {
    print("C")
} else {
    print("F")
}
```

**注意**: `if` 条件必须用括号包裹：`if (cond) { ... }`。

### Truthy 规则

```helen
if 0 { print("不会执行") }        // 0 → false
if "" { print("不会执行") }       // 空字符串 → false
if [] { print("不会执行") }       // 空列表 → false
if null { print("不会执行") }     // null → false
if 1 { print("会执行") }          // 非零 → true
if "hello" { print("会执行") }    // 非空字符串 → true
if [1] { print("会执行") }        // 非空列表 → true
```

## 循环

### for ... in

```helen
for item in ["apple", "banana", "cherry"] {
    print(item)
}
// apple
// banana
// cherry
```

### 带索引遍历

```helen
let fruits = ["apple", "banana", "cherry"]
for fruit in fruits {
    print(fruit)
}
```

### range 遍历

```helen
for i in range(5) {
    print(i)    // 0, 1, 2, 3, 4
}

for i in range(1, 6) {
    print(i)    // 1, 2, 3, 4, 5
}

for i in range(0, 10, 2) {
    print(i)    // 0, 2, 4, 6, 8
}
```

### while

```helen
let count = 0
while (count < 5) {
    print(count)
    count = count + 1
}
```

**注意**: `while` 条件必须用括号包裹：`while (cond) { ... }`。使用 `count = count + 1`（赋值）而非 `let count = count + 1`（新声明），后者会创建局部变量导致死循环。

### break / continue

```helen
for i in range(10) {
    if i == 3 {
        continue    // 跳过 3
    }
    if i == 7 {
        break       // 在 7 退出
    }
    print(i)
}
// 0, 1, 2, 4, 5, 6
```

## 模式匹配

```helen
let status = "success"

match status {
    case "success" { print("OK") }
    case "error" { print("Failed") }
    default { print("Unknown") }
}
```

**注意**: `case` 和 `default` 后面使用 `{ }` 包裹代码块，不是 `:`。

### 数字匹配

```helen
let code = 404

match code {
    case 200 { print("OK") }
    case 404 { print("Not Found") }
    case 500 { print("Server Error") }
    default { print("Other") }
}
```

## 异常处理

### throw 抛出异常

使用 `throw` 语句主动抛出预定义类型的异常：

```helen
// 带消息 - 用 try-catch 捕获
try {
    throw RuntimeError("something went wrong")
} catch RuntimeError err {
    print("Caught: " + err.message)
}

// 无消息（使用默认消息）
try {
    throw LLMError
} catch LLMError err {
    print("Caught LLM error")
}
```

在函数中使用 throw 进行参数验证：

```helen
fn validate_age(age: int) {
    if (age < 0) {
        throw RuntimeError("age cannot be negative")
    }
    if (age > 150) {
        throw RuntimeError("age seems unrealistic")
    }
    return age
}

try {
    let result = validate_age(-5)
} catch RuntimeError err {
    print("Validation failed: " + err.message)
}
```

**预定义异常类型**：

| 类型 | 说明 |
|------|------|
| `RuntimeError` | 运行时错误 |
| `LLMError` | LLM 相关错误（基类） |
| `TimeoutError` | LLM 调用超时（继承 LLMError） |
| `ModelError` | 模型不可用或配额耗尽（继承 LLMError） |
| `ToolError` | 工具调用失败 |
| `AggregateError` | 多个异步任务失败（await [list]） |

**异常继承**：`catch LLMError` 也会捕获 `TimeoutError` 和 `ModelError`。

### try / catch

```helen
try {
    let result = validate_age(-5)
    print(result)
} catch RuntimeError err {
    print("Runtime error: " + err.message)
} catch TimeoutError err {
    print("Timeout: " + err.message)
}
```

**语法**: `catch Type varname { ... }`，类型名后直接跟变量名，不需要 `as` 关键字。

### catch-all

```helen
try {
    risky_operation()
} catch {
    // 捕获任何未匹配的错误
    print("Something went wrong")
}
```

### finally

```helen
try {
    open_file()
    process_data()
} catch RuntimeError err {
    print("Error: " + err.message)
} finally {
    close_file()    // 始终执行
}
```

### catch 顺序

```helen
// ✅ 具体类型在前，catch-all 在后
try {
    ...
} catch TimeoutError err {
    ...
} catch LLMError err {
    ...
} catch RuntimeError err {
    ...
} catch {
    ...
}

// ❌ catch-all 必须在最后
try {
    ...
} catch {
    ...
} catch TimeoutError err {    // E0343
    ...
}
```

### 完整示例：自定义验证

```helen
fn divide(a: int, b: int): int {
    if (b == 0) {
        throw RuntimeError("division by zero")
    }
    return a / b
}

try {
    let result = divide(10, 0)
    print("Result: " + str(result))
} catch RuntimeError err {
    print("Cannot divide: " + err.message)
}
// 输出: Cannot divide: division by zero
```

## 综合示例：FizzBuzz

```helen
main {
    for i in range(1, 101) {
        if (i % 15 == 0) {
            print("FizzBuzz")
        } else if (i % 3 == 0) {
            print("Fizz")
        } else if (i % 5 == 0) {
            print("Buzz")
        } else {
            print(i)
        }
    }
}
```

**注意**: 上面的 `main { }` 需要在 `agent` 内部使用。顶层程序直接写 `for`/`if` 等语句即可。

## 练习

1. 使用 for 循环计算 1 到 100 的和
2. 使用 while 循环实现二分查找
3. 编写一个函数，使用 match 判断星期几 (1-7)
4. 编写 try-catch 处理除零错误

---

# 教程 05: Agent 编程

> agent 声明 / description / prompt / 配置

## 什么是 Agent？

在 Helen 中，Agent 是**一等公民**——不是库对象，而是语言级别的结构。

传统方式（Python):

```python
class Translator:
    def __init__(self):
        self.description = "Translate text"
        self.prompt = "You are a translator..."
```

Helen 方式:

```helen
agent Translator {
    description "Translate text"
    prompt "You are a translator..."
}
```

编译器理解 Agent 的语义，可以在 LSP 中补全、在文档中自动提取。

## 基本 Agent

```helen
agent Translator {
    description "Translate text between languages"
    prompt """
    You are a professional translator.
    Translate the given text accurately.
    """
}
```

## Agent 配置

### model — 指定模型

```helen
agent SmartTranslator {
    description "High-quality translation"
    model "gpt-4"
    prompt "Translate carefully..."
}
```

### temperature — 控制随机性

```helen
agent CreativeWriter {
    description "Write creative stories"
    temperature 0.9    // 高创造性
    prompt "Write a story..."
}

agent DataExtractor {
    description "Extract structured data"
    temperature 0.1    // 低随机性，精确输出
    prompt "Extract data..."
}
```

### max-turns — 多轮对话

```helen
agent Interviewer {
    description "Conduct an interview"
    max-turns 5    // 最多 5 轮对话
    prompt "Ask follow-up questions..."
}
```

### tools — 内置工具

Agent 可以声明使用哪些内置工具，LLM 会在 `llm act` 时通过 function calling 调用：

```helen
agent Researcher {
    description "Research assistant"
    tools ["web_search", "web_fetch", "read_file"]
    prompt "Research the given topic thoroughly."
}

agent Coder {
    description "Code writer"
    tools ["write_file", "shell_exec", "calculate"]
    prompt "Write and execute code."
}
```

**可用工具：**

| 工具 | 功能 | 参数 |
|------|------|------|
| `web_search` | 搜索 Wikipedia | `query: str` |
| `web_fetch` | 获取网页内容 | `url: str` |
| `read_file` | 读取文件 | `path: str` |
| `write_file` | 写入文件 | `path: str, content: str` |
| `shell_exec` | 执行 shell 命令 | `command: str` |
| `calculate` | 数学计算 | `expression: str` |

## Agent main 块

Agent 可以包含 `main` 块作为执行入口，使用 `call` 调用：

```helen
agent Translator(text: str, target: str) {
    description "Translate text"
    model "gpt-4"
    temperature 0.3
    prompt """
    Translate to {{target}}:
    {{text}}
    """
    
    functions {
        fn validate_input(s: str): bool {
            return len(s) > 0
        }
    }
    
    main {
        if validate_input(text) {
            let result = llm act    // bare form：自动使用渲染后的 prompt
            return result
        }
        return "输入为空"
    }
}

// 调用方式（推荐函数式调用）：
let translated = Translator(text="Hello", target="French")
// 函数式调用：let translated = Translator(text="Hello", target="French")
```

**执行流程：**
1. `Translator(text="Hello", target="French")` 创建隔离 Environment
2. 绑定参数：`text="Hello"`, `target="French"`
3. 执行 `main` 块
4. `main` 中的 `llm act`（bare form）触发 LLM 调用：
   - `prompt` 模板渲染 → `system_prompt` + `user` 消息
   - 工具调用循环（如果有 `tools`）
5. 返回结果

## Agent 参数

```helen
agent Translator {
    description "Translate text"

    // 参数声明 (未来版本支持类型检查)
    // text: str — 要翻译的文本
    // target_lang: str — 目标语言

    prompt """
    Translate: {{text}}
    Target language: {{target_lang}}
    """
}

main {
    let result = Translator("Hello", "French")
}
```

## 调用 Agent

```helen
agent Summarizer {
    description "Summarize text"
    prompt "Summarize the following:"
}

main {
    let text = "Long article content here..."
    let summary = Summarizer(text)
    print(summary)
}
```

## 完整示例：邮件分类系统

```helen
agent EmailClassifier {
    description "Classify emails into categories"
    model "gpt-4"
    temperature 0.1
    prompt """
    Classify the email into one of:
    - urgent: Requires immediate attention
    - meeting: Calendar-related
    - informational: FYI only
    - spam: Unwanted email
    """
}

agent UrgentResponder {
    description "Draft response to urgent emails"
    prompt "Draft a professional response..."
}

agent EmailClassifier {
    description "Classify emails"
    prompt "Classify this email..."
    main {
        let email = "URGENT: Server down in production!"

        llm if "Classify this email" {
            branch "urgent" {
                print("🚨 URGENT email detected!")
                UrgentResponder(email)
            }
            branch "meeting" {
                print("📅 Meeting request")
            }
            branch "informational" {
                print("📧 FYI email")
            }
            branch "spam" {
                print("🗑️ Spam, ignoring")
            }
            default {
                print("📬 Uncategorized")
            }
        }
    }
}
```

## 练习

1. 创建一个 Agent，描述为"判断文本情感"，测试不同输入
2. 创建一个 Agent 配置 temperature 为 0，观察输出稳定性
3. 创建一个多 Agent 系统：分类器 + 响应器 + 总结器

---

# 教程 06: LLM 语句

> llm act / llm if 实战

## LLM 语句概述

Helen 有两个关键字级 LLM 语句：

| 语句 | 用途 | 返回值 |
|---|---|---|
| `llm act` | 让 LLM 执行任务 | 响应文本 |
| `llm if` | 让 LLM 分类路由 | 执行匹配分支或返回值 |

## llm act

### 基本用法

`llm act` 用于直接调用 LLM，传入 prompt 字符串：

```helen
main {
    let result = llm act "Translate 'Hello, world!' to French"
    print(result)
    // Bonjour, le monde!
}
```

### 在 agent 中使用

在 agent 的 `main` 块中，`llm act` 会自动使用 agent 的配置（model、temperature 等）：

```helen
agent Translator(text: str, target: str) {
    description "Translate text"
    model "qwen-plus"
    temperature 0.3
    prompt """
    Translate to {{target}}:
    {{text}}
    """

    main {
        // bare form：自动使用渲染后的 prompt
        let result = llm act
        return result
    }
}

main {
    let translated = Translator(text="Hello", target="French")
    print(translated)
}
```

### 带动态 prompt

可以在 `llm act` 后传入表达式，动态构建 prompt：

```helen
main {
    let review = "This product is amazing!"
    let result = llm act "Analyze sentiment of: " + review
    print(result)
}
```

### Bare form（在 agent 内无参数调用）

当 `llm act` 在 agent 的 `main` 块中使用时，可以省略参数。此时会自动使用 agent 的 `prompt` 模板渲染后的内容作为 user 消息：

```helen
agent Translator(text: str, target: str) {
    description "Translate text"
    temperature 0.3
    prompt """
    Translate to {{target}}:
    {{text}}
    """

    main {
        // bare form：自动使用渲染后的 prompt
        let result = llm act
        return result
    }
}

main {
    let translated = Translator(text="Hello", target="French")
    print(translated)
    // Bonjour
}
```

**Bare form 检测规则：**
- 语句结束符：`}`、`;`、EOF
- 语句关键字：`return`、`let`、`if`、`for` 等
- 换行边界：下一个 token 在不同行

## llm if

### 基本用法

```helen
llm if "Classify email priority" {
    branch "urgent" {
        print("🚨 URGENT — notify on-call immediately")
    }
    branch "high" {
        print("🔴 HIGH — address within 1 hour")
    }
    branch "normal" {
        print("🟢 NORMAL — handle in next sprint")
    }
    branch "low" {
        print("⚪ LOW — handle when convenient")
    }
    default {
        print("❓ Unknown priority")
    }
}
```

**注意**: `llm if` 使用 `branch` 关键字定义分支，不是 `case`。每个分支用 `{ }` 包裹代码块。

### 嵌套使用

```helen
let query = "How do I reset my password?"

llm if "Classify query type" {
    branch "question" {
        llm if "Identify question category" {
            branch "technical" {
                TechSupport(query)
            }
            branch "billing" {
                BillingSupport(query)
            }
            default {
                GeneralSupport(query)
            }
        }
    }
    branch "command" {
        execute_command(query)
    }
    default {
        print("I don't understand")
    }
}
```

### 支持表达式作为描述

`llm if` 的描述支持表达式，可以动态构建：

```helen
let text = "今天天气真好！"
let mood = llm if text + "反映的情绪" {
    branch "正面" { "happy" }
    branch "负面" { "sad" }
    default { "neutral" }
}
print("Mood: " + mood)
```

## llm stream — 流式输出

### 基本用法

`llm stream` 逐 chunk 流式输出 LLM 响应，适用于长文本生成场景：

```helen
main {
    llm stream "Write a short poem about programming"
}
```

默认行为：每个 chunk 到达时立即打印到终端（使用 `stream_print`），无需等待完整响应。

### 带回调函数

使用 `on_chunk` 指定回调函数，自定义处理每个 chunk：

```helen
fn handle_chunk(chunk) {
    stream_print("[" + chunk + "]")
}

main {
    llm stream "Explain recursion in one paragraph" on_chunk handle_chunk
}
```

### 在 agent 中使用

`llm stream` 在 agent 内自动使用 agent 的配置（model、temperature、prompt）：

```helen
agent Poet(topic: str) {
    description "Write poetry"
    temperature 0.9
    prompt """
    Write a poem about: {{topic}}
    """

    main {
        llm stream    // bare form：使用渲染后的 prompt
    }
}
```

### 动态 prompt

```helen
main {
    let topic = "the beauty of recursion"
    llm stream "Write a haiku about " + topic
}
```

### 与其他 LLM 语句对比

| 语句 | 用途 | 输出方式 |
|------|------|----------|
| `llm act` | 获取完整响应文本 | 等待完成后返回 |
| `llm if` | LLM 分类路由 | 等待完成后执行分支 |
| `llm stream` | 流式输出生成内容 | 逐 chunk 实时输出 |

## 对比：何时使用哪个？

| 场景 | 使用 |
|---|---|
| 需要 LLM 返回文本 | `llm act` |
| 需要 LLM 做分类决策 | `llm if` |
| 需要 LLM 从选项中选择并执行代码 | `llm if` + `branch` |
| 需要实时输出生成过程 | `llm stream` |
| 多步骤决策 | 嵌套 `llm if` |
| 需要结果变量 | `llm if` 或 `llm act` |

## 对话历史自动记录

每次 LLM 交互自动记录到对话历史：

```helen
main {
    // 自动记录: [user] "Classify email priority"
    llm if "Classify email priority" {
        branch "urgent" { print("Urgent!") }
        default { print("Other") }
    }
    // 自动记录: [assistant] "[routed to: urgent]"

    // 下次 LLM 调用会包含上面的历史作为上下文
    llm act "Draft response for the email"
}
```

历史上限 **4096 tokens**，自动截断最旧消息。

## Function Calling（工具调用）

当 Agent 配置了 `tools` 时，`llm act` 会自动进入 function calling 循环：

```helen
agent Researcher(topic) {
    description "Research assistant"
    tools ["web_search", "read_file"]
    main {
        return llm act "Research about: " + topic
    }
}
```

**执行流程：**

1. LLM 收到 prompt + 工具 schema
2. LLM 返回工具调用请求 → Helen 执行工具 → 结果返回 LLM
3. 循环直到 LLM 输出最终文本响应
4. 达到 `max_turns - 1` 时自动注入 nudge 提示，强制 LLM 输出最终答案

**内置工具列表：**

| 工具 | 功能 |
|------|------|
| `web_search` | Wikipedia 搜索 |
| `web_fetch` | 获取网页内容 |
| `read_file` | 读取文件 |
| `write_file` | 写入文件（覆盖） |
| `patch_file` | 精确修改文件（9 种模糊匹配策略） |
| `shell_exec` | 执行 shell 命令 |
| `calculate` | 数学计算 |

### patch_file 模糊匹配

`patch_file` 使用 `old_string` → `new_string` 模式精确修改文件，内置 9 种匹配策略处理 LLM 生成代码的常见差异：

```helen
// 修改文件中的特定函数
llm act "Read /tmp/main.py and change the function name from 'foo' to 'bar'"
```

匹配策略（按优先级）：
1. **Exact** — 精确字符串匹配
2. **Line-trimmed** — 行首尾空格差异
3. **Whitespace-normalized** — 多个空格/tab 归一化
4. **Indentation-flexible** — 缩进完全忽略
5. **Escape-normalized** — `\n` `\t` 转义差异
6. **Trimmed-boundary** — 首尾行空白修剪
7. **Unicode-normalized** — 智能引号、破折号等
8. **Block-anchor** — SequenceMatcher 相似度 (50%/70%)
9. **Context-aware** — 逐行相似度 (80% 阈值，50% 行匹配)

## Agent prompt 与 system_prompt

Agent 的 `prompt` 字段在 `llm act` 时作为 **system_prompt** 注入 LLM 调用：

```helen
agent Translator(text) {
    description "Professional translator"
    prompt """
    Translate the following text to {{target}}:
    {{text}}
    """
    main {
        // prompt 渲染后 → system_prompt ({"role": "system"})
        return llm act "Please translate accurately"
        // → user 消息 ({"role": "user"})
    }
}
```

**消息结构：**
```json
[
  {"role": "system", "content": "<description>\n<skills>\n<rendered prompt>"},
  {"role": "user", "content": "llm act 的表达式值"}
]
```

## 练习

1. 创建一个 llm if 三层嵌套的分类系统
2. 使用 llm if 让 LLM 选择算法策略并返回结果
3. 使用 llm act 实现一个翻译管道
4. 观察多次 LLM 调用后的对话历史

---

# 教程 07: 异步编程

> async / await / AggregateError / 并发 Agent 调用

## 概述

Helen 支持 `async` 启动并发 Agent 调用，通过 `await [list]` 等待全部完成。
`async Agent(...)` 是表达式，返回 `Task` 对象，可存入变量。

**真正的异步并发**：使用纯 `asyncio` 单线程并发，LLM 调用非阻塞执行，内存开销接近零。

## 基本用法

```helen
agent Researcher(topic: str) {
    description "Research a topic"
    prompt "Research and summarize:"
    main {
        return "Research result for: " + topic
    }
}

agent Analyst(topic: str) {
    description "Analyze data"
    prompt "Analyze the following data:"
    main {
        return "Analysis result for: " + topic
    }
}

main {
    let topic = "AI in healthcare"

    // 启动两个并发任务
    let research_task = async Researcher(topic)
    let data_task = async Analyst(topic)

    // 等待全部完成
    let results = await [research_task, data_task]
    let research = results[0]
    let analysis = results[1]
    print("Research: " + research)
    print("Analysis: " + analysis)
}
```

## 两种 async 形式

### 1. 表达式形式（延迟执行）

```helen
let task = async MyAgent(input)
// 创建 pending Task，不立即执行
// 在 await 时并发执行
```

**特点**：
- 返回 `Task.pending` 对象
- 延迟到 `await` 时执行
- 多个 pending Task 在 `await` 时并发执行

### 2. 语句形式（立即执行）

```helen
async MyAgent(input)
// 立即执行，返回 Task.completed
```

**特点**：
- 立即同步执行
- 返回 `Task.completed` 或 `Task.failed`
- 适用于不需要并发的场景

## Task 对象

`async Agent(...)` 返回 `Task` 对象，可存入变量：

```helen
let task = async MyAgent(input)
// task 是 Task 对象，包含结果或异常
```

`await` 支持列表和单个 Task：

```helen
// 列表形式：返回结果列表
let results = await [task1, task2, task3]

// 单个 Task 放在列表中
let result = await [task]
let value = result[0]
```

## await 行为

### 全部成功

```helen
let results = await [task1, task2, task3]
// results = [result1, result2, result3]
```

### 部分失败

当多个任务失败时，`await` 抛出 `AggregateError`：

```helen
try {
    let results = await [task1, task2, task3]
} catch AggregateError err {
    print("Multiple tasks failed: " + err.message)
    // err.errors 包含所有失败的异常列表
    print(err.errors)
}
```

## 实际示例：多源信息聚合

```helen
agent NewsSearcher(topic: str) {
    description "Search latest news"
    prompt "Search for news about:"
    main {
        return "News about " + topic
    }
}

agent AcademicSearcher(topic: str) {
    description "Search academic papers"
    prompt "Find papers about:"
    main {
        return "Papers about " + topic
    }
}

agent SocialSearcher(topic: str) {
    description "Search social media"
    prompt "Find social media posts about:"
    main {
        return "Social posts about " + topic
    }
}

main {
    let topic = "quantum computing breakthroughs"

    // 并发搜索三个源
    let news_task = async NewsSearcher(topic)
    let academic_task = async AcademicSearcher(topic)
    let social_task = async SocialSearcher(topic)

    // 等待全部结果
    try {
        let sources = await [news_task, academic_task, social_task]
        print("News: " + sources[0])
        print("Academic: " + sources[1])
        print("Social: " + sources[2])
    } catch AggregateError err {
        print("Some sources failed: " + err.message)
    }
}
```

## 普通函数异步调用

`async` 也可用于普通函数：

```helen
fn compute(x: num) {
    return x * x
}

fn cube(x: num) {
    return x * x * x
}

main {
    let t1 = async compute(3)
    let t2 = async cube(2)
    let results = await [t1, t2]
    print(results[0] + results[1])  // 9 + 8 = 17
}
```

## 性能特性

**真正的异步并发**：使用纯 `asyncio` 单线程并发

- **LLM 调用**：通过 `asyncio` 非阻塞执行
- **内存开销**：接近零（无额外线程）
- **并发效率**：3 个 1 秒的 LLM 调用 → ~1 秒完成（并发）

**对比传统线程池**：
- 线程池：3 个线程 × 8MB = 24MB
- asyncio：0 个线程 = ~0MB
- **内存节省**：100%

## 流式迭代（for await）

Helen 支持 `for await` 语法异步迭代流式响应：

```helen
agent Streamer(topic: str) {
    description "Stream a long response"
    prompt "Write a detailed essay about: {{topic}}"
}

main {
    let response = async Streamer("the history of computing")
    for await chunk in response {
        stream_print(chunk)
    }
}
```

`for await` 逐 chunk 处理异步可迭代对象，适用于：
- 流式 LLM 响应
- 异步数据源
- 大文件逐行处理

**注意**：`for await` 只能在 `async` 上下文中使用。

## 注意事项

| 规则 | 说明 |
|---|---|
| `async` 可用于表达式 | `let task = async Agent()` ✅ |
| `async` 也可作为语句 | `async Agent()` ✅（立即执行） |
| `await` 参数必须是列表 | `await [task]` ✅，`await task` ❌ |
| 真正异步并发 | LLM 调用通过 asyncio 非阻塞执行 |
| 错误聚合 | 多个失败 → `AggregateError`（可被 try-catch 捕获） |
| 环境隔离 | 每个 Task 有独立的环境快照 |

## 练习

1. 创建三个并发 Agent 调用，处理同一输入的不同方面
2. 模拟一个失败的任务，使用 try-catch 处理 AggregateError
3. 比较串行调用和 async/await 的执行时间
4. 尝试用 `async` 调用普通函数，观察并发效果

---

# 教程 08: 模块与导入

> import / 多格式 / 跨文件复用 / 路径安全

## 基本导入

```helen
// utils.helen
fn double(x) {
    return x * 2
}

agent Helper {
    description "A helper agent"
    prompt "Help the user."
}

// main.helen
import "./utils.helen"

main {
    let result = double(21)    // 42
    Helper()              // 使用导入的 Agent
}
```

## 导入别名

```helen
import "./math_utils.helen" as math

main {
    let result = math.add(1, 2)
}
```

## 多格式导入

### 导入 .json

```helen
// config.json
{
    "model": "gpt-4",
    "temperature": 0.7,
    "max_turns": 3
}

// main.helen
import "./config.json" as cfg

main {
    // cfg 包含解析后的 JSON 数据
    // (在 v1 中通过环境变量或运行时访问)
}
```

### 导入 .md

```helen
// prompt.md
You are a helpful assistant.
Always respond in a friendly tone.
Be concise but thorough.

// main.helen
import "./prompt.md" as system_prompt

main {
    // system_prompt 包含纯文本内容
}
```

## import 不执行 main

被导入文件的 `main` 块**不会**自动执行：

```helen
// lib.helen
fn utility() {
    return "useful"
}

main {
    print("This will NOT run when imported!")
}

// main.helen
import "./lib.helen"

main {
    utility()    // ✅ 可以使用函数
    // lib.helen 的 main 不会执行
}
```

## 路径安全

### 允许的导入

```helen
import "./utils.helen"          // ✅ 当前目录
import "./lib/helpers.helen"    // ✅ 子目录
import "../sibling/utils.helen" // ✅ 同级目录（在安全范围内）
```

### 拦截的导入

```helen
import "../../secrets.helen"    // ❌ 路径越界
import "/etc/passwd"             // ❌ 绝对路径
```

路径安全检查确保导入文件在项目目录内。

## 循环导入检测

```helen
// a.helen
import "./b.helen"
fn from_a() { return "A" }

// b.helen
import "./a.helen"    // 循环导入，静默跳过
fn from_b() { return "B" }

// main.helen
import "./a.helen"

main {
    from_a()    // ✅
    from_b()    // ✅ (b.helen 从 main 导入)
}
```

## 项目结构示例

```
my-project/
├── main.helen
├── agents/
│   ├── translator.helen
│   ├── summarizer.helen
│   └── classifier.helen
├── utils/
│   ├── text.helen
│   └── validation.helen
├── config.json
└── prompts/
    ├── translator.md
    └── summarizer.md
```

```helen
// main.helen
import "./agents/translator.helen"
import "./agents/summarizer.helen"
import "./agents/classifier.helen"
import "./utils/text.helen" as text_utils
import "./config.json" as config

main {
    // 使用所有导入的 Agent 和工具
}
```

## 练习

1. 创建一个 utils.helen 文件，包含常用函数
2. 在 main.helen 中导入并使用这些函数
3. 创建一个 config.json 并导入
4. 尝试循环导入，观察行为

---

# 教程 09: Python FFI

> 导入 Python 库 / 调用 Python 函数 / 类型自动转换

## 概述

Helen 支持通过 Python FFI（外部函数接口）直接导入和使用 Python 库。这让 Helen 可以访问 Python 的整个生态系统（40 万+ 包），包括数值计算、网络请求、数据处理等。

**核心特性：**
- ✅ 使用 `import` 语法导入 Python 模块
- ✅ 自动类型转换（Helen ↔ Python）
- ✅ 调用 Python 函数、访问属性和常量
- ✅ 支持嵌套模块（如 `os.path`）
- ✅ 复杂对象自动包装

## 基本用法

### 导入 Python 模块

```helen
import "math" as math
import "json" as json
import "os.path" as path
```

**语法规则：**
- 无文件扩展名 → Python 模块
- `.py` 扩展名 → Python 模块
- `.helen` → Helen 文件
- `.json`/`.md`/`.yaml` → 数据文件

### 调用 Python 函数

```helen
import "math" as math

main {
    let sqrt_result = math.sqrt(16)
    print(sqrt_result)    // 4.0
    
    let power = math.pow(2, 10)
    print(power)          // 1024.0
}
```

### 访问 Python 常量

```helen
import "math" as math

main {
    let pi = math.pi
    print(pi)             // 3.141592653589793
    
    let e = math.e
    print(e)              // 2.718281828459045
}
```

## 类型转换

### Helen → Python（自动）

| Helen 类型 | Python 类型 |
|-----------|------------|
| `int` | `int` |
| `float` | `float` |
| `str` | `str` |
| `bool` | `bool` |
| `null` | `None` |
| `list` | `list`（递归转换） |
| `map` | `dict`（递归转换） |

### Python → Helen（自动）

| Python 类型 | Helen 类型 |
|------------|-----------|
| `int` | `int` |
| `float` | `float` |
| `str` | `str` |
| `bool` | `bool` |
| `None` | `null` |
| `list` | `list`（递归转换） |
| `dict` | `map`（递归转换） |
| `tuple` | `list` |
| 复杂对象 | 包装为 `PythonObject` |

### 示例：JSON 处理

```helen
import "json" as json

main {
    // Helen map → Python dict → JSON string
    let data = {"name": "Alice", "age": 30, "active": true}
    let json_str = json.dumps(data)
    print(json_str)
    // {"name": "Alice", "age": 30, "active": true}
    
    // JSON string → Python dict → Helen map
    let parsed = json.loads(json_str)
    print(parsed["name"])    // Alice
}
```

## 嵌套模块

支持导入嵌套模块（如 `os.path`）：

```helen
import "os.path" as path

main {
    let joined = path.join("home", "user", "docs")
    print(joined)    // home/user/docs
    
    let ext = path.splitext("file.txt")
    print(ext)       // ["file", ".txt"]
}
```

## 实际示例

### 示例 1：数学计算

```helen
import "math" as math

main {
    // 三角函数
    let angle = math.pi / 4
    let sin_val = math.sin(angle)
    let cos_val = math.cos(angle)
    print("sin(π/4) = " + str(sin_val))
    print("cos(π/4) = " + str(cos_val))
    
    // 对数
    let log_val = math.log(100, 10)
    print("log₁₀(100) = " + str(log_val))
    
    // 取整
    print(math.floor(3.7))    // 3
    print(math.ceil(3.2))     // 4
}
```

### 示例 2：文件路径操作

```helen
import "os.path" as path

main {
    let filepath = "/home/user/documents/report.txt"
    
    // 提取文件名
    let basename = path.basename(filepath)
    print(basename)    // report.txt
    
    // 提取目录
    let dirname = path.dirname(filepath)
    print(dirname)     // /home/user/documents
    
    // 分离扩展名
    let parts = path.splitext(filepath)
    print(parts[0])    // /home/user/documents/report
    print(parts[1])    // .txt
}
```

### 示例 3：数据处理

```helen
import "json" as json

main {
    // 创建数据
    let users = [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
        {"name": "Charlie", "age": 35}
    ]
    
    // 序列化为 JSON
    let json_data = json.dumps(users)
    print(json_data)
    
    // 解析 JSON
    let parsed = json.loads(json_data)
    for user in parsed {
        print(user["name"] + " is " + str(user["age"]) + " years old")
    }
}
```

### 示例 4：在 Agent 中使用 Python 库

```helen
import "math" as math

agent DataAnalyzer(data: list) {
    description "Analyze numerical data"
    prompt """
    Analyze the following data: {{data}}
    """
    
    functions {
        fn calculate_stats() -> map {
            let n = len(data)
            let sum = 0
            for value in data {
                sum = sum + value
            }
            let mean = sum / n
            
            // 使用 Python 的 math.sqrt
            let variance = 0
            for value in data {
                let diff = value - mean
                variance = variance + diff * diff
            }
            variance = variance / n
            let std_dev = math.sqrt(variance)
            
            return {
                "mean": mean,
                "std_dev": std_dev,
                "min": min(data),
                "max": max(data)
            }
        }
    }
    
    main {
        let stats = calculate_stats()
        return "Mean: " + str(stats["mean"]) + 
               ", Std Dev: " + str(stats["std_dev"])
    }
}

main {
    let data = [10, 20, 30, 40, 50]
    let analyzer = DataAnalyzer(data)
    let result = analyzer()
    print(result)
}
```

## 错误处理

### 导入不存在的模块

```helen
import "nonexistent_module" as bad

main {
    // 运行时错误：Cannot import Python module 'nonexistent_module'
}
```

### 访问不存在的属性

```helen
import "math" as math

main {
    let value = math.nonexistent_function()
    // 运行时错误：'math' has no property 'nonexistent_function'
}
```

### 使用 try-catch 处理

```helen
import "math" as math

main {
    try {
        let result = math.sqrt(-1)
        print(result)
    } catch RuntimeError err {
        print("Error: " + err.message)
    }
}
```

## 性能注意事项

- **类型转换**：简单类型（int/float/str）转换开销极低
- **复杂对象**：大型 list/dict 转换有一定开销，建议批量处理
- **函数调用**：每次调用都有跨语言开销，避免在紧密循环中频繁调用

## 与 Helen 原生功能的对比

| 功能 | Helen 原生 | Python FFI |
|------|-----------|-----------|
| 字符串处理 | ✅ 内置 string 函数 | ✅ 可用 Python re 等 |
| 数学计算 | ✅ 基础 math 函数 | ✅ 可用 numpy/scipy |
| 文件操作 | ✅ read_file/write_file | ✅ 可用 os/pathlib |
| 网络请求 | ❌ 无 | ✅ 可用 requests |
| 数据处理 | ❌ 有限 | ✅ 可用 pandas |
| 机器学习 | ❌ 无 | ✅ 可用 torch/tensorflow |

**建议**：优先使用 Helen 原生功能，需要高级功能时使用 Python FFI。

## 练习

1. 导入 `math` 模块，计算圆的面积（半径 = 5）
2. 导入 `json` 模块，将 map 转换为 JSON 字符串并解析回来
3. 导入 `os.path` 模块，提取文件路径的目录和文件名
4. 创建一个 Agent，使用 Python 的 `math` 模块进行复杂计算

---

# 教程 10: 标准库参考

> 185 个内置函数，覆盖 AI 应用开发的所有核心需求

## 概览

Helen 标准库提供 185 个内置函数，分为 9 大类别：

| 类别 | 函数数 | 功能 |
|------|--------|------|
| **Core** | 11 | 类型转换、通用操作 |
| **String** | 36 | 字符串处理、正则、文本分析 |
| **Data** | 25 | JSON、HTML、CSV、Markdown、YAML、TOML、XML |
| **Collection** | 22 | 列表、字典、集合操作 |
| **Network** | 9 | HTTP 请求、URL 处理 |
| **Time** | 13 | 日期时间、格式化、运算 |
| **Math** | 15 | 数学运算、统计分析 |
| **File** | 16 | 文件读写、目录操作、临时文件 |
| **System** | 16 | 环境变量、进程管理、日志 |
| **Crypto** | 11 | 哈希、随机数 |
| **IO** | 5 | 流式输出控制 |

## Core 函数 (11)

### 类型转换

```helen
str(42)                       // "42"
int("42")                     // 42
float("3.14")                 // 3.14
```

### 通用操作

```helen
len("hello")                  // 5
len([1, 2, 3])               // 3

abs(-42)                      // 42
min(3, 1, 4)                 // 1
max(3, 1, 4)                 // 4

range(5)                      // [0, 1, 2, 3, 4]
range(1, 6)                   // [1, 2, 3, 4, 5]
```

### 类型检查

```helen
type(42)                      // "int"
isinstance(42, "int")         // true
```

## String 函数 (36)

### 基础操作 (12)

```helen
// 大小写
upper("hello")                // "HELLO"
lower("HELLO")                // "hello"

// 修剪
strip("  hello  ")            // "hello"
trim_prefix("hello", "he")    // "llo"
trim_suffix("hello", "lo")    // "hel"

// 分割与连接
split("a,b,c", ",")           // ["a", "b", "c"]
join("-", ["a", "b", "c"])    // "a-b-c"

// 检查
startswith("hello", "hel")    // true
endswith("hello", "lo")       // true

// 查找与替换
find("hello", "ell")          // 1
replace("hello", "l", "L")    // "heLLo"
substring("hello", 1, 3)      // "el"
```

### 正则表达式 (5)

```helen
// 匹配
let m = regex_match(r"\d+", "123abc")
print(m.match)                // "123"

// 搜索
let s = regex_search(r"\d+", "abc123def")
print(s.match)                // "123"

// 替换
regex_replace(r"\d+", "abc123def", "NUM")
// "abcNUMdef"

// 分割
regex_split(r"\s+", "a  b  c")
// ["a", "b", "c"]

// 查找所有
regex_findall(r"\d+", "a1b2c3")
// ["1", "2", "3"]
```

### 文本分析 (8)

```helen
// 分词
tokenize("Hello, world!")     // ["Hello", "world"]

// 词频统计
word_count("hello world hello")
// {"hello": 2, "world": 1}

// 编辑距离
levenshtein("hello", "hallo") // 1

// 相似度
similarity("hello", "hallo")  // 0.8

// 去除标点
remove_punctuation("Hello!")  // "Hello"

// 标准化空白
normalize_whitespace("a  b  c")  // "a b c"

// 提取 URL
extract_urls("Visit https://example.com")
// ["https://example.com"]

// 提取邮箱
extract_emails("Contact user@example.com")
// ["user@example.com"]
```

### 编码转换 (4)

```helen
// Base64
base64_encode("Hello")        // "SGVsbG8="
base64_decode("SGVsbG8=")     // "Hello"

// HTML 转义
html_escape("<script>")       // "&lt;script&gt;"
html_unescape("&lt;")         // "<"
```

### 字符串操作 (7)

```helen
repeat("ab", 3)               // "ababab"
reverse("hello")              // "olleh"

pad_left("42", 5, "0")        // "00042"
pad_right("hi", 5)            // "hi   "
center("hi", 6)               // "  hi  "

count("hello", "l")           // 2
index("hello", "ll")          // 2
```

## Data 函数 (25)

### JSON (4)

```helen
// 解析
let data = json_parse('{"name": "Alice", "age": 30}')
print(data.name)              // "Alice"

// 生成
let json_str = json_stringify({"name": "Alice"})
// '{"name": "Alice"}'

// 文件操作
json_save("data.json", data)
let loaded = json_load("data.json")
```

### HTML (3)

```helen
// 提取文本
html_text("<p>Hello <b>World</b></p>")
// "Hello World"

// 提取链接
html_links('<a href="http://example.com">Link</a>')
// ["http://example.com"]

// 解析
let dom = html_parse("<div>content</div>")
```

### Markdown (2)

```helen
// 转 HTML
markdown_to_html("# Title\n\nParagraph")
// "<h1>Title</h1><p>Paragraph</p>"

// 提取标题
markdown_extract_headings("# H1\n## H2")
// [{"level": 1, "text": "H1"}, {"level": 2, "text": "H2"}]
```

### CSV (4)

```helen
// 解析
let rows = csv_parse("name,age\nAlice,30")
// [["name", "age"], ["Alice", "30"]]

// 生成
csv_stringify([["a", "b"], ["1", "2"]])
// "a,b\n1,2\n"

// 文件操作
csv_save("data.csv", rows)
let loaded = csv_load("data.csv")
```

### YAML (4)

```helen
// 解析
let data = yaml_parse("name: Alice\nage: 30")
// {"name": "Alice", "age": 30}

// 生成
yaml_stringify({"name": "Alice"})
// "name: Alice\n"

// 文件操作
yaml_save("config.yaml", data)
let loaded = yaml_load("config.yaml")
```

### TOML (4)

```helen
// 解析
let data = toml_parse("name = \"Alice\"\nage = 30")
// {"name": "Alice", "age": 30}

// 生成
toml_stringify({"name": "Alice"})
// "name = \"Alice\"\n"

// 文件操作
toml_save("config.toml", data)
let loaded = toml_load("config.toml")
```

### XML (4)

```helen
// 解析
let data = xml_parse("<root><name>Alice</name></root>")
// {"root": {"name": "Alice"}}

// 生成
xml_stringify({"name": "Alice"}, root="user")
// "<user><name>Alice</name></user>"

// 文件操作
xml_save("data.xml", data)
let loaded = xml_load("data.xml")
```

## Collection 函数 (22)

### 列表操作 (12)

```helen
// 函数式编程
map([1, 2, 3], x => x * 2)
// [2, 4, 6]

filter([1, 2, 3, 4], x => x > 2)
// [3, 4]

reduce([1, 2, 3], (acc, x) => acc + x, 0)
// 6

// 查找
find_if([1, 2, 3], x => x > 1)
// 2

every([2, 4, 6], x => x % 2 == 0)
// true

some([1, 2, 3], x => x > 2)
// true

// 排序与去重
sort([3, 1, 4, 1, 5])
// [1, 1, 3, 4, 5]

unique([1, 2, 2, 3])
// [1, 2, 3]

// 列表变换
flatten([[1, 2], [3, 4]])
// [1, 2, 3, 4]

chunk([1, 2, 3, 4, 5], 2)
// [[1, 2], [3, 4], [5]]

zip([1, 2], ["a", "b"])
// [(1, "a"), (2, "b")]
```

### 字典操作 (6)

```helen
let user = {"name": "Alice", "age": 30}

keys(user)                    // ["name", "age"]
values(user)                  // ["Alice", 30]
entries(user)                 // [("name", "Alice"), ("age", 30)]

// 合并
merge({"a": 1}, {"b": 2})
// {"a": 1, "b": 2}

// 选择与排除
pick(user, ["name"])
// {"name": "Alice"}

omit(user, ["age"])
// {"name": "Alice"}
```

### 集合操作 (5)

```helen
let s1 = make_set([1, 2, 3])
let s2 = make_set([2, 3, 4])

set_union(s1, s2)             // {1, 2, 3, 4}
set_intersection(s1, s2)      // {2, 3}
set_difference(s1, s2)        // {1}
set_has(s1, 2)                // true
```

## Network 函数 (9)

### HTTP 请求 (5)

```helen
// GET
let response = http_get("https://api.example.com/data")
print(response.status)        // 200
print(response.body)          // JSON string

// POST
let post_data = http_post(
    "https://api.example.com/users",
    {"name": "Alice"}
)

// PUT
http_put("https://api.example.com/users/1", {"name": "Bob"})

// DELETE
http_delete("https://api.example.com/users/1")

// 下载文件
http_download("https://example.com/image.png", "image.png")
```

### URL 处理 (4)

```helen
// 解析
let parsed = url_parse("https://example.com:8080/path?q=1")
print(parsed.scheme)          // "https"
print(parsed.host)            // "example.com"
print(parsed.port)            // 8080
print(parsed.path)            // "/path"
print(parsed.query)           // "q=1"

// 构建
url_build("https", "example.com", "/path", "q=1")
// "https://example.com/path?q=1"

// 编码/解码
url_encode("hello world")     // "hello%20world"
url_decode("hello%20world")   // "hello world"
```

## Time 函数 (13)

### 时间获取 (3)

```helen
// 当前日期时间
now()                         // "2026-06-18T14:30:45"

// Unix 时间戳
time()                        // 1750345845.123

// 暂停执行
sleep(2)                      // 暂停 2 秒
```

### 日期操作 (10)

```helen
// 创建日期
date()                        // "2026-06-18"
date(2024, 6, 18)             // "2024-06-18"

// 创建日期时间
datetime(2024, 6, 18, 10, 30, 0)
// "2024-06-18T10:30:00"

// 格式化
date_format("2024-06-18", "%d/%m/%Y")
// "18/06/2024"

// 解析
date_parse("18/06/2024", "%d/%m/%Y")
// "2024-06-18"

// 日期运算
date_add("2024-06-18", days=7)
// "2024-06-25"

date_add("2024-06-18T10:00:00", hours=2)
// "2024-06-18T12:00:00"

// 日期差值
date_diff("2024-06-18", "2024-06-25", "days")
// 7.0

// 提取组件
date_year("2024-06-18")       // 2024
date_month("2024-06-18")      // 6
date_day("2024-06-18")        // 18
date_weekday("2024-06-18")    // 1 (Tuesday)
```

## Math 函数 (15)

### 基础数学 (4)

```helen
round(3.14159, 2)             // 3.14
sqrt(16)                      // 4.0
floor(3.9)                    // 3
ceil(3.1)                     // 4
```

### 统计分析 (11)

```helen
let data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

// 基本统计
mean(data)                    // 5.5
median(data)                  // 5.5
mode([1, 2, 2, 3, 3])         // [2, 3]

// 方差与标准差
variance(data)                // 8.25
stddev(data)                  // 2.87

// 相关性
let x = [1, 2, 3, 4, 5]
let y = [2, 4, 6, 8, 10]
correlation(x, y)             // 1.0

// 百分位数
percentile(data, 25)          // 3.25
percentile(data, 75)          // 7.75

// 聚合
sum(data)                     // 55
product([1, 2, 3, 4])         // 24
stats_min(data)               // 1
stats_max(data)               // 10
```

## File 函数 (16)

### 基础文件操作 (5)

```helen
// 读写文件
let content = read_file("data.txt")
write_file("output.txt", "Hello, Helen!")
append_file("log.txt", "New line\n")

// 目录创建
mkdir("new_dir")
mkdir_p("a/b/c")              // 递归创建
```

### 路径操作 (6)

```helen
path_join("a", "b", "c")      // "a/b/c"
path_dirname("/a/b/c.txt")    // "/a/b"
path_basename("/a/b/c.txt")   // "c.txt"

path_exists("file.txt")       // true
path_is_file("file.txt")      // true
path_is_dir("dir")            // true
```

### 高级文件操作 (10)

```helen
// 文件信息
file_size("document.txt")     // 1024 (bytes)
file_modified("doc.txt")      // "2026-06-18T14:30:45"

// 目录操作
list_dir("/path/to/dir")
// ["file1.txt", "file2.txt", "subdir"]

list_dir("/path", pattern="*.txt")
// ["file1.txt", "file2.txt"]

walk_dir("/path")
// [("/path", ["subdir"], ["file.txt"]), ...]

// 文件操作
copy_file("source.txt", "backup.txt")
move_file("old.txt", "new.txt")
delete_file("temp.txt")
delete_dir("empty_dir")
delete_dir("full_dir", recursive=true)

// 临时文件
let tmp = temp_file(suffix=".txt")
let tmpdir = temp_dir(prefix="workspace")
```

## System 函数 (16)

### 环境变量 (4)

```helen
// 获取
let path = env_get("PATH")
let value = env_get("MY_VAR", "default")

// 设置
env_set("MY_VAR", "my_value")

// 列出所有
let all = env_list()

// 删除
env_delete("MY_VAR")
```

### 进程管理 (5)

```helen
// 执行命令
let result = exec("ls -la")
print(result.stdout)
print(result.returncode)

// 异步执行
let pid = exec_async("sleep 10")

// 当前进程
let my_pid = pid()

// 退出
exit(0)

// 发送信号
kill(pid, 15)                 // SIGTERM
```

### 日志系统 (7)

```helen
// 日志级别
log_debug("Debug message")
log_info("Info message")
log_warn("Warning message")
log_error("Error message")
log_critical("Critical message")

// 设置级别
log_set_level("INFO")

// 输出到文件
log_to_file("/var/log/helen.log")
```

## Crypto 函数 (11)

### 哈希函数 (6)

```helen
// 文本哈希
md5("hello")
// "5d41402abc4b2a76b9719d911017c592"

sha1("hello")
// "aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d"

sha256("hello")
// "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

sha512("hello")
// 128 字符的哈希

// HMAC
hmac_sha256("secret_key", "message")

// 文件哈希
hash_file("document.txt", "sha256")
```

### 随机函数 (5)

```helen
// 随机浮点数 (0-1)
random()                      // 0.123456789

// 随机整数
randint(1, 100)               // 42

// 随机选择
choice([1, 2, 3, 4, 5])       // 3

// 随机打乱
shuffle([1, 2, 3, 4, 5])
// [3, 1, 5, 2, 4]

// 随机采样
sample([1, 2, 3, 4, 5], 3)
// [2, 5, 1]
```

## IO 流式输出函数 (5)

```helen
// 无换行打印
stream_print("Loading")
stream_print("...")
stream_print(" Done!")

// 清除当前行
stream_clear()

// 进度条
progress_bar(50, 100)
// [██████████░░░░░░░░░░] 50%

// 光标移动
stream_cursor_up(2)
stream_cursor_down(1)
```

## 综合示例

### 1. 网络爬虫

```helen
main {
    // 获取网页
    let response = http_get("https://example.com")
    
    // 提取链接
    let links = html_links(response.body)
    
    // 提取文本
    let text = html_text(response.body)
    
    // 分析词频
    let words = word_count(text)
    
    // 保存结果
    json_save("links.json", links)
    json_save("words.json", words)
    
    print("Crawled " + str(len(links)) + " links")
}
```

### 2. 数据处理管道

```helen
main {
    // 读取 CSV
    let data = csv_load("data.csv")
    
    // 提取列
    let names = map(data, row => row[0])
    
    // 过滤
    let filtered = filter(names, name => len(name) > 3)
    
    // 排序
    let sorted = sort(filtered)
    
    // 去重
    let unique_names = unique(sorted)
    
    // 保存结果
    csv_save("output.csv", unique_names)
    
    print("Processed " + str(len(unique_names)) + " names")
}
```

### 3. 配置文件管理

```helen
main {
    // 读取配置
    let config = yaml_load("config.yaml")
    
    // 修改配置
    let new_config = merge(config, {
        "version": "2.0",
        "updated": now()
    })
    
    // 保存配置
    yaml_save("config.yaml", new_config)
    
    // 备份
    let backup_path = "config_" + date() + ".yaml"
    copy_file("config.yaml", backup_path)
    
    log_info("Config updated and backed up")
}
```

## 依赖说明

### 核心功能（零依赖）

所有核心功能使用 Python 标准库，无需额外安装：
- Core、String、Collection、Network、Time、Math、File、System、Crypto、IO

### 可选依赖

以下功能需要额外安装：

```bash
# YAML 支持
pip install pyyaml

# TOML 支持（Python 3.11+ 已内置）
pip install toml
```

XML 使用 Python 标准库 `xml.etree.ElementTree`，无需额外安装。

## 练习

1. 使用 `regex_findall` 提取文本中的所有数字
2. 使用 `http_get` 和 `json_parse` 获取 API 数据
3. 使用 `map` 和 `filter` 处理列表数据
4. 使用 `date_add` 计算一周后的日期
5. 使用 `mean` 和 `stddev` 计算统计数据
6. 使用 `walk_dir` 遍历目录并统计文件数量
7. 使用 `sha256` 计算文件校验和
8. 使用 `yaml_load` 和 `yaml_save` 管理配置文件

---

# 教程 11: 构建多 Agent 系统

> 完整案例：从需求到实现

## 案例：智能客服系统

### 需求

构建一个智能客服系统，能够：
1. 理解用户问题
2. 分类问题类型
3. 根据类型调用不同专业 Agent
4. 生成满意回复

## 第一步：定义 Agent

```helen
// 问题分类器
agent QuestionClassifier {
    description "Classify customer questions into categories"
    model "gpt-4"
    temperature 0.1
    prompt """
    Classify the question into one of:
    - product: Questions about products or features
    - billing: Questions about pricing, invoices, payments
    - technical: Technical issues, bugs, errors
    - account: Account management, login, settings
    - general: Everything else
    """
}

// 产品专家
agent ProductExpert {
    description "Answer product-related questions"
    model "gpt-4"
    temperature 0.3
    prompt """
    You are a product expert. Answer questions about our products
    clearly and helpfully. If unsure, say so honestly.
    """
}

// 账单专家
agent BillingExpert {
    description "Handle billing inquiries"
    model "gpt-4"
    temperature 0.1
    prompt """
    You are a billing expert. Help customers with pricing, invoices,
    and payment issues. Be precise with numbers.
    """
}

// 技术支持
agent TechSupport {
    description "Provide technical support"
    model "gpt-4"
    temperature 0.2
    prompt """
    You are a technical support engineer. Help users resolve technical
    issues step by step. Ask clarifying questions if needed.
    """
}

// 回复润色器
agent ResponsePolisher {
    description "Polish responses to be friendly and professional"
    temperature 0.5
    prompt """
    Rewrite the response to be warm, professional, and helpful.
    Keep the technical accuracy but improve the tone.
    """
}
```

## 第二步：实现路由逻辑

```helen
main {
    let customer_question = "How do I reset my password?"

    // 第一步：分类
    llm if "Classify customer question" {
        branch "product" {
            print("📦 Product question")
            let answer = ProductExpert(customer_question)
        }
        branch "billing" {
            print("💰 Billing question")
            let answer = BillingExpert(customer_question)
        }
        branch "technical" {
            print("🔧 Technical question")
            let answer = TechSupport(customer_question)
        }
        branch "account" {
            print("👤 Account question")
            let answer = TechSupport(customer_question)
        }
        default {
            print("📋 General question")
            let answer = "Thank you for your question. Let me help you."
        }
    }

    // 第三步：润色回复
    let polished = ResponsePolisher(answer)

    // 第四步：输出
    print("\n--- Response to Customer ---")
    print(polished)
}
```

## 第三步：添加并发优化

```helen
// 优化的版本：并发查询知识库
main {
    let question = "How do I reset my password?"

    // 并发获取上下文
    let kb_task = async KnowledgeBase(question)
    let history_task = async HistoryLookup("password reset")

    // 先分类（串行，需要结果路由）
    llm if "Classify customer question" {
        branch "technical" {
            // 等待上下文
            let context = await [kb_task, history_task]
            let full_context = context[0] + "\n" + context[1]
            let answer = TechSupport(question + "\nContext: " + full_context)
        }
        default {
            let answer = "I'll help you with that."
        }
    }

    let polished = ResponsePolisher(answer)
    print(polished)
}
```

## 第四步：添加错误处理

```helen
main {
    let question = "How do I reset my password?"

    try {
        llm if "Classify customer question" {
            branch "technical" {
                let answer = TechSupport(question)
                let polished = ResponsePolisher(answer)
                print(polished)
            }
            default {
                print("I'll help you with that.")
            }
        }
    } catch TimeoutError err {
        print("⏱️ The service is taking too long. Please try again.")
    } catch RuntimeError err {
        print("⚠️ Something went wrong: " + str(err))
        print("A human agent will contact you shortly.")
    } catch {
        print("❌ An unexpected error occurred.")
        print("Please try again or contact support@company.com")
    }
}
```

## 项目结构

```
customer-service/
├── main.helen
├── agents/
│   ├── classifier.helen
│   ├── product_expert.helen
│   ├── billing_expert.helen
│   ├── tech_support.helen
│   └── polisher.helen
├── utils/
│   └── formatting.helen
└── config.json
```

## 运行与验证

```bash
# 验证
$ helen check customer-service/main.helen
✓ customer-service/main.helen: OK

# 运行
$ helen run customer-service/main.helen
🔧 Technical question


--- Response to Customer ---
To reset your password, please follow these steps...

# 生成文档
$ helen doc customer-service/main.helen --format markdown
```

## 总结

通过这个案例，你学会了：
1. ✅ 声明多个 Agent 及其配置
2. ✅ 使用 `llm if` 进行智能路由
3. ✅ 使用 `async` + `await` 并发获取上下文
4. ✅ 使用 `try-catch` 处理 LLM 异常
5. ✅ 组织多文件项目结构

---

# 教程 12: 安全沙箱

> Helen 运行时内置安全机制，保护系统资源免受恶意或意外操作的影响

## 概述

Helen 的安全沙箱（`helen/runtime/security.py`）为所有系统交互提供防护层：

```
Helen 程序
    │
    ▼
┌─────────────────────┐
│   安全沙箱           │  ← 所有系统调用经过此层
│  validate_path()    │
│  validate_url()     │
│  validate_command() │
└──────────┬──────────┘
           │
           ▼
      操作系统资源
```

## 路径安全

所有文件操作（`read_file`、`write_file`、`import`）都经过路径验证：

```python
# 安全的路径验证规则
validate_path(path, base_dir=".")
```

| 规则 | 说明 |
|------|------|
| 基础目录限制 | 路径必须在 `base_dir` 内，阻止 `../` 遍历 |
| 敏感路径阻止 | `/etc/shadow`、`/proc`、`/sys`、`/dev` 被禁止 |
| 符号链接解析 | 先解析符号链接再验证，防止绕过 |
| 绝对路径检查 | 绝对路径也需要通过安全检查 |

```helen
# 这些操作会被安全沙箱阻止
read_file("/etc/shadow")       # ❌ SecurityError: sensitive path
read_file("../../etc/passwd")  # ❌ SecurityError: path traversal
```

## URL 过滤 (SSRF 防护)

网络请求（`http_get`、`http_post`、`web_fetch`）经过 URL 验证：

```python
validate_url(url, allow_private=False)
```

| 规则 | 说明 |
|------|------|
| 协议限制 | 仅允许 `http://` 和 `https://` |
| 私有 IP 阻止 | `10/8`、`172.16/12`、`192.168/16`、`127/8` 被禁止 |
| IPv6 保护 | 阻止 `::1`（回环）、`fc00::/7`（ULA）、`fe80::/10`（link-local） |
| DNS 重绑定 | 解析后再次验证 IP（防止 DNS rebinding 攻击） |

```helen
# SSRF 防护示例
http_get("http://169.254.169.254/latest/meta-data/")  # ❌ SecurityError: private IP
http_get("https://example.com/api")                     # ✅ OK
```

## 命令安全

`shell_exec` 工具集成命令安全检查：

```python
validate_command(command)
```

| 阻止的命令 | 原因 |
|-----------|------|
| `rm -rf /` | 删除根目录 |
| `mkfs.*` | 格式化磁盘 |
| `dd if=/dev/zero of=/dev/sda` | 覆盖磁盘 |
| `:(){ :\|:& };:` | Fork bomb |
| `chmod -R 777 /` | 权限破坏 |

此外，`shell_exec` 默认使用 `shell=False`（列表参数模式），防止命令注入：

```helen
# 安全的命令执行（推荐）
shell_exec(["ls", "-la", "/tmp"])  # ✅ 列表参数，无注入风险

# 不安全的命令执行（需要显式启用）
shell_exec("ls -la /tmp", shell=True)  # ⚠️ 需要显式 opt-in
```

## 资源限制

| 资源 | 限制 | 常量 |
|------|------|------|
| 文件读取大小 | 16 MB | `MAX_READ_SIZE` |
| 文件写入大小 | 64 MB | `MAX_WRITE_SIZE` |
| HTTP 下载大小 | 100 MB | `MAX_DOWNLOAD_SIZE` |
| HTTP 响应大小 | 8 MB | `MAX_RESPONSE_SIZE` |
| 命令超时 | 300 秒 | `MAX_COMMAND_TIMEOUT` |
| HTTP 请求超时 | 30 秒 | `DEFAULT_REQUEST_TIMEOUT` |

## 环境变量保护

`env_list` 函数自动掩码敏感环境变量：

```helen
let env = env_list()
# PASSWORD=********  (自动掩码)
# API_KEY=********   (自动掩码)
# HOME=/home/user    (正常显示)
```

掩码规则：键名包含 `PASSWORD`、`SECRET`、`TOKEN`、`API_KEY`、`PRIVATE_KEY` 的值会被替换为 `********`。

## 进程安全

| 功能 | 限制 |
|------|------|
| `kill(pid, signal)` | PID ≤ 1 或当前进程被阻止 |
| 允许的信号 | 仅 SIGTERM、SIGINT、SIGHUP、SIGUSR1、SIGUSR2 |

## 安全错误处理

安全违规抛出 `SecurityError` 异常：

```helen
try {
    read_file("/etc/shadow")
} catch SecurityError as e {
    print("安全违规: " + e.message)
    # 输出: 安全违规: Path '/etc/shadow' is in sensitive directory
}
```

## 总结

Helen 安全沙箱提供多层防护：

1. ✅ **路径验证** — 阻止敏感文件访问和目录遍历
2. ✅ **URL 过滤** — SSRF 防护，阻止私有网络访问
3. ✅ **命令安全** — 阻止危险命令，默认防注入
4. ✅ **资源限制** — 防止资源耗尽攻击
5. ✅ **环境掩码** — 保护敏感凭据
6. ✅ **进程保护** — 限制信号和 PID 操作

这些安全机制对所有 Helen 程序透明生效，无需额外配置。

## 下一步

- 探索 LSP 在 IDE 中的补全和诊断功能
- 使用 `helen repl` 快速原型
- 阅读设计哲学深入了解语言理念
- 查看错误码参考排查问题
