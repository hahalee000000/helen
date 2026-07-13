# spawnagent 方案（v3）

> 版本：v3.0 草案  
> 日期：2026-07-13  
> 状态：待评审  
> 优先级：**高于**流式中断方案（`streaming-interrupt-proposal.md`）  
> 关联：`streaming-interrupt-proposal.md`（中断方案需适配本方案）  
> 变更：
> - v1→v2：snapshot 全部深复制无例外；旧 `channel X { fields }` 语法废弃；shared store 角色降级
> - v2→v3：channel 是 agent 通信的**通用工具**——spawnagent 跨线程和普通 agent 隔离场景设计一致；Channel 通过构造函数 `Channel()` 创建，无需 stdlib 工厂函数

---

## 目录

1. [动机](#1-动机)
2. [设计目标](#2-设计目标)
3. [核心语义](#3-核心语义)
4. [Channel 消息队列](#4-channel-消息队列)
5. [snapshot 语义](#5-snapshot-语义)
6. [shared store 角色变更](#6-shared-store-角色变更)
7. [spawnagent 完整设计](#7-spawnagent-完整设计)
8. [async/await 废弃](#8-asyncawait-废弃)
9. [并发中断](#9-并发中断)
10. [语法与关键字](#10-语法与关键字)
11. [示例程序](#11-示例程序)
12. [运行时实现](#12-运行时实现)
13. [现有代码迁移](#13-现有代码迁移)
14. [测试方案](#14-测试方案)
15. [与其他方案的关系](#15-与其他方案的关系)
16. [开放问题](#16-开放问题)

---

## 1. 动机

### 1.1 当前 `detach` 的问题

```helen
detach Worker("task")   // 返回 null
```

| 问题 | 说明 |
|------|------|
| **无返回值** | 主线程无法获取 spawned agent 的结果，只能靠预约定的 shared store 轮询 |
| **隔离性差** | snapshot 将所有 SharedStore/channel 按引用传递，spawned agent 能看到主线程的一切共享状态 |
| **无法中断** | daemon 线程无句柄，主线程无法通知 spawned agent 停止 |
| **命名不准** | `detach`（分离）暗示"放手不管"，实际意图是"生成子 agent" |

### 1.2 `async`/`await` 的问题

```helen
let t = async Agent("task")
result = await t
```

| 问题 | 说明 |
|------|------|
| **不是真异步** | 底层是 `ThreadPoolExecutor`，和 `threading.Thread` 无本质区别 |
| **功能被 spawnagent 覆盖** | spawnagent + channel 能覆盖所有场景，且在流式、取消、竞争模式上更好 |
| **已知 bug** | `on_chunk` 在 async 路径中阻塞 event loop |
| **两套并发模型** | 用户需理解 `detach` vs `async`，认知负担重 |

### 1.3 当前 `channel` 名不副实

```helen
channel Result {
    let status: str = "pending"
    let data: str = ""
}
```

`channel` 在运行时就是 `SharedStore`——带 RLock 的结构体。无队列、无 send/receive、无阻塞等待。通信靠轮询共享字段。名字叫"通道"，实际是"共享变量"。

### 1.4 目标：统一并发与通信模型

```
agent 通信          — channel（消息队列，send/receive）【升级为真正的通道】
数据共享            — shared store（带锁结构体）
顺序执行            — 普通 agent main {}
跨线程（取结果）     — mailbox = spawnagent Agent(...) + mailbox.receive()
跨线程（fire-and-forget）— spawnagent Agent(...)（忽略返回值）
跨线程（多路复用）   — mailbox_select([m1, m2, ...])
```

channel 是 agent 通信的通用工具——在 spawnagent 跨线程场景和普通 agent 隔离场景中设计一致。

---

## 2. 设计目标

| 目标 | 说明 |
|------|------|
| **隔离优先** | snapshot 全部深复制，无例外。agent 默认与外部环境完全隔离 |
| **channel 即通道** | channel 升级为消息队列（send/receive），是 agent 通信的通用工具——spawnagent 跨线程和普通 agent 隔离场景设计一致 |
| **返回即控制** | spawnagent 返回的 channel 同时是数据面和控制面（cancel） |
| **共享是显式的** | 需要共享时，通过 channel 传递 shared store 引用——开发者有意为之 |
| **语义极简** | 一个并发原语（spawnagent）+ 一个通信机制（channel 消息队列） |

---

## 3. 核心语义

### 3.1 语法

```helen
mailbox = spawnagent Worker("数据分析")

result = mailbox.receive()   // 阻塞等待
mailbox.send("指令")          // 主线程发消息给 spawned agent
mailbox.cancel()              // 通知 spawned agent 停止
```

### 3.2 对比旧设计

```helen
// ═══ 旧 detach ═══
shared store Result { let status = "pending"; let data = "" }
detach Worker("task")
循环 { 如果 Result.status == "done" { 跳出 } sleep(100) }

// ═══ 新 spawnagent ═══
mailbox = spawnagent Worker("task")
result = mailbox.receive()    // 阻塞等待，无需轮询
```

### 3.3 spawned agent 的参数约定

spawned agent 的**最后一个参数**接收通信 channel，由 spawnagent 自动注入：

```helen
agent Worker(task: str, reply: Channel) {
    main {
        // reply 由 spawnagent 自动绑定到返回的 mailbox
        结果 = llm act "处理" + task
        reply.send(结果)
        // 函数结束 → reply 自动关闭 → 主线程 receive() 收到 null
    }
}

// 调用
mailbox = spawnagent Worker("数据分析")
// Worker 内部的 reply 就是 mailbox 的另一端
```

### 3.4 显式共享

需要 spawned agent 访问主线程的 shared store 时，通过 channel 传递引用：

```helen
shared store Counter {
    let count: int = 0
    fn inc() { count += 1 }
    fn get(): int { return count }
}

agent Worker(reply: Channel) {
    main {
        // 从 channel 接收 shared store 引用
        store = reply.receive()
        store.inc()
        reply.send("done")
    }
}

mailbox = spawnagent Worker()
mailbox.send(Counter)    // 显式传递引用——只有这个 spawned agent 能看到
print(mailbox.receive()) // "done"
print(Counter.get())     // 1 — 同一个对象，修改可见
```

---

## 4. Channel 消息队列

channel 是 agent 通信的通用工具。在 spawnagent 跨线程场景和普通 agent 隔离场景中，设计完全一致——都是 send/receive 消息队列。

### 4.1 与旧 channel 的区别

| | 旧 `channel X { fields }` | 新 Channel |
|--|-------------------------|------------|
| 运行时类型 | `SharedStore`（带锁结构体） | `Channel`（消息队列） |
| 通信方式 | 轮询共享字段 | send/receive 阻塞队列 |
| 声明方式 | `channel X { let f = ... }` | **不支持声明语法**——通过 spawnagent 或 `Channel()` 构造函数创建 |
| 方向 | 双向但无队列 | 双向队列 |
| 取消 | 无 | `cancel()` 设置 cancel_event |
| 适用范围 | 仅线程内 | **通用**：线程内 agent 隔离 + spawnagent 跨线程 |

### 4.2 Channel 运行时实现

```python
class Channel:
    """线程安全的消息通道。

    agent 通信的通用工具——在 spawnagent 跨线程场景和普通 agent 隔离场景中
    设计一致。内部两个队列，支持双向通信。
    """

    def __init__(self, name: str = ""):
        self._name = name
        self._to_spawned = queue.Queue()     # 主线程 → spawned agent
        self._from_spawned = queue.Queue()   # spawned agent → 主线程
        self._cancel_event = threading.Event()
        self._closed = threading.Event()

    def send(self, msg: Any) -> None:
        """发送消息到对端。可传递任意对象（包括 SharedStore 引用）。"""
        if self._closed.is_set():
            return
        # 判断消息应进入哪个队列
        # 如果调用者是 spawned agent 端 → 放入 from_spawned
        # 如果调用者是主线程端 → 放入 to_spawned
        # 实现上通过标记当前端来区分
        self._my_outbox.put(msg)

    def receive(self, timeout: float | None = None) -> Any:
        """阻塞接收。返回 null 表示通道关闭（对端退出）。"""
        try:
            return self._my_inbox.get(timeout=timeout)
        except queue.Empty:
            return None

    def try_receive(self) -> Any:
        """非阻塞接收。无消息返回 null。"""
        try:
            return self._my_inbox.get_nowait()
        except queue.Empty:
            return None

    def cancel(self) -> None:
        """取消对端 agent + 关闭通道。"""
        self._cancel_event.set()
        self.close()

    def close(self) -> None:
        """关闭通道。对端 receive() 收到 null。"""
        self._closed.set()
        try:
            self._my_outbox.put_nowait(None)   # 唤醒阻塞的 receive
        except Exception:
            pass

    def is_closed(self) -> bool:
        return self._closed.is_set()

    @property
    def cancel_event(self) -> threading.Event:
        """供 spawned agent 内部检查取消信号。"""
        return self._cancel_event
```

### 4.3 Channel 双端模型

每个 Channel 实例有两个端点，主线程和 spawned agent 各持有一个：

```python
class ChannelEndpoint:
    """Channel 的一个端点。"""
    def __init__(self, channel: Channel, is_main: bool):
        self._channel = channel
        if is_main:
            self._my_outbox = channel._to_spawned
            self._my_inbox = channel._from_spawned
        else:
            self._my_outbox = channel._from_spawned
            self._my_inbox = channel._to_spawned

    def send(self, msg): ...
    def receive(self, timeout=None): ...
    def try_receive(self): ...
    def cancel(self): ...    # 仅主线程端可用
    def close(self): ...
```

spawnagent 创建 Channel 后：
- 主线程端 → 作为返回值
- spawned agent 端 → 注入到 agent 的 `reply` 参数

### 4.3b Channel 在非 spawnagent 场景中的使用

channel 同样用于普通 agent 隔离环境中的通信。例如，主 agent 创建子 agent 并传递 channel：

```helen
agent Producer(output: Channel) {
    main {
        循环 i 在 range(10) {
            output.send("产品 " + str(i))
        }
        output.close()
    }
}

agent Consumer(input: Channel) {
    main {
        循环 {
            msg = input.receive()
            如果 msg == null { 跳出 }
            print("消费: " + msg)
        }
    }
}

// 创建 channel 连接两个 agent
let pipe = Channel()
spawnagent Producer(pipe)      // pipe 作为 output 传入
spawnagent Consumer(pipe)      // pipe 作为 input 传入
```

这里 `Channel()` 是 Channel 类型的构造函数，创建独立的消息通道。
设计与 spawnagent 返回的 channel 完全一致——同样的 send/receive/close/cancel 接口。

### 4.4 Channel 方法汇总

| 方法 | 说明 |
|------|------|
| `send(msg)` | 发送消息到对端（可传任意对象，包括 SharedStore 引用） |
| `receive(timeout?)` | 阻塞接收，超时返回 null，通道关闭返回 null |
| `try_receive()` | 非阻塞接收，无消息返回 null |
| `cancel()` | 发送取消信号 + 关闭通道（仅主线程端） |
| `close()` | 关闭通道 |
| `is_closed()` | 检查通道是否关闭 |

### 4.5 中文别名

| 英文 | 中文 |
|------|------|
| `send()` | `发送()` |
| `receive()` | `接收()` |
| `try_receive()` | `尝试接收()` |
| `cancel()` | `取消()` |
| `close()` | `关闭()` |
| `is_closed()` | `已关闭()` |

### 4.6 `mailbox_select` — 多路复用

```helen
let m1 = spawnagent StrategyA()
let m2 = spawnagent StrategyB()

result = mailbox_select([m1, m2])   // 谁先完成用谁
```

```python
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

## 5. snapshot 语义

### 5.1 规则：全部深复制，无例外

```python
def snapshot(self):
    new_bindings = {}
    for name, value in self._store.items():
        new_bindings[name] = copy.deepcopy(value)
    new_env = Environment(parent=...)
    new_env._store = new_bindings
    return new_env
```

| 类型 | snapshot 行为 | 说明 |
|------|--------------|------|
| `SharedStore` | **深复制** | 创建独立副本 |
| `Channel`（消息队列） | **深复制** | 创建独立空 channel（队列清空） |
| `list` / `dict` | 深复制 | 不变 |
| `int` / `str` / `bool` / `None` | 按引用（不可变类型） | 不变 |
| 函数 / 闭包 | 按引用（不可变） | 不变 |

注意：Channel 深复制后创建的是独立的空 channel，不与原 channel 连通。
若需要在 agent 间建立通信，应显式传递 channel 引用（通过参数或 channel.send）。

### 5.2 与 v1.17 的对比

| | v1.17（当前） | v3（本方案） |
|--|-------------|------------|
| SharedStore | 按引用 | **深复制** |
| channel（旧语法） | 按引用（= SharedStore） | **废弃声明语法** |
| Channel（消息队列） | 不存在 | **新增**，深复制 |
| list/dict | 深复制 | 深复制 |
| 通信模型 | 隐式共享（全有或全无） | 显式传递（通过 channel） |
| 隔离性 | 🔴 差 | 🟢 完全隔离 |

### 5.3 需要共享时

通过 channel 显式传递 shared store 引用：

```helen
shared store Config { let timeout = 30; let retries = 3 }

mailbox = spawnagent Worker()
mailbox.send(Config)    // 显式传递——只有这个 agent 能看到
```

深复制的 `SharedStore` 支持吗？——需要实现 `SharedStore.__deepcopy__`：

```python
class SharedStore:
    def __deepcopy__(self, memo):
        new_store = SharedStore(self._name, copy.deepcopy(self._fields, memo), {})
        for name, method in self._methods.items():
            new_store._methods[name] = SharedStoreMethod(method._node, new_store, ...)
        memo[id(self)] = new_store
        return new_store
```

---

## 6. shared store 与 channel 的角色

### 6.1 职责分工

| 工具 | 职责 | 通信模型 |
|------|------|---------|
| `shared store` | **数据共享** — 带锁的可变结构体，方法封装访问逻辑 | 共享可变状态（需显式传递引用） |
| `channel` | **agent 通信** — 消息队列，send/receive | 消息传递（阻塞/非阻塞） |

两者互补：
- `shared store` 适合多 agent 读写同一份状态（如计数器、缓存）
- `channel` 适合 agent 间传递消息和结果（如任务完成通知、流式进度）

### 6.2 channel 的通用性

channel 在**所有 agent 通信场景**中设计一致：

| 场景 | 创建方式 | 说明 |
|------|---------|------|
| spawnagent 跨线程 | `spawnagent` 自动创建 | 返回值即 Channel |
| agent 隔离环境通信 | `Channel()` 构造函数 | 手动创建，传递给 agent |
| 管道模式 | `Channel()` 连接多个 agent | producer-consumer 等模式 |

### 6.3 旧 `channel X { fields }` 语法废弃

```helen
// 旧语法——废弃
channel Result {
    let status: str = "pending"
    fn set_result(d: str) { status = "done" }
}

// 替代方案：
// 1. agent 间通信 → channel（消息队列）
// 2. 带锁结构体 → shared store
```

废弃原因：
- 运行时类型完全不同（消息队列 vs 带锁结构体），保留旧语法造成混淆
- `channel` 一词现在专指消息通道
- 旧 `channel` 的功能被 `shared store`（带锁结构体）和新 `Channel`（消息队列）完全覆盖

---

## 7. spawnagent 完整设计

### 7.1 语法

```helen
agent Worker(task: str, reply: Channel) {
    description "后台工作 agent"
    model "qwen3.7-plus"
    main {
        结果 = llm act "处理" + task on_chunk fn(chunk: str) {
            reply.send("进度: " + chunk)
        }
        reply.send("完成: " + 结果)
    }
}

// 主线程
mailbox = spawnagent Worker("数据分析")

// 持续读取进度
循环 {
    msg = mailbox.receive()
    如果 msg == null { 跳出 }
    print(msg)
}
```

### 7.2 执行流程

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

### 7.3 返回值

`spawnagent` 返回 `Channel` 类型的主线程端点。

```helen
let mailbox: Channel = spawnagent Worker("task")
```

### 7.4 fire-and-forget

```helen
spawnagent Logger("后台日志")   // 忽略返回值
```

### 7.5 错误处理

spawned agent 中未捕获的异常发送到 channel：

```python
def run_spawned():
    try:
        node.call.accept(spawned_interpreter)
    except Exception as e:
        reply_endpoint.send({"__error__": True, "message": str(e)})
    finally:
        reply_endpoint.close()
```

### 7.6 生命周期

| 事件 | 行为 |
|------|------|
| spawned agent 正常结束 | `reply.close()` → 主线程 `receive()` 返回 null |
| spawned agent 异常 | `reply.send(error_dict)` + `reply.close()` |
| 主线程 `mailbox.cancel()` | cancel_event.set() → spawned agent 流式循环中断 |
| 主线程进程退出 | daemon 线程随之死亡 |

---

## 8. async/await 废弃

### 8.1 理由

| 理由 | 说明 |
|------|------|
| 底层是线程池 | `_await_tasks` 用 `ThreadPoolExecutor`，和 `threading.Thread` 无本质区别 |
| 功能被 spawnagent 覆盖 | 所有并发场景均可用 spawnagent + channel 实现 |
| 有已知 bug | `on_chunk` 阻塞 event loop |
| 消除冗余 | 一个并发原语比两个更清晰 |

### 8.2 功能映射

| async/await | spawnagent 替代 |
|-------------|----------------|
| `let t = async Agent(...)` | `let m = spawnagent Agent(...)` |
| `result = await t` | `result = m.receive()` |
| `await [t1, t2]` | `[m1.receive(), m2.receive()]` |
| `async call fn()` | `spawnagent fn()` |

### 8.3 删除清单

| 删除内容 | 文件 |
|---------|------|
| `async` / `await` 关键字 | `tokens.py` |
| `AsyncCallStmtNode` / `AsyncCallExprNode` | `ast.py` |
| `visit_async_call_stmt` / `visit_async_call_expr` | `interpreter.py` |
| `AsyncLLMInterpreter` | `async_interpreter.py`（整个文件） |
| `_await_tasks` | `interpreter.py` |
| `Task` 类 | `task.py` |
| `act_async()` / `act_stream_async()` | `http_llm.py` |
| `route_async()` | `llm_runtime.py` |

关键字 `async`/`await`/`异步`/`等待` 彻底释放，不再保留。

---

## 9. 并发中断

### 9.1 spawnagent 的中断路径

```
mailbox.cancel()
  │
  ├─ channel._cancel_event.set()
  ├─ channel.close()
  │
  ↓
spawned agent 内部
  │
  ├─ reply.receive() 返回 null（通道关闭）
  ├─ llm act 流式循环检查 reply.cancel_event → break
  │
  ↓
spawned agent 退出
```

### 9.2 与流式中断方案的整合

spawnagent 中断不需要：
- ~~`_detach_threads` 列表~~ → channel 即句柄
- ~~SIGINT handler 遍历线程~~ → 通过 `mailbox.cancel()` 逐个取消
- ~~cancel_event 桥接线程~~ → channel 内部已有 cancel_event

### 9.3 Ctrl+C 行为

| 场景 | 行为 |
|------|------|
| REPL 中 Ctrl+C | 中断主线程当前 `llm act`，spawned agent 继续运行 |
| 脚本中 Ctrl+C | 主线程退出 → 进程退出 → daemon 线程死亡 |
| 显式取消 | `mailbox.cancel()` — 精确控制单个 spawned agent |

---

## 10. 语法与关键字

### 10.1 关键字变更

| 动作 | 英文 | 中文 |
|------|------|------|
| **新增** | `spawnagent` | `生成` |
| **废弃** | `detach` | `分离` |
| **废弃** | `async` | `异步` |
| **废弃** | `await` | `等待` |
| **废弃** | `channel`（声明语法） | `通道`（声明语法） |
| **保留** | `shared store` | `仓库` |
| **保留** | `shared let` | `共享定义` |
| **新增类型** | `Channel` | `消息通道` |

### 10.2 新增 stdlib 函数

| 函数 | 中文 | 说明 |
|------|------|------|
| `mailbox_select([channels])` | `邮箱选择([...])` | 多路复用，返回最先到达的消息 |

Channel 通过构造函数 `Channel()` 创建，不需要额外的 stdlib 工厂函数：

```helen
let pipe = Channel()                    // 创建独立 channel
let named = Channel("producer-consumer") // 可选名称
spawnagent Producer(pipe)
spawnagent Consumer(pipe)
```

### 10.3 Parser

```python
SPAWAGENT = auto()   # token: spawnagent / 生成

def _spawnagent_stmt(self):
    self._expect(TokenType.SPAWNAGENT)
    call = self._call_expr()
    return SpawnagentExprNode(call=call, span=...)
```

### 10.3 AST

```python
@dataclass(frozen=True)
class SpawnagentExprNode(ExprNode):
    call: CallNode    # agent 调用
```

继承 `ExprNode`（不是 `StmtNode`），因为 spawnagent 有返回值。

### 10.4 语义分析

- spawnagent 的参数必须是 agent 调用
- agent 的最后一个参数类型必须是 `Channel`
- 返回类型为 `Channel`
- `Channel` 类型支持方法：`send`/`receive`/`try_receive`/`cancel`/`close`/`is_closed` 及中文别名

---

## 11. 示例程序

### 11.1 基本用法

```helen
agent Fetcher(url: str, reply: Channel) {
    description "后台抓取网页"
    main {
        content = web_fetch(url)
        reply.send(content)
    }
}

let m1 = spawnagent Fetcher("https://example.com")
let m2 = spawnagent Fetcher("https://example.org")

print(m1.receive())
print(m2.receive())
```

### 11.2 流式进度

```helen
agent LongTask(prompt: str, reply: Channel) {
    main {
        result = llm act prompt on_chunk fn(chunk: str) {
            reply.send({type: "progress", data: chunk})
        }
        reply.send({type: "done", data: result})
    }
}

let mailbox = spawnagent LongTask("写一篇关于 AI 的论文")
循环 {
    msg = mailbox.receive()
    如果 msg == null { 跳出 }
    如果 msg["type"] == "progress" { print(msg["data"]) }
    否则 { print("完成: " + msg["data"]) }
}
```

### 11.3 竞争模式

```helen
let m1 = spawnagent StrategyA("问题")
let m2 = spawnagent StrategyB("问题")

let result = mailbox_select([m1, m2])
print("最快结果: " + result["message"])

// 取消另一个
如果 result["endpoint"] == m1 { m2.cancel() } 否则 { m1.cancel() }
```

### 11.4 双向通信

```helen
agent Calculator(reply: Channel) {
    main {
        循环 {
            cmd = reply.receive()
            如果 cmd == null 或 cmd == "quit" { 跳出 }
            reply.send(calculate(cmd))
        }
    }
}

let calc = spawnagent Calculator()
calc.send("2 + 3")
print(calc.receive())     // 5
calc.send("10 * 20")
print(calc.receive())     // 200
calc.send("quit")
```

### 11.5 显式共享 shared store

```helen
shared store Cache {
    let _data: dict = {}
    fn get(key: str): str? { return _data.get(key) }
    fn set(key: str, val: str) { _data[key] = val }
}

agent Worker(reply: Channel) {
    main {
        cache = reply.receive()     // 接收 shared store 引用
        cache.set("result", "42")
        reply.send("已写入缓存")
    }
}

let mailbox = spawnagent Worker()
mailbox.send(Cache)                 // 显式传递 shared store 引用
print(mailbox.receive())            // "已写入缓存"
print(Cache.get("result"))          // "42" — 同一个对象
```

### 11.6 fire-and-forget

```helen
spawnagent Logger("系统启动日志")
spawnagent Monitor("健康检查")
print("系统已启动")
```

---

## 12. 运行时实现

### 12.1 改动文件清单

| 文件 | 改动 |
|------|------|
| `helen/core/tokens.py` | 新增 `SPAWAGENT`/`生成`；废弃 `DETACH`/`分离`/`ASYNC`/`异步`/`AWAIT`/`等待`；废弃 `CHANNEL`/`通道`（声明语法） |
| `helen/core/parser.py` | 新增 `_spawnagent_stmt`；删除 `_detach_stmt`/`_async_call_stmt`/`_async_call_expr`/`_channel_decl` |
| `helen/core/ast.py` | 新增 `SpawnagentExprNode`；删除 `DetachStmtNode`/`AsyncCallStmtNode`/`AsyncCallExprNode`/`ChannelDeclNode` |
| `helen/semantic/analyzer.py` | spawnagent 语义检查；删除 channel 声明分析 |
| `helen/interpreter/interpreter.py` | 新增 `visit_spawnagent_expr`；删除 `visit_detach_stmt`/`visit_async_call_stmt`/`visit_async_call_expr`/`visit_channel_decl`；更新 `snapshot()` |
| `helen/interpreter/interpreter.py` | `SharedStore.__deepcopy__` 新增 |
| `helen/interpreter/async_interpreter.py` | **整个文件删除** |
| `helen/interpreter/task.py` | **整个文件删除** |
| `helen/runtime/channel.py` | **新文件** — Channel 消息队列 |
| `helen/runtime/llm_runtime.py` | 删除 `act_async`/`act_stream_async`/`route_async` |
| `helen/runtime/http_llm.py` | 删除 `act_stream_async` |
| `helen/stdlib/mailbox.py` | **新文件** — `mailbox_select` |

### 12.2 Channel 实现要点

```python
# helen/runtime/channel.py

import queue
import threading
import copy
from typing import Any


class Channel:
    """双向消息通道。agent 通信的通用工具。

    在 spawnagent 跨线程场景和普通 agent 隔离场景中设计一致。
    内部两个队列，支持双向通信。
    """

    def __init__(self, name: str = ""):
        self._name = name
        self._to_spawned = queue.Queue()
        self._from_spawned = queue.Queue()
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
            self._outbox.put_nowait(None)
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

### 12.3 SharedStore.__deepcopy__

```python
class SharedStore:
    def __deepcopy__(self, memo):
        import copy
        new_store = SharedStore(
            self._name,
            copy.deepcopy(self._fields, memo),
            {}   # methods 不复制（闭包引用旧环境）
        )
        memo[id(self)] = new_store
        return new_store
```

### 12.4 visit_spawnagent_expr

```python
def visit_spawnagent_expr(self, node: SpawnagentExprNode) -> object:
    from helen.runtime.channel import Channel, ChannelEndpoint

    call_node = node.call
    agent_name = call_node.callee.name
    agent_decl = self._agents.get(agent_name)
    if agent_decl is None:
        self.errors.error(...)
        return None

    # 评估参数（排除最后一个 Channel 参数）
    arg_values = [arg.accept(self) for arg in call_node.args]

    # 创建 Channel
    channel = Channel(name=f"spawn_{agent_name}")
    main_endpoint = ChannelEndpoint(channel, is_main_thread=True)
    spawned_endpoint = ChannelEndpoint(channel, is_main_thread=False)

    # 将 spawned 端追加到参数列表
    arg_values.append(spawned_endpoint)

    # 快照环境（全部深复制）
    env_snapshot = self.environment.snapshot()

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

    return main_endpoint
```

### 12.5 snapshot 变更

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

---

## 13. 现有代码迁移

由于 Helen 当前只有单一用户，直接替换，无需兼容。

### 13.1 关键字替换

| 旧 | 新 |
|----|-----|
| `detach Agent(...)` | `spawnagent Agent(...)` |
| `分离 Agent(...)` | `生成 Agent(...)` |
| `let t = async Agent(...)` | `let m = spawnagent Agent(...)` |
| `await t` | `m.receive()` |
| `await [t1, t2]` | `[m1.receive(), m2.receive()]` |

### 13.2 通信模式迁移

```helen
// 旧：detach + shared store 轮询
shared store Result { let done = false; let data = "" }
detach Worker("task")
循环 { 如果 Result.done { 跳出 } sleep(100) }

// 新：spawnagent + channel
let m = spawnagent Worker("task")
let data = m.receive()

// 旧：channel 声明语法
channel EventBus { let last_event = "" }

// 新：改用 shared store（如需带锁结构体）
shared store EventBus { let last_event = "" }
```

### 13.3 删除的文件

| 文件 | 动作 |
|------|------|
| `helen/interpreter/async_interpreter.py` | 删除 |
| `helen/interpreter/task.py` | 删除 |
| `tests/interpreter/test_detach_shared_store.py` | 重写为 `test_spawnagent.py` |
| `tests/execution/test_async_await.py` | 删除 |
| `tests/parser/test_detach.py` | 重写为 `test_spawnagent.py` |
| `tests/parser/test_llm_stream.py`（async 部分） | 删除 async 测试 |

---

## 14. 测试方案

### 14.1 新增测试文件

| 文件 | 覆盖 |
|------|------|
| `tests/runtime/test_channel.py` | Channel/ChannelEndpoint：send/receive/cancel/close/双向/超时 |
| `tests/interpreter/test_spawnagent.py` | spawnagent 基本用法、参数传递、channel 注入、返回值 |
| `tests/interpreter/test_spawnagent_isolation.py` | snapshot 全部深复制、shared store 独立副本、显式传递引用 |
| `tests/interpreter/test_spawnagent_interrupt.py` | cancel() 中断 spawned agent、cancel_event 传播 |
| `tests/execution/test_spawnagent_e2e.py` | 端到端：流式进度、竞争模式、双向通信、fire-and-forget、错误传播 |
| `tests/stdlib/test_mailbox_select.py` | mailbox_select 多路复用 |

### 14.2 关键测试用例

```python
class TestChannel:
    def test_send_receive(self):
    def test_receive_blocks_until_send(self):
    def test_receive_timeout_returns_null(self):
    def test_close_unblocks_receive(self):
    def test_cancel_sets_event(self):
    def test_bidirectional_communication(self):

class TestSpawnagent:
    def test_basic_spawn_and_receive(self):
    def test_spawned_agent_gets_channel_as_last_param(self):
    def test_returns_channel_type(self):
    def test_error_propagation(self):
    def test_cancel_stops_spawned_agent(self):
    def test_fire_and_forget(self):

class TestSpawnagentIsolation:
    def test_shared_store_deep_copied(self):
    def test_explicit_reference_passing_via_channel(self):
    def test_spawned_cannot_see_parent_shared_store(self):

class TestMailboxSelect:
    def test_returns_first_available(self):
    def test_timeout_returns_null(self):
```

---

## 15. 与其他方案的关系

### 15.1 与流式中断方案的关系

`streaming-interrupt-proposal.md` 需适配：

| 原方案 Phase | 适配 |
|-------------|------|
| Phase 1-5（主线程中断） | **不变** |
| Phase 6（detach 中断） | **替换**为 spawnagent 中断（通过 `mailbox.cancel()`） |
| Phase 7（async/await 预留） | **删除** |

### 15.2 实施顺序

```
spawnagent 方案（优先）
  ├─ Phase A: Channel 运行时（channel.py）
  ├─ Phase B: spawnagent 语法（token + parser + AST）
  ├─ Phase C: visit_spawnagent_expr + snapshot 全部深复制
  ├─ Phase D: 删除 detach / async / await / channel 声明语法
  ├─ Phase E: mailbox_select stdlib
  └─ Phase F: SharedStore.__deepcopy__

流式中断方案（后续）
  ├─ Phase 1-5: 主线程中断（不变）
  └─ Phase 6: spawnagent 中断（通过 channel.cancel）
```

---

## 16. 开放问题

| 编号 | 问题 | 当前建议 | 备选 |
|------|------|---------|------|
| Q1 | spawned agent 的 reply 参数是显式声明还是自动注入？ | 显式声明（类型安全） | 自动注入 + `当前回复通道()` stdlib |
| Q2 | `shared store` 是否也应该废弃？ | 保留——作为"带锁结构体"有用 | 废弃，用普通 dict + 手动锁 |
| Q3 | mailbox_select 是 stdlib 函数还是语法关键字？ | stdlib 函数 | 语法关键字 `select m1, m2` |
| Q4 | spawned agent 异常时，默认发错误消息还是抛异常？ | 发错误消息 | 抛异常 |
| Q5 | `async`/`await` 关键字是否保留为保留字？ | 不保留，释放命名空间 | 保留为保留字 |
| Q6 | Channel 是否需要容量限制？ | 无限制 | 有界队列防内存溢出 |
| Q7 | spawnagent 是否支持 agent 之外的函数调用？ | 仅 agent 调用 | 支持任意函数 |
| Q8 | daemon 线程的 stdout 交错如何处理？ | 文档说明，暂不解决 | queue 序列化 |
| Q9 | SharedStore 深复制时方法是否复制？ | 不复制（闭包引用旧环境） | 复制并重新绑定 |

---

## 附录 A: 并发模型演进

```
v1.0-v1.11: 单线程 agent
v1.12: + detach（fire-and-forget，返回 null）
       + async/await（Task + ThreadPoolExecutor）
       + shared store / channel（= SharedStore，按引用传递）
v1.17: + SharedStore/channel 在 snapshot 中按引用传递（v1.12 修复）
v1.18（本方案）:
       + spawnagent（替代 detach，返回 Channel）
       + Channel 升级为消息队列（send/receive/cancel）
       + snapshot 全部深复制，无例外
       + 共享通过 channel 显式传递引用
       - detach 废弃
       - async/await 废弃
       - channel X { fields } 声明语法废弃
       + shared store 角色降级为带锁结构体
```
