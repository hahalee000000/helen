# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in the **Helen** repo.
For the broader multi-project layout, see `../CLAUDE.md`.

## Overview

**Helen** — a prompt-first Agent programming language (AI-native DSL, currently v1.15).
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
pytest                              # Run all 2395+ tests
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
```

## Architecture (3-layer pipeline)

```
Layer 1: Helen Core (pure language)
  Lexer (maximal-munch, frozenset O(1) lookup, 92 keywords: 46 EN + 46 CN)
    → Parser (Pratt precedence + recursive descent)
    → AST (65+ frozen dataclass nodes, Visitor pattern)
    → SemanticAnalyzer (two-pass for forward refs, SymbolTable, 14-type system, agent isolation checks)
    → Interpreter (environment chain, sentinels for control flow)

Layer 2: Runtime (LLM integration)
  LLMRuntime (abstract) → HttpLLMRuntime (httpx connection pool + async, OpenAI-compatible API, retry w/ backoff)
  PromptBuilder (single source of truth for prompt construction, template rendering, Skill Index injection)
  Tools (7 built-in: web_search[Bing], web_fetch[gzip], read/write/patch_file, shell_exec[/bin/bash], calculate)
  HistoryManager (token estimation, compression: summarize/truncate/none, persistence, retrieval)
  ImportResolver (.helen/.json/.yaml/.md/.txt/Python), Config, Memory

Layer 3: Toolchain
  CLI (run/check/repl/test/quality/doc/init/lsp)
  REPL (multi-line, :help/:reset/:ask/:agent/:trace/:stats commands)
  LSP (diagnostics, completion, go-to-definition)
  VS Code Extension (syntax highlighting + LSP)
```

## Key Source Layout

```
helen/
├── core/          # lexer.py, parser.py, ast.py, tokens.py, errors.py, source_span.py
├── semantic/      # analyzer.py (two-pass semantic analysis, agent isolation checks), symbols.py
├── interpreter/   # interpreter.py, llm_mixin.py (LLM visitor methods), environment.py, exceptions.py
├── runtime/       # llm_runtime.py, http_llm.py, tools.py, config.py, import_resolver.py, prompt_builder.py, history.py
├── stdlib/        # 185+ built-in functions (string, math, crypto, collections, test, context, etc.)
├── ffi/           # Python FFI for importing Python modules from Helen
├── cli/           # __main__.py (entry point), repl.py, formatter.py, docgen.py
├── lsp/           # Language Server Protocol (JSON-RPC 2.0 over stdio)
└── agent/         # Helen assistant program
```

## Language Concepts

- **Agent declarations**: First-class `agent` blocks with description, model, temperature, tools, prompt template (`{{var}}`), `functions {}` block (becomes LLM-callable tools), and `main {}` logic
- **Agent scope isolation (v1.12)**: Three isolation levels via decorators:
  - `@open` (L0): Can access module-level `let` (for debugging). Default in earlier versions.
  - Standard (L1, default): `agent main {}` runs in isolated environment. Module-level `let` is **not** visible (compile-time error). Module-level `const` is auto-visible (read-only). Use `shared let` for cross-agent mutable variables.
  - `@strict` (L2): Standard + read-only parameter wrapping (list/dict params auto-wrapped in `ReadOnlyView`).
  - `@sandbox` (L3): No tools at all (not even `load_skill`). Full isolation.
  - Closures in agent main capture values (snapshot), not environment references.
- **Shared store (v1.12)**: `shared store Name { fields, methods }` — cross-agent mutable state with private fields (`_` prefix convention). Thread-safe method calls.
- **Channel (v1.13)**: `channel`/`通道` declaration — typed, thread-safe inter-agent communication. Structurally identical to shared store but semantically a communication endpoint.
- **LLM primitives**: `llm act` (tool-calling loop + optional streaming via `on_chunk`/`on_complete` callbacks, usable as expression since v1.10). **Breaking (v1.14)**: `llm stream` removed; streaming merged into `llm act`. `llm if` (LLM-routed branching).
- **System/User prompt separation (v1.15)**: Agent prompt rendered as user message; system message contains framework instructions, conventions, description, skill index.
- **Framework instructions (v1.15)**: `<framework_instructions>` block auto-injected into all agent system prompts with P0+P1 behavior rules (MUST use tools, MUST load skills, batch independent calls, working artifact, memory management).
- **Context management (v1.15)**: `clear_context()` and `compress_context(strategy)` stdlib functions for long-running agents. Strategies: `"auto"`, `"summarize"`, `"truncate"`, `"none"`.
- **Async/await**: `async call` for concurrent agent execution, `await [list]` for Promise.all. HTTP layer also has async support: `act_async()` / `act_stream_async()` via `httpx.AsyncClient` (v1.10)
- **Short-circuit evaluation (v1.10)**: `&&` and `||` short-circuit
- **Type system**: 14 types including Optional (`str?`), Union (`int | str`), Protocol, Agent, Literal. Return type annotation uses `:` syntax only (`fn foo(): int {}`); `->` syntax removed (v1.10)
- **Pattern matching**: `match` with range, wildcard, variable binding, type patterns
- **Exception hierarchy (v1.11)**: `AnyError` is the base. `AnyError → LLMError → TimeoutError/ModelError`, `ToolError`, `RuntimeError` (including wrapped stdlib Python exceptions since v1.10, `AgentError` since v1.12), `AssertionError`, `AggregateError`. `catch AnyError` catches all.
- **Imports**: Multi-format (`.helen`, `.json`, `.yaml`, `.md`, `.txt`, Python), circular detection; imported `shared let` tracked correctly since v1.10
- **Chinese support**: 92 keywords with bilingual Chinese/English support (46 EN + 46 CN, CJK identifiers, fullwidth punctuation since v1.10)
- **Subscript/field assignment (v1.10)**: `arr[i] = x` and `obj.field = x` are supported as assignment targets
- **Alias statement (v1.10)**: `alias X as Y`/`别名 X 为 Y` for stdlib multi-language function aliases
- **History persistence (v1.12)**: `save_history(path)` / `load_history(path)` / `clear_history()` / `search_history()` for LLM conversation history

## Configuration

Helen uses `~/.helen/config.yaml`:
```yaml
llm:
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  api_key: "your-key"
  model: "qwen3.7-plus"
```
Also supports `.env` format and falls back to `~/.hermes/.env`.

## Testing Architecture

Tests in `tests/` mirror the source structure:
- `core/` — Lexer, parser, AST, tokens, errors
- `semantic/` — Semantic analyzer, agent scope isolation
- `interpreter/` — Interpreter, async
- `execution/` — End-to-end (agents, async, control flow, functions, imports, match, exceptions, v1.12 isolation, shared let writeback)
- `runtime/` — LLM runtime, tools, memory, history, config, imports, context protection
- `stdlib/` — Standard library functions, context management, aliases
- `language/` — Feature tests (v16-v18: pattern matching, closures, protocols)
- `performance/` — Benchmarks
- `integration/` — Full agent integration
- `lsp/` — Language Server
- `cli/` — REPL commands (including `:ask`, `:stats`)

Helen also has a built-in test framework (`helen/stdlib/test.py`) with `test()`, `assert_equal()`, `assert_true()`, `assert_throws()`, suites, filtering, JSON output, and watch mode.
