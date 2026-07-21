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
| **Transcript** | 17 | `get_session_id`, `get_session_meta`, `list_sessions`, `replay_transcript`, `export_transcript`, `search_transcript`, `list_invocations`, `get_invocation`, `get_invocation_tree`, `invocation_path`, `get_compression_audit`, `resume_session`, `get_session_dir`, `set_session_dir`, `delete_session`, `delete_current_session`, `cleanup_sessions` |
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
# ... 执行操作 ...
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
let pid = pid()                   # 进程 ID
let os = platform()               # "linux", "darwin", "windows"
let host = hostname()             # 主机名
let py_ver = python_version()     # Python 版本
let cpus = cpu_count()            # CPU 核心数
let mem = memory_info()           # {total: ..., available: ..., used: ..., percent: ...}

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
let parsed = uuid_from_string("550E8400-E29B-41D4-A716-446655440000")  # 规范化

# 随机字节
let bytes = random_bytes(16)      # 32 字符的十六进制字符串
let hex_str = random_hex(32)      # 32 字符的十六进制字符串
let b64 = random_base64(16)       # base64 编码的随机数据
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

### Context 高级函数

```helen
// ═══════════════════════════════════════════════════════════════
// 上下文检查 (Inspection)
// ═══════════════════════════════════════════════════════════════

// context_stats() — 上下文统计
let stats = context_stats()
// {message_count: 10, total_tokens: 2500, system_tokens: 500, ...}

// context_usage() — 上下文占用率 (0.0-1.0)
let usage = context_usage()
if usage > 0.8 {
    compress_context("auto")
}

// get_message(uuid) — 获取单条消息
let msg = get_message("550e8400-e29b-41d4")
print(msg["role"] + ": " + msg["content"])

// ═══════════════════════════════════════════════════════════════
// 细粒度变更 (Fine-grained Mutation)
// ═══════════════════════════════════════════════════════════════

// insert_message(role, content, index?) — 插入消息
insert_message("system", "重要提示", 0)  // 插入到开头

// replace_message(uuid, content) — 替换消息内容
replace_message("msg-uuid", "新内容")

// delete_message(uuid) — 删除消息
delete_message("msg-uuid")

// pin_message(uuid) / unpin_message(uuid) — 钉住消息（不受压缩影响）
pin_message("important-msg")   // 钉住，压缩时保留
unpin_message("important-msg") // 取消钉住

// ═══════════════════════════════════════════════════════════════
// 工作记忆 (Working Memory)
// ═══════════════════════════════════════════════════════════════

// 工作记忆自动跟踪活跃文件、最近决策、待办事项、错误历史
working_memory_set("current_file", "main.py")
working_memory_set("decision", "使用 JWT 认证")
working_memory_set("todo", "修复登录 bug")

let file = working_memory_get("current_file")  // "main.py"
working_memory_remove("todo")
working_memory_clear()  // 清空所有工作记忆

// ═══════════════════════════════════════════════════════════════
// 运行时配置 (Runtime Config)
// ═══════════════════════════════════════════════════════════════

// 动态调整压缩策略
set_compression_strategy("graduated")  // "auto"|"summarize"|"truncate"|"none"|"graduated"

// 设置上下文窗口大小
set_context_window(128000)  // 128K tokens

// 启用/禁用工作记忆
set_working_memory_enabled(true)

// 启用缓存感知压缩（提高缓存命中率）
set_cache_aware(true)

// 获取当前配置
let config = get_context_config()
// {strategy: "graduated", window: 128000, working_memory: true, cache_aware: true}

// ═══════════════════════════════════════════════════════════════
// 查询 (Query)
// ═══════════════════════════════════════════════════════════════

// search_context(query) — 搜索上下文
let matches = search_context("认证")
// [{uuid: "...", role: "user", content: "..."}, ...]

// context_slice(start, end?) — 上下文切片
let recent = context_slice(-5)  // 最近 5 条消息
let range = context_slice(0, 10)  // 前 10 条消息

// ═══════════════════════════════════════════════════════════════
// 多 Agent 转移 (Multi-Agent Transfer)
// ═══════════════════════════════════════════════════════════════

// export_context() — 导出当前上下文
let exported = export_context()
// [{role: "user", content: "..."}, {role: "assistant", content: "..."}, ...]

// import_context(messages) — 导入上下文到当前会话
import_context(exported)

// fork_context() — 分叉上下文（创建独立副本）
let forked = fork_context()
// 可以在另一个 agent 中使用，不影响原始上下文

// ═══════════════════════════════════════════════════════════════
// 跨会话恢复 (Cross-Session Restore) — v1.21+
// ═══════════════════════════════════════════════════════════════

// restore_context(session_id) — 从旧 transcript session 恢复 active context
// 恢复后 LLM 在下一次 llm act 调用时能看到旧会话的所有消息

// 步骤 1：列出旧会话
let sessions = list_sessions()
for s in sessions {
    print("{s.session_id}: {s.message_count} msgs, scope={s.scope}")
}

// 步骤 2：恢复到当前 active context
let r = restore_context("session_1783492628_d9d9c0aa")
if r["status"] == "ok" {
    print("恢复了 " + str(r["restored_messages"]) + " 条消息")
    print("跳过 " + str(r["boundary_markers"]) + " 个压缩边界")
} else {
    print("恢复失败: " + r["error"])
}

// 中文别名
恢复上下文("session_1783492628_d9d9c0aa")

// ⚠️ 限制：只恢复 messages，不恢复 working_memory 和 config
// 需要时手动恢复：
working_memory_set("current_task", "从旧会话继续的工作")
set_compression_strategy("graduated")

// restore_context vs resume_session:
// - restore_context: 恢复 active context，支持按 agent/invocation 过滤
// - resume_session:  恢复 active context，导入全部消息（v1.23 后 LLM 能看到）
```

