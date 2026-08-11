# Helen 调试功能开发方案

## Context

Helen v1.39.10 的调试能力在动态语言里属中上，AI 原生可观测性（transcript、llm_log、error snapshot）领先，但离"调试体验最好的语言"有距离。本方案基于 `reports/helen-debugging-roadmap-ai-perspective-2026-08-11.md` 的决策结果，实现 6 个调试功能。

**核心筛选标准**：功能做了之后 LLM 作为 SKILL.md 消费者是否会高概率使用。只保留 Push 模型（80-95%）和高概率 Pull 模型（50-60%）功能。

**预期结果**：
- P0 完成（~3 周）：AI 调试 Helen 从"翻 transcript"升级为"精准查询 + 结构化错误诊断"
- P1 完成（再 +3 周）：AI 调试 Helen 具备录制重放 + 数据血缘 + 事后回放能力

**关键约束**：
- Runtime 错误链 100% 确定性：不调 LLM，纯静态（模板 + fuzzy + 规则）
- TranscriptStore 默认 JSONL 后端（`config.get("backend", "jsonl")`），SQLite 需显式启用
- 错误分类一步到位覆盖全部 10 种异常类型
- 数据血缘用独立 SQLite sidecar `<session_id>_lineage.db`
- SKILL.md 用"第一步必须 / ❌ 禁止"强制语气

---

## 整体架构

```
新增模块：
  helen/runtime/error_diagnostics.py    ← P0: 错误分类 + suggestion 生成
  helen/runtime/recording.py            ← P1: LLM 录制/重放
  helen/runtime/data_lineage.py         ← P1: 数据血缘 sidecar

修改模块：
  helen/runtime/observability.py        ← ErrorSnapshot 扩展字段
  helen/runtime/transcript_store.py     ← 新增 query() 抽象方法
  helen/stdlib/__init__.py              ← 注册新 stdlib 函数
  helen/stdlib/transcript.py            ← query_transcript() 实现
  helen/stdlib/debug.py（新建）          ← 调试相关 stdlib 函数
  helen/runtime/http_llm.py             ← 录制钩子插入点
  helen/runtime/channel.py              ← 数据血缘追踪
  helen/interpreter/interpreter.py      ← 错误捕获增强
```

---

## Phase 1: 结构化错误分类 + 数据流回溯（P0，~1 周）

### 目标
- ErrorSnapshot 新增 `suggestion`、`data_flow`、`diagnostic_category` 字段
- 错误发生时由 runtime 自动填充（纯静态，零 LLM）
- 覆盖全部 10 种异常类型
- `:last_error` 和 `repl_last_error` 工具自动输出新字段

### API 设计

#### ErrorSnapshot 新增字段（observability.py）

```python
@dataclass
class ErrorSnapshot:
    # ... 现有字段 ...
    
    # 新增字段：
    diagnostic_category: str = ""          # 语义分类，如 "LLMOutputFormatMismatch"
    suggestion: str = ""                   # 静态 suggestion 文本
    data_flow: list[dict[str, Any]] = field(default_factory=list)
    # data_flow 元素格式：
    # {"source": "msg_abc123", "via": "Reviewer llm_act", "origin": "Coder agent 输出"}
```

#### stdlib 新函数

```helen
# stdlib/debug.py（新模块，需 import std.debug.*）
last_error_detail() -> dict?
  # 返回 ErrorSnapshot.to_dict() 的新版本，包含 suggestion / data_flow / diagnostic_category
  # 如果没有错误返回 null

error_category(err: dict) -> str
  # 从错误 dict 提取 diagnostic_category
  
error_suggestion(err: dict) -> str
  # 从错误 dict 提取 suggestion
```

### 数据模型

#### ERROR_SUGGESTION_REGISTRY（error_diagnostics.py 新建）

