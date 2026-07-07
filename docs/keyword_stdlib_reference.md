# Helen 语言关键字与标准库函数 — 中英文对照表

> 自动生成自源码 `helen/core/tokens.py`、`helen/stdlib/__init__.py`、`helen/stdlib/locales/zh.py`
>
> 生成日期：2026-07-07 | Helen v1.15

---

## 一、语言关键字（Keywords）

共 97 个关键字（48 英文 + 49 中文），中英文关键字完全等价，可混合使用。

### 1.1 变量与函数声明

| English | 中文 | TokenType | 说明 |
|---------|------|-----------|------|
| `let` | `让` | LET | 变量声明（可变） |
| `const` | `常量` | CONST | 常量声明（不可变） |
| `fn` | `函数` | FN | 函数声明 |
| `return` | `返回` | RETURN | 函数返回 |
| `shared` | `共享` | SHARED | 共享变量声明（跨 agent 可见） |
| `alias` | `别名` | ALIAS | 创建函数/变量别名 |

### 1.2 控制流

| English | 中文 | TokenType | 说明 |
|---------|------|-----------|------|
| `if` | `如果` | IF | 条件分支 |
| `else` | `否则` | ELSE | 条件分支（否则） |
| `for` | `对于` | FOR | for 循环 |
| `in` | `属于` | IN | 迭代 / 成员检测 |
| `while` | `当` | WHILE | while 循环 |
| `break` | `中断` | BREAK | 跳出循环 |
| `continue` | `继续` | CONTINUE | 跳过本轮循环 |
| `match` | `匹配` | MATCH | 模式匹配 |
| `case` | `情况` | CASE | 匹配分支 |
| `default` | `默认` | DEFAULT | 匹配默认分支 |
| `branch` | `分支` | BRANCH | 分支（llm if 内部） |

### 1.3 异常处理

| English | 中文 | TokenType | 说明 |
|---------|------|-----------|------|
| `try` | `尝试` | TRY | 异常捕获块 |
| `catch` | `捕获` | CATCH | 异常捕获 |
| `finally` | `最终` | FINALLY | 无论如何执行 |
| `throw` | `抛出` | THROW | 抛出异常 |
| `assert` | `断言` | ASSERT | 断言条件 |

### 1.4 字面量与运算符

| English | 中文 | TokenType | 说明 |
|---------|------|-----------|------|
| `true` | `真` | TRUE | 布尔真值 |
| `false` | `假` | FALSE | 布尔假值 |
| `null` | `空` | NULL_KW | 空值 |
| `is` | `是` | IS | 类型判断运算符 |

### 1.5 Agent / LLM

| English | 中文 | TokenType | 说明 |
|---------|------|-----------|------|
| `agent` | `智能体` | AGENT | Agent 声明 |
| `llm` | `大模型` | LLM | LLM 调用（`llm act` / `llm if`） |
| `act` | `执行` | ACT | LLM 执行（`llm act`） |
| `async` | `异步` | ASYNC | 异步调用（`async call`） |
| `await` | `等待` | AWAIT | 等待异步结果 |
| `detach` | `分离` | DETACH | fire-and-forget 异步 |
| `prompt` | `提示` | PROMPT | Agent 提示词模板 |
| `description` | `描述` | DESCRIPTION | Agent 描述 |
| `model` | `模型` | MODEL | 指定 LLM 模型 |
| `tools` | `工具` | TOOLS | Agent 可用工具列表 |
| `streaming` | `流式输出` | STREAMING | 启用流式输出 |
| `temperature` | `温度` | TEMPERATURE | LLM 温度参数 |
| `max-turns` | `最大轮次` | MAX_TURNS | LLM 最大对话轮次 |
| `functions` | `函数区` | FUNCTIONS | Agent 可调用函数区 |
| `main` | `主函` | MAIN | Agent / 程序入口 |

### 1.6 模块与类型系统

