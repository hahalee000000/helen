# 标准库 (Stdlib)

> 模块 M15 | `helen/stdlib/__init__.py` | **255 builtins** | 测试: `tests/stdlib/`

---

## 注册表

```python
class StdlibRegistry:
    @staticmethod
    def register(func: BuiltinFunction) -> None     # 注册函数
    @staticmethod
    def lookup(name: str) -> BuiltinFunction | None  # 按名查找
    @staticmethod
    def list_by_category(category: str) -> list[BuiltinFunction]  # 按分类列出
    @staticmethod
    def list_all() -> list[BuiltinFunction]         # 列出全部
    @property
    def names(self) -> list[str]                    # 函数名列表 (property)
```

### BuiltinFunction

```python
@dataclass
class BuiltinFunction:
    name: str           # 函数名
    description: str    # 描述
    signature: str      # 签名
    fn: Callable        # Python 实现
    category: str       # 分类: core/string/math/data/collection/network/time/file/system/crypto/io/test/quality
```

---

## 函数分类统计

| 类别 | 函数数 | 模块文件 |
|------|--------|----------|
| **Core** | 11 | `__init__.py` |
| **String** | 37 | `string.py` |
| **Data** | 25 | `data.py`, `data_formats.py` |
| **Collection** | 22 | `collection.py` |
| **Network** | 9 | `network.py` |
| **Time** | 13 | `time.py` |
| **Math** | 15 | `math_stats.py` |
| **File** | 18 | `file_advanced.py` |
| **System** | 18 | `system.py` |
| **Crypto** | 11 | `crypto.py` |
| **Test** | 14 | `test.py` |
| **Quality** | 4 | `quality.py` |
| **IO** | 5 | `__init__.py` |
| **Observability** | 4 | `observability.py` |
| **Context** | 2 | `context.py` |
| **Transcript** | 6 | `transcript.py` |
| **Media** | 12 | `media.py` |
| **Tools** | 24 | `tools.py` |
| **总计** | **255** | - |

---

## Core (11)

| 函数 | 签名 | 说明 |
|---|---|---|
| `print` | `print(*args)` → str | 打印值，返回字符串表示 |
| `len` | `len(value)` → int | 字符串长度/列表长度 |
| `str` | `str(value)` → str | 转换为字符串 |
| `int` | `int(value)` → int | 转换为整数 |
| `float` | `float(value)` → float | 转换为浮点数 |
| `abs` | `abs(value)` → float | 绝对值 |
| `min` | `min(*args)` → Any | 最小值 |
| `max` | `max(*args)` → Any | 最大值 |
| `range` | `range(start, stop?, step?)` → list[int] | 生成整数列表 |
| `type` | `type(value)` → str | 返回类型名称 |
| `isinstance` | `isinstance(value, type_name)` → bool | 类型检查 |

---

## String (37)

### 基础操作 (12)

| 函数 | 签名 | 说明 |
|---|---|---|
| `upper` | `upper(s)` → str | 转大写 |
| `lower` | `lower(s)` → str | 转小写 |
| `strip` | `strip(s)` → str | 去除两端空白 |
| `trim_prefix` | `trim_prefix(s, prefix)` → str | 去除前缀 |
| `trim_suffix` | `trim_suffix(s, suffix)` → str | 去除后缀 |
| `split` | `split(s, sep?)` → list[str] | 分割字符串 |
| `join` | `join(sep, items)` → str | 连接字符串列表 |
| `startswith` | `startswith(s, prefix)` → bool | 前缀检查 |
| `endswith` | `endswith(s, suffix)` → bool | 后缀检查 |
| `replace` | `replace(s, old, new)` → str | 替换子串 |
| `find` | `find(s, sub)` → int | 查找子串位置 |
| `substring` | `substring(s, start, end?)` → str | 提取子串 |

### 正则表达式 (5)

| 函数 | 签名 | 说明 |
|---|---|---|
| `regex_match` | `regex_match(pattern, s)` → dict? | 匹配开头 |
| `regex_search` | `regex_search(pattern, s)` → dict? | 搜索任意位置 |
| `regex_replace` | `regex_replace(pattern, s, replacement)` → str | 替换 |
| `regex_split` | `regex_split(pattern, s)` → list[str] | 分割 |
| `regex_findall` | `regex_findall(pattern, s)` → list[str] | 查找所有 |

### 文本分析 (8)

