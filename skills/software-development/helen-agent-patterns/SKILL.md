---
name: helen-agent-patterns
description: "Helen Agent 设计模式 — 单 Agent、多 Agent 协作、路由、流式处理"
version: 1.0.0
author: Helen Team
license: MIT
metadata:
  hermes:
    tags: [helen, agent, patterns, design, llm]
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

# 调用（推荐显式使用 call 关键字）
let result = call SimpleAgent()
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
let result = call Translator("Hello", "Chinese")
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
    tools ["web_search", "read_file", "write_file"]  # 可用工具
    
    main {
        return llm act "Do something complex"
    }
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
    tools ["read_file", "write_file", "shell_exec"]
    
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
    tools ["web_search", "web_fetch"]
    
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
    tools ["http_get"]
    
    main {
        return llm act "Fetch data from: " + source
    }
}

agent DataAggregator {
    description "Aggregate data from multiple sources"
    
    main {
        # 并发获取数据
        let task1 = async call DataFetcher("https://api.source1.com/data")
        let task2 = async call DataFetcher("https://api.source2.com/data")
        let task3 = async call DataFetcher("https://api.source3.com/data")
        
        # 等待所有完成
        let results = await [task1, task2, task3]
        
        # 聚合结果
        return llm act "Aggregate these results: " + str(results)
    }
}
```

### 模式 5: 流式 Agent（llm stream / streaming true + for await）

**场景**：实时输出 LLM 响应，改善用户体验

#### 方式 A：使用 `llm stream`（自动输出到终端）

```helen
agent StreamingWriter(topic: str) {
    description "Write content with streaming output"
    
    main {
        llm stream "Write a detailed article about " + topic {
            on_chunk(chunk) {
                # 实时输出每个片段
                print(chunk, end="")
            }
        }
    }
}

# 使用 — 用户立即看到输出，无需等待完整响应
StreamingWriter("The future of AI")
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
    tools ["read_file", "write_file", "patch_file", "shell_exec", "web_search"]
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
    tools ["web_search", "read_file", "write_file", "shell_exec"]
    
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
    tools ["read_file"]  # 只需要读取
}

# ❌ 授予过多工具
agent SimpleAgent {
    tools ["read_file", "write_file", "shell_exec", "web_search"]  # 太多
}
```

## 调试技巧

### 1. 打印 Agent 配置

```helen
agent DebugAgent {
    description "Debug agent"
    model "gpt-4"
    temperature 0.7
    
    main {
        print("Agent starting...")
        let result = llm act "Debug task"
        print("Agent completed")
        return result
    }
}
```

### 2. 使用 :ask 在 REPL 中测试

```bash
$ helen repl
>>> :ask How does the Translator agent work?
# AI 助手会解释 Agent 的工作原理
```

### 3. 检查对话历史

```helen
# 在 Agent 中访问历史
agent HistoryAwareAgent {
    main {
        # 自动维护历史
        let response = llm act "Question 1"
        let followup = llm act "Follow up on that"
        return followup
    }
}
```

### 4. 使用可观测性调试 Agent

Helen 提供 AI 原生可观测性，帮助调试 Agent 行为：

```helen
agent DebuggableAgent(input) {
    description "Agent with observability"
    
    fn validate(data) {
        # 运行时断言
        assert data != null, "input must not be null"
        assert len(data) > 0, "input must not be empty"
        
        # 结构化调试输出
        debug("validated input", data)
        return true
    }
    
    main {
        # 开启执行追踪
        trace_on()
        
        let valid = validate(input)
        if valid {
            let result = llm act "Process: " + str(input)
            debug("LLM result", result)
            return result
        }
        
        trace_off()
    }
}
```

**REPL 调试命令**：

```
:trace on          # 开启追踪
:trace show 20     # 显示最近 20 条执行记录
:last_error        # 显示上次错误的 JSON 上下文
:llm_log 5         # 显示最近 5 次 LLM 调用审计
```

**错误快照格式**（JSON，AI 可直接消费）：

```json
{
  "error": {"type": "AssertionError", "message": "...", "location": "..."},
  "call_stack": [{"function": "...", "args": {...}}],
  "scope": {"var": "value"}
}
```

## 总结

Helen Agent 设计模式：

1. **专家 Agent** — 领域专家，单一职责
2. **路由 Agent** — `llm if` 分类路由
3. **管道 Agent** — 顺序处理，阶段化
4. **并发 Agent** — `async/await` 并发执行
5. **流式 Agent** — `llm stream` 实时输出
6. **工具 Agent** — 使用工具完成复杂任务
7. **对话 Agent** — 多轮对话，保持上下文

选择合适的模式，遵循最佳实践，构建强大的 AI 应用。
