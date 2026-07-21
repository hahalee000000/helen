# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in the **Helen** repo.
For the broader multi-project layout, see `../CLAUDE.md`.

## Overview

**Helen** — a prompt-first Agent programming language (AI-native DSL).
Combines deterministic constructs (variables, functions, control flow) with
first-class LLM primitives (`llm act`, `llm if`).

## Development Commands

```bash
uv pip install -e .                 # Install in editable mode (Python 3.12+, using uv)
uv pip install -e ".[dev]"          # Install dev dependencies (pytest, flake8)
# 或者使用传统 pip
pip install -e .                    # Install in editable mode (Python 3.12+)
pip install -e ".[dev]"             # Install dev dependencies (pytest, flake8)

# Running programs
helen <file.helen>              # Execute a Helen program
helen check <file.helen>        # Validate syntax/semantics without executing
helen repl                      # Interactive REPL

# Testing
pytest                              # Run all 2791+ tests
pytest tests/core/                  # Run tests for a specific module
pytest tests/execution/test_functions.py::test_function_call -v  # Single test
helen test <file.helen>             # Run Helen's built-in test framework
helen test <file.helen> --only "name" --suite "suite"  # Filtered test run

# Quality & tooling
flake8 helen/                       # Lint (max-line-length=120, E501 ignored)
helen quality <file.helen>          # 7-dimension quality assessment
helen doc <file.helen>              # Generate documentation
helen lsp                           # Start Language Server (JSON-RPC over stdio)
helen init                          # Initialize ~/.helen/ config directory
helen template                      # List built-in code templates
helen template <name>               # Show template content
helen template <name> --copy        # Copy template to current directory
```

## Architecture (3-layer pipeline)

```
Layer 1: Helen Core (pure language)
  Lexer (maximal-munch, frozenset O(1) lookup, 89 bilingual keywords)
    → Parser (Pratt precedence + recursive descent)
    → AST (64 frozen dataclass nodes, Visitor pattern)
    → SemanticAnalyzer (two-pass for forward refs, SymbolTable, 14-type system)
    → Interpreter (environment chain, sentinels for control flow, mixin-based architecture)

Layer 2: Runtime (LLM integration)
  LLMRuntime (abstract) → HttpLLMRuntime (httpx connection pool, OpenAI-compatible API)
  Tools (11 built-in: web_search, web_fetch, read/write/patch_file, shell_exec, calculate, load_skill, list_skill_references, find_files, search_files)
  ImportResolver (.helen/.json/.yaml/.md/.txt/Python), Config, History (with compression)
  TranscriptStore (v1.16: SSOT for all messages, SQLite/JSONL backends, LRU cache, UUID addressing)

Layer 3: Toolchain
  CLI (run/check/repl/test/quality/doc/init/lsp)
  REPL (multi-line, :help/:reset/:ask/:agent/:trace/:stats/:llm_log/:last_error/:transcript/:sessions/:session_id)
  LSP (diagnostics, completion, go-to-definition, alias-aware)
  VS Code Extension (syntax highlighting + LSP)
```

## Key Source Layout

```
helen/
├── core/          # lexer.py, parser.py, ast.py, tokens.py, errors.py, source_span.py
├── semantic/      # analyzer.py (two-pass semantic analysis)
├── interpreter/   # interpreter.py (core execution engine, ~2000 lines)
│                  # llm_mixin.py (LLM visitor methods), environment.py, exceptions.py
│                  # pattern_mixin.py (match/case), exception_mixin.py (try/catch)
│                  # import_mixin.py (multi-format imports), streaming_mixin.py (streaming cancel)
│                  # closure.py (Closure + free variable analysis), readonly_view.py (ReadOnlyView)
│                  # shared_store.py (SharedStore + SharedStoreMethod, thread-safe)
├── runtime/       # llm_runtime.py, http_llm.py, tools.py, config.py, import_resolver.py
│                  # prompt_builder.py (system prompt + skill index), history.py, observability.py
│                  # fuzzy_match.py (9-strategy file patching)
│                  # transcript_store.py (v1.16: SSOT, SQLiteBackend, JSONLBackend, LRU cache)
│                  # session_manager.py (v1.16: session lifecycle, path management)
│                  # channel.py (v1.18: Channel + ChannelEndpoint message queue)
├── stdlib/        # 324 built-in functions (21 categories: core, string, math, crypto, etc.)
│                  # Per-category register functions (_register_core, _register_string, etc.)
│                  # locales/zh.py (287 Chinese aliases)
│                  # mailbox.py (v1.18: mailbox_select for multi-channel select)
├── ffi/           # Python FFI for importing Python modules from Helen
├── cli/           # __main__.py (entry point), repl.py, formatter.py, docgen.py
├── lsp/           # Language Server Protocol (JSON-RPC 2.0 over stdio)
├── agent/         # Helen assistant program (helen_assistant.helen)
└── skills/        # 16 built-in skills (SKILL.md + references/) — distributed with the package
    ├── software-development/  # helen-syntax, helen-stdlib, helen-testing, helen-quality,
    │                          # helen-agent-patterns, helen-agent-collaboration,
    │                          # helen-language-development, helen-programming-methodology,
    │                          # code-quality, debugging, plan, tdd, subagent-driven, writing-plans
    └── devops/                # github, hellen-consistency-checker
```

