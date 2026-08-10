# Helen 调试能力演进路线图

**日期**：2026-08-11
**作者**：Claude（与用户协作设计评审）
**状态**：提案阶段，待决策
**关键词**：debugging, observability, trace, agent replay, AI-native, transcript

---

## 摘要

本文档评估 Helen 当前的调试体验，分析"外部指定行范围 trace"这一具体提案的价值，并从 AI 调试者视角给出一份按 ROI 排序的调试能力演进路线图。

**核心结论**：

1. 行范围 trace 是**有用但非紧急**的功能，价值取决于配套的基础能力（语句级 tracing）是否先就位。
2. Helen 当前调试体验在动态语言里属**中上**，但离"最好"有明显距离。
3. **真正的杠杆点是 AI 原生的调试能力**——这些是 Python/JS 调试器一辈子不会解决的问题域，Helen 有机会定义这个领域。
4. 优先推荐的三件事：**Agent 录制/重放**、**Agent 调用树可视化**、**错误上下文增强**。

---

## 第一部分：行范围 Trace 提案分析

### 1.1 用户原始提案

> "如果可以外部指定 interpreter 执行某个 helen 程序时在某行到某行打开 trace，并显示执行记录，对调试 Helen 程序有帮助吗？跟现在的 trace 功能差别大吗？"

即：支持 `helen --trace-lines 42-80 prog.helen` 这种形式，外部指定 trace 输出范围，不需要修改源码。

### 1.2 当前 trace 实现现状

**文件位置**：`helen/runtime/observability.py`

**架构**：

```
ObservabilityManager
├── CallStackTracker      # 调用栈追踪
├── ExecutionTracer       # 执行轨迹（本提案焦点）
│   ├── enabled: bool
│   ├── _entries: list[TraceEntry]   # 上限 10000
│   └── trace(event_type, span, data)
├── LLMAuditLog           # LLM 调用审计
└── CoverageTracker       # 测试覆盖率
```

**关键发现**：`ExecutionTracer` 设计了 `stmt/branch/call/return` 多种事件类型，但**实际解释器只 emit 了 4 个事件点**：

```
helen/interpreter/interpreter.py:1585  →  tracer.trace("call", ...)    函数入口
helen/interpreter/interpreter.py:1619  →  tracer.trace("return", ...)  函数出口
helen/interpreter/interpreter.py:1823  →  tracer.trace("call", ...)    agent 入口
helen/interpreter/interpreter.py:1946  →  tracer.trace("return", ...)  agent 出口
```

**结论**：现在的 trace 是**函数/agent 级别的 call graph**，不是语句级的执行追踪。没有循环迭代、变量赋值、分支走向、单行执行记录。

**暴露方式**：
- REPL：`:trace on|off|show [n]`
- stdlib：`trace_on()` / `trace_off()`
- 错误时：`:last_error -v` 包含最近 20 条 trace

### 1.3 行范围 trace 的价值分析

#### 价值分两层，必须拆开看

**层次 1：语句级 tracing（核心缺失）**

现状最缺的是在 `visit_*` 系列方法里给每条语句 emit 一个 `stmt` 事件，记录：
- 当前行号 / span
- 语句类型（赋值/调用/if/for/while/return/...）
- 关键变量快照（可选）

没有这个基础，只加"行范围过滤"几乎无用——事件本身只有函数进出，过滤了也只剩几行 call/return。

**层次 2：外部指定的行范围过滤（有价值的增强）**

在语句级 tracing 基础上，加 `--trace-lines 10-50` CLI 参数 / API。

#### 价值分布：AI vs 人类用户

| 维度 | 对 AI 调试者 | 对人类调试者 |
|---|---|---|
| 价值程度 | 边际提升 | 显著有用 |
| 使用频率 | 10-20% 场景 | 40-60% 场景 |
| 替代方案 | 精准 `print()` 通常更好 | 比 `print()` 好很多 |
| 关键优势 | 不改源码 | 不需要静态推理能力 |
| 关键劣势 | 输出吃上下文窗口 | 需要学习 |

