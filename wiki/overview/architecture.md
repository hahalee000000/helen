# Helen 整体架构

> 三层架构：Core (核心编译器) → Runtime (运行时) → Toolchain (工具链)

---

## 架构分层

```
┌────────────────────────────────────────────────────────────┐
│                    Toolchain 工具链层                        │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌───────┐ ┌──────┐ │
│  │ CLI M11 │ │ LSP M12  │ │ VSCode   │ │Stdlib  │ │DocGen│ │
│  │run/check│ │diagnose  │ │ M13      │ │ M15    │ │      │ │
│  │/repl/doc│ │/complete │ │highlight │ │287 fn  │ │      │ │
│  └────┬────┘ └────┬─────┘ └────┬─────┘ └───┬───┘ └──┬───┘ │
├───────┼───────────┼────────────┼───────────┼─────────┼────┤
│                    Runtime 运行时层                         │
│  ┌──────────┐ ┌───────────┐ ┌───────┐ ┌──────┐ ┌──────┐  │
│  │LLM RT M7 │ │Prompt M6  │ │Memory │ │History│ │Import│  │
│  │ABC×12    │ │Tier 1/2   │ │M7/M16 │ │M16   │ │ M8   │  │
│  │cancel    │ │render     │ │file   │ │budget│ │safe  │  │
│  └────┬─────┘ └─────┬─────┘ └───┬───┘ └──┬───┘ └──┬───┘  │
│  ┌──────────────────────────────────────────────────┐    │
│  │  Interpreter Mixin Architecture                   │    │
│  │  LlmMixin      — LLM act/if, 工具构建, 历史管理  │    │
│  │  PatternMixin  — match/case 模式匹配              │    │
│  │  ExceptionMixin — try/catch/throw/assert          │    │
│  │  ImportMixin   — 多格式导入 (.helen/.py/.json等)  │    │
│  │  StreamingMixin — 流式调用管理与取消               │    │
│  └──────────────────────────────────────────────────┘    │
├───────┼─────────────┼───────────┼─────────┼────────┼──────┤
│                    Core 核心编译层                          │
│  ┌──────┐ ┌────────┐ ┌─────┐ ┌─────────┐ ┌────┐ ┌─────┐  │
│  │Lexer │ │Parser  │ │ AST │ │Semantic │ │Type│ │Error│  │
│  │ M1   │ │ M2     │ │ M3  │ │Analyzer │ │ M9 │ │ M10 │  │
│  │77Tok │ │Pratt×10│ │49Nd │ │46Visitor│ │14Ty│ │42Cd │  │
│  └──┬───┘ └───┬────┘ └──┬──┘ └────┬────┘ └─┬──┘ └──┬──┘  │
└─────┼─────────┼─────────┼─────────┼────────┼───────┼──────┘
      │         │         │         │        │       │
      ▼         ▼         ▼         ▼        ▼       ▼
   源码 → Token流 → AST树 → 符号表/类型 → 执行结果
```

---

## Core 层：核心编译器

### 数据流

```
source.helen
    │
    ▼ ┌─────────────────┐
    │ │   Lexer (M1)    │  扫描源码 → Token 流
    │ │ Maximal Munch   │  39 关键字 / 77 Token 类型
    │ │ 39 keywords     │  SourceSpan 全链路
    │ └────────┬────────┘
    │          ▼ Token[type, lexeme, line, col, span]
    │ ┌─────────────────┐
    │ │  Parser (M2)    │  Token 流 → AST 树
    │ │ Pratt × 10级    │  panic mode 错误恢复
    │ │ EBNF 392行      │  49 种 AST 节点
    │ └────────┬────────┘
    │          ▼ ProgramNode[statements...]
    │ ┌─────────────────┐
    │ │SemanticAnalyzer │  AST → 类型检查 + 符号表
    │ │   (M4)          │  6 种作用域: global/agent/fn/block/catch/loop
    │ │ 46 Visitor方法  │  42 ErrorCode 精确定位
    │ └────────┬────────┘
    │          ▼ (errors or clean AST)
    │  ┌─────────────────┐
    │  │ Interpreter(M5) │  AST → 执行结果
    │  │ Visitor[object] │  Environment 作用域链
    │  │ + 5 Mixins      │  Agent 隔离调用
    │  │ + LLM Runtime   │  Mixin: Llm/Pattern/Exception/Import/Streaming
    │  └─────────────────┘
```

### 关键设计决策

| 决策 | 选择 | 原因 |
|---|---|---|
| 手写扫描器 | 非正则 | 最大灵活性，支持三引号/连字符消歧 |
| Pratt Parsing | 非传统递归下降 | 10 级表达式优先级，`spawn` 前缀处理 |
| Visitor 模式 | 44 抽象方法 | 三个编译阶段共享同一 AST 遍历接口 |
| SourceSpan | 全链路 | 每个 Token/AST 节点携带源码位置，用于精准错误定位 |

