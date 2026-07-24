---
name: helen-stdlib
description: "Helen Standard Library Guide — Categorized reference and examples for 200+ built-in functions"
version: 1.16.0
author: Helen Team
license: MIT
metadata:
  hermes:
    tags: [helen, stdlib, builtins, reference]
---

# Helen Standard Library Reference

Helen's standard library provides **203 built-in functions**, covering all core needs for AI application development.

## Category Overview

| Category | Count | Representative Functions |
|----------|--------|--------------------------|
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

## Multilingual stdlib (v1.10)

Helen's stdlib supports multilingual function names. Every stdlib function has an English canonical name and localized aliases, all loaded at startup.

### Chinese stdlib Aliases

Helen has 230+ built-in Chinese aliases covering all stdlib categories. Common examples:

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

For the complete list, see `helen/stdlib/locales/zh.py`.

### Usage Examples

```helen
// Use Chinese stdlib function names directly (no import or alias needed)
函数 数据处理() {
    定义 原始数据 = [3, 1, 4, 1, 5, 9, 2, 6]
    定义 排序后 = 排序(原始数据)
    定义 去重后 = 去重(排序后)
    返回 长度(去重后)
}

// Mixing Chinese and English is also perfectly legal
函数 混合使用() {
    let data = [1, 2, 3]
    let sorted = 排序(data)     // English variables + Chinese function
    return len(sorted)
}
```

### Custom Aliases

```helen
alias len as 我的长度
别名 print as 输出
```

### Design Principles

- **Single mechanism**: stdlib aliases and user `alias` use the same Environment binding
- **Full loading**: All locale alias tables are registered at startup, not filtered by locale
- **locale only affects display**: `locale: zh` in `~/.helen/config.yaml` only affects the language of docs/LSP/error messages
- **Extending to new languages**: Adding a new language only requires creating `helen/stdlib/locales/<code>.py`

## Common Function Examples

### Core

```helen
# Type conversion
let num = int("42")           # string → integer
let text = str(3.14)          # float → string
let flt = float("2.5")        # string → float

# Length and range
let length = len([1, 2, 3])   # 3
let items = range(0, 10, 2)   # [0, 2, 4, 6, 8]

# Math basics
let maximum = max(1, 2, 3)    # 3
let minimum = min(1, 2, 3)    # 1
let absolute = abs(-42)       # 42

# Type checking
if isinstance(value, str) {
    print("It's a string")
}
```

### String

```helen
# Case conversion
let upper = upper("hello")    # "HELLO"
let lower = lower("WORLD")    # "world"

# Split and join
let parts = split("a,b,c", ",")  # ["a", "b", "c"]
let joined = join(["a", "b"], "-")  # "a-b"

# Find and replace
let found = find("hello world", "world")  # 6
let replaced = replace("foo bar", "foo", "baz")  # "baz bar"

# Regular expressions
if regex_match("hello123", r"\d+") {
    print("Contains digits")
}
let cleaned = regex_replace("a1b2c3", r"\d", "")  # "abc"

# Whitespace handling
let trimmed = strip("  hello  ")  # "hello"
let padded = pad_start("42", 5, "0")  # "00042"

# Float formatting
let formatted1 = format_float(8.5, 1)      # "8.5"
let formatted2 = format_float(7.857, 2)    # "7.86" (rounded)
let formatted3 = format_float(3.14159, 3)  # "3.142"

# Chinese aliases
let formatted = 格式化浮点(8.5, 1)  # "8.5"
```

### Data

```helen
# JSON
let data = json_parse('{"name": "Helen", "version": 1}')
let json = json_stringify(data, indent=2)

# YAML
let config = yaml_parse("key: value\nlist:\n  - item1\n  - item2")

# CSV
let rows = csv_parse("name,age\nAlice,30\nBob,25")
# [["name", "age"], ["Alice", "30"], ["Bob", "25"]]

# URL encoding
let encoded = url_encode("hello world&foo=bar")
let decoded = url_decode(encoded)

# Base64
let encoded = base64_encode("secret data")
let decoded = base64_decode(encoded)
```

