# Helen 大型 Agent 工程基础设施路线图

**日期**：2026-07-30
**作者**：Claude（与用户协作讨论）
**版本**：Helen v1.30.4
**背景**：讨论 Helen 是否需要用 Rust 重写以支持大型 Agent 工程（代码复杂、长期运行、运行稳定、大量 spawn）

---

## 结论摘要

**现阶段全面重写是错误决策，但针对性的 Rust 重写某些层是有价值的。**

更重要的工程投入是 **6 大基础设施方向**（与语言无关）：

| 优先级 | 方向 | 理由 |
|---|---|---|
| **P0** | 1. Agent 生命周期管理 | 没有这个，大型工程根本跑不起来（hang、泄漏、孤儿） |
| **P0** | 5. 资源预算 | 没有预算控制，LLM 成本失控是秒级灾难 |
| **P1** | 2. 错误传播 | 没有因果链，调试跨 agent bug 是地狱 |
| **P1** | 3. 可观测性 | 没有 trace/metrics，生产环境是黑盒 |
| **P2** | 4. 确定性测试 | 影响开发效率，不影响生产运行 |
| **P2** | 6. 会话恢复 | v1.27 已有基础，增强即可 |

---

## 一、是否应该用 Rust 重写？

### Helen 的真实瓶颈

基于 knowledge graph 索引数据（13,666 节点，57,696 边）：

| 层 | 节点 | 调用密度 | 特点 |
|---|---|---|---|
| `core` (lexer/parser/ast) | 1,165 fan-in | 443 calls from execution | **纯 CPU**，可优化 |
| `semantic` | 309 calls to core | 一次性分析 | **编译期**，运行时无感 |
| `interpreter` | fan-in=220, fan-out=701 | 热点 `ASTNode.accept` (98) | **CPU + 内存** |
| `runtime` (LLM/工具/transcript) | fan-in=286, fan-out=196 | `TranscriptStore.append` (122) | **IO 密集** |
| `stdlib` (333 builtins) | — | — | 混合 |

**关键洞察**：大型 Agent 工程的延迟大头是 LLM 调用（1-30秒），Python 解释器循环的开销（ns 级）在整体延迟中占比 <0.001%。所以"性能"本身**不是**重写的首要理由。

### 大型 Agent 工程的真实痛点

| 特征 | 真实痛点 | Python 能力 |
|---|---|---|
| **代码复杂** | 模块边界、类型安全、IDE 支持 | 一般（动态类型是双刃剑） |
| **长期运行** | 内存泄漏、GC 暂停、句柄泄漏 | **较弱**（CPython refcount 有盲区） |
| **运行稳定** | 错误隔离、故障恢复、确定性 | **较弱**（GIL 下异常传播不干净） |
| **大量 spawn** | 千级 agent 并发、内存占用、调度 | **弱**（asyncio 在 CPU 混合负载下差） |

后三个才是 Python 真正吃力的地方，前两个可以通过工程手段缓解。

### 建议：分层重写，而非全面重写

```
┌─────────────────────────────────────────┐
│ Layer 3: CLI / REPL / LSP (保持 Python) │ ← 开发速度优先
├─────────────────────────────────────────┤
│ Layer 2: Runtime (考虑 Rust)            │ ← 长期运行关键路径
│  • TranscriptStore (SQLite/JSONL)       │
│  • Channel / Mailbox / Select           │
│  • HTTP LLM Runtime (流式解析)           │
│  • Session Manager + Lock               │
│  • Tool 调度器                          │
├─────────────────────────────────────────┤
│ Layer 1: Core (可选 Rust)               │ ← 看 profile 数据
│  • Lexer / Parser                       │
│  • Semantic Analyzer                    │
│  • Interpreter loop                     │
└─────────────────────────────────────────┘
```

#### 优先级 1：Runtime 层用 Rust（PyO3 绑定）

理由：
- **TranscriptStore** 是 I/O 密集 + 需要持久化 + 跨进程锁 → Rust + SQLite 天然契合
- **Channel/Mailbox** 在大量 spawn 下是性能关键 → tokio mpsc 比 Python asyncio.Queue 强一个量级
- **HTTP 流式解析** → Rust 的 `reqwest` + `tokio` 处理 SSE 更干净
- **Session Manager** 的跨进程锁、心跳、孤儿检测 → Rust 的确定性资源清理是杀手锏

