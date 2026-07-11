# Helen 语言完整教程

> **Helen** — A Prompt-first Agent Programming Language
> 版本: v1.15 | 状态: Phase 0-10 + Phase 1-7 上下文管理 + 中文语法 + Agent 隔离

<!-- ⚠️ AUTO-GENERATED — DO NOT EDIT MANUALLY -->
<!-- Generated from wiki/tutorial/*.md by scripts/build_tutorial.py -->
<!-- Generated at: 2026-07-09 23:37 -->

---

<!-- TABLE OF CONTENTS -->

| 章节 | 主题 |
|------|------|
| [01](#教程-01:-入门指南) | 教程 01: 入门指南 — 安装 Helen、配置环境、编写第一个程序、使用 REPL |
| [02](#教程-02:-变量与类型) | 教程 02: 变量与类型 — let / const / 类型注解 / 基本运算 |
| [03](#教程-03:-函数) | 教程 03: 函数 — fn 声明 / 参数 / 返回值 / 函数调用 |
| [04](#教程-04:-控制流) | 教程 04: 控制流 — if / for / while / match / try-catch |
| [05](#教程-05:-agent-编程) | 教程 05: Agent 编程 — agent 声明 / description / prompt / 配置 |
| [06](#教程-06:-llm-语句) | 教程 06: LLM 语句 — llm act / llm if 实战 |
| [07](#教程-07:-异步编程) | 教程 07: 异步编程 — async / await / for await / AggregateError / 并发 Agent 调用 / 流式迭代 |
| [08](#教程-08:-模块与导入) | 教程 08: 模块与导入 — import / 多格式 / 跨文件复用 / 路径安全 |
| [09](#教程-09:-python-ffi) | 教程 09: Python FFI — 导入 Python 库 / 调用 Python 函数 / 类型自动转换 |
| [10](#教程-10:-标准库参考) | 教程 10: 标准库参考 — 255 个内置函数，覆盖 AI 应用开发的所有核心需求 |
| [11](#教程-11:-构建多-agent-系统) | 教程 11: 构建多 Agent 系统 — 完整案例：从需求到实现 |
| [12](#教程-12:-测试框架与-tdd) | 教程 12: 测试框架与 TDD — 用 Helen 内置测试框架写测试、跑 TDD |
| [13](#教程-13:-技能系统) | 教程 13: 技能系统 — 让 Agent 带着专业知识工作 |
| [14](#教程-14:-ai-原生可观测性) | 教程 14: AI 原生可观测性 — 给 AI 一个它能读懂的"黑匣子"，而不是给人类一个 GDB。 |
| [15](#教程-15:-python-bridge) | 教程 15: Python Bridge — 让 Python 直接使用 Helen Agent |
| [16](#教程-16:-质量评估7-维框架) | 教程 16: 质量评估（7 维框架） — Helen 内置 7 维质量评估框架，自动化质量分析 |
| [17](#多模态支持-(v1.17)) | 多模态支持 (v1.17) |

---

# 教程 01: 入门指南

> 安装 Helen、配置环境、编写第一个程序、使用 REPL

---

## 系统要求

- **Python 3.7+**（推荐 3.9+）
- 操作系统：Linux、macOS、Windows

---

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

---

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

### Transcript 配置 (v1.16)

Helen v1.16 引入了 TranscriptStore，自动保存所有对话历史。默认启用，无需配置即可使用：

```yaml
# ~/.helen/config.yaml

llm:
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  api_key: "your-api-key-here"
  model: "qwen3.7-plus"

# Transcript 配置（可选，以下为默认值）
transcript:
  enabled: true              # 启用 TranscriptStore（默认 true）
  backend: "jsonl"           # 后端类型："jsonl" 或 "sqlite"
  session_dir: "~/.helen/sessions"  # 会话存储目录
  max_memory_items: 1000     # LRU 缓存大小
```

**默认行为**：
- TranscriptStore 默认启用，所有对话自动保存到 `~/.helen/sessions/`
- 使用 JSONL 后端（人类可读，崩溃安全）
- LRU 缓存限制内存使用（1000 条消息）

**自定义配置**：
- 设置 `enabled: false` 禁用 TranscriptStore
- 设置 `backend: "sqlite"` 使用高性能 SQLite 后端
- 设置 `session_dir` 自定义存储位置

**CLI 参数**：
```bash
# 自定义 transcript 输出路径
$ helen chat.helen --transcript-log=/tmp/my_chat.jsonl
```

**REPL 命令**：
```
>>> :sessions              # 列出所有会话
>>> :session_id            # 显示当前会话 ID
>>> :transcript            # 显示当前 transcript
>>> :resume <session_id>   # 恢复到指定会话
```

详见 [TranscriptStore 文档](../runtime/transcript-store.md) 和 [标准库参考](10-stdlib.md#transcript-函数-6-v116)。

---

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

### 传递命令行参数

文件名之后的参数会传递给 Helen 程序，通过预定义常量 `argv` 访问：

```bash
$ helen greet.helen Alice Bob
```

```helen
// greet.helen
for name in argv {
    print("Hello, " + name + "!")
}
```

```
Hello, Alice!
Hello, Bob!
```

也可以使用 `parse_cli_args()` 进行结构化解析：

```helen
// tool.helen — 运行: helen tool.helen --verbose --output=json file.txt
let config = parse_cli_args({
    "verbose": {"type": "flag", "default": false},
    "output": {"type": "string", "default": "text"}
})

if config["verbose"] {
    print("Verbose mode on, output=" + config["output"])
}
```

详见 [[toolchain/cli|CLI 文档]] 和 [[toolchain/stdlib|标准库 System 章节]]。

---

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

---

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

---

## 使用 REPL

```bash
$ helen repl
Helen REPL v1.2
Type 'exit' or Ctrl+D to quit, ':help' for commands

>>> print("Hello!")
Hello!
>>> let x = 42
>>> x
42
>>> let y = x * 2
>>> y
84
>>>
```

### 交互特性

REPL 支持以下交互功能：

| 功能 | 说明 |
|------|------|
| **光标移动** | ← → 方向键移动光标 |
| **命令历史** | ↑ ↓ 方向键浏览历史 |
| **Tab 补全** | 按 Tab 键触发关键字补全 |

### REPL 命令

```
:help             显示帮助信息
:reset            清除所有定义
:list             列出已定义的函数和 agent
:undefine <name>  删除指定定义
:ask <question>   向 Helen 语言助手提问
exit              退出 REPL
```

### Helen 语言助手

REPL 内置 AI 语言助手（位于 `helen/agent/helen_assistant.helen`），可以回答 Helen 语言问题、帮助编写代码、调试程序。

助手会加载：
- **Helen 文档**（`docs/tutorial.md`，由 `wiki/tutorial/*.md` 自动生成）— 语法、语义、示例
- **Helen 源码**（`helen/` 目录）— parser、interpreter、AST、lexer

这意味着助手不仅能回答语法问题，还能解释实现细节和内部机制。

使用 `:ask` 命令提问：

```
>>> :ask How do I define an agent?

🤔 Thinking...

# Defining an Agent in Helen

An `agent` is a first-class language construct...
[详细的回答和代码示例]
```

**流式输出**：助手使用 `llm act`（带 `on_chunk` 回调）流式输出回答，内容逐 chunk 实时显示，无需等待完整响应。

助手会加载 Helen 文档，生成包含代码示例的详细回答。

### 多行输入

当括号未闭合时，REPL 进入多行模式（`...` 提示符）：

```
>>> for i in [1, 2, 3] {
...     print(i)
... }
1
2
3
```

**退出多行模式的方法：**

| 方式 | 说明 |
|------|------|
| **空行** | 在 `...` 提示符下按 Enter（输入空行） |
| **Ctrl+C** | 取消当前多行输入 |
| **Ctrl+D** | 退出整个 REPL |

示例：如果输入错误导致卡在多行模式：

```
>>> agent Bad(x) {
...   main {
...     return x *
... 
(multi-line input cancelled)
>>>
```

### 退出 REPL

按 `Ctrl+D` 或输入 `exit`。

---

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
设 姓名 = "张三"
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

**中文关键字映射**：`定义`=let, `函数`=fn, `如果`=if, `否则`=else, `返回`=return, `真`=true, `假`=false, `空`=null 等 44 个。详见 [[syntax/keywords|关键字参考]]。

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

// 文件存在性检查示例
let file = "config.txt"
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

### 列表拼接

使用 `+` 操作符可以拼接两个列表，返回一个新列表（原列表不变）：

```helen
let a = [1, 2]
let b = [3, 4]
let c = a + b             // [1, 2, 3, 4]

// 常用于增量构建
let items = []
items = items + ["a"]     // ["a"]
items = items + ["b", "c"]  // ["a", "b", "c"]
```

> 注意：`+` 返回新列表，不修改原列表。如需原地修改，使用 `append()` 或 `extend()`。

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

### 子脚本/字段赋值 (v1.10)

v1.10 添加了**子脚本赋值**和**字段赋值**支持，可以直接修改数组元素和对象字段：

#### 数组索引赋值

```helen
let arr = [1, 2, 3]
arr[0] = 10  // ✅ arr 变为 [10, 2, 3]
arr[1] = 20  // ✅ arr 变为 [10, 20, 3]

// 动态索引
let i = 2
arr[i] = 30  // ✅ arr 变为 [10, 20, 30]
```

#### 对象字段赋值

```helen
let person = {"name": "Alice", "age": 30}
person["age"] = 31  // ✅ person 变为 {"name": "Alice", "age": 31}
person.name = "Bob"  // ✅ person 变为 {"name": "Bob", "age": 31}
```

#### 嵌套访问

```helen
let matrix = [[1, 2], [3, 4]]
matrix[0][1] = 99  // ✅ matrix 变为 [[1, 99], [3, 4]]

let data = {"users": [{"name": "Alice"}, {"name": "Bob"}]}
data["users"][0]["name"] = "Charlie"  // ✅ 嵌套修改
```

#### 错误示例

```helen
const arr = [1, 2, 3]
arr[0] = 10  // ❌ E0346 CONST_ASSIGNMENT: const 不可修改

const obj = {"name": "Alice"}
obj.name = "Bob"  // ❌ E0346 CONST_ASSIGNMENT: const 不可修改
```

#### 实际示例

```helen
// 更新数组中的记录
let users = [
  {"name": "Alice", "score": 85},
  {"name": "Bob", "score": 90}
]

// 更新第一个用户的分数
users[0]["score"] = 95

// 添加新字段
users[1]["grade"] = "A"

print(users)
// [
//   {"name": "Alice", "score": 95},
//   {"name": "Bob", "score": 90, "grade": "A"}
// ]
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

### 基本语法

```helen
alias <canonical> as <alias_name>
```

### 给 stdlib 起别名

Helen 的 stdlib 已经内置 255 个中文别名（`长度`、`打印`、`排序` 等），可以直接使用。也可以用 `alias` 添加自定义别名：

```helen
alias len as 我的长度
alias print as 输出

主函 {
    我的长度([1, 2, 3])   // 3
    输出("hello")
}
```

### 给用户函数起别名

```helen
函数 greet(name: str): str {
    返回 "Hello, " + name
}

alias greet as 打招呼
alias greet as say_hello

主函 {
    打招呼("Helen")       // "Hello, Helen"
    say_hello("World")    // "Hello, World"
}
```

### 中文关键字 `别名`

`alias` 的中文等价形式：

```helen
别名 len as 长度
别名 greet as 打招呼
```

### 作用域

别名遵守正常的变量作用域规则：
- 顶层 alias 在整个模块可见
- 块内的 alias 只在该块及其嵌套作用域可见
- 别名是快照绑定：`alias f as g` 时 g 指向当时的 f，后续重新定义 f 不影响 g

```helen
函数 foo() { 返回 1 }
alias foo as bar
函数 foo() { 返回 2 }   // 重新定义 foo

主函 {
    foo()   // 2 - 使用新的 foo
    bar()   // 1 - bar 仍指向旧的 foo
}
```

### 错误处理

给不存在的名字起别名会在语义分析阶段报错：

```helen
alias nonexistent as foo   // ❌ Error: cannot alias 'nonexistent': name not found
```

## 练习

1. 编写一个计算斐波那契数列的递归函数
2. 编写一个函数，接受列表并返回最大值
3. 编写一个函数，判断一个字符串是否为回文
4. 使用闭包实现一个计数器函数 `make_counter()`，每次调用返回递增的值
5. 使用 `map` 和匿名函数将列表中的所有字符串转换为大写

---

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

### 短路求值 (v1.10)

`&&` 和 `||` 运算符支持**短路求值**，避免不必要的计算：

首先定义一些示例函数：

```helen
fn expensiveFunction(): str {
    // 模拟耗时操作
    return "result"
}

fn getUser(): map? {
    return {"name": "Alice"}
}

fn isValid(): bool {
    return true
}

fn processData(): str {
    return "processed"
}

fn loadConfig(): map? {
    return null
}

fn defaultConfig(): map {
    return {"debug": false}
}

fn createDefaultUser(): map {
    return {"name": "Guest"}
}
```

#### && 短路

```helen
// 如果左侧为 false，右侧不会执行
let result = false && expensiveFunction()  // expensiveFunction() 不会执行

// 实际应用：安全访问
let user = getUser()
let name = user != null && user.getName()  // 如果 user 为 null，不会调用 getName()

// 条件执行
let valid = isValid() && processData()  // 只在 valid 时处理
```

#### || 短路

```helen
// 如果左侧为 true，右侧不会执行
let result = true || expensiveFunction()  // expensiveFunction() 不会执行

// 实际应用：默认值
let config = loadConfig() || defaultConfig()  // 只在加载失败时使用默认值

let user = getUser() || createDefaultUser()  // 如果获取失败，创建默认用户
```

#### 优先级

```helen
// && 优先级高于 ||
let result = a || b && c  // 等价于 a || (b && c)

// 使用括号明确意图
let result = (a || b) && c  // 明确分组
```

#### 实际示例

```helen
// 安全的列表访问
let items = [1, 2, 3]
let first = len(items) > 0 && items[0]  // 避免空列表错误

// 缓存检查
let cached = cache.get(key)
let result = cached != null || computeExpensive()

// 权限检查
let canAccess = isLoggedIn() && hasPermission("admin")
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
    let data = read_file("/nonexistent/path")  // Python FileNotFoundError
} catch RuntimeError err {
    // 通过 err.message 前缀区分类型
    if (startswith(err.message, "Python FileNotFoundError")) {
        print("File not found")
    }
}
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

### tools — LLM 可见的工具白名单

`tools = [...]` 是 **LLM 可见性的唯一白名单**（两层授权模型）。

**两层授权：**

- `functions {}` 块声明 agent 的**全部能力**——`main {}` 的 Helen 代码可以调用其中任意函数，但 LLM 默认看不到它们。
- `tools = [...]` 从中挑选**允许 LLM 自主决定调用**的部分。
- **不写 `tools`** 时，LLM 没有任何工具可用（除内置的 `load_skill`）。

```helen
agent Assistant {
    description "Helpful assistant"
    tools = ["web_search", "read_file"]   // LLM 可以自主调用这两个
    functions {
        fn fetch_summary(url: str): str {  // 在 functions 里声明
            let content = read_file(url)
            return summarize(content)
        }
        fn dangerous_op() { ... }          // LLM 看不到
    }
    main {
        // main 可以调用 functions 里任意函数（不受 tools 限制）
        let summary = fetch_summary("http://example.com")
        dangerous_op()                      // ✅ main 可以调
        return llm act "..."                // LLM 只能调 web_search/read_file/fetch_summary
    }
}
```

`tools` 里的名字先查 `functions {}` 块（Helen 函数），再查 Python 工具注册表（`web_search`、`read_file` 等）。同名时 Helen 函数优先。

### context {} — 上下文管理配置（v1.15+）

`context {}` 块允许为每个 agent 自定义上下文管理策略，包括压缩算法、工作记忆等。

#### 基本语法

```helen
agent SmartAssistant {
    description "Smart assistant with custom context config"
    
    context {
        compression "graduated"      // 压缩策略
        cache-aware true             // 缓存感知
        working-memory true          // 工作记忆
        working-memory-tokens 5000   // 工作记忆词元预算
    }
    
    tools ["read_file", "web_search"]
    prompt "You are a helpful assistant."
    
    main {
        return llm act "..."
    }
}
```

#### 配置选项

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `compression` | str | `"graduated"` | 压缩策略：`"none"` / `"graduated"` / `"traditional"` |
| `cache-aware` | bool | `true` | 启用缓存感知压缩（提高缓存命中率） |
| `working-memory` | bool | `true` | 启用工作记忆（跟踪活跃文件、决策、错误） |
| `working-memory-tokens` | int | `5000` | 工作记忆词元预算 |

#### 压缩策略详解

**1. `"none"` — 不压缩**

适合短对话或需要完整历史的场景。

```helen
context {
    compression "none"
}
```

**2. `"graduated"` — 渐进压缩（默认）**

五层渐进策略，自动根据上下文使用率应用：

| 层级 | 使用率阈值 | 策略 | 说明 |
|------|-----------|------|------|
| Layer 1 | 60% | Budget Reduction | 替换大工具输出为引用指针 |
| Layer 2 | 70% | Snip | 丢弃过时轮次 |
| Layer 3 | 80% | Microcompact | 清除旧工具结果，保留决策 |
| Layer 4 | 90% | Context Collapse | 归档并投射折叠视图 |
| Layer 5 | 95% | Auto-Compact | LLM 语义压缩 |

```helen
context {
    compression "graduated"  // 推荐用于长对话
}
```

**3. `"traditional"` — 传统压缩**

简单的截断策略，适合快速场景。

```helen
context {
    compression "traditional"
}
```

#### 缓存感知压缩

启用 `cache-aware` 后，压缩算法会考虑 prompt cache，提高缓存命中率：

- **稳定前缀**：保留前 30% 消息不变（缓存友好区）
- **批量阈值**：使用率达到 75% 才触发压缩
- **仅后缀修改**：只在缓存区域外进行修改

```helen
context {
    compression "graduated"
    cache-aware true  // 提高缓存命中率 70-80%
}
```

#### 工作记忆

启用 `working-memory` 后，agent 会自动跟踪：

- **活跃文件**：最近读写的文件路径
- **最近决策**：assistant 的关键决策
- **待办事项**：从注释中提取的 TODO
- **错误历史**：工具调用的错误记录

```helen
context {
    working-memory true
    working-memory-tokens 5000  // 工作记忆预算
}
```

#### 中文关键字

支持中文关键字配置：

```helen
agent 智能助手 {
    描述 "智能助手"
    
    上下文 {
        压缩 "graduated"
        缓存感知 true
        工作记忆 true
        工作记忆词元 5000
    }
    
    主逻辑 {
        返回 llm act "..."
    }
}
```

#### 完整示例：高性能研究 Agent

```helen
agent Researcher(topic: str) {
    description "Research assistant with optimized context"
    
    // 优化上下文管理
    context {
        compression "graduated"      // 渐进压缩
        cache-aware true             // 缓存感知
        working-memory true          // 跟踪研究文件
        working-memory-tokens 8000   // 更大的工作记忆
    }
    
    tools ["web_search", "web_fetch", "read_file", "write_file"]
    
    prompt """
    你是研究助手。
    研究主题：{{topic}}
    
    使用工具搜索和整理信息。
    """
    
    main {
        let result = llm act "开始研究"
        return result
    }
}
```

#### 默认行为

如果不指定 `context {}`，agent 使用默认配置：

```helen
// 等同于：
agent DefaultAgent {
    context {
        compression "graduated"
        cache-aware true
        working-memory true
        working-memory-tokens 5000
    }
}
```

#### 三通道上下文

启用工作记忆后，LLM 看到的上下文分为三个通道：

1. **系统指令（15%）**：框架指令、语言规范、agent 描述
2. **工作记忆（50%）**：活跃文件、最近决策、待办事项、错误历史
3. **对话历史（35%）**：压缩后的对话消息

这种结构确保 LLM 始终了解当前上下文，同时保持历史连贯性。

#### Transcript 会话记录（v1.16+）

Helen v1.16 引入了 TranscriptStore，自动保存所有对话历史。可以在 agent 中通过 stdlib 函数访问和管理会话：

```helen
agent ChatBot {
    description "Chat bot with transcript management"
    prompt "You are a helpful chat assistant."
    
    main {
        // 获取当前会话 ID
        let session_id = get_session_id()
        print("当前会话: " + session_id)
        
        // 列出所有会话
        let sessions = list_sessions()
        for s in sessions {
            print("{s.session_id}: {s.message_count} 条消息")
        }
        
        // 回放当前会话
        let messages = replay_transcript()
        for msg in messages {
            print("{msg.role}: {msg.content}")
        }
        
        // 导出会话到文件
        export_transcript("chat_log.json", "json")
        
        // 获取压缩审计（分析压缩效率）
        let audit = get_compression_audit()
        for event in audit {
            print("{event.layer}: {event.original_token_count} -> {event.compressed_token_count}")
        }
        
        // 恢复到之前的会话
        let success = resume_session("session_1783492628_d9d9c0aa")
        if success {
            print("会话已恢复")
        }
        
        return llm act "Hello!"
    }
}
```

**使用场景**：
- **会话恢复**: 使用 `resume_session(session_id)` 恢复之前的对话
- **审计追踪**: 使用 `get_compression_audit()` 分析压缩效率
- **会话导出**: 使用 `export_transcript()` 保存对话记录
- **多会话管理**: 使用 `list_sessions()` 管理多个会话

**配置**：在 `~/.helen/config.yaml` 中配置 transcript：

```yaml
transcript:
  enabled: true              # 默认启用
  backend: "jsonl"           # 或 "sqlite"
  session_dir: "~/.helen/sessions"
  max_memory_items: 1000     # LRU 缓存大小
```

**CLI 参数**：使用 `--transcript-log` 自定义输出路径：

```bash
$ helen chat.helen --transcript-log=/tmp/my_chat.jsonl
```

**REPL 命令**：在 REPL 中使用 transcript 命令：

```
>>> :sessions              # 列出所有会话
>>> :session_id            # 显示当前会话 ID
>>> :transcript            # 显示当前 transcript
>>> :resume <session_id>   # 恢复到指定会话
```

详见 [TranscriptStore 文档](../runtime/transcript-store.md) 和 [标准库参考](10-stdlib.md#transcript-函数-6-v116)。

#### tools = CONST_NAME（复用工具集）

`tools` 可以引用**模块级 const**，减少重复声明，并保持工具集**静态可审计**（安全边界清晰）：

```helen
// 项目顶部定义一次
const FILE_TOOLS = ["read_file", "write_file", "path_exists"]
const RESEARCH_TOOLS = ["web_search", "web_fetch", "read_file"]

agent Contractor {
    tools = FILE_TOOLS                // ✅ 复用 const
    ...
}

agent Researcher {
    tools = RESEARCH_TOOLS            // ✅ 复用 const
    ...
}
```

**严格校验**（编译期）：

| 写法 | 是否允许 | 原因 |
|------|---------|------|
| `tools = CONST_NAME` | ✅ | 模块级 const，静态可追踪 |
| `tools = ["...", ...]` | ✅ | 字面量列表，静态 |
| `tools = my_var` | ❌ | 可变变量，动态 |
| `tools = my_fn` | ❌ | 函数，不是列表 |
| `tools = OtherAgent` | ❌ | agent，不是列表 |
| `tools = UNKNOWN` | ❌ | 未定义 |
| 两次 `tools = ...` | ❌ | 重复声明，语义不明 |

> ⚠️ 不支持 agent 内部 const、不支持表达式拼接（如 `A + B`）——这是**安全设计**，不是缺陷。工具是 LLM 的能力边界，必须静态可审计。

**可用内建工具：**

| 工具 | 功能 | 参数 |
|------|------|------|
| `web_search` | 搜索网页（Bing） | `query: str` |
| `web_fetch` | 获取网页内容 | `url: str` |
| `read_file` | 读取文件 | `path: str` |
| `write_file` | 写入文件 | `path: str, content: str` |
| `shell_exec` | 执行 shell 命令 | `command: str` |
| `calculate` | 数学计算 | `expression: str` |
| `load_skill` | 加载技能文档 | `name: str` |

> **注意**：`load_skill` 总是可用（即使不在 `tools` 列表中），用于加载技能文档。

## Agent 系统提示词架构（v1.15+）

Helen v1.15 引入了清晰的 System/User 角色分离，使 agent 的提示词架构符合 LLM 最佳实践。

### System Prompt（行为规则层）

System prompt 自动注入以下内容，定义 agent 的行为规则和能力边界：

```
1. Framework Instructions (P0+P1 框架指令)
   - Tool Use (CRITICAL): MUST use tools, not describe
   - Skills (CRITICAL): MUST load relevant skills
   - Parallel Tool Calls: batch independent calls
   - Completion Criteria: working artifact, not description
   - Memory Management: save durable facts, skip trivial

2. Helen Language Conventions (语言规范)
   - Core Principles (agent-centric design)
   - Skill-Driven Development (load skills before coding)
   - Code Generation Best Practices
   - Common Pitfalls to Avoid
   - Quick Reference (testing syntax, agent structure)

3. Agent Description (角色定义)
   - 来自 agent 的 description 字段

4. Skill Index (技能索引)
   - <available_skills> 列表
   - MUST load 指令
```

### User Prompt（任务层）

User prompt 包含具体的任务描述和查询：

```
1. Rendered Agent Prompt (任务描述)
   - 来自 agent 的 prompt 字段（渲染后）
   - 如果 prompt 包含 {{var}}，会被替换为实际值

2. LLM Act Expression (实际查询)
   - 来自 llm act 后面的表达式
   - 例如：llm act "How do I sort a list?"
```

### 示例

```helen
agent CodingAgent {
    description "A coding assistant"
    prompt "You are a Python expert. Help me with coding."
    tools ["read_file", "write_file"]
    
    main {
        llm act "How do I sort a list?"
    }
}
```

**LLM 看到的消息结构**：

```
System: <framework_instructions>
        You MUST use your tools to take action...
        You MUST load relevant skills...
        </framework_instructions>
        
        <helen_conventions>
        Helen language rules and best practices...
        </helen_conventions>
        
        A coding assistant                    ← description
        
        <available_skills>
        Before replying, scan skills below...
        You MUST load relevant skills...
        </available_skills>

User:   You are a Python expert.             ← prompt (任务描述)
        Help me with coding.
        
        How do I sort a list?                ← llm act expression (查询)
```

### 设计原则

| 原则 | 说明 |
|------|------|
| **角色清晰** | System = 行为规则，User = 具体任务 |
| **自动注入** | Framework 和 Conventions 对所有 agent 自动生效 |
| **技能驱动** | 强制要求加载相关技能再生成代码 |
| **执行导向** | 强制要求使用工具执行，而不是描述 |
| **向后兼容** | 所有现有 agent 定义继续工作 |

### Token 预算

系统提示词约占 1300 tokens（~13%），在典型 32k-128k 上下文窗口中完全可接受。

---

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

## Agent 上下文管理 (v1.15)

Helen v1.15 引入了完整的上下文管理增强，让 Agent 在长时间运行中保持高效和稳定。

### 概述

上下文管理系统包含三层：

| 组件 | 作用 | 说明 |
|------|------|------|
| **工作记忆** | 自动跟踪关键信息 | 活跃文件、最近决策、待办事项、错误历史 |
| **渐进压缩** | 五层压缩管线 | 从 60% 到 95% 使用率，逐层升级 |
| **缓存感知压缩** | 优化缓存命中 | 保留前缀不变，仅修改后缀 |

### `context {}` 配置块

在 Agent 声明中使用 `context {}` 配置上下文策略：

```helen
agent ResearchAssistant {
    description "Long-running research agent"
    
    // v1.15: 上下文配置
    context {
        compression "graduated"      // "none" | "graduated" | "traditional"
        cache-aware true             // 启用缓存感知压缩
        working-memory true          // 启用工作记忆
        working-memory-tokens 8000   // 工作记忆词元预算
    }
    
    tools ["read_file", "write_file", "web_search"]
    
    prompt "You are a research assistant. Help the user find and summarize information."
}

// 中文关键字等价
agent 研究助手 {
    上下文 {
        压缩 "graduated"
        缓存感知 true
        工作记忆 true
        工作记忆词元 8000
    }
}
```

**配置选项**：

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `compression` | str | `"graduated"` | 压缩策略 |
| `cache-aware` | bool | `true` | 缓存感知压缩 |
| `working-memory` | bool | `true` | 工作记忆开关 |
| `working-memory-tokens` | int | `5000` | 工作记忆预算 |

### 工作记忆

启用 `working-memory true` 后，Agent 自动跟踪：

- **活跃文件** — 通过 `read_file`、`write_file` 操作的文件
- **最近决策** — Assistant 做出的关键选择（如 "Modified src/main.py"）
- **待办事项** — 从 TODO/FIXME/`[ ]` 注释中提取
- **错误历史** — shell 命令失败记录

```helen
// 辅助函数：修复代码
fn fix_code(code: str): str {
    // 实际的代码修复逻辑
    return code  // 简化示例
}

agent CodeReviewer {
    context {
        working-memory true
        working-memory-tokens 6000
    }
    
    tools ["read_file", "write_file", "patch_file"]
    
    functions {
        fn fix_code(code: str): str {
            // 实际的代码修复逻辑
            return code  // 简化示例
        }
    }
    
    main {
        // 自动跟踪：这些操作会更新工作记忆
        let code = read_file("src/main.py")
        let fixed = fix_code(code)
        write_file("src/main.py", fixed)
        
        // LLM 现在知道哪些文件被修改了
        return llm act "Review the changes"
    }
}
```

### 渐进压缩 (五层管线)

当上下文使用率增长时，自动应用逐层压缩：

| 层级 | 阈值 | 策略 | 成本 |
|------|:----:|------|:----:|
| Layer 1: Budget Reduction | 60% | 替换大工具输出为引用 | 零 |
| Layer 2: Snip | 70% | 丢弃旧的对话轮次 | 零 |
| Layer 3: Microcompact | 80% | 清除旧工具结果，保留决策 | 零 |
| Layer 4: Context Collapse | 90% | 归档并生成结构摘要 | 零 |
| Layer 5: Auto-Compact | 95% | 激进压缩（最后手段） | 零 |

所有层都是零推理成本（不调用 LLM）。

### 缓存感知压缩

启用 `cache-aware true` 后，压缩策略变为缓存友好：

- **稳定前缀**（30%）— 前 N 条消息完全不变，最大化缓存命中
- **可压缩后缀**（70%）— 仅在后缀区域应用压缩
- **批量阈值**（75%）— 使用率低于 75% 时不触发压缩

预期效果：
- 缓存命中率：10-20% → **70-80%**
- 成本降低：**50-70%**
- 延迟降低：**30-50%**

### 三通道上下文

启用工作记忆后，LLM 看到的上下文分为三个通道：

| 通道 | 比例 | 内容 |
|------|:----:|------|
| 系统指令 | 15% | 框架指令、Agent 描述、技能索引 |
| 工作记忆 | 50% | 活跃文件、决策、待办、错误 |
| 对话历史 | 35% | 压缩后的对话消息 |

### 最佳实践

| Agent 类型 | 推荐配置 | 说明 |
|-----------|---------|------|
| 研究型 Agent | `compression "graduated"` + `working-memory true` | 长对话，需跟踪文件 |
| 快速响应 | `compression "none"` + `working-memory false` | 短对话，低延迟 |
| 多轮对话 | `cache-aware true` + `working-memory-tokens 8000` | 高缓存命中率 |

---

> **下一步**: [[tutorial/06-llm-statements|LLM 语句实战]]

---

# 教程 06: LLM 语句

> llm act / llm if 实战

---

## LLM 语句概述

Helen 有两个关键字级 LLM 语句：

| 语句 | 用途 | 返回值 |
|---|---|---|
| `llm act` | 让 LLM 执行任务（支持可选流式回调） | 响应文本 |
| `llm if` | 让 LLM 分类路由 | 执行匹配分支或返回值 |

---

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

---

`llm act` 也可以作为表达式直接使用，不需要 agent 上下文：

```helen
// 顶层直接调用
llm act "translate hello to chinese."

// 在函数中使用
fn translate(text, target) {
    return llm act "translate " + text + " to " + target
}

// 赋值给变量
let result = llm act "summarize this article"

// 字符串拼接构建 prompt
let topic = "climate change"
let analysis = llm act "analyze the impact of " + topic
```

**语法对比：**

| 形式 | 语法 | 用途 |
|------|------|------|
| 表达式形式 | `llm act <expr>` | 直接调用 LLM，expr 的值作为 prompt |
| Bare form | `llm act` | 在 agent main 中省略参数，自动使用渲染后的 prompt |

**注意：** 语句形式 `llm act Agent(args) "desc"` 已废弃，请使用 `Agent(args)` 调用 agent。

**何时使用表达式形式：**
- 快速原型测试，不想定义 agent
- 动态构建 prompt
- 在 REPL 中直接调用 LLM
- 简单的 LLM 调用场景

---

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

---

## llm act 流式输出（on_chunk / on_complete）

`llm act` 支持可选的 `on_chunk` 和 `on_complete` 回调，用于逐 chunk 流式输出 LLM 响应，适用于长文本生成场景。

### 基本用法

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

fn on_done() {
    print("\n\n✅ 流式传输完成")
}

main {
    llm act "Write a short story" on_chunk handle_chunk on_complete on_done
}
```

`on_complete` 回调在流式传输完成后调用，适合用于：
- 显示完成提示
- 记录统计信息（如总 token 数）
- 触发后续操作

### 在 agent 中使用

`llm act` 的流式回调在 agent 内自动使用 agent 的配置（model、temperature、prompt）：

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
| `llm act` | 获取完整响应文本（可选流式回调） | 等待完成后返回，或通过 on_chunk 逐 chunk 输出 |
| `llm if` | LLM 分类路由 | 等待完成后执行分支 |

---

## 对比：何时使用哪个？

| 场景 | 使用 |
|---|---|
| 需要 LLM 返回文本 | `llm act` |
| 需要 LLM 做分类决策 | `llm if` |
| 需要 LLM 从选项中选择并执行代码 | `llm if` + `branch` |
| 需要实时输出生成过程 | `llm act` + `on_chunk` 回调 |
| 多步骤决策 | 嵌套 `llm if` |
| 需要结果变量 | `llm if` 或 `llm act` |

---

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

### 上下文窗口保护 (HLD 3.12)

对话历史会**自动裁剪后传给 LLM**（之前版本存在 bug：history 只累积但从未传给 API，现在已修复）。

| 保护 | 行为 |
|---|---|
| Model-aware context window | 根据模型自动选择 context window 大小（qwen3.7-plus=131072、gpt-4o=128000 等）|
| 自动裁剪 | 每次 LLM 调用前，根据 system prompt + 当前 prompt 计算剩余预算，删除最旧消息 |
| 自动压缩 | 历史超过 context window 80% 时，旧消息压缩成 `[Previous conversation summary]` 系统消息 |
| 工具结果上限 | 单次工具循环最多 10 个结果（`MAX_TOOL_RESULTS_PER_TURN=10`）|
| 上下文超限恢复 | API 返回 context-too-large 错误时，自动删除最老消息并重试一次 |

Token 估算使用字符类型感知（CJK 1.2 字符/token，拉丁 4 字符/token），误差约 15%。

---

## REPL 中的 LLM 调用

在 REPL 中，`llm act` 表达式会调用真实的 LLM（通过 HTTP API）：

```bash
$ helen repl
>>> llm act "translate hello to chinese"
'hello → 你好 (nǐ hǎo)'
>>> let result = llm act "what is 2+2?"
>>> result
'4'
```

**性能：**
- REPL 和脚本模式均使用 `HttpLLMRuntime`，直接调用 API
- 响应时间：7-11秒（取决于网络和模型）
- 自动从 `~/.helen/config.yaml` 或 `~/.helen/.env` 读取配置

**配置：**
确保 `~/.helen/config.yaml` 包含：
```yaml
llm:
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  api_key: "your-api-key-here"
  model: "qwen3.7-plus"
```

或使用 `~/.helen/.env`：
```
HELEN_API_KEY=***
HELEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

**注意：**
- 脚本执行（`helen <file>`）和 REPL 均直接使用 `HttpLLMRuntime` 调用真实 LLM
- 向后兼容 `~/.hermes/.env` 配置

---

## Function Calling（工具调用）

当 Agent 配置了 `tools = [...]` 时，`llm act` 会自动进入 function calling 循环：

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

**内置工具列表（10 个）：**

| 工具 | 功能 | 参数 |
|------|------|------|
| `web_search` | 搜索网页（Bing） | `query: str` |
| `web_fetch` | 获取网页内容 | `url: str` |
| `read_file` | 读取文件 | `path: str` |
| `write_file` | 写入文件（覆盖） | `path: str, content: str` |
| `patch_file` | 精确修改文件（9 种模糊匹配策略） | `path: str, old_string: str, new_string: str` |
| `shell_exec` | 执行 shell 命令 | `command: str` |
| `calculate` | 数学计算 | `expression: str` |
| `find_files` | 按 glob 模式查找文件 | `path: str, pattern: str = "**/*", max_results: int = 200` |
| `search_files` | 按内容搜索文件（文本/正则） | `path: str, pattern: str, regex: bool = false, case_sensitive: bool = true, max_results: int = 100` |
| `load_skill` | 加载技能文档（总是可用） | `name: str` |

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

