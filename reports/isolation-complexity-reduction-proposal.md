# Helen 隔离性 vs 编程复杂度 — 减负方案

**日期**：2026-07-20
**背景**：Helen v1.10-v1.23 逐步强化 agent 隔离性，编程复杂度相应上升。本文提出分层减负方案，在**不削弱隔离性**的前提下降低用户负担。

---

## 🎯 核心原则

> **不削弱隔离性，只减少样板代码**
> 
> 让"正确的做法"更容易写出来，而不是让"错误的做法"成为可能。

---

## 📊 复杂度来源分析

| 来源 | 症状 | 用户感受 |
|------|------|---------|
| 每次调用 agent 都要显式传所有参数 | 参数列表冗长 | "太啰嗦" |
| spawn 后 transcript 隔离 | 需要 `resume_session` 才能共享 | "为什么不能自动继承？" |
| 多 agent 数据交换要用 shared store 或 Channel | 模式选择困难 | "哪种方式对？" |
| 跨进程恢复要持久化 session_id | 样板代码 | "为什么这么麻烦？" |
| LLM 看到的最小上下文需要手动筛选 | 设计负担 | "我该传什么？" |

**关键洞察**：复杂度没有消失，只是从**设计时**转移到了**调试时**。强隔离把复杂度**显式化**了——你必须面对它，而不是被它偷袭。

---

## 📊 方案总览

| 优先级 | 方案 | 减负程度 | 实施成本 | 风险 |
|--------|------|---------|---------|------|
| **P0** | 错误提示改进 | ⭐⭐ | 低 | 无 |
| **P0** | 文档模板库 | ⭐⭐ | 低 | 无 |
| **P1** | stdlib 组合子 | ⭐⭐⭐⭐ | 中 | 低 |
| **P1** | Context 对象模式 | ⭐⭐⭐ | 低 | 低 |
| **P2** | Transcript 继承选项 | ⭐⭐⭐ | 中 | 中 |
| **P2** | 声明式上下文需求 | ⭐⭐⭐⭐ | 高 | 中 |
| **P3** | 调试工具链 | ⭐⭐⭐⭐ | 高 | 低 |
| **P3** | Agent Context Propagation | ⭐⭐⭐⭐⭐ | 高 | 高 |

---

## 🟢 P0：立即做（1-2 周）

### 方案 1：错误提示智能化

**问题**：用户访问不可见变量时，只得到"undefined variable"，不知道怎么办。

**现状**：
```
Error: undefined variable 'user_data'
  --> main.helen:5:12
```

**改进后**：
```
Error: undefined variable 'user_data'
  --> main.helen:5:12

💡 'user_data' is a module-level `let`, which is NOT visible inside agent main.
   This is by design — Helen agents are strictly isolated.

   How to fix:
   1. Pass as parameter (recommended):
      agent Worker(user_data: dict) { ... }
      main { Worker(user_data) }

   2. Make it a const (read-only sharing):
      const USER_DATA = {...}

   3. Use shared let (mutable, cross-agent):
      shared let user_data = {...}

   4. Pass via Channel message:
      ch.send(user_data)

   See: helen-agent-collaboration §"调用者决定上下文"
```

**实现要点**：
- 在 semantic analyzer 报错时，检查变量在哪个作用域定义
- 根据定义位置（module let / 外层 agent / 导入的模块）给出不同建议
- 附上相关文档链接

**代码位置**：`helen/semantic/analyzer.py` + `helen/core/errors.py`

### 方案 2：内置模板库

**问题**：用户不知道常见场景该怎么写。

**方案**：在 stdlib 中提供一组"模式模板"，用户可以直接复制使用。

```helen
// stdlib 提供模板（不是真代码，是文档片段）
// 用户可以通过 helen doc --template <pattern> 查看

// 模板 1: 简单 agent 调用
template agent_simple {
    agent Worker(input: str) {
        main { return llm act "Process: " + input }
    }
    main { let result = Worker("hello") }
}

// 模板 2: spawn + Channel
template spawn_channel {
    agent Worker(task: str, ch: Channel) {
        main { ch.send("done: " + task) }
    }
    main {
        let m = spawn Worker("task")
        let result = m.receive()
    }
}

// 模板 3: spawn + transcript 继承
template spawn_with_transcript {
    agent Worker(task: str, parent_sid: str, ch: Channel) {
        main {
            resume_session(parent_sid)
            ch.send("done")
        }
    }
    main {
        let parent_sid = get_session_id()
        let m = spawn Worker("task", parent_sid)
    }
}

// 模板 4: SharedStore 数据交换
template shared_store {
    shared store DataStore { results: dict = {} }
    
    agent Producer(key: str, value: str) {
        main { DataStore.results[key] = value }
    }
    agent Consumer(key: str) {
        main { return DataStore.results[key] }
    }
}
```

