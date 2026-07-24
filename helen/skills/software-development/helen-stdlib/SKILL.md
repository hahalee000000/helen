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
| **Core** | 17 | `print`, `len`, `str`, `int`, `float`, `bool`, `list`, `dict`, `abs`, `min`, `max`, `range`, `type`, `isinstance`, `input`, `multiline_input`, `exit` |
| **String** | 40 | `upper`, `lower`, `strip`, `split`, `join`, `replace`, `find`, `reverse`, `repeat`, `regex_match`, `regex_replace`, `format_float`, `tokenize`, `levenshtein`, `base64_encode` |
| **Data** | 27 | `json_parse`, `json_stringify`, `yaml_parse`, `toml_parse`, `csv_parse`, `xml_parse`, `html_escape`, `html_parse`, `markdown_parse`, `markdown_to_html` |
| **Collection** | 22 | `sort`, `reverse`, `unique`, `flatten`, `zip`, `map`, `filter`, `reduce`, `chunk`, `set_union`, `set_intersection`, `set_difference` |
| **Network** | 9 | `http_get`, `http_post`, `http_put`, `http_delete`, `http_download`, `url_parse`, `url_build`, `url_encode`, `url_decode` |
| **Time** | 16 | `now`, `time`, `date`, `datetime`, `date_format`, `date_parse`, `date_add`, `date_diff`, `sleep`, `stopwatch_start`, `stopwatch_elapsed`, `stopwatch_lap` |
| **Math** | 27 | `round`, `sqrt`, `floor`, `ceil`, `sum`, `product`, `mean`, `median`, `mode`, `stddev`, `variance`, `percentile`, `correlation`, `cos`, `sin`, `tan`, `pow`, `log`, `log2`, `log10`, `exp` |
| **File** | 12 | `read_file`, `write_file`, `append_file`, `list_dir`, `mkdir`, `mkdir_p`, `copy_file`, `delete_file`, `file_size`, `glob_files`, `grep_files`, `temp_file` |
| **System** | 24 | `env_get`, `env_set`, `env_delete`, `env_list`, `get_cli_args`, `parse_cli_args`, `shell_exec`, `exec`, `exec_async`, `pid`, `exit`, `kill`, `log_info`, `log_error`, `log_debug`, `platform`, `hostname`, `python_version`, `cpu_count`, `memory_info` |
| **Crypto** | 20 | `md5`, `sha1`, `sha256`, `sha512`, `hmac_sha256`, `random`, `randint`, `choice`, `shuffle`, `sample`, `uuid_generate`, `uuid_from_string`, `uuid_nil`, `random_bytes`, `random_hex`, `random_base64` |
| **IO** | 9 | `stream_print`, `stream_clear`, `progress_bar`, `mkdir`, `mkdir_p`, `append_file`, `stream_cursor_up`, `stream_cursor_down` |
| **Path** | 6 | `path_basename`, `path_dirname`, `path_exists`, `path_is_dir`, `path_is_file`, `path_join` |
| **Tools** | 7 | `shell_exec`, `calculate`, `patch_file`, `load_skill`, `list_skill_references`, `web_search`, `web_fetch` |
| **Observability** | 4 | `debug`, `trace_on`, `trace_off`, `get_trace` |
| **Context** | 28 | `clear_context`, `compress_context`, `compress_context_target`, `context_stats`, `context_usage`, `get_message`, `delete_message`, `pin_message`, `unpin_message`, `insert_message`, `replace_message`, `working_memory_get`, `working_memory_set`, `working_memory_remove`, `working_memory_clear`, `set_compression_strategy`, `set_context_window`, `set_working_memory_enabled`, `set_cache_aware`, `get_context_config`, `search_context`, `context_slice`, `export_context`, `import_context`, `fork_context`, `restore_context`, `on_compression`, `on_context_overflow` |
| **Transcript** | 22 | `get_session_id`, `get_session_meta`, `list_sessions`, `replay_transcript`, `replay_full_session`, `export_transcript`, `search_transcript`, `list_invocations`, `get_invocation`, `get_invocation_tree`, `invocation_path`, `get_compression_audit`, `resume_session`, `get_session_dir`, `set_session_dir`, `delete_session`, `delete_current_session`, `cleanup_sessions`, `get_spawned_sessions`, `get_spawn_tree` |
| **Media** | 12 | `media`, `media_base64`, `is_media`, `media_type`, `to_openai_parts`, `to_claude_parts`, `to_gemini_parts`, `media_to_base64`, `save_media`, `is_image`, `is_video`, `is_audio` |
| **Test** | 23 | `test_suite`, `test_case`, `test_case_skip`, `test_end_suite`, `set_test_timeout`, `run_tests`, `run_tests_json`, `test_count`, `test_reset`, `before_all`, `after_all`, `before_each`, `after_each`, `assert_equal`, `assert_not_equal`, `assert_true`, `assert_contains`, `assert_throws`, `describe`, `expect`, `it`, `it_skip`, `fail` |
| **Quality** | 4 | `analyze_code`, `check_security`, `quality_score`, `quality_report` |
| **LLM** | 3 | `cancel_llm_call`, `current_llm_call_id`, `cancel_all_llm_calls` |
| **Concurrency** | 1 | `mailbox_select` |

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
let current = time()                  # 当前时间（datetime 对象）

