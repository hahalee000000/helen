# 语义 Working Memory 设计方案

**Proposal Date**: 2026-07-23
**Author**: Helen Core
**Status**: Draft
**Target Version**: Helen v1.25
**Related**: `working-memory-audit-2026-07-20.md`, v1.15 context enhancement, v1.16 TranscriptStore SSOT

---

## 1. 问题陈述

### 1.1 当前 Working Memory 的局限

Helen v1.15 引入的 Working Memory 采用**纯正则启发式匹配**填充：

| 字段 | 触发机制 | 实际覆盖率 |
|---|---|---|
| `task_description` | 必须手动 set | 几乎永远空 |
| `active_files` | `read_file`/`write_file`/`patch_file` 工具调用 | 仅编码场景 |
| `recent_decisions` | 正则匹配 "I'll use X" / "Let me try X" | **只识别英文** |
| `pending_todos` | 正则匹配 TODO/FIXME/[ ] | 只识别结构化 TODO |
| `error_history` | `shell_exec` 非零退出码 | 仅 shell 错误 |

**关键缺陷（面向"持续对话"场景）：**

1. **无语义提取**：无法从对话中抽取"用户偏好""关键决策""约定事实"
2. **语言偏见**：决策提取正则只匹配英文句式（`I'll`, `Let me`），中文 agent 完全失效
3. **不持久化**：interpreter 结束即丢失
4. **不跨 invocation**：`spawn` 出的子 agent 有独立 working memory，无法继承父 agent 的
5. **无重要性区分**：按时间 LRU 淘汰，关键决策和闲聊同等对待
6. **结构僵化**：5 个固定字段无法表达复杂会话状态

### 1.2 用户的真实需求

> "agent 需要保持与用户的持续沟通，每次执行上下文独立"

翻译成系统需求：

- **跨 invocation 连续性**：用户第 10 次提问时，agent 应该"记得"前 9 次的要点
- **每次执行隔离**：agent 内部仍是干净环境（Helen 第一原则）
- **效率可控**：不能每次重新加载完整 transcript
- **跨重启**：进程挂了，下次启动还能继续对话
- **成本可控**：不能每次都跑一次昂贵的 LLM 调用

---

## 2. 设计目标

### 2.1 必须满足

- **G1**：对话内容能被语义提取为紧凑摘要（不依赖正则）
- **G2**：摘要能跨 invocation 传递（同一进程内的 `spawn` 和跨进程的 CLI 调用）
- **G3**：摘要能跨重启持久化（借助 TranscriptStore SSOT）
- **G4**：大小恒定（无论对话多长，摘要占用固定 token 预算）
- **G5**：多语言中立（中文、英文、混合场景同样工作）
- **G6**：向后兼容（现有 `working_memory_get/set` stdlib 继续工作）

### 2.2 应该满足

- **G7**：成本可控——使用小模型做摘要，且能配置触发频率
- **G8**：可 introspect——用户能看到当前摘要、强制刷新、手动覆盖
- **G9**：不阻塞主流程——摘要生成可以异步（失败时降级）

### 2.3 非目标（明确排除）

- 不替代 TranscriptStore（完整历史仍然是 SSOT）
- 不替代当前正则-based working memory（工具追踪仍然是精确的）
- 不实现 RAG 向量检索（摘要本身就是"压缩索引"）

---

## 3. 核心概念

### 3.1 三层上下文模型

重新理解 Helen 的上下文层次：

