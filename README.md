# Helen — A Prompt-First Programming Language for AI Agents

[![PyPI version](https://img.shields.io/pypi/v/helen-lang.svg)](https://pypi.org/project/helen-lang/)
[![Python](https://img.shields.io/pypi/pyversions/helen-lang.svg)](https://pypi.org/project/helen-lang/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-2946%20passed-green.svg)](https://github.com/hahalee000000/helen)

**Helen** is an AI-native DSL (Domain-Specific Language) designed specifically for AI Agent development. It fuses deterministic constructs (variables, functions, control flow) with first-class LLM primitives (`llm act`, `llm if`) into a single language.

## ✨ Why Helen?

- **Prompt-first**: `agent` is a first-class citizen — agents are language constructs, not library patterns
- **287 built-in stdlib functions**: 287 bilingual (Chinese/English) functions covering the full AI application development pipeline
- **5-layer graduated compression + working memory**: Long-conversation agents automatically manage context, no manual tuning required
- **Transcript SSOT**: Conversation records persisted as SQLite/JSONL, supporting audit and replay
- **Multi-agent concurrency**: `spawn` + Channel message queues, with built-in mailbox_select multi-select
- **Python bidirectional integration**: Helen → Python FFI + Python → Helen Bridge
- **89 bilingual keywords**: 44.5 English + 44.5 Chinese, native Chinese programming support

## 🎯 When to Use Helen?

### ✅ Choose Helen if you need:
- **Agents as language constructs**: Not library patterns — agents are first-class citizens
- **Bilingual support**: Native Chinese and English programming, lowering the learning curve for teams
- **Automatic context management**: Long-conversation agents with automatic compression, no manual tuning
- **Complete DSL**: Variables, functions, control flow + LLM primitives fused into one language
- **Multi-agent concurrency**: spawn + Channel message queues for fine-grained concurrency control
- **Session persistence**: Built-in TranscriptStore with audit and replay support
- **Excellent debugging experience**: REPL + Transcript + Observability

### 🔄 Helen vs Other Frameworks

| Scenario | Recommended | Reason |
|----------|-------------|--------|
| Rapid prototyping | **Helen** | Concise syntax, automatic context management |
| Complex RAG pipelines | LangChain | Large number of pre-built components |
| Multi-agent team collaboration | CrewAI / **Helen** | Helen provides finer-grained concurrency control |
| Chinese-English bilingual apps | **Helen** | Native bilingual support |
| Long-conversation agents | **Helen** | 5-layer graduated compression + working memory |
| Session audit & replay | **Helen** | Built-in TranscriptStore SSOT |

📖 Detailed comparison: [Helen vs LangChain vs CrewAI vs AutoGen](reports/COMPARISON.md)

## 🚀 Quick Start

### Installation

```bash
pip install helen-lang
```

### Hello Helen

Create `hello.helen`:

```helen
agent Greeter(name: str) {
    description "A friendly greeter"
    prompt "Greet {{name}} warmly in one sentence"

    main {
        return llm act "Greet {{name}} warmly"
    }
}

main {
    let g = Greeter("World")
    print(g)
}
```

Run:

```bash
helen hello.helen
# Hello, World! It's wonderful to meet you!
```

### REPL Interaction

```bash
helen repl
> let x = 1 + 2
> print(x)
3
> :help
```

### Python Bridge Usage

Helen Agents can be used directly in Python via the Python Bridge, just like ordinary Python classes:

1. Create a Helen Agent file `translator.helen`:

```helen
agent TranslatorAgent(text: str, target: str) {
    description "Translate text to the target language"
    prompt "Translate '{{text}}' to {{target}}"

    main {
        return llm act "Translate '{{text}}' to {{target}}"
    }
}
```

2. Import and call in Python:

```python
from translator import TranslatorAgent

agent = TranslatorAgent()
result = agent("Hello", "French")
print(result)  # "Bonjour"
```

### Python Integration Features

- **Direct .helen file import**: `from my_agents import TranslatorAgent`
- **Type hint support**: IDE auto-completion for Helen Agents
- **Async calls**: `await agent.async_call(...)`
- **Decorator pattern**: `@helen_agent` decorates Python functions
- **Parameter validation**: Helen automatically validates agent parameter types

```python
from helen.python_bridge import helen_agent

@helen_agent("translator.helen", "TranslatorAgent")
def translate(text: str, target: str) -> str:
    pass

result = translate("Hello", "French")
```

## 🎯 Use Cases

### AI Agent Development

```python
from agents import ResearchAgent, AnalysisAgent

# Research phase
researcher = ResearchAgent()
findings = researcher("quantum computing", depth="deep")

# Analysis phase
analyzer = AnalysisAgent()
insights = analyzer(findings)
```

### Multi-Agent Collaboration

```python
from workflow import PlannerAgent, ExecutorAgent, ReviewerAgent

planner = PlannerAgent()
plan = planner("Build a web app")

executor = ExecutorAgent()
result = executor(plan)

reviewer = ReviewerAgent()
feedback = reviewer(result)
```

### LLM Applications

```python
from llm_agents import ChatBot, Summarizer, Translator

chatbot = ChatBot()
response = chatbot("What is AI?")

summarizer = Summarizer()
summary = summarizer(long_text)

translator = Translator()
translated = translator(summary, target="Chinese")
```

## 🛠️ API Reference

### HelenAgentWrapper

```python
class HelenAgentWrapper:
    def __init__(self, agent_name: str, helen_file: str, interpreter=None)

    def __call__(self, *args, **kwargs) -> Any
        """Call agent"""

    async def async_call(self, *args, **kwargs) -> Any
        """Async call agent"""
```

### Decorators

```python
@helen_agent(helen_file: str, agent_name: str = None)
def my_function(...):
    """Wrap function as a Helen agent call"""

@helen_module(helen_file: str)
class MyModule:
    """Wrap class as a collection of Helen agents"""
```

### Import Hook

```python
from helen.python_bridge import install_import_hook

# Auto-install (default)
install_import_hook()

# Manual uninstall
from helen.python_bridge import uninstall_import_hook
uninstall_import_hook()
```

## 📖 More Examples

### Batch Processing

```python
from agents import TranslatorAgent

agent = TranslatorAgent()
texts = ["Hello", "World", "AI"]

results = [agent(text, target="French") for text in texts]
print(results)  # ["Bonjour", "Monde", "IA"]
```

### Error Handling

```python
from agents import TranslatorAgent

agent = TranslatorAgent()

try:
    result = agent("Hello", target="French")
except TypeError as e:
    print(f"Parameter error: {e}")
except Exception as e:
    print(f"Execution error: {e}")
```

### Shared Interpreter

```python
from helen.interpreter import Interpreter
from helen.python_bridge import HelenAgentWrapper

# Create a shared interpreter
interpreter = Interpreter()

# Multiple agents share the same interpreter
agent1 = HelenAgentWrapper("Agent1", "agents.helen", interpreter)
agent2 = HelenAgentWrapper("Agent2", "agents.helen", interpreter)
```

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 📄 License

MIT License

## 🔗 Links

- Documentation: https://helen.readthedocs.io
- GitHub: https://github.com/hahalee000000/helen
- PyPI: https://pypi.org/project/helen-lang

## 📚 Documentation

- [Wiki Documentation](wiki/index.md) - Complete technical documentation
- [Tutorial](reports/tutorial.md) - Learn Helen from scratch
- [Python Bridge Tutorial](wiki/tutorial/15-python-bridge.md) - Python integration guide
- [Context Management](wiki/runtime/context-management.md) - Intelligent context handling (v1.20)
- [Skill System](wiki/runtime/skills.md) - Skill loading and usage

## 🆕 Version History

### v1.20 - Transcript Session Scope
- Transcripts are isolated per application in `.helen/sessions/` by default (REPL scenario opts in to global)
- `session_scope` configuration: `auto` | `global` | `project`
- `HELEN_SESSION_DIR` environment variable to force a specific path
- New `get_session_dir()` / `set_session_dir()` stdlib functions

### v1.19 - Context Management API Completion
- Complete 6-dimension API (Inspection / Working Memory / Fine-grained Mutation / Runtime Config / Query / Multi-agent Transfer)
- 24 new stdlib functions: `context_stats` / `context_usage` / `pin_message` / `working_memory_*` / `export_context`, etc.
- `Message.pinned: bool` field — pinned messages are immune to all 5 compression layers
- Internalized `classify_message`

### v1.18 - spawn Concurrency Primitives
- `spawn Agent(...)` returns a Channel, replacing `async/await/detach`
- Channel message queue: `send/receive/try_receive/cancel/close`
- `mailbox_select()` multi-select primitive
- Streaming interrupt: `on_chunk` callback returns `false` to stop streaming; Ctrl+C interrupt

### v1.16 - TranscriptStore SSOT
- Conversation history SSOT with SQLite/JSONL dual backends
- LRU cache (10K messages ~10MB)
- UUID addressing, O(1) lookups
- Non-destructive compression (BoundaryMarker audit trail)

### v1.15 - Context Management Enhancement
- Working Memory
- Graduated Compression
- Cache-Aware Compression
- Three-Channel Context
- Agent context configuration


### v1.14 - LLM Streaming Support
- `llm act` supports streaming output (on_chunk/on_complete callbacks)
- `llm stream` removed (functionality merged into `llm act`)

### v1.13 - Python Bridge
- Direct Python import and usage of Helen Agents
- Bidirectional FFI (Helen ↔ Python)

### v1.12 - Agent Isolation Enhancement
- Agent isolation levels (@open, @strict, @sandbox)
- Shared store and channel
- ReadOnlyView
- Closure value capture

### v1.10 - Core Features
- Agent scope isolation
- Short-circuit evaluation
- Subscript/field assignment
- Alias statements

## 🤝 Community & Contributing

- **GitHub**: https://github.com/hahalee000000/helen — Report issues, submit PRs, join discussions
- **License**: MIT — Business-friendly, open-source-friendly
- **Python**: 3.12+ required
- **Platforms**: Linux / macOS / Windows

Contributions welcome! See [CLAUDE.md](CLAUDE.md) for the development workflow, or [wiki/index.md](wiki/index.md) for complete documentation.

## 📊 Project Stats

- **Code size**: ~40,000 lines of Python (96 source files)
- **Test coverage**: 2917 tests, 137 test files
- **Built-in stdlib**: 287 functions, 287 Chinese aliases
- **Built-in skills**: 17 (helen-syntax, helen-stdlib, code-quality, github, etc.)
- **Bilingual keywords**: 89 (44.5 English + 44.5 Chinese)