---

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
        // prompt 渲染后 → system_prompt
        // "Translate the following text to French:\nHello"
        // → 作为 {"role": "system"} 注入
        return llm act "Please translate accurately"
        // → 作为 {"role": "user"} 注入
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

---

## 练习

1. 创建一个 llm if 三层嵌套的分类系统
2. 使用 llm if 让 LLM 选择算法策略并返回结果
3. 使用 llm act 实现一个翻译管道
4. 观察多次 LLM 调用后的对话历史

---

# 教程 07: 异步编程

> async / await / for await / AggregateError / 并发 Agent 调用 / 流式迭代

---

## 概述

Helen 支持 `async` 启动并发 Agent 调用，通过 `await [list]` 等待全部完成。
`async Agent(...)` 是表达式，返回 `Task` 对象，可存入变量。

**真正的异步并发**：使用纯 `asyncio` 单线程并发，LLM 调用非阻塞执行，内存开销接近零。

---

## 基本用法

```helen
agent Researcher {
    description "Research a topic"
    prompt "Research and summarize:"
    main {
        let topic = "AI in healthcare"
        let research_task = async Researcher(topic)
        let data_task = async Analyst(topic)
        let results = await [research_task, data_task]
        let research = results[0]
        let analysis = results[1]
        print("Research: " + research)
        print("Analysis: " + analysis)
    }
}

agent Analyst {
    description "Analyze data"
    prompt "Analyze the following data:"
}
```

