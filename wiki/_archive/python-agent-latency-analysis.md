# Python 版 Helen Agent 延迟问题分析

> 源码位置: `~/helen/helen/helen/agent/`

## 架构概览

```
浏览器 ←WebSocket→ FastAPI/uvicorn (asyncio)
                       ↓ run_in_executor (线程池)
                  chat_tui_web.py (Python Bridge)
                       ↓ FFI import/call
                  Helen Interpreter (独立线程)
                       ↓ spawn
                  ChatSessionActor (Helen agent, 另一线程)
                       ↓ llm act streaming
                  HttpLLMRuntime → OpenAI-compatible API
```

每个 LLM chunk 的回调链路:

```
SSE event → interpreter streaming loop → on_chunk callback
  → _actor_chunks_cb (Helen function call)
    → import "ui.stream_emitter" (FFI: import + define)
    → _CancelCheck.is_cancel_requested() (FFI: getattr + method call)
    → _emit_actor_stream_event("llm_chunk", text)
      → import "ui.stream_emitter" (FFI: import + define)
      → ActorStreamEmitter.emit_stream_event() (FFI: getattr + method call)
        → Python callback → loop.call_soon_threadsafe → asyncio.Queue
          → wait_for → WebSocket broadcast
```

## 延迟源分析

### 1. 🔴 每个 chunk 重复 FFI import（最大开销）

`chat_session_actor.helen:306-315` — `_actor_chunks_cb`:
```helen
fn _actor_chunks_cb(text) {
    try {
        import "ui.stream_emitter" as _CancelCheck  // ← FFI import
        if _CancelCheck.is_cancel_requested() {      // ← FFI method call
            cancel_all_llm_calls()
            _CancelCheck.clear_cancel()
            return
        }
    } catch {}
    _emit_actor_stream_event("llm_chunk", text)  // ← 又一次 FFI import
}
```

`_emit_actor_stream_event` (`chat_session_actor.helen:257-263`):
```helen
fn _emit_actor_stream_event(event_type: str, data: str) {
    try {
        ensure_python_path()
        import "ui.stream_emitter" as ActorStreamEmitter  // ← FFI import
        ActorStreamEmitter.emit_stream_event(event_type, data)  // ← FFI method call
    } catch {}
}
```

**每个 chunk 执行 2 次 FFI import + 2 次 FFI method call**。

虽然 `DefaultPythonRuntime.import_module()` 有缓存（dict lookup），但每次 import 仍然:
1. 检查 `hasattr(self, '_python_runtime')` 
2. 查 `_modules` dict
3. 调用 `self.environment.define(alias, module)` — 在环境中重新绑定变量
4. 创建 `WrappedPythonModule.__getattr__` → `DefaultTypeConverter.python_to_helen()` 转换

对于一次典型响应（几百个 chunk），这意味着上千次 FFI 穿越。Python 的 FFI 穿越涉及 GIL 获取/释放、类型转换、函数调用开销。

### 2. 🔴 每次 statusline 更新也做 FFI import

`_actor_tool_end_cb` (`chat_session_actor.helen:323-351`) 在每个工具调用结束后:
```helen
fn _actor_tool_end_cb(tool_name, tool_result) {
    try {
        import "ui.stream_emitter" as _CancelCheck    // FFI import #1
        if _CancelCheck.is_cancel_requested() { ... }
    } catch {}
    _actor_emit_statusline()                           // 内部又做 FFI import
    try {
        import "ui.hint_queue" as _HintQueueMod        // FFI import #2
        let q = _HintQueueMod.get_hint_queue()
        let hints = q.pop_all_hints("")
        ...
    } catch { return null }
}
```

`_actor_emit_statusline` (`chat_session_actor.helen:265-278`):
```helen
fn _actor_emit_statusline() {
    try {
        import "ui.status_emitter" as _StatusMod        // FFI import #3
        let stats = context_stats()
        ...
        _StatusMod.emit_status(ratio, model_name)
    } catch {}
}
```

每个工具调用结束触发 3 次 FFI import。

### 3. 🟡 asyncio.Queue 的 100ms 轮询

`helen_bridge.py:387`:
```python
event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
```

当 LLM 在思考（工具调用期间无 chunk 输出），这个 100ms timeout 会反复触发。每次 timeout 都检查 `helen_task.done()`，添加不必要的 event loop 调度开销。

**影响**: 工具调用完成后，complete 信号的检测最多延迟 100ms。

### 4. 🟡 Hint 仅在工具边界注入

`chat_session_actor.helen:335-350` — hint 只在 `_actor_tool_end_cb` 中消费。LLM 纯文本生成期间（无工具调用），用户追加的 hint 排队等待。

如果 LLM 在做长文本输出（如写大文件），hint 可能等待数十秒才被处理。

