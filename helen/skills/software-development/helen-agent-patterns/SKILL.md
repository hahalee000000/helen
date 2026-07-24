---
name: helen-agent-patterns
description: "Helen Agent 设计模式 — 单 Agent 核心模式、作用域隔离、路由、流式、工具回调、最佳实践"
version: 1.22.0
author: Helen Team
license: MIT
tags: [helen, agent, patterns, design, llm, scope-isolation, shared-let, v1.12, closure, spawn, channel, v1.18, on-tool-end, v1.21, invocation, v1.22]
---

# Helen Agent 设计模式

Helen 将 Agent 作为**一等语言构造**，提供声明式语法和强大的 LLM 集成。本文聚焦**单 Agent 核心模式**；多 Agent 协作详见 `helen-agent-collaboration`。

## 🎯 第一原则：调用者决定上下文（Caller Decides Context）

> **"调用 agent 前先问：它需要知道什么？"**

- Agent **严格隔离**——每次调用创建独立执行环境
- **不会自动继承**调用者的变量、历史、LLM 上下文
- **所有**上下文必须通过参数、`shared store`、`const` 或 Channel **显式传递**

无论选择什么协作模式，**第一步总是画出上下文流图**：

```
调用者 ──参数──► Agent 输入
      ──SharedStore──► 共享状态
      ◄──返回值/Channel── Agent 输出
```

> 💡 完整说明详见 `helen-agent-collaboration` §"设计原则：调用者决定上下文"

---

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

let result = SimpleAgent()
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

let result = Translator("Hello", "Chinese")
```

### Agent 配置选项

```helen
agent ConfiguredAgent {
    description "Agent with full configuration"
    prompt "You are an expert assistant."
    model "gpt-4"              # LLM 模型
    temperature 0.7            # 创造性 (0.0-1.0)
    max-turns 10               # 最大工具调用轮次
    streaming true             # 启用流式响应
    tools = ["web_search", "read_file", "write_file"]
    
    main {
        return llm act "Do something complex"
    }
}
```

`tools` 可引用模块级 const，减少重复并保持工具集静态可审计：

```helen
const FILE_TOOLS = ["read_file", "write_file", "path_exists"]
agent FileWorker {
    tools = FILE_TOOLS
    main { ... }
}
```

### Agent vs Skill

| 维度 | Agent | Skill |
|------|-------|-------|
| 本质 | 运行时实体 | 静态文档 |
| 可调用 | ✅ `Agent()` | ❌ 不可调用 |
| 有状态 | ✅ 维护对话/工具状态 | ❌ 无状态 |
| 用途 | **执行**任务 | **指导**如何执行 |

Agent 可加载 Skill 作为知识源：`load_skill("helen-testing")`。

---

## Agent 作用域隔离（v1.10/v1.12）

### 核心规则

**Agent main 在完全隔离的环境中运行**：

| 变量类型 | 在 agent main 中 | 说明 |
|---------|-----------------|------|
| 模块级 `let` | ❌ 不可见 | 编译时报错（@open 除外）|
| 模块级 `const` | ✅ 自动可见 | 只读共享 |
| `shared let`（值类型） | ✅ 可见 | 跨 agent 可写 |
| `shared store` | ✅ 可见 | 通过方法访问 |
| 局部变量 | ✅ 可见 | 闭包值捕获 |

**v1.12 增强**：
- `@open` / `@strict` / `@sandbox` 三种隔离装饰器
- `shared let` 只允许值类型（int/float/str/bool）
- 引用类型参数自动包装为只读视图（ReadOnlyView）
- 闭包采用值捕获（深拷贝快照）
- `arr[i] = x` 和 `obj.field = x` 也受隔离检查约束

### 隔离级别

```helen
@open agent DebugAgent() {         // L0: 模块级 let 可见（调试用）
    main { return module_let }
}
agent NormalAgent() { ... }        // L1: 标准隔离（默认）
@strict agent StrictAgent(data: list) {  // L2: 深拷贝参数和返回值
    main { data.append(4); return data }
}
@sandbox agent SafeAgent() { ... } // L3: 强制 tools=[]
```

### 示例：作用域隔离

```helen
let module_counter = 0           // ❌ agent main 中不可见
const MAX_RETRIES = 3            // ✅ agent main 中自动可见
shared let shared_count = 0      // ✅ agent main 中可见可写

