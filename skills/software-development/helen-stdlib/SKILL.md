---
name: helen-stdlib
description: "Helen 标准库使用指南 — 200 个内置函数的分类参考与示例"
version: 1.16.0
author: Helen Team
license: MIT
metadata:
  hermes:
    tags: [helen, stdlib, builtins, reference]
---

# Helen 标准库参考

Helen 标准库提供 **203 个内置函数**，覆盖 AI 应用开发的所有核心需求。

## 分类概览

| 类别 | 数量 | 代表函数 |
|------|------|----------|
| **Core** | 11 | `print`, `len`, `str`, `int`, `float`, `abs`, `min`, `max`, `range`, `type`, `isinstance` |
| **String** | 37 | `upper`, `lower`, `strip`, `split`, `join`, `replace`, `find`, `reverse`, `repeat`, `regex_match`, `regex_replace`, `format_float` |
| **Data** | 25 | `json_parse`, `json_stringify`, `yaml_parse`, `toml_parse`, `csv_parse`, `xml_parse`, `html_escape`, `url_encode`, `base64_encode` |
| **Collection** | 22 | `sort`, `reverse`, `unique`, `flatten`, `zip`, `map`, `filter`, `reduce`, `group_by`, `chunk`, `intersection` |
| **Network** | 9 | `http_get`, `http_post`, `http_put`, `http_delete`, `http_download`, `url_parse` |
| **Time** | 13 | `now`, `timestamp`, `date_format`, `date_parse`, `sleep`, `stopwatch_start`, `stopwatch_elapsed` |
| **Math** | 15 | `round`, `sqrt`, `floor`, `ceil`, `pow`, `log`, `sin`, `cos`, `random_int`, `random_float`, `mean`, `median`, `stddev` |
| **File** | 18 | `read_file`, `write_file`, `append_file`, `file_exists`, `list_dir`, `mkdir`, `copy_file`, `delete_file`, `file_size`, `glob_files`, `grep_files` |
| **System** | 18 | `env_get`, `env_set`, `get_cli_args`, `parse_cli_args`, `shell_exec`, `process_id`, `platform`, `hostname`, `log_info`, `log_error` |
| **Crypto** | 11 | `hash_md5`, `hash_sha256`, `hash_sha512`, `hmac_sha256`, `uuid_generate`, `random_bytes` |
| **IO** | 5 | `read_line`, `prompt`, `format_table`, `progress_bar`, `terminal_width` |
| **Observability** | 4 | `debug`, `trace_on`, `trace_off`, `get_trace` |
| **Context** | 2 | `clear_context`, `compress_context` |
| **Transcript** | 6 | `get_session_id`, `list_sessions`, `replay_transcript`, `export_transcript`, `get_compression_audit`, `resume_session` |
| **Media** | 4 | `media`, `media_base64`, `is_media`, `media_type` (v1.17) |
| **Test** | 14 | `test_suite`, `test_case`, `test_end_suite`, `assert_true`, `assert_equal`, `expect`, `run_tests`, `before_each`, `after_each` |
| **Quality** | 4 | `analyze_code`, `check_security`, `quality_score`, `quality_report` |

## 多语言 stdlib (v1.10)

Helen 的 stdlib 支持多语言函数名。每个 stdlib 函数都有英文 canonical 名和本地化别名，启动时全量加载。

### 中文 stdlib 别名

Helen 内置 230+ 个中文别名，覆盖全部 stdlib 分类。常用示例：

| 英文 | 中文 | 类别 |
|------|------|------|
| `len` | `长度` | Core |
| `print` | `打印` | Core |
| `sort` | `排序` | Collection |
| `filter` | `过滤` | Collection |
| `map` | `映射` | Collection |
| `json_parse` | `json解析` | Data |
| `json_stringify` | `json序列化` | Data |
| `http_get` | `http获取` | Network |
| `regex_match` | `正则匹配` | String |
| `regex_replace` | `正则替换` | String |
| `format_float` | `格式化浮点` | String |
| `date_format` | `日期格式化` | Time |
| `read_file` | `读文件` | File |
| `write_file` | `写文件` | File |
| `shell_exec` | `执行命令` | System |