| 函数 | 签名 | 说明 |
|---|---|---|
| `tokenize` | `tokenize(text)` → list[str] | 分词 |
| `word_count` | `word_count(text)` → dict | 词频统计 |
| `levenshtein` | `levenshtein(s1, s2)` → int | 编辑距离 |
| `similarity` | `similarity(s1, s2)` → float | 相似度 |
| `remove_punctuation` | `remove_punctuation(text)` → str | 去除标点 |
| `normalize_whitespace` | `normalize_whitespace(text)` → str | 标准化空白 |
| `extract_urls` | `extract_urls(text)` → list[str] | 提取 URL |
| `extract_emails` | `extract_emails(text)` → list[str] | 提取邮箱 |

### 编码转换 (4)

| 函数 | 签名 | 说明 |
|---|---|---|
| `base64_encode` | `base64_encode(s)` → str | Base64 编码 |
| `base64_decode` | `base64_decode(s)` → str | Base64 解码 |
| `html_escape` | `html_escape(s)` → str | HTML 转义 |
| `html_unescape` | `html_unescape(s)` → str | HTML 反转义 |

### 字符串操作 (7)

| 函数 | 签名 | 说明 |
|---|---|---|
| `repeat` | `repeat(s, n)` → str | 重复 |
| `reverse` | `reverse(s)` → str | 反转 |
| `pad_left` | `pad_left(s, width, char?)` → str | 左填充 |
| `pad_right` | `pad_right(s, width, char?)` → str | 右填充 |
| `center` | `center(s, width, char?)` → str | 居中 |
| `count` | `count(s, sub)` → int | 计数 |
| `index` | `index(s, sub)` → int | 查找索引 |

---

## Data (25)

### JSON (4)

| 函数 | 签名 | 说明 |
|---|---|---|
| `json_parse` | `json_parse(text)` → Any | 解析 JSON |
| `json_stringify` | `json_stringify(value, indent?)` → str | 生成 JSON |
| `json_load` | `json_load(path)` → Any | 从文件加载 |
| `json_save` | `json_save(path, value, indent?)` → str | 保存到文件 |

### HTML (3)

| 函数 | 签名 | 说明 |
|---|---|---|
| `html_parse` | `html_parse(text)` → dict | 解析 HTML |
| `html_text` | `html_text(html)` → str | 提取文本 |
| `html_links` | `html_links(html)` → list[str] | 提取链接 |

### Markdown (2)

| 函数 | 签名 | 说明 |
|---|---|---|
| `markdown_to_html` | `markdown_to_html(text)` → str | 转 HTML |
| `markdown_extract_headings` | `markdown_extract_headings(text)` → list[dict] | 提取标题 |

### CSV (4)

| 函数 | 签名 | 说明 |
|---|---|---|
| `csv_parse` | `csv_parse(text, delimiter?)` → list[list[str]] | 解析 CSV |
| `csv_stringify` | `csv_stringify(rows, delimiter?)` → str | 生成 CSV |
| `csv_load` | `csv_load(path, delimiter?)` → list[list[str]] | 从文件加载 |
| `csv_save` | `csv_save(path, rows, delimiter?)` → str | 保存到文件 |

### YAML (4)

| 函数 | 签名 | 说明 |
|---|---|---|
| `yaml_parse` | `yaml_parse(text)` → Any | 解析 YAML |
| `yaml_stringify` | `yaml_stringify(value)` → str | 生成 YAML |
| `yaml_load` | `yaml_load(path)` → Any | 从文件加载 |
| `yaml_save` | `yaml_save(path, value)` → str | 保存到文件 |

### TOML (4)

| 函数 | 签名 | 说明 |
|---|---|---|
| `toml_parse` | `toml_parse(text)` → dict | 解析 TOML |
| `toml_stringify` | `toml_stringify(value)` → str | 生成 TOML |
| `toml_load` | `toml_load(path)` → dict | 从文件加载 |
| `toml_save` | `toml_save(path, value)` → str | 保存到文件 |

### XML (4)

| 函数 | 签名 | 说明 |
|---|---|---|
| `xml_parse` | `xml_parse(text)` → dict | 解析 XML |
| `xml_stringify` | `xml_stringify(value, root?)` → str | 生成 XML |
| `xml_load` | `xml_load(path)` → dict | 从文件加载 |
| `xml_save` | `xml_save(path, value, root?)` → str | 保存到文件 |

---

## Collection (22)

### 列表操作 (12)

