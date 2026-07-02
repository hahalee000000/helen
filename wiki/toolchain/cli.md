# 命令行工具 (CLI)

> 模块 M11 | `helen/cli/__main__.py` + `repl.py` + `formatter.py` + `docgen.py`

---

## 子命令

```bash
$ helen <file> [args...]  # 编译 + 执行（args 传入程序作为 argv）
$ helen check <file>       # 仅验证 (Lex + Parse + Analyze)
$ helen repl               # 交互式解释器
$ helen doc <files...>     # 生成文档
$ helen init               # 初始化配置目录
$ helen lsp                # 启动 Language Server (LSP)
$ helen test <file>        # 运行测试
$ helen quality <file>     # 7维质量评估
```

---

## helen lsp

```bash
$ helen lsp
```

启动 Helen Language Server，通过 stdin/stdout 进行 JSON-RPC 2.0 通信。

### 用途

- **VS Code 集成**：安装 [Helen VS Code 扩展](vscode.md) 后自动启动
- **手动测试**：`echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | helen lsp`
- **自定义 IDE**：为其他编辑器提供 LSP 支持

### 功能

| 功能 | 说明 |
|------|------|
| 实时诊断 | 语法和语义错误即时提示 |
| 代码补全 | 关键字、类型、stdlib 函数 |
| 跳转定义 | 跳转到 agent/fn/let 声明 |

详见 [LSP 文档](lsp.md) 和 [VS Code 扩展文档](vscode.md)。

---

## helen init

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

初始化 Helen 独立配置目录 `~/.helen/`：

| 创建内容 | 说明 |
|---------|------|
| `~/.helen/` | Helen 主目录 |
| `~/.helen/skills/` | Skill 目录 |
| `~/.helen/config.yaml` | LLM API 配置模板 |

如果 `config.yaml` 已存在，不会覆盖，仅提示编辑。

### 配置文件格式

YAML 格式 (`~/.helen/config.yaml`)：

```yaml
llm:
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  api_key: "your-api-key-here"
  model: "qwen3.7-plus"
  temperature: 0.7
  timeout: 60
```

.env 格式 (`~/.helen/.env`)：

```bash
HELEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
HELEN_API_KEY=your-api-key-here
HELEN_MODEL=qwen3.7-plus
```

### 配置加载优先级

| 优先级 | 文件 | 说明 |
|--------|------|------|
| 1（最低） | `~/.hermes/.env` | Hermes 兼容回退 |
| 2 | `~/.helen/.env` | Helen .env |
| 3 | `~/.helen/config.yml` | Helen YAML |
| 4（最高） | `~/.helen/config.yaml` | Helen YAML |

### Skill 目录优先级

| 优先级 | 目录 | 说明 |
|--------|------|------|
| 1（最高） | `~/.helen/skills/` | Helen 原生 |
| 2 | `~/.hermes/skills/` | Hermes 回退 |
| 3 | `~/.hermes/hermes-agent/skills/` | Hermes agent |

---

## helen <file>

```
$ helen main.helen
$ helen main.helen --verbose --output=json --port=8080 input.txt
```

执行完整编译链：
1. Lexer → 词法分析
2. Parser → 语法分析
3. SemanticAnalyzer → 语义分析
4. Interpreter → 解释执行

退出码：`0`=成功 `1`=词法错误 `2`=语法错误 `3`=语义/运行时错误

### 程序参数（argv）

文件名之后的所有参数会传递给 Helen 程序，在程序中可通过三种方式访问：

| 访问方式 | 类型 | 说明 |
|---------|------|------|
| `argv` | `const list<str>` | 预定义常量，包含所有命令行参数 |
| `get_cli_args()` | `list<str>` | 标准库函数，返回与 argv 相同的列表 |
| `parse_cli_args(spec?)` | `map` | 结构化解析（支持 flag、key=value、位置参数） |

**示例**：

```bash
$ helen my_tool.helen --verbose --output=json --port=8080 input.txt
```

```helen
// my_tool.helen

// 1. 直接访问 argv
print(argv)  // ["--verbose", "--output=json", "--port=8080", "input.txt"]

// 2. 自动解析
let parsed = parse_cli_args()
// {verbose: true, output: "json", port: "8080", _positional: ["input.txt"]}

// 3. 结构化解析（带类型和默认值）
let spec = {
    "verbose": {"type": "flag", "default": false},
    "output": {"type": "string", "default": "text"},
    "port": {"type": "int", "default": 3000}
}
let config = parse_cli_args(spec)
// {verbose: true, output: "json", port: 8080, _positional: ["input.txt"]}
```

> **注意**：`argv` 是 `const`，不可重新赋值。它在 agent 作用域中自动可见（通过 const 只读共享机制）。

> **注意**：嵌套 map 字面量中的 `}}` 会被词法分析器识别为模板引用关闭符（`TEMPLATE_CLOSE`），需要在两个 `}` 之间加空格：`} }`。

---