agent Worker(task: str) {
    functions {
        fn process(): str {
            module_counter = module_counter + 1  // ✅ functions 块中可见
            return "processed: " + task
        }
    }
    
    main {
        // ❌ 编译错误：module_counter 在 agent main 中不可见
        print("Max retries: " + MAX_RETRIES)     // ✅ const 自动可见
        shared_count = shared_count + 1           // ✅ shared let 可见
        return llm act "Process: " + task
    }
}
```

### 参数只读 + 闭包捕获

```helen
agent ProcessItems(items: list<int>) {
    main {
        let first = items[0]         // ✅ 可读
        // items[0] = 999            // ❌ ScopeViolationError
        let my_items = list(items)   // 创建副本修改
        return my_items
    }
}

agent DataProcessor(data: list) {
    main {
        let threshold = 10
        fn filter(items: list): list {  // 闭包捕获局部变量
            let result = []
            for item in items {
                if item > threshold { result.append(item) }
            }
            return result
        }
        return llm act "Filtered: " + str(filter(data))
    }
}
```

### shared let 跨 Agent 协作

```helen
shared let request_count = 0
shared let last_request_time = ""

agent RequestCounter() {
    main {
        request_count = request_count + 1
        last_request_time = "2024-01-01"  // str 是值类型
        return request_count
    }
}

// 引用类型通过参数传递，自动只读包装
agent CacheWriter(cache: map, key: str, value: any) {
    main {
        let my_cache = dict(cache)  // 创建副本
        my_cache[key] = value
        return my_cache
    }
}
```

### Shared Store 协作（v1.12）

```helen
shared store TaskManager {
    let pending = 0
    let completed = 0
    fn submit()  { pending = pending + 1 }
    fn finish()  { pending = pending - 1; completed = completed + 1 }
    fn get_status(): str {
        return str(pending) + " pending, " + str(completed) + " completed"
    }
}

agent TaskProducer() { main { TaskManager.submit(); TaskManager.submit() } }
agent TaskWorker()   { main { TaskManager.finish() } }

main {
    TaskProducer()
    TaskWorker()
    print(TaskManager.get_status())  // "1 pending, 1 completed"
}
```

### v1.12 隔离修复要点

| 修复项 | 修复后 |
|--------|--------|
| ReadOnlyView | 读操作正常、迭代项也被包装 |
| 闭包捕获 | 深拷贝快照，不受后续修改影响 |
| @sandbox | LLM 工具列表强制为空 |
| SharedStore | RLock 保护、`_` 前缀属性不可访问 |

---

## Agent 上下文隔离（v1.22/v1.23）

除变量作用域隔离外，v1.22 引入 **invocation 级别上下文隔离**——每次进入 agent `main {}` 创建新的 `invocation_id`，LLM 只看到当前 invocation 的消息。

```helen
agent AgentA { main { return llm act "我是 Alice" } }
agent AgentB { main { return llm act "我叫什么名字？" } }

let a = AgentA()  // invocation_id: inv_abc123
let b = AgentB()  // invocation_id: inv_def456
// AgentB 的 LLM 看不到 AgentA 的对话 — 每个 main {} 是 fresh context
```

| 隔离维度 | 作用域隔离（v1.10/v1.12） | 上下文隔离（v1.22/v1.23） |
|---------|------------------------|-------------------------|
| 隔离对象 | 变量 | LLM 对话历史 |
| 机制 | 编译时检查 | 运行时 invocation_id 过滤 |
| 目的 | 防止变量污染 | 防止上下文泄露 |

嵌套调用形成调用树（`parent_invocation_id`），可用 `list_invocations()` / `get_invocation_tree()` 查询。`restore_context()` 支持按 invocation 过滤。v1.23 修复了 `_prepare_history_for_llm()` 绕过 invocation 过滤的 bug。

---

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
    prompt "You are a mathematics professor. Provide rigorous proofs."
    temperature 0.2  // 低温度，更确定
    
    main {
        return llm act "Solve this math problem step by step"
    }
}
```