PyO3 绑定成本不高，接口保持 Python 不变。

#### 优先级 2：Core 层看 profile

`Scanner.scan_all` (fan-in 135) 和 `Parser.parse` (fan-in 111) 是热点，但只在编译期跑。除非 Helen 有"热重载 agent 定义"的用法，否则不急。

#### 不推荐：全面 Rust 重写

理由：
1. **开发速度折损 10-50x** — Helen 的核心价值是 prompt-first DSL 的表达力，不是运行速度
2. **3308 个测试要重写** — 迁移风险极高
3. **AI 生态在 Python** — OpenAI SDK、LangChain、向量库全在 Python
4. **0 新功能 6-12 个月** — 在 AI Agent 这个快速演进的领域是致命的
5. **Python 已经证明能做大规模** — Dropbox 数亿行代码、Instagram 数十亿用户

### 比重写更重要的工程投入

大型 Agent 工程的真正难题，用 Rust 也解决不了，必须靠设计：

1. **Agent 生命周期管理** — 资源配额、超时、强制回收
2. **跨 Agent 错误传播** — 现在 `AggregateError` 不够，需要因果链
3. **可观测性** — v1.23 有调用树，但缺 trace 聚合、metrics 导出
4. **确定性测试** — 大量 spawn 下的并发 bug 难复现，需要 mock LLM + 时间控制
5. **资源预算** — token/memory/time per agent, per spawn tree
6. **会话恢复** — v1.27 的 spawn resume 是好的开始，但缺状态校验

---

## 二、Helen 现状分析（基于 Knowledge Graph）

### 异常层级

```
AnyError
├── LLMError
│   ├── TimeoutError
│   ├── ModelError
│   └── AgentError   ← 包装了 agent_name + agent_args + cause
├── HelenRuntimeError
│   ├── RuntimeError
│   ├── ToolError
│   ├── ConstAssignmentError
│   └── ScopeViolationError
├── AssertionError
├── AggregateError   ← await [list] 多失败聚合
├── CancelledError
├── PromptTooLongError
└── HelenError (compile-time, 单独层级)
```

关键文件：`helen/interpreter/exceptions.py`

### 关键类

| 类 | 文件 | 行数 | 作用 |
|---|---|---|---|
| `Channel` / `ChannelEndpoint` | `runtime/channel.py` | 51 / 148 | 双向邮箱 |
| `SessionManager` | `runtime/session_manager.py` | 294 | transcript 会话管理 |
| `TranscriptStore` | `runtime/transcript_store.py` | 588 | SSOT（消息真源） |
| `SessionMeta` | `runtime/transcript_store.py` | 104 | 会话元数据（含 parent_session_id） |
| `ExecutionTracer` | `runtime/observability.py` | 85 | 执行 trace 记录 |
| `ObservabilityManager` | `runtime/observability.py` | 53 | 中央观测管理 |
| `TraceEntry` | `runtime/observability.py` | 23 | 单条 trace 条目 |
| `ChannelActorManager` | `agent/webui/...` | 122 | WebUI 长驻 actor 管理 |
| `SpawnExprNode` | `core/ast.py` | 25 | spawn 语法节点（含 resume 子句） |

---

## 三、六大基础设施详细设计

### 1. Agent 生命周期管理

#### 现状

- `SessionManager`（294 行）管理 transcript 会话，但不管 agent 进程
- `ChannelActorManager`（122 行）是 WebUI 专属，管"长驻 actor"
- `Channel` / `ChannelEndpoint` 只管消息收发，不管对端是否还活着
- `release_session_lock()`（v1.30.2）只是补救措施，不是系统性方案

#### 缺什么

**a) 资源配额（Resource Quotas）**

```helen
// 设想的语法
@resource(max_tokens=100_000, max_memory_mb=512, timeout_sec=300)
agent Worker { ... }

// 运行时强制执行
let budget = token_budget(100_000)
spawn Worker("task") with budget
// 超过配额 → 抛 ResourceExhaustedError
```

现状：没有任何配额机制。一个失控 agent 可以无限消耗 token/内存。

