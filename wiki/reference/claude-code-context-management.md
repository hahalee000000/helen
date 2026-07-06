# Claude Code 上下文管理技术详解

> 基于 arXiv:2604.14228v2 (Liu et al., 2026)、Anthropic 官方文档整理

**日期**：2026-07-06
**来源**：
- [arXiv:2604.14228v2 — "Dive into Claude Code"](https://arxiv.org/html/2604.14228v2)
- [Context Editing API](https://platform.claude.com/docs/en/build-with-claude/context-editing)
- [Context Windows](https://platform.claude.com/docs/en/build-with-claude/context-windows)

---

## 一、整体架构概览

Claude Code 的上下文管理由三个独立但互补的系统组成：

```
┌──────────────────────────────────────────────────────────────┐
│                     客户端 (Claude Code)                      │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  5 层渐进式压缩管线 (Graduated Compaction Pipeline)     │  │
│  │  执行位置: query.ts:365-453                              │  │
│  │  执行时机: 每次模型调用前                                 │  │
│  │                                                        │  │
│  │  Layer 1: Budget Reduction  (零成本，总是启用)           │  │
│  │  Layer 2: Snip              (零成本，feature flag)       │  │
│  │  Layer 3: Microcompact      (零成本，缓存感知路径可选)   │  │
│  │  Layer 4: Context Collapse  (零成本，纯读时投影)         │  │
│  │  Layer 5: Auto-Compact      (LLM 调用，最后手段)         │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  附加机制                                               │  │
│  │  - Reactive Compaction (REACTIVE_COMPACT flag)          │  │
│  │  - Prompt-too-long 恢复级联                             │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                     API 层 (Anthropic)                        │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Context Editing (服务端编辑)                            │  │
│  │  Beta: context-management-2025-06-27                     │  │
│  │                                                        │  │
│  │  策略 1: clear_tool_uses_20250919 (工具结果清除)         │  │
│  │  策略 2: clear_thinking_20251015 (思考块清除)            │  │
│  │  策略 3: compact_20260112 (服务端压缩)                   │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Context Awareness (上下文感知)                          │  │
│  │  - 自动注入 token 预算标签到系统提示                     │  │
│  │  - 每次工具调用后注入剩余容量更新                        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  上下文窗口                                              │  │
│  │  - 200K tokens (旧模型)                                 │  │
│  │  - 1M tokens (Claude 4.6+ 系列)                         │  │
│  │  - 溢出行为: Claude 4.5+ 优雅停止; 旧模型返回错误        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 二、5 层渐进式压缩管线（核心）

### 设计哲学："最廉价动作优先"（Cheapest Move First）

来自论文原文：

> "The graduated design reflects a lazy-degradation principle: apply the least disruptive compression first, escalating only when cheaper strategies prove insufficient."

五层按成本从低到高排列，每层只在更便宜的层不够用时才升级：

| 层级 | 名称 | 推理成本 | 启用状态 | 核心机制 |
|------|------|----------|----------|----------|
| 1 | Budget Reduction | 零（纯内容替换） | **总是启用** | 大工具输出 → 引用指针 |
| 2 | Snip | 零（纯消息裁剪） | Feature flag `HISTORY_SNIP` | 丢弃过时历史段 |
| 3 | Microcompact | 零（结构操作） | 时间路径总是启用；缓存路径 flag `CACHED_MICROCOMPACT` | 按 tool_use_id 清除旧工具结果 |
| 4 | Context Collapse | 零（读时投影） | Feature flag `CONTEXT_COLLAPSE` | 读时投射折叠视图，不修改底层数据 |
| 5 | Auto-Compact | **一次 LLM 推理** | 默认启用，用户可关闭 | LLM 语义摘要 |

### 执行流程

```python
# query.ts:365-453 — 每次模型调用前的管线
def prepare_messages_for_query(messages_for_query):
    """五层管线按顺序执行"""

    # Layer 1: 总是运行 — 替换超大工具输出
    messages = apply_tool_result_budget(messages_for_query)

    # Layer 2: Feature flag 控制 — 裁剪过时历史
    if feature("HISTORY_SNIP"):
        result = snip_compact_needed(messages)
        messages = result.messages
        snip_tokens_freed = result.tokens_freed  # 关键：传递给 auto-compact

    # Layer 3: 时间路径总是运行；缓存路径 flag 控制
    result = microcompact(messages)
    messages = result.messages
    compaction_info = result.compaction_info

    # Layer 4: Feature flag 控制 — 折叠视图
    if feature("CONTEXT_COLLAPSE"):
        messages = apply_collapse_if_needed(messages)

    # Layer 5: 最后手段 — 只在前面四层都不够时触发
    if context_still_exceeds_pressure_threshold(messages):
        messages = compact_conversation(messages)  # LLM 调用

    return messages
```

**关键设计细节**：
- Layer 1 在 Layer 3 之前运行，因为 Layer 1 检查内容（content-level），Layer 3 按 ID 操作（ID-level），两者组合无冲突
- Layer 2 释放的 token 数（`snip_tokens_freed`）显式传递给 Layer 5，因为 token 计数器从最后一条 assistant 消息的 `usage` 字段推导，而 snip 不修改该消息
- Layer 4 是唯一不修改消息数组的层 — 它是纯读时投影

---

### Layer 1: Budget Reduction（预算削减）

**函数**: `applyToolResultBudget()`
**成本**: 零推理成本（纯内容替换）
**状态**: 总是启用，无 feature flag

#### 机制

对每个工具结果消息，检查大小是否超过 `maxResultSizeChars` 限制：
- 超过 → 替换为"内容引用"（content reference / pointer）
- 未超过 → 保持原样

#### 豁免工具

`maxResultSizeChars` 为 **非有限值**（`Infinity` 或未设置）的工具不受预算削减影响。

#### 持久化

内容替换被持久化到 agent 和 session 查询源，以便在恢复（resume）时可以重建。

#### 与 Microcompact 的关系

Budget Reduction 在 Microcompact 之前运行，因为：
- Budget Reduction = **内容层**操作（检查工具结果的内容大小）
- Microcompact = **结构层**操作（按 tool_use_id 识别要压缩的对，不检查内容）

#### 论文未给出的细节
- `maxResultSizeChars` 的具体值
- "内容引用"的具体格式

---

### Layer 2: Snip（裁剪）

**函数**: `snipCompactIfNeeded()`
**成本**: 零推理成本（纯消息裁剪）
**状态**: Feature flag `HISTORY_SNIP`

#### 机制

轻量级裁剪，移除较旧的历史段。处理"时间深度"（temporal depth）问题 — 随对话推进累积的旧轮次。

#### 返回值

```python
{
    "messages": [...],           # 裁剪后的消息列表
    "tokensFreed": int,          # 释放的 token 数
    "boundaryMessage": Message,  # 边界消息（标记裁剪点）
}
```

#### 关键的管道传递

`snipTokensFreed` 值显式传递给 auto-compact。原因：
- 主 token 计数器从最近一条 assistant 消息的 `usage` 字段推导上下文大小
- Snip 不修改该消息，所以其原始 `input_tokens` 仍然attached
- 如果不显式传递，snip 的节省对计数器不可见

#### 什么使一个轮次"过时"

论文未给出精确算法或阈值。只说 snip "removes older history segments"。

---

### Layer 3: Microcompact（微压缩）— 核心创新

**成本**: 零推理成本
**状态**: 时间路径总是启用；缓存感知路径由 `CACHED_MICROCOMPACT` flag 控制

#### 两条子路径

1. **时间路径**（总是运行）— 基于时间的压缩
2. **缓存感知路径**（flag 控制）— 使用 API 返回的实际缓存删除数据

#### 核心机制：按 tool_use_id 操作

> "Microcompact operates purely by `tool_use_id` and **never inspects content**."

这是 Microcompact 的关键结构洞察：
- 通过 tool_use_id 识别哪些 tool_use/tool_result 对需要压缩
- **不检查工具结果的内容**
- 与 Budget Reduction 在不同层面操作，无冲突

#### 缓存感知路径的精妙设计

当启用缓存感知路径时：
- **边界消息被延迟到 API 响应之后**
- 使用 API 返回的**实际 `cache_deleted_input_tokens`** 而非估算值
- 系统不猜测释放了多少缓存，而是从响应中读取实际数字

#### 返回值

```python
{
    "messages": [...],
    "compactionInfo": {
        "pendingCacheEdits": [...]  # 缓存感知路径的待处理编辑
    }
}
```

#### 推断的 tool_use vs tool_result 处理

虽然论文没有明确描述块级转换，但可以推断：
- **tool_use 块**（assistant 消息中的工具调用决策）→ 保留
- **tool_result 块**（user 消息中的工具返回数据）→ 替换为占位文本

这意味着模型"记得自己做了什么"（tool_use），但"不记得工具返回了什么"（tool_result）。

---

### Layer 4: Context Collapse（上下文折叠）

**函数**: `applyCollapsesIfNeeded()`
**成本**: 零推理成本
**状态**: Feature flag `CONTEXT_COLLAPSE`

#### 架构独特性：纯读时投影

> "Nothing is yielded; the collapsed view is a read-time projection over the REPL's full history. Summary messages live in the collapse store, not the REPL array. This is what makes collapses persist across turns."

**与其他四层的根本区别**：
| 层级 | 是否修改消息数组 | 底层数据 |
|------|----------------|----------|
| Budget Reduction | ✅ 修改 | 修改 |
| Snip | ✅ 修改 | 修改 |
| Microcompact | ✅ 修改 | 修改 |
| **Context Collapse** | ❌ 不修改 | **不修改** |
| Auto-Compact | ✅ 修改 | 修改 |

Context Collapse 是唯一不修改底层数据的层。

#### 工作机制

```
底层存储 (REPL array)        读时视图 (messagesForQuery)
┌─────────────────────┐     ┌─────────────────────────┐
│ Turn 1: user+asst   │     │                         │
│ Turn 2: user+asst   │ ──→ │ [折叠摘要: 前 N 轮]      │
│ Turn 3: user+asst   │     │ Turn N-2: user+asst     │
│ Turn 4: user+asst   │     │ Turn N-1: user+asst     │
│ Turn 5: user+asst   │     │ Turn N:   user+asst     │
└─────────────────────┘     └─────────────────────────┘
完整历史永不修改             模型只看到折叠视图
```

#### 存储

- 摘要消息存储在独立的 **"collapse store"** 中
- 折叠跨轮次持久化（因为存在 store 中，不是临时数组）
- 用户不可见 — "operates without user-visible output"

---

### Layer 5: Auto-Compact（自动压缩）— 最后手段

**函数**: `compactConversation()` (compact.ts)
**成本**: 一次完整 LLM 推理调用
**状态**: 默认启用，用户可配置关闭

#### 触发条件

> "Auto-compact fires **only when the context still exceeds the pressure threshold** after all four previous shapers have run."

即只有当前面四层都不够时，才触发 LLM 压缩。

#### LLM 摘要流程

```python
def compact_conversation(messages):
    # 1. PreCompact hooks 先触发 — 允许 hook 注入自定义指令
    hook_results = run_pre_compact_hooks()

    # 2. 创建摘要请求
    summary_prompt = get_compact_prompt()  # 摘要提示词

    # 3. 调用 LLM 生成压缩摘要（一次完整的推理调用）
    summary_response = llm_call(
        messages=build_summary_messages(messages),
        prompt=summary_prompt,
    )

    # 4. 构建压缩后消息
    return build_post_compact_messages(
        boundary_marker,       # 压缩边界标记
        summary_messages,      # 摘要消息
        messages_to_keep,      # 保留的最近消息
        attachments,           # 运行时状态附件
        hook_results,          # hook 结果
    )
```

#### 边界标记的"mostly-append"设计

```python
# build_post_compact_messages 返回:
[
    boundary_marker,       # 压缩边界，附带 preserved-segment 元数据
    ...summary_messages,   # LLM 生成的摘要
    ...messages_to_keep,   # 保留的最近消息
    ...attachments,        # 运行时状态（plans, skills, agents）
    ...hook_results,       # hook 注入的内容
]

# 边界标记附带元数据:
boundary_marker.metadata = {
    "headUuid": "...",     # 头部保留段的 UUID
    "anchorUuid": "...",   # 锚点 UUID
    "tailUuid": "...",     # 尾部保留段的 UUID
}
```

这些 UUID 使 session loader 能够在**读时修补消息链**：
- 保留的消息保持其原始 `parentUuids`
- Loader 使用边界元数据正确链接

**关键设计原则**：压缩通常**不修改或删除之前写入的 transcript 行** — 只追加新的边界和摘要事件。

#### 压缩后的运行时状态重建

压缩丢弃了之前的 attachment 消息，但不丢弃底层状态。因此：
- 压缩后，attachment builders 从**实时 app 状态**重新发布（plans、skills、async agents）
- 确保模型知道当前进行中的工作

#### 缓存行为（实验数据）

GrowthBook feature flag 控制压缩路径是否复用主对话的 prompt cache：

```
实验（2026 年 1 月）:
- "false path"（不复用 cache）→ 98% cache miss
- 但只消耗 ~0.76% 的 fleet cache_creation tokens
```

#### 论文未给出的细节
- 确切的"压力阈值"数值
- `getCompactPrompt()` 的确切内容
- 用于摘要调用的模型
- 摘要的确切 token 目标

---

## 三、附加压缩机制

### 3.1 Reactive Compaction（反应式压缩）

**Feature flag**: `REACTIVE_COMPACT`

```
触发条件: 在轮次执行期间，上下文接近容量上限
行为: 只摘要刚好够释放空间的内容
限制: hasAttemptedReactiveCompact flag 确保每轮最多触发一次
```

### 3.2 Prompt-too-long 恢复级联

当 API 返回 `prompt_too_long` 错误时：

```
步骤 1: 尝试 context-collapse overflow recovery
步骤 2: 如果失败 → 尝试 reactive compaction
步骤 3: 如果仍失败 → 终止，reason: 'prompt_too_long'
```

---

## 四、服务端 Context Editing API

### 4.1 API 概览

```
Beta header: context-management-2025-06-27
运行位置: 服务端（API 侧），在 prompt 到达 Claude 之前应用
客户端状态: 不修改 — 客户端维护完整的未修改对话历史
```

**核心原则**：Context editing 是**服务端应用**的。客户端应用维护完整的未修改对话历史，不需要与编辑后的版本同步。

### 4.2 策略 1: 工具结果清除 (clear_tool_uses_20250919)

#### 参数详解

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `trigger` | 100,000 input_tokens | 策略激活阈值。可以是 `input_tokens` 或 `tool_uses` 类型 |
| `keep` | 3 tool_uses | 清除后保留的最近工具调用/结果对数量。API 按时间顺序移除最旧的 |
| `clear_at_least` | 无 | 确保每次激活至少清除的 token 数。如果无法清除到最少，策略**不会被应用** |
| `exclude_tools` | 无 | 永不清除的工具名列表。保护重要上下文 |
| `clear_tool_inputs` | false | 是否同时清除工具调用参数。默认只清除结果，保留 Claude 的工具调用可见 |

#### 行为细节

```
激活时:
1. API 按时间顺序清除最旧的工具结果
2. 每个被清除的结果替换为占位文本，让 Claude 知道它被移除了
3. 默认保留 Claude 的 tool_use 块（工具调用决策）
4. 如果 clear_tool_inputs=true，同时清除工具调用参数

保留的内容:
✅ System prompt — 永不清除
✅ User messages — 永不清除
✅ Assistant text — 永不清除
✅ tool_use blocks（默认）— Claude 的决策记录

清除的内容:
❌ 旧的 tool_result content — 工具返回的原始数据
❌ (可选) tool_use parameters — 工具调用参数
```

#### 代码示例

```python
# 基础使用
response = client.beta.messages.create(
    model="claude-opus-4-8",
    max_tokens=4096,
    messages=[{"role": "user", "content": "搜索 AI 最新进展"}],
    tools=[{"type": "web_search_20250305", "name": "web_search"}],
    betas=["context-management-2025-06-27"],
    context_management={
        "edits": [{"type": "clear_tool_uses_20250919"}]
    },
)

# 高级配置
response = client.beta.messages.create(
    model="claude-opus-4-8",
    max_tokens=4096,
    messages=[{"role": "user", "content": "创建一个 Python 计算器"}],
    tools=[
        {"type": "text_editor_20250728", "name": "str_replace_based_edit_tool"},
        {"type": "web_search_20250305", "name": "web_search"},
    ],
    betas=["context-management-2025-06-27"],
    context_management={
        "edits": [{
            "type": "clear_tool_uses_20250919",
            "trigger": {"type": "input_tokens", "value": 30000},
            "keep": {"type": "tool_uses", "value": 3},
            "clear_at_least": {"type": "input_tokens", "value": 5000},
            "exclude_tools": ["web_search"],  # web_search 结果永不清除
        }]
    },
)
```

#### 缓存行为

```
清除工具结果 → 使缓存的 prompt 前缀失效
每次清除 → 产生 cache write 费用
后续请求 → 可以复用新缓存的前缀

最佳实践:
- 使用 clear_at_least 确保每次清除的 token 数足够多，
  使缓存失效的代价值得
- 否则频繁的小量清除会导致 cache 不断失效
```

### 4.3 策略 2: 思考块清除 (clear_thinking_20251015)

#### 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `keep` | 模型特定 | 保留的最近包含思考块的 assistant 轮次数 |

**keep 格式**:
```python
{"type": "thinking_turns", "value": 2}  # 保留最近 2 轮的思考
"all"                                    # 保留所有思考块（最大化缓存命中）
```

**各模型的默认行为**:

| 模型类别 | 保留所有思考 | 只保留最后一轮思考 |
|----------|-------------|-------------------|
| Opus | 4.5+ | 4.1 及以下 |
| Sonnet | 4.6+ | 4.5 及以下 |
| Haiku | (无) | 所有模型 |

#### 缓存行为

```
保留思考块 → 缓存保持有效 ✅
清除思考块 → 缓存在清除点失效 ❌

选择 keep 参数时的权衡:
- 更多思考块 = 更多推理连续性 = 更好的缓存
- 更少思考块 = 更多上下文空间
```

#### 代码示例

```python
# 保留最近 2 轮的思考
response = client.beta.messages.create(
    model="claude-opus-4-8",
    max_tokens=16000,
    messages=[{"role": "user", "content": "Hello"}],
    thinking={"type": "adaptive"},
    betas=["context-management-2025-06-27"],
    context_management={
        "edits": [{
            "type": "clear_thinking_20251015",
            "keep": {"type": "thinking_turns", "value": 2},
        }]
    },
)

# 组合两个策略（注意顺序：thinking 必须在前面）
context_management={
    "edits": [
        {
            "type": "clear_thinking_20251015",          # ← 必须在前
            "keep": {"type": "thinking_turns", "value": 2},
        },
        {
            "type": "clear_tool_uses_20250919",
            "trigger": {"type": "input_tokens", "value": 50000},
            "keep": {"type": "tool_uses", "value": 5},
        },
    ]
}
```

### 4.4 响应格式

```json
{
  "id": "msg_013Zva2CMHLNnXjNJJKqJ2EF",
  "role": "assistant",
  "content": [...],
  "usage": {...},
  "context_management": {
    "applied_edits": [
      {
        "type": "clear_thinking_20251015",
        "cleared_thinking_turns": 3,
        "cleared_input_tokens": 15000
      },
      {
        "type": "clear_tool_uses_20250919",
        "cleared_tool_uses": 8,
        "cleared_input_tokens": 50000
      }
    ]
  }
}
```

**Token counting 端点的特殊响应**:
```json
{
  "input_tokens": 25000,
  "context_management": {
    "original_input_tokens": 70000
  }
}
// 可以看到清除前 70K → 清除后 25K，节省 45K tokens
```

### 4.5 策略 3: 服务端压缩 (compact_20260112)

替代已弃用的 SDK `compaction_control` 参数。在服务端执行完整的对话压缩。

---

## 五、Context Awareness（上下文感知）

### 5.1 自动注入机制

Anthropic API 自动为支持的模型注入上下文感知标签：

**系统提示中的预算标签**:
```xml
<budget:token_budget>200000</budget:token_budget>
```

**每次工具调用后的更新**:
```xml
<system_warning>Token usage: 35000/200000; 165000 remaining</system_warning>
```

### 5.2 支持的模型

| 模型 | 预算值 |
|------|--------|
| Claude Sonnet 5, Sonnet 4.6 | 1M tokens |
| Claude Sonnet 4.5, Haiku 4.5 | 200K tokens |

### 5.3 更新模型的行为

Claude Opus 4.7+、Fable 5、Mythos 5 **不再接收这些注入标签**，而是可以使用 task budgets（beta 功能）显式设置预算。

---

## 六、上下文窗口管理

### 6.1 窗口大小

| 模型 | 窗口大小 | 最大输出 |
|------|---------|---------|
| Claude Opus 4.8/4.7/4.6 | 1M | — |
| Claude Sonnet 5/4.6 | 1M | — |
| Claude Fable 5 / Mythos 5 | 1M | 128K tokens |
| Claude Sonnet 4.5 | 200K | — |
| 其他模型 | 200K | — |

### 6.2 什么计入上下文窗口

```
计入的内容:
✅ System prompt
✅ messages 数组中的每条消息
✅ 工具结果、图片、文档
✅ 工具定义 (tool definitions)
✅ Claude 生成的输出（包括扩展思考）
✅ 所有历史对话

⚠️ Prompt cache 的 token 也计入窗口
   (cache 只影响费用，不影响计数)
```

### 6.3 溢出行为

```
情况 1: 仅输入超过窗口
  → 所有模型返回 400 error: "prompt is too long"

情况 2: 输入 + max_tokens 超过窗口
  Claude 4.5+ 及更新模型:
    → API 接受请求，生成到限制时停止
    → stop_reason: "model_context_window_exceeded"
  旧模型:
    → 返回验证错误
    → 可通过 beta header 启用新行为:
      model-context-window-exceeded-2025-08-26
```

### 6.4 扩展思考与上下文

**保留思考块的模型**（默认）:
- Opus 4.5+, Sonnet 4.6+, Fable 5, Mythos 5, Mythos Preview
- 之前的思考块作为输入 token 计费

**自动剥离思考块的模型**（默认）:
- 更早的 Opus/Sonnet 模型, 所有 Haiku 模型
- API 自动从对话历史中剥离

**关键要求**: 返回工具结果时，必须包含**完整未修改的思考块**（包括加密签名）。修改思考块会导致 API 错误。

---

## 七、关键设计原则总结

### 7.1 "行动 > 数据"原则

```
Claude Code 的核心洞察:

✅ 保留 tool_use blocks — "LLM 决定做什么"
❌ 清除 tool_result content — "工具返回了什么"

理由:
- 工具的原始输出（文件内容、搜索结果）体积大，且通常在处理后不再需要
- LLM 的工具调用决策记录了推理路径，对未来决策有参考价值
- 用 20% 的 token 保留 80% 的决策上下文
```

### 7.2 "最廉价动作优先"原则

```
成本阶梯:
  零成本 → 内容替换 (Layer 1)
  零成本 → 消息裁剪 (Layer 2)
  零成本 → 结构压缩 (Layer 3)
  零成本 → 读时投影 (Layer 4)
  LLM 调用 → 语义压缩 (Layer 5)  ← 只在前面都不够时

每层只在更便宜的层不够用时才激活
```

### 7.3 "mostly-append"持久化原则

```
压缩不修改不删除之前的 transcript 行
只追加新的边界和摘要事件
保留的消息保持原始 parentUuids
读时通过边界元数据修补消息链
```

### 7.4 "缓存感知"原则

```
Microcompact 缓存路径:
- 延迟边界消息到 API 响应之后
- 使用实际的 cache_deleted_input_tokens
- 不猜测，从响应中读取

缓存失效的代价管理:
- clear_at_least 确保每次清除量足够大
- 避免频繁小量清除导致 cache 不断失效
```

### 7.5 "上下文质量 > 数量"原则

```
来自 Anthropic 文档:

"Context is a finite resource with diminishing returns —
 irrelevant content degrades model focus."

"More context isn't automatically better.
 As token count grows, accuracy and recall degrade
 (phenomenon known as 'context rot')."

"Curating what's in context is just as important
 as how much space is available."
```

---

## 八、 quantitative 数据

### 性能数据

| 指标 | 数值 | 来源 |
|------|------|------|
| 上下文编辑启用后性能提升 | **29%** | Anthropic 报告 |
| 清理代码对 Claude Code 的影响 | token 减少 **7-8%**，文件复查减少 **34%** | 对照实验 |
| Prompt cache 过期 | 不活跃 **5 分钟**后过期 | 论文 KAIROS 部分 |
| Fleet cache 成本（不复用路径） | **~0.76%** 的 fleet cache_creation | 2026 年 1 月实验 |
| 不复用路径 cache miss 率 | **98%** | 同上 |
| 自动批准率轨迹 | <50 会话 **~20%** → 750 会话 **>40%** | 纵向使用数据 |
| 95% 每步准确率下 100 步任务成功率 | **0.6%** | 引用研究 |

### 压缩效果

```
典型场景: 50 轮对话，大量工具调用

渐进式压缩流程:
  原始: ~200K tokens (接近 200K 窗口)
  Layer 1: 替换大工具输出 → ~160K (减少 20%)
  Layer 2: 丢弃过时轮次 → ~130K (减少 35%)
  Layer 3: 清除旧工具结果 → ~80K (减少 60%)
           保留所有 tool_use 决策
  Layer 4: 折叠视图 → ~60K (减少 70%)
  Layer 5: LLM 压缩 → ~40K (减少 80%)
           语义摘要保留关键信息

典型恢复: 60-70% 的上下文窗口
下次压缩触发: 在新的可用容量的 60% 处
```

---

## 九、与 Helen 的对应关系

| Claude Code 概念 | Helen 对应 | 差距 |
|-----------------|-----------|------|
| 5 层渐进压缩 | 1 层（80% 触发） | 缺 4 层 |
| Microcompact (按 ID 清除工具结果) | 无 | 核心缺失 |
| Context Collapse (读时投影) | 无 | 概念新颖 |
| Auto-Compact (LLM 语义压缩) | "summarize"（只是拼接） | 非真正 LLM 摘要 |
| Reactive Compaction | 无 | 缺 |
| Context Editing API | 无 | 缺服务端编辑 |
| Context Awareness (token 标签) | 无 | 模型不知道剩余容量 |
| 工具结果清除策略 | 截断到 16K | 更粗糙 |
| 思考块清除策略 | 无扩展思考 | N/A |
| mostly-append 持久化 | 无 | 缺 |
| 缓存感知压缩 | 无 | 缺 |
| 边界标记 UUID 链修补 | 无 | 缺 |
| "行动 > 数据"区分 | 无差别对待消息 | 核心缺失 |