```python
ERROR_SUGGESTION_REGISTRY: dict[str, dict] = {
    "AnyError": {
        "category": "GenericError",
        "template": "通用错误。检查错误消息 '{message}' 里的具体描述。",
        "fields": ["message"],
    },
    "LLMError": {
        "category": "LLMGenericError",
        "template": "LLM 调用失败。检查 LLM 配置（base_url、api_key、model）是否正确。",
        "fields": [],
    },
    "TimeoutError": {
        "category": "LLMTimeout",
        "template": "LLM 调用超时。考虑：(1) 增加 timeout 配置，(2) 减小 prompt 长度，(3) 检查网络连接。",
        "fields": [],
    },
    "ModelError": {
        "category": "LLMModelUnavailable",
        "template": "模型不可用或配额耗尽。检查：(1) model 名称是否正确，(2) API key 是否有效，(3) 账户余额。",
        "fields": [],
    },
    "PromptTooLongError": {
        "category": "LLMContextOverflow",
        "template": "Prompt 超出模型上下文窗口（{tokens_used}/{tokens_limit} tokens）。"
                   "使用 compress_context() 压缩历史，或 clear_context() 清空，"
                   "或减小 agent prompt 模板大小。",
        "fields": ["tokens_used", "tokens_limit"],
    },
    "AgentError": {
        "category": "AgentCallFailed",
        "template": "Agent '{agent_name}' 调用失败。根因：{cause}。"
                   "检查：(1) agent 参数类型是否匹配，(2) agent 内部逻辑是否有 bug，"
                   "(3) agent 的 LLM 调用是否失败（用 :llm_log 查看）。",
        "fields": ["agent_name", "cause"],
    },
    "ToolError": {
        "category": "ToolCallFailed",
        "template": "工具调用失败。检查：(1) 工具参数是否符合 schema，(2) 工具是否返回错误，"
                   "(3) 加重试逻辑或 try/catch 包裹。",
        "fields": [],
    },
    "RuntimeError": {
        "category": "RuntimeGenericError",
        "template": "运行时错误：{message}。检查变量类型和边界条件。",
        "fields": ["message"],
        "rules": [
            # 规则 1：除零
            {"match": "division by zero", "suggestion": "除零错误。在除法前检查分母是否为 0。"},
            # 规则 2：类型错误
            {"match": "expected.*, got.*", "suggestion": "类型不匹配。检查函数返回值类型是否符合预期。"},
            # 规则 3：未定义变量
            {"match": "undefined variable.*", "suggestion": "未定义变量。检查变量是否已声明，或作用域是否正确。"},
        ],
    },
    "AssertionError": {
        "category": "AssertionFailed",
        "template": "断言失败：{message}。程序状态不符合预期。检查断言条件是否正确，以及上游数据是否异常。",
        "fields": ["message"],
    },
    "AggregateError": {
        "category": "MultipleFailures",
        "template": "{error_count} 个并发任务失败。查看 errors 列表里的每个具体错误。"
                   "通常先修第一个错误，后续错误可能是级联失败。",
        "fields": ["error_count"],
    },
}
```

#### 数据流回溯生成规则

```python
def _build_data_flow(snapshot: ErrorSnapshot, error: Exception) -> list[dict]:
    """从错误上下文推断数据流。"""
    flow = []
    
    # 规则 1：如果 scope 里有 Message 类型变量，追溯到它的来源
    for name, value in snapshot.scope.items():
        if isinstance(value, Message) and hasattr(value, "uuid"):
            flow.append({
                "variable": name,
                "source": value.uuid,
                "via": getattr(value, "agent_name", "unknown"),
            })
    
    # 规则 2：如果 call_stack 里有 agent 调用，追溯到 agent 输出
    for frame in snapshot.call_stack:
        if frame.get("function", "").startswith("agent:"):
            flow.append({
                "source": "agent_output",
                "via": frame["function"],
                "origin": frame.get("location", ""),
            })
    
    return flow
```

### 代码修改清单

| 文件 | 改动 | 具体位置 |
|---|---|---|
| `helen/runtime/error_diagnostics.py` | **新建**。ERROR_SUGGESTION_REGISTRY + `generate_suggestion(error_type, message, context)` + `_build_data_flow()` | 新文件 |
| `helen/runtime/observability.py` | ErrorSnapshot 新增 3 个字段 + `format_text()` 输出新字段 | L271-L353 |
| `helen/runtime/observability.py` | `ObservabilityManager.capture_error()` 调用 `generate_suggestion()` 填充新字段 | L489-L512 |
| `helen/interpreter/exceptions.py` | 不修改。保留现有异常层级 | 只读参考 |
| `helen/stdlib/debug.py` | **新建**。`last_error_detail()`、`error_category()`、`error_suggestion()` 实现 | 新文件 |
| `helen/stdlib/__init__.py` | 注册新模块 `std.debug.*` + 3 个新函数 | `_register_debug()` 附近 |
| `helen/cli/repl.py` | `:last_error` 输出新增 suggestion/data_flow 段 | L356-L365 |
| `helen/cli/ask_assistant.py` | `repl_last_error` 工具输出新版 ErrorSnapshot | L164-L175 |

### 测试策略

| 测试文件 | 场景 |
|---|---|
| `tests/runtime/test_error_diagnostics.py`（新建） | 10 种异常类型各自的 suggestion 生成 |
| `tests/runtime/test_error_diagnostics.py` | RuntimeError 的 3 条规则匹配（除零、类型错误、未定义变量） |
| `tests/runtime/test_error_diagnostics.py` | 数据流回溯（scope 里有 Message、call_stack 里有 agent） |
| `tests/runtime/test_observability.py` | ErrorSnapshot 新字段序列化（to_dict）+ 文本格式化（format_text） |
| `tests/stdlib/test_debug.py`（新建） | last_error_detail / error_category / error_suggestion 函数 |
| `tests/cli/test_repl.py` | `:last_error` 输出包含 suggestion 字段 |