```
┌──────────────────────────────────────────────────┐
│ Layer 3: Transcript (完整历史)                    │  ← SSOT, 用于审计/恢复/全量回放
│ - 所有消息 + BoundaryMarkers                     │
│ - 大小: 无上限                                   │
│ - 加载成本: O(n)                                 │
└──────────────────────────────────────────────────┘
            ↓ 压缩（graduated / LLM 摘要）
┌──────────────────────────────────────────────────┐
│ Layer 2: Semantic Working Memory (语义摘要)       │  ← 本方案新增
│ - LLM 生成的会话状态快照                         │
│ - 大小: 恒定 ~500 tokens (可配置)                │
│ - 加载成本: O(1)                                 │
│ - 触发更新: invocation 边界 / 阈值 / 显式        │
└──────────────────────────────────────────────────┘
            ↓ 精确追踪
┌──────────────────────────────────────────────────┐
│ Layer 1: Structural Working Memory (结构追踪)     │  ← 现有实现保留
│ - active_files, error_history (工具调用精确追踪) │
│ - 大小: 受 token 预算限制                        │
│ - 触发更新: 工具调用 / 消息正则                  │
└──────────────────────────────────────────────────┘
```

**三层独立、互补、同时注入 LLM context**：

- Layer 1 提供**精确的工具状态**（哪些文件被读过、哪些命令失败）
- Layer 2 提供**语义理解**（用户在做什么、已达成什么共识、有什么偏好）
- Layer 3 提供**完整证据**（仅在用户显式请求或需要细节时加载）

### 3.2 Semantic Working Memory (SWM) 的定义

**SWM 是一个由 LLM 维护的、固定大小的、自由格式的会话状态快照。**

它不是结构化 JSON，而是一段**markdown 文本**，由 LLM 根据指导模板生成并持续更新。示例：

```markdown
## 用户画像
- 名字: 小王
- 偏好语言: 中文
- 技术水平: 熟悉 Python，不熟悉 Helen
- 回复风格: 简洁直接，不要过多解释

## 当前任务
修复 Helen issue #19（多模态 Message 字段丢失）。
已确定方案：使用 dataclasses.replace() 而不是手动复制字段。

## 关键决策
- 2026-07-23: 决定保留现有 _restore_media_in_messages 结构，只补全字段
- 2026-07-23: 回归测试策略：新建 TestRestoreMediaPreservesFields 类

## 已完成
- 修复代码已提交 (69933a5)
- 版本 bump 到 1.24.9
- PyPI 已发布

## 待办
- [ ] 用户验证 agent 内多模态场景
- [ ] 移除 ~/.helen/config.yaml 中的 workaround

## 上下文约束
- 用户在 ARM64 Linux 环境
- 使用阿里云 DashScope 作为 LLM provider
```

**关键特性**：
- **自由格式**：markdown 文本，LLM 可自由组织
- **有指导模板**：提供"建议包含的维度"，但不强制
- **增量更新**：每次更新时，LLM 看到旧摘要 + 新消息，产出新摘要
- **大小恒定**：prompt 里明确要求"不超过 N tokens"

---

## 4. 架构设计

### 4.1 组件关系

```
┌─────────────────────────────────────────────────────────┐
│                 Interpreter                             │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  AgentContextManager                            │   │
│  │                                                 │   │
│  │  working_memory: WorkingMemory (Layer 1, 现有)  │   │
│  │  semantic_memory: SemanticMemory (Layer 2, 新增)│   │
│  │                                                 │   │
│  │  prepare_context():                             │   │
│  │    1. compress history → Layer 3                │   │
│  │    2. build three-channel context               │   │
│  │       - system (15%)                            │   │
│  │       - working_memory + semantic_memory (50%)  │   │
│  │       - history (35%)                           │   │
│  └─────────────────────────────────────────────────┘   │
│                         │                               │
│                         │ 持久化                         │
│                         ▼                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │  TranscriptStore (SSOT)                         │   │
│  │                                                 │   │
│  │  transcript: [Message | BoundaryMarker |        │   │
│  │                SemanticSnapshot]                 │   │
│  │                                                 │   │
│  │  SemanticSnapshot 作为特殊的 pinned message     │   │
│  │  通过 SessionMeta.working_memory_uuid 引用      │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│                         │                               │
│                         │ 摘要生成                      │
│                         ▼                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Summarizer (LLM 调用封装)                      │   │
│  │                                                 │   │
│  │  - 使用小模型 (Haiku 级别)                      │   │
│  │  - 增量更新 (old_summary + new_messages → new)  │   │
│  │  - 失败降级 (返回 old_summary)                  │   │
│  │  - 节流 (min_interval, min_messages)            │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 4.2 关键类

```python
@dataclass
class SemanticSnapshot:
    """一次语义摘要快照。

    作为特殊的 transcript 项持久化，继承 SSOT 的所有好处。
    """
    uuid: str                       # 唯一 ID
    content: str                    # markdown 摘要正文
    token_estimate: int             # 预估 token 数
    based_on_message_uuids: list[str]  # 覆盖了哪些消息
    previous_snapshot_uuid: str | None  # 链式引用（历史）
    timestamp: float
    trigger: str                    # "invocation_end" | "threshold" | "explicit"
    model_used: str                 # 摘要所用模型


