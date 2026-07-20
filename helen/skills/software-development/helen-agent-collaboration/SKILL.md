---
name: helen-agent-collaboration
description: "Helen Agent 协作模式 — 多 Agent 协作、编排、分工、数据流、共享状态、作用域隔离"
version: 1.18.0
author: Helen Team
license: MIT
tags: [helen, agent, collaboration, orchestration, workflow, multi-agent, shared-let, scope-isolation, v1.12, read-only-params, ground-truth-injection, v1.17, spawn, channel, v1.18]
---

# Helen Agent 协作模式

本技能描述 Helen 语言中多 Agent 协作的模式和最佳实践（v1.18 更新：spawn + Channel 替代 async/await）。

## 核心概念

### 🎯 设计原则：调用者决定上下文（Caller Decides Context）

> **"调用 agent 前先问：它需要知道什么？"**
>
> Agent 是严格隔离的——调用前必须显式考虑要向 agent 提供什么上下文。

这是 Helen 多 agent 协作的**第一原则**。无论是同步调用 `call Agent(...)`、还是 `spawn Agent(...)`，每次调用都会创建一个全新的、独立的执行环境。**Agent 不会自动继承调用者的任何变量、历史、或 LLM 上下文**。

#### 为什么这样设计？

1. **可预测性**：agent 看到什么完全由参数决定，不会被外层状态污染
2. **可复用性**：同一个 agent 在不同调用点可以用不同上下文工作
3. **可测试性**：测试 agent 不需要构造完整的外层环境
4. **安全性**：敏感数据不会被意外泄漏给不需要的 agent
5. **并发友好**：spawn 出去的 agent 不会默默读写主 transcript

#### 调用 agent 前的思考清单

```
┌─ 调用者 ──────────────────────────────────────────┐
│  let user_data = {...}                            │
│  let config = {...}                               │
│  let history = [...]                              │
│                                                   │
│  ❓ 调用 MyAgent 前，先问：                       │
│  • 它需要 user_data 吗？→ 通过参数传入             │
│  • 它需要 config 吗？→ 用 const 或参数             │
│  • 它需要 history 吗？→ 通过参数或 resume_session │
│  • 它要修改共享状态吗？→ 用 shared store           │
│  • 它要返回结果吗？→ 用返回值或 Channel            │
└───────────────────────────────────────────────────┘
```

#### ❌ 错误模式：隐式假设

```helen
let user_name = "Alice"

agent Greeter {
    main {
        // ❌ 错误：假设 user_name 自动可见
        // 编译会报 "undefined variable: user_name"
        print("Hello " + user_name)
    }
}
```

#### ✅ 正确模式：显式传递

```helen
agent Greeter(user_name: str) {
    main {
        // ✅ 通过参数进入 agent
        print("Hello " + user_name)
    }
}

main {
    let user_name = "Alice"
    Greeter(user_name)  // 显式传递
}
```

#### 上下文传递方式速查

| 场景 | 推荐方式 |
|------|---------|
| 一次性输入 | 参数传递 `Agent(x, y)` |
| 只读配置 | `const` 模块常量（自动可见） |
| 跨 agent 共享可变状态 | `shared store` / `shared let`（仅值类型） |
| spawn 子 agent 的输出 | Channel 消息 `ch.send(result)` |
| 跨进程恢复对话 | `resume_session(sid)` |
| LLM 看到的上下文 | agent 的 `prompt` 模板（`{{var}}` 占位符） |

> 💡 完整的"上下文接力模式"详见 `helen-programming-methodology` §5

### Agent 是一等公民

在 Helen 中，Agent 是语言级别的一等构造，可以像函数一样被调用：

```helen
agent MyAgent(input: str) {
    description "我的 Agent"
    prompt """
    处理输入: {{input}}
    """
    
    functions {
        fn process(data: str): str {
            return "processed: " + data
        }
    }
    
    main {
        llm act
    }
}

// 调用 Agent（像调用函数一样）
let result = MyAgent("hello")
print(result)
```