### 依赖
- 无前置依赖。复用 `fuzzy_match.py` 的 `find_closest_lines()`（可选增强）。

### 风险
- **数据流回溯准确性**：scope 里的 Message 不一定能追溯到确切来源（如果没有 uuid）。保守策略：只展示能确定的部分。
- **suggestion 模板维护**：10 个模板 + 规则库需要持续扩展。建议先实现基础版，后续根据实际错误分布迭代。

---

## Phase 2: Output contract 检查（P0，3-5 天）

### 目标
- Agent 声明里支持 `output_contract: "json"` 或 `output_contract: {type: "object", required: ["verdict"]}`
- LLM 输出后自动校验，不符合时抛出 `LLMOutputContractError`（新增异常类型）
- 错误消息包含具体的 schema violation 信息

### API 设计

#### Agent 声明语法（parser 扩展）

```helen
agent Reviewer {
    model: "qwen3.7-plus"
    output_contract: "json"                    # 简写：期望合法 JSON
    # 或
    output_contract: {                          # 详细 schema
        type: "object",
        required: ["verdict", "confidence"],
        properties: {
            verdict: {type: "string", enum: ["pass", "fail"]},
            confidence: {type: "number", min: 0, max: 1}
        }
    }
    main {
        llm act "Review this code..."
    }
}
```

#### 新增异常类型

```python
# helen/interpreter/exceptions.py
class LLMOutputContractError(LLMError):
    """LLM output does not match agent's output_contract."""
    
    agent_name: str = ""
    contract: Any = None
    actual_output: str = ""
    violation: str = ""        # 具体违反的约束
    
    def __init__(self, agent_name="", contract=None, actual_output="", 
                 violation="", message=None, span=None):
        ...
```

#### stdlib 函数（可选，用户可手动调用）

```helen
validate_output(output: str, contract: Any) -> dict
  # 返回 {"valid": bool, "violation": str, "parsed": Any}
```

### 数据模型
- Agent 声明节点 `AgentDeclNode` 新增 `output_contract` 字段（`helen/core/ast.py` L699-L712）
- Parser 解析 `output_contract: <expr>`（`helen/core/parser.py` L841-L857 附近）

### 代码修改清单

| 文件 | 改动 | 具体位置 |
|---|---|---|
| `helen/core/ast.py` | `AgentDeclNode` 新增 `output_contract` 字段 | L699-L712 |
| `helen/core/parser.py` | 解析 `output_contract: <expr>` | L841-L857 |
| `helen/interpreter/exceptions.py` | 新增 `LLMOutputContractError` 类 + 注册到 `_PREDEFINED_EXCEPTIONS` | L113-L268 |
| `helen/interpreter/llm_mixin.py` | `_visit_llm_act()` 后插入 output 校验逻辑 | L435-L467 后 |
| `helen/runtime/output_validator.py` | **新建**。`validate_output(output, contract) -> ValidationResult` | 新文件 |
| `helen/runtime/error_diagnostics.py` | 新增 `LLMOutputContractError` 的 suggestion 模板 | ERROR_SUGGESTION_REGISTRY |
| `helen/stdlib/debug.py` | 新增 `validate_output()` stdlib 函数 | 新文件 |

### 测试策略

| 测试文件 | 场景 |
|---|---|
| `tests/interpreter/test_output_contract.py`（新建） | agent 声明 `output_contract: "json"`，LLM 返回合法 JSON → 通过 |
| `tests/interpreter/test_output_contract.py` | agent 声明 `output_contract: "json"`，LLM 返回纯文本 → 抛 `LLMOutputContractError` |
| `tests/interpreter/test_output_contract.py` | 详细 schema 校验（required 字段、type、enum） |
| `tests/runtime/test_output_validator.py`（新建） | validate_output() 函数单元测试 |
| `tests/runtime/test_error_diagnostics.py` | LLMOutputContractError 的 suggestion 生成 |

### 依赖
- Phase 1（需要 ErrorSnapshot 扩展字段承载 contract violation 信息）

### 风险
- **parser 改动**：新增 `output_contract` 语法需要谨慎处理向后兼容（默认无 contract）
- **schema 复杂度**：JSON Schema 全功能实现成本高，建议先支持子集（type、required、enum、properties）
- **性能**：每次 LLM 输出都校验，需要确保 validator 快速（<1ms for simple contracts）

---

## Phase 3: 增量 transcript 查询 API（P0，~1 周）

### 目标
- `TranscriptStoreBackend` 新增 `query()` 抽象方法（默认实现：load_all + 内存过滤）
- `SQLiteBackend` 用 SQL WHERE 下推实现高效查询
- `JSONLBackend` 沿用默认实现（流式加载 + 过滤，加 10 万条上限）
- stdlib 新增 `query_transcript()` 函数，AI 可精准切片 transcript

### API 设计

#### TranscriptStoreBackend.query() 抽象方法

