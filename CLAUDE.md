# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is **Helen** — a prompt-first Agent programming language (AI-native DSL).
This CLAUDE.md lives inside the Helen repo root. Related projects on this machine:

| Project | Path | Description |
|---------|------|-------------|
| **Helen** | `./` (current) | Prompt-first Agent programming language (AI-native DSL) |
| **Hermes** | `../work/hermes/` | Self-improving AI agent platform (Docker-deployed) |
| **CoPaw** | `../.copaw/` | Persistent AI agent with memory and personality |
| **Helen Design** | `../project/helen/` | Early design docs and HLD specs for Helen |

## Helen — Primary Project

Helen is a prompt-first DSL for building Agent workflows. It combines deterministic constructs (variables, functions, control flow) with first-class LLM primitives (`llm act`, `llm if`, `llm stream`).

### Development Commands

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
pytest                              # Run all 1850+ tests
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

### Architecture (3-layer pipeline)

```
Layer 1: Helen Core (pure language)
  Lexer (maximal-munch, frozenset O(1) lookup)
    → Parser (Pratt precedence + recursive descent)
    → AST (60+ frozen dataclass nodes, Visitor pattern)
    → SemanticAnalyzer (two-pass for forward refs, SymbolTable, 14-type system)
    → Interpreter (environment chain, sentinels for control flow)

Layer 2: Runtime (LLM integration)
  LLMRuntime (abstract) → HttpLLMRuntime (httpx connection pool + async, OpenAI-compatible API)
  Tools (7 built-in: web_search, web_fetch, read/write/patch_file, shell_exec, calculate)
  ImportResolver (.helen/.json/.yaml/.md/.txt/Python), Config, History, Memory

Layer 3: Toolchain
  CLI (run/check/repl/test/quality/doc/init/lsp)
  REPL (multi-line, :help/:reset/:ask/:agent/:trace commands)
  LSP (diagnostics, completion, go-to-definition)
  VS Code Extension (syntax highlighting + LSP)
```

### Key Source Layout

```
helen/
├── core/          # lexer.py, parser.py, ast.py, tokens.py, errors.py, source_span.py
├── semantic/      # analyzer.py (two-pass semantic analysis)
├── interpreter/   # interpreter.py, llm_mixin.py (LLM visitor methods), environment.py
├── runtime/       # llm_runtime.py, http_llm.py, tools.py, config.py, import_resolver.py
├── stdlib/        # 185+ built-in functions (string, math, crypto, collections, test, etc.)
├── ffi/           # Python FFI for importing Python modules from Helen
├── cli/           # __main__.py (entry point), repl.py, formatter.py, docgen.py
├── lsp/           # Language Server Protocol (JSON-RPC 2.0 over stdio)
└── agent/         # Helen assistant program
```

### Language Concepts

- **Agent declarations**: First-class `agent` blocks with description, model, temperature, tools, prompt template (`{{var}}`), `functions {}` block (becomes LLM-callable tools), and `main {}` logic
- **Agent scope isolation (v1.10)**: `agent main {}` runs in a fully isolated environment. Module-level `let` is **not** visible inside agent main (compile-time error). Module-level `const` is auto-visible (read-only sharing). Use `shared let` for cross-agent visible mutable variables. Closures in agent main can capture local variables.
- **LLM primitives**: `llm act` (tool-calling loop, also usable as expression since v1.10), `llm if` (LLM-routed branching), `llm stream` (chunked responses, also usable as expression returning full text since v1.10)
- **Async/await**: `async call` for concurrent agent execution, `await [list]` for Promise.all. HTTP layer also has async support: `act_async()` / `act_stream_async()` via `httpx.AsyncClient` (v1.10)
- **Short-circuit evaluation (v1.10)**: `&&` and `||` short-circuit
- **Type system**: 14 types including Optional (`str?`), Union (`int | str`), Protocol, Agent, Literal. Return type annotation uses `:` syntax only (`fn foo(): int {}`); `->` syntax removed (v1.10)
- **Pattern matching**: `match` with range, wildcard, variable binding, type patterns
- **Exception hierarchy**: `AnyError → LLMError → TimeoutError/ModelError`, `ToolError`, `RuntimeError` (including wrapped stdlib Python exceptions since v1.10), `AssertionError`, `AggregateError`
- **Imports**: Multi-format (`.helen`, `.json`, `.yaml`, `.md`, `.txt`, Python), circular detection; imported `shared let` tracked correctly since v1.10
- **Chinese support**: 91 keywords with bilingual Chinese/English support (CJK identifiers, fullwidth punctuation since v1.10)
- **Subscript/field assignment (v1.10)**: `arr[i] = x` and `obj.field = x` are supported as assignment targets

### Configuration

Helen uses `~/.helen/config.yaml`:
```yaml
llm:
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  api_key: "your-key"
  model: "qwen3.7-plus"
```
Also supports `.env` format and falls back to `~/.hermes/.env`.

### Testing Architecture

Tests in `tests/` mirror the source structure:
- `core/` — Lexer, parser, AST, tokens, errors
- `semantic/` — Semantic analyzer
- `interpreter/` — Interpreter, async
- `execution/` — End-to-end (agents, async, control flow, functions, imports, match, exceptions)
- `runtime/` — LLM runtime, tools, memory, history, config, imports
- `stdlib/` — Standard library functions
- `language/` — Feature tests (v16-v18: pattern matching, closures, protocols)
- `performance/` — Benchmarks
- `integration/` — Full agent integration
- `lsp/` — Language Server

Helen also has a built-in test framework (`helen/stdlib/test.py`) with `test()`, `assert_equal()`, `assert_true()`, `assert_throws()`, suites, filtering, JSON output, and watch mode.

## Hermes (Docker-deployed)

Hermes Agent (by Nous Research) runs in Docker at `work/hermes/`. Key commands:

```bash
cd ../work/hermes
./deploy.sh                                          # Start container
docker exec -it hermes-agent /bin/bash               # Enter container
docker exec hermes-agent supervisorctl status        # Check services
docker exec hermes-agent tail -f /var/log/supervisor/hermes-gateway.log  # Gateway logs
```

Helen's runtime layer has backward compatibility with Hermes: fallback to `~/.hermes/.env`, fuzzy matching from Hermes (9 strategies), and `hermes_cli_llm.py` for Hermes-compatible LLM interface.

## Environment

- **Python**: 3.12.13 (Helen requires 3.12+)
- **Package Manager**: uv 0.11.26 (10-100x faster than pip)
- **Node.js**: v24.1.0 (via nvm)
- **Rust**: stable-aarch64-unknown-linux-gnu
- **Docker**: Required for Hermes services
- **Platform**: Ubuntu/Kylin ARM64 (aarch64)