| English | 中文 | TokenType | 说明 |
|---------|------|-----------|------|
| `import` | `导入` | IMPORT | 导入模块 |
| `as` | `作为` | AS | 导入别名 / 类型转换 |
| `protocol` | `协议` | PROTOCOL | 协议声明（结构类型） |
| `impl` | `实现` | IMPL | 协议实现 |

### 1.7 共享状态与通信（v1.12–v1.13）

| English | 中文 | TokenType | 说明 |
|---------|------|-----------|------|
| `store` | `仓库` | STORE | 共享仓库声明 |
| `channel` | `通道` | CHANNEL | Agent 间通信通道 |

---

## 二、标准库函数（Stdlib Functions）

共 **198** 个内置函数，按类别分组。有中文别名的函数可直接使用中文名调用。

### 2.1 核心函数（Core）

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `print` | `打印` | `print(*args)` | 输出到标准输出 |
| `len` | `长度` | `len(value)` | 返回字符串/列表/字典长度 |
| `str` | `字符串` | `str(value)` | 转换为字符串 |
| `int` | `整数` | `int(value)` | 转换为整数 |
| `float` | `浮点` | `float(value)` | 转换为浮点数 |
| `abs` | `绝对值` | `abs(value)` | 绝对值 |
| `min` | `最小值` | `min(*args)` | 最小值 |
| `max` | `最大值` | `max(*args)` | 最大值 |
| `range` | `范围` | `range(start, stop?, step?)` | 整数序列 |
| `type` | `类型` | `type(value)` | 返回类型名称 |
| `isinstance` | `类型判断` | `isinstance(value, type_name)` | 类型检查 |
| `input` | `输入` | `input(prompt?)` | 读取一行输入 |
| `multiline_input` | `多行输入` | `multiline_input(prompt?)` | 读取多行输入（空行结束） |
| `exit` | `退出` | `exit(code?)` | 退出程序 |

### 2.2 字符串操作（String）

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `upper` | `转大写` | `upper(s)` | 转大写 |
| `lower` | `转小写` | `lower(s)` | 转小写 |
| `strip` | `去除空白` | `strip(s)` | 去除首尾空白 |
| `split` | `分割` | `split(s, sep?)` | 按分隔符分割 |
| `join` | `连接` | `join(items, sep)` | 连接字符串列表 |
| `startswith` | `以...开头` | `startswith(s, prefix)` | 检查前缀 |
| `endswith` | `以...结尾` | `endswith(s, suffix)` | 检查后缀 |
| `replace` | `替换` | `replace(s, old, new)` | 替换子串 |
| `find` | `查找` | `find(s, sub)` | 查找子串索引（未找到返回 -1） |
| `contains` | `包含` | `contains(s, sub)` | 检查是否包含子串 |
| `substring` | `子串` | `substring(s, start, end?)` | 提取子串 |
| `trim_prefix` | `去前缀` | `trim_prefix(s, prefix)` | 去除前缀 |
| `trim_suffix` | `去后缀` | `trim_suffix(s, suffix)` | 去除后缀 |
| `interpolate` | `插值` | `interpolate(template, vars)` | 模板字符串插值 `{{var}}` |
| `repeat` | `重复` | `repeat(s, n)` | 重复字符串 n 次 |
| `reverse` | `反转` | `reverse(s)` | 反转字符串 |
| `pad_left` | `左填充` | `pad_left(s, width, char?)` | 左填充至指定宽度 |
| `pad_right` | `右填充` | `pad_right(s, width, char?)` | 右填充至指定宽度 |
| `center` | `居中` | `center(s, width, char?)` | 居中对齐 |
| `count` | `计数` | `count(s, sub)` | 统计子串出现次数 |
| `index` | `查找索引` | `index(s, sub)` | 查找子串索引 |
| `format_float` | `格式化浮点` | `format_float(value, decimals)` | 格式化浮点数 |

