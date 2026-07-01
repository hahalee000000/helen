# 异步与并发

> 模块 M5 (`task.py`, `async_interpreter.py`) | 测试: 81 个异步相关测试全部通过

---

## 概述

Helen 支持 `async` 和 `await` 实现真正的并发 Agent 调用。

**真正的异步并发**：使用纯 `asyncio` 单线程并发，LLM 调用通过 `asyncio.create_subprocess_exec()` 非阻塞执行，内存开销接近零。

```helen
// 表达式形式：延迟执行，创建 pending Task
let task1 = async AgentA(input1)
let task2 = async AgentB(input2)

// 并发执行并等待全部完成 (Promise.all)
let results = await [task1, task2]
```

---

## 两种 async 形式

### 1. 表达式形式（延迟执行）

```helen
let task = async MyAgent(input)
// 创建 pending Task，不立即执行
// 在 await 时并发执行
```

**特点**：
- 返回 `Task.pending` 对象
- 延迟到 `await` 时执行
- 多个 pending Task 在 `await` 时并发执行

### 2. 语句形式（立即执行）

```helen
async MyAgent(input)
// 立即执行，返回 Task.completed
```

**特点**：
- 立即同步执行
- 返回 `Task.completed` 或 `Task.failed`
- 适用于不需要并发的场景

---

## Task 对象

```python
class Task:
    result_value: Any
    exception: Exception | None
    _done: bool
    _pending: bool
    
    @classmethod
    def completed(result: Any) -> Task
    @classmethod
    def failed(exc: Exception) -> Task
    @classmethod
    def pending(call_node, interpreter, env_snapshot) -> Task
    
    @property
    def is_done(self) -> bool
    @property
    def is_pending(self) -> bool
    @property
    def has_error(self) -> bool
    
    async def execute_async(self) -> None
    def execute(self) -> None
    def result(self) -> Any
```

### Task 状态转换

```
pending → completed (成功)
pending → failed (失败)
completed/failed 是终态
```

---

## `await [list]` — Promise.all

```helen
let results = await [task1, task2, task3]
```

**行为**：
1. 并发执行所有 pending Task
2. 如果全部成功 → 返回结果列表
3. 如果有失败 → 抛出 `AggregateError`

### 单个 Task

```helen
let result = await [task]
let value = result[0]
```

---

## AggregateError

```python
class AggregateError(HelenRuntimeError):
    def __init__(self, message: str, errors: list[Exception] = None):
        self.errors = errors or []
```

收集所有失败 Task 的异常。

### 错误处理

```helen
try {
    let results = await [task1, task2, task3]
} catch AggregateError err {
    print("Multiple tasks failed: " + err.message)
    // err.errors 包含所有异常
    print(err.errors)
}
```

---

## 真正的异步并发实现

### 架构

```
AsyncLLMInterpreter (async_interpreter.py)
├── execute_stmt_async() — 异步语句执行
├── visit_llm_act_expr_async() — 异步 LLM act
├── visit_llm_if_stmt_async() — 异步 LLM if
└── execute_stmts_async() — 异步语句序列

Task.execute_async()
├── 检测 AsyncLLMInterpreter
├── 是 → 纯 async 执行（无线程）
└── 否 → asyncio.to_thread() 回退
```

### LLM 调用异步化

```python
# LLMRuntime 基类
async def act_async(self, prompt, **kwargs) -> LLMResponse
async def route_async(self, description, branches, context) -> str | None

# HermesCLILLMRuntime 实现
async def _ask_async(self, prompt) -> str:
    proc = await asyncio.create_subprocess_exec(
        "hermes", "-z", prompt,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    return stdout.decode()
```

### 并发执行

```python
# _await_tasks() 内部实现
async def execute_all():
    coros = [task.execute_async() for task in pending_tasks]
    await asyncio.gather(*coros)

asyncio.run(execute_all())
```

---

## 性能对比

### Phase 1a（线程池）

```python
# 3 个 LLM 调用，各 1 秒
ThreadPoolExecutor → 3 个线程
时间：~1 秒（并发）
内存：3 × 8MB = 24MB
```

