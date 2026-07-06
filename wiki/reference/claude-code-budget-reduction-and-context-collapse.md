# Claude Code 上下文管理详解：Budget Reduction 与 Context Collapse

> 深入分析 Claude Code 压缩管线的两个关键层

**日期**：2026-07-06
**来源**：arXiv:2604.14228v2 (Liu et al., 2026)

---

## 一、Budget Reduction（Layer 1）：大工具输出 → 引用指针

### 1.1 核心机制

**函数**: `applyToolResultBudget()`
**位置**: query.ts（在每次模型调用前执行）
**状态**: 总是启用，无 feature flag
**成本**: 零推理成本（纯内容替换）

#### 工作原理

Budget Reduction 是压缩管线的第一层，在每次模型调用前执行。它的核心职责是：

```
对每个工具结果消息:
  检查大小是否超过 maxResultSizeChars 限制
  ├── 超过 → 替换为"内容引用"（content reference）
  └── 未超过 → 保持原样
```

#### 关键设计决策

**1. 豁免机制**

某些工具被标记为"豁免"，不受预算削减影响：

```typescript
// 工具定义中的 maxResultSizeChars 字段
// 如果为 Infinity 或未设置（非有限值），则该工具的输出不被削减
{
  name: "important_tool",
  maxResultSizeChars: Infinity,  // 豁免：保留完整输出
}

{
  name: "regular_tool",
  maxResultSizeChars: 10000,     // 正常：超过 10000 字符会被替换
}
```

**设计理由**：某些工具的输出对后续推理至关重要（如关键错误信息、结构化数据），不能被截断。

**2. 内容引用（Content Reference）**

论文未给出"内容引用"的确切格式，但可以推断其结构：

```
原始工具结果（15KB）:
┌─────────────────────────────────────────┐
│ import React from 'react';              │
│ import { useState } from 'react';       │
│ ... (15KB 代码内容) ...                  │
│ export default Component;               │
└─────────────────────────────────────────┘

替换后的内容引用（~200 字符）:
┌─────────────────────────────────────────┐
│ [read_file: src/component.tsx, 15KB]    │
│ 前 100 字符: import React from...       │
│ 后 100 字符: ...export default...       │
└─────────────────────────────────────────┘
```

**推断的依据**：
- 论文说"replacing oversized outputs with content references"
- 论文提到"persisted for agent and session query sources to enable reconstruction on resume"
- 这意味着引用包含足够信息让模型知道文件存在、大小、首尾内容

**3. 持久化与恢复**

```typescript
// 内容替换被持久化到磁盘
// 存储在 agent 和 session 查询源中
// 目的：在 session resume 时可以重建

// 伪代码：
persistContentReplacement({
  tool_use_id: "toolu_01ABC...",
  original_content_hash: "sha256:...",
  replacement_pointer: "[read_file: src/main.py, 12KB]",
  source: "agent_query" | "session_query",
  timestamp: Date.now(),
})

// Resume 时：
reconstructFromDisk() → 恢复替换记录，可以继续压缩历史
```

### 1.2 与 Microcompact 的组合设计

**关键洞察**：Budget Reduction 在 Microcompact 之前运行，因为两者在不同层面操作，组合无冲突。

```
执行顺序：
1. Budget Reduction → 检查内容（content-level）
   └─ 替换超大工具输出为引用指针

2. Microcompact → 按 ID 操作（ID-level）
   └─ 通过 tool_use_id 识别要压缩的对
   └─ 不检查内容，只操作结构
```

**为什么这个顺序重要**：

```
如果反过来：
  Microcompact 先运行 → 清除旧的 tool_result 内容
  Budget Reduction 后运行 → 试图检查已清除的内容 → 无效

正确顺序：
  Budget Reduction 先运行 → 检查并替换超大内容
  Microcompact 后运行 → 按 ID 压缩，不关心内容是什么
```

**代码层面的组合**：