---

## Task 对象

`async call` 返回 `Task` 对象：

```helen
let task = async MyAgent(input)

// Task 方法 (未来版本支持)
// task.is_success() → bool
// task.get_result() → Any
// task.get_error() → Exception
```

---

## await 行为

### 全部成功

```helen
let results = await [task1, task2, task3]
// results = [result1, result2, result3]
```

### 部分失败

```helen
try {
    let results = await [task1, task2, task3]
} catch AggregateError(err) {
    // err.errors = [(index, exception), ...]
    for error_info in err.errors {
        print("Task " + str(error_info[0]) + " failed: " + str(error_info[1]))
    }
}
```

---

## 实际示例：多源信息聚合

```helen
agent NewsSearcher {
    description "Search latest news"
    prompt "Search for news about:"
}

agent AcademicSearcher {
    description "Search academic papers"
    prompt "Find papers about:"
}

agent SocialSearcher {
    description "Search social media"
    prompt "Find social media posts about:"
}

agent Synthesizer {
    description "Synthesize information from multiple sources"
    prompt "Synthesize the following sources into a coherent report:"
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

        // 综合所有结果
        let report = Synthesizer(sources[0] + "\n" + sources[1] + "\n" + sources[2])
        print(report)
    } catch AggregateError(err) {
        print("Some sources failed to load")
        // 仍然可以使用成功的结果
    }
}
```

