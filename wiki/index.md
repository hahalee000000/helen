# Helen Language Wiki Index

> **Helen** — A Prompt-first Agent Programming Language
> [![PyPI version](https://img.shields.io/pypi/v/helen-lang.svg)](https://pypi.org/project/helen-lang/)
> Version: v1.22 | Status: Published on PyPI (`pip install helen-lang`) | Invocation Tree + Per-Main Fresh Context + search_transcript + Context Management API + Transcript Scoping + spawn Concurrency + Chinese Syntax | Tests: 3037+ passed

---

## 📖 Quick Navigation

### 1. Language Overview
- [[overview/design-philosophy|Design Philosophy]] — Why we need an Agent programming language
- [[overview/language-spec|Language Specification]] — 89 keywords (44.5 English + 44.5 Chinese), Tokens, AST nodes at a glance
- [[overview/architecture|Overall Architecture]] — 3-layer architecture (Core / Runtime / Toolchain)

### 2. Frontend Compilation
- [[syntax/lexical|Lexical Analysis]] — 89 Token types, Maximal Munch, triple-quoted strings, CJK character set
- [[syntax/grammar|Grammar Specification]] — Full EBNF grammar, Pratt Parsing with 10 precedence levels
- [[syntax/keywords|Keyword Reference]] — 89 keywords categorized with usage (includes Chinese keyword mapping table)

### 3. Intermediate Representation and Semantics
- [[compiler/ast|AST Node Definitions]] — 50 node classes, Visitor pattern (47 methods)
- [[compiler/semantic|Semantic Analysis]] — Symbol table, scoping, type checking
- [[compiler/types|Type System]] — 14 types, gradual type checking

### 4. Interpretive Execution
- [[interpreter/execution|Execution Engine]] — AST traversal interpreter, Environment scope chain
- [[interpreter/llm-integration|LLM Integration]] — `llm act/if`, conversation history
- [[interpreter/spawn|Concurrency and spawn]] — `spawn`, Channel message queue, mailbox_select

### 5. Runtime Systems
- [[runtime/llm-runtime|LLM Runtime]] — route/act interface, cancellation mechanism
- [[runtime/prompt-builder|Prompt Building]] — Two-layer progressive disclosure, template rendering
- [[runtime/memory|Memory System]] — FileMemoryProvider, InMemoryProvider
- [[runtime/transcript-store|TranscriptStore SSOT]] — Single source of truth for messages, SQLite/JSONL backends, LRU cache, UUID addressing, non-destructive compression (**v1.16 new feature**); `search_transcript()` content search (**v1.22 new feature**); `session_meta` session metadata — argv, startup time, version info (**v1.23.3 new feature**)
- [[runtime/context-management|Context Management Architecture]] — Design philosophy (Context vs Transcript, four-layer lifecycle), unified entry point, three-channel, graduated compression, cache-aware, working memory (**authoritative document**)
- [[runtime/context-compression-research|Context Compression Research]] — Academic references: RCC, CogCanvas, DAST, etc.
- [[runtime/history|History Management]] — Token budget, truncation strategy, conversation_summary
- [[runtime/import|Module System]] — Multi-format import, circular detection, path safety
- [[runtime/skills|Skill System]] — Three-layer search architecture, two-layer disclosure mechanism
- [[runtime/working_memory|Working Memory]] — v1.25 system prompt-based approach: LLM proactively maintains context via `<working_memory>` block (**v1.25 new feature**)

> Note: Content from `runtime/graduated_compression`, `runtime/cache_aware_compression`, and `runtime/agent_context` has been merged into `runtime/context-management`. Old pages archived to `_archive/`. `working_memory` has been rewritten with the v1.25 approach.

### 6. Toolchain
- [[toolchain/cli|Command-Line Tools]] — `helen <file>/check/test/quality/repl/doc/init/lsp/template`
- [[toolchain/testing|Testing Framework]] — TDD support, assertion API, `--watch` mode
- [[toolchain/quality|Quality Assessment]] — 7-dimension framework, security scoring, CI integration
- [[toolchain/lsp|Language Server]] — `helen lsp`, JSON-RPC 2.0, diagnostics/completion/go-to-definition
- [[toolchain/vscode|VS Code Extension]] — Syntax highlighting, LSP integration, code completion, go-to-definition
- [[toolchain/stdlib|Standard Library]] — 287 builtins (287 Chinese aliases) (core/string/data/collection/network/time/math/file/system/crypto/io/test/quality/context/transcript/media)
- [[toolchain/templates|Built-in Template Library]] — `helen template`, complete examples for common agent patterns
- [[toolchain/error-format|Error Formatting]] — HLD 3.11.2 diagnostic output (with smart fix suggestions)

### 7. Tutorials
- [[tutorial/01-getting-started|Getting Started]] — Installation, configuration, Hello World, REPL
- [[tutorial/02-variables-and-types|Variables and Types]] — let/const, type annotations
- [[tutorial/03-functions|Functions]] — fn declarations, parameters, return values
- [[tutorial/04-control-flow|Control Flow]] — if/for/while/match/try-catch
- [[tutorial/05-agents|Agent Programming]] — agent declarations, description, prompt
- [[tutorial/06-llm-statements|LLM Statements]] — act/if in practice
- [[tutorial/07-spawn|Concurrent Programming]] — spawn, Channel message queue, mailbox_select, explicit sharing
- [[tutorial/08-modules|Modules and Imports]] — import, cross-file reuse
- [[tutorial/09-python-ffi|Python FFI]] — Python library imports, type conversion
- [[tutorial/10-stdlib|Standard Library Reference]] — 287 built-in functions (287 Chinese aliases)
- [[tutorial/11-building-agents|Building Multi-Agent Systems]] — Complete case study
- [[tutorial/12-testing|Testing Framework and TDD]] — Assertion API, expect chains, `--watch` mode
- [[tutorial/13-skills|Skill System]] — Three-layer search, two-layer disclosure, LLM-aware
- [[tutorial/14-observability|AI-Native Observability]] — assert, debug(), trace, LLM audit
- [[tutorial/15-python-bridge|Python Bridge]] — Let Python directly use Helen Agents
- [[tutorial/16-quality-assessment|Quality Assessment]] — 7-dimension framework, security scoring, CI integration
- [[tutorial/17-multimodal|Multimodal Support]] — MediaPart, on_media/on_generate callbacks, media adaptation (**v1.17 new feature**)

### 8. References
- [[reference/python-integration|Helen ↔ Python Bidirectional Integration]] ⭐ — Full picture: FFI (Helen → Python) + Bridge (Python → Helen) + hybrid usage patterns
- [[reference/claude-code-context-management|Claude Code Context Management Deep Dive]] — 5-layer graduated compression pipeline, TranscriptStore SSOT, cache-aware
- [[reference/claude-code-budget-reduction-and-context-collapse|Claude Code Budget Reduction and Context Collapse]] — Layer 1-4 zero-cost compression strategies
- [[reference/agent-system-prompt-guide|Agent Prompt Engineering Complete Guide]] ⭐ — Insights from Claude Code reverse engineering: structure layout, writing principles, anti-patterns, Token budget, cache design, mid-stream injection (**v1.17 new**)

### 9. Appendix
- [[appendix/error-codes|Error Code Reference]] — Full list of 42 ErrorCodes
- [[appendix/exceptions|Exception Hierarchy]] — Exception class inheritance tree
- [[appendix/changelog|Version History]] — Changelog from v1.0 to v1.20
- [[appendix/hld-compliance|HLD Compliance]] — 17-module implementation status

### 10. Installation and Publishing
- [PyPI Project Page](https://pypi.org/project/helen-lang/) — `pip install helen-lang`
- [GitHub Repository](https://github.com/hahalee000000/helen) — Source code, issues, discussions
- [[tutorial/01-getting-started|Getting Started]] — Installation + your first program
