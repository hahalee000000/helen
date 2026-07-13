# 运行时系统

> 模块 M7 (`helen/runtime/`) | HLD 3.8

---

## Runtime ABC (12 方法)

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

**Core 代码从不直接 import Hermes**，只通过这个接口交互。

---

## HelenHermesRuntime

默认实现，继承 `Runtime` ABC：

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

## 可取消 LLM 调用

### _CallHandle

```python
class _CallHandle:
    cancelled: threading.Event   # 取消信号
    result: Any                  # 调用结果
    exception: Exception | None  # 异常
    done: threading.Event        # 完成信号
```

### cancel_llm_call()

```python
def cancel_llm_call(self, call_id: str) -> bool:
    with self._lock:
        handle = self._active_calls.get(call_id)
    if handle is None:
        return False          # 未找到或已完成
    handle.cancelled.set()
    return True               # 已发送取消信号
```

### CancelledError

```python
class CancelledError(Exception):
    def __init__(self, call_id: str):
        self.call_id = call_id
        super().__init__(f"LLM call {call_id} was cancelled")
```

---

## MockLLMRuntime (测试用)

```python
@dataclass
class MockLLMRuntime(LLMRuntime):
    route_return: str | None = None       # 预设 route() 返回值
    act_return: LLMResponse | str | None  # 预设 act() 返回值
    route_fail: Exception | None = None   # 预设 route() 异常
    act_fail: Exception | None = None     # 预设 act() 异常
    route_history: list[dict]             # 调用记录
    act_history: list[dict]               # 调用记录
```

支持确定性测试，无需真实 LLM。

---

## HermesCLILLMRuntime（CLI 模式，慢速）

通过 Hermes CLI 调用 LLM（备用方案）：

```python
@dataclass
class HermesCLILLMRuntime(LLMRuntime):
    hermes_path: str = "hermes"      # Hermes CLI 路径
    default_model: str | None = None # 默认模型
    timeout: int = 120               # 超时秒数
```

**性能：** 15-17秒/次（包含进程启动开销）

**使用场景：**
- HTTP API 不可用时的备用方案
- 需要 hermes 特殊功能（skills、tools）时

---

## HttpLLMRuntime（HTTP 模式，快速）

直接调用 OpenAI 兼容 API（推荐）：

```python
@dataclass
class HttpLLMRuntime(LLMRuntime):
    base_url: str = ""      # API 端点
    api_key: str = ""       # API 密钥
    default_model: str = "qwen3.7-plus"  # 默认模型
    timeout: int = 120
```

**配置加载：** 通过 `helen.runtime.config` 模块，按优先级从多个源加载：

| 优先级 | 文件 | 说明 |
|--------|------|------|
| 1（最低） | `~/.hermes/.env` | Hermes 兼容回退 |
| 2 | `~/.helen/.env` | Helen .env 格式 |
| 3 | `~/.helen/config.yml` | Helen YAML |
| 4（最高） | `~/.helen/config.yaml` | Helen YAML |

支持的环境变量名：
- `HELEN_BASE_URL` / `DASHSCOPE_BASE_URL` / `OPENAI_BASE_URL`
- `HELEN_API_KEY` / `DASHSCOPE_API_KEY` / `OPENAI_API_KEY`
- `HELEN_MODEL` / `DEFAULT_MODEL`
- `HELEN_TEMPERATURE` / `TEMPERATURE`
- `HELEN_TIMEOUT` / `TIMEOUT`

**性能：** 7-11秒/次（无进程启动开销）

**实现原理：**
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

**使用场景：**
- REPL 交互（默认）
- 脚本模式（`helen <file>`）
- 需要快速响应的场景
- 生产环境部署

---

## 内置工具系统

Helen 提供 7 个内置工具，LLM 可在 `llm act` 执行期间通过 function calling 调用：

| 工具 | 功能 | 参数 |
|------|------|------|
| `web_search` | 搜索 Wikipedia | `query: str` |
| `web_fetch` | 获取网页内容 | `url: str` |
| `read_file` | 读取文件 | `path: str` |
| `write_file` | 写入文件（覆盖） | `path: str, content: str` |
| `patch_file` | 精确修改文件（模糊匹配） | `path, old_string, new_string` |
| `shell_exec` | 执行 shell 命令 | `command: str` |
| `calculate` | 数学计算 | `expression: str` |

