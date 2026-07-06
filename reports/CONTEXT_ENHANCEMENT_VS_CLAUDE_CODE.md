# Helen 上下文管理增强方案：对比 Claude Code

> 分析 Helen 与 Claude Code 上下文管理的差距，提出增强建议

**日期**：2026-07-06
**状态**：分析完成，待实施

**资料来源**：
- [arXiv:2604.14228v2 — "Dive into Claude Code"](https://arxiv.org/html/2604.14228v2) (Liu et al., UCL, April 2026)
- [Anthropic Context Editing API](https://platform.claude.com/docs/en/build-with-claude/context-editing)
- [Anthropic Context Windows](https://platform.claude.com/docs/en/build-with-claude/context-windows)
- 详细技术分析见 `wiki/reference/claude-code-context-management.md`

---

## 一、现状对比

### 1.1 架构对比

| 维度 | Helen 现状 | Claude Code |
|------|-----------|-------------|
| **压缩层级** | 1 层（触发后直接压缩） | 5 层渐进式压缩（cheapest move first） |
| **压缩策略** | 3 种：summarize/truncate/none | 5 级：Budget Reduction → Snip → Microcompact → Context Collapse → Auto-Compact |
| **触发机制** | 被动（超 80% 才压缩） | 主动（70% 预警，80% 遮蔽，90% 紧急，99% 完全压缩） |
| **LLM 压缩** | ❌ 无（"summarize" 只是拼接文本） | ✅ Layer 5 用 LLM 做语义压缩 |
| **内容选择性** | ❌ 无差别对待所有消息 | ✅ 区分行动（tool_use）和数据（tool_result） |
| **工具结果管理** | 截断到 16K 字符 | 清除旧结果，保留动作历史 |
| **缓存友好** | ❌ 压缩会破坏缓存 | ✅ 部分策略保持缓存有效 |
| **Token 计数** | tiktoken（可选）+ 启发式（~85% 准确） | 精确计数 |

### 1.2 Claude Code 详细做法

> 详细技术分析见 `wiki/reference/claude-code-context-management.md`

#### 1.2.1 三层系统架构

Claude Code 的上下文管理由三个独立但互补的系统组成：

```
┌──────────────────────────────────────────────────────────────┐
│  客户端 (Claude Code)                                        │
│  └── 5 层渐进式压缩管线 (query.ts:365-453)                   │
│      执行时机: 每次模型调用前                                  │
│      设计哲学: "最廉价动作优先" (cheapest move first)         │
├──────────────────────────────────────────────────────────────┤
│  API 层 (Anthropic)                                          │
│  ├── Context Editing (服务端编辑, Beta)                       │
│  │   ├── 策略 1: clear_tool_uses_20250919 (工具结果清除)     │
│  │   ├── 策略 2: clear_thinking_20251015 (思考块清除)        │
│  │   └── 策略 3: compact_20260112 (服务端压缩)               │
│  └── Context Awareness (上下文感知)                          │
│      ├── 自动注入 token 预算标签到系统提示                     │
│      └── 每次工具调用后注入剩余容量更新                        │
├──────────────────────────────────────────────────────────────┤
│  上下文窗口                                                  │
│  ├── 200K tokens (旧模型)                                    │
│  ├── 1M tokens (Claude 4.6+ 系列)                            │
│  └── 溢出行为: Claude 4.5+ 优雅停止; 旧模型返回错误          │
└──────────────────────────────────────────────────────────────┘
```

#### 1.2.2 五层渐进式压缩管线详解

**设计哲学**："最廉价动作优先" — 每层按成本从低到高排列，只在更便宜的层不够用时才升级。

| 层级 | 名称 | 函数 | 推理成本 | Feature Flag | 核心机制 |
|------|------|------|----------|--------------|----------|
| 1 | Budget Reduction | `applyToolResultBudget()` | 零 | 无（总是启用） | 大工具输出 → 引用指针 |
| 2 | Snip | `snipCompactIfNeeded()` | 零 | `HISTORY_SNIP` | 丢弃过时历史段 |
| 3 | Microcompact | — | 零 | 时间路径总是启用；缓存路径 `CACHED_MICROCOMPACT` | 按 tool_use_id 清除旧工具结果 |
| 4 | Context Collapse | `applyCollapsesIfNeeded()` | 零 | `CONTEXT_COLLAPSE` | 读时投射折叠视图，不修改底层数据 |
| 5 | Auto-Compact | `compactConversation()` | **一次 LLM 推理** | 默认启用 | LLM 语义摘要 |

**执行流程（伪代码）**:
```python
# query.ts:365-453
def prepare_messages_for_query(messages):
    # Layer 1: 总是运行 — 替换超大工具输出
    messages = apply_tool_result_budget(messages)

    # Layer 2: Feature flag 控制 — 裁剪过时历史
    if feature("HISTORY_SNIP"):
        result = snip_compact_needed(messages)
        messages = result.messages
        snip_tokens_freed = result.tokens_freed  # 关键：传递给 auto-compact

    # Layer 3: 时间路径总是运行；缓存路径 flag 控制
    result = microcompact(messages)
    messages = result.messages

    # Layer 4: Feature flag 控制 — 折叠视图
    if feature("CONTEXT_COLLAPSE"):
        messages = apply_collapse_if_needed(messages)

    # Layer 5: 最后手段 — 只在前面四层都不够时触发
    if context_still_exceeds_threshold(messages):
        messages = compact_conversation(messages)  # LLM 调用

    return messages
```

**关键设计细节**:
- Layer 1 在 Layer 3 之前运行：Layer 1 检查内容（content-level），Layer 3 按 ID 操作（ID-level），两者组合无冲突
- Layer 2 释放的 token 数显式传递给 Layer 5：因为 token 计数器从最后一条 assistant 消息的 `usage` 字段推导，而 snip 不修改该消息
- Layer 4 是唯一不修改消息数组的层 — 它是纯读时投影

#### 1.2.3 每层详细机制

**Layer 1: Budget Reduction**
- 对每个工具结果消息，检查大小是否超过 `maxResultSizeChars` 限制
- 超过 → 替换为"内容引用"（content reference / pointer）
- `maxResultSizeChars` 为非有限值的工具不受影响（豁免）
- 内容替换被持久化，以便在恢复时重建

**Layer 2: Snip**
- 轻量级裁剪，移除较旧的历史段
- 返回 `{messages, tokensFreed, boundaryMessage}`
- 关键：`snipTokensFreed` 显式传递给 auto-compact，否则节省对计数器不可见

**Layer 3: Microcompact — 核心创新**
- **核心机制**："按 tool_use_id 操作，不检查内容"
- 通过 tool_use_id 识别哪些 tool_use/tool_result 对需要压缩
- 保留 tool_use 块（assistant 的工具调用决策）
- 清除 tool_result 内容（工具的返回数据），替换为占位文本
- **缓存感知路径**：延迟边界消息到 API 响应之后，使用实际的 `cache_deleted_input_tokens` 而非估算值
- 效果：模型"记得自己做了什么"，但"不记得工具返回了什么"

**Layer 4: Context Collapse — 架构独特**
- **唯一不修改底层数据的层**
- 纯读时投影：底层存储（REPL array）永不修改
- 摘要消息存储在独立的 "collapse store" 中
- 折叠跨轮次持久化
- 模型只看到折叠视图，完整历史仍可用于重建

**关键设计：两阶段架构**

Context Collapse 的"零成本"指的是**投影过程**，不是摘要生成：

```
阶段 1：摘要生成（有成本，发生在别处）
  ├── 可能由 Auto-Compact (Layer 5) 生成
  ├── 可能由后台进程生成
  └── 可能由其他压缩层生成
      ↓
  摘要存储在 collapse store 中

阶段 2：读时投影（零成本，Context Collapse 的工作）
  ├── 从 collapse store 读取预生成的摘要
  ├── 投射到 messagesForQuery 数组
  └── 不生成新内容，只选择显示什么
```

**论文关键线索**：
> "External research on summary-based compaction documents two costs beyond opacity that the source-level view does not surface: **the summarization step is a blocking inference stall**, and it is non-deterministic"

**解读**：
- "summarization step" 是一个独立的步骤（需要 LLM 调用）
- 它是 "blocking inference stall"（阻塞性推理停顿）
- 这个成本在 Context Collapse 的"零成本"描述之外

**源码注释**：
> "Summary messages live in the collapse store, not the REPL array. **This is what makes collapses persist across turns.**"

**设计优势**：
1. **分离关注点**：摘要生成（高成本）和视图投射（零成本）分离
2. **按需计算**：只在需要时生成摘要，不是每轮都生成
3. **可复用**：生成的摘要可以跨轮次使用
4. **灵活性**：可以用不同策略生成摘要（LLM、规则、混合）

**Layer 5: Auto-Compact — 最后手段**
- 触发条件："只有当前面四层都不够时才触发"
- 流程：PreCompact hooks → 创建摘要请求 → LLM 调用 → 构建压缩后消息
- **Mostly-append 设计**：压缩不修改或删除之前的 transcript 行，只追加新的边界和摘要事件
- 边界标记附带 `headUuid`/`anchorUuid`/`tailUuid`，使 session loader 能在读时修补消息链
- 压缩后，attachment builders 从实时 app 状态重新发布（plans、skills、agents）

#### 1.2.4 附加机制

**Reactive Compaction** (feature flag: `REACTIVE_COMPACT`):
- 在轮次执行期间，上下文接近容量上限时触发
- 只摘要刚好够释放空间的内容
- `hasAttemptedReactiveCompact` flag 确保每轮最多触发一次

**Prompt-too-long 恢复级联**:
```
步骤 1: 尝试 context-collapse overflow recovery
步骤 2: 如果失败 → 尝试 reactive compaction
步骤 3: 如果仍失败 → 终止，reason: 'prompt_too_long'
```

#### 1.2.5 服务端 Context Editing API

**核心原则**：Context editing 是服务端应用的。客户端维护完整的未修改对话历史，不需要与编辑后的版本同步。

**策略 1: 工具结果清除** (`clear_tool_uses_20250919`)

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `trigger` | 100,000 input_tokens | 策略激活阈值 |
| `keep` | 3 tool_uses | 清除后保留的最近工具调用对数量 |
| `clear_at_least` | 无 | 每次激活至少清除的 token 数。如果无法达到，策略**不会被应用** |
| `exclude_tools` | 无 | 永不清除的工具名列表 |
| `clear_tool_inputs` | false | 是否同时清除工具调用参数 |

```python
# 示例
context_management={
    "edits": [{
        "type": "clear_tool_uses_20250919",
        "trigger": {"type": "input_tokens", "value": 30000},
        "keep": {"type": "tool_uses", "value": 3},
        "clear_at_least": {"type": "input_tokens", "value": 5000},
        "exclude_tools": ["web_search"],
    }]
}
```

**策略 2: 思考块清除** (`clear_thinking_20251015`)

```python
context_management={
    "edits": [{
        "type": "clear_thinking_20251015",
        "keep": {"type": "thinking_turns", "value": 2},
    }]
}
```

**响应格式**:
```json
{
  "context_management": {
    "applied_edits": [
      {
        "type": "clear_tool_uses_20250919",
        "cleared_tool_uses": 8,
        "cleared_input_tokens": 50000
      }
    ]
  }
}
```

#### 1.2.6 Context Awareness（上下文感知）

Anthropic API 自动为支持的模型注入上下文感知标签：

```xml
<!-- 系统提示中的预算标签 -->
<budget:token_budget>200000</budget:token_budget>

<!-- 每次工具调用后的更新 -->
<system_warning>Token usage: 35000/200000; 165000 remaining</system_warning>
```

支持的模型：
- Claude Sonnet 5, Sonnet 4.6 → 1M tokens 预算
- Claude Sonnet 4.5, Haiku 4.5 → 200K tokens 预算

#### 1.2.7 关键设计原则

**原则 1: "行动 > 数据"**
```
✅ 保留 tool_use blocks — "LLM 决定做什么"
❌ 清除 tool_result content — "工具返回了什么"

理由:
- 工具的原始输出体积大，且通常在处理后不再需要
- LLM 的工具调用决策记录了推理路径，对未来决策有参考价值
- 用 20% 的 token 保留 80% 的决策上下文
```

**原则 2: "最廉价动作优先"**
```
成本阶梯:
  零成本 → 内容替换 (Layer 1)
  零成本 → 消息裁剪 (Layer 2)
  零成本 → 结构压缩 (Layer 3)
  零成本 → 读时投影 (Layer 4)
  LLM 调用 → 语义压缩 (Layer 5)  ← 只在前面都不够时
```

**原则 3: "mostly-append" 持久化**
```
压缩不修改不删除之前的 transcript 行
只追加新的边界和摘要事件
保留的消息保持原始 parentUuids
读时通过边界元数据修补消息链
```

**原则 4: "缓存感知"**
```
Microcompact 缓存路径:
- 延迟边界消息到 API 响应之后
- 使用实际的 cache_deleted_input_tokens
- 不猜测，从响应中读取

缓存失效的代价管理:
- clear_at_least 确保每次清除量足够大
- 避免频繁小量清除导致 cache 不断失效
```

**原则 5: "上下文质量 > 数量"**
```
来自 Anthropic 文档:

"Context is a finite resource with diminishing returns —
 irrelevant content degrades model focus."

"More context isn't automatically better.
 As token count grows, accuracy and recall degrade
 (phenomenon known as 'context rot')."
```

#### 1.2.8 性能数据

| 指标 | 数值 | 来源 |
|------|------|------|
| 上下文编辑启用后性能提升 | **29%** | Anthropic 报告 |
| 清理代码对 Claude Code 的影响 | token 减少 **7-8%**，文件复查减少 **34%** | 对照实验 |
| Prompt cache 过期 | 不活跃 **5 分钟**后过期 | 论文 KAIROS 部分 |
| Fleet cache 成本（不复用路径） | **~0.76%** 的 fleet cache_creation | 2026 年 1 月实验 |
| 不复用路径 cache miss 率 | **98%** | 同上 |
| 典型恢复率 | **60-70%** 的上下文窗口 | 综合 |
| 95% 每步准确率下 100 步任务成功率 | **0.6%** | 引用研究 |

### 1.3 Helen 当前策略（单层）
```
超 80% → 立即选择一种策略压缩
├── summarize: 拼接 [role] content 文本（非 LLM 摘要）
├── truncate: 丢弃最旧消息，保留 5 条
└── none: 不处理（等 API 报错）
```

### 1.4 消息优先级对比

| 优先级 | Claude Code | Helen |
|--------|-------------|-------|
| 🟢 永不删除 | 系统提示、用户消息、助手文本、tool_use 块 | 系统消息 |
| 🟡 尽量保留 | 近期 tool_result、当前轮次 | 最近 5 条消息 |
| 🟠 可清除 | 旧 tool_result 内容 | — |
| 🔴 首先丢弃 | 过时轮次、旧思考块 | 最旧消息（无差别） |

### 1.5 关键差距总结

```
差距 1：缺少"行动 vs 数据"区分
  Helen 丢弃整条消息，包括 LLM 的决策记录
  Claude Code 保留 tool_use（做了什么），只丢 tool_result（返回了什么）

差距 2：缺少渐进式压缩
  Helen 一刀切，要么不压缩要么全压缩
  Claude Code 先试零成本方案，逐步升级到 LLM 压缩

差距 3：缺少 LLM 语义压缩
  Helen 的 "summarize" 只是文本拼接
  Claude Code 用 LLM 做真正的语义摘要

差距 4：缺少主动预警
  Helen 等到 80% 才反应
  Claude Code 在 70% 就开始轻量清理

差距 5：缺少选择性内容清除
  Helen 只能全部清除或全部保留
  Claude Code 可按类型选择性清除（工具结果、思考块等）
```

---

## 二、增强方案

### 2.1 Phase 1：消息分类与选择性清除（P0）

#### 核心思想：区分"行动"和"数据"

```
当前 Helen 消息类型：
  system / user / assistant / tool

增强为：
  system          → 永不删除
  user            → 高优先级保留
  assistant_text  → 助手文本回复，高优先级
  assistant_tools → 助手的工具调用决策（tool_use），高优先级 ⭐ 新增
  tool_result     → 工具返回数据，低优先级（可清除）⭐ 新增分类
```

#### 实现方案

```python
# history.py — 消息优先级

ROLE_PRIORITY = {
    "system": 100,          # 永不删除
    "user": 90,             # 高优先级
    "assistant_text": 80,   # 助手文本
    "assistant_tools": 70,  # 工具调用决策
    "tool_result": 20,      # 工具结果（可清除）
}

def microcompact(history, target_tokens):
    """Layer 3: 清除旧工具结果，保留动作历史"""
    # 1. 分离消息为 动作层 和 数据层
    actions = [m for m in history if m.role in ("assistant", "user", "system")
               and m.tool_calls]  # 有 tool_calls 的助手消息 = 动作
    data = [m for m in history if m.role == "tool"]  # 工具结果

    # 2. 保留最近的 N 个工具结果
    recent_results = data[-MIN_RECENT_TOOL_RESULTS:]
    old_results = data[:-MIN_RECENT_TOOL_RESULTS]

    # 3. 将旧工具结果替换为摘要指针
    for msg in old_results:
        msg.content = f"[工具结果已清除: {msg.tool_name} 调用于 turn {msg.turn_id}]"
        msg._compressed = True

    return history
```

#### Helen 代码层面的变化

```helen
// Agent 声明中可指定上下文策略
agent CodeReviewer {
    description "代码审查"
    model "qwen3.7-plus"
    max-turns 20
    context {
        compression "graduated"   // 新策略：渐进式
        max-tool-results 5        // 保留最近 5 个工具结果
        preserve-actions true     // 保留 tool_use 决策
    }
    tools ["read_file", "shell_exec"]
    main {
        let review = llm act "审查这段代码"
        return review
    }
}
```

### 2.2 Phase 2：渐进式压缩管线（P0）

#### 五级压缩触发

```
上下文使用率    阶段       动作
─────────────────────────────────────────────────
< 60%          正常       不处理
60%            预警       Layer 1: 大工具输出 → 引用指针
70%            清理       Layer 2: 丢弃过时轮次
80%            遮蔽       Layer 3: 清除旧工具结果（Microcompact）
90%            紧急       Layer 4: 归档 + 折叠视图
95%+           完全压缩   Layer 5: LLM 语义压缩（Auto-Compact）
```

#### 实现方案

```python
# history.py — 渐进式压缩

COMPRESSION_THRESHOLDS = {
    "budget_reduction": 0.60,   # 60% — 替换大输出
    "snip": 0.70,               # 70% — 丢弃过时轮次
    "microcompact": 0.80,       # 80% — 清除旧工具结果
    "context_collapse": 0.90,   # 90% — 归档折叠
    "auto_compact": 0.95,       # 95% — LLM 压缩
}

def graduated_compress(history, usage_ratio):
    """渐进式压缩 — cheapest move first"""

    if usage_ratio < 0.60:
        return history, "none"

    # Layer 1: 零成本 — 替换大工具输出
    if usage_ratio >= 0.60:
        history = budget_reduction(history)
        new_ratio = calculate_usage(history)
        if new_ratio < 0.70:
            return history, "budget_reduction"

    # Layer 2: 极低成本 — 丢弃过时轮次
    if usage_ratio >= 0.70:
        history = snip_stale_turns(history)
        new_ratio = calculate_usage(history)
        if new_ratio < 0.80:
            return history, "snip"

    # Layer 3: 低成本 — 清除旧工具结果
    if usage_ratio >= 0.80:
        history = microcompact(history)
        new_ratio = calculate_usage(history)
        if new_ratio < 0.90:
            return history, "microcompact"

    # Layer 4: 中等成本 — 归档折叠
    if usage_ratio >= 0.90:
        history = context_collapse(history)
        new_ratio = calculate_usage(history)
        if new_ratio < 0.95:
            return history, "context_collapse"

    # Layer 5: 高成本 — LLM 语义压缩
    history = auto_compact(history)  # 调用 LLM
    return history, "auto_compact"
```

#### 每层详细策略

```
Layer 1 — Budget Reduction（零成本）
  └─ 工具输出 > 4000 字符 → 替换为 "[read_file: 12KB, 前 200 字符...]"
  └─ 保留头部 + 尾部，中间用省略号
  └─ 效果: 通常减少 30-50% 工具输出体积

Layer 2 — Snip（极低成本）
  └─ 识别"过时"轮次：超过 N 轮前的工具调用+结果对
  └─ 保留最近的 8 个完整轮次
  └─ 丢弃更早的完整轮次（包括 user+assistant+tool）
  └─ 效果: 减少 20-40% 体积

Layer 3 — Microcompact（低成本）⭐ 最关键的创新
  └─ 保留所有 user/assistant 消息
  └─ 保留所有 tool_use 块（LLM 的决策记录）
  └─ 只清除旧 tool_result 的具体内容
  └─ 替换为 "[tool_result: read_file 'src/main.py', 234 行, 已清除]"
  └─ 效果: 减少 40-60% 体积，几乎不损失决策上下文

Layer 4 — Context Collapse（中等成本）
  └─ 将超过 20 轮的消息归档
  └─ 生成简单的结构化摘要（不用 LLM）
  └─ 格式: "[对话摘要] 共 N 轮，涉及文件: a.py, b.py, 关键决策: ..."
  └─ 效果: 减少 50-70% 体积

Layer 5 — Auto-Compact（高成本，LLM 调用）
  └─ 用 LLM 对完整历史做语义压缩
  └─ 提示: "将以下对话压缩为摘要，保留关键决策、文件修改、错误修复"
  └─ 效果: 减少 60-70% 体积，语义损失最小
```

### 2.3 Phase 3：LLM 语义压缩（P1）

#### 当前问题

Helen 的 `summarize` 模式不是真正的摘要，只是文本拼接：
```python
# 当前实现 — 只是把消息拼在一起
summary = "[user] 请帮我修改代码\n[assistant] 好的...\n[tool] 文件内容..."
```

这丢失了语义结构，LLM 无法从拼接文本中高效提取关键信息。

#### 增强方案

```python
async def llm_summarize(history, llm_runtime):
    """Layer 5: 使用 LLM 做语义压缩"""

    # 1. 构建压缩提示
    prompt = """请将以下对话历史压缩为结构化摘要。

保留：
- 用户的核心意图和目标
- 关键决策和结论
- 文件修改记录（路径 + 修改内容摘要）
- 错误和修复记录
- 重要的工具调用结果摘要

丢弃：
- 重复的试探性操作
- 中间过程的详细输出
- 已经过时的临时数据

输出格式：
## 任务目标
[用户想要做什么]

## 关键决策
[做出的重要选择和原因]

## 文件变更
- path/to/file.py: [修改了什么]

## 已完成
- [完成了什么]

## 待完成
- [还需要做什么]

## 注意事项
- [重要的约束、偏好、错误模式]

对话历史：
"""
    # 2. 格式化历史（只保留文本，不保留工具原始输出）
    for msg in history:
        if msg.role == "tool":
            prompt += f"[工具结果: {msg.tool_name}] {msg.content[:200]}...\n"
        else:
            prompt += f"[{msg.role}] {msg.content}\n"

    # 3. 调用 LLM
    response = await llm_runtime.act(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=0.3,  # 低温度 → 更忠实的摘要
    )

    # 4. 将摘要替换为单条系统消息
    return [Message(role="system", content=f"[对话摘要]\n{response.text}")]
```

#### 60% 规则

压缩后的下次压缩触发点：
```
压缩后上下文 = 30% 容量
下次压缩触发 = 30% + 60% × 70% = 72% 容量
```

这避免了"压缩后立即又需要压缩"的死循环。

### 2.4 Phase 4：上下文有效性提取（P1）

#### 核心问题

提交给 LLM 的上下文中，大量是无效或冗余的。如何提取有效上下文？

#### 方案：三通道上下文构建

```
┌────────────────────────────────────────────────┐
│           提交给 LLM 的上下文                   │
├────────────────────────────────────────────────┤
│                                                │
│  通道 1: 系统指令 (固定)                        │
│  ├── 框架指令 (工具使用规则、完成标准)           │
│  ├── 语言约定 (Helen 语法、最佳实践)            │
│  └── 技能索引 (可用技能列表)                    │
│                                                │
│  通道 2: 工作记忆 (动态，高优先级)              │
│  ├── 当前任务描述                               │
│  ├── 最近的对话轮次 (3-5 轮)                    │
│  ├── 当前打开/编辑的文件                        │
│  └── 待完成的 TODO                              │
│                                                │
│  通道 3: 长期记忆 (按需检索)                    │
│  ├── 对话摘要 (压缩后的历史)                    │
│  ├── 关键决策记录                               │
│  ├── 错误修复记录                               │
│  └── 用户偏好/约束                              │
│                                                │
│  Token 预算分配:                                │
│  通道 1: 15% (固定开销)                         │
│  通道 2: 50% (工作记忆)                         │
│  通道 3: 35% (长期记忆)                         │
│                                                │
└────────────────────────────────────────────────┘
```

#### 实现：Working Memory 机制

```python
@dataclass
class WorkingMemory:
    """工作记忆 — 当前任务的核心上下文"""
    task_description: str          # 当前任务
    active_files: list[str]        # 当前操作的文件
    recent_decisions: list[str]    # 最近的关键决策
    pending_todos: list[str]       # 待完成项
    error_history: list[dict]      # 最近的错误和修复

    def to_context(self) -> str:
        """将工作记忆格式化为上下文"""
        parts = ["## 当前任务", self.task_description]

        if self.active_files:
            parts.append("\n## 当前文件")
            parts.extend(f"- {f}" for f in self.active_files)

        if self.recent_decisions:
            parts.append("\n## 关键决策")
            parts.extend(f"- {d}" for d in self.recent_decisions[-5:])

        if self.pending_todos:
            parts.append("\n## 待完成")
            parts.extend(f"- [ ] {t}" for t in self.pending_todos)

        return "\n".join(parts)
```

#### 自动更新工作记忆

```python
def update_working_memory(memory, tool_call, tool_result):
    """每次工具调用后自动更新工作记忆"""

    if tool_call.name == "read_file":
        memory.active_files.append(tool_call.args["path"])
        memory.active_files = memory.active_files[-10:]  # 保留最近 10 个

    elif tool_call.name == "write_file" or tool_call.name == "patch_file":
        path = tool_call.args["path"]
        memory.recent_decisions.append(f"修改文件: {path}")

    elif tool_call.name == "shell_exec":
        if tool_result.exit_code != 0:
            memory.error_history.append({
                "command": tool_call.args["command"],
                "error": tool_result.output[:500],
            })
```

### 2.5 Phase 5：修复已知 Bug（P0）

#### Bug 1: clear_context() token 估算错误

```python
# 当前（错误）— Message 是 dataclass，没有 .get() 方法
total_chars = sum(len(msg.get("content", "")) for msg in _interpreter_history)

# 修复
total_tokens = sum(msg.token_count for msg in _interpreter_history)
```

#### Bug 2: compress_context() 类型错误

```python
# 当前（错误）— estimate_tokens 接受 str，但传入了 list[Message]
before_tokens = _interpreter_history_manager.estimate_tokens(_interpreter_history)

# 修复
before_tokens = sum(msg.token_count for msg in _interpreter_history)
```

---

## 三、实施优先级

### P0 — 立即实施（影响大，工作量小）

| 项目 | 工作量 | 效果 |
|------|--------|------|
| 修复 clear_context/compress_context Bug | 0.5 天 | 修复功能性缺陷 |
| 实现 Layer 3 Microcompact（清除旧工具结果） | 2 天 | 减少 40-60% 上下文体积 |
| 实现渐进式压缩触发（60/70/80/90/95%） | 2 天 | 避免突然大量丢失上下文 |

### P1 — 短期实施（影响大，工作量中等）

| 项目 | 工作量 | 效果 |
|------|--------|------|
| LLM 语义压缩（Auto-Compact） | 3 天 | 真正的语义保留压缩 |
| Working Memory 机制 | 3 天 | 自动维护有效上下文 |
| Agent 级别 context 配置 | 2 天 | 每个 Agent 可独立配置压缩策略 |

### P2 — 中期实施（影响中等，工作量大）

| 项目 | 工作量 | 效果 |
|------|--------|------|
| 上下文编辑 API（选择性清除） | 3 天 | 精细控制上下文内容 |
| 嵌入向量检索历史 | 5 天 | 语义搜索相关历史上下文 |
| 工具 Schema Token 计数 | 1 天 | 更准确的预算计算 |

---

## 四、代码示例：增强后的上下文管理

### 4.1 Agent 声明中的上下文配置

```helen
agent LongRunningCoder {
    description "长时间运行的编码 Agent"
    model "qwen3.7-plus"
    max-turns 50

    // 新的上下文配置块
    context {
        strategy "graduated"          // 渐进式压缩
        budget-ratio 0.80             // 历史占上下文窗口的 80%
        preserve-actions true         // 保留 tool_use 决策
        max-tool-results 5            // 保留最近 5 个工具结果
        microcompact-threshold 0.80   // 80% 时开始清除旧结果
        auto-compact-threshold 0.95   // 95% 时 LLM 压缩
        working-memory true           // 启用工作记忆
    }

    tools ["read_file", "write_file", "patch_file", "shell_exec", "find_files"]

    main {
        // 上下文管理对 Agent 透明
        // 系统自动在后台做渐进式压缩
        let result = llm act "实现这个功能"
        return result
    }
}
```

### 4.2 手动上下文控制

```helen
// 清除无用上下文（保留工作记忆）
let status = clear_context(keep="working_memory")
// → {"status": "ok", "cleared_tokens": 15000, "kept_tokens": 2000}

// 选择性压缩（只压缩工具结果）
let status = compress_context(target="tool_results")
// → {"status": "ok", "compressed": 8, "saved_tokens": 12000}

// 提取有效上下文
let summary = extract_context()
// → {"task": "...", "decisions": [...], "active_files": [...], "pending": [...]}

// 手动触发 LLM 压缩
let result = compress_context("llm_summarize")
// → {"status": "ok", "original_tokens": 50000, "compressed_tokens": 8000}
```

### 4.3 上下文有效性分析

```helen
// REPL 中查看上下文分析
:stats detailed

// 输出：
// ╭──────────────────────────────────────────╮
// │ 上下文分析                                │
// ├──────────────────────────────────────────┤
// │ 总 Tokens:    45,200 / 131,072 (34.5%)  │
// │ 压缩阶段:     microcompact (Layer 3)     │
// │                                          │
// │ 有效性分布:                               │
// │   系统指令:    6,800 (15.0%) [固定]       │
// │   工作记忆:   22,600 (50.0%) [活跃]       │
// │   长期记忆:   15,800 (35.0%) [摘要]       │
// │                                          │
// │ 消息分类:                                 │
// │   用户消息:    12 条 (8,500 tokens)       │
// │   助手文本:    15 条 (12,000 tokens)      │
// │   工具决策:    23 条 (6,200 tokens)  ⭐   │
// │   工具结果:    23 条 (18,500 tokens)      │
// │     已压缩:    18 条 (12,000 tokens)      │
// │     未压缩:     5 条 (6,500 tokens)       │
// │                                          │
// │ 工作记忆:                                  │
// │   活跃文件:    src/main.py, src/utils.py  │
// │   待完成:      3 项                       │
// │   最近错误:    0                          │
// ╰──────────────────────────────────────────╯
```

---

## 五、与 Claude Code 关键差异的弥合

| Claude Code 特性 | Helen 现状 | 弥合方案 | 优先级 |
|-----------------|-----------|----------|--------|
| 5 层渐进压缩 | 1 层 | Phase 2: 渐进式压缩管线 | P0 |
| Microcompact（保留动作，清除数据） | 无 | Phase 1: 消息分类 + 选择性清除 | P0 |
| LLM 语义压缩 | 无（只是文本拼接） | Phase 3: Auto-Compact | P1 |
| 70/80/90/95% 阈值 | 80% 单一阈值 | Phase 2: 渐进式触发 | P0 |
| 工具结果选择性清除 | 截断到 16K | Phase 1: Microcompact | P0 |
| Context Editing API | 无 | Phase 4+: 选择性清除 API | P2 |
| 工作记忆 | 无 | Phase 4: WorkingMemory | P1 |
| 缓存友好压缩 | 无 | 长期：部分策略保持缓存 | P3 |

---

## 六、预期效果

### 压缩效果预估

```
场景：50 轮对话，大量工具调用

当前 Helen：
  原始: 200K tokens
  80% 触发 → 粗暴截断 → 50K tokens
  信息损失: ~75%（包括关键决策）

增强后 Helen：
  原始: 200K tokens
  60% → Layer 1 大输出替换 → 160K (减少 20%)
  70% → Layer 2 过时轮次丢弃 → 130K (减少 35%)
  80% → Layer 3 Microcompact → 80K (减少 60%)
         保留所有 tool_use 决策
         只清除旧 tool_result 内容
  95% → Layer 5 LLM 压缩 → 40K (减少 80%)
         语义摘要保留关键信息
  信息损失: ~20%（主要丢失工具原始输出）
```

### 关键指标

| 指标 | 当前 | 增强后 | 改善 |
|------|------|--------|------|
| 上下文恢复率 | 60-70%（粗暴截断） | 60-70%（语义保留） | 质量提升 |
| 信息损失 | ~75%（包括决策） | ~20%（仅原始输出） | 3.75x |
| 压缩触发平滑度 | 突变（80% 一刀切） | 渐进（5 级平滑过渡） | 显著提升 |
| LLM 可用上下文质量 | 中（拼接文本） | 高（结构化摘要） | 显著提升 |
