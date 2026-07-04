# Helen Language VS Code Extension

[![Version](https://img.shields.io/badge/version-1.10.0-blue.svg)](https://github.com/hahalee00000/helen)
[![Helen](https://img.shields.io/badge/Helen-v1.10-green.svg)](https://github.com/hahalee00000/helen)

VS Code extension for the [Helen Agent Programming Language](https://github.com/hahalee00000/helen) - a domain-specific language for building AI agents.

## Features

### 🎨 Syntax Highlighting
- Full syntax highlighting for `.helen` files
- English and Chinese keyword support (91 bilingual keywords)
- CJK identifier support
- Agent declarations and function definitions
- String interpolation support

### 🔍 Language Server (LSP)
- **Real-time diagnostics** - Syntax and semantic errors as you type
- **Code completion** - Keywords (English + Chinese), types, and stdlib functions
- **Go-to-definition** - Jump to agent/function/variable declarations (including `shared let`)

### ⚡ Quick Actions
- Restart Language Server command
- Status bar indicator
- Automatic server startup

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

**From VSIX (recommended for development):**
```bash
cd vscode-extension
npm install
npm run compile
npx vsce package
# Install the generated .vsix file in VS Code
```

**From source:**
```bash
# Copy the vscode-extension folder to your VS Code extensions directory
# Linux: ~/.vscode/extensions/
# macOS: ~/.vscode/extensions/
# Windows: %USERPROFILE%\.vscode\extensions\
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
// Define an AI agent
agent code_reviewer {
    description = "Reviews code for quality and security"
    model = "gpt-4"
    temperature = 0.3
    
    functions {
        fn review(code: str): dict {
            let issues = []
            // Analysis logic...
            return {"issues": issues, "score": 85}
        }
    }
}

// Pattern matching
fn categorize(error: dict): str {
    let code = error["code"] ?? 0
    return match code {
        case 1..100 { "error-patterns" }
        case 101..200 { "code-quality" }
        default { "general" }
    }
}

// Protocol (interface)
protocol Validator {
    fn validate(data: any): bool
}

// Shared variable (v1.10)
shared let counter = 0

// Main entry point
fn main() {
    let result = code_reviewer.review("print('hello')")
    print(result)
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
   which helen
   helen help
   ```

2. **Check VS Code settings:**
   - Open Settings (Ctrl+,)
   - Search for "helen"
   - Verify `helen.lsp.path` is correct

3. **Check Output panel:**
   - View → Output
   - Select "Helen Language Server" from dropdown
   - Look for error messages

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
npx vsce package
# Creates helen-language-1.10.0.vsix
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

- **Agent declarations** with LLM configuration and `functions {}` blocks
- **Bilingual keywords** — full Chinese/English support (91 keywords)
- **Pattern matching** with `match/case`
- **Protocols** (interfaces) with `protocol/impl`
- **Shared variables** with `shared let` for cross-agent state
- **Error handling** with `try/catch/finally`
- **Async/await** for concurrent operations
- **Standard library** with common utilities

## License

MIT License - see [LICENSE](../LICENSE) file for details.

## Contributing

Contributions welcome! Please open an issue or PR on [GitHub](https://github.com/hahalee00000/helen).

---

**Helen** - The Agent Programming Language 🚀
