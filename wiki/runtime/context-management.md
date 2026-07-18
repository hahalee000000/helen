# 上下文管理架构 (Context Management Architecture)

> **版本**: v1.23 | **最后更新**: 2026-07-18
> 统一说明 Helen 的上下文管理系统，替换原 `agent_context.md`、`graduated_compression.md`、`cache_aware_compression.md`、`working_memory.md` 中的分散描述。

---

## 零、设计哲学与生命周期

> 在深入实现细节之前，先厘清上下文管理的本质问题：**Context 应该存在多久？**

### 0.1 核心区分：Context vs Transcript

Helen 有两套看似重叠实则职责分明的系统：

| | **Context（上下文）** | **Transcript（转录）** |
|---|---|---|
| 本质 | LLM **当前看到**的信息 | LLM **曾经说过**的完整记录 |
| 目的 | 支撑推理 | 审计、恢复、追溯 |
| 可变性 | 压缩、裁剪、替换 | 只追加，不可变（[[runtime/transcript-store|TranscriptStore SSOT]]） |
| 生命周期 | 会话级，可销毁 | 持久化（SQLite/JSONL） |
| 类比 | 工作台——当前正在用的东西 | 档案柜——所有历史都在 |

**设计原则**：Context 管理追求**在有限窗口内做到极致**，Transcript 追求**完整不丢失**。两者的分离让系统既高效（context 激进压缩不心疼）又安全（transcript 完整可审计）。

> Context 是"此刻 LLM 该知道什么"，Transcript 是"LLM 曾经知道什么"。

### 0.2 四层生命周期架构

Context 的持续时间是分层的，每一层服务于不同的推理粒度：

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Transcript（审计层）                              │
│  生命周期：永久                                             │
│  职责：不参与 LLM 推理，但可通过 replay_transcript() 恢复   │
│  实现：[[runtime/transcript-store|TranscriptStore SSOT]]     │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Pinned Context（持久关注层）                      │
│  生命周期：跨 llm act 调用，Agent 会话内                    │
│  职责：用户显式 pin 的关键信息，免疫所有 5 层压缩           │
│  实现：pin_message(uuid)、working_memory_set()              │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Active Context（活跃层）⭐ 核心                   │
│  生命周期：Agent 会话（main {} 执行期）                     │
│  职责：多轮 llm act 之间的对话历史 + 工具调用结果           │
│  实现：AgentContextManager + 渐进压缩 + 三通道              │
├─────────────────────────────────────────────────────────────┤
│  Layer 0: Working Memory（即时层）                          │
│  生命周期：单次 llm act 调用内部                            │
│  职责：当前任务焦点、活跃文件、最近决策                     │
│  实现：WorkingMemory 自动更新                               │
└─────────────────────────────────────────────────────────────┘
```

**关键设计决策**：

1. **Layer 0 是临时的注意力引导**——单次 `llm act` 返回后即可销毁，不需要持久化。
2. **Layer 1 的边界 = 单次 `main {}` 的执行期**（v1.22 实现）——每次 agent `main {}` 调用都是 fresh context，main {} 退出后丢弃。同一 agent 多次调用之间也不共享。详见 §0.5。
3. **Layer 2 是用户主动声明"这些信息重要"的机制**——和 Layer 1 共享同一个 token 窗口，但享有压缩豁免权。
4. **Layer 3 不是 Context**——它是 SSOT 审计记录，通过 `replay_transcript()` / `export_transcript()` 按需恢复。

### 0.3 Context 应该持久化多久？

| 问题 | 答案 | 理由 |
|---|---|---|
| 跨 `llm act` 调用？ | ✅ 是 | 这是 Active Context 的核心价值——多轮工具调用需要连续性 |
| 跨 agent？ | ❌ 不隐式共享 | 通过 [[interpreter/spawn|Channel / SharedStore]] 显式传递，避免作用域污染 |
| 跨 Helen 进程？ | ❌ 不 | 进程重启通常意味着用户意图变了；通过 Transcript 恢复即可 |
| 跨用户会话（天/周级）？ | ❌ 不是 context 的职责 | 是 [[runtime/skills|Skills]] / 外部记忆 / 文件的职责 |

**跨进程为什么不该靠 context 持久化**：

1. 跨进程恢复需要反序列化整个上下文状态（环境、压缩标记、pin 状态、working memory），复杂度很高
2. 进程重启时用户意图通常已变，旧上下文的价值下降
3. 如果真需要延续，应该通过 **显式导出/导入** 或**文件持久化**完成（见下文"跨会话恢复的实际路径"）
4. 把"持久化"的责任从 context 剥离，让 context 可以激进压缩而不必顾虑信息丢失

**跨会话的"记忆"应该靠什么**：

- **`restore_context(session_id)`** ⭐ (v1.21+)：直接从旧 transcript session 恢复成 active context。内部读取 TranscriptStore、保留所有字段（`tool_calls`/`tool_call_id`/`compressed`/`pinned`/`uuid`）、调用 `import_context()` 填充当前历史。**一步到位，无需手写格式适配。**
- **`search_transcript(query)`** ⭐ (v1.22+)：按**内容**搜索持久化 transcript。支持 `scope="all"` 跨所有 session 搜索、`regex=true` 正则匹配、`role="user"` 角色过滤。一般场景下用户记不住 session_id，但记得内容——用 `search_transcript` 找到匹配的 session_id，再用 `restore_context` 恢复。详见 [[runtime/transcript-store|TranscriptStore SSOT §search_transcript]]。
- **`export_context()` / `import_context(data)`**：会话结束前导出 context 快照（含 messages + working_memory + config）到文件，下次启动时读入并导入。适合需要同时保存 working_memory 和 config 的场景
- **`replay_transcript(session_id)`**：读取旧 transcript 的消息列表（审计/查看用），**不会**自动注入到当前 context，且返回格式与 `import_context()` 不兼容
- **文件持久化**：用户把关键信息写入文件，下次启动时读入
- **Skills**：把模式、偏好、项目约定沉淀为 skill，不依赖上下文

**`restore_context` vs `resume_session` 的区别**：

| | `restore_context(session_id)` | `resume_session(session_id)` |
|---|---|---|
| 恢复目标 | **Active Context**（LLM 看到的对话历史） | **Active Context** + 保持审计追踪连续性 |
| 操作方式 | 清空当前历史，导入旧会话消息 | 导入旧会话消息到当前 store |
| LLM 能看到恢复的消息？ | ✅ 能 | ✅ 能（v1.23 修复后） |
| 调用树过滤 | 支持（按 agent/invocation 过滤） | 不支持（导入全部消息） |
| session_id 变化 | 保持当前 session_id | 保持当前 session_id（v1.23 修复后） |
| 适用场景 | 接续旧会话的特定 agent/invocation | 恢复整个旧会话的所有消息 |

**v1.23 变更**：`resume_session` 从"替换 transcript store 引用"改为"导入消息到当前 store"。这意味着：
- 恢复的消息现在对 LLM 可见（标记当前 invocation_id）
- 当前 session_id 保持不变（审计追踪连续）
- 如果需要按 agent/invocation 精准恢复，使用 `restore_context`

### 0.4 `context {}` 配置的生命周期语义

Agent 声明中的 `context { ... }` 配置绑定了 Active Context 的行为策略：

```helen
agent MyAgent {
    context {
        compression "graduated"       // 压缩策略
        cache-aware true              // 缓存感知
        working-memory true           // 工作记忆
        working-memory-tokens 5000    // 工作记忆 token 预算
    }
    main { ... }
}
```

**语义**：这些配置控制 Agent 会话期间 Active Context 如何管理自己，**不控制跨会话持久化**。每次 `helen` 进程启动，Agent 都从 fresh context 开始。如果需要延续旧会话，有两种方式：

```helen
// 方式 1（推荐）：从旧 transcript session 直接恢复 active context
let sessions = list_sessions()
// ... 选择要恢复的 session_id ...
let r = restore_context("session_1783492628_d9d9c0aa")
// r: {status: "ok", restored_messages: 42, boundary_markers: 3, note: "..."}