### Collection

```helen
# Sort and deduplicate
let sorted = sort([3, 1, 4, 1, 5])  # [1, 1, 3, 4, 5]
let unique_items = unique([1, 2, 2, 3])  # [1, 2, 3]

# Map and filter
let doubled = map([1, 2, 3], x => x * 2)  # [2, 4, 6]
let evens = filter([1, 2, 3, 4], x => x % 2 == 0)  # [2, 4]

# Reduce
let sum = reduce([1, 2, 3, 4], (acc, x) => acc + x, 0)  # 10

# Group by
let grouped = group_by(users, u => u["role"])
# {"admin": [...], "user": [...]}

# Chunk
let chunks = chunk([1, 2, 3, 4, 5], 2)
# [[1, 2], [3, 4], [5]]

# Set operations
let common = intersection([1, 2, 3], [2, 3, 4])  # [2, 3]
```

### Network

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

# Download file
http_download("https://example.com/file.pdf", "/tmp/file.pdf")
```

### Time

```helen
# Current time
let now_ts = now()                    # Unix timestamp (seconds)
let current = time()                  # Current time (datetime object)

# Formatting
let formatted = date_format(now(), "%Y-%m-%d %H:%M:%S")
# "2026-06-19 17:30:00"

# Parsing
let parsed = date_parse("2026-06-19", "%Y-%m-%d")

# Date arithmetic
let tomorrow = date_add(now(), days=1)
let diff = date_diff(date1, date2, "days")

# Sleep
sleep(1.5)  # Sleep for 1.5 seconds

# Stopwatch (high precision)
let sw = stopwatch_start()
let elapsed = stopwatch_elapsed(sw)   # Seconds (float, high precision)
print("Elapsed: " + str(elapsed) + " seconds")
```

### Math

```helen
# Basic math
let rounded = round(3.14159, 2)   # 3.14
let root = sqrt(16)               # 4.0
let ceiling = ceil(3.2)           # 4
let flooring = floor(3.8)         # 3
let power = pow(2, 10)            # 1024

# Logarithms
let natural = log(2.718)          # Natural log (ln)
let base2 = log2(8)               # 3 (2^3 = 8)
let base10 = log10(100)           # 2 (10^2 = 100)
let exponential = exp(1)          # 2.718... (e^1)

# Trigonometric functions (radians)
let cosine = cos(0)               # 1
let sine = sin(3.14159 / 2)       # 1
let tangent = tan(0)              # 0
let angle = acos(0.5)             # 1.047... (60°)
let angle2 = asin(0.5)            # 0.523... (30°)
let angle3 = atan(1)              # 0.785... (45°)
let angle4 = atan2(1, 1)          # 0.785... (45°, y/x)

# Statistics
let avg = mean([1, 2, 3, 4, 5])   # 3.0
let mid = median([1, 2, 3, 4, 5]) # 3
let std = stddev([1, 2, 3, 4, 5]) # 1.414...
let total = sum([1, 2, 3, 4, 5])  # 15
let prod = product([1, 2, 3, 4])  # 24

# Random numbers
let rand = random()               # Random float between 0 and 1
let rand_int = randint(1, 100)    # Random integer between 1 and 100
let item = choice([1, 2, 3, 4])   # Random selection
let shuffled = shuffle([1, 2, 3]) # Random shuffle
```

### File

```helen
# Read/write files
let content = read_file("/path/to/file.txt")
write_file("/path/to/output.txt", "Hello, World!")
append_file("/path/to/log.txt", "New log entry\n")

# File info
if path_exists("/path/to/file.txt") {
    let size = file_size("/path/to/file.txt")
    print("File size: " + str(size) + " bytes")
}

# Directory operations
let files = list_dir("/path/to/dir")
mkdir("/path/to/new/dir")
mkdir_p("/path/to/deep/nested/dir")  # Recursive creation
copy_file("/src/file.txt", "/dst/file.txt")
delete_file("/path/to/file.txt")

# File search
let py_files = glob_files("src", "*.py")       # Recursively find all Python files
let md_files = glob_files("docs", "**/*.md")   # Use ** for explicit recursion