**b) 超时（Timeout）**

- `TimeoutError` 存在（继承 `LLMError`），但只在 LLM 调用层
- 没有 agent 级超时：`spawn Worker(...)` 可能永远 hang
- 没有 spawn tree 级超时：父等子、子等孙，层层累积

```helen
// 缺失的能力
let ch = spawn Worker("task") 
let result = ch.receive(timeout=30)  // ✅ 已有
let result = ch.receive(deadline=now()+30)  // ❌ 没有绝对截止时间
await_all([ch1, ch2], timeout=60)  // ❌ 没有批量超时
```

**c) 强制回收（Forced Reclamation）**

- `Channel.cancel()` 可以中断流式，但不保证清理
- 没有 `SIGKILL` 等价物：如果 agent 卡在 C 扩展或系统调用，无法强制终止
- 没有孤儿检测：父进程挂了，子 agent 可能还在跑

#### 具体建议

**短期（Python 可实现）**：
1. `spawn` 增加 `timeout` 和 `budget` 参数
2. `ChannelEndpoint` 增加 `is_alive()` / `health_check()` 方法
3. 引入 `ResourceBudget` 类，在 `LLMRuntime` 层做 token 计数
4. 引入 `AgentRegistry` 单例，跟踪所有活跃 agent 的 thread handle

**中期**：
5. 实现 `supervisor` 模式：父 agent 可定义子 agent 故障策略（restart / abort / escalate）
6. 引入 `graceful_shutdown()` 全局 API，按依赖顺序关闭 spawn tree

---

### 2. 跨 Agent 错误传播

#### 现状

`AgentError` 已经做了基本包装（agent_name + cause），但：
- 只记录一层 cause，不记录完整因果链
- 跨 spawn tree 时，错误上下文丢失
- `AggregateError.errors` 是个列表，没有结构化关联

#### 缺什么

**a) 因果链（Causal Chain）**

```helen
// 现状：错误丢失祖先信息
agent A {
    let ch = spawn B()
    let r = ch.receive()  // B 抛 ToolError
    // 此时 A 看到 AgentError(cause=ToolError)，但 B 之前调的 LLM 失败信息丢了
}

// 应该：结构化因果链
// AgentError
//   agent: "A"
//   cause: AgentError
//            agent: "B"  
//            cause: ToolError(tool="web_fetch", url="...")
//              cause: TimeoutError(seconds=30)
//   spawn_path: ["main", "A", "B"]
//   invocation_id: "uuid-xyz"
```

**b) Spawn Tree 传播策略**

```helen
// 缺失：声明式错误传播策略
@error_propagation(
    on_child_failure = "escalate",   // or "ignore", "retry", "fallback"
    max_retry = 3,
    retry_delay = 1.0
)
agent Supervisor { ... }
```

**c) 分布式 trace ID**

- 当前 `invocation_id` 是 per-agent 的，不跨 agent 关联
- 没有 `trace_id` 贯穿整个 spawn tree
- 日志/错误/指标无法按"一次完整任务"聚合

#### 具体建议

1. **扩展 `AgentError`**：增加 `spawn_path: list[str]` 和 `trace_id: str` 字段
2. **引入 `CausalChain` 类**：错误抛出时自动沿 spawn 栈向上收集 cause
3. **引入 `trace_id`**：spawn 时继承父 trace_id（或创建新的），贯穿所有子 agent
4. **`AggregateError` 增强**：每个错误带来源 agent 标识，支持结构化查询
5. **新增 `ErrorPolicy` 装饰器**：声明式定义子 agent 失败时的处理策略

---

### 3. 可观测性

#### 现状

从 `observability.py`：
- `ExecutionTracer`（85 行）：记录 stmt/branch/call/return 事件
- `TraceEntry`（23 行）：timestamp + event_type + location + data
- `ObservabilityManager`（53 行）：中央管理

v1.23 的调用树（invocation tree）提供了跨 agent 的调用关系可视化。

#### 缺什么

**a) Trace 聚合**

现状：每个 agent 独立写自己的 trace，没有全局聚合。

