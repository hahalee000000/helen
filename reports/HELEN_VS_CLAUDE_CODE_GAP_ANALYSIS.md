# Helen vs Claude Code 上下文管理差距分析

> **日期**: 2026-07-07  
> **版本**: Helen v1.15 (最新)  
> **参考**: 
> - `wiki/reference/claude-code-context-management.md`
> - `wiki/runtime/context-management.md`
> - `wiki/runtime/context-compression-research.md`

---

## 概述

Helen v1.15 通过 Phase 1-7 实施了完整的上下文管理增强，已对齐 Claude Code 的核心功能。最新改进（2026-07-07）进一步缩小了差距：

**最新改进**:
- ✅ Layer 5 Auto-Compact 集成 LLM 语义摘要（对齐 Claude Code）
- ✅ Context Collapse 改进为时间线保留（借鉴 RCC、CogCanvas）
- ✅ WorkingMemory 改为 token 级淘汰（更精确的预算控制）

仍存在一些差距，特别是在服务端编辑、反应式压缩、持久化设计等方面。

---

## 已实现的功能（对齐度 100%）

### ✅ 五层渐进压缩管线

| 层级 | Claude Code | Helen v1.15 | 状态 |
|------|------------|-------------|------|
| Layer 1: Budget Reduction | ✅ 零成本，总是启用 | ✅ 零成本，总是启用 | 完全对齐 |
| Layer 2: Snip | ✅ 零成本，feature flag | ✅ 零成本，保留最近 8 轮 | 完全对齐 |
| Layer 3: Microcompact | ✅ 零成本，保留 tool_use 决策 | ✅ 零成本，保留 tool_use 决策 ⭐ | 完全对齐 |
| Layer 4: Context Collapse | ✅ 零成本，纯读时投影 | ✅ 零成本，**时间线视图** 🆕 | **超越**（借鉴 RCC/CogCanvas）|
| Layer 5: Auto-Compact | ✅ LLM 调用，最后手段 | ✅ **LLM 语义摘要** 🆕 | 完全对齐 |

**Layer 4 改进详情**:
- Helen 现在将旧消息分段（每 10 条一块），生成时间线视图
- 每段提取：时间标记、文件引用、工具使用、用户意图
- 保留任务进展的时序结构（借鉴 CogCanvas 的认知工件思想）
- Claude Code 的 Context Collapse 是纯读时投影，Helen 实现了类似效果

**Layer 5 改进详情**:
- Helen 现在通过 `llm_client` 参数可选启用 LLM 语义摘要
- 调用 `LLMSummarizer` 生成高质量摘要（任务目标、关键决策、文件变更）
- LLM 不可用时回退到零成本结构摘要
- 完全对齐 Claude Code 的 `compactConversation()` 机制

### ✅ 缓存感知压缩

| 特性 | Claude Code | Helen v1.15 | 状态 |
|------|------------|-------------|------|
| 稳定前缀 (30%) | ✅ | ✅ | 完全对齐 |
| 批量阈值 (75%) | ✅ | ✅ | 完全对齐 |
| 仅后缀修改 | ✅ | ✅ | 完全对齐 |
| 缓存边界标记 | ✅ | ✅ | 完全对齐 |
| 缓存感知 Microcompact | ✅ `CACHED_MICROCOMPACT` flag | ✅ cache_aware_enabled | 完全对齐 |

### ✅ 工作记忆

| 特性 | Claude Code | Helen v1.15 | 状态 |
|------|------------|-------------|------|
| 活跃文件跟踪 | ✅ | ✅ | 完全对齐 |
| 最近决策提取 | ✅ | ✅ | 完全对齐 |
| 待办事项提取 | ✅ | ✅ | 完全对齐 |
| 错误历史 | ✅ | ✅ | 完全对齐 |
| **Token 级淘汰** 🆕 | ✅ (推断) | ✅ `_evict_to_budget()` | 完全对齐 |

**Token 级淘汰详情**:
- 每次添加条目后检查 token 预算
- 超出 `max_tokens` 时按优先级淘汰最旧条目
- 淘汰顺序：TODOs > Decisions > Files > Errors
- `task_description` 永不淘汰（最高优先级）

### ✅ Agent 集成

