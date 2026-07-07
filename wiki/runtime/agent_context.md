# Agent 上下文管理器 (AgentContextManager)

> ⚠️ **本文档已被 [[runtime/context-management|上下文管理架构]] 取代。** 本页保留供历史参考，部分内容已过时（如 `compression_enabled: bool` API、`CacheAwareCompressor` 直接调用）。请参阅新文档了解统一压缩架构。

> Phase 7 | `helen/interpreter/agent_context.py` | 测试: `tests/interpreter/test_phase7_agent_context.py`

---

## 概述

AgentContextManager 是 Phase 7 的核心组件，将工作记忆、渐进压缩、缓存感知压缩统一集成到 agent 执行流程中，并为每个 agent 提供独立的上下文配置。

---

## 设计目标

1. **自动集成**：所有 agent 默认使用上下文管理增强
2. **可配置性**：每个 agent 可以独立配置上下文策略
3. **向后兼容**：现有代码无需修改
4. **三通道上下文**：系统指令 + 工作记忆 + 对话历史

---

## 核心组件

### AgentContextManager 类

```python
class AgentContextManager:
    """Agent 上下文管理器。
    
    封装工作记忆和压缩策略，自动集成到 agent 执行流程。
    """
    
    def __init__(
        self,
        working_memory_tokens: int = 5000,
        compression_enabled: bool = True,
        working_memory_enabled: bool = True,
        cache_aware_enabled: bool = True,
    ):
        self.working_memory = WorkingMemory(max_tokens=working_memory_tokens)
        self.compression_enabled = compression_enabled
        self.working_memory_enabled = working_memory_enabled
        self.cache_aware_enabled = cache_aware_enabled
```

---

## 主要方法

### update_from_message

从消息更新工作记忆。

```python
def update_from_message(self, content: str, role: str) -> None:
    """从消息更新工作记忆。
    
    提取：
    - 文件引用（从内容中）
    - 最近决策（从 assistant 消息）
    - 待办事项（从注释）
    """
    if not self.working_memory_enabled:
        return
    
    # 提取文件引用
    files = self._extract_file_references(content)
    for file in files:
        self.working_memory._add_active_file(file)
    
    # 提取 TODO
    todos = self._extract_todos(content)
    for todo in todos:
        self.working_memory._add_decision(f"TODO: {todo}")
    
    # 从 assistant 消息提取决策
    if role == "assistant":
        decisions = self._extract_decisions(content)
        for decision in decisions:
            self.working_memory._add_decision(decision)
```

### update_from_tool_call

从工具调用更新工作记忆。

```python
def update_from_tool_call(
    self,
    tool_name: str,
    tool_args: dict,
    tool_result: Any,
    exit_code: int | None = None,
) -> None:
    """从工具调用更新工作记忆。
    
    跟踪：
    - 文件操作（read/write/patch）
    - 工具调用结果和错误
    """
    if not self.working_memory_enabled:
        return
    
    if tool_name == "read_file":
        file_path = tool_args.get("file_path", "")
        if file_path:
            self.working_memory._add_active_file(file_path)
    
    elif tool_name == "write_file":
        file_path = tool_args.get("file_path", "")
        if file_path:
            self.working_memory._add_active_file(file_path)
            self.working_memory._add_decision(f"Modified {file_path}")
    
    elif tool_name == "patch_file":
        file_path = tool_args.get("file_path", "")
        if file_path:
            self.working_memory._add_active_file(file_path)
            self.working_memory._add_decision(f"Patched {file_path}")
    
    elif tool_name == "shell_exec":
        command = tool_args.get("command", "")
        if exit_code is not None and exit_code != 0:
            error_msg = str(tool_result)[:200]
            self.working_memory._add_error(command, error_msg)
```

### prepare_context

准备三通道上下文。

```python
def prepare_context(
    self,
    system_prompt: str | None,
    history: list[Message],
    max_tokens: int,
    current_prompt: str | None = None,
) -> list[dict[str, str]]:
    """准备三通道上下文。
    
    应用：
    1. 渐进压缩（如果启用）
    2. 缓存感知压缩（如果启用）
    3. 三通道上下文构建
    """
    # 1. 应用渐进压缩
    if self.compression_enabled:
        compressed_history, layer = graduated_compress(
            history, max_tokens
        )
        if layer != "none":
            logger.debug(f"Applied graduated compression: {layer}")
    else:
        compressed_history = history
    
    # 2. 应用缓存感知压缩
    if self.cache_aware_enabled:
        compressor = CacheAwareCompressor()
        usage_ratio = self._calculate_usage(compressed_history, max_tokens)
        compressed_history, cache_status = compressor.compress(
            compressed_history, usage_ratio
        )
        logger.debug(f"Cache status: {cache_status}")
    
    # 3. 构建三通道上下文
    if self.working_memory_enabled:
        messages = build_three_channel_context(
            system_prompt=system_prompt or "",
            working_memory=self.working_memory,
            history=compressed_history,
        )
    else:
        # 回退：仅系统 + 历史
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        for msg in compressed_history:
            messages.append({
                "role": msg.role,
                "content": msg.content,
            })
    
    return messages
```

