---
name: helen-agent-patterns
description: "Helen Agent 设计模式 — 单 Agent、多 Agent 协作、作用域隔离、共享变量、路由、流式处理、历史管理、上下文管理、Transcript 会话记录"
version: 1.17.0
author: Helen Team
license: MIT
tags: [helen, agent, patterns, design, llm, scope-isolation, shared-let, v1.12, closure, concurrency, history, persistence, context-window, context-management, transcript, session, v1.16, ground-truth-injection, v1.17]
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

// 调用
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

// 调用
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

#### 上下文配置 (v1.15+)

Helen v1.15 引入了完整的上下文管理增强，可以为每个 agent 独立配置：

```helen
agent SmartAssistant {
    description "Smart assistant with optimized context"
    
    // 上下文配置
    context {
        compression "graduated"      // 压缩策略
        cache-aware true             // 缓存感知
        working-memory true          // 工作记忆
        working-memory-tokens 5000   // 工作记忆预算
    }
    
    tools = ["read_file", "web_search"]
    
    main {
        return llm act "..."
    }
}
```

**配置选项**：

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `compression` | str | `"graduated"` | 压缩策略 |
| `cache-aware` | bool | `true` | 启用缓存感知压缩 |
| `working-memory` | bool | `true` | 启用工作记忆 |
| `working-memory-tokens` | int | `5000` | 工作记忆预算 |

**压缩策略**：

| 策略 | 说明 | 使用场景 |
|------|------|---------|
| `"none"` | 不压缩 | 短对话 |
| `"graduated"` | 五层渐进压缩（默认） | 长对话 |
| `"traditional"` | 传统截断 | 快速场景 |

#### Transcript 配置 (v1.16+)

Helen v1.16 引入了 TranscriptStore，自动保存所有对话历史。可以在 agent 中通过 stdlib 函数访问：

```helen
agent ChatBot {
    description "Chat bot with transcript management"
    
    main {
        // 获取当前会话 ID
        let session_id = get_session_id()
        print("会话 ID: " + session_id)
        
        // 列出所有会话
        let sessions = list_sessions()
        for s in sessions {
            print("{s.session_id}: {s.message_count} 条消息")
        }
        
        // 回放当前会话
        let messages = replay_transcript()
        for msg in messages {
            print("{msg.role}: {msg.content}")
        }
        
        // 导出会话
        export_transcript("chat_log.json", "json")
        
        // 获取压缩审计
        let audit = get_compression_audit()
        for event in audit {
            print("{event.layer}: {event.original_token_count} -> {event.compressed_token_count}")
        }
        
        return llm act "Hello!"
    }
}
```

**使用场景**：
- **会话恢复**: 使用 `resume_session(session_id)` 恢复之前的对话
- **审计追踪**: 使用 `get_compression_audit()` 分析压缩效率
- **会话导出**: 使用 `export_transcript()` 保存对话记录
- **多会话管理**: 使用 `list_sessions()` 管理多个会话

**配置**：在 `~/.helen/config.yaml` 中配置 transcript：

```yaml
transcript:
  enabled: true              # 默认启用
  backend: "jsonl"           # 或 "sqlite"
  session_dir: "~/.helen/sessions"
  max_memory_items: 1000
```

详见 [TranscriptStore 文档](../../docs/transcript_store_user_guide.md)。

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

### v1.12 隔离修复总结

v1.12 实施后的第二轮修复确保了隔离承诺的可靠性：

| 修复项 | 问题 | 修复后 |
|--------|------|--------|
| ReadOnlyView | `param[0]` 报错、迭代泄露原始引用 | 读操作正常、迭代项也被包装 |
| 闭包捕获 | 引用类型按引用捕获，后续修改可见 | 深拷贝快照，不受后续修改影响 |
| @sandbox | 工具限制未实现 | LLM 工具列表强制为空 |
| SharedStore | 无锁、内部属性可篡改 | RLock 保护、`_` 前缀属性不可访问 |
| 闭包作用域 | `_in_closure` 跳过所有检查 | 闭包内同样检查作用域隔离 |
| @open 写回 | 模块级 let 修改不写回 | @open agent 写回所有修改 |

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
// 定义专家
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