// ═══════════════════════════════════════════════════════════════
// 生命周期钩子 (Lifecycle Hooks)
// ═══════════════════════════════════════════════════════════════

// on_compression(fn) — 压缩前回调
on_compression(fn(stats) {
    print("即将压缩: " + str(stats["token_count"]) + " tokens")
})

// on_context_overflow(fn) — 上下文溢出回调
on_context_overflow(fn(stats) {
    print("上下文溢出！当前: " + str(stats["usage_ratio"]))
    compress_context("truncate")
})
```

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

## Transcript（会话记录）

TranscriptStore 是 v1.16 引入的 SSOT（Single Source of Truth），所有对话消息都持久化存储。

```helen
// ═══════════════════════════════════════════════════════════════
// 会话管理
// ═══════════════════════════════════════════════════════════════

// get_session_id() — 获取当前会话 ID
let session = get_session_id()
print("当前会话: " + session)

// get_session_meta() — 获取会话元数据（v1.23.3）
// 返回启动时记录的 argv、时间戳、版本等信息，用于审计和调试
let meta = get_session_meta()
if meta["status"] == "ok" {
    let data = meta["data"]
    print("启动命令: " + str(data["argv"]))        // ["helen", "my_app.helen"]
    print("启动时间: " + str(data["timestamp"]))   // 1720435200.123
    print("Helen 版本: " + data["helen_version"])  // 1.23.3
    print("Python 版本: " + data["python_version"])
    print("工作目录: " + data["cwd"])
    print("作用域: " + data["session_scope"])      // "global" | "project"
}
// 中文别名: 获取会话元数据()

// ── 关键行为（Transcript 运行时隔离设计原则） ──
// ✅ 同一进程内多次调用 → 相同 ID（@property getter）
// ✅ 重启程序 → 新 Interpreter → 新 session_id（session_{timestamp}_{uuid8}）
// ✅ spawn 创建的 agent → 新 Interpreter → 新 session_id（独立 transcript）
// ✅ 普通 agent 调用（同进程）→ 共享 session_id，靠 invocation_id 区分
// ⚠️ session_id 与目录路径无关——不是"目录绑定的持久 ID"
// ⚠️ 跨运行时继承必须显式编程：resume_session(parent_sid) 或 Channel.send(sid)

// list_sessions(scope?) — 列出所有会话
let sessions = list_sessions()
// [{session_id: "...", created_at: ..., modified_at: ..., size_bytes: ..., message_count: ..., scope: "global"|"project"}, ...]

let global_sessions = list_sessions("global")   // 全局会话
let project_sessions = list_sessions("project") // 项目会话

// get_session_dir() / set_session_dir(path) — 会话目录管理
let info = get_session_dir()
// {status: "ok", session_dir: "/path/to/sessions", scope: "global"|"project"|"env_override", project_dir: str | null}
print("会话目录: " + info["session_dir"])
print("作用域: " + info["scope"])

