# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in the **Helen** repo.
For the broader multi-project layout, see `../CLAUDE.md`.

## Overview

**Helen** — a prompt-first Agent programming language (AI-native DSL). Combines deterministic constructs (variables, functions, control flow) with first-class LLM primitives (`llm act`, `llm if`). 

- **Version**: 1.40.0
- **Keywords**: 99 bilingual (48 English + 51 Chinese)
- **Built-in functions**: 377 stdlib functions (22 categories), 728 total names (with locale aliases)
- **Stdlib modules**: 22 modules (std.core, std.str, std.math, std.list, ...)
- **Tests**: 3806 passing (Python pytest)
- **Python**: 3.12+ required

## Development Commands

```bash
# Installation
uv pip install -e .                 # Install in editable mode
uv pip install -e ".[dev]"          # Install with dev dependencies (pytest, flake8)
uv pip install -e ".[all]"          # Install all optional features

# Running programs
helen <file.helen>              # Execute a Helen program
helen check <file.helen>        # Validate syntax/semantics without executing
helen repl                      # Interactive REPL

# Testing
pytest                              # Run all tests
pytest tests/core/                  # Run tests for a specific module
pytest tests/core/test_lexer.py::test_name  # Run a single test
helen test <file.helen>             # Run Helen's built-in test framework

# Quality & tooling
flake8 helen/                       # Lint (max-line-length=120, E501 ignored)
helen quality <file.helen>          # 7-dimension quality assessment
helen doc <file.helen>              # Generate documentation
helen lsp                           # Start Language Server (JSON-RPC over stdio)
```

## Code Intelligence with codebase-memory-mcp-helen

**MUST use codebase-memory-mcp MCP tools for ALL code queries** — Python AND Helen (`.helen`) code. Do NOT fall back to grep/glob/read for code exploration.

The locally-compiled binary integrates Helen language support (tree-sitter grammar + AST specs for `agent` declarations, `llm act` expressions, imports, etc.). 1760+ Helen nodes are indexed alongside Python code.

### ⚠️ CRITICAL: Always pass `format: "json"` to MCP tools

The MCP server's default output format (TOON tree text) puts data in `content[0].text` with an empty `structuredContent: {}`. Claude Code only reads `structuredContent`, so **all default-format calls return `{}`**. Always pass `format: "json"` to get actual results:

```
search_graph(project="home-rxx-helen", name_pattern="foo", format="json")
trace_path(project="home-rxx-helen", function_name="foo", format="json")
query_graph(project="home-rxx-helen", query="MATCH ...", format="json")
get_architecture(project="home-rxx-helen", format="json")
```

### Mandatory MCP tools:
- Finding function/class definitions → `search_graph` (pass `format: "json"`)
- Understanding who calls a function → `trace_path` (mode=calls, direction=inbound, `format: "json"`)
- Understanding what a function calls → `trace_path` (mode=calls, direction=outbound, `format: "json"`)
- Reading specific function/class source → `get_code_snippet`
- Complex multi-hop queries (call chains, dependencies) → `query_graph` (pass `format: "json"`)
- High-level architecture overview → `get_architecture` (pass `format: "json"`)
- Text search with structural ranking → `search_code`

### When grep/read is acceptable (rare):
- Reading non-code files (markdown, yaml, config, etc.) that aren't indexed
- You already know the EXACT file path AND line number
- MCP server is unavailable or unresponsive

Available tools (in priority order):
- `search_graph` — Find functions, classes, variables, agents (Python + Helen)
- `trace_path` — Trace callers/callees, data flow, cross-service paths
- `get_code_snippet` — Read specific function/class source
- `query_graph` — Cypher queries for complex patterns (call chains, dependencies, hot paths)
- `get_architecture` — High-level architecture overview
- `search_code` — Graph-augmented code search (text pattern + structural ranking)

Project name: `home-rxx-helen`

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

**Key architectural boundaries** (from codebase graph):
- `execution` → `core` (443 calls): test execution depends heavily on core
- `semantic` → `core` (309 calls): semantic analysis built on core
- `stdlib` → `runtime` (266 calls): stdlib functions integrate with runtime
- `interpreter` → `runtime` (237 calls): interpreter uses runtime for LLM

## Key Source Layout