// 方式 2：导出/导入完整快照（保留 working_memory + config）
// 会话结束前保存
let snapshot = export_context()
write_file("context_snapshot.json", to_json(snapshot.context))
// 新会话启动时恢复
let saved = parse_json(read_file("context_snapshot.json"))
import_context(saved)
```

**方式 1 vs 方式 2**：
- `restore_context(session_id)`：恢复 **messages**，字段完整（含 tool_calls、pinned、compressed、uuid）。**不**恢复 working_memory 和 config（因为 transcript 不存这些）。
- `export_context() / import_context()`：恢复 messages + working_memory + config 全部，但需要先写文件再读回。

**未来考虑**：
- 如果 Helen 支持 agent 复用/池化，需要明确——同一 agent 多次执行，context 是否复用？设计倾向：**不复用**，每次执行都是 fresh context。跨执行的延续通过 `restore_context()` 或参数传入。

### 0.5 v1.22 实现：Per-Main Fresh Context + Invocation Tree

> **状态**：已实现（v1.22）。详见 `reports/v1.22-invocation-tree-proposal.md`。

v1.22 把上述设计原则落地为两个核心机制：

**1. Per-Main Fresh Context（每次 main {} 都是 fresh）**

每次进入 agent `main {}`（或顶层 main）时，interpreter 创建一个新的 `invocation_id`。`_history` 属性按 `invocation_id` 过滤--LLM 只看到当前 invocation 的消息。main {} 退出后，invocation 结束，下一次调用又是 fresh。

实现位置：`helen/interpreter/interpreter.py`
- `_enter_invocation(agent_name)` / `_exit_invocation()`：管理 invocation 栈
- `_call_agent`：进入 agent 时 `_enter_invocation`，finally 块 `_exit_invocation`
- `visit_main_block`：顶层 main 也创建 invocation
- `_history` property：按 `_current_invocation_id` 过滤

**2. Invocation Tree（调用树）**

每条消息带三个新字段（`helen/runtime/history.py` 的 `Message` dataclass）：
- `agent_name`：产生该消息的 agent 名（顶层为 `None`）
- `invocation_id`：本次 main {} 执行的唯一 ID
- `parent_invocation_id`：父调用的 invocation_id（构建调用树）

transcript 仍然记录**所有**消息（SSOT 审计完整），但 active context 按 invocation 过滤。

**查询 API**（`helen/stdlib/transcript.py`）：
- `list_invocations(session_id?, agent?, limit?, offset?)`：列出 invocation
- `get_invocation(invocation_id, session_id?)`：查单个 invocation 元数据
- `get_invocation_tree(session_id?)`：获取完整调用树（嵌套结构）
- `invocation_path(invocation_id, session_id?)`：调用路径字符串（如 `top -> A -> C`）

**扩展的过滤参数**：
- `replay_transcript(..., agent?, invocation_id?, last_only?, include_subtree?)`
- `restore_context(session_id, invocation_id?, agent?, last_only?, include_subtree?)`

**隔离边界**：

| 场景 | 是否共享 active context |
|---|---|
| 同一 agent 的 `main {}` 内部多次 `llm act` | 累积（工具循环必需） |
| 同一 agent 的两次 `main {}` 调用 | 隔离（每次 fresh） |
| 不同 agent 的 `main {}` | 隔离 |
| 嵌套调用：Outer 调 Inner 后 | Outer 看不到 Inner 的消息 |
| `spawn A()` 并发 | 隔离 |
| 跨 `helen` 进程 | 隔离 |

**中文别名**：`列出调用`、`获取调用`、`获取调用树`、`调用路径`。

### 0.6 v1.23 修复：Invocation 隔离的实现修正

> **状态**：已修复（v1.23，2026-07-18）。

v1.22 实现了 per-main fresh context 的设计，但 v1.23 发现并修复了关键实现缺陷：

**问题 1：`_prepare_history_for_llm()` 绕过 invocation 过滤**

v1.22 中，`_prepare_history_for_llm()` 直接读取 `transcript_store.read_view()`，绕过了 `_history` property 的 invocation_id 过滤。这导致 agent 之间能看到彼此的上下文，违反了 per-main fresh context 的设计原则。

**修复**：`_prepare_history_for_llm()` 统一走 `self._history`（包含 invocation_id 过滤）。

**问题 2：`_import_context()` 双存储不一致**

`_import_context()` 同时写入 `_interpreter_history` 和 `TranscriptStore`，导致数据不一致。且导入的消息没有标记 `invocation_id`，无法正确隔离。

**修复**：改为单写策略——TranscriptStore 启用时只写 TranscriptStore，否则只写 `_interpreter_history`。导入的消息标记当前 `invocation_id`。

**问题 3：`resume_session()` 语义错误**

`resume_session()` 直接替换 TranscriptStore 引用，导致恢复的消息不受 invocation 隔离控制。

**修复**：改为导入消息到当前 store 并标记 `invocation_id`，保持审计追踪的连续性。

**验证测试**：

```helen
// v1.23 之前的 bug（已修复）
agent AgentA { main { return llm act "我是 Alice" } }
agent AgentB { main { return llm act "我叫什么？" } }

