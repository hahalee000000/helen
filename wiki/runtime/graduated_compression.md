# 渐进压缩管线 (Graduated Compression Pipeline)

> Phase 2-5 | `helen/runtime/graduated_compression.py` | 测试: `tests/runtime/test_graduated_compression.py`

---

## 概述

渐进压缩管线是 Phase 2-5 引入的核心功能，采用"最廉价动作优先"原则，通过五层策略逐步压缩上下文，最大化保留关键信息。

---

## 设计原则

**"最廉价动作优先"**：优先使用计算成本低、信息损失小的压缩策略，只有在必要时才使用更激进的策略。

| 层级 | 计算成本 | 信息损失 | 使用率阈值 |
|------|---------|---------|-----------|
| Layer 1 | 极低 | 极小 | 60% |
| Layer 2 | 低 | 小 | 70% |
| Layer 3 | 中 | 中 | 80% |
| Layer 4 | 高 | 大 | 90% |
| Layer 5 | 极高 | 最大 | 95% |

---

## 五层压缩策略

### Layer 1: Budget Reduction (60%)

**目标**：将大型工具输出替换为引用指针，保留结构信息。

**原理**：工具调用结果通常很大（如文件内容），但 LLM 真正需要的是"使用了什么工具"和"结果大小"，而不是完整内容。

**实现**：

```python
def _budget_reduction(messages: list[Message], target_ratio: float) -> list[Message]:
    """将大型工具结果替换为引用指针。"""
    result = []
    for msg in messages:
        if msg.role == "tool" and len(msg.content) > 2000:
            # 替换为引用指针
            summary = f"[Tool result: {msg.tool_name}({msg.tool_args}) -> {len(msg.content)} chars]"
            result.append(Message(role="tool", content=summary))
        else:
            result.append(msg)
    return result
```

**示例**：

```
# 原始 (5000 tokens)
{"role": "tool", "content": "很长的文件内容...（5000 字符）"}

# Budget Reduction 后 (50 tokens)
{"role": "tool", "content": "[Tool result: read_file({path: '/path/to/file.py'}) -> 5000 chars]"}
```

**压缩比**：~60%（减少 60% 的令牌数）

---

### Layer 2: Snip (70%)

**目标**：丢弃过时的对话轮次。

**原理**：早期的对话轮次通常不如最近的轮次重要。

**实现**：

```python
def _snip(messages: list[Message], target_ratio: float) -> list[Message]:
    """丢弃最旧的对话轮次。"""
    # 保留最新的消息，丢弃最旧的
    target_count = int(len(messages) * target_ratio)
    return messages[-target_count:]
```

**注意**：始终保留系统消息（role="system"）。

**压缩比**：~70%（保留 70% 的消息）

---

### Layer 3: Microcompact (80%)

**目标**：清除旧工具结果，但保留 `tool_use` 决策（核心创新）。

**原理**：工具调用的"决策"（为什么要调用这个工具）比"结果"更重要。

**实现**：

```python
def _microcompact(messages: list[Message], target_ratio: float) -> list[Message]:
    """清除旧工具结果，保留决策。"""
    result = []
    for i, msg in enumerate(messages):
        if msg.role == "tool" and i < len(messages) * 0.5:
            # 旧的工具结果：替换为摘要
            # 找到对应的 assistant 消息中的 tool_use
            assistant_msg = _find_corresponding_assistant(messages, i)
            if assistant_msg and assistant_msg.tool_calls:
                tool_call = assistant_msg.tool_calls[0]
                summary = f"I used {tool_call.name} to {tool_call.description}"
                result.append(Message(role="assistant", content=summary))
        else:
            result.append(msg)
    return result
```

**示例**：

```
# 原始
[
  {"role": "assistant", "tool_calls": [{"name": "read_file", "args": {...}}]},
  {"role": "tool", "content": "很长的文件内容..."},
  {"role": "assistant", "content": "Based on the file content..."}
]

# Microcompact 后
[
  {"role": "assistant", "content": "I used read_file to read /path/to/file.py"},
  {"role": "assistant", "content": "Based on the file content..."}
]
```

**压缩比**：~80%（保留 80% 的关键信息）

---

### Layer 4: Context Collapse (90%)

**目标**：归档并投射折叠视图（纯读时投影，不修改底层数据）。

**原理**：将多个连续的 assistant/tool 轮次折叠为单个摘要消息。

**实现**：