```python
# helen/runtime/transcript_store.py

class TranscriptStoreBackend(ABC):
    # ... 现有抽象方法 ...
    
    def query(
        self,
        *,
        roles: list[str] | None = None,           # ["user", "assistant"]
        agent_names: list[str] | None = None,     # ["Reviewer"]
        invocation_ids: list[str] | None = None,  # ["inv_xyz"]
        since: float | None = None,               # timestamp
        until: float | None = None,               # timestamp
        content_regex: str | None = None,         # regex on content
        message_types: list[str] | None = None,   # ["llm_act", "tool_call"]
        limit: int | None = None,                 # max results
        offset: int = 0,                          # for pagination
    ) -> list[Message | BoundaryMarker]:
        """Default: load_all() + filter in Python. Override for indexed backends."""
        items = self.load_all()
        return _apply_filters(items, roles=roles, agent_names=agent_names, ...)
```

#### stdlib query_transcript()

```helen
# stdlib/transcript.py 新增
query_transcript(
    session_id: str = "",
    role: str = "",                    # "user" / "assistant" / "tool"
    agent: str = "",                   # agent 名称
    invocation_id: str = "",           # 具体 invocation
    since: float = 0,                  # timestamp
    until: float = 0,                  # timestamp
    content_regex: str = "",           # regex
    message_type: str = "",            # "llm_act" / "tool_call"
    limit: int = 1000,                 # 默认上限
    offset: int = 0
) -> list[dict]
  # 返回结构化消息列表（每条消息含 uuid, role, content, agent_name, invocation_id, timestamp）
  # 当结果 > limit 时，返回 {truncated: true, count: N, hint: "use offset/limit for pagination"}
```

### 数据模型

#### SQLiteBackend 查询优化

```python
# SQLiteBackend.query() 实现
def query(self, **filters) -> list:
    clauses = []
    params = []
    
    if filters.get("roles"):
        placeholders = ",".join("?" * len(filters["roles"]))
        clauses.append(f"JSON_EXTRACT(data, '$.role') IN ({placeholders})")
        params.extend(filters["roles"])
    
    if filters.get("agent_names"):
        placeholders = ",".join("?" * len(filters["agent_names"]))
        clauses.append(f"JSON_EXTRACT(data, '$.agent_name') IN ({placeholders})")
        params.extend(filters["agent_names"])
    
    if filters.get("since"):
        clauses.append("timestamp >= ?")
        params.append(filters["since"])
    
    if filters.get("until"):
        clauses.append("timestamp <= ?")
        params.append(filters["until"])
    
    # ... 其他过滤条件 ...
    
    sql = "SELECT data FROM transcript"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY id ASC"
    
    if filters.get("limit"):
        sql += f" LIMIT {filters['limit']} OFFSET {filters.get('offset', 0)}"
    
    cursor = self.conn.execute(sql, params)
    return [json.loads(row[0]) for row in cursor]
```

#### 建议新增索引（SQLiteBackend）

```python
# SQLiteBackend.__init__() 里新增
self.conn.executescript("""
    CREATE INDEX IF NOT EXISTS idx_role ON transcript(JSON_EXTRACT(data, '$.role'));
    CREATE INDEX IF NOT EXISTS idx_agent ON transcript(JSON_EXTRACT(data, '$.agent_name'));
    CREATE INDEX IF NOT EXISTS idx_type ON transcript(JSON_EXTRACT(data, '$.message_type'));
""")
```

### 代码修改清单

| 文件 | 改动 | 具体位置 |
|---|---|---|
| `helen/runtime/transcript_store.py` | `TranscriptStoreBackend` 新增 `query()` 默认实现 | L234-L300 后 |
| `helen/runtime/transcript_store.py` | `SQLiteBackend` override `query()` + 新增索引 | L490-L703 |
| `helen/runtime/transcript_store.py` | `JSONLBackend` 沿用默认实现（可选 override 加流式过滤） | L303-L488 |
| `helen/runtime/transcript_store.py` | `TranscriptStore` 层新增 `query()` 便捷方法 | L774-L1371 |
| `helen/stdlib/transcript.py` | 新增 `query_transcript()` stdlib 函数 | 现有 transcript.py 后 |
| `helen/stdlib/__init__.py` | 注册 `query_transcript` 到 stdlib | `_register_transcript()` 附近 |

### 测试策略

| 测试文件 | 场景 |
|---|---|
| `tests/runtime/test_transcript_query.py`（新建） | TranscriptStoreBackend.query() 默认实现（内存过滤） |
| `tests/runtime/test_transcript_query.py` | SQLiteBackend.query() 各过滤条件（role/agent/time/regex/limit/offset） |
| `tests/runtime/test_transcript_query.py` | JSONLBackend.query() 10 万条上限测试 |
| `tests/runtime/test_transcript_query.py` | 双后端结果一致性（同一数据集，JSONL 和 SQLite 返回相同结果） |
| `tests/stdlib/test_query_transcript.py`（新建） | query_transcript() stdlib 函数测试 |
| `tests/stdlib/test_search_transcript.py` | 现有 search_transcript 改用 store.query() 后回归测试 |