```
helen/
├── core/          # lexer.py, parser.py, ast.py, tokens.py, errors.py, source_span.py
├── semantic/      # analyzer.py (two-pass semantic analysis)
├── interpreter/   # interpreter.py + mixins (llm, pattern, exception, import, streaming)
│                  # environment.py, exceptions.py, closure.py, readonly_view.py, shared_store.py
├── runtime/       # llm_runtime.py, http_llm.py, tools.py, config.py, import_resolver.py
│                  # prompt_builder.py, history.py, observability.py, fuzzy_match.py
│                  # transcript_store.py, session_manager.py, channel.py
│                  # provider_protocol.py, model_capabilities.py, probe.py (v1.40.1)
├── stdlib/        # 364 built-in functions (21 categories), 22 modules
│                  # locales/zh.py (Chinese aliases), mailbox.py (v1.18: mailbox_select)
├── ffi/           # Python FFI
├── cli/           # __main__.py, repl.py, ask_assistant.py, formatter.py, docgen.py
├── lsp/           # Language Server Protocol
├── agent/         # Helen agent components (chat_session_actor, chat_tui, task_manager, etc.)
└── skills/        # 15 built-in skills (distributed with package)
```

## Core Language Concepts

- **🎯 First Principle: Caller Decides Context**: Before calling an agent, explicitly consider what context to provide. Agents are strictly isolated — each invocation creates independent execution environment. All information must be passed explicitly through parameters, `shared store`, `const`, or Channel.

- **Agent declarations**: `agent` blocks with description, model, temperature, tools, prompt template (`{{var}}`), `functions {}` block (LLM-callable tools), `transcript` control (v1.29), and `main {}` logic. Transcript levels: `"none"` (default), `"memory"` (in-memory), `"persistent"` (write to disk).

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

- **Chinese support**: 99 bilingual keywords (48 English + 51 Chinese). Full bilingual support: CJK identifiers, fullwidth punctuation, Chinese quotes.

- **Context management (v1.12, v1.19)**: `clear_context()`, `compress_context(strategy)`. v1.19 adds 24 stdlib functions: working memory, fine-grained mutation, runtime config, query, multi-agent transfer, lifecycle hooks.

- **TranscriptStore SSOT (v1.16)**: Single Source of Truth for all messages. Persistent sessions in `~/.helen/sessions/<session_id>/`. Dual backends (JSONL/SQLite). UUID addressing. Session scope: project (`.helen/sessions/`) or global (`~/.helen/sessions/`).

- **Explicit stdlib import (v1.39)**: Stdlib functions are NOT auto-registered — must `import std.xxx.*` explicitly. Three forms: wildcard (`import std.core.*`), selective (`import std.str.{len, upper}`), namespace (`import std.str as S`). Each function runs in its declaring file's module environment (per-file module_env).

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

Tests in `tests/` mirror source structure: `core/`, `semantic/`, `interpreter/`, `execution/`, `runtime/`, `stdlib/`, `language/`, `performance/`, `integration/`, `lsp/`, `cli/`.

Helen also has built-in test framework (`helen/stdlib/test.py`) with `test()`, `assert_equal()`, `assert_true()`, `assert_throws()`, expect chains, suites, filtering, JSON output.

## Skill Index

Helen has 16 built-in skills. **SSOT is `helen/skills/<category>/<name>/`** — this is what ships with the package and what `load_skill()` loads at runtime. `.claude/skills/<name>/` is a **generated mirror** (via `scripts/sync_skills.sh`) for Claude Code's auto-load; **never edit `.claude/skills/` directly** — changes will be overwritten on next sync.

To add or update a skill: edit `helen/skills/<category>/<name>/SKILL.md`, then run `./scripts/sync_skills.sh` before committing.

Claude Code auto-loads relevant skills based on task context:

**Helen-Specific Skills** (for Helen development):
- `helen-syntax` — Complete language syntax reference (99 keywords, types, expressions)
- `helen-stdlib` — 364 built-in functions reference with examples
- `helen-testing` — Test framework usage, TDD workflow, agent testing
- `helen-quality` — 7-dimension quality assessment guide
- `helen-agent-patterns` — Single agent design patterns (7 patterns)
- `helen-agent-collaboration` — Multi-agent collaboration patterns (6 patterns)
- `helen-custom-provider` — Write custom LLM provider adapters (PlatformProtocol subclasses auto-loaded from `~/.helen/providers/`)
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
- Integrating a new LLM provider → `helen-custom-provider`
- Language development → `helen-language-development`
- Code review → `code-quality`, `helen-quality`
