# Command-Line Tools (CLI)

> Module M11 | `helen/cli/__main__.py` + `repl.py` + `formatter.py` + `docgen.py`

---

## Subcommands

```bash
$ helen <file> [args...]  # Compile + execute (args passed to the program as argv)
$ helen check <file>       # Validate only (Lex + Parse + Analyze)
$ helen repl               # Interactive interpreter
$ helen doc <files...>     # Generate documentation
$ helen init               # Initialize config directory
$ helen lsp                # Start Language Server (LSP)
$ helen test <file>        # Run tests
$ helen quality <file>     # 7-dimension quality assessment
```

---

## helen lsp

```bash
$ helen lsp
```

Starts the Helen Language Server, communicating via JSON-RPC 2.0 over stdin/stdout.

### Usage

- **VS Code integration**: Automatically started after installing the [Helen VS Code extension](vscode.md)
- **Manual testing**: `echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | helen lsp`
- **Custom IDEs**: Provides LSP support for other editors

### Features

| Feature | Description |
|---------|-------------|
| Real-time diagnostics | Instant syntax and semantic error reporting |
| Code completion | Keywords, types, stdlib functions |
| Go to definition | Jump to agent/fn/let declarations |

See also [LSP Documentation](lsp.md) and [VS Code Extension Documentation](vscode.md).

---

## helen init

```bash
$ helen init
Helen home: /home/user/.helen
Skills directory: /home/user/.helen/skills
Config created: /home/user/.helen/config.yaml

Next steps:
  1. Edit /home/user/.helen/config.yaml
  2. Set your API key
  3. Run a Helen program: helen <file.helen>
```

Initializes the Helen standalone config directory `~/.helen/`:

| Created | Description |
|---------|-------------|
| `~/.helen/` | Helen home directory |
| `~/.helen/skills/` | Skill directory |
| `~/.helen/config.yaml` | LLM API config template |

If `config.yaml` already exists, it will not be overwritten — you will only be prompted to edit it.

### Configuration File Format

YAML format (`~/.helen/config.yaml`):

```yaml
llm:
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  api_key: "your-api-key-here"
  model: "qwen3.7-plus"
  temperature: 0.7
  timeout: 60
```

.env format (`~/.helen/.env`):

```bash
HELEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
HELEN_API_KEY=your-api-key-here
HELEN_MODEL=qwen3.7-plus
```

### Config Loading Priority

| Priority | File | Description |
|----------|------|-------------|
| 1 (lowest) | `~/.hermes/.env` | Hermes compatibility fallback |
| 2 | `~/.helen/.env` | Helen .env |
| 3 | `~/.helen/config.yml` | Helen YAML |
| 4 (highest) | `~/.helen/config.yaml` | Helen YAML |

### Skill Directory Priority

| Priority | Directory | Description |
|----------|-----------|-------------|
| 1 (highest) | `~/.helen/skills/` | Helen native |
| 2 | `~/.hermes/skills/` | Hermes fallback |
| 3 | `~/.hermes/hermes-agent/skills/` | Hermes agent |

---

## helen <file>

```
$ helen main.helen
$ helen main.helen --verbose --output=json --port=8080 input.txt
$ helen main.helen --transcript-log=/tmp/my_transcript.jsonl
```

Executes the full compilation pipeline:
1. Lexer → Lexical analysis
2. Parser → Syntax analysis
3. SemanticAnalyzer → Semantic analysis
4. Interpreter → Interpretation and execution

Exit codes: `0` = success, `1` = lexical error, `2` = syntax error, `3` = semantic/runtime error

### Transcript Log (v1.16)

Use the `--transcript-log` option to save conversation records to a specified file:

```bash
$ helen chat.helen --transcript-log=/tmp/chat_session.jsonl
$ helen agent.helen --transcript-log=/var/log/helen/agent.db
```

**Parameter format**:
- `--transcript-log <path>` — Specify transcript output path
- `--transcript-log=<path>` — Equals-sign format also supported

**File types**:
- `.jsonl` extension — Uses JSONL backend (human-readable)
- `.db` extension — Uses SQLite backend (high-performance)