# 格式化
let formatted = date_format(now(), "%Y-%m-%d %H:%M:%S")
# "2026-06-19 17:30:00"

# 解析
let parsed = date_parse("2026-06-19", "%Y-%m-%d")

# 日期运算
let tomorrow = date_add(now(), days=1)
let diff = date_diff(date1, date2, "days")

# 休眠
sleep(1.5)  # 休眠 1.5 秒

# 计时（高精度）
let sw = stopwatch_start()
let elapsed = stopwatch_elapsed(sw)   # 秒（浮点数，高精度）
print("耗时: " + str(elapsed) + " 秒")
```

### Math（数学运算）

```helen
# 基础数学
let rounded = round(3.14159, 2)   # 3.14
let root = sqrt(16)               # 4.0
let ceiling = ceil(3.2)           # 4
let flooring = floor(3.8)         # 3
let power = pow(2, 10)            # 1024

# 对数
let natural = log(2.718)          # 自然对数 (ln)
let base2 = log2(8)               # 3 (2^3 = 8)
let base10 = log10(100)           # 2 (10^2 = 100)
let exponential = exp(1)          # 2.718... (e^1)

# 三角函数（弧度制）
let cosine = cos(0)               # 1
let sine = sin(3.14159 / 2)       # 1
let tangent = tan(0)              # 0
let angle = acos(0.5)             # 1.047... (60°)
let angle2 = asin(0.5)            # 0.523... (30°)
let angle3 = atan(1)              # 0.785... (45°)
let angle4 = atan2(1, 1)          # 0.785... (45°, y/x)

# 统计
let avg = mean([1, 2, 3, 4, 5])   # 3.0
let mid = median([1, 2, 3, 4, 5]) # 3
let std = stddev([1, 2, 3, 4, 5]) # 1.414...
let total = sum([1, 2, 3, 4, 5])  # 15
let prod = product([1, 2, 3, 4])  # 24

# 随机数
let rand = random()               # 0-1 的随机浮点数
let rand_int = randint(1, 100)    # 1-100 的随机整数
let item = choice([1, 2, 3, 4])   # 随机选择
let shuffled = shuffle([1, 2, 3]) # 随机打乱
```

### File（文件操作）

```helen
# 读写文件
let content = read_file("/path/to/file.txt")
write_file("/path/to/output.txt", "Hello, World!")
append_file("/path/to/log.txt", "New log entry\n")

# 文件信息
if path_exists("/path/to/file.txt") {
    let size = file_size("/path/to/file.txt")
    print("文件大小: " + str(size) + " bytes")
}

# 目录操作
let files = list_dir("/path/to/dir")
mkdir("/path/to/new/dir")
mkdir_p("/path/to/deep/nested/dir")  # 递归创建
copy_file("/src/file.txt", "/dst/file.txt")
delete_file("/path/to/file.txt")

# 文件搜索
let py_files = glob_files("src", "*.py")       # 递归查找所有 Python 文件
let md_files = glob_files("docs", "**/*.md")   # 使用 ** 显式递归