// 路由 Agent
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

// 使用
let response = SupportRouter("I can't login to my account")
// 路由到 TechSupport
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

// 管道
agent ContentPipeline(topic: str) {
    description "Research → Write → Edit pipeline"
    
    main {
        // 阶段 1: 研究
        let research = Researcher(topic)
        
        // 阶段 2: 写作
        let draft = Writer(topic, research)
        
        // 阶段 3: 编辑
        let final = Editor(draft)
        
        return final
    }
}

// 使用
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
        // 并发获取数据
        let task1 = async DataFetcher("https://api.source1.com/data")
        let task2 = async DataFetcher("https://api.source2.com/data")
        let task3 = async DataFetcher("https://api.source3.com/data")
        
        // 等待所有完成
        let results = await [task1, task2, task3]
        
        // 聚合结果
        return llm act "Aggregate these results: " + str(results)
    }
}
```

### 模式 5: 流式 Agent（llm act + on_chunk 回调 / streaming true + for await）

**场景**：实时输出 LLM 响应，改善用户体验

#### 方式 A：使用 `llm act` + `on_chunk` 回调

```helen
fn print_chunk(chunk: str) {
    stream_print(chunk)
}

agent StreamingWriter(topic: str) {
    description "Write content with streaming output"
    
    main {
        llm act "Write a detailed article about " + topic on_chunk print_chunk
    }
}

// 使用 — 用户立即看到输出，无需等待完整响应
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
        llm act "Write a detailed article about " + topic on_chunk on_chunk on_complete on_complete
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
        // 自动维护对话历史
        // 每次调用 llm act 都会记录到历史
        let response = llm act "Remember this context"
        
        // 后续调用可以引用之前的内容
        let followup = llm act "Based on what I said before, what do you think?"
        
        return followup
    }
}

