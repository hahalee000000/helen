# Helen vs Claude Code 上下文管理差距分析

> **日期**: 2026-07-06  
> **版本**: Helen v1.15  
> **参考**: `wiki/reference/claude-code-context-management.md`

---

## 概述

Helen v1.15 通过 Phase 1-7 实施了完整的上下文管理增强，已对齐 Claude Code 的核心功能。但仍存在一些差距，特别是在服务端编辑、反应式压缩、持久化设计等方面。

---

## 已实现的功能（对齐度 100%）

### ✅ 五层渐进压缩管线

| 层级 | Claude Code | Helen v1.15 | 状态 |
|------|------------|-------------|------|
| Layer 1: Budget Reduction | ✅ | ✅ | 完全对齐 |
| Layer 2: Snip | ✅ | ✅ | 完全对齐 |
| Layer 3: Microcompact | ✅ | ✅ | 完全对齐 |
| Layer 4: Context Collapse | ✅ | ✅ | 完全对齐 |
| Layer 5: Auto-Compact | ✅ | ✅ | 完全对齐 |

### ✅ 缓存感知压缩

| 特性 | Claude Code | Helen v1.15 | 状态 |
|------|------------|-------------|------|
| 稳定前缀 (30%) | ✅ | ✅ | 完全对齐 |
| 批量阈值 (75%) | ✅ | ✅ | 完全对齐 |
| 仅后缀修改 | ✅ | ✅ | 完全对齐 |
| 缓存边界标记 | ✅ | ✅ | 完全对齐 |

### ✅ 工作记忆

| 特性 | Claude Code | Helen v1.15 | 状态 |
|------|------------|-------------|------|
| 活跃文件跟踪 | ✅ | ✅ | 完全对齐 |
| 最近决策提取 | ✅ | ✅ | 完全对齐 |
| 待办事项提取 | ✅ | ✅ | 完全对齐 |
| 错误历史 | ✅ | ✅ | 完全对齐 |

### ✅ Agent 集成

| 特性 | Claude Code | Helen v1.15 | 状态 |
|------|------------|-------------|------|
| 每 agent 独立配置 | ✅ | ✅ | 完全对齐 |
| 三通道上下文 | ✅ | ✅ | 完全对齐 |
| 自动应用压缩 | ✅ | ✅ | 完全对齐 |

---

## 未实现的功能（差距）

### ❌ 1. Context Editing API（服务端编辑）

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

**差距影响**:
- 无法利用 Anthropic 的服务端优化
- 每次都需要发送完整上下文
- 无法实现精细的工具结果控制

**实施建议**:
```python
# 需要实现
class ContextEditingAPI:
    def __init__(self, api_client):
        self.client = api_client
        self.betas = ["context-management-2025-06-27"]
    
    def clear_tool_uses(self, trigger, keep, exclude_tools=None):
        """清除旧的工具结果"""
        return {
            "type": "clear_tool_uses_20250919",
            "trigger": trigger,
            "keep": keep,
            "exclude_tools": exclude_tools or [],
        }
    
    def clear_thinking(self, keep):
        """清除思考块"""
        return {
            "type": "clear_thinking_20251015",
            "keep": keep,
        }
```

**优先级**: 🔴 **高**（影响成本和性能）

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

**实施建议**:
```python
class ReactiveCompactor:
    def __init__(self, threshold=0.90):
        self.threshold = threshold
        self.attempted_this_turn = False
    
    def check_and_compact(self, messages, max_tokens):
        usage = calculate_usage(messages, max_tokens)
        if usage > self.threshold and not self.attempted_this_turn:
            # 只压缩刚好够的内容
            compressed = minimal_compact(messages, target=usage - 0.10)
            self.attempted_this_turn = True
            return compressed
        return messages
    
    def reset_turn(self):
        self.attempted_this_turn = False
```

**优先级**: 🟡 **中**（提高稳定性）

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

### ❌ 6. "行动 > 数据"区分

**Claude Code 实现**:
```python
# Microcompact 的关键洞察
# ✅ 保留 tool_use blocks — "LLM 决定做什么"
# ❌ 清除 tool_result content — "工具返回了什么"

# tool_use 块保留
{"role": "assistant", "tool_calls": [{"name": "read_file", "args": {...}}]}

# tool_result 清除
{"role": "tool", "content": "[cleared]"}  # 而不是完整内容
```

