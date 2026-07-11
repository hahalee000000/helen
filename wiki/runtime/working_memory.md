# 工作记忆 (Working Memory)

> ⚠️ **本文档已被 [[runtime/context-management|上下文管理架构]] 取代。** 本页保留供历史参考，部分内容已过时。请参阅新文档了解最新 API（`to_context(budget_chars)`、Channel 2 预算截断）。

> Phase 1 | `helen/runtime/working_memory.py` | 测试: `tests/runtime/test_working_memory.py`

---

## 概述

工作记忆是 Phase 1 引入的核心功能，自动跟踪 agent 执行过程中的关键信息，为 LLM 提供上下文感知的"短期记忆"。

---

## 核心组件

### WorkingMemory 类

```python
@dataclass
class WorkingMemory:
    active_files: list[str]        # 最近读写的文件路径
    recent_decisions: list[str]    # 关键决策（从 assistant 消息提取）
    pending_todos: list[str]       # 待办事项（从注释提取）
    error_history: list[dict]      # 错误记录（工具调用失败）
    max_tokens: int = 5000         # 词元预算
```

### 自动跟踪

| 信息类型 | 来源 | 示例 |
|---------|------|------|
| 活跃文件 | `read_file`/`write_file`/`patch_file` 调用 | `/path/to/main.py` |
| 最近决策 | Assistant 消息中的关键模式 | "I'll use recursion" |
| 待办事项 | 注释中的 TODO/FIXME | "TODO: Add error handling" |
| 错误历史 | 工具调用失败 | `shell_exec` 返回非零退出码 |

---

## 文件跟踪

### 自动提取文件路径

```python
def _add_active_file(self, file_path: str) -> None:
    """添加活跃文件，保持最近 10 个。"""
    if file_path not in self.active_files:
        self.active_files.append(file_path)
        if len(self.active_files) > 10:
            self.active_files = self.active_files[-10:]
```

### 示例

```helen
agent CodeReviewer {
    tools ["read_file", "write_file"]
    
    main {
        let code = read_file("src/main.py")     // ✅ 自动跟踪
        let fixed = fix_code(code)
        write_file("src/main.py", fixed)        // ✅ 自动跟踪
        
        return llm act "Review the changes"
        // 工作记忆现在知道：src/main.py 是活跃文件
    }
}
```

---

## 决策跟踪

### 从 Assistant 消息提取

```python
def _add_decision(self, decision: str) -> None:
    """添加最近决策，保持最近 10 个。"""
    self.recent_decisions.append(decision)
    if len(self.recent_decisions) > 10:
        self.recent_decisions = self.recent_decisions[-10:]
```

### 提取模式

从 assistant 消息中提取以下模式：

- "I'll use..."
- "I will..."
- "Let me try..."
- "I'm going to..."
- "Decided to..."
- "Approach:..."
- "using..."
- "chose..."
- "selected..."
- "opted for..."

### 示例

```
Assistant: I'll use a recursive approach to solve this problem.
→ 工作记忆: "use a recursive approach"

Assistant: Let me try implementing with dynamic programming.
→ 工作记忆: "try implementing with dynamic programming"
```

---

## 待办事项跟踪

### 从注释提取

```python
# 从代码注释中提取 TODO
def _extract_todos(self, content: str) -> list[str]:
    """提取 TODO/FIXME 项。"""
    patterns = [
        r'TODO[:\s]+(.+?)(?:\n|$)',
        r'FIXME[:\s]+(.+?)(?:\n|$)',
        r'\[\s\]\s+(.+?)(?:\n|$)',
    ]
    # ...
```

### 示例

```helen
// main.helen
// TODO: Add error handling
// FIXME: Fix memory leak
// [ ] Write unit tests

main {
    // 工作记忆自动提取这些 TODO
}
```

---

## 错误跟踪

### 工具调用失败

```python
def _add_error(self, command: str, error: str) -> None:
    """添加错误记录，保持最近 5 个。"""
    self.error_history.append({
        "command": command,
        "error": error,
    })
    if len(self.error_history) > 5:
        self.error_history = self.error_history[-5:]
```

### 示例

```helen
agent DebugHelper {
    tools ["shell_exec"]
    
    main {
        let result = shell_exec("invalid_command")
        // 退出码非零 → 自动记录错误
        // 工作记忆: {"command": "invalid_command", "error": "command not found"}
        
        return llm act "What went wrong?"
        // LLM 可以看到之前的错误历史
    }
}
```

---

## 词元预算

### 限制工作记忆大小

```python
max_tokens: int = 5000  # 默认 5000 tokens
```

工作记忆的总词元数不超过 `max_tokens`，超出时丢弃最旧的记录。

### 计算词元

```python
def _calculate_tokens(self) -> int:
    """计算当前工作记忆的词元数。"""
    total = 0
    for file in self.active_files:
        total += len(file) // 4
    for decision in self.recent_decisions:
        total += len(decision) // 4
    # ...
    return total
```

---

## 三通道上下文构建

工作记忆是"三通道上下文"的第二个通道：