# Search file content (literal)
let matches = grep_files("src/", "TODO")
# [{"file": "main.py", "line": 42, "text": "    # TODO: fix this"}]

# Search file content (regex)
let functions = grep_files("src/", "def \\w+\\(", regex=true)

# Case-insensitive search
let errors = grep_files("logs/", "error", case_sensitive=false)
```

### System

```helen
# Environment variables
let home = env_get("HOME")
env_set("MY_VAR", "value")
let all_env = env_list()  # Sensitive values are auto-masked

# CLI arguments (predefined constant argv + parsing functions)
# Command line: helen tool.helen --verbose --output=json input.txt
print(argv)  # ["--verbose", "--output=json", "input.txt"]

let parsed = parse_cli_args()           # Auto-parse
# {verbose: true, output: "json", _positional: ["input.txt"]}

let spec = {
    "verbose": {"type": "flag", "default": false},
    "output": {"type": "string", "default": "text"}
}
let config = parse_cli_args(spec)       # Structured parsing (with types + defaults)

# Shell commands (default shell=true, uses /bin/bash, supports full shell syntax)
let result = shell_exec("ls -la")
let result = shell_exec("mkdir -p ~/project/{src,tests,contracts}")
let result = shell_exec("cat file.txt | grep pattern | wc -l")
print(result["output"])

# Safe mode: use shell=false when handling untrusted input to prevent shell injection
let result = shell_exec("echo " + user_input, shell=false)

# System info
let pid = pid()                   # Process ID
let os = platform()               # "linux", "darwin", "windows"
let host = hostname()             # Hostname
let py_ver = python_version()     # Python version
let cpus = cpu_count()            # CPU core count
let mem = memory_info()           # {total, available, used, percent}

# Logging
log_info("Application started")
log_error("Something went wrong", category="app")
```

### Crypto

```helen
# Hashing
let md5_hash = md5("data")
let sha256_hash = sha256("data")
let sha512_hash = sha512("data")

# HMAC
let sig = hmac_sha256("message", "secret_key")

# Random numbers
let rand = random()               # Random float between 0 and 1
let rand_int = randint(1, 100)    # Random integer
let item = choice([1, 2, 3])      # Random selection

# UUID
let id = uuid_generate()          # "550e8400-e29b-41d4-a716-446655440000"
let nil_id = uuid_nil()           # "00000000-0000-0000-0000-000000000000"
let parsed = uuid_from_string("550E8400-E29B-41D4-A716-446655440000")

# Random bytes
let bytes = random_bytes(16)      # 32-character hex string
let hex_str = random_hex(32)
let b64 = random_base64(16)       # Base64-encoded random data
```

## Observability

AI-native observability functions providing structured debugging context for AI agents.

```helen
# debug() — Structured debug output to stderr
debug("variable value", x)
# Output: [DEBUG] variable value {"value": 42}
debug("checkpoint reached")

# trace_on() / trace_off() — Enable/disable execution tracing
trace_on()
let result = compute_something()
trace_off()

# get_trace() — Get recent execution trace records
let trace = get_trace(10)
```

**Design features**: Zero overhead by default (no impact when tracing is off), JSON structured output (AI-consumable), automatic call stack + scope variable capture on errors/assertions, `llm act` automatically records call details.

## Context (Context Management)

Functions for managing LLM conversation context, used for context control in long-running agent conversations.

```helen
# Basic operations
clear_context()                       # Clear context, returns {cleared_messages, cleared_tokens}
compress_context("auto")              # Compress context
# Strategies: "auto" | "summarize" (LLM summary) | "truncate" | "none" | "graduated"

# Inspection
context_stats()                       # {message_count, total_tokens, system_tokens, ...}
context_usage()                       # 0.0-1.0 usage ratio
let usage = context_usage()
if usage > 0.8 { compress_context("auto") }
get_message(uuid)                     # Get a single message