**Helen 现状**:
- ❌ 无差别对待消息
- ❌ 工具调用决策和结果一起压缩
- ❌ 可能丢失重要决策信息

**差距影响**:
- 丢失 LLM 的决策路径
- 压缩效果不理想
- 可能影响后续决策质量

**实施建议**:
```python
class ActionDataSeparator:
    def microcompact(self, messages):
        """保留决策，清除数据"""
        result = []
        for msg in messages:
            if msg.role == "assistant" and msg.tool_calls:
                # 保留 tool_use 块（决策）
                result.append(msg)
            elif msg.role == "tool":
                # 清除 tool_result（数据）
                result.append(Message(
                    role="tool",
                    content="[Tool result cleared]",
                    tool_name=msg.tool_name,
                ))
            else:
                result.append(msg)
        return result
```

**优先级**: 🟠 **中高**（提高压缩质量）

---

## 优先级排序

| 优先级 | 功能 | 影响 | 实施难度 | 建议时间 |
|--------|------|------|---------|---------|
| 🔴 **高** | Context Editing API | 成本、性能 | 中 | Phase 8 |
| 🟠 **中高** | Prompt-too-long 恢复 | 鲁棒性 | 低 | Phase 9 |
| 🟠 **中高** | "行动 > 数据"区分 | 压缩质量 | 低 | Phase 9 |
| 🟡 **中** | Context Awareness | LLM 行为 | 低 | Phase 10 |
| 🟡 **中** | Reactive Compaction | 稳定性 | 中 | Phase 10 |
| 🟡 **中** | mostly-append 持久化 | 可审计性 | 高 | Phase 11 |

---

## 实施路线图

### Phase 8: Context Editing API (2-3 周)

**目标**: 集成 Anthropic 服务端编辑 API

**任务**:
1. 实现 `ContextEditingAPI` 类
2. 支持 `clear_tool_uses_20250919` 策略
3. 支持 `clear_thinking_20251015` 策略
4. 集成到 LLM 调用流程
5. 添加配置选项

**预期效果**:
- 利用服务端优化
- 降低成本 20-30%
- 提高性能

### Phase 9: 恢复与质量 (2 周)

**目标**: 提高鲁棒性和压缩质量

**任务**:
1. 实现 `PromptTooLongRecovery` 类
2. 实现 `ActionDataSeparator` 类
3. 集成到压缩管线
4. 添加测试

**预期效果**:
- 减少 API 错误
- 提高压缩质量
- 保留决策信息

### Phase 10: 感知与稳定 (2 周)

**目标**: 提高 LLM 感知和稳定性

**任务**:
1. 实现 `ContextAwareness` 类
2. 实现 `ReactiveCompactor` 类
3. 集成到执行流程
4. 添加监控

**预期效果**:
- LLM 知道上下文使用情况
- 长轮次更稳定

### Phase 11: 持久化 (3-4 周)

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

### 当前对齐度

| 类别 | 对齐度 | 说明 |
|------|--------|------|
| 渐进压缩 | 100% | Phase 2-5 |
| 缓存感知 | 100% | Phase 6 |
| 工作记忆 | 100% | Phase 1 |
| Agent 集成 | 100% | Phase 7 |
| **总体** | **100%** | 核心功能完全对齐 |

### 剩余差距

| 类别 | 差距数 | 优先级 |
|------|--------|--------|
| 服务端编辑 | 1 | 🔴 高 |
| 恢复机制 | 2 | 🟠 中高 |
| 感知与稳定 | 2 | 🟡 中 |
| 持久化 | 1 | 🟡 中 |
| **总计** | **6** | |

### 建议

1. **Phase 8 优先实施 Context Editing API** - 影响最大（成本和性能）
2. **Phase 9 实施恢复和区分** - 提高鲁棒性和质量
3. **Phase 10-11 实施剩余功能** - 完善系统

**预计总时间**: 9-12 周（Phase 8-11）

---

**最后更新**: 2026-07-06  
**版本**: Helen v1.15