### Agent 作用域隔离（v1.10/v1.12）

**重要**：Agent main 在完全隔离的环境中运行。

| 变量类型 | 在 agent main 中 | 使用场景 |
|---------|-----------------|---------|
| 模块级 `let` | ❌ 不可见 | 仅在 functions 块中使用 |
| 模块级 `const` | ✅ 只读 | 全局常量配置 |
| `shared let`（值类型） | ✅ 可读写 | 跨 Agent 共享简单状态 |
| 局部变量 | ✅ 可见 | 闭包可捕获 |

**v1.12 重要变更**：
- `shared let` **只允许值类型**（int, float, str, bool）
- 引用类型（list, dict）通过**参数传递**，自动只读包装
- 需要共享可变引用类型时，使用返回值或显式副本

### 协作中的状态管理

**v1.12 推荐模式**：使用值类型计数器 + 引用类型通过参数传递

```helen
// ✅ v1.12: shared let 只用于值类型
shared let task_count = 0
shared let completed_count = 0
const MAX_CONCURRENT = 5

// 引用类型通过参数传递
agent TaskProducer(tasks: list, queue: list) {
    description "Produce tasks to queue"
    
    main {
        // 创建副本后修改（参数是只读的）
        let my_queue = list(queue)
        for task in tasks {
            my_queue.append(task)
            task_count = task_count + 1
        }
        print("Queued " + str(task_count) + " tasks")
        return my_queue
    }
}

agent TaskWorker(worker_id: str, queue: list, completed: map) {
    description "Process tasks from queue"
    
    main {
        let my_queue = list(queue)
        let my_completed = dict(completed)
        
        while len(my_queue) > 0 {
            let task = my_queue.pop(0)
            print("Worker " + worker_id + " processing: " + task)
            
            // 模拟处理
            let result = llm act "Process: " + task
            
            // 记录完成
            my_completed[task] = "done by " + worker_id
            completed_count = completed_count + 1
        }
        
        return { "queue": my_queue, "completed": my_completed }
    }
}

// 协作流程（v1.18: spawn + Channel）
let initial_queue = []
let queue = TaskProducer(["task1", "task2", "task3"], initial_queue)
let w1 = spawn TaskWorker("W1", queue, {})
let w2 = spawn TaskWorker("W2", queue, {})
let r1 = w1.receive()
let r2 = w2.receive()
print("Completed: " + str(completed_count))
```
```

## 协作模式

### 模式 1：顺序链（Sequential Chain）

多个 Agent 按顺序执行，前一个的输出作为后一个的输入。

```helen
agent WorkflowOrchestrator(requirement: str) {
    description "工作流编排器 - 顺序链模式"
    prompt """
    需求: {{requirement}}
    
    工作流程：
    1. 调用 ContractDesigner 设计接口
    2. 调用 TestBuilder 生成测试
    3. 调用 Implementer 编写实现
    4. 调用 QualityChecker 评估质量
    """
    
    functions {
        fn run_workflow(req: str): map {
            // Step 1: 契约设计
            let contract = ContractDesigner(req)
            print("✅ Step 1: 契约设计完成")
            
            // Step 2: 测试生成
            let tests = TestBuilder(contract)
            write_file("tests/generated.helen", tests)
            print("✅ Step 2: 测试生成完成")
            
            // Step 3: 实现编写
            let impl = Implementer(contract, tests)
            write_file("src/implementation.helen", impl)
            print("✅ Step 3: 实现编写完成")
            
            // Step 4: 质量评估
            let quality = QualityChecker("src/implementation.helen")
            print("✅ Step 4: 质量评估完成")
            
            return {
                "contract": contract,
                "tests": tests,
                "implementation": impl,
                "quality": quality
            }
        }
    }
    
    main {
        let result = run_workflow(requirement)
        print("工作流完成")
    }
}
```

**适用场景**：
- 任务有明确的阶段划分
- 后一阶段依赖前一阶段的输出
- 需要严格的执行顺序

### 模式 2：并行扇出（Parallel Fan-out）

同时调用多个 Agent 处理不同的子任务，然后汇总结果。

```helen
// v1.12: 结果通过返回值传递，不用 shared let
shared let completed_count = 0

