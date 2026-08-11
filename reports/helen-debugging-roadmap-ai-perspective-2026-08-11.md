# Helen 调试路线图：AI 调试视角筛选

**日期**：2026-08-11
**作者**：Claude（基于 `helen-debugging-roadmap-2026-08-11.md` 的评审）
**状态**：决策已确认
**关键词**：AI-native debugging, replay, transcript query, data lineage

---

## 摘要

本文档基于 `helen-debugging-roadmap-2026-08-11.md` 路线图，以**"对 AI 调试者是否真正有用"**为单一标准重新筛选功能，剔除主要服务人类用户的功能，并补充原路线图遗漏的几个 AI 调试关键方向。

**核心主张**：

- 路线图 Tier 1 里的 **Agent 调用树可视化** 本质是给人看的，应替换为**结构化 transcript 查询 API**——同一份底层数据，对 AI 的效用差一个数量级。
- **录制/重放**是 AI 调试基础设施的核心拼图。
- **错误分类 + 诊断建议**比"错误上下文增强"高一个层级，是 AI 直接定位根因的关键。
- P0 三项做完后，AI 调试 Helen 就从"翻 transcript"升级为"精准查询 + 确定性重放 + 数据流回溯"。
- **关键约束**：功能做了不等于 LLM 会用。第七部分对每个功能做了 LLM 使用概率评估，区分 Push 模型（被动接收）vs Pull 模型（主动调用），并据此筛选功能——没有高概率使用方案的功能不予纳入。

---

## 第一部分：从路线图筛选

### ✅ 保留的功能

按对 AI 调试的价值从高到低排序：

| 功能 | 路线图 Tier | 对 AI 的价值 | 理由 |
|---|---|---|---|
| **Agent 录制/重放** | Tier 1 | ⭐⭐⭐⭐⭐ | LLM 非确定性 bug 复现问题，AI 调试者和人类调试者一样头疼。录制后确定性回放，AI 就能用二分法定位是哪条 prompt / 哪个工具调用出了问题。 |
| **错误上下文增强**（数据流回溯） | Tier 1 | ⭐⭐⭐⭐⭐ | 错误里带上"这个值从哪条语句来、上游是什么"，AI 直接从错误对象里拿上下文，省去反复翻 transcript 和源码。这是对 AI 价值比人类还高的少数功能。 |
| **Output contract 检查**（LLM 输出格式验证） | 第四部分表 | ⭐⭐⭐⭐ | Helen 独有的痛点：LLM 返回格式漂移。AI 调试时如果有 schema 校验失败，立刻知道是 LLM 输出问题而不是代码逻辑问题。 |
| **Transcript 事后回放** | Tier 2 | ⭐⭐⭐ | 用户明确要求保留。基础设施已就位（TranscriptStore），AI 可以程序化遍历消息序列复现/分析。是重放的底层数据。 |

### ❌ 丢弃的功能

| 功能 | 丢弃理由 |
|---|---|
| **Agent 调用树可视化** | 路线图自己写了"可视化"。AI 不需要树状图，需要的是结构化数据查询接口（例如 `trace_path` 那种 API）。可视化是给人看的。 |
| **REPL watch / breakpoint / step** | 纯人类交互式调试。AI 不会用交互式 breakpoint；它读 transcript + 跑程序。 |
| **行范围 trace** | 路线图自己也说"边际提升"。AI 用精准 `debug()` 信噪比更高。 |
| **Tool 调用 Profiling** | 性能诊断，Helen 场景极少。AI 调试很少关心性能。 |
| **Prompt 行为 Diff** | 主要给 prompt 工程师用。AI 调试者很少需要做 prompt 回归对比。 |

---

## 第二部分：补充功能

原路线图遗漏了几个对 AI 调试者特别有用的方向。

### 💡 2.1 结构化错误分类（不只是增强 ErrorSnapshot）

**痛点**：路线图建议给 ErrorSnapshot 加数据流回溯——这很好。但还缺一层：**错误语义分类 + 诊断建议**。