# 搜索文件内容（字面量）
let matches = grep_files("src/", "TODO")
# [{"file": "main.py", "line": 42, "text": "    # TODO: fix this"}]

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

# Shell 命令（默认 shell=True，使用 /bin/bash，支持完整 shell 语法）
let result = shell_exec("ls -la")
let result = shell_exec("mkdir -p ~/project/{src,tests,contracts}")
let result = shell_exec("cat file.txt | grep pattern | wc -l")
print(result["output"])

# 安全模式：处理不可信输入时使用 shell=false 防止 shell 注入
let result = shell_exec("echo " + user_input, shell=false)

# 系统信息
let pid = pid()                   # 进程 ID
let os = platform()               # "linux", "darwin", "windows"
let host = hostname()             # 主机名
let py_ver = python_version()     # Python 版本
let cpus = cpu_count()            # CPU 核心数
let mem = memory_info()           # {total, available, used, percent}

# 日志
log_info("Application started")
log_error("Something went wrong", category="app")
```

### Crypto（加密哈希）

```helen
# 哈希
let md5_hash = md5("data")
let sha256_hash = sha256("data")
let sha512_hash = sha512("data")

# HMAC
let sig = hmac_sha256("message", "secret_key")

# 随机数
let rand = random()               # 0-1 随机浮点
let rand_int = randint(1, 100)    # 随机整数
let item = choice([1, 2, 3])      # 随机选择

# UUID
let id = uuid_generate()          # "550e8400-e29b-41d4-a716-446655440000"
let nil_id = uuid_nil()           # "00000000-0000-0000-0000-000000000000"
let parsed = uuid_from_string("550E8400-E29B-41D4-A716-446655440000")

# 随机字节
let bytes = random_bytes(16)      # 32 字符的十六进制字符串
let hex_str = random_hex(32)
let b64 = random_base64(16)       # base64 编码的随机数据
```

## Observability（可观测性）

AI 原生可观测性函数，为 AI Agent 提供结构化调试上下文。

```helen
# debug() — 结构化调试输出到 stderr
debug("variable value", x)
# 输出: [DEBUG] variable value {"value": 42}
debug("checkpoint reached")

# trace_on() / trace_off() — 开启/关闭执行追踪
trace_on()
let result = compute_something()
trace_off()

# get_trace() — 获取最近执行追踪记录
let trace = get_trace(10)
```

**设计特点**: 零开销默认（追踪关闭时无影响）、JSON 结构化输出（AI 可消费）、错误/断言自动捕获调用栈 + 作用域变量、`llm act` 自动记录调用详情。

## Context（上下文管理）

管理 LLM 对话上下文的函数，用于长对话 agent 的上下文控制。

```helen
# 基础操作
clear_context()                       # 清空上下文，返回 {cleared_messages, cleared_tokens}
compress_context("auto")              # 压缩上下文
# 策略: "auto" | "summarize" (LLM摘要) | "truncate" | "none" | "graduated"

# 检查 (Inspection)
context_stats()                       # {message_count, total_tokens, system_tokens, ...}
context_usage()                       # 0.0-1.0 占用率
let usage = context_usage()
if usage > 0.8 { compress_context("auto") }
get_message(uuid)                     # 获取单条消息

# 细粒度变更 (Fine-grained Mutation)
insert_message("system", "重要提示", 0)  # 插入消息（可指定位置）
replace_message(uuid, "新内容")          # 替换消息内容
delete_message(uuid)                     # 删除消息
pin_message(uuid) / unpin_message(uuid)  # 钉住消息（不受压缩影响）

# 工作记忆 (Working Memory) — 自动跟踪活跃文件、决策、待办、错误历史
working_memory_set("current_file", "main.py")
working_memory_set("decision", "使用 JWT 认证")
working_memory_get("current_file")       # "main.py"
working_memory_remove("todo")
working_memory_clear()

# 运行时配置 (Runtime Config)
set_compression_strategy("graduated")    # 动态调整压缩策略
set_context_window(128000)               # 设置上下文窗口大小
set_working_memory_enabled(true)
set_cache_aware(true)                    # 启用缓存感知压缩（提高缓存命中率）
get_context_config()                     # {strategy, window, working_memory, cache_aware}