---

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

---

## 性能特性

**真正的异步并发**：使用纯 `asyncio` 单线程并发

- **LLM 调用**：通过 `asyncio` 非阻塞执行
- **内存开销**：接近零（无额外线程）
- **并发效率**：3 个 1 秒的 LLM 调用 → ~1 秒完成（并发）

**对比传统线程池**：
- 线程池：3 个线程 × 8MB = 24MB
- asyncio：0 个线程 = ~0MB
- **内存节省**：100%

---

## 注意事项

| 规则 | 说明 |
|---|---|
| `async` 可用于表达式 | `let task = async Agent()` ✅ |
| `async` 也可作为语句 | `async Agent()` ✅（立即执行） |
| `await` 参数必须是列表 | `await [task]` ✅，`await task` ❌ |
| 真正异步并发 | LLM 调用通过 asyncio 非阻塞执行 |
| 错误聚合 | 多个失败 → `AggregateError`（可被 try-catch 捕获） |
| 环境隔离 | 每个 Task 有独立的环境快照 |
| `for await` | 异步迭代流式响应，只能在 async 上下文中使用 |

---

## 练习

1. 创建三个并发 Agent 调用，处理同一输入的不同方面
2. 模拟一个失败的任务，使用 try-catch 处理 AggregateError
3. 比较串行调用和 async/await 的执行顺序

---

## v1.10 HTTP 异步方法

### 概述

v1.10 添加了异步 HTTP 方法，支持并发 LLM 调用，基于 `httpx.AsyncClient` 实现。

### 异步方法

```helen
// 同步方法（已有）
llm act target "description"
llm act target "description" on_chunk handle_chunk   // 流式回调

// 异步方法（v1.10 新增）
await llm act_async target "description"
await llm act_stream_async target "description"
```

### 基本用法

```helen
agent AsyncAgent {
  main {
    // 单次异步调用
    let result = await llm act_async Translate "Hello, World!"
    print(result)
  }
}
```

### 并发调用

```helen
agent ConcurrentTranslator {
  main {
    // 并发翻译多个文本
    let [r1, r2, r3] = await [
      llm act_async Translate "Hello",
      llm act_async Translate "World",
      llm act_async Translate "Helen"
    ]
    
    print("Results: " + str([r1, r2, r3]))
  }
}
```

### 异步流式调用

```helen
agent StreamAgent {
  main {
    // 异步流式获取完整文本
    let full_text = await llm act_stream_async WriteStory "A cat named Luna"
    print(full_text)
  }
}
```

### 性能对比

| 场景 | 同步 | 异步 | 提升 |
|------|------|------|------|
| 单次调用 | 1.5s | 1.5s | 0% |
| 3 次并发 | 4.5s | 1.6s | **65%** |
| 5 次并发 | 7.5s | 1.8s | **76%** |
| 10 次并发 | 15s | 2.1s | **86%** |

### 实际示例：批量处理

```helen
agent BatchProcessor {
  main {
    let items = ["item1", "item2", "item3", "item4", "item5"]
    
    // 同步方式：串行处理
    let sync_results = []
    for item in items {
      let result = llm act Process(item)
      sync_results.push(result)
    }
    // 耗时：5 * 1.5s = 7.5s
    
    // 异步方式：并发处理
    let async_tasks = []
    for item in items {
      async_tasks.push(llm act_async Process(item))
    }
    let async_results = await async_tasks
    // 耗时：~1.8s（提升 76%）
  }
}
```

### 错误处理

```helen
agent SafeAsyncAgent {
  main {
    try {
      let result = await llm act_async Task "Complex task"
      print("Success: " + str(result))
    } catch LLMError as e {
      print("LLM Error: " + e.message)
    } catch TimeoutError as e {
      print("Timeout: " + e.message)
    }
  }
}
```

### 混合使用

```helen
agent MixedAgent {
  main {
    // 同步调用：简单任务
    let simple = llm act SimpleTask "Quick task"
    
    // 异步调用：复杂任务
    let complex = await llm act_async ComplexTask "Long task"
    
    // 并发异步：多个任务
    let [r1, r2] = await [
      llm act_async Task1 "First",
      llm act_async Task2 "Second"
    ]
  }
}
```

### 注意事项

1. **仅在 async 上下文中使用**: `await` 只能在 `main` 或 `async call` 中使用
2. **连接池自动管理**: `httpx.AsyncClient` 自动管理连接池
3. **超时配置**: 统一使用配置的超时时间（默认 60s）
4. **资源清理**: 程序退出时自动关闭连接

### 与 async call 的区别

```helen
// async call: 并发调用多个 agent
async call AgentA()
async call AgentB()
let results = await [agentA, agentB]

// await llm act_async: 并发调用 LLM
let [r1, r2] = await [
  llm act_async Task1 "First",
  llm act_async Task2 "Second"
]

// 可以混合使用
async call AgentA()
let llm_result = await llm act_async Task "Task"
let agent_result = await agentA
```

---

**最后更新**: 2026-07-01  
**版本**: v1.10

---

# 教程 08: 模块与导入

> import / 多格式 / 跨文件复用 / 路径安全

---

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

---

## 导入别名

```helen
import "./math_utils.helen" as math

main {
    let result = math.add(1, 2)
}
```

---

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

---

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

---

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

---

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

---

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

---

## 练习

1. 创建一个 utils.helen 文件，包含常用函数
2. 在 main.helen 中导入并使用这些函数
3. 创建一个 config.json 并导入
4. 尝试循环导入，观察行为

---

# 教程 09: Python FFI

> 导入 Python 库 / 调用 Python 函数 / 类型自动转换

---

## 概述

Helen 支持通过 Python FFI（外部函数接口）直接导入和使用 Python 库。这让 Helen 可以访问 Python 的整个生态系统（40 万+ 包），包括数值计算、网络请求、数据处理等。

**核心特性：**
- ✅ 使用 `import` 语法导入 Python 模块
- ✅ 自动类型转换（Helen ↔ Python）
- ✅ 调用 Python 函数、访问属性和常量
- ✅ 支持嵌套模块（如 `os.path`）
- ✅ 复杂对象自动包装

---

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

---

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

---

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

---

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

---

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

---

## 性能注意事项

- **类型转换**：简单类型（int/float/str）转换开销极低
- **复杂对象**：大型 list/dict 转换有一定开销，建议批量处理
- **函数调用**：每次调用都有跨语言开销，避免在紧密循环中频繁调用

---

## 与 Helen 原生功能的对比

| 功能 | Helen 原生 | Python FFI |
|------|-----------|-----------|
| 字符串处理 | ✅ 36 个 string 函数 | ✅ 可用 Python re 等 |
| 数学计算 | ✅ 15 个 math 函数 | ✅ 可用 numpy/scipy |
| 文件操作 | ✅ 16 个 file 函数 | ✅ 可用 os/pathlib |
| 网络请求 | ✅ 9 个 network 函数 | ✅ 可用 requests（高级场景） |
| 数据处理 | ✅ 25 个 data 函数（JSON/CSV/HTML/XML） | ✅ 可用 pandas（大数据集） |
| 机器学习 | ❌ 无 | ✅ 可用 torch/tensorflow |

**建议**：优先使用 Helen 原生功能（255 个内置函数覆盖常见需求），需要高级功能（如大数据处理、机器学习）时使用 Python FFI。

---

## 练习

1. 导入 `math` 模块，计算圆的面积（半径 = 5）
2. 导入 `json` 模块，将 map 转换为 JSON 字符串并解析回来
3. 导入 `os.path` 模块，提取文件路径的目录和文件名
4. 创建一个 Agent，使用 Python 的 `math` 模块进行复杂计算

---

> **下一步**: 学习 [[tutorial/15-python-bridge|Python Bridge]] — 让 Python 直接使用 Helen Agent

---

# 教程 10: 标准库参考

> 255 个内置函数，覆盖 AI 应用开发的所有核心需求

## 概览

Helen 标准库提供 255 个内置函数，分为 17 大类别：

| 类别 | 函数数 | 功能 |
|------|--------|------|
| **Core** | 11 | 类型转换、通用操作 |
| **String** | 37 | 字符串处理、正则、文本分析、模板插值 |
| **Data** | 25 | JSON、HTML、CSV、Markdown、YAML、TOML、XML |
| **Collection** | 22 | 列表、字典、集合操作 |
| **Network** | 9 | HTTP 请求、URL 处理 |
| **Time** | 13 | 日期时间、格式化、运算 |
| **Math** | 15 | 数学运算、统计分析 |
| **File** | 18 | 文件读写、目录操作、临时文件、文件搜索 |
| **System** | 18 | 环境变量、CLI 参数、进程管理、日志 |
| **Crypto** | 11 | 哈希、随机数 |
| **IO** | 5 | 流式输出控制 |
| **Context** | 2 | 上下文管理（v1.15 新增） |
| **Transcript** | 6 | 会话记录管理（v1.16 新增） |
| **Media** | 12 | 多模态媒体处理（v1.17 新增） |

## 多语言 stdlib (v1.10)

Helen 的 stdlib 支持多语言函数名。每个 stdlib 函数都有英文 canonical 名和本地化别名，启动时全量加载，可按需使用。

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
| `date_format` | `日期格式化` | Time |

完整列表见 `helen/stdlib/locales/zh.py`。

### 使用示例

```helen
// 直接用中文 stdlib 函数名（不需要任何 import 或 alias）
函数 数据处理() {
    设 原始数据 = [3, 1, 4, 1, 5, 9, 2, 6]
    设 排序后 = 排序(原始数据)
    设 去重后 = 去重(排序后)
    返回 长度(去重后)
}

// 中英混用也完全合法
函数 混合使用() {
    let data = [1, 2, 3]
    let sorted = 排序(data)     // 英文变量 + 中文函数
    return len(sorted)          // 切回英文
}

// 处理网络数据
函数 获取数据() {
    设 响应 = http获取("https://api.example.com/data")
    设 解析后 = json解析(响应)
    返回 解析后["name"]
}
```

### 自定义别名

如果需要给自己的函数或 stdlib 函数起额外的别名，使用 `alias` 语句：

```helen
// 给 stdlib 函数起自定义别名
alias len as 我的长度
alias print as 输出

// 给用户函数起别名
函数 greet(name: str): str {
    返回 "Hello, " + name
}
alias greet as 打招呼
```

中文关键字 `别名` 等价：

```helen
别名 len as 长度
```

### 设计原则

- **一套机制**：stdlib 别名和用户 `alias` 使用相同的 Environment binding，行为完全一致
- **全量加载**：所有 locale 的别名表启动时全部注册，不按 locale 过滤
- **locale 只影响展示**：`~/.helen/config.yaml` 中的 `locale: zh` 只影响 docs/LSP/错误消息的语言，不影响运行时可用的名字
- **向后兼容**：英文 canonical 名永远可用

### 扩展新语言

添加新语言的 stdlib 别名只需创建一个新文件，不需要改语法/解析器/解释器：

```python
# helen/stdlib/locales/ja.py
ALIASES = {
    "長さ": "len",
    "表示": "print",
    "ソート": "sort",
    # ...
}
```

启动时自动加载所有 `helen/stdlib/locales/*.py` 文件中的别名。

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

## CLI 参数（System 模块）

Helen 程序可以直接访问命令行参数。文件名之后的所有参数会传递给程序：

```bash
$ helen my_tool.helen --verbose --output=json --port=8080 input.txt
```

### argv 预定义常量

`argv` 是预定义的 `const list<str>`，包含所有命令行参数：

```helen
// 直接访问
print(argv)  // ["--verbose", "--output=json", "--port=8080", "input.txt"]
print(len(argv))  // 4

// 检查特定参数
if contains(argv, "--verbose") {
    print("详细模式已开启")
}

// 遍历所有参数
for arg in argv {
    print("参数: " + arg)
}
```

`argv` 是 `const`，不可重新赋值。它在 agent 作用域中自动可见（通过 const 只读共享机制）。

### get_cli_args() 函数

与 `argv` 等价的标准库函数形式：

```helen
let args = get_cli_args()  // 与 argv 相同
```

### parse_cli_args() 结构化解析

**自动模式**（无需参数）—— 自动识别各类参数：

```helen
let parsed = parse_cli_args()
// 输入: --verbose --output=json --port 8080 input.txt
// 结果: {
//   verbose: true,
//   output: "json",
//   port: "8080",
//   _positional: ["input.txt"]
// }
```

