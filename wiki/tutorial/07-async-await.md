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