// 在 REPL 中，对话历史自动维护
// 每次 :ask 都会记住之前的对话
```

## 高级模式

### 动态 Agent 选择

```helen
agent DynamicRouter(input: str) {
    description "Dynamically select agent based on input"
    
    main {
        // 使用 LLM 决定路由
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
// 基础 Agent
agent BaseAgent {
    description "Base agent with common configuration"
    model "gpt-4"
    temperature 0.7
    
    main {
        return llm act "Base behavior"
    }
}

// 组合多个 Agent 的能力
agent MultiSkillAgent(task: str) {
    description "Agent that can use multiple skills"
    tools = ["web_search", "read_file", "write_file", "shell_exec"]
    
    main {
        // 根据任务动态选择策略
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
                // 等待后重试
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
    // err.message    — "Agent 'Contractor' failed: ..."
    // err.agent_name — "Contractor"
    // err.agent_args — {req: "...", dir: "..."}
    // err.cause      — 底层异常
    error("失败: " + err.message)
}
```

`AgentError` 继承 `LLMError`，因此 `catch LLMError` 一并捕获 agent 失败。嵌套 agent 调用时，内层 AgentError 透传不双层包装。

## 最佳实践

### 1. 清晰的 description

```helen
// ✅ 好的 description
agent CodeReviewer {
    description "Review code for bugs, security issues, and best practices"
    // ...
}

// ❌ 模糊的 description
agent Helper {
    description "Helps with stuff"
    // ...
}
```

### 2. 具体的 prompt

```helen
// ✅ 具体的 prompt
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

// ❌ 模糊的 prompt
agent Analyst {
    prompt "You analyze things."
}
```

### 3. 合理的 temperature

```helen
// 创造性任务：高 temperature
agent CreativeWriter {
    temperature 0.9
}

// 精确任务：低 temperature
agent CodeGenerator {
    temperature 0.2
}

// 平衡任务：中等 temperature
agent GeneralAssistant {
    temperature 0.7
}
```

### 4. 适当的 max-turns

```helen
// 简单问答：少轮次
agent QuickAnswer {
    max-turns 3
}

// 复杂任务：多轮次
agent ComplexSolver {
    max-turns 15
}
```

### 5. 最小权限工具

```helen
// ✅ 只授予需要的工具
agent FileReader {
    tools = ["read_file"]  # 只需要读取
}

// ❌ 授予过多工具
agent SimpleAgent {
    tools = ["read_file", "write_file", "shell_exec", "web_search"]  # 太多
}
```

### 6. 正确使用作用域（v1.10/v1.12）

```helen
// ✅ 使用 shared let 进行跨 agent 共享（v1.12: 只允许值类型）
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

// ❌ 错误 v1：期望模块级 let 在 agent main 中可见
let local_cache = {}  // 模块级 let

agent BadCacheReader(key: str) {
    main {
        // 编译错误！local_cache 在 agent main 中不可见
        return local_cache[key]
    }
}

// ❌ 错误 v2：v1.12 起 shared let 不能使用引用类型
// shared let bad_cache = {}  # 语义错误！
```

### 7. Inject task-relevant ground truth via `{{}}`

**Principle: an agent cannot know what you do not tell it. If a runtime fact matters for correctness, inject it — never let the LLM guess.**

LLMs have no access to the current environment: the clock, the working directory, the OS, the git branch, the file layout. When a task depends on such facts and they are absent from the prompt, the model will **confabulate plausible-sounding but wrong values** — silently, with high confidence. This is the single most common source of subtle agent bugs.

The fix is mechanical: **resolve the fact in Helen, interpolate it into the prompt via `{{}}`.** The prompt is the agent's entire world — anything missing from it is effectively unknowable.

```helen
// ✅ Ground truth injected — LLM sees real values
agent DevAgent(cwd: str) {
    description "Programming assistant"
    prompt """
    You are a senior engineer working in {{cwd}}.
    Current time: {{now()}}
    OS: {{os_name()}}
    Working directory: {{cwd}}

    Answer only based on these facts; if something is not provided, say so.
    """
    tools = ["read_file", "write_file", "shell_exec"]

    main {
        return llm act "Review the project layout"
    }
}

// ❌ Ground truth missing — LLM will fabricate
agent VagueDevAgent {
    description "Programming assistant"
    prompt "You are a senior engineer. Help with code."
    // No cwd, no time, no OS → LLM invents them
}
```

**Rule of thumb — ask "what does this agent need to be true about the world?" then inject it:**

| Task domain | Inject via `{{}}` |
|-------------|-------------------|
| Programming | `cwd`, `os_name()`, `shell_exec("git branch --show-current")` |
| Scheduling / reminders | `now()`, `timezone()` |
| File operations | directory listing, absolute paths |
| Database agents | schema excerpt, connection target |
| Data analysis | row counts, column names, sample rows |
| Multi-agent pipelines | upstream agent outputs, shared state snapshot |

**Two anti-patterns to avoid:**

```helen
// ❌ Anti-pattern 1: asking the LLM to "assume" environment facts
prompt "Assume you are in /home/user/project on Linux at 2026-07-11."
// Wrong the moment the assumption drifts from reality.

// ❌ Anti-pattern 2: putting dynamic facts in `description`
description "Agent for /home/rxx/helen"  // baked at parse time, not runtime
// `description` is static — use `prompt` with `{{}}` for dynamic facts.
```

**Why this matters more than it sounds:** LLMs are trained to be helpful, not to refuse. When asked "what file am I in?" without context, they will answer — and the answer will be wrong. Injecting ground truth turns a hallucination failure mode into a non-issue.

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

---

## 上下文管理（v1.15 新增）

Helen v1.15 引入了完整的上下文管理增强，通过 7 个 Phase 实施，对齐 Claude Code 的上下文管理能力。

### 设计模式：高性能研究 Agent

使用渐进压缩和工作记忆优化长对话：

```helen
agent Researcher(topic: str) {
    description "Research assistant with optimized context"
    
    // 上下文配置
    context {
        compression "graduated"      // 五层渐进压缩
        cache-aware true             // 缓存感知（提高缓存命中率）
        working-memory true          // 自动跟踪文件操作
        working-memory-tokens 8000   // 更大的工作记忆
    }
    
    tools ["web_search", "web_fetch", "read_file", "write_file"]
    
    main {
        // 工作记忆自动跟踪文件操作
        let data = read_file("research_data.json")
        let analysis = analyze(data)
        write_file("analysis_result.json", analysis)
        
        // LLM 可以看到哪些文件被读取和修改
        return llm act "Analyze the research data and write report"
        // 工作记忆包含：
        // - 活跃文件: research_data.json, analysis_result.json
        // - 最近决策: Modified analysis_result.json
    }
}
```

### 设计模式：快速响应 Agent

禁用工作记忆以提高响应速度：

```helen
agent QuickResponder {
    description "Fast response agent"
    
    context {
        compression "none"           // 不压缩
        working-memory false         // 禁用工作记忆
    }
    
    main {
        // 快速响应，无需上下文管理开销
        return llm act "Quick answer"
    }
}
```

### 三通道上下文

启用工作记忆后，LLM 看到的上下文分为三个通道：

| 通道 | 比例 | 内容 |
|------|------|------|
| 系统指令 | 15% | 框架指令、agent 描述、技能索引 |
| 工作记忆 | 50% | 活跃文件、最近决策、待办事项、错误历史 |
| 对话历史 | 35% | 压缩后的对话消息 |

### 渐进压缩管线

五层渐进压缩策略，"最廉价动作优先"原则：

| 层级 | 使用率阈值 | 策略 | 说明 |
|------|-----------|------|------|
| Layer 1 | 60% | Budget Reduction | 替换大工具输出为引用指针 |
| Layer 2 | 70% | Snip | 丢弃过时轮次 |
| Layer 3 | 80% | Microcompact | 清除旧工具结果，保留决策 |
| Layer 4 | 90% | Context Collapse | 归档并投射折叠视图 |
| Layer 5 | 95% | Auto-Compact | LLM 语义压缩 |

### 缓存感知压缩

考虑 prompt cache 的缓存友好策略：

- **稳定前缀**：保留前 30% 消息不变（缓存友好区）
- **批量阈值**：使用率达到 75% 才触发压缩
- **仅后缀修改**：只在缓存区域外进行修改

**效果**：缓存命中率从 10-20% 提升到 70-80%

### 工作记忆

自动跟踪 agent 执行过程中的关键信息：

```helen
agent CodeReviewer {
    context {
        working-memory true  // 启用工作记忆
    }
    
    tools ["read_file", "write_file", "patch_file"]
    
    main {
        // 自动跟踪：读取的文件
        let code = read_file("src/main.py")
        
        // 自动跟踪：修改的文件
        let fixed = fix_code(code)
        write_file("src/main.py", fixed)
        
        // LLM 现在知道哪些文件被修改了
        return llm act "Review the changes"
    }
}
```

### 上下文管理最佳实践

| Agent 类型 | 推荐配置 | 说明 |
|-----------|---------|------|
| 研究型 Agent | `compression "graduated"` + `working-memory true` | 长对话，需要跟踪文件 |
| 快速响应 Agent | `compression "none"` + `working-memory false` | 短对话，快速响应 |
| 多轮对话 Agent | `cache-aware true` + `working-memory-tokens 8000` | 提高缓存命中率 |
| 简单任务 Agent | 默认配置 | 无需特殊配置 |

### 上下文监控

在 REPL 中使用 `:stats` 查看上下文使用情况：

```
> :stats
╔══════════════════════════════════════╗
║       Context Usage Statistics        ║
╠══════════════════════════════════════╣
║ ✅ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  12.3%            ║
║ Tokens:   15,984 /  131,072              ║
║ Model:  qwen3.7-plus                  ║
║ Messages: 8                           ║
║                                       ║
║ Working Memory:                       ║
║   Active Files: 3                     ║
║   Recent Decisions: 5                 ║
║   Pending TODOs: 2                    ║
║   Error History: 1                    ║
╚══════════════════════════════════════╝
```

### 程序化访问

```helen
main {
    // 获取上下文统计
    let stats = context_stats()
    print("Token usage: " + stats["usage_ratio"])
    
    // 获取工作记忆快照
    let wm = working_memory_snapshot()
    print("Active files: " + wm["active_files"])
    
    // 手动触发压缩
    compress_context("graduated")
    
    // 清除上下文
    clear_context()
}
```

---

## 总结

Helen v1.15 的上下文管理增强包括：

1. ✅ **自动集成**：所有 agent 默认使用渐进压缩和工作记忆
2. ✅ **可配置性**：每个 agent 可以独立配置上下文策略
3. ✅ **向后兼容**：现有代码无需修改
4. ✅ **对齐 Claude Code**：100% 对齐

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

## 延伸阅读

- **[[Agent 提示词工程完全指南]]**（`wiki/reference/agent-system-prompt-guide.md`）— 来自 Claude Code 系统提示词逆向工程的设计方法论：结构布局、写作原则、反模式、Token 预算、缓存设计、中途注入机制。本技能 § 最佳实践 7（注入环境事实）的原则即来源于此。



### 模式：LLM 结构化输出 + JSON 降级

**场景**：要求 LLM 返回结构化 JSON，但需要处理解析失败的情况。

```helen
agent StructuredAnalyzer(input: str) {
    description "返回结构化分析结果"
    prompt """
    分析: {{input}}
    
    严格以 JSON 格式返回:
    {"key_points": [...], "summary": "...", "score": 0-10}
    """
    
    main {
        let response = llm act
        
        // 模式: try JSON parse, fallback to default structure
        try {
            let parsed = json_parse(response)
            // 验证必需字段
            if !has_key(parsed, "key_points") {
                parsed["key_points"] = []
            }
            return parsed
        } catch RuntimeError err {
            // LLM 输出不是合法 JSON 时降级
            return {
                "key_points": ["解析失败，原始输出已保存"],
                "summary": response,
                "score": 0,
                "_raw": response  // 保留原始输出供调试
            }
        }
    }
}
```

**陷阱**:
- LLM 可能在 JSON 前后添加 markdown 代码块标记，需要先清理
- 始终提供降级结构，避免调用方收到 null
- 验证必需字段存在，LLM 可能省略某些字段

### 模式：配置驱动的参数化 Agent

**场景**：多个相似 Agent 只有配置不同（角色、视角、风格等），避免重复定义。

```helen
// ❌ 冗余：为每个角色创建独立 Agent
agent OptimistAgent(topic: str) { ... }
agent PessimistAgent(topic: str) { ... }
agent InnovatorAgent(topic: str) { ... }

// ✅ 推荐：配置驱动，一个 Agent 处理所有角色
agent RoleAgent(topic: str, config: map) {
    description "可配置的角色 Agent"
    prompt """
    你是「{{config["name"]}}」。
    角色描述: {{config["description"]}}
    风格: {{config["style"]}}
    
    分析: {{topic}}
    """
    main {
        return llm act
    }
}

// 使用
let configs = [
    {"name": "乐观派", "description": "看到最好的一面", "style": "积极向上"},
    {"name": "悲观派", "description": "关注风险", "style": "谨慎保守"}
]

for config in configs {
    let result = RoleAgent("话题", config)
}
```

**优势**: 新增角色只需添加配置，无需修改代码。