# Fine-grained Mutation
insert_message("system", "Important note", 0)  # Insert message (position optional)
replace_message(uuid, "New content")            # Replace message content
delete_message(uuid)                            # Delete message
pin_message(uuid) / unpin_message(uuid)         # Pin message (immune to compression)

# Working Memory — Auto-tracks active files, decisions, TODOs, error history
working_memory_set("current_file", "main.py")
working_memory_set("decision", "Use JWT authentication")
working_memory_get("current_file")       # "main.py"
working_memory_remove("todo")
working_memory_clear()

# Runtime Config
set_compression_strategy("graduated")    # Dynamically adjust compression strategy
set_context_window(128000)               # Set context window size
set_working_memory_enabled(true)
set_cache_aware(true)                    # Enable cache-aware compression (improves cache hit rate)
get_context_config()                     # {strategy, window, working_memory, cache_aware}

# Query
search_context("authentication")         # [{uuid, role, content}, ...]
context_slice(-5)                        # Last 5 messages
context_slice(0, 10)                     # First 10 messages

# Multi-Agent Transfer
export_context()                         # Export [{role, content}, ...]
import_context(messages)                 # Import into current session
fork_context()                           # Create independent copy

# Cross-session restore (v1.21+)
restore_context("session_xxx")           # Restore active context from old transcript
# After restore, LLM can see old session messages on the next llm act call
# ⚠️ Only restores messages, not working_memory or config (those need manual restore)

# vs resume_session:
# - restore_context: Restores active context, supports filtering by agent/invocation
# - resume_session:  Imports all messages into current new session

# Lifecycle Hooks
on_compression(fn(stats) {
    print("About to compress: " + str(stats["token_count"]) + " tokens")
})
on_context_overflow(fn(stats) {
    compress_context("truncate")
})
```

**REPL debug commands**: `:trace on/off/show [n]`, `:last_error` (structured JSON), `:llm_log [n]` (LLM call audit log)

**assert statement**:
```helen
assert x > 0
assert x > 0, "x must be positive"
# Assertion failure throws AssertionError, which can be caught with try-catch
```

## Test (Testing Framework)

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
# helen test calc.helen              # Run tests
# helen test calc.helen --watch      # Watch mode
# helen test calc.helen --filter "add"  # Filter
```

### Expect Chain API

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

`before_all`/`after_all`/`before_each`/`after_each` hooks are available.

## Quality (Quality Assessment)

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

### 7 Assessment Dimensions

| Dimension | Weight | Assesses |
|-----------|:------:|----------|
| Architecture | 20% | Function length, complexity, nesting depth |
| Code Quality | 15% | Comment ratio, average function length |
| Security | 20% | Dangerous pattern detection |
| Test Coverage | 15% | Test file existence |
| Documentation | 10% | Docstring coverage |
| Maintainability | 10% | Long functions, high-complexity functions |
| Engineering Standards | 10% | Naming conventions, file size |

## Transcript (Session Records)

TranscriptStore (v1.16) — SSOT, persistent storage for all conversation messages.

### Session Management

```helen
# get_session_id() — Current session ID
let session = get_session_id()  # "session_{timestamp}_{uuid8}"

# get_session_meta() (v1.23.3) — Session metadata (recorded at startup)
let meta = get_session_meta()
# {argv, timestamp, helen_version, python_version, cwd, session_scope}

# list_sessions(scope?) — List all sessions
let sessions = list_sessions()
# [{session_id, created_at, modified_at, size_bytes, message_count, scope}, ...]
let global_sessions = list_sessions("global")
let project_sessions = list_sessions("project")

# Session directory management
let info = get_session_dir()    # {session_dir, scope, project_dir}
set_session_dir("/custom/path")
```

**Runtime isolation principles**:
- Multiple calls to `get_session_id()` within the same process → Same ID
- Restart program → New Interpreter → New session_id
- `spawn`-created agent → New Interpreter → New session_id (independent transcript)
- Normal agent call (same process) → Shared session_id, distinguished by `invocation_id`
- Cross-runtime inheritance must be explicit: `resume_session(parent_sid)` or `Channel.send(sid)`

### Replay, Export & Search

