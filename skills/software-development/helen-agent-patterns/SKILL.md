---
name: helen-agent-patterns
description: "Helen Agent 设计模式 — 单 Agent、多 Agent 协作、作用域隔离、共享变量、路由、流式处理"
version: 1.1.0
author: Helen Team
license: MIT
tags: [helen, agent, patterns, design, llm, scope-isolation, shared-let, v1.10, closure, concurrency]
---

# Helen Agent 设计模式

Helen 将 Agent 作为**一等语言构造**，提供声明式语法和强大的 LLM 集成。

## Agent 基础

### 最小 Agent

```helen
agent SimpleAgent {
    description "A simple agent"
    prompt "You are a helpful assistant."
    
    main {
        return llm act "Hello, world!"
    }
}

# 调用
let result = SimpleAgent()
print(result)
```

### 参数化 Agent

```helen
agent Translator(text: str, target_lang: str) {
    description "Translate text to target language"
    prompt "You are a professional translator. Translate to {{target_lang}}."
    model "gpt-4"
    temperature 0.3
    
    main {
        return llm act "Translate: " + text
    }
}

# 调用
let result = Translator("Hello", "Chinese")
print(result)  # "你好"
```

### Agent 配置选项

```helen
agent ConfiguredAgent {
    description "Agent with full configuration"
    prompt "You are an expert assistant."
    model "gpt-4"              # LLM 模型
    temperature 0.7            # 创造性 (0.0-1.0)
    max-turns 10               # 最大工具调用轮次
    streaming true             # 启用流式响应（返回 StreamingResponse）
    tools = ["web_search", "read_file", "write_file"]  # 可用工具
    
    main {
        return llm act "Do something complex"
    }
}
```

## Agent vs Skill：本质区别

> **Agent 是"谁来做"，Skill 是"怎么做"的知识。**

| 维度 | Agent（智能体） | Skill（技能） |
|------|----------------|--------------|
| **本质** | 运行时实体 | 静态文档 |
| **语言级别** | 一等公民（语法支持） | 外部概念（纯 Markdown） |
| **可调用** | ✅ `Agent()` 像函数调用 | ❌ 不可调用 |
| **有状态** | ✅ 维护对话/工具状态 | ❌ 无状态 |
| **执行逻辑** | ✅ `main { }` 块 | ❌ 无执行逻辑 |
| **用途** | **执行**任务 | **指导**如何执行 |

**Agent 是执行者**：有 model、temperature、tools，可被调用、组合，实际执行 LLM 调用和工具操作。像**员工**。

**Skill 是知识库**：纯 Markdown 文档，提供模式、最佳实践、API 用法，被 Agent 读取作为上下文。像**手册**。

**用 Agent** 当你需要实际执行操作、维护状态、被代码调用。
**用 Skill** 当你需要提供知识、文档化工作流、让多个 Agent 共享知识。

**实际关系**：Agent 可以加载 Skill 作为知识源：

```helen
agent Developer {
    tools = ["load_skill"]
    main {
        let guide = load_skill("helen-testing")
        return llm act "Follow: " + guide
    }
}
```

## Agent 作用域隔离（v1.10）

### 核心规则

**Agent main 在完全隔离的环境中运行**，这是 v1.10 的重要特性：

| 变量类型 | 在 agent main 中 | 说明 |
|---------|-----------------|------|
| 模块级 `let` | ❌ **不可见** | 编译时报错 |
| 模块级 `const` | ✅ 自动可见 | 只读共享 |
| `shared let` | ✅ 可见 | 跨 agent 可写 |
| 局部变量 | ✅ 可见 | 闭包可捕获 |

### 示例：作用域隔离

```helen
// 模块级变量
let module_counter = 0           // ❌ agent main 中不可见
const MAX_RETRIES = 3            // ✅ agent main 中自动可见
shared let shared_state = {}     // ✅ agent main 中可见可写

agent Worker(task: str) {
    description "Worker agent"
    
    functions {
        fn process(): str {
            // functions 块中可以访问模块级 let
            module_counter = module_counter + 1
            return "processed: " + task
        }
    }
    
    main {
        // ❌ 编译错误：module_counter 在 agent main 中不可见
        // print(module_counter)
        
        // ✅ const 自动可见
        print("Max retries: " + MAX_RETRIES)
        
        // ✅ shared let 可见
        shared_state["task"] = task
        
        // ✅ 局部变量
        let local_data = "local"
        
        return llm act "Process: " + task
    }
}
```

