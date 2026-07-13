# Helen 流式推理中断方案

> 版本：v2.1（适配 v1.18 spawn/分生 + Channel 模型）  
> 日期：2026-07-13  
> 状态：待评审  
> 替代：v1.0 草案（基于 v1.17 detach/async-await 模型，已废弃）  
> v2.1 变更：新增 Phase 7 — `spawnagent` → `spawn`/`分生` 关键字重命名

---

## 目录

1. [问题陈述](#1-问题陈述)
2. [设计目标](#2-设计目标)
3. [v1.18 并发模型回顾](#3-v118-并发模型回顾)
4. [两种调用形式分析](#4-两种调用形式分析)
5. [中断机制总览](#5-中断机制总览)
6. [现有架构](#6-现有架构)
7. [方案详细设计](#7-方案详细设计)
   - 7.1 [Phase 1: on_chunk 返回值中断](#71-phase-1-on_chunk-返回值中断)
   - 7.2 [Phase 2: cancel_event 贯穿 Runtime 层](#72-phase-2-cancel_event-贯穿-runtime-层)
   - 7.3 [Phase 3: 解释器流式调用注册表](#73-phase-3-解释器流式调用注册表)
   - 7.4 [Phase 4: REPL 存活](#74-phase-4-repl-存活)
   - 7.5 [Phase 5: stdlib 函数](#75-phase-5-stdlib-函数)
   - 7.6 [Phase 6: spawn 取消](#76-phase-6-spawn-取消)
   - 7.7 [Phase 7: spawnagent → spawn/分生 关键字重命名](#77-phase-7-spawnagent--spawn分生-关键字重命名)
8. [向后兼容性](#8-向后兼容性)
9. [风险矩阵](#9-风险矩阵)
10. [测试方案](#10-测试方案)
11. [实施路线图](#11-实施路线图)
12. [开放问题](#12-开放问题)
13. [附录 A: v1.0 → v2.1 变更摘要](#附录-a-v10--v21-变更摘要)

---

## 1. 问题陈述

Helen 的 `llm act` 流式推理目前无法中途停止，存在三个具体缺陷：

| 缺陷 | 影响 |
|------|------|
| `on_chunk` 回调返回值被丢弃 | 用户代码无法请求中断 |
| Ctrl+C 退出整个 REPL | 所有变量、函数、agent 定义丢失 |
| Channel `cancel_event` 未接入流式路径 | 编程式取消仅停留在 Channel 层，无法中断正在进行的 HTTP 流 |

v1.18 的 `spawn + Channel` 模型带来了新的中断需求：

- **主线程 `llm act`**：Ctrl+C 退出整个 REPL，流式无法中断
- **spawn 后台 agent**：`endpoint.cancel()` 设置了 `cancel_event`，但 agent 内部的 `llm act` 流式路径不检查此信号，HTTP 连接无法关闭，agent 线程无法优雅退出

### 与 v1.0 提案的差异

v1.0 提案基于 v1.17 的三种并发形式（主线程、`detach`、`async/await`）。v1.18 进行了破坏性重构：

| v1.17（v1.0 提案基础） | v1.18（本提案基础） |
|----------------------|-------------------|
| 主线程 `llm act` | 主线程 `llm act`（不变） |
| `detach` 守护线程 | ❌ 已删除 |
| `async call` / `await` | ❌ 已删除 |
| `channel X { fields }` 声明 | ❌ 已删除 |
| — | `spawn Agent(...)` → 返回 Channel |
| — | `ChannelEndpoint.cancel()` → `cancel_event` |
| — | `mailbox_select([ch1, ch2])` 多通道选择 |

本提案完全重写，仅覆盖两种调用形式：**主线程** 和 **spawn**。

---

## 2. 设计目标

| 目标 | 说明 |
|------|------|
| **三层中断** | 回调返回值、Ctrl+C 信号、Channel.cancel() 编程式 API |
| **REPL 存活** | Ctrl+C 中断当前 `llm act`，保留所有运行时状态 |
| **协议一致** | 两种调用形式（主线程、spawn）共享相同的中断语义 |
| **复用 v1.18 基础设施** | Channel 已有 `cancel_event`，本方案将其接入流式路径而非新建 |
| **向后兼容** | 现有 Helen 程序无需任何修改 |
| **渐进实施** | 按 Phase 分阶段交付，每个 Phase 可独立验证 |

---

## 3. v1.18 并发模型回顾

### 3.1 spawn + Channel 架构

```helen
// 生成 agent，立即返回 Channel（邮箱）
设 mailbox = spawn Worker("后台任务")

// 双向通信
mailbox.send("开始工作")
设 result = mailbox.receive()

// 取消后台 agent
mailbox.cancel()
```

**关键组件**：

| 组件 | 文件 | 功能 |
|------|------|------|
| `Channel` | `helen/runtime/channel.py` | 双向消息通道（两个 Queue + cancel_event + closed） |
| `ChannelEndpoint` | 同上 | Channel 的一端（主线程端 / spawned agent 端） |
| `mailbox_select` | `helen/stdlib/mailbox.py` | 多通道选择器（first-ready wins） |

### 3.2 Channel 已有的取消基础设施

```python
# helen/runtime/channel.py

class Channel:
    def __init__(self, name: str = ""):
        self._to_spawned: queue.Queue = queue.Queue()
        self._from_spawned: queue.Queue = queue.Queue()
        self._cancel_event = threading.Event()   # ← 已存在
        self._closed = threading.Event()

    def mark_cancelled(self) -> None:
        self._cancel_event.set()    # ← 设置取消信号
        self._closed.set()

class ChannelEndpoint:
    def cancel(self) -> None:
        """取消对端 agent 并关闭通道。"""
        self._channel.mark_cancelled()
        self._send_sentinel()    # 唤醒阻塞的 receive()

    @property
    def cancel_event(self) -> threading.Event:
        """取消信号（仅对 spawned agent 端有意义）。"""
        return self._channel.cancel_event
```

**断裂点**：`cancel_event` 已存在，但：
1. `act_stream()` 不接受也不检查 `cancel_event`
2. `_visit_llm_act_streaming` 的 `for event` 循环无取消检查
3. spawned agent 的 Interpreter 不感知 `cancel_event`
4. Ctrl+C 只影响主线程，spawned agent 线程无法感知

---

## 4. 两种调用形式分析

### 4.1 主线程 `llm act`（直接流式）

```helen
agent ChatBot(user_input: str) {
    main {
        llm act user_input on_chunk fn(chunk: str) {
            print(chunk)
        }
    }
}
```

**现状**：
- 控制流：`repl → _execute_input → interp.interpret → visit_llm_act_expr → _visit_llm_act_streaming → act_stream()`
- 单线程、单调用，控制流清晰
- `KeyboardInterrupt` 天然在主线程抛出

| 维度 | 评估 |
|------|------|
| 实现难度 | 🟢 低 |
| 中断机制 | `KeyboardInterrupt` 自然可用；`cancel_event` 一个 Event 即可 |
| 状态一致性 | 🟢 中断后 interpreter 状态完整 |
| HTTP 清理 | 🟢 `with self._client.stream(...)` 退出即关闭 |
| 风险 | 极低，改动范围仅在 `llm_mixin.py` 流式循环内 |

### 4.2 spawn（后台 agent + Channel 取消）

```helen
agent Worker(task: str, mailbox: Channel) {
    main {
        result = llm act task on_chunk fn(chunk: str) {
            print(chunk)
            mailbox.send(chunk)    // 实时回传进度
        }
        mailbox.send({"done": true, "result": result})
    }
}

// 主线程
设 ch = spawn Worker("写一篇长文")
// ... 做其他事 ...
// 需要时取消
ch.cancel()    // ← 设置 cancel_event，但 agent 内部不检查
```

**现状**：
- `visit_spawn_expr`（`interpreter.py:2359-2462`）创建 daemon 线程，运行全新 `Interpreter`
- 返回 `ChannelEndpoint`（主线程端）—— 有 `cancel()` 方法
- `cancel()` 设置 `channel._cancel_event`，但 **spawned agent 内部不检查**
- `KeyboardInterrupt` **只在主线程抛出**，daemon 线程收不到
- spawned agent 内的 `llm act` 流式路径不接受 `cancel_event`

| 维度 | 评估 |
|------|------|
| 实现难度 | 🟡 中 — 需将 `cancel_event` 注入 spawned interpreter |
| 中断机制 | Channel `cancel_event` 已存在，需贯穿到 Runtime 层 |
| 状态一致性 | 🟢 主线程不受影响；spawned agent 内部部分响应丢失 |
| HTTP 清理 | 🟡 `cancel_event` 需穿透到 spawned interpreter 的 `act_stream` |
| 优雅退出 | 🟡 `cancel()` + sentinel 已唤醒 `receive()`；需补充流式中断 |

**关键优势（相比 v1.0 的 detach）**：

| 选择 | v1.0 detach | v1.18 spawn |
|------|-------------|-------------|
| 线程句柄 | 返回 `None`，无句柄 | 返回 `ChannelEndpoint`，可 cancel |
| 取消信号 | 需新建 `_detach_cancel_event` | ✅ Channel 已有 `cancel_event` |
| 双向通信 | 无（fire-and-forget） | ✅ 双向 Queue |
| 进度反馈 | 无 | ✅ 通过 Channel 回传 |
| 多 agent 取消 | 需遍历线程列表 | ✅ `endpoint.cancel()` 一对一 |
| 多 agent 选择 | 不支持 | ✅ `mailbox_select` |

### 4.3 两种形式对比总结

| 调用形式 | 实现难度 | 风险 | 建议 |
|----------|---------|------|------|
| 主线程 `llm act` | 🟢 低 | 极低 | ✅ 本次实现 |
| `spawn` | 🟡 中 | 低 | ✅ 本次实现（复用 Channel cancel_event） |

---

## 5. 中断机制总览

```
┌─────────────────────────────────────────────────────────────────┐
│                       用户触发中断                                │
│                                                                 │
│  ① on_chunk 返回 false    ② Ctrl+C          ③ endpoint.cancel() │
│       ↓                      ↓                     ↓             │
│  break 出 for-event 循环   KeyboardInterrupt     cancel_event    │
│       ↓                      ↓                   .set()          │
│       │                      ↓                     ↓             │
│  ┌────┴─────────────────────────────────────────────────────┐   │
│  │       _visit_llm_act_streaming (llm_mixin.py)            │   │
│  │  • interrupted = True                                    │   │
│  │  • break 出流式循环                                        │   │
│  │  • 跳过 on_complete                                      │   │
│  │  • 返回部分响应                                            │   │
│  └──────────────────────────┬───────────────────────────────┘   │
│                             ↓                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           act_stream (http_llm.py)                        │   │
│  │  • cancel_event.is_set() → break                         │   │
│  │  • with 块退出 → httpx 自动关闭连接                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              REPL (repl.py)                                │   │
│  │  • except KeyboardInterrupt → 打印提示，继续循环              │   │
│  │  • 所有变量/函数/agent 状态保留                               │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │       spawn 场景（后台 agent）                                │   │
│  │  • endpoint.cancel() → cancel_event.set()                │   │
│  │  • spawned interpreter 在 act_stream 中检查 cancel_event  │   │
│  │  • 流式停止 → spawned_endpoint.close() → 主线程收到 None    │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. 现有架构

### 6.1 关键文件与行号

| 文件 | 行号 | 功能 |
|------|------|------|
| `helen/interpreter/llm_mixin.py` | L420-561 | `_visit_llm_act_streaming()` — 流式循环核心 |
| `helen/interpreter/llm_mixin.py` | L496, L505, L513 | `on_chunk_fn(content)` — 返回值被丢弃 |
| `helen/runtime/http_llm.py` | L902-1290 | `act_stream()` — 同步 SSE 流 |
| `helen/runtime/http_llm.py` | L1001-1068 | `with self._client.stream(...)` + `for line_bytes in response.iter_lines()` |
| `helen/runtime/llm_runtime.py` | L69-90 | `LLMRuntime.act_stream()` — ABC 默认实现（无 cancel_event 参数） |
| `helen/runtime/channel.py` | L18-72 | `Channel` — 双向消息通道（已有 cancel_event） |
| `helen/runtime/channel.py` | L74-217 | `ChannelEndpoint` — 端点操作（cancel/close/send/receive） |
| `helen/interpreter/interpreter.py` | L2359-2462 | `visit_spawn_expr` — 生成 agent + Channel |
| `helen/cli/repl.py` | L558-567 | `KeyboardInterrupt` during `input()` |
| `helen/cli/repl.py` | L588-598, L610-618 | 执行块（无 KeyboardInterrupt 处理） |
| `helen/cli/repl.py` | L624-626 | 外层 `except KeyboardInterrupt` → 退出 REPL |

### 6.2 控制流路径

```
REPL (repl.py)
  └→ _execute_input() (repl.py:65)
       └→ interp.interpret(program) (repl.py:105)
            └→ visit_llm_act_expr(node) (llm_mixin.py:146)
                 ├→ has_streaming = node.on_chunk is not None
                 │
                 ├→ [是] _visit_llm_act_streaming() (llm_mixin.py:420)
                 │    └→ self.llm_runtime.act_stream(...) (llm_mixin.py:482)
                 │         └→ SSE 迭代 → yield events
                 │
                 └→ [否] _visit_llm_act_sync() (llm_mixin.py:380)
                      └→ self.llm_runtime.act(...)

spawn (interpreter.py:2359)
  └→ threading.Thread(daemon=True)
       └→ 新 Interpreter 实例
            └→ 同一 visit_llm_act_expr 路径
            └→ ⚠ 不感知 Channel cancel_event
```

### 6.3 已有取消基础设施（v1.18 Channel，未接通流式）

```python
# helen/runtime/channel.py — 已存在，可用

class Channel:
    def __init__(self, name: str = ""):
        self._cancel_event = threading.Event()   # ✅ 取消信号
        self._closed = threading.Event()

    @property
    def cancel_event(self) -> threading.Event:
        return self._cancel_event

    def mark_cancelled(self) -> None:
        self._cancel_event.set()
        self._closed.set()

class ChannelEndpoint:
    def cancel(self) -> None:
        """取消对端 agent 并关闭通道。"""
        self._channel.mark_cancelled()
        self._send_sentinel()
```

**断裂点**：
1. `act_stream()` 不接受也不检查 `cancel_event`
2. `_visit_llm_act_streaming` 的 `for event` 循环无取消检查
3. `visit_spawn_expr` 创建的 spawned interpreter 不感知 `cancel_event`
4. 流式路径绕过 Channel，直接调用 `self.llm_runtime.act_stream()`

### 6.4 已有 HelenRuntime 取消（遗留死代码）

```python
# helen/runtime/__init__.py

class _CallHandle:
    def __init__(self):
        self.cancelled = threading.Event()
        self.done = threading.Event()

class HelenRuntime:
    def cancel_llm_call(self, call_id: str) -> bool:
        handle = self._active_calls.get(call_id)
        if handle is None: return False
        handle.cancelled.set()
        return True
```

**问题**：`HttpLLMRuntime` 不继承 `HelenRuntime`，`cancel_llm_call()` 从未被调用。本方案不复用此机制，而是在解释器层新建注册表（Phase 3）。

---

## 7. 方案详细设计

### 7.1 Phase 1: on_chunk 返回值中断

**目标**：用户代码可通过 `on_chunk` 返回 `false` 停止流式。

**文件**：`helen/interpreter/llm_mixin.py`

**改动**：3 处 `on_chunk_fn(...)` 调用改为捕获返回值。

```python
# 现有（L496）:
on_chunk_fn(content)

# 改为:
chunk_result = on_chunk_fn(content)
if chunk_result is False:    # 仅精确 False（身份比较）
    interrupted = True
    break
```

**三处调用点**：

| 位置 | 事件类型 | 现有代码 | 改动 |
|------|----------|---------|------|
| L496 | `content` | `on_chunk_fn(content)` | 检查返回值 `is False` → break |
| L505 | `tool_call` progress | `on_chunk_fn(progress)` | 同上 |
| L513 | `tool_result` | `on_chunk_fn(result_msg)` | 同上 |

**为什么用 `is False` 而非 `== False`**：

| 返回值 | `is False` | `== False` | 期望行为 |
|--------|-----------|-----------|---------| 
| `None`（大多数现有回调） | ❌ 继续 | ✅ 继续 | 继续 ✅ |
| `False` | ✅ 停止 | ✅ 停止 | 停止 ✅ |
| `0` | ❌ 继续 | ✅ 停止 | 继续 ✅ |
| `""` | ❌ 继续 | ✅ 停止 | 继续 ✅ |
| `[]` | ❌ 继续 | ✅ 停止 | 继续 ✅ |
| `True` | ❌ 继续 | ❌ 继续 | 继续 ✅ |

`is False` 确保只有显式的 `false` 才停止，最大程度向后兼容。

**Helen 用法示例**：

```helen
// 限制最多接收 5 个 chunk
设 count = 0
result = llm act "写一篇长文" on_chunk fn(chunk: str) {
    设 count = count + 1
    print(chunk)
    如果 count >= 5 { 返回 false }
}
```

---

### 7.2 Phase 2: cancel_event 贯穿 Runtime 层

**目标**：为 `act_stream()` 添加取消能力。

#### 7.2.1 ABC 签名变更

**文件**：`helen/runtime/llm_runtime.py` (L69-90)

```python
import threading

class LLMRuntime(ABC):
    def act_stream(self, prompt, model=None, temperature=1.0,
                   system_prompt=None, tools=None, max_turns=5,
                   history=None, dispatch_fn=None,
                   cancel_event: "threading.Event | None" = None,  # 新增
                   ) -> Iterator[dict[str, Any]]:
        # 默认实现不变 — cancel_event 被接受但忽略（同步回退）
        response = self.act(prompt, ...)
        if response and response.text:
            yield {"type": "content", "content": response.text}
```

`MockLLMRuntime` 继承默认实现，自动获得参数。所有现有测试不受影响。

#### 7.2.2 HttpLLMRuntime 同步流

**文件**：`helen/runtime/http_llm.py` — `act_stream()` (L902)

签名新增 `cancel_event`。两处插入检查：

```python
def act_stream(self, ..., cancel_event=None):
    ...
    while budget.consume():
        # ★ 检查点 A：工具调用轮次之间
        if cancel_event is not None and cancel_event.is_set():
            yield {"type": "error", "message": "Cancelled"}
            break

        ...
        with self._client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            for line_bytes in response.iter_lines():
                # ★ 检查点 B：SSE 迭代中
                if cancel_event is not None and cancel_event.is_set():
                    break    # with 块退出 → httpx 自动关闭连接
                ...
```

`break` 触发 `with` 块退出 → `response.__exit__()` → HTTP 连接自动关闭。无需手动清理。

#### 7.2.3 Protocol 更新

如有 `stream_contracts.py` 中 `StreamingLLMRuntime` Protocol，同步更新签名。

---

### 7.3 Phase 3: 解释器流式调用注册表

**目标**：解释器跟踪所有活跃的流式调用，支持编程式取消和 Ctrl+C 中断。

**文件**：`helen/interpreter/interpreter.py`

#### 7.3.1 新增 `_StreamingHandle`

```python
import threading
import uuid

class _StreamingHandle:
    """跟踪一次活跃的流式 LLM 调用。"""
    def __init__(self):
        self.call_id = str(uuid.uuid4())
        self.cancelled = threading.Event()
        self.done = threading.Event()
```

#### 7.3.2 Interpreter 注册表

`Interpreter.__init__()` 添加：

```python
self._streaming_calls: dict[str, _StreamingHandle] = {}
self._streaming_lock = threading.Lock()
```

#### 7.3.3 管理方法

```python
def _register_streaming_call(self) -> _StreamingHandle:
    handle = _StreamingHandle()
    with self._streaming_lock:
        self._streaming_calls[handle.call_id] = handle
    return handle

def _unregister_streaming_call(self, call_id: str) -> None:
    with self._streaming_lock:
        self._streaming_calls.pop(call_id, None)

def cancel_streaming_call(self, call_id: str) -> bool:
    with self._streaming_lock:
        handle = self._streaming_calls.get(call_id)
    if handle is None:
        return False
    handle.cancelled.set()
    return True

def get_current_streaming_call_id(self) -> str | None:
    with self._streaming_lock:
        for cid, h in self._streaming_calls.items():
            if not h.done.is_set():
                return cid
    return None

def cancel_all_streaming_calls(self) -> int:
    """取消所有活跃的流式调用。返回取消数量。"""
    count = 0
    with self._streaming_lock:
        for handle in self._streaming_calls.values():
            if not handle.done.is_set():
                handle.cancelled.set()
                count += 1
    return count
```

#### 7.3.4 核心中断逻辑

**文件**：`helen/interpreter/llm_mixin.py` — `_visit_llm_act_streaming()` 重构

```python
try:
    dispatch_fn = self._create_dispatch_fn()
    full_response, tool_calls_log, stream_usage = [], [], {}
    stream_handle = self._register_streaming_call()
    interrupted = False

    # 合并取消信号：stream_handle + 外部 cancel_event（spawn 场景）
    external_cancel = getattr(self, '_agent_cancel_event', None)

    try:
        for event in self.llm_runtime.act_stream(
            ...,
            cancel_event=stream_handle.cancelled,    # Phase 2 参数
        ):
            # 检查取消信号（stream_handle 或外部 cancel_event）
            if stream_handle.cancelled.is_set():
                interrupted = True
                break
            if external_cancel is not None and external_cancel.is_set():
                stream_handle.cancelled.set()    # 联动
                interrupted = True
                break

            event_type = event.get("type", "content")

            if event_type == "content":
                content = event.get("content", "")
                if content:
                    full_response.append(content)
                    if on_chunk_fn is not None:
                        chunk_result = on_chunk_fn(content)    # Phase 1
                        if chunk_result is False:
                            interrupted = True
                            break

            elif event_type == "tool_call":
                ...
                if on_chunk_fn is not None:
                    chunk_result = on_chunk_fn(progress)
                    if chunk_result is False:
                        interrupted = True
                        break

            elif event_type == "tool_result":
                ...
                if on_chunk_fn is not None:
                    chunk_result = on_chunk_fn(result_msg)
                    if chunk_result is False:
                        interrupted = True
                        break

            elif event_type == "usage":
                ...

            elif event_type == "error":
                ...
                break

    except KeyboardInterrupt:
        # Ctrl+C — 仅流式路径捕获，REPL 看不到
        interrupted = True
        stream_handle.cancelled.set()    # 通知 HTTP 层关闭连接

    finally:
        stream_handle.done.set()
        self._unregister_streaming_call(stream_handle.call_id)

    # on_complete 仅在不中断时调用
    if not interrupted and on_complete_fn is not None:
        on_complete_fn()

    # 记录历史（包含部分响应）
    full_text = "".join(full_response)
    if full_text or tool_calls_log:
        ...
        self._record_llm_response_to_history(stream_resp)

    # 审计日志
    if interrupted:
        self._log_llm_audit("act_stream", prompt, audit_start, agent_name, model,
                           response=full_text + " [interrupted]", ...)
    else:
        self._log_llm_audit("act_stream", prompt, audit_start, agent_name, model,
                           response=full_text, ...)

    # 返回（中断时返回部分响应）
    return full_text

except Exception as e:
    # KeyboardInterrupt 是 BaseException，不到这里
    self._log_llm_audit(..., error=str(e))
    self.errors.error(RUNTIME_ERROR, f"Streaming LLM call failed: {e}", node.span)
    return None
```

**关键语义**：

| 行为 | 说明 |
|------|------|
| `KeyboardInterrupt` 在内层捕获 | REPL 层永远看不到（流式路径） |
| `on_complete` 中断时不调用 | 中断 ≠ 完成 |
| 部分响应保留返回 | `full_text` 包含已收到的内容 |
| `except Exception` 不受影响 | `KeyboardInterrupt` 是 `BaseException` |
| `_agent_cancel_event` 联动 | spawn 场景，Channel cancel → 流式中断 |

#### 7.3.5 `_agent_cancel_event` 注入点

spawned interpreter 需要感知 Channel 的 `cancel_event`。在 `visit_spawn_expr` 中注入：

```python
# interpreter.py — visit_spawn_expr → run_spawned()

def run_spawned():
    try:
        spawned_interp = Interpreter(...)
        spawned_interp.environment = env_snapshot
        spawned_interp._agents = dict(self._agents)
        spawned_interp._functions = dict(self._functions)

        # ★ 注入 Channel 的 cancel_event
        spawned_interp._agent_cancel_event = spawned_endpoint.cancel_event

        new_call.accept(spawned_interp)
    except Exception as e:
        ...
```

---

### 7.4 Phase 4: REPL 存活

**目标**：Ctrl+C 中断当前 `llm act`，REPL 继续运行，状态完整保留。

**文件**：`helen/cli/repl.py`

在两处 `_execute_input()` 调用点外添加 `except KeyboardInterrupt`：

**Site 1 — 多行自动执行**（L588-598）：

```python
if buffer.strip():
    try:
        success, result = _execute_input(buffer, interp, analyzer)
        if success:
            if result is not None:
                print(repr(result))
        else:
            print(f"Error: {result}", file=sys.stderr)
    except KeyboardInterrupt:
        # 取消所有活跃的流式调用
        if hasattr(interp, 'cancel_all_streaming_calls'):
            interp.cancel_all_streaming_calls()
        print("\n⚡ 已中断 — 状态已保留")
    except Exception as e:
        print(f"Internal Error: {e}", file=sys.stderr)
```

**Site 2 — 单行执行**（L610-618）：同上。

**安全网语义**：

- 流式路径的 `KeyboardInterrupt` 已在 Phase 3.4 内层捕获，正常不会到 REPL 层
- REPL 层的 `except KeyboardInterrupt` 是兜底，覆盖同步 `act()` 阻塞等其他场景
- 外层 `except KeyboardInterrupt`（L624）保持不变，仅作用于 `input()` 时的 Ctrl+C（退出 REPL）

---

### 7.5 Phase 5: stdlib 函数

**目标**：暴露取消 API 给 Helen 程序。

#### 7.5.1 新文件 `helen/stdlib/llm_control.py`

```python
"""大模型调用运行时控制。"""

import threading
from typing import Any

_interpreter_ref: Any = None
_ref_lock = threading.Lock()


def _set_interpreter_ref(interp: Any) -> None:
    global _interpreter_ref
    with _ref_lock:
        _interpreter_ref = interp


def _cancel_llm_call(call_id: str) -> bool:
    """取消一次进行中的大模型调用。"""
    if _interpreter_ref is None:
        return False
    return _interpreter_ref.cancel_streaming_call(call_id)


def _current_llm_call_id() -> str | None:
    """返回当前进行中的大模型调用 ID，无则返回 null。"""
    if _interpreter_ref is None:
        return None
    return _interpreter_ref.get_current_streaming_call_id()


def _cancel_all_llm_calls() -> int:
    """取消所有进行中的大模型调用。返回取消数量。"""
    if _interpreter_ref is None:
        return 0
    return _interpreter_ref.cancel_all_streaming_calls()
```

#### 7.5.2 注册到 stdlib

**文件**：`helen/stdlib/__init__.py`

```python
from helen.stdlib.llm_control import (
    _cancel_llm_call, _current_llm_call_id, _cancel_all_llm_calls, _set_interpreter_ref,
)

# _register_builtins() 中：
BuiltinFunction("cancel_llm_call", "取消一次进行中的大模型调用",
                "cancel_llm_call(call_id)", _cancel_llm_call, "llm"),
BuiltinFunction("current_llm_call_id", "获取当前大模型调用 ID",
                "current_llm_call_id()", _current_llm_call_id, "llm"),
BuiltinFunction("cancel_all_llm_calls", "取消所有进行中的大模型调用",
                "cancel_all_llm_calls()", _cancel_all_llm_calls, "llm"),
```

**中文别名**（`locales/zh.py`）：

```python
"cancel_llm_call": "取消大模型调用",
"current_llm_call_id": "当前大模型调用id",
"cancel_all_llm_calls": "取消所有大模型调用",
```

#### 7.5.3 连接解释器引用

**文件**：`helen/interpreter/interpreter.py` — `_setup_stdlib()`

```python
from helen.stdlib.llm_control import _set_interpreter_ref
_set_interpreter_ref(self)
```

**Helen 用法示例**：

```helen
// 从另一个 agent 中取消当前调用
设 id = 当前大模型调用id()
如果 id != null {
    取消大模型调用(id)
}

// 取消所有进行中的调用
取消所有大模型调用()
```

---

### 7.6 Phase 6: spawn 取消

**目标**：`endpoint.cancel()` 能中断 spawned agent 内正在进行的 `llm act` 流式。

**策略**：复用 v1.18 Channel 已有的 `cancel_event`，通过 Phase 3 的 `_agent_cancel_event` 注入到 spawned interpreter，在流式循环中检查。

**这是 v1.18 相比 v1.17 的最大简化** — 不需要新建线程跟踪、不需要 bridge 线程、不需要额外 Event。

#### 7.6.1 修改 `visit_spawn_expr`

**文件**：`helen/interpreter/interpreter.py` (L2359-2462)

```python
def run_spawned():
    try:
        spawned_interp = Interpreter(
            errors=errors,
            llm_runtime=llm_runtime,
            import_resolver=import_resolver,
            program_args=program_args,
            transcript_store_enabled=transcript_enabled,
        )
        spawned_interp.environment = env_snapshot
        spawned_interp._agents = dict(self._agents)
        spawned_interp._functions = dict(self._functions)

        # ★ 注入 Channel cancel_event — 主线程调用 endpoint.cancel() 时
        # 此 Event 被设置，spawned interpreter 的流式路径检查它
        spawned_interp._agent_cancel_event = spawned_endpoint.cancel_event

        new_call.accept(spawned_interp)
    except Exception as e:
        try:
            spawned_endpoint.send({"__error__": True, "message": str(e)})
        except Exception:
            pass
    finally:
        spawned_endpoint.close()
```

#### 7.6.2 流式路径检查（Phase 3 已包含）

`_visit_llm_act_streaming` 中的外部 cancel_event 检查（Phase 3.4）已在每个 event 循环迭代中检查 `self._agent_cancel_event`：

```python
external_cancel = getattr(self, '_agent_cancel_event', None)
...
if external_cancel is not None and external_cancel.is_set():
    stream_handle.cancelled.set()    # 联动 stream_handle → act_stream 也停止
    interrupted = True
    break
```

#### 7.6.3 端到端流

```
主线程                          后台 spawned agent
  │                                  │
  │ spawn Worker("task")             │
  │ ──────────────────────────────→  │ 启动
  │ ← main_endpoint                  │
  │                                  │ llm act "task" on_chunk ...
  │                                  │ ← 流式中...
  │                                  │
  │ endpoint.cancel()                │
  │ ──→ cancel_event.set() ────────→ │ _agent_cancel_event.is_set() == True
  │                                  │ → stream_handle.cancelled.set()
  │                                  │ → act_stream cancel_event check → break
  │                                  │ → HTTP 连接关闭
  │                                  │ → interrupted = True
  │                                  │ → spawned_endpoint.close()
  │ ← receive() == None              │ 线程退出
  │   (通道已关闭)                     │
```

#### 7.6.4 与 `on_chunk` 协作的完整示例

```helen
agent Worker(task: str, mailbox: Channel) {
    main {
        设 count = 0
        result = llm act task on_chunk fn(chunk: str) {
            设 count = count + 1
            mailbox.send({"type": "chunk", "content": chunk})
            // 不返回 false — 取消由主线程通过 mailbox.cancel() 控制
        }
        mailbox.send({"type": "done", "result": result})
    }
}

// 主线程
设 ch = spawn Worker("写一篇长文")

// 实时接收进度
循环 {
    设 msg = ch.try_receive()
    如果 msg == null {
        // 做其他事...
        继续
    }
    如果 msg["type"] == "done" {
        print("完成: " + msg["result"])
        跳出循环
    }
    print(msg["content"])
}

// 或者：用 mailbox_select 等待多个 worker
设 w1 = spawn Worker("策略A")
设 w2 = spawn Worker("策略B")
设 winner = mailbox_select([w1, w2])
print("先完成: " + winner["message"])

// 取消另一个
如果 winner["endpoint"] == w1 {
    w2.cancel()    // ← cancel_event.set() → 后台流式中断
} 否则 {
    w1.cancel()
}
```

---

### 7.7 Phase 7: `spawnagent` → `spawn`/`分生` 关键字重命名

**目标**：将 v1.18 的关键字 `spawnagent`/`生成` 重命名为更简洁、更符合 Helen 关键字风格的 `spawn`/`分生`。

**动机**：

| 维度 | `spawnagent`/`生成`（现状） | `spawn`/`分生`（目标） |
|------|---------------------------|----------------------|
| 长度 | 11 字母，Helen 唯一 camelCase 关键字 | 5 字母，与其他关键字长度一致 |
| 风格 | 像函数名，不像关键字 | 符合 Helen 短单词关键字风格 |
| 中文语义 | `生成` = generate，太泛 | `分生` = 分出一部分生成新个体（细胞分裂），精确 |
| 编程先例 | 无 | Erlang `spawn` 是消息传递并发的经典术语 |
| 隐喻 | 无 | agent 声明如同分生组织，每次 spawn 是一次细胞分裂 |

#### 7.7.1 改动清单

| 文件 | 改动 |
|------|------|
| `helen/core/tokens.py` | 关键字 `spawnagent` → `spawn`；中文 `生成` → `分生` |
| `helen/core/parser.py` | `parse_spawnagent_expr()` → `parse_spawn_expr()`；token 匹配更新 |
| `helen/core/ast.py` | `SpawnagentExprNode` → `SpawnExprNode` |
| `helen/interpreter/interpreter.py` | `visit_spawnagent_expr()` → `visit_spawn_expr()` |
| `helen/stdlib/locales/zh.py` | `"spawnagent": "生成"` → `"spawn": "分生"` |
| `helen/semantic/analyzer.py` | `visit_spawnagent_expr()` → `visit_spawn_expr()`（如存在） |
| `helen/lsp/` | 补全/定义跳转中 `spawnagent` → `spawn` |
| 测试文件 | 重命名 + 内容更新 |
| 文档/技能 | wiki、教程、SKILL.md 中所有 `spawnagent` → `spawn` |

#### 7.7.2 Token 变更

```python
# helen/core/tokens.py

# 删除：
# "spawnagent": Token.SPAWNAGENT,
# "生成": Token.SPAWNAGENT,

# 新增：
"spawn": Token.SPAWN,
"分生": Token.SPAWN,
```

关键字总数不变：89 个（英文 44.5 + 中文 44.5）。

#### 7.7.3 AST 节点重命名

```python
# helen/core/ast.py

# 删除：
# class SpawnagentExprNode(ExpressionNode):
#     call: CallNode

# 新增：
class SpawnExprNode(ExpressionNode):
    """spawn Agent(args) — 启动 agent 实例，返回 Channel。"""
    call: CallNode
```

#### 7.7.4 向后兼容

`spawnagent`/`生成` 在 v1.18 中首次引入，尚无大量存量代码。重命名的破坏性可控：

| 策略 | 说明 |
|------|------|
| **硬切换** | 直接替换，旧代码编译报错 | 简洁，无遗留负担 |
| **过渡期别名** | 保留 `spawnagent`/`生成` 为废弃别名，编译时发出 deprecation 警告 | 向后兼容，但增加维护负担 |

**推荐**：硬切换。v1.18 刚发布，用户迁移成本低。在 CHANGELOG 中明确标注为破坏性变更。

#### 7.7.5 测试

```python
class TestSpawnKeyword:
    def test_spawn_keyword_parses(self):
        """`spawn Agent("task")` 解析为 SpawnExprNode"""

    def test_fensheng_chinese_keyword_parses(self):
        """`分生 Agent("任务")` 解析为 SpawnExprNode"""

    def test_spawnagent_removed(self):
        """`spawnagent` 不再是有效关键字"""

    def test_shengcheng_removed(self):
        """`生成` 不再是 spawn 的中文关键字"""

    def test_spawn_returns_channel(self):
        """spawn 返回 ChannelEndpoint（语义不变）"""

    def test_spawn_with_channel_param(self):
        """spawn Agent(task, mailbox) 自动注入 Channel 参数"""

    def test_spawn_cancel_still_works(self):
        """spawn + cancel 端到端（重命名后功能不变）"""

    def test_spawn_in_agent_main(self):
        """在 agent main 中使用 spawn"""
```

#### 7.7.6 与中断方案的关系

Phase 7 是**纯重命名**，不影响中断逻辑。可以与 Phase 1-6 并行开发：

- 如果 Phase 7 先完成：Phase 6 直接基于 `visit_spawn_expr` 开发
- 如果 Phase 6 先完成：Phase 7 重命名时连带更新 cancel_event 注入代码

推荐：**Phase 7 与 Phase 6 同时实施**，因为两者都改动 `visit_spawn_expr`，合并减少冲突。

---

## 8. 向后兼容性

| 场景 | 影响 | 分析 |
|------|------|------|
| 现有 `on_chunk` 返回 `None` | ✅ 不受影响 | `None is False` → `False`，继续流式 |
| `MockLLMRuntime` 继承默认 `act_stream()` | ✅ 自动获得参数 | `cancel_event` 可选，默认 `None` |
| 自定义 `LLMRuntime` 覆盖 `act_stream()` | ⚠️ 需更新签名 | ABC 已添加参数。不更新会 `TypeError`。可在调用处 `try/except TypeError` 兼容 |
| REPL Ctrl+C 退出 | ✅ 不变 | `input()` 处 Ctrl+C 仍退出 REPL |
| 现有 Helen 程序 | ✅ 无语法/语义变更 | 新 stdlib 函数不与现有名称冲突 |
| `spawnagent`/`生成` 旧代码 | ⚠️ 破坏性（Phase 7） | 关键字重命名为 `spawn`/`分生`。v1.18 刚发布，存量少 |
| spawn 程序 | ✅ 不变 | 无 cancel 调用时行为完全一致 |
| Channel 程序（非 spawn） | ✅ 不变 | Channel cancel 本就只设 Event，现在只是流式路径多了一个检查 |

### 自定义 LLMRuntime 兼容方案

```python
# llm_mixin.py — 传入 cancel_event 前，用 try/except TypeError 回退
try:
    stream = self.llm_runtime.act_stream(..., cancel_event=stream_handle.cancelled)
except TypeError:
    stream = self.llm_runtime.act_stream(...)    # 不支持 cancel_event → 回退
```

推荐此方案 — 零开销，只在异常路径才付出代价。

---

## 9. 风险矩阵

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|---------| 
| `KeyboardInterrupt` 在历史更新/审计期间击中 | 中 | 高 | `try/except KeyboardInterrupt` 仅包裹流式循环，历史/日志在循环之后 |
| 工具执行中取消 | 中 | 低 | 当前工具执行完成后再检查 cancel（工具不可抢占） |
| `_StreamingHandle` 泄漏（未 unregister） | 低 | 低 | `finally` 块保证 unregister。Interpreter 销毁时 dict 随之释放 |
| 自定义 `LLMRuntime` 不兼容新参数 | 低 | 低 | `try/except TypeError` 回退 |
| `_agent_cancel_event` 与 `stream_handle.cancelled` 竞态 | 低 | 低 | 两者都是 `set()` 操作，幂等；先 set 者赢 |
| spawn 取消后 HTTP 连接残留 | 低 | 中 | `cancel_event` 检查在 `iter_lines()` 循环内，break 后 `with` 块退出自动关闭 |
| REPL `except KeyboardInterrupt` 吞掉非流式中断 | 低 | 低 | 仅影响同步 `act()` 阻塞场景；打印提示后 REPL 继续 |
| 多个 spawn 同时流式，cancel_all 影响所有 | 低 | 中 | 文档说明 `cancel_all_llm_calls()` 语义；通常用户只需 cancel 单个 endpoint |

---

## 10. 测试方案

### 10.1 新增测试文件

| 文件 | 测试数 | 覆盖 |
|------|--------|------|
| `tests/interpreter/test_streaming_interrupt.py` | ~12 | Phase 1-3 全覆盖 |
| `tests/runtime/test_http_llm_cancel.py` | ~3 | Phase 2 HTTP 层 |
| `tests/cli/test_repl_interrupt.py` | ~2 | Phase 4 REPL 存活 |
| `tests/interpreter/test_spawn_cancel.py` | ~5 | Phase 6 spawn 取消 |
| `tests/language/test_spawn_keyword.py` | ~8 | Phase 7 关键字重命名 |

### 10.2 测试用例明细

#### `tests/interpreter/test_streaming_interrupt.py`

```python
class TestOnChunkReturnValue:
    """Phase 1: on_chunk 返回值停止流式"""

    def test_on_chunk_returns_false_stops_streaming(self):
        """on_chunk 返回 False → 流式停止"""

    def test_on_chunk_returns_none_continues(self):
        """on_chunk 返回 None → 继续（向后兼容）"""

    def test_on_chunk_returns_zero_continues(self):
        """on_chunk 返回 0 → 继续（仅 False 停止）"""

    def test_on_chunk_returns_empty_string_continues(self):
        """on_chunk 返回 "" → 继续"""

    def test_on_chunk_returns_false_on_tool_call(self):
        """tool_call 事件中 on_chunk 返回 False → 停止"""

    def test_on_chunk_returns_false_on_tool_result(self):
        """tool_result 事件中 on_chunk 返回 False → 停止"""


class TestKeyboardInterrupt:
    """Phase 3-4: Ctrl+C 中断"""

    def test_keyboard_interrupt_returns_partial(self):
        """Ctrl+C 中断流式 → 返回部分响应"""

    def test_keyboard_interrupt_preserves_state(self):
        """Ctrl+C 后变量/函数/agent 保留"""

    def test_keyboard_interrupt_skips_on_complete(self):
        """中断时 on_complete 不调用"""

    def test_keyboard_interrupt_sets_cancel_event(self):
        """Ctrl+C → cancel_event.set() → HTTP 连接关闭"""


class TestProgrammaticCancel:
    """Phase 5: 编程式取消"""

    def test_cancel_llm_call_stops_streaming(self):
        """cancel_llm_call(id) → 流式停止"""

    def test_current_llm_call_id_during_streaming(self):
        """current_llm_call_id() 返回活跃调用 ID"""

    def test_current_llm_call_id_none_when_idle(self):
        """无活跃调用时返回 None"""

    def test_cancel_nonexistent_returns_false(self):
        """无效 ID → 返回 False"""

    def test_cancel_all_llm_calls(self):
        """cancel_all_llm_calls() 取消所有活跃调用"""
```

#### `tests/runtime/test_http_llm_cancel.py`

```python
class TestHttpLLMCancelEvent:
    def test_act_stream_accepts_cancel_event(self):
        """签名兼容"""

    def test_act_stream_stops_on_cancel(self):
        """cancel_event.set() → 停止 yield"""

    def test_act_stream_yields_cancel_error(self):
        """cancel_event.set() → yield error event"""
```

#### `tests/cli/test_repl_interrupt.py`

```python
class TestReplInterrupt:
    def test_repl_survives_interrupt_during_streaming(self):
        """REPL 不因 Ctrl+C 退出"""

    def test_repl_state_preserved_after_interrupt(self):
        """中断后 let x = 42 仍可用"""
```

#### `tests/interpreter/test_spawn_cancel.py`

```python
class TestSpawnCancel:
    def test_cancel_event_propagates_to_spawned_interpreter(self):
        """endpoint.cancel() → spawned interpreter 感知 cancel_event"""

    def test_cancel_stops_streaming_in_spawned_agent(self):
        """spawned agent 的 llm act 流式被 cancel 中断"""

    def test_cancel_closes_http_connection(self):
        """cancel → act_stream break → httpx with 块退出"""

    def test_spawned_agent_sends_nothing_after_cancel(self):
        """cancel 后 spawned agent 不再发送消息"""

    def test_main_thread_state_preserved_after_cancel(self):
        """cancel spawned agent 后主线程状态不受影响"""
```

#### `tests/language/test_spawn_keyword.py`

```python
class TestSpawnKeyword:
    """Phase 7: spawnagent → spawn/分生 关键字重命名"""

    def test_spawn_keyword_parses(self):
        """`spawn Agent("task")` 解析为 SpawnExprNode"""

    def test_fensheng_chinese_keyword_parses(self):
        """`分生 Agent("任务")` 解析为 SpawnExprNode"""

    def test_spawnagent_removed(self):
        """`spawnagent` 不再是有效关键字"""

    def test_shengcheng_removed(self):
        """`生成` 不再是 spawn 的中文关键字"""

    def test_spawn_returns_channel(self):
        """spawn 返回 ChannelEndpoint（语义不变）"""

    def test_spawn_with_channel_param(self):
        """spawn Agent(task, mailbox) 自动注入 Channel 参数"""

    def test_spawn_cancel_still_works(self):
        """spawn + cancel 端到端（重命名后功能不变）"""

    def test_spawn_in_agent_main(self):
        """在 agent main 中使用 spawn"""
```

### 10.3 端到端验证

```bash
# 1. on_chunk 返回 false 停止
cat > /tmp/test_on_chunk.helen << 'EOF'
agent Test(prompt: str) {
    main {
        设 count = 0
        result = llm act prompt on_chunk fn(chunk: str) {
            设 count = count + 1
            print(chunk)
            如果 count >= 3 { 返回 false }
        }
        print("收到: " + result)
    }
}
Test("从 1 数到 100")
EOF
helen /tmp/test_on_chunk.helen
# 预期: 只打印前 3 个 chunk 后停止

# 2. REPL Ctrl+C 存活
helen repl
>>> 设 x = 42
>>> llm act "写一篇长文" on_chunk fn(chunk) { print(chunk) }
（流式中... Ctrl+C）
⚡ 已中断 — 状态已保留
>>> print(x)
42

# 3. spawn 取消
cat > /tmp/test_spawn_cancel.helen << 'EOF'
agent Worker(task: str, mailbox: Channel) {
    main {
        result = llm act task on_chunk fn(chunk: str) {
            mailbox.send(chunk)
        }
        mailbox.send({"done": true})
    }
}

设 ch = spawn Worker("从 1 数到 10000")
// 等一小会让流式开始
设 msg = ch.receive()
print("收到: " + 字符串(msg))
// 取消
ch.cancel()
print("已取消")
// 通道应已关闭
设 next = ch.try_receive()
print("取消后: " + 字符串(next))
EOF
helen /tmp/test_spawn_cancel.helen

# 4. mailbox_select + cancel 另一个
cat > /tmp/test_mailbox_select.helen << 'EOF'
agent StrategyA(mailbox: Channel) {
    main {
        result = llm act "从 A 策略分析"
        mailbox.send({"winner": "A", "result": result})
    }
}
agent StrategyB(mailbox: Channel) {
    main {
        result = llm act "从 B 策略分析"
        mailbox.send({"winner": "B", "result": result})
    }
}

设 a = spawn StrategyA()
设 b = spawn StrategyB()
设 winner = mailbox_select([a, b])
print("先完成: " + winner["message"]["winner"])

// 取消另一个
如果 winner["endpoint"] == a {
    b.cancel()
    print("已取消 B")
} 否则 {
    a.cancel()
    print("已取消 A")
}
EOF
helen /tmp/test_mailbox_select.helen

# 5. 全量测试
pytest tests/interpreter/test_streaming_interrupt.py -v
pytest tests/runtime/test_http_llm_cancel.py -v
pytest tests/cli/test_repl_interrupt.py -v
pytest tests/interpreter/test_spawn_cancel.py -v
pytest tests/language/test_spawn_keyword.py -v
pytest                                          # 无回归
flake8 helen/                                   # lint
```

---

## 11. 实施路线图

```
Phase 1 ─── on_chunk 返回值 ──────────────────────── 1-2 天
  │  llm_mixin.py（3 处改动）
  │  测试: 6 个
  │  可独立交付 ✅
  │
Phase 2 ─── cancel_event 贯穿 Runtime ────────────── 1-2 天
  │  llm_runtime.py + http_llm.py
  │  测试: 3 个
  │  可独立交付 ✅
  │
Phase 3 ─── 解释器注册表 + 核心中断逻辑 ─────────────── 2-3 天
  │  interpreter.py + llm_mixin.py
  │  测试: 8 个
  │  依赖 Phase 2
  │
Phase 4 ─── REPL 存活 ─────────────────────────────── 0.5 天
  │  repl.py
  │  测试: 2 个
  │  依赖 Phase 3
  │
Phase 5 ─── stdlib 函数 ───────────────────────────── 1 天
  │  llm_control.py + __init__.py + locales/zh.py
  │  测试: 5 个
  │  依赖 Phase 3
  │
Phase 6 ─── spawn 取消 ───────────────────────────── 1 天
  │  interpreter.py（visit_spawn_expr 注入 cancel_event）
  │  测试: 5 个
  │  依赖 Phase 3 + Phase 2
  │  ★ v1.18 简化：复用 Channel cancel_event，无需新建跟踪机制
  │
Phase 7 ─── spawnagent → spawn/分生 关键字重命名 ──── 1 天
  │  tokens.py + parser.py + ast.py + interpreter.py + stdlib/locales/zh.py
  │  测试: ~8 个（关键字解析、AST 节点、解释器、中文别名）
  │  可与 Phase 1-6 并行（不影响中断逻辑）
  │  ★ 纯重命名，无语义变化
```

**总计**：7-10 天（Phase 1-7）。Phase 7 可与 Phase 1-6 并行。

**对比 v1.0**：v1.0 预估 6-10 天（含 Phase 6 detach + Phase 7 async/await 预留）。v2.1 少了 detach 跟踪开销，新增 Phase 7 关键字重命名（1 天）。

---

## 12. 开放问题

| 编号 | 问题 | 当前建议 | 备选 |
|------|------|---------|------|
| Q1 | 中断后 `on_complete` 是否应收到 `interrupted` 标志？ | 不调用（中断 ≠ 完成） | 调用并传入 `interrupted=true` 参数 |
| Q2 | 自定义 `LLMRuntime` 不兼容 `cancel_event` 参数如何处理？ | `try/except TypeError` 回退 | `inspect.signature` 预检查 |
| Q3 | 是否提供 `cancel_all_llm_calls()` stdlib？ | ✅ 提供（已纳入 Phase 5） | 不提供 |
| Q4 | 中断后的部分响应是否应写入 transcript？ | 是，标记 `[interrupted]` | 不写入 |
| Q5 | `_agent_cancel_event` 是否应改为 Interpreter 构造参数？ | 暂用属性注入（灵活，不改构造函数） | 改为 `__init__(cancel_event=...)` |
| Q6 | spawn 取消后是否需要 join 等待线程退出？ | 不 join（daemon 线程自行退出） | join(timeout=3s) |
| Q7 | `ErrorReporter` 共享给 spawned interpreter 是否需加锁？ | 暂不加（GIL 保证 append 原子性） | 添加 `threading.Lock` |
| Q8 | Channel cancel 后是否应区分 "正常完成" 和 "被取消"？ | `try_receive()` 返回 None 表示关闭；`is_closed()` 检查状态 | 新增 `is_cancelled()` 方法 |
| Q9 | `spawnagent` → `spawn` 重命名是否提供过渡期别名？ | 硬切换（v1.18 刚发布，存量少） | 保留 `spawnagent`/`生成` 为废弃别名，编译时发 deprecation 警告 |

---

## 附录 A: v1.0 → v2.1 变更摘要

| 维度 | v1.0（v1.17 基础） | v2.1（v1.18 基础） |
|------|-------------------|-------------------|
| **并发模型** | 主线程 + detach + async/await | 主线程 + spawn |
| **Phase 数量** | 7 个（含 async/await 预留） | 7 个（Phase 7 = 关键字重命名） |
| **后台线程跟踪** | 新建 `_detach_threads` 列表 + `_detach_cancel_event` | 复用 Channel `cancel_event`（已存在） |
| **取消信号传递** | 手动 bridge 线程连接两个 Event | `_agent_cancel_event` 属性注入 |
| **Phase 6 复杂度** | 🔴 高（线程跟踪 + bridge + join 决策） | 🟢 低（一行属性注入） |
| **Phase 7** | async/await 预留（不实现） | `spawnagent` → `spawn`/`分生` 重命名 |
| **多 agent 取消** | 不支持 | `endpoint.cancel()` 一对一 + `cancel_all_llm_calls()` |
| **多 agent 选择** | 不支持 | `mailbox_select` 竞争模式 |
| **删除的文件** | — | 无需新建 async_interpreter.py 相关测试 |
| **新增的文件** | `llm_control.py` + 4 个测试文件 | `llm_control.py` + 4 个测试文件（相同） |
| **总工期** | 6-10 天 | 7-10 天（Phase 7 可并行） |
| **关键简化** | — | Channel cancel_event 已存在，无需新建取消基础设施 |

### 核心架构差异

```
v1.0（detach 模型）                    v2.1（spawn 模型）
─────────────────                     ────────────────
主线程                                 主线程
  │                                     │
  ├─ detach Worker()                    ├─ ch = spawn Worker()
  │   └─ daemon 线程                     │   └─ daemon 线程 + Channel
  │       └─ 新 Interpreter              │       └─ 新 Interpreter
  │           └─ ❌ 无 cancel 感知        │           └─ ✅ _agent_cancel_event
  │                                     │
  ├─ ❌ 无返回值（None）                  ├─ ✅ 返回 ChannelEndpoint
  ├─ ❌ 无双向通信                        ├─ ✅ send/receive/try_receive
  ├─ ❌ 需新建线程跟踪列表                  ├─ ✅ 复用 Channel cancel_event
  └─ ❌ 需 bridge 线程连接 Event          └─ ✅ 直接属性注入
```
