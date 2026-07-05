---
name: helen-agent-patterns
description: "Helen Agent 设计模式 — 单 Agent、多 Agent 协作、作用域隔离、共享变量、路由、流式处理、历史管理"
version: 1.12.0
author: Helen Team
license: MIT
tags: [helen, agent, patterns, design, llm, scope-isolation, shared-let, v1.12, closure, concurrency, history, persistence, context-window]
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
    tools = ["web_search", "read_file", "write_file"]  # 可用工具（字面量列表）
    
    main {
        return llm act "Do something complex"
    }
}
```

#### tools = CONST_NAME（复用工具集）

`tools` 可引用**模块级 const**，减少重复并保持工具集**静态可审计**（安全边界清晰）：

```helen
const FILE_TOOLS = ["read_file", "write_file", "path_exists"]
const RESEARCH_TOOLS = ["web_search", "web_fetch", "read_file"]

agent Contractor {
    tools = FILE_TOOLS            # 复用 const
    ...
}
```

**严格校验**：
- ✅ 模块级 const 引用 + 字面量列表
- ❌ 可变变量、函数、agent、未定义标识符、重复声明
- ❌ 表达式拼接（`A + B`）— 安全设计，工具边界必须静态可追踪

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

## Agent 作用域隔离（v1.10/v1.12）

### 核心规则

**Agent main 在完全隔离的环境中运行**，这是 v1.10 的重要特性，v1.12 进一步增强：

| 变量类型 | 在 agent main 中 | 说明 |
|---------|-----------------|------|
| 模块级 `let` | ❌ **不可见** | 编译时报错（@open 除外）|
| 模块级 `const` | ✅ 自动可见 | 只读共享 |
| `shared let`（值类型） | ✅ 可见 | 跨 agent 可写 |
| `shared store` | ✅ 可见 | 通过方法访问 |
| 局部变量 | ✅ 可见 | 闭包值捕获 |

**v1.12 新增**：
- `@open` 装饰器：允许访问模块级 let（调试用）
- `@strict` 装饰器：参数和返回值深拷贝
- `@sandbox` 装饰器：最严格隔离
- `shared let` 只允许值类型（int/float/str/bool）
- 引用类型（list/dict）通过**参数传递**，自动只读包装
- 闭包采用值捕获，不持有整个环境引用
- `arr[i] = x` 和 `obj.field = x` 也受隔离检查约束

### 隔离级别

```helen
// L0: @open — 模块级 let 可见（调试用）
@open agent DebugAgent() {
    main { return module_let }
}

// L1: 标准隔离（默认）
agent NormalAgent() { ... }

// L2: @strict — 深拷贝参数和返回值
@strict agent StrictAgent(data: list) {
    main {
        data.append(4)  // 安全：data 是副本
        return data     // 返回值也是副本
    }
}