支持的参数格式：
- `--flag` → 布尔值 `true`
- `--key=value` → 字符串值（在第一个 `=` 处分割）
- `--key value` → 字符串值（空格分隔）
- `-v` → 短标志，布尔值 `true`
- 其他 → 位置参数（收集到 `_positional`）

**Spec 模式**（传入规格 map）—— 带类型转换和默认值：

```helen
let spec = {
    "verbose": {"type": "flag", "default": false},
    "output": {"type": "string", "default": "text"},
    "port": {"type": "int", "default": 3000}
}
let config = parse_cli_args(spec)
// port 自动转为 int 类型
print(type(config["port"]))  // "int"
```

支持的 spec 类型：`flag`、`string`、`int`、`float`。

> **注意**：嵌套 map 字面量中 `}}` 会被词法分析器识别为模板引用关闭符。需要在两个 `}` 之间加空格：`} }`。

## Context 函数 (2) (v1.15)

上下文管理函数，用于控制 LLM 对话上下文的生命周期。

### 清空上下文

```helen
// 清空当前对话历史
let result = clear_context()
print("已清空 " + str(result["cleared_messages"]) + " 条消息")
print("释放约 " + str(result["cleared_tokens"]) + " tokens")
// 返回: {"status": "ok", "cleared_messages": 5, "cleared_tokens": 1200, "warning": "..."}
```

**使用场景**：
- 用户要求"重新开始"对话
- 错误恢复时重置上下文
- 长对话 agent 定期清理

### 压缩上下文

```helen
// 自动压缩（基于 token 阈值）
let result = compress_context("auto")
print("从 " + str(result["original_tokens"]) + " 压缩到 " + str(result["compressed_tokens"]))
// 返回: {"status": "ok", "original_messages": 10, "compressed_messages": 5, ...}

// 强制使用 LLM 摘要压缩
compress_context("summarize")

// 截断保留最近 10 条消息
compress_context("truncate")
```

**压缩策略**：
- `"auto"`：自动选择（默认，仅在 token 超过阈值时压缩）
- `"summarize"`：使用 LLM 生成摘要（慢但保留上下文）
- `"truncate"`：截断旧消息（快但丢失上下文）
- `"none"`：不压缩（no-op）

**长对话 agent 示例**：

```helen
agent ChatBot {
    main {
        let message_count = 0
        while true {
            let input = prompt("you> ")
            let response = llm act { ... }
            
            message_count += 1
            
            // 每 10 轮对话自动压缩
            if message_count % 10 == 0 {
                let result = compress_context("auto")
                if result["status"] == "ok" {
                    print("已压缩上下文，节省 " + 
                          str(result["original_tokens"] - result["compressed_tokens"]) + 
                          " tokens")
                }
            }
            
            // 用户命令：/clear 清空上下文
            if input == "/clear" {
                clear_context()
                print("上下文已清空")
            }
        }
    }
}
```

## Transcript 函数 (6) (v1.16)

会话记录管理函数，用于访问和操作 Helen 的 TranscriptStore（v1.16 SSOT 架构）。TranscriptStore 是所有对话消息的唯一真实来源，提供持久化、会话恢复和压缩审计功能。

### 获取会话 ID

```helen
// 获取当前会话 ID
let session_id = get_session_id()
print("当前会话: " + session_id)
// 返回: "session_1783492628_d9d9c0aa"
```

**使用场景**：
- 记录会话标识符用于调试
- 在日志中标记会话
- 会话恢复时验证 ID

### 列出所有会话

```helen
// 列出所有 transcript 会话
let sessions = list_sessions()
for session in sessions {
    print(session["session_id"] + ": " + str(session["message_count"]) + " 条消息")
}
// 返回: [{"session_id": "...", "message_count": 50, "size_bytes": 2500, ...}]
```

**返回字段**：
- `session_id`：会话 ID
- `message_count`：消息数量
- `size_bytes`：文件大小（字节）
- `created_at`：创建时间
- `modified_at`：最后修改时间

### 回放会话

```helen
// 回放当前会话（仅有效视图）
let messages = replay_transcript()
for msg in messages {
    print(msg["role"] + ": " + msg["content"])
}

// 回放指定会话，包括压缩的消息
let full = replay_transcript("session_1783492628_d9d9c0aa", true)
```

**参数**：
- `session_id`（可选）：要回放的会话 ID，默认当前会话
- `include_compressed`（可选）：是否包括被压缩的消息，默认 false

**返回**：消息列表，每条消息包含 `role`、`content`、`uuid`、`timestamp`

### 导出会话

```helen
// 导出为 JSON
export_transcript("my_chat.json", "json")

// 导出为 Markdown
export_transcript("my_chat.md", "markdown")

// 导出为纯文本
export_transcript("my_chat.txt", "text")

// 导出指定会话
export_transcript("old_chat.json", "json", "session_1783492600_abc12345")
```

**参数**：
- `output_path`：输出文件路径
- `format`：导出格式（"json"、"markdown"、"text"）
- `session_id`（可选）：要导出的会话 ID

**返回**：输出文件路径（成功）或空字符串（失败）

### 获取压缩审计

```helen
// 获取所有压缩事件的审计追踪
let audit = get_compression_audit()
for event in audit {
    print("层级: " + event["layer"])
    print("压缩前: " + str(event["original_token_count"]) + " tokens")
    print("压缩后: " + str(event["compressed_token_count"]) + " tokens")
    print("摘要: " + event["summary"])
}
```

**返回字段**：
- `uuid`：边界标记 UUID
- `layer`：压缩层级（"graduated"、"traditional"、"cache_aware+graduated" 等）
- `head_uuid`：压缩范围起始消息 UUID
- `tail_uuid`：压缩范围结束消息 UUID
- `anchor_uuid`：锚点消息 UUID
- `summary`：压缩摘要
- `original_token_count`：压缩前 token 数
- `compressed_token_count`：压缩后 token 数
- `timestamp`：压缩时间戳

**使用场景**：
- 分析压缩效率
- 调试压缩问题
- 审计对话历史

### 恢复会话

```helen
// 恢复到指定会话
let success = resume_session("session_1783492628_d9d9c0aa")
if success {
    print("会话已恢复")
    let messages = replay_transcript()
    print("已加载 " + str(len(messages)) + " 条消息")
} else {
    print("恢复失败，会话可能不存在")
}
```

**参数**：
- `session_id`：要恢复的会话 ID

**返回**：true（成功）或 false（失败）

**使用场景**：
- 恢复之前的对话
- 在 REPL 中继续之前的工作
- 加载历史会话进行分析

### 中文别名

Transcript 函数支持中文别名，可以直接使用中文函数名：

| 英文 | 中文 | 说明 |
|------|------|------|
| `get_session_id` | `获取会话id` | 获取当前会话 ID |
| `list_sessions` | `列出会话` | 列出所有会话 |
| `replay_transcript` | `回放会话` | 回放会话消息 |
| `export_transcript` | `导出会话` | 导出会话到文件 |
| `get_compression_audit` | `压缩审计` | 获取压缩历史 |
| `resume_session` | `恢复会话` | 恢复到指定会话 |

**使用示例**：

```helen
// 使用中文函数名
let 会话id = 获取会话id()
print("当前会话: " + 会话id)

// 列出所有会话
let 会话列表 = 列出会话()
for 会话 in 会话列表 {
    print(会话["session_id"] + ": " + str(会话["message_count"]) + " 条消息")
}

// 回放当前会话
let 消息 = 回放会话()
for 消息 in 消息 {
    print(消息["role"] + ": " + 消息["content"])
}

// 导出会话
导出会话("我的对话.json", "json")

// 恢复会话
let 成功 = 恢复会话("session_1783492628_d9d9c0aa")
```

> **提示**：中文别名和英文函数名可以混合使用，Helen 会在启动时全量加载所有别名。完整别名列表见 `helen/stdlib/locales/zh.py`。

### REPL 命令

除了 stdlib 函数，还可以在 REPL 中使用以下命令：

```
:transcript           # 显示当前 transcript 视图
:transcript --full    # 显示完整 transcript（包括压缩的消息）
:transcript --audit   # 显示压缩审计追踪
:sessions             # 列出所有会话
:session_id           # 显示当前会话 ID
:resume <session_id>  # 恢复到指定会话
```

### 配置

在 `~/.helen/config.yaml` 中配置 transcript：

```yaml
transcript:
  enabled: true              # 启用 TranscriptStore（默认 true）
  backend: "sqlite"          # 后端类型："jsonl" 或 "sqlite"
  session_dir: "~/.helen/sessions"
  max_memory_items: 1000     # LRU 缓存大小
```

**后端选择**：
- `jsonl`：简单、人类可读、崩溃安全（默认）
- `sqlite`：高性能、索引优化、WAL 模式

**详细文档**：见 [[runtime/transcript-store]]

## File 函数 (18)

文件操作函数分为三组：基础 I/O、目录操作、文件搜索。

### 文件搜索 (2) (v1.15 新增)

#### glob_files — 递归查找文件

```helen
// 查找所有 Python 文件（递归）
let py_files = glob_files("src", "*.py")
// 返回: ["main.py", "utils/helper.py", "tests/test_main.py"]

// 查找特定模式的文件
let test_files = glob_files(".", "*test*.py")
// 返回: ["test_main.py", "tests/test_utils.py"]

// 使用 ** 显式递归
let md_files = glob_files("docs", "**/*.md")
// 返回: ["readme.md", "guide/intro.md", "api/reference.md"]

// 复杂模式
let config_files = glob_files("config", "**/*.{json,yaml,yml}")
// 返回配置文件列表
```

**参数**：
- `path` (str): 搜索根目录
- `pattern` (str, 可选): glob 模式，默认 `"**/*"`（所有文件）

**返回**：`list<str>` — 匹配文件的相对路径列表

**示例**：统计项目中所有 Python 文件的行数

```helen
fn 统计代码行数(目录: str) {
    let files = glob_files(目录, "*.py")
    let total_lines = 0
    for file in files {
        let content = read_file(file)
        total_lines += len(split(content, "\n"))
    }
    return {"files": len(files), "lines": total_lines}
}

let stats = 统计代码行数("src")
print("找到 " + str(stats["files"]) + " 个文件，共 " + str(stats["lines"]) + " 行")
```

#### grep_files — 搜索文件内容

```helen
// 字面量搜索
let matches = grep_files("src/", "TODO")
// 返回: [{"file": "main.py", "line": 42, "text": "    # TODO: fix this"}]

// 正则搜索
let functions = grep_files("src/", "def \\w+\\(", regex=true)
// 返回所有函数定义

// 大小写不敏感搜索
let errors = grep_files("logs/", "error", case_sensitive=false)
// 返回所有包含 "error"（不区分大小写）的行

// 限制结果数量
let first_10 = grep_files(".", "pattern", max_results=10)
```

**参数**：
- `path` (str): 文件路径或目录
- `pattern` (str): 搜索模式（字面量或正则）
- `regex` (bool, 可选): 是否使用正则，默认 `false`
- `case_sensitive` (bool, 可选): 大小写敏感，默认 `true`
- `max_results` (int, 可选): 最大返回数，默认 `100`

**返回**：`list<map>` — 匹配结果列表，每个匹配包含 `file`、`line`、`text` 字段

**示例**：查找所有未处理的异常

```helen
agent 异常检查助手 {
    description "检查代码中未处理的异常"
    main {
        let todos = grep_files("src/", "TODO.*exception", regex=true)
        if len(todos) > 0 {
            print("发现 " + str(len(todos)) + " 处待处理的异常:")
            for match in todos {
                print("  " + match["file"] + ":" + str(match["line"]))
                print("    " + match["text"])
            }
        }
    }
}
```

### 基础文件 I/O (2)

```helen
// 读取文件
let content = read_file("config.json")

// 写入文件（自动创建父目录）
write_file("output/result.txt", "Hello World")
```

### 文件信息 (2)

```helen
// 文件大小（字节）
let size = file_size("document.pdf")
print("文件大小: " + str(size) + " bytes")

// 修改时间（ISO 8601 格式）
let mtime = file_modified("data.csv")
print("最后修改: " + mtime)
```

### 目录操作 (6)

```helen
// 列出目录内容
let files = list_dir("src")
// 返回: ["main.py", "utils.py", "tests/"]

// 带模式过滤
let py_files = list_dir("src", "*.py")
// 返回: ["main.py", "utils.py"]

// 递归遍历目录树
let tree = walk_dir("project")
// 返回: [(dirpath, dirnames, filenames), ...]
for entry in tree {
    let dir = entry[0]
    let subdirs = entry[1]
    let files = entry[2]
    print(dir + ": " + str(len(files)) + " files")
}

// 创建目录
mkdir("new_dir")
mkdir_p("deep/nested/dir")  // 递归创建

// 删除
delete_file("temp.txt")
delete_dir("old_dir", recursive=true)
```

### 文件操作 (2)

```helen
// 复制文件
copy_file("source.txt", "backup.txt")

// 移动/重命名文件
move_file("old_name.txt", "new_name.txt")
```

### 临时文件 (2)

