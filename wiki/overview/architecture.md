# Helen Overall Architecture

> Three-layer architecture: Core (core compiler) → Runtime (runtime) → Toolchain (toolchain)

---

## Architecture Layers

```
┌────────────────────────────────────────────────────────────┐
│                    Toolchain Layer                          │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌───────┐ ┌──────┐ │
│  │ CLI M11 │ │ LSP M12  │ │ VSCode   │ │Stdlib  │ │DocGen│ │
│  │run/check│ │diagnose  │ │ M13      │ │ M15    │ │      │ │
│  │/repl/doc│ │/complete │ │highlight │ │287 fn  │ │      │ │
│  └────┬────┘ └────┬─────┘ └────┬─────┘ └───┬───┘ └──┬───┘ │
├───────┼───────────┼────────────┼───────────┼─────────┼────┤
│                    Runtime Layer                            │
│  ┌──────────┐ ┌───────────┐ ┌───────┐ ┌──────┐ ┌──────┐  │
│  │LLM RT M7 │ │Prompt M6  │ │Memory │ │History│ │Import│  │
│  │ABC×12    │ │Tier 1/2   │ │M7/M16 │ │M16   │ │ M8   │  │
│  │cancel    │ │render     │ │file   │ │budget│ │safe  │  │
│  └────┬─────┘ └─────┬─────┘ └───┬───┘ └──┬───┘ └──┬───┘  │
│  ┌──────────────────────────────────────────────────┐    │
│  │  Interpreter Mixin Architecture                   │    │
│  │  LlmMixin      — LLM act/if, tool building,     │    │
│  │                    history management             │    │
│  │  PatternMixin  — match/case pattern matching      │    │
│  │  ExceptionMixin — try/catch/throw/assert          │    │
│  │  ImportMixin   — Multi-format imports             │    │
│  │                    (.helen/.py/.json etc.)        │    │
│  │  StreamingMixin — Streaming call management       │    │
│  │                    and cancellation               │    │
│  └──────────────────────────────────────────────────┘    │
├───────┼─────────────┼───────────┼─────────┼────────┼──────┤
│                    Core Compilation Layer                 │
│  ┌──────┐ ┌────────┐ ┌─────┐ ┌─────────┐ ┌────┐ ┌─────┐  │
│  │Lexer │ │Parser  │ │ AST │ │Semantic │ │Type│ │Error│  │
│  │ M1   │ │ M2     │ │ M3  │ │Analyzer │ │ M9 │ │ M10 │  │
│  │77Tok │ │Pratt×10│ │49Nd │ │46Visitor│ │14Ty│ │42Cd │  │
│  └──┬───┘ └───┬────┘ └──┬──┘ └────┬────┘ └─┬──┘ └──┬──┘  │
└─────┼─────────┼─────────┼─────────┼────────┼───────┼──────┘
      │         │         │         │        │       │
      ▼         ▼         ▼         ▼        ▼       ▼
   Source → Token Stream → AST Tree → Symbol Table/Types → Execution Results
```

---

## Core Layer: Core Compiler

### Data Flow

```
source.helen
    │
    ▼ ┌─────────────────┐
    │ │   Lexer (M1)    │  Scans source → Token stream
    │ │ Maximal Munch   │  39 keywords / 77 token types
    │ │ 39 keywords     │  SourceSpan throughout the pipeline
    │ └────────┬────────┘
    │          ▼ Token[type, lexeme, line, col, span]
    │ ┌─────────────────┐
    │ │  Parser (M2)    │  Token stream → AST tree
    │ │ Pratt × 10 prec │  Panic mode error recovery
    │ │ EBNF 392 lines  │  49 AST node types
    │ └────────┬────────┘
    │          ▼ ProgramNode[statements...]
    │ ┌─────────────────┐
    │ │SemanticAnalyzer │  AST → Type checking + symbol table
    │ │   (M4)          │  6 scope types: global/agent/fn/block/catch/loop
    │ │ 46 Visitor meth.│  42 ErrorCodes for precise localization
    │ └────────┬────────┘
    │          ▼ (errors or clean AST)
    │  ┌─────────────────┐
    │  │ Interpreter(M5) │  AST → Execution results
    │  │ Visitor[object] │  Environment scope chain
    │  │ + 5 Mixins      │  Agent isolated invocation
    │  │ + LLM Runtime   │  Mixins: Llm/Pattern/Exception/Import/Streaming
    │  └─────────────────┘
```

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Hand-written scanner | Not regex | Maximum flexibility; supports triple-quote / hyphen disambiguation |
| Pratt Parsing | Not traditional recursive descent | 10 expression precedence levels; `spawn` prefix handling |
| Visitor pattern | 44 abstract methods | Three compilation stages share the same AST traversal interface |
| SourceSpan | Throughout the pipeline | Every Token/AST node carries source code location for precise error localization |

---

## Runtime Layer: Runtime System

### Abstract Interface

