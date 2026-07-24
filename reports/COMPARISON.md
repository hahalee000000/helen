# Helen vs 其他 Agent 框架：何时选择 Helen？

## 快速决策指南

### 选择 Helen，如果你需要：
- ✅ **Agent 即语言构造**：不是库模式，Agent 是一等公民
- ✅ **双语支持**：原生中英文编程，89 个双语关键字
- ✅ **自动上下文管理**：5 层渐进压缩 + 工作记忆，无需手工调优
- ✅ **完整 DSL**：变量、函数、控制流 + LLM 原语融合
- ✅ **多 Agent 并发**：spawn + Channel 消息队列
- ✅ **会话持久化**：TranscriptStore SSOT，SQLite/JSONL 后端

### 选择 LangChain，如果你需要：
- ✅ 大量预构建 chain 和 tool
- ✅ 成熟的生态系统
- ✅ 复杂的 RAG 管道
- ❌ 不介意样板代码和调试困难

### 选择 CrewAI，如果你需要：
- ✅ 快速搭建多 Agent 团队
- ✅ 基于角色的 Agent 设计
- ✅ 简单的任务委派模式
- ❌ 不需要深度定制 Agent 行为

### 选择 AutoGen，如果你需要：
- ✅ 多 Agent 对话模式
- ✅ 灵活的 Agent 协作拓扑
- ✅ 代码执行能力
- ❌ 不介意复杂的配置

---

## 详细对比

### Helen vs LangChain

| 特性 | Helen | LangChain |
|------|-------|-----------|
| **Agent 定义** | 语言级构造 `agent` | Python 类 + 装饰器 |
| **学习曲线** | 低（类 Python 语法） | 高（大量抽象概念） |
| **上下文管理** | 自动（5 层压缩） | 手动（需配置 memory） |
| **双语支持** | ✅ 原生中英文 | ❌ 仅英文 |
| **调试体验** | 优秀（REPL + Transcript） | 困难（链式调用难追踪） |
| **代码量** | 少（DSL 抽象） | 多（样板代码） |
| **并发模型** | spawn + Channel | 需手动实现 |
| **会话持久化** | 内置 TranscriptStore | 需集成外部存储 |

**何时选 Helen**：
- 需要快速原型开发
- 团队成员不熟悉 Python 高级特性
- 需要中文编程支持
- 重视调试和可观测性

**何时选 LangChain**：
- 需要大量预构建组件
- 复杂的 RAG 场景
- 已有 LangChain 生态投资

---

### Helen vs CrewAI

| 特性 | Helen | CrewAI |
|------|-------|--------|
| **Agent 模型** | 语言级 + 工具 | 角色 + 任务 + 工具 |
| **协作模式** | Channel 消息传递 | 任务委派链 |
| **上下文共享** | 显式（shared store） | 隐式（任务传递） |
| **自定义程度** | 高（完整 DSL） | 中（配置驱动） |
| **并发控制** | 细粒度（spawn + Channel） | 粗粒度（顺序/并行） |
| **学习曲线** | 低 | 低 |

**何时选 Helen**：
- 需要复杂的 Agent 协作逻辑
- 需要细粒度并发控制
- 需要自定义 Agent 行为
- 需要会话持久化和审计

**何时选 CrewAI**：
- 快速搭建简单的多 Agent 系统
- 角色分工明确的场景
- 不想学习新语言

---

### Helen vs AutoGen

| 特性 | Helen | AutoGen |
|------|-------|---------|
| **Agent 定义** | `agent` 关键字 | Python 类 |
| **对话模式** | 内置上下文管理 | 对话历史管理 |
| **代码执行** | 内置 shell_exec | 内置代码执行器 |
| **多 Agent 拓扑** | Channel 消息队列 | 灵活配置 |
| **人机协作** | 通过 prompt 设计 | 内置 HumanProxyAgent |
| **配置复杂度** | 低（YAML） | 中-高 |

**何时选 Helen**：
- 需要完整的编程语言特性
- 需要双语支持
- 重视代码简洁性
- 需要自动上下文压缩

**何时选 AutoGen**：
- 需要复杂的多 Agent 对话
- 需要代码执行沙箱
- 需要人机协作模式

---

## Use Case 示例

### 1. 客服机器人系统

**推荐 Helen**，如果你需要：
- 多轮对话上下文自动管理
- 会话记录审计
- 中英文双语客服
- 快速迭代 Agent 逻辑

