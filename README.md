# Helen

> A Prompt-first Agent Programming Language

Helen is an AI-native DSL for building Agent workflows. It combines deterministic programming constructs (variables, functions, control flow) with first-class LLM primitives (`llm act`, `llm if`, `llm choose`) to make Agent development intuitive and type-safe.

## Quick Start

```bash
git clone https://github.com/hahalee000000/helen.git
cd helen
pip install -e .
```

### Hello, World!

```helen
main {
    print("Hello, World!")
}
```

```bash
$ helen run hello.helen
Hello, World!
```

## CLI Usage

| Command | Description |
|---------|-------------|
| `helen run <file>` | Execute a Helen program |
| `helen check <file>` | Validate syntax and semantics without executing |
| `helen repl` | Start the interactive REPL |
| `helen doc <file>` | Generate documentation |

## Language Features

- **Agent as first-class citizen** — `agent` declarations with description, prompt, model config
- **LLM primitives** — `llm act`, `llm if` (routing with branches), `llm choose` (selection)
- **Async/await** — `async call` for concurrent Agent execution, `await [list]` for Promise.all semantics
- **Type system** — Optional types (`str?`), union types (`int | str`), gradual type checking
- **Import system** — Multi-format imports (`.helen`, `.json`, `.md`), path safety, circular import detection
- **Exception handling** — `try/catch/catch-all/finally` with typed exception matching
- **Standard library** — 24+ built-in functions (core, string, math)
- **Toolchain** — LSP server, VS Code extension, formatter, doc generator

## Project Structure

```
helen/
├── helen/
│   ├── core/          # Lexer, Parser, AST, SourceSpan, Errors
│   ├── semantic/      # SemanticAnalyzer, SymbolTable, TypeSystem
│   ├── interpreter/   # AST Interpreter, Environment, Sentinels
│   ├── runtime/       # Runtime API, Memory, ImportResolver, LLM, History
│   ├── stdlib/        # Built-in functions
│   ├── cli/           # CLI entry point, REPL, Formatter, DocGen
│   └── lsp/           # Language Server Protocol
├── tests/             # 886 unit + integration tests
├── docs/              # Documentation & tutorials
└── extensions/        # VS Code extension
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Helen Core (纯语言层)               │
│  Lexer → Parser → SemanticAnalyzer → AST        │
│                                    ↓            │
│                              Interpreter        │
└─────────────────────┬───────────────────────────┘
                      │ Runtime API
┌─────────────────────┴───────────────────────────┐
│        Helen Hermes Runtime (默认适配层)          │
│  Prompt Builder / LLM Runtime / Memory / Tools   │
│  History Manager / Structured Output / Import    │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────┐
│              Toolchain (工具链层)                 │
│  CLI / REPL / LSP / VS Code Extension / DocGen   │
└─────────────────────────────────────────────────┘
```

## Documentation

- 📖 **[Complete Tutorial](docs/tutorial.md)** — 10 chapters from beginner to multi-Agent systems
- 📋 [HLD v1.2.1](../documents/Hellen_High_Level_Design_v1.2.md) — High-Level Design Specification

## Status

| Phase | Component | Status |
|-------|-----------|--------|
| 0-3 | Lexer → Parser → Analyzer → Interpreter | ✅ Complete |
| 4 | Type System | ✅ Complete (14 types) |
| 5 | CLI/REPL | ✅ Complete |
| 6 | Stdlib | ✅ Complete (24+ builtins) |
| 7 | LSP/VS Code | ⚠️ Partial (syntax highlight + diagnostics) |
| - | Real LLM API | ❌ Missing (Mock only) |
| - | Memory (HLD v1.2.1) | ⚠️ Partial (interface mismatch) |

**Tests:** 886 passed | **Coverage:** 86%

## License

MIT