let a = AgentA()
let b = AgentB()
// v1.22（bug）：AgentB 能回答 "Alice" ❌
// v1.23（修复）：AgentB 看不到 AgentA 的上下文 ✅
```

**相关文件**：
- `helen/interpreter/llm_mixin.py`：`_prepare_history_for_llm()` 修复
- `helen/stdlib/context.py`：`_import_context()` 单写策略
- `helen/stdlib/transcript.py`：`resume_session()` 导入语义
- `tests/interpreter/test_v123_invocation_isolation.py`：新增隔离验证测试

---

## 一、总览

Helen 的上下文管理由四个子系统协作组成，目标是在有限的上下文窗口中最大化 LLM 获得的信息质量：

```
┌──────────────────────────────────────────────────────────────────┐
│                    AgentContextManager (统一入口)                  │
│                  helen/interpreter/agent_context.py                │
│                                                                   │
│   prepare_context(system_prompt, history, max_tokens)             │
│       │                                                           │
│       ├─► _compress_history()        ← 统一压缩入口               │
│       │     ├─ strategy="none"        → 跳过                      │
│       │     ├─ strategy="traditional" → HistoryManager 单层压缩   │
│       │     └─ strategy="graduated"   → 5 层渐进管线              │
│       │     └─ if cache_aware: _apply_cache_aware_wrap()          │
│       │          保留前 30% 消息不变，对可压缩区重新运行基础策略    │
│       │                                                           │
│       └─► build_three_channel_context()  ← 三通道构建             │
│             ├─ Channel 1 (15%): 系统指令                          │
│             ├─ Channel 2 (50%): 工作记忆 (受预算截断)             │
│             └─ Channel 3 (35%): 对话历史                          │
└──────────────────────────────────────────────────────────────────┘
```

### 子系统对照

| 子系统 | 文件 | 职责 |
|--------|------|------|
| 工作记忆 | `runtime/working_memory.py` | 跟踪当前任务状态（活跃文件、决策、TODO、错误） |
| 渐进压缩 | `runtime/graduated_compression.py` | 5 层渐进式压缩管线（零成本优先） |
| 缓存感知 | 集成在 `agent_context.py` 中 | 保留稳定前缀，提高 prompt cache 命中率 |
| 历史管理 | `runtime/history.py` | Message 数据结构、token 估算、传统压缩 |

---

## 二、AgentContextManager — 统一入口

### 2.1 类定义

```python
class AgentContextManager:
    def __init__(
        self,
        working_memory_tokens: int = 5000,
        compression_strategy: str = "graduated",  # "none" | "graduated" | "traditional"
        working_memory_enabled: bool = True,
        cache_aware_enabled: bool = True,
        *,
        compression_enabled: bool | None = None,  # 向后兼容 shim
    ):