```typescript
// query.ts:365-453 的执行顺序
function prepareMessagesForQuery(messagesForQuery) {
  // Layer 1: 总是运行
  messages = applyToolResultBudget(messagesForQuery);
  // 此时：超大工具输出已替换为引用指针
  // 但 tool_use_id 保持不变

  // ... Layer 2: Snip ...

  // Layer 3: 按 tool_use_id 操作
  messages = microcompact(messages);
  // 此时：旧的 tool_use/tool_result 对被压缩
  // 不检查内容，只按 ID 识别
}
```

### 1.3 实际效果预估

```
场景：50 轮对话，每次 read_file 返回 10-50KB 代码

原始状态：
  - 50 个 read_file 调用
  - 平均 20KB/调用
  - 总计 ~1MB 工具输出
  - 约 250K tokens（超出 200K 窗口）

Budget Reduction 后：
  - 50 个 read_file 调用
  - 超过 10KB 的输出被替换为引用指针（~200 字符）
  - 假设 30 个被替换，20 个保留
  - 30 × 200 字符 + 20 × 20KB = 6KB + 400KB = ~406KB
  - 约 100K tokens（减少 60%）

关键保留：
  ✅ tool_use 块（模型记得"我读了哪些文件"）
  ✅ 引用指针（模型知道"文件存在，大小 X KB"）
  ✅ 首尾内容（模型可以看到文件的开头和结尾）
  ❌ 完整内容（丢失，但可以通过再次 read_file 恢复）
```

### 1.4 论文未给出的细节

以下信息在论文中**未明确说明**，需要参考源码或实验推断：

1. **`maxResultSizeChars` 的默认值**
   - 论文只说"configurable size"
   - 推测值：10KB-50KB（基于典型代码文件大小）

2. **内容引用的确切格式**
   - 论文只说"content references"
   - 推测包含：工具名、文件名、大小、首尾片段

3. **哪些工具被标记为豁免**
   - 论文只说"exempt tools"
   - 推测：`search_files`、`grep` 等返回结构化结果的工具可能被豁免

4. **持久化的确切存储位置**
   - 论文说"persisted for agent and session query sources"
   - 推测：存储在 session transcript (JSONL) 中

---

## 二、Context Collapse（Layer 4）：读时投影

### 2.1 核心机制

**函数**: `applyCollapsesIfNeeded()`
**位置**: query.ts（feature-gated，动态 `require()`）
**Feature Flag**: `CONTEXT_COLLAPSE`
**成本**: 零推理成本（纯读时投影）
**状态**: 不修改底层数据

#### 工作原理

Context Collapse 是五层中**唯一不修改消息数组**的层。它是一个**读时投影**（read-time projection），在底层完整历史之上投射一个折叠视图。

```
底层存储 (REPL array)              读时视图 (messagesForQuery)
┌─────────────────────────┐       ┌───────────────────────────┐
│ Turn 1: user+assistant  │       │                           │
│ Turn 2: user+assistant  │       │ [折叠摘要: 前 20 轮]       │
│ Turn 3: user+assistant  │  ──→  │ Turn 21: user+assistant   │
│ ...                     │       │ Turn 22: user+assistant   │
│ Turn 20: user+assistant │       │ ...                       │
│ Turn 21: user+assistant │       │ Turn 50: user+assistant   │
│ ...                     │       └───────────────────────────┘
│ Turn 50: user+assistant │
└─────────────────────────┘
完整历史永不修改              模型只看到折叠视图
（append-only JSONL）          （投影到 messagesForQuery）
```

### 2.2 源码注释解读

论文引用了源码中的关键注释：

> **"Nothing is yielded; the collapsed view is a read-time projection over the REPL's full history. Summary messages live in the collapse store, not the REPL array. This is what makes collapses persist across turns."**

逐句解读：

**"Nothing is yielded"**
- Context Collapse 不产生新的消息
- 不像 Auto-Compact 那样生成摘要消息并插入历史
- 它只是"投射"一个视图

**"read-time projection over the REPL's full history"**
- REPL array 是底层存储（append-only JSONL）
- "read-time" 意味着在读取时动态计算
- "projection" 是数据库术语，指从完整数据中选择一个子集