### 闭包捕获局部变量

```helen
agent DataProcessor(data: list) {
    description "Process data with closure"
    
    main {
        let threshold = 10  // 局部变量
        
        // 闭包可以捕获局部变量
        fn filter_data(items: list): list {
            let result = []
            for item in items {
                if item > threshold {  // ✅ 捕获外层局部变量
                    result.append(item)
                }
            }
            return result
        }
        
        let filtered = filter_data(data)
        return llm act "Filtered data: " + str(filtered)
    }
}
```

### shared let 跨 Agent 协作

```helen
// 全局共享状态
shared let global_cache = {}
shared let request_count = 0

agent CacheReader(key: str) {
    description "Read from shared cache"
    
    main {
        request_count = request_count + 1
        
        if key in global_cache {
            return global_cache[key]
        }
        return null
    }
}

agent CacheWriter(key: str, value: any) {
    description "Write to shared cache"
    
    main {
        request_count = request_count + 1
        global_cache[key] = value
        return "cached"
    }
}

// 使用
CacheWriter("user:1", {"name": "Alice"})
let user = CacheReader("user:1")
print("Requests: " + request_count)  // 2
```

## 设计模式

### 模式 1: 专家 Agent

**场景**：为特定领域创建专家 Agent

```helen
agent CodeExpert {
    description "Programming expert"
    prompt """
    You are a senior software engineer with 20 years of experience.
    You provide clear, concise, and correct code solutions.
    Always explain your reasoning.
    """
    tools = ["read_file", "write_file", "shell_exec"]
    
    main {
        return llm act "Review this code and suggest improvements"
    }
}

agent MathExpert {
    description "Mathematics expert"
    prompt "You are a mathematics professor. Provide rigorous proofs and explanations."
    temperature 0.2  # 低温度，更确定
    
    main {
        return llm act "Solve this math problem step by step"
    }
}
```

### 模式 2: 路由 Agent（llm if）

**场景**：根据输入内容路由到不同的专家 Agent

```helen
# 定义专家
agent TechSupport(query: str) {
    description "Technical support specialist"
    prompt "You are a technical support expert."
    main {
        return llm act "Help with: " + query
    }
}

agent BillingSupport(query: str) {
    description "Billing support specialist"
    prompt "You are a billing support expert."
    main {
        return llm act "Help with: " + query
    }
}

agent GeneralSupport(query: str) {
    description "General support specialist"
    prompt "You are a general support assistant."
    main {
        return llm act "Help with: " + query
    }
}

# 路由 Agent
agent SupportRouter(query: str) {
    description "Route support queries to specialists"
    
    main {
        llm if query {
            case "technical issue, bug, error, crash, not working" {
                return TechSupport(query)
            }
            case "billing, payment, invoice, subscription, refund" {
                return BillingSupport(query)
            }
            default {
                return GeneralSupport(query)
            }
        }
    }
}

# 使用
let response = SupportRouter("I can't login to my account")
# 路由到 TechSupport
```

### 模式 3: 管道 Agent

**场景**：多个 Agent 顺序处理，每个阶段处理一个方面

```helen
agent Researcher(topic: str) {
    description "Research specialist"
    tools = ["web_search", "web_fetch"]
    
    main {
        return llm act "Research this topic and provide key findings: " + topic
    }
}

agent Writer(topic: str, research: str) {
    description "Content writer"
    prompt "You are a professional content writer."
    
    main {
        return llm act "Write an article about " + topic + 
                       " based on this research: " + research
    }
}

agent Editor(content: str) {
    description "Content editor"
    prompt "You are a meticulous editor. Fix grammar, improve clarity, ensure consistency."
    temperature 0.3
    
    main {
        return llm act "Edit and improve this content: " + content
    }
}

# 管道
agent ContentPipeline(topic: str) {
    description "Research → Write → Edit pipeline"
    
    main {
        # 阶段 1: 研究
        let research = Researcher(topic)
        
        # 阶段 2: 写作
        let draft = Writer(topic, research)
        
        # 阶段 3: 编辑
        let final = Editor(draft)
        
        return final
    }
}

# 使用
let article = ContentPipeline("Helen programming language")
```