class SemanticMemory:
    """语义 working memory 管理器。

    维护当前生效的 SemanticSnapshot，并提供：
    - 加载（从 transcript 或 SessionMeta 指针）
    - 更新（触发 LLM 摘要）
    - 查询（to_context() 给 LLM 看）
    """
    current: SemanticSnapshot | None = None
    max_tokens: int = 500
    auto_enabled: bool = True
    summarizer: Summarizer

    def to_context(self, budget_chars: int) -> str: ...
    def should_update(self, new_messages: int) -> bool: ...
    def update(self, new_messages: list[Message]) -> SemanticSnapshot: ...
    def force_update(self) -> SemanticSnapshot: ...
    def load_from_session(self, session_id: str) -> None: ...
```

### 4.3 与现有系统的集成点

| 集成点 | 现有行为 | 新增行为 |
|---|---|---|
| `AgentContextManager.__init__` | 创建 `WorkingMemory` | 同时创建 `SemanticMemory` |
| `_add_to_history()` | 调用 `update_from_message` | 不直接触发语义更新（节流） |
| `prepare_context()` | 注入 `working_memory.to_context()` | 同时注入 `semantic_memory.to_context()` |
| `llm act` 结束 | — | **新增**：触发语义更新（如果满足条件） |
| `TranscriptStore.append()` | 接受 Message/BoundaryMarker | 接受 SemanticSnapshot |
| `SessionMeta` | 记录 argv, timestamp | 新增 `working_memory_uuid` 字段 |
| `resume_session()` | 导入完整 transcript | 同时加载最新 SemanticSnapshot |
| `spawn` | 子 agent 新建 session | 子 agent 可选择继承父 SWM |

---

## 5. 持久化方案

### 5.1 存储位置：SemanticSnapshot 作为 Transcript 项

**为什么不是独立文件**：
- 独立文件需要额外的同步逻辑（与 transcript 对齐）
- 失去 SSOT 的审计、恢复、压缩等能力
- 跨进程一致性难保证

**为什么不是 SessionMeta 字段**：
- SessionMeta 设计为元数据（启动时写入一次）
- 摘要会频繁更新，不适合放在 meta

**方案**：
- SemanticSnapshot 作为 transcript 中的**独立项**（与 Message、BoundaryMarker 同级）
- SessionMeta 增加 `working_memory_uuid: str` 字段，指向**最新的** SemanticSnapshot
- JSONL 后端：作为一行 `{ "type": "semantic_snapshot", ... }` 存储
- SQLite 后端：新建 `semantic_snapshots` 表（或复用 items 表）

```
Transcript 结构:
┌─ SessionMeta
├─ Message (user)
├─ Message (assistant)
├─ SemanticSnapshot (uuid=abc, based_on=[m1, m2])  ← 第一次摘要
├─ Message (user)
├─ Message (assistant)
├─ SemanticSnapshot (uuid=def, prev=abc, based_on=[m1..m4])  ← 增量更新
├─ BoundaryMarker (compression)
├─ ...
```

### 5.2 加载路径

**interpreter 启动时**：
1. 读取 SessionMeta → 拿到 `working_memory_uuid`
2. 通过 UUID 索引 O(1) 读取对应 SemanticSnapshot
3. 装入 `SemanticMemory.current`

**resume_session(parent_sid) 时**：
1. 父 session 的 SessionMeta → 拿到 working_memory_uuid
2. 加载该 snapshot
3. 作为子 session 的**初始** SemanticSnapshot（后续更新从此继承）

**spawn 时**：
- 默认行为：**不继承**（保持 agent 隔离原则）
- 显式调用：`spawn Agent(..., inherit_memory=True)` 继承父 SWM
- 或者：通过 Channel 消息显式传递（符合"调用者决定上下文"原则）

---

## 6. 触发策略

### 6.1 三种触发方式

| 触发 | 条件 | 默认开启 |
|---|---|---|
| **Invocation boundary** | `llm act` 完成一次调用后 | ✅ 默认开启 |
| **阈值触发** | 自上次摘要后新增 N 条消息 | ✅ 默认开启（N=10） |
| **显式触发** | 用户调用 `working_memory_summarize()` stdlib | 总是可用 |

### 6.2 节流策略（成本控制）

```python
class SummarizationPolicy:
    min_messages_since_last: int = 10      # 至少 10 条新消息才触发
    min_seconds_since_last: int = 60       # 至少 60 秒间隔
    max_tokens_per_summary: int = 500      # 摘要最大 token
    summarizer_model: str = "auto"         # "auto" = 比主模型低一级
    force_on_context_overflow: bool = True # 上下文快满时强制触发

    def should_trigger(self, ctx) -> bool:
        if ctx.messages_since_last < self.min_messages_since_last:
            return False
        if ctx.seconds_since_last < self.min_seconds_since_last:
            return False
        if ctx.usage_ratio > 0.8:  # context 80% 占用
            return True
        return True