```helen
// 缺失：跨 agent trace 聚合查询
let trace = get_trace(trace_id="abc-123")
// 返回完整的 spawn tree 调用图，带耗时、token 消耗、错误

// 现状只能：
:trace  // 当前 agent 的 trace
:stats  // 当前会话的统计
// 没有：
:trace --tree <trace_id>  // 整棵 spawn tree
```

**b) Metrics 导出**

现状：没有 metrics 概念。所有观测都是"日志式"的 trace entry。

缺失：
- 计数器：`llm_calls_total`, `tokens_used_total`, `spawn_count_total`
- 直方图：`llm_latency_seconds`, `tool_duration_seconds`
- 仪表：`active_agents`, `memory_usage_bytes`
- 导出：Prometheus / OpenTelemetry / StatsD

**c) 结构化日志**

现状：`log_error()` 是 stdlib 函数，但日志格式是字符串。

缺失：
- JSON 结构化日志（带 trace_id, span_id, agent_name）
- 日志级别过滤
- 日志 sink（stdout / file / OTLP）

#### 具体建议

1. **引入 `TraceContext`**：`trace_id` + `span_id` + `parent_span_id`（W3C Trace Context 标准）
2. **每个 agent 启动时创建 span**，LLM 调用/工具调用是子 span
3. **`get_trace(trace_id)` stdlib 函数**：返回完整 span tree
4. **`metrics()` stdlib 函数**：返回计数器/直方图/仪表快照
5. **OpenTelemetry 导出器**：可选，把 spans + metrics 推到 OTLP endpoint
6. **`:trace --tree` REPL 命令**：可视化 spawn tree

---

### 4. 确定性测试

#### 现状

Helen 已有：
- `MockLLMRuntime`（测试基础设施）
- `helen test <file.helen>` 内置测试框架
- 3308 个 pytest 测试

#### 问题

大量 spawn 下的并发 bug 难以复现：

```helen
// 这个测试可能偶尔通过偶尔失败
test "concurrent workers" {
    let chs = [spawn Worker(i) for i in range(10)]
    let results = [ch.receive() for ch in chs]
    assert_equal(len(results), 10)
    // 但如果 Worker 依赖 LLM，LLM 响应顺序不确定
    // 如果 Worker 之间通过 shared store 交互，race condition 难复现
}
```

#### 缺什么

**a) 时间控制**

```helen
// 缺失：可注入的时钟
@mock_clock(start=1700000000, tick=1.0)
test "timeout handling" {
    let ch = spawn Worker()
    // 人工推进时间，触发超时
    clock.advance(31)  // 跳过 30 秒
    assert_throws(TimeoutError, fn() => ch.receive())
}
```

**b) 确定性 LLM Mock**

现状 `MockLLMRuntime` 只能返回预设响应，但：
- 不能按顺序返回多个响应
- 不能模拟流式响应的分块时机
- 不能模拟 LLM 失败（超时/5xx）

```helen
// 缺失：脚本化 LLM 行为
@mock_llm(script=[
    {delay: 0.1, response: "step 1"},
    {delay: 0.2, response: "step 2"},
    {delay: 0.1, error: TimeoutError},  // 第三次调用失败
    {delay: 0.1, response: "step 3 after retry"},
])
test "retry logic" { ... }
```

**c) Race Condition 检测**

```helen
// 缺失：自动 race detection
@detect_races(iterations=1000, random_seed=42)
test "shared store concurrent access" {
    shared store Counter { let n = 0; fn inc() { n += 1 } }
    let chs = [spawn Worker() for _ in range(10)]
    // 自动以不同顺序调度，检测 race
}
```

#### 具体建议

1. **`MockClock` 类**：可注入的时间源，支持 `advance()` / `freeze()` / `set_speed()`
2. **`ScriptedLLMRuntime`**：按脚本返回响应，支持延迟/错误/流式分块
3. **`@deterministic` 装饰器**：固定随机种子 + 时钟 + LLM 脚本，确保测试可复现
4. **`RaceDetector`**：基于 `faulthandler` 或 `thread-sanitizer` 思想，检测 shared store 并发访问
5. **`ChaosAgent` 测试工具**：随机注入故障（LLM 失败、网络超时、进程崩溃），验证恢复逻辑

---

### 5. 资源预算

#### 现状