完整列表见 `helen/stdlib/locales/zh.py`。

### 使用示例

```helen
// 直接用中文 stdlib 函数名（不需要任何 import 或 alias）
函数 数据处理() {
    定义 原始数据 = [3, 1, 4, 1, 5, 9, 2, 6]
    定义 排序后 = 排序(原始数据)
    定义 去重后 = 去重(排序后)
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

如果需要给 stdlib 函数起额外的别名，使用 `alias`/`别名` 语句：

```helen
alias len as 我的长度
别名 print as 输出
```

### 设计原则

- **一套机制**：stdlib 别名和用户 `alias` 使用相同的 Environment binding
- **全量加载**：所有 locale 的别名表启动时全部注册，不按 locale 过滤
- **locale 只影响展示**：`~/.helen/config.yaml` 中的 `locale: zh` 只影响 docs/LSP/错误消息的语言
- **扩展新语言**：添加新语言只需创建 `helen/stdlib/locales/<code>.py`

## 常用函数示例

### Core（核心）

```helen
# 类型转换
let num = int("42")           # 字符串 → 整数
let text = str(3.14)          # 浮点数 → 字符串
let flt = float("2.5")        # 字符串 → 浮点数

# 长度与范围
let length = len([1, 2, 3])   # 3
let items = range(0, 10, 2)   # [0, 2, 4, 6, 8]

# 数学基础
let maximum = max(1, 2, 3)    # 3
let minimum = min(1, 2, 3)    # 1
let absolute = abs(-42)       # 42

# 类型检查
if isinstance(value, str) {
    print("是字符串")
}
```

### String（字符串）

```helen
# 大小写转换
let upper = upper("hello")    # "HELLO"
let lower = lower("WORLD")    # "world"

# 分割与连接
let parts = split("a,b,c", ",")  # ["a", "b", "c"]
let joined = join(["a", "b"], "-")  # "a-b"

# 查找与替换
let found = find("hello world", "world")  # 6
let replaced = replace("foo bar", "foo", "baz")  # "baz bar"

# 正则表达式
if regex_match("hello123", r"\d+") {
    print("包含数字")
}
let cleaned = regex_replace("a1b2c3", r"\d", "")  # "abc"

# 空白处理
let trimmed = strip("  hello  ")  # "hello"
let padded = pad_start("42", 5, "0")  # "00042"

# 浮点数格式化
let formatted1 = format_float(8.5, 1)      # "8.5"
let formatted2 = format_float(7.857, 2)    # "7.86" (四舍五入)
let formatted3 = format_float(3.14159, 3)  # "3.142"
let formatted4 = format_float(100, 0)      # "100"

# 中文别名
let formatted = 格式化浮点(8.5, 1)  # "8.5"
```

### Data（数据格式）

```helen
# JSON
let data = json_parse('{"name": "Helen", "version": 1}')
let json = json_stringify(data, indent=2)

# YAML
let config = yaml_parse("key: value\nlist:\n  - item1\n  - item2")

# CSV
let rows = csv_parse("name,age\nAlice,30\nBob,25")
# [["name", "age"], ["Alice", "30"], ["Bob", "25"]]

# URL 编码
let encoded = url_encode("hello world&foo=bar")
let decoded = url_decode(encoded)

# Base64
let encoded = base64_encode("secret data")
let decoded = base64_decode(encoded)
```

### Media（多模态）(v1.17)

```helen
# 创建 MediaPart - 从文件
let img = media("file:///path/to/image.png")

# 创建 MediaPart - 从 URL
let remote = media("https://example.com/image.jpg")

# 创建 MediaPart - 从 base64
let b64_data = base64_encode(read_file_bytes("image.png"))
let inline = media_base64(b64_data, "image/png")