agent CodeAnalyzer(path: str) {
    description "分析代码文件"
    main {
        completed_count = completed_count + 1
        return { "path": path, "status": "ok", "issues": 0 }
    }
}

agent ResultSummarizer(results: list) {
    description "汇总结果"
    main {
        return { "total": len(results), "status": "done" }
    }
}

agent ParallelOrchestrator(file_paths: list) {
    description "并行编排器 - 扇出模式"
    prompt """
    文件列表: {{file_paths}}
    
    并行分析每个文件，然后汇总结果。
    """
    
    functions {
        fn analyze_files_parallel(paths: list): map {
            // 启动并行分析（v1.18: spawn）
            let mailboxes = []
            for path in paths {
                let mailbox = spawn CodeAnalyzer(path)
                mailboxes.append(mailbox)
            }
            
            // 逐个接收结果
            let results = []
            for mailbox in mailboxes {
                results.append(mailbox.receive())
            }
            
            // 汇总结果
            let summary = ResultSummarizer(results)
            return {
                "individual": results,
                "summary": summary
            }
        }
    }
    
    main {
        let result = analyze_files_parallel(file_paths)
        print("分析完成，共 " + str(len(result["individual"])) + " 个文件")
        print("完成计数: " + str(completed_count))
    }
}
```

**适用场景**：
- 多个独立子任务可以并行
- 需要汇总多个结果
- 提高吞吐量

### 模式 3：管道（Pipeline）

多个 Agent 组成处理管道，每个阶段处理特定方面。

```helen
// v1.12: 使用值类型计数器跟踪进度
shared let pipeline_stage = 0

agent DataCollector(source: str) {
    description "阶段 1: 数据收集"
    tools = ["web_search", "web_fetch"]
    
    main {
        let raw_data = llm act "Collect data from: " + source
        pipeline_stage = 1
        print("✅ 数据收集完成")
        return raw_data  // 通过返回值传递
    }
}

agent DataCleaner(data: str) {
    description "阶段 2: 数据清洗"
    
    main {
        let cleaned = llm act "Clean this data: " + data
        pipeline_stage = 2
        print("✅ 数据清洗完成")
        return cleaned
    }
}

agent DataAnalyzer(data: str) {
    description "阶段 3: 数据分析"
    
    main {
        let analysis = llm act "Analyze: " + data
        pipeline_stage = 3
        print("✅ 数据分析完成")
        return analysis
    }
}

agent DataReporter(analysis: str) {
    description "阶段 4: 生成报告"
    
    main {
        let report = llm act "Generate report from: " + analysis
        pipeline_stage = 4
        print("✅ 报告生成完成")
        return report
    }
}

// 管道执行
agent DataPipeline(source: str) {
    description "完整数据处理管道"
    
    main {
        let raw = DataCollector(source)
        let cleaned = DataCleaner(raw)
        let analysis = DataAnalyzer(cleaned)
        let report = DataReporter(analysis)
        
        print("管道执行完成")
        return report
    }
}
```

### 模式 4：路由分发（Router）

根据输入内容路由到不同的专业 Agent。

```helen
agent TechSupport(query: str) {
    description "技术支持"
    prompt "你是技术支持专家。"
    main {
        return llm act "解答技术问题: " + query
    }
}

agent BillingSupport(query: str) {
    description "账单支持"
    prompt "你是账单支持专家。"
    main {
        return llm act "解答账单问题: " + query
    }
}

agent SalesSupport(query: str) {
    description "销售支持"
    prompt "你是销售顾问。"
    main {
        return llm act "解答销售问题: " + query
    }
}

