---
name: helen-agent-collaboration
description: "Helen Agent 协作模式 — 多 Agent 协作、编排、分工、数据流"
version: 1.0.0
author: Helen Team
license: MIT
metadata:
  hermes:
    tags: [helen, agent, collaboration, orchestration, workflow, multi-agent]
---

# Helen Agent 协作模式

本技能描述 Helen 语言中多 Agent 协作的模式和最佳实践。

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

### Agent 调用语法

```helen
// 在 functions 块中调用 Agent
fn call_my_agent(param: str): str {
    return MyAgent(param)
}

// 不能在 prompt 中直接调用 Agent
// ❌ 错误：prompt 中写 "MyAgent()" 会报错
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
agent ParallelOrchestrator(file_paths: list) {
    description "并行编排器 - 扇出模式"
    prompt """
    文件列表: {{file_paths}}
    
    并行分析每个文件，然后汇总结果。
    """
    
    functions {
        fn analyze_files(paths: list): map {
            let results = []
            
            // 并行调用 CodeAnalyzer（概念上并行，实际顺序执行）
            for path in paths {
                let analysis = CodeAnalyzer(path)
                results.append({
                    "file": path,
                    "analysis": analysis
                })
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
        let result = analyze_files(file_paths)
        print("并行分析完成")
    }
}
```

**适用场景**：
- 多个独立的子任务
- 子任务之间无依赖关系
- 需要汇总所有子任务的结果

### 模式 3：条件分支（Conditional Branching）

根据条件选择不同的 Agent 执行。

```helen
agent Router(input: str) {
    description "路由器 - 条件分支模式"
    prompt """
    输入: {{input}}
    
    根据输入类型选择合适的处理器：
    - 如果是代码问题 → Debugger
    - 如果是质量问题 → QualityImprover
    - 如果是文档问题 → DocWriter
    - 其他 → GeneralAssistant
    """
    
    functions {
        fn route(user_input: str): str {
            // 分析输入类型
            let analysis = analyze_input_type(user_input)
            
            if analysis == "code_issue" {
                return Debugger(user_input)
            } else if analysis == "quality_issue" {
                return QualityImprover(user_input)
            } else if analysis == "doc_issue" {
                return DocWriter(user_input)
            } else {
                return GeneralAssistant(user_input)
            }
        }
        
        fn analyze_input_type(input: str): str {
            if contains(input, "bug") || contains(input, "error") {
                return "code_issue"
            } else if contains(input, "quality") || contains(input, "improve") {
                return "quality_issue"
            } else if contains(input, "doc") || contains(input, "document") {
                return "doc_issue"
            }
            return "general"
        }
    }
    
    main {
        let result = route(input)
        print(result)
    }
}
```

**适用场景**：
- 输入类型不确定
- 需要根据内容动态选择处理策略
- 不同类型的任务需要不同的专业 Agent

### 模式 4：主从协作（Master-Slave）

一个主 Agent 协调多个从 Agent，分配任务并汇总结果。

```helen
agent MasterCoordinator(project_dir: str) {
    description "主协调器 - 主从模式"
    prompt """
    项目目录: {{project_dir}}
    
    作为主协调器，分配任务给从 Agent：
    1. Analyzer - 分析代码结构
    2. Tester - 生成测试
    3. Reviewer - 代码审查
    4. Optimizer - 性能优化
    
    汇总所有从 Agent 的结果，生成最终报告。
    """
    
    functions {
        fn coordinate(dir: str): map {
            // 分配任务给从 Agent
            let analysis = Analyzer(dir)
            let tests = Tester(dir, analysis)
            let review = Reviewer(dir, analysis)
            let optimization = Optimizer(dir, analysis)
            
            // 汇总结果
            let report = generate_report(analysis, tests, review, optimization)
            
            return {
                "analysis": analysis,
                "tests": tests,
                "review": review,
                "optimization": optimization,
                "report": report
            }
        }
        
        fn generate_report(a: str, t: str, r: str, o: str): str {
            return """
            # 项目分析报告
            
            ## 代码分析
            {a}
            
            ## 测试覆盖
            {t}
            
            ## 代码审查
            {r}
            
            ## 优化建议
            {o}
            """
        }
    }
    
    main {
        let result = coordinate(project_dir)
        write_file("project_report.md", result["report"])
        print("主从协作完成")
    }
}
```

**适用场景**：
- 复杂的多步骤任务
- 需要多个专业 Agent 协作
- 主 Agent 负责任务分配和结果汇总

## 数据流设计

### Agent 间数据传递

```helen
agent DataFlowDemo(input: str) {
    functions {
        fn demonstrate_flow(data: str): map {
            // Agent 1: 处理输入
            let step1 = Processor(data)
            
            // Agent 2: 验证结果
            let step2 = Validator(step1)
            
            // Agent 3: 转换格式
            let step3 = Transformer(step2)
            
            // Agent 4: 输出结果
            let step4 = OutputGenerator(step3)
            
            return {
                "step1": step1,
                "step2": step2,
                "step3": step3,
                "step4": step4,
                "final": step4
            }
        }
    }
    
    main {
        let result = demonstrate_flow(input)
        print(result)
    }
}
```

### 共享状态管理