# 检查是否为 MediaPart
如果 是媒体(img) {
    打印("这是一个媒体对象")
}

# 获取媒体类型
let type = 媒体类型(img)  # "image"

# 在 llm act 中使用
let result = llm act "描述这张图片" media(img)
let result = llm act "比较这些图片" media(img1, img2)

# on_media 回调（自定义媒体适配）
let result = llm act "分析图片"
    media(img)
    on_media fn(parts, provider) {
        返回 parts.map(fn(part) {
            返回 {"type": "image_url", "image_url": {"url": part.content}}
        })
    }

# on_generate 回调（媒体生成）
let result = llm act "生成一张图"
    on_generate fn(params) {
        let url = call_generation_api(params["prompt"])
        返回 media("url://" + url)
    }
```

**MediaPart 字段**：
- `source`: 来源类型（"file"、"url"、"base64"）
- `content`: 内容（文件路径、URL 或 base64 字符串）
- `mime`: MIME 类型（如 "image/png"）
- `media_type`: 媒体类型（"image"、"video"、"audio"）
- `metadata`: 额外元数据（字典）

**中文别名**：`media()` → `媒体()`, `media_base64()` → `媒体base64()`, `is_media()` → `是媒体()`, `media_type()` → `媒体类型()`

### Collection（集合操作）

```helen
# 排序与去重
let sorted = sort([3, 1, 4, 1, 5])  # [1, 1, 3, 4, 5]
let unique_items = unique([1, 2, 2, 3])  # [1, 2, 3]

# 映射与过滤
let doubled = map([1, 2, 3], x => x * 2)  # [2, 4, 6]
let evens = filter([1, 2, 3, 4], x => x % 2 == 0)  # [2, 4]

# 归约
let sum = reduce([1, 2, 3, 4], (acc, x) => acc + x, 0)  # 10

# 分组
let grouped = group_by(users, u => u["role"])
# {"admin": [...], "user": [...]}

# 分块
let chunks = chunk([1, 2, 3, 4, 5], 2)
# [[1, 2], [3, 4], [5]]

# 集合运算
let common = intersection([1, 2, 3], [2, 3, 4])  # [2, 3]
```

### Network（网络请求）

```helen
# HTTP GET
let response = http_get("https://api.example.com/data")
let data = json_parse(response["body"])

# HTTP POST
let result = http_post(
    "https://api.example.com/submit",
    headers={"Content-Type": "application/json"},
    body=json_stringify({"name": "Helen"})
)

# 下载文件
http_download("https://example.com/file.pdf", "/tmp/file.pdf")
```

### Time（时间日期）

```helen
# 当前时间
let now_ts = now()                    # Unix 时间戳（秒）
let now_ms = timestamp()              # Unix 时间戳（毫秒）

# 格式化
let formatted = date_format(now(), "%Y-%m-%d %H:%M:%S")
# "2026-06-19 17:30:00"

# 解析
let parsed = date_parse("2026-06-19", "%Y-%m-%d")

# 计时
let sw = stopwatch_start()
# ... 执行操作 ...
let elapsed = stopwatch_elapsed(sw)   # 秒（浮点数）

# 休眠
sleep(1.5)  # 休眠 1.5 秒
```

### Math（数学运算）

```helen
# 基础数学
let rounded = round(3.14159, 2)   # 3.14
let squared = pow(2, 10)          # 1024
let root = sqrt(16)               # 4.0

# 统计
let avg = mean([1, 2, 3, 4, 5])   # 3.0
let mid = median([1, 2, 3, 4, 5]) # 3
let std = stddev([1, 2, 3, 4, 5]) # 1.414...

# 随机数
let rand_int = random_int(1, 100)      # 1-100 的随机整数
let rand_float = random_float(0, 1)    # 0-1 的随机浮点数
```

### File（文件操作）

```helen
# 读写文件
let content = read_file("/path/to/file.txt")
write_file("/path/to/output.txt", "Hello, World!")
append_file("/path/to/log.txt", "New log entry\n")