现在 `LLMError → TimeoutError / ModelError / AgentError` 的层级偏技术。AI 调试时更需要语义分类：

```helen
Error: LLMOutputFormatMismatch
  Agent: Reviewer
  Expected: JSON with field "verdict"
  Got: Plain text "I think the code is wrong because..."
  
  # 下面全部由静态机制生成，零 LLM 调用
  Suggestion: 在 agent prompt 里显式要求 '返回严格的 JSON 格式'，
              或在 llm act 后用 json_parse() 做容错解析。
              [fuzzy match] 相关函数：json_parse_lenient
  
  Data flow: msg_abc123 (Reviewer llm_act) ← prompt 第 3 段 ← Coder agent 输出
```

**价值**：

- AI 拿到这种错误就能直接定位到 prompt 问题，不用自己推理"是 LLM 不听指令还是代码 bug"。
- 错误分类让 AI 能用 `match` 语句精准捕获特定类别的 LLM 故障。

#### 🔑 关键架构决策：Suggestion 从哪里来？

**核心原则：runtime 异常处理链里不调用 LLM。**

原因：

1. **确定性原则破环**：错误处理路径必须可预测。如果建议生成本身也可能失败（LLM 调用超时/报错），错误处理代码会抛出"错误处理中的错误"——灾难。
2. **延迟叠加**：错误已经发生，用户/AI 等着看诊断，再插入一次 LLM 往返（几秒）体验很差。
3. **成本问题**：每个错误都触发一次 LLM 调用，调试循环里成本累积。
4. **循环依赖风险**：如果 LLM runtime 自己出错，再去调 LLM 要诊断建议——无限递归。

**三种静态机制组合（零 LLM 依赖）**：

| 机制 | 来源 | 延迟 | 成本 | 覆盖率 |
|---|---|---|---|---|
| **静态模板** | 错误分类 → 预定义模板 | 0ms | 0 | 80% |
| **Fuzzy match** | 现有 `fuzzy_match.py` | <1ms | 0 | NameError 100% |
| **规则库** | if/elif 预定义 | <1ms | 低（人力） | 中（高频痛点） |

**机制 1：静态模板（主力）**

每个错误类别绑定一个 suggestion 模板，模板里的变量用当前错误上下文填充：

```python
# helen/runtime/error_diagnostics.py（新增）

ERROR_SUGGESTION_REGISTRY = {
    "LLMOutputFormatMismatch": {
        "template": "Agent '{agent}' 期望输出 {expected}，实际得到 {actual_type}。"
                   "检查 agent prompt 是否明确要求输出格式，或使用 output_contract 参数。",
        "fields": ["agent", "expected", "actual_type"],
    },
    "ScopeViolationError": {
        "template": "Agent '{agent}' 试图访问模块级 let 变量 '{var}'。"
                   "Helen 默认 agent 隔离不允许此访问。改用 shared let 或通过参数显式传递。",
        "fields": ["agent", "var"],
    },
    "ToolCallFailure": {
        "template": "工具 '{tool}' 调用失败：{reason}。"
                   "检查工具参数是否符合 schema，或加重试逻辑。",
        "fields": ["tool", "reason"],
    },
    # ... 几十个核心类别
}
```

**机制 2：Fuzzy match（Helen 已有基础设施）**

`helen/runtime/fuzzy_match.py` 已经实现了函数名/关键字的模糊匹配。直接复用：

```python
# 现有：NameError: undefined 'json_parse'
# Fuzzy match 找到：json_parse_lenient, json_parse_strict
# Suggestion 自动拼接："你是不是想用 json_parse_lenient？"
```

**机制 3：规则库（高频痛点覆盖）**

对更复杂的模式，用预定义规则（不用 LLM，就是 if/elif 链）：