### 模式 2: 路由 Agent（llm if）

**场景**：根据输入内容路由到不同专家 Agent

```helen
agent TechSupport(query: str) {
    description "Technical support specialist"
    prompt "You are a technical support expert."
    main { return llm act "Help with: " + query }
}

agent BillingSupport(query: str) {
    description "Billing support specialist"
    prompt "You are a billing support expert."
    main { return llm act "Help with: " + query }
}

agent GeneralSupport(query: str) {
    description "General support specialist"
    main { return llm act "Help with: " + query }
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
    prompt "You are a meticulous editor. Fix grammar, improve clarity."
    temperature 0.3
    
    main {
        return llm act "Edit and improve this content: " + content
    }
}

// 管道
agent ContentPipeline(topic: str) {
    description "Research → Write → Edit pipeline"
    
    main {
        let research = Researcher(topic)
        let draft = Writer(topic, research)
        let final = Editor(draft)
        return final
    }
}

let article = ContentPipeline("Helen programming language")
```

### 模式 4: 并发 Agent（spawn + Channel）

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
        let m1 = spawn DataFetcher("https://api.source1.com/data")
        let m2 = spawn DataFetcher("https://api.source2.com/data")
        let m3 = spawn DataFetcher("https://api.source3.com/data")
        
        let r1 = m1.receive()
        let r2 = m2.receive()
        let r3 = m3.receive()
        let results = [r1, r2, r3]
        
        return llm act "Aggregate these results: " + str(results)
    }
}
```

**多路复用**：`mailbox_select([m1, m2, m3])` 返回第一个就绪的 Channel 结果。

**⚠️ Transcript 运行时隔离**（关键设计原则）：

`spawn` 创建的每个 agent 都在**独立 Interpreter 实例**中运行，拥有独立 `session_id` 和 transcript。这是**刻意设计**：

- 同一进程多次 `get_session_id()` → 相同 ID
- 重启程序 → 新 session_id（`session_{timestamp}_{uuid8}`）
- `spawn` → 新 session_id + 新 transcript
- 普通 agent 调用（同进程）→ 共享 session_id，靠 `invocation_id` 区分

#### ❌ 反模式：假设自动继承

```helen
agent Worker(task: str, ch: Channel) {
    main {
        let sid = get_session_id()     // ❌ 这是 worker 自己的新 session
        ch.send("done in " + sid)
    }
}
```

#### ✅ 接力模板：显式传递 session_id

```helen
main {
    let parent_sid = get_session_id()
    let m = spawn Worker("task", parent_sid)  // 显式传递
}

agent Worker(task: str, parent_sid: str, ch: Channel) {
    main {
        resume_session(parent_sid)  // 显式继承父 transcript
        ch.send("done")
    }
}
```

#### 📋 三种接力方式

| 场景 | 推荐做法 |
|------|---------|
| spawn 子 agent 需父 transcript | 传 parent_sid + `resume_session` |
| agent 产出需被其他 agent 看到 | `working_memory_set` + Channel 传递 |
| 跨进程恢复对话（程序重启） | 持久化 session_id + `resume_session` |

> 🔑 **口诀**："spawn 即隔离，接力靠显式"

### 模式 5: 流式 Agent（llm act + on_chunk 回调）

**场景**：实时输出 LLM 响应

**v1.18**：`llm stream` 已删除（v1.14），`for await` 已删除（v1.18）。流式统一用 `llm act` + `on_chunk`。

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

StreamingWriter("The future of AI")
```

带完整回调的流式：

```helen
fn on_chunk(chunk: str) { stream_print(chunk) }
fn on_complete() { print("\n\n✅ 完成") }

agent StreamingWriter(topic: str) {
    main {
        llm act "Write article about " + topic on_chunk on_chunk on_complete on_complete
    }
}
```

#### 流式中断 (v1.18)