---

## Runtime 层：运行时系统

### 抽象接口

```python
class Runtime(ABC):                          # HLD 3.8.1, 12个抽象方法
    def load_tool() -> Any                   # 加载工具
    def list_skills() -> list[SkillMeta]     # 技能索引 (Tier 1)
    def load_skill(name) -> str              # 加载技能内容 (Tier 2)
    def call_llm(messages, tools, ...)       # 调用 LLM
    def cancel_llm_call(call_id) -> bool     # 取消 LLM 调用
    def get_memory(key) -> str | None        # 获取记忆
    def set_memory(key, value)               # 设置记忆
    def resolve_import(path, from_file)      # 解析导入
    def get_token_count(text) -> int         # Token 估算
    def get_conversation_history()           # 获取对话历史
    def set_conversation_history(history)    # 设置对话历史
    def register_memory_provider(proto, p)   # 注册记忆提供者
```

### HelenHermesRuntime (具体实现)

- 继承 `Runtime` ABC
- `threading.Event` 实现可取消 LLM 调用
- `_active_calls` 字典跟踪进行中的调用
- `_memory` 字典实现键值存储
- `_conversation_history` 管理对话历史

### 配置系统 (config.py)

```
~/.helen/
├── config.yaml    # LLM API 配置 (YAML)
├── .env           # LLM API 配置 (.env 格式)
└── skills/        # Helen 原生 skill 目录
```

配置加载优先级：`~/.hermes/.env` → `~/.helen/.env` → `config.yml` → `config.yaml`

### 内置工具 (tools.py)

| 工具 | 功能 |
|------|------|
| `web_search` | Wikipedia 搜索 |
| `web_fetch` | 网页内容获取 |
| `read_file` | 文件读取 |
| `write_file` | 文件写入（覆盖） |
| `patch_file` | 文件精确修改（模糊匹配） |
| `shell_exec` | Shell 命令执行 |
| `calculate` | 数学计算 |

LLM 通过 OpenAI function calling 协议调用工具，支持多轮循环 + nudge 机制。

### 模糊匹配引擎 (fuzzy_match.py)

从 Hermes 集成的 860 行模糊匹配引擎，支持 9 种策略：
- 精确匹配、行修剪、空白归一化、缩进灵活
- 转义归一化、边界修剪、Unicode 归一化
- 块锚点（SequenceMatcher）、上下文感知（逐行相似度）

还包括：转义漂移检测、缩进重锚、"Did you mean?" 提示。

### 组件关系

```
┌─────────────────────────────────────────────┐
│              Interpreter                     │
│  ┌──────────────┐     ┌──────────────────┐  │
│  │ visit_llm_*  │────▶│   LLMRuntime     │  │
│  │ (act/if)           │   (ABC)          │  │
│  └──────┬───────┘     │  route/act       │  │
│         │             └────────┬─────────┘  │
│         │                      │            │
│  ┌──────▼───────┐     ┌────────▼─────────┐  │
│  │ _get_context │────▶│  HistoryManager  │  │
│  │              │     │  budget/trim/sum │  │
│  └──────┬───────┘     └──────────────────┘  │
│         │                                    │
│  ┌──────▼───────┐     ┌──────────────────┐  │
│  │ _call_agent  │────▶│ ImportResolver   │  │
│  │ isolated Env │     │ safe_path/cycle  │  │
│  └──────────────┘     └──────────────────┘  │
└─────────────────────────────────────────────┘
```

---

## Toolchain 层：工具链

### CLI (helen)

```
$ helen main.helen      # 编译 + 执行
$ helen check main.helen  # 仅验证 (Lex + Parse + Analyze)
$ helen repl               # 交互式解释器
$ helen doc main.helen    # 生成文档 (markdown/json)
$ helen init               # 初始化 ~/.helen/ 配置目录
```

退出码：`0`=成功 `1`=词法错误 `2`=语法错误 `3`=语义/运行时错误

### LSP Server (JSON-RPC 2.0 over stdio)

```json
// 客户端 → 服务器
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{...}}
{"jsonrpc":"2.0","method":"textDocument/didOpen","params":{...}}

// 服务器 → 客户端
{"jsonrpc":"2.0","id":1,"result":{"capabilities":{...}}}
{"jsonrpc":"2.0","method":"textDocument/publishDiagnostics","params":{...}}
```

支持方法：`initialize` `textDocument/didOpen` `textDocument/didChange` `textDocument/didClose` `textDocument/diagnostics` `textDocument/completion` `textDocument/definition`

### VS Code Extension

- `syntaxes/helen.tmLanguage.json` — TextMate 语法（覆盖 42 关键字）
- `language-configuration.json` — 括号配对、自动闭合、缩进规则
- `package.json` — 扩展清单