### 2.3 正则表达式（Regex）

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `regex_match` | `正则匹配` | `regex_match(pattern, s)` | 从开头匹配 |
| `regex_search` | `正则搜索` | `regex_search(pattern, s)` | 搜索匹配位置 |
| `regex_test` | `正则测试` | `regex_test(pattern, s)` | 测试是否匹配（返回 bool） |
| `regex_replace` | `正则替换` | `regex_replace(pattern, s, replacement)` | 正则替换 |
| `regex_split` | `正则分割` | `regex_split(pattern, s)` | 正则分割 |
| `regex_findall` | `正则查找全部` | `regex_findall(pattern, s)` | 查找全部匹配 |

### 2.4 文本分析（Text Analysis）

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `tokenize` | `分词` | `tokenize(text)` | 文本分词 |
| `word_count` | `词频统计` | `word_count(text)` | 词频统计 |
| `levenshtein` | `编辑距离` | `levenshtein(s1, s2)` | 编辑距离 |
| `similarity` | `相似度` | `similarity(s1, s2)` | 字符串相似度 |
| `remove_punctuation` | `去标点` | `remove_punctuation(text)` | 去除标点符号 |
| `normalize_whitespace` | `规范化空白` | `normalize_whitespace(text)` | 规范化空白字符 |
| `extract_urls` | `提取链接` | `extract_urls(text)` | 提取 URL |
| `extract_emails` | `提取邮箱` | `extract_emails(text)` | 提取邮箱地址 |

### 2.5 编码（Encoding）

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `base64_encode` | `base64编码` | `base64_encode(s)` | Base64 编码 |
| `base64_decode` | `base64解码` | `base64_decode(s)` | Base64 解码 |
| `html_escape` | `html转义` | `html_escape(s)` | HTML 转义 |
| `html_unescape` | `html反转义` | `html_unescape(s)` | HTML 反转义 |

### 2.6 数据格式（Data Formats）

#### JSON

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `json_parse` | `json解析` | `json_parse(text)` | 解析 JSON 字符串 |
| `json_stringify` | `json序列化` | `json_stringify(value, indent?)` | 序列化为 JSON |
| `json_load` | `json加载` | `json_load(path)` | 从文件加载 JSON |
| `json_save` | `json保存` | `json_save(path, value, indent?)` | 保存 JSON 到文件 |

#### HTML

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `html_parse` | `html解析` | `html_parse(text)` | 解析 HTML |
| `html_text` | `html文本` | `html_text(html)` | 提取纯文本 |
| `html_links` | `html链接` | `html_links(html)` | 提取所有链接 |
| `html_select` | `html选择` | `html_select(html, selector)` | CSS 选择器查询 |

#### Markdown

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `markdown_to_html` | `md转html` | `markdown_to_html(text)` | Markdown 转 HTML |
| `markdown_extract_headings` | `md提取标题` | `markdown_extract_headings(text)` | 提取标题 |
| `markdown_parse` | `md解析` | `markdown_parse(text)` | 解析为块结构 |

#### CSV

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `csv_parse` | `csv解析` | `csv_parse(text, delimiter?)` | 解析 CSV |
| `csv_stringify` | `csv序列化` | `csv_stringify(rows, delimiter?)` | 序列化为 CSV |
| `csv_load` | `csv加载` | `csv_load(path, delimiter?)` | 从文件加载 CSV |
| `csv_save` | `csv保存` | `csv_save(path, rows, delimiter?)` | 保存 CSV 到文件 |

#### YAML

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `yaml_parse` | `yaml解析` | `yaml_parse(text)` | 解析 YAML |
| `yaml_stringify` | `yaml序列化` | `yaml_stringify(value)` | 序列化为 YAML |
| `yaml_load` | `yaml加载` | `yaml_load(path)` | 从文件加载 YAML |
| `yaml_save` | `yaml保存` | `yaml_save(path, value)` | 保存 YAML 到文件 |

#### TOML

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `toml_parse` | `toml解析` | `toml_parse(text)` | 解析 TOML |
| `toml_stringify` | `toml序列化` | `toml_stringify(value)` | 序列化为 TOML |
| `toml_load` | `toml加载` | `toml_load(path)` | 从文件加载 TOML |
| `toml_save` | `toml保存` | `toml_save(path, value)` | 保存 TOML 到文件 |

