# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in the **Helen** repo.
For the broader multi-project layout, see `../CLAUDE.md`.

## Overview

**Helen** — a prompt-first Agent programming language (AI-native DSL). Combines deterministic constructs (variables, functions, control flow) with first-class LLM primitives (`llm act`, `llm if`). 91 bilingual keywords (45 English + 46 Chinese), 330 built-in functions, 3241 tests.

## Development Commands

```bash
uv pip install -e .                 # Install in editable mode (Python 3.12+, using uv)
uv pip install -e ".[dev]"          # Install dev dependencies (pytest, flake8)

# Running programs
helen <file.helen>              # Execute a Helen program
helen check <file.helen>        # Validate syntax/semantics without executing
helen repl                      # Interactive REPL

# Testing
pytest                              # Run all 3241 tests
pytest tests/core/                  # Run tests for a specific module
helen test <file.helen>             # Run Helen's built-in test framework

# Quality & tooling
flake8 helen/                       # Lint (max-line-length=120, E501 ignored)
helen quality <file.helen>          # 7-dimension quality assessment
helen doc <file.helen>              # Generate documentation
helen lsp                           # Start Language Server (JSON-RPC over stdio)
```

## Architecture (3-layer pipeline)

```
Layer 1: Helen Core (pure language)
  Lexer → Parser → AST → SemanticAnalyzer → Interpreter

Layer 2: Runtime (LLM integration)
  LLMRuntime → HttpLLMRuntime (OpenAI-compatible API)
  Tools (11 built-in: web_search, web_fetch, read/write/patch_file, shell_exec, calculate, load_skill, list_skill_references, find_files, search_files)
  TranscriptStore (SSOT, SQLite/JSONL backends, LRU cache, UUID addressing)

Layer 3: Toolchain
  CLI (run/check/repl/test/quality/doc/init/lsp)
  REPL (multi-line, :help/:reset/:ask/:agent/:trace/:stats/:llm_log/:last_error/:transcript/:sessions/:session_id)
  LSP (diagnostics, completion, go-to-definition, alias-aware)
```

## Key Source Layout

```
helen/
├── core/          # lexer.py, parser.py, ast.py, tokens.py, errors.py, source_span.py
├── semantic/      # analyzer.py (two-pass semantic analysis)
├── interpreter/   # interpreter.py, llm_mixin.py, environment.py, exceptions.py
│                  # pattern_mixin.py, exception_mixin.py, import_mixin.py, streaming_mixin.py
│                  # closure.py, readonly_view.py, shared_store.py
├── runtime/       # llm_runtime.py, http_llm.py, tools.py, config.py, import_resolver.py
│                  # prompt_builder.py, history.py, observability.py, fuzzy_match.py
│                  # transcript_store.py, session_manager.py, channel.py
├── stdlib/        # 330 built-in functions (21 categories)
│                  # locales/zh.py (329 Chinese aliases)
│                  # mailbox.py (v1.18: mailbox_select)
├── ffi/           # Python FFI
├── cli/           # __main__.py, repl.py, ask_assistant.py, formatter.py, docgen.py
├── lsp/           # Language Server Protocol
├── agent/         # Helen agent components (chat_session_actor, chat_tui, task_manager, etc.)
└── skills/        # 15 built-in skills (distributed with package)
```

## Core Language Concepts

- **🎯 First Principle: Caller Decides Context**: Before calling an agent, explicitly consider what context to provide. Agents are strictly isolated — each invocation creates independent execution environment. All information must be passed explicitly through parameters, `shared store`, `const`, or Channel.

- **Agent declarations**: `agent` blocks with description, model, temperature, tools, prompt template (`{{var}}`), `functions {}` block (LLM-callable tools), `transcript` control (v1.29), and `main {}` logic. Transcript levels: `"none"` (default, no recording), `"memory"` (in-memory only), `"persistent"` (write to disk).

- **Agent isolation levels (v1.12)**: `@open agent` (can access module `let`), `@strict agent` (deep-copies shared let), `@sandbox agent` (forces `tools=[]`). Default: standard isolation — module `let` invisible, `const` auto-visible read-only.

- **Agent scope isolation (v1.10)**: `agent main {}` runs in isolated environment. Module-level `let` not visible (compile-time error). Module-level `const` auto-visible. Use `shared let` for cross-agent mutable variables.

- **Shared store & channel (v1.12-v1.13)**: `shared store Name { fields, methods }` — thread-safe mutable shared state with RLock protection. `_` prefix fields are private.