```

**`compression_strategy` 三个值的含义**：

| 策略 | 路径 | 特点 |
|------|------|------|
| `"none"` | 跳过压缩 | 适合短对话 |
| `"graduated"` | `graduated_compress()` — 5 层管线 | 最廉价动作优先，零成本层不调用 LLM |
| `"traditional"` | `HistoryManager.enforce_limit()` | 旧版单层 summarize/truncate，简单可预测 |

**`cache_aware_enabled`**：包裹（而非替代）基础策略。启用后保留前 30% 消息作为缓存稳定区，仅对后缀运行基础压缩。可与 `graduated` 或 `traditional` 任意组合。

**向后兼容**：`compression_enabled=True/False` 仍可使用，通过 property 映射到 `"graduated"` / `"none"`。

### 2.2 核心调用流程

```
prepare_context()
    │
    ├─► _compress_history(history, max_tokens)
    │     │
    │     │  # Step 1: 选择基础压缩
    │     ├─ strategy == "none" or len(history) <= 10:
    │     │     return history  (跳过)
    │     │
    │     ├─ strategy == "traditional":
    │     │     return HistoryManager(context_window=max_tokens).enforce_limit(history)
    │     │
    │     └─ strategy == "graduated":
    │           return graduated_compress(history, usage_ratio, max_tokens)
    │
    │     # Step 2: 缓存感知包裹 (if cache_aware_enabled)
    │     └─ _apply_cache_aware_wrap(compressed, original_history, max_tokens)
    │           cache_zone = original_history[:N]       # 前 30%，原样保留
    │           suffix     = original_history[N:]        # 后缀
    │           return cache_zone + base_compress(suffix, adjusted_budget)
    │
    └─► build_three_channel_context(system_prompt, working_memory, compressed)
          ├─ Channel 1: system prompt (截断到 15% 预算)
          ├─ Channel 2: working_memory.to_context(budget_chars=50%*max_tokens)
          └─ Channel 3: 历史消息 (从新到旧填充 35% 预算)
```

### 2.3 Interpreter 集成

```python
# interpreter.py — 初始化
self._agent_context = AgentContextManager(
    working_memory_tokens=5000,
    compression_strategy="graduated",
    working_memory_enabled=True,
    cache_aware_enabled=True,
)

# llm_mixin.py — 每次 llm act 前应用 agent 的 context {} 配置
self._agent_context.compression_strategy = ctx_config.compression
self._agent_context.working_memory_enabled = ctx_config.working_memory
self._agent_context.cache_aware_enabled = ctx_config.cache_aware
```

### 2.4 Agent 声明配置

```helen
agent SmartAssistant {
    context {
        compression "graduated"       // "none" | "graduated" | "traditional"
        cache-aware true              // 缓存感知包裹
        working-memory true           // 工作记忆
        working-memory-tokens 5000    // 工作记忆词元预算
    }
    main { ... }
}

// 中文关键字
agent 智能助手 {
    上下文 {
        压缩 "graduated"
        缓存感知 true
        工作记忆 true
        工作记忆词元 5000
    }
    主逻辑 { ... }
}
```

---

## 三、工作记忆 (Working Memory)

### 3.1 数据结构

```python
@dataclass
class WorkingMemory:
    task_description: str = ""         # 当前任务描述（永不淘汰，最高优先级）
    active_files: list[str]            # 活跃文件（受 token 预算淘汰）
    recent_decisions: list[str]        # 最近决策（受 token 预算淘汰）
    pending_todos: list[str]           # 待办事项（受 token 预算淘汰）
    error_history: list[dict]          # 错误记录（受 token 预算淘汰）
    max_tokens: int = 5000             # token 预算
```

**Token 级淘汰（v1.15+）**：`_add_active_file`、`_add_decision`、`_add_todo`、`_add_error` 每次添加后检查总 token 数。超出 `max_tokens` 时，按优先级从低到高淘汰最旧条目：

```
淘汰顺序（最先淘汰 → 最后淘汰）:
Pending TODOs → Recent Decisions → Active Files → Error History
（task_description 永不淘汰）
```

**与旧版差异**：旧版使用硬编码列表长度上限（10/10/20/5），新版改为 token 预算驱动。条目大小不均时更精确，大条目（长路径、长错误）更快触发淘汰。

### 3.2 自动更新

通过 `AgentContextManager` 在两个时机自动更新：

- **`update_from_message(content, role)`**：从消息内容正则提取文件引用、TODO、决策
- **`update_from_tool_call(tool_name, tool_args, tool_result)`**：从工具调用结构化跟踪

| 工具 | 效果 |
|------|------|
| `read_file` | 添加到 `active_files` |
| `write_file` / `patch_file` | 添加到 `active_files` + 记录决策 |
| `shell_exec` (失败) | 添加到 `error_history` |
| `glob_files` / `grep_files` | 记录搜索决策 |

### 3.3 格式化输出与预算截断

`to_context(budget_chars=None)` 将工作记忆格式化为 Markdown 字符串：

```
## Current Task
修复认证 bug

## Recent Errors
- Command: pytest
  Error: 3 failed

## Active Files
- src/auth.py
- tests/test_auth.py
```

**当提供 `budget_chars` 时**，按优先级从低到高渐进丢弃分区：

```
Pending TODOs (最先丢弃)
    ↓