**诚实评估**：

- **作为 AI**：80% 的场景我还是会用 `print()` / `debug()`，因为**信噪比更高、更贴合我正在思考的具体问题**。行范围 trace 产生原始日志，我最怕大量原始日志吃光上下文窗口。
- **对人类用户**：价值明显更高。人类没有 AI 的静态推理能力，行范围 trace 能让他们直观看到循环、分支、状态变化，比反复"改代码→重跑→看输出→再改"高效得多。

### 1.4 安全性分析

**核心风险**：变量值快照是敏感数据。

如果 trace 自动记录被 trace 行上的所有变量值：

```helen
let api_key = "sk-xxxx"        # 第 42 行
let user_token = load_token()  # 第 43 行
# ... 第 44-50 行 ...
helen --trace-lines 42-50 prog.helen
```

trace 输出里会包含 `api_key` 和 `user_token` 的明文。

**泄漏路径**：
1. trace 被 pip 到 log 文件 → 密钥泄露到磁盘
2. trace 被 REPL `:trace show` 打印到 terminal → 可能被截屏
3. trace 被作为 context 喂给 LLM（AI 调试的典型路径！）→ **密钥进入 prompt，可能被 logging 到 LLM provider**

**缓解方案（按成本递增）**：

| 方案 | 描述 | 成本 | 安全性 |
|---|---|---|---|
| A | 默认不记录变量值，只记录"执行了哪一行" | 低 | 高 |
| B | 显式 opt-in：`--with-values` 才记录变量 | 低 | 高 |
| C | 自动 redact：识别 `key/token/password/secret` 命名的变量 | 中 | 很高 |
| D | `@trace-ignore` 装饰器标注敏感变量 | 高 | 高，但风格不符 |

**建议**：底线是**默认不记录变量值**（方案 A）。

### 1.5 性能分析

**关闭时**：
- `if not self._enabled: return` 一行守卫，单次属性访问，纳秒级
- **零影响** ✅

**开启但无行范围过滤时**：
- 每条语句 emit：dict 构造 + 时间戳 + list append + 可能 `pop(0)` 移动 10000 个元素
- 对 Helen 这种解释型语言，**单条语句执行时间被拖长 10-100 倍**
- 紧循环（`for i in range(1000000)`）会从毫秒级变成秒级
- **风险**：用户会以为 Helen 很慢——口碑风险

**开启 + 行范围过滤时**：
- 在范围外的语句只做 enabled 检查（便宜）
- 在范围内的才做完整 emit
- **关键问题**：循环体在 trace 范围内，循环 10000 次照样炸

**必选的防护措施**：

1. **同线重复折叠**：同一行连续执行超过 N 次时自动折叠
   - 例：`line 45: 997 more times`
   - 保留第一次和最后一次的完整数据
2. **可配置上限**：单会话内最大 trace 条目数（现 10000，可调）
3. **采样模式**：`--trace-sample 1/100` 每 100 次记一次

**具体数字估算**：

| 模式 | 性能影响 | 可接受度 |
|---|---|---|
| 关闭 trace | 基线 | ✅ 生产可用 |
| 开启 + 行范围 + 折叠 | 目标代码段慢 5-10x | ✅ 调试可接受 |
| 开启 + 行范围 + 无限流 | 循环体慢 100x+ | ❌ 不可接受 |
| 开启 + 无行范围 | 整体慢 10-50x | ❌ 不可接受 |

### 1.6 行范围 trace 总结

**结论**：

- 有用但非紧急，**不是 Helen 调试体系的杠杆点**
- 依赖前置条件（语句级 tracing）才能发挥价值
- 安全和性能问题可控，但必须设计防护
- 对人类用户价值 > 对 AI 用户价值

---

## 第二部分：Helen 调试现状评估

### 2.1 现有调试能力清单