```helen
# Replay
replay_transcript()                              # Current session
replay_transcript("session_123", true)           # Include compressed messages
replay_transcript(agent="A", last_only=true)     # Filter by agent
replay_transcript(invocation_id="inv_1", include_subtree=true)

# Export
export_transcript(null, "json")                  # Export current as JSON
export_transcript(null, "text")                  # Export as plain text
export_transcript("full.json", "json", include_spawned=true)  # Include spawned

# Search (v1.22+) — Search persisted transcript (unlike search_context which searches current context)
search_transcript("auth bug")                    # Basic search
search_transcript("database", scope="all", limit=10)  # Across all sessions
search_transcript("fix.*bug", regex=true)        # Regex
search_transcript("TODO", role="user")           # Filter by role
search_transcript("error", include_spawned=true) # Cross-spawn search (v1.23.7)

# Typical search → restore context workflow
let matches = search_transcript("auth bug", scope="all")
if len(matches) > 0 {
    restore_context(matches[0]["session_id"])
}
```

### Invocation Tree Query (v1.22+)

```helen
# Each agent main {} execution is an invocation with a unique invocation_id
list_invocations()                               # List all invocations
list_invocations(agent="Researcher", limit=10)   # Filter by agent

get_invocation("inv_xxx")                        # Query single
# {agent_name, message_count, parent_invocation_id, ...}

get_invocation_tree()                            # Full call tree (nested structure)
invocation_path("inv_3")                         # "top -> A -> C"

# Chinese aliases
列出调用()
获取调用("inv_xxx")
获取调用树()
调用路径("inv_3")
```

**Context isolation (v1.22/v1.23)**: Each agent main {} execution is an independent invocation; the LLM can only see messages from the current invocation.

### Session Restore & Cleanup

```helen
# Restore
resume_session("session_123")                    # Import historical messages into current session

# Delete
delete_session("session_123")                    # Default: cascade delete spawned
delete_session("session_123", cascade=false)     # Only delete main session
delete_current_session(true)                     # Delete current session

# Cleanup
cleanup_sessions(keep_count=10)                  # Keep the most recent 10
cleanup_sessions(older_than_days=30)             # Delete those older than 30 days
cleanup_sessions(keep_count=5, older_than_days=7, cascade=false)

# Compression audit
get_compression_audit()
# [{timestamp, strategy, before_tokens, after_tokens, boundary_uuid}, ...]
```

### Spawn Relationship Tracking (v1.23.7)

```helen
get_spawned_sessions()                           # Direct child sessions
get_spawn_tree()                                 # Full spawn tree
replay_full_session()                            # Aggregate main session + all spawned
```

### Session Scope (v1.20)

- `global`: `~/.helen/sessions/`
- `project`: `.helen/sessions/` (when `.helen/`, `helen.yaml`, or `helen.toml` is detected)
- `auto` (default): Auto-detect project directory, otherwise global

### Startup Session Recovery (v1.24+)

```bash
helen --session=session_xxx file.helen    # Start with specified session
helen --resume-latest file.helen          # Auto-restore most recent session
helen repl --resume-latest                # REPL shorthand: -r
```

```python
# Python API
from helen.interpreter import Interpreter
interp = Interpreter(session_id="session_xxx")
```

| Feature | `--session` (startup) | `resume_session()` (runtime) |
|---------|----------------------|------------------------------|
| Timing | Before interpreter starts | During program execution |
| Behavior | Directly reuses specified session | Imports historical messages into current new session |
| transcript | One file | Two files |

## Media (Media/Multimodal)

v1.17 introduces multimodal support; `MediaPart` is a first-class data type.