**Use cases**:
- Debugging conversation history
- Exporting session records
- Custom storage location
- Production environment auditing

**Configuration priority**:
1. `--transcript-log` CLI argument (highest)
2. `transcript.session_dir` in `~/.helen/config.yaml`
3. Default `~/.helen/sessions/`

See also [TranscriptStore Documentation](../runtime/transcript-store.md).

### Program Arguments (argv)

All arguments after the filename are passed to the Helen program and can be accessed in three ways:

| Access Method | Type | Description |
|---------------|------|-------------|
| `argv` | `const list<str>` | Predefined constant containing all command-line arguments |
| `get_cli_args()` | `list<str>` | Stdlib function, returns the same list as argv |
| `parse_cli_args(spec?)` | `map` | Structured parsing (supports flags, key=value, positional arguments) |

**Example**:

```bash
$ helen my_tool.helen --verbose --output=json --port=8080 input.txt
```

```helen
// my_tool.helen

// 1. Direct access to argv
print(argv)  // ["--verbose", "--output=json", "--port=8080", "input.txt"]

// 2. Auto-parse
let parsed = parse_cli_args()
// {verbose: true, output: "json", port: "8080", _positional: ["input.txt"]}

// 3. Structured parsing (with types and defaults)
let spec = {
    "verbose": {"type": "flag", "default": false},
    "output": {"type": "string", "default": "text"},
    "port": {"type": "int", "default": 3000}
}
let config = parse_cli_args(spec)
// {verbose: true, output: "json", port: 8080, _positional: ["input.txt"]}
```

> **Note**: `argv` is `const` and cannot be reassigned. It is auto-visible inside agent scope (via the const read-only sharing mechanism).

> **Note**: In nested map literals, `}}` is recognized by the lexer as a template reference closer (`TEMPLATE_CLOSE`). You need to add a space between the two braces: `} }`.

---

## helen check

```
$ helen check main.helen
✓ main.helen: OK
```

Executes frontend validation (no execution):
1. Lexer → Lexical analysis
2. Parser → Syntax analysis
3. SemanticAnalyzer → Semantic analysis

`check` also supports passing program arguments (for validating programs that use `argv`):

```
$ helen check main.helen --verbose --output=json
✓ main.helen: OK
```

Useful for code quality checks in CI/CD.

---

## helen repl

```
$ helen repl
Helen REPL v1.2
Type 'exit' or Ctrl+D to quit, ':help' for commands
In multi-line mode (...), press Enter on empty line or Ctrl+C to cancel

>>> let x = 42
>>> x
42
>>>
```

### Interactive Features

| Feature | Description |
|---------|-------------|
| **Cursor movement** | Arrow keys ← → to move cursor, ↑ ↓ to browse history |
| **Command history** | Input history automatically saved, browse with ↑ ↓ |
| **Tab completion** | Press Tab to trigger completion (e.g., keywords) |

### REPL Commands

```
:help               Show help
:reset              Clear all definitions (functions, agents)
:list               List all defined functions and agents
:undefine <name>    Remove a specific function or agent definition
:ask <question>     Ask the AI assistant (uses LLM to answer Helen language questions)
:trace on|off       Enable/disable execution tracing
:trace show [n]     Show last n trace entries (default 50)
:last_error [-v]    Show structured context of last error (-v shows execution trace)
:llm_log [n] [-v]   Show last n LLM call audit logs (-v shows details)
:stats              Show context window usage statistics (Phase 4)
:transcript         Show current transcript (SSOT effective view)
:transcript --full  Show full transcript (including compressed messages)
:transcript --audit Show compression audit trail
:sessions           List all transcript sessions
:session_id         Show current session ID
:resume <id>        Resume a specific transcript session
exit                Exit REPL
```

> **Note**: Stack traces and execution tracing are enabled by default in the REPL — no need for manual `:trace on`.

#### Transcript Commands (v1.16)

Transcript commands are used to manage and view conversation history:

```
>>> :session_id
Current session: session_1783503886_67a17b79

>>> :sessions
Transcript sessions (3 total):
  [1] session_1783503886_67a17b79
       Modified: 2026-07-08 17:30:00, Size: 2.5 KB, Messages: ~50
  [2] session_1783503800_abc12345
       Modified: 2026-07-08 16:00:00, Size: 1.2 KB, Messages: ~20
  ...

>>> :transcript
Current transcript view (15 messages):
  [1] [user] Hello
  [2] [assistant] Hi there
  ...
Stats: 20 total items, 15 messages, 5 compression boundaries

>>> :transcript --audit
Compression audit (3 events):
  [1] Layer: auto_compact
      UUID: a1b2c3d4e5f6
      Range: abc123..def456
      Anchor: ghi789
      Tokens: 500 -> 100
      Summary: Compressed conversation...
```

**Resuming a session**:
```
>>> :resume session_1783503800_abc12345
Session resumed: session_1783503800_abc12345
Transcript loaded. Use :transcript to view.
```

See also [TranscriptStore Documentation](../runtime/transcript-store.md).

#### :ask — AI Assistant

The `:ask` command launches a built-in Helen language expert Agent that can answer questions about Helen syntax, standard library, usage, etc.:

```
>>> :ask 标准库有哪些字符串函数？
🤔 Thinking...

Helen 标准库提供 36 个字符串函数，包括：
- upper/lower/strip — Case and whitespace handling
- split/join — Splitting and joining
- replace/find — Replacing and finding
- regex_match/regex_replace — Regular expressions
...
```

`:ask` uses the `HelenAssistant` agent (defined in `stdlib/_helen_assistant.helen`), which has:
- Complete Helen language knowledge (syntax, type system, standard library)
- Access to tools such as `read_file`, `write_file`, `web_search`
- Conversation history context (maintained within the same REPL session)

### Multi-Line Input

When brackets are unclosed, the REPL enters multi-line mode (`...` prompt):

```
>>> agent Trans(text) {
...   main {
...     return llm act "translate " + text
...   }
... }
```

**Ways to exit multi-line mode:**

| Method | Description |
|--------|-------------|
| **Empty line** | Press Enter at the `...` prompt (enter an empty line) |
| **Ctrl+C** | Cancel current multi-line input, return to `>>>` prompt |
| **Ctrl+D** | Exit the entire REPL |

### Multi-Line Input Detection

The REPL uses a lightweight state machine to determine whether to continue input:

```python
def _needs_continuation(buffer: str) -> bool:
    """Detect unclosed brackets/quotes."""
    brace_count = paren_count = bracket_count = 0
    in_string = False
    escape_next = False

    for ch in buffer:
        if escape_next:
            escape_next = False
            continue
        if ch == '\\' and in_string:
            escape_next = True
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{': brace_count += 1
        elif ch == '}': brace_count -= 1
        elif ch == '(': paren_count += 1
        elif ch == ')': paren_count -= 1
        elif ch == '[': bracket_count += 1
        elif ch == ']': bracket_count -= 1

    return brace_count > 0 or paren_count > 0 or bracket_count > 0
```

When brackets are unclosed, the `...` prompt is shown waiting for more input.

### Error Formatting

The REPL uses `format_error()` to output structured errors:

```
Error: [E0311] at <repl>:2:5
  2 | let x = y
    |         ^
Undefined variable 'y'
```

---

## helen doc

```
$ helen doc main.helen
# Helen Program Documentation

## Agents

### Translator
- **Description**: Translate text between languages
- **Model**: gpt-4
- **Parameters**: text (str)

## Functions
...

## Built-in Functions
...
```

Supports `--format markdown|json` and `-o output_file`.

---

## Error Formatter (formatter.py)

Follows HLD 3.11.2 format:

```python
def format_error(error: HelenError) -> str:
    """
    Error: [E0301] at main.helen:5:10
      5 | let x = "hello
        |           ^^^^^
    Unterminated string

    Code: E0301 — UNTERMINATED_STRING
    """
```

Output includes:
1. Error header: `Error: [E{code}] at {file}:{line}:{col}`
2. Source code line
3. Caret indicator `^^^^`
4. Error message
5. Error code description