| 能力 | 机制 | 强度 |
|---|---|---|
| 结构化错误快照 | `:last_error [-v]` + `ErrorSnapshot` | ✅ 强 |
| 函数级 call trace | `trace_on/off` + `:trace` | 中 |
| LLM 调用审计 | `:llm_log` + `LLMAuditLog` | ✅ 强 |
| 测试覆盖率 | `coverage_on/off/report` | ✅ 强 |
| Agent 会话 transcript | `:transcript` + `TranscriptStore` | ✅ 强（基础设施） |
| 会话管理 | `:sessions / :session_id` | ✅ 完整 |
| 调用树完整性 | v1.24 resume_session + visibility markers | ✅ 强 |
| 子会话恢复 | v1.27 spawn resume | ✅ 强 |
| 语句级 trace | — | ❌ 缺失 |
| 断点 / 单步 | — | ❌ 缺失 |
| Watch 表达式 | — | ❌ 缺失 |
| Agent 录制 / 重放 | — | ❌ 缺失 |
| Agent 调用树可视化 | — | ❌ 缺失 |
| Prompt 行为对比 | — | ❌ 缺失 |

### 2.2 评估结论

**强项**：AI 原生的可观测性（transcript、llm_log、error snapshot）已经做到相当深度。TranscriptStore 作为 SSOT 存储了所有消息，基础设施完备。

**弱项**：传统调试能力（step/break/watch）完全没有；**AI 原生调试能力**还有几个关键缺失（见下一节）。

**总体评分**：在动态语言里**中上**，AI 原生可观测性**领先**，但离"调试体验最好的语言"有距离。

---

## 第三部分：调试能力演进路线图

### 3.1 Tier 1：天天会用（最高优先级）

#### 3.1.1 Agent 录制 / 重放 ⭐⭐⭐

**痛点**：Helen 程序的核心逻辑大量依赖 `llm act`，而 LLM 是非确定性的。一个 bug 出现后**几乎无法复现**——同样的输入、同样的 prompt，LLM 可能给出不同响应。改了 prompt 想修 bug，不知道是真修好了还是运气好。

**设计**：

```helen
# 录制：agent 调用 LLM 时，把 request/response 对写盘
@record agent MyAgent {
    model: "qwen3.7-plus"
    main {
        llm act "..."
    }
}

# 重放：用录制的 LLM 响应，确定性重跑 agent 逻辑
@replay agent MyAgent from "session_abc" { ... }
```

**价值**：
- 复现 LLM 应用 bug（Helen 独有痛点，Python/JS 没有）
- prompt 回归测试——改了 prompt，跑一遍录制的 session，看行为是否一致
- CI 里稳定测试 agent——不再依赖 LLM 在线、不再 flaky

**实现成本**：中等（约 1 周）。TranscriptStore 已存所有消息，差一层"mock LLM runtime，回放历史响应"的适配器。

**差异化**：⭐⭐⭐⭐⭐ Python/JS 调试器一辈子也不会有这个，因为问题域不在那里。

#### 3.1.2 Agent 调用树可视化 ⭐⭐⭐

**痛点**：多 agent 系统出问题时，agent 之间的调用关系、每个 agent 的输入输出、哪个 agent 在哪一步跑偏——只能从 transcript 里人肉翻。

**设计**：

```
$ helen agent-tree session_xyz

MyAgent (root)
├── Researcher (230ms, 3 tool calls)
│   ├── web_search("helen lang") → 5 results
│   ├── web_fetch("...") → ok
│   └── llm_act → "summary..."
├── Coder (input_tokens=1200, output=450)
│   ├── llm_act → [代码生成]
│   └── write_file("main.helen") → ok
└── Reviewer (status=ERROR)
    └── RuntimeError: line 42: expected list, got str
        ↳ Input was: {"data": "..."} from Coder output
```

**价值**：AI 应用调试的核心视图，类似于传统调试里的 call graph + profiler 合体。

**实现成本**：低（3-5 天）。TranscriptStore 数据现成，差可视化层。

**差异化**：⭐⭐⭐⭐ 同样是 Helen 的应有权。