```helen
// 创建临时文件
let tmp = temp_file(suffix=".txt", prefix="data_")
write_file(tmp, "temporary data")
// 使用完毕后需手动删除
delete_file(tmp)

// 创建临时目录
let tmp_dir = temp_dir(prefix="build_")
// 使用完毕后需手动删除
delete_dir(tmp_dir, recursive=true)
```

### 路径操作 (6)

```helen
// 路径拼接
let full_path = path_join("src", "utils", "helper.py")
// 返回: "src/utils/helper.py"

// 提取路径组件
let base = path_basename("/path/to/file.txt")  // "file.txt"
let dir = path_dirname("/path/to/file.txt")    // "/path/to"

// 路径检查
let exists = path_exists("config.json")
let is_dir = path_is_dir("src")
let is_file = path_is_file("main.py")
```

## 异常处理 (v1.9+)

标准库函数调用时抛出的 Python 异常会自动包装为 `RuntimeError`，可通过 try-catch 捕获：

```helen
try {
    let x = len(42)           // Python TypeError
} catch RuntimeError err {
    print(err.message)        // "Python TypeError: object of type 'int' has no len()"
}

try {
    let data = read_file("/nonexistent")
} catch RuntimeError err {
    print(err.message)        // "Python FileNotFoundError: [Errno 2] ..."
}
```

异常消息格式为 `"Python <类型名>: <原始消息>"`，可在 catch 块中通过消息前缀区分具体的 Python 异常类型。

---

# 教程 11: 构建多 Agent 系统

> 完整案例：从需求到实现

---

## 案例：智能客服系统

### 需求

构建一个智能客服系统，能够：
1. 理解用户问题
2. 分类问题类型
3. 根据类型调用不同专业 Agent
4. 生成满意回复

---

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

---

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

---

## 第三步：添加并发优化

```helen
// 知识库查询 agent
agent KnowledgeBase(query: str) {
    description "Search knowledge base"
    prompt "Search knowledge base for: {{query}}"
}

// 历史查询 agent
agent HistoryLookup(topic: str) {
    description "Lookup relevant history"
    prompt "Find relevant history for: {{topic}}"
}

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

---

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

---

## 第五步：优化上下文管理 (v1.15+)

Helen v1.15 引入了完整的上下文管理增强，可以为每个 agent 独立配置：

```helen
// 技术支持 agent：优化上下文管理
agent TechSupport {
    description "Provide technical support"
    model "gpt-4"
    
    // Phase 7: 上下文配置
    context {
        compression "graduated"      // 渐进压缩
        cache-aware true             // 缓存感知
        working-memory true          // 工作记忆
        working-memory-tokens 8000   // 更大的工作记忆
    }
    
    tools ["read_file", "web_search"]
    
    prompt """
    You are a technical support engineer. Help users resolve technical
    issues step by step.
    """
}

// 产品专家：简单的上下文配置
agent ProductExpert {
    description "Answer product questions"
    
    context {
        compression "none"           // 不压缩（短对话）
        working-memory false         // 禁用工作记忆
    }
    
    prompt """
    You are a product expert.
    """
}
```

### 上下文管理最佳实践

| Agent 类型 | 推荐配置 | 说明 |
|-----------|---------|------|
| 研究型 Agent | `compression "graduated"` + `working-memory true` | 长对话，需要跟踪文件 |
| 快速响应 Agent | `compression "none"` + `working-memory false` | 短对话，快速响应 |
| 多轮对话 Agent | `cache-aware true` + `working-memory-tokens 8000` | 提高缓存命中率 |

---

## 第六步：使用工作记忆 (v1.15+)

工作记忆自动跟踪 agent 执行过程中的关键信息：

```helen
// 辅助函数：修复代码
fn fix_code(code: str): str {
    // 实际的代码修复逻辑
    return code  // 简化示例
}

agent CodeReviewer {
    description "Review code changes"
    
    context {
        working-memory true  // 自动跟踪文件操作
    }
    
    tools ["read_file", "write_file", "patch_file"]
    
    functions {
        fn fix_code(code: str): str {
            // 实际的代码修复逻辑
            return code  // 简化示例
        }
    }
    
    main {
        // 自动跟踪：读取的文件
        let code = read_file("src/main.py")
        
        // 自动跟踪：修改的文件
        let fixed = fix_code(code)
        write_file("src/main.py", fixed)
        
        // LLM 现在知道哪些文件被修改了
        return llm act "Review the changes"
        // 工作记忆包含：
        // - 活跃文件: src/main.py
        // - 最近决策: Modified src/main.py
    }
}
```

### 三通道上下文

启用工作记忆后，LLM 看到的上下文分为三个通道：

| 通道 | 比例 | 内容 |
|------|------|------|
| 系统指令 | 15% | 框架指令、agent 描述、技能索引 |
| 工作记忆 | 50% | 活跃文件、最近决策、待办事项、错误历史 |
| 对话历史 | 35% | 压缩后的对话消息 |

---

## 第七步：监控上下文使用 (v1.15+)

在 REPL 中使用 `:stats` 查看上下文使用情况：

```
> :stats
╔══════════════════════════════════════╗
║       Context Usage Statistics        ║
╠══════════════════════════════════════╣
║ ✅ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  12.3%            ║
║ Tokens:   15,984 /  131,072              ║
║ Model:  qwen3.7-plus                  ║
║ Messages: 8                           ║
║                                       ║
║ Working Memory:                       ║
║   Active Files: 3                     ║
║   Recent Decisions: 5                 ║
║   Pending TODOs: 2                    ║
║   Error History: 1                    ║
╚══════════════════════════════════════╝
```

---

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

---

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

---

## 总结

通过这个案例，你学会了：
1. ✅ 声明多个 Agent 及其配置
2. ✅ 使用 `llm if` 进行智能路由
3. ✅ 使用 `async call` + `await` 并发获取上下文
4. ✅ 使用 `try-catch` 处理 LLM 异常
5. ✅ 组织多文件项目结构

---

## 下一步

- 探索 LSP 在 IDE 中的补全和诊断功能
- 使用 `helen repl` 快速原型
- 阅读 [[overview/design-philosophy|设计哲学]] 深入了解语言理念
- 查看 [[appendix/error-codes|错误码参考]] 排查问题

---

# 教程 12: 测试框架与 TDD

> 用 Helen 内置测试框架写测试、跑 TDD

---

## 为什么需要测试框架？

Helen 是 AI 原生语言——Agent 写的代码更需要自动化测试保障。内置测试框架让你：

- 用 Helen 语法写测试（不需要外部工具）
- 链式断言（`expect().toBe()`）
- 监听模式（`--watch`）实现 TDD 红-绿-重构循环
- JSON 输出便于 CI 集成

## 快速开始

### 1. 创建测试文件

```helen
// calculator_test.helen

fn add(a, b) { return a + b }
fn subtract(a, b) { return a - b }

fn test_add() {
    assert_equal(add(2, 3), 5)
    assert_equal(add(-1, 1), 0)
}

fn test_subtract() {
    assert_equal(subtract(10, 4), 6)
    assert_equal(subtract(0, 0), 0)
}

test_suite("Calculator")
test_case("adds numbers", test_add)
test_case("subtracts numbers", test_subtract)
test_end_suite()

run_tests()
```

### 2. 运行测试

```bash
$ helen test calculator_test.helen
============================================================
  HELEN TEST RESULTS
============================================================

  Calculator
    ✓ adds numbers (0.1ms)
    ✓ subtracts numbers (0.0ms)

------------------------------------------------------------
  2 passed, 0 failed, 0 skipped (2 total)
  Duration: 0.5ms
============================================================
  ✓ ALL TESTS PASSED
============================================================
```

## 断言函数

| 函数 | 说明 |
|------|------|
| `assert_true(condition)` | 断言条件为真 |
| `assert_equal(actual, expected)` | 断言相等 |
| `assert_not_equal(a, b)` | 断言不等 |
| `assert_throws(fn)` | 断言抛出异常 |

```helen
fn test_assertions() {
    assert_true(10 > 5)
    assert_equal("hello" + " world", "hello world")
    assert_not_equal(1, 2)
    
    try {
        assert_throws(fn() { throw RuntimeError("boom") })
    } catch AssertionError e {
        // 断言失败本身也是 AssertionError
    }
}
```

## Expect 链式 API

更可读的断言风格：

```helen
fn test_expect_chain() {
    // 基本断言
    expect(42).toBe(42)
    expect([1, 2, 3]).toContain(2)
    expect("hello world").toStartWith("hello")
    expect("hello world").toEndWith("world")
    expect([1, 2, 3]).toHaveLength(3)
    
    // 数值比较
    expect(10).toBeGreaterThan(5)
    expect(3).toBeLessThan(7)
    
    // 类型检查
    expect("hello").toBeType("str")
    expect(42).toBeType("int")
    
    // 否定
    expect(42).not_.toBe(0)
    expect([]).not_.toContain(1)
    
    // 深度相等
    expect({"a": 1, "b": 2}).toEqual({"b": 2, "a": 1})
    
    // 正则匹配
    expect("hello123").toMatch("hello\\d+")
    
    // 空值检查
    expect("").toBeEmpty()
    expect([]).toBeEmpty()
    expect("hello").toBeTruthy()
    expect(null).toBeFalsy()
}
```

## 测试套件与过滤

### 多个测试套件

```helen
test_suite("String Utils")
test_case("uppercase", test_upper)
test_case("lowercase", test_lower)
test_end_suite()

test_suite("Math Utils")
test_case("add", test_add)
test_case("multiply", test_multiply)
test_end_suite()

run_tests()
```

### CLI 过滤

```bash
# 只运行某个测试
helen test file.helen --only "adds numbers"

# 只运行某个 suite
helen test file.helen --suite "Calculator"

# 正则过滤
helen test file.helen --filter "add|subtract"
```

## 钩子函数

`before_each` 和 `after_each` 在每个测试前后运行：

```helen
fn setup() {
    // 重置全局状态、初始化数据
    print("Setting up...")
}

fn teardown() {
    // 清理资源
    print("Tearing down...")
}

test_suite("With Hooks")
before_each(setup)
after_each(teardown)
test_case("test1", test_something)
test_case("test2", test_another)
test_end_suite()
```

## 跳过测试

还没写好的测试可以暂时跳过：

```helen
test_suite("Feature")
test_case("completed feature", test_done)
test_case_skip("work in progress", test_wip)    // 跳过
test_end_suite()
```

## TDD 工作流

### 1. RED — 写失败的测试

```helen
// 我们想实现一个 FizzBuzz
fn test_fizzbuzz() {
    expect(fizzbuzz(3)).toBe("Fizz")
    expect(fizzbuzz(5)).toBe("Buzz")
    expect(fizzbuzz(15)).toBe("FizzBuzz")
    expect(fizzbuzz(7)).toBe("7")
}

test_suite("FizzBuzz")
test_case("returns correct string", test_fizzbuzz)
test_end_suite()

run_tests()
```

### 2. GREEN — 实现功能

```helen
fn fizzbuzz(n) {
    if n % 15 == 0 { return "FizzBuzz" }
    if n % 3 == 0 { return "Fizz" }
    if n % 5 == 0 { return "Buzz" }
    return str(n)
}
```

### 3. 监听模式 — 自动重跑

```bash
$ helen test fizzbuzz_test.helen --watch
Watching for changes... (Ctrl+C to stop)
```

保存文件后测试自动重跑，即时反馈。

## JSON 输出与 CI 集成

```bash
$ helen test file.helen --json
{
  "suites": [
    {
      "name": "Calculator",
      "tests": [
        {"name": "adds numbers", "passed": true, "duration_ms": 0.1},
        {"name": "subtracts numbers", "passed": true, "duration_ms": 0.0}
      ]
    }
  ],
  "summary": {"total": 2, "passed": 2, "failed": 0, "skipped": 0}
}
```

在 CI 中使用退出码判断成功/失败：

```yaml
# GitHub Actions 示例
- run: helen test tests/ --json
  # 非零退出码 = 测试失败
```

## 练习

1. 为一个字符串反转函数写测试套件，至少 3 个测试用例
2. 用 `expect` 链式 API 重写一个已有测试
3. 创建一个包含 `before_each` 的测试套件，验证钩子函数正确执行
4. 用 `--watch` 模式实现一个简单的 TDD 循环

---

> **相关文档**: [[toolchain/testing|测试框架 API 参考]] | [[tutorial/01-getting-started|入门指南]]

---

# 教程 13: 技能系统

> 让 Agent 带着专业知识工作

---

## 什么是技能？

技能（Skill）是模块化的知识单元，以 Markdown 文件形式存在。它们让 LLM 在需要时加载特定领域的知识，而不是把所有知识塞进 system prompt。

## Agent vs Skill：本质区别

> **Agent 是"谁来做"，Skill 是"怎么做"的知识。**

| 维度 | Agent（智能体） | Skill（技能） |
|------|----------------|--------------|
| **本质** | 运行时实体 | 静态文档 |
| **语言级别** | 一等公民（语法支持） | 外部概念（纯 Markdown） |
| **可调用** | ✅ `Agent()` 像函数调用 | ❌ 不可调用 |
| **有状态** | ✅ 维护对话/工具状态 | ❌ 无状态 |
| **执行逻辑** | ✅ `main { }` 块 | ❌ 无执行逻辑 |
| **用途** | **执行**任务 | **指导**如何执行 |

**Agent 是执行者**：有 model、temperature、tools，可被调用、组合，实际执行 LLM 调用和工具操作。像**员工**。

**Skill 是知识库**：纯 Markdown 文档，提供模式、最佳实践、API 用法，被 Agent 读取作为上下文。像**手册**。

**用 Agent** 当你需要实际执行操作、维护状态、被代码调用。  
**用 Skill** 当你需要提供知识、文档化工作流、让多个 Agent 共享知识。

**实际关系**：Agent 可以加载 Skill 作为知识源：

```helen
agent Developer {
    tools = ["load_skill"]
    main {
        let guide = load_skill("helen-testing")
        return llm act "Follow: " + guide
    }
}
```

## 技能目录结构

```
~/.helen/skills/
├── web-search/
│   ├── SKILL.md           # 主文件（必须）
│   ├── references/        # 参考资料
│   ├── templates/         # 模板文件
│   └── scripts/           # 辅助脚本
└── code-review/
    └── SKILL.md