- `TranscriptStore` 记录消息，但不统计 token
- `LLMRuntime` 调用 API 但不累计消耗
- `working_memory` 有 `build_three_channel_context` 的 Channel 2 budget（从测试看到），但仅限 working memory

#### 缺什么

**a) Per-Agent Budget**

```helen
// 缺失：每个 agent 的资源预算
agent Worker {
    @budget(tokens=10_000, time_sec=60, memory_mb=100)
    fn main(input: str) {
        // 超过预算 → 自动终止，抛 BudgetExceededError
    }
}
```

**b) Per-Spawn-Tree Budget**

```helen
// 缺失：整棵 spawn tree 的总预算
let budget = spawn_budget(tokens=100_000, time_sec=300)
let ch1 = spawn Worker("task1") with budget
let ch2 = spawn Worker("task2") with budget
// ch1 和 ch2 共享 100k token 预算
// 任一 agent 消耗 token，从总预算扣除
```

**c) 实时消耗查询**

```helen
// 缺失：运行时查询预算消耗
let used = budget.used_tokens()     // 已用 token
let remain = budget.remaining()     // 剩余
let pct = budget.usage_percentage() // 使用率 %

// 可在 agent 内主动决策
if budget.remaining() < 1000 {
    return summarize_instead_of_full_response()
}
```

#### 具体建议

1. **`ResourceBudget` 类**：thread-safe 计数器，支持 token/time/memory 三种维度
2. **`LLMRuntime` 集成**：每次 API 调用后，从 response `usage` 字段提取 token，更新 budget
3. **`with budget` 语法**：spawn 时绑定 budget，子 agent 继承或共享
4. **`budget_*()` stdlib 函数**：`budget_used()`, `budget_remaining()`, `budget_check()`
5. **预算告警回调**：`budget.on_threshold(80%, fn() => notify())`
6. **REPL `:budget` 命令**：显示当前会话的预算消耗

---

### 6. 会话恢复

#### 现状

v1.27 的 `spawn resume("<session_id>")`：
- 跨进程锁防止并发损坏
- 恢复 transcript 到子 agent
- `expose_resumed_messages_to` 让 `llm act` 看到历史

`SessionMeta` 有 `parent_session_id`，追踪 spawn 关系。

#### 缺什么

**a) 状态校验（State Validation）**

```helen
// 现状：resume 直接恢复 transcript，不校验状态一致性
spawn Worker resume("session_xyz")
// 问题：
// - 如果 session_xyz 的 shared store 状态已丢失？
// - 如果 session_xyz 依赖的外部资源（文件、网络连接）已变化？
// - 如果 session_xyz 的 transcript 被手动修改过？
```

**b) 增量恢复 vs 全量恢复**

```helen
// 缺失：选择性恢复
spawn Worker resume("session_xyz", strategy="incremental")
// incremental: 只恢复最近的 N 条消息，快速启动
// full: 恢复完整 transcript（现状）
// checkpoint: 从最近的 checkpoint 恢复（需要 checkpoint 机制）
```

**c) Checkpoint 机制**

```helen
// 缺失：agent 可主动 checkpoint
agent LongRunning {
    fn main() {
        for i in range(1000) {
            process(item(i))
            if i % 100 == 0 {
                checkpoint(state={progress: i, partial_result: ...})
            }
        }
    }
}

// 崩溃后恢复
spawn LongRunning resume("session_xyz", from_checkpoint=true)
// 从 i=500 的 checkpoint 恢复，而不是从 0 开始
```

**d) 恢复后的一致性保证**

```helen
// 缺失：恢复后验证关键不变量
@resume_invariants([
    "shared_store.counter >= 0",
    "channel_buffer_size < 1000",
    "external_api_health() == 'ok'"
])
agent Worker { ... }

// resume 后自动检查不变量，失败则拒绝启动或触发告警
```

#### 具体建议

1. **`Checkpoint` 类**：序列化 agent 状态（shared store、变量、位置）到 transcript
2. **`checkpoint(state)` stdlib 函数**：agent 主动触发
3. **`resume(..., strategy=...)` 增强**：支持 `incremental` / `from_checkpoint` / `full`
4. **`validate_resume(session_id)` stdlib 函数**：恢复前校验 transcript 完整性、依赖资源可用性
5. **`@resume_invariants` 装饰器**：声明式定义恢复后的不变量
6. **`resume_status(session_id)` stdlib 函数**：返回恢复的详细状态（成功/部分成功/失败原因）

