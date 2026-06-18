# Helen 标准库实施计划

> 版本: v1.0 | 状态: 实施中 | 最后更新: 2026-06-18

## 实施原则

采用 **契约优先 + TDD** 模式：
1. **契约**（Contracts）：定义类型签名和接口
2. **测试**（Tests）：编写可执行规范
3. **实现**（Implementation）：TDD RED→GREEN→REFACTOR

## 当前状态

### ✅ 已完成

| 模块 | 功能 | 文件 |
|------|------|------|
| Network | HTTP 请求、URL 处理 | `network.py`, `network_contracts.py` |
| String | 基础操作（upper/lower/split/join 等） | `__init__.py` |
| File | 读写文件、目录创建 | `__init__.py` |
| Path | 路径操作 | `__init__.py` |
| Math | 基础数学（sqrt/floor/ceil/round） | `__init__.py` |
| Core | 类型转换、通用操作 | `__init__.py` |

### 🚧 待实施

#### P0 - 立即实现（AI 核心）

| 模块 | 功能 | 优先级 | 状态 |
|------|------|--------|------|
| String | 正则表达式 | P0 | ⏳ 待实施 |
| String | 文本分析 | P0 | ⏳ 待实施 |
| String | 编码转换 | P0 | ⏳ 待实施 |
| Data | JSON 解析 | P0 | ⏳ 待实施 |
| Collection | map/filter/reduce | P0 | ⏳ 待实施 |
| Collection | 字典操作 | P0 | ⏳ 待实施 |

#### P1 - 近期实现（基础功能）

| 模块 | 功能 | 优先级 | 状态 |
|------|------|--------|------|
| Data | HTML 解析 | P1 | ⏳ 待实施 |
| Data | Markdown 解析 | P1 | ⏳ 待实施 |
| Math | 统计函数 | P1 | ⏳ 待实施 |
| Time | 日期时间 | P1 | ⏳ 待实施 |

#### P2 - 中期实现（完善功能）

| 模块 | 功能 | 优先级 | 状态 |
|------|------|--------|------|
| File | 高级文件操作 | P2 | ⏳ 待实施 |
| System | 环境变量、日志 | P2 | ⏳ 待实施 |
| Crypto | 加密哈希 | P2 | ⏳ 待实施 |

## 实施阶段

### 阶段 1：P0 核心功能（当前）

**目标**：实现 AI 应用的基础能力

#### 1.1 String 增强

**契约**：`helen/stdlib/string_contracts.py`
**测试**：`tests/stdlib/test_string.py`
**实现**：`helen/stdlib/string.py`

功能清单：
- 正则表达式：`regex_match`, `regex_search`, `regex_replace`, `regex_split`, `regex_findall`
- 文本分析：`tokenize`, `word_count`, `levenshtein`, `similarity`, `remove_punctuation`, `normalize_whitespace`, `extract_urls`, `extract_emails`
- 编码转换：`base64_encode`, `base64_decode`, `html_escape`, `html_unescape`
- 字符串操作：`repeat`, `reverse`, `pad_left`, `pad_right`, `center`, `count`, `index`

#### 1.2 Data 模块（JSON）

**契约**：`helen/stdlib/data_contracts.py`
**测试**：`tests/stdlib/test_data.py`
**实现**：`helen/stdlib/data.py`

功能清单：
- JSON：`json_parse`, `json_stringify`, `json_load`, `json_save`

#### 1.3 Collection 模块

**契约**：`helen/stdlib/collection_contracts.py`
**测试**：`tests/stdlib/test_collection.py`
**实现**：`helen/stdlib/collection.py`

功能清单：
- 数组操作：`map`, `filter`, `reduce`, `find`, `every`, `some`, `sort`, `reverse`, `unique`, `flatten`, `chunk`, `zip`
- 字典操作：`keys`, `values`, `entries`, `merge`, `pick`, `omit`

### 阶段 2：P1 基础功能

#### 2.1 Data 模块（HTML/Markdown）

功能清单：
- HTML：`html_parse`, `html_select`, `html_text`, `html_links`
- Markdown：`markdown_parse`, `markdown_to_html`, `markdown_extract_headings`

#### 2.2 Math 模块（统计）

功能清单：
- 统计：`mean`, `median`, `mode`, `variance`, `stddev`, `correlation`

#### 2.3 Time 模块

**契约**：`helen/stdlib/time_contracts.py`
**测试**：`tests/stdlib/test_time.py`
**实现**：`helen/stdlib/time.py`

功能清单：
- 时间：`now`, `time`, `sleep`
- 日期：`date`, `datetime`, `date_format`, `date_parse`, `date_add`, `date_diff`

### 阶段 3：P2 完善功能

#### 3.1 File 模块（高级）

功能清单：
- 文件信息：`file_size`, `file_modified`, `list_dir`, `walk_dir`
- 文件操作：`copy_file`, `move_file`, `delete_file`, `delete_dir`
- 临时文件：`temp_file`, `temp_dir`

#### 3.2 System 模块

**契约**：`helen/stdlib/system_contracts.py`
**测试**：`tests/stdlib/test_system.py`
**实现**：`helen/stdlib/system.py`

功能清单：
- 环境变量：`env_get`, `env_set`, `env_list`
- 进程：`exec`, `exec_async`, `exit`, `pid`
- 日志：`log_debug`, `log_info`, `log_warn`, `log_error`, `log_set_level`

#### 3.3 Crypto 模块

**契约**：`helen/stdlib/crypto_contracts.py`
**测试**：`tests/stdlib/test_crypto.py`
**实现**：`helen/stdlib/crypto.py`

功能清单：
- 哈希：`md5`, `sha1`, `sha256`, `hmac`

## 质量保证

每个模块必须满足：
- ✅ 测试覆盖率 ≥ 80%
- ✅ 所有测试通过
- ✅ 类型注解完整
- ✅ 文档字符串完整
- ✅ 错误处理完善

## 提交规范

每个模块实施完成后：
1. 运行测试：`pytest tests/stdlib/test_<module>.py`
2. 检查覆盖率：`pytest --cov=helen.stdlib tests/stdlib/`
3. 提交代码：`git add . && git commit -m "feat(stdlib): add <module> module"`
4. 推送远程：`git push origin master`

---

**下一步**：开始实施阶段 1.1（String 增强）