Recent Decisions
    ↓
Active Files
    ↓
Recent Errors
    ↓
Current Task (最后丢弃，必要时截断正文到行边界)
```

### 3.4 已知限制

`max_tokens` 字段当前仅用于 `build_three_channel_context` 中的预算计算。`WorkingMemory` 本身不执行 token 级别的淘汰——只依赖列表长度上限（10/10/20/5）。

---

## 四、渐进压缩管线 (Graduated Compression)

### 4.1 五层管线

位于 `helen/runtime/graduated_compression.py`，设计原则："最廉价动作优先"——每层只在更便宜的层不够用时才触发。

| 层级 | 阈值 | 策略 | 成本 | 机制 |
|------|------|------|------|------|
| Layer 1 | 60% | Budget Reduction | 零 | 替换 >4000 字符的工具结果为引用指针 |
| Layer 2 | 70% | Snip | 零 | 丢弃过时轮次，保留最近 8 轮 |
| Layer 3 | 80% | Microcompact | 零 | 清除旧工具结果内容，保留 `tool_use` 决策 ⭐ |
| Layer 4 | 90% | Context Collapse | 零 | 归档旧轮次，**投射时间线视图**（分段摘要，保留时间结构） |
| Layer 5 | 95% | Auto-Compact | **零或高** | 优先调用 `LLMSummarizer` 进行语义摘要；LLM 不可用时回退到零成本结构摘要 |

**Pinned 消息免疫压缩**（v1.19）：被 `pin_message(uuid)` 标记的消息在所有 5 层中都被保留：Layer 1 不替换其内容、Layer 2 不丢弃、Layer 3 不清除、Layer 4 不归档、Layer 5 不摘要。用于保护关键上下文（系统提示、关键决策、few-shot 示例等）。`Message.pinned: bool` 字段加入 `history.py`，`TranscriptStore` 持久化时一并保存。

**Layer 4 改进（时间线保留）**：受 RCC (Recurrent Context Compression) 和 CogCanvas 启发，Context Collapse 现在将旧消息分段（每 10 条一块），每段提取文件引用、工具使用、用户意图，生成时间线视图，保留任务进展的时序结构。

**Layer 5 改进（LLM 语义摘要）**：当 `llm_client` 参数提供时，`_auto_compact` 调用 `LLMSummarizer` 生成高质量语义摘要，保留任务目标、关键决策、文件变更等。LLM 不可用时回退到零成本结构摘要（提取文件路径、工具计数、用户意图等）。

### 4.2 API

```python
def graduated_compress(
    history: list[Message],
    usage_ratio: float,
    max_tokens: int = 131072,
    llm_client: Callable | None = None,  # 新增：Layer 5 LLM 客户端
) -> tuple[list[Message], str]:
    """
    Args:
        llm_client: 可选 LLM 客户端，用于 Layer 5 语义摘要。
                    签名: llm_client(messages) -> str
                    为 None 时 Layer 5 回退到结构摘要。

    Returns:
        (compressed_history, layer_used)
        layer_used: "none" | "budget_reduction" | "snip" |
                    "microcompact" | "context_collapse" | "auto_compact"
    """
```

### 4.3 Microcompact 核心创新

区分"行动"（`tool_use` blocks）和"数据"（`tool_result` content）：
- ✅ 保留 `tool_use` blocks — "LLM 决定做什么"
- ❌ 清除旧 `tool_result` content — "工具返回了什么"

效果：用 20% 的 token 保留 80% 的决策上下文。

### 4.4 Context Collapse 时间线视图

**设计思想**：受 CogCanvas 和 RCC 启发，保留对话的时序结构，避免传统摘要丢失"何时发生"的信息。

**算法**：
1. 将旧消息分段（每 10 条一块）
2. 每段提取：
   - 时间标记（消息索引范围）
   - 文件引用（正则提取路径）
   - 工具使用（统计 tool_calls）
   - 用户意图（首行截取）
3. 生成时间线摘要 + 全局统计

**示例输出**：
```
[Context Collapse: 30 turns archived as timeline]
  [0-10] Files: main.py, utils.py | Tools: read_file(3), write_file(1) | Tasks: Fix auth bug
  [10-20] Files: auth.py, test_auth.py | Tools: shell_exec(2) | Tasks: Run tests
  [20-30] Files: config.yaml | Tools: patch_file(1)
[Global] Turns: 15u/15a | Tool calls: 12 | Errors: 2
[Preserved: last 20 turns for continuity]
```

### 4.5 Auto-Compact LLM 语义摘要

**启用方式**：在 `AgentContextManager` 初始化时传入 `llm_client`：

```python
agent_context = AgentContextManager(
    compression_strategy="graduated",
    llm_client=my_llm_client,  # 签名: (messages) -> str
)
```

**LLM 摘要格式**（由 `LLMSummarizer` 生成）：
```
## Task Objective
[用户目标]

## Key Decisions
- [决策 1 及理由]

## File Changes
- path/to/file.py: [变更内容]

## Completed
- [已完成项]