#### 3.1.3 错误上下文增强 ⭐⭐⭐

**痛点**：`RuntimeError: expected list, got str` 有位置、有 call stack，但**不知道程序在做什么**——那个 str 是怎么来的？走了哪条分支才到这里？

**设计**：
- 错误里附带**最后几个关键变量的值**（不只是当前 scope，而是数据流上的上游值）
- **错误路径回溯**："这个 str 来自第 35 行的 `json_parse`，原始输入是 `\"hello\"`（缺少外引号）"
- **建议**："你是不是想用 `json_parse_lenient`？"（Helen 已有 fuzzy match 基础）

**价值**：
- 对人类：直接看到问题根因
- 对 AI：**最有价值**——能直接从错误里拿到上下文，不用再去翻源码

**实现成本**：低（2-3 天）。在现有 `ErrorSnapshot` 里加数据流回溯。

**差异化**：⭐⭐⭐ 通用语言也能做，但 Helen 做起来更自然。

### 3.2 Tier 2：定期会用

#### 3.2.1 REPL 里的 Watch 表达式 / 断点

```
helen repl> watch x > 10      # 当 x > 10 时暂停
helen repl> watch len(items)  # 显示每次变化
helen repl> break 42          # 第 42 行断点
helen repl> step              # 单步
helen repl> inspect           # 当前 scope 全部变量
```

**价值**：用户体验提升巨大，尤其对人类用户。
**成本**：高（几周，要改 interpreter 控制流、加断点钩子）。
**建议**：重要但不紧急，放在 Tier 2。

#### 3.2.2 Transcript 事后回放（Post-mortem）

```
helen replay session_xyz --interactive
```

进入交互式回放器，**时间旅行**般逐步看 agent 状态变化：这条消息发出后 scope 长什么样、哪个变量变了、tool 调用的输入输出。

**价值**：数据都已在 TranscriptStore，差一个 UI。
**成本**：中等。

#### 3.2.3 契约断言（Contract assertions）

```helen
for item in items {
    @invariant item.price > 0
    @invariant item.name != ""
    # ... 业务逻辑 ...
}

fn process(x): int 
    @requires x > 0
    @ensures result >= 0
{
    ...
}
```

**价值**：错误发生时告诉你**哪个 invariant 失败了**、在哪次迭代。对复杂循环和 agent 函数的 precondition/postcondition 验证特别有用。
**成本**：中等。

### 3.3 Tier 3：特定场景下有用

#### 3.3.1 Prompt 行为 Diff

```
helen prompt-diff agent=Reviewer prompt_v1.helen prompt_v2.helen test_inputs.json
```

跑同一组输入，对比两次 prompt 下 agent 行为差异。对 **prompt 工程**是杀手级工具。

#### 3.3.2 Tool 调用 Profiling

```
$ helen profile myagent.helen

Tool Calls:
  web_search: 12 calls, avg 320ms, p95 1200ms, 1 failures
  read_file:  34 calls, avg 12ms, p95 45ms
  llm_act:    8 calls, avg 2100ms, 14200 tokens total
```

性能调试用。TranscriptStore + LLM audit log 有全部数据，差聚合视图。

#### 3.3.3 行范围 Trace（原提案）

在 Tier 1 的语句级 tracing 基础上实现，否则价值有限（见第一部分）。

---

## 第四部分：Helen 独有的调试机会

Helen 作为 AI 原生语言，有些调试痛点是 Python/JS 没有的——**这些才是差异化的地方**：

| 痛点 | 传统语言有吗 | Helen 能做 | 优先级 |
|---|---|---|---|
| LLM 非确定性导致 bug 无法复现 | ❌ | ✅ agent 录制/重放 | Tier 1 |
| Prompt 改了行为漂移 | ❌ | ✅ prompt behavior diff | Tier 3 |
| Agent 之间传递信息丢字段 | ❌ | ✅ agent IO schema validation | Tier 2 |
| Tool 调用失败 cascade | 部分 | ✅ tool failure propagation view | Tier 2 |
| LLM 输出格式不符合预期 | ❌ | ✅ output contract 检查 | Tier 2 |