**"Summary messages live in the collapse store, not the REPL array"**
- 折叠摘要存储在独立的 "collapse store" 中
- 不写入 REPL array（底层历史）
- 这是关键的架构决策

**"This is what makes collapses persist across turns"**
- 因为摘要在独立的 store 中
- 所以跨轮次持久化
- 即使 REPL array 增长，折叠视图仍然有效

### 2.3 与其他层的根本区别

| 层级 | 是否修改消息数组 | 底层数据 | 持久化方式 |
|------|----------------|----------|-----------|
| Budget Reduction | ✅ 修改 | 修改（替换内容） | 写入 REPL array |
| Snip | ✅ 修改 | 修改（删除消息） | 写入 REPL array |
| Microcompact | ✅ 修改 | 修改（清除内容） | 写入 REPL array |
| **Context Collapse** | ❌ 不修改 | **不修改** | **collapse store** |
| Auto-Compact | ✅ 修改 | 修改（追加摘要） | 写入 REPL array |

**为什么 Context Collapse 选择"不修改"？**

```
设计哲学：append-only 设计优先于可审计性

优势：
✅ 可以 resume（从磁盘恢复完整历史）
✅ 可以 fork（基于完整历史创建分支）
✅ 可以 audit（审查完整历史）
✅ 不会丢失信息（只是隐藏，不是删除）

劣势：
❌ 结构化查询需要事后重建
   （如"显示所有修改文件 X 的工具调用"需要扫描完整历史）
```

### 2.4 实现细节推断

论文未给出确切实现，但可以基于架构推断：

#### Collapse Store 的数据结构

```typescript
// 推断的 collapse store 结构
interface CollapseStore {
  sessionId: string;
  collapses: Collapse[];
}

interface Collapse {
  id: string;
  turnRange: [number, number];  // 折叠的轮次范围 [1, 20]
  summary: string;               // 折叠摘要
  createdAt: number;             // 创建时间
  tokenCount: number;            // 摘要的 token 数
}

// 示例：
{
  sessionId: "sess_01ABC...",
  collapses: [
    {
      id: "collapse_001",
      turnRange: [1, 20],
      summary: "前 20 轮：用户要求修复 auth.test.ts，模型读取了 auth.ts、auth.test.ts，发现测试失败原因...",
      createdAt: 1704067200000,
      tokenCount: 500,
    },
    {
      id: "collapse_002",
      turnRange: [21, 40],
      summary: "轮次 21-40：模型修改了 auth.ts，运行测试，修复了 3 个错误...",
      createdAt: 1704067500000,
      tokenCount: 600,
    }
  ]
}
```

#### applyCollapsesIfNeeded() 的伪代码

```typescript
function applyCollapsesIfNeeded(messagesForQuery: Message[]): Message[] {
  if (!feature("CONTEXT_COLLAPSE")) {
    return messagesForQuery;  // Feature flag 关闭，不折叠
  }

  const collapseStore = loadCollapseStore(sessionId);
  if (collapseStore.collapses.length === 0) {
    return messagesForQuery;  // 没有折叠，返回原视图
  }

  // 构建折叠视图
  const collapsedView: Message[] = [];

  for (const collapse of collapseStore.collapses) {
    // 检查当前消息是否在这个折叠范围内
    const messagesInRange = messagesForQuery.filter(
      msg => msg.turnNumber >= collapse.turnRange[0]
          && msg.turnNumber <= collapse.turnRange[1]
    );

    if (messagesInRange.length > 0) {
      // 用折叠摘要替换这些消息
      collapsedView.push({
        role: "system",
        content: `[对话折叠] ${collapse.summary}`,
        turnNumber: collapse.turnRange[0],
        isCollapseSummary: true,
      });
    }
  }

  // 添加未被折叠的消息
  const nonCollapsedMessages = messagesForQuery.filter(
    msg => !collapseStore.collapses.some(
      c => msg.turnNumber >= c.turnRange[0] && msg.turnNumber <= c.turnRange[1]
    )
  );

  collapsedView.push(...nonCollapsedMessages);

  // 按轮次排序
  collapsedView.sort((a, b) => a.turnNumber - b.turnNumber);

  return collapsedView;
}
```