## Pending
- [ ] [待办项]
```

**回退机制**：LLM 调用失败时自动回退到结构摘要，确保压缩流程不中断。

---

## 五、缓存感知压缩 (Cache-Aware Compression)

### 5.1 设计动机

大多数 LLM API 支持 prompt cache：对话前缀被缓存，重复使用时成本降低 50-90%。**修改前缀会导致缓存失效**。

传统的渐进压缩（如 Snip 丢弃早期消息、Context Collapse 在开头插入摘要）会无意中破坏缓存。

### 5.2 当前实现：包裹模式

缓存感知作为**包裹层**而非独立策略：

```
原始历史: [msg1, msg2, ..., msg50]
                ↓
┌─ cache zone (前 30%) ─┐  ┌─ compressible zone (后 70%) ─┐
│ msg1..msg15 (原样保留) │  │ msg16..msg50 (运行基础压缩)   │
└────────────────────────┘  └──────────────────────────────┘
                ↓
结果: [msg1..msg15 (不变)] + [compressed msg16..msg50]
```

**核心保证**：前缀不变 → prompt cache 命中。

### 5.3 与基础策略的组合

| 组合 | 行为 |
|------|------|
| `graduated` + `cache_aware` | 5 层管线仅应用于后缀 |
| `traditional` + `cache_aware` | 单层压缩仅应用于后缀 |
| `none` + `cache_aware` | 无意义，跳过 |

### 5.4 常量

```python
DEFAULT_CACHE_ZONE_RATIO = 0.30     # 前 30% 为缓存区
MIN_CACHE_ZONE_MESSAGES = 5         # 最少 5 条消息
BATCH_COMPRESSION_THRESHOLD = 0.75  # 使用率 ≥75% 才触发
```

---

## 六、三通道上下文 (Three-Channel Context)

### 6.1 预算分配

`build_three_channel_context()` 将上下文分为三个通道：

| 通道 | 预算 | 内容 | 截断方式 |
|------|------|------|----------|
| Channel 1 | 15% × max_tokens | 系统提示 | 字符级截断 |
| Channel 2 | min(50% × max_tokens, working_memory.max_tokens) | 工作记忆 | 分区优先级丢弃 |
| Channel 3 | 35% × max_tokens | 对话历史 | 从新到旧填充 |

### 6.2 Channel 2 预算截断

工作记忆通过 `to_context(budget_chars=...)` 执行预算截断。当内容超出预算时，按优先级渐进丢弃分区（详见 §3.3）。

---

## 七、传统压缩 (Traditional Compression)

### 7.1 HistoryManager

位于 `helen/runtime/history.py`，是 Helen 早期的压缩实现。当 `compression_strategy="traditional"` 时使用。

```python
class HistoryManager:
    compression_mode: str  # "summarize" | "truncate" | "none"

    def enforce_limit(self, history, budget_ratio=0.8) -> list[Message]:
        """三层压缩：最近消息保留 → 中间消息压缩 → 最老消息丢弃"""
```

### 7.2 与渐进压缩的区别

| 维度 | 传统压缩 | 渐进压缩 |
|------|---------|---------|
| 层级 | 单层 | 5 层 |
| 触发 | 超过预算后一次性压缩 | 渐进式（60%→70%→80%→90%→95%）|
| 内容选择 | 无差别对待 | 区分行动和数据 |
| LLM 调用 | 否 | 否（所有层零成本）|
| 适用场景 | 简单短对话 | 长时间运行的 Agent |

---

## 八、stdlib 函数

### 8.1 `clear_context()`

```helen
let result = clear_context()
// 返回: {status: "ok", cleared_messages: 15, cleared_tokens: 8000}
```

清除对话历史。

**已知限制**：当前只清除 `_interpreter_history`，不清除 `AgentContextManager.working_memory`。工作记忆中的活跃文件、决策、TODO、错误会在清除后残留。

### 8.2 `compress_context(strategy)`

```helen
let result = compress_context("auto")      // 按 HistoryManager.compression_mode
let result = compress_context("summarize")  // 拼接旧消息为摘要
let result = compress_context("truncate")   // 丢弃旧消息
let result = compress_context("none")       // 无操作
// 返回: {status, original_messages, compressed_messages, original_tokens, compressed_tokens, strategy}
```

**已知限制**：当前实现中 `enforce_limit()` / `_summarize_compress()` / `_truncate_compress()` 的返回值被丢弃，历史实际未被修改（bug）。

### 8.3 `compress_context(target, keep_recent)`

```helen
let result = compress_context(target="tool_results", keep_recent=5)
// 清除旧工具结果，保留 tool_use 决策
let result = compress_context(target="stale_turns", keep_recent=8)
// 丢弃过时轮次
```

### 8.4 `clear_context()` / `compress_context()` 中文别名

```helen
清除上下文()     // = clear_context()
压缩上下文()     // = compress_context()
```

### 8.5 v1.19 新增：上下文检查与细粒度操作

v1.19 之前，上下文管理 API 只有"批量清空"和"批量压缩"两种粗粒度动作，Agent 既**看不见**当前上下文状态、也**动不了**单条消息。v1.19 补齐了**6 个维度**的 API。

#### 8.5.1 检查类（Inspection）

```helen
// context_stats() — 详细统计
let stats = context_stats()
// 返回:
// {
//   status: "ok",
//   message_count: 42,        // 消息总数
//   total_tokens: 18000,      // 估算 token 总数
//   usage_ratio: 0.45,        // 上下文窗口占用率（0.0–1.0+）
//   max_tokens: 40000,        // 配置的上下文窗口大小
//   by_role: {system: 1, user: 15, assistant: 14, tool: 12},
//   compressed_count: 5,      // 已经被压缩的消息数
//   pinned_count: 2,          // 被钉住的消息数
// }

