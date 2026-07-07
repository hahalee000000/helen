# 架构问题分析报告：llm_summarizer.auto_compact 和压缩系统冲突

> **日期**: 2026-07-07  
> **范围**: Helen v1.15 上下文管理模块  
> **状态**: 分析完成，待决策

---

## 问题 1: `llm_summarizer.auto_compact()` 死代码分析

### 1.1 现状

**位置**: `helen/runtime/llm_summarizer.py:187-242`

```python
def auto_compact(history: list, llm_client: Callable, target_tokens: int = 2000) -> list:
    """Auto-compact layer for graduated compression pipeline.

    This is the Layer 5 compression that uses LLM to generate intelligent summaries.
    """
    # ... 实现代码 ...
    summary_msg = Message(
        role="system",
        content=f"[Previous conversation summary - LLM generated]\n\n{summary_text}",
        # ...
    )
    compressed_history = [...]  # Mark all as compressed
    return [summary_msg] + compressed_history
```

### 1.2 调用关系分析

```
graduated_compression.py                    llm_summarizer.py
┌─────────────────────────┐                 ┌──────────────────────┐
│ graduated_compress()    │                 │ LLMSummarizer 类     │
│   └─> _auto_compact()   │ ── uses ──────▶│   .summarize()       │
│       (L473-544)        │                 │                      │
│   └─> _structural_auto_ │                 │ auto_compact() 函数  │
│       compact()         │                 │   (L187-242) ← 无调用者│
│                         │                 │                      │
│ _auto_compact() 内部：  │                 │                      │
│   - 直接导入 LLMSumma-  │                 │                      │
│     rizer 类            │                 │                      │
│   - 调用 .summarize()   │                 │                      │
└─────────────────────────┘                 └──────────────────────┘
```

**搜索结果**:
- `auto_compact()` 函数：**0 个调用者**（搜索整个代码库）
- `_auto_compact()` 函数：**1 个调用者**（`graduated_compress()` L132）
- `LLMSummarizer` 类：**2 个调用者**
  - `graduated_compression.py:517` — `_auto_compact()` 内部
  - `reactive_compaction.py:319` — `_MsgAdapter` 配合使用

### 1.3 代码对比

| 维度 | `auto_compact()` (llm_summarizer.py) | `_auto_compact()` (graduated_compression.py) |
|------|------|------|
| 输入 | `history: list` (类型宽泛) | `history: list[Message]` (类型明确) |
| 输出 | `[summary_msg] + compressed_history` | `[summary_msg] + recent_msgs` |
| 处理方式 | 将所有旧消息标记为 `compressed=True` | **只保留最近 N 条**，丢弃旧消息 |
| Token 控制 | `target_tokens` 参数 | `target_tokens` 参数 |
| LLM 回退 | `_fallback_summary()` | `_structural_auto_compact()` |
| **调用者** | **0** | **1** (`graduated_compress`) |

**关键差异**:
- `auto_compact()` 返回 `[summary_msg] + 所有旧消息(compressed=True)` — **实际上不压缩**，只是标记
- `_auto_compact()` 返回 `[summary_msg] + 最近N条` — **真正压缩**，丢弃旧消息

### 1.4 建议处置

**选项 A: 删除（推荐）**
```python
# 删除 llm_summarizer.py 中的 auto_compact() 函数 (L187-242)
# 删除 calculate_next_compaction_threshold() 函数 (L245-267) — 同样无调用者
```

**理由**:
1. 完全无调用者，是死代码
2. 实现有缺陷（不真正压缩，只是标记）
3. `_auto_compact()` 已经完整实现了 Layer 5 功能
4. 减少代码混淆

**选项 B: 修复并启用**
如果想保留 `auto_compact()`，需要：
1. 修改实现：只保留最近消息，而非全部标记
2. 在 `AgentContextManager` 中暴露配置开关
3. 添加单元测试

**选项 C: 统一为一个接口**
让 `llm_summarizer.py` 成为唯一入口，`graduated_compression.py` 调用它：
```python
# llm_summarizer.py 提供公共 API
def auto_compact(history, llm_client, keep_recent=4, target_tokens=2000):
    # 真正实现压缩
    ...

# graduated_compression.py 使用它
from helen.runtime.llm_summarizer import auto_compact
```

**推荐**: 选项 A（删除）。理由：
- `LLMSummarizer` 类已经足够灵活
- `_auto_compact()` 的实现更正确
- 减少维护负担

---

## 问题 2: 两个压缩系统冲突分析

### 2.1 系统概述

Helen 当前有**两个独立的压缩系统**，概念边界模糊：

```
系统 A: stdlib/context.py — Helen 内建函数 (面向用户)
├── clear_context()
├── compress_context(strategy)
└── compress_context_target(target, keep_recent)

系统 B: graduated_compression.py — 5 层管线 (面向系统)
├── Layer 1: Budget Reduction (60%)
├── Layer 2: Snip (70%)
├── Layer 3: Microcompact (80%)
├── Layer 4: Context Collapse (90%)
└── Layer 5: Auto-Compact (95%)
```

### 2.2 系统 A 详细分析

**入口函数**: `helen/stdlib/context.py`

| 函数 | 实现方式 | 作用 |
|------|---------|------|
| `_clear_context()` | `history[:] = []` | 清空历史 |
| `_compress_context(strategy)` | 调用 `_interpreter_history_manager` 的压缩 | 按策略压缩 |
| `_compress_context_target(target, keep_recent)` | **直接修改 Message 对象** | 按类型选择性压缩 |