```helen
agent SharedStateOrchestrator(initial_state: map) {
    functions {
        fn process_with_state(state: map): map {
            let current_state = state
            
            // Agent 1 修改状态
            let result1 = StateModifier1(current_state)
            current_state = merge_state(current_state, result1)
            
            // Agent 2 读取并修改状态
            let result2 = StateModifier2(current_state)
            current_state = merge_state(current_state, result2)
            
            // Agent 3 基于最终状态生成输出
            let final_result = OutputGenerator(current_state)
            
            return {
                "final_state": current_state,
                "output": final_result
            }
        }
        
        fn merge_state(base: map, update: map): map {
            // 简单的状态合并逻辑
            let merged = base
            for key in update {
                merged[key] = update[key]
            }
            return merged
        }
    }
    
    main {
        let result = process_with_state(initial_state)
        print("状态管理完成")
    }
}
```

## 错误处理

### Agent 调用失败处理

```helen
agent ErrorHandlingOrchestrator(input: str) {
    functions {
        fn safe_call_agent(data: str): map {
            // 尝试调用 Agent
            let result = WorkerAgent(data)
            
            // 检查结果
            if result == null || result == "" {
                // 调用失败，使用备用 Agent
                return BackupAgent(data)
            }
            
            return {"status": "success", "data": result}
        }
        
        fn retry_call(data: str, max_retries: int): map {
            let attempts = 0
            
            while attempts < max_retries {
                let result = WorkerAgent(data)
                if result != null && result != "" {
                    return {"status": "success", "data": result, "attempts": attempts + 1}
                }
                attempts = attempts + 1
            }
            
            return {"status": "failed", "attempts": attempts}
        }
    }
    
    main {
        let result = safe_call_agent(input)
        if result["status"] == "failed" {
            print("⚠️ Agent 调用失败，已重试 " + str(result["attempts"]) + " 次")
        }
    }
}
```

## 最佳实践

### 1. Agent 职责单一

```helen
// ✅ 好：职责单一
agent ContractDesigner(requirement: str) {
    description "专门设计接口契约"
    prompt """
    只负责设计 Protocol 接口，不编写实现。
    """
}

// ❌ 差：职责过多
agent DoEverythingAgent(requirement: str) {
    description "设计契约、编写测试、实现代码、评估质量"
    prompt """
    做所有事情...
    """
}
```

### 2. 明确的数据流

```helen
// ✅ 好：数据流清晰
fn process(data: str): map {
    let step1 = Agent1(data)
    let step2 = Agent2(step1)
    let step3 = Agent3(step2)
    return step3
}

// ❌ 差：数据流混乱
fn process(data: str): map {
    let a = Agent1(data)
    let b = Agent2(data)  // 重复输入
    let c = Agent3(a)     // 跳过 b
    return c
}
```

### 3. 错误处理

```helen
// ✅ 好：有错误处理
fn safe_process(data: str): map {
    let result = WorkerAgent(data)
    if result == null {
        return BackupAgent(data)
    }
    return result
}

// ❌ 差：无错误处理
fn unsafe_process(data: str): map {
    return WorkerAgent(data)  // 如果失败会崩溃
}
```

### 4. 避免循环依赖

```helen
// ❌ 差：循环依赖
agent AgentA(input: str) {
    functions {
        fn process(data: str): str {
            return AgentB(data)  // A 调用 B
        }
    }
}

agent AgentB(input: str) {
    functions {
        fn process(data: str): str {
            return AgentA(data)  // B 调用 A → 无限循环
        }
    }
}

// ✅ 好：单向依赖
agent AgentA(input: str) {
    functions {
        fn process(data: str): str {
            return AgentB(data)  // A 调用 B
        }
    }
}

agent AgentB(input: str) {
    functions {
        fn process(data: str): str {
            return AgentC(data)  // B 调用 C（不回调用 A）
        }
    }
}
```

## 常见陷阱

### 1. 使用 `call` 关键字调用 Agent

```helen
// ❌ 错误：使用 call 关键字
let result = call MyAgent("hello")  // 解析错误：Expected expression, got CALL

// ✅ 正确：函数式调用
let result = MyAgent("hello")
```

**原因**：
- Helen 中 Agent 是一等公民，应该像函数一样调用
- `call` 关键字在表达式位置（赋值、参数、返回值）会导致解析错误
- `call` 仅用于语句位置（不接收返回值时），但函数式调用更简洁

**正确用法**：
```helen
// 表达式位置 - 必须使用函数式调用
let result = MyAgent("hello")
return MyAgent("hello")
let x = some_fn(MyAgent("hello"))

// 语句位置 - 两种方式都可以
call MyAgent("hello")  // 可以，但不推荐
MyAgent("hello")       // 推荐，更简洁
```

### 2. 在 prompt 中直接调用 Agent

```helen
// ❌ 错误
agent MyAgent(input: str) {
    prompt """
    调用 OtherAgent() 处理输入  // 这会导致语法错误
    """
}

// ✅ 正确
agent MyAgent(input: str) {
    functions {
        fn call_other(data: str): str {
            return OtherAgent(data)  // 在 functions 块中调用
        }
    }
    
    prompt """
    使用 call_other() 函数处理输入
    """
}
```

### 2. Agent 参数不匹配

```helen
// ❌ 错误：参数不匹配
agent MyAgent(input: str, config: map) {
    // ...
}

let result = MyAgent("hello")  // 缺少 config 参数

// ✅ 正确
let result = MyAgent("hello", {"mode": "strict"})
```

### 3. 忽略 Agent 返回值

```helen
// ❌ 错误：忽略返回值
WorkerAgent(data)  // 结果丢失

// ✅ 正确：处理返回值
let result = WorkerAgent(data)
if result != null {
    print(result)
}
```

## 参考资源

- [Helen Agent 设计模式](./helen-agent-patterns/SKILL.md)
- [Helen 编程方法论](./helen-programming-methodology/SKILL.md)
- [Helen 语法参考](./helen-syntax/SKILL.md)