let result = set_session_dir("/custom/path")
// {status: "ok", session_dir: "/custom/path", previous: "/previous/path"}
if result["status"] == "ok" {
    print("已切换到: " + result["session_dir"])
}

// ═══════════════════════════════════════════════════════════════
// 会话回放与导出
// ═══════════════════════════════════════════════════════════════

// replay_transcript(session_id?, include_compressed?) — 回放会话
let messages = replay_transcript()
// [{role: "user", content: "...", uuid: "...", timestamp: ...}, ...]

let full = replay_transcript("session_123", true)  // 包含压缩消息

// export_transcript(session_id?, format?) — 导出会话
export_transcript(null, "json")   // 导出当前会话为 JSON
export_transcript(null, "text")   // 导出为纯文本

// ═══════════════════════════════════════════════════════════════
// 内容搜索 (v1.22+)
// ═══════════════════════════════════════════════════════════════

// search_transcript(query, ...) — 按内容搜索持久化 transcript
// 与 search_context() 不同：搜持久化历史，可跨会话
let matches = search_transcript("认证 bug")
// [{session_id, message_uuid, role, content, snippet, match_position}, ...]

// 跨所有 session 搜索（跨会话发现）
let matches = search_transcript("数据库 schema", scope="all", limit=10)

// 正则匹配
let matches = search_transcript("fix.*bug", regex=true)

// 只搜 user 消息
let matches = search_transcript("TODO", role="user")

// 中文别名
let matches = 搜索会话("认证 bug", scope="all")

// 典型用法：搜索 → 恢复完整上下文
if len(matches) > 0 {
    restore_context(matches[0]["session_id"])
}

// ═══════════════════════════════════════════════════════════════
// 调用树查询 (v1.22+)
// ═══════════════════════════════════════════════════════════════

// 每个 agent main {} 执行都是一个 invocation，带唯一 invocation_id
// transcript 完整记录所有 invocation，可查询调用结构

// list_invocations() - 列出所有 invocation（可过滤、分页）
let invs = list_invocations()
// [{invocation_id, agent_name, parent_invocation_id, message_count, ...}, ...]

let a_runs = list_invocations(agent="Researcher", limit=10)

// get_invocation(invocation_id) - 查单个 invocation
let info = get_invocation("inv_xxx")
// {agent_name: "A", message_count: 4, parent_invocation_id: "inv_top", ...}

// get_invocation_tree() - 完整调用树（嵌套结构）
let tree = get_invocation_tree()
// tree.children 是嵌套的 invocation 列表

// invocation_path(invocation_id) - 调用路径字符串
print(invocation_path("inv_3"))  // "top -> A -> C"

// 中文别名
列出调用()
获取调用("inv_xxx")
获取调用树()
调用路径("inv_3")

// ═══════════════════════════════════════════════════════════════
// 上下文隔离 (v1.22/v1.23)
// ═══════════════════════════════════════════════════════════════

// v1.22 引入 per-agent 上下文隔离：每个 agent main {} 执行都是独立的 invocation
// LLM 只能看到当前 invocation 的消息，不会看到其他 agent 或其他 invocation 的历史

// v1.23 修复了关键 bug：
// - _prepare_history_for_llm() 现在正确过滤 invocation_id
// - _import_context() 改为单写策略，避免双存储不一致
// - resume_session() 导入消息到当前 store，标记 invocation_id

// 验证示例：
agent AgentA { main { return llm act "我是 Alice" } }
agent AgentB { main { return llm act "我叫什么？" } }

let a = AgentA()  // invocation_id: inv_abc
let b = AgentB()  // invocation_id: inv_def
// AgentB 的 LLM 看不到 AgentA 的上下文 ✅

// 配合 replay_transcript 过滤
let a_msgs = replay_transcript(agent="A")              // 只看 A 的消息
let last = replay_transcript(agent="A", last_only=true) // 只看 A 最近一次
let sub = replay_transcript(invocation_id="inv_1", include_subtree=true)

// 配合 restore_context 精准恢复
restore_context("session_xxx", agent="A", last_only=true)
restore_context("session_xxx", invocation_id="inv_1", include_subtree=true)

// ═══════════════════════════════════════════════════════════════
// 压缩审计
// ═══════════════════════════════════════════════════════════════

// get_compression_audit() — 获取压缩事件历史
let audit = get_compression_audit()
// [{timestamp: ..., strategy: ..., before_tokens: ..., after_tokens: ..., boundary_uuid: ...}, ...]