# 查询 (Query)
search_context("认证")                   # [{uuid, role, content}, ...]
context_slice(-5)                        # 最近 5 条消息
context_slice(0, 10)                     # 前 10 条消息

# 多 Agent 转移 (Multi-Agent Transfer)
export_context()                         # 导出 [{role, content}, ...]
import_context(messages)                 # 导入到当前会话
fork_context()                           # 创建独立副本

# 跨会话恢复 (v1.21+)
restore_context("session_xxx")           # 从旧 transcript 恢复 active context
# 恢复后 LLM 在下一次 llm act 调用时能看到旧会话消息
# ⚠️ 只恢复 messages，不恢复 working_memory 和 config（需手动恢复）

# vs resume_session:
# - restore_context: 恢复 active context，支持按 agent/invocation 过滤
# - resume_session:  导入全部消息到当前新 session

# 生命周期钩子 (Lifecycle Hooks)
on_compression(fn(stats) {
    print("即将压缩: " + str(stats["token_count"]) + " tokens")
})
on_context_overflow(fn(stats) {
    compress_context("truncate")
})
```

**REPL 调试命令**: `:trace on/off/show [n]`、`:last_error`（结构化 JSON）、`:llm_log [n]`（LLM 调用审计日志）

**assert 语句**:
```helen
assert x > 0
assert x > 0, "x must be positive"
# 断言失败抛出 AssertionError，可通过 try-catch 捕获
```

## Test（测试框架）

```helen
fn test_add() {
    assert_equal(2 + 3, 5)
}

fn test_subtract() {
    assert_equal(10 - 4, 6)
}

test_suite("Calculator")
test_case("adds numbers", test_add)
test_case("subtracts numbers", test_subtract)
test_end_suite()
run_tests()

# CLI:
# helen test calc.helen              # 运行测试
# helen test calc.helen --watch      # 监听模式
# helen test calc.helen --filter "add"  # 过滤
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

`before_all`/`after_all`/`before_each`/`after_each` 钩子可用。

## Quality（质量评估）

```helen
let source = read_file("my_program.helen")

let metrics = analyze_code(source, "my_program.helen")
print("Functions: " + str(metrics["function_count"]))

let issues = check_security(source)
print("Security issues: " + str(len(issues)))

let scores = quality_score(source, "my_program.helen")
print("Total: " + str(scores["total"]) + " Grade: " + scores["grade"])

print(quality_report(source, "my_program.helen"))
# CLI: helen quality my_program.helen --json
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

## Transcript（会话记录）

TranscriptStore (v1.16) — SSOT，所有对话消息持久化存储。

### 会话管理

```helen
# get_session_id() — 当前会话 ID
let session = get_session_id()  # "session_{timestamp}_{uuid8}"

# get_session_meta() (v1.23.3) — 会话元数据（启动时记录）
let meta = get_session_meta()
# {argv, timestamp, helen_version, python_version, cwd, session_scope}

# list_sessions(scope?) — 列出所有会话
let sessions = list_sessions()
# [{session_id, created_at, modified_at, size_bytes, message_count, scope}, ...]
let global_sessions = list_sessions("global")
let project_sessions = list_sessions("project")

# 会话目录管理
let info = get_session_dir()    # {session_dir, scope, project_dir}
set_session_dir("/custom/path")
```

**运行时隔离原则**:
- 同一进程内多次调用 `get_session_id()` → 相同 ID
- 重启程序 → 新 Interpreter → 新 session_id
- `spawn` 创建的 agent → 新 Interpreter → 新 session_id（独立 transcript）
- 普通 agent 调用（同进程）→ 共享 session_id，靠 `invocation_id` 区分
- 跨运行时继承必须显式编程：`resume_session(parent_sid)` 或 `Channel.send(sid)`

### 回放、导出与搜索

```helen
# 回放
replay_transcript()                              # 当前会话
replay_transcript("session_123", true)           # 包含压缩消息
replay_transcript(agent="A", last_only=true)     # 按 agent 过滤
replay_transcript(invocation_id="inv_1", include_subtree=true)