```python
def generate_suggestion(error, context):
    # 规则 1：LLM 返回了纯文本但期望 JSON
    if isinstance(error, LLMOutputFormatMismatch):
        if "json" in context["expected"].lower() and not context["actual"].strip().startswith("{"):
            return "LLM 返回纯文本而非 JSON。在 agent prompt 里显式要求 '返回严格的 JSON 格式'，" \
                   "或在 llm act 后用 json_parse() 做容错解析。"
    
    # 规则 2：循环里不变量失败 + 迭代次数大
    if isinstance(error, InvariantViolation) and context.get("iteration_count", 0) > 100:
        return f"不变量在第 {context['iteration']} 次迭代失败（共 {context['iteration_count']} 次）。" \
                "通常原因：循环内累积的数值溢出/精度丢失，或边界条件未在循环入口处理。"
    
    # 规则 3：工具调用失败级联
    if isinstance(error, ToolChainFailure):
        return f"工具链失败起始于 {context['first_failure_tool']}。后续 {context['cascade_count']} " \
                "个失败是下游依赖。先修第一个。"
```

**实现成本**：中（约 1 周）。在现有 ErrorSnapshot 基础上加分类层 + 模板注册表 + fuzzy match 集成。**一步到位覆盖全部 LLMError 子类型**（非仅 3-5 个核心类别），需枚举所有 LLMError 子类并为每个定义 suggestion 模板。三种静态机制零 LLM 依赖，runtime 异常处理链保持确定性。

### 💡 2.2 Agent 间数据流追踪（跨 agent 的数据血缘）

**痛点**：路线图讲了"agent 调用树可视化"给人看，但 AI 需要的是**可编程查询**：

```helen
# stdlib 函数：追溯某个值的来源
trace_value_origin(some_value)
# 返回：[Coder agent 的 llm_act msg_xyz, 第 3 个 tool call 的输出]

# stdlib 函数：追溯某个值被谁消费
trace_value_consumers(msg_id)
# 返回：[Reviewer agent 第 2 个 llm_act 的 prompt 注入点]
```

**价值**：

- Helen 的 agent 隔离 + Channel/send 设计意味着数据在 agent 之间的流动是显式的，**完全可以追踪**。
- 多 agent 系统出问题时，AI 能立刻回答"这个错误值最初是哪个 agent 的哪条 LLM 响应产生的"。
- Python 调试器做不到这一点——这是 Helen 的应有权。

**实现成本**：中-高（约 2 周）。采用 **SQLite sidecar 文件**（`<session_id>_lineage.db`）独立存储血缘元数据，与 TranscriptStore 的 transcript backend（JSONL 或 SQLite）解耦——无论用户选择哪种 transcript 后端，血缘数据都用 SQLite 存，支持 JOIN 查询。在 Channel/send 边界做值标记，写入 sidecar 的 `data_lineage` 表。

**⚠️ TranscriptStore 后端现状澄清**：

代码中 `TranscriptStore` 默认使用 **JSONL 后端**（`config.py:140`，`config.get("backend", "jsonl")`），SQLite 后端存在但需要用户在 `~/.helen/config.yaml` 里显式配置 `transcript.backend: "sqlite"` 才启用。因此血缘数据**不能假设 SQLite transcript 表存在**，必须用独立 sidecar。

**差异化**：⭐⭐⭐⭐⭐

### 💡 2.3 增量 Transcript 查询（而不是全量加载）

**痛点**：路线图假设"transcript 数据现成，差可视化层"。但 transcript 可能很大。AI 调试时如果每次都要加载完整 transcript 到上下文窗口，会很快爆掉。

**设计**：应该提供结构化查询 API：

```helen
# 只拿某个 agent 的所有 LLM 调用
query_transcript(session_id, filter={agent="Reviewer", type="llm_act"})

# 拿某个时间窗口的消息
query_transcript(session_id, time_range=(t1, t2))

# 拿包含特定工具调用的消息链
query_transcript(session_id, tool_chain=["web_search", "web_fetch"])
```

返回结构化 JSON（不是文本），AI 可以精准消化。

**价值**：

- 比"可视化"对 AI 有用 10 倍——AI 不需要图，需要精准数据切片。
- 保护 AI 的上下文窗口不被无关消息撑爆。
- 与 TranscriptStore SSOT 设计完全一致。