// context_usage() — 简化版，只返回占用率
if context_usage() > 0.7 {
    compress_context("auto")
}
```

#### 8.5.2 单条消息访问与操作

```helen
// 读取
get_message(uuid)      // 按 UUID 读取消息快照

// 写入
insert_message(role, content, position?)   // 插入新消息（默认追加到末尾）
replace_message(uuid, new_content)         // 替换消息内容
delete_message(uuid)                       // 逻辑删除（审计保留）

// 钉住（Compression Immunity）
pin_message(uuid)      // 钉住消息，所有 5 层压缩都跳过
unpin_message(uuid)    // 取消钉住
```

Pinned 消息在 Layer 1–5 全部保留：
- Layer 1：不替换其 tool 输出
- Layer 2：不丢弃（即使是"过期"轮次）
- Layer 3：不清除其内容
- Layer 4：不归档（保留在投射视图中）
- Layer 5：不参与语义摘要

#### 8.5.3 工作记忆访问（P1）

```helen
// 读取（key 为空时返回全部）
let data = working_memory_get("task")         // 返回任务描述
let all = working_memory_get()                // 返回全部字段

// 写入（list 类型 key 默认追加，也可整体替换）
working_memory_set("task", "Build feature X")
working_memory_set("active_files", "new.py")  // 追加
working_memory_set("active_files", ["a.py"])  // 替换

// 删除（item 为空时清空整个字段）
working_memory_remove("task")
working_memory_remove("active_files", "old.py")

// 清空全部
working_memory_clear()
```

**可用 keys**: `task` | `active_files` | `decisions` | `todos` | `errors`

#### 8.5.4 运行时配置（P2）

v1.19 之前，这些配置只能在 `agent context {}` 块中声明。v1.19 支持运行时修改。

```helen
set_compression_strategy("graduated")   // "graduated" | "traditional" | "none"
set_context_window(64000)               // 设置上下文窗口大小（token 数）
set_working_memory_enabled(true)        // 开关工作记忆
set_cache_aware(true)                   // 开关缓存感知
let cfg = get_context_config()          // 查询当前配置
// cfg: {compression_strategy, max_tokens, working_memory_enabled, cache_aware_enabled, ...}
```

#### 8.5.5 查询（P3）

```helen
// 全文搜索
let r = search_context("TODO", role="user", limit=10)
// r.matches: [{uuid, role, snippet, index}, ...]

// 上下文切片
let slice = context_slice(start=5, end=20, role="")
// slice.messages: [{uuid, role, content, token_count, compressed, pinned, index}, ...]
```

#### 8.5.6 多 Agent 上下文共享（P2/P3）

```helen
// 导出当前上下文为可传输的 dict
let snapshot = export_context()
// snapshot.context: {messages, working_memory, config}

// 导入上下文（替换当前历史）
import_context(snapshot.context)

// Fork：返回与 export_context 相同结构的深拷贝
let forked = fork_context()
// 修改 forked 不影响原上下文
```

典型用途：通过 Channel 把当前对话上下文传给另一个 Agent；保存上下文到磁盘；fork 后并行探索多个方向。

#### 8.5.6b 跨会话恢复（v1.21+）

```helen
// 列出所有旧会话
let sessions = list_sessions()
for s in sessions {
    print("{s.session_id}: {s.message_count} msgs, scope={s.scope}")
}

// 从旧 transcript session 直接恢复 active context
let r = restore_context("session_1783492628_d9d9c0aa")
// r: {
//   status: "ok",
//   restored_messages: 42,
//   session_id: "session_1783492628_d9d9c0aa",
//   boundary_markers: 3,       // 跳过的压缩边界标记数
//   note: "Working memory and context config are not persisted..."
// }

// 中文别名
let r2 = 恢复上下文("session_1783492628_d9d9c0aa")
```

**`restore_context(session_id)` 的语义**：

1. 从磁盘读取指定 session 的 TranscriptStore
2. 遍历所有 Message（跳过 BoundaryMarker），保留完整字段：`role`、`content`、`tool_calls`、`tool_call_id`、`uuid`、`compressed`、`pinned`
3. 内部调用 `import_context()` 替换当前 `_interpreter_history`
4. 恢复后，下一次 `llm act` 调用就能看到旧会话的所有消息

**限制**：只恢复 messages。**不**恢复 working_memory 和 context config（transcript 不存这些）。需要时通过 `working_memory_set()` / `set_compression_strategy()` 等手动恢复。

**与 `resume_session()` 的区别**：

| | `restore_context` | `resume_session` |
|---|---|---|
| 恢复目标 | Active Context（LLM 看到的） | TranscriptStore（审计记录） |
| LLM 能看到恢复的消息？ | ✅ 能 | ❌ 不能（只换 SSOT 引用） |
| 适用场景 | 接续旧会话继续工作 | 切换到旧 transcript 流 |

#### 8.5.7 生命周期钩子（P1）

```helen
// 注册压缩事件回调
on_compression(callback)
// callback 接收：{layer, original_tokens, compressed_tokens, ...}

// 注册上下文溢出回调（预留接口）
on_context_overflow(callback)