## Language Concepts

- **Agent declarations**: First-class `agent` blocks with description, model, temperature, tools, prompt template (`{{var}}`), `functions {}` block (becomes LLM-callable tools), and `main {}` logic
- **Agent isolation levels (v1.12)**: Three decorator levels control scope access:
  - `@open agent`: Can access and modify module-level `let` (breaks isolation)
  - `@strict agent`: Deep-copies shared let on access (prevents accidental mutation)
  - `@sandbox agent`: Forces `tools=[]` (no external tools, only load_skill)
  - Default (no decorator): Standard isolation — module `let` invisible, `const` auto-visible read-only
- **Shared store & channel (v1.12-v1.13)**: Thread-safe shared state containers
  - `shared store Name { fields, methods }` — mutable shared state with RLock protection
  - `通道` (channel) — Chinese alias for `shared store` (same declaration syntax, same runtime)
  - Chinese keywords: `仓库` (store), `通道` (channel alias)
  - `_` prefix fields are private (inaccessible from agent code)
- **Channel message queue (v1.18)**: `spawn` returns a Channel (mailbox) for message-passing concurrency
  - `spawn Agent(...)` — spawns agent, returns Channel immediately
  - Channel methods: `send(msg)`, `receive()`, `try_receive()`, `cancel()`, `close()`
  - `mailbox_select([m1, m2])` — multi-channel select (first-ready wins)
  - Chinese aliases: `发送()`, `接收()`, `尝试接收()`, `取消()`, `关闭()`
  - **Streaming interrupt (v1.18)**: `on_chunk` callback return `false` to stop streaming; Ctrl+C during streaming interrupts and preserves REPL state; `spawn` + `Channel.cancel()` can interrupt background agent streaming
  - **Stdlib**: `cancel_llm_call()`, `current_llm_call_id()`, `cancel_all_llm_calls()`
  - **中文别名**: `取消大模型调用`, `当前大模型调用id`, `取消所有大模型调用`
- **ReadOnlyView (v1.12)**: Immutable wrapper for agent parameters
  - Blocks all mutation attempts → raises `ScopeViolationError`
  - Supports `__getitem__`, `__len__`, `__iter__`, `__contains__`, `__bool__`, `__str__`, comparison operators, `__add__`, `__radd__`, `__hash__`
  - Nested iterables auto-wrapped on iteration
  - dict methods: `keys()`, `values()`, `items()`, `get()`
- **🎯 第一原则：调用者决定上下文（Caller Decides Context）**：**调用 agent 前必须显式考虑要向 agent 提供什么上下文**。Agent 是严格隔离的——每次调用都创建独立执行环境，**不会自动继承**调用者的变量、历史、LLM 上下文。所有信息必须通过参数、`shared store`、`const` 或 Channel 显式传递。这是 Helen "显式优于隐式" 哲学在多 agent 协作中的核心体现。设计多 agent 系统时，第一步是画出上下文流图（调用者 → 参数/SharedStore/Channel → agent）。详见 `helen-agent-collaboration` §"设计原则：调用者决定上下文" 和 `helen-programming-methodology` §5 "上下文接力模式"
- **Agent scope isolation (v1.10)**: `agent main {}` runs in isolated environment. Module-level `let` is **not** visible inside agent main (compile-time error). Module-level `const` is auto-visible (read-only sharing). Use `shared let` for cross-agent visible mutable variables. Closures in agent main can capture local variables.
- **Closure value capture**: Closures capture a **deep copy** of reference-type variables (snapshot semantics, immune to subsequent modifications)
- **LLM primitives**: `llm act` (tool-calling loop + optional callbacks, usable as expression since v1.10), `llm if` (LLM-routed branching)
  - v1.14: `llm stream` **deleted** — streaming merged into `llm act` with optional callbacks
  - v1.17: 新增 `on_media` / `on_generate` / `provider` 子句，支持多模态输入与文生图/视频
  - v1.21: 新增 `on_tool_end fn(name, result)` 回调——在每个工具执行后调用，返回 str/dict 注入 hint 到下一次 LLM 调用，返回 null 不注入。用于 agentic loop 中间引导 LLM 方向。Hint 自动持久化到 TranscriptStore，可通过 `:transcript` 查看
  - Syntax: `llm act "prompt" [media(...)] [provider("...")] [on_media fn(...)] [on_generate fn(...)] [on_chunk fn(...)] [on_complete fn(...)] [on_tool_end fn(...)]`
  - 中文别名：`逐块处理`(on_chunk)、`完成`(on_complete)、`工具结束`(on_tool_end)、`处理媒体`(on_media)、`生成`(on_generate)