## helen check

```
$ helen check main.helen
✓ main.helen: OK
```

执行前端验证（不执行）：
1. Lexer → 词法分析
2. Parser → 语法分析
3. SemanticAnalyzer → 语义分析

`check` 也支持传入程序参数（用于验证使用了 `argv` 的程序）：

```
$ helen check main.helen --verbose --output=json
✓ main.helen: OK
```

用于 CI/CD 中的代码质量检查。

---

## helen repl

```
$ helen repl
Helen REPL v1.2
Type 'exit' or Ctrl+D to quit, ':help' for commands
In multi-line mode (...), press Enter on empty line or Ctrl+C to cancel

>>> let x = 42
>>> x
42
>>>
```

### 交互特性

| 功能 | 说明 |
|------|------|
| **光标移动** | 支持方向键 ← → 移动光标，↑ ↓ 浏览历史 |
| **命令历史** | 自动保存输入历史，可用 ↑ ↓ 翻阅 |
| **Tab 补全** | 按 Tab 键触发补全（如关键字） |

### REPL 命令

```
:help               显示帮助信息
:reset              清除所有定义（函数、agent）
:list               列出所有已定义的函数和 agent
:undefine <name>    删除指定的函数或 agent 定义
:ask <question>     向 AI 助手提问（使用 LLM 回答 Helen 语言相关问题）
:trace on|off       开启/关闭执行追踪
:trace show [n]     显示最近 n 条追踪记录（默认 50）
:last_error [-v]    显示上次错误的结构化上下文（-v 显示执行追踪）
:llm_log [n] [-v]   显示最近 n 次 LLM 调用审计日志（-v 显示详细信息）
exit                退出 REPL
```

> **注意**：REPL 中调用栈追踪和执行追踪默认开启，无需手动 `:trace on`。

#### :ask — AI 助手

`:ask` 命令启动一个内置的 Helen 语言专家 Agent，可以回答关于 Helen 语法、标准库、用法等问题：

```
>>> :ask 标准库有哪些字符串函数？
🤔 Thinking...

Helen 标准库提供 36 个字符串函数，包括：
- upper/lower/strip — 大小写和空白处理
- split/join — 分割和连接
- replace/find — 替换和查找
- regex_match/regex_replace — 正则表达式
...
```

`:ask` 使用 `HelenAssistant` agent（定义在 `stdlib/_helen_assistant.helen`），具备：
- 完整的 Helen 语言知识（语法、类型系统、标准库）
- 可访问 `read_file`、`write_file`、`web_search` 等工具
- 对话历史上下文（同一 REPL 会话内保持）

### 多行输入

当括号未闭合时，REPL 进入多行模式（`...` 提示符）：

```
>>> agent Trans(text) {
...   main {
...     return llm act "translate " + text
...   }
... }
```

**退出多行模式的方法：**

| 方式 | 说明 |
|------|------|
| **空行** | 在 `...` 提示符下直接按 Enter（输入空行） |
| **Ctrl+C** | 取消当前多行输入，返回 `>>>` 提示符 |
| **Ctrl+D** | 退出整个 REPL |

### 多行输入检测

REPL 使用轻量状态机判断是否需要继续输入：

```python
def _needs_continuation(buffer: str) -> bool:
    """检测括号/引号是否未闭合。"""
    brace_count = paren_count = bracket_count = 0
    in_string = False
    escape_next = False

    for ch in buffer:
        if escape_next:
            escape_next = False
            continue
        if ch == '\\' and in_string:
            escape_next = True
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{': brace_count += 1
        elif ch == '}': brace_count -= 1
        elif ch == '(': paren_count += 1
        elif ch == ')': paren_count -= 1
        elif ch == '[': bracket_count += 1
        elif ch == ']': bracket_count -= 1

    return brace_count > 0 or paren_count > 0 or bracket_count > 0
```

当括号未闭合时，显示 `...` 提示符等待更多输入。

### 错误格式化

REPL 使用 `format_error()` 输出结构化错误：

```
Error: [E0311] at <repl>:2:5
  2 | let x = y
    |         ^
Undefined variable 'y'
```

---

## helen doc

```
$ helen doc main.helen
# Helen Program Documentation

## Agents

### Translator
- **Description**: Translate text between languages
- **Model**: gpt-4
- **Parameters**: text (str)

## Functions
...

## Built-in Functions
...
```

支持 `--format markdown|json` 和 `-o output_file`。

---

## 错误格式化器 (formatter.py)

遵循 HLD 3.11.2 格式：

```python
def format_error(error: HelenError) -> str:
    """
    Error: [E0301] at main.helen:5:10
      5 | let x = "hello
        |           ^^^^^
    Unterminated string

    Code: E0301 — UNTERMINATED_STRING
    """
```

输出包含：
1. 错误标题：`Error: [E{code}] at {file}:{line}:{col}`
2. 源码行
3. 定位符 `^^^^`
4. 错误消息
5. 错误码说明