// ═══════════════════════════════════════════════════════════════
// 会话恢复与清理
// ═══════════════════════════════════════════════════════════════

// resume_session(session_id) — 恢复历史会话
resume_session("session_123")

// delete_session(session_id) — 删除指定会话
delete_session("session_123")

// delete_current_session(confirm?) — 删除当前会话
delete_current_session(true)  // 需要确认

// cleanup_sessions(keep_count?, older_than_days?) — 清理旧会话
cleanup_sessions(keep_count=10)                    // 保留最近 10 个
cleanup_sessions(older_than_days=30)               // 删除 30 天前的
cleanup_sessions(keep_count=5, older_than_days=7)  // 组合条件
```

**会话作用域 (v1.20)**：
- `global`: 存储在 `~/.helen/sessions/`
- `project`: 存储在项目的 `.helen/sessions/`（需要 `.helen/`、`helen.yaml` 或 `helen.toml`）
- `auto`（默认）: 自动检测项目目录，否则使用全局

## Media（媒体/多模态）

v1.17 引入多模态支持，`MediaPart` 是一等数据类型。

```helen
// ═══════════════════════════════════════════════════════════════
// 创建媒体
// ═══════════════════════════════════════════════════════════════

// media(source, type?) — 从文件路径或 URL 创建
let img = media("/path/to/image.png")
let video = media("https://example.com/video.mp4")
let audio = media("/path/to/audio.mp3", "audio")  // 显式指定类型

// media_base64(data, mime, type?) — 从 base64 创建
let base64_img = media_base64("iVBORw0KGgo...", "image/png")

// ═══════════════════════════════════════════════════════════════
// 检查媒体
// ═══════════════════════════════════════════════════════════════

// is_media(value) — 检查是否为 MediaPart
if is_media(value) {
    print("是媒体对象")
}

// media_type(value) — 获取媒体类型
let t = media_type(img)  // "image" | "video" | "audio"

// is_image(value) / is_video(value) / is_audio(value)
if is_image(img) { print("是图片") }
if is_video(video) { print("是视频") }
if is_audio(audio) { print("是音频") }

// ═══════════════════════════════════════════════════════════════
// 格式适配器
// ═══════════════════════════════════════════════════════════════

// to_openai_parts(media_list) — 转换为 OpenAI 格式
let openai_parts = to_openai_parts([img, video])
// [{type: "image_url", image_url: {url: "..."}}, ...]

// to_claude_parts(media_list) — 转换为 Claude 格式
let claude_parts = to_claude_parts([img])
// [{type: "image", source: {type: "base64", media_type: "...", data: "..."}}, ...]

// to_gemini_parts(media_list) — 转换为 Gemini 格式
let gemini_parts = to_gemini_parts([img])

// ═══════════════════════════════════════════════════════════════
// 媒体工具
// ═══════════════════════════════════════════════════════════════

// media_to_base64(media_part) — 转换为 base64 字符串
let b64 = media_to_base64(img)

// save_media(media_part, path) — 保存到文件
save_media(img, "/path/to/save.png")

// ═══════════════════════════════════════════════════════════════
// 在 llm act 中使用
// ═══════════════════════════════════════════════════════════════

llm act "分析这张图片"
    media("/path/to/image.png")
    on_media fn(parts, provider) {
        // 自定义适配器：将 MediaPart 转换为 provider 特定格式
        if provider == "claude" {
            return to_claude_parts(parts)
        }
        return to_openai_parts(parts)
    }
```

## LLM（大模型调用控制）

控制正在进行的 LLM 流式调用。

```helen
// cancel_llm_call(call_id) — 取消指定的 LLM 调用
let call_id = current_llm_call_id()
if call_id != null {
    cancel_llm_call(call_id)
}

// current_llm_call_id() — 获取当前活跃的流式调用 ID
let id = current_llm_call_id()
// 返回 string | null

// cancel_all_llm_calls() — 取消所有活跃的流式调用
let cancelled_count = cancel_all_llm_calls()
print("已取消 " + str(cancelled_count) + " 个调用")

// 中文别名
取消大模型调用(call_id)
let id = 当前大模型调用id()
取消所有大模型调用()
```

**使用场景**：
- 在 `on_chunk` 回调中检测终止条件并中断流式输出
- 用户按 Ctrl+C 时取消后台调用
- 超时控制

## Concurrency（并发）

v1.18 引入基于 Channel 的消息传递并发模型。

```helen
// ═══════════════════════════════════════════════════════════════
// spawn — 启动并发 Agent
// ═══════════════════════════════════════════════════════════════

