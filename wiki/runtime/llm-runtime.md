# Runtime System

> Module M7 (`helen/runtime/`) | HLD 3.8

---

## Runtime ABC (12 Methods)

```python
class Runtime(ABC):
    # Tool & Skill
    def load_tool(name) -> Any
    def list_skills() -> list[SkillMeta]
    def load_skill(name) -> str

    # LLM
    def call_llm(messages, tools, model, temperature, max_turns) -> Any
    def cancel_llm_call(call_id) -> bool

    # Memory
    def get_memory(key) -> str | None
    def set_memory(key, value)

    # Import
    def resolve_import(path, from_file) -> Any

    # Token & History
    def get_token_count(text) -> int
    def get_conversation_history() -> list[Message]
    def set_conversation_history(history)

    # Provider
    def register_memory_provider(protocol, provider)
```

**Core code never directly imports Hermes** — it only interacts through this interface.

---

## HelenHermesRuntime

Default implementation, inherits from `Runtime` ABC:

```python
class HelenHermesRuntime(Runtime):
    def __init__(self, llm_runtime=None, import_resolver=None):
        self._llm_runtime = llm_runtime
        self._import_resolver = import_resolver
        self._memory: dict[str, str] = {}
        self._conversation_history: list[Message] = []
        self._active_calls: dict[str, _CallHandle] = {}
        self._memory_providers: dict[str, Any] = {}
        self._lock = threading.Lock()
```

---

## Cancellable LLM Calls

### _CallHandle

```python
class _CallHandle:
    cancelled: threading.Event   # Cancellation signal
    result: Any                  # Call result
    exception: Exception | None  # Exception
    done: threading.Event        # Completion signal
```

### cancel_llm_call()

```python
def cancel_llm_call(self, call_id: str) -> bool:
    with self._lock:
        handle = self._active_calls.get(call_id)
    if handle is None:
        return False          # Not found or already completed
    handle.cancelled.set()
    return True               # Cancellation signal sent
```

### CancelledError

```python
class CancelledError(Exception):
    def __init__(self, call_id: str):
        self.call_id = call_id
        super().__init__(f"LLM call {call_id} was cancelled")
```

---

## MockLLMRuntime (for Testing)

```python
@dataclass
class MockLLMRuntime(LLMRuntime):
    route_return: str | None = None       # Preset route() return value
    act_return: LLMResponse | str | None  # Preset act() return value
    route_fail: Exception | None = None   # Preset route() exception
    act_fail: Exception | None = None     # Preset act() exception
    route_history: list[dict]             # Call history
    act_history: list[dict]               # Call history
```

Supports deterministic testing without a real LLM.

---

## HermesCLILLMRuntime (CLI Mode, Slow)

Calls LLM through Hermes CLI (fallback approach):

```python
@dataclass
class HermesCLILLMRuntime(LLMRuntime):
    hermes_path: str = "hermes"      # Hermes CLI path
    default_model: str | None = None # Default model
    timeout: int = 120               # Timeout in seconds
```

**Performance:** 15-17 seconds/call (includes process startup overhead)

**Use cases:**
- Fallback when HTTP API is unavailable
- When Hermes-specific features (skills, tools) are needed

---

## HttpLLMRuntime (HTTP Mode, Fast)

Directly calls OpenAI-compatible API (recommended):

```python
@dataclass
class HttpLLMRuntime(LLMRuntime):
    base_url: str = ""      # API endpoint
    api_key: str = ""       # API key
    default_model: str = "qwen3.7-plus"  # Default model
    timeout: int = 120
```

**Configuration loading:** Via `helen.runtime.config` module, loads from multiple sources by priority:

| Priority | File | Description |
|--------|------|------|
| 1 (lowest) | `~/.hermes/.env` | Hermes compatibility fallback |
| 2 | `~/.helen/.env` | Helen .env format |
| 3 | `~/.helen/config.yml` | Helen YAML |
| 4 (highest) | `~/.helen/config.yaml` | Helen YAML |

Supported environment variable names:
- `HELEN_BASE_URL` / `DASHSCOPE_BASE_URL` / `OPENAI_BASE_URL`
- `HELEN_API_KEY` / `DASHSCOPE_API_KEY` / `OPENAI_API_KEY`
- `HELEN_MODEL` / `DEFAULT_MODEL`
- `HELEN_TEMPERATURE` / `TEMPERATURE`
- `HELEN_TIMEOUT` / `TIMEOUT`

**Performance:** 7-11 seconds/call (no process startup overhead)

**Implementation:**
```python
def _chat(self, prompt: str, model: str = None, temperature: float = 1.0):
    url = f"{self.base_url}/chat/completions"
    payload = {
        "model": model or self.default_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }
    # HTTP POST request...
```

**Use cases:**
- REPL interaction (default)
- Script mode (`helen <file>`)
- Scenarios requiring fast response
- Production deployment

---

## Built-in Tool System

Helen provides 7 built-in tools that the LLM can call via function calling during `llm act` execution:

| Tool | Function | Parameters |
|------|------|------|
| `web_search` | Search Wikipedia | `query: str` |
| `web_fetch` | Fetch web content | `url: str` |
| `read_file` | Read file | `path: str` |
| `write_file` | Write file (overwrite) | `path: str, content: str` |
| `patch_file` | Precise file modification (fuzzy matching) | `path, old_string, new_string` |
| `shell_exec` | Execute shell command | `command: str` |
| `calculate` | Math calculation | `expression: str` |

### patch_file Fuzzy Matching

`patch_file` uses 9 matching strategies to handle common discrepancies in LLM-generated code:

| # | Strategy | Handles |
|---|------|---------|
| 1 | Exact | Exact match |
| 2 | Line-trimmed | Leading/trailing whitespace differences |
| 3 | Whitespace-normalized | Multiple spaces/tabs normalized |
| 4 | Indentation-flexible | Indentation completely ignored |
| 5 | Escape-normalized | `\n` `\t` escape differences |
| 6 | Trimmed-boundary | First/last line whitespace trimmed |
| 7 | Unicode-normalized | Smart quotes, dashes, etc. |
| 8 | Block-anchor | SequenceMatcher similarity |
| 9 | Context-aware | Line-by-line similarity |

Tool registry is located in `helen/runtime/tools.py`; the fuzzy matching engine is in `helen/runtime/fuzzy_match.py` (integrated from Hermes, runs independently).

```python
@dataclass
class HelenTool:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema
    handler: Callable[..., str]
```

Agents declare available tools through `tools` configuration:

```helen
agent Researcher(topic) {
    description "Research assistant"
    tools = ["web_search", "web_fetch", "read_file"]
    main {
        return llm act "Research: " + topic
    }
}
```

---

## Skill System

Skill directory scan priority:

1. `~/.helen/skills/` — Helen native skills
2. `~/.hermes/skills/` — Hermes fallback
3. `~/.hermes/hermes-agent/skills/` — Hermes agent skills

### Two-Phase Disclosure

Helen implements the two-phase skill disclosure mechanism from HLD §3.7.1:

**Tier 1: Skill Index (lightweight)**

`PromptBuilder.build_skill_index()` scans the skill directory, reads SKILL.md YAML frontmatter (name, description, category), and formats it as an `<available_skills>` XML block injected into the System Prompt:

```xml
<available_skills>
Before replying, scan skills below. If relevant,
use load_skill tool to load full content.

  devops:
    - helen-language: Helen programming language development...
  research:
    - research: Research discovery and monitoring...
</available_skills>
```

**Tier 2: load_skill Tool (on-demand loading)**

The `load_skill` tool is registered in `helen/runtime/tools.py`; the LLM can load full SKILL.md content on demand via function calling:

```python
# LLM calls load_skill tool
dispatch_tool('load_skill', {'name': 'helen-language'})
# Returns full SKILL.md content (67KB+)
```

**Advantages**:
- Tier 1 only consumes ~16KB tokens (all skill names + descriptions)
- Tier 2 loads on demand — full content is loaded only when the LLM needs it
- Avoids wasting tokens by sending large skill content every time

---

## Performance Comparison

| Runtime | Call Time | Overhead Source |
|---------|---------|---------|
| HttpLLMRuntime | 7-11s | Network latency + LLM inference |
| HermesCLILLMRuntime | 15-17s | Process startup + config loading + network + inference |

**REPL uses HttpLLMRuntime by default**, approximately 2× performance improvement.

---

## llm act Expression

`llm act` supports two usage forms:

### 1. Statement Form (within agent context)

```helen
agent Translator(text) {
    prompt "Translate text"
    model "gpt-4"
    main {
        llm act Translator(text=text) "Translate to Chinese"
    }
}
```

Syntax: `llm act target(arg=value, ...) "description"`

### 2. Expression Form (direct LLM call)

```helen
// Top-level direct call
llm act "translate hello to chinese."

// Used in a function
fn translate(text, target) {
    return llm act "translate " + text + " to " + target
}

// Assigned to a variable
let result = llm act "summarize this article"

// Used in an agent
agent Smart(text) {
    main {
        return llm act "analyze: " + text
    }
}
```

Syntax: `llm act <expression>`

The expression form will:
- Evaluate the expression as the prompt
- Call the LLM runtime
- Return the LLM response text (string)

### Parser Disambiguation

The parser determines the form via lookahead:
- If `llm act` is followed by an IDENTIFIER with `(` or STRING after it → statement form
- Otherwise → expression form

---

## Memory System

### MemoryProvider ABC

```python
class MemoryProvider(ABC):
    @abstractmethod
    def get(self, key: str) -> str | None
    @abstractmethod
    def set(self, key: str, value: str) -> None
    @abstractmethod
    def delete(self, key: str) -> None
    @abstractmethod
    def list_keys(self) -> list[str]
```

### FileMemoryProvider

JSON file persistence:

```python
class FileMemoryProvider(MemoryProvider):
    def __init__(self, path: str):
        self._path = path
        self._data = self._load()

    def _load(self) -> dict:
        if os.path.exists(self._path):
            return json.load(open(self._path))
        return {}

    def _save(self):
        json.dump(self._data, open(self._path, 'w'))
```

