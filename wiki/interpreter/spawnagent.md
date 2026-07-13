# spawnagent 并发原语

> 模块 M5 (`interpreter.py`) + 运行时 (`channel.py`) | 测试: `tests/interpreter/test_spawnagent*.py`、`tests/runtime/test_channel.py`

---

## 概述

Helen v1.18 使用 `spawnagent` + Channel 消息队列替代旧的 `async/await/detach` 并发模型。`spawnagent` 是唯一的并发原语，Channel 是 agent 间通信的通用工具。

**核心设计**：
- 一个并发原语（`spawnagent`）+ 一个通信机制（Channel 消息队列）
- 隔离优先：snapshot 全部深复制，agent 默认与外部环境完全隔离
- 共享是显式的：通过 Channel 传递 SharedStore 引用

---

## Channel 运行时实现

### Channel + ChannelEndpoint（双队列设计）

```python
# helen/runtime/channel.py

class Channel:
    """双向消息通道。agent 通信的通用工具。

    在 spawnagent 跨线程场景和普通 agent 隔离场景中设计一致。
    内部两个队列，支持双向通信。
    """

    def __init__(self, name: str = ""):
        self._name = name
        self._to_spawned = queue.Queue()     # 主线程 → spawned agent
        self._from_spawned = queue.Queue()   # spawned agent → 主线程
        self._cancel_event = threading.Event()
        self._closed = threading.Event()


class ChannelEndpoint:
    """Channel 的一个端点（主线程端或 spawned agent 端）。"""

    def __init__(self, channel: Channel, is_main_thread: bool):
        self._channel = channel
        if is_main_thread:
            self._outbox = channel._to_spawned
            self._inbox = channel._from_spawned
        else:
            self._outbox = channel._from_spawned
            self._inbox = channel._to_spawned
        self._is_main = is_main_thread

    def send(self, msg: Any) -> None:
        if self._channel._closed.is_set():
            return
        self._outbox.put(msg)

    def receive(self, timeout: float | None = None) -> Any:
        try:
            return self._inbox.get(timeout=timeout)
        except queue.Empty:
            return None

    def try_receive(self) -> Any:
        try:
            return self._inbox.get_nowait()
        except queue.Empty:
            return None

    def cancel(self) -> None:
        """取消对端 agent（仅主线程端可用）。"""
        self._channel._cancel_event.set()
        self.close()

    def close(self) -> None:
        self._channel._closed.set()
        try:
            self._outbox.put_nowait(None)   # 唤醒阻塞的 receive
        except Exception:
            pass

    def is_closed(self) -> bool:
        return self._channel._closed.is_set()

    @property
    def cancel_event(self) -> threading.Event:
        return self._channel._cancel_event

    def call_method(self, name: str, args: list) -> Any:
        methods = {
            "send": self.send, "发送": self.send,
            "receive": self.receive, "接收": self.receive,
            "try_receive": self.try_receive, "尝试接收": self.try_receive,
            "cancel": self.cancel, "取消": self.cancel,
            "close": self.close, "关闭": self.close,
            "is_closed": self.is_closed, "已关闭": self.is_closed,
        }
        fn = methods.get(name)
        if fn is None:
            raise AttributeError(f"Channel has no method '{name}'")
        return fn(*args)
```

### 双端模型

每个 Channel 实例有两个端点：
- **主线程端**：`spawnagent` 返回值，`send()` 写入 `_to_spawned`，`receive()` 从 `_from_spawned` 读取
- **spawned agent 端**：注入到 agent 的 `reply` 参数，方向相反

```
主线程端 ──send()──→ _to_spawned ──→ receive()── spawned agent 端
spawned agent 端 ──send()──→ _from_spawned ──→ receive()── 主线程端
```

---

## spawnagent 执行流程

```python
def visit_spawnagent_expr(self, node: SpawnagentExprNode) -> object:
    from helen.runtime.channel import Channel, ChannelEndpoint

    call_node = node.call
    agent_name = call_node.callee.name
    agent_decl = self._agents.get(agent_name)
    if agent_decl is None:
        self.errors.error(...)
        return None

    # 1. 评估参数（排除最后一个 Channel 参数）
    arg_values = [arg.accept(self) for arg in call_node.args]

    # 2. 创建 Channel（双端队列）
    channel = Channel(name=f"spawn_{agent_name}")
    main_endpoint = ChannelEndpoint(channel, is_main_thread=True)
    spawned_endpoint = ChannelEndpoint(channel, is_main_thread=False)

    # 3. 将 spawned 端追加到参数列表
    arg_values.append(spawned_endpoint)

    # 4. 快照环境（全部深复制）
    env_snapshot = self.environment.snapshot()

    # 5. 在新线程中执行 spawned agent
    def run_spawned():
        spawned_interpreter = Interpreter(
            errors=self.errors,
            llm_runtime=self.llm_runtime,
            import_resolver=self.import_resolver,
        )
        spawned_interpreter.environment = env_snapshot
        try:
            call_node.accept(spawned_interpreter)
        except Exception as e:
            try:
                spawned_endpoint.send({"__error__": True, "message": str(e)})
            except Exception:
                pass
        finally:
            spawned_endpoint.close()

    thread = threading.Thread(target=run_spawned, daemon=True)
    thread.start()

    # 6. 返回主线程端点
    return main_endpoint
```