- **Multimodal support (v1.17)**: 回调即适配器——协议差异由用户回调处理，Helen 核心不内置 provider 格式
  - **`media()` stdlib 函数**：普通函数（非关键字），返回 `MediaPart` 对象，自动识别文件路径/URL/base64
  - **`MediaPart` 数据类型**：一等公民，可赋值、传参、存入列表；字段：`source`/`content`/`mime`/`media_type`/`metadata`
  - **`on_media fn(parts, provider)`**：多模态输入适配器，将 `MediaPart` 列表转换为 provider 特定格式（Content Parts）；不指定时使用默认 OpenAI 兼容适配器
  - **`on_generate fn(params)`**：将生成能力注册为工具，LLM 在工具循环中决定是否调用；支持文生图、文生视频等，协议差异完全由回调处理
  - **设计原则**：协议未统一时不固化进语法；未来新模态/新协议无需修改语言核心，用户更新回调或 skill 即可
  - **配套 skill**：`multimodal-providers` 提供各主流 provider（OpenAI/Claude/Gemini/Seedance/Kling 等）的标准回调写法模板
  - **中文别名**：`媒体()`, `媒体base64()`, `是媒体()`, `媒体类型()`, `处理媒体 fn(...)`, `生成 fn(...)`
- **spawn + Channel (v1.18)**: `spawn Agent(...)` spawns an agent and returns a Channel (mailbox) immediately. The spawned agent runs in an isolated environment with a deep-copied snapshot of ALL variables (including SharedStore). Inter-agent data sharing is done explicitly by passing SharedStore references through Channel messages. `mailbox_select([m1, m2, ...])` provides multi-channel select (first-ready wins). Old async/await/detach keywords and `channel X { fields }` declaration syntax removed (v1.18).
- **Short-circuit evaluation (v1.10)**: `&&` and `||` short-circuit
- **Type system**: 14 types including Optional (`str?`), Union (`int | str`), Protocol, Agent, Literal. Return type annotation uses `:` syntax only (`fn foo(): int {}`); `->` syntax removed (v1.10)
- **Pattern matching**: `match` with range, wildcard, variable binding, type patterns
- **Exception hierarchy**: `AnyError → LLMError → TimeoutError/ModelError/AgentError`, `ToolError`, `RuntimeError` (including wrapped stdlib Python exceptions since v1.10), `AssertionError`, `AggregateError`, `ScopeViolationError`
- **Imports**: Multi-format (`.helen`, `.json`, `.yaml`, `.md`, `.txt`, Python), circular detection; imported `shared let` tracked correctly since v1.10
- **Chinese support**: 89 bilingual keywords (44.5 English + 44.5 Chinese) with full bilingual support (CJK identifiers, fullwidth punctuation since v1.10, Chinese quotes since v1.10)
- **Subscript/field assignment (v1.10)**: `arr[i] = x` and `obj.field = x` are supported as assignment targets
- **Alias statement (v1.10)**: `alias <canonical> as <alias_name>` / `别名 <canonical> 为 <alias_name>` — create aliases for stdlib, user functions, agents, and variables
- **Context management (v1.12, v1.19)**: `clear_context()` clears conversation history; `compress_context(strategy)` with strategies: `auto`, `summarize`, `truncate`, `none`. v1.19 adds 24 new stdlib functions covering 6 dimensions: Inspection (`context_stats`, `context_usage`), Working Memory (`working_memory_get/set/remove/clear`), Fine-grained Mutation (`insert/replace/delete/pin/unpin_message`), Runtime Config (`set_compression_strategy/set_context_window/set_working_memory_enabled/set_cache_aware/get_context_config`), Query (`search_context/context_slice`), Multi-Agent Transfer (`export/import/fork_context`), Lifecycle Hooks (`on_compression/on_context_overflow`). Pinned messages are immune to all 5 graduated compression layers. `classify_message` internalized (no longer public).
- **Context enhancement (v1.15, Phase 1-7)**:
  - **Working Memory**: Automatically tracks active files, recent decisions, pending TODOs, error history
  - **Graduated Compression**: Five-layer progressive compression (Layer 1-5, from 60% to 95% usage)
  - **Cache-Aware Compression**: Preserves stable prefix (30%), improves cache hit rate from 10-20% to 70-80%
  - **Three-Channel Context**: System instructions (15%) + Working memory (50%) + Conversation history (35%)
  - **Agent context configuration**: `context { compression "graduated" cache-aware true working-memory true working-memory-tokens 5000 }`
