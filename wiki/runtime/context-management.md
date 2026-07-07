# 上下文管理架构 (Context Management Architecture)

> **版本**: v1.15 | **最后更新**: 2026-07-07
> 统一说明 Helen 的上下文管理系统，替换原 `agent_context.md`、`graduated_compression.md`、`cache_aware_compression.md`、`working_memory.md` 中的分散描述。

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
        working-memory-tokens 5000    // 工作记忆令牌预算
    }
    main { ... }
}

// 中文关键字
agent 智能助手 {
    上下文 {
        压缩 "graduated"
        缓存感知 true
        工作记忆 true
        工作记忆令牌 5000
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
    task_description: str = ""         # 当前任务描述
    active_files: list[str]            # 最近 10 个文件
    recent_decisions: list[str]        # 最近 10 个决策
    pending_todos: list[str]           # 最近 20 个 TODO
    error_history: list[dict]          # 最近 5 个错误
    max_tokens: int = 5000             # 预算（当前仅用于三通道构建，WorkingMemory 内部未强制）
```

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
| Layer 4 | 90% | Context Collapse | 零 | 归档旧轮次，投射结构折叠视图 |
| Layer 5 | 95% | Auto-Compact | 零 | 零成本结构摘要（提取文件路径、工具计数等） |

**重要澄清**：所有 5 层都是**零成本**的——使用正则/字符串操作，不调用 LLM。`LLMSummarizer`（`runtime/llm_summarizer.py`）是一个独立的模块，提供 LLM 语义摘要功能，但当前**未被集成到压缩管线中**。

### 4.2 API

```python
def graduated_compress(
    history: list[Message],
    usage_ratio: float,
    max_tokens: int = 131072,
) -> tuple[list[Message], str]:
    """
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

---

## 九、已知问题与限制

> 以下是当前架构中的已知问题，按严重程度排列。

### 9.1 架构问题

| 问题 | 说明 |
|------|------|
| **`LLMSummarizer` 未集成** | `runtime/llm_summarizer.py` 提供 LLM 语义摘要，但未被压缩管线或任何生产路径调用 |
| **`WorkingMemory` 列表长度限制** | 仅依赖硬编码的列表长度上限（10/10/20/5），无 token 级淘汰策略 |

### 9.2 文档与代码不符

| 文档 | 不符内容 |
|------|---------|
| `wiki/runtime/working_memory.md` | 描述了不存在的方法 (`has_content()`, `format_for_context()`) |
| `wiki/runtime/history.md` | `estimate_tokens` 描述为 `len(text)//4`，实际有字符类型感知和 CJK 支持 |

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

**最后更新**: 2026-07-07
**版本**: v1.15
