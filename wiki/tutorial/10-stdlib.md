# 教程 10: 标准库参考

> 285 个内置函数，覆盖 AI 应用开发的所有核心需求

## 概览

Helen 标准库提供 285 个内置函数，分为 17 大类别：

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

### 恢复上下文 (v1.21)

接续旧的 transcript session 到当前 active context——LLM 在下一次 `llm act` 调用时能看到恢复的所有消息。

```helen
// 1. 列出所有旧会话
let sessions = list_sessions()
for s in sessions {
    print("{s.session_id}: {s.message_count} 条消息, scope={s.scope}")
}

// 2. 恢复指定会话到当前 active context
let r = restore_context("session_1783492628_d9d9c0aa")
if r["status"] == "ok" {
    print("恢复了 " + str(r["restored_messages"]) + " 条消息")
    print("跳过 " + str(r["boundary_markers"]) + " 个压缩边界")
} else {
    print("恢复失败: " + r["error"])
}

// 中文别名
恢复上下文("session_1783492628_d9d9c0aa")
```

**与 `resume_session` 的区别**：

- `restore_context(session_id)`：恢复 **active context**（LLM 能看到），适合接续旧会话继续工作
- `resume_session(session_id)`：替换 **transcript store** 引用（LLM 看不到），适合查看旧 transcript 流

**注意事项**：

- `restore_context` 只恢复 messages（完整字段：`role`、`content`、`tool_calls`、`tool_call_id`、`uuid`、`compressed`、`pinned`）
- **不**恢复 working_memory 和 context config（transcript 不持久化这些）
- 需要恢复 working_memory 时，用 `working_memory_set()` 手动设置

**跨会话保存/恢复完整上下文（含 working_memory）**：

```helen
// 会话结束前：导出完整快照到文件
let snapshot = export_context()
write_file("context_snapshot.json", to_json(snapshot.context))

// 新会话启动时：读入并导入
let saved = parse_json(read_file("context_snapshot.json"))
import_context(saved)
```

## Transcript 函数 (6) (v1.16)

会话记录管理函数，用于访问和操作 Helen 的对话历史（v1.16+）。提供持久化、会话恢复和压缩审计功能。

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
- `layer`：压缩策略（"graduated"、"traditional" 等）
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
  enabled: true              # 启用会话记录（默认 true）
  backend: "sqlite"          # 后端类型："jsonl" 或 "sqlite"
  session_dir: "~/.helen/sessions"
```

**后端选择**：
- `jsonl`：简单、人类可读、崩溃安全（默认）
- `sqlite`：高性能、索引优化（适合大型会话）

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