| 特性 | Claude Code | Helen v1.15 | 状态 |
|------|------------|-------------|------|
| 每 agent 独立配置 | ✅ | ✅ `context {}` 块 | 完全对齐 |
| 三通道上下文 | ✅ | ✅ System 15% + WM 50% + History 35% | 完全对齐 |
| 自动应用压缩 | ✅ | ✅ `prepare_context()` | 完全对齐 |
| Channel 2 预算截断 | ✅ (推断) | ✅ `to_context(budget_chars)` | 完全对齐 |

---

## 未实现的功能（差距）

### ⏸️ 1. Context Editing API（服务端编辑）- 暂不考虑

**Claude Code 实现**:
- 服务端 Context Editing API（Beta: `context-management-2025-06-27`）
- 三种策略：
  1. `clear_tool_uses_20250919` - 工具结果清除
  2. `clear_thinking_20251015` - 思考块清除
  3. `compact_20260112` - 服务端压缩

**Helen 现状**:
- ❌ 无服务端编辑能力
- ❌ 所有压缩在客户端完成
- ❌ 无法利用 API 侧的优化

**暂不考虑原因**:
- 🔒 **强依赖 Anthropic API**: 该功能是 Anthropic 专有 Beta API，仅限 Claude 模型使用
- 🚫 **不支持多模型**: Helen 支持多种 LLM 提供商（OpenAI、阿里云等），无法统一实现
- 💡 **替代方案已存在**: Helen 已通过客户端五层渐进压缩实现类似效果
- 📊 **成本效益不明**: 服务端编辑的成本节省需要大量调用才能体现，当前阶段优先级低

**替代方案**:
- ✅ 五层渐进压缩（Layer 1-5）已提供完整的客户端压缩能力
- ✅ Layer 3 Microcompact 保留工具决策，与 `clear_tool_uses` 效果类似
- ✅ Layer 5 Auto-Compact 使用 LLM 语义摘要，质量更高

**状态**: ⏸️ **暂不考虑**（等待行业标准或多模型支持方案）

---

### ❌ 2. Context Awareness（上下文感知）

**Claude Code 实现**:
```xml
<!-- 系统提示中的预算标签 -->
<budget:token_budget>200000</budget:token_budget>

<!-- 每次工具调用后的更新 -->
<system_warning>Token usage: 35000/200000; 165000 remaining</system_warning>
```

**Helen 现状**:
- ❌ 不自动注入 token 预算标签
- ❌ 模型不知道剩余容量
- ❌ 无法在工具调用时更新使用情况

**差距影响**:
- LLM 不知道上下文使用情况
- 无法主动避免超出限制
- 无法优化 token 使用

**实施建议**:
```python
# 在 system prompt 中注入
def build_system_prompt_with_budget(base_prompt, max_tokens):
    budget_tag = f"<budget:token_budget>{max_tokens}</budget:token_budget>"
    return f"{budget_tag}\n\n{base_prompt}"

# 在工具调用后注入更新
def inject_usage_warning(usage_ratio, remaining_tokens):
    return f"<system_warning>Token usage: {int(usage_ratio*100)}%; {remaining_tokens} remaining</system_warning>"
```

**优先级**: 🟡 **中**（改善 LLM 行为）

---

### ❌ 3. Reactive Compaction（反应式压缩）

**Claude Code 实现**:
```python
# 在轮次执行期间，上下文接近容量上限时触发
if feature("REACTIVE_COMPACT"):
    if context_approaches_capacity():
        reactive_compact()  # 只摘要刚好够释放空间的内容
        hasAttemptedReactiveCompact = True  # 每轮最多触发一次
```

**Helen 现状**:
- ❌ 无反应式压缩
- ❌ 无法在轮次执行期间动态压缩
- ❌ 只能在轮次结束后压缩

**差距影响**:
- 长轮次可能超出上下文限制
- 无法及时释放空间
- 用户体验差（可能报错）

#### 候选摘要算法分析

Helen 当前已有两个可复用的压缩算法（`helen/runtime/graduated_compression.py`）：

| 算法 | 位置 | 成本 | 质量 | 特点 |
|------|------|------|------|------|
| **Context Collapse (Layer 4)** | `_context_collapse()` | 🟢 零成本 | 中 | 结构化提取：文件引用/工具使用/用户意图，时间线分块（每10条一块） |
| **Auto-Compact (Layer 5)** | `LLMSummarizer.summarize()` | 🔴 LLM 调用 | 高 | 语义摘要：保留任务目标/决策/变更，生成结构化 markdown |

**Reactive Compaction 可复用的算法方案**:

**方案 A: 复用 Context Collapse 的零成本结构化提取（推荐）** ✅
```python
# 复用 _summarize_block() + _extract_global_stats()
# 优势：零延迟，适合轮次中紧急触发
# 策略：对最旧的 N 条消息做结构化分块摘要，只释放刚好够的空间
def reactive_compact_structural(messages, target_usage):
    # 从前往后分块，每块10条，做结构化提取
    # 直到 token 使用降到 target_usage 以下
    ...
```

**方案 B: 复用 Auto-Compact 的 LLM 语义摘要**
```python
# 复用 LLMSummarizer.summarize()
# 优势：摘要质量高，保留语义连贯性
# 劣势：轮次中增加 LLM 调用延迟和成本
def reactive_compact_semantic(messages, target_usage):
    summarizer = LLMSummarizer(llm_client)
    summary = summarizer.summarize(messages_to_compress)
    ...
```

**方案 C: 混合分层策略（最优）** 🌟
```python
# 轮次内首次触发：用零成本结构化提取（快速释放空间）
# 轮次结束或空间仍紧张时：升级为 LLM 语义摘要（提升质量）
class ReactiveCompactor:
    def check_and_compact(self, messages, max_tokens):
        usage = calculate_usage(messages, max_tokens)
        if usage > 0.90 and not self.attempted_this_turn:
            # 方案 A: 快速结构化压缩（零延迟）
            compressed = self._structural_compact(messages, target=usage - 0.10)
            self.attempted_this_turn = True
            return compressed
        elif usage > 0.95:
            # 方案 B: 升级为 LLM 语义压缩（更彻底）
            return self._semantic_compact(messages, target=usage - 0.30)
        return messages
```

**推荐**: 方案 C（混合分层），因为：
- 轮次中需要**低延迟**（结构化提取 < 1ms vs LLM 调用 > 1s）
- 轮次后可以**提升质量**（用 LLM 做更彻底的语义压缩）
- 两者算法代码**都已实现**（`_context_collapse` 和 `LLMSummarizer`），无需重写

---

### ❌ 4. Prompt-too-long 恢复级联

**Claude Code 实现**:
```
步骤 1: 尝试 context-collapse overflow recovery
步骤 2: 如果失败 → 尝试 reactive compaction
步骤 3: 如果仍失败 → 终止，reason: 'prompt_too_long'
```

**Helen 现状**:
- ❌ 无恢复级联
- ❌ API 返回 `prompt_too_long` 时直接报错
- ❌ 无法自动恢复

**差距影响**:
- API 错误处理不优雅
- 用户体验差
- 需要手动干预

**实施建议**:
```python
class PromptTooLongRecovery:
    def recover(self, error, messages, max_tokens):
        # 步骤 1: Context Collapse 恢复
        try:
            recovered = context_collapse_overflow_recovery(messages)
            return recovered, "context_collapse"
        except:
            pass
        
        # 步骤 2: Reactive Compaction
        try:
            recovered = reactive_compact(messages)
            return recovered, "reactive"
        except:
            pass
        
        # 步骤 3: 终止
        raise PromptTooLongError("Cannot recover from prompt_too_long")
```

**优先级**: 🟠 **中高**（提高鲁棒性）

---

### ❌ 5. mostly-append 持久化

**Claude Code 实现**:
```python
# 压缩不修改不删除之前的 transcript 行
# 只追加新的边界和摘要事件
# 保留的消息保持原始 parentUuids
# 读时通过边界元数据修补消息链

boundary_marker.metadata = {
    "headUuid": "...",
    "anchorUuid": "...",
    "tailUuid": "...",
}
```

**Helen 现状**:
- ❌ 压缩会修改底层消息数组
- ❌ 无 UUID 链修补
- ❌ 无法恢复原始历史
- ❌ 无法跨轮次持久化折叠

**差距影响**:
- 丢失原始历史
- 无法审计压缩过程
- 无法恢复特定版本