```

### 6.3 触发位置

```
visit_llm_act_expr()
  ├─ 准备 context → 注入 SWM
  ├─ LLM 调用 → 拿到响应
  ├─ 工具循环 → 执行工具
  ├─ 记录历史 → 多条 Message 写入 transcript
  └─ **新增**：检查 SWM 触发条件
       └─ 如果 should_trigger(): async_summarize(new_messages)
```

**异步执行**：摘要生成**不阻塞主流程**。失败时降级（保留旧摘要）。

---

## 7. 摘要生成：增量更新算法

### 7.1 核心思想

**不重做，只增量**：每次摘要时，LLM 看到：
- 旧摘要（上一次快照）
- 新增消息（自上次快照以来）
- 输出：新摘要（融合两者）

### 7.2 Prompt 模板

```
你是一个会话摘要助手。请根据以下材料更新"会话状态摘要"。

## 旧摘要
{old_summary or "(无)"}

## 新增对话
{new_messages_formatted}

## 要求
1. 新摘要必须包含以下维度（按需更新，没有变化的保留）：
   - 用户画像（身份、偏好、技术水平）
   - 当前任务（明确目标、当前状态）
   - 关键决策（已确定的方案、原因）
   - 已完成事项
   - 待办事项
   - 上下文约束（环境、依赖、限制）

2. 格式约束：
   - Markdown 格式
   - 总长度不超过 {max_tokens} tokens
   - 过时信息主动丢弃
   - 重复信息合并
   - 重要决策保留细节，次要细节可概括

3. 如果新对话没有提供新信息，保持旧摘要不变。