#### XML

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `xml_parse` | `xml解析` | `xml_parse(text)` | 解析 XML |
| `xml_stringify` | `xml序列化` | `xml_stringify(value, root?)` | 序列化为 XML |
| `xml_load` | `xml加载` | `xml_load(path)` | 从文件加载 XML |
| `xml_save` | `xml保存` | `xml_save(path, value, root?)` | 保存 XML 到文件 |

### 2.7 集合操作（Collections）

#### 列表操作

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `map` | `映射` | `map(lst, fn)` | 映射转换 |
| `filter` | `过滤` | `filter(lst, fn)` | 过滤元素 |
| `reduce` | `归约` | `reduce(lst, fn, initial?)` | 归约为单值 |
| `find_if` | `条件查找` | `find_if(lst, fn)` | 按条件查找元素 |
| `every` | `全部满足` | `every(lst, fn)` | 是否全部满足条件 |
| `some` | `部分满足` | `some(lst, fn)` | 是否有元素满足条件 |
| `sort` | `排序` | `sort(lst, compare?)` | 排序 |
| `unique` | `去重` | `unique(lst)` | 去重 |
| `flatten` | `展平` | `flatten(lst)` | 展平嵌套列表 |
| `chunk` | `分块` | `chunk(lst, size)` | 分块 |
| `zip` | `压缩` | `zip(*lists)` | 压缩多个列表 |

#### 字典操作

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `keys` | `键` | `keys(dict)` | 获取所有键 |
| `values` | `值` | `values(dict)` | 获取所有值 |
| `entries` | `键值对` | `entries(dict)` | 获取所有键值对 |
| `merge` | `合并` | `merge(*dicts)` | 合并字典 |
| `pick` | `选取` | `pick(dict, keys)` | 选取指定键 |
| `omit` | `剔除` | `omit(dict, keys)` | 剔除指定键 |

#### 集合（Set）操作

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `make_set` | `构造集合` | `make_set(items)` | 创建集合 |
| `set_union` | `集合并` | `set_union(s1, s2)` | 并集 |
| `set_intersection` | `集合交` | `set_intersection(s1, s2)` | 交集 |
| `set_difference` | `集合差` | `set_difference(s1, s2)` | 差集 |
| `set_has` | `集合包含` | `set_has(set, item)` | 检查成员 |

### 2.8 时间日期（Time）

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `now` | `当前时间戳` | `now()` | 当前日期时间 |
| `time` | `当前时间` | `time()` | Unix 时间戳 |
| `sleep` | `休眠` | `sleep(seconds)` | 暂停执行 |
| `date` | `日期` | `date(year?, month?, day?)` | 创建/获取日期 |
| `datetime` | `日期时间` | `datetime(year?, month?, day?, hour?, minute?, second?)` | 创建/获取日期时间 |
| `date_format` | `日期格式化` | `date_format(date_str, format_str)` | 格式化日期 |
| `date_parse` | `日期解析` | `date_parse(date_str, format_str)` | 解析日期字符串 |
| `date_add` | `日期相加` | `date_add(date_str, days?, hours?, minutes?, seconds?)` | 日期加法 |
| `date_diff` | `日期相减` | `date_diff(date1, date2, unit?)` | 日期差值 |
| `date_year` | `年` | `date_year(date_str)` | 提取年份 |
| `date_month` | `月` | `date_month(date_str)` | 提取月份 |
| `date_day` | `日` | `date_day(date_str)` | 提取日期 |
| `date_weekday` | `星期` | `date_weekday(date_str)` | 星期几 |