```

## SKILL.md 格式

```markdown
---
name: web-search
description: Search the web for information
version: 1.0.0
author: Your Name
tags: [web, search, research]
---

# Web Search Skill

## When to Use
- User asks for current information
- Need to verify facts

## How to Use
1. Use web_search tool
2. Analyze results
3. Summarize findings
```

## 三层搜索架构

技能按优先级从高到低搜索：

| 优先级 | 目录 | 说明 |
|--------|------|------|
| 1（最高） | `<project>/.helen/skills/` | 项目级，团队共享 |
| 2 | `~/.helen/skills/` | 用户级，个人全局 |
| 3 | `<helen>/skills/` | 内置级，随语言分发（13 个） |
| 可选 | `~/.hermes/skills/` | Hermes 回退（如已安装） |

同名技能，高优先级覆盖低优先级。

## 两层披露机制

### 第一层：技能索引

所有技能的 name + description + **tags** 被扫描并注入 system prompt：

```
<available_skills>
Before replying, scan skills below. If a skill matches or is
even partially relevant to your task, you MUST load it with
load_skill and follow its instructions. Err on the side of loading.

  research:
    - web-search: Search the web for information (tags: web, search, research)
  dev:
    - code-review: Review code for quality and security (tags: review, security, quality)
</available_skills>
```

**v1.15 强化**：技能索引现在包含 **MUST load** 强制指令，要求 LLM 在技能相关时必须加载，而不是可选的。这确保 agent 在生成代码前主动学习相关技能，避免猜测 API 和语法。

**tags 字段**是提升技能命中率的关键。LLM 根据标签中的关键词匹配用户意图，比仅靠 description 文字匹配更准确。建议使用统一的命名规范（小写、英文关键词）。

### 第二层：按需加载

LLM 看到索引后，判断需要时调用 `load_skill` 工具获取完整内容。

## LLM 语句中的技能感知

`llm act` 自动注入技能索引到 system prompt：

```helen
agent Researcher(query) {
    description: "Research topics using web search"
    
    main {
        // LLM 在这里可以看到所有可用技能
        llm act "Research: " + query
    }
}
```

LLM 在执行时会看到所有可用技能，并能根据需要参考相关技能的知识。

## 技能管理最佳实践

### 命名规范

```
✅ web-search, code-review, data-analysis
❌ WebSearch, code_review, dataAnalysis
```

### 粒度控制

```
✅ 一个技能 = 一个明确的任务领域
❌ 一个技能 = 所有事情（太宽泛）
❌ 一个技能 = 一行指令（太细碎）
```

### 分层组织

```
项目级（.helen/skills/）  → 项目特定规范、API 约定
用户级（~/.helen/skills/） → 个人偏好、常用工作流
内置级（helen/skills/）    → 通用技能、语言相关
```

## 内置技能

Helen 自带多个内置技能：

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
| `helen-agent-patterns` | Agent 设计模式（v1.12：历史管理） |
| `helen-agent-collaboration` | 多 Agent 协作模式 |
| `helen-quality` | 代码质量评估 |
| `helen-syntax` | Helen 语法参考 |
| `helen-programming-methodology` | 编程方法论 |

## 练习

1. 在 `~/.helen/skills/` 下创建一个 `greeting` 技能
2. 为当前项目创建 `.helen/skills/` 目录，添加项目规范技能
3. 在 REPL 中用 `:ask` 测试技能是否被正确感知
4. 编写 Helen 程序，使用 `llm act` 调用会参考技能的 Agent

---

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

## 上下文管理可观测性 (v1.15+)

Helen v1.15 引入了完整的上下文管理增强，提供了丰富的可观测性。

### 上下文使用统计

```
:stats                 # 显示上下文使用统计
```

显示信息：
- Token 使用率和总数
- 当前模型
- 消息数量
- 工作记忆状态（活跃文件、最近决策、待办事项、错误历史）

### 工作记忆查看

```
:working_memory        # 显示当前工作记忆内容
:working_memory files  # 只显示活跃文件
:working_memory decisions  # 只显示最近决策
:working_memory todos  # 只显示待办事项
:working_memory errors # 只显示错误历史
```

### 压缩状态

```
:compression           # 显示当前压缩状态
```

显示信息：
- 当前压缩层（Layer 1-5）
- 使用率
- 缓存命中状态

### 程序化访问

```helen
main {
    // 获取上下文统计
    let stats = context_stats()
    print("Token usage: " + stats["usage_ratio"])
    print("Active files: " + stats["active_files"])
    
    // 获取工作记忆
    let wm = working_memory_snapshot()
    print("Recent decisions: " + wm["recent_decisions"])
    
    // 手动触发压缩
    compress_context("graduated")
    
    // 清除上下文
    clear_context()
}
```

### 上下文管理调试

```helen
// 辅助函数：修复代码
fn fix_code(code: str): str {
    // 实际的代码修复逻辑
    return code  // 简化示例
}

agent DebugHelper {
    context {
        compression "graduated"
        working-memory true
    }
    
    tools ["read_file", "write_file"]
    
    functions {
        fn fix_code(code: str): str {
            // 实际的代码修复逻辑
            return code  // 简化示例
        }
    }
    
    main {
        // 工作记忆自动跟踪文件操作
        let code = read_file("src/main.py")
        let fixed = fix_code(code)
        write_file("src/main.py", fixed)
        
        // 查看工作记忆
        let wm = working_memory_snapshot()
        debug("Working memory after file operations", wm)
        
        return llm act "Review the changes"
    }
}
```

---

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

---

# 教程 15: Python Bridge

> 让 Python 直接使用 Helen Agent

## 概述

Helen Python Bridge 允许 Python 开发者直接导入和使用 Helen Agent，就像使用普通的 Python 类一样。这是 Helen 与 Python 生态系统的深度集成方案。

## 快速开始

### 1. 创建 Helen Agent

创建 `translator.helen` 文件：

```helen
agent TranslatorAgent(text: str, target: str) {
    description "翻译文本到目标语言"
    prompt "Translate '{{text}}' to {{target}}"
    
    main {
        return llm act "Translate '{{text}}' to {{target}}"
    }
}
```

### 2. 在 Python 中使用

```python
from translator import TranslatorAgent

# 创建 agent 实例
agent = TranslatorAgent()

# 调用 agent
result = agent("Hello", "French")
print(result)  # "Bonjour"
```

就这么简单！Python 开发者无需学习 Helen 语法，可以像使用普通 Python 类一样使用 Helen Agent。

## 核心特性

### 自动导入

Python Bridge 使用 Import Hook 自动识别 `.helen` 文件：

```python
# 自动加载 translator.helen 文件
from translator import TranslatorAgent, SummarizerAgent
```

### 参数验证

```python
agent = TranslatorAgent()

# ✅ 正确调用
result = agent("Hello", target="French")

# ❌ 缺少必需参数
result = agent("Hello")  # TypeError: missing required argument

# ❌ 未知参数
result = agent("Hello", target="French", extra="value")  # TypeError
```

### 类型转换

自动在 Python 和 Helen 类型之间转换：

```python
# Python → Helen
agent(42, "text", [1, 2, 3], {"key": "value"})

# Helen → Python
result = agent(...)  # 自动转换为 Python 类型
```

支持的类型：
- 基本类型：`int`, `float`, `str`, `bool`
- 集合类型：`list`, `dict`
- 空值：`None`

### 异步调用

```python
import asyncio

async def main():
    agent = TranslatorAgent()
    result = await agent.async_call("Hello", "Spanish")
    print(result)

asyncio.run(main())
```

### 关键字参数

```python
agent = TranslatorAgent()

# 位置参数
result = agent("Hello", "French")

# 关键字参数
result = agent(text="Hello", target="French")

# 混合使用
result = agent("Hello", target="French")
```

## 高级用法

### 装饰器模式

使用 `@helen_agent` 装饰器简化调用：

```python
from helen.python_bridge import helen_agent

@helen_agent("translator.helen", "TranslatorAgent")
def translate(text: str, target: str) -> str:
    pass

result = translate("Hello", "French")
```

### 共享解释器

多个 agent 可以共享同一个解释器实例：

```python
from helen.interpreter import Interpreter
from helen.python_bridge import HelenAgentWrapper

# 创建共享解释器
interpreter = Interpreter()

# 多个 agent 共享
agent1 = HelenAgentWrapper("Agent1", "agents.helen", interpreter)
agent2 = HelenAgentWrapper("Agent2", "agents.helen", interpreter)
```

### 批量处理

```python
from agents import TranslatorAgent

agent = TranslatorAgent()
texts = ["Hello", "World", "AI"]

results = [agent(text, target="French") for text in texts]
print(results)  # ["Bonjour", "Monde", "IA"]
```

### 错误处理

```python
from agents import TranslatorAgent

agent = TranslatorAgent()

try:
    result = agent("Hello", target="French")
except TypeError as e:
    print(f"参数错误: {e}")
except Exception as e:
    print(f"执行错误: {e}")
```

## 使用场景

### AI Agent 开发

```python
from agents import ResearchAgent, AnalysisAgent

# 研究阶段
researcher = ResearchAgent()
findings = researcher("quantum computing", depth="deep")

# 分析阶段
analyzer = AnalysisAgent()
insights = analyzer(findings)
```

### 多 Agent 协作

```python
from workflow import PlannerAgent, ExecutorAgent, ReviewerAgent

planner = PlannerAgent()
plan = planner("Build a web app")

executor = ExecutorAgent()
result = executor(plan)

reviewer = ReviewerAgent()
feedback = reviewer(result)
```

### LLM 应用

```python
from llm_agents import ChatBot, Summarizer, Translator

chatbot = ChatBot()
response = chatbot("What is AI?")

summarizer = Summarizer()
summary = summarizer(long_text)

translator = Translator()
translated = translator(summary, target="Chinese")
```

## API 参考

### HelenAgentWrapper

```python
class HelenAgentWrapper:
    def __init__(self, agent_name: str, helen_file: str, interpreter=None):
        """
        初始化包装器
        
        Args:
            agent_name: Agent 名称
            helen_file: Helen 文件路径
            interpreter: 可选的解释器实例（用于共享）
        """
    
    def __call__(self, *args, **kwargs) -> Any:
        """调用 agent"""
    
    async def async_call(self, *args, **kwargs) -> Any:
        """异步调用 agent"""
```

### 装饰器

```python
@helen_agent(helen_file: str, agent_name: str = None)
def my_function(...):
    """将函数包装为 Helen agent 调用"""

@helen_module(helen_file: str)
class MyModule:
    """将类包装为 Helen agents 集合"""
```

### Import Hook

```python
from helen.python_bridge import install_import_hook

# 自动安装（默认）
install_import_hook()

# 手动卸载
from helen.python_bridge import uninstall_import_hook
uninstall_import_hook()
```

## 实现原理

1. **Import Hook**: 使用 Python 的 `sys.meta_path` 拦截模块导入
2. **动态类生成**: 解析 Helen 文件，为每个 agent 动态创建 Python 类
3. **类型转换**: 自动在 Python 和 Helen 类型之间转换
4. **参数验证**: 检查参数类型和必需参数
5. **异步支持**: 提供 `async_call` 方法用于异步调用

## 限制

- 需要 Python 3.10+（因为 Helen 使用 match 语句）
- 当前只支持 agent 调用，不支持 Helen 的其他特性
- 类型转换目前只支持基本类型（int, float, str, bool, list, dict）

## 未来计划

- 支持更多 Helen 特性（函数、类等）
- 改进类型转换（支持自定义类型）
- 添加类型提示生成
- 支持 Helen 模块系统

## 示例代码

完整示例请查看 `examples/python_bridge/` 目录：

- `translator.helen`: Helen agent 定义
- `example_usage.py`: 完整使用示例
- `test_simple.py`: 简单测试

## 总结

Helen Python Bridge 让 Helen 成为 Python 的"原生扩展"，Python 开发者可以像使用 `numpy`、`pandas` 一样使用 Helen Agent，这会让 Helen 在 Python 生态系统中获得最大的采用率。

---

# 教程 16: 质量评估（7 维框架）

> Helen 内置 7 维质量评估框架，自动化质量分析

---

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
| S | 9.0-10.0 | 生产就绪，exemplary |
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

---

> **相关文档**: [[toolchain/quality|质量评估工具参考]] | [[tutorial/12-testing|测试框架与 TDD]]

---

# 多模态支持 (v1.17)

Helen v1.17 引入了基于回调的多模态支持，采用**回调即适配器**的设计模式，使 Helen 能够处理图像、视频、音频等多种媒体类型，同时保持与各种 LLM provider 的兼容性。

## 设计原则

多模态支持的核心原则是：**协议差异由用户回调处理，Helen 核心不内置 provider 特定格式**。

这种设计带来以下优势：

- **协议无关**：Helen 核心不绑定任何特定 provider 的媒体格式
- **可扩展性**：新增模态或 provider 无需修改语言核心
- **灵活性**：用户可以根据需要自定义媒体处理逻辑
- **向后兼容**：纯文本程序无需任何修改

## 核心概念

### MediaPart 数据类型

`MediaPart` 是一等公民数据类型，表示媒体内容：

```helen
# 从文件创建
let img = media("file:///path/to/image.png")