// 传 None 清除回调
on_compression(None)
```

#### 8.5.8 中文别名（v1.19 全部 24 个 + v1.21 新增 1 个）

| 英文名 | 中文名 |
|--------|--------|
| context_stats | 上下文统计 |
| context_usage | 上下文占用率 |
| get_message | 获取消息 |
| delete_message | 删除消息 |
| pin_message | 钉住消息 |
| unpin_message | 取消钉住 |
| insert_message | 插入消息 |
| replace_message | 替换消息 |
| working_memory_get | 获取工作记忆 |
| working_memory_set | 设置工作记忆 |
| working_memory_remove | 移除工作记忆 |
| working_memory_clear | 清空工作记忆 |
| set_compression_strategy | 设置压缩策略 |
| set_context_window | 设置上下文窗口 |
| set_working_memory_enabled | 设置工作记忆开关 |
| set_cache_aware | 设置缓存感知 |
| get_context_config | 获取上下文配置 |
| search_context | 搜索上下文 |
| context_slice | 上下文切片 |
| export_context | 导出上下文 |
| import_context | 导入上下文 |
| fork_context | 分叉上下文 |
| **restore_context** | **恢复上下文** (v1.21+) |
| on_compression | 压缩回调 |
| on_context_overflow | 溢出回调 |

#### 8.5.9 内部化

原 stdlib 函数 `classify_message` 已内部化为 `_classify_message`，不再对外暴露。中文别名"消息分类"同步移除。

---

## 九、已知问题与限制

> 以下是当前架构中的已知问题，按严重程度排列。

### 9.1 架构问题

**已修复**：
- ✅ `LLMSummarizer` 已集成到 Layer 5：通过 `graduated_compress(llm_client=...)` 传递，LLM 不可用时回退到结构摘要
- ✅ `WorkingMemory` 已改为 token 级淘汰：`_evict_to_budget()` 按优先级淘汰最旧条目

### 9.2 文档与代码不符

**已修复**：
- ✅ `wiki/runtime/working_memory.md`：已更新为正确的 API（`to_context(budget_chars)`、Channel 2 预算截断）
- ✅ `wiki/runtime/history.md`：已更新 `estimate_tokens` 描述，说明字符类型感知和 CJK 支持

---

## 十、数据流总览

```
用户输入 prompt
    │
    ▼
visit_llm_act_expr()
    │
    ├─► 读取 agent.context_config
    │   └─► 更新 AgentContextManager 的 strategy/cache_aware/working_memory 设置
    │
    ├─► _add_to_history("user", prompt)
    │   ├─► 追加 Message 到 self._history
    │   ├─► HistoryManager.enforce_limit()    ← 传统压缩（第一层）
    │   └─► agent_context.update_from_message() ← 更新工作记忆
    │
    ├─► LLM 调用 + 工具循环
    │   └─► _record_llm_response_to_history()
    │       ├─► 追加 assistant/tool Message
    │       └─► agent_context.update_from_tool_call() ← 更新工作记忆
    │
    └─► _prepare_history_for_llm()
        └─► agent_context.prepare_context()
            ├─► _compress_history()           ← 渐进压缩 + 缓存感知包裹（第二层）
            └─► build_three_channel_context() ← 三通道构建
                ├─ Channel 1: 系统指令 (15%)
                ├─ Channel 2: 工作记忆 (50%, 受预算截断)
                └─ Channel 3: 对话历史 (35%)
                    │
                    ▼
                发送给 LLM API
```

**注意**：图中标注了"第一层"和"第二层"压缩——这是当前双重压缩问题的根源。`_add_to_history()` 中的 `enforce_limit()` 使用传统算法先压一次，`prepare_context()` 中的 `_compress_history()` 使用渐进算法再压一次。

---

## 十一、文件索引

| 文件 | 职责 |
|------|------|
| `helen/interpreter/agent_context.py` | 统一入口：AgentContextManager、工作记忆更新、压缩编排、三通道构建 |
| `helen/runtime/working_memory.py` | WorkingMemory 数据类、`to_context(budget_chars)` 格式化、`build_three_channel_context()` |
| `helen/runtime/graduated_compression.py` | 5 层渐进管线、`graduated_compress()`、各层函数 |
| `helen/runtime/cache_aware_compression.py` | `CacheAwareCompressor` 类（当前未被 agent_context 调用）、便捷函数 |
| `helen/runtime/history.py` | Message 数据类、HistoryManager（传统压缩、token 估算）|
| `helen/runtime/llm_summarizer.py` | LLMSummarizer、`auto_compact()`（当前未集成）|
| `helen/stdlib/context.py` | `clear_context()`、`compress_context()`、`compress_context_target()` |
| `helen/core/ast.py` | `ContextConfigNode` AST 节点 |
| `helen/core/parser.py` | `context {}` 块解析 |
| `helen/interpreter/llm_mixin.py` | `context_config` 应用、历史更新集成 |

---

## 十二、参考文献

本文档描述的上下文管理系统借鉴了以下学术研究：

- **RCC (Recurrent Context Compression)** — 分段摘要，保留时序结构 → Layer 4 Context Collapse
- **CogCanvas** — 保留时间细节，避免信息丢失 → Layer 4 时间线视图
- **DAST (Dynamic Allocation)** — 动态分配压缩 tokens（未来改进方向）

详见 [[runtime/context-compression-research|上下文压缩研究资料]]。

---

**最后更新**: 2026-07-17
**版本**: v1.22
