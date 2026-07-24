---
name: helen-agent-collaboration
description: "Helen Agent 协作模式 — 多 Agent 协作、编排、分工、数据流、共享状态、作用域隔离"
version: 1.19.0
author: Helen Team
license: MIT
tags: [helen, agent, collaboration, orchestration, workflow, multi-agent, shared-let, scope-isolation, v1.12, read-only-params, ground-truth-injection, v1.17, spawn, channel, v1.18]
---

# Helen Agent 协作模式

本技能描述 Helen 语言中多 Agent 协作的模式和最佳实践（v1.18 更新：spawn + Channel 替代 async/await）。

## 核心概念

> 💡 **单 Agent 设计模式、作用域隔离、上下文管理详见 `helen-agent-patterns`**

### 🎯 调用者决定上下文（Caller Decides Context）

Agent 严格隔离——每次调用/spawn 创建全新执行环境，**不自动继承**调用者的变量、历史或 LLM 上下文。调用前必须显式考虑提供什么上下文：

```
调用者 ──参数──► Agent 输入
      ──SharedStore──► 共享状态
      ◄──返回值/Channel── Agent 输出
```

```helen
// ❌ 错误：假设模块变量自动可见
let user_name = "Alice"
agent Greeter { main { print("Hello " + user_name) } }  // 编译错误！

// ✅ 正确：显式传递
agent Greeter(user_name: str) { main { print("Hello " + user_name) } }
main { Greeter("Alice") }
```

| 场景 | 推荐方式 |
|------|---------|
| 一次性输入 | 参数 `Agent(x, y)` |
| 只读配置 | `const`（自动可见） |
| 跨 agent 共享可变状态 | `shared store` |
| spawn 子 agent 输出 | Channel `ch.send(result)` |
| 跨进程恢复对话 | `resume_session(sid)` |

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

> 💡 详细示例和反模式详见 `helen-agent-patterns` § 作用域隔离 / § 最佳实践 6

协作中共享状态的方式选择：

| 方式 | 适用场景 | 约束 |
|------|---------|------|
| `shared let` | 跨 agent 值类型计数器/标志 | v1.12: 仅 int/float/str/bool |
| `const` | 只读配置（agent 中自动可见） | 不可变 |
| 参数传递 | 引用类型（list/dict） | 自动只读包装，需修改时 `list(x)` 创建副本 |
| `shared store` | 复杂可变共享状态 | RLock 线程安全，`_` 前缀私有 |
| Channel | agent 间消息/结果传递 | spawn 返回 Channel |

**关键规则**：`shared let` 禁止引用类型；模块级 `let` 在 agent main 中不可见（编译错误）。

Shared Store 快速示例：

```helen
shared store TaskRegistry {
    tasks: dict = {}
    _counter: int = 0
    fn register(name: str, data: any) { _counter += 1; tasks[name] = data }
    fn get(name: str): any { return tasks[name] }
    fn size(): int { return len(tasks) }
}

agent Producer(r: TaskRegistry) { main { r.register("t1", {status: "pending"}) } }
agent Consumer(r: TaskRegistry) { main { let t = r.get("t1") } }
main { let r = TaskRegistry; spawn Producer(r); spawn Consumer(r) }
```

### 使用 Channel 消息队列进行 Agent 间通信（v1.18）

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

### 向下游 Agent 传播环境事实（v1.17）

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

## 错误处理与性能

**并发错误处理**：spawn + Channel 配合 try/catch AggregateError：

```helen
agent RobustOrchestrator(tasks: list) {
    main {
        let mailboxes = []
        for task in tasks { mailboxes.append(spawn TaskWorker(task)) }
        try {
            let results = []
            for mb in mailboxes { results.append(mb.receive()) }
            return results
        } catch AggregateError as e {
            print("部分任务失败: " + str(len(e.errors)))
            return []  // 处理失败情况
        }
    }
}
```

**性能要点**：
- **分批并发**：`for i in range(0, len(items), MAX_CONCURRENT)` 控制每次 spawn 数量
- **缓存**：通过参数传递 cache map，返回值返回更新后副本，`shared let` 跟踪命中统计

## 相关技能

- **helen-agent-patterns** — Agent 设计模式详解
- **helen-syntax** — Helen 语法（shared let、const、agent main 等）
- **subagent-driven-development** — 子代理驱动开发工作流

## 延伸阅读

- **[[Agent 提示词工程完全指南]]**（`wiki/reference/agent-system-prompt-guide.md`）— agent prompt 设计方法论，编排者 agent 尤其需要遵循"原则优先于流程"和"注入环境事实"。
