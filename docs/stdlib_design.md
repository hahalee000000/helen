# Helen 标准库设计文档

> 版本: v1.0 | 状态: 设计阶段 | 最后更新: 2026-06-18

## 目录

- [概述](#概述)
- [设计原则](#设计原则)
- [标准库模块清单](#标准库模块清单)
- [优先级排序](#优先级排序)
- [实施计划](#实施计划)
- [参考与对比](#参考与对比)

---

## 概述

Helen 是一门 AI-native DSL（领域特定语言），主要用于：
- 处理网络资料（文本、图片、语音、视频）
- 构建 AI Agent 和 LLM 应用
- 自动化任务和工作流

标准库设计目标：
1. **文字处理为核心**：AI 主要处理文本，这是重点
2. **网络操作内置**：获取网上资料是高频需求
3. **AI 功能差异化**：LLM/Agent 是核心竞争力
4. **多媒体通过 FFI**：图片/语音/视频通过 Python 生态
5. **精简实用**：避免重复造轮子，保持语言简洁

---

## 设计原则

### 三层架构

```
┌─────────────────────────────────────┐
│  第三层：AI/LLM 功能（差异化）       │
│  - Agent 系统                        │
│  - LLM 调用（act/stream/if）         │
│  - 向量操作、记忆系统                │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  第二层：核心 stdlib（Helen 原生）    │
│  - 文件 I/O、路径操作                │
│  - 字符串处理、集合操作              │
│  - 网络通信、数据格式                │
│  - 基础数学、时间日期                │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  第一层：Python FFI（桥接生态）       │
│  - HTTP 高级功能（requests）         │
│  - 数据科学（numpy, pandas）         │
│  - 多媒体处理（PIL, opencv）         │
│  - 专业领域库（40 万+ Python 包）    │
└─────────────────────────────────────┘
```

### 内置 vs FFI 决策标准

| 类别 | 策略 | 理由 |
|------|------|------|
| 文件 I/O | ✅ 内置 | 高频操作，签名简单 |
| 路径操作 | ✅ 内置 | 基础功能，零依赖 |
| 字符串处理 | ✅ 内置 | 日常必需，AI 核心 |
| 网络请求 | ✅ 内置 | 获取资料的核心 |
| 数据解析 | ✅ 内置 | JSON/HTML 是基础 |
| AI/LLM | ✅ 内置 | 差异化优势 |
| HTTP 高级功能 | ❌ FFI | 复杂协议，Python 成熟 |
| 数据科学 | ❌ FFI | 专业领域，Python 无可替代 |
| 多媒体处理 | ❌ FFI | 底层优化，Python 绑定高效 |
| 数据库驱动 | ❌ FFI | 驱动复杂，Python 实现稳定 |

### 参考的主流语言

| 语言 | 标准库特点 | Helen 借鉴 |
|------|-----------|-----------|
| **Python** | "batteries included"，丰富实用 | 文件、路径、字符串操作 |
| **JavaScript** | 简洁核心 + npm 生态 | 集合操作（map/filter/reduce） |
| **Go** | 标准库强大，网络内置 | HTTP 客户端、路径操作 |
| **Rust** | 核心 stdlib + crates.io | 类型安全、错误处理 |
| **Julia** | 科学计算 + PyCall.jl | FFI 桥接策略 |

---

## 标准库模块清单

### 1. Core（核心模块）

基础类型操作和控制流辅助。

#### 已实现 ✅

```helen
// 类型转换
str(value)           // 转字符串
int(value)           // 转整数
float(value)         // 转浮点
bool(value)          // 转布尔

// 类型检查
type(value)          // 获取类型名
isinstance(value, type_name)  // 类型检查

// 通用操作
len(value)           // 长度
abs(value)           // 绝对值
min(*args)           // 最小值
max(*args)           // 最大值
range(start, stop?, step?)    // 整数序列

// 输出
print(*args)         // 打印
input(prompt?)       // 用户输入
```

#### 待实现 ❌

```helen
// 类型转换
list(value)          // 转列表
dict(value)          // 转字典
```

**状态**：✅ 基本完成

---

### 2. String（字符串处理）⭐ 重点

AI 文字处理的核心模块。

#### 2.1 基础操作

**已实现 ✅**

```helen
upper(s)             // 转大写
lower(s)             // 转小写
strip(s)             // 去除空白
split(s, sep?)       // 分割
join(sep, items)     // 拼接
startswith(s, prefix)  // 前缀检查
endswith(s, suffix)    // 后缀检查
replace(s, old, new)   // 替换
find(s, sub)           // 查找位置
substring(s, start, end?)  // 子串提取
trim_prefix(s, prefix)     // 移除前缀
trim_suffix(s, suffix)     // 移除后缀
```

**待实现 ❌**

```helen
repeat(s, n)         // 重复字符串
reverse(s)           // 反转字符串
pad_left(s, width, char?)   // 左填充
pad_right(s, width, char?)  // 右填充
center(s, width, char?)     // 居中
count(s, sub)        // 计数子串
index(s, sub)        // 查找索引（未找到抛异常）
```

#### 2.2 正则表达式 ❌ 待实现

```helen
regex_match(pattern, s)      // 匹配
regex_search(pattern, s)     // 搜索
regex_replace(pattern, s, replacement)  // 替换
regex_split(pattern, s)      // 分割
regex_findall(pattern, s)    // 查找所有
```

#### 2.3 文本分析 ❌ 待实现

```helen
// 分词
tokenize(text)               // 简单分词
word_count(text)             // 词频统计

// 相似度
levenshtein(s1, s2)          // 编辑距离
similarity(s1, s2)           // 相似度（0-1）

// 文本清洗
remove_punctuation(text)     // 去除标点
normalize_whitespace(text)   // 标准化空白
extract_urls(text)           // 提取 URL
extract_emails(text)         // 提取邮箱
```

#### 2.4 编码转换 ❌ 待实现

```helen
encode(s, encoding?)         // 编码（utf-8, gbk 等）
decode(bytes, encoding?)     // 解码
base64_encode(s)             // Base64 编码
base64_decode(s)             // Base64 解码
url_encode(s)                // URL 编码
url_decode(s)                // URL 解码
html_escape(s)               // HTML 转义
html_unescape(s)             // HTML 反转义
```

**状态**：⚠️ 部分实现，需增强

---

### 3. File（文件 I/O）

文件、目录和路径操作。

#### 3.1 文件读写 ✅ 已实现

```helen
read_file(path)              // 读取文件
write_file(path, content)    // 写入文件
append_file(path, content)   // 追加文件
```

#### 3.2 目录操作 ✅ 已实现

```helen
mkdir(path)                  // 创建目录
mkdir_p(path)                // 创建目录树
```

#### 3.3 路径操作 ✅ 已实现

```helen
path_join(*parts)            // 拼接路径
path_dirname(path)           // 目录名
path_basename(path)          // 文件名
path_exists(path)            // 是否存在
path_is_file(path)           // 是否文件
path_is_dir(path)            // 是否目录
```

#### 3.4 高级文件操作 ❌ 待实现

```helen
// 文件信息
file_size(path)              // 文件大小
file_modified(path)          // 修改时间
list_dir(path)               // 列出目录
walk_dir(path)               // 递归遍历

// 文件操作
copy_file(src, dst)          // 复制文件
move_file(src, dst)          // 移动文件
delete_file(path)            // 删除文件
delete_dir(path)             // 删除目录

// 临时文件
temp_file()                  // 创建临时文件
temp_dir()                   // 创建临时目录
```

**状态**：⚠️ 基础已实现，需增强

---

### 4. Network（网络通信）⭐ 核心

获取网上资料的核心模块。

#### 4.1 HTTP 请求 ❌ 待实现

```helen
// 基础请求
http_get(url, headers?)      // GET 请求
http_post(url, data?, headers?)  // POST 请求
http_put(url, data?, headers?)   // PUT 请求
http_delete(url, headers?)   // DELETE 请求

// 高级功能
http_request(method, url, options?)  // 通用请求
http_download(url, path)     // 下载文件
http_upload(url, file)       // 上传文件

// 响应对象
response.status              // 状态码
response.headers             // 响应头
response.body                // 响应体
response.json()              // 解析 JSON
response.text()              // 获取文本
```

#### 4.2 URL 处理 ❌ 待实现

```helen
url_parse(url)               // 解析 URL
url_build(scheme, host, path?, query?)  // 构建 URL
url_query_parse(query_string)  // 解析查询参数
url_query_build(params)      // 构建查询参数
```

#### 4.3 WebSocket ❌ 待实现

```helen
ws_connect(url)              // 连接 WebSocket
ws_send(socket, message)     // 发送消息
ws_receive(socket)           // 接收消息
ws_close(socket)             // 关闭连接
```

**状态**：❌ 未实现，优先级高

---

### 5. Data（数据格式）

解析和生成各种数据格式。

#### 5.1 JSON ❌ 待实现

```helen
json_parse(text)             // 解析 JSON
json_stringify(value, indent?)  // 生成 JSON
json_load(path)              // 从文件加载
json_save(path, value)       // 保存到文件
```

#### 5.2 HTML/XML ❌ 待实现

```helen
// HTML 解析
html_parse(text)             // 解析 HTML
html_select(html, selector)  // CSS 选择器
html_text(html)              // 提取文本
html_links(html)             // 提取链接

// XML 解析
xml_parse(text)              // 解析 XML
xml_find(xml, path)          // XPath 查询
```

#### 5.3 Markdown ❌ 待实现

```helen
markdown_parse(text)         // 解析 Markdown
markdown_to_html(text)       // 转 HTML
markdown_extract_headings(text)  // 提取标题
```

#### 5.4 CSV ❌ 待实现

```helen
csv_parse(text, delimiter?)  // 解析 CSV
csv_stringify(rows, delimiter?)  // 生成 CSV
csv_load(path)               // 从文件加载
csv_save(path, rows)         // 保存到文件
```

#### 5.5 YAML/TOML ❌ 待实现

```helen
yaml_parse(text)             // 解析 YAML
yaml_stringify(value)        // 生成 YAML
toml_parse(text)             // 解析 TOML
toml_stringify(value)        // 生成 TOML
```

**状态**：❌ 未实现，优先级中

---

### 6. Collection（集合与数据结构）

数组、字典、集合等。

#### 6.1 数组/列表 ⚠️ 部分实现

**已实现 ✅**

```helen
len(list)                    // 长度
min(list), max(list)         // 最值
```

**待实现 ❌**

```helen
map(list, fn)                // 映射
filter(list, fn)             // 过滤
reduce(list, fn, initial?)   // 归约
find(list, fn)               // 查找
every(list, fn)              // 全部满足
some(list, fn)               // 部分满足
sort(list, compare?)         // 排序
reverse(list)                // 反转
unique(list)                 // 去重
flatten(list)                // 扁平化
chunk(list, size)            // 分块
zip(*lists)                  // 压缩
```

#### 6.2 字典/映射 ❌ 待实现

```helen
keys(dict)                   // 所有键
values(dict)                 // 所有值
entries(dict)                // 所有键值对
merge(*dicts)                // 合并字典
pick(dict, keys)             // 选择键
omit(dict, keys)             // 排除键
```

#### 6.3 集合 ❌ 待实现

```helen
set(items)                   // 创建集合
set_union(s1, s2)            // 并集
set_intersection(s1, s2)     // 交集
set_difference(s1, s2)       // 差集
set_has(set, item)           // 是否包含
```

**状态**：⚠️ 部分实现，需增强

---

### 7. Math（数学与统计）

基础数学和统计计算。

#### 7.1 基础数学 ✅ 已实现

```helen
abs(value)                   // 绝对值
sqrt(value)                  // 平方根
floor(value)                 // 向下取整
ceil(value)                  // 向上取整
round(value, ndigits?)       // 四舍五入
```

#### 7.2 高级数学 ❌ 待实现

```helen
// 三角函数
sin(value), cos(value), tan(value)
asin(value), acos(value), atan(value)

// 指数对数
exp(value)                   // e^x
log(value, base?)            // 对数
pow(base, exp)               // 幂运算

// 随机数
random()                     // 0-1 随机数
randint(min, max)            // 整数随机
choice(list)                 // 随机选择
shuffle(list)                // 随机打乱
```

#### 7.3 统计 ❌ 待实现

```helen
mean(list)                   // 平均值
median(list)                 // 中位数
mode(list)                   // 众数
variance(list)               // 方差
stddev(list)                 // 标准差
correlation(list1, list2)    // 相关系数
```

**状态**：⚠️ 部分实现，需增强

---

### 8. Time（时间与日期）❌ 待实现

时间戳、日期计算和格式化。

```helen
now()                        // 当前时间戳
time()                       // 当前时间（秒）
sleep(seconds)               // 休眠

// 日期操作
date(year, month, day)       // 创建日期
datetime(year, month, day, hour?, minute?, second?)  // 创建日期时间
date_format(date, pattern?)  // 格式化
date_parse(text, pattern?)   // 解析日期
date_add(date, days?)        // 日期加法
date_diff(date1, date2)      // 日期差

// 计时器
timer_start()                // 开始计时
timer_elapsed()              // 已用时间
```

**状态**：❌ 未实现，优先级中

---

### 9. AI/LLM（AI 专用）⭐ 差异化

Helen 的核心竞争力。

#### 9.1 LLM 调用 ✅ 已实现

```helen
// 语法级支持
llm act prompt               // 执行 LLM 动作
llm stream prompt            // 流式输出
llm if description -> branches  // LLM 路由
```

#### 9.2 Agent 系统 ✅ 已实现

```helen
// 语法级支持
agent Name {
    prompt "..."
    tools ["..."]
    model "..."
    max-turns N
}
```

#### 9.3 向量操作 ❌ 待实现

```helen
// Embedding
embed(text)                  // 文本向量化
embed_batch(texts)           // 批量向量化

// 相似度
cosine_similarity(v1, v2)    // 余弦相似度
dot_product(v1, v2)          // 点积
euclidean_distance(v1, v2)   // 欧氏距离

// 向量运算
vector_add(v1, v2)           // 向量加法
vector_scale(v, scalar)      // 向量缩放
vector_normalize(v)          // 向量归一化
```

#### 9.4 记忆系统 ❌ 待实现

```helen
// 记忆存储
memory_get(key)              // 获取记忆
memory_set(key, value)       // 设置记忆
memory_delete(key)           // 删除记忆
memory_list()                // 列出所有记忆

// 语义搜索
memory_search(query, top_k?) // 语义搜索记忆
```

**状态**：⚠️ 核心已实现，需增强向量操作

---

### 10. Media（多媒体处理）🎯 通过 FFI

图片、语音、视频处理通过 Python 生态。

#### 10.1 图片处理（通过 FFI）✅

```helen
// 通过 Python PIL/OpenCV
import "PIL.Image" as Image
import "cv2" as cv2

let img = Image.open("photo.jpg")
let resized = img.resize((800, 600))
img.save("output.jpg")
```

#### 10.2 语音处理（通过 FFI）✅

```helen
// 通过 Python speech_recognition / whisper
import "speech_recognition" as sr
import "whisper" as whisper

let model = whisper.load_model("base")
let result = model.transcribe("audio.mp3")
```

#### 10.3 视频处理（通过 FFI）✅

```helen
// 通过 Python moviepy / opencv
import "moviepy.editor" as mpy
import "cv2" as cv2

let video = mpy.VideoFileClip("video.mp4")
let audio = video.audio
```

**状态**：✅ 通过 FFI 实现，无需内置

---

### 11. System（系统与环境）❌ 待实现

环境变量、进程管理和日志。

#### 11.1 环境变量

```helen
env_get(key, default?)       // 获取环境变量
env_set(key, value)          // 设置环境变量
env_list()                   // 列出所有环境变量
```

#### 11.2 进程管理

```helen
exec(command)                // 执行命令
exec_async(command)          // 异步执行
exit(code?)                  // 退出程序
pid()                        // 当前进程 ID
```

#### 11.3 日志

```helen
log_debug(message)           // 调试日志
log_info(message)            // 信息日志
log_warn(message)            // 警告日志
log_error(message)           // 错误日志
log_set_level(level)         // 设置日志级别
```

**状态**：❌ 未实现，优先级低

---

### 12. Crypto（加密与安全）❌ 待实现

哈希、编码和加密。

```helen
// 哈希
md5(text)                    // MD5 哈希
sha1(text)                   // SHA1 哈希
sha256(text)                 // SHA256 哈希
hmac(key, text, algorithm?)  // HMAC

// 加密（通过 FFI）
import "cryptography" as crypto
```

**状态**：❌ 未实现，优先级低

---

## 优先级排序

### P0（立即实现）- AI 核心 ⭐

| 模块 | 功能 | 理由 |
|------|------|------|
| **String** | 正则表达式、文本分析 | 文字处理是 AI 核心 |
| **Network** | HTTP 请求、URL 处理 | 获取网上资料的核心 |
| **AI/LLM** | 向量操作、记忆系统 | 差异化优势 |

### P1（近期实现）- 基础功能

| 模块 | 功能 | 理由 |
|------|------|------|
| **Collection** | map/filter/reduce | 函数式编程基础 |
| **Data** | JSON/HTML/Markdown 解析 | 数据处理必需 |
| **Math** | 统计函数 | 数据分析基础 |

### P2（中期实现）- 完善功能

| 模块 | 功能 | 理由 |
|------|------|------|
| **Time** | 日期时间 | 通用需求 |
| **File** | 高级文件操作 | 完善功能 |
| **System** | 环境变量、日志 | 系统交互 |

### P3（长期实现）- 可选功能

| 模块 | 功能 | 理由 |
|------|------|------|
| **Crypto** | 加密 | 安全需求 |
| **Media** | 通过 FFI | 已解决 |

---

## 实施计划

### 阶段 1：核心功能（1-2 周）

**目标**：实现 AI 应用的基础能力

- [ ] 实现 HTTP 请求（http_get, http_post）
- [ ] 实现 JSON 解析（json_parse, json_stringify）
- [ ] 增强字符串处理（正则表达式）
- [ ] 实现 URL 处理（url_parse, url_build）

**交付物**：
- `helen/stdlib/network.py`
- `helen/stdlib/data.py`（JSON 部分）
- 增强 `helen/stdlib/__init__.py`（正则部分）

### 阶段 2：数据处理（2-3 周）

**目标**：支持常见数据格式和集合操作

- [ ] 实现 HTML 解析（html_parse, html_select）
- [ ] 实现集合操作（map, filter, reduce）
- [ ] 实现统计函数（mean, median, stddev）
- [ ] 实现 Markdown 解析

**交付物**：
- 增强 `helen/stdlib/data.py`（HTML/Markdown）
- `helen/stdlib/collection.py`
- 增强 `helen/stdlib/math.py`

### 阶段 3：AI 增强（2-3 周）

**目标**：强化 AI 能力

- [ ] 实现向量操作（embed, cosine_similarity）
- [ ] 实现记忆系统（memory_get, memory_search）
- [ ] 实现日期时间（now, date_format）
- [ ] 实现高级文件操作（list_dir, walk_dir）

**交付物**：
- `helen/stdlib/ai.py`
- `helen/stdlib/time.py`
- 增强 `helen/stdlib/file.py`

### 阶段 4：完善功能（持续）

**目标**：完善标准库

- [ ] 实现系统功能（env_get, exec, log）
- [ ] 实现加密功能（md5, sha256）
- [ ] 实现 CSV/YAML 解析
- [ ] 实现 WebSocket

**交付物**：
- `helen/stdlib/system.py`
- `helen/stdlib/crypto.py`
- 增强 `helen/stdlib/data.py`

---

## 参考与对比

### 与其他语言标准库对比

| 功能 | Python | JavaScript | Go | Rust | Helen |
|------|--------|-----------|-----|------|-------|
| 文件 I/O | ✅ 内置 | ✅ 内置 | ✅ 内置 | ✅ 内置 | ✅ 内置 |
| 网络请求 | ❌ 第三方 | ✅ fetch | ✅ 内置 | ❌ 第三方 | ✅ 内置 |
| JSON | ✅ 内置 | ✅ 内置 | ✅ 内置 | ❌ 第三方 | ✅ 内置 |
| 正则 | ✅ 内置 | ✅ 内置 | ✅ 内置 | ❌ 第三方 | ✅ 内置 |
| HTTP 服务器 | ✅ 内置 | ✅ 内置 | ✅ 内置 | ❌ 第三方 | ❌ FFI |
| 数据科学 | ✅ 第三方 | ❌ 第三方 | ❌ 第三方 | ❌ 第三方 | ❌ FFI |
| AI/LLM | ❌ 第三方 | ❌ 第三方 | ❌ 第三方 | ❌ 第三方 | ✅ 内置 |

### Helen 的差异化优势

1. **语法级 AI 支持**：`llm act`, `agent`, `llm stream`
2. **内置向量操作**：embed, cosine_similarity
3. **记忆系统**：memory_get, memory_search
4. **流式输出**：llm stream 原生支持
5. **工具调用**：agent tools 声明式语法

---

## 总结

### 标准库占比

| 类别 | 策略 | 占比 |
|------|------|------|
| **文字处理** | 内置，重点增强 | 30% |
| **网络通信** | 内置，核心功能 | 20% |
| **AI/LLM** | 内置，差异化 | 15% |
| **数据格式** | 内置，基础解析 | 15% |
| **多媒体** | FFI，Python 生态 | 10% |
| **其他** | 内置，基础功能 | 10% |

### 核心原则

- ✅ **文字处理是重点**（AI 主要处理文本）
- ✅ **网络操作是核心**（获取网上资料）
- ✅ **AI 功能是差异化**（LLM/Agent/向量）
- ✅ **多媒体通过 FFI**（不重复造轮子）
- ✅ **精简实用**（避免 stdlib 膨胀）

### 最终目标

- Helen 语法简洁、AI-native
- stdlib 精简、实用、零依赖
- Python FFI 桥接 40 万+ 生态
- 三者结合，形成独特竞争力

---

## 附录

### A. 函数命名规范

- 使用 snake_case：`http_get`, `json_parse`
- 动词开头：`read_file`, `write_file`
- 名词结尾：`path_dirname`, `file_size`
- 布尔函数：`path_exists`, `startswith`

### B. 错误处理

所有 stdlib 函数应该：
- 返回明确的错误信息
- 支持 try-catch 捕获
- 提供有用的错误上下文

```helen
try {
    let content = read_file("nonexistent.txt")
} catch RuntimeError err {
    print("Error: " + err.message)
}
```

### C. 文档规范

每个 stdlib 函数应该包含：
- 函数签名
- 参数说明
- 返回值说明
- 使用示例
- 错误情况

```python
def _http_get(url: str, headers: dict | None = None) -> dict:
    """Send an HTTP GET request.
    
    Args:
        url: The URL to request
        headers: Optional HTTP headers
    
    Returns:
        Dict with keys: status, headers, body
    
    Example:
        let response = http_get("https://api.example.com")
        print(response.status)
    
    Raises:
        RuntimeError: If request fails
    """
```

---

**文档版本**：v1.0  
**最后更新**：2026-06-18  
**维护者**：Helen 开发团队