# 导出
export_transcript(null, "json")                  # 导出当前为 JSON
export_transcript(null, "text")                  # 导出为纯文本
export_transcript("full.json", "json", include_spawned=true)  # 包含 spawn

# 搜索 (v1.22+) — 搜索持久化 transcript（区别于 search_context 搜当前上下文）
search_transcript("认证 bug")                    # 基本搜索
search_transcript("数据库", scope="all", limit=10)  # 跨所有 session
search_transcript("fix.*bug", regex=true)        # 正则
search_transcript("TODO", role="user")           # 按角色过滤
search_transcript("error", include_spawned=true) # 跨 spawn 搜索 (v1.23.7)

# 搜索 → 恢复上下文的典型用法
let matches = search_transcript("认证 bug", scope="all")
if len(matches) > 0 {
    restore_context(matches[0]["session_id"])
}
```

### 调用树查询 (v1.22+)

```helen
# 每个 agent main {} 执行都是一个 invocation，带唯一 invocation_id
list_invocations()                               # 列出所有 invocation
list_invocations(agent="Researcher", limit=10)   # 按 agent 过滤

get_invocation("inv_xxx")                        # 查单个
# {agent_name, message_count, parent_invocation_id, ...}

get_invocation_tree()                            # 完整调用树（嵌套结构）
invocation_path("inv_3")                         # "top -> A -> C"

# 中文别名
列出调用()
获取调用("inv_xxx")
获取调用树()
调用路径("inv_3")
```

**上下文隔离 (v1.22/v1.23)**: 每个 agent main {} 执行都是独立 invocation，LLM 只能看到当前 invocation 的消息。

### 会话恢复与清理

```helen
# 恢复
resume_session("session_123")                    # 导入历史消息到当前 session

# 删除
delete_session("session_123")                    # 默认级联删除 spawn
delete_session("session_123", cascade=false)     # 只删主 session
delete_current_session(true)                     # 删除当前会话

# 清理
cleanup_sessions(keep_count=10)                  # 保留最近 10 个
cleanup_sessions(older_than_days=30)             # 删除 30 天前的
cleanup_sessions(keep_count=5, older_than_days=7, cascade=false)

# 压缩审计
get_compression_audit()
# [{timestamp, strategy, before_tokens, after_tokens, boundary_uuid}, ...]
```

### Spawn 关系追踪 (v1.23.7)

```helen
get_spawned_sessions()                           # 直接子 session
get_spawn_tree()                                 # 完整 spawn 树
replay_full_session()                            # 聚合主 session + 所有 spawn
```

### 会话作用域 (v1.20)

- `global`: `~/.helen/sessions/`
- `project`: `.helen/sessions/`（检测到 `.helen/`、`helen.yaml`、`helen.toml`）
- `auto`（默认）: 自动检测项目目录，否则全局

### 启动时恢复 Session (v1.24+)

```bash
helen --session=session_xxx file.helen    # 指定 session 启动
helen --resume-latest file.helen          # 自动恢复最近 session
helen repl --resume-latest                # REPL 简写: -r
```

```python
# Python API
from helen.interpreter import Interpreter
interp = Interpreter(session_id="session_xxx")
```

| 特性 | `--session` (启动时) | `resume_session()` (运行时) |
|------|---------------------|---------------------------|
| 时机 | 解释器启动前 | 程序运行中 |
| 行为 | 直接复用指定 session | 导入历史消息到当前新 session |
| transcript | 一个文件 | 两个文件 |

## Media（媒体/多模态）

v1.17 引入多模态支持，`MediaPart` 是一等数据类型。

```helen
# 创建
let img = media("/path/to/image.png")          # 文件路径或 URL
let video = media("https://example.com/video.mp4")
let audio = media("/path/to/audio.mp3", "audio")  # 显式指定类型
let base64_img = media_base64("iVBORw0KGgo...", "image/png")

# 检查
is_media(value)                                # 是否为 MediaPart
media_type(img)                                # "image" | "video" | "audio"
is_image(img) / is_video(video) / is_audio(audio)

# 格式适配器
to_openai_parts([img, video])                  # [{type: "image_url", ...}]
to_claude_parts([img])                         # [{type: "image", source: {...}}]
to_gemini_parts([img])