| 函数 | 签名 | 说明 |
|---|---|---|
| `map` | `map(lst, fn)` → list | 映射 |
| `filter` | `filter(lst, fn)` → list | 过滤 |
| `reduce` | `reduce(lst, fn, initial?)` → Any | 归约 |
| `find_if` | `find_if(lst, fn)` → Any? | 查找 |
| `every` | `every(lst, fn)` → bool | 全部满足 |
| `some` | `some(lst, fn)` → bool | 部分满足 |
| `sort` | `sort(lst, compare?)` → list | 排序 |
| `unique` | `unique(lst)` → list | 去重 |
| `flatten` | `flatten(lst)` → list | 扁平化 |
| `chunk` | `chunk(lst, size)` → list[list] | 分块 |
| `zip` | `zip(*lists)` → list[tuple] | 压缩 |

### 字典操作 (6)

| 函数 | 签名 | 说明 |
|---|---|---|
| `keys` | `keys(dict)` → list | 所有键 |
| `values` | `values(dict)` → list | 所有值 |
| `entries` | `entries(dict)` → list[tuple] | 所有键值对 |
| `merge` | `merge(*dicts)` → dict | 合并 |
| `pick` | `pick(dict, keys)` → dict | 选择键 |
| `omit` | `omit(dict, keys)` → dict | 排除键 |

### 集合操作 (5)

| 函数 | 签名 | 说明 |
|---|---|---|
| `make_set` | `make_set(items)` → set | 创建集合 |
| `set_union` | `set_union(s1, s2)` → set | 并集 |
| `set_intersection` | `set_intersection(s1, s2)` → set | 交集 |
| `set_difference` | `set_difference(s1, s2)` → set | 差集 |
| `set_has` | `set_has(set, item)` → bool | 包含检查 |

---

## Network (9)

### HTTP 请求 (5)

| 函数 | 签名 | 说明 |
|---|---|---|
| `http_get` | `http_get(url, headers?)` → dict | GET 请求 |
| `http_post` | `http_post(url, data?, headers?)` → dict | POST 请求 |
| `http_put` | `http_put(url, data?, headers?)` → dict | PUT 请求 |
| `http_delete` | `http_delete(url, headers?)` → dict | DELETE 请求 |
| `http_download` | `http_download(url, path)` → str | 下载文件 |

### URL 处理 (4)

| 函数 | 签名 | 说明 |
|---|---|---|
| `url_parse` | `url_parse(url)` → dict | 解析 URL |
| `url_build` | `url_build(scheme, host, path?, query?)` → str | 构建 URL |
| `url_encode` | `url_encode(s)` → str | URL 编码 |
| `url_decode` | `url_decode(s)` → str | URL 解码 |

---

## Time (13)

### 时间获取 (3)

| 函数 | 签名 | 说明 |
|---|---|---|
| `now` | `now()` → str | 当前日期时间 |
| `time` | `time()` → float | Unix 时间戳 |
| `sleep` | `sleep(seconds)` → None | 暂停执行 |

### 日期操作 (10)

| 函数 | 签名 | 说明 |
|---|---|---|
| `date` | `date(year?, month?, day?)` → str | 创建/获取日期 |
| `datetime` | `datetime(...)` → str | 创建/获取日期时间 |
| `date_format` | `date_format(date_str, format_str)` → str | 格式化日期 |
| `date_parse` | `date_parse(date_str, format_str)` → str | 解析日期 |
| `date_add` | `date_add(date_str, days?, hours?, ...)` → str | 日期加法 |
| `date_diff` | `date_diff(date1, date2, unit?)` → float | 日期差值 |
| `date_year` | `date_year(date_str)` → int | 提取年份 |
| `date_month` | `date_month(date_str)` → int | 提取月份 |
| `date_day` | `date_day(date_str)` → int | 提取日期 |
| `date_weekday` | `date_weekday(date_str)` → int | 获取星期几 |

---

## Math (15)

### 基础数学 (4)

| 函数 | 签名 | 说明 |
|---|---|---|
| `round` | `round(value, ndigits=0)` → float | 四舍五入 |
| `sqrt` | `sqrt(value)` → float | 平方根 |
| `floor` | `floor(value)` → int | 向下取整 |
| `ceil` | `ceil(value)` → int | 向上取整 |

### 统计分析 (11)

| 函数 | 签名 | 说明 |
|---|---|---|
| `mean` | `mean(numbers)` → float | 算术平均 |
| `median` | `median(numbers)` → float | 中位数 |
| `mode` | `mode(numbers)` → list | 众数 |
| `variance` | `variance(numbers, population?)` → float | 方差 |
| `stddev` | `stddev(numbers, population?)` → float | 标准差 |
| `correlation` | `correlation(x, y)` → float | 相关系数 |
| `percentile` | `percentile(numbers, p)` → float | 百分位数 |
| `sum` | `sum(numbers)` → float | 求和 |
| `product` | `product(numbers)` → float | 求积 |
| `stats_min` | `stats_min(numbers)` → float | 最小值 |
| `stats_max` | `stats_max(numbers)` → float | 最大值 |