### patch_file 模糊匹配

`patch_file` 使用 9 种匹配策略，处理 LLM 生成代码的常见差异：

| # | 策略 | 处理场景 |
|---|------|---------|
| 1 | Exact | 精确匹配 |
| 2 | Line-trimmed | 行首尾空格差异 |
| 3 | Whitespace-normalized | 多个空格/tab 归一化 |
| 4 | Indentation-flexible | 缩进完全忽略 |
| 5 | Escape-normalized | `\n` `\t` 转义差异 |
| 6 | Trimmed-boundary | 首尾行空白修剪 |
| 7 | Unicode-normalized | 智能引号、破折号等 |
| 8 | Block-anchor | SequenceMatcher 相似度 |
| 9 | Context-aware | 逐行相似度 |

工具注册表位于 `helen/runtime/tools.py`，模糊匹配引擎位于 `helen/runtime/fuzzy_match.py`（从 Hermes 集成，独立运行）。

```python
@dataclass
class HelenTool:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema
    handler: Callable[..., str]
```

Agent 通过 `tools` 配置声明可用工具：

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

## Skill 系统

Skill 目录扫描优先级：

1. `~/.helen/skills/` — Helen 原生 skill
2. `~/.hermes/skills/` — Hermes 回退
3. `~/.hermes/hermes-agent/skills/` — Hermes agent skill

### 两阶段披露 (Two-Phase Disclosure)

Helen 实现了 HLD §3.7.1 的两阶段 skill 披露机制：

**Tier 1: Skill Index（轻量级索引）**

`PromptBuilder.build_skill_index()` 扫描 skill 目录，读取 SKILL.md 的 YAML frontmatter（name, description, category），格式化为 `<available_skills>` XML 块注入 System Prompt：

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

**Tier 2: load_skill 工具（按需加载）**

`load_skill` 工具注册在 `helen/runtime/tools.py`，LLM 可通过 function calling 按需加载完整 SKILL.md 内容：

```python
# LLM 调用 load_skill 工具
dispatch_tool('load_skill', {'name': 'helen-language'})
# 返回完整的 SKILL.md 内容（67KB+）
```

**优势**：
- Tier 1 只占用 ~16KB token（所有 skill 的名称+描述）
- Tier 2 按需加载，只在 LLM 需要时才加载完整内容
- 避免每次都发送大量 skill 内容浪费 token

---

## 性能对比

| Runtime | 调用时间 | 开销来源 |
|---------|---------|---------|
| HttpLLMRuntime | 7-11s | 网络延迟 + LLM 推理 |
| HermesCLILLMRuntime | 15-17s | 进程启动 + 配置加载 + 网络 + 推理 |

**REPL 默认使用 HttpLLMRuntime**，性能提升约 2 倍。

---

## llm act 表达式

`llm act` 支持两种使用形式：

### 1. 语句形式（在 agent 上下文中）

```helen
agent Translator(text) {
    prompt "Translate text"
    model "gpt-4"
    main {
        llm act Translator(text=text) "Translate to Chinese"
    }
}
```

语法：`llm act target(arg=value, ...) "description"`

### 2. 表达式形式（直接调用 LLM）

```helen
// 顶层直接调用
llm act "translate hello to chinese."

// 在函数中使用
fn translate(text, target) {
    return llm act "translate " + text + " to " + target
}

// 赋值给变量
let result = llm act "summarize this article"

// 在 agent 中使用
agent Smart(text) {
    main {
        return llm act "analyze: " + text
    }
}
```

语法：`llm act <expression>`

表达式形式会：
- 计算表达式的值作为 prompt
- 调用 LLM runtime
- 返回 LLM 响应文本（字符串）

### Parser 消歧义

Parser 通过前瞻判断形式：
- 如果 `llm act` 后是 IDENTIFIER，且后面跟着 `(` 或 STRING → 语句形式
- 否则 → 表达式形式

---

## Memory 系统

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

JSON 文件持久化：

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

纯内存实现，用于测试。

---

## v1.10 异步 HTTP 支持

### 概述

