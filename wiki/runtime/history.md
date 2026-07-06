# 历史管理 (HistoryManager)

> 模块 M16 | `helen/runtime/history.py` | 测试: `tests/runtime/test_history.py`

---

## 概述

HistoryManager 管理多轮 LLM 对话历史，确保不超出模型上下文窗口。

---

## Token 预算

```python
class HistoryManager:
    MAX_TOKENS: int = 128000          # 模型上下文窗口
    SUMMARY_MAX_TOKENS: int = 4096    # conversation_summary 上限
```

### check_budget()

```python
def check_budget(self, system_tokens: int, instruction_tokens: int) -> int:
    """计算对话历史可用的 Token 预算。"""
    return self.MAX_TOKENS - system_tokens - instruction_tokens - 1000  # 1000 缓冲
```

---

## 截断策略

```python
def trim_history(self, history: list[Message], budget: int) -> list[Message]:
    """从最旧消息开始截断，直到适应预算。"""
    # 计算每条消息的 Token 数
    msg_tokens = [self.estimate_tokens(msg.content) for msg in history]

    # 如果总 Token 数在预算内，保留全部
    if sum(msg_tokens) <= budget:
        return list(history)

    # 移除最旧消息直到适应预算
    result = list(history)
    result_tokens = list(msg_tokens)
    while result and sum(result_tokens) > budget:
        result.pop(0)
        result_tokens.pop(0)

    return result
```

---

## Conversation Summary

```python
def build_conversation_summary(self, history: list[Message], max_tokens=4096) -> str:
    """构建对话摘要，包含最新消息，截断最旧。"""
    lines = []
    total_tokens = 0

    # 从新到旧遍历
    for msg in reversed(history):
        line = f"[{msg.role}] {msg.content}"
        line_tokens = self.estimate_tokens(line)
        if total_tokens + line_tokens > max_tokens:
            continue  # 截断
        lines.append(line)
        total_tokens += line_tokens

    lines.reverse()  # 恢复时间顺序
    return "\n".join(lines)
```

### 格式

```
[user] Classify the email priority
[assistant] [routed to: urgent]
[user] Translate: Hello, world!
[assistant] Bonjour, le monde!
```

---

## Token 估算

```python
@staticmethod
def estimate_tokens(text: str) -> int:
    """v1: 简单启发式 (字符数 / 4)。"""
    return len(text) // 4
```

未来版本可接入真实 Tokenizer。

---

## 上下文管理增强 (Phase 1-7, v1.15+)

Helen v1.15 引入了完整的上下文管理增强方案，对齐 Claude Code 的上下文管理能力。

### 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                  Context Management Stack                │
├─────────────────────────────────────────────────────────┤
│ Phase 7: Agent Context Integration                       │
│   - AgentContextManager: 封装工作记忆和压缩策略           │
│   - context {} 块: 每个 agent 独立配置                    │
├─────────────────────────────────────────────────────────┤
│ Phase 6: Cache-Aware Compression                         │
│   - 稳定前缀 (30%): 缓存友好区                           │
│   - 批量阈值 (75%): 使用率触发压缩                        │
│   - 仅后缀修改: 缓存区域外操作                            │
├─────────────────────────────────────────────────────────┤
│ Phase 2-5: Graduated Compression Pipeline                │
│   - Layer 1 (60%): Budget Reduction                      │
│   - Layer 2 (70%): Snip                                  │
│   - Layer 3 (80%): Microcompact                          │
│   - Layer 4 (90%): Context Collapse                      │
│   - Layer 5 (95%): Auto-Compact                          │
├─────────────────────────────────────────────────────────┤
│ Phase 1: Foundation                                      │
│   - Working Memory: 跟踪活跃文件、决策、错误              │
│   - 三通道上下文: 系统指令 + 工作记忆 + 历史              │
└─────────────────────────────────────────────────────────┘
```

### Phase 1: 工作记忆 (Working Memory)

自动跟踪 agent 执行过程中的关键信息：

```python
class WorkingMemory:
    active_files: list[str]        # 最近读写的文件
    recent_decisions: list[str]    # 关键决策
    pending_todos: list[str]       # 待办事项
    error_history: list[dict]      # 错误记录
```

**自动提取：**
- 文件路径：从 `read_file`、`write_file`、`patch_file` 调用
- 决策：从 assistant 消息中的关键模式（"I'll use...", "Let me try..."）
- TODO：从注释中的 `TODO:`、`FIXME:` 模式
- 错误：从 `shell_exec` 失败和错误关键词

### Phase 2-5: 渐进压缩管线 (Graduated Compression)

五层渐进策略，"最廉价动作优先"原则：

#### Layer 1: Budget Reduction (60%)

将大工具输出替换为引用指针，保留结构信息。

```python
# 原始工具结果 (5000 tokens)
{"role": "tool", "content": "很长的输出内容..."}