# 文件信息
if file_exists("/path/to/file.txt") {
    let size = file_size("/path/to/file.txt")
    print("文件大小: " + str(size) + " bytes")
}

# 目录操作
let files = list_dir("/path/to/dir")
mkdir("/path/to/new/dir")
copy_file("/src/file.txt", "/dst/file.txt")
delete_file("/path/to/file.txt")

# 文件搜索（v1.15 新增）
# 递归查找所有 Python 文件
let py_files = glob_files("src", "*.py")
# 返回: ["main.py", "utils/helper.py", "tests/test_main.py"]

# 使用 ** 显式递归
let md_files = glob_files("docs", "**/*.md")

# 搜索文件内容（字面量）
let matches = grep_files("src/", "TODO")
# 返回: [{"file": "main.py", "line": 42, "text": "    # TODO: fix this"}]

# 搜索文件内容（正则）
let functions = grep_files("src/", "def \\w+\\(", regex=true)

# 大小写不敏感搜索
let errors = grep_files("logs/", "error", case_sensitive=false)
```

### System（系统操作）

```helen
# 环境变量
let home = env_get("HOME")
env_set("MY_VAR", "value")
let all_env = env_list()  # 敏感值自动掩码

# CLI 参数（预定义常量 argv + 解析函数）
# 命令行: helen tool.helen --verbose --output=json input.txt
print(argv)  # ["--verbose", "--output=json", "input.txt"]

let parsed = parse_cli_args()           # 自动解析
# {verbose: true, output: "json", _positional: ["input.txt"]}

let spec = {
    "verbose": {"type": "flag", "default": false},
    "output": {"type": "string", "default": "text"}
}
let config = parse_cli_args(spec)       # 结构化解析（带类型+默认值）

# Shell 命令（默认 shell=True，支持完整 shell 语法）
# 使用 /bin/bash 执行，支持 brace expansion 等 bash 特性
# 所有 shell 语法都支持：&&、||、|、>、<、;、$()、{} 等
let result = shell_exec("ls -la")
let result = shell_exec("mkdir -p ~/project/{src,tests,contracts}")  # 创建三个目录
let result = shell_exec("cat file.txt | grep pattern | wc -l")
let result = shell_exec("echo 'hello' > output.txt")
print(result["output"])

# 安全模式：shell=False 用于处理不可信输入
# 当命令包含用户输入时，使用 shell=False 防止 shell 注入
let user_input = "some_input"
let result = shell_exec("echo " + user_input, shell=false)

# 系统信息
let pid = process_id()
let os = platform()        # "linux", "darwin", "windows"
let host = hostname()

# 日志
log_info("Application started")
log_error("Something went wrong", category="app")
```

### Crypto（加密哈希）

```helen
# 哈希
let md5 = hash_md5("data")
let sha256 = hash_sha256("data")
let sha512 = hash_sha512("data")

# HMAC
let sig = hmac_sha256("message", "secret_key")

# UUID
let id = uuid_generate()  # "550e8400-e29b-41d4-a716-446655440000"

# 随机字节
let bytes = random_bytes(16)  # 16 字节随机数据
```

## Observability（可观测性）

AI 原生可观测性函数，为 AI Agent 提供结构化调试上下文。

```helen
# debug() — 结构化调试输出到 stderr
let x = 42
debug("variable value", x)
# 输出: [DEBUG] variable value {"value": 42}

debug("checkpoint reached")
# 输出: [DEBUG] checkpoint reached

# trace_on() / trace_off() — 开启/关闭执行追踪
trace_on()
let result = compute_something()
trace_off()

# get_trace() — 获取最近执行追踪记录
let trace = get_trace(10)
print(trace)
```

## Context（上下文管理）

管理 LLM 对话上下文的函数，用于长对话 agent 的上下文控制。

```helen
# clear_context() — 清空当前对话上下文
# 用于重新开始对话或重置上下文
let result = clear_context()
print("已清空 " + str(result["cleared_messages"]) + " 条消息")
print("释放约 " + str(result["cleared_tokens"]) + " tokens")
# 返回: {"status": "ok", "cleared_messages": 5, "cleared_tokens": 1200, "warning": "..."}