**实现成本**：约 1 周。需要**双后端查询路径**：
- **SQLite 后端**：直接生成 WHERE 子句下推到 SQL（高效，已有能力）
- **JSONL 后端**（默认）：流式加载 + Python 过滤，加 size limit 防爆内存（默认 10 万条上限，超过报错提示用户切换 SQLite）

两种后端共享同一个 stdlib 接口 `query_transcript()`，内部根据当前 session 的 backend 类型分发。

**⚠️ TranscriptStore 后端现状澄清**：

代码中 TranscriptStore 默认使用 JSONL 后端（`config.get("backend", "jsonl")`），不能假设 SQLite 已启用。SQLite 查询路径成本几乎为零（已有基础设施），JSONL 查询路径需要新写流式加载器。

---

## 第三部分：AI 调试视角的优先级重排

综合路线图保留项 + 补充功能，按**"对 AI 调试的价值 × LLM 实际使用概率"**重排（详见第七部分评估）：

| 优先级 | 功能 | 成本 | 价值 | LLM 使用概率 | 综合评分 |
|---|---|---|---|---|---|
| **P0** | **结构化错误 + 数据流回溯 + 错误分类**（静态机制） | ~1 周 | ⭐⭐⭐⭐⭐ | 🟢 95% | **必做** |
| **P0** | **Output contract 检查** | 3-5 天 | ⭐⭐⭐⭐ | 🟢 90% | **必做** |
| **P0** | **增量 transcript 查询 API** | ~1 周 | ⭐⭐⭐⭐⭐ | 🟢 80% | **必做**，需双后端支持（JSONL 流式过滤 + SQLite WHERE 下推） |
| **P1** | **Agent 录制/重放** | ~1 周 | ⭐⭐⭐⭐⭐ | 🟡 50-60% | **值得做**，skill 必须写死触发规则 |
| **P1** | **跨 agent 数据血缘追踪** | ~2 周 | ⭐⭐⭐⭐ | 🟡 50-60% | **值得做**，skill 必须写死触发规则 |
| **P1** | **Transcript 事后回放** | 中等 | ⭐⭐⭐ | 🟢 70% | 用户要求保留，基础设施现成 |

**P0 完成标准**：AI 调试 Helen 程序从"翻 transcript"升级为"精准查询 + 确定性重放 + 数据流回溯"。

**筛选标准**：没有高概率使用方案的功能（Execution Checkpoint、契约断言、`explain_error()` stdlib）不予纳入。详见第七部分评估。

---

## 第四部分：关键替换建议

路线图的 Tier 1 第二项是 **Agent 调用树可视化**，我建议替换为 **结构化 transcript 查询 API**。

| 维度 | 调用树可视化 | 结构化查询 API |
|---|---|---|
| 目标用户 | 人类 | AI |
| 数据基础 | 同一份 TranscriptStore | 同一份 TranscriptStore |
| 实现成本 | 3-5 天（可视化层） | 2-3 天（stdlib 封装） |
| AI 使用价值 | 低（AI 不读树状图） | 高（AI 直接查询切片） |
| 差异化 | 中（通用可视化都有） | 高（Helen 应有权） |

**理由**：这符合报告的战略洞察——"定义新领域 > 进入成熟领域竞争"。可视化是 pdb/Chrome DevTools 的领域；**可编程的 transcript 查询是 Helen 的领域**。

---

## 第五部分：与原路线图的对应关系