// L3: @sandbox — 最严格
@sandbox agent SafeAgent() { ... }
```

### 示例：作用域隔离

```helen
// 模块级变量
let module_counter = 0           // ❌ agent main 中不可见
const MAX_RETRIES = 3            // ✅ agent main 中自动可见
shared let shared_count = 0      // ✅ agent main 中可见可写（v1.12: 值类型）

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
        
        // ✅ shared let 可见（v1.12: 只允许值类型）
        shared_count = shared_count + 1
        
        // ✅ 局部变量
        let local_data = "local"
        
        return llm act "Process: " + task
    }
}
```

**v1.12 参数只读**：引用类型参数自动包装为只读视图

```helen
agent ProcessItems(items: list<int>) {
    main {
        // ✅ 可以读取
        let first = items[0]
        let count = len(items)
        
        // ❌ 不能修改（v1.12 起自动只读包装）
        // items[0] = 999  // ScopeViolationError
        
        // 如需修改，创建副本
        let my_items = list(items)
        my_items.append(100)
        return my_items
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

**v1.12 更新**：`shared let` 只能使用值类型。需要共享引用类型时，通过参数传递。

```helen
// v1.12: shared let 只允许值类型
shared let request_count = 0
shared let last_request_time = ""

agent RequestCounter() {
    description "Count requests"
    
    main {
        request_count = request_count + 1
        last_request_time = "2024-01-01"  // str 是值类型
        return request_count
    }
}

// 引用类型通过参数传递
agent CacheWriter(cache: map, key: str, value: any) {
    description "Write to cache (passed as parameter)"
    
    main {
        // v1.12: cache 是只读视图，创建副本修改
        let my_cache = dict(cache)
        my_cache[key] = value
        return my_cache
    }
}

// 使用
let my_cache = {}
let updated = CacheWriter(my_cache, "user:1", "Alice")
RequestCounter()
print("Requests: " + request_count)  // 1
```

### Shared Store 协作模式（v1.12）

对于需要共享复杂可变状态的场景，使用 `shared store`：

```helen
// v1.12: 使用 shared store 管理复杂共享状态
shared store TaskManager {
    let pending = 0
    let completed = 0

    fn submit() {
        pending = pending + 1
    }

    fn finish() {
        pending = pending - 1
        completed = completed + 1
    }

    fn get_status(): str {
        return str(pending) + " pending, " + str(completed) + " completed"
    }
}

agent TaskProducer() {
    main {
        TaskManager.submit()
        TaskManager.submit()
        return "submitted"
    }
}

agent TaskWorker() {
    main {
        TaskManager.finish()
        return "done"
    }
}

main {
    TaskProducer()
    TaskWorker()
    print(TaskManager.get_status())  // "1 pending, 1 completed"
}
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

#### Agent 调用失败 — AgentError

Agent 调用失败时抛出 `AgentError`，携带结构化上下文（agent_name、agent_args、cause）：

```helen
try {
    let result = Contractor(req, dir)
} catch AgentError err {
    # err.message    — "Agent 'Contractor' failed: ..."
    # err.agent_name — "Contractor"
    # err.agent_args — {req: "...", dir: "..."}
    # err.cause      — 底层异常
    error("失败: " + err.message)
}
```

`AgentError` 继承 `LLMError`，因此 `catch LLMError` 一并捕获 agent 失败。嵌套 agent 调用时，内层 AgentError 透传不双层包装。

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

### 6. 正确使用作用域（v1.10/v1.12）

```helen
# ✅ 使用 shared let 进行跨 agent 共享（v1.12: 只允许值类型）
shared let cache_hits = 0
shared let cache_misses = 0

agent CacheReader(key: str, cache: map) {
    main {
        if key in cache {
            cache_hits = cache_hits + 1
            return cache[key]
        }
        cache_misses = cache_misses + 1
        return null
    }
}

# ❌ 错误 v1：期望模块级 let 在 agent main 中可见
let local_cache = {}  // 模块级 let

agent BadCacheReader(key: str) {
    main {
        # 编译错误！local_cache 在 agent main 中不可见
        return local_cache[key]
    }
}

# ❌ 错误 v2：v1.12 起 shared let 不能使用引用类型
# shared let bad_cache = {}  # 语义错误！
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

## 历史管理（v1.12 新增）

### 设计模式：持久化 Agent

跨会话保留对话连续性：

```helen
agent PersistentAssistant {
    description "Assistant with persistent history"
    
    main {
        // 启动时加载历史
        let loaded = load_history("./session.json")
        if loaded > 0 {
            print("Resumed session with " + str(loaded) + " messages")
        }
        
        // 执行任务
        let result = llm act "Continue our previous conversation"
        
        // 退出时保存历史
        save_history("./session.json")
        return result
    }
}
```

### 设计模式：智能研究 Agent

利用历史检索避免重复工具调用：

```helen
agent SmartResearcher {
    tools ["web_search", "web_fetch"]
    
    main {
        // 搜索之前的工具调用
        let past_searches = search_history(tool_name="web_search")
        
        if len(past_searches) > 0 {
            // 引用之前的搜索结果
            return llm act "Based on my previous research: " + str(past_searches[0])
        }
        
        // 首次搜索
        let info = web_search("Helen programming language")
        return llm act "Analyzed: " + info
    }
}
```

### 设计模式：上下文感知 Agent

使用上下文统计优化 token 使用：

```helen
agent ContextAwareAgent {
    description "Agent that monitors its own context usage"
    model "qwen3.7-plus"
    
    main {
        // 获取上下文统计
        let stats = get_context_stats()
        let usage = stats["usage_percent"]
        
        if usage > 80 {
            // 上下文快满了，切换压缩模式
            // 或提前结束对话
            print("Warning: context usage at " + str(usage) + "%")
        }
        
        return llm act "Continue work..."
    }
}
```

### REPL 调试

在 REPL 中使用 `:stats` 命令查看上下文使用情况：

```
> :stats
╔══════════════════════════════════════╗
║       Context Usage Statistics        ║
╠══════════════════════════════════════╣
║ ✅ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  12.3%            ║
║ Tokens:   15,984 /  131,072              ║
║ Model:  qwen3.7-plus                  ║
║ Messages: 8                           ║
╚══════════════════════════════════════╝
```

### History 压缩策略

三种压缩模式：

| 模式 | 行为 | 使用场景 |
|------|------|---------|
| `summarize`（默认） | 三层：recent→middle→oldest | 长对话保持上下文 |
| `truncate` | 直接丢弃旧消息 | 简洁场景 |
| `none` | 不压缩 | 短对话/测试 |

```python
# Python API 动态切换
interpreter._history_manager.set_compression_mode("truncate")
```

### Token 精确计数

安装 `tiktoken` 获得精确 token 计数：

```bash
pip install "helen[accurate-tokens]"
```

未安装时使用字符级启发式（~15% 精度）。

## 相关技能

- **helen-agent-collaboration** — 多 Agent 协作模式详解
- **helen-syntax** — Helen 语法参考（包括 shared let、agent main 等）
- **helen-testing** — Agent 测试策略
- **helen-quality** — Agent 代码质量评估