### 依赖
- 无前置依赖。

### 风险
- **JSON_EXTRACT 性能**：SQLite JSON 函数索引在大表上可能不如列索引快。如果性能不达标，考虑把 `role`/`agent_name` 抽成独立列（需要 schema migration）。
- **JSONL 大文件**：10 万条消息的 JSONL 文件加载可能 OOM。保守策略：超过上限时报错提示用户切换 SQLite。
- **向后兼容**：现有 `search_transcript` 和 `replay_transcript` 改用 `store.query()` 时需要回归测试。

---

## Phase 4: Agent 录制/重放（P1，~1 周）

### 目标
- 录制：把 LLM 完整 request/response 写入 cassette 文件
- 重放：用录制数据替代真实 LLM 调用，确定性重跑 agent
- 支持按 session 或按 agent 录制/重放

### API 设计

#### stdlib 函数

```helen
# stdlib/debug.py 新增
record_session(session_id: str = "") -> dict
  # 开始录制当前 session 的所有 LLM 调用
  # 返回 {"status": "recording", "cassette_path": "..."}

stop_recording() -> dict
  # 停止录制，返回 {"status": "stopped", "entries": N, "cassette_path": "..."}

replay_session(cassette_path: str, session_id: str = "") -> dict
  # 用 cassette 数据替代 LLM 调用，重放 session
  # 返回 {"status": "replayed", "entries_used": N, "mismatches": [...]}
```

#### Agent 声明语法（可选扩展）

```helen
@record agent MyAgent {    # 装饰器形式，自动录制
    model: "qwen3.7-plus"
    main { ... }
}

@replay("path/to/cassette.jsonl") agent MyAgent {    # 装饰器形式，自动重放
    model: "qwen3.7-plus"
    main { ... }
}
```

### 数据模型

#### Cassette 文件格式（JSONL）

```jsonl
{"type": "llm_call", "seq": 1, "timestamp": 1234567890.123, "agent_name": "Reviewer", "model": "qwen3.7-plus", "request": {"messages": [...], "tools": [...], "temperature": 0.7}, "response": {"content": "...", "tool_calls": [...]}}
{"type": "llm_call", "seq": 2, ...}
```

#### RecordingHook 接口

```python
# helen/runtime/recording.py（新建）

class RecordingHook(Protocol):
    def on_request(self, messages: list[dict], payload: dict, metadata: dict) -> None: ...
    def on_response(self, response_message: dict, usage: dict, duration_ms: float) -> None: ...
    def on_tool(self, tool_call: dict, result: Any) -> None: ...
    def on_turn_complete(self, full_messages: list[dict], final_response: dict) -> None: ...

class CassetteWriter:
    """Writes LLM calls to a JSONL cassette file."""
    def __init__(self, path: Path): ...
    def write_entry(self, entry: dict) -> None: ...
    def close(self) -> None: ...

class ReplayLLMRuntime(LLMRuntime):
    """Replays LLM calls from a cassette file."""
    def __init__(self, cassette_path: Path): ...
    def act(self, prompt, history=None, ...) -> LLMResponse:
        # 按 seq 顺序匹配，或按 messages 相似度匹配
        ...
```

### 代码修改清单

| 文件 | 改动 | 具体位置 |
|---|---|---|
| `helen/runtime/recording.py` | **新建**。CassetteWriter + ReplayLLMRuntime + RecordingHook | 新文件 |
| `helen/runtime/http_llm.py` | 插入录制钩子：`_chat_with_messages()` L995（request）、L1005-L1028（response） | 具体插入点 |
| `helen/runtime/llm_runtime.py` | `LLMRuntime` 新增 `hooks: list[RecordingHook]` 参数 | __post_init__ |
| `helen/stdlib/debug.py` | 新增 `record_session()`、`stop_recording()`、`replay_session()` stdlib 函数 | 新文件 |
| `helen/interpreter/interpreter.py` | `_call_agent()` 支持 `@record` / `@replay` 装饰器 | L1788 附近 |
| `helen/core/parser.py` | 解析 `@record` / `@replay` 装饰器（可选） | L841 附近 |

### 测试策略

| 测试文件 | 场景 |
|---|---|
| `tests/runtime/test_recording.py`（新建） | CassetteWriter 写入 + 读回一致性 |
| `tests/runtime/test_recording.py` | ReplayLLMRuntime 按 seq 匹配 |
| `tests/runtime/test_recording.py` | ReplayLLMRuntime 按 messages 相似度匹配（模糊匹配） |
| `tests/stdlib/test_recording.py`（新建） | record_session / stop_recording / replay_session stdlib 函数 |
| `tests/interpreter/test_agent_recording.py`（新建） | @record agent 端到端录制 + @replay 重放 |