```
原路线图                    本文档处理
-----------                 -----------
Tier 1: Agent 录制/重放     → ✅ P0 保留
Tier 1: Agent 调用树可视化   → ❌ 丢弃，替换为 结构化查询 API（P1）
Tier 1: 错误上下文增强       → ✅ P0 保留 + 升级为 结构化错误分类
Tier 2: REPL watch/break     → ❌ 丢弃（纯人类功能）
Tier 2: Transcript 回放      → ✅ 保留（用户明确要求）
Tier 2: 契约断言             → ❌ 丢弃（LLM 不会主动写 annotation，使用概率 ~15%）
Tier 3: Prompt Diff          → ❌ 丢弃（人类 prompt 工程师用）
Tier 3: Tool Profiling       → ❌ 丢弃（性能诊断非 AI 调试重心）
Tier 3: 行范围 trace         → ❌ 丢弃（边际提升）
第四部分: Output contract    → ✅ P0 保留
第四部分: Agent IO schema    → ✅ P1 保留（并入数据血缘追踪）
第四部分: Tool failure prop  → ❌ 丢弃（部分场景）

补充功能:
+ 结构化错误分类              → P0 新增
+ 跨 agent 数据血缘           → P1 新增
+ 增量 transcript 查询        → P0 新增

排除的功能:
- Execution Checkpoint        → LLM 不会主动探索替代分支，使用概率 ~15%，无可行 Push 转型
- `explain_error()` stdlib    → LLM 过度自信会跳过，使用概率 ~25%，静态 suggestion 已覆盖 80%
```

---

## 第七部分：LLM 使用概率评估

> **核心问题**：功能做了，提供给 LLM 作为 SKILL.md，LLM 高概率会使用吗？

### 7.1 LLM 使用工具的三个障碍

1. **触发识别失败**：LLM 没意识到当前场景应该用这个工具
2. **过度自信**：LLM 认为自己能推理出来，不需要工具
3. **主动行为缺失**：LLM 只做眼前最明显的动作，不会"提前布局"

### 7.2 Push vs Pull 模型

| 模型 | 描述 | LLM 使用概率 | 例子 |
|---|---|---|---|
| **Push 模型** | 信息主动送到 LLM 面前（错误信息里自带、transcript 查询返回） | 🟢 80-95% | 结构化错误 Suggestion、Output contract 检查失败消息 |
| **Pull 模型** | LLM 需要主动调用工具 | 🟡 30-60% | `record_session()`、`trace_value_origin()` |
| **前瞻模型** | 要求 LLM 在写代码时就想到未来调试需求 | 🔴 10-20% | （已被排除的功能均属此类：Execution Checkpoint、契约断言、`explain_error()`） |

### 7.3 按使用概率分类

#### ✅ 高概率使用（Push 模型：信息主动送到 LLM 面前）

| 功能 | 为什么 LLM 会用 | 触发条件 |
|---|---|---|
| **结构化错误分类 + Suggestion** | 错误信息里自带，LLM 被动接收 | 错误发生时自动看到 |
| **增量 transcript 查询 API** | transcript 大时不查会爆 context window，LLM 会吃到苦头然后学会 | transcript 长度 > 阈值（skill 里明确写） |
| **Output contract 检查** | 错误信息里直接说"LLM 输出不符合 schema"，LLM 自然会修 | 错误触发时自动看到 |

**关键特征**：这些都是**被动消费**——错误/数据已经结构化好，LLM 不需要"想起"用工具，它读错误信息时就自然吸收了。

#### ⚠️ 中概率使用（Pull 模型：LLM 需要主动调用）

| 功能 | 为什么可能不用 | 风险 |
|---|---|---|
| **Agent 录制/重放** | LLM 看到 bug 后倾向直接读代码推理根因，不会主动想到"先录制一下" | 需要 skill 里写"**看到非确定性行为时，第一步必须 record**" |
| **跨 agent 数据血缘追踪** | LLM 会尝试自己读 transcript 找数据流，不会第一时间想到用 `trace_value_origin()` | 需要 skill 里写"**多 agent 错误时，先用血缘追踪，再读 transcript**" |

**关键特征**：LLM 会用，但需要 skill 文档**非常明确地写触发条件**，否则会跳过。

**排除的功能**：Execution Checkpoint、契约断言（@invariant）、`explain_error()` stdlib 三个功能因 LLM 使用概率低于 30% 且无可行 Push 转型方案，从计划中移除。具体原因见 7.4。

### 7.4 为什么排除 Execution Checkpoint、契约断言、`explain_error()`

LLM（包括我自己）在调试时的实际行为模式是：

1. **读错误信息** → 自己推理 → 直接改代码（**过度自信循环**）
2. **读源码** → 静态推理 → 假设根因 → 改代码
3. **跑程序看输出** → 对比期望 → 调整