**实施建议**:
```python
class MostlyAppendPersister:
    def __init__(self):
        self.transcript = []  # 永不修改
        self.collapse_store = {}  # 折叠视图
    
    def append(self, message):
        """只追加，不修改"""
        message.uuid = generate_uuid()
        self.transcript.append(message)
    
    def compress(self, messages_to_compress, summary):
        """压缩时只追加边界标记"""
        boundary = BoundaryMarker(
            head_uuid=messages_to_compress[0].uuid,
            tail_uuid=messages_to_compress[-1].uuid,
            summary=summary,
        )
        self.transcript.append(boundary)
        self.collapse_store[boundary.anchor_uuid] = summary
    
    def read_view(self):
        """读时通过边界元数据修补消息链"""
        view = []
        for item in self.transcript:
            if isinstance(item, BoundaryMarker):
                # 跳过被压缩的消息，添加摘要
                view.append(Message(role="system", content=item.summary))
            else:
                view.append(item)
        return view
```

**优先级**: 🟡 **中**（提高可审计性）

---

## 优先级排序

| 优先级 | 功能 | 影响 | 实施难度 | 状态 |
|--------|------|------|---------|------|
| ⏸️ **暂不考虑** | Context Editing API | 成本、性能 | 中 | Anthropic 专有 |
| ✅ **已实现** | Prompt-too-long 恢复 | 鲁棒性 | 低 | Phase 8 ✅ |
| ✅ **已实现** | Context Awareness | LLM 行为 | 低 | Phase 9A ✅ |
| ✅ **已实现** | Reactive Compaction | 稳定性 | 中 | Phase 9B ✅ |
| ✅ **已实现** | mostly-append 持久化 | 可审计性 | 高 | Phase 10 ✅ |

**已实现（不再列为差距）**:
- ✅ "行动 > 数据"区分 — Layer 3 Microcompact 已实现
- ✅ Layer 5 LLM 语义摘要 — 已集成 LLMSummarizer
- ✅ Context Collapse 时间线保留 — 借鉴 RCC/CogCanvas
- ✅ WorkingMemory token 级淘汰 — `_evict_to_budget()`
- ✅ Prompt-too-long 恢复级联 — `PromptTooLongRecovery` (Phase 8)
- ✅ Context Awareness 上下文感知 — `ContextAwareness` + budget tag + usage warning (Phase 9A)
- ✅ Reactive Compaction 反应式压缩 — `ReactiveCompactor` 混合分层策略 (Phase 9B)
- ✅ Mostly-append 持久化 — `TranscriptStore` + `BoundaryMarker` + Message UUID (Phase 10)

**暂不考虑**:
- ⏸️ Context Editing API — Anthropic 专有 Beta API，Helen 已用客户端五层压缩替代

---

## 实施路线图（Phase 8-10 全部完成 ✅）

### Phase 8: 恢复机制 ✅

**目标**: 提高鲁棒性

**实现**:
1. ✅ 新建 `helen/runtime/context_recovery.py` — `PromptTooLongRecovery` 类，4 步恢复级联
2. ✅ 集成到 `http_llm.py` sync 和 stream 路径
3. ✅ 新增 `PromptTooLongError(LLMError)` 异常类型
4. ✅ 测试 `tests/runtime/test_context_recovery.py`

**效果**:
- 恢复级联：Context Collapse → Reactive Structural → Reactive Semantic → Aggressive Trim
- 同步和流式路径均集成
- 每次恢复记录 tokens 减少量

### Phase 9A: Context Awareness ✅

**目标**: 提高 LLM 上下文感知

**实现**:
1. ✅ 新建 `helen/runtime/context_awareness.py` — `ContextAwareness` 类
2. ✅ `AgentContextManager.prepare_context()` 注入 `<budget:token_budget>` 标签
3. ✅ `http_llm.py` 工具循环注入 `<system_warning>` 使用警告（4 级：normal/warning/critical/emergency）
4. ✅ 测试 `tests/runtime/test_context_awareness.py`

**效果**:
- LLM 知道 context window 限制
- 工具调用后根据使用率注入警告（50%/75%/90% 阈值）
- 4 级警告影响 LLM 行为

### Phase 9B: Reactive Compaction ✅

**目标**: 提高轮次中稳定性

**实现**:
1. ✅ 新建 `helen/runtime/reactive_compaction.py` — `ReactiveCompactor` 类
2. ✅ 混合分层策略：90% 阈值零成本结构化提取，95% 阈值 LLM 语义压缩
3. ✅ 每轮最多触发 1 次（避免压缩循环）
4. ✅ 集成到 `http_llm.py` 所有 4 个工具循环（sync/stream/async/async_stream）
5. ✅ 测试 `tests/runtime/test_reactive_compaction.py`