### 依赖
- 无前置依赖。但建议在 Phase 3 之后实现（复用 transcript 查询能力定位要重放的 session）。

### 风险
- **messages 相似度匹配**：完全相同的 prompt 才能精确匹配。如果用户改了 prompt，相似度匹配可能返回错误的 response。保守策略：默认精确匹配（前缀相同），相似度匹配作为 opt-in。
- **tool_calls 录制**：tool 调用的结果需要完整录制（包括文件内容、HTTP 响应等），可能很大。保守策略：截断到 10KB。
- **向后兼容**：现有 `MockLLMRuntime` 不改动，`ReplayLLMRuntime` 是新类。

---

## Phase 5: 跨 agent 数据血缘追踪（P1，~2 周）

### 目标
- 记录 agent 间数据流动（谁产生、谁消费）
- 提供 stdlib 函数追溯值的来源和消费者
- 用独立 SQLite sidecar 文件存储

### API 设计

#### stdlib 函数

```helen
# stdlib/debug.py 新增
trace_value_origin(value: Any) -> list[dict]
  # 追溯 value 的来源
  # 返回：[{"source_uuid": "msg_abc", "agent": "Coder", "via": "llm_act", "timestamp": ...}]

trace_value_consumers(value_id: str) -> list[dict]
  # 追溯 value 被谁消费
  # 返回：[{"consumer_uuid": "msg_def", "agent": "Reviewer", "via": "prompt", "timestamp": ...}]

get_data_lineage(session_id: str = "") -> dict
  # 返回整个 session 的数据血缘图（节点 = 消息，边 = 数据流）
```

### 数据模型

#### SQLite sidecar schema（`<session_id>_lineage.db`）

```sql
CREATE TABLE data_lineage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producer_uuid TEXT NOT NULL,      -- 产生值的消息 UUID
    consumer_uuid TEXT NOT NULL,      -- 消费值的消息 UUID
    value_type TEXT,                  -- "llm_output" / "tool_result" / "channel_message"
    value_hash TEXT,                  -- 值的 hash（用于匹配）
    via TEXT,                         -- "prompt" / "channel" / "shared_store"
    timestamp REAL NOT NULL,
    metadata JSON                     -- 额外信息（如 channel name）
);

CREATE INDEX idx_producer ON data_lineage(producer_uuid);
CREATE INDEX idx_consumer ON data_lineage(consumer_uuid);
CREATE INDEX idx_timestamp ON data_lineage(timestamp);
```

#### DataLineageTracker 类

```python
# helen/runtime/data_lineage.py（新建）

class DataLineageTracker:
    """Tracks data flow between agents using SQLite sidecar."""
    
    def __init__(self, session_dir: Path):
        self.db_path = session_dir / f"{session_id}_lineage.db"
        self.conn = sqlite3.connect(str(self.db_path))
        self._init_schema()
    
    def record_flow(self, producer_uuid: str, consumer_uuid: str, 
                    value_type: str, value_hash: str, via: str, metadata: dict = None) -> None: ...
    
    def get_origin(self, value_hash: str) -> list[dict]: ...
    
    def get_consumers(self, producer_uuid: str) -> list[dict]: ...
    
    def get_full_lineage(self) -> dict: ...
    
    def close(self) -> None: ...
```

### 代码修改清单

| 文件 | 改动 | 具体位置 |
|---|---|---|
| `helen/runtime/data_lineage.py` | **新建**。DataLineageTracker + schema | 新文件 |
| `helen/runtime/channel.py` | `ChannelEndpoint.send()` / `receive()` 调用 DataLineageTracker.record_flow() | send/receive 方法 |
| `helen/interpreter/interpreter.py` | `_call_agent()` 记录参数传递（A→B 调用） | L1788 附近 |
| `helen/interpreter/llm_mixin.py` | `_add_to_history()` 记录 prompt 注入点 | L1590-L1618 |
| `helen/stdlib/debug.py` | 新增 `trace_value_origin()`、`trace_value_consumers()`、`get_data_lineage()` | 新文件 |
| `helen/interpreter/agent_context.py` | `AgentContextManager` 初始化 DataLineageTracker | _init_transcript_store 附近 |

### 测试策略

| 测试文件 | 场景 |
|---|---|
| `tests/runtime/test_data_lineage.py`（新建） | DataLineageTracker 基本 CRUD |
| `tests/runtime/test_data_lineage.py` | trace_value_origin 端到端 |
| `tests/runtime/test_data_lineage.py` | trace_value_consumers 端到端 |
| `tests/runtime/test_data_lineage.py` | Channel 消息自动记录 |
| `tests/runtime/test_data_lineage.py` | Agent 调用参数自动记录 |
| `tests/stdlib/test_data_lineage.py`（新建） | trace_value_origin / trace_value_consumers / get_data_lineage stdlib 函数 |