# 工具
media_to_base64(img)                           # 转为 base64 字符串
save_media(img, "/path/to/save.png")           # 保存到文件

# llm act 中使用（回调即适配器）
llm act "分析这张图片"
    media("/path/to/image.png")
    on_media fn(parts, provider) {
        if provider == "claude" { return to_claude_parts(parts) }
        return to_openai_parts(parts)
    }
```

## LLM（大模型调用控制）

控制正在进行的 LLM 流式调用。

```helen
let call_id = current_llm_call_id()     # string | null
cancel_llm_call(call_id)
cancel_all_llm_calls()                  # 返回取消数量

# 中文别名
取消大模型调用(call_id)
当前大模型调用id()
取消所有大模型调用()
```

用于 `on_chunk` 回调中检测终止条件、Ctrl+C 中断、超时控制。

## Concurrency（并发）

v1.18 基于 Channel 的消息传递并发模型。

```helen
agent Worker(task: str) {
    main {
        # 执行任务...
        return "结果"
    }
}

# spawn 返回 Channel（邮箱）
let ch = spawn Worker("任务 1")

# Channel 方法
ch.send("消息")              # 发送消息
let msg = ch.receive()       # 阻塞接收
let maybe = ch.try_receive() # 非阻塞接收（无消息返回 null）
ch.cancel()                  # 取消（中断流式 LLM 调用）
ch.close()                   # 关闭通道
ch.is_closed()               # 检查是否已关闭

# 中文别名: 发送(), 接收(), 尝试接收(), 取消(), 关闭(), 已关闭()

# mailbox_select — 多通道选择（竞争模式：谁先完成用谁）
let m1 = spawn StrategyA()
let m2 = spawn StrategyB()
let m3 = spawn StrategyC()
let result = mailbox_select([m1, m2, m3])  # {endpoint: Channel, message: "..."}

# 带超时
let result = mailbox_select([m1, m2], timeout=5.0)  # 超时返回 null
if result == null { print("超时") }

# 中文别名
let result = 邮箱选择([m1, m2, m3])
```

**关键特性**: 快照语义（spawn 深拷贝所有变量包括 SharedStore）、隔离环境、流式中断 (`ch.cancel()`)。Agent 间数据共享通过 Channel 消息显式传递。

## 异常处理 (v.9+)

Python 异常自动包装为 `RuntimeError`，格式 `"Python <类型名>: <原始消息>"`：

```helen
try {
    let x = len(42)
} catch RuntimeError err {
    print(err.message)    # "Python TypeError: object of type 'int' has no len()"
}

try {
    let data = read_file("/nonexistent")
} catch RuntimeError err {
    print(err.message)    # "Python FileNotFoundError: [Errno 2] ..."
}
```

可通过消息前缀区分 Python 异常类型。已存在的 Helen 异常（如 `TimeoutError`）保持原有类型不变。

## 模块缓存（Python REPL/Jupyter）

`ImportResolver` 使用内存缓存（`_cached_results`），修改 `.helen` 文件后需手动清除：

```python
# 方案 1: 每次新建 Interpreter（简单）
interp = Interpreter()

# 方案 2: 手动清除缓存（高效）
interp.import_resolver._cached_results.clear()
interp.import_resolver._loaded.clear()

# 调试: 检查缓存状态
print(f"Cached: {len(interp.import_resolver._cached_results)} files")
for path in interp.import_resolver._loaded:
    print(f"  - {path}")
```

推荐方案：使用 CLI 开发（`helen my_program.helen`），每次新进程自动重新加载。

## 内置模板库

```bash
helen template --list                  # 查看所有模板
helen template simple_agent            # 查看模板内容
helen template spawn_channel --copy my_worker.helen  # 复制到当前目录
```

模板：`simple_agent`、`spawn_channel`、`shared_store`、`context_object`、`pipeline`。所有模板遵循"调用者决定上下文"原则——agent 的所有信息通过参数显式传递。

---

**最后更新**: 2026-07-24

## 相关技能

- **helen-syntax** — Helen 语法参考（关键字、类型、表达式）
- **helen-agent-patterns** — Agent 设计模式
- **helen-agent-collaboration** — 多 Agent 协作模式
- **helen-testing** — 测试框架使用指南
