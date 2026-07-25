# Helen Programming Assistant

AI-powered programming assistant built with Helen language.

## Architecture

**Single Long-lived Actor** (v8.0)
- ChatSessionActor handles all conversations
- Direct tool access (no specialist agent delegation)
- Knowledge loaded on-demand via `load_skill`
- Channel communication with Web UI
- Context accumulates in session (no resume bottleneck)

## Installation

### Step 1: Install Helen with agent support

```bash
# Option A: Install with agent dependencies
pip install helen-lang[agent]

# Option B: Install base + agent separately
pip install helen-lang
pip install fastapi uvicorn[standard] websockets sqlalchemy \
            pydantic pydantic-settings python-dotenv python-multipart
```

### Step 2: Install Node.js (for frontend)

Download from https://nodejs.org/ (version 18+)

### Step 3: Configure LLM API

Edit `~/.helen/config.yaml`:

```yaml
llm:
  base_url: "https://api.openai.com/v1"
  api_key: "your-api-key"
  model: "gpt-4"
```

### Step 4: Launch

```bash
helen agent
```

The first launch will automatically install frontend dependencies (npm install).

## Key Features

- 💬 **Web-based interface** - Modern chat UI
- 🧠 **Smart context** - Working memory, graduated compression
- 📚 **Skill system** - Domain knowledge as loadable skills
- 🔄 **Session management** - Resume conversations, persistent history
- ⚡ **Low latency** - Streaming chunks via FFI (not Channel)
- 🎯 **Direct tools** - LLM calls tools directly (no delegation)

## How It Works

```
User Input → Web UI → Channel → ChatSessionActor
                                      ↓
                              LLM (llm act)
                                      ↓
                          Direct tool calls (read_file, write_file, etc.)
                                      ↓
                              Response → Channel → Web UI
```

The actor maintains a long-lived session. Context accumulates naturally.
No need to resume sessions repeatedly.

## Included Skills

- `helen-contractor-design` - 契约设计方法论
- `helen-test-patterns` - 测试生成方法论
- `helen-tdd-methodology` - TDD 方法论
- `helen-quality-rubrics` - 7 维质量评分规则
- `helen-code-integrity` - 代码完整性检查
- `multi-agent-orchestration` - 多 Agent 编排模式

## Requirements

- Python 3.12+
- Node.js 18+ (for frontend)
- LLM API configured in `~/.helen/config.yaml`

## Development

This is a snapshot of helenagent included in the Helen language package.
The independent project continues active development.

## License

MIT