三个被排除的功能分别撞上这些行为模式的硬墙：

| 功能 | 为什么 LLM 不会用 | 致命问题 | 为什么没有 Push 转型方案 |
|---|---|---|---|
| **Execution Checkpoint** | LLM 不会自然想到"假设分析"——倾向线性推理"如果 A 错了，那改 A" | **反认知**：要求 LLM 主动探索替代分支 | runtime 自动打 checkpoint 只能解决"让 LLM 看到 checkpoint"，不能解决"让 LLM 想探索 checkpoint"。探索替代分支是 meta-cognitive 行为，Push 模型无法强制。 |
| **契约断言（@invariant 等）** | LLM 写代码时倾向写最小必要逻辑，不会主动加 annotation | **前瞻性行为**：要求 LLM 在写代码时就想到未来调试需求 | 无法 Push——annotation 必须由代码作者主动写。runtime 自动推断 invariant 是另一个完全不同的功能，且覆盖范围有限。 |
| **`explain_error()` stdlib** | LLM **过度自信**——看到错误就自己解释，不会觉得需要工具帮忙 | **与 LLM 自身能力竞争**：LLM 认为自己解释错误的能力 > 调用函数 | 无法 Push——这是主动调用型工具。静态 suggestion（模板 + fuzzy + 规则）已覆盖 80% 场景，AI 真需要更深入分析会自己读源码和 transcript。 |

**核心判断标准**：如果一个功能既不能用 Push 模型（信息主动送到 LLM 面前），也不能用带强制触发规则的 Pull 模型（skill 里写"第一步必须"），那它就不应该进入 AI 调试工具集——LLM 不会用。

### 7.5 SKILL.md 写法指南：如何提升 LLM 使用率

对保留的功能，SKILL.md 不能写成"功能清单"，必须写成**"触发规则清单"**：

```markdown
# Helen AI 调试技能

## 调试触发规则（必须遵守）

### 当你看到任何错误时：
1. 首先读错误的完整结构化信息（包含 Suggestion、Data flow）
2. 如果 Suggestion 字段存在，优先按 Suggestion 行动
3. 如果 Data flow 字段存在，先看数据流，再读源码
4. ❌ 禁止跳过错误信息自己推理根因

### 当你看到非确定性行为（同输入不同输出）时：
1. **第一步必须**：用 `record_session()` 录制 agent 执行
2. **第二步必须**：重放 3 次确认问题可复现
3. **第三步才**：分析录制的 transcript 找根因
4. ❌ 禁止不录制就试图分析非确定性 bug

### 当 transcript 长度 > 2000 tokens 时：
1. **第一步必须**：用 `query_transcript()` 查询，不要全量加载
2. 查询时加 filter 参数缩小范围
3. ❌ 禁止把完整 transcript 读入上下文

### 当多 agent 系统出错时：
1. **第一步必须**：用 `trace_value_origin(error_value)` 追溯数据血缘
2. **第二步必须**：用 `trace_value_consumers()` 看谁消费了错误值
3. **第三步才**：读相关 agent 的 transcript
4. ❌ 禁止不查血缘就直接读 transcript
```

**关键**：每条规则都用"**第一步必须 / 第二步必须 / ❌ 禁止**"这种强制语气。否则 LLM 会跳过。

### 7.6 最终优先级总表

| 优先级 | 功能 | LLM 使用概率 | 价值 | 综合评分 | 备注 |
|---|---|---|---|---|---|
| **P0** | 结构化错误分类 + 数据流回溯（静态机制） | 🟢 95% | ⭐⭐⭐⭐⭐ | 必做 | Push 模型 |
| **P0** | Output contract 检查 | 🟢 90% | ⭐⭐⭐⭐ | 必做 | Push 模型 |
| **P0** | 增量 transcript 查询 API | 🟢 80% | ⭐⭐⭐⭐⭐ | 必做 | 需双后端支持（JSONL + SQLite） |
| **P1** | Agent 录制/重放 | 🟡 50-60% | ⭐⭐⭐⭐⭐ | 值得做 | skill 必须写死触发规则 |
| **P1** | 跨 agent 数据血缘追踪 | 🟡 50-60% | ⭐⭐⭐⭐ | 值得做 | skill 必须写死触发规则 |
| **P1** | Transcript 事后回放 | 🟢 70% | ⭐⭐⭐ | 用户要求保留 | 基础设施现成 |