### 模式 4: 并发 Agent（async/await）

**场景**：多个 Agent 并发执行，提高吞吐量

```helen
agent DataFetcher(source: str) {
    description "Fetch data from a source"
    tools = ["http_get"]
    
    main {
        return llm act "Fetch data from: " + source
    }
}

agent DataAggregator {
    description "Aggregate data from multiple sources"
    
    main {
        # 并发获取数据
        let task1 = async DataFetcher("https://api.source1.com/data")
        let task2 = async DataFetcher("https://api.source2.com/data")
        let task3 = async DataFetcher("https://api.source3.com/data")
        
        # 等待所有完成
        let results = await [task1, task2, task3]
        
        # 聚合结果
        return llm act "Aggregate these results: " + str(results)
    }
}
```

### 模式 5: 流式 Agent（llm stream / streaming true + for await）

**场景**：实时输出 LLM 响应，改善用户体验

#### 方式 A：使用 `llm stream` + `on_chunk` 回调

```helen
fn print_chunk(chunk: str) {
    stream_print(chunk)
}

agent StreamingWriter(topic: str) {
    description "Write content with streaming output"
    
    main {
        llm stream "Write a detailed article about " + topic on_chunk print_chunk
    }
}

# 使用 — 用户立即看到输出，无需等待完整响应
StreamingWriter("The future of AI")
```

带完整回调的流式输出：

```helen
fn on_chunk(chunk: str) {
    stream_print(chunk)
}

fn on_complete() {
    print("\n\n✅ 完成")
}

agent StreamingWriter(topic: str) {
    description "Write content with streaming output"
    
    main {
        llm stream "Write a detailed article about " + topic on_chunk on_chunk on_complete on_complete
    }
}
```

#### 方式 B：使用 `streaming true` + `for await`（自定义处理每个 chunk）

```helen
agent Streamer(topic: str) {
    description "Stream a long response"
    streaming true
    prompt "Write a detailed essay about: {{topic}}"
}

main {
    let response = async Streamer("the history of computing")
    
    // 逐 chunk 处理流式响应
    for await chunk in response {
        stream_print(chunk)
    }
}
```

`streaming true` 使 agent 调用返回 `StreamingResponse` 对象，可在 `for await` 中迭代。
适用于需要自定义处理逻辑的场景（过滤、转换、聚合）：

```helen
main {
    let response = async Streamer("long essay")
    let total_length = 0
    
    // 流式聚合
    for await chunk in response {
        total_length = total_length + len(chunk)
        if len(chunk) > 10 {
            stream_print(chunk)  // 只输出长 chunk
        }
    }
    print("Total length: " + total_length)
}
```

### 模式 6: 工具使用 Agent

**场景**：Agent 使用工具完成复杂任务

```helen
agent CodeAssistant {
    description "AI coding assistant with file access"
    prompt """
    You are an expert coding assistant. You can:
    - Read and write files
    - Execute shell commands
    - Search the web for documentation
    
    Always explain your changes before making them.
    """
    tools = ["read_file", "write_file", "patch_file", "shell_exec", "web_search"]
    max-turns 15  # 允许多轮工具调用
    
    main {
        return llm act "Help me implement a REST API in Python"
    }
}
```

### 模式 7: 对话 Agent（对话历史）

**场景**：保持对话上下文的多轮对话

```helen
agent ConversationalAssistant {
    description "Multi-turn conversational assistant"
    prompt "You are a helpful conversational assistant. Remember context from previous messages."
    
    main {
        # 自动维护对话历史
        # 每次调用 llm act 都会记录到历史
        let response = llm act "Remember this context"
        
        # 后续调用可以引用之前的内容
        let followup = llm act "Based on what I said before, what do you think?"
        
        return followup
    }
}

# 在 REPL 中，对话历史自动维护
# 每次 :ask 都会记住之前的对话
```

## 高级模式

### 动态 Agent 选择

```helen
agent DynamicRouter(input: str) {
    description "Dynamically select agent based on input"
    
    main {
        # 使用 LLM 决定路由
        let decision = llm act "Classify this input into one of: tech, billing, general. Input: " + input
        
        if decision == "tech" {
            return TechSupport(input)
        } else if decision == "billing" {
            return BillingSupport(input)
        } else {
            return GeneralSupport(input)
        }
    }
}
```