| 通道 | 比例 | 内容 |
|------|------|------|
| 系统指令 | 15% | 框架指令、语言规范、agent 描述 |
| **工作记忆** | **50%** | **活跃文件、最近决策、待办事项、错误历史** |
| 对话历史 | 35% | 压缩后的对话消息 |

### 构建函数

```python
def build_three_channel_context(
    system_prompt: str,
    working_memory: WorkingMemory,
    history: list[Message],
    budget: dict[str, float] | None = None,
    max_tokens: int = 131072,
) -> list[dict]:
    """构建三通道上下文。"""
    if budget is None:
        budget = {"system": 0.15, "working": 0.50, "history": 0.35}
    
    messages = []
    
    # 通道 1: 系统指令（15% 预算）
    system_budget = int(max_tokens * budget["system"])
    if system_prompt:
        # 字符级截断（4 字符 ≈ 1 token）
        max_chars = system_budget * 4
        truncated_prompt = system_prompt[:max_chars] if len(system_prompt) > max_chars else system_prompt
        messages.append({"role": "system", "content": truncated_prompt})
    
    # 通道 2: 工作记忆（50% 预算，受 max_tokens 限制）
    working_budget = int(max_tokens * budget["working"])
    working_budget = min(working_budget, working_memory.max_tokens)
    working_budget_chars = working_budget * 4
    
    working_context = working_memory.to_context(budget_chars=working_budget_chars)
    if working_context:
        messages.append({
            "role": "system",
            "content": f"[Working Memory]\n{working_context}",
        })
    
    # 通道 3: 对话历史（35% 预算）
    history_budget = int(max_tokens * budget["history"])
    history_budget_chars = history_budget * 4
    
    # 从新到旧填充历史
    selected_history = []
    used_chars = 0
    for msg in reversed(history):
        msg_chars = len(msg.content)
        if used_chars + msg_chars <= history_budget_chars:
            selected_history.insert(0, msg)
            used_chars += msg_chars
        else:
            break
    
    for msg in selected_history:
        messages.append({"role": msg.role, "content": msg.content})
    
    return messages
```

### 工作记忆格式化

```python
def to_context(self, budget_chars: int | None = None) -> str:
    """格式化工作记忆为上下文字符串。
    
    Args:
        budget_chars: 可选字符预算。当提供时，按优先级渐进丢弃分区：
            Pending TODOs (最先丢弃) → Recent Decisions → Active Files → 
            Recent Errors → Current Task (最后丢弃)
    
    Returns:
        格式化的 Markdown 字符串
    """
    # max_tokens 作为硬上限
    effective_budget = budget_chars
    if self.max_tokens > 0:
        max_chars = self.max_tokens * 4
        if effective_budget is None:
            effective_budget = max_chars
        else:
            effective_budget = min(effective_budget, max_chars)
    
    # 按优先级构建分区（最高优先级优先）
    sections = []
    
    if self.task_description:
        sections.append((["## Current Task"], [self.task_description, ""]))
    
    if self.error_history:
        body = []
        for e in self.error_history[-3:]:
            body.append(f"- Command: {e.get('command', 'unknown')}")
            body.append(f"  Error: {e.get('error', 'unknown')[:100]}")
        sections.append((["## Recent Errors"], body))
    
    if self.active_files:
        body = [f"- {f}" for f in self.active_files[-5:]]
        sections.append((["## Active Files"], body))
    
    if self.recent_decisions:
        body = [f"- {d}" for d in self.recent_decisions[-5:]]
        sections.append((["## Recent Decisions"], body))
    
    if self.pending_todos:
        body = [f"- [ ] {t}" for t in self.pending_todos[:10]]
        sections.append((["## Pending TODOs"], body))
    
    # 如果超出预算，从最低优先级开始丢弃分区
    # ... (截断逻辑)
    
    return "\n".join(parts)
```

---

## 与 AgentContextManager 集成

工作记忆由 `AgentContextManager` 管理，自动集成到 agent 执行流程：

```python
class AgentContextManager:
    def __init__(self, working_memory_tokens: int = 5000):
        self.working_memory = WorkingMemory(max_tokens=working_memory_tokens)
    
    def update_from_message(self, content: str, role: str):
        """从消息更新工作记忆。"""
        files = self._extract_file_references(content)
        for file in files:
            self.working_memory._add_active_file(file)
        
        decisions = self._extract_decisions(content)
        for decision in decisions:
            self.working_memory._add_decision(decision)
    
    def update_from_tool_call(self, tool_name: str, tool_args: dict, ...):
        """从工具调用更新工作记忆。"""
        if tool_name in ("read_file", "write_file", "patch_file"):
            file_path = tool_args.get("file_path", "")
            if file_path:
                self.working_memory._add_active_file(file_path)
```

---

## 配置

通过 agent 的 `context {}` 块配置：

```helen
agent SmartAssistant {
    context {
        working-memory true           // 启用工作记忆
        working-memory-tokens 8000    // 词元预算 8000
    }
    
    main { ... }
}
```

---

## 测试覆盖

- `tests/runtime/test_working_memory.py` - 17 个测试
  - 文件跟踪
  - 决策提取
  - TODO 提取
  - 错误记录
  - 词元预算
  - 三通道构建

---

**最后更新**: 2026-07-06  
**版本**: v1.15 (Phase 7)