### 2.9 数学与统计（Math / Stats）

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `round` | `四舍五入` | `round(value, ndigits?)` | 四舍五入 |
| `sqrt` | `平方根` | `sqrt(value)` | 平方根 |
| `floor` | `向下取整` | `floor(value)` | 向下取整 |
| `ceil` | `向上取整` | `ceil(value)` | 向上取整 |
| `mean` | `平均值` | `mean(numbers)` | 算术平均值 |
| `median` | `中位数` | `median(numbers)` | 中位数 |
| `mode` | `众数` | `mode(numbers)` | 众数 |
| `variance` | `方差` | `variance(numbers, population?)` | 方差 |
| `stddev` | `标准差` | `stddev(numbers, population?)` | 标准差 |
| `correlation` | `相关系数` | `correlation(x, y)` | Pearson 相关系数 |
| `percentile` | `百分位` | `percentile(numbers, p)` | 百分位数 |
| `sum` | `求和` | `sum(numbers)` | 求和 |
| `product` | `求积` | `product(numbers)` | 求积 |
| `stats_min` | `统计最小` | `stats_min(numbers)` | 统计最小值 |
| `stats_max` | `统计最大` | `stats_max(numbers)` | 统计最大值 |

### 2.10 文件读写（File I/O）

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `read_file` | `读文件` | `read_file(path)` | 读取文件内容 |
| `write_file` | `写文件` | `write_file(path, content)` | 写入文件 |
| `append_file` | `追加文件` | `append_file(path, content)` | 追加到文件 |
| `file_size` | `文件大小` | `file_size(path)` | 文件大小（字节） |
| `file_modified` | `文件修改时间` | `file_modified(path)` | 文件修改时间 |
| `list_dir` | `列出目录` | `list_dir(path, pattern?)` | 列出目录内容 |
| `walk_dir` | `遍历目录` | `walk_dir(path)` | 递归遍历目录树 |
| `copy_file` | `复制文件` | `copy_file(src, dst)` | 复制文件 |
| `move_file` | `移动文件` | `move_file(src, dst)` | 移动文件 |
| `delete_file` | `删除文件` | `delete_file(path)` | 删除文件 |
| `delete_dir` | `删除目录` | `delete_dir(path, recursive?)` | 删除目录 |
| `mkdir` | `创建目录` | `mkdir(path)` | 创建目录 |
| `mkdir_p` | `递归创建目录` | `mkdir_p(path)` | 递归创建目录 |
| `temp_file` | `临时文件` | `temp_file(suffix?, prefix?, dir?)` | 创建临时文件 |
| `temp_dir` | `临时目录` | `temp_dir(suffix?, prefix?, dir?)` | 创建临时目录 |
| `path_join` | `路径拼接` | `path_join(*parts)` | 路径拼接 |
| `path_dirname` | `路径目录名` | `path_dirname(path)` | 获取目录部分 |
| `path_basename` | `路径基础名` | `path_basename(path)` | 获取文件名部分 |
| `path_exists` | `路径存在` | `path_exists(path)` | 检查路径是否存在 |
| `path_is_file` | `是否文件` | `path_is_file(path)` | 检查是否为文件 |
| `path_is_dir` | `是否目录` | `path_is_dir(path)` | 检查是否为目录 |
| `hash_file` | `文件哈希` | `hash_file(path, algorithm?)` | 计算文件哈希 |
| `glob_files` | `查找文件` | `glob_files(path, pattern?)` | 按模式查找文件 |
| `grep_files` | `搜索内容` | `grep_files(path, pattern, regex?, case_sensitive?, max_results?)` | 搜索文件内容 |

### 2.11 系统（System）

#### 环境变量

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `env_get` | `环境变量获取` | `env_get(key, default?)` | 获取环境变量 |
| `env_set` | `环境变量设置` | `env_set(key, value)` | 设置环境变量 |
| `env_delete` | `环境变量删除` | `env_delete(key)` | 删除环境变量 |
| `env_list` | `环境变量列表` | `env_list()` | 列出所有环境变量 |

#### 命令行参数

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `get_cli_args` | `命令行参数` | `get_cli_args()` | 获取命令行参数 |
| `parse_cli_args` | `解析命令行参数` | `parse_cli_args(spec?)` | 解析命令行参数 |