### 5. 🟡 `cancel_all_llm_calls()` 的中断传播

`chat_session_actor.helen:310` 调用 `cancel_all_llm_calls()` 后:
- 解释器的 streaming loop 在下一次 SSE event 检查 `stream_handle.cancelled.is_set()` 时才会中断（`llm_mixin.py:780`）
- 如果 HTTP 连接正在等待 SSE 数据（无 chunk 到达），中断要等到 HTTP 超时或下一个 event

**Cancel 的实际延迟**: 取决于 SSE event 的到达频率。在 LLM 快速输出时延迟很小（毫秒级），在等待工具执行结果时延迟可能达到秒级。

### 6. 🟡 `ensure_actor()` 的 FFI 健康检查

`channel_actor_manager.py:75-77`:
```python
def ensure_actor(self) -> dict:
    with self._lock:
        if self._actor_spawned:
            if not self._check_actor_alive():  # ← FFI call
```

`_check_actor_alive()` (`channel_actor_manager.py:58-63`):
```python
def _check_actor_alive(self) -> bool:
    try:
        from chat_tui_web import is_chat_actor_running
        return bool(is_chat_actor_running())
    except Exception:
        return False
```

每条用户消息发送前都做一次 FFI 调用检查 actor 是否存活。`is_chat_actor_running()` 通过 mailbox 发送探测消息并等待响应，这添加了几毫秒到每条消息的处理时间。

### 7. 🟢 Helen Interpreter 的 GIL 竞争

Helen interpreter 运行在线程池中（`run_in_executor`），asyncio event loop 在主线程运行。两者共享 Python GIL。

当 interpreter 密集执行（处理 SSE events + 回调），它持有 GIL，asyncio 线程的 `call_soon_threadsafe` 需要等待 GIL 释放。这导致 chunk 从 interpreter 到 WebSocket 的传播有微小但持续的延迟。

## 与 Rust 版的关键差异

| 维度 | Python 版 | Rust 版 (helen-rust) |
|------|-----------|---------------------|
| `import "ui.stream_emitter"` | ✅ 可用（Python FFI） | ❌ 失败（无 python-ffi） |
| 每 chunk FFI 开销 | 2 次 FFI import + 2 次 method call | N/A（import 失败） |
| Cancel 机制 | 3 层: interpreter + stream_emitter + callback | 1 层: AtomicBool |
| Hint 注入 | 工具边界 (`_actor_tool_end_cb`) | 工具边界（同） |
| Event loop | asyncio + GIL 竞争 | tokio（无 GIL） |
| Streaming chunk 路径 | FFI → Python callback → asyncio.Queue → WS | Channel → broadcast → WS |

## 修复建议

| 优先级 | 问题 | 修复方案 |
|--------|------|----------|
| P0 | 每 chunk 2 次 FFI import | 将 `import "ui.stream_emitter"` 移到 `main {}` 顶层或 `functions {}` 块顶部，只执行一次。后续直接引用 `_CancelCheck` 和 `ActorStreamEmitter` |
| P0 | `_actor_chunks_cb` 中 FFI 开销 | 用 Helen 内置的 `agent_cancel_event` 检查替代 FFI cancel 检查，避免每 chunk 的 Python FFI 穿越 |
| P1 | `_emit_actor_stream_event` FFI 开销 | 将 stream_emitter 模块缓存为模块级变量，避免每次回调都 import |
| P1 | 100ms 轮询 | 改为 event-driven：用 `asyncio.Event` 替代 timeout 轮询 |
| P1 | Hint 仅工具边界 | 在 `on_chunk` 回调中也检查 hint queue，或在独立线程中定时检查 |
| P2 | `ensure_actor()` 健康检查 | 降低频率：每 N 条消息检查一次，或用 passive 监控代替 active 探测 |

### P0 修复示例：消除每 chunk FFI import

```helen
// chat_session_actor.helen — functions {} 块顶部

// 只 import 一次，后续所有回调直接引用
shared let _stream_emitter = null
shared let _hint_queue_mod = null

fn _init_ffi_modules() {
    try {
        import "ui.stream_emitter" as _SE
        _stream_emitter = _SE
    } catch {}
    try {
        import "ui.hint_queue" as _HQ
        _hint_queue_mod = _HQ
    } catch {}
}

// 回调直接使用缓存的引用
fn _actor_chunks_cb(text) {
    try {
        if _stream_emitter != null {
            if _stream_emitter.is_cancel_requested() {
                cancel_all_llm_calls()
                _stream_emitter.clear_cancel()
                return
            }
        }
    } catch {}
    try {
        if _stream_emitter != null {
            _stream_emitter.emit_stream_event("llm_chunk", text)
        }
    } catch {}
}
```

这样每个 chunk 只需 2 次 FFI method call（无 import），减少约 50% 的 FFI 开销。
