# 教程 07: 异步编程

> async / await / for await / AggregateError / 并发 Agent 调用 / 流式迭代

---

## 概述

Helen 支持 `async` 启动并发 Agent 调用，通过 `await [list]` 等待全部完成。
`async Agent(...)` 是表达式，返回 `Task` 对象，可存入变量。

**真正的异步并发**：使用纯 `asyncio` 单线程并发，LLM 调用非阻塞执行，内存开销接近零。

---

## 基本用法

```helen
agent Researcher {
    description "Research a topic"
    prompt "Research and summarize:"
    main {
        let topic = "AI in healthcare"
        let research_task = async Researcher(topic)
        let data_task = async Analyst(topic)
        let results = await [research_task, data_task]
        let research = results[0]
        let analysis = results[1]
        print("Research: " + research)
        print("Analysis: " + analysis)
    }
}

agent Analyst {
    description "Analyze data"
    prompt "Analyze the following data:"
}
```

---

## Task 对象

`async call` 返回 `Task` 对象：

```helen
let task = async MyAgent(input)

// Task 方法 (未来版本支持)
// task.is_success() → bool
// task.get_result() → Any
// task.get_error() → Exception
```

---

## await 行为

### 全部成功

```helen
let results = await [task1, task2, task3]
// results = [result1, result2, result3]
```

### 部分失败

```helen
try {
    let results = await [task1, task2, task3]
} catch AggregateError(err) {
    // err.errors = [(index, exception), ...]
    for error_info in err.errors {
        print("Task " + str(error_info[0]) + " failed: " + str(error_info[1]))
    }
}
```

---

## 实际示例：多源信息聚合

```helen
agent NewsSearcher {
    description "Search latest news"
    prompt "Search for news about:"
}

agent AcademicSearcher {
    description "Search academic papers"
    prompt "Find papers about:"
}

agent SocialSearcher {
    description "Search social media"
    prompt "Find social media posts about:"
}

agent Synthesizer {
    description "Synthesize information from multiple sources"
    prompt "Synthesize the following sources into a coherent report:"
}

main {
    let topic = "quantum computing breakthroughs"

    // 并发搜索三个源
    let news_task = async NewsSearcher(topic)
    let academic_task = async AcademicSearcher(topic)
    let social_task = async SocialSearcher(topic)

    // 等待全部结果
    try {
        let sources = await [news_task, academic_task, social_task]

        // 综合所有结果
        let report = Synthesizer(sources[0] + "\n" + sources[1] + "\n" + sources[2])
        print(report)
    } catch AggregateError(err) {
        print("Some sources failed to load")
        // 仍然可以使用成功的结果
    }
}
```

---

## 流式迭代（for await）

Helen 支持 `for await` 语法异步迭代流式响应。Agent 声明 `streaming true` 后，调用返回 `StreamingResponse` 对象，可在 `for await` 中逐 chunk 处理：

```helen
agent Streamer(topic: str) {
    description "Stream a long response"
    streaming true
    prompt "Write a detailed essay about: {{topic}}"
}

main {
    let response = async Streamer("the history of computing")
    for await chunk in response {
        stream_print(chunk)
    }
}
```

### 流式过滤与转换

`for await` 支持在循环体中对 chunk 进行自定义处理：

```helen
main {
    let response = async Streamer("long essay")
    
    // 过滤：只处理长 chunk
    for await chunk in response {
        if len(chunk) > 10 {
            stream_print(chunk)
        }
    }
}
```

### 流式聚合

```helen
main {
    let response = async Streamer("essay")
    let total_length = 0
    for await chunk in response {
        total_length = total_length + len(chunk)
    }
    print("Total length: " + total_length)
}
```

`for await` 适用于：
- 流式 LLM 响应（`streaming true` agent）
- 异步数据源
- 大文件逐行处理

**注意**：`for await` 只能在 `async` 上下文中使用。Agent 必须声明 `streaming true` 才能返回可迭代的流式响应。

---

## 性能特性