// 路由 Agent
agent SupportRouter(query: str) {
    description "智能路由客服查询"
    
    functions {
        fn classify(query: str): str {
            // 使用 LLM 进行分类
            let category = llm act "分类查询到: tech, billing, sales. 查询: " + query
            return category
        }
    }
    
    main {
        let category = classify(query)
        
        if category == "tech" {
            return TechSupport(query)
        } else if category == "billing" {
            return BillingSupport(query)
        } else if category == "sales" {
            return SalesSupport(query)
        } else {
            return llm act "通用回复: " + query
        }
    }
}
```

### 模式 5：层级协作（Hierarchical）

主 Agent 协调多个子 Agent，子 Agent 可以继续分解任务。

```helen
// v1.12: 使用值类型跟踪状态
shared let project_phase = "init"
shared let project_progress = 0

agent ProjectManager(requirement: str) {
    description "项目经理 - 总体协调"
    
    main {
        project_phase = "planning"
        
        // 阶段 1: 需求分析
        let analysis = RequirementAnalyst(requirement)
        project_progress = 25
        
        // 阶段 2: 架构设计
        let architecture = Architect(analysis)
        project_progress = 50
        
        // 阶段 3: 并行开发（v1.18: spawn + Channel）
        let frontend_mb = spawn FrontendDev(architecture)
        let backend_mb = spawn BackendDev(architecture)
        let dev_results = [frontend_mb.receive(), backend_mb.receive()]
        project_progress = 80
        
        // 阶段 4: 集成测试
        let integration = IntegrationTester(dev_results)
        project_progress = 100
        project_phase = "complete"
        
        return integration
    }
}

agent RequirementAnalyst(req: str) {
    description "需求分析师"
    main {
        return llm act "分析需求: " + req
    }
}

agent Architect(analysis: str) {
    description "架构师"
    main {
        return llm act "设计架构: " + analysis
    }
}

agent FrontendDev(arch: str) {
    description "前端开发"
    tools = ["write_file"]
    main {
        return llm act "实现前端: " + arch
    }
}

agent BackendDev(arch: str) {
    description "后端开发"
    tools = ["write_file"]
    main {
        return llm act "实现后端: " + arch
    }
}

agent IntegrationTester(results: list) {
    description "集成测试"
    main {
        return llm act "执行集成测试"
    }
}
```

### 模式 6：竞争与选择（Compete & Select）

多个 Agent 竞争解决同一问题，选择最佳结果。

```helen
shared let best_solution = null
shared let best_score = 0

agent SolutionGenerator(problem: str, strategy: str) {
    description "生成解决方案"
    
    main {
        let solution = llm act "用 " + strategy + " 策略解决: " + problem
        
        // 自我评估
        let score = llm act "评估方案质量(0-100): " + solution
        
        // 更新最佳方案（需要并发安全）
        if score > best_score {
            best_score = score
            best_solution = {
                "strategy": strategy,
                "solution": solution,
                "score": score
            }
        }
        
        return solution
    }
}

agent SolutionSelector(problem: str) {
    description "竞争选择最佳方案"
    
    main {
        // 多种策略并行竞争（v1.18: spawn）
        let strategies = ["分治法", "动态规划", "贪心算法", "回溯法"]
        let mailboxes = []
        
        for strategy in strategies {
            let mailbox = spawn SolutionGenerator(problem, strategy)
            mailboxes.append(mailbox)
        }
        
        // 接收所有结果
        for mailbox in mailboxes {
            mailbox.receive()
        }
        
        // 返回最佳方案
        return best_solution
    }
}
```

## 共享状态最佳实践

### 1. 使用 shared let 进行跨 Agent 通信（v1.12）

**v1.12 更新**: `shared let` 只允许值类型。引用类型通过参数传递。

```helen
// ✅ v1.12 正确：shared let 只用于值类型
shared let message_count = 0
shared let last_message = ""

agent Producer(msg: str) {
    main {
        message_count = message_count + 1
        last_message = msg
        // 引用类型通过返回值传递
        return [msg]
    }
}

