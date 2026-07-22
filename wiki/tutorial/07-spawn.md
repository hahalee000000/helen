# 教程 07: 并发编程 (spawn)

> spawn / Channel 消息队列 / mailbox_select / 显式共享 / fire-and-forget / 错误处理

---

## 概述

Helen v1.18 使用 `spawn` + Channel 消息队列实现并发。`spawn Agent(...)` 返回一个 Channel（邮箱），用于双向通信。

**核心原则**：
- 一个并发原语（`spawn`）+ 一个通信机制（Channel 消息队列）
- **隔离优先**：snapshot 全部深复制，agent 默认与外部环境完全隔离
- **上下文显式传递**：spawn 创建的 agent **完全看不到**父 agent 的变量、transcript、working memory——它只能看到传入的参数和 Channel。**调用前必须显式决定要传什么上下文**
- 共享是显式的：通过 Channel 传递 SharedStore 引用

> 💡 这条原则适用于所有 agent 调用，不只是 spawn。详见 [教程 05: 核心设计原则](05-agents.md#核心设计原则调用者决定上下文)。

---

## spawn 基本用法

```helen
agent Worker(task: str, reply: Channel) {
    description "后台工作 agent"
    main {
        let result = "处理完成: " + task
        reply.send(result)
        // 函数结束 → reply 自动关闭 → 主线程 receive() 收到 null
    }
}

main {
    let mailbox = spawn Worker("数据分析")
    let result = mailbox.receive()
    print(result)  // "处理完成: 数据分析"
}
```

**要点**：
- `spawn` 返回 `Channel` 类型（邮箱）
- spawned agent 的**最后一个参数**接收通信 channel（由 spawn 自动注入）
- `reply.send(msg)` 发送消息到主线程
- `mailbox.receive()` 阻塞等待消息

---

## Channel 消息队列

### send / receive

```helen
// 发送消息
mailbox.send("hello")

// 阻塞接收
let msg = mailbox.receive()

// 带超时的接收
let msg = mailbox.receive(5.0)  // 5 秒超时，返回 null
```

### try_receive（非阻塞）

```helen
let msg = mailbox.try_receive()
if msg == null {
    print("暂无消息")
}
```

### cancel（取消）

```helen
mailbox.cancel()  // 发送取消信号 + 关闭通道
```

spawned agent 内部可通过 `reply.cancel_event` 检查取消信号：

```helen
agent LongTask(reply: Channel) {
    main {
        for i in range(100) {
            if reply.cancel_event.is_set() { break }
            // 执行工作...
            reply.send("进度: " + str(i))
        }
    }
}
```

### 流式中断（cancel_event + on_chunk 返回 false）

当 spawned agent 正在流式输出 LLM 响应时，主线程可通过 `mailbox.cancel()` 发送取消信号。spawned agent 内部可通过两种方式响应：

1. **检查 `reply.cancel_event`**：在循环中检测取消信号
2. **`on_chunk` 回调返回 `false`**：立即中断 LLM 流式输出

```helen
agent StreamWorker(prompt: str, reply: Channel) {
    main {
        let result = llm act prompt on_chunk fn(chunk: str) {
            // 检查取消信号：如果主线程已取消，返回 false 中断流式
            if reply.cancel_event.is_set() {
                return false  // 立即停止 LLM 流式输出
            }
            reply.send({type: "chunk", data: chunk})
            return true  // 继续接收下一个 chunk
        }
        reply.send({type: "done", data: result})
    }
}

main {
    let mailbox = spawn StreamWorker("写一篇长文")
    // 读取前 3 个 chunk 后取消
    let count = 0
    loop {
        let msg = mailbox.receive()
        if msg == null { break }
        print(msg["data"])
        count = count + 1
        if count >= 3 {
            mailbox.cancel()  // 发送取消信号
            break
        }
    }
}
```

### close（关闭）

```helen
mailbox.close()  // 关闭通道，对端 receive() 返回 null
```

### 完整示例：流式进度

```helen
agent LongTask(prompt: str, reply: Channel) {
    main {
        let result = llm act prompt on_chunk fn(chunk: str) {
            reply.send({type: "progress", data: chunk})
        }
        reply.send({type: "done", data: result})
    }
}

main {
    let mailbox = spawn LongTask("写一篇关于 AI 的论文")
    loop {
        let msg = mailbox.receive()
        if msg == null { break }
        if msg["type"] == "progress" {
            print(msg["data"])
        } else {
            print("完成: " + msg["data"])
        }
    }
}
```

---

## 竞争模式 (mailbox_select)

`mailbox_select([m1, m2, ...])` 从多个 channel 中接收第一个到达的消息：

```helen
agent StrategyA(problem: str, reply: Channel) {
    main {
        let result = llm act "策略A解决: " + problem
        reply.send(result)
    }
}

agent StrategyB(problem: str, reply: Channel) {
    main {
        let result = llm act "策略B解决: " + problem
        reply.send(result)
    }
}

main {
    let m1 = spawn StrategyA("复杂问题")
    let m2 = spawn StrategyB("复杂问题")

    let result = mailbox_select([m1, m2])
    print("最快结果: " + result["message"])

    // 取消另一个
    if result["endpoint"] == m1 {
        m2.cancel()
    } else {
        m1.cancel()
    }
}
```

---

## 显式共享（通过 Channel 传递 SharedStore）

spawned agent 默认与外部环境完全隔离。如需访问主线程的 shared store，通过 channel 显式传递引用：

```helen
shared store Counter {
    let count: int = 0
    fn inc() { count = count + 1 }
    fn get(): int { return count }
}

agent Worker(reply: Channel) {
    main {
        // 从 channel 接收 shared store 引用
        let store = reply.receive()
        store.inc()
        store.inc()
        reply.send("done")
    }
}

main {
    let mailbox = spawn Worker()
    mailbox.send(Counter)           // 显式传递引用
    print(mailbox.receive())        // "done"
    print(Counter.get())            // 2 — 同一个对象，修改可见
}
```

**为什么需要显式传递？**
- snapshot 全部深复制，spawned agent 默认得到 SharedStore 的独立副本
- 通过 channel 传递引用是**有意为之**的共享，开发者明确知道哪些状态被共享

---

## fire-and-forget

不需要结果时，忽略 spawn 的返回值：

```helen
spawn Logger("系统启动日志")
spawn Monitor("健康检查")
print("系统已启动")  // 立即执行，不等待 spawned agent 完成
```

---

## 双向通信

Channel 支持双向通信，主线程和 spawned agent 可以互发消息：

```helen
agent Calculator(reply: Channel) {
    main {
        loop {
            let cmd = reply.receive()
            if cmd == null || cmd == "quit" { break }
            reply.send(calculate(cmd))
        }
    }
}

main {
    let calc = spawn Calculator()
    calc.send("2 + 3")
    print(calc.receive())     // 5
    calc.send("10 * 20")
    print(calc.receive())     // 200
    calc.send("quit")
}
```

---

## 错误处理

spawned agent 中未捕获的异常会通过 channel 传播：

```helen
agent RiskyTask(reply: Channel) {
    main {
        let result = 100 / 0  // 抛出异常
        reply.send(result)
    }
}

main {
    let mailbox = spawn RiskyTask()
    let msg = mailbox.receive()
    if msg != null && msg["__error__"] == true {
        print("spawned agent 出错: " + msg["message"])
    }
}
```

**生命周期**：

| 事件 | 行为 |
|------|------|
| spawned agent 正常结束 | `reply.close()` → 主线程 `receive()` 返回 null |
| spawned agent 异常 | `reply.send({__error__: true, message: ...})` + `reply.close()` |
| 主线程 `mailbox.cancel()` | cancel_event.set() → spawned agent 可检查取消信号 |
| 主线程进程退出 | daemon 线程随之死亡 |

---

## 中文别名

所有关键字和方法都有中文别名：

| 英文 | 中文 |
|------|------|
| `spawn` | `分生` |
| `mailbox.send()` | `邮箱.发送()` |
| `mailbox.receive()` | `邮箱.接收()` |
| `mailbox.try_receive()` | `邮箱.尝试接收()` |
| `mailbox.cancel()` | `邮箱.取消()` |
| `mailbox.close()` | `邮箱.关闭()` |
| `mailbox_select([...])` | `邮箱选择([...])` |

中文示例：

```helen
智能体 工作者(任务: str, 回复: 消息通道) {
    主函 {
        回复.发送("完成: " + 任务)
    }
}

主函 {
    设 邮箱 = 分生 工作者("数据分析")
    设 结果 = 邮箱.接收()
    打印(结果)
}
```

---

## 与旧 async/await 的对比

| 旧 async/await | 新 spawn |
|----------------|---------------|
| `let t = async Agent(...)` | `let m = spawn Agent(...)` |
| `result = await t` | `result = m.receive()` |
| `await [t1, t2]` | `[m1.receive(), m2.receive()]` |
| `detach Agent(...)` | `spawn Agent(...)`（忽略返回值） |

**为什么替换？**
- `async/await` 底层是线程池，与 `threading.Thread` 无本质区别
- spawn + channel 能覆盖所有场景，且在流式、取消、竞争模式上更好
- 一个并发原语比两个更清晰

---

## 注意事项

| 规则 | 说明 |
|---|---|
| `spawn` 参数 | 必须是 agent 调用 |
| 最后一个参数 | 必须是 `Channel` 类型（由 spawn 自动注入） |
| 返回类型 | `Channel`（主线程端点） |
| 隔离 | snapshot 全部深复制，无例外 |
| 共享 | 通过 channel 显式传递引用 |
| daemon 线程 | spawned agent 在 daemon 线程中运行 |

---

## Spawn Transcript 管理 (v1.23.7+)

每个 spawn 的 agent 都有独立的 transcript session。v1.23.7 引入 spawn 关系追踪和级联管理功能。

### 查询 Spawn 关系

```helen
// 获取当前 session 的所有直接子 session
设 子会话 = 获取子会话()
对于 子会话 中的 每个子 {
    打印("Spawned: " + 每个子["session_id"])
    打印("  Agent: " + 每个子["agent_name"])
}

// 获取完整 spawn 树（包括嵌套 spawn）
设 会话树 = 获取会话树()
打印("Root: " + 会话树["session_id"])
对于 会话树["children"] 中的 每个子 {
    打印("  Child: " + 每个子["session_id"])
}
```

### 聚合查看

```helen
// 查看主 session + 所有 spawn 的完整执行流程
设 所有消息 = 回放完整会话()
对于 所有消息 中的 消息 {
    打印("[" + 消息["session_id"] + "] " + 消息["role"] + ": " + 消息["content"][:50])
}

// 跨 spawn 搜索
设 错误 = 搜索会话("error", 包含spawn=true)
```

### 级联删除

删除 session 时，默认级联删除所有 spawn 子会话，避免孤儿 transcript：

```helen
// 删除 session 及其所有 spawn（默认）
删除会话("session_abc123")

// 只删除指定 session，保留 spawn
删除会话("session_abc123", 级联=false)

// 清理旧 session（级联删除 spawn）
清理会话(保留数量=10)  // 保留最近 10 个，级联删除 spawn
```

**设计原理**：
- Spawn 是子任务，生命周期应绑定到主 session
- 避免孤儿 transcript（主 session 删除后，spawn 失去上下文）
- 简化清理流程，无需手动查找和删除所有 spawn

> **详细文档**：参见 `10-stdlib.md` 的 "Transcript 函数" 章节

---

## Session 恢复与调试 (v1.24+)

### 启动时恢复 Session

v1.24 支持在启动时指定恢复历史 session，方便调试和继续工作：

```bash
# 恢复指定 session
helen --session=session_xxx file.helen
helen repl --session=session_xxx

# 自动恢复最近的 session
helen --resume-latest file.helen
helen repl --resume-latest
helen repl -r  # 简写
```

### Python API 恢复 Session

```python
from helen.interpreter import Interpreter

# 恢复指定 session
interp = Interpreter(session_id="session_xxx")

# 恢复最近的 session
from helen.runtime.session_manager import SessionManager
manager = SessionManager()
sessions = manager.list_sessions()
if sessions:
    latest_sid = sessions[0]["session_id"]
    interp = Interpreter(session_id=latest_sid)
```

### 调试 Spawn 执行流程

结合 session 恢复和 spawn 追踪，可以完整调试多 agent 协作：

```bash
# 1. 运行程序，记录 session_id
helen my_agent.helen
# 输出: 当前 session: session_abc123

# 2. 恢复 session，查看完整 spawn 树
helen --session=session_abc123 debug.helen
```

```helen
// debug.helen: 分析之前的执行流程
main {
    // 查看 spawn 树
    let tree = get_spawn_tree()
    print("Spawn 树:")
    for child in tree["children"] {
        print("  - " + child["session_id"])
    }

    // 聚合查看所有消息
    let all = replay_full_session()
    for msg in all {
        print("[" + msg["session_id"] + "] " + msg["role"] + ": " + msg["content"][:50])
    }
}
```

---

## 练习

1. 创建两个并发 agent，分别处理不同任务，用 `mailbox.receive()` 获取结果
2. 实现竞争模式：两个 agent 解决同一问题，用 `mailbox_select` 取最快结果
3. 实现双向通信：spawned agent 接收指令，返回计算结果
4. 使用 shared store + channel 实现显式共享的计数器

---

**最后更新**: 2026-07-22  
**版本**: v1.24