### InMemoryProvider

Pure in-memory implementation, used for testing.

---

## v1.10 Async HTTP Support

### Overview

v1.10 added async HTTP methods based on `httpx.AsyncClient`, supporting concurrent LLM calls.

### Async Methods

```python
class LLMRuntime:
    # Synchronous methods
    def act(self, target: str, description: str, **kwargs) -> Any
    def act_stream(self, target: str, description: str, **kwargs) -> Iterator[str]
```

**v1.18 change**: `act_async()` / `act_stream_async()` have been removed, replaced by `spawn` + Channel. Concurrent LLM calls are now achieved through spawn:

```helen
// v1.18 concurrent LLM calls
let m1 = spawn AgentA("task1")
let m2 = spawn AgentB("task2")
let [r1, r2] = [m1.receive(), m2.receive()]
```

### httpx.Client

Synchronous methods use `httpx.Client`:

```python
class HttpLLMRuntime(LLMRuntime):
    def __init__(self, base_url: str, api_key: str, model: str):
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0
        )
```

**v1.18 change**: `httpx.AsyncClient` has been removed; concurrency is now implemented via `spawn` (threading.Thread).

### Usage Example

```helen
agent MyAgent {
  main {
    // Synchronous call
    let result = llm act Translate "Hello"
    
    // Concurrent call (v1.18 spawn)
    let m1 = spawn Translate("Hello")
    let m2 = spawn Translate("World")
    let r1 = m1.receive()
    let r2 = m2.receive()
  }
}
```

### Connection Pool Management

`httpx.Client` automatically manages connection pooling:

- **Connection reuse**: Multiple requests reuse the same TCP connection
- **Concurrency control**: Concurrency via `spawn` (threading.Thread)
- **Timeout management**: Unified timeout configuration
- **Resource cleanup**: Connections automatically closed on program exit

### Performance Advantages

| Scenario | Serial | Spawn Concurrency | Improvement |
|------|------|----------------|------|
| Single call | 1.5s | 1.5s | 0% |
| 3 concurrent | 4.5s | ~1.6s | 65% |
| 10 concurrent | 15s | ~2.1s | 86% |

**Note**: Since v1.18, concurrency is implemented via `spawn`, with each spawned agent running in an independent daemon thread.

### Error Handling

Async methods use the same error handling mechanism:

```helen
try {
  let result = await llm act_async Task "Complex task"
} catch LLMError as e {
  print("LLM Error: " + e.message)
} catch TimeoutError as e {
  print("Timeout: " + e.message)
}
```

---

**Last Updated**: 2026-07-04  
**Version**: v1.11

---

## P4 History Management Enhancement (v1.11 Addition)

> v1.11 introduced complete history persistence, retrieval, and context visualization features.

### History Persistence

Retain conversation continuity across sessions:

```helen
agent PersistentAgent {
    main {
        // Save current history to JSON file
        save_history("./session.json")
        
        // Load history from file (on next startup)
        let loaded = load_history("./session.json")
        print("Loaded " + str(loaded) + " messages")
    }
}
```

**JSON format**:
```json
{
  "version": 1,
  "model": "qwen3.7-plus",
  "saved_at": "2026-07-04T12:00:00Z",
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

### History Retrieval

Agents can query specific information in history:

```helen
agent SmartResearcher {
    tools ["web_search", "load_skill"]
    main {
        // Search previous tool calls
        let past_searches = search_history(tool_name="web_search")
        
        // Filter by role
        let user_questions = search_history(role="user")
        
        // Text search (case-insensitive)
        let mentions = search_history(query="Python")
        
        // Get tool call history
        let tool_log = get_tool_history("web_search")
        
        return llm act "Continue research..."
    }
}
```

### Context Usage Visualization

Use the `:stats` command in REPL to view context usage statistics:

```
> :stats
╔══════════════════════════════════════╗
║       Context Usage Statistics        ║
╠══════════════════════════════════════╣
║ ✅ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  12.3%            ║
║ Tokens:   15,984 /  131,072              ║
║ Model:  qwen3.7-plus                  ║
║ Messages: 8                           ║
╠──────────────────────────────────────╣
║  User             3,200 tokens        ║
║  Assistant        8,500 tokens        ║
║  System_prompt    2,100 tokens        ║
║  System           2,184 tokens        ║
╚══════════════════════════════════════╝
```

### Token Estimation Enhancement

v1.11 supports optional tiktoken exact counting (install `helen[accurate-tokens]`), otherwise uses character-level heuristics (~15% accuracy):

```bash
# Install exact token counting
pip install "helen[accurate-tokens]"
```

### History Compression Strategies

v1.11 provides three compression modes:

| Mode | Description | Use Case |
|------|------|---------|
| `summarize` (default) | Three-layer compression: recent → middle → oldest | Long conversations maintaining context |
| `truncate` | Directly drops old messages | Simple scenarios |
| `none` | No compression (may exceed context limits) | Short conversations/testing |

```python
# Dynamically switch compression mode
interpreter._history_manager.set_compression_mode("truncate")
```
