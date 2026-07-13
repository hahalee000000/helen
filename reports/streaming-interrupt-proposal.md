# Helen 流式推理中断方案

> 版本：v1.0 草案  
> 日期：2026-07-13  
> 状态：待评审

---

## 目录

1. [问题陈述](#1-问题陈述)
2. [设计目标](#2-设计目标)
3. [三种调用形式分析](#3-三种调用形式分析)
4. [中断机制总览](#4-中断机制总览)
5. [现有架构](#5-现有架构)
6. [方案详细设计](#6-方案详细设计)
   - 6.1 [Phase 1: on_chunk 返回值中断](#61-phase-1-on_chunk-返回值中断)
   - 6.2 [Phase 2: cancel_event 贯穿 Runtime 层](#62-phase-2-cancel_event-贯穿-runtime-层)
   - 6.3 [Phase 3: 解释器流式调用注册表](#63-phase-3-解释器流式调用注册表)
   - 6.4 [Phase 4: REPL 存活](#64-phase-4-repl-存活)
   - 6.5 [Phase 5: stdlib 函数](#65-phase-5-stdlib-函数)
   - 6.6 [Phase 6: detach 中断](#66-phase-6-detach-中断)
   - 6.7 [Phase 7: async/await（预留）](#67-phase-7-asyncawait预留)
7. [向后兼容性](#7-向后兼容性)
8. [风险矩阵](#8-风险矩阵)
9. [测试方案](#9-测试方案)
10. [实施路线图](#10-实施路线图)
11. [开放问题](#11-开放问题)

---

## 1. 问题陈述

Helen 的 `llm act` 流式推理目前无法中途停止，存在三个具体缺陷：

| 缺陷 | 影响 |
|------|------|
| `on_chunk` 回调返回值被丢弃 | 用户代码无法请求中断 |
| Ctrl+C 退出整个 REPL | 所有变量、函数、agent 定义丢失 |
| `cancel_llm_call()` 未接入流式路径 | 编程式取消仅对同步 `act()` 有效，流式无效 |

此外，`detach`（守护线程）和 `async call`/`await`（异步任务）两种并发调用形式存在额外的中断困境：

- **detach**：`KeyboardInterrupt` 只在主线程抛出，daemon 线程无法感知，Ctrl+C 只能杀死整个进程
- **async/await**：当前 async 路径根本不走流式（`AsyncLLMInterpreter` 调用 `act_async()` 而非 `act_stream_async()`），`on_chunk` 在 async 中阻塞 event loop

---

## 2. 设计目标

| 目标 | 说明 |
|------|------|
| **三层中断** | 回调返回值、Ctrl+C 信号、编程式 API，覆盖所有场景 |
| **REPL 存活** | Ctrl+C 中断当前 `llm act`，保留所有运行时状态 |
| **协议一致** | 三种调用形式（主线程、detach、async）共享相同的中断语义 |
| **向后兼容** | 现有 Helen 程序无需任何修改 |
| **渐进实施** | 按 Phase 分阶段交付，每个 Phase 可独立验证 |

---

## 3. 三种调用形式分析

### 3.1 主线程 `llm act`（直接流式）

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

### 3.2 `detach`（守护线程）

```helen
detach Worker("background-task")
// Worker 在独立线程中运行，拥有独立 Interpreter 实例
```

**现状**：
- `visit_detach_stmt`（`interpreter.py:2428-2472`）创建 daemon 线程，运行全新 `Interpreter`
- 返回 `None` — 无线程句柄，无法 join/cancel
- `KeyboardInterrupt` **只在主线程抛出**，daemon 线程收不到
- 主线程 Ctrl+C → 只能杀进程，daemon 随之死亡

| 维度 | 评估 |
|------|------|
| 实现难度 | 🟡 中 — 需跟踪线程、传递 cancel Event |
| 中断机制 | 必须用 `threading.Event` 显式通知 |
| 状态一致性 | 🟡 主线程不受影响；detach 内部部分响应丢失（detach 返回 `None`） |
| HTTP 清理 | 🟡 cancel Event 需穿透到 detached interpreter 的 `act_stream` |
| stdout 交错 | 🔴 主线程和 detach 线程同时 `print()` 输出交错 |
| 共享状态 | 🟡 `SharedStore` 有 RLock，但中断时可能留中间状态 |

**关键取舍**：

| 选择 | 利 | 弊 |
|------|---|---|
| Ctrl+C 立即取消 + join 等待 | 干净退出，无悬挂连接 | "fire-and-forget" 语义被打破 |
| Ctrl+C 设 Event + 不 join | REPL 立即恢复，detach 自行退出 | 无法保证 detach 何时真正停止 |
| 不处理（保持现状） | 零改动 | 悬挂 HTTP 连接；不符合 REPL 存活目标 |

### 3.3 `async call` / `await`（异步任务）

```helen
let t1 = async AgentA("task1")
let t2 = async AgentB("task2")
await [t1, t2]
```

**现状**：
- `visit_async_call_expr`（`interpreter.py:2474-2489`）返回 `Task.pending(...)`，延迟到 `await` 执行
- `AsyncLLMInterpreter.visit_llm_act_expr_async`（`async_interpreter.py:138-178`）调用 `act_async()`（**非流式**）
- `act_stream_async()`（`http_llm.py:1429`）已定义但**从未被调用**
- `on_chunk` 在 async 路径中走 sync fallback，**阻塞 event loop** — 已有 bug
- `Task` 无 `cancel()` 方法，无取消原语

| 维度 | 评估 |
|------|------|
| 实现难度 | 🔴 高 — 需新增异步流式路径、Task 取消、event loop 取消传播 |
| 中断机制 | 需 per-task `asyncio.Event` + `asyncio.TaskGroup` 语义 |
| 状态一致性 | 🟡 Promise.all 语义 — 一个取消，其他怎么办？ |
| HTTP 清理 | 🔴 多并发流式连接同时取消，逐一关闭 |
| stdout 交错 | 🔴 多 async task 的 `on_chunk` 并发打印 |
| 风险 | 高，涉及 `async_interpreter.py`、`task.py`、`_await_tasks` 重构 |

### 3.4 三种形式对比总结

| 调用形式 | 实现难度 | 风险 | 建议 |
|----------|---------|------|------|
| 主线程 `llm act` | 🟢 低 | 极低 | ✅ 本次实现 |
| `detach` | 🟡 中 | 中 | ✅ 本次实现（设 Event + 不 join） |
| `async call`/`await` | 🔴 高 | 高 | ⏳ 本次仅签名就位，后续独立实现 |

---

## 4. 中断机制总览

```
┌─────────────────────────────────────────────────────────────┐
│                    用户触发中断                                │
│                                                             │
│  ① on_chunk 返回 false    ② Ctrl+C         ③ cancel_llm_call(id) │
│       ↓                      ↓                    ↓          │
│  break 出 for-event 循环   KeyboardInterrupt     threading.Event.set() │
│       ↓                      ↓                    ↓          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │        _visit_llm_act_streaming (llm_mixin.py)       │   │
│  │  • interrupted = True                                │   │
│  │  • stream_handle.cancelled.set()                     │   │
│  │  • break 出流式循环                                    │   │
│  │  • 跳过 on_complete                                  │   │
│  │  • 返回部分响应                                        │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         ↓                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           act_stream (http_llm.py)                    │   │
│  │  • cancel_event.is_set() → break                     │   │
│  │  • with 块退出 → httpx 自动关闭连接                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              REPL (repl.py)                           │   │
│  │  • except KeyboardInterrupt → 打印提示，继续循环          │   │
│  │  • 所有变量/函数/agent 状态保留                           │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. 现有架构

### 5.1 关键文件与行号

| 文件 | 行号 | 功能 |
|------|------|------|
| `helen/interpreter/llm_mixin.py` | L420-561 | `_visit_llm_act_streaming()` — 流式循环核心 |
| `helen/interpreter/llm_mixin.py` | L496, L505, L513 | `on_chunk_fn(content)` — 返回值被丢弃 |
| `helen/runtime/http_llm.py` | L902-1290 | `act_stream()` — 同步 SSE 流 |
| `helen/runtime/http_llm.py` | L1001-1068 | `with self._client.stream(...)` + `for line_bytes in response.iter_lines()` |
| `helen/runtime/http_llm.py` | L1429-1647 | `act_stream_async()` — 异步 SSE 流（**未被调用**） |
| `helen/runtime/llm_runtime.py` | L90-111 | `LLMRuntime.act_stream()` — ABC 默认实现 |
| `helen/runtime/__init__.py` | L165-172 | `_CallHandle` — `cancelled = threading.Event()` |
| `helen/runtime/__init__.py` | L463-478 | `cancel_llm_call()` — 仅对同步 `act()` 有效 |
| `helen/interpreter/interpreter.py` | L2428-2472 | `visit_detach_stmt` — daemon 线程创建 |
| `helen/interpreter/interpreter.py` | L3001-3029 | `_call_llm_streaming()` — agent 流式路径 |
| `helen/interpreter/async_interpreter.py` | L138-178 | `visit_llm_act_expr_async` — 非流式 async |
| `helen/cli/repl.py` | L558-567 | `KeyboardInterrupt` during `input()` |
| `helen/cli/repl.py` | L608-626 | 执行块 + 外层 `except KeyboardInterrupt` |
| `helen/runtime/stream_contracts.py` | L30-43 | `StreamingLLMRuntime` Protocol |

### 5.2 控制流路径

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

detach (interpreter.py:2428)
  └→ threading.Thread(daemon=True)
       └→ 新 Interpreter 实例
            └→ 同一 visit_llm_act_expr 路径

async call (interpreter.py:2474)
  └→ Task.pending(node.call, self, env_snapshot)
       └→ await → _await_tasks() (interpreter.py:3031)
            └→ AsyncLLMInterpreter.visit_llm_act_expr_async()
                 └→ self.llm_runtime.act_async()  ← 非流式！
```

### 5.3 已有取消基础设施（未接通流式）

```python
# helen/runtime/__init__.py

class _CallHandle:
    def __init__(self):
        self.cancelled = threading.Event()   # 取消信号
        self.done = threading.Event()        # 完成信号

def cancel_llm_call(self, call_id: str) -> bool:
    handle = self._active_calls.get(call_id)
    if handle is None: return False
    handle.cancelled.set()    # 设置 Event，但流式路径不检查它
    return True
```

断裂点：
1. 流式路径绕过 `HelenRuntime`，直接调用 `self.llm_runtime.act_stream()`
2. `act_stream()` 不接受也不检查 `cancel_event`
3. `_visit_llm_act_streaming` 的 `for event` 循环无取消检查

---

## 6. 方案详细设计

### 6.1 Phase 1: on_chunk 返回值中断

**目标**：用户代码可通过 `on_chunk` 返回 `false` 停止流式。

**文件**：`helen/interpreter/llm_mixin.py`

**改动**：3 处 `on_chunk_fn(...)` 调用改为捕获返回值。

```python
# 现有（L496）:
on_chunk_fn(content)

# 改为:
chunk_result = on_chunk_fn(content)
if chunk_result is False:    # 仅精确 False（身份比较）
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
count = 0
result = llm act "写一篇长文" on_chunk fn(chunk: str) {
    设 count = count + 1
    print(chunk)
    if count >= 5 { return false }
}
```

---

### 6.2 Phase 2: cancel_event 贯穿 Runtime 层

**目标**：为 `act_stream()` / `act_stream_async()` 添加取消能力。

#### 6.2.1 ABC 签名变更

**文件**：`helen/runtime/llm_runtime.py` (L90-111)

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

#### 6.2.2 HttpLLMRuntime 同步流

**文件**：`helen/runtime/http_llm.py` — `act_stream()` (L902)

签名新增 `cancel_event`。两处插入检查：

```python
def act_stream(self, ..., cancel_event=None):
    ...
    while budget.consume():
        # ★ 检查点 A：工具调用轮次之间
        if cancel_event is not None and cancel_event.is_set():
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

#### 6.2.3 HttpLLMRuntime 异步流

**文件**：`helen/runtime/http_llm.py` — `act_stream_async()` (L1429)

同样新增 `cancel_event` 参数，同样两处检查。`threading.Event.is_set()` 是非阻塞的，从 async 代码调用安全。

```python
async def act_stream_async(self, ..., cancel_event=None):
    ...
    async with self._async_client.stream("POST", url, json=payload) as response:
        async for line_bytes in response.aiter_lines():
            if cancel_event is not None and cancel_event.is_set():
                break
            ...
```

#### 6.2.4 Protocol 更新

**文件**：`helen/runtime/stream_contracts.py` (L30-43)

```python
@runtime_checkable
class StreamingLLMRuntime(Protocol):
    def act_stream(self, ..., cancel_event=None) -> Iterator[StreamChunk]:
        ...
```

---

### 6.3 Phase 3: 解释器流式调用注册表

**目标**：解释器跟踪所有活跃的流式调用，支持编程式取消和 Ctrl+C 中断。

**文件**：`helen/interpreter/interpreter.py`

#### 6.3.1 新增 `_StreamingHandle`

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

#### 6.3.2 Interpreter 注册表

`Interpreter.__init__()` (L803 附近) 添加：

```python
self._streaming_calls: dict[str, _StreamingHandle] = {}
self._streaming_lock = threading.Lock()
```

#### 6.3.3 管理方法

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
```

#### 6.3.4 核心中断逻辑

**文件**：`helen/interpreter/llm_mixin.py` — `_visit_llm_act_streaming()` 重构

```python
try:
    dispatch_fn = self._create_dispatch_fn()
    full_response, tool_calls_log, stream_usage = [], [], {}
    stream_handle = self._register_streaming_call()
    interrupted = False

    try:
        for event in self.llm_runtime.act_stream(
            ...,
            cancel_event=stream_handle.cancelled,    # Phase 2 参数
        ):
            # 检查取消信号
            if stream_handle.cancelled.is_set():
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

    # 记录历史（不变）
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

#### 6.3.5 Agent 流式路径

`_call_llm_streaming()`（`interpreter.py:3001-3029`）也需传入 `cancel_event`：

```python
def _call_llm_streaming(self, prompt, agent):
    ...
    if hasattr(self.llm_runtime, 'act_stream'):
        stream_handle = self._register_streaming_call()
        try:
            stream_iterator = self.llm_runtime.act_stream(
                prompt, model=model, temperature=temperature,
                system_prompt=system_prompt,
                cancel_event=stream_handle.cancelled,
            )
            return StreamingResponse(stream_iterator)
        finally:
            stream_handle.done.set()
            self._unregister_streaming_call(stream_handle.call_id)
```

---

### 6.4 Phase 4: REPL 存活

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
        print("\n⚡ 已中断 — 状态已保留")
    except Exception as e:
        print(f"Internal Error: {e}", file=sys.stderr)
```

**Site 2 — 单行执行**（L608-618）：同上。

**安全网语义**：

- 流式路径的 `KeyboardInterrupt` 已在 Phase 3.4 内层捕获，正常不会到 REPL 层
- REPL 层的 `except KeyboardInterrupt` 是兜底，覆盖同步 `act()` 阻塞等其他场景
- 外层 `except KeyboardInterrupt`（L624）保持不变，仅作用于 `input()` 时的 Ctrl+C（退出 REPL）

---

### 6.5 Phase 5: stdlib 函数

**目标**：暴露 `cancel_llm_call()` 和 `current_llm_call_id()` 给 Helen 程序。

#### 6.5.1 新文件 `helen/stdlib/llm_control.py`

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
```

#### 6.5.2 注册到 stdlib

**文件**：`helen/stdlib/__init__.py`

1. 导入（L150 附近）：
```python
from helen.stdlib.llm_control import (
    _cancel_llm_call, _current_llm_call_id, _set_interpreter_ref,
)
```

2. `_register_builtins()` 中注册：
```python
BuiltinFunction("cancel_llm_call", "取消一次进行中的大模型调用",
                "cancel_llm_call(call_id)", _cancel_llm_call, "llm"),
BuiltinFunction("current_llm_call_id", "获取当前大模型调用 ID",
                "current_llm_call_id()", _current_llm_call_id, "llm"),
```

3. 中文别名（`locales/zh.py`）：
```python
"cancel_llm_call": "取消大模型调用",
"current_llm_call_id": "当前大模型调用id",
```

#### 6.5.3 连接解释器引用

**文件**：`helen/interpreter/interpreter.py` — `_setup_stdlib()` (L879 附近)

```python
from helen.stdlib.llm_control import _set_interpreter_ref
_set_interpreter_ref(self)
```

**Helen 用法示例**：

```helen
// 从另一个 agent 中取消当前调用
id = 当前大模型调用id()
如果 id != null {
    取消大模型调用(id)
}
```

---

### 6.6 Phase 6: detach 中断

**目标**：Ctrl+C 通知所有 detach 线程优雅退出，REPL 立即恢复。

**策略**：设置 `cancel Event` + 不 join（daemon 自行检测退出）。

**文件**：`helen/interpreter/interpreter.py` — `visit_detach_stmt` (L2428-2472)

#### 6.6.1 跟踪 detach 线程

`Interpreter.__init__()` 添加：

```python
self._detach_threads: list[tuple[threading.Thread, threading.Event]] = []
self._detach_lock = threading.Lock()
```

#### 6.6.2 修改 `visit_detach_stmt`

```python
def visit_detach_stmt(self, node: DetachStmtNode) -> object:
    env_snapshot = self.environment.snapshot()
    cancel_event = threading.Event()

    def run_detached():
        detached_interpreter = Interpreter(
            errors=self.errors,
            llm_runtime=self.llm_runtime,
            import_resolver=self.import_resolver,
        )
        detached_interpreter.environment = env_snapshot
        detached_interpreter._detach_cancel_event = cancel_event  # 传递取消信号
        try:
            node.call.accept(detached_interpreter)
        except Exception:
            pass    # daemon 线程静默退出

    thread = threading.Thread(target=run_detached, daemon=True)

    with self._detach_lock:
        self._detach_threads.append((thread, cancel_event))

    thread.start()
    return None
```

#### 6.6.3 Detached Interpreter 检查 cancel

`_visit_llm_act_streaming` 在循环中额外检查 `self._detach_cancel_event`：

```python
# 在 for event 循环开头
detach_cancel = getattr(self, '_detach_cancel_event', None)
if detach_cancel is not None and detach_cancel.is_set():
    interrupted = True
    break
```

同时传入 `act_stream`：

```python
# 合并 cancel_event：优先使用 stream_handle 的，fallback 到 detach 的
effective_cancel = stream_handle.cancelled
if detach_cancel is not None:
    # 两个 Event 任一设置都中断
    # 用 polling 方式检查
    ...
```

更简洁的方案：让 `_StreamingHandle.cancelled` 与 `_detach_cancel_event` 联动：

```python
# 在 stream_handle 注册后，启动一个监控线程
if detach_cancel is not None:
    def _bridge():
        detach_cancel.wait()
        stream_handle.cancelled.set()
    t = threading.Thread(target=_bridge, daemon=True)
    t.start()
```

#### 6.6.4 主线程 Ctrl+C 通知所有 detach

**文件**：`helen/cli/repl.py` — `except KeyboardInterrupt` 处理中

```python
except KeyboardInterrupt:
    # 通知所有 detach 线程
    if hasattr(interp, '_detach_threads'):
        with interp._detach_lock:
            for _, event in interp._detach_threads:
                event.set()
    print("\n⚡ 已中断 — 状态已保留")
```

#### 6.6.5 清理已完成线程

定期清理 `_detach_threads` 中已结束的线程（避免泄漏）：

```python
# 在每次 detach 时或 REPL 循环中
with self._detach_lock:
    self._detach_threads = [
        (t, e) for t, e in self._detach_threads if t.is_alive()
    ]
```

---

### 6.7 Phase 7: async/await（预留）

**目标**：本次仅确保签名就位，不接入 async 解释器路径。后续作为独立特性实现。

#### 6.7.1 本次范围

- `act_stream_async()` 签名已添加 `cancel_event`（Phase 2 完成）✅
- `StreamingLLMRuntime` Protocol 已更新 ✅
- 不改动 `AsyncLLMInterpreter`、`Task`、`_await_tasks`

#### 6.7.2 后续实现路线图（不在本次范围）

| 步骤 | 改动 | 说明 |
|------|------|------|
| 1 | `async_interpreter.py` 新增 `visit_llm_act_expr_async_streaming` | 使用 `async for event in act_stream_async(...)` |
| 2 | `Task` 添加 `_cancel_event: asyncio.Event` | per-task 取消 |
| 3 | `_await_tasks` 使用 `asyncio.TaskGroup` | 统一取消传播 |
| 4 | 并发 `on_chunk` 输出序列化 | 每 task 一个 queue，主线程消费 |
| 5 | 修复 sync fallback 阻塞 event loop 的已有 bug | 确保 async 路径不再走 sync `act_stream` |

---

## 7. 向后兼容性

| 场景 | 影响 | 分析 |
|------|------|------|
| 现有 `on_chunk` 返回 `None` | ✅ 不受影响 | `None is False` → `False`，继续流式 |
| `MockLLMRuntime` 继承默认 `act_stream()` | ✅ 自动获得参数 | `cancel_event` 可选，默认 `None` |
| 自定义 `LLMRuntime` 覆盖 `act_stream()` | ⚠️ 需更新签名 | ABC 已添加参数。不更新会 `TypeError`。可在调用处 `inspect.signature` 兼容检查 |
| REPL Ctrl+C 退出 | ✅ 不变 | `input()` 处 Ctrl+C 仍退出 REPL |
| 现有 Helen 程序 | ✅ 无语法/语义变更 | 新 stdlib 函数不与现有名称冲突 |
| detach 程序 | ✅ 不变 | 无 cancel Event 时行为完全一致 |
| async 程序 | ✅ 不变 | 本次不改动 async 路径 |

### 自定义 LLMRuntime 兼容方案

如果担心用户自定义 `LLMRuntime` 子类未更新签名：

```python
# llm_mixin.py — 传入 cancel_event 前检查
import inspect

cancel_event = stream_handle.cancelled
sig = inspect.signature(self.llm_runtime.act_stream)
if 'cancel_event' not in sig.parameters:
    cancel_event = None    # 不支持则不传

for event in self.llm_runtime.act_stream(..., cancel_event=cancel_event):
    ...
```

或更简单：直接在调用时用 `try/except TypeError` 回退：

```python
try:
    stream = self.llm_runtime.act_stream(..., cancel_event=stream_handle.cancelled)
except TypeError:
    stream = self.llm_runtime.act_stream(...)    # 不支持 cancel_event
```

推荐后者 — 零开销，只在异常路径才付出代价。

---

## 8. 风险矩阵

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|---------|
| `KeyboardInterrupt` 在历史更新/审计期间击中 | 中 | 高 | `try/except KeyboardInterrupt` 仅包裹流式循环，历史/日志在循环之后 |
| 工具执行中取消 | 中 | 低 | 当前工具执行完成后再检查 cancel（工具不可抢占） |
| 并发 detach `on_chunk` stdout 交错 | 中 | 中 | 文档说明。后续可引入 queue 序列化 |
| `ErrorReporter` 线程安全 | 低 | 中 | CPython GIL 保证 list.append 原子性。语义顺序丢失可接受 |
| `_StreamingHandle` 泄漏（未 unregister） | 低 | 低 | `finally` 块保证 unregister。Interpreter 销毁时 dict 随之释放 |
| 自定义 `LLMRuntime` 不兼容新参数 | 低 | 低 | `try/except TypeError` 回退 |
| detach cancel Event 桥接线程泄漏 | 低 | 低 | daemon 线程，进程退出自动清理 |
| REPL `except KeyboardInterrupt` 吞掉非流式中断 | 低 | 低 | 仅影响同步 `act()` 阻塞场景；打印提示后 REPL 继续 |

---

## 9. 测试方案

### 9.1 新增测试文件

| 文件 | 测试数 | 覆盖 |
|------|--------|------|
| `tests/interpreter/test_streaming_interrupt.py` | ~12 | Phase 1-3 全覆盖 |
| `tests/runtime/test_http_llm_cancel.py` | ~3 | Phase 2 HTTP 层 |
| `tests/cli/test_repl_interrupt.py` | ~2 | Phase 4 REPL 存活 |
| `tests/interpreter/test_detach_interrupt.py` | ~3 | Phase 6 detach 中断 |

### 9.2 测试用例明细

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
```

#### `tests/runtime/test_http_llm_cancel.py`

```python
class TestHttpLLMCancelEvent:
    def test_act_stream_accepts_cancel_event(self):
        """签名兼容"""

    def test_act_stream_stops_on_cancel(self):
        """cancel_event.set() → 停止 yield"""

    def test_act_stream_async_stops_on_cancel(self):
        """async 版本同理"""
```

#### `tests/cli/test_repl_interrupt.py`

```python
class TestReplInterrupt:
    def test_repl_survives_interrupt_during_streaming(self):
        """REPL 不因 Ctrl+C 退出"""

    def test_repl_state_preserved_after_interrupt(self):
        """中断后 let x = 42 仍可用"""
```

#### `tests/interpreter/test_detach_interrupt.py`

```python
class TestDetachInterrupt:
    def test_detach_cancel_event_set_on_ctrl_c(self):
        """Ctrl+C → 所有 detach 线程的 Event 被设置"""

    def test_detach_thread_exits_on_cancel(self):
        """detach 线程检测 cancel 后退出"""

    def test_main_thread_state_preserved(self):
        """detach 中断后主线程状态不受影响"""
```

### 9.3 端到端验证

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

# 3. 编程式取消
cat > /tmp/test_cancel.helen << 'EOF'
agent Test() {
    main {
        id = 当前大模型调用id()
        print("调用 ID: " + str(id))
    }
}
Test()
EOF

# 4. 全量测试
pytest tests/interpreter/test_streaming_interrupt.py -v
pytest tests/runtime/test_http_llm_cancel.py -v
pytest tests/cli/test_repl_interrupt.py -v
pytest tests/interpreter/test_detach_interrupt.py -v
pytest                                          # 无回归
flake8 helen/                                   # lint
```

---

## 10. 实施路线图

```
Phase 1 ─── on_chunk 返回值 ──────────────────────── 1-2 天
  │  llm_mixin.py（3 处改动）
  │  测试: 6 个
  │  可独立交付 ✅
  │
Phase 2 ─── cancel_event 贯穿 Runtime ────────────── 1-2 天
  │  llm_runtime.py + http_llm.py + stream_contracts.py
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
  │  测试: 4 个
  │  依赖 Phase 3
  │
Phase 6 ─── detach 中断 ───────────────────────────── 1-2 天
  │  interpreter.py + repl.py
  │  测试: 3 个
  │  依赖 Phase 3
  │
Phase 7 ─── async/await（预留，本次不实现）─────────── 后续
```

**总计**：6-10 天（Phase 1-6），Phase 7 作为独立特性另行评估。

---

## 11. 开放问题

| 编号 | 问题 | 当前建议 | 备选 |
|------|------|---------|------|
| Q1 | detach 中断时是否 join 等待？ | 设 Event + 不 join（REPL 立即恢复） | 设 Event + join(timeout=3s) |
| Q2 | 中断后 `on_complete` 是否应收到 `interrupted` 标志？ | 不调用（中断 ≠ 完成） | 调用并传入 `interrupted=true` 参数 |
| Q3 | detach 线程的 stdout 交错如何处理？ | 文档说明，本次不解决 | 引入 queue 序列化（REPL 场景） |
| Q4 | 自定义 `LLMRuntime` 不兼容 `cancel_event` 参数如何处理？ | `try/except TypeError` 回退 | `inspect.signature` 预检查 |
| Q5 | `ErrorReporter` 共享给 detach 线程是否需加锁？ | 暂不加（GIL 保证 append 原子性） | 添加 `threading.Lock` |
| Q6 | async/await 何时实现真异步流式？ | 作为 v1.18 独立特性 | 本次一并实现 |
| Q7 | 是否提供 `cancel_all_llm_calls()` stdlib？ | 暂不提供 | 提供，遍历 `_streaming_calls` 全部取消 |
| Q8 | 中断后的部分响应是否应写入 transcript？ | 是，标记 `[interrupted]` | 不写入 |

---

## 附录 A: 完整改动文件清单

| 文件 | Phase | 改动类型 |
|------|-------|---------|
| `helen/interpreter/llm_mixin.py` | 1, 3 | 核心改动 |
| `helen/runtime/llm_runtime.py` | 2 | 签名变更 |
| `helen/runtime/http_llm.py` | 2 | 签名 + 逻辑 |
| `helen/runtime/stream_contracts.py` | 2 | Protocol 更新 |
| `helen/interpreter/interpreter.py` | 3, 6 | 注册表 + detach 跟踪 |
| `helen/cli/repl.py` | 4, 6 | KeyboardInterrupt 处理 |
| `helen/stdlib/llm_control.py` | 5 | 新文件 |
| `helen/stdlib/__init__.py` | 5 | 注册 |
| `helen/stdlib/locales/zh.py` | 5 | 中文别名 |
| `tests/interpreter/test_streaming_interrupt.py` | 1-3 | 新文件 |
| `tests/runtime/test_http_llm_cancel.py` | 2 | 新文件 |
| `tests/cli/test_repl_interrupt.py` | 4 | 新文件 |
| `tests/interpreter/test_detach_interrupt.py` | 6 | 新文件 |

## 附录 B: 现有代码参考

### B.1 `on_chunk` 使用模式（现有 examples）

```helen
// examples/chatbot.helen
agent ChatBot(user_input: str) {
    model "qwen3.7-plus"
    main {
        llm act user_input on_chunk fn(chunk: str) {
            print(chunk)
        }
    }
}
```

所有现有 examples 的 `on_chunk` 均返回 `None`（`print()` 无返回值），不受 Phase 1 影响。

### B.2 `_CallHandle` 现有实现（`runtime/__init__.py`）

```python
class _CallHandle:
    def __init__(self):
        self.cancelled = threading.Event()
        self.result: Any = None
        self.exception: Exception | None = None
        self.done = threading.Event()
```

`_StreamingHandle` 复用相同模式，简化为 `call_id` + `cancelled` + `done`。

### B.3 stdlib 注册模式（跟随 context/transcript/media）

```python
# __init__.py 中已有的模式：
from helen.stdlib.context import _clear_context, _compress_context, _set_interpreter_context
from helen.stdlib.transcript import _get_session_id, ...
from helen.stdlib.media import _media, _media_base64, ...

# 新增：
from helen.stdlib.llm_control import _cancel_llm_call, _current_llm_call_id, _set_interpreter_ref
```

解释器连接（`_setup_stdlib` L879）：

```python
_set_interpreter_context(self._interpreter_history, self._history_manager, self._agent_context)
_set_transcript_context(self._agent_context)
# 新增：
_set_interpreter_ref(self)
```