**关键代码** (`_compress_context_target`):
```python
def _compress_context_target(target: str, keep_recent: int = 5) -> dict:
    for i, msg in enumerate(_interpreter_history):
        if i >= len(_interpreter_history) - keep_recent * 2:
            break  # Keep recent

        # 直接修改消息对象（就地修改）
        if target == "tool_results":
            if msg.role == "tool":
                msg.content = f"[Tool result cleared: {msg.tool_call_id}]"
                msg.compressed = True
                msg._token_count = 10
```

**问题**:
- **就地修改** Message 对象 — 不可逆
- 通过**模块级全局变量** `_interpreter_history` 访问历史
- 由 `_set_interpreter_context()` 设置，耦合到解释器
- 与 `graduated_compress()` 的**返回新列表**风格不一致

### 2.3 系统 B 详细分析

**入口函数**: `helen/runtime/graduated_compression.py:graduated_compress()`

**调用者**:
1. `AgentContextManager._compress_history()` — 自动压缩
2. `AgentContextManager._apply_cache_aware_wrap()` — 缓存感知压缩

**特点**:
- **不修改**原始历史，返回新列表
- 5 层渐进，每层有独立阈值
- Layer 1-4 零成本，Layer 5 可选 LLM

### 2.4 冲突矩阵

| 维度 | 系统 A (stdlib) | 系统 B (graduated) | 冲突 |
|------|----------------|-------------------|------|
| **触发方式** | 用户显式调用 | 自动按阈值触发 | 🟡 可能重复 |
| **修改方式** | 就地修改 Message | 返回新列表 | 🔴 **严重冲突** |
| **可逆性** | 不可逆 | 可逆（原始历史不变） | 🔴 **严重冲突** |
| **配置** | 无配置 | `context {}` 块 | 🟡 不一致 |
| **阈值** | `keep_recent=5` | 60/70/80/90/95% | 🟡 不同概念 |
| **状态管理** | 全局变量 | 实例参数 | 🟡 耦合方式不同 |

### 2.5 冲突场景

**场景 1: 用户调用 `compress_context()` 后再调用 LLM**
```python
# Helen 代码
clear_context()              # 清空 _interpreter_history
compress_context("summarize") # 尝试压缩空历史（无效）
llm act "what did we discuss?" # LLM 看到的是空历史
```

**场景 2: 自动压缩后用户再调用 `compress_context_target()`**
```python
# 系统触发 graduated_compress() → 返回新列表（旧列表不变）
# 用户调用 compress_context_target("tool_results") → 就地在旧列表上修改
# 下次 LLM 调用：AgentContextManager 使用旧列表的修改版本
# → 用户修改和系统压缩混在一起
```

**场景 3: `_interpreter_history` 和 `self._history` 不同步**
```python
# interpreter.py:762
self._history = []

# stdlib/context.py:17
_interpreter_history = None  # 通过 _set_interpreter_context() 指向 self._history

# 如果 _history 被替换（如 [:] = 赋值），引用仍然有效
# 但如果 _history 被重新赋值（=），引用会失效
```

### 2.6 架构建议

**方案 1: 统一入口（推荐）** 🌟

让 `AgentContextManager` 成为唯一入口，`stdlib/context.py` 委托给它：

```python
# stdlib/context.py
def _compress_context(strategy: str = "auto"):
    if _interpreter_agent_context is not None:
        # 委托给 AgentContextManager
        _interpreter_agent_context.compress(strategy=strategy)
    else:
        # 回退到直接修改（兼容模式）
        ...

# agent_context.py 新增方法
class AgentContextManager:
    def compress(self, strategy: str = "auto"):
        """手动触发压缩（面向用户的 API）"""
        # 通过 transcript_store 记录压缩事件
        # 调用 graduated_compress
        ...
```

**优点**:
- 单一入口，消除冲突
- 可逆压缩（通过 TranscriptStore）
- 统一配置

**缺点**:
- 需要重构 `stdlib/context.py`
- 需要暴露 `compress()` 方法

**方案 2: 明确边界（折中）**

保留两个系统但明确职责：
- `stdlib/context.py`: 仅用于**紧急手动操作**（clear, emergency compress）
- `graduated_compress()`: 所有自动压缩
- 文档明确说明两者区别

**方案 3: 废弃系统 A**

删除 `compress_context()` 和 `compress_context_target()`，只保留：
- `clear_context()` — 紧急清空
- 所有其他压缩由自动管线处理

### 2.7 推荐实施路径

**短期（v1.16）**:
1. 在 `AgentContextManager` 添加 `compress(strategy)` 方法
2. 修改 `stdlib/context.py` 的 `_compress_context()` 委托给 `AgentContextManager`
3. `_compress_context_target()` 改用返回新列表（与 graduated 一致）
4. 添加文档说明

**中期（v1.17）**:
1. 统一配置入口（`context {}` 块 + 手动 API）
2. TranscriptStore 作为唯一状态源
3. 移除模块级全局变量 `_interpreter_history`

**长期**:
1. 考虑将压缩做成插件系统
2. 支持用户自定义压缩策略
3. 压缩事件可观察（接入 observability）

---

## 总结

| 问题 | 严重程度 | 推荐处置 | 实施难度 |
|------|---------|---------|---------|
| `auto_compact()` 死代码 | 🟡 中 | 删除（选项 A） | 低（10 分钟） |
| 两个压缩系统冲突 | 🔴 高 | 统一入口（方案 1） | 中（1-2 周） |

### 下一步行动

1. **立即**: 删除 `llm_summarizer.auto_compact()` 和 `calculate_next_compaction_threshold()`
2. **Phase 11**: 实施统一入口方案
3. **文档**: 更新 `wiki/runtime/context-management.md` 说明架构决策