- **spawn + Channel (v1.18)**: `spawn Agent(...)` spawns agent and returns Channel (mailbox) immediately. Spawned agent runs in isolated environment with deep-copied snapshot. Channel methods: `send(msg)`, `receive()`, `try_receive()`, `cancel()`, `close()`. `mailbox_select([m1, m2])` for multi-channel select.

- **spawn resume (v1.27)**: `spawn Agent(...) resume("<session_id>")` continues previously saved child-session transcript. Cross-process lock prevents concurrent corruption.

- **LLM primitives**: `llm act` (tool-calling loop + callbacks), `llm if` (LLM-routed branching). Callbacks: `on_media`, `on_generate`, `on_chunk`, `on_complete`, `on_tool_end` (v1.21).

- **Multimodal support (v1.17)**: `media()` stdlib function returns `MediaPart` objects. Callbacks as adapters: `on_media fn(parts, provider)`, `on_generate fn(params)`. Design principle: don't hardcode protocols.

- **Type system**: 14 types including Optional (`str?`), Union (`int | str`), Protocol, Agent, Literal. Return type uses `:` syntax (`fn foo(): int {}`).

- **Pattern matching**: `match` with range, wildcard, variable binding, type patterns.

- **Exception hierarchy**: `AnyError → LLMError → TimeoutError/ModelError/AgentError`, `ToolError`, `RuntimeError`, `AssertionError`, `AggregateError`, `ScopeViolationError`.

- **Chinese support**: 91 bilingual keywords (45 English + 46 Chinese). Full bilingual support: CJK identifiers, fullwidth punctuation, Chinese quotes.

- **Context management (v1.12, v1.19)**: `clear_context()`, `compress_context(strategy)`. v1.19 adds 24 stdlib functions: working memory, fine-grained mutation, runtime config, query, multi-agent transfer, lifecycle hooks.

- **TranscriptStore SSOT (v1.16)**: Single Source of Truth for all messages. Persistent sessions in `~/.helen/sessions/<session_id>/`. Dual backends (JSONL/SQLite). UUID addressing. Session scope: project (`.helen/sessions/`) or global (`~/.helen/sessions/`).

## Configuration

Helen uses `~/.helen/config.yaml`:
```yaml
llm:
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  api_key: "your-key"
  model: "qwen3.7-plus"

transcript:
  enabled: true
  backend: "sqlite"          # or "jsonl"
  session_scope: "auto"      # "auto" | "global" | "project"
  session_dir: "~/.helen/sessions"
  max_memory_items: 1000

multimodal:
  max_media_size_mb: 20
  max_media_per_request: 10
```
Also supports `.env` format and falls back to `~/.hermes/.env`.

## Testing Architecture

Tests in `tests/` mirror source structure: `core/`, `semantic/`, `interpreter/`, `execution/`, `runtime/`, `stdlib/`, `language/`, `performance/`, `integration/`, `lsp/`, `cli/`. **3241 tests passing** (Python pytest).

Helen also has built-in test framework (`helen/stdlib/test.py`) with `test()`, `assert_equal()`, `assert_true()`, `assert_throws()`, expect chains, suites, filtering, JSON output.

## Skill Index

Helen has 15 built-in skills in `.claude/skills/`. Claude Code auto-loads relevant skills based on task context:

**Helen-Specific Skills** (for Helen development):
- `helen-syntax` — Complete language syntax reference (91 keywords, types, expressions)
- `helen-stdlib` — 330 built-in functions reference with examples
- `helen-testing` — Test framework usage, TDD workflow, agent testing
- `helen-quality` — 7-dimension quality assessment guide
- `helen-agent-patterns` — Single agent design patterns (7 patterns)
- `helen-agent-collaboration` — Multi-agent collaboration patterns (6 patterns)
- `helen-language-development` — Language implementation patterns (AST, parser, interpreter)
- `helen-programming-methodology` — Contract-first + TDD + quality workflow
- `helen-python-bridge` — Python ↔ Helen integration (FFI + Bridge)

**Generic Skills** (applicable to any project):
- `code-quality` — 7-dimension scoring, pre-commit verification
- `debugging` — Systematic debugging methodology + language-specific tools
- `planning` — Plan mode + implementation plan writing
- `test-driven-development` — Strict TDD enforcement (RED-GREEN-REFACTOR)
- `subagent-driven-development` — Execute plans via subagents with 2-stage review
- `github` — Complete GitHub workflow (PRs, issues, CI/CD)

**When to load skills**:
- Writing Helen code → `helen-syntax`, `helen-stdlib`
- Debugging Helen programs → `debugging`, `helen-agent-patterns`
- Testing → `helen-testing`, `test-driven-development`
- Multi-agent systems → `helen-agent-collaboration`
- Language development → `helen-language-development`
- Code review → `code-quality`, `helen-quality`