**使用方式**：
```bash
helen template spawn_channel  # 打印模板代码
helen template --list          # 列出所有模板
```

---

## 🟡 P1：短期（1-2 个月）

### 方案 3：stdlib 组合子

**问题**：常见模式（管道、fan-out、重试）每次都要手写。

**方案**：在 stdlib 中提供一组组合子函数。

```helen
// ═══ 管道模式 ═══
// 顺序执行一系列 agent
let result = pipe([AgentA, AgentB, AgentC], initial_input)

// ═══ Fan-out 模式 ═══
// 对每个输入并行执行 agent
let results = fanout(Agent, [input1, input2, input3])

// ═══ Map-Reduce ═══
let final = map_reduce(Worker, inputs, fn(results) { merge(results) })

// ═══ 带重试 ═══
let result = with_retry(Agent, input, max_retries=3, on_error=fn(e) { ... })

// ═══ 带超时 ═══
let result = with_timeout(Agent, input, timeout_ms=5000)

// ═══ 管道 + 重试 + 超时组合 ═══
let result = pipe(
    [AgentA, with_retry(AgentB, _, 3), with_timeout(AgentC, _, 5000)],
    input
)
```

**实现思路**：
```python
# stdlib/pipeline.py

def pipe(agents, initial_input):
    """Sequentially pass output of one agent as input to next."""
    current = initial_input
    for agent in agents:
        current = agent(current)
    return current

def fanout(agent, inputs):
    """Run agent in parallel for each input using spawn."""
    channels = [spawn agent(x) for x in inputs]
    return [ch.receive() for ch in channels]

def with_retry(agent, input, max_retries=3, on_error=None):
    """Retry agent on failure."""
    for attempt in range(max_retries):
        try:
            return agent(input)
        except Exception as e:
            if on_error:
                on_error(e, attempt)
            if attempt == max_retries - 1:
                raise
```

**关键设计**：
- 组合子是普通函数，不是语法扩展
- 保持显式传递原则——用户仍然能看到数据流
- 可以任意组合（`pipe` 里嵌套 `with_retry`）

### 方案 4：Context 对象模式

**问题**：agent 参数列表太长，每次传递一堆相关数据。

**方案**：用 Context 对象聚合相关参数。

```helen
// ═══ 定义 Context 类型 ═══
type AppContext {
    user: User
    config: Config
    session_id: str
}

// ═══ Agent 接收 Context 而不是散参数 ═══
agent Processor(ctx: AppContext) {
    main {
        let user = ctx.user
        let config = ctx.config
        // 使用 ctx.xxx 而不是散参数
        return llm act "Process for user " + user.name
    }
}

// ═══ 调用时构建 Context ═══
main {
    let ctx = AppContext {
        user: load_user(),
        config: load_config(),
        session_id: get_session_id()
    }
    Processor(ctx)  // 一个参数搞定
}
```

**进阶：Context 扩展**

```helen
// 可以扩展 Context（类似 middleware）
let ctx = AppContext { user: u, config: c, session_id: s }
let enriched_ctx = ctx.with_trace_id(generate_trace_id())

// 可以部分覆盖
let ctx2 = ctx { user = other_user }  // 只改 user，其他保持
```

**关键点**：
- 不破坏隔离性——Context 仍然是显式传递
- 减少参数列表长度
- Context 对象可序列化，便于跨 agent/跨进程传递

---

## 🟠 P2：中期（3-6 个月）

### 方案 5：Transcript 继承选项

**问题**：spawn 后 transcript 隔离，需要手动 `resume_session`。

**方案**：提供可选的 transcript 继承。

```helen
// ═══ 当前：手动继承 ═══
main {
    let parent_sid = get_session_id()
    let m = spawn Worker("task", parent_sid)
}

agent Worker(task: str, parent_sid: str, ch: Channel) {
    main {
        resume_session(parent_sid)  // 手动恢复
        // ...
    }
}

// ═══ 提议：语法糖 ═══
main {
    // inherit_transcript=true 自动传递 session_id 并恢复
    let m = spawn Worker("task", inherit_transcript=true)
}

agent Worker(task: str, ch: Channel) {
    // 不需要声明 parent_sid 参数
    // transcript 自动继承
    main { ... }
}
```