#### 进程

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `exec` | `执行` | `exec(command, shell?, timeout?)` | 执行命令 |
| `exec_async` | `异步执行` | `exec_async(command, shell?)` | 异步执行命令 |
| `pid` | `进程ID` | `pid()` | 获取当前进程 ID |
| `kill` | `终止进程` | `kill(pid, signal?)` | 发送信号到进程 |

#### 日志

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `log_debug` | `日志调试` | `log_debug(message)` | 调试日志 |
| `log_info` | `日志信息` | `log_info(message)` | 信息日志 |
| `log_warn` | `日志警告` | `log_warn(message)` | 警告日志 |
| `log_error` | `日志错误` | `log_error(message)` | 错误日志 |
| `log_critical` | `日志严重` | `log_critical(message)` | 严重日志 |
| `log_set_level` | `日志设置级别` | `log_set_level(level)` | 设置日志级别 |
| `log_to_file` | `日志写入文件` | `log_to_file(path)` | 日志输出到文件 |

### 2.12 加密（Crypto）

#### 哈希

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `md5` | `md5` | `md5(text)` | MD5 哈希 |
| `sha1` | `sha1` | `sha1(text)` | SHA1 哈希 |
| `sha256` | `sha256` | `sha256(text)` | SHA256 哈希 |
| `sha512` | `sha512` | `sha512(text)` | SHA512 哈希 |
| `hmac_sha256` | `hmac_sha256` | `hmac_sha256(key, message)` | HMAC-SHA256 |

#### 随机数

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `random` | `随机` | `random()` | 生成随机浮点数 [0, 1) |
| `randint` | `随机整数` | `randint(min, max)` | 生成随机整数 |
| `choice` | `随机选择` | `choice(items)` | 随机选择一个元素 |
| `shuffle` | `洗牌` | `shuffle(items)` | 随机打乱列表 |
| `sample` | `随机抽样` | `sample(items, k)` | 随机抽样 k 个元素 |

### 2.13 网络（Network）

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `http_get` | `http获取` | `http_get(url, headers?)` | HTTP GET 请求 |
| `http_post` | `http发布` | `http_post(url, data?, headers?)` | HTTP POST 请求 |
| `http_put` | `http提交` | `http_put(url, data?, headers?)` | HTTP PUT 请求 |
| `http_delete` | `http删除` | `http_delete(url, headers?)` | HTTP DELETE 请求 |
| `http_download` | `http下载` | `http_download(url, path)` | 下载文件 |
| `url_parse` | `链接解析` | `url_parse(url)` | 解析 URL |
| `url_build` | `链接构建` | `url_build(scheme, host, path?, query?)` | 构建 URL |
| `url_encode` | `链接编码` | `url_encode(s)` | URL 编码 |
| `url_decode` | `链接解码` | `url_decode(s)` | URL 解码 |

### 2.14 流式输出（Stream）

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `stream_print` | `流式打印` | `stream_print(text)` | 不换行打印 |
| `stream_clear` | `流式清除` | `stream_clear()` | 清除当前行 |
| `stream_cursor_up` | `光标上移` | `stream_cursor_up(n?)` | 光标上移 n 行 |
| `stream_cursor_down` | `光标下移` | `stream_cursor_down(n?)` | 光标下移 n 行 |
| `progress_bar` | `进度条` | `progress_bar(current, total, width?)` | 显示进度条 |

### 2.15 调试/跟踪（Debug / Trace）

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `debug` | `调试` | `debug(message, data?)` | 输出结构化调试信息 |
| `trace_on` | `开启跟踪` | `trace_on()` | 启用执行跟踪 |
| `trace_off` | `关闭跟踪` | `trace_off()` | 禁用执行跟踪 |
| `get_trace` | `获取跟踪` | `get_trace(n?)` | 获取最近执行跟踪 |