### 2.5 折叠的触发与创建

论文未说明折叠是如何触发的，但可以推断：

```
推断的折叠触发条件：

1. 轮次数量阈值
   - 当对话超过 N 轮（如 50 轮）
   - 自动创建折叠摘要

2. Token 阈值
   - 当历史超过 M tokens（如 100K）
   - 对最早的 N 轮创建折叠

3. 显式触发
   - 用户或系统调用折叠命令
   - 如 "/compact" 或自动压缩

折叠摘要的生成：
- 可能使用 LLM 生成摘要
- 也可能是简单的规则提取（如"前 N 轮，涉及文件 X, Y, Z"）
- 论文未说明
```

### 2.6 与其他压缩层的协作

```
执行顺序与职责分工：

Layer 1 (Budget Reduction):
  └─ 替换单个超大工具输出
  └─ 不关心轮次，只关心单个消息大小

Layer 2 (Snip):
  └─ 丢弃过时的轮次
  └─ 修改 REPL array（删除消息）

Layer 3 (Microcompact):
  └─ 清除旧工具结果内容
  └─ 按 tool_use_id 操作

Layer 4 (Context Collapse):  ← 唯一不修改的层
  └─ 投射折叠视图
  └─ 不修改 REPL array
  └─ 摘要在 collapse store 中

Layer 5 (Auto-Compact):
  └─ LLM 语义压缩
  └─ 生成摘要并写入 REPL array

协作示例：
  1. Budget Reduction 替换大输出 → 减少单消息体积
  2. Snip 丢弃过时轮次 → 减少轮次数量
  3. Microcompact 清除旧结果 → 减少工具数据体积
  4. Context Collapse 投射折叠视图 → 模型看到压缩视图
  5. Auto-Compact 生成摘要 → 最后手段
```

### 2.7 Feature Flag 与动态加载

```typescript
// query.ts 中的 feature-gated 加载
// 由于 bun:bundle tree-shaking 约束，使用动态 require()

// 错误方式（会被 tree-shaking 移除）：
import { applyCollapsesIfNeeded } from "./contextCollapse";
if (feature("CONTEXT_COLLAPSE")) {
  messages = applyCollapsesIfNeeded(messages);
}

// 正确方式（动态 require）：
if (feature("CONTEXT_COLLAPSE")) {
  const { applyCollapsesIfNeeded } = require("./contextCollapse");
  messages = applyCollapsesIfNeeded(messages);
}
```

**为什么用动态 `require()`？**

- Bun 的 bundler 会在编译时做 tree-shaking
- `feature()` 只在 if/ternary 条件中工作
- 静态 `import` 会被 bundler 分析并可能移除
- 动态 `require()` 绕过 tree-shaking，确保代码在运行时可用

### 2.8 实际效果预估

```
场景：100 轮对话，每轮平均 2K tokens

原始状态：
  - 100 轮 × 2K tokens = 200K tokens
  - 刚好达到 200K 窗口上限
  - 无法继续对话

Context Collapse 后（假设折叠前 60 轮）：
  - 折叠摘要：60 轮 → 1 条摘要（~2K tokens）
  - 未折叠消息：40 轮 × 2K tokens = 80K tokens
  - 总计：2K + 80K = 82K tokens
  - 减少 59%
  - 可以继续对话

关键特性：
  ✅ 完整历史仍在磁盘（可以 resume/fork/audit）
  ✅ 模型只看到折叠视图（节省上下文）
  ✅ 折叠摘要持久化（跨轮次有效）
  ✅ 可以"展开"折叠（如果需要审查历史）
```

### 2.9 论文未给出的细节

1. **折叠摘要如何生成**
   - 用 LLM 还是规则？
   - 摘要的质量如何？
   - 论文未说明

2. **折叠的触发条件**
   - 轮次阈值？Token 阈值？显式命令？
   - 论文未说明