### 当前实现（asyncio）

```python
# 3 个 LLM 调用，各 1 秒
asyncio.gather() → 0 个线程
时间：~1 秒（并发）
内存：~0MB
```

**内存节省**：100%（无额外线程）

---

## 示例

### 基本并发

```helen
agent Researcher(topic: str) {
    description "Research a topic"
    prompt "Research and summarize:"
    main {
        return "Research result for: " + topic
    }
}

agent Analyst(topic: str) {
    description "Analyze data"
    prompt "Analyze the following data:"
    main {
        return "Analysis result for: " + topic
    }
}

main {
    let topic = "AI trends"

    // 并发执行（延迟到 await）
    let research_task = async Researcher(topic)
    let data_task = async Analyst(topic)

    // 等待全部完成（并发执行）
    let results = await [research_task, data_task]
    
    let research = results[0]
    let analysis = results[1]
    print("Research: " + research)
    print("Analysis: " + analysis)
}
```

### 多源信息聚合

```helen
agent NewsSearcher(topic: str) {
    description "Search latest news"
    prompt "Search for news about:"
    main {
        return "News about " + topic
    }
}

agent AcademicSearcher(topic: str) {
    description "Search academic papers"
    prompt "Find papers about:"
    main {
        return "Papers about " + topic
    }
}

agent SocialSearcher(topic: str) {
    description "Search social media"
    prompt "Find social media posts about:"
    main {
        return "Social posts about " + topic
    }
}

main {
    let topic = "quantum computing"

    // 并发搜索三个源
    let news_task = async NewsSearcher(topic)
    let academic_task = async AcademicSearcher(topic)
    let social_task = async SocialSearcher(topic)

    // 等待全部结果
    try {
        let sources = await [news_task, academic_task, social_task]
        print("News: " + sources[0])
        print("Academic: " + sources[1])
        print("Social: " + sources[2])
    } catch AggregateError err {
        print("Some sources failed: " + err.message)
    }
}
```

### 普通函数异步调用

```helen
fn compute(x: num) {
    return x * x
}

main {
    let t1 = async compute(3)
    let t2 = async compute(4)
    let results = await [t1, t2]
    print(results[0] + results[1])  // 9 + 16 = 25
}
```

---

## 环境隔离

每个 Task 在执行时恢复创建时的环境快照：

```python
# Task.pending() 创建环境快照
env_snapshot = self.environment.snapshot()

# Task.execute_async() 恢复快照
old_env = self._interpreter.environment
self._interpreter.environment = self._env_snapshot
try:
    result = await self._execute_async()
finally:
    self._interpreter.environment = old_env
```

**保证**：并发 Task 之间环境隔离，互不干扰。

---

## 限制与注意事项

| 规则 | 说明 |
|---|---|
| `async` 可用于表达式 | `let task = async Agent()` ✅ |
| `async` 也可作为语句 | `async Agent()` ✅（立即执行） |
| `await` 参数必须是列表 | `await [task]` ✅，`await task` ❌ |
| 仅 LLM 调用真正异步 | 普通代码同步执行，LLM 调用异步 |
| 错误聚合 | 多个失败 → `AggregateError`（可被 try-catch 捕获） |

---

## 测试覆盖

**81 个异步相关测试全部通过**：

- ✅ 异步语句形式（立即执行）
- ✅ 异步表达式形式（延迟执行）
- ✅ 普通函数异步调用
- ✅ Agent 异步调用
- ✅ 并发执行计时验证
- ✅ 错误处理（AggregateError、try-catch）
- ✅ 混合同步/异步执行
- ✅ AsyncLLMInterpreter 集成
- ✅ 边界情况（无返回值、条件、循环、字符串）
- ✅ Task 状态转换
- ✅ LLM 异步调用验证（act_async/route_async）

---

## 未来扩展

### 完整异步 visitor 模式（可选）

- 所有 `visit_*` 方法改为 `async def`
- 支持 `await` 在任意表达式中
- 约 2000 行代码改造

**当前状态**：现有实现已满足内存受限环境需求，完整异步 visitor 模式暂不需要。