### Agent 组合与继承

```helen
# 基础 Agent
agent BaseAgent {
    description "Base agent with common configuration"
    model "gpt-4"
    temperature 0.7
    
    main {
        return llm act "Base behavior"
    }
}

# 组合多个 Agent 的能力
agent MultiSkillAgent(task: str) {
    description "Agent that can use multiple skills"
    tools = ["web_search", "read_file", "write_file", "shell_exec"]
    
    main {
        # 根据任务动态选择策略
        llm if task {
            case "research, search, find" {
                return llm act "Research: " + task
            }
            case "code, implement, write" {
                return llm act "Implement: " + task
            }
            default {
                return llm act "Handle: " + task
            }
        }
    }
}
```

### 错误处理与重试

```helen
agent RobustAgent(task: str) {
    description "Agent with error handling and retry"
    
    main {
        let max_retries = 3
        let attempt = 0
        
        while attempt < max_retries {
            try {
                let result = llm act task
                return result
            } catch LLMError as e {
                attempt = attempt + 1
                if attempt >= max_retries {
                    throw RuntimeError("Failed after " + str(max_retries) + " attempts: " + e.message)
                }
                # 等待后重试
                sleep(2)
            }
        }
    }
}
```

## 最佳实践

### 1. 清晰的 description

```helen
# ✅ 好的 description
agent CodeReviewer {
    description "Review code for bugs, security issues, and best practices"
    # ...
}

# ❌ 模糊的 description
agent Helper {
    description "Helps with stuff"
    # ...
}
```

### 2. 具体的 prompt

```helen
# ✅ 具体的 prompt
agent DataAnalyst {
    prompt """
    You are a data analyst with expertise in Python, SQL, and statistics.
    When analyzing data:
    1. First understand the data structure
    2. Identify patterns and anomalies
    3. Provide statistical summaries
    4. Suggest actionable insights
    Always show your work and explain your reasoning.
    """
}

# ❌ 模糊的 prompt
agent Analyst {
    prompt "You analyze things."
}
```

### 3. 合理的 temperature

```helen
# 创造性任务：高 temperature
agent CreativeWriter {
    temperature 0.9
}

# 精确任务：低 temperature
agent CodeGenerator {
    temperature 0.2
}

# 平衡任务：中等 temperature
agent GeneralAssistant {
    temperature 0.7
}
```

### 4. 适当的 max-turns

```helen
# 简单问答：少轮次
agent QuickAnswer {
    max-turns 3
}

# 复杂任务：多轮次
agent ComplexSolver {
    max-turns 15
}
```

### 5. 最小权限工具

```helen
# ✅ 只授予需要的工具
agent FileReader {
    tools = ["read_file"]  # 只需要读取
}

# ❌ 授予过多工具
agent SimpleAgent {
    tools = ["read_file", "write_file", "shell_exec", "web_search"]  # 太多
}
```

### 6. 正确使用作用域（v1.10）

```helen
# ✅ 使用 shared let 进行跨 agent 共享
shared let cache = {}

agent CacheReader(key: str) {
    main {
        if key in cache {
            return cache[key]
        }
        return null
    }
}

# ❌ 错误：期望模块级 let 在 agent main 中可见
let local_cache = {}  // 模块级 let

agent BadCacheReader(key: str) {
    main {
        // 编译错误！local_cache 在 agent main 中不可见
        return local_cache[key]
    }
}
```

## 调试技巧

### 查看 Agent 配置

```helen
agent DebuggableAgent {
    description "Debug example"
    prompt "You are helpful."
    model "gpt-4"
    temperature 0.7
    max-turns 10
    
    main {
        // 打印配置信息
        print("Agent started")
        return llm act "Do something"
    }
}
```

### 使用 trace 跟踪

```helen
main {
    trace_on()  // 启用跟踪
    
    let result = MyAgent("test")
    
    let trace = get_trace()
    print("Execution trace: " + str(trace))
    
    trace_off()
}
```

## 相关技能

- **helen-agent-collaboration** — 多 Agent 协作模式详解
- **helen-syntax** — Helen 语法参考（包括 shared let、agent main 等）
- **helen-testing** — Agent 测试策略
- **helen-quality** — Agent 代码质量评估
