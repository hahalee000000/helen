---
name: helen-agent-collaboration
description: "Helen Agent 协作模式 — 多 Agent 协作、编排、分工、数据流、共享状态、作用域隔离"
version: 1.1.0
author: Helen Team
license: MIT
tags: [helen, agent, collaboration, orchestration, workflow, multi-agent, shared-let, scope-isolation, v1.10]
---

# Helen Agent 协作模式

本技能描述 Helen 语言中多 Agent 协作的模式和最佳实践（v1.10 更新）。

## 核心概念

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
        llm stream
    }
}

// 调用 Agent（像调用函数一样）
let result = MyAgent("hello")
print(result)
```

### Agent 作用域隔离（v1.10）

**重要**：Agent main 在完全隔离的环境中运行。

| 变量类型 | 在 agent main 中 | 使用场景 |
|---------|-----------------|---------|
| 模块级 `let` | ❌ 不可见 | 仅在 functions 块中使用 |
| 模块级 `const` | ✅ 只读 | 全局常量配置 |
| `shared let` | ✅ 可读写 | 跨 Agent 共享状态 |
| 局部变量 | ✅ 可见 | 闭包可捕获 |

### 协作中的状态管理

```helen
// ✅ 正确：使用 shared let 进行跨 Agent 共享
shared let task_queue = []
shared let completed_tasks = {}
const MAX_CONCURRENT = 5

agent TaskProducer(tasks: list) {
    description "Produce tasks to queue"
    
    main {
        for task in tasks {
            task_queue.append(task)
        }
        print("Queued " + str(len(tasks)) + " tasks")
    }
}

agent TaskWorker(worker_id: str) {
    description "Process tasks from queue"
    
    main {
        while len(task_queue) > 0 {
            let task = task_queue.pop(0)
            print("Worker " + worker_id + " processing: " + task)
            
            // 模拟处理
            let result = llm act "Process: " + task
            
            // 记录完成
            completed_tasks[task] = {
                "worker": worker_id,
                "result": result,
                "status": "done"
            }
        }
    }
}

// 协作流程
TaskProducer(["task1", "task2", "task3"])
let w1 = async TaskWorker("W1")
let w2 = async TaskWorker("W2")
await [w1, w2]
print("Completed: " + str(len(completed_tasks)))
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
// 共享状态用于结果收集
shared let analysis_results = {}

agent ParallelOrchestrator(file_paths: list) {
    description "并行编排器 - 扇出模式"
    prompt """
    文件列表: {{file_paths}}
    
    并行分析每个文件，然后汇总结果。
    """
    
    functions {
        fn analyze_files_parallel(paths: list): map {
            // 启动并行分析
            let tasks = []
            for path in paths {
                let task = async CodeAnalyzer(path)
                tasks.append(task)
            }
            
            // 等待所有完成
            let results = await tasks
            
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
shared let pipeline_data = {}

agent DataCollector(source: str) {
    description "阶段 1: 数据收集"
    tools ["web_search", "web_fetch"]
    
    main {
        let raw_data = llm act "Collect data from: " + source
        pipeline_data["raw"] = raw_data
        print("✅ 数据收集完成")
        return raw_data
    }
}

agent DataCleaner(data: str) {
    description "阶段 2: 数据清洗"
    
    main {
        let cleaned = llm act "Clean this data: " + data
        pipeline_data["cleaned"] = cleaned
        print("✅ 数据清洗完成")
        return cleaned
    }
}

agent DataAnalyzer(data: str) {
    description "阶段 3: 数据分析"
    
    main {
        let analysis = llm act "Analyze: " + data
        pipeline_data["analysis"] = analysis
        print("✅ 数据分析完成")
        return analysis
    }
}

agent DataReporter(analysis: str) {
    description "阶段 4: 生成报告"
    
    main {
        let report = llm act "Generate report from: " + analysis
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
shared let project_status = {
    "phase": "init",
    "progress": 0
}

agent ProjectManager(requirement: str) {
    description "项目经理 - 总体协调"
    
    main {
        project_status["phase"] = "planning"
        
        // 阶段 1: 需求分析
        let analysis = RequirementAnalyst(requirement)
        project_status["progress"] = 25
        
        // 阶段 2: 架构设计
        let architecture = Architect(analysis)
        project_status["progress"] = 50
        
        // 阶段 3: 并行开发
        let frontend_task = async FrontendDev(architecture)
        let backend_task = async BackendDev(architecture)
        let dev_results = await [frontend_task, backend_task]
        project_status["progress"] = 80
        
        // 阶段 4: 集成测试
        let integration = IntegrationTester(dev_results)
        project_status["progress"] = 100
        project_status["phase"] = "complete"
        
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
    tools ["write_file"]
    main {
        return llm act "实现前端: " + arch
    }
}

agent BackendDev(arch: str) {
    description "后端开发"
    tools ["write_file"]
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
        // 多种策略并行竞争
        let strategies = ["分治法", "动态规划", "贪心算法", "回溯法"]
        let tasks = []
        
        for strategy in strategies {
            let task = async SolutionGenerator(problem, strategy)
            tasks.append(task)
        }
        
        await tasks
        
        // 返回最佳方案
        return best_solution
    }
}
```

## 共享状态最佳实践

### 1. 使用 shared let 进行跨 Agent 通信

```helen
// ✅ 正确：使用 shared let
shared let message_queue = []

agent Producer(msg: str) {
    main {
        message_queue.append(msg)
    }
}

agent Consumer {
    main {
        while len(message_queue) > 0 {
            let msg = message_queue.pop(0)
            print("消费: " + msg)
        }
    }
}
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

## 错误处理

### 并发任务错误处理

```helen
agent RobustOrchestrator(tasks: list) {
    description "带错误处理的编排器"
    
    main {
        let promises = []
        for task in tasks {
            promises.append(async TaskWorker(task))
        }
        
        try {
            let results = await promises
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
        
        // 分批处理
        for i in range(0, len(items), MAX_CONCURRENT) {
            let batch = items[i:i + MAX_CONCURRENT]
            let tasks = []
            
            for item in batch {
                tasks.append(async Worker(item))
            }
            
            let batch_results = await tasks
            results.extend(batch_results)
        }
        
        return results
    }
}
```

### 2. 使用缓存减少重复计算

```helen
shared let cache = {}

agent CachedWorker(task_id: str) {
    main {
        // 检查缓存
        if task_id in cache {
            return cache[task_id]
        }
        
        // 执行计算
        let result = llm act "处理任务: " + task_id
        
        // 存入缓存
        cache[task_id] = result
        
        return result
    }
}
```

## 相关技能

- **helen-agent-patterns** — Agent 设计模式详解
- **helen-syntax** — Helen 语法（shared let、const、agent main 等）
- **subagent-driven-development** — 子代理驱动开发工作流
