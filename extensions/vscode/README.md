# Helen Language VS Code Extension

[![Version](https://img.shields.io/badge/version-1.30.6-blue.svg)](https://github.com/hahalee00000/helen)
[![Helen](https://img.shields.io/badge/Helen-v1.30.6-green.svg)](https://github.com/hahalee00000/helen)

VS Code extension for the [Helen Agent Programming Language](https://github.com/hahalee00000/helen) — a prompt-first AI-native DSL with 91 bilingual keywords, 333 built-in functions, and first-class LLM primitives.

## Features

### 🎨 Syntax Highlighting
- Full syntax highlighting for `.helen` files (TextMate grammar)
- 91 bilingual keywords (English + Chinese)
- CJK identifier and fullwidth punctuation support
- Agent declarations, LLM primitives, channel/concurrency syntax
- String interpolation (`{expr}`), nested block comments (`/* */`)
- Decorators (`@open`, `@strict`, `@sandbox`)
- Multimodal keywords (`media()`, `on_media`, `on_chunk`)

### 🔍 Language Server (LSP)
- **Real-time diagnostics** — full Lexer → Parser → SemanticAnalyzer pipeline, errors as you type
- **Code completion** — 91 keywords (EN+CN), context keywords, 16 snippet templates, 333 stdlib functions with signatures
- **Go-to-definition** — jump to agent/function/variable/protocol declarations
- **Find references** — cross-document symbol references
- **Hover** — type info and docstrings for stdlib functions, keywords, and user-defined symbols
- **Document symbols** — outline view with hierarchical agent → method → variable nesting
- **Smart snippets** — agent, fn, llm act, llm if, shared store, match, try, spawn, @decorator templates

### ⚡ Quick Actions
- Restart Language Server command
- Status bar indicator (click to restart)
- Automatic server startup on `.helen` file open

## Installation

### Prerequisites

1. Install [Helen](https://github.com/hahalee00000/helen):
```bash
git clone https://github.com/hahalee00000/helen.git
cd helen
pip install -e .
```

2. Verify installation:
```bash
helen --version
helen help
```

### Install Extension

**From VSIX (recommended):**
```bash
cd extensions/vscode
npm install
npm run compile
npm run package
# Install the generated helen-language-1.30.6.vsix in VS Code
```

**Install from VS Code directly:**
```bash
code --install-extension helen-language-1.30.6.vsix
```

### Windows Installation

On Windows, ensure the Python Scripts directory is on your `%PATH%`:

```powershell
# Find the Scripts directory
python -c "import sysconfig; print(sysconfig.get_path('scripts'))"
# Typical location: C:\Users\<You>\AppData\Roaming\Python\Python312\Scripts

# Add to PATH (run in PowerShell as Administrator)
[Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";C:\Users\<You>\AppData\Roaming\Python\Python312\Scripts", "User")
```

Or set the LSP path explicitly in VS Code settings:
```json
{
    "helen.lsp.path": "C:\\Users\\<You>\\AppData\\Roaming\\Python\\Python312\\Scripts\\helen.cmd"
}
```

**Windows (PowerShell):**
```powershell
cd extensions\vscode
npm install
npm run compile
npx vsce package
# Then in VS Code: Ctrl+Shift+P → "Extensions: Install from VSIX..."
```

**From VS Code directly:**
```bash
code --install-extension helen-language-1.30.6.vsix
```

## Configuration

### Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `helen.lsp.path` | Path to Helen LSP executable | `"helen"` |
| `helen.lsp.args` | Arguments for LSP server | `["lsp"]` |
| `helen.lsp.enabled` | Enable/disable Language Server | `true` |

### Example Configuration

If Helen is installed in a custom location:

```json
{
  "helen.lsp.path": "/home/user/helen/venv/bin/helen",
  "helen.lsp.args": ["lsp"]
}
```

## Usage

### Basic Usage

1. Open any `.helen` file in VS Code
2. The extension automatically activates
3. Syntax highlighting is applied immediately
4. Language Server starts in the background

### Example Helen Code

```helen
// Define an AI agent with tools
agent code_reviewer {
    description "Reviews code for quality and security"
    model "gpt-4"
    temperature 0.3
    tools ["read_file", "search_files"]

    functions {
        fn review(code: str): dict {
            let issues = []
            return {"issues": issues, "score": 85}
        }
    }

    main {
        let result = llm act code_reviewer("Review this code")
        print(result)
    }
}

// Spawn agent with Channel communication
let ch = spawn code_reviewer("review src/main.py")
let response = ch.receive()

// Pattern matching with type patterns
fn categorize(error: any): str {
    match error {
        case n is int => { return "code-{n}" }
        case s is str => { return "msg-{s}" }
        default { return "unknown" }
    }
}

// Protocol (interface)
protocol Validator {
    fn validate(data: any): bool
}

// Shared store for cross-agent state (v1.12)
shared store Counter {
    fields {
        let count = 0
    }
    methods {
        fn increment(): int {
            let count = count + 1
            return count
        }
    }
}

// Decorator: sandbox agent with no tools
@sandbox agent safe_agent {
    description "Runs with no tool access"
    main {
        let result = llm if ("Is this safe?") {
            return "safe"
        } else {
            return "unsafe"
        }
    }
}
```

### Commands

- `Helen: Restart Language Server` - Restart the LSP server

### Status Bar

The status bar shows "Helen" when the Language Server is active. Click it to restart the server.

## Troubleshooting

### Language Server Not Starting

1. **Check Helen installation:**
   ```bash
   which helen        # Linux/macOS
   where helen        # Windows
   helen --version
   ```

2. **Check VS Code settings:**
   - Open Settings (Ctrl+,)
   - Search for "helen"
   - Verify `helen.lsp.path` is correct

3. **Check Output panel:**
   - View → Output
   - Select "Helen Language Server" from dropdown
   - Look for error messages

### Windows: LSP Server Not Found

If VS Code shows "Failed to start Helen Language Server" on Windows:

1. **Open PowerShell and run:**
   ```powershell
   where helen
   # Should show: C:\Users\<You>\AppData\Roaming\Python\Python312\Scripts\helen.cmd
   ```

2. **If `where` fails**, the Scripts directory isn't on PATH. Either:
   - Add it to PATH (see [Windows Installation](#windows-installation) above)
   - Or set `helen.lsp.path` in VS Code settings to the full path of `helen.cmd`

3. **If VS Code was launched from desktop shortcut**, it inherits a different PATH than terminal.
   Restart VS Code from the terminal:
   ```powershell
   code .
   ```

4. **Verify in VS Code Output panel** (View → Output → "Helen Language Server"):
   Look for `Helen LSP binary: ...` — it should show the detected path.

### Syntax Highlighting Not Working

1. Ensure file has `.helen` extension
2. Check language mode (bottom right corner)
3. Manually set language: Ctrl+Shift+P → "Change Language Mode" → "Helen"

### Completion Not Working

1. Wait for Language Server to initialize (check status bar)
2. Check Output panel for errors
3. Try restarting the Language Server

## Development

### Building from Source

```bash
cd vscode-extension
npm install
npm run compile
```

### Packaging

```bash
npm run package
# Creates helen-language-1.30.6.vsix
```

### Testing

```bash
# Press F5 in VS Code to launch Extension Development Host
# Open a .helen file in the new window
```

## Language Reference

For complete Helen language documentation, see:
- [Helen GitHub Repository](https://github.com/hahalee00000/helen)
- [Helen High Level Design](https://github.com/hahalee00000/helen/blob/main/documents/Helen_High_Level_Design_v1.2.md)

### Key Features

- **Agent declarations** with model, tools, prompt templates, and transcript control
- **Bilingual keywords** — full Chinese/English support (91 keywords)
- **LLM primitives** — `llm act` (tool-calling loop), `llm if` (LLM-routed branching)
- **Concurrency** — `spawn` with Channel-based inter-agent communication
- **Shared stores** — thread-safe mutable shared state across agents
- **Pattern matching** with `match/case` (range, type, wildcard, variable binding)
- **Protocols** (interfaces) with `protocol/impl`
- **Multimodal support** — `media()`, image/audio/video callbacks
- **Context management** — working memory, graduated compression, caching
- **333 built-in functions** across 21 categories
- **15 built-in skills** for agent capabilities (code review, TDD, debugging, etc.)

## License

MIT License - see [LICENSE](../LICENSE) file for details.

## Contributing

Contributions welcome! Please open an issue or PR on [GitHub](https://github.com/hahalee00000/helen).

---

**Helen** - The Agent Programming Language 🚀