`on_chunk` 返回 `false` 提前终止。`spawn` + `Channel.cancel()` 中断后台 agent 流式：

```helen
fn conditional_chunk(chunk: str) {
    stream_print(chunk)
    if should_stop() { return false }  // 终止流式
}

let mailbox = spawn StreamingAgent("long task")
mailbox.cancel()  // 中断后台流式

cancel_llm_call(call_id)
取消大模型调用(call_id)  // 中文别名
```

### 模式 5B: 工具执行后注入提示（on_tool_end, v1.21）

**场景**：在 agentic loop 中，工具执行后引导 LLM 方向。

**签名**：`fn(tool_name: str, tool_result: str): str | dict | null`
- 返回 str → 注入为 `user` 消息（`[System Hint]` 前缀）
- 返回 dict → `{"role": "user"|"system", "content": "..."}`
- 返回 null → 不注入

注入的 hint 自动保存到 TranscriptStore。

```helen
agent Coder {
    tools ["write_file", "shell_exec", "read_file"]

    main {
        llm act "Create hello.py and run it"
            on_chunk fn(c) { stream_print(c) }
            on_tool_end fn(name, result) {
                if name == "write_file" {
                    return "文件已写入，下一步可以运行测试验证"
                }
                if name == "shell_exec" {
                    return {"role": "system", "content": "禁止执行 rm -rf 等危险命令"}
                }
                return null
            }
    }
}
```

**外部队列集成**：

```helen
agent Worker {
    tools ["read_file", "write_file"]
    main {
        llm act "完成分配的任务"
            on_tool_end fn(name, result) {
                let hint = get_hint_from_queue()
                return hint  // null 时不注入
            }
    }
}
```

`on_tool_end` 可与 `on_chunk` / `on_complete` 组合：

```helen
llm act "task"
    逐块处理 fn(c) { stream_print(c) }
    完成 fn() { print("\n✅ 完成") }
    工具结束 fn(name, result) { return "提示" }
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
    max-turns 15  // 允许多轮工具调用
    
    main {
        return llm act "Help me implement a REST API in Python"
    }
}
```

### 模式 7: 对话 Agent

**场景**：保持对话上下文的多轮对话

```helen
agent ConversationalAssistant {
    description "Multi-turn conversational assistant"
    prompt "You are a helpful assistant. Remember context from previous messages."
    
    main {
        let response = llm act "Remember this context"
        let followup = llm act "Based on what I said before, what do you think?"
        return followup
    }
}

// 在 REPL 中，对话历史自动维护；每次 :ask 都会记住之前的对话
```

---

## 高级模式

### 动态 Agent 选择

```helen
agent DynamicRouter(input: str) {
    description "Dynamically select agent based on input"
    
    main {
        let decision = llm act "Classify: tech, billing, or general. Input: " + input
        
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

### 配置驱动的 Agent（避免重复定义）

```helen
agent RoleAgent(topic: str, config: map) {
    description "可配置的角色 Agent"
    prompt """
    你是「{{config["name"]}}」。角色: {{config["description"]}}，风格: {{config["style"]}}
    分析: {{topic}}
    """
    main { return llm act }
}