```python
class Runtime(ABC):                          # HLD 3.8.1, 12 abstract methods
    def load_tool() -> Any                   # Load a tool
    def list_skills() -> list[SkillMeta]     # Skill index (Tier 1)
    def load_skill(name) -> str              # Load skill content (Tier 2)
    def call_llm(messages, tools, ...)       # Call LLM
    def cancel_llm_call(call_id) -> bool     # Cancel an LLM call
    def get_memory(key) -> str | None        # Get memory
    def set_memory(key, value)               # Set memory
    def resolve_import(path, from_file)      # Resolve import
    def get_token_count(text) -> int         # Token estimation
    def get_conversation_history()           # Get conversation history
    def set_conversation_history(history)    # Set conversation history
    def register_memory_provider(proto, p)   # Register memory provider
```

### HelenHermesRuntime (Concrete Implementation)

- Inherits `Runtime` ABC
- `threading.Event` implements cancellable LLM calls
- `_active_calls` dict tracks in-progress calls
- `_memory` dict implements key-value storage
- `_conversation_history` manages conversation history

### Configuration System (config.py)

```
~/.helen/
├── config.yaml    # LLM API configuration (YAML)
├── .env           # LLM API configuration (.env format)
└── skills/        # Helen native skill directory
```

Configuration loading priority: `~/.hermes/.env` → `~/.helen/.env` → `config.yml` → `config.yaml`

### Built-in Tools (tools.py)

| Tool | Function |
|------|----------|
| `web_search` | Wikipedia search |
| `web_fetch` | Web content retrieval |
| `read_file` | File reading |
| `write_file` | File writing (overwrite) |
| `patch_file` | Precise file modification (fuzzy matching) |
| `shell_exec` | Shell command execution |
| `calculate` | Mathematical computation |

The LLM calls tools via the OpenAI function calling protocol, with multi-turn loops + nudge mechanism.

### Fuzzy Match Engine (fuzzy_match.py)

An 860-line fuzzy matching engine integrated from Hermes, supporting 9 strategies:
- Exact match, line trimming, whitespace normalization, indentation flexibility
- Escape normalization, boundary trimming, Unicode normalization
- Chunk anchors (SequenceMatcher), context-aware (line-by-line similarity)

Also includes: escape drift detection, indentation re-anchoring, "Did you mean?" hints.

### Component Relationships

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

## Toolchain Layer: Toolchain

### CLI (helen)

```
$ helen main.helen      # Compile + execute
$ helen check main.helen  # Validate only (Lex + Parse + Analyze)
$ helen repl               # Interactive interpreter
$ helen doc main.helen    # Generate documentation (markdown/json)
$ helen init               # Initialize ~/.helen/ configuration directory
```

Exit codes: `0`=success `1`=lex error `2`=syntax error `3`=semantic/runtime error

### LSP Server (JSON-RPC 2.0 over stdio)

```json
// Client → Server
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{...}}
{"jsonrpc":"2.0","method":"textDocument/didOpen","params":{...}}

// Server → Client
{"jsonrpc":"2.0","id":1,"result":{"capabilities":{...}}}
{"jsonrpc":"2.0","method":"textDocument/publishDiagnostics","params":{...}}
```

Supported methods: `initialize` `textDocument/didOpen` `textDocument/didChange` `textDocument/didClose` `textDocument/diagnostics` `textDocument/completion` `textDocument/definition`

### VS Code Extension

- `syntaxes/helen.tmLanguage.json` — TextMate grammar (covers 42 keywords)
- `language-configuration.json` — Bracket pairing, auto-closing, indentation rules
- `package.json` — Extension manifest

### Standard Library (287 builtins)

| Category | Count | Representative Functions |
|----------|-------|-------------------------|
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

See [stdlib.md](../toolchain/stdlib.md) for details.

### AI-Native Observability (observability.py)

Provides structured debugging context for AI Agents, replacing traditional interactive debuggers:

| Component | Function | Default State |
|-----------|----------|---------------|
| `CallStackTracker` | Function/Agent call stack tracing | Off |
| `ExecutionTracer` | Statement execution tracing (ring buffer, 10000 entries) | Off |
| `ErrorSnapshot` | Structured error context (JSON) | Auto-capture |
| `LLMAuditLog` | LLM call audit log (ring buffer, 1000 entries) | On |
| `ObservabilityManager` | Unified management entry point | — |

REPL commands: `:trace on|off|show`, `:last_error`, `:llm_log`
Built-in functions: `debug()`, `trace_on()`, `trace_off()`, `get_trace()`
Language feature: `assert` statement (automatically captures context on failure)

---

## Compilation Stages and ErrorCode Mapping

| Stage | Module | ErrorCode Range | Typical Errors |
|-------|--------|-----------------|----------------|
| Lexical Analysis | M1 | E0300-E0309 | Unterminated string, invalid escape |
| Syntax Analysis | M2 | E0301-E0320 | Unexpected token, missing token |
| Semantic Analysis | M4 | E0330-E0350 | Undeclared variable, type mismatch |
| Execution Stage | M5 | E0334-E0350 | Agent runtime error, constant assignment |

---

## Quality Metrics

| Metric | Value |
|--------|-------|
| Python source lines | 19,500+ |
| Test code lines | 17,000+ |
| Test-to-source ratio | 0.87 |
| Test case count | 1,830+ |
| Test pass rate | 100% |
| flake8 warnings | 0 |
| Visitor methods implemented | 47/47 |
| CI/CD | GitHub Actions (pytest + flake8 + coverage) |
| Overall quality score | 7.93/10 (7-dimension assessment) |