**战略洞察**：这些功能 Python 调试器一辈子也不会有，因为问题域不在那里。Helen 应该把这些做到极致，而不是去和 pdb 比 step-through。**定义新领域 > 进入成熟领域竞争**。

---

## 第五部分：具体建议

### 5.1 如果只做 3 件事（按 ROI 排序）

1. **Agent 录制/重放**（约 1 周）
   - 基础设施已就位，差异化最大，对 AI 和人类都有用
   - Helen 作为 AI 原生语言的"应有权"

2. **Agent 调用树可视化**（3-5 天）
   - TranscriptStore 数据现成
   - 立刻让多 agent 调试从"翻日志"变"看地图"

3. **错误上下文增强**（2-3 天）
   - 在现有 `ErrorSnapshot` 里加数据流回溯
   - 对 AI 调试帮助最直接

**这三件事做完，Helen 的调试体验会在 AI 应用这个细分领域显著超过任何通用语言工具。**

### 5.2 关于传统调试器能力（breakpoint/step/watch）

实现成本巨大（几周），且对 AI 调试帮助不大。

**建议**：不是说不做，而是优先级往后排。先做 Helen 独有的 AI 原生调试能力，建立差异化；传统调试能力作为后续完善。

### 5.3 关于原提案（行范围 trace）

- **不反对做**，但应该在语句级 tracing 先就位后做
- **不要单独做**——只加行范围过滤而不升级 granularity，等于在只有 call/return 的稀疏日志上加放大镜
- 位置：Tier 3，在 Tier 1 三件事之后做

---

## 第六部分：附录

### A. 现有调试相关代码位置

| 模块 | 文件 | 主要职责 |
|---|---|---|
| Observability | `helen/runtime/observability.py` | `ObservabilityManager`, `ExecutionTracer`, `CallStackTracker`, `ErrorSnapshot`, `LLMAuditLog` |
| TranscriptStore | `helen/runtime/transcript_store.py` | SSOT 消息存储，SQLite/JSONL 后端，UUID 寻址 |
| REPL | `helen/cli/repl.py` | `:trace`, `:last_error`, `:llm_log`, `:transcript` 等命令 |
| stdlib trace | `helen/stdlib/__init__.py:489-511` | `trace_on()`, `trace_off()` |
| Interpreter trace 点 | `helen/interpreter/interpreter.py:1585,1619,1823,1946` | 函数/agent 进出 |

### B. 相关版本历史

- v1.16: TranscriptStore SSOT
- v1.24: resume_session 可见性标记 + 调用树完整性
- v1.27: spawn resume 子会话恢复
- v1.29: agent 级 transcript 控制
- v1.30: working_memory 流式泄漏修复

### C. 相关 Memory 文件

- `helen-v1.24-update.md`：resume_session 改进
- `helen-v1.27-update.md`：spawn resume
- `helen-v1.29-update.md`：agent transcript 控制
- `helen-v1.30-1-bugfixes.md`：working_memory 修复

---

## 第七部分：决策点

### 需要用户决策的问题

1. **是否做 Agent 录制/重放？** 这是最大的差异化机会，但需要明确产品定位（Helen 是语言还是 AI 应用开发平台？）
2. **Agent 调用树可视化的形态？** CLI 工具 vs REPL 命令 vs Web UI？
3. **错误上下文增强的范围？** 只加变量值，还是做完整的数据流回溯？
4. **行范围 trace 是否进入近期路线图？** 建议延后，但如用户坚持可提前。

### 建议的下一步

1. 用户 review 本文档，确认方向
2. 选定 1-2 个 Tier 1 项目进入 plan mode
3. 出具体实现计划（API 设计、数据模型、测试策略）
4. 实施 + 用户验收

---

**文档结束**

*本报告由 Claude 与用户协作生成，基于对 Helen 当前调试基础设施的代码分析。*
