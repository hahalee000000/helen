# Helen 代码健康度报告 — Phase 1 客观检查

**日期**: 2026-07-11
**检查范围**: `helen/` (96 个 Python 文件)
**检查依据**: `code-quality` skill §1 (Dead-Code Audit) + §2 (Inconsistency Detection)

---

## 总览

| 类别 | 🔴 Critical | 🟡 Medium | 🟢 Low | ✅ Clean |
|------|------------|-----------|--------|----------|
| 未实现代码 (stub/TODO) | 0 | 0 | 0 | ✅ |
| 未调用函数 (dead code) | 22 | — | 3 (API) | — |
| 静默异常吞没 | 7 | — | — | — |
| 不一致 (常量/函数) | 1 | 2 | 2 | — |

---

## §1 Dead-Code Audit

### 1.1 未实现代码 ✅

| 检查项 | 结果 |
|--------|------|
| `raise NotImplementedError` | 0 处 |
| `TODO` / `FIXME` / `HACK` / `XXX` 标记 | 0 处真实未实现 (出现的均为"提取 TODO 的功能代码"本身) |
| 空 `if TYPE_CHECKING: pass` 块 | 0 处 (5 个 TYPE_CHECKING 块均有实际 import) |
| 空函数体 (`pass` 在非异常类中) | 0 处 |

**结论: 代码库无 stub/TODO 类未完成代码。**

### 1.2 未调用函数 🔴 (22 个真实死代码)

以下函数/方法在代码库中**无任何调用者**（排除 Python protocol 方法和 __dunder__）：

#### 核心层 (core/)
| 文件 | 行 | 函数 | 说明 |
|------|-----|------|------|
| `core/parser.py` | 1053 | `_prompt_def()` | 方法已定义但被 line 827 的内联代码替代，未清理 |

#### 解释器层 (interpreter/)
| 文件 | 行 | 函数 | 说明 |
|------|-----|------|------|
| `interpreter/task.py` | 51 | `is_done()` | Task 类方法，从未调用 |
| `interpreter/task.py` | 177 | `is_list()` | AwaitExpression 类方法，从未调用 |
| `interpreter/agent_context.py` | 776 | `get_stats()` | 从未调用 |
| `interpreter/llm_mixin.py` | 1341 | `clear_history()` | 从未调用 |
| `interpreter/working_memory.py` | 248 | `_complete_todo()` | 从未调用 |

#### 运行时层 (runtime/) — 死代码最多
| 文件 | 行 | 函数 | 说明 |
|------|-----|------|------|
| `runtime/structured.py` | 20 | `build_route_schema()` | 从未调用 |
| `runtime/structured.py` | 58 | `parse_route_response()` | 从未调用 |
| `runtime/config.py` | 107 | `get_locale_aliases()` | 从未调用 |
| `runtime/history.py` | 804 | `save_to_file()` | 从未调用 |
| `runtime/history.py` | 848 | `load_from_file()` | 从未调用 |
| `runtime/http_llm.py` | 253 | `_trim_messages_for_recovery()` | 从未调用 |
| `runtime/session_manager.py` | 187 | `get_session_dir()` | 从未调用 |
| `runtime/cache_aware_compression.py` | 289 | `cache_aware_compress()` | 模块级函数，从未调用（内部方法 `_apply_cache_aware_compression` 才是实际使用的） |
| `runtime/token_utils.py` | 71 | `is_cjk_codepoint()` | 从未调用 |
| `runtime/token_utils.py` | 172 | `calculate_usage_ratio_from_dicts()` | 从未调用 |
| `runtime/token_utils.py` | 190 | `calculate_usage_ratio_from_messages()` | 从未调用 |
| `runtime/token_utils.py` | 222 | `summarize_message_block()` | 从未调用 |
| `runtime/token_utils.py` | 316 | `extract_global_stats()` | 从未调用（`graduated_compression.py` 有独立的 `_extract_global_stats`） |
| `runtime/tools.py` | 50 | `list_tools()` | 从未调用 |

#### 其他
| 文件 | 行 | 函数 | 说明 |
|------|-----|------|------|
| `semantic/symbols.py` | 188 | `in_global_scope()` | 从未调用 |
| `semantic/symbols.py` | 193 | `current_scope_type()` | 从未调用 |
| `python_bridge/type_converter.py` | 66 | `convert_args()` | 从未调用 |

**聚集热点**:
- `runtime/token_utils.py` — **5 个函数全部未调用**，此模块可能是重构残留
- `runtime/structured.py` — **2 个函数全部未调用**，可能是 llm route 的废弃设计
- `runtime/history.py` — 2 个序列化函数未调用，transcript_store 可能已替代其功能

### 1.3 公共 API 候选 (🟢 需人工判断)

以下函数是模块公共 API，代码库内部未调用但可能是设计预留：

| 文件 | 函数 | 评估 |
|------|------|------|
| `stdlib/__init__.py` | `is_alias()` | BuiltinRegistry 方法，工具链/Docus 可能用 |
| `stdlib/__init__.py` | `list_by_category()` | 同上 |
| `stdlib/__init__.py` | `canonical_names` (property) | 同上 |
| `python_bridge/import_hook.py` | `uninstall_import_hook()` | 清理函数，可能外部使用 |

### 1.4 假阳性 (✅ 已排除)

以下函数看似无引用但实际是 Python protocol 方法，由运行时调用：
- `import_hook.py:12 find_spec()` — `MetaPathFinder` protocol
- `import_hook.py:45 create_module()` — `Loader` protocol
- `import_hook.py:49 exec_module()` — `Loader` protocol