3. **折叠摘要的质量控制**
   - 如何确保摘要保留关键信息？
   - 论文未说明

4. **如何"展开"折叠**
   - 用户或系统如何恢复完整历史视图？
   - 论文未说明

5. **多个折叠的合并策略**
   - 如果有多个折叠，如何组合？
   - 论文未说明

---

## 三、对比总结

| 维度 | Budget Reduction | Context Collapse |
|------|-----------------|------------------|
| **层级** | Layer 1 | Layer 4 |
| **成本** | 零 | 零 |
| **Feature Flag** | 无（总是启用） | `CONTEXT_COLLAPSE` |
| **修改消息数组** | ✅ 是 | ❌ 否 |
| **修改底层数据** | ✅ 是（替换内容） | ❌ 否（纯投影） |
| **操作粒度** | 单个消息 | 轮次范围 |
| **保留信息** | 引用指针（首尾+大小） | 折叠摘要 |
| **可恢复性** | 通过磁盘记录恢复 | 完整历史始终可用 |
| **主要目标** | 减少单个超大输出 | 减少长时间对话的体积 |
| **与其他层的关系** | 在 Microcompact 前运行 | 独立投影，不干扰其他层 |
| **持久化** | 写入 REPL array | collapse store（独立） |
| **用户可见性** | 低（内容被替换） | 低（"operates without user-visible output"） |

---

## 四、对 Helen 的启示

### 4.1 Budget Reduction 的启示

**核心思想**：不是删除工具输出，而是替换为"引用指针"

```python
# Helen 可以实现的简化版本

def budget_reduction(messages, max_chars=10000):
    """Budget Reduction: 替换超大工具输出"""
    for msg in messages:
        if msg.role == "tool" and len(msg.content) > max_chars:
            # 保留首尾
            head = msg.content[:200]
            tail = msg.content[-200:]
            # 替换为引用
            msg.content = f"[工具结果: {msg.tool_name}, {len(msg.content)} 字符]\n"
            msg.content += f"前 200 字符: {head}...\n"
            msg.content += f"后 200 字符: ...{tail}"
            msg._original_hash = hash(msg.content)  # 用于恢复
    return messages
```

**关键设计决策**：
1. 保留首尾（模型可以看到文件的开头和结尾）
2. 保留大小信息（模型知道文件的规模）
3. 保留 tool_use_id（与 Microcompact 组合）

### 4.2 Context Collapse 的启示

**核心思想**：不修改底层数据，只投射视图

```python
# Helen 可以实现的简化版本

class CollapseStore:
    """折叠存储"""
    def __init__(self):
        self.collapses = []  # List[Collapse]

    def add_collapse(self, turn_range, summary):
        self.collapses.append({
            "turn_range": turn_range,
            "summary": summary,
        })

def context_collapse(messages, collapse_store):
    """Context Collapse: 投射折叠视图"""
    collapsed_view = []

    # 添加折叠摘要
    for collapse in collapse_store.collapses:
        start, end = collapse["turn_range"]
        collapsed_view.append({
            "role": "system",
            "content": f"[对话折叠: 轮次 {start}-{end}]\n{collapse['summary']}",
        })

    # 添加未被折叠的消息
    for msg in messages:
        if not any(start <= msg.turn <= end for start, end in collapse_store.get_ranges()):
            collapsed_view.append(msg)

    return collapsed_view
```

**关键设计决策**：
1. 不修改 `messages` 列表（底层历史）
2. 返回新的 `collapsed_view`（读时投影）
3. 折叠摘要在独立的 `CollapseStore` 中

---

## 五、参考资料

- arXiv:2604.14228v2 — "Dive into Claude Code: The Design Space of Today's and Future AI Agent Systems" (Liu et al., UCL, April 2026)
- Claude Code 源码 v2.1.88（通过论文分析推断）
- query.ts:365-453（压缩管线执行位置）
- compact.ts（Auto-Compact 实现）
- sessionStorage.ts（session 持久化）