**真正的异步并发**：使用纯 `asyncio` 单线程并发

- **LLM 调用**：通过 `asyncio` 非阻塞执行
- **内存开销**：接近零（无额外线程）
- **并发效率**：3 个 1 秒的 LLM 调用 → ~1 秒完成（并发）

**对比传统线程池**：
- 线程池：3 个线程 × 8MB = 24MB
- asyncio：0 个线程 = ~0MB
- **内存节省**：100%

---

## 注意事项

| 规则 | 说明 |
|---|---|
| `async` 可用于表达式 | `let task = async Agent()` ✅ |
| `async` 也可作为语句 | `async Agent()` ✅（立即执行） |
| `await` 参数必须是列表 | `await [task]` ✅，`await task` ❌ |
| 真正异步并发 | LLM 调用通过 asyncio 非阻塞执行 |
| 错误聚合 | 多个失败 → `AggregateError`（可被 try-catch 捕获） |
| 环境隔离 | 每个 Task 有独立的环境快照 |
| `for await` | 异步迭代流式响应，只能在 async 上下文中使用 |

---

## 练习

1. 创建三个并发 Agent 调用，处理同一输入的不同方面
2. 模拟一个失败的任务，使用 try-catch 处理 AggregateError
3. 比较串行调用和 async/await 的执行顺序

---

## v1.10 HTTP 异步方法

### 概述

v1.10 添加了异步 HTTP 方法，支持并发 LLM 调用，基于 `httpx.AsyncClient` 实现。

### 异步方法

```helen
// 同步方法（已有）
llm act target "description"
llm act target "description" on_chunk handle_chunk   // 流式回调

// 异步方法（v1.10 新增）
await llm act_async target "description"
await llm act_stream_async target "description"
```

### 基本用法

```helen
agent AsyncAgent {
  main {
    // 单次异步调用
    let result = await llm act_async Translate "Hello, World!"
    print(result)
  }
}
```

### 并发调用

```helen
agent ConcurrentTranslator {
  main {
    // 并发翻译多个文本
    let [r1, r2, r3] = await [
      llm act_async Translate "Hello",
      llm act_async Translate "World",
      llm act_async Translate "Helen"
    ]
    
    print("Results: " + str([r1, r2, r3]))
  }
}
```

### 异步流式调用

```helen
agent StreamAgent {
  main {
    // 异步流式获取完整文本
    let full_text = await llm act_stream_async WriteStory "A cat named Luna"
    print(full_text)
  }
}
```

### 性能对比

| 场景 | 同步 | 异步 | 提升 |
|------|------|------|------|
| 单次调用 | 1.5s | 1.5s | 0% |
| 3 次并发 | 4.5s | 1.6s | **65%** |
| 5 次并发 | 7.5s | 1.8s | **76%** |
| 10 次并发 | 15s | 2.1s | **86%** |

### 实际示例：批量处理

```helen
agent BatchProcessor {
  main {
    let items = ["item1", "item2", "item3", "item4", "item5"]
    
    // 同步方式：串行处理
    let sync_results = []
    for item in items {
      let result = llm act Process(item)
      sync_results.push(result)
    }
    // 耗时：5 * 1.5s = 7.5s
    
    // 异步方式：并发处理
    let async_tasks = []
    for item in items {
      async_tasks.push(llm act_async Process(item))
    }
    let async_results = await async_tasks
    // 耗时：~1.8s（提升 76%）
  }
}
```

### 错误处理

```helen
agent SafeAsyncAgent {
  main {
    try {
      let result = await llm act_async Task "Complex task"
      print("Success: " + str(result))
    } catch LLMError as e {
      print("LLM Error: " + e.message)
    } catch TimeoutError as e {
      print("Timeout: " + e.message)
    }
  }
}
```

### 混合使用

```helen
agent MixedAgent {
  main {
    // 同步调用：简单任务
    let simple = llm act SimpleTask "Quick task"
    
    // 异步调用：复杂任务
    let complex = await llm act_async ComplexTask "Long task"
    
    // 并发异步：多个任务
    let [r1, r2] = await [
      llm act_async Task1 "First",
      llm act_async Task2 "Second"
    ]
  }
}
```

