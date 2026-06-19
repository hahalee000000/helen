---
name: helen-stdlib
description: "Helen 标准库使用指南 — 185 个内置函数的分类参考与示例"
version: 1.0.0
author: Helen Team
license: MIT
tags: [helen, stdlib, builtins, reference]
---

# Helen 标准库参考

Helen 标准库提供 **185 个内置函数**，覆盖 AI 应用开发的所有核心需求。

## 分类概览

| 类别 | 数量 | 代表函数 |
|------|------|----------|
| **Core** | 11 | `print`, `len`, `str`, `int`, `float`, `abs`, `min`, `max`, `range`, `type`, `isinstance` |
| **String** | 36 | `upper`, `lower`, `strip`, `split`, `join`, `replace`, `find`, `reverse`, `repeat`, `regex_match`, `regex_replace` |
| **Data** | 25 | `json_parse`, `json_stringify`, `yaml_parse`, `toml_parse`, `csv_parse`, `xml_parse`, `html_escape`, `url_encode`, `base64_encode` |
| **Collection** | 22 | `sort`, `reverse`, `unique`, `flatten`, `zip`, `map`, `filter`, `reduce`, `group_by`, `chunk`, `intersection` |
| **Network** | 9 | `http_get`, `http_post`, `http_put`, `http_delete`, `http_download`, `url_parse` |
| **Time** | 13 | `now`, `timestamp`, `date_format`, `date_parse`, `sleep`, `stopwatch_start`, `stopwatch_elapsed` |
| **Math** | 15 | `round`, `sqrt`, `floor`, `ceil`, `pow`, `log`, `sin`, `cos`, `random_int`, `random_float`, `mean`, `median`, `stddev` |
| **File** | 16 | `read_file`, `write_file`, `append_file`, `file_exists`, `list_dir`, `mkdir`, `copy_file`, `delete_file`, `file_size` |
| **System** | 16 | `env_get`, `env_set`, `shell_exec`, `process_id`, `platform`, `hostname`, `log_info`, `log_error` |
| **Crypto** | 11 | `hash_md5`, `hash_sha256`, `hash_sha512`, `hmac_sha256`, `uuid_generate`, `random_bytes` |
| **IO** | 5 | `read_line`, `prompt`, `format_table`, `progress_bar`, `terminal_width` |

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
```

### System（系统操作）

```helen
# 环境变量
let home = env_get("HOME")
env_set("MY_VAR", "value")
let all_env = env_list()  # 敏感值自动掩码

# Shell 命令
let result = shell_exec(["ls", "-la"])
print(result["stdout"])

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

## 安全注意事项

所有文件、网络、系统操作都经过**安全沙箱**保护：

- **路径验证**：阻止访问 `/etc/shadow`、`/proc` 等敏感路径
- **URL 过滤**：SSRF 防护，阻止私有 IP 访问
- **命令安全**：阻止 `rm -rf /`、`mkfs` 等危险命令
- **资源限制**：文件大小限制（读 16MB / 写 64MB）、HTTP 下载限制（100MB）

详见 `helen-security` 技能。