```helen
agent CustomerService {
    description "智能客服助手"
    tools ["search_knowledge_base", "create_ticket"]
    
    main {
        llm act "回答用户问题"
            on_tool_end fn(name, result) {
                if name == "search_knowledge_base" {
                    return "找到了相关知识，请基于此回答用户"
                }
            }
    }
}
```

### 2. 数据分析助手

**推荐 Helen**，如果你需要：
- 复杂的数据处理管道
- 多 Agent 协作（数据清洗、分析、可视化）
- 自动上下文压缩（长数据分析过程）
- 会话回放和审计

```helen
agent DataAnalyst {
    tools ["read_csv", "execute_sql", "create_chart"]
    
    main {
        llm act "分析数据并生成报告"
            on_tool_end fn(name, result) {
                if name == "execute_sql" {
                    return "查询完成，请分析结果并生成可视化"
                }
            }
    }
}
```

### 3. 代码审查助手

**推荐 Helen**，如果你需要：
- 多文件上下文管理
- 工具调用历史追踪
- 自动压缩长对话
- 中文代码注释支持

```helen
agent CodeReviewer {
    tools ["read_file", "search_code", "create_comment"]
    
    main {
        llm act "审查代码变更"
            on_chunk fn(chunk) { stream_print(chunk) }
            on_tool_end fn(name, result) {
                if name == "read_file" {
                    return "文件已读取，请分析代码质量和潜在问题"
                }
            }
    }
}
```

---

## 迁移指南

### 从 LangChain 迁移

**概念映射**：
- `Chain` → Helen 的 `agent main {}`
- `Memory` → Helen 的自动上下文管理
- `Tool` → Helen 的 `tools` 声明
- `Agent` → Helen 的 `agent` 关键字

**迁移步骤**：
1. 将 Chain 逻辑转换为 Helen agent
2. 移除手动 memory 管理代码
3. 将 Tool 声明为 Helen 函数
4. 使用 REPL 测试和调试

### 从 CrewAI 迁移

**概念映射**：
- `Crew` → 多个 Helen agent + spawn
- `Agent` → Helen `agent`
- `Task` → agent 的 `prompt` + `main`
- `Tool` → Helen `tools`

**迁移步骤**：
1. 将每个 CrewAI Agent 转换为 Helen agent
2. 使用 `spawn` 实现并发
3. 使用 Channel 实现任务传递
4. 添加 `on_tool_end` 优化 Agent 行为

---

## 常见问题

### Q: Helen 适合生产环境吗？
A: Helen 目前处于 Beta 阶段（v1.21），已有 2946 个测试通过。适合原型开发和中小规模应用。大规模生产环境建议先在测试环境验证。

### Q: Helen 性能如何？
A: Helen 是解释型语言，性能低于编译型语言。但对于 LLM 应用，瓶颈在 API 调用而非语言本身。Helen 的自动上下文管理可以减少 token 消耗，降低成本。

### Q: 可以与现有 Python 代码集成吗？
A: 可以！Helen 支持：
- Python → Helen Bridge：在 Python 中调用 Helen Agent
- Helen → Python FFI：在 Helen 中调用 Python 库
- 直接导入 .helen 文件：`from my_agents import MyAgent`

### Q: 学习 Helen 需要多长时间？
A: 如果你熟悉 Python，1-2 天即可上手。Helen 语法类似 Python，核心概念只有：
- `agent`：定义 Agent
- `llm act`：调用 LLM
- `llm if`：LLM 路由
- `tools`：声明工具

### Q: Helen 支持哪些 LLM？
A: Helen 支持所有 OpenAI 兼容的 API：
- OpenAI GPT-4/3.5
- Anthropic Claude
- 阿里通义千问
- 本地模型（通过 Ollama/vLLM）

只需配置 `~/.helen/config.yaml`：
```yaml
llm:
  api_key: "your-key"
  base_url: "https://api.openai.com/v1"
  model: "gpt-4"
```

---

## 总结

**Helen 的核心优势**：
1. **Agent 即语言**：不是库模式，是语言级构造
2. **自动上下文管理**：无需手工调优，5 层渐进压缩
3. **双语支持**：原生中英文，降低学习门槛
4. **完整 DSL**：变量、函数、控制流 + LLM 原语
5. **优秀的调试体验**：REPL + Transcript + 可观测性

**不适合的场景**：
- 需要大量预构建组件（选 LangChain）
- 超大规模生产环境（等待更成熟版本）
- 纯 RAG 场景（Helen 更擅长 Agent 编排）

**立即开始**：
```bash
pip install helen-lang
helen repl
```

访问 [GitHub](https://github.com/hahalee000000/helen) 了解更多示例和文档。