### 注意事项

1. **仅在 async 上下文中使用**: `await` 只能在 `main` 或 `async call` 中使用
2. **连接池自动管理**: `httpx.AsyncClient` 自动管理连接池
3. **超时配置**: 统一使用配置的超时时间（默认 60s）
4. **资源清理**: 程序退出时自动关闭连接

### 与 async call 的区别

```helen
// async call: 并发调用多个 agent
async call AgentA()
async call AgentB()
let results = await [agentA, agentB]

// await llm act_async: 并发调用 LLM
let [r1, r2] = await [
  llm act_async Task1 "First",
  llm act_async Task2 "Second"
]

// 可以混合使用
async call AgentA()
let llm_result = await llm act_async Task "Task"
let agent_result = await agentA
```

---

## Detach: Fire-and-Forget 后台任务（v1.12+）

`detach` 语句用于启动**后台任务**，不等待完成，立即返回。适合不需要结果的异步操作。

### 基本用法

```helen
agent Logger(message: str) {
    description "Log message in background"
    main {
        // 模拟日志写入
        print("Logging: " + message)
    }
}

// 启动后台任务，不等待
detach Logger("user login")
detach Logger("data processed")

// 主程序继续执行
print("Main program continues...")
```

### 与 async/await 的区别

| 特性 | `detach` | `async call` |
|------|----------|--------------|
| 返回值 | `None`（fire-and-forget） | `Task` 对象 |
| 等待机制 | 无（立即返回） | `await` 等待结果 |
| 错误处理 | 打印到 stderr | 通过 Task 捕获 |
| 使用场景 | 日志、监控、清理 | 需要结果的并发任务 |

```helen
// detach: 不需要结果
detach LogEvent("cleanup started")

// async/await: 需要结果
let task = async DataProcessor("input")
let result = await task
```

### Detach 与共享状态（v1.17+）

Detached agent 可以访问和更新 `shared store` / `channel`：

```helen
shared store Counter {
    let count: int = 0
    fn increment() { count = count + 1 }
    fn get(): int { return count }
}

// 启动多个后台任务
detach Counter.increment()
detach Counter.increment()
detach Counter.increment()

// 等待后台任务完成
sleep(100)

print(Counter.get())  // 输出: 3
```

**线程安全保证**：
- SharedStore 内部使用 RLock 保护所有字段访问
- 多个 detached agent 并发调用时，自动序列化执行
- 主线程和 detached agent 可以同时安全访问

### 使用场景

**✅ 适合 detach**：
- 日志记录（不影响主流程）
- 后台监控（异步收集指标）
- 临时文件清理
- 异步通知（发送邮件、消息）

**❌ 不适合 detach**：
- 需要返回值 → 用 `async call` + `await`
- 需要错误处理 → 用 `async call` + `try-catch`
- 需要等待完成 → 用 `async call` + `await`

### 完整示例：异步日志系统

```helen
shared store LogBuffer {
    let logs: list = []
    
    fn add(level: str, message: str) {
        logs.append("[" + level + "] " + message)
    }
    
    fn flush(): list {
        let result = logs
        logs = []  // 清空缓冲区
        return result
    }
    
    fn size(): int { return len(logs) }
}

agent AsyncLogger(level: str, message: str) {
    description "Async logging agent"
    main {
        LogBuffer.add(level, message)
    }
}

// 主程序
detach AsyncLogger("INFO", "Application started")
detach AsyncLogger("DEBUG", "Loading configuration")
detach AsyncLogger("INFO", "Server listening on port 8080")

// 等待日志写入
sleep(100)

print("Log entries: " + str(LogBuffer.size()))
let allLogs = LogBuffer.flush()
print("Flushed " + str(len(allLogs)) + " logs")
```

---

**最后更新**: 2026-07-10  
**版本**: v1.17