v1.10 添加了异步 HTTP 方法，基于 `httpx.AsyncClient` 实现，支持并发 LLM 调用。

### 异步方法

```python
class LLMRuntime:
    # 同步方法
    def act(self, target: str, description: str, **kwargs) -> Any
    def act_stream(self, target: str, description: str, **kwargs) -> Iterator[str]
```

**v1.18 变更**: `act_async()` / `act_stream_async()` 已删除，由 `spawnagent` + Channel 替代。并发 LLM 调用现在通过 spawnagent 实现：

```helen
// v1.18 并发 LLM 调用
let m1 = spawnagent AgentA("task1")
let m2 = spawnagent AgentB("task2")
let [r1, r2] = [m1.receive(), m2.receive()]
```

### httpx.Client

同步方法使用 `httpx.Client`：

```python
class HttpLLMRuntime(LLMRuntime):
    def __init__(self, base_url: str, api_key: str, model: str):
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0
        )
```

**v1.18 变更**: `httpx.AsyncClient` 已删除，并发通过 `spawnagent`（threading.Thread）实现。

### 使用示例

```helen
agent MyAgent {
  main {
    // 同步调用
    let result = llm act Translate "Hello"
    
    // 并发调用（v1.18 spawnagent）
    let m1 = spawnagent Translate("Hello")
    let m2 = spawnagent Translate("World")
    let r1 = m1.receive()
    let r2 = m2.receive()
  }
}
```

### 连接池管理

`httpx.Client` 自动管理连接池：

- **连接复用**: 多个请求复用同一 TCP 连接
- **并发控制**: 通过 `spawnagent`（threading.Thread）实现并发
- **超时管理**: 统一的超时配置
- **资源清理**: 程序退出时自动关闭连接

### 性能优势

| 场景 | 串行 | spawnagent 并发 | 提升 |
|------|------|----------------|------|
| 单次调用 | 1.5s | 1.5s | 0% |
| 3 次并发 | 4.5s | ~1.6s | 65% |
| 10 次并发 | 15s | ~2.1s | 86% |

**注意**: v1.18 起并发通过 `spawnagent` 实现，每个 spawned agent 在独立 daemon 线程中运行。

### 错误处理

异步方法使用相同的错误处理机制：

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

**最后更新**: 2026-07-04  
**版本**: v1.11

---

## P4 历史管理增强（v1.11 新增）

> v1.11 引入了完整的历史持久化、检索和上下文可视化功能。

### 历史持久化

跨会话保留对话连续性：

```helen
agent PersistentAgent {
    main {
        // 保存当前历史到 JSON 文件
        save_history("./session.json")
        
        // 从文件加载历史（下次启动时）
        let loaded = load_history("./session.json")
        print("Loaded " + str(loaded) + " messages")
    }
}
```

**JSON 格式**：
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

### 历史检索

Agent 可以查询历史中的特定信息：

```helen
agent SmartResearcher {
    tools ["web_search", "load_skill"]
    main {
        // 搜索之前的工具调用
        let past_searches = search_history(tool_name="web_search")
        
        // 按角色过滤
        let user_questions = search_history(role="user")
        
        // 文本搜索（大小写不敏感）
        let mentions = search_history(query="Python")
        
        // 获取工具调用历史
        let tool_log = get_tool_history("web_search")
        
        return llm act "Continue research..."
    }
}
```

### 上下文使用可视化

REPL 中用 `:stats` 命令查看上下文使用统计：

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

### Token 估算增强

v1.11 支持可选的 tiktoken 精确计数（安装 `helen[accurate-tokens]`），否则使用字符级启发式（~15% 精度）：

```bash
# 安装精确 token 计数
pip install "helen[accurate-tokens]"
```

### History 压缩策略

v1.11 提供三种压缩模式：

| 模式 | 说明 | 使用场景 |
|------|------|---------|
| `summarize`（默认） | 三层压缩：recent → middle → oldest | 长对话保持上下文 |
| `truncate` | 直接丢弃旧消息 | 简洁场景 |
| `none` | 不压缩（可能超出上下文限制） | 短对话/测试 |

```python
# 动态切换压缩模式
interpreter._history_manager.set_compression_mode("truncate")
```