agent Consumer(messages: list) {
    main {
        for msg in messages {
            print("消费: " + msg)
        }
        print("总计: " + str(message_count) + " 条消息")
    }
}

// 使用
let msgs = Producer("hello")
Consumer(msgs)
```

### 2. 使用 const 进行只读配置共享

```helen
// ✅ 正确：常量配置
const API_URL = "https://api.example.com"
const MAX_RETRIES = 3
const TIMEOUT = 30

agent ApiClient(endpoint: str) {
    main {
        // const 在 agent main 中自动可见
        let url = API_URL + "/" + endpoint
        return llm act "调用 API: " + url
    }
}
```

### 3. 避免模块级 let

```helen
// ❌ 错误：模块级 let 在 agent main 中不可见
let counter = 0

agent BadCounter {
    main {
        // 编译错误！
        counter = counter + 1
    }
}

// ✅ 正确：使用 shared let
shared let good_counter = 0

agent GoodCounter {
    main {
        good_counter = good_counter + 1
    }
}
```

### 4. 使用 Shared Store 共享引用类型（v1.12）

`shared let` 限制为值类型。需要共享 list/dict 时，使用 `shared store`：

```helen
shared store TaskRegistry {
    tasks: dict = {}
    _counter: int = 0

    fn register(task_name: str, task_data: any) {
        _counter += 1
        tasks[task_name] = task_data
    }

    fn get(task_name: str): any { return tasks[task_name] }
    fn size(): int { return len(tasks) }
    fn all(): dict { return tasks }
}

agent Producer(registry: TaskRegistry) {
    main {
        registry.register("task_1", {status: "pending", priority: 1})
        registry.register("task_2", {status: "pending", priority: 2})
    }
}

agent Consumer(registry: TaskRegistry) {
    main {
        for i in range(registry.size()) {
            // 通过方法安全访问共享 dict
            let task = registry.get("task_" + str(i + 1))
            // 处理任务
        }
    }
}

main {
    let registry = TaskRegistry
    spawn Producer(registry)
    spawn Consumer(registry)
}
```

**Shared Store 优势**:
- 线程安全（RLock 保护所有字段访问）
- `_` 前缀字段为私有，agent 不可直接访问
- 方法封装逻辑，避免散落的锁操作

### 5. 使用 Channel 消息队列进行 Agent 间通信（v1.18）

v1.18 引入 `spawn` + Channel 消息队列，替代旧的 async/await 并发模型：

```helen
// spawn 返回 Channel（邮箱）
agent Sender(output: Channel) {
    main {
        output.send("Hello from sender")
        output.send("Another message")
        return "done"
    }
}

agent Receiver(input: Channel) {
    main {
        let msg1 = input.receive()
        let msg2 = input.receive()
        print("Received: " + msg1 + ", " + msg2)
        return msg1 + msg2
    }
}

main {
    // 创建 channel 连接 sender 和 receiver
    // 通过 spawn 启动并发 agent
    let mb1 = spawn Sender(null)
    let result = mb1.receive()
}
```

**v1.18 Channel 消息队列 vs Shared Store**:

| 场景 | 推荐 |
|------|------|
| 多个 Agent 读写同一个状态 | Shared Store |
| Agent 间传递消息/任务结果 | spawn + Channel |
| 多路复用选择 | mailbox_select([m1, m2, ...]) |
| 需要线程安全的字段访问 | Shared Store |

### 6. 向下游 Agent 传播环境事实（v1.17）

编排者（orchestrator）最常见的失误：**自己掌握环境事实，却不在 prompt 中传给下游 Agent**。LLM 看不见运行时环境，缺什么就会编什么。

```helen
// ✅ Orchestrator resolves ground truth once, fans out via {{}}
agent Orchestrator(task: str) {
    main {
        let cwd = shell_exec("pwd")
        let git_branch = shell_exec("git branch --show-current")
        let now = now()
        return Worker(task, cwd, git_branch, now)
    }
}

