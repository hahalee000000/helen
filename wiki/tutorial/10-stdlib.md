# 教程 10: 标准库参考

> 186 个内置函数，覆盖 AI 应用开发的所有核心需求

## 概览

Helen 标准库提供 186 个内置函数，分为 9 大类别：

| 类别 | 函数数 | 功能 |
|------|--------|------|
| **Core** | 11 | 类型转换、通用操作 |
| **String** | 37 | 字符串处理、正则、文本分析、模板插值 |
| **Data** | 25 | JSON、HTML、CSV、Markdown、YAML、TOML、XML |
| **Collection** | 22 | 列表、字典、集合操作 |
| **Network** | 9 | HTTP 请求、URL 处理 |
| **Time** | 13 | 日期时间、格式化、运算 |
| **Math** | 15 | 数学运算、统计分析 |
| **File** | 16 | 文件读写、目录操作、临时文件 |
| **System** | 16 | 环境变量、进程管理、日志 |
| **Crypto** | 11 | 哈希、随机数 |
| **IO** | 5 | 流式输出控制 |

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