**实现思路**：
```python
# interpreter/interpreter.py - visit_spawn_expr

def visit_spawn_expr(self, node):
    # ... 现有逻辑 ...
    
    # 检查 inherit_transcript 选项
    if node.options.get("inherit_transcript"):
        parent_sid = self._agent_context.session_id
        # 注入到 spawn 的参数中
        arg_values.append(LiteralNode(value=parent_sid))
        # 在 spawned interpreter 初始化时自动 resume
        spawned_interp._auto_resume_session = parent_sid
```

**权衡**：
- ✅ 减少样板代码
- ⚠️ 可能让新手困惑（"我的 transcript 怎么突然变了？"）
- ✅ 仍然是显式的（`inherit_transcript=true` 必须明确写）
- ✅ 不破坏隔离性——只是简化了常见的 transcript 继承模式

### 方案 6：声明式上下文需求

**问题**：agent 需要什么上下文是固定的，但每次调用都要手动传。

**方案**：让 agent 声明它需要什么，调用者自动满足。

```helen
// ═══ Agent 声明需求 ═══
agent Processor {
    requires [user: User, config: Config]
    
    main {
        // user 和 config 自动可用
        return llm act "Process for " + user.name
    }
}

// ═══ 调用时自动匹配 ═══
main {
    let user = load_user()
    let config = load_config()
    
    Processor()  // 自动从当前作用域匹配 user 和 config
}
```

**实现思路**：
```python
# semantic/analyzer.py

def analyze_agent_requires(self, agent_node):
    # 收集 requires 声明
    required_vars = []
    for req in agent_node.requires:
        required_vars.append((req.name, req.type))
    
    # 记录到 agent 元数据
    agent_node.required_context = required_vars

# interpreter/interpreter.py - _call_agent

def _call_agent(self, agent, args):
    # 自动填充 requires 声明的变量
    for var_name, var_type in agent.required_context:
        if var_name not in args:
            # 从调用者作用域查找
            try:
                value = self.environment.lookup(var_name)
                args[var_name] = value
            except NameError:
                raise Error(f"Required context '{var_name}' not found in caller scope")
    
    # 正常调用
    ...
```

**权衡**：
- ✅ 大幅减少样板代码
- ⚠️ 有点像隐式传递（但范围有限，只在 requires 声明内）
- ✅ 仍然是显式的——agent 必须声明它需要什么
- ⚠️ 可能导致"魔法"行为——需要清晰的错误提示

**安全约束**：
- requires 只能匹配**当前作用域的变量**（不会向上追溯多层）
- requires 不能匹配**模块级 let**（只能匹配 const、shared let、局部变量）
- 匹配失败时给出明确的错误提示

---

## 🔴 P3：长期探索（6 个月+）

### 方案 7：调试工具链

**工具 1: `helen trace`**

可视化 agent 调用链和数据流：

```bash
$ helen trace --session session_abc123

╭──────────────────────────────────────────────────────────╮
│ Agent Call Graph                                         │
├──────────────────────────────────────────────────────────┤
│ Main                                                     │
│ ├─ user_data: {name: "Alice", ...}                       │
│ ├─ config: {timeout: 30, ...}                            │
│ │                                                        │
│ └─► Processor(user_data, config)                         │
│     ├─ received: user_data, config                       │
│     ├─ llm act: "Process for Alice..."                   │
│     └─ returned: "Processed!"                            │
│                                                          │
│     └─► Worker(task="analyze")  [spawn]                  │
│         ├─ received: task                                │
│         ├─ transcript: session_def456 (inherited)        │
│         └─ returned: "Analysis done"                     │
╰──────────────────────────────────────────────────────────╯
```

**工具 2: `:context` REPL 命令**

查看当前 agent 的上下文：

```
helen> :context

Current Agent: Processor
├─ Parameters:
│  ├─ user: {name: "Alice", id: 42}
│  └─ config: {timeout: 30}
├─ Working Memory:
│  ├─ task: "Process for Alice"
│  ├─ active_files: ["main.py", "utils.py"]
│  └─ decisions: ["Modified main.py"]
├─ Transcript:
│  └─ session_id: session_abc123
│  └─ message_count: 12
└─ Invocation:
   └─ inv_id: inv_1720435200_abcd1234
```

**工具 3: `:dataflow` REPL 命令**

追踪数据如何在 agent 间流动：