- **TranscriptStore SSOT (v1.16)**: Single Source of Truth for all conversation messages
  - **Persistent Sessions**: All conversations auto-saved to `~/.helen/sessions/<session_id>/`
  - **Dual Backends**: JSONL (simple, human-readable) or SQLite (WAL mode, indexed, fast)
  - **LRU Cache**: Memory-efficient (configurable `max_memory_items`, default 1000)
  - **UUID Addressing**: O(1) lookups via `get(uuid)`, no list index dependencies
  - **Non-Destructive Compression**: BoundaryMarkers record compression events, full audit trail
  - **View Caching**: Dirty flag + cached view for O(1) reads
  - **REPL Commands**: `:transcript [--full|--audit]`, `:sessions`, `:session_id`
  - **Stdlib Functions**: `get_session_id()`, `get_session_meta()`, `list_sessions()`, `replay_transcript()`, `export_transcript()`, `get_compression_audit()`, `get_session_dir()`, `set_session_dir()`, `delete_session(id)`, `delete_current_session(confirm?)`, `cleanup_sessions(keep_count?, older_than_days?)`
  - **Session Meta (v1.23.3)**: 每个新 transcript 文件的第一行自动写入 `session_meta` 记录，包含 argv（程序名和调用参数）、timestamp（启动时间）、helen_version、python_version、platform、cwd、session_id、session_scope。用于会话识别、审计追踪和调试。通过 `get_session_meta()` stdlib 函数读取。
  - **Session Scope (v1.20)**: transcripts 默认按作用域存储——项目目录 `.helen/sessions/`（检测到 `.helen/`、`helen.yaml`、`helen.toml` 时）或全局 `~/.helen/sessions/`（REPL、脚本）。通过 `session_scope: "auto"|"global"|"project"` 配置，或 `HELEN_SESSION_DIR` 环境变量强制指定路径
  - **Runtime Isolation (设计原则)**: transcript 按 **Interpreter 实例** 隔离，而非按目录绑定。每个 Interpreter 生命周期内 `get_session_id()` 返回相同值；不同 Interpreter 实例各自独立 transcript。具体规则：
    - **同一进程内**多次调用 `get_session_id()` → 相同 ID（属性 getter）
    - **重启程序** → 新 Interpreter → 新 session_id（`session_{timestamp}_{uuid8}`）
    - **`spawn`** → 新建 Interpreter → 新建 session_id 与 transcript 目录
    - **普通 agent 调用**（同进程）→ 共享 Interpreter → 共享 session_id，靠 `invocation_id` 区分
    - **跨运行时继承必须显式编程**：用 `resume_session(parent_sid)` 或 `Channel.send(sid)` 传递，不自动共享。这是"显式优于隐式"的体现，避免并发写入污染与状态混乱
  - **Configuration**:
    ```yaml
    transcript:
      enabled: true              # Default: true (SSOT enabled)
      backend: "sqlite"          # or "jsonl"
      session_scope: "auto"      # "auto" (default) | "global" | "project"
      session_dir: "~/.helen/sessions"          # used when scope=global
      project_session_dir: ".helen/sessions"    # used when scope=project
      max_memory_items: 1000     # LRU cache size
    ```

## Configuration