**效果**:
- 轮次中动态压缩，避免 context overflow
- 零延迟的结构化提取（< 1ms） + 高质量 LLM 语义压缩（可选）
- 与现有 graduated compression 共享算法

### Phase 10: Mostly-append 持久化 ✅

**目标**: 实现可审计的压缩历史

**实现**:
1. ✅ 新建 `helen/runtime/transcript_store.py` — `TranscriptStore` + `BoundaryMarker`
2. ✅ `Message` dataclass 新增可选 `uuid` 字段（向后兼容）
3. ✅ `AgentContextManager` 新增 `transcript_store_enabled` 参数
4. ✅ 压缩事件记录为 `BoundaryMarker`（不修改原始消息）
5. ✅ 序列化/反序列化支持完整审计追踪
6. ✅ 测试 `tests/runtime/test_transcript_store.py`

**效果**:
- Append-only 历史存储，可完整审计
- 压缩事件保留原始消息 + 边界标记
- `read_view()` 重建当前有效视图
- UUID 链接支持历史追踪

**总测试数**: 2660+ (新增 ~70 个测试)

### Phase 9: 感知与稳定 (2 周)

**目标**: 提高 LLM 感知和稳定性

**任务**:
1. 实现 `ContextAwareness` 类
2. 实现 `ReactiveCompactor` 类
3. 集成到执行流程
4. 添加监控

**预期效果**:
- LLM 知道上下文使用情况
- 长轮次更稳定

### Phase 10: 持久化 (3-4 周)

**目标**: 实现 mostly-append 持久化

**任务**:
1. 实现 `MostlyAppendPersister` 类
2. 重构历史存储
3. 实现 UUID 链修补
4. 添加审计日志

**预期效果**:
- 可审计的压缩过程
- 可恢复的历史

---

## 总结

### 当前对齐度（2026-07-07 更新）

| 类别 | 对齐度 | 说明 |
|------|--------|------|
| 渐进压缩 | **100%+** | Phase 2-5 + Layer 5 LLM 集成 + Context Collapse 时间线 |
| 缓存感知 | 100% | Phase 6 |
| 工作记忆 | **100%+** | Phase 1 + token 级淘汰 |
| Agent 集成 | 100% | Phase 7 + Channel 2 预算截断 |
| 恢复机制 | **100%** | Phase 8 — 4 步恢复级联 |
| 上下文感知 | **100%** | Phase 9A — budget tag + usage warning |
| 反应式压缩 | **100%** | Phase 9B — 混合分层策略 |
| 持久化 | **100%** | Phase 10 — append-only transcript |
| **总体** | **100%** | **所有差距已关闭**（Context Editing API 暂不考虑） |

### 剩余差距

| 类别 | 差距数 | 优先级 |
|------|--------|--------|
| **总计** | **0** | **所有差距已关闭** ✅ |

**暂不考虑**:
- ⏸️ Context Editing API — Anthropic 专有 Beta API，Helen 已用客户端五层压缩替代

### 最新改进（2026-07-07 Phase 8-10）

1. **Prompt-too-long 恢复级联** — `PromptTooLongRecovery` 4 步级联（Context Collapse → Structural → Semantic → Aggressive Trim）
2. **Context Awareness 上下文感知** — `<budget:token_budget>` + `<system_warning>` 4 级警告
3. **Reactive Compaction 反应式压缩** — `ReactiveCompactor` 混合分层策略（90% 结构化 + 95% 语义）
4. **Mostly-append 持久化** — `TranscriptStore` + `BoundaryMarker` + Message UUID
5. **PromptTooLongError** — 新增异常类型（继承 `LLMError`）

### 建议

**所有 Phase 8-10 已完成实现** ✅

1. **Context Editing API 暂不考虑** - 待 Anthropic API 开放或出现跨模型方案时再评估
2. **未来可扩展** - 将压缩事件接入 observability 系统（`ObservabilityManager.compression_events`）
3. **未来可扩展** - REPL 命令 `:compression_log` 展示压缩历史（基于 TranscriptStore 审计）

**实现状态**:
- ✅ Phase 8: Prompt-too-long 恢复级联
- ✅ Phase 9A: Context Awareness 上下文感知
- ✅ Phase 9B: Reactive Compaction 反应式压缩
- ✅ Phase 10: Mostly-append 持久化
- ⏸️ Context Editing API（暂不考虑）

---

**最后更新**: 2026-07-07 (Phase 8-10 完成)
**版本**: Helen v1.15 (最新)