### 依赖
- 无强前置依赖。但建议在 Phase 3 之后实现（复用 transcript 查询定位消息）。

### 风险
- **性能开销**：每次 send/receive 都写 SQLite，可能拖慢 agent 通信。保守策略：批量写入（每 100 条 commit 一次）。
- **value_hash 碰撞**：用 hash 匹配值可能有碰撞。保守策略：用 (producer_uuid, value_hash) 复合键。
- **向后兼容**：DataLineageTracker 是 opt-in（agent 声明 `@track_lineage` 或全局配置），默认关闭。

---

## Phase 6: Transcript 事后回放（P1，中等）

### 目标
- 交互式回放器，逐步看 agent 状态变化
- 复用 Phase 3 的 query_transcript + Phase 5 的 data_lineage
- CLI 工具 + REPL 命令

### API 设计

#### CLI 工具

```bash
$ helen replay session_xyz --interactive
```

进入交互式回放器：
- `next` / `prev`：前进/后退一条消息
- `jump N`：跳到第 N 条消息
- `scope`：显示当前 scope 的所有变量
- `dataflow`：显示当前消息的数据血缘（如果 Phase 5 已实现）
- `filter agent=Reviewer`：只看某个 agent 的消息
- `quit`：退出

#### stdlib 函数（增强现有）

```helen
# stdlib/transcript.py 增强
replay_transcript_interactive(session_id: str = "") -> str
  # 进入交互式回放器（仅 REPL 可用）
```

### 数据模型
- 复用现有 TranscriptStore + Phase 3 的 query_transcript + Phase 5 的 data_lineage
- 不需要新数据模型

### 代码修改清单

| 文件 | 改动 | 具体位置 |
|---|---|---|
| `helen/cli/replay.py` | **新建**。交互式回放器 TUI | 新文件 |
| `helen/cli/__main__.py` | 新增 `helen replay` 子命令 | CLI 入口 |
| `helen/cli/repl.py` | 新增 `:replay` REPL 命令 | 现有命令列表 |
| `helen/stdlib/transcript.py` | 增强 `replay_transcript()`，支持 `interactive=True` 参数 | 现有函数 |

### 测试策略

| 测试文件 | 场景 |
|---|---|
| `tests/cli/test_replay.py`（新建） | 回放器 next/prev/jump 基本导航 |
| `tests/cli/test_replay.py` | 回放器 filter 功能 |
| `tests/cli/test_replay.py` | 回放器 dataflow 显示（需要 Phase 5） |

### 依赖
- Phase 3（query_transcript 用于高效切片）
- Phase 5（data_lineage 用于显示数据流，可选）

### 风险
- **TUI 复杂度**：交互式 TUI 开发成本高。保守策略：先做简单版（只支持 next/prev/quit），复杂版后续迭代。
- **向后兼容**：现有 `replay_transcript()` 函数不改签名，只新增 `interactive` 参数。

---

## SKILL.md 触发规则清单

```markdown
# Helen AI 调试技能

## 调试触发规则（必须遵守）

### 当你看到任何错误时：
1. **第一步必须**：调用 `last_error_detail()` 获取完整结构化错误信息（包含 Suggestion、Data flow、Diagnostic category）
2. **第二步必须**：如果 Suggestion 字段存在，优先按 Suggestion 行动
3. **第三步必须**：如果 Data flow 字段存在，先看数据流，再读源码
4. ❌ 禁止跳过错误信息自己推理根因
5. ❌ 禁止直接读源码猜错误原因

### 当你看到非确定性行为（同输入不同输出）时：
1. **第一步必须**：用 `record_session()` 录制 agent 执行
2. **第二步必须**：重放 3 次确认问题可复现
3. **第三步才**：分析录制的 cassette 找根因
4. ❌ 禁止不录制就试图分析非确定性 bug
5. ❌ 禁止直接改 prompt 碰运气

### 当 transcript 长度 > 2000 tokens 时：
1. **第一步必须**：用 `query_transcript()` 查询，不要全量加载
2. **第二步必须**：查询时加 filter 参数（role/agent/time_range）缩小范围
3. **第三步**：如果结果 > 1000 条，用 limit/offset 分页
4. ❌ 禁止把完整 transcript 读入上下文

### 当多 agent 系统出错时：
1. **第一步必须**：用 `trace_value_origin(error_value)` 追溯数据血缘
2. **第二步必须**：用 `trace_value_consumers(producer_uuid)` 看谁消费了错误值
3. **第三步才**：读相关 agent 的 transcript
4. ❌ 禁止不查血缘就直接读 transcript
5. ❌ 禁止假设数据流方向，必须用工具验证

### 当你想验证 prompt 修改是否有效时：
1. **第一步必须**：用 `record_session()` 录制修改前的行为
2. **第二步必须**：改 prompt 后用 `replay_session(cassette_path)` 对比
3. **第三步才**：确认行为变化符合预期
4. ❌ 禁止不录制就改 prompt
5. ❌ 禁止改完 prompt 直接跑一次就认为修好了
```

