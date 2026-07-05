# Helen 语言完整教程

> **Helen** — A Prompt-first Agent Programming Language
> 版本: v1.14 | 状态: Phase 0-10 + 中文语法 + Agent 隔离 + Shared Store + Channel | 测试: 2400+ passed

---

<!-- TABLE OF CONTENTS -->

| 章节 | 主题 |
|------|------|
| [01](#教程-01-入门指南) | 安装、配置、Hello World、REPL、中文编程(v1.9)、代码验证、文档生成 |
| [02](#教程-02-变量与类型) | let/const/shared let(v1.10)、数据类型、类型注解、运算、集合操作、子脚本/字段赋值(v1.10) |
| [03](#教程-03-函数) | fn 声明、参数、返回值、递归、Agent 内部函数、作用域、闭包(v1.7) |
| [04](#教程-04-控制流) | if/for/while/match、break/continue、try-catch、管道操作符(v1.8)、模式匹配增强(v1.8)、短路求值(v1.10) |
| [05](#教程-05-agent-编程) | agent 声明、配置、参数、调用、协议(v1.7)、作用域隔离(v1.10)、隔离注解(v1.12)、Shared Store(v1.12)、Channel(v1.13) |
| [06](#教程-06-llm-语句) | llm act/if、对话历史、流式输出（on_chunk/on_complete 回调，v1.14 统一到 llm act）、异步 HTTP(v1.10) |
| [07](#教程-07-异步编程) | async、await、并发 Agent 调用、HTTP 异步方法(v1.10) |
| [08](#教程-08-模块与导入) | import、多格式、跨文件复用、路径安全、shared let 导入(v1.10) |
| [09](#教程-09-python-ffi) | Python 库导入、类型转换、调用 Python 函数 |
| [10](#教程-10-标准库参考) | 186 个内置函数，覆盖 AI 应用开发所有核心需求 |
| [11](#教程-11-构建多-agent-系统) | 多 Agent 协作、工具调用、Agent 模式、Shared Store 协作(v1.12)、Channel 通信(v1.13) |
| [12](#教程-12-测试框架与-tdd) | 测试 API、断言函数、Expect 链式、TDD 工作流、监听模式 |
| [13](#教程-13-技能系统) | 技能概念、三层搜索、创建技能、REPL 技能感知 |
| [14](#教程-14-ai-原生可观测性) | 调试、日志、追踪、性能监控、AI 原生观测能力 |
| [15](#教程-15-质量评估-7-维框架) | 7 维质量评估、评分等级、CLI 命令、API 接口 |

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
$ helen hello.helen
Hello, World!
```

## VS Code 集成

Helen 提供完整的 VS Code 支持，包括语法高亮、代码补全和实时错误检查。

### 第一步：安装扩展

**方法一：从 VSIX 安装（推荐）**

```bash
cd ~/helen/vscode-extension
npm install
npm run compile
npx vsce package
```

然后在 VS Code 中：
1. 按 `Ctrl+Shift+P` 打开命令面板
2. 输入 `Extensions: Install from VSIX...`
3. 选择生成的 `helen-language-1.8.0.vsix` 文件

**方法二：开发模式**

```bash
# 复制扩展目录到 VS Code 扩展目录
cp -r vscode-extension ~/.vscode/extensions/helen-language
```

### 第二步：确保 Helen 已安装

```bash
# 确认 helen 命令可用
which helen
helen help
```

### 第三步：开始使用

1. **打开 .helen 文件** — 自动获得语法高亮
2. **LSP 自动启动** — 提供实时错误检查、代码补全、跳转定义

### 功能一览

| 功能 | 操作 |
|------|------|
| 语法高亮 | 自动 |
| 实时诊断 | 自动（红/黄波浪线） |
| 代码补全 | 输入时自动弹出，或按 `Ctrl+Space` |
| 跳转定义 | `Ctrl+Click` 或 `F12` |
| 重启 LSP | `Ctrl+Shift+P` → `Helen: Restart Language Server` |

### 快速测试

创建 `test.helen`：

```helen
fn greet(name: string): string {
    return "Hello, " + name + "!"
}

main {
    let msg = greet("Helen")
    print(msg)
}
```

打开后应该看到：
- ✅ 关键字高亮（`fn`, `let`, `main`, `return`）
- ✅ 类型高亮（`string`）
- ✅ 函数名高亮（`greet`, `print`）
- ✅ 输入 `pri` 时弹出补全（`print`）
- ✅ `Ctrl+Click` 函数名跳转到定义

### 配置选项

在 VS Code 设置（`Ctrl+,`）中搜索 `helen`：

| 设置 | 说明 | 默认值 |
|------|------|--------|
| `helen.lsp.path` | LSP 服务器路径 | `"helen"` |
| `helen.lsp.args` | LSP 参数 | `["lsp"]` |
| `helen.lsp.enabled` | 启用/禁用 LSP | `true` |

如果 helen 不在 PATH 中，配置自定义路径：

```json
{
  "helen.lsp.path": "/home/user/.local/bin/helen"
}
```

### 故障排除

**LSP 没启动？**

1. 检查 VS Code 输出面板：`View` → `Output` → 选择 `Helen Language Server`
2. 确认 helen 命令可用：`which helen`
3. 如果路径不对，修改 `helen.lsp.path` 设置
4. 重启 LSP：`Ctrl+Shift+P` → `Helen: Restart Language Server`

**语法高亮不工作？**

1. 确保文件扩展名为 `.helen`
2. 检查右下角语言模式，手动设置为 "Helen"

详见 [VS Code 扩展文档](../toolchain/vscode.md)。

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

**流式输出**：助手使用 `llm act` 的 `on_chunk` 回调流式输出回答，内容逐 chunk 实时显示，无需等待完整响应。

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

---

## 中文编程 (v1.9)

Helen 支持中英双语关键字，中文关键字与英文关键字映射到相同的 TokenType，可以自由混用。

```helen
// 纯中文 Hello World
主函 {
    print("你好，世界！")
}

// 中文变量和函数
让 姓名 = "张三"
函数 打招呼(名字: str) {
    print("你好, " + 名字)
}
打招呼(姓名)

// 中英混合
let 年龄 = 30
如果 年龄 >= 18 {
    print("成年")
} 否则 {
    print("未成年")
}
```

**中文关键字映射**：`让`=let, `函数`=fn, `如果`=if, `否则`=else, `返回`=return, `真`=true, `假`=false, `空`=null 等 44 个。

---

## 练习

1. 创建一个打印你名字的 Helen 程序（试试用中文关键字）
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

### 中文类型名 (v1.10)

`list` 和 `map` 支持中文别名：`列表`、`映射`。

```helen
函数 获取列表(): 列表 {
    返回 [1, 2, 3]
}

函数 获取映射(): 映射 {
    返回 {"a": 1}
}
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

Helen 使用 `&&`（与）、`||`（或）、`!`（非）作为逻辑操作符：

```helen
let and = true && false   // false
let or = true || false    // true
let not = !true           // false

// 实际使用示例
let x = 5
if x > 0 && x < 10 {
    print("x is between 0 and 10")
}

if !path_exists(file) {
    print("File not found")
}
```

**注意**：Helen 不使用 `and`、`or`、`not` 关键字，而是使用符号 `&&`、`||`、`!`。

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

### 列表方法

Helen 的列表基于 Python list，自动支持所有常用方法：

```helen
let items = [1, 2, 3]

// 添加元素
items.append(4)           // [1, 2, 3, 4]
items.insert(0, 0)        // [0, 1, 2, 3, 4]
items.extend([5, 6])      // [0, 1, 2, 3, 4, 5, 6]

// 移除元素
items.pop()               // 移除并返回最后一个: 6
items.remove(0)           // 移除第一个值为 0 的元素
items.clear()             // 清空列表

// 查询
let idx = items.index(2)  // 返回元素 2 的索引
let cnt = items.count(3)  // 返回元素 3 出现的次数

// 排序与反转
let unsorted = [3, 1, 4, 1, 5]
unsorted.sort()           // [1, 1, 3, 4, 5]
unsorted.reverse()        // [5, 4, 3, 1, 1]

// 复制
let copy = items.copy()   // 浅拷贝
```

**可用方法列表**：
| 方法 | 说明 |
|------|------|
| `append(x)` | 在末尾添加元素 |
| `extend(iterable)` | 扩展列表 |
| `insert(i, x)` | 在位置 i 插入元素 |
| `remove(x)` | 移除第一个值为 x 的元素 |
| `pop([i])` | 移除并返回位置 i 的元素（默认末尾） |
| `clear()` | 清空列表 |
| `index(x)` | 返回第一个值为 x 的索引 |
| `count(x)` | 返回 x 出现的次数 |
| `sort()` | 原地排序 |
| `reverse()` | 原地反转 |
| `copy()` | 浅拷贝 |

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

## 闭包与匿名函数（v1.7+）

Helen 支持闭包（closures）和匿名函数（anonymous functions），允许你创建内联函数并捕获外部作用域的变量。

### 匿名函数

使用 `fn(params) { body }` 语法创建匿名函数：

```helen
// 匿名函数赋值给变量
let add = fn(a, b) { return a + b }
print(add(2, 3))  // 5

// 直接作为参数传递
let doubled = map([1, 2, 3], fn(x) { return x * 2 })
print(doubled)  // [2, 4, 6]

let evens = filter([1, 2, 3, 4, 5], fn(x) { return x % 2 == 0 })
print(evens)  // [2, 4]
```

### 闭包

闭包可以捕获定义时的环境，在后续调用中访问外部变量：

```helen
// 闭包捕获外部变量
fn make_adder(x) {
    return fn(y) { return x + y }
}

let add5 = make_adder(5)
print(add5(10))  // 15
print(add5(20))  // 25

// 闭包在实际应用中
fn make_multiplier(factor) {
    return fn(x) { return x * factor }
}

let double = make_multiplier(2)
let triple = make_multiplier(3)

print(double(5))   // 10
print(triple(5))   // 15
```

### 与高阶函数配合

闭包与 `map`、`filter`、`reduce` 等高阶函数配合使用：

```helen
let nums = [1, 2, 3, 4, 5]

// 使用闭包进行数据转换
let squared = map(nums, fn(n) { return n * n })
print(squared)  // [1, 4, 9, 16, 25]

// 使用闭包进行过滤
let large = filter(nums, fn(n) { return n > 3 })
print(large)  // [4, 5]

// 使用闭包进行聚合
let sum = reduce(nums, fn(acc, n) { return acc + n }, 0)
print(sum)  // 15

// 链式调用
let result = nums
    |> filter(fn(n) { return n % 2 == 0 })
    |> map(fn(n) { return n * 10 })
print(result)  // [20, 40]
```

### 注意事项

- 闭包捕获的是变量的**引用**，不是值
- 匿名函数可以访问定义时的所有外部变量
- 闭包可以用于创建工厂函数、回调函数等模式

## 函数别名 (v1.10)

`alias` 语句可以给现有的函数（stdlib 或用户定义）创建额外的名字。

```helen
// 给 stdlib 起自定义别名
alias len as 我的长度
alias print as 输出

// 给用户函数起别名
函数 greet(name: str): str {
    返回 "Hello, " + name
}
alias greet as 打招呼

// 中文关键字 `别名` 等价
别名 sort as 排序
```

Helen 的 stdlib 已内置 230+ 个中文别名（`长度`、`打印`、`排序` 等），启动时自动加载，可以直接使用。所有 locale 的别名表启动时全量加载，无论 locale 设置。详见 [教程 10: 标准库参考](#教程-10-标准库参考)。

## 练习

1. 编写一个计算斐波那契数列的递归函数
2. 编写一个函数，接受列表并返回最大值
3. 编写一个函数，判断一个字符串是否为回文
4. 使用闭包实现一个计数器函数 `make_counter()`，每次调用返回递增的值
5. 使用 `map` 和匿名函数将列表中的所有字符串转换为大写

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

### 范围匹配

使用 `..` 运算符匹配数值范围（包含边界）：

```helen
let score = 85

match score {
    case 90..100 { print("A") }
    case 80..89 { print("B") }
    case 70..79 { print("C") }
    case 60..69 { print("D") }
    default { print("F") }
}
// 输出: B
```

**注意**：范围运算符 `..` 不会与浮点数混淆。`1..10` 被解析为范围，`1.5` 被解析为浮点数。

### 守卫条件

使用 `if` 添加额外条件判断：

```helen
let x = 25

match x {
    case 21..30 if x == 25 { print("exactly 25") }
    case 21..30 { print("other in range") }
    default { print("out of range") }
}
// 输出: exactly 25
```

守卫条件在范围匹配之后求值，只有两者都满足才会执行对应的 case 块。

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

### 捕获标准库异常 (v1.9+)

标准库函数抛出的 Python 异常（`TypeError`、`ValueError`、`FileNotFoundError` 等）会被自动包装为 `RuntimeError`，可用 try-catch 捕获：

```helen
try {
    let x = len(42)        // Python TypeError
} catch RuntimeError err {
    print(err.message)     // "Python TypeError: object of type 'int' has no len()"
}

try {
    let data = read_file("/nonexistent/path")
} catch RuntimeError err {
    // 通过 err.message 中的 "Python FileNotFoundError" 前缀区分异常类型
    print("File error: " + err.message)
}
```

异常消息格式为 `"Python <类型名>: <原始消息>"`，可在 catch 块中通过消息前缀区分具体的 Python 异常类型。

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

**注意**：三引号字符串（`"""..."""`）会自动去除公共前导空白（auto-dedent），使得在代码中缩进的多行字符串在运行时保持整洁。例如上面的 prompt 在运行时不会包含前导空格。

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
    tools = ["web_search", "web_fetch", "read_file"]
    prompt "Research the given topic thoroughly."
}

agent Coder {
    description "Code writer"
    tools = ["write_file", "shell_exec", "calculate"]
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

## functions 块与 tools 白名单（两层授权模型）

Agent 的能力管理采用**两层授权**：

- `functions {}` 块声明 agent 的**全部能力**——`main {}` 的 Helen 代码可以调用其中任意函数。
- `tools = [...]` 是 **LLM 可见性的唯一白名单**——只有列表中的名字对 LLM 可见，可以被 LLM 在 `llm act` 中自主调用。
- **不写 `tools`** 时，LLM 没有任何工具可用（除内置的 `load_skill`）。

`tools` 里的名字**统一解析**：先在 `functions {}` 块里查（Helen 函数），找不到再查 Python 工具注册表（`web_search`、`read_file` 等）。

### 示例

```helen
agent CodeAnalyzer {
    description "Analyze code quality"
    model "gpt-4"
    
    // 白名单：LLM 可以调用这 3 个函数
    tools = ["count_lines", "find_todos", "calculate_complexity"]
    
    // 全部能力：functions 块还可以放 main 内部使用的私有函数
    functions {
        fn count_lines(code: str): int {
            return len(split(code, "\n"))
        }
        
        fn find_todos(code: str): list {
            let lines = split(code, "\n")
            let todos = []
            for line in lines {
                if regex_test("TODO|FIXME", line) {
                    todos.append(line)
                }
            }
            return todos
        }
        
        fn calculate_complexity(code: str): int {
            let keywords = ["if", "for", "while", "match"]
            var complexity = 0
            for kw in keywords {
                complexity = complexity + count(code, kw)
            }
            return complexity
        }
        
        // 私有函数：main 可以调，LLM 看不到（没列在 tools 里）
        fn internal_helper() { ... }
    }
    
    prompt """
    分析以下代码的质量：
    {{code}}
    
    你可以调用以下工具函数：
    - count_lines(code: str): 统计代码行数
    - find_todos(code: str): 查找 TODO 注释
    - calculate_complexity(code: str): 估算代码复杂度
    """
    
    main {
        // main 可以调用 functions 里任意函数（不受 tools 限制）
        internal_helper()
        llm act "..."
    }
}
```

### 混合使用 Helen 函数与 Python 工具

`tools` 白名单可以同时包含 Helen 函数和 Python 工具：

```helen
agent HybridAgent {
    description "Hybrid agent with both Helen and Python tools"
    
    // 统一白名单：Helen 函数 + Python 工具
    tools = ["search_local_docs", "web_search", "calculate"]
    
    functions {
        // Helen 自定义工具（LLM 可见，因为在 tools 里）
        fn search_local_docs(query: str): str {
            let results = read_file("docs/index.txt")
            return filter(results, fn(line) { return contains(line, query) })
        }
    }
    
    prompt "..."
    main { llm act "..." }
}
```

### 类型推断

函数参数的类型注解会被转换为 JSON Schema：

| Helen 类型 | JSON Schema 类型 |
|-----------|------------------|
| `str` | `string` |
| `int`, `integer` | `integer` |
| `float`, `number` | `number` |
| `bool`, `boolean` | `boolean` |
| `list`, `array` | `array` |
| `map`, `dict`, `object` | `object` |

没有类型注解的参数默认为 `string`。

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
        let default_format = "formal"
        const MAX_LENGTH = 1000
        
        fn validate_input(s: str): bool {
            return len(s) > 0
        }
        
        fn format_output(text: str): str {
            if default_format == "formal" {
                return text.upper()
            }
            return text
        }
    }
    
    main {
        if validate_input(text) {
            let result = llm act    // bare form：自动使用渲染后的 prompt
            return format_output(result)
        }
        return "输入为空"
    }
}

// 调用方式（推荐函数式调用）：
let translated = Translator(text="Hello", target="French")
// 函数式调用：let translated = Translator(text="Hello", target="French")
```

**functions 块中的变量定义**：

`functions {}` 块现在支持 `let` 和 `const` 声明，这些变量在 agent 的所有函数中可见：

```helen
agent MyAgent {
    description "Example agent"
    prompt "..."
    
    functions {
        let config = "default"
        const MAX_RETRIES = 3
        
        fn get_config(): str {
            return config  // ✅ 可以访问
        }
        
        fn retry() {
            for i in range(MAX_RETRIES) {
                print("Retry " + str(i))
            }
        }
    }
}
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

Agent 使用函数式调用，像调用普通函数一样：

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

### 函数式调用的优势

```helen
main {
    // 简洁直观
    let result = MyAgent("input")
    
    // 可以在表达式中使用
    if contains(Analyzer(text), "error") {
        print("问题检测")
    }
    
    // 可以链式调用
    let processed = Cleaner(Parser(raw_data))
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

main {
    let email = "URGENT: Server down in production!"
    
    let category = EmailClassifier(email)
    
    if category == "urgent" {
        print("🚨 URGENT email detected!")
        let response = UrgentResponder(email)
        print(response)
    } else if category == "meeting" {
        print("📅 Meeting request")
    } else if category == "informational" {
        print("📧 FYI email")
    } else {
        print("🗑️ Spam, ignoring")
    }
}
```

## Shared Store — 受控的共享可变状态 (v1.12)

`shared let` 限制为值类型（int/float/str/bool），无法共享引用类型（list、dict）。`shared store` 填补了这个空缺，为跨 agent 共享可变引用类型提供结构化方式。

### 基本语法

```helen
shared store Cache {
    data: dict = {}
    _hits: int = 0  // 私有字段（_前缀），agent 不可直接访问

    fn get(key): any {
        _hits += 1
        return data[key]
    }

    fn set(key, value) { data[key] = value }
    fn size(): int { return len(data) }
    fn hits(): int { return _hits }
}
```

### 在 Agent 中使用

```helen
agent Worker(cache: Cache) {
    main {
        cache.set("user:1", {name: "Alice"})
        print(cache.get("user:1"))  // {name: "Alice"}
        print(cache.size())         // 1
        // cache._hits = 0          // ❌ 私有字段不可访问
    }
}
```

### 线程安全

Shared Store 内部使用 RLock 保护所有字段访问，多个 agent 可以安全地并发访问：

```helen
shared store Counter { count: int = 0 }

agent Worker(counter: Counter) {
    main {
        for i in range(100) {
            counter.count = counter.count + 1  // 线程安全
        }
    }
}

main {
    let counter = Counter
    async call Worker(counter)
    async call Worker(counter)
    await []
    print(counter.count)  // 200
}
```

## Channel 通道 — Agent 间通信 (v1.13)

Channel 为 agent 间通信提供类型安全的结构化方式。语法与 shared store 一致，语义上表示通信端点。

### 基本语法

```helen
channel TaskQueue {
    pending: list = []

    fn enqueue(task) { pending.append(task) }
    fn dequeue(): any { return pending.shift() }
    fn size(): int { return len(pending) }
    fn is_empty(): bool { return len(pending) == 0 }
}
```

### 中文语法

```helen
通道 任务队列 {
    待处理: list = []

    fn 入队(任务) { 待处理.append(任务) }
    fn 出队(): any { 返回 待处理.shift() }
    fn 大小(): int { 返回 len(待处理) }
}
```

### Channel vs Shared Store

| 特性 | Shared Store | Channel |
|------|-------------|---------|
| 关键字 | `shared store` | `channel` |
| 中文 | `共享 仓库` | `通道` |
| 语义 | 共享状态容器 | 通信端点 |
| 运行时 | `SharedStore` 类 | 复用 `SharedStore` |
| 线程安全 | RLock | RLock |
| 私有字段 | `_` 前缀 | `_` 前缀 |

## Agent 隔离注解 (v1.12)

Agent 声明前可添加 `@open`/`@strict`/`@sandbox` 隔离注解：

```helen
@open agent Permissive {
    // 可访问模块 let
    main { print(module_var) }
}

@sandbox agent Safe {
    // 禁用外部工具，禁止 shared let
    // 只能访问 params 和 const
    main { llm act "simple task" }
}
```

| 隔离级别 | 模块 let | 模块 const | shared let | 外部工具 |
|----------|----------|------------|------------|----------|
| 标准 (默认) | ❌ | ✅ | ✅ | ✅ |
| `@open` | ✅ | ✅ | ✅ | ✅ |
| `@strict` | ❌ | ✅ | ✅ (深拷贝) | ✅ |
| `@sandbox` | ❌ | ✅ | ❌ | ❌ |

---

## 练习

1. 创建一个 Agent，描述为"判断文本情感"，测试不同输入
2. 创建一个 Agent 配置 temperature 为 0，观察输出稳定性
3. 创建一个多 Agent 系统：分类器 + 响应器 + 总结器
4. 创建一个 shared store 用于在多个 Agent 之间共享计数器
5. 创建一个 channel 作为任务队列，实现生产者-消费者模式
6. 使用 `@sandbox` 注解创建一个受限 Agent，验证其无法访问 shared let

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

## llm act 流式输出 — on_chunk / on_complete 回调

`llm act` 支持可选的 `on_chunk` 和 `on_complete` 回调，实现流式输出，适用于长文本生成场景。

**v1.14 变更**: `llm stream` 关键字已删除，流式功能统一合并到 `llm act`。旧语法 `llm stream "..." on_chunk handle` 现在写为 `llm act "..." on_chunk handle`。

### 基本用法

通过 `on_chunk` 回调逐 chunk 处理 LLM 响应：

```helen
fn print_chunk(chunk: str) {
    stream_print(chunk)
}

main {
    llm act "Write a short poem about programming" on_chunk print_chunk
}
```

默认行为：不提供 `on_chunk` 时，`llm act` 等待完成后返回完整文本；提供 `on_chunk` 后，每个 chunk 实时传递给回调函数。

### 带回调函数

使用 `on_chunk` 指定回调函数，自定义处理每个 chunk：

```helen
fn handle_chunk(chunk) {
    stream_print("[" + chunk + "]")
}

main {
    llm act "Explain recursion in one paragraph" on_chunk handle_chunk
}
```

使用 `on_complete` 指定流式传输完成后的回调：

```helen
fn handle_chunk(chunk) {
    print(chunk, end="")
}

fn on_complete() {
    print("\n\n✅ 流式传输完成")
}

main {
    llm act "Write a short story" on_chunk handle_chunk on_complete on_complete
}
```

`on_complete` 回调在流式传输完成后调用，适合用于：
- 显示完成提示
- 记录统计信息（如总 token 数）
- 触发后续操作

### 在 agent 中使用

在 agent 内，`llm act` 自动使用 agent 的配置（model、temperature、prompt），配合回调实现流式输出：

```helen
agent Poet(topic: str) {
    description "Write poetry"
    temperature 0.9
    prompt """
    Write a poem about: {{topic}}
    """

    main {
        fn print_chunk(chunk: str) { stream_print(chunk) }
        llm act on_chunk print_chunk    // bare form：使用渲染后的 prompt
    }
}
```

### 动态 prompt

```helen
fn print_chunk(chunk: str) {
    stream_print(chunk)
}

main {
    let topic = "the beauty of recursion"
    llm act "Write a haiku about " + topic on_chunk print_chunk
}
```

### 与其他 LLM 语句对比

| 语句 | 用途 | 输出方式 |
|------|------|----------|
| `llm act` | 让 LLM 执行任务 | 等待完成后返回（或通过 on_chunk 流式输出） |
| `llm if` | LLM 分类路由 | 等待完成后执行分支 |

## 对比：何时使用哪个？

| 场景 | 使用 |
|---|---|
| 需要 LLM 返回文本 | `llm act` |
| 需要 LLM 做分类决策 | `llm if` |
| 需要 LLM 从选项中选择并执行代码 | `llm if` + `branch` |
| 需要实时输出生成过程 | `llm act` + `on_chunk` 回调 |
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
    tools = ["web_search", "read_file"]
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

Helen 支持 `for await` 语法异步迭代流式响应。Agent 声明 `streaming true` 后，调用返回 `StreamingResponse` 对象，可在 `for await` 中逐 chunk 处理：

```helen
agent Streamer(topic: str) {
    description "Stream a long response"
    streaming true
    prompt "Write a detailed essay about: {{topic}}"
}

main {
    let response = async Streamer("the history of computing")
    for await chunk in response {
        stream_print(chunk)
    }
}
```

### 流式过滤与转换

`for await` 支持在循环体中对 chunk 进行自定义处理：

```helen
main {
    let response = async Streamer("long essay")
    
    // 过滤：只处理长 chunk
    for await chunk in response {
        if len(chunk) > 10 {
            stream_print(chunk)
        }
    }
}
```

### 流式聚合

```helen
main {
    let response = async Streamer("essay")
    let total_length = 0
    for await chunk in response {
        total_length = total_length + len(chunk)
    }
    print("Total length: " + total_length)
}
```

`for await` 适用于：
- 流式 LLM 响应（`streaming true` agent）
- 异步数据源
- 大文件逐行处理

**注意**：`for await` 只能在 `async` 上下文中使用。Agent 必须声明 `streaming true` 才能返回可迭代的流式响应。

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
        fn calculate_stats(): map {
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
| 字符串处理 | ✅ 36 个 string 函数 | ✅ 可用 Python re 等 |
| 数学计算 | ✅ 15 个 math 函数 | ✅ 可用 numpy/scipy |
| 文件操作 | ✅ 16 个 file 函数 | ✅ 可用 os/pathlib |
| 网络请求 | ✅ 9 个 network 函数 | ✅ 可用 requests（高级场景） |
| 数据处理 | ✅ 25 个 data 函数（JSON/CSV/HTML/XML） | ✅ 可用 pandas（大数据集） |
| 机器学习 | ❌ 无 | ✅ 可用 torch/tensorflow |

**建议**：优先使用 Helen 原生功能（185 个内置函数覆盖常见需求），需要高级功能（如大数据处理、机器学习）时使用 Python FFI。

## 练习

1. 导入 `math` 模块，计算圆的面积（半径 = 5）
2. 导入 `json` 模块，将 map 转换为 JSON 字符串并解析回来
3. 导入 `os.path` 模块，提取文件路径的目录和文件名
4. 创建一个 Agent，使用 Python 的 `math` 模块进行复杂计算

---

# 教程 10: 标准库参考

> 186 个内置函数，覆盖 AI 应用开发的所有核心需求

## 概览

Helen 标准库提供 186 个内置函数，分为 9 大类别：

| 类别 | 函数数 | 功能 |
|------|--------|------|
| **Core** | 11 | 类型转换、通用操作 |
| **String** | 37 | 字符串处理、正则、文本分析、模板插值 |
| **Data** | 25 | JSON、HTML、CSV、Markdown、YAML、TOML、XML |
| **Collection** | 22 | 列表、字典、集合操作 |
| **Network** | 9 | HTTP 请求、URL 处理 |
| **Time** | 13 | 日期时间、格式化、运算 |
| **Math** | 15 | 数学运算、统计分析 |
| **File** | 16 | 文件读写、目录操作、临时文件 |
| **System** | 16 | 环境变量、进程管理、日志 |
| **Crypto** | 11 | 哈希、随机数 |
| **IO** | 5 | 流式输出控制 |

## 多语言 stdlib (v1.10)

Helen 的 stdlib 支持多语言函数名。每个 stdlib 函数都有英文 canonical 名和本地化别名，启动时全量加载。

### 中文 stdlib 别名

Helen 内置 230+ 个中文别名，覆盖全部 stdlib 分类。例如：

| 英文 | 中文 | 类别 |
|------|------|------|
| `len` | `长度` | Core |
| `print` | `打印` | Core |
| `sort` | `排序` | Collection |
| `filter` | `过滤` | Collection |
| `json_parse` | `json解析` | Data |
| `http_get` | `http获取` | Network |
| `regex_match` | `正则匹配` | String |
| `sha256` | `sha256` | Crypto |

完整列表见 `helen/stdlib/locales/zh.py`。

### 使用示例

```helen
// 直接用中文 stdlib 函数名（不需要任何 import 或 alias）
函数 数据处理() {
    让 原始数据 = [3, 1, 4, 1, 5, 9, 2, 6]
    让 排序后 = 排序(原始数据)
    让 去重后 = 去重(排序后)
    返回 长度(去重后)
}

// 中英混用也完全合法
函数 混合使用() {
    let data = [1, 2, 3]
    let sorted = 排序(data)     // 英文变量 + 中文函数
    return len(sorted)
}
```

### 自定义别名

如果需要给 stdlib 函数起额外的别名，使用 `alias` 语句：

```helen
alias len as 我的长度
alias print as 输出
```

中文关键字 `别名` 等价：

```helen
别名 len as 长度
```

### 设计原则

- **一套机制**：stdlib 别名和用户 `alias` 使用相同的 Environment binding
- **全量加载**：所有 locale 的别名表启动时全部注册，不按 locale 过滤
- **locale 只影响展示**：`~/.helen/config.yaml` 中的 `locale: zh` 只影响 docs/LSP/错误消息的语言，不影响运行时可用的名字
- **扩展新语言**：添加新语言的 stdlib 别名只需创建 `helen/stdlib/locales/<code>.py`

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

## String 函数 (37)

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

// 字符串插值（v1.8.1+）
let template = "Hello, {{name}}! You are {{age}} years old."
let vars = {"name": "Alice", "age": 30}
interpolate(template, vars)
// "Hello, Alice! You are 30 years old."

// 支持嵌套属性访问
let template2 = "User: {{user.name}}, Email: {{user.email}}"
let vars2 = {"user": {"name": "Bob", "email": "bob@example.com"}}
interpolate(template2, vars2)
// "User: Bob, Email: bob@example.com"
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
$ helen customer-service/main.helen
🔧 Technical question


--- Response to Customer ---
To reset your password, please follow these steps...

# 生成文档
$ helen doc customer-service/main.helen --format markdown
```

## 多 Agent 协作模式 (v1.12/v1.13)

### Shared Store 协作

当多个 Agent 需要共享可变状态时，使用 `shared store`：

```helen
shared store Metrics {
    total_requests: int = 0
    error_count: int = 0
    _start_time: str = ""  // 私有字段

    fn record_request() { total_requests += 1 }
    fn record_error() { error_count += 1 }
    fn error_rate(): float {
        if total_requests == 0 { return 0.0 }
        return float(error_count) / float(total_requests)
    }
}

agent RequestHandler(metrics: Metrics) {
    main {
        metrics.record_request()
        try {
            // 处理请求
            llm act "process request"
        } catch {
            metrics.record_error()
        }
    }
}
```

### Channel 通信

当 Agent 之间需要结构化通信时，使用 `channel`：

```helen
channel TaskQueue {
    tasks: list = []
    fn submit(task) { tasks.append(task) }
    fn next(): any { return tasks.shift() }
    fn pending(): int { return len(tasks) }
}

agent Producer(queue: TaskQueue) {
    main {
        queue.submit("task 1")
        queue.submit("task 2")
    }
}

agent Consumer(queue: TaskQueue) {
    main {
        while queue.pending() > 0 {
            let task = queue.next()
            llm act "Process: " + task
        }
    }
}

main {
    let queue = TaskQueue
    async call Producer(queue)
    async call Consumer(queue)
    await []
}
```

## 总结

通过这个案例，你学会了：
1. ✅ 声明多个 Agent 及其配置
2. ✅ 使用 `llm if` 进行智能路由
3. ✅ 使用 `async` + `await` 并发获取上下文
4. ✅ 使用 `try-catch` 处理 LLM 异常
5. ✅ 组织多文件项目结构

---

---

# 教程 13: 技能系统

> 技能概念 / 三层搜索架构 / 创建自定义技能 / REPL 技能感知 / 在 LLM 语句中使用技能

## 什么是技能（Skill）

**技能**是 Helen 的扩展知识单元。每个技能是一个包含 `SKILL.md` 的目录，用 Markdown 描述特定的领域知识、工作流程或操作指南。

技能的核心价值：**让 LLM 在需要时加载专业知识，而不是把所有知识塞进一个巨大的 system prompt。**

```
skills/
├── web-research/
│   └── SKILL.md          # 网络搜索技能
├── code-review/
│   ├── SKILL.md          # 代码审查技能
│   └── templates/
│       └── checklist.md  # 审查清单模板
└── data-analysis/
    ├── SKILL.md          # 数据分析技能
    └── scripts/
        └── visualize.py  # 可视化脚本
```

## 技能目录结构

### 最小结构

一个技能只需要一个 `SKILL.md` 文件：

```
my-skill/
└── SKILL.md
```

### 完整结构

```
my-skill/
├── SKILL.md              # 必需：技能描述和指令
├── references/           # 参考资料（API 文档、规范等）
│   └── api.md
├── templates/            # 模板文件
│   └── config.yaml
├── scripts/              # 辅助脚本
│   └── validate.py
└── assets/               # 其他资源
    └── examples.json
```

## SKILL.md 格式

`SKILL.md` 使用 YAML frontmatter + Markdown body：

```markdown
---
name: web-research
description: Research topics using web search and content extraction
category: research
tags: [search, research, web, information]
version: 1.0.0
author: Helen Community
license: MIT
---

# Web Research Skill

## When to Use
- User asks to search for information online
- Need to find current/recent data
- Research a topic across multiple sources

## Steps
1. Analyze the user's query to extract search terms
2. Use `web_search()` to find relevant pages
3. Use `web_extract()` to read page content
4. Synthesize findings into a clear answer

## Pitfalls
- Don't rely on a single source
- Check publication dates for recency
- Summarize, don't copy-paste
```

### Frontmatter 字段

| 字段 | 必需 | 说明 |
|------|------|------|
| `name` | ✅ | 技能唯一标识（小写，连字符分隔） |
| `description` | ✅ | 一句话描述技能用途 |
| `category` | ❌ | 分类（research, devops, creative 等） |
| `tags` | ❌ | 关键词标签列表（用于技能发现） |
| `version` | ❌ | 技能版本号 |
| `author` | ❌ | 作者信息 |
| `license` | ❌ | 许可证（如 MIT） |

**重要**：`tags` 字段是提升技能命中率的关键。系统会将 tags 注入到 system prompt 中，LLM 根据这些标签更容易发现和加载相关技能。建议使用统一的命名规范（如小写、英文关键词）。

### Markdown Body

正文包含：
- **使用场景**：什么时候应该使用这个技能
- **操作步骤**：具体的工作流程
- **注意事项**：常见陷阱和最佳实践
- **示例**：具体的使用案例

## 三层搜索架构

Helen 使用三层技能搜索，按优先级从高到低：

```
┌─────────────────────────────────────┐
│  🥇 项目级   <project>/.helen/skills/  │  ← 最高优先级
├─────────────────────────────────────┤
│  🥈 用户级   ~/.helen/skills/          │  ← 用户自定义
├─────────────────────────────────────┤
│  🥉 内置级   ~/helen/skills/           │  ← 语言自带（13 个）
├─────────────────────────────────────┤
│  ⚙️ 可选     ~/.hermes/skills/         │  ← Hermes 回退（如已安装）
├─────────────────────────────────────┤
│  ⚙️ 可选     ~/.hermes/hermes-agent/   │  ← Hermes agent（如已安装）
│             skills/                    │
└─────────────────────────────────────┘
```

**优先级规则：**
- 高优先级目录的技能**覆盖**低优先级的同名技能
- 不同名的技能**累加**，全部可用
- 项目级技能适合团队共享的项目特定知识
- Hermes 层为可选扩展，仅在 Hermes 已安装时可用

### 查看可用技能

在 REPL 中使用 `:ask` 命令，技能会自动注入到 LLM 上下文中：

```bash
helen> :ask 列出当前可用的技能
```

LLM 会看到所有 13 个 Helen 内置技能的索引，并能根据需求推荐合适的技能。如果安装了 Hermes，还会额外看到 Hermes 的技能。

## 创建自定义技能

### 示例：创建代码审查技能

**第 1 步：创建目录**

```bash
mkdir -p ~/.helen/skills/code-review
```

**第 2 步：编写 SKILL.md**

```markdown
---
name: code-review
description: Systematic code review with security and quality checks
category: development
tags: [review, code-review, security, quality, checklist]
version: 1.0.0
author: Helen Community
license: MIT
---

# Code Review Skill

## When to Use
- User asks to review code
- Before merging a PR
- Checking code quality

## Review Checklist

### 1. Correctness
- Logic errors, off-by-one, null handling
- Edge cases and boundary conditions

### 2. Security
- Input validation
- No SQL injection, command injection
- Secrets not hardcoded

### 3. Performance
- Unnecessary loops or allocations
- N+1 queries
- Missing indexes

### 4. Maintainability
- Clear naming
- Functions < 50 lines
- No dead code

## Output Format

For each issue found:
- **Severity**: 🔴 Critical / 🟡 Warning / 🟢 Suggestion
- **Location**: file:line
- **Issue**: what's wrong
- **Fix**: how to fix it
```

**第 3 步：验证技能**

```bash
helen> :ask 帮我审查这段代码
```

LLM 会自动加载 `code-review` 技能并按照清单进行审查。

### 示例：项目级技能

为团队项目创建共享技能：

```bash
mkdir -p myproject/.helen/skills/api-conventions
```

```markdown
---
name: api-conventions
description: Our team's API design conventions and patterns
category: project
---

# API Conventions

## Naming
- REST resources: plural nouns (`/users`, `/orders`)
- Actions: POST with verb (`/users/:id/activate`)

## Error Format
```json
{
  "error": {
    "code": "USER_NOT_FOUND",
    "message": "User with id 123 not found"
  }
}
```

## Authentication
- Bearer token in Authorization header
- Token expires after 24 hours
```

这样团队成员在使用 Helen 时，会自动加载项目的 API 规范。

## REPL 技能感知

### `:ask` 命令

REPL 的 `:ask` 命令会自动注入所有可用技能的索引到 LLM 上下文中：

```bash
helen> :ask 如何搜索网络信息？
```

LLM 会：
1. 看到 13 个 Helen 内置技能的索引（如安装了 Hermes，还会看到 Hermes 技能）
2. 识别出 `web-search`、`research` 等相关技能
3. 按照技能中的指导回答问题

### 技能索引格式

注入的技能索引是 XML 格式的摘要：

```xml
<skills>
<skill name="web-search" category="research">
  <description>Search the web for information</description>
  <triggers>search, find, lookup</triggers>
</skill>
...
</skills>
```

这使 LLM 能快速定位相关技能，而不需要加载每个技能的完整内容。

## 在 LLM 语句中使用技能

### `llm act`（含流式回调）

当你在 Helen 代码中使用 `llm act` 时（无论是否带 `on_chunk`/`on_complete` 回调），技能索引会自动注入到 system prompt 中：

```helen
agent Researcher {
    description "Research assistant"
    prompt "You are a research assistant."
}

main {
    let result = llm act Researcher
        "搜索关于量子计算的最新进展"
    print(result)
}
```

LLM 在执行时会看到所有可用技能，并能根据需要参考相关技能的知识。

### 技能与 Agent 的关系

| 概念 | 作用域 | 加载方式 |
|------|--------|----------|
| **Agent prompt** | 单个 Agent | 声明时定义 |
| **技能索引** | 所有 LLM 调用 | 自动注入 |
| **技能完整内容** | 按需 | LLM 判断需要时加载 |

Agent 的 `prompt` 定义角色和行为，技能提供额外的领域知识。两者互补。

## 技能管理最佳实践

### 1. 技能命名

```
✅ web-search, code-review, data-analysis
❌ WebSearch, code_review, dataAnalysis
```

使用小写 + 连字符，简洁明了。

### 2. 技能粒度

```
✅ 一个技能 = 一个明确的任务领域
❌ 一个技能 = 所有事情（太宽泛）
❌ 一个技能 = 一行指令（太细碎）
```

### 3. 技能描述

```markdown
✅ description: "Review code for security vulnerabilities and quality issues"
❌ description: "Does stuff with code"
```

描述越精确，LLM 越能正确选择和使用技能。

### 4. 包含实际示例

```markdown
✅ ## Example
    Input: "SELECT * FROM users WHERE id = " + user_input
    Issue: 🔴 SQL Injection
    Fix: Use parameterized queries

❌ ## Example
    Check for SQL injection.
```

### 5. 分层组织

```
项目级（.helen/skills/）  → 项目特定规范、API 约定
用户级（~/.helen/skills/） → 个人偏好、常用工作流
内置级（helen/skills/）    → 通用技能、语言相关
```

## 内置技能

Helen 自带 13 个内置技能，覆盖常见任务：

| 技能 | 说明 |
|------|------|
| `helen-debugging` | Helen 程序调试 |
| `helen-testing` | Helen 测试编写 |
| `helen-stdlib` | 标准库使用指南 |
| `helen-async` | 异步编程模式 |
| `helen-security` | 安全编程实践 |
| `helen-ffi` | Python FFI 集成 |
| `helen-lsp` | LSP 开发 |
| `helen-contributing` | 贡献指南 |
| `helen-architecture` | 架构设计 |
| `helen-tutorial` | 教程内容 |
| `helen-design` | 设计哲学 |
| `helen-overview` | 语言概览 |
| `helen-llm-runtime` | LLM 运行时 |

这些技能在 REPL 的 `:ask` 命令中自动可用，帮助 LLM 更准确地回答 Helen 相关问题。

## 练习

1. 在 `~/.helen/skills/` 下创建一个 `greeting` 技能，让 LLM 用特定格式打招呼
2. 为当前项目创建 `.helen/skills/` 目录，添加一个项目规范技能
3. 在 REPL 中用 `:ask` 测试你的技能是否被正确感知
4. 编写一个 Helen 程序，使用 `llm act` 的 `on_chunk` 回调调用一个会参考技能的 Agent

## 总结

Helen 技能系统提供：

1. ✅ **模块化知识** — 每个技能独立，按需加载
2. ✅ **三层搜索** — 项目 > 用户 > 内置 > Hermes，灵活覆盖
3. ✅ **自动感知** — `:ask` 和 `llm` 语句自动注入技能索引
4. ✅ **易于创建** — 只需一个 `SKILL.md` 文件
5. ✅ **团队共享** — 项目级技能随代码库分发

技能让 Helen 程序不只是代码，而是**带着专业知识工作的智能 Agent**。

# 教程 14: AI 原生可观测性

> 给 AI 一个它能读懂的"黑匣子"，而不是给人类一个 GDB。

---

## 为什么需要 AI 原生可观测性？

传统调试器（断点、单步执行、变量监视）是为**人类交互式调试**设计的。在 AI 编程场景下，消费调试信息的是 AI Agent，它需要的是**结构化的、可机器消费的上下文**——而不是交互式暂停/恢复。

Helen 的 AI 原生可观测性提供：

| 传统 Debugger | Helen 可观测性 |
|--------------|---------------|
| 断点暂停 | 结构化错误快照 (JSON) |
| 单步执行 | 执行追踪日志 |
| 变量监视 | 调用栈 + 作用域变量 |
| 调用栈面板 | 程序化调用栈追踪 |
| 无 LLM 记录 | LLM 调用审计日志 |

## assert 语句

`assert` 是最基础的可观测性工具——在运行时验证假设。

### 基本语法

```helen
// 简单断言
assert x > 0

// 带消息的断言
assert x > 0, "x must be positive"
```

### 断言失败

当断言条件为 `false` 时，抛出 `AssertionError`：

```helen
fn divide(a, b) {
    assert b != 0, "divisor must not be zero"
    return a / b
}

main {
    try {
        let result = divide(10, 0)
    } catch AssertionError e {
        print("Caught: " + e.message)
        // 输出: Caught: assertion failed: divisor must not be zero
    }
}
```

### assert 与可观测性集成

断言失败时，自动捕获结构化错误上下文：

```json
{
  "error": {
    "type": "AssertionError",
    "message": "assertion failed: divisor must not be zero",
    "location": "main.helen:2:5"
  },
  "call_stack": [
    {"function": "main", "location": "main.helen:7:1"},
    {"function": "divide", "location": "main.helen:1:1", "args": {"a": 10, "b": 0}}
  ],
  "scope": {"a": 10, "b": 0}
}
```

## debug() 函数

`debug()` 输出结构化调试信息到 stderr，不影响程序正常输出。

### 基本用法

```helen
main {
    let x = 42
    let items = [1, 2, 3]
    
    debug("variable value", x)
    // 输出: [DEBUG] variable value {"value": 42}
    
    debug("list contents", items)
    // 输出: [DEBUG] list contents {"value": [1, 2, 3]}
    
    debug("checkpoint reached")
    // 输出: [DEBUG] checkpoint reached
}
```

### 与 print() 的区别

| 特性 | `print()` | `debug()` |
|------|-----------|-----------|
| 输出目标 | stdout | stderr |
| 格式 | 纯文本 | JSON 结构化 |
| 用途 | 程序正常输出 | 开发调试信息 |
| 生产环境 | 保留 | 可过滤 |

## 执行追踪

执行追踪记录程序的执行路径，帮助理解代码流程和定位问题。

### REPL 命令

```
:trace on          # 开启执行追踪
:trace off         # 关闭执行追踪
:trace show [n]    # 显示最近 n 条追踪记录（默认 50）
```

### 程序化追踪

```helen
main {
    trace_on()
    
    let x = compute_value()
    let y = transform(x)
    let z = validate(y)
    
    trace_off()
    
    // 获取追踪记录
    let trace = get_trace(10)
    print(trace)
}
```

### 追踪输出格式

```
[TRACE] call main at <repl>:1:1 {}
[TRACE] call compute_value at <repl>:3:9 {}
[TRACE] return compute_value → 42
[TRACE] call transform at <repl>:4:9 {"x": 42}
[TRACE] return transform → 84
[TRACE] call validate at <repl>:5:9 {"y": 84}
[TRACE] return validate → true
```

## 结构化错误上下文

当运行时错误发生时，Helen 自动捕获完整的错误上下文。

### REPL 命令

```
:last_error        # 显示上次错误的完整上下文（人类可读格式）
:last_error -v     # 详细模式，包含执行追踪
```

### 错误快照格式

REPL 中 `:last_error` 显示人类可读的文本格式：

```
Error: AssertionError: divisor must not be zero
Location: <repl>:1:31
Time: 2026-06-20 18:56:59

Call Stack:
-> <repl>:1:1 in divide

Variables in scope:
  a = 10
  b = 0

Tip: use :last_error -v to show execution trace
```

使用 `-v` 参数会额外显示执行追踪：

```
Execution Trace (last 1 entries):
  → <repl>:1:1 call divide
```

### JSON 格式（编程访问）

AI Agent 可以通过编程方式获取 JSON 格式的错误快照：

```helen
// 在代码中访问错误快照
let snapshot = observability.last_error
if snapshot != null {
    let json_str = snapshot.to_json()  // JSON 格式
    let dict = snapshot.to_dict()      // 字典格式
}
```

JSON 格式结构：

```json
{
  "error": {
    "type": "RuntimeError",
    "message": "division by zero",
    "location": "main.helen:23:5"
  },
  "call_stack": [
    {"function": "main", "location": "main.helen:10:1", "args": {}},
    {"function": "calculate", "location": "main.helen:20:1", "args": {"total": 100, "count": 0}}
  ],
  "scope": {
    "total": 100,
    "count": 0
  },
  "trace": [
    {"type": "call", "function": "main", "location": "main.helen:10:1"},
    {"type": "call", "function": "calculate", "location": "main.helen:20:1"}
  ],
  "timestamp": 1718812800.0
}
```

### 为什么 AI 需要 JSON 格式？

AI Agent 可以直接解析 JSON 错误快照，提取：
- **错误类型和消息** → 理解问题本质
- **调用栈** → 理解错误发生的路径
- **作用域变量** → 理解错误发生时的数据状态
- **执行追踪** → 理解程序的执行流程

这比传统的 stack trace 文本格式更容易被 AI 消费和分析。

## LLM 调用审计日志

所有 `llm act` 调用（含流式回调）自动记录到审计日志。

### REPL 命令

```
:llm_log [n]       # 显示最近 n 次 LLM 调用（默认 10）
:llm_log [n] -v    # 详细模式，显示完整审计信息
```

### 审计记录内容

每次 LLM 调用记录：

| 字段 | 说明 |
|------|------|
| `timestamp` | 调用时间 |
| `call_type` | `act`（普通）或 `act_stream`（带 on_chunk 回调） |
| `agent_name` | 调用的 Agent 名称 |
| `model` | 使用的模型 |
| `prompt` | 输入的 prompt |
| `response` | 返回的文本（普通 act）或 null（act_stream 回调模式） |
| `tokens_in` | 输入 token 数 |
| `tokens_out` | 输出 token 数 |
| `duration_ms` | 耗时（毫秒） |
| `tool_calls` | 工具调用列表（act_stream 模式） |
| `error` | 错误信息（如果有） |

### 审计日志示例

```json
[
  {
    "timestamp": 1718812800.0,
    "call_type": "act",
    "agent_name": "Translator",
    "model": "qwen3.7-plus",
    "prompt": "translate Hello to Chinese",
    "response": "你好",
    "tokens_in": 15,
    "tokens_out": 3,
    "duration_ms": 1200.5,
    "error": null
  },
  {
    "timestamp": 1718812805.0,
    "call_type": "act_stream",
    "agent_name": "Researcher",
    "model": "qwen3.7-plus",
    "prompt": "search for Helen language",
    "response": null,
    "tokens_in": 20,
    "tokens_out": 150,
    "duration_ms": 3500.0,
    "tool_calls": [
      {"name": "web_search", "args": {"query": "Helen language"}},
      {"name": "web_fetch", "args": {"url": "https://..."}}
    ],
    "error": null
  }
]
```

## 可观测性架构

```
helen/runtime/observability.py
├── CallFrame              # 单个栈帧（函数名、位置、参数）
├── CallStackTracker       # 调用栈追踪（push/pop，最大深度保护）
├── TraceEntry             # 单条追踪记录（类型、位置、数据）
├── ExecutionTracer        # 执行追踪（环形缓冲区）
├── ErrorSnapshot          # 结构化错误上下文（JSON 可序列化）
├── LLMAuditEntry          # 单条 LLM 调用记录
├── LLMAuditLog            # LLM 审计日志（环形缓冲区）
└── ObservabilityManager   # 统一管理器
```

### 集成点

| 模块 | 集成方式 |
|------|----------|
| `interpreter.py` | `ObservabilityManager` 初始化，调用栈 push/pop，错误捕获 |
| `llm_mixin.py` | LLM 调用审计日志记录 |
| `stdlib/__init__.py` | `debug()`, `trace_on/off()`, `get_trace()` 内置函数 |
| `cli/repl.py` | `:trace`, `:last_error`, `:llm_log` REPL 命令 |

### 零开销设计

- **追踪默认关闭**：只有显式 `trace_on()` 或 `:trace on` 才记录（REPL 中默认开启）
- **调用栈默认关闭**：只在追踪开启时记录（REPL 中默认开启）
- **LLM 审计默认开启**：对 prompt-first 程序至关重要
- **环形缓冲区**：限制内存使用（追踪 10000 条，LLM 日志 1000 条，调用栈 100 层）

## 实战示例：调试 Agent 行为

```helen
agent DataProcessor(input) {
    description: "Process and validate data"
    
    fn validate(data) {
        assert data != null, "data must not be null"
        assert data.size > 0, "data must not be empty"
        debug("validated data", data)
        return true
    }
    
    fn transform(data) {
        debug("transforming", data)
        let result = []
        for item in data {
            result.append(item * 2)
        }
        return result
    }
    
    main {
        trace_on()
        
        let valid = validate(input)
        if valid {
            let result = transform(input)
            debug("final result", result)
            return result
        }
        
        trace_off()
    }
}

main {
    try {
        let data = [1, 2, 3, 4, 5]
        let result = DataProcessor(data)
        print("Result: " + result)
    } catch AssertionError e {
        print("Validation failed: " + e.message)
        // 在 REPL 中可以用 :last_error 查看完整上下文
    }
}
```

## REPL 调试工作流

```
>>> :trace on
追踪已开启

>>> let result = my_function()
[DEBUG] entering my_function {"x": 42}
[TRACE] call my_function at <repl>:1:1 {"x": 42}
[TRACE] return my_function → 84

>>> :trace show 5
[TRACE] call my_function at <repl>:1:1 {"x": 42}
[TRACE] return my_function → 84

>>> :llm_log 3
[LLM] act Translator "translate Hello" → "你好" (1200ms)
[LLM] act_stream Researcher "search..." → 2 tool calls (3500ms)

>>> :last_error
Error: RuntimeError: division by zero
Location: main.helen:23:5

Call Stack:
-> main.helen:23:5 in calculate
   main.helen:10:1 in main

Variables in scope:
total = 100
count = 0
```

## 练习

1. 编写一个函数，使用 `assert` 验证输入参数，测试正常和异常情况
2. 在 REPL 中使用 `:trace on` 追踪一段代码的执行路径
3. 使用 `debug()` 输出中间计算结果
4. 编写一个会抛出异常的程序，用 `:last_error` 查看错误上下文
5. 使用 `llm act` 调用一个 Agent，然后用 `:llm_log` 查看审计记录

## 总结

Helen 的 AI 原生可观测性提供：

1. ✅ **assert 语句** — 运行时假设验证，失败自动捕获上下文
2. ✅ **debug() 函数** — 结构化调试输出，JSON 格式
3. ✅ **执行追踪** — 记录程序执行路径，程序化 + REPL 控制
4. ✅ **结构化错误** — JSON 格式错误快照，包含调用栈 + 作用域变量
5. ✅ **LLM 审计** — 自动记录所有 LLM 调用，含 prompt/response/tokens/耗时
6. ✅ **零开销默认** — 追踪关闭时无性能影响
7. ✅ **AI 友好** — 所有输出都是结构化 JSON，AI 可直接解析

传统调试器给人用，Helen 可观测性给 AI 用。

---

# 教程 12: 测试框架与 TDD

> 完整的测试 API、TDD 工作流、监听模式、测试组织

## 快速开始

### 1. 创建测试文件

```helen
// calculator_test.helen

// 定义测试函数
fn test_add() {
    assert_equal(2 + 3, 5)
}

fn test_subtract() {
    assert_equal(10 - 4, 6)
}

// 注册测试
test_suite("Calculator")
test_case("adds numbers", test_add)
test_case("subtracts numbers", test_subtract)
test_end_suite()

// 运行测试
run_tests()
```

### 2. 运行测试

```bash
# 基本运行
helen test calculator_test.helen

# 监听模式（TDD）
helen test calculator_test.helen --watch

# JSON 输出
helen test calculator_test.helen --json
```

## 测试 API

### 断言函数

| 函数 | 说明 |
|------|------|
| `assert_true(condition)` | 断言条件为真 |
| `assert_equal(actual, expected)` | 断言相等 |
| `assert_not_equal(a, b)` | 断言不等 |
| `assert_contains(container, item)` | 断言容器包含元素 |
| `assert_throws(fn)` | 断言抛出异常 |

```helen
fn test_assertions() {
    assert_true(1 == 1)
    assert_equal(2 + 3, 5)
    assert_not_equal("hello", "world")
    assert_contains("hello world", "world")
    assert_contains([1, 2, 3], 2)
}
```

### Expect 链式 API

```helen
fn test_expect() {
    // 相等
    expect(42).toBe(42)
    
    // 包含
    expect("hello world").toContain("world")
    expect([1, 2, 3]).toContain(2)
    
    // 比较
    expect(10).toBeGreaterThan(5)
    expect(3).toBeLessThan(7)
    
    // 字符串
    expect("test123").toMatch("[0-9]+")
    expect("hello").toStartWith("he")
    expect("world").toEndWith("ld")
    
    // 集合
    expect([1, 2, 3]).toHaveLength(3)
    expect("").toBeEmpty()
    
    // 否定
    expect(5).not_.toBe(6)
    
    // 链式
    expect("hello world")
        .toContain("hello")
        .toContain("world")
        .toStartWith("hello")
}
```

### 测试组织

```helen
// 方式 1：回调风格（推荐）
test_suite("Math", fn() {
    test_case("adds", fn() {
        assert_equal(2 + 3, 5)
    })
    test_case("subtracts", fn() {
        assert_equal(10 - 4, 6)
    })
})

// 方式 2：自动发现（最简单）
// 以 test_ 开头的函数会被自动注册
fn test_addition() {
    assert_equal(1 + 1, 2)
}

fn test_subtraction() {
    assert_equal(5 - 3, 2)
}

// 运行: helen test your_file.helen
// 所有 test_* 函数会自动执行

// 方式 3：显式注册（传统方式）
test_suite("String")
test_case("uppercases", test_upper)
test_end_suite()
```

### 钩子函数

```helen
fn setup() {
    // 每个测试前运行
}

fn teardown() {
    // 每个测试后运行
}

test_suite("With hooks")
before_each(setup)
after_each(teardown)
test_case("test1", test_something)
test_case("test2", test_another)
test_end_suite()
```

## CLI 选项

### 过滤测试

```bash
# 运行单个测试
helen test my_test.helen --only "adds numbers"

# 运行单个 suite
helen test my_test.helen --suite "Calculator"

# 按模式过滤（正则）
helen test my_test.helen --filter "add|subtract"
helen test my_test.helen --filter "test_.*_api"
```

### 输出格式

```bash
# 人类可读（默认）
helen test my_test.helen

# JSON 格式（CI 集成）
helen test my_test.helen --json

# 显示覆盖率提示
helen test my_test.helen --coverage
```

### 监听模式

```bash
# 文件变更自动重跑
helen test my_test.helen --watch

# 监听 + 过滤
helen test my_test.helen --watch --filter "add"
```

## 输出示例

```
============================================================
  HELEN TEST RESULTS
============================================================

  Calculator
    ✓ adds numbers (0.1ms)
    ✓ subtracts numbers (0.0ms)
    ○ skipped test (skipped)

  String
    ✓ uppercases (0.0ms)

------------------------------------------------------------
  3 passed, 0 failed, 1 skipped (4 total)
  Duration: 0.5ms
============================================================
  ✓ ALL TESTS PASSED
============================================================
```

## TDD 工作流

### 1. 红（RED）— 写失败的测试

```helen
// my_feature_test.helen
import "my_feature" as feature

fn test_new_feature() {
    assert_equal(feature.do_something(), expected_result)
}

test_suite("New Feature")
test_case("does something", test_new_feature)
test_end_suite()

run_tests()
```

```bash
# 启动监听
helen test my_feature_test.helen --watch
```

### 2. 绿（GREEN）— 实现功能

```helen
// my_feature.helen
fn do_something() {
    return expected_result
}
```

保存文件 → 测试自动重跑 → 看到通过！

### 3. 重构（REFACTOR）

改进代码，保持测试通过。

## 跳过测试

```helen
test_suite("Work in progress")
test_case("completed", test_done)
test_case_skip("not ready", test_wip)  // 跳过
test_end_suite()
```

## 完整示例

```helen
// string_utils_test.helen

fn test_reverse() {
    assert_equal(reverse("hello"), "olleh")
    assert_equal(reverse(""), "")
}

fn test_uppercase() {
    expect(upper("hello")).toBe("HELLO")
    expect(upper("World")).toBe("WORLD")
}

fn test_contains() {
    expect("hello world").toContain("world")
    expect("hello world").not_.toContain("xyz")
}

fn test_split() {
    let parts = split("a,b,c", ",")
    expect(parts).toHaveLength(3)
    expect(parts).toContain("b")
}

test_suite("String Utils")
test_case("reverse", test_reverse)
test_case("uppercase", test_uppercase)
test_case("contains", test_contains)
test_case("split", test_split)
test_end_suite()

run_tests()
```

## 练习

1. 为 `calculator.helen` 编写测试，覆盖加减乘除
2. 使用 `--watch` 模式进行 TDD 开发
3. 使用 `--filter` 只运行特定测试
4. 使用 `expect` 链式 API 重写断言
5. 添加 `before_each` 钩子初始化测试数据

## 总结

Helen 测试框架提供：

1. ✅ **简单 API** — `test_suite` / `test_case` / `test_end_suite`
2. ✅ **丰富断言** — `assert_*` + `expect().toBe()` 链式
3. ✅ **灵活过滤** — `--only` / `--suite` / `--filter`
4. ✅ **TDD 支持** — `--watch` 监听模式
5. ✅ **CI 集成** — `--json` 输出
6. ✅ **跳过测试** — `test_case_skip`
7. ✅ **钩子函数** — `before_each` / `after_each`

---

# 教程 15: 质量评估（7 维框架）

> Helen 内置 7 维质量评估框架，自动化质量分析

## 快速开始

### CLI 命令

```bash
# 基本评估
helen quality my_program.helen

# JSON 输出
helen quality my_program.helen --json

# 设置阈值（CI 集成）
helen quality my_program.helen --threshold 7.5

# 单维度评估
helen quality my_program.helen --dimension security
```

### 在 Helen 代码中使用

```helen
let source = read_file("my_program.helen")

// 获取代码指标
let metrics = analyze_code(source, "my_program.helen")
print("Functions: " + str(metrics["function_count"]))
print("Complexity: " + str(metrics["avg_complexity"]))

// 安全检查
let issues = check_security(source)
print("Security issues: " + str(len(issues)))

// 质量评分
let scores = quality_score(source, "my_program.helen")
print("Total score: " + str(scores["total"]))
print("Grade: " + scores["grade"])

// 完整报告
let report = quality_report(source, "my_program.helen")
print(report)
```

## 7 个维度

| 维度 | 权重 | 评估内容 |
|------|:----:|---------|
| **架构设计** | 20% | 函数长度、复杂度、嵌套深度、参数数量 |
| **代码质量** | 15% | 注释率、函数平均长度、平均复杂度 |
| **安全性** | 20% | 危险模式检测（eval、shell=True、未验证输入等） |
| **测试覆盖** | 15% | 测试文件存在性、测试/代码比 |
| **文档** | 10% | 函数 docstring 覆盖率 |
| **可维护性** | 10% | 长函数数量、高复杂度函数数量 |
| **工程规范** | 10% | 命名规范、文件大小 |

## 评分等级

| 等级 | 分数范围 | 含义 |
|:----:|:--------:|------|
| S | 9.0-10.0 | 生产就绪， exemplary |
| A | 7.5-8.9 | 良好，少量改进 |
| B | 6.0-7.4 | 可接受，需要改进 |
| C | 4.0-5.9 | 低于标准 |
| D | 0.0-3.9 | 不可接受 |

## 输出示例

```
============================================================
  HELEN QUALITY REPORT
============================================================
  File: calculator.helen

  Code Metrics:
    Total lines: 150
    Code lines: 120
    Comment lines: 25 (17%)
    Functions: 8
    Agents: 1
    Avg function length: 12.5 lines
    Max function length: 35 lines
    Avg complexity: 2.3
    Max complexity: 6

  Quality Scores (0-10):
    Architecture:      9.50 (20%)
    Code Quality:      8.00 (15%)
    Security:          10.00 (20%)
    Test Coverage:     6.00 (15%)
    Documentation:     7.50 (10%)
    Maintainability:   9.00 (10%)
    Engineering:       8.50 (10%)
    ─────────────────────────────
    TOTAL:             8.48
    GRADE:             A

  Recommendations:
    • Add test file for better coverage
    • Add docstrings to 2 undocumented functions

============================================================
```

## 安全检查

自动检测以下危险模式：

| 模式 | 严重度 | 说明 |
|------|:------:|------|
| `eval()` | HIGH | 可执行任意代码 |
| `exec()` | HIGH | 可执行任意代码 |
| `shell=true` | HIGH | 命令注入风险 |
| `import os` | MEDIUM | 系统资源访问 |
| `import subprocess` | MEDIUM | 命令执行 |
| `open(..., "w")` | MEDIUM | 无验证的文件写入 |
| `input()` | LOW | 用户输入需验证 |

## CI 集成

```bash
# 在 CI 中使用阈值
helen quality src/*.helen --threshold 7.0 --json > quality.json

# 检查是否达标
if [ $? -ne 0 ]; then
    echo "Quality threshold not met!"
    exit 1
fi
```

## API 参考

### `analyze_code(source, filename?)`

分析代码指标，返回：
- `total_lines`, `code_lines`, `comment_lines`, `blank_lines`
- `comment_ratio`, `function_count`, `agent_count`
- `avg_function_length`, `max_function_length`
- `avg_complexity`, `max_complexity`
- `functions[]` — 每个函数的详细信息

### `check_security(source)`

检查安全问题，返回问题列表：
- `line` — 行号
- `severity` — "high" / "medium" / "low"
- `pattern` — 匹配的模式
- `message` — 问题描述

### `quality_score(source, file_path?)`

计算 7 维评分，返回：
- `architecture`, `code_quality`, `security`
- `test_coverage`, `documentation`, `maintainability`, `engineering`
- `total` — 加权总分
- `grade` — 字母等级

### `quality_report(source, filename?)`

生成格式化的完整报告字符串。

## 练习

1. 对你写的 Helen 程序运行质量评估
2. 根据建议改进代码，提高评分
3. 在 CI 中设置质量阈值
4. 使用 `--dimension security` 专注安全改进
5. 对比改进前后的评分变化

## 总结

Helen 质量评估提供：

1. ✅ **7 维框架** — 全面的质量视角
2. ✅ **自动分析** — 无需人工审查
3. ✅ **安全评分** — 检测危险模式
4. ✅ **改进建议** — 可操作的优化方向
5. ✅ **CI 集成** — 阈值检查 + JSON 输出
6. ✅ **编程接口** — 可在 Helen 代码中调用


---

# v1.10 新特性总结

> 本章节总结 Helen v1.10 的所有新特性和改进

## 概述

Helen v1.10 引入了 **Agent 作用域隔离**、**shared let**、**子脚本/字段赋值**、**短路求值**、**异步 HTTP** 等重要特性，进一步增强了语言的表达能力和安全性。

---

## 1. shared let — 跨 agent 可见变量

### 语法

```helen
shared let counter = 0
shared let SHARED_CONFIG = {"debug": true}
```

### 中文关键字

```helen
共享 let counter = 0
```

### 作用域规则

| 变量类型 | 在 agent main 中可见？ | 可修改？ |
|---------|---------------------|---------|
| 模块级 `let` | ❌ 不可见 | - |
| 模块级 `const` | ✅ 可见 | ❌ 只读 |
| `shared let` | ✅ 可见 | ✅ 可读写 |

### 示例

```helen
shared let SHARED_COUNTER = 0
const MODULE_CONST = "常量"
let moduleVar = "模块级"  // agent main 中不可见

agent Worker {
  main {
    // moduleVar        // ❌ E0350 SCOPE_VIOLATION
    MODULE_CONST       // ✅ 只读
    SHARED_COUNTER += 1  // ✅ 可读写
  }
}
```

---

## 2. Agent 作用域隔离

### 规则

- `agent main {}` 在**完全隔离的环境**中运行
- 模块级 `let` 不可见（编译时错误）
- 模块级 `const` 自动可见（只读）
- 使用 `shared let` 显式声明跨 agent 可见的可变变量
- Agent main 中的闭包可以捕获局部变量

### 为什么需要？

1. **避免隐式副作用**: agent 不能随意修改全局状态
2. **提高代码可读性**: 共享状态必须显式声明
3. **便于测试**: agent 的行为不依赖外部状态

### 最佳实践

1. 使用 `SHARED_` 前缀命名共享变量
2. 最小化共享状态
3. 小心并发修改（线程安全）

---

## 3. 子脚本/字段赋值

### 语法

```helen
// 数组索引赋值
let arr = [1, 2, 3]
arr[0] = 10  // [10, 2, 3]

// 对象字段赋值
let obj = {"name": "Alice"}
obj.name = "Bob"  // {"name": "Bob"}
obj["age"] = 30   // {"name": "Bob", "age": 30}

// 嵌套访问
let matrix = [[1, 2], [3, 4]]
matrix[0][1] = 99  // [[1, 99], [3, 4]]
```

### 错误示例

```helen
const arr = [1, 2, 3]
arr[0] = 10  // ❌ E0352 IMMUTABLE_ASSIGNMENT
```

---

## 4. 短路求值

### && 短路

```helen
// 如果左侧为 false，右侧不会执行
let result = false && expensiveCall()  // 不执行

// 安全访问
let user = getUser()
let name = user != null && user.getName()
```

### || 短路

```helen
// 如果左侧为 true，右侧不会执行
let result = true || expensiveCall()  // 不执行

// 默认值
let config = loadConfig() || defaultConfig()
```

### 优先级

- `||` 优先级 3（左结合）
- `&&` 优先级 4（左结合）
- `&&` 优先级高于 `||`

---

## 5. 返回类型注解语法变化

### 新语法（仅支持）

```helen
fn add(a: int, b: int): int {
  return a + b
}
```

### 旧语法（已移除）

```helen
// ❌ 不再支持
fn add(a: int, b: int) -> int {
  return a + b
}
```

---

## 6. 异常处理增强

### RuntimeError 包装 stdlib 异常

```helen
try {
  let result = int("not a number")  // Python ValueError
} catch RuntimeError as e {
  print("Error: " + e.message)
  // "ValueError: invalid literal for int()..."
}
```

### 新增异常

- `ScopeViolationError` — agent main 访问不可见的模块级变量

---

## 7. 异步 HTTP 支持

### 异步方法

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

### 性能提升

| 场景 | 同步 | 异步 | 提升 |
|------|------|------|------|
| 单次调用 | 1.5s | 1.5s | 0% |
| 3 次并发 | 4.5s | 1.6s | **65%** |
| 10 次并发 | 15s | 2.1s | **86%** |

---

## 8. 导入跟踪

### shared let 导入

```helen
// module_a.helen
shared let counter = 0

// module_b.helen
import "./module_a.helen"

agent Worker {
  main {
    counter += 1  // ✅ 可以访问导入的 shared let
  }
}
```

---

## 9. 新增错误码

| 代码 | 名称 | 触发条件 |
|------|------|---------|
| E0350 | SCOPE_VIOLATION | 模块级 let 在 agent main 中不可见 |
| E0351 | SHARED_NOT_MODULE_LEVEL | shared let 不在模块级声明 |
| E0352 | IMMUTABLE_ASSIGNMENT | 子脚本/字段赋值目标不可变 |

---

## 10. 完整示例

### 并发数据处理系统

```helen
// 共享状态
shared let SHARED_RESULTS = []
shared let SHARED_COUNTER = 0

// 配置
const CONFIG = {
  "max_retries": 3,
  "timeout": 5000
}

// 数据处理 agent
agent DataProcessor {
  description "Process data concurrently"
  
  main {
    // 递增共享计数器
    SHARED_COUNTER += 1
    
    // 处理数据
    let data = fetch_data()
    let processed = process(data)
    
    // 添加到共享结果
    SHARED_RESULTS.push(processed)
    
    // 使用短路求值安全访问
    let first_result = len(SHARED_RESULTS) > 0 && SHARED_RESULTS[0]
    
    print("Processed: " + str(SHARED_COUNTER))
  }
}

// 主程序
main {
  // 并发处理 5 个数据源
  async call DataProcessor()
  async call DataProcessor()
  async call DataProcessor()
  async call DataProcessor()
  async call DataProcessor()
  
  // 等待完成
  // SHARED_COUNTER 现在是 5
  // SHARED_RESULTS 包含 5 个结果
  
  // 子脚本赋值
  if len(SHARED_RESULTS) > 0 {
    SHARED_RESULTS[0]["processed"] = true
  }
  
  print("Total: " + str(SHARED_COUNTER))
}
```

---

## 迁移指南

### 从 v1.9 迁移到 v1.10

#### 1. 检查模块级变量

```helen
// v1.9: 可以访问
let x = 1
agent A {
  main {
    print(x)  // v1.9 可以，v1.10 报错
  }
}

// v1.10: 使用 shared let
shared let x = 1
agent A {
  main {
    print(x)  // ✅ 可以访问
  }
}
```

#### 2. 更新返回类型语法

```helen
// v1.9
fn add(a, b) -> int { return a + b }

// v1.10
fn add(a: int, b: int): int { return a + b }
```

#### 3. 利用短路求值

```helen
// 旧方式
let user = getUser()
if user != null {
  let name = user.getName()
}

// 新方式（短路）
let user = getUser()
let name = user != null && user.getName()
```

#### 4. 使用异步 HTTP

```helen
// 同步（慢）
let results = []
for item in items {
  results.push(llm act Process(item))
}

// 异步（快）
let tasks = []
for item in items {
  tasks.push(llm act_async Process(item))
}
let results = await tasks
```

---

## 总结

Helen v1.10 的主要改进：

1. **安全性**: Agent 作用域隔离防止隐式副作用
2. **表达力**: 子脚本/字段赋值、短路求值
3. **性能**: 异步 HTTP 支持并发调用
4. **一致性**: 统一的异常处理、明确的共享状态
5. **可维护性**: 显式声明共享变量，代码更清晰

**迁移成本**: 低（主要是 shared let 和返回类型语法）

**建议**: 新项目直接使用 v1.10 语法，旧项目逐步迁移

---

**最后更新**: 2026-07-01  
**版本**: v1.10