## 输出
直接输出新摘要正文，不要任何前后缀。
```

### 7.3 模型选择策略

| 主模型级别 | 摘要模型 | 原因 |
|---|---|---|
| Opus 级 | Sonnet 级 | 省 10x 成本 |
| Sonnet 级 | Haiku 级 | 省 20x 成本 |
| Haiku 级 | 同模型 | 已经最便宜 |
| 本地模型 | 同模型或配置 | 用户自行决定 |

配置方式：
```yaml
# ~/.helen/config.yaml
working_memory:
  semantic:
    enabled: true
    max_tokens: 500
    summarizer_model: "auto"     # 自动降级
    min_messages: 10
    min_interval_seconds: 60
    language_hint: "auto"        # "auto" | "zh" | "en" | ...
```

### 7.4 失败降级

- LLM 调用失败 → 保留旧 snapshot，记录错误日志
- 返回过长 → 截断 + 标记需要下次压缩
- 返回空 → 保留旧 snapshot
- 超时 → 同上

**永远不要因为摘要失败而中断主流程**。

---

## 8. API 设计

### 8.1 新增 stdlib 函数

| 函数 | 作用 |
|---|---|
| `working_memory_summarize()` | 立即触发一次摘要（同步等待） |
| `working_memory_summarize_async()` | 立即触发一次摘要（异步，立即返回） |
| `working_memory_get_semantic()` | 获取当前语义摘要文本 |
| `working_memory_set_semantic(text)` | 手动覆盖语义摘要 |
| `working_memory_auto(enabled)` | 启用/禁用自动摘要 |
| `working_memory_stats()` | 返回摘要统计（次数、大小、模型等） |
| `working_memory_clear_semantic()` | 清空语义摘要（保留结构追踪） |

### 8.2 中文别名

```
摘要工作记忆()            → working_memory_summarize()
异步摘要工作记忆()         → working_memory_summarize_async()
获取语义工作记忆()         → working_memory_get_semantic()
设置语义工作记忆()         → working_memory_set_semantic()
设置工作记忆自动化()       → working_memory_auto()
工作记忆统计()            → working_memory_stats()
清空语义工作记忆()         → working_memory_clear_semantic()
```

### 8.3 Agent 配置扩展

```helen
agent ChatBot(query: str) {
    description "持续对话助手"
    context {
        working-memory true
        working-memory-tokens 5000
        // v1.25 新增
        semantic-memory true
        semantic-memory-tokens 500
        semantic-memory-model "auto"
        semantic-memory-min-messages 5
    }
    main {
        let response = llm act query
        return response
    }
}
```

---

## 9. 三通道上下文集成

v1.15 的三通道上下文（system 15% / working 50% / history 35%）需要调整：

### 9.1 新的 budget 分配

```
System instructions:      15%  (不变)
Working memory (combined): 50%  (Layer 1 + Layer 2 共享)
  ├─ Structural (精确工具追踪): ~10%
  └─ Semantic (语义摘要):       ~40%
