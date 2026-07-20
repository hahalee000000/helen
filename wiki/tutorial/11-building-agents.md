# 教程 11: 构建多 Agent 系统

> 完整案例：从需求到实现

---

## ⚠️ 设计原则：调用者决定上下文

在进入案例之前，请牢记 Helen 多 agent 系统的核心设计原则：

> **Agent 是严格隔离的——调用前必须显式考虑要向 agent 提供什么上下文。**

多 agent 系统最常见的错误是**假设 agent 会自动看到外层的变量或历史**。在 Helen 中，这永远不会发生。

设计多 agent 系统时，请先画出**上下文流图**：

```
[调用者]
  │
  ├─── 参数 ────────────► [Agent A 需要的输入]
  │
  ├─── SharedStore 引用 ─► [Agent A 需要访问的共享状态]
  │
  └─── Channel ──────────► [Agent A 输出的结果流向]
```

**检查清单**：
- 每个 agent 完成任务**最少**需要哪些信息？
- 这些信息是否都通过参数或共享状态显式传递了？
- 不同 agent 之间**不应该**知道的上下文，是否真的隔离了？

> 💡 详见 [教程 05: 核心设计原则](05-agents.md#核心设计原则调用者决定上下文)

---

## 案例：智能客服系统

### 需求

构建一个智能客服系统，能够：
1. 理解用户问题
2. 分类问题类型
3. 根据类型调用不同专业 Agent
4. 生成满意回复

---

## 第一步：定义 Agent

```helen
// 问题分类器
agent QuestionClassifier {
    description "Classify customer questions into categories"
    model "gpt-4"
    temperature 0.1
    prompt """
    Classify the question into one of:
    - product: Questions about products or features
    - billing: Questions about pricing, invoices, payments
    - technical: Technical issues, bugs, errors
    - account: Account management, login, settings
    - general: Everything else
    """
}

// 产品专家
agent ProductExpert {
    description "Answer product-related questions"
    model "gpt-4"
    temperature 0.3
    prompt """
    You are a product expert. Answer questions about our products
    clearly and helpfully. If unsure, say so honestly.
    """
}

// 账单专家
agent BillingExpert {
    description "Handle billing inquiries"
    model "gpt-4"
    temperature 0.1
    prompt """
    You are a billing expert. Help customers with pricing, invoices,
    and payment issues. Be precise with numbers.
    """
}

// 技术支持
agent TechSupport {
    description "Provide technical support"
    model "gpt-4"
    temperature 0.2
    prompt """
    You are a technical support engineer. Help users resolve technical
    issues step by step. Ask clarifying questions if needed.
    """
}

// 回复润色器
agent ResponsePolisher {
    description "Polish responses to be friendly and professional"
    temperature 0.5
    prompt """
    Rewrite the response to be warm, professional, and helpful.
    Keep the technical accuracy but improve the tone.
    """
}
```

---

## 第二步：实现路由逻辑

```helen
main {
    let customer_question = "How do I reset my password?"

    // 第一步：分类
    llm if "Classify customer question" {
        branch "product" {
            print("📦 Product question")
            let answer = ProductExpert(customer_question)
        }
        branch "billing" {
            print("💰 Billing question")
            let answer = BillingExpert(customer_question)
        }
        branch "technical" {
            print("🔧 Technical question")
            let answer = TechSupport(customer_question)
        }
        branch "account" {
            print("👤 Account question")
            let answer = TechSupport(customer_question)
        }
        default {
            print("📋 General question")
            let answer = "Thank you for your question. Let me help you."
        }
    }

    // 第三步：润色回复
    let polished = ResponsePolisher(answer)

    // 第四步：输出
    print("\n--- Response to Customer ---")
    print(polished)
}
```

---

## 第三步：添加并发优化

```helen
// 知识库查询 agent — 接收 reply Channel 用于返回结果
agent KnowledgeBase(query: str, reply: Channel) {
    description "Search knowledge base"
    prompt "Search knowledge base for: {{query}}"
    main {
        let result = llm act "搜索知识库: " + query
        reply.send(result)
    }
}

// 历史查询 agent — 接收 reply Channel 用于返回结果
agent HistoryLookup(topic: str, reply: Channel) {
    description "Lookup relevant history"
    prompt "Find relevant history for: {{topic}}"
    main {
        let result = llm act "查找相关历史: " + topic
        reply.send(result)
    }
}

// 优化的版本：并发查询知识库（v1.18+ spawn 模式）
main {
    let question = "How do I reset my password?"

    // 并发获取上下文：spawn 返回 Channel
    let kb_mailbox = spawn KnowledgeBase(question)
    let history_mailbox = spawn HistoryLookup("password reset")

    // 从 Channel 接收结果
    let kb_result = kb_mailbox.receive()
    let history_result = history_mailbox.receive()
    let full_context = kb_result + "\n" + history_result

    // 先分类（串行，需要结果路由）
    llm if "Classify customer question" {
        branch "technical" {
            let answer = TechSupport(question + "\nContext: " + full_context)
        }
        default {
            let answer = "I'll help you with that."
        }
    }

    let polished = ResponsePolisher(answer)
    print(polished)
}
```

---

## 第四步：添加错误处理

```helen
main {
    let question = "How do I reset my password?"

    try {
        llm if "Classify customer question" {
            branch "technical" {
                let answer = TechSupport(question)
                let polished = ResponsePolisher(answer)
                print(polished)
            }
            default {
                print("I'll help you with that.")
            }
        }
    } catch TimeoutError err {
        print("⏱️ The service is taking too long. Please try again.")
    } catch RuntimeError err {
        print("⚠️ Something went wrong: " + str(err))
        print("A human agent will contact you shortly.")
    } catch {
        print("❌ An unexpected error occurred.")
        print("Please try again or contact support@company.com")
    }
}
```

---

## 第五步：优化上下文管理 (v1.15+)

Helen v1.15 引入了完整的上下文管理增强，可以为每个 agent 独立配置：

```helen
// 技术支持 agent：优化上下文管理
agent TechSupport {
    description "Provide technical support"
    model "gpt-4"
    
    // 上下文配置
    context {
        compression "graduated"      // 渐进压缩
        cache-aware true             // 缓存感知
        working-memory true          // 工作记忆
        working-memory-tokens 8000   // 更大的工作记忆
    }
    
    tools ["read_file", "web_search"]
    
    prompt """
    You are a technical support engineer. Help users resolve technical
    issues step by step.
    """
}

// 产品专家：简单的上下文配置
agent ProductExpert {
    description "Answer product questions"
    
    context {
        compression "none"           // 不压缩（短对话）
        working-memory false         // 禁用工作记忆
    }
    
    prompt """
    You are a product expert.
    """
}
```

### 上下文管理最佳实践

| Agent 类型 | 推荐配置 | 说明 |
|-----------|---------|------|
| 研究型 Agent | `compression "graduated"` + `working-memory true` | 长对话，需要跟踪文件 |
| 快速响应 Agent | `compression "none"` + `working-memory false` | 短对话，快速响应 |
| 多轮对话 Agent | `cache-aware true` + `working-memory-tokens 8000` | 提高缓存命中率 |

---

## 第六步：使用工作记忆 (v1.15+)

工作记忆自动跟踪 agent 执行过程中的关键信息：

```helen
// 辅助函数：修复代码
fn fix_code(code: str): str {
    // 实际的代码修复逻辑
    return code  // 简化示例
}

agent CodeReviewer {
    description "Review code changes"
    
    context {
        working-memory true  // 自动跟踪文件操作
    }
    
    tools ["read_file", "write_file", "patch_file"]
    
    functions {
        fn fix_code(code: str): str {
            // 实际的代码修复逻辑
            return code  // 简化示例
        }
    }
    
    main {
        // 自动跟踪：读取的文件
        let code = read_file("src/main.py")
        
        // 自动跟踪：修改的文件
        let fixed = fix_code(code)
        write_file("src/main.py", fixed)
        
        // LLM 现在知道哪些文件被修改了
        return llm act "Review the changes"
        // 工作记忆包含：
        // - 活跃文件: src/main.py
        // - 最近决策: Modified src/main.py
    }
}
```

---

## 第七步：监控上下文使用 (v1.15+)

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

---

## 第八步：多 Agent 协作模式（v1.18+）

在实际应用中，多个 Agent 经常需要**共享状态**或**相互通信**。Helen 提供两种机制：`shared store`（共享状态容器）和 **spawn + Channel**（消息通信）。

### 使用 Shared Store 共享状态

假设我们的客服系统需要跟踪所有会话的统计信息：

```helen
shared store SessionStats {
    let totalSessions: int = 0
    let resolvedSessions: int = 0
    let activeSessions: list = []
    
    fn startSession(sessionId: str) {
        totalSessions = totalSessions + 1
        activeSessions.append(sessionId)
    }
    
    fn endSession(sessionId: str) {
        resolvedSessions = resolvedSessions + 1
        activeSessions.remove(sessionId)
    }
    
    fn getResolutionRate(): str {
        if (totalSessions == 0) {
            return "0%"
        }
        let rate = resolvedSessions * 100 / totalSessions
        return str(rate) + "%"
    }
}

// Agent 接收 reply Channel 和 sessionId 参数
agent CustomerService(sessionId: str, question: str, reply: Channel) {
    description "Handle customer session"
    main {
        SessionStats.startSession(sessionId)
        
        // 处理客户问题...
        let response = llm act Assistant "Question: " + question
        
        SessionStats.endSession(sessionId)
        reply.send(response)
    }
}

// 多个 Agent 并发运行（v1.18+ spawn 模式）
let mb1 = spawn CustomerService("session-1", "How to reset password?")
let mb2 = spawn CustomerService("session-2", "Billing issue")
let mb3 = spawn CustomerService("session-3", "Technical support")

// 等待所有会话完成
let r1 = mb1.receive()
let r2 = mb2.receive()
let r3 = mb3.receive()

print("Resolution rate: " + SessionStats.getResolutionRate())
```

### 使用 Channel 传递消息

假设我们需要一个后台任务处理队列：

```helen
// 生产者 Agent：生成任务并通过 Channel 发送
agent TaskProducer(reply: Channel) {
    description "Produce tasks"
    main {
        reply.send("send-email-1")
        reply.send("send-email-2")
        reply.send("send-email-3")
        reply.send("done")  // 完成信号
    }
}

// 消费者 Agent：从 Channel 接收并处理任务
agent TaskConsumer(task: str, reply: Channel) {
    description "Consume tasks"
    main {
        print("Processing: " + task)
        // 处理任务...
        reply.send("completed: " + task)
    }
}

// 生产者并发运行
let producer_mb = spawn TaskProducer()

// 消费所有任务
let task = producer_mb.receive()
while (task != "done") {
    let consumer_mb = spawn TaskConsumer(task)
    let result = consumer_mb.receive()
    print(result)
    task = producer_mb.receive()
}
producer_mb.close()
```

### 协作模式选择

| 模式 | 适用场景 | 示例 |
|------|---------|------|
| **Shared Store** | 多个 Agent 读写同一份数据 | 统计计数器、缓存、配置 |
| **Channel（spawn）** | Agent 间传递消息/事件 | 任务队列、结果回报、信号 |

**最佳实践**：
- ✅ 用 `shared store` 管理**全局状态**（统计、配置、缓存）
- ✅ 用 `spawn` + Channel 实现**消息通信**（队列、事件、信号）
- ✅ 用 `mailbox_select` 监听多个 Channel 的结果
- ✅ Channel 自动注入为 Agent 最后一个参数，无需手动传递

---

## 项目结构

```
customer-service/
├── main.helen
├── agents/
│   ├── classifier.helen
│   ├── product_expert.helen
│   ├── billing_expert.helen
│   ├── tech_support.helen
│   └── polisher.helen
├── utils/
│   └── formatting.helen
└── config.json
```

---

## 运行与验证

```bash
# 验证
$ helen check customer-service/main.helen
✓ customer-service/main.helen: OK

# 运行
$ helen customer-service/main.helen
🔧 Technical question


--- Response to Customer ---
To reset your password, please follow these steps...

# 生成文档
$ helen doc customer-service/main.helen --format markdown
```

---

## 总结

通过这个案例，你学会了：
1. ✅ 声明多个 Agent 及其配置
2. ✅ 使用 `llm if` 进行智能路由
3. ✅ 使用 `spawn` + Channel 并发获取上下文
4. ✅ 使用 `try-catch` 处理 LLM 异常
5. ✅ 组织多文件项目结构

---

## 下一步

- 探索 LSP 在 IDE 中的补全和诊断功能
- 使用 `helen repl` 快速原型
- 阅读 [[../reference/agent-system-prompt-guide|Agent 提示词工程完全指南]] — 来自 Claude Code 逆向工程的 agent prompt 设计方法论
- 阅读 [[overview/design-philosophy|设计哲学]] 深入了解语言理念
- 查看 [[appendix/error-codes|错误码参考]] 排查问题