---

## 实现顺序与依赖关系

```
Phase 1 (错误分类) ──┐
                      ├──→ Phase 4 (录制/重放) ──→ Phase 6 (事后回放)
Phase 3 (查询 API) ──┘            │
                                   │
                      ├──→ Phase 5 (数据血缘) ────┘
                      │
Phase 2 (Output contract) ──┘
```

**并行机会**：
- Phase 1 + Phase 2 + Phase 3 可以并行（无互相依赖）
- Phase 4 + Phase 5 可以并行（都依赖 Phase 3，但不互相依赖）
- Phase 6 必须等 Phase 3 + Phase 5 完成

**关键路径**：
- Phase 1 → Phase 4 → Phase 6（错误分类 → 录制 → 回放）
- Phase 3 → Phase 5（查询 → 血缘）

**建议顺序**：
1. **第 1-2 周**：Phase 1 + Phase 2 + Phase 3（并行，P0 全部完成）
2. **第 3-4 周**：Phase 4 + Phase 5（并行，P1 大部分完成）
3. **第 5 周**：Phase 6（P1 收尾）

---

## 验证方法

### 端到端测试场景

**场景 1：结构化错误诊断**
```helen
agent Reviewer {
    model: "qwen3.7-plus"
    main {
        let result = llm act "Return a number"
        let x = result / 0    # 触发 RuntimeError
    }
}
```
预期：`:last_error` 输出包含：
- `diagnostic_category: "RuntimeGenericError"`
- `suggestion: "运行时错误：division by zero。在除法前检查分母是否为 0。"`

**场景 2：Output contract 校验**
```helen
agent Reviewer {
    model: "qwen3.7-plus"
    output_contract: "json"
    main {
        llm act "Return plain text"    # LLM 返回非 JSON
    }
}
```
预期：抛出 `LLMOutputContractError`，suggestion 说"LLM 返回纯文本而非 JSON。在 agent prompt 里显式要求 '返回严格的 JSON 格式'。"

**场景 3：增量 transcript 查询**
```helen
# session 有 5000 条消息
let msgs = query_transcript(agent="Reviewer", role="assistant", limit=100)
# 预期：只返回 Reviewer agent 的 assistant 消息，最多 100 条
```

**场景 4：录制/重放**
```helen
record_session()
agent Reviewer { main { llm act "..." } }
stop_recording()
# 修改 prompt 后：
replay_session("path/to/cassette.jsonl")
# 预期：用录制的 LLM response 重跑，输出确定性结果
```

**场景 5：数据血缘追踪**
```helen
agent Coder { main { let code = llm act "..." ; send(code) } }
agent Reviewer { main { let code = receive() ; llm act code } }
spawn Coder()
# 出错后：
trace_value_origin(code)
# 预期：返回 Coder agent 的 llm_act 输出
```

### 回归测试
- 现有 `pytest` 3694 个测试全部通过
- 新功能的测试覆盖 > 80%
- SKILL.md 触发规则被 LLM 遵守的概率 > 80%（通过实际调试场景验证）

### 性能基准
- `query_transcript()` 在 10 万条消息的 transcript 上 < 100ms（SQLite）/ < 2s（JSONL）
- `last_error_detail()` < 1ms（纯内存操作）
- `trace_value_origin()` < 10ms（SQLite 索引查询）
- 录制 LLM 调用的额外开销 < 5ms / call

---

## 关键文件汇总

| 类别 | 文件路径 |
|---|---|
| **异常层级** | `helen/interpreter/exceptions.py`（L89-L303） |
| **ErrorSnapshot** | `helen/runtime/observability.py`（L271-L353） |
| **TranscriptStore + Backend** | `helen/runtime/transcript_store.py`（L234-L1371） |
| **stdlib 注册模式** | `helen/stdlib/__init__.py`（L1396-L1630） |
| **fuzzy_match 可复用** | `helen/runtime/fuzzy_match.py`（L556-L621） |
| **HttpLLMRuntime 录制插入点** | `helen/runtime/http_llm.py`（L995, L1005-L1028） |
| **Channel 实现** | `helen/runtime/channel.py`（完整 220 行） |
| **Agent 调用路径** | `helen/interpreter/interpreter.py`（L1788 `_call_agent`） |
| **Prompt 构造** | `helen/interpreter/llm_mixin.py`（L435-L467, L1529, L1590-L1618） |
| **stdlib transcript 现有函数** | `helen/stdlib/transcript.py`（17 个函数） |
| **SessionManager** | `helen/runtime/session_manager.py`（完整 326 行） |
| **AgentContextManager** | `helen/interpreter/agent_context.py`（L254-L451） |