---

## 四、实施路线图

### Phase 1（3 个月）— P0：生命周期 + 预算

**里程碑**：Helen 可以稳定运行 100+ agent 的 spawn tree 持续 24 小时

- [ ] `ResourceBudget` 类（thread-safe，支持 token/time/memory）
- [ ] `LLMRuntime` 集成 budget 扣减（从 API response `usage` 提取 token）
- [ ] `spawn` 增加 `timeout` 和 `budget` 参数
- [ ] `ChannelEndpoint.is_alive()` / `health_check()`
- [ ] `AgentRegistry` 单例（跟踪所有活跃 agent 的 thread handle）
- [ ] 孤儿 agent 检测与清理（基于 AgentRegistry + heartbeat）
- [ ] REPL `:budget` 命令
- [ ] stdlib 函数：`budget_used()`, `budget_remaining()`, `budget_check()`

### Phase 2（3 个月）— P1：错误传播 + 可观测性

**里程碑**：任意 spawn tree 故障可在 5 分钟内定位到根因

- [ ] `AgentError` 增加 `spawn_path` 和 `trace_id` 字段
- [ ] `TraceContext`（W3C 标准）：`trace_id` + `span_id` + `parent_span_id`
- [ ] 每个 agent 启动时创建 span，LLM/工具调用是子 span
- [ ] `get_trace(trace_id)` stdlib 函数
- [ ] `metrics()` stdlib 函数（计数器/直方图/仪表）
- [ ] `CausalChain` 类（自动沿 spawn 栈收集 cause）
- [ ] `ErrorPolicy` 装饰器（声明式故障策略）
- [ ] OpenTelemetry 导出器（可选）
- [ ] REPL `:trace --tree <trace_id>` 命令

### Phase 3（2 个月）— P2：确定性测试 + 会话恢复

**里程碑**：并发 bug 可在 CI 中稳定复现，崩溃后可从 checkpoint 恢复

- [ ] `MockClock` 类（可注入时间源）
- [ ] `ScriptedLLMRuntime`（脚本化 LLM 行为）
- [ ] `@deterministic` 装饰器（固定随机种子 + 时钟 + LLM 脚本）
- [ ] `RaceDetector`（shared store 并发访问检测）
- [ ] `ChaosAgent` 测试工具（随机故障注入）
- [ ] `Checkpoint` 类 + `checkpoint(state)` stdlib
- [ ] `resume(..., strategy=...)` 增强（incremental / from_checkpoint / full）
- [ ] `validate_resume(session_id)` stdlib
- [ ] `@resume_invariants` 装饰器

---

## 五、关键设计原则

1. **显式优于隐式** — 资源预算、错误策略、恢复不变量都要显式声明
2. **可观测优先于可配置** — 先看到问题，再解决问题
3. **渐进增强，不破坏兼容** — 所有新功能都是 opt-in，旧代码无需改动
4. **Python 优先，性能关键路径才用 Rust** — 80% 的代码保持 Python
5. **测试即文档** — 每个新特性必须有并发场景的测试覆盖

---

## 六、参考资源

- Helen v1.27 spawn resume：`helen/interpreter/import_mixin.py`, `helen/runtime/session_manager.py`
- Helen v1.23 调用树：`helen/runtime/observability.py`
- Helen v1.30.2 锁释放：`helen/stdlib/transcript.py`
- Knowledge Graph 索引：`.codebase-memory/graph.db.zst`（13,666 nodes, 57,696 edges）
- W3C Trace Context 标准：https://www.w3.org/TR/trace-context/
- OpenTelemetry：https://opentelemetry.io/
- PyO3（Rust-Python 绑定）：https://pyo3.rs/

---

**总结**：Helen 的问题是"长期运行 + 大量 spawn"下的资源管理问题，不是"解释器太慢"的问题。用 Rust 重写 runtime 层（PyO3 绑定），同时投入 6 大工程基础设施，是 ROI 最高的路径。全面重写是把手段当成了目的。
