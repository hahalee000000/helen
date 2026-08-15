# Helen Language Wiki Index

> **Helen** — A Prompt-first Agent Programming Language
> [![PyPI version](https://img.shields.io/pypi/v/helen-lang.svg)](https://pypi.org/project/helen-lang/)
> Version: v1.40.1 | Status: Published on PyPI (`pip install helen-lang`) | Provider auto-detection + connectivity probing + AI-native debugging toolkit + Explicit stdlib import + 22 stdlib modules + Chinese Syntax | Tests: 3806+ passed

---

## 📖 Quick Navigation

### 1. Language Overview
- [[overview/design-philosophy|Design Philosophy]] — Why we need an Agent programming language
- [[overview/language-spec|Language Specification]] — 99 keywords (48 English + 51 Chinese), Tokens, AST nodes at a glance
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
- [[runtime/llm-runtime|LLM Runtime]] — route/act interface, cancellation mechanism, platform protocol abstraction (v1.35), thinking mode support (v1.36), provider auto-detection & connectivity probing (v1.40.1)
- [[runtime/prompt-builder|Prompt Building]] — Two-layer progressive disclosure, template rendering
- [[runtime/memory|Memory System]] — FileMemoryProvider, InMemoryProvider
- [[runtime/transcript-store|TranscriptStore SSOT]] — Single source of truth for messages, SQLite/JSONL backends, LRU cache, UUID addressing, non-destructive compression (**v1.16 new feature**); `search_transcript()` content search (**v1.22 new feature**); `session_meta` session metadata — argv, startup time, version info (**v1.23.3 new feature**)
- [[runtime/session-scoping|Session Scoping]] — Project vs global scope, `.helen/` marker auto-creation, `HELEN_SESSION_DIR` override, memento format (**v1.29 new**)
- [[runtime/context-management|Context Management Architecture]] — Design philosophy (Context vs Transcript, four-layer lifecycle), unified entry point, three-channel, graduated compression, cache-aware, working memory (**authoritative document**)
- [[runtime/context-compression-research|Context Compression Research]] — Academic references: RCC, CogCanvas, DAST, etc.
- [[runtime/history|History Management]] — Token budget, truncation strategy, conversation_summary
- [[runtime/import|Module System]] — Multi-format import, circular detection, path safety
- [[runtime/skills|Skill System]] — Three-layer search architecture, two-layer disclosure mechanism
- [[runtime/working_memory|Working Memory]] — v1.25 system prompt-based approach: LLM proactively maintains context via `<working_memory>` block (**v1.25 new feature**)
- [[runtime/mcp-integration|MCP Integration]] — Model Context Protocol client support, external tool discovery and invocation, multi-server management (**v1.33 new feature**)
- [[runtime/llm-provider-protocol-reference|LLM Provider Protocol Reference]] ⭐ — Complete OpenAI-compatible protocol across 6 providers: Qwen, Zhipu, DeepSeek, Minimax, Kimi, Doubao. Full conversation lifecycle: auth → request → streaming → tool calling → reasoning → multi-turn → error handling. Provider auto-detection & custom adapters (v1.40.1)

> Note: Content from `runtime/graduated_compression`, `runtime/cache_aware_compression`, and `runtime/agent_context` has been merged into `runtime/context-management`. Old pages archived to `_archive/`. `working_memory` has been rewritten with the v1.25 approach.

### 6. Toolchain
- [[toolchain/cli|Command-Line Tools]] — `helen <file>/check/test/quality/repl/doc/init/provider/lsp/template`
- [[toolchain/testing|Testing Framework]] — TDD support, assertion API, `--watch` mode
- [[toolchain/quality|Quality Assessment]] — 7-dimension framework, security scoring, CI integration
- [[toolchain/lsp|Language Server]] — `helen lsp`, JSON-RPC 2.0, diagnostics/completion/go-to-definition
- [[toolchain/vscode|VS Code Extension]] — Syntax highlighting, LSP integration, code completion, go-to-definition
- [[toolchain/stdlib|Standard Library]] — 364 builtins (351 Chinese aliases) (core/string/data/collection/network/time/math/file/system/crypto/io/test/quality/context/transcript/media/llm)
- [[toolchain/templates|Built-in Template Library]] — `helen template`, complete examples for common agent patterns
- [[toolchain/error-format|Error Formatting]] — HLD 3.11.2 diagnostic output (with smart fix suggestions)

### 7. Beginner Guide (Agent-First)

> **Start here** — pedagogical, linear narrative. Learn Helen's philosophy ("prompts are first-class") before diving into language mechanics.

- [[guide/README|Guide Overview]] — What is Helen, who is this for, skill-driven development
- [[guide/01-hello-agent|Chapter 1: Your First Agent]] — What agents are, how to create and run one
- [[guide/02-prompt|Chapter 2: Prompts — The Soul of Agents]] — Purpose of prompts, template variables, Ground Truth Injection
- [[guide/03-llm-statements|Chapter 3: Talking to LLMs]] — `llm act`, `llm if`, streaming output
- [[guide/04-tools|Chapter 4: Equipping Agents with Tools]] — Tool declarations, callbacks, read/write files
- [[guide/05-basics|Chapter 5: Variables and Data Types]] — Basic types, lists, maps, constants
- [[guide/06-control-flow|Chapter 6: Control Flow]] — if/for/while/match/try-catch
- [[guide/07-functions|Chapter 7: Functions and Closures]] — Function definitions, closures, pipe operator
- [[guide/08-collaboration|Chapter 8: Agent Collaboration]] — Sequential chains, parallel, pipelines, spawn and Channel
- [[guide/09-stdlib|Chapter 9: Standard Library Tour]] — 364 built-in functions categorized
- [[guide/10-testing|Chapter 10: Testing and Debugging]] — Testing framework, assertions, debugging techniques
- [[guide/11-advanced|Chapter 11: Advanced Topics]] — Scope isolation, multimodal, protocols, MCP
- [[guide/appendix|Appendix: Keywords and Quick Reference]] — 99 keywords, error codes, naming conventions

### 8. Language Reference (By Topic)

> **Look things up** — comprehensive, topic-indexed. For when you know what you're looking for.

- [[reference/01-getting-started|Getting Started]] — Installation, configuration, Hello World, REPL
- [[reference/02-variables-and-types|Variables and Types]] — let/const, type annotations
- [[reference/03-functions|Functions]] — fn declarations, parameters, return values
- [[reference/04-control-flow|Control Flow]] — if/for/while/match/try-catch
- [[reference/05-agents|Agent Programming]] — agent declarations, description, prompt
- [[reference/06-llm-statements|LLM Statements]] — act/if in practice
- [[reference/07-spawn|Concurrent Programming]] — spawn, Channel message queue, mailbox_select, explicit sharing
- [[reference/08-modules|Modules and Imports]] — import, cross-file reuse
- [[reference/09-python-ffi|Python FFI]] — Python library imports, type conversion
- [[reference/10-stdlib|Standard Library Reference]] — 364 built-in functions (351 Chinese aliases)
- [[reference/11-building-agents|Building Multi-Agent Systems]] — Complete case study
- [[reference/12-testing|Testing Framework and TDD]] — Assertion API, expect chains, `--watch` mode
- [[reference/13-skills|Skill System]] — Three-layer search, two-layer disclosure, LLM-aware
- [[reference/14-observability|AI-Native Observability]] — assert, debug(), trace, LLM audit
- [[reference/15-python-bridge|Python Bridge]] — Let Python directly use Helen Agents
- [[reference/16-quality-assessment|Quality Assessment]] — 7-dimension framework, security scoring, CI integration
- [[reference/17-multimodal|Multimodal Support]] — MediaPart, on_media/on_generate callbacks, media adaptation (**v1.17 new feature**)
- [[reference/18-helen-agent|Helen Agent Programming Assistant]] — Interactive self-evolving coding assistant, Web UI, ChatSessionActor architecture, skill/memory evolution loop (**v1.26+ new**)
- [[guide/goal-command|/goal Command]] — Autonomous goal pursuit in WebUI, auto-continue loop, LLM self-reporting completion (**v1.44.1 new**)

### 9. Extended References
- [[reference/python-integration|Helen ↔ Python Bidirectional Integration]] ⭐ — Full picture: FFI (Helen → Python) + Bridge (Python → Helen) + hybrid usage patterns
- [[reference/claude-code-context-management|Claude Code Context Management Deep Dive]] — 5-layer graduated compression pipeline, TranscriptStore SSOT, cache-aware
- [[reference/claude-code-budget-reduction-and-context-collapse|Claude Code Budget Reduction and Context Collapse]] — Layer 1-4 zero-cost compression strategies
- [[reference/agent-system-prompt-guide|Agent Prompt Engineering Complete Guide]] ⭐ — Insights from Claude Code reverse engineering: structure layout, writing principles, anti-patterns, Token budget, cache design, mid-stream injection (**v1.17 new**)

### 10. Appendix
- [[appendix/error-codes|Error Code Reference]] — Full list of 42 ErrorCodes
- [[appendix/exceptions|Exception Hierarchy]] — Exception class inheritance tree
- [[appendix/changelog|Version History]] — Changelog from v1.0 to v1.20
- [[appendix/hld-compliance|HLD Compliance]] — 17-module implementation status

### 11. Installation and Publishing
- [PyPI Project Page](https://pypi.org/project/helen-lang/) — `pip install helen-lang`
- [GitHub Repository](https://github.com/hahalee000000/helen) — Source code, issues, discussions
- [[reference/01-getting-started|Getting Started]] — Installation + your first program