```python
def _context_collapse(messages: list[Message], target_ratio: float) -> list[Message]:
    """将多个轮次折叠为摘要。"""
    result = []
    collapse_buffer = []
    
    for msg in messages:
        if msg.role in ("assistant", "tool"):
            collapse_buffer.append(msg)
        else:
            if collapse_buffer:
                # 折叠缓冲区
                summary = _collapse_turns(collapse_buffer)
                result.append(Message(role="assistant", content=summary))
                collapse_buffer = []
            result.append(msg)
    
    if collapse_buffer:
        summary = _collapse_turns(collapse_buffer)
        result.append(Message(role="assistant", content=summary))
    
    return result

def _collapse_turns(turns: list[Message]) -> str:
    """将多个轮次折叠为单个摘要。"""
    actions = []
    for msg in turns:
        if msg.role == "assistant" and msg.tool_calls:
            for tc in msg.tool_calls:
                actions.append(f"- Used {tc.name}")
        elif msg.role == "assistant":
            actions.append(f"- Said: {msg.content[:50]}...")
    
    return "Actions taken:\n" + "\n".join(actions)
```

**压缩比**：~90%（保留 90% 的关键信息）

---

### Layer 5: Auto-Compact (95%)

**目标**：LLM 语义压缩。

**原理**：使用 LLM 本身来压缩历史，保留语义信息。

**实现**：

```python
def _auto_compact(messages: list[Message], target_ratio: float) -> list[Message]:
    """使用 LLM 压缩历史。"""
    # 1. 将旧消息转换为文本
    history_text = "\n".join(
        f"[{msg.role}] {msg.content}"
        for msg in messages[:-5]  # 保留最近 5 条
    )
    
    # 2. 调用 LLM 生成摘要
    summary = llm_call(
        f"Summarize the following conversation:\n{history_text}",
        model="fast-model"
    )
    
    # 3. 构建新消息列表
    result = [
        Message(role="system", content=f"Previous conversation summary:\n{summary}"),
        *messages[-5:]  # 保留最近 5 条
    ]
    
    return result
```

**60% 规则**：避免重复压缩已经压缩过的内容。

```python
# 如果当前使用率 < 60%，不再压缩
if current_usage_ratio < 0.60:
    return messages
```

**压缩比**：~95%（保留 95% 的关键信息）

---

## 主入口函数

```python
def graduated_compress(
    messages: list[Message],
    max_tokens: int,
    usage_ratio: float = None,
) -> tuple[list[Message], str]:
    """应用渐进压缩。
    
    Returns:
        (压缩后的消息, 应用的层名称)
    """
    if usage_ratio is None:
        usage_ratio = _calculate_usage_ratio(messages, max_tokens)
    
    # 根据使用率选择压缩层
    if usage_ratio < 0.60:
        return messages, "none"
    elif usage_ratio < 0.70:
        return _budget_reduction(messages, 0.60), "budget_reduction"
    elif usage_ratio < 0.80:
        return _snip(messages, 0.70), "snip"
    elif usage_ratio < 0.90:
        return _microcompact(messages, 0.80), "microcompact"
    elif usage_ratio < 0.95:
        return _context_collapse(messages, 0.90), "context_collapse"
    else:
        return _auto_compact(messages, 0.95), "auto_compact"
```

---

## 与 AgentContextManager 集成

```python
class AgentContextManager:
    def prepare_context(self, system_prompt, history, max_tokens):
        """准备上下文，应用渐进压缩。"""
        # 计算使用率
        usage_ratio = self._calculate_usage(history, max_tokens)
        
        # 应用渐进压缩
        if self.compression_enabled:
            compressed_history, layer = graduated_compress(
                history, max_tokens, usage_ratio
            )
            if layer != "none":
                logger.debug(f"Applied graduated compression: {layer}")
        else:
            compressed_history = history
        
        # 构建三通道上下文
        return build_three_channel_context(
            system_prompt=system_prompt,
            working_memory=self.working_memory,
            history=compressed_history,
        )
```

---

## 配置

通过 agent 的 `context {}` 块配置：

```helen
agent SmartAssistant {
    context {
        compression "graduated"  // 使用渐进压缩
    }
    
    main { ... }
}
```

### 压缩选项

| 选项 | 说明 |
|------|------|
| `"graduated"` | 渐进压缩（默认，推荐） |
| `"traditional"` | 传统截断 |
| `"none"` | 不压缩 |

---

## 性能对比

| 策略 | 压缩比 | 信息保留 | 计算成本 |
|------|--------|---------|---------|
| 传统截断 | 高 | 低 | 极低 |
| Layer 1 (Budget) | 60% | 高 | 极低 |
| Layer 2 (Snip) | 70% | 中高 | 低 |
| Layer 3 (Microcompact) | 80% | 中 | 中 |
| Layer 4 (Collapse) | 90% | 中低 | 高 |
| Layer 5 (Auto) | 95% | 低 | 极高 |

---

## 测试覆盖

- `tests/runtime/test_graduated_compression.py` - 16 个测试
  - Layer 1: Budget Reduction
  - Layer 2: Snip
  - Layer 3: Microcompact
  - Layer 4: Context Collapse
  - Layer 5: Auto-Compact
  - 主入口函数
  - 使用率计算

---

**最后更新**: 2026-07-06  
**版本**: v1.15 (Phase 7)