### 2.16 工具（Tools）

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `web_search` | `网页搜索` | `web_search(query, limit?)` | 搜索网页 |
| `web_fetch` | `网页获取` | `web_fetch(url)` | 获取网页内容 |
| `shell_exec` | `执行命令` | `shell_exec(command, timeout?, shell?)` | 执行 Shell 命令 |
| `calculate` | `计算表达式` | `calculate(expression)` | 计算数学表达式 |
| `patch_file` | `修补文件` | `patch_file(path, old_string, new_string, replace_all?)` | 模糊匹配修补文件 |
| `load_skill` | `加载技能` | `load_skill(name)` | 按名称加载技能 |

### 2.17 测试框架（Test）

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `describe` | `描述` | `describe(name, fn)` | 定义测试套件 |
| `it` | `它` | `it(name, fn)` | 定义测试用例 |
| `it_skip` | `跳过它` | `it_skip(name, fn?)` | 定义跳过的测试用例 |
| `expect` | `期望` | `expect(value)` | 创建链式断言 |
| `assert_true` | `断言为真` | `assert_true(condition, message?)` | 断言条件为真 |
| `assert_equal` | `断言相等` | `assert_equal(actual, expected, message?)` | 断言相等 |
| `assert_not_equal` | `断言不等` | `assert_not_equal(actual, expected, message?)` | 断言不等 |
| `assert_contains` | `断言包含` | `assert_contains(container, item, message?)` | 断言包含 |
| `assert_throws` | `断言抛出` | `assert_throws(fn, error_type?)` | 断言抛出异常 |
| `before_each` | `前置每个` | `before_each(fn)` | 每个用例前执行 |
| `after_each` | `后置每个` | `after_each(fn)` | 每个用例后执行 |
| `before_all` | `前置所有` | `before_all(fn)` | 所有用例前执行 |
| `after_all` | `后置所有` | `after_all(fn)` | 所有用例后执行 |
| `run_tests` | `运行测试` | `run_tests(only?, suite?, filter?)` | 执行测试并打印报告 |
| `run_tests_json` | `运行测试json` | `run_tests_json(only?, suite?, filter?)` | 执行测试返回 JSON |
| `test_reset` | `重置测试` | `test_reset()` | 清除所有已注册测试 |
| `test_count` | `测试计数` | `test_count()` | 统计已注册测试数 |
| `test_suite` | `测试套件` | `test_suite(name)` | 开始测试套件 |
| `test_case` | `测试用例` | `test_case(name, fn)` | 注册测试用例 |
| `test_case_skip` | `跳过测试用例` | `test_case_skip(name, fn?)` | 注册跳过的测试 |
| `test_end_suite` | `结束测试套件` | `test_end_suite()` | 结束当前测试套件 |
| `fail` | `失败` | `fail(message?)` | 显式标记测试失败 |
| `set_test_timeout` | `设置测试超时` | `set_test_timeout(seconds)` | 设置单测试超时 |

### 2.18 代码质量（Quality）

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `analyze_code` | `分析代码` | `analyze_code(source, filename?)` | 代码指标分析 |
| `check_security` | `安全检查` | `check_security(source)` | 安全检查 |
| `quality_score` | `质量评分` | `quality_score(source, file_path?)` | 质量评分 |
| `quality_report` | `质量报告` | `quality_report(source, filename?)` | 生成质量报告 |

### 2.19 上下文管理（Context，v1.15）

| English | 中文 | 签名 | 说明 |
|---------|------|------|------|
| `clear_context` | `清除上下文` | `clear_context()` | 清除对话历史 |
| `compress_context` | `压缩上下文` | `compress_context(strategy?)` | 压缩对话上下文 |
| `classify_message` | `消息分类` | `classify_message(message)` | 消息类型与优先级分类 |
| `compress_context_target` | `定向压缩` | `compress_context_target(target, keep_recent?)` | 按目标类型压缩上下文 |

---

## 三、统计汇总

| 分类 | 数量 |
|------|------|
| 英文关键字 | 48 |
| 中文关键字 | 49 |
| 标准库函数（英文） | 237 |
| 标准库函数中文别名 | 237 |
| 无中文别名的函数 | 0 |