# 从 URL 创建
let remote_img = media("https://example.com/image.jpg")

# 从 base64 创建
let b64_data = read_file_base64("image.png")
let inline_img = media_base64(b64_data, "image/png")

# 检查是否为 MediaPart
是媒体(img)  # 返回: 真

# 获取媒体类型
媒体类型(img)  # 返回: "image"
```

### MediaPart 字段

每个 `MediaPart` 对象包含以下字段：

- `source`: 来源类型（"file"、"url"、"base64"）
- `content`: 内容（文件路径、URL 或 base64 字符串）
- `mime`: MIME 类型（如 "image/png"）
- `media_type`: 媒体类型（"image"、"video"、"audio"）
- `metadata`: 额外元数据（字典）

## llm act 多模态语法

### 基本用法

在 `llm act` 中传递媒体：

```helen
agent 图像分析 {
    description "分析图像内容"
    
    main {
        let img = media("photo.jpg")
        let result = llm act "描述这张图片" media(img)
        print(result)
    }
}
```

### 多个媒体

可以传递多个媒体对象：

```helen
let img1 = media("image1.png")
let img2 = media("image2.png")
let result = llm act "比较这两张图片" media(img1, img2)
```

### on_media 回调（媒体适配器）

`on_media` 回调用于将 `MediaPart` 列表转换为特定 provider 所需的格式。Helen 内置了三个格式适配器 stdlib 函数，绝大多数场景无需手写 JSON：

```helen
agent Claude媒体处理 {
    main {
        let img = media("diagram.png")
        
        # 推荐：使用内置格式适配器（一行搞定）
        let result = llm act "解释这个图表" 
            media(img)
            on_media fn(parts, provider) { 转Claude格式(parts) }
    }
}
```

**内置格式适配器**：

| 函数 | 说明 |
|------|------|
| `to_openai_parts(parts)` / `转OpenAI格式(parts)` | OpenAI 兼容格式（默认，通常无需手动指定） |
| `to_claude_parts(parts)` / `转Claude格式(parts)` | Anthropic Claude Messages API 格式 |
| `to_gemini_parts(parts)` / `转Gemini格式(parts)` | Google Gemini inline_data 格式 |

**自定义适配器**：仅当使用非标准 provider 或需要特殊处理时才需手写：

```helen
on_media fn(parts, provider) {
    # 仅为非标准 provider 手写
    返回 parts.map(fn(part) {
        返回 {
            "type": "media",
            "mime_type": part.mime,
            "data": 媒体转base64(part),
            "encoding": "base64"
        }
    })
}
```

**参数说明**：
- `parts`: `MediaPart` 对象列表
- `provider`: 当前使用的 provider 名称（如 "openai"、"claude"）
- **返回值**: 转换后的内容部分列表（provider 特定格式）

**默认行为**：如果不指定 `on_media`，Helen 使用默认的 OpenAI 兼容适配器（内部调用 `to_openai_parts()`）。

### on_generate 回调（媒体生成）

`on_generate` 回调将媒体生成能力注册为工具，让 LLM 决定何时调用：

```helen
agent 图像生成器 {
    description "根据描述生成图像"
    
    main {
        let result = llm act "创建一张日落风景图"
            on_generate fn(params) {
                # params 包含: prompt, size, model 等
                let prompt = params["prompt"]
                
                # 调用图像生成 API
                let image_url = call_image_generation_api(prompt)
                
                # 返回生成的媒体
                返回 media("url://" + image_url)
            }
        
        print("生成的图像: " + result)
    }
}
```

**工作原理**：
1. `on_generate` 将生成能力注册为 LLM 可调用的工具
2. LLM 在工具循环中决定是否调用生成工具
3. 调用时执行回调函数，返回生成的 `MediaPart`
4. 生成的媒体自动添加到对话上下文中

**支持场景**：
- 文生图（text-to-image）
- 文生视频（text-to-video）
- 任何可通过 API 生成的媒体类型

### provider 子句

指定使用的 provider（影响默认适配器行为）：

```helen
let result = llm act "分析这张图片"
    media(img)
    provider("claude")
```

### 流式回调

多模态也支持流式输出回调：

```helen
let result = llm act "详细描述这张图片"
    media(img)
    on_chunk fn(chunk) {
        print(chunk, flush=false)
    }
    on_complete fn(full_text) {
        print("\n完成!")
    }
```

## 中文别名

所有多模态相关函数都支持中文别名：

| 英文 | 中文 |
|------|------|
| `media()` | `媒体()` |
| `media_base64()` | `媒体base64()` |
| `is_media()` | `是媒体()` |
| `media_type()` | `媒体类型()` |
| `on_media fn(...)` | `处理媒体 fn(...)` |
| `on_generate fn(...)` | `生成 fn(...)` |
| `to_openai_parts()` | `转OpenAI格式()` |
| `to_claude_parts()` | `转Claude格式()` |
| `to_gemini_parts()` | `转Gemini格式()` |
| `media_to_base64()` | `媒体转base64()` |
| `save_media()` | `保存媒体()` |
| `is_image()` | `是图片()` |
| `is_video()` | `是视频()` |
| `is_audio()` | `是音频()` |

## 内置 stdlib 函数参考

### 格式适配器

将 `MediaPart` 列表转换为特定 provider 的内容格式：

```helen
# OpenAI 兼容格式（默认，通常无需手动指定）
let parts = to_openai_parts(media_list)

# Anthropic Claude Messages API 格式
let parts = to_claude_parts(media_list)
# 注意：Claude 不支持视频和音频输入，会抛出 ValueError

# Google Gemini inline_data 格式
let parts = to_gemini_parts(media_list)
```

### 媒体工具

```helen
# 将任意 MediaPart 转为纯 base64 字符串（无论 source 是 file/url/base64）
let b64 = media_to_base64(img)

# 保存 MediaPart 到文件（path 可选，默认保存到 ~/.helen/generated_media/）
let path = save_media(img, "/tmp/output.png")
let path2 = save_media(img)  # 自动命名
```

### 类型谓词

```helen
如果 是图片(part) { 打印("这是图片") }
如果 是视频(part) { 打印("这是视频") }
如果 是音频(part) { 打印("这是音频") }

# 非 MediaPart 安全：返回假，不抛异常
是图片("不是媒体")  # 返回: 假
```

## 完整示例

### 图像分析 Agent

```helen
agent 图像分析助手 {
    description "专业的图像分析助手，能够理解和描述图像内容"
    model "qwen-vl-max"
    
    main {
        # 从用户获取图像路径
        let image_path = input("请输入图像路径: ")
        
        # 创建 MediaPart
        let img = media(image_path)
        
        # 分析图像
        let analysis = llm act "请详细描述这张图片的内容、风格和可能的用途"
            media(img)
        
        print("\n分析结果:\n" + analysis)
    }
}
```

### 多图像比较 Agent

```helen
agent 图像比较器 {
    description "比较多个图像的差异"
    
    main {
        let img1 = media("before.png")
        let img2 = media("after.png")
        
        let comparison = llm act "比较这两张图片，指出主要的变化和差异"
            media(img1, img2)
        
        print(comparison)
    }
}
```

### 图像生成 Agent

```helen
agent 创意图像生成器 {
    description "根据文字描述生成图像"
    
    main {
        let description = input("描述你想生成的图像: ")
        
        let result = llm act description
            on_generate fn(params) {
                # 这里应该调用实际的图像生成 API
                # 示例使用占位符
                let prompt = params["prompt"]
                let api_response = call_dalle_api(prompt, size="1024x1024")
                
                # 返回生成的图像
                返回 media(api_response["url"])
            }
        
        print("生成的图像: " + result)
    }
}
```

### 自定义 Provider 适配

使用内置格式适配器（推荐）：

```helen
agent Claude分析 {
    main {
        let img = media("chart.png")
        
        # 使用内置 Claude 适配器 — 一行搞定
        let result = llm act "分析这个图表"
            media(img)
            on_media fn(parts, provider) { 转Claude格式(parts) }
        
        print(result)
    }
}
```

为非标准 provider 手写适配器：

```helen
agent 自定义媒体处理 {
    main {
        let img = media("chart.png")
        
        let result = llm act "分析这个图表"
            media(img)
            provider("custom_provider")
            on_media fn(parts, provider) {
                # 使用媒体转base64辅助，手写 provider 特定格式
                返回 parts.map(fn(part) {
                    返回 {
                        "type": "media",
                        "mime_type": part.mime,
                        "data": 媒体转base64(part),
                        "encoding": "base64"
                    }
                })
            }
    }
}
```

## TranscriptStore 集成

多模态内容完全集成到 TranscriptStore SSOT：

- **自动持久化**：所有多模态对话自动保存到 `~/.helen/sessions/`
- **大媒体外部存储**：≥1MB 的 base64 媒体自动提取到外部文件（Phase 3）
- **会话恢复**：重启 Helen 后可以完整恢复包含媒体的对话
- **压缩安全**：上下文压缩正确处理多模态内容

配置外部存储阈值（`~/.helen/config.yaml`）：

```yaml
multimodal:
  max_media_size_mb: 20              # 单个媒体最大 20MB
  max_media_per_request: 10          # 每次最多 10 个媒体
  media_external_threshold_mb: 1.0   # ≥1MB 提取到外部文件
  media_cache_dir: "~/.helen/media_cache"
  video_frame_interval: 1.0          # 视频抽帧间隔（秒）
```

## 最佳实践

### 1. 使用内置格式适配器

对于主流 provider，直接使用内置适配器，无需手写 JSON：

```helen
# OpenAI 兼容 provider（默认，无需 on_media）
let result = llm act "分析图片" media(img)

# Claude — 一行适配器
let result = llm act "分析图片"
    media(img)
    on_media fn(parts, provider) { 转Claude格式(parts) }

# Gemini
let result = llm act "分析图片"
    media(img)
    on_media fn(parts, provider) { 转Gemini格式(parts) }

# 仅在需要非标准 provider 时才手写 on_media
```

### 1.5 利用媒体工具函数

`media_to_base64()` 和 `save_media()` 在 `on_generate` 回调中特别有用：

```helen
on_generate fn(params) {
    let resp = http_post("https://api.example.com/generate", {...})
    let img = media_base64(resp.image_data, "image/png")
    
    # 保存到指定路径
    保存媒体(img, params["output_path"])
    
    # 或获取 base64 做进一步处理
    let b64 = 媒体转base64(img)
    
    返回 img
}
```

### 1.6 使用类型谓词过滤

处理混合媒体列表时，类型谓词可以精确过滤：

```helen
let parts = [img1, video1, audio1, img2]
let images = parts.filter(是图片)    # 只保留图片
let videos = parts.filter(是视频)    # 只保留视频
```

### 2. 合理管理大媒体

大媒体文件会自动外部存储，但可以手动控制：

```helen
# 小图像（<1MB）：内联存储
let small_img = media("icon.png")

# 大图像（≥1MB）：自动外部存储
let large_img = media("high_res_photo.png")
```

### 3. 错误处理

处理可能的媒体加载错误：

```helen
尝试 {
    let img = media("可能不存在的文件.png")
    let result = llm act "分析" media(img)
} 捕获 err {
    print("媒体加载失败: " + err.消息)
}
```

### 4. 批量处理

处理多个媒体时，注意 provider 限制：

```helen
# 默认每次最多 10 个媒体
let images = [media("img1.png"), media("img2.png"), ...]
设 result = llm act "分析这些图片" media(images...)
```

## 限制和注意事项

1. **Provider 支持**：并非所有 LLM provider 都支持多模态，需要确认 provider 能力
2. **文件大小**：默认单个媒体最大 20MB，可在配置中调整
3. **网络媒体**：URL 媒体需要网络访问，可能需要处理超时
4. **格式兼容**：不同 provider 支持的媒体格式不同，需要适当转换

## 相关资源

- [TranscriptStore 用户指南](../docs/transcript_store_user_guide.md)
- [helen-syntax skill](../skills/software-development/helen-syntax/SKILL.md)
- [helen-stdlib skill](../skills/software-development/helen-stdlib/SKILL.md)
- [多模态提案](../reports/multimodal-proposal.md)

---


---

<!-- Auto-generated from wiki/tutorial/*.md | 2026-07-09 23:37 | Helen v1.15 -->
