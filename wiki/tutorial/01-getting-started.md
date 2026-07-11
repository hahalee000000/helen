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
  enabled: true              # 启用会话记录（默认 true）
  backend: "jsonl"           # 后端类型："jsonl" 或 "sqlite"
  session_dir: "~/.helen/sessions"  # 会话存储目录
```

**默认行为**：
- 会话记录默认启用，所有对话自动保存到 `~/.helen/sessions/`
- 使用 JSONL 后端（人类可读，崩溃安全）

**自定义配置**：
- 设置 `enabled: false` 禁用会话记录
- 设置 `backend: "sqlite"` 使用 SQLite 后端（适合大型会话）
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
定义 姓名 = "张三"
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