---

## 集成点

### 1. Interpreter 初始化

```python
# helen/interpreter/interpreter.py
class Interpreter:
    def __init__(self, ...):
        # Phase 7: 初始化 AgentContextManager
        from helen.interpreter.agent_context import AgentContextManager
        self._agent_context = AgentContextManager(
            working_memory_tokens=5000,
            compression_enabled=True,
            working_memory_enabled=True,
            cache_aware_enabled=True,
        )
```

### 2. 历史记录更新

```python
# helen/interpreter/llm_mixin.py
def _add_to_history(self, role: str, content: str) -> None:
    """添加消息到历史。"""
    # ... 添加到历史
    
    # Phase 7: 更新工作记忆
    if hasattr(self, '_agent_context') and self._agent_context is not None:
        self._agent_context.update_from_message(content, role)
```

### 3. 工具调用记录

```python
# helen/interpreter/llm_mixin.py
def _record_llm_response_to_history(self, ...) -> None:
    """记录 LLM 响应到历史。"""
    # ... 记录工具调用
    
    # Phase 7: 从工具调用更新工作记忆
    if hasattr(self, '_agent_context') and self._agent_context is not None:
        self._agent_context.update_from_tool_call(
            tool_name, tool_args, result, exit_code
        )
```

### 4. 上下文准备

```python
# helen/interpreter/llm_mixin.py
def _prepare_history_for_llm(self, system_prompt, current_prompt):
    """准备 LLM 调用的上下文。"""
    # Phase 7: 使用 AgentContextManager
    if hasattr(self, '_agent_context') and self._agent_context is not None:
        max_tokens = self._history_manager.MAX_TOKENS
        return self._agent_context.prepare_context(
            system_prompt=system_prompt,
            history=self._history,
            max_tokens=max_tokens,
            current_prompt=current_prompt,
        )
    
    # 回退：使用 HistoryManager
    return self._history_manager.prepare_for_llm(...)
```

### 5. Agent 配置应用

```python
# helen/interpreter/llm_mixin.py
def visit_llm_act_expr(self, node: LlmActExprNode) -> object:
    """执行 llm act 表达式。"""
    # ... 提取 agent 设置
    
    # Phase 7: 应用 agent 的 context config
    if self._current_agent is not None and hasattr(self._current_agent, 'context_config'):
        ctx_config = self._current_agent.context_config
        if ctx_config is not None and hasattr(self, '_agent_context'):
            # 更新 AgentContextManager 配置
            self._agent_context.compression_enabled = (ctx_config.compression != "none")
            self._agent_context.working_memory_enabled = ctx_config.working_memory
            if ctx_config.working_memory_tokens > 0:
                self._agent_context.working_memory.max_tokens = ctx_config.working_memory_tokens
```

---

## 配置

### Agent 声明中的 context {} 块

```helen
agent SmartAssistant {
    description "Smart assistant with custom context"
    
    context {
        compression "graduated"      // 压缩策略
        cache-aware true             // 缓存感知
        working-memory true          // 工作记忆
        working-memory-tokens 5000   // 工作记忆令牌预算
    }
    
    tools ["read_file", "web_search"]
    
    main {
        return llm act "..."
    }
}
```

### 配置选项

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `compression` | str | `"graduated"` | 压缩策略：`"none"` / `"graduated"` / `"traditional"` |
| `cache-aware` | bool | `true` | 启用缓存感知压缩 |
| `working-memory` | bool | `true` | 启用工作记忆 |
| `working-memory-tokens` | int | `5000` | 工作记忆令牌预算 |

### 中文关键字

```helen
agent 智能助手 {
    上下文 {
        压缩 "graduated"
        缓存感知 true
        工作记忆 true
        工作记忆令牌 5000
    }
}
```

---

## 三通道上下文

启用工作记忆后，LLM 看到的上下文分为三个通道：

### 通道 1: 系统指令 (15%)

```
Framework Instructions:
  - Tool Use (CRITICAL): MUST use tools, not describe
  - Skills (CRITICAL): MUST load relevant skills
  - Parallel Tool Calls: batch independent calls

Helen Conventions:
  - Core Principles
  - Skill-Driven Development
  - Code Generation Best Practices

Agent Description:
  - You are a helpful assistant

Skill Index:
  - <available_skills>
```