---

## File (18)

### 基础文件操作 (5)

| 函数 | 签名 | 说明 |
|---|---|---|
| `read_file` | `read_file(path)` → str | 读取文件 |
| `write_file` | `write_file(path, content)` → str | 写入文件 |
| `append_file` | `append_file(path, content)` → str | 追加文件 |
| `mkdir` | `mkdir(path)` → str | 创建目录 |
| `mkdir_p` | `mkdir_p(path)` → str | 递归创建目录 |

### 路径操作 (6)

| 函数 | 签名 | 说明 |
|---|---|---|
| `path_join` | `path_join(*parts)` → str | 拼接路径 |
| `path_dirname` | `path_dirname(path)` → str | 获取目录名 |
| `path_basename` | `path_basename(path)` → str | 获取文件名 |
| `path_exists` | `path_exists(path)` → bool | 检查存在 |
| `path_is_file` | `path_is_file(path)` → bool | 检查是文件 |
| `path_is_dir` | `path_is_dir(path)` → bool | 检查是目录 |

### 高级文件操作 (5)

| 函数 | 签名 | 说明 |
|---|---|---|
| `file_size` | `file_size(path)` → int | 文件大小 |
| `file_modified` | `file_modified(path)` → str | 修改时间 |
| `list_dir` | `list_dir(path, pattern?)` → list[str] | 列出目录 |
| `walk_dir` | `walk_dir(path)` → list[tuple] | 遍历目录树 |
| `copy_file` | `copy_file(src, dst)` → str | 复制文件 |
| `move_file` | `move_file(src, dst)` → str | 移动文件 |
| `delete_file` | `delete_file(path)` → str | 删除文件 |
| `delete_dir` | `delete_dir(path, recursive?)` → str | 删除目录 |

### 文件搜索 (2) (v1.15)

| 函数 | 签名 | 说明 |
|---|---|---|
| `glob_files` | `glob_files(path, pattern?)` → list[str] | 递归查找文件（glob 模式） |
| `grep_files` | `grep_files(path, pattern, regex?, case_sensitive?, max_results?)` → list[map] | 搜索文件内容 |
| `temp_file` | `temp_file(suffix?, prefix?, dir?)` → str | 创建临时文件 |
| `temp_dir` | `temp_dir(suffix?, prefix?, dir?)` → str | 创建临时目录 |

---

## System (18)

### 环境变量 (4)

| 函数 | 签名 | 说明 |
|---|---|---|
| `env_get` | `env_get(key, default?)` → str? | 获取环境变量 |
| `env_set` | `env_set(key, value)` → str | 设置环境变量 |
| `env_list` | `env_list()` → dict | 列出所有 |
| `env_delete` | `env_delete(key)` → str | 删除环境变量 |

### CLI 参数 (2)

| 函数 | 签名 | 说明 |
|---|---|---|
| `get_cli_args` | `get_cli_args()` → list[str] | 获取命令行参数（与 `argv` 相同） |
| `parse_cli_args` | `parse_cli_args(spec?)` → map | 结构化解析 CLI 参数 |

`parse_cli_args()` 支持两种模式：

- **自动模式**（无参数）：自动识别 `--flag`、`--key=value`、`--key value`、`-v` 短标志、位置参数（收集到 `_positional` 键）
- **Spec 模式**（传入 spec map）：按类型（`flag`/`string`/`int`/`float`）转换并应用默认值

> 另见：`argv` 预定义常量（[[toolchain/cli|CLI 文档]]）。

### 进程管理 (5)

| 函数 | 签名 | 说明 |
|---|---|---|
| `exec` | `exec(command, shell?, timeout?)` → dict | 执行命令 |
| `exec_async` | `exec_async(command, shell?)` → int | 异步执行 |
| `pid` | `pid()` → int | 当前进程 ID |
| `exit` | `exit(code?)` → None | 退出程序 |
| `kill` | `kill(pid, signal?)` → str | 发送信号 |

### 日志系统 (7)

| 函数 | 签名 | 说明 |
|---|---|---|
| `log_debug` | `log_debug(message)` → str | 调试日志 |
| `log_info` | `log_info(message)` → str | 信息日志 |
| `log_warn` | `log_warn(message)` → str | 警告日志 |
| `log_error` | `log_error(message)` → str | 错误日志 |
| `log_critical` | `log_critical(message)` → str | 严重日志 |
| `log_set_level` | `log_set_level(level)` → str | 设置级别 |
| `log_to_file` | `log_to_file(path)` → str | 输出到文件 |

---