agent Worker(task: str, cwd: str, branch: str, now: str) {
    prompt """
    Task: {{task}}
    Working directory: {{cwd}}
    Git branch: {{branch}}
    Current time: {{now}}
    """
    main { return llm act }
}
```

原则：**谁拥有事实，谁负责注入**。共享的 `shared store` 适合状态，但时间/OS/路径等不可变事实直接走 `{{}}` 进 prompt，开销最低、最不容易出错。详见 **helen-agent-patterns § 最佳实践 7**。

## 错误处理

### 并发任务错误处理

```helen
agent RobustOrchestrator(tasks: list) {
    description "带错误处理的编排器"
    
    main {
        let mailboxes = []
        for task in tasks {
            mailboxes.append(spawn TaskWorker(task))
        }
        
        try {
            let results = []
            for mailbox in mailboxes {
                results.append(mailbox.receive())
            }
            return results
        } catch AggregateError as e {
            print("部分任务失败: " + str(len(e.errors)))
            
            // 处理失败的任务
            let successes = []
            for i in range(len(tasks)) {
                if i < len(results) {
                    successes.append(results[i])
                }
            }
            return successes
        }
    }
}
```

## 性能优化

### 1. 合理控制并发数

```helen
const MAX_CONCURRENT = 5

agent BatchProcessor(items: list) {
    main {
        let results = []
        
        // 分批处理（v1.18: spawn）
        for i in range(0, len(items), MAX_CONCURRENT) {
            let batch = items[i:i + MAX_CONCURRENT]
            let mailboxes = []
            
            for item in batch {
                mailboxes.append(spawn Worker(item))
            }
            
            for mailbox in mailboxes {
                results.append(mailbox.receive())
            }
        }
        
        return results
    }
}
```

### 2. 使用缓存减少重复计算（v1.12）

**v1.12 模式**: 缓存通过参数传递，使用返回值返回更新后的缓存。

```helen
// v1.12: 用值类型跟踪缓存统计
shared let cache_hits = 0
shared let cache_misses = 0

agent CachedWorker(task_id: str, cache: map) {
    main {
        // 检查缓存（cache 是只读视图）
        if task_id in cache {
            cache_hits = cache_hits + 1
            return { "result": cache[task_id], "cache": cache }
        }
        
        cache_misses = cache_misses + 1
        
        // 执行计算
        let result = llm act "处理任务: " + task_id
        
        // 创建更新后的缓存副本
        let updated_cache = dict(cache)
        updated_cache[task_id] = result
        
        return { "result": result, "cache": updated_cache }
    }
}

// 使用
let my_cache = {}
let r1 = CachedWorker("task1", my_cache)
let r2 = CachedWorker("task2", r1["cache"])
let r3 = CachedWorker("task1", r2["cache"])  // 命中缓存
print("缓存命中: " + str(cache_hits))
print("缓存未命中: " + str(cache_misses))
```

## 相关技能

- **helen-agent-patterns** — Agent 设计模式详解
- **helen-syntax** — Helen 语法（shared let、const、agent main 等）
- **subagent-driven-development** — 子代理驱动开发工作流

## 📦 内置模板库

Helen 提供一组内置模板，涵盖本文档中讨论的所有协作模式：

```bash
# 查看所有模板
helen template --list

# 查看协作相关模板
helen template shared_store          # SharedStore 数据交换
helen template spawn_channel         # spawn + Channel 并发
helen template pipeline              # Agent 管道

# 复制模板到当前目录开始开发
helen template shared_store --copy my_collaboration.helen
```

每个模板都是完整可运行的示例，遵循 **"调用者决定上下文"** 原则。

## 延伸阅读

- **[[Agent 提示词工程完全指南]]**（`wiki/reference/agent-system-prompt-guide.md`）— 来自 Claude Code 逆向工程的 agent prompt 设计方法论。编排者 agent 的 prompt 尤其需要遵循该指南的"原则优先于流程"和"注入环境事实"两条。
