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
pytest                              # Run all 2583+ tests
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
  Lexer (maximal-munch, frozenset O(1) lookup, 97 bilingual keywords)
    → Parser (Pratt precedence + recursive descent)
    → AST (64 frozen dataclass nodes, Visitor pattern)
    → SemanticAnalyzer (two-pass for forward refs, SymbolTable, 14-type system)
    → Interpreter (environment chain, sentinels for control flow)

Layer 2: Runtime (LLM integration)
  LLMRuntime (abstract) → HttpLLMRuntime (httpx connection pool + async, OpenAI-compatible API)
  Tools (10 built-in: web_search, web_fetch, read/write/patch_file, shell_exec, calculate, load_skill, find_files, search_files)
  ImportResolver (.helen/.json/.yaml/.md/.txt/Python), Config, History (with compression)

Layer 3: Toolchain
  CLI (run/check/repl/test/quality/doc/init/lsp)
  REPL (multi-line, :help/:reset/:ask/:agent/:trace/:stats/:llm_log/:last_error)
  LSP (diagnostics, completion, go-to-definition, alias-aware)
  VS Code Extension (syntax highlighting + LSP)
```

## Key Source Layout

```
helen/
├── core/          # lexer.py, parser.py, ast.py, tokens.py, errors.py, source_span.py
├── semantic/      # analyzer.py (two-pass semantic analysis)
├── interpreter/   # interpreter.py, llm_mixin.py (LLM visitor methods), environment.py, exceptions.py
├── runtime/       # llm_runtime.py, http_llm.py, tools.py, config.py, import_resolver.py
│                  # prompt_builder.py (system prompt + skill index), history.py, observability.py
│                  # fuzzy_match.py (9-strategy file patching)
├── stdlib/        # 198+ built-in functions (string, math, crypto, collections, test, quality, context, etc.)
│                  # locales/zh.py (230+ Chinese aliases)
├── ffi/           # Python FFI for importing Python modules from Helen
├── cli/           # __main__.py (entry point), repl.py, formatter.py, docgen.py
├── lsp/           # Language Server Protocol (JSON-RPC 2.0 over stdio)
└── agent/         # Helen assistant program (helen_assistant.helen)

skills/            # 16 built-in skills (SKILL.md + references/)
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
  - `channel Name { fields, methods }` — inter-agent communication endpoints (same runtime as store)
  - Chinese keywords: `仓库` (store), `通道` (channel)
  - `_` prefix fields are private (inaccessible from agent code)
- **ReadOnlyView (v1.12)**: Immutable wrapper for agent parameters
  - Blocks all mutation attempts → raises `ScopeViolationError`
  - Supports `__getitem__`, `__len__`, `__iter__`, `__contains__`, `__bool__`, `__str__`, comparison operators, `__add__`, `__radd__`, `__hash__`
  - Nested iterables auto-wrapped on iteration
  - dict methods: `keys()`, `values()`, `items()`, `get()`
- **Agent scope isolation (v1.10)**: `agent main {}` runs in isolated environment. Module-level `let` is **not** visible inside agent main (compile-time error). Module-level `const` is auto-visible (read-only sharing). Use `shared let` for cross-agent visible mutable variables. Closures in agent main can capture local variables.
- **Closure value capture**: Closures capture a **deep copy** of reference-type variables (snapshot semantics, immune to subsequent modifications)
- **LLM primitives**: `llm act` (tool-calling loop + optional streaming via on_chunk/on_complete callbacks since v1.14, usable as expression since v1.10), `llm if` (LLM-routed branching)
  - v1.14: `llm stream` **deleted** — streaming merged into `llm act` with optional callbacks
  - Syntax: `llm act "prompt" on_chunk fn(chunk) {...} on_complete fn() {...}`
- **Async/await**: `async call` for concurrent agent execution, `await [list]` for Promise.all. HTTP layer has true async: `act_async()` / `act_stream_async()` via `httpx.AsyncClient` (v1.10)
- **Short-circuit evaluation (v1.10)**: `&&` and `||` short-circuit
- **Type system**: 14 types including Optional (`str?`), Union (`int | str`), Protocol, Agent, Literal. Return type annotation uses `:` syntax only (`fn foo(): int {}`); `->` syntax removed (v1.10)
- **Pattern matching**: `match` with range, wildcard, variable binding, type patterns
- **Exception hierarchy**: `AnyError → LLMError → TimeoutError/ModelError/AgentError`, `ToolError`, `RuntimeError` (including wrapped stdlib Python exceptions since v1.10), `AssertionError`, `AggregateError`, `ScopeViolationError`
- **Imports**: Multi-format (`.helen`, `.json`, `.yaml`, `.md`, `.txt`, Python), circular detection; imported `shared let` tracked correctly since v1.10
- **Chinese support**: 97 bilingual keywords (48.5 English + 48.5 Chinese) with full bilingual support (CJK identifiers, fullwidth punctuation since v1.10, Chinese quotes since v1.10)
- **Subscript/field assignment (v1.10)**: `arr[i] = x` and `obj.field = x` are supported as assignment targets
- **Alias statement (v1.10)**: `alias <canonical> as <alias_name>` / `别名 <canonical> 为 <alias_name>` — create aliases for stdlib, user functions, agents, and variables
- **Context management (v1.12)**: `clear_context()` clears conversation history; `compress_context(strategy)` with strategies: `auto`, `summarize`, `truncate`, `none`
- **Context enhancement (v1.15, Phase 1-7)**:
  - **Working Memory**: Automatically tracks active files, recent decisions, pending TODOs, error history
  - **Graduated Compression**: Five-layer progressive compression (Layer 1-5, from 60% to 95% usage)
  - **Cache-Aware Compression**: Preserves stable prefix (30%), improves cache hit rate from 10-20% to 70-80%
  - **Three-Channel Context**: System instructions (15%) + Working memory (50%) + Conversation history (35%)
  - **Agent context configuration**: `context { compression "graduated" cache-aware true working-memory true working-memory-tokens 5000 }`

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
- `interpreter/` — Interpreter, async, isolation (v1.12)
- `execution/` — End-to-end (agents, async, control flow, functions, imports, match, exceptions, v1.12 isolation)
- `runtime/` — LLM runtime, tools, memory, history, config, imports, working memory, graduated compression, cache-aware compression
- `stdlib/` — Standard library functions, context management
- `language/` — Feature tests (v16-v18: pattern matching, closures, protocols)
- `performance/` — Benchmarks
- `integration/` — Full agent integration
- `lsp/` — Language Server
- `cli/` — CLI and REPL

**2583+ tests passing** (Python pytest)

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