# compress_context() — 压缩当前对话上下文
# 用于减少 token 消耗，保留重要上下文
let result = compress_context("auto")
# 策略: "auto" (自动), "summarize" (LLM 摘要), "truncate" (截断), "none" (不压缩)
print("从 " + str(result["original_tokens"]) + " 压缩到 " + str(result["compressed_tokens"]) + " tokens")
# 返回: {"status": "ok", "original_messages": 10, "compressed_messages": 5, ...}
```

**使用场景**：
- 长对话 agent 定期压缩上下文（避免 token 超限）
- 用户要求"重新开始"时清空上下文
- 错误恢复时重置上下文

**注意事项**：
- `clear_context()` 会清空所有对话历史，LLM 将失去之前的上下文
- `compress_context("auto")` 只在 token 超过阈值时才压缩
- `compress_context("summarize")` 会调用 LLM，较慢但保留上下文
- `compress_context("truncate")` 快速但会丢失旧消息

### REPL 调试命令

```
:trace on          # 开启执行追踪
:trace off         # 关闭执行追踪
:trace show [n]    # 显示最近 n 条追踪记录
:last_error        # 显示上次错误的结构化上下文（JSON）
:llm_log [n]       # 显示最近 n 次 LLM 调用审计日志
```

### assert 语句

```helen
# 运行时断言
assert x > 0
assert x > 0, "x must be positive"

# 断言失败抛出 AssertionError，可捕获
try {
    assert false, "test"
} catch AssertionError as e {
    print("Caught: " + e.message)
}
```

### 设计特点

- **零开销默认**：追踪关闭时无性能影响
- **JSON 结构化**：所有输出都是 AI 可消费的格式
- **自动上下文**：错误/断言失败自动捕获调用栈 + 作用域变量
- **LLM 审计**：`llm act` 自动记录调用详情

## Test（测试框架）

```helen
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

// 运行: helen test calculator_test.helen
// 监听: helen test calculator_test.helen --watch
// 过滤: helen test calculator_test.helen --filter "add"
```

### Expect 链式 API

```helen
fn test_expect() {
    expect(42).toBe(42)
    expect("hello").toContain("ell")
    expect([1, 2, 3]).toHaveLength(3)
    expect(10).toBeGreaterThan(5)
    expect("test123").toMatch("[0-9]+")
    expect(5).not_.toBe(6)
}
```

## Quality（质量评估）

```helen
// 读取源代码
let source = read_file("my_program.helen")

// 代码分析
let metrics = analyze_code(source, "my_program.helen")
print("Functions: " + str(metrics["function_count"]))
print("Complexity: " + str(metrics["avg_complexity"]))

// 安全检查
let issues = check_security(source)
print("Security issues: " + str(len(issues)))

// 7 维评分
let scores = quality_score(source, "my_program.helen")
print("Total: " + str(scores["total"]))
print("Grade: " + scores["grade"])

// 完整报告
print(quality_report(source, "my_program.helen"))

// CLI: helen quality my_program.helen --json
```

### 7 个评估维度

| 维度 | 权重 | 评估内容 |
|------|:----:|---------|
| 架构设计 | 20% | 函数长度、复杂度、嵌套深度 |
| 代码质量 | 15% | 注释率、函数平均长度 |
| 安全性 | 20% | 危险模式检测 |
| 测试覆盖 | 15% | 测试文件存在性 |
| 文档 | 10% | docstring 覆盖率 |
| 可维护性 | 10% | 长函数、高复杂度函数 |
| 工程规范 | 10% | 命名规范、文件大小 |

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

异常消息格式为 `"Python <类型名>: <原始消息>"`，可在 catch 块中通过消息前缀区分具体的 Python 异常类型。已存在的 Helen 异常（如 `TimeoutError`）保持原有类型不变。