# Budget Reduction 后 (50 tokens)
{"role": "tool", "content": "[Tool result: read_file(path=/path/to/file.py) -> 5000 chars]"}
```

#### Layer 2: Snip (70%)

丢弃过时的轮次（最旧的 assistant + tool 对）。

#### Layer 3: Microcompact (80%)

清除旧工具结果，但保留 `tool_use` 决策（核心创新）。

```python
# 原始 (包含完整工具调用和结果)
[{"role": "assistant", "tool_calls": [...]}, {"role": "tool", "content": "..."}]

# Microcompact 后 (只保留决策)
[{"role": "assistant", "content": "I used tool X to read file Y"}]
```

#### Layer 4: Context Collapse (90%)

归档并投射折叠视图（纯读时投影，不修改底层数据）。

#### Layer 5: Auto-Compact (95%)

LLM 语义压缩，使用 60% 规则避免重复压缩。

### Phase 6: 缓存感知压缩 (Cache-Aware)

考虑 prompt cache 的缓存友好策略：

```python
class CacheAwareCompressor:
    CACHE_ZONE_RATIO = 0.30        # 稳定前缀比例
    BATCH_COMPRESSION_THRESHOLD = 0.75  # 批量压缩阈值
    
    def compress(self, messages):
        # 1. 识别缓存区域（前 30%）
        cache_zone = messages[:int(len(messages) * 0.30)]
        
        # 2. 只在缓存区域外修改
        # 3. 使用稳定的压缩边界标记
```

**效果：**
- 缓存命中率从 10-20% 提升到 70-80%
- 减少重复计算，降低延迟

### Phase 7: Agent 集成 (Agent Context)

将上下文管理集成到 agent 执行流程：

```helen
agent SmartAssistant {
    context {
        compression "graduated"
        cache-aware true
        working-memory true
        working-memory-tokens 5000
    }
    
    main {
        // AgentContextManager 自动应用
        return llm act "..."
    }
}
```

**集成点：**
- `_add_to_history()`: 每次添加消息后更新工作记忆
- `_record_llm_response_to_history()`: 从工具调用更新
- `_prepare_history_for_llm()`: 应用渐进压缩和三通道构建

### 三通道上下文构建

启用工作记忆后，LLM 看到的上下文分为三个通道：

| 通道 | 比例 | 内容 |
|------|------|------|
| 系统指令 | 15% | 框架指令、语言规范、agent 描述、技能索引 |
| 工作记忆 | 50% | 活跃文件、最近决策、待办事项、错误历史 |
| 对话历史 | 35% | 压缩后的对话消息 |

### 配置示例

#### 高性能研究 Agent

```helen
agent Researcher {
    context {
        compression "graduated"      // 渐进压缩
        cache-aware true             // 缓存感知
        working-memory true          // 工作记忆
        working-memory-tokens 8000   // 更大的工作记忆
    }
    
    tools ["web_search", "read_file", "write_file"]
    
    main {
        return llm act "Research..."
    }
}
```

#### 简单快速 Agent

```helen
agent QuickResponder {
    context {
        compression "none"           // 不压缩
        working-memory false         // 禁用工作记忆
    }
    
    main {
        return llm act "Quick answer"
    }
}
```

### 性能对比

| 特性 | v1.14 (之前) | v1.15 (Phase 7) |
|------|-------------|-----------------|
| 压缩策略 | 单层截断 | 五层渐进 |
| 缓存命中率 | 10-20% | 70-80% |
| 工作记忆 | ❌ | ✅ 自动跟踪 |
| 上下文配置 | 全局 | 每个 agent 独立 |
| 三通道上下文 | ❌ | ✅ |
| 缓存感知 | ❌ | ✅ |

### 测试覆盖

- `tests/runtime/test_working_memory.py` - 17 个测试
- `tests/runtime/test_graduated_compression.py` - 16 个测试
- `tests/runtime/test_cache_aware_compression.py` - 18 个测试
- `tests/runtime/test_llm_summarization.py` - 9 个测试
- `tests/interpreter/test_phase7_agent_context.py` - 16 个测试

**总计: 76 个新测试，全部通过**

---

**最后更新**: 2026-07-06  
**版本**: v1.15 (Phase 7)