**执行时序**：

```
主线程                                  spawned agent
──────                                  ─────────────
spawnagent Worker("task")
  │
  ├─ 创建 Channel（双端队列）
  ├─ env.snapshot()（全部深复制）
  ├─ 新 Interpreter 实例
  ├─ Channel 的 spawned 端绑定到 reply 参数
  ├─ threading.Thread(daemon=True) 启动
  ├─ 返回 Channel 的主线程端（mailbox）
  │                                        agent 执行 main {}
  │                                        reply.send("进度1") ──→
  mailbox.receive() ←────────────────────── "进度1"
  mailbox.receive() ←────────────────────── "完成: 结果"
  │                                        reply.close()（自动）
  mailbox.receive() → null                  agent 退出
```

---

## snapshot 语义变更（全部深复制）

```python
# environment.py
def snapshot(self):
    import copy
    parent_snapshot = self.parent.snapshot() if self.parent else None
    new_env = Environment(parent=parent_snapshot)

    new_store = {}
    for key, value in self._store.items():
        new_store[key] = copy.deepcopy(value)   # 全部深复制，无例外

    new_env._store = new_store
    new_env._consts = copy.copy(self._consts)
    return new_env
```

| 类型 | snapshot 行为 | 说明 |
|------|--------------|------|
| `SharedStore` | **深复制** | 创建独立副本（通过 `__deepcopy__`） |
| `Channel`（消息队列） | **深复制** | 创建独立空 channel（队列清空） |
| `list` / `dict` | 深复制 | 不变 |
| `int` / `str` / `bool` / `None` | 按引用（不可变类型） | 不变 |
| 函数 / 闭包 | 按引用（不可变） | 不变 |

**注意**：Channel 深复制后创建的是独立的空 channel，不与原 channel 连通。若需要在 agent 间建立通信，应显式传递 channel 引用（通过参数或 channel.send）。

---

## SharedStore.__deepcopy__

```python
class SharedStore:
    def __deepcopy__(self, memo):
        import copy
        # fields 深复制，methods 不复制（闭包引用旧环境）
        new_store = SharedStore(
            self._name,
            copy.deepcopy(self._fields, memo),
            {}   # methods 不复制
        )
        memo[id(self)] = new_store
        return new_store
```

**要点**：
- `fields` 深复制 — spawned agent 得到独立副本
- `methods` 不复制 — 闭包引用旧环境，复制无意义
- 如需共享同一个 SharedStore，通过 channel 显式传递引用

---

## 显式共享模式

需要 spawned agent 访问主线程的 shared store 时，通过 channel 传递引用：

```helen
shared store Config { let timeout = 30 }

main {
    let mailbox = spawnagent Worker()
    mailbox.send(Config)    // 显式传递引用——只有这个 spawned agent 能看到
    let result = mailbox.receive()
}
```

**对比旧模型**：

| | v1.17（旧） | v1.18（新） |
|--|-------------|------------|
| SharedStore | 按引用传递（snapshot 例外） | **深复制**（默认隔离） |
| 通信方式 | 隐式共享（全有或全无） | **显式传递**（通过 channel） |
| 隔离性 | 🔴 差 | 🟢 完全隔离 |

---

## mailbox_select — 多路复用

```python
# helen/stdlib/mailbox.py
def mailbox_select(channels, timeout=None):
    """从多个 channel 端点中接收第一个到达的消息。"""
    deadline = time.time() + timeout if timeout else None
    while True:
        for ep in channels:
            msg = ep.try_receive()
            if msg is not None:
                return {"endpoint": ep, "message": msg}
        if deadline and time.time() >= deadline:
            return None
        time.sleep(0.01)
```

---

## 删除的旧内容

| 删除内容 | 原文件 |
|---------|------|
| `async` / `await` / `detach` 关键字 | `tokens.py` |
| `AsyncCallStmtNode` / `AsyncCallExprNode` / `DetachStmtNode` | `ast.py` |
| `visit_async_call_stmt` / `visit_async_call_expr` / `visit_detach_stmt` | `interpreter.py` |
| `AsyncLLMInterpreter` | `async_interpreter.py`（整个文件删除） |
| `_await_tasks` / `Task` 类 | `interpreter.py` / `task.py`（整个文件删除） |
| `act_async()` / `act_stream_async()` / `route_async()` | `http_llm.py` / `llm_runtime.py` |
| `channel X { fields }` 声明语法 | `parser.py` / `ast.py` |
| `ChannelDeclNode` / `visit_channel_decl` | `ast.py` / `interpreter.py` |

---

## 相关页面

- [[tutorial/07-spawnagent|并发编程教程]]
- [[interpreter/execution|执行引擎]]
- [[syntax/keywords|关键字参考]]

---

**最后更新**: 2026-07-13  
**版本**: v1.18