```
helen> :dataflow user_data

Data Flow for 'user_data':
  [Defined] main.helen:5  let user_data = load_user()
      │
      ▼
  [Passed] main.helen:10  Processor(user_data, config)
      │
      ▼
  [Used] Processor:15  llm act "Process for " + user_data.name
      │
      ▼
  [Passed] Processor:20  spawn Worker(user_data)
      │
      ▼
  [Used] Worker:8  print(user_data.id)
```

### 方案 8：Agent Context Propagation（类似 React Context）

**问题**：某些上下文（user、config）需要穿透多层 agent，但显式传递很啰嗦。

**方案**：提供类似 React Context 的机制，让特定数据自动向下传递。

```helen
// ═══ 定义 Context ═══
provide UserContext {
    user: User
    trace_id: str
}

// ═══ 使用 Context ═══
agent DeepNestedAgent {
    main {
        let user = use UserContext.user     // 自动获取
        let trace_id = use UserContext.trace_id
        // 不需要参数传递
    }
}

// ═══ 提供 Context ═══
main {
    let user = load_user()
    let trace_id = generate_trace_id()
    
    // 在这个 block 内，所有 agent 都能访问 UserContext
    provide UserContext(user=user, trace_id=trace_id) {
        AgentA()
        AgentB()
        DeepNestedAgent()  // 自动获得 UserContext
    }
}
```

**权衡**：
- ✅ 大幅减少"穿透多层"的参数传递
- ⚠️ 有点像隐式传递（但范围可控）
- ✅ 仍然是显式的——必须用 `use` 关键字明确获取
- ⚠️ 可能导致"Context 地狱"——需要严格限制 Context 的使用场景

**适用场景**：
- 跨多层的全局配置（user、config、trace_id）
- 不适合用于业务数据（应该用参数传递）

---

## 🎯 实施路线图

### 第一阶段（1-2 周）：快速见效

✅ **方案 1**：错误提示智能化
✅ **方案 2**：内置模板库

这两个方案成本极低，但能立即帮助用户理解 Helen 的设计哲学。

### 第二阶段（1-2 个月）：减少样板

✅ **方案 3**：stdlib 组合子
✅ **方案 4**：Context 对象模式

这两个方案能显著减少常见模式的样板代码，且不破坏隔离性。

### 第三阶段（3-6 个月）：高级特性

✅ **方案 5**：Transcript 继承选项
✅ **方案 6**：声明式上下文需求（谨慎实施）

这两个方案引入了更多"魔法"，需要仔细设计和充分测试。

### 第四阶段（6 个月+）：工具链

✅ **方案 7**：调试工具链

长期投资，但对开发者体验至关重要。

### 暂不实施

⚠️ **方案 8**：Agent Context Propagation

这个方案虽然强大，但有引入"隐式传递"的风险。建议在方案 5/6 充分验证后再考虑。

---

## 💡 设计哲学反思

### 为什么强隔离是必要的？

1. **LLM 时代需要"最小上下文原则"**
   - LLM 看到的上下文越多，决策越不精准
   - 弱隔离 = LLM 看到一堆无关上下文 = 决策质量下降

2. **与工业界成熟模式一致**
   - Erlang/Elixir: "let it crash" + 进程完全隔离
   - Actor 模型: 消息传递而非共享内存
   - Microservices: 服务边界清晰 > 单体内部模块耦合

3. **复杂度转移而非增加**
   - 弱隔离下，复杂度没有消失，只是隐藏了
   - 强隔离把复杂度**显式化**——你写代码时就要想清楚数据流向
   - 这是经典的"shift left"——把复杂度从运行时移到设计时

### 减负的正确姿态

> **让"正确的做法"容易，让"错误的做法"困难**

- ❌ 削弱隔离性（让"错误做法"容易）
- ✅ 减少样板代码（让"正确做法"容易）

### 关键约束

| 要做的 | 不能做的 |
|-------|---------|
| 提供语法糖简化显式传递 | 引入隐式数据流 |
| 提供组合子抽象常见模式 | 破坏 agent 边界 |
| 提供工具增强可观测性 | 让用户忽视隔离原则 |
| 提供模板降低入门门槛 | 让用户写出不可维护的代码 |

---

## 📚 参考

- Helen v1.23.2 "调用者决定上下文" 设计原则
- Erlang/OTP 进程隔离模型
- React Context API（方案 8 的灵感来源）
- Barnum pipeline 组合子（方案 3 的参考）
- 12-Factor App 方法论（显式配置 > 隐式环境）

---

**下一步**：先实施 P0（错误提示 + 模板库），收集用户反馈后再推进 P1。