History:                35%  (不变)
```

### 9.2 注入顺序

```python
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "system", "content": f"[Working Memory - Structural]\n{structural_wm.to_context()}"},
    {"role": "system", "content": f"[Working Memory - Semantic]\n{semantic_wm.to_context()}"},
    # ... history messages ...
]
```

**为什么分成两条 system message**：
- 让 LLM 区分"精确状态" vs "语义理解"
- 便于 debug（哪一层出问题可以单独关闭）
- 未来可以独立调整 budget

---

## 10. 成本分析

### 10.1 单会话成本估算

假设：
- 用户与 agent 对话 100 轮
- 每轮平均 500 tokens 输入 + 200 tokens 输出
- 摘要触发：每 10 轮一次 = 10 次摘要调用
- 摘要输入：旧摘要 (500) + 新消息 (10 × 700 = 7000) = 7500 tokens
- 摘要输出：500 tokens

| 项目 | 主模型 (Qwen3.7-Plus) | 摘要模型 (Haiku) |
|---|---|---|
| 主对话：100 轮 | 100 × 700 = 70K in + 20K out | — |
| 摘要：10 次 | — | 10 × 7500 = 75K in + 5K out |
| **总输入** | ~70K | ~75K |
| **总输出** | ~20K | ~5K |
| **相对成本** | 1.0x (baseline) | ~0.05x（用 Haiku）|

**结论**：用 Haiku 级模型做摘要，增加约 5% 总成本。**完全可接受**。

### 10.2 节省的收益

- 不再需要每次加载完整 transcript → **省 80-90% 输入 token**
- 长会话不再需要复杂压缩 → **省掉 graduated compression 大部分复杂度**
- LLM 看到的信息密度高 → **响应质量提升**（减少"忘了之前说的"情况）

---

## 11. 实现分期

### Phase 1: 基础设施（1-2 周）

**目标**：让 SemanticSnapshot 能存能取

- [ ] 定义 `SemanticSnapshot` dataclass
- [ ] 扩展 `TranscriptStore` 接受 SemanticSnapshot 项
- [ ] JSONL 后端序列化/反序列化
- [ ] SQLite 后端支持（新表或复用）
- [ ] 扩展 `SessionMeta` 增加 `working_memory_uuid` 字段
- [ ] 单元测试：snapshot 写入、读取、链式引用

**可独立验证**：能手工写入 snapshot 并在重启后读取

### Phase 2: 摘要生成（1-2 周）

**目标**：`Summarizer` 能生成增量摘要

- [ ] 实现 `Summarizer` 类（封装 LLM 调用）
- [ ] 实现摘要 prompt 模板
- [ ] 模型选择策略（auto 降级）
- [ ] 失败降级逻辑
- [ ] 节流策略
- [ ] 单元测试：摘要生成、失败处理、节流

**可独立验证**：给定一段对话，能生成合理摘要

### Phase 3: 集成到 AgentContextManager（1 周）

**目标**：`llm act` 自动触发摘要

- [ ] `AgentContextManager` 持有 `SemanticMemory`
- [ ] `prepare_context()` 注入语义摘要
- [ ] `llm act` 结束后检查触发条件
- [ ] 异步执行（不阻塞主流程）
- [ ] `spawn` 集成（默认不继承，显式开启）
- [ ] `resume_session()` 集成（自动加载最新 snapshot）

**可独立验证**：多次 `llm act` 后，新调用能看到之前的摘要

### Phase 4: stdlib 与配置（0.5 周）

**目标**：用户可控制

- [ ] 新增 stdlib 函数（见 §8）
- [ ] 中文别名
- [ ] `~/.helen/config.yaml` 配置项
- [ ] agent `context {}` 块新字段

**可独立验证**：用户能通过 stdlib 强制触发、查看、覆盖摘要

### Phase 5: 工具链与文档（0.5 周）

**目标**：用户能用起来

- [ ] REPL 命令 `:semantic_memory` 查看当前摘要
- [ ] Helen 官方文档更新
- [ ] 示例程序：`examples/continuous_chat.helen`
- [ ] skill: `continuous-conversation`

---

## 12. 与现有机制的关系

### 12.1 与 TranscriptStore (v1.16)

- **互补**：Transcript 是完整历史，SWM 是压缩视图
- **继承 SSOT**：SemanticSnapshot 是 transcript 的一项
- **不替代**：用户仍然可以 `replay_transcript()` 看完整历史

### 12.2 与 Graduated Compression (v1.15)

- **互补**：SWM 提供语义层压缩，graduated 提供结构层压缩
- **可能简化**：SWM 成熟后，graduated 的 Layer 5（LLM 摘要）可以下沉到 SWM，减少复杂度
- **不立即替代**：v1.25 两者并存

### 12.3 与 Structural Working Memory (v1.15)

- **互补**：结构层保留精确的工具追踪，语义层提供对话理解
- **共享 budget**：50% working memory 通道由两者共享
- **独立可开关**：可单独关闭任一层

### 12.4 与 Pinned Messages (v1.19)

- **互补**：pinned 是用户显式标记的"不可压缩"消息；SWM 是自动维护的摘要
- **SWM 可以包含 pinned 内容**：摘要生成时特别关注 pinned messages

### 12.5 与 Invocation Tree (v1.22)

- **SWM 默认按 invocation 隔离**：每次 invocation 边界可触发独立摘要
- **可配置跨 invocation 共享**：`inherit_memory=True` 让子 invocation 看到父 SWM

### 12.6 与 Channel (v1.18)

- **Channel 消息可触发 SWM 更新**：收到关键消息时可以触发摘要
- **SWM 不通过 Channel 传递**（保持 agent 隔离原则）
- **显式传递**：通过 `spawn(inherit_memory=True)` 或 Channel 消息手工传

---

## 13. 风险与缓解

### 13.1 风险列表

| 风险 | 严重性 | 可能性 | 缓解 |
|---|---|---|---|
| 摘要质量差，丢失重要信息 | 高 | 中 | 失败降级保留旧摘要；用户可强制重写；保留完整 transcript 作为兜底 |
| 摘要成本失控（频繁触发） | 中 | 低 | 严格节流（min_messages + min_interval）；可配置关闭 |
| 摘要延迟（异步没完成时新调用开始） | 中 | 中 | 阻塞模式开关；默认非阻塞，失败时旧快照兜底 |
| 跨进程一致性问题（两个进程同时更新同一 session） | 中 | 低 | SWM 默认 per-interpreter；跨进程继承必须显式 |
| 与现有 working_memory 行为冲突 | 低 | 中 | 完全独立的字段/类；共享注入通道但独立控制 |
| LLM provider 不支持摘要模型 | 低 | 低 | `summarizer_model: "auto"` 自动降级到主模型 |

### 13.2 监控指标

- `semantic_summary_updates_total` — 总更新次数
- `semantic_summary_failures_total` — 失败次数
- `semantic_summary_avg_latency_ms` — 平均延迟
- `semantic_summary_avg_tokens` — 平均 token 数
- `semantic_summary_cost_usd` — 累计成本

通过 stdlib `working_memory_stats()` 暴露给用户。

---

## 14. 开放问题

### 14.1 待讨论

1. **摘要粒度**：是"整个会话一个摘要"还是"每个 invocation 一个摘要，组合起来"？
   - 推荐：前者（简单），但保留后者的扩展空间
2. **SWM 可见性**：是否允许 LLM 主动调用 `working_memory_set_semantic()` 自我更新？
   - 推荐：允许，但需显式配置（避免 LLM 污染自己的上下文）
3. **多 Agent 场景**：多个 agent 协作时，是否共享 SWM？
   - 推荐：默认独立；通过 `shared store` 或 Channel 显式共享
4. **与 RAG 的关系**：未来是否引入向量检索 + SWM 混合？
   - 推荐：v1.25 不做；保留 API 扩展空间

### 14.2 待实验

1. **摘要模板的效果**：固定模板 vs 自由格式 vs 混合
2. **触发频率的最优值**：min_messages=5/10/20 哪个效果/成本平衡最好
3. **异步 vs 同步的用户体验**：默认异步，但用户是否能感知到"延迟"

---

## 15. 成功标准

### 15.1 功能验收

- [ ] 10 轮对话后，新 invocation 能正确回答"我之前说了什么"
- [ ] 进程重启后，新 interpreter 能继承上一轮的 SWM
- [ ] 中文对话和英文对话的摘要质量相当
- [ ] 摘要触发不影响主流程响应时间（< 100ms 阻塞）
- [ ] 失败降级工作正常（LLM 调用失败不影响主对话）

### 15.2 性能验收

- [ ] 摘要生成延迟 < 2s（Haiku 级模型）
- [ ] 摘要大小稳定在 max_tokens ± 20%
- [ ] 100 轮对话累计摘要成本 < 主对话成本的 10%
- [ ] 摘要加载时间 < 10ms（从 transcript 读取）

### 15.3 用户体验验收

- [ ] 现有 stdlib `working_memory_get/set` 继续工作
- [ ] 新用户无需理解三层模型也能开箱即用
- [ ] 高级用户能通过 stdlib/config 完全控制行为

---

## 16. 参考

- **Helen 现有报告**：
  - `working-memory-audit-2026-07-20.md` — 当前实现审计
  - `CONTEXT_ENHANCEMENT_VS_CLAUDE_CODE.md` — 与 Claude Code 的对比
  - `multimodal-proposal.md` — "回调即适配器" 设计哲学
- **业界参考**：
  - OpenAI Assistants API — Thread 概念（持久化会话状态）
  - Anthropic Projects Memory — 项目级记忆
  - LangChain Memory Modules — ConversationSummaryMemory
  - MemGPT — 分层 memory + LLM 自管理
- **Helen 第一原则**：
  - "调用者决定上下文"（Caller Decides Context）
  - "显式优于隐式"
  - "回调即适配器"

---

## 附录 A: 示例交互流程

```helen
// ~/.helen/config.yaml 启用 SWM
// working_memory.semantic.enabled: true