## Crypto (11)

### 哈希函数 (6)

| 函数 | 签名 | 说明 |
|---|---|---|
| `md5` | `md5(text)` → str | MD5 哈希 |
| `sha1` | `sha1(text)` → str | SHA1 哈希 |
| `sha256` | `sha256(text)` → str | SHA256 哈希 |
| `sha512` | `sha512(text)` → str | SHA512 哈希 |
| `hmac_sha256` | `hmac_sha256(key, message)` → str | HMAC-SHA256 |
| `hash_file` | `hash_file(path, algorithm?)` → str | 文件哈希 |

### 随机函数 (5)

| 函数 | 签名 | 说明 |
|---|---|---|
| `random` | `random()` → float | 随机浮点数 |
| `randint` | `randint(min, max)` → int | 随机整数 |
| `choice` | `choice(items)` → Any | 随机选择 |
| `shuffle` | `shuffle(items)` → list | 随机打乱 |
| `sample` | `sample(items, k)` → list | 随机采样 |

---

## IO (5)

| 函数 | 签名 | 说明 |
|---|---|---|
| `stream_print` | `stream_print(text)` → str | 无换行打印 |
| `stream_clear` | `stream_clear()` → str | 清除当前行 |
| `progress_bar` | `progress_bar(current, total, width?)` → str | 进度条 |
| `stream_cursor_up` | `stream_cursor_up(n?)` → str | 光标上移 |
| `stream_cursor_down` | `stream_cursor_down(n?)` → str | 光标下移 |

---

## Media (12) (v1.17)

| 函数 | 签名 | 说明 |
|---|---|---|
| `media` | `media(source, type?)` → MediaPart | 从文件路径或 URL 创建媒体 |
| `media_base64` | `media_base64(data, mime, type?)` → MediaPart | 从 base64 数据创建媒体 |
| `is_media` | `is_media(value)` → bool | 检查是否为 MediaPart |
| `media_type` | `media_type(value)` → str? | 获取媒体类型 |
| `to_openai_parts` | `to_openai_parts(parts)` → list[map] | 转 OpenAI content_parts 格式 |
| `to_claude_parts` | `to_claude_parts(parts)` → list[map] | 转 Claude content_blocks 格式 |
| `to_gemini_parts` | `to_gemini_parts(parts)` → list[map] | 转 Gemini inline_data 格式 |
| `media_to_base64` | `media_to_base64(part)` → str | 任意 source → 纯 base64 |
| `save_media` | `save_media(part, path?)` → str | 保存媒体到文件 |
| `is_image` | `is_image(value)` → bool | 是否为图片 MediaPart |
| `is_video` | `is_video(value)` → bool | 是否为视频 MediaPart |
| `is_audio` | `is_audio(value)` → bool | 是否为音频 MediaPart |

---

## 自动注册

```python
def _register_builtins():
    """import helen.stdlib 时自动执行。"""
    registry = StdlibRegistry
    registry.register(BuiltinFunction("print", "...", "print(*args)", _print, "core"))
    # ... 注册全部 195 个函数
```

---

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

---

## 使用示例

```helen
main {
    // Core
    let len = len("hello")          # 5
    let nums = range(1, 5)          # [1, 2, 3, 4]
    let t = type(42)                # "int"

    // String
    let upper = upper("hello")      # "HELLO"
    let parts = split("a,b,c", ",") # ["a", "b", "c"]
    let joined = join("-", parts)   # "a-b-c"
    
    // Regex
    let matches = regex_findall(r"\d+", "a1b2c3")  # ["1", "2", "3"]

    // Data
    let data = json_parse('{"name": "Alice"}')
    let yaml_data = yaml_load("config.yaml")

    // Collection
    let doubled = map([1, 2, 3], x => x * 2)  # [2, 4, 6]
    let filtered = filter([1, 2, 3, 4], x => x > 2)  # [3, 4]

    // Network
    let response = http_get("https://api.example.com")
    
    // Time
    let today = date()              # "2026-06-18"
    let tomorrow = date_add(today, days=1)

    // Math
    let avg = mean([1, 2, 3, 4, 5])  # 3.0
    
    // File
    let content = read_file("data.txt")
    let files = list_dir(".", pattern="*.helen")
    
    // System
    let path = env_get("PATH")
    log_info("Processing started")
    
    // CLI 参数
    let args = argv                       // 预定义 const list<str>
    let parsed = parse_cli_args()         // 自动解析
    // 或带 spec: parse_cli_args({"verbose": {"type": "flag", "default": false} })
    
    // Crypto
    let hash = sha256("hello")
    let rand = randint(1, 100)
}
```
