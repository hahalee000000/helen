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