### 通道 2: 工作记忆 (50%)

```
<active_files>
  - src/main.py
  - tests/test_agent.py
</active_files>

<recent_decisions>
  - I'll use recursion
  - Let me try dynamic programming
</recent_decisions>

<pending_todos>
  - Add error handling
  - Write unit tests
</pending_todos>

<error_history>
  - shell_exec("invalid_cmd"): command not found
</error_history>
```

### 通道 3: 对话历史 (35%)

```
[user] Can you help me fix the bug?
[assistant] I'll use read_file to examine the code.
[assistant] I found the bug on line 42.
```

---

## 工作流程

### Agent 执行流程

```
1. visit_agent_decl()
   └─> 注册 agent，设置 _current_agent

2. visit_llm_act_expr()
   ├─> 读取 agent 的 context_config
   ├─> 更新 AgentContextManager 配置
   │
   ├─> _add_to_history("user", prompt)
   │   └─> update_from_message() 更新工作记忆
   │       ├─> 提取文件引用
   │       ├─> 提取 TODO
   │       └─> 提取决策
   │
   ├─> LLM 调用 + 工具循环
   │   └─> _record_llm_response_to_history()
   │       └─> update_from_tool_call() 更新工作记忆
   │           ├─> 跟踪文件操作
   │           └─> 跟踪错误
   │
   └─> _prepare_history_for_llm()
       ├─> 应用渐进压缩
       ├─> 应用缓存感知压缩
       └─> 构建三通道上下文
```

---

## 性能优化

### 1. 令牌计算缓存

```python
class AgentContextManager:
    def __init__(self):
        self._last_usage_ratio = 0.0
    
    def _calculate_usage(self, history, max_tokens):
        """计算使用率，缓存结果。"""
        # 如果历史没有变化，使用缓存的值
        if len(history) == self._last_history_length:
            return self._last_usage_ratio
        
        # 重新计算
        total_tokens = sum(self._estimate_tokens(msg) for msg in history)
        usage_ratio = total_tokens / max_tokens
        
        # 缓存结果
        self._last_history_length = len(history)
        self._last_usage_ratio = usage_ratio
        
        return usage_ratio
```

### 2. 工作记忆清理

```python
def _cleanup_working_memory(self):
    """清理过期的工作记忆。"""
    # 保留最近的文件（最多 10 个）
    if len(self.working_memory.active_files) > 10:
        self.working_memory.active_files = self.working_memory.active_files[-10:]
    
    # 保留最近的决策（最多 10 个）
    if len(self.working_memory.recent_decisions) > 10:
        self.working_memory.recent_decisions = self.working_memory.recent_decisions[-10:]
```

---

## 测试覆盖

- `tests/interpreter/test_phase7_agent_context.py` - 16 个测试
  - AgentContextManager 初始化
  - 工作记忆更新
  - 工具调用跟踪
  - 三通道上下文构建
  - context {} 块解析
  - 配置应用

---

## 统计信息

```python
def get_stats(self) -> dict[str, Any]:
    """获取上下文管理器统计信息。"""
    return {
        "working_memory_enabled": self.working_memory_enabled,
        "compression_enabled": self.compression_enabled,
        "cache_aware_enabled": self.cache_aware_enabled,
        "active_files": len(self.working_memory.active_files),
        "recent_decisions": len(self.working_memory.recent_decisions),
        "pending_todos": len(self.working_memory.pending_todos),
        "error_history": len(self.working_memory.error_history),
    }
```

### 在 REPL 中使用

```
> :stats
╔══════════════════════════════════════╗
║       Context Usage Statistics        ║
╠══════════════════════════════════════╣
║ ✅ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  12.3%            ║
║ Tokens:   15,984 /  131,072              ║
║ Model:  qwen3.7-plus                  ║
║ Messages: 8                           ║
║                                       ║
║ Working Memory:                       ║
║   Active Files: 3                     ║
║   Recent Decisions: 5                 ║
║   Pending TODOs: 2                    ║
║   Error History: 1                    ║
╚══════════════════════════════════════╝
```

---

## 对齐 Claude Code

AgentContextManager 完整实现了 Claude Code 的上下文管理功能：

| 特性 | Claude Code | Helen v1.15 |
|------|------------|-------------|
| 工作记忆 | ✅ | ✅ ✅ |
| 渐进压缩 | ✅ | ✅ ✅ |
| 缓存感知 | ✅ | ✅ ✅ |
| 三通道上下文 | ✅ | ✅ ✅ |
| 每 agent 配置 | ✅ | ✅ ✅ |

**对齐程度**: 100%

---

**最后更新**: 2026-07-06  
**版本**: v1.15 (Phase 7)