### 标准库 (287 builtins)

| 类别 | 数量 | 代表函数 |
|---|---|---|
| **Core** | 11 | `print`, `len`, `str`, `int`, `float`, `abs`, `min`, `max`, `range`, `type`, `isinstance` |
| **String** | 37 | `upper`, `lower`, `strip`, `split`, `join`, `replace`, `find`, `reverse`, `repeat`, `regex_match`, `regex_replace` |
| **Data** | 25 | `json_parse`, `json_stringify`, `yaml_parse`, `toml_parse`, `csv_parse`, `xml_parse`, `html_escape`, `url_encode`, `base64_encode` |
| **Collection** | 22 | `sort`, `reverse`, `unique`, `flatten`, `zip`, `map`, `filter`, `reduce`, `group_by`, `chunk`, `intersection` |
| **Network** | 9 | `http_get`, `http_post`, `http_put`, `http_delete`, `http_download`, `url_parse` |
| **Time** | 13 | `now`, `timestamp`, `date_format`, `date_parse`, `sleep`, `stopwatch_start`, `stopwatch_elapsed` |
| **Math** | 15 | `round`, `sqrt`, `floor`, `ceil`, `pow`, `log`, `sin`, `cos`, `random_int`, `random_float`, `mean`, `median`, `stddev` |
| **File** | 18 | `read_file`, `write_file`, `append_file`, `file_exists`, `list_dir`, `mkdir`, `copy_file`, `delete_file`, `file_size` |
| **System** | 18 | `env_get`, `env_set`, `shell_exec`, `process_id`, `platform`, `hostname`, `log_info`, `log_error` |
| **Crypto** | 11 | `hash_md5`, `hash_sha256`, `hash_sha512`, `hmac_sha256`, `uuid_generate`, `random_bytes` |
| **IO** | 5 | `read_line`, `prompt`, `format_table`, `progress_bar`, `terminal_width` |
| **Observability** | 4 | `debug`, `trace_on`, `trace_off`, `get_trace` |
| **Context** | 27 | `clear_context`, `compress_context`, `context_stats`, `pin_message`, `working_memory_*`, `set_compression_strategy`, `export_context`, ... |
| **Transcript** | 8 | `get_session_id`, `list_sessions`, `replay_transcript`, `export_transcript`, `get_session_dir`, `set_session_dir`, ... |
| **Media** | 12 | `media`, `media_base64`, `to_openai_parts`, `to_claude_parts`, `to_gemini_parts`, `media_to_base64`, `save_media`, `is_image` |
| **Test** | 14 | `test_suite`, `assert_true`, `assert_equal`, `expect`, `run_tests` |
| **Quality** | 4 | `analyze_code`, `check_security`, `quality_score`, `quality_report` |
| **Tools** | 24 | `web_search`, `web_fetch`, `read_file`, `write_file`, `shell_exec` |

详见 [stdlib.md](../toolchain/stdlib.md)。

### AI 原生可观测性 (observability.py)

为 AI Agent 提供结构化的调试上下文，替代传统交互式 Debugger：

| 组件 | 功能 | 默认状态 |
|------|------|----------|
| `CallStackTracker` | 函数/Agent 调用栈追踪 | 关闭 |
| `ExecutionTracer` | 语句执行追踪（环形缓冲区 10000 条） | 关闭 |
| `ErrorSnapshot` | 结构化错误上下文（JSON） | 自动捕获 |
| `LLMAuditLog` | LLM 调用审计日志（环形缓冲区 1000 条） | 开启 |
| `ObservabilityManager` | 统一管理入口 | — |

REPL 命令：`:trace on|off|show`、`:last_error`、`:llm_log`
内置函数：`debug()`、`trace_on()`、`trace_off()`、`get_trace()`
语言特性：`assert` 语句（失败自动捕获上下文）

---

## 编译阶段与 ErrorCode 映射

| 阶段 | 模块 | ErrorCode 范围 | 典型错误 |
|---|---|---|---|
| 词法分析 | M1 | E0300-E0309 | 未终止字符串、无效转义 |
| 语法分析 | M2 | E0301-E0320 | 意外 Token、缺少 Token |
| 语义分析 | M4 | E0330-E0350 | 未声明变量、类型不匹配 |
| 执行阶段 | M5 | E0334-E0350 | Agent 运行时错误、常量赋值 |

---

## 质量指标

| 指标 | 值 |
|---|---|
| Python 源代码行数 | 19,500+ |
| 测试代码行数 | 17,000+ |
| 测试/源码比 | 0.87 |
| 测试用例数 | 1,830+ |
| 测试通过率 | 100% |
| flake8 警告 | 0 |
| Visitor 方法实现 | 47/47 |
| CI/CD | GitHub Actions (pytest + flake8 + coverage) |
| 综合质量评分 | 7.93/10 (7 维评估法) |