```helen
# Creation
let img = media("/path/to/image.png")          # File path or URL
let video = media("https://example.com/video.mp4")
let audio = media("/path/to/audio.mp3", "audio")  # Explicitly specify type
let base64_img = media_base64("iVBORw0KGgo...", "image/png")

# Inspection
is_media(value)                                # Whether it's a MediaPart
media_type(img)                                # "image" | "video" | "audio"
is_image(img) / is_video(video) / is_audio(audio)

# Format adapters
to_openai_parts([img, video])                  # [{type: "image_url", ...}]
to_claude_parts([img])                         # [{type: "image", source: {...}}]
to_gemini_parts([img])

# Utilities
media_to_base64(img)                           # Convert to base64 string
save_media(img, "/path/to/save.png")           # Save to file

# Usage in llm act (callbacks as adapters)
llm act "Analyze this image"
    media("/path/to/image.png")
    on_media fn(parts, provider) {
        if provider == "claude" { return to_claude_parts(parts) }
        return to_openai_parts(parts)
    }
```

## LLM (LLM Call Control)

Control ongoing LLM streaming calls.

```helen
let call_id = current_llm_call_id()     # string | null
cancel_llm_call(call_id)
cancel_all_llm_calls()                  # Returns count of cancelled calls

# Chinese aliases
取消大模型调用(call_id)
当前大模型调用id()
取消所有大模型调用()
```

Used in `on_chunk` callbacks to detect termination conditions, Ctrl+C interruption, and timeout control.

## Concurrency

v1.18 Channel-based message-passing concurrency model.

```helen
agent Worker(task: str) {
    main {
        # Execute task...
        return "Result"
    }
}

# spawn returns a Channel (mailbox)
let ch = spawn Worker("Task 1")

# Channel methods
ch.send("message")              # Send message
let msg = ch.receive()          # Blocking receive
let maybe = ch.try_receive()    # Non-blocking receive (returns null if no message)
ch.cancel()                     # Cancel (interrupts streaming LLM call)
ch.close()                      # Close channel
ch.is_closed()                  # Check if closed

# Chinese aliases: 发送(), 接收(), 尝试接收(), 取消(), 关闭(), 已关闭()

# mailbox_select — Multi-channel select (race mode: first to complete wins)
let m1 = spawn StrategyA()
let m2 = spawn StrategyB()
let m3 = spawn StrategyC()
let result = mailbox_select([m1, m2, m3])  # {endpoint: Channel, message: "..."}

# With timeout
let result = mailbox_select([m1, m2], timeout=5.0)  # Returns null on timeout
if result == null { print("Timeout") }

# Chinese aliases
let result = 邮箱选择([m1, m2, m3])
```

**Key features**: Snapshot semantics (spawn deep-copies all variables including SharedStore), isolated environment, streaming interrupt (`ch.cancel()`). Inter-agent data sharing is done explicitly through Channel messages.

## Exception Handling (v.9+)

Python exceptions are automatically wrapped as `RuntimeError`, with format `"Python <Type Name>: <Original Message>"`:

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

Python exception types can be distinguished by the message prefix. Existing Helen exceptions (such as `TimeoutError`) retain their original types unchanged.

## Module Cache (Python REPL/Jupyter)

`ImportResolver` uses an in-memory cache (`_cached_results`). After modifying `.helen` files, you need to manually clear it:

```python
# Option 1: Create a new Interpreter each time (simple)
interp = Interpreter()

# Option 2: Manually clear cache (efficient)
interp.import_resolver._cached_results.clear()
interp.import_resolver._loaded.clear()

# Debug: Check cache status
print(f"Cached: {len(interp.import_resolver._cached_results)} files")
for path in interp.import_resolver._loaded:
    print(f"  - {path}")
```

Recommended approach: Use the CLI for development (`helen my_program.helen`); each new process automatically reloads.

## Built-in Template Library

```bash
helen template --list                  # View all templates
helen template simple_agent            # View template content
helen template spawn_channel --copy my_worker.helen  # Copy to current directory
```

Templates: `simple_agent`, `spawn_channel`, `shared_store`, `context_object`, `pipeline`. All templates follow the "Caller Decides Context" principle — all agent information is passed explicitly through parameters.

---

**Last updated**: 2026-07-24

## Related Skills

- **helen-syntax** — Helen syntax reference (keywords, types, expressions)
- **helen-agent-patterns** — Agent design patterns
- **helen-agent-collaboration** — Multi-agent collaboration patterns
- **helen-testing** — Testing framework usage guide