// 程序: chat_assistant.helen
agent ChatBot(user_msg: str) {
    description "持续对话助手"
    context {
        working-memory true
        semantic-memory true     // v1.25 新字段
        semantic-memory-tokens 500
    }
    main {
        let response = llm act user_msg
        // llm act 结束时自动检查并触发摘要（如果满足条件）
        return response
    }
}

// REPL 或 Web UI 主循环
let session_id = get_session_id()

while (true) {
    let user_input = read_line()
    let response = ChatBot(user_input)
    print(response)
}

// 第一次启动时：
//   SWM 为空
//   用户: "我叫小王，帮我修复 issue #19"
//   agent: "好的，小王。我会帮你修复 issue #19..."
//   [10 条消息后自动触发摘要]
//   SWM → "用户：小王；任务：修复 issue #19；..."

// 用户 Ctrl+C 退出，下次重启
// helen chat_assistant.helen --resume-latest
//   interpreter 启动 → 加载 SessionMeta → 找到 working_memory_uuid
//   读取最新 SemanticSnapshot → 装入 SWM
//   用户: "继续上次的工作"
//   agent: "好的小王，上次我们修复了 issue #19，已经提交到 PyPI..."
//   ↑ agent 通过 SWM 知道了用户名字和上次任务，无需重新解释
```

---

## 附录 B: 配置示例

```yaml
# ~/.helen/config.yaml
working_memory:
  # 现有配置（保留）
  enabled: true
  max_tokens: 5000

  # 新增：语义层配置
  semantic:
    enabled: true
    max_tokens: 500              # 摘要最大 token
    summarizer_model: "auto"     # "auto" | 具体模型名
    min_messages: 10             # 至少 N 条新消息才触发
    min_interval_seconds: 60     # 两次摘要最小间隔
    language_hint: "auto"        # "auto" | "zh" | "en" | ...
    trigger_on_invocation_end: true
    trigger_on_threshold: true
    trigger_on_context_overflow: true

    # 失败降级
    fallback_on_error: true      # LLM 失败时保留旧摘要
    max_retries: 1               # 失败重试次数

    # 模板（高级用户可覆盖）
    template: |
      你是一个会话摘要助手。请根据以下材料更新"会话状态摘要"。

      ## 旧摘要
      {old_summary}

      ## 新增对话
      {new_messages}

      ## 要求
      1. 必须包含：用户画像、当前任务、关键决策、已完成、待办、上下文约束
      2. Markdown 格式，不超过 {max_tokens} tokens
      3. 过时信息主动丢弃，重复信息合并

      ## 输出
      直接输出新摘要正文。
```