agent Worker(task: str) {
    main {
        // 执行任务...
        return "结果"
    }
}

// spawn 返回 Channel（邮箱）
let ch = spawn Worker("任务 1")

// ═══════════════════════════════════════════════════════════════
// Channel 方法
// ═══════════════════════════════════════════════════════════════

ch.send("消息")              // 发送消息
let msg = ch.receive()       // 阻塞接收
let maybe = ch.try_receive() // 非阻塞接收（返回 null 如果无消息）
ch.cancel()                  // 取消（中断正在进行的流式调用）
ch.close()                   // 关闭通道
let closed = ch.is_closed()  // 检查是否已关闭

// 中文别名
发送("消息")
接收()
尝试接收()
取消()
关闭()
已关闭()

// ═══════════════════════════════════════════════════════════════
// mailbox_select — 多通道选择
// ═══════════════════════════════════════════════════════════════

// 竞争模式：谁先完成用谁
let m1 = spawn StrategyA()
let m2 = spawn StrategyB()
let m3 = spawn StrategyC()

let result = mailbox_select([m1, m2, m3])
// {endpoint: Channel, message: "..."}

// 带超时
let result = mailbox_select([m1, m2], timeout=5.0)  // 5 秒超时
if result == null {
    print("超时")
}

// 中文别名
let result = 邮箱选择([m1, m2, m3])
```

**关键特性**：
- **快照语义**: spawn 时深拷贝所有变量（包括 SharedStore），Agent 间数据共享通过 Channel 消息显式传递
- **隔离环境**: 每个 spawned agent 运行在独立环境中
- **流式中断**: `ch.cancel()` 可以中断正在进行的流式 LLM 调用

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

---

## ⚠️ 使用 stdlib 时的注意事项：模块缓存

### 问题场景

在 Python REPL、Jupyter 或 Web 服务中使用 Helen stdlib 函数时，如果修改了导入的 `.helen` 模块文件，**修改不会自动生效**！

```python
# Python REPL 中
from helen.interpreter import Interpreter

interp = Interpreter()
interp.execute_file("my_utils.helen")  # 加载 v1
interp.execute("print(custom_function())")  # 使用 v1 的函数

# 修改 my_utils.helen...

interp.execute_file("my_utils.helen")  # ❌ 仍然是 v1！
```

### 根本原因

`ImportResolver` 使用内存缓存（`_cached_results`）加速重复导入：

```python
class ImportResolver:
    def __init__(self):
        self._cached_results: dict[str, ImportResult] = {}
```

### 快速解决方案

```python
# 方案 1: 每次新建 Interpreter（简单）
interp = Interpreter()
interp.execute_file("my_utils.helen")

# 方案 2: 手动清除缓存（高效）
interp.import_resolver._cached_results.clear()
interp.import_resolver._loaded.clear()
interp.execute_file("my_utils.helen")  # ✅ 重新加载

# 方案 3: 使用 CLI 开发（推荐）
# bash: helen my_program.helen  # 每次新进程，自动重新加载
```

### 调试 stdlib 时的技巧

```python
# 检查哪些文件被缓存了
print(f"Cached: {len(interp.import_resolver._cached_results)} files")

# 列出所有已加载的文件
for path in interp.import_resolver._loaded:
    print(f"  - {path}")
```

### 相关文档

- `wiki/runtime/import.md` — 完整的缓存机制说明
- `wiki/tutorial/08-modules.md` — 开发时的注意事项

---

## 📦 内置模板库

Helen 提供一组内置模板，涵盖常见 agent 模式。每个模板都是完整可运行的示例代码。

```bash
# 查看所有模板
helen template --list

# 查看具体模板
helen template simple_agent          # 简单 agent 调用
helen template spawn_channel         # spawn + Channel 并发
helen template shared_store          # SharedStore 数据交换
helen template context_object        # Context 对象聚合参数
helen template pipeline              # Agent 管道

# 复制模板到当前目录
helen template spawn_channel --copy my_worker.helen
```

**模板设计原则**：所有模板都遵循 **"调用者决定上下文"** 原则——agent 的所有信息都通过参数显式传递，不依赖隐式继承。

---

**最后更新**: 2026-07-20

