# HelenChat

An autonomous AI agent built with the Helen language, inspired by Hermes agent.

## Features

- **Interactive Loop**: Accepts user instructions in a continuous conversation
- **Auto-Planning**: LLM decomposes complex tasks into step-by-step plans
- **Tool Execution**: Built-in tools for web search, file operations, shell commands, and more
- **Skill System**: Load detailed workflows and procedures on demand
- **Persistent Memory**: Uses markdown files to store long-term knowledge

## Usage

```bash
helen examples/helenchat/helenchat.helen
```

## Commands

- `/quit` or `exit` — Exit the program
- `/memory` — Display current memory contents
- `/remember <fact>` — Save a fact to persistent memory
- `/plan <task>` — Create a detailed plan without executing
- `/clear` — Clear conversation context

## Available Tools (for the LLM)

The agent can use these tools during conversations:

- `web_search(query)` — Search the web for information
- `web_fetch(url)` — Fetch content from a URL
- `read_file(path)` — Read a local file
- `write_file(path, content)` — Write content to a file
- `shell_exec(command)` — Execute a shell command
- `calculate(expression)` — Evaluate a math expression
- `patch_file(path, old_string, new_string)` — Edit a file with fuzzy matching
- `load_skill(name)` — Load a detailed skill/workflow by name

## Memory System

HelenChat persists knowledge in the `memory/` directory:

- `memory/MEMORY.md` — Long-term facts, user preferences, environment details
- `memory/TODO.md` — Active tasks and their status (created on demand)
- `memory/KNOWLEDGE.md` — Domain knowledge accumulated during sessions (created on demand)

The agent automatically reads memory at the start of each task and can write new findings back to memory files.

## Architecture

HelenChat is built using Helen's agent system:

1. **Agent Declaration**: Defines the agent's prompt, tools, and behavior
2. **Main Loop**: Handles user input and special commands
3. **LLM Integration**: Uses `llm act` with tool calling for autonomous execution
4. **Python FFI**: Uses `os` and `io` modules for file operations

## Example Session

```
╔══════════════════════════════════════════════╗
║          HelenChat v1.0                      ║
║   Autonomous AI Agent — Powered by Helen     ║
╚══════════════════════════════════════════════╝

Commands: /memory  /plan <task>  /remember <fact>  /clear  /quit

You > /remember I'm learning Helen language

Saved to memory: I'm learning Helen language

You > What is Helen?

HelenChat: Helen is an AI-native programming language designed for building 
autonomous agents and LLM-powered applications. It provides native syntax 
for agent declarations, LLM calls, and tool integration...

You > /quit

HelenChat: Goodbye!
```

## Requirements

- Helen language compiler (included in this repo)
- LLM API configuration in `~/.helen/config.yaml` or `~/.hermes/.env`

## License

Part of the Helen language project.