let configs = [
    {"name": "乐观派", "description": "看到最好的一面", "style": "积极向上"},
    {"name": "悲观派", "description": "关注风险", "style": "谨慎保守"}
]
for config in configs {
    let result = RoleAgent("话题", config)
}
```

### 错误处理与重试

```helen
agent RobustAgent(task: str) {
    main {
        let max_retries = 3
        let attempt = 0
        
        while attempt < max_retries {
            try {
                return llm act task
            } catch LLMError as e {
                attempt = attempt + 1
                if attempt >= max_retries {
                    throw RuntimeError("Failed after " + str(max_retries) + " attempts: " + e.message)
                }
                sleep(2)
            }
        }
    }
}
```

#### Agent 调用失败（AgentError）

```helen
try {
    let result = Contractor(req, dir)
} catch AgentError err {
    // err.agent_name — "Contractor"
    // err.agent_args — {req: "...", dir: "..."}
    // err.cause      — 底层异常
    error("失败: " + err.message)
}
```

`AgentError` 继承 `LLMError`（`catch LLMError` 一并捕获）。嵌套调用时内层 AgentError 透传不双层包装。

---

## 最佳实践

| # | 实践 | ✅ 推荐 | ❌ 避免 |
|---|------|--------|--------|
| 1 | **description** | `"Review code for bugs, security, and best practices"` | `"Helps with stuff"` |
| 2 | **prompt** | 具体角色 + 步骤 + 输出格式 | `"You analyze things."` |
| 3 | **temperature** | 创造性 0.9 / 精确 0.2 / 平衡 0.7 | 一律 0.5 |
| 4 | **max-turns** | 简单问答 3 / 复杂任务 15 | 无限 |
| 5 | **tools** | 最小权限：`["read_file"]` | `["read_file","write_file","shell_exec","web_search"]` |
| 6 | **作用域** | `shared let` 跨 agent 共享值类型 | 期望模块 `let` 在 agent 中可见 |
| 7 | **ground truth** | 用 `{{}}` 注入环境事实 | 让 LLM 猜测 cwd/时间 |

### 关键原则：注入环境事实（`{{}}`）

> **Agent 不知道你没告诉它的。运行时事实必须注入——永远不要让 LLM 猜测。**

LLM 无法访问当前环境（时钟、cwd、OS、git 分支）。缺失这些事实时，模型会**自信地编造错误值**。

修复方法：**在 Helen 中解析事实，通过 `{{}}` 注入 prompt**。

```helen
// ✅ Ground truth 注入 — LLM 看到真实值
agent DevAgent(cwd: str) {
    prompt """
    You are a senior engineer in {{cwd}}.
    Time: {{now()}}  OS: {{os_name()}}
    Answer only based on these facts; if not provided, say so.
    """
    main { return llm act "Review the project" }
}

// ❌ Ground truth 缺失 — LLM 会编造
agent VagueAgent {
    prompt "You are a senior engineer. Help with code."
}
```

**按领域注入：**

| 领域 | 通过 `{{}}` 注入 |
|------|----------------|
| 编程 | `cwd`, `os_name()`, `shell_exec("git branch --show-current")` |
| 调度 | `now()`, `timezone()` |
| 文件操作 | 目录列表、绝对路径 |
| 数据库 | schema 摘要、连接目标 |
| 数据分析 | 行数、列名、样本行 |
| 多 agent 管道 | 上游输出、共享状态快照 |

**反模式：**
```helen
// ❌ 让 LLM "假设"环境事实 — 一旦 drift 就出错
prompt "Assume you are in /home/user/project on Linux."

// ❌ 把动态事实放在 description — 解析时固定，不是运行时
description "Agent for /home/rxx/helen"  // 静态！用 prompt + {{}}
```

---

## 调试技巧

```helen
main {
    trace_on()
    let result = MyAgent("test")
    let trace = get_trace()
    print("Trace: " + str(trace))
    trace_off()
}
```

REPL 命令：`:stats`（上下文统计）、`:transcript`（消息记录）、`:last_error`（最后错误）。

---

## 相关技能

- **helen-agent-collaboration** — 多 Agent 协作模式详解
- **helen-syntax** — Helen 语法参考（shared let、agent main 等）
- **helen-stdlib** — 上下文管理 API 完整参考（`context_stats`/`compress_context`/`pin_message` 等）
- **helen-testing** — Agent 测试策略

## 总结

Helen Agent 设计模式的核心：

1. 🎯 **调用者决定上下文** — 所有信息显式传递
2. 🔒 **作用域隔离** — agent main 默认隔离，通过装饰器调节
3. 📦 **invocation 隔离** — 每次 agent 执行独立 LLM 上下文
4. 🛠 **模式选择** — 专家/路由/管道/并发/流式/工具/对话
5. 📋 **最佳实践** — 清晰 description、最小权限工具、注入 ground truth

上下文管理 API（`compress_context`、`working_memory`、`pin_message` 等 24+ 函数）详见 `helen-stdlib`。

---

**最后更新**: 2026-07-24
**版本**: v1.22