Helen uses `~/.helen/config.yaml`:
```yaml
llm:
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  api_key: "your-key"
  model: "qwen3.7-plus"

transcript:
  enabled: true
  backend: "sqlite"
  session_scope: "auto"                  # v1.20: "auto" (default) | "global" | "project"
  session_dir: "~/.helen/sessions"       # scope=global 时使用
  project_session_dir: ".helen/sessions" # scope=project 时使用
  max_memory_items: 1000

multimodal:                          # v1.17
  max_media_size_mb: 20              # 单个媒体最大 20MB
  max_media_per_request: 10          # 每次最多 10 个媒体
  video_frame_interval: 1.0          # 默认视频抽帧间隔（秒）
  media_cache_dir: "~/.helen/media_cache"
```
Also supports `.env` format and falls back to `~/.hermes/.env`.

## Testing Architecture

Tests in `tests/` mirror the source structure:
- `core/` — Lexer, parser, AST, tokens, errors
- `semantic/` — Semantic analyzer, agent scope isolation
- `interpreter/` — Interpreter, isolation (v1.12)
- `execution/` — End-to-end (agents, control flow, functions, imports, match, exceptions, v1.12 isolation, v1.18 spawn)
- `runtime/` — LLM runtime, tools, memory, history, config, imports, working memory, graduated compression, cache-aware compression, transcript store, session manager
- `stdlib/` — Standard library functions, context management, transcript functions
- `language/` — Feature tests (v16-v18: pattern matching, closures, protocols)
- `performance/` — Benchmarks
- `integration/` — Full agent integration
- `lsp/` — Language Server
- `cli/` — CLI and REPL

**2791+ tests passing** (Python pytest)

Helen also has a built-in test framework (`helen/stdlib/test.py`) with `test()`, `assert_equal()`, `assert_true()`, `assert_throws()`, expect chains, suites, filtering, JSON output, watch mode, and coverage tracking.

## Skill System (Two-Tier Disclosure)

Helen has its own skill system (similar to Claude Code skills):
- **Tier 1**: Lightweight skill index injected into system prompt (name + description + tags)
- **Tier 2**: Full SKILL.md content loaded on-demand via `load_skill` tool
- Skill locations (priority order):
  1. `<project>/.helen/skills/` (project-level)
  2. `~/.helen/skills/` (user-level)
  3. `<helen-install>/skills/` (built-in — 16 skills)
  4. `~/.hermes/skills/` (Hermes fallback)
- Each skill is a directory with `SKILL.md` (YAML frontmatter + markdown content)
- Skills can have `references/` subdirectory for supplementary documents

## Claude Code Skill Conversion Assessment

Helen's 16 built-in skills can be categorized for Claude Code conversion:

### Helen-Specific Skills (convert for Helen development assistance)
| Skill | Lines | Purpose |
|-------|-------|---------|
| helen-syntax | 967 | Complete language syntax reference (92 keywords, types, expressions) |
| helen-stdlib | 533 | 198 built-in functions reference with examples |
| helen-testing | 589 | Test framework usage, TDD workflow, agent testing |
| helen-quality | 107 | 7-dimension quality assessment guide |
| helen-agent-patterns | 1115 | Agent design patterns (7 patterns + history management) |
| helen-agent-collaboration | 773 | Multi-agent collaboration patterns (6 patterns) |
| helen-language-development | 472 | Language implementation patterns (AST, parser, interpreter extension) |
| helen-programming-methodology | 437 | Contract-first + TDD + quality workflow |
| hellen-consistency-checker | 1040 | Design document consistency checking |

### Generic Skills (already applicable to any project)
| Skill | Lines | Purpose |
|-------|-------|---------|
| code-quality | 403 | 7-dimension scoring, pre-commit verification, parallel cleanup |
| debugging | 302 | Systematic debugging methodology + language-specific tools |
| plan | 339 | Plan mode: write actionable plans without execution |
| test-driven-development | 355 | Strict TDD enforcement (RED-GREEN-REFACTOR) |
| subagent-driven-development | 625 | Execute plans via subagents with 2-stage review |
| writing-plans | 300 | Implementation plan writing craft |
| github | 324 | Complete GitHub workflow (PRs, issues, CI/CD) |

### Conversion Strategy
1. **Direct mapping**: Helen's SKILL.md format is already compatible with Claude Code skill format (both use YAML frontmatter + markdown)
2. **Helen-specific skills** → Create as project skills in `.claude/skills/helen-*` for Helen development
3. **Generic skills** → Already exist in Claude Code ecosystem; no conversion needed
4. **Priority**: helen-syntax, helen-stdlib, helen-testing (most frequently needed for Helen dev)