### 1.5 静默异常吞没 🟡 (7 处)

`except Exception: pass` 无日志，出错时无法调试：

| 文件 | 行 | 上下文 | 建议 |
|------|-----|--------|------|
| `interpreter/interpreter.py` | 796 | skill dirs 加载失败 | 加 `logging.debug` |
| `interpreter/llm_mixin.py` | 1004 | skill listing 失败 | 加 `logging.debug` |
| `interpreter/llm_mixin.py` | 1151 | tool args JSON 解析失败 | 加 `logging.debug` |
| `runtime/http_llm.py` | 473 | async client close 失败 | 可接受但加 debug log |
| `runtime/prompt_builder.py` | 341 | skill mtime 检查失败 | 加 `logging.debug` |
| `runtime/transcript_store.py` | 327 | DB close 失败 | 加 `logging.debug` |
| `runtime/session_manager.py` | 145 | transcript 行数统计失败 | 加 `logging.debug` |

---

## §2 Inconsistency Detection

### 2.1 矛盾常量 🔴 (1 处严重)

| 常量 | 文件 A | 值 | 文件 B | 值 | 严重性 |
|------|--------|-----|--------|-----|--------|
| `DEFAULT_CONTEXT_WINDOW` | `runtime/history.py:67` | **128000** | `runtime/token_utils.py:32` | **131072** | 🔴 CRITICAL |

**差异**: 3072 tokens (2.4%)。两个模块对"默认上下文窗口"的定义不同。如果用户配置缺失，`history.py` 会用 128000，而 `token_utils.py` 会用 131072，可能导致 token 计算和压缩策略不一致。

### 2.2 重复常量 🟡 (3 组)

| 常量 | 文件 A | 文件 B | 值是否一致 |
|------|--------|--------|----------|
| `CHARS_PER_TOKEN_CJK` | `history.py:76` (1.2) | `token_utils.py:27` (1.2) | ✅ 一致但重复 |
| `CHARS_PER_TOKEN_EN` | `history.py:75` (4.0) | `token_utils.py:26` (4.0) | ✅ 一致但重复 |
| `CHARS_PER_TOKEN_MIXED` | `history.py:77` (3.0) | `token_utils.py:28` (3.0) | ✅ 一致但重复 |

值目前一致，但分散两处维护。修改一处漏改另一处就会变成 🔴 矛盾。应合并到 `token_utils.py`，`history.py` import 使用。

### 2.3 发散重复函数 🟡 (2 处)

**① `estimate_tokens()` — 不同实现质量**

| 位置 | 实现 | 精度 |
|------|------|------|
| `working_memory.py:324` | `len(context) // 4` | 粗糙（注释自己承认 "Rough estimate"） |
| `history.py:140` | CJK-aware heuristic + tiktoken fallback | 较精确 |

同一个功能，两种质量差异巨大的实现。`working_memory.py` 版本对中文内容误差可达 3 倍以上。应统一使用 `history.py` 版本。

**② `replace_var()` — 近乎复制粘贴**

| 位置 | 变量来源 |
|------|---------|
| `stdlib/__init__.py:500` (内部闭包) | `vars.get(parts[0])` — 从 dict 查 |
| `interpreter/llm_mixin.py:1028` (内部闭包) | `self.environment.lookup(parts[0])` — 从环境链查 |

逻辑几乎完全相同（split → traverse dict → fallback），唯一区别是变量来源。可提取公共函数 `render_template(template, lookup_fn)` 接受一个 lookup 回调。

### 2.4 命名漂移 🟢 (观察项)

未发现严重的命名漂移问题。代码库命名较为一致（`session_id` 统一、`estimate_tokens` 命名统一）。

---

## 改进建议优先级

### P0 (立即修复)
1. **统一 `DEFAULT_CONTEXT_WINDOW`** — 在 `token_utils.py` 定义唯一值，`history.py` 改为 import
2. **合并 `estimate_tokens()`** — `working_memory.py` 改用 `history.estimate_tokens()`

### P1 (本轮迭代)
3. **清理 22 个未调用函数** — 优先处理 `token_utils.py`（5 个全死）和 `structured.py`（2 个全死）
4. **合并重复常量** — `CHARS_PER_TOKEN_*` 系列统一到 `token_utils.py`
5. **提取 `replace_var` 公共逻辑** — 减少 `stdlib/__init__.py` 和 `llm_mixin.py` 的重复

### P2 (持续改进)
6. **7 处静默异常** — 逐个加 `logging.debug(exc_info=True)`
7. **评估公共 API 候选** — 确认 `is_alias` / `list_by_category` / `canonical_names` 是否有外部用户

---

## 方法论说明

本次检查按 `code-quality` skill 工作流执行：

1. **§1 Dead-Code Audit 5 步工作流**:
   - Step 1: AST 解析收集所有函数定义 (96 文件)
   - Step 2: 全文搜索统计每个函数名的引用数
   - Step 3: 扫 stub/TODO/NotImplementedError
   - Step 4: 检查 TYPE_CHECKING 块、except pass 模式
   - Step 5: 手动验证每个候选项（排除 protocol 方法、property、getattr 间接引用）

2. **§2 Inconsistency Detection 工作流**:
   - 同名常量跨文件扫描 + 值对比
   - 同名函数跨文件扫描 + 实现对比
   - 重点验证 token 计算、session 管理等关键路径

**工具**: Python `ast` 模块 + `grep` + `sed` 手动验证