---

## 第八部分：附录

### A. 关键差异总结

| 本文档 vs 原路线图 | 变化 |
|---|---|
| Tier 1 第二项替换 | 调用树可视化 → 结构化查询 API |
| 错误处理升级 | 数据流回溯 → 数据流回溯 + 语义分类 + 诊断建议（静态机制，runtime 不调 LLM） |
| 新增 P0 | 增量 transcript 查询、Output contract 检查 |
| 新增 P1 | 跨 agent 数据血缘追踪 |
| 排除 3 个低使用率功能 | Execution Checkpoint、契约断言、`explain_error()` stdlib 因 LLM 使用概率 <30% 且无可行 Push 转型方案而移除 |
| TranscriptStore 后端澄清 | 代码实际默认 **JSONL 后端**（非 SQLite）。2.2 节数据血缘改用独立 SQLite sidecar；2.3 节 transcript 查询需双后端支持（JSONL 流式过滤 + SQLite WHERE 下推）。成本从 2-3 天上调到 ~1 周。 |
| 新增第七部分 | LLM 使用概率评估（Push vs Pull 模型 + 排除理由） |
| 总成本估算 | P0 约 3 周（结构化错误 ~1 周 + Output contract 3-5 天 + transcript 查询 ~1 周）；P1 约 3 周（录制/重放 ~1 周 + 数据血缘 ~2 周 + transcript 回放中等） |

### B. 决策点（已确认）

| # | 决策 | 结论 | 影响 |
|---|---|---|---|
| 1 | 调用树可视化 → 结构化查询 API | ✅ **接受替换** | 第四部分方案落地，不做可视化层 |
| 2 | 错误分类的粒度 | ✅ **一步到位覆盖全部 LLMError 子类型** | 2.1 节实现时需枚举所有 LLMError 子类并为每个定义 suggestion 模板 |
| 3 | 跨 agent 数据血缘的元数据存储 | ✅ **单独的元数据表**（SQLite sidecar） | 2.2 节采用独立 `<session_id>_lineage.db` 文件，与 TranscriptStore 的 transcript backend（JSONL 或 SQLite）解耦。无论用户选哪种 transcript 后端，血缘数据都用 SQLite 存，支持 JOIN 查询。 |
| 4 | SKILL.md 格式 | ✅ **采用"触发规则清单"格式** | 7.5 节的写法指南成为 skill 文档标准，用"第一步必须 / ❌ 禁止"强制语气 |

### C. 相关文档

- `helen-debugging-dev-plan-2026-08-11.md`（**开发方案**，6 个 Phase 的具体实现计划）
- `helen-debugging-roadmap-2026-08-11.md`（原路线图）
- `helen/runtime/observability.py`（现有 ObservabilityManager）
- `helen/runtime/transcript_store.py`（TranscriptStore SSOT）
- `helen/runtime/fuzzy_match.py`（现有模糊匹配，可复用于错误 suggestion）

---

**文档结束**

*本报告基于对 `helen-debugging-roadmap-2026-08-11.md` 的 AI 调试视角评审。核心筛选标准：功能做了之后 LLM 作为 SKILL.md 消费者是否会高概率使用。据此将功能分为 Push 模型（80-95% 使用率）、Pull 模型（50-60%）、前瞻模型（10-20%）三档，排除了 Execution Checkpoint、契约断言、`explain_error()` stdlib 三个无可行 Push 转型方案的功能。最终保留 6 个功能：P0 三项（结构化错误分类、Output contract、增量 transcript 查询）+ P1 三项（Agent 录制/重放、跨 agent 数据血缘、Transcript 事后回放）。*
