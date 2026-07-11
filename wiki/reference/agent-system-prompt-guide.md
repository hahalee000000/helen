# Agent 提示词工程完全指南 — 来自 Claude Code 逆向工程的启示

> 基于对 Claude Code v2.0.14 系统提示词的逆向工程、DeepAgents 框架源码分析，以及 Helen 语言自身的 agent 设计实践。
> 原文：[The Complete Guide to Writing Agent System Prompts](https://fengliu.substack.com/) — Feng Liu, 2026-03-20
> 本文：针对 Helen 语言改写，所有示例均为 Helen 语法

**日期**：2026-07-11
**适用版本**：Helen v1.17+

---

## 〇、本文定位

这篇指南回答一个问题：**如何为 Helen 的 agent 写出高质量的 `prompt` 和 `description`？**

它不教 Helen 语法（见 [[syntax/grammar]] 与 [[tutorial/05-agents]]），而是聚焦于 **agent 提示词的设计哲学、结构布局、写作原则、常见反模式**——这些是语法之外、决定 agent 质量的"软知识"。

核心洞察来自对 Claude Code 系统提示词的逆向工程。Claude Code 本身就是一个复杂的 agent，其系统提示词经过 Anthropic 大量实战打磨。我们把这些经验**翻译到 Helen 的语境**—— Helen 的 `agent {}` 块、`prompt`/`description` 字段、`tools` 列表、`context {}` 配置，就是 Helen agent 的"系统提示词"。

---

## 一、设计哲学：Harness Mindset

> "An agent is a model. Not a framework. Not a prompt chain." — shareAI-lab/learn-claude-code

LLM 已经会推理、规划、执行。你的 agent 提示词**不是教它思考**，而是**为它搭建工作环境**。

像招一个资深工程师：你不会给他一份 20 步清单让他一步步照做。你会说：**我们是谁、边界在哪、什么是好的交付**，然后让他自己干活。

### 1.1 Agent 提示词的四项职责

Helen agent 的 `prompt` 只有四件事要做：

| # | 职责 | Helen 字段 | 例子 |
|---|------|-----------|------|
| 1 | 告诉它**是谁** | `description` | `"Review code for bugs and security issues"` |
| 2 | 画出**边界** | `prompt` + `@sandbox` | `NEVER expose API keys` |
| 3 | 定义**什么是好** | `prompt` | `Always explain changes before making them` |
| 4 | 提供**工具和知识** | `tools` + `load_skill` | `tools = ["read_file", "shell_exec"]` |

其他一切都是噪声。

### 1.2 Harness 公式

```
Harness = 工具 + 知识 + 观察 + 行动接口 + 权限
```

Helen 的实现：
- **工具**：`tools = [...]` 列表，10 个内置 + `load_skill` 加载领域知识
- **知识**：`prompt` 中的领域上下文 + 通过 `{{}}` 注入的环境事实
- **观察**：`working-memory`、`transcript`、`:stats`
- **行动接口**：`llm act` + 工具调用循环
- **权限**：`@open` / `@strict` / `@sandbox` 隔离级别

不要把 agent 写成流程图——模型会自己决定执行顺序。

---

## 二、提示词结构布局

### 2.1 推荐顺序（逆向工程自 Claude Code v2.0.14）

```
┌─────────────────────────────────────────────┐
│ 1. 身份 Identity             │ ← 首读，锚定行为
│ 2. 安全边界 Safety           │ ← IMPORTANT 标记，不可妥协
│ 3. 语气风格 Tone & Style     │ ← 控制输出形态
│ 4. 核心工作流 Core Workflow  │ ← 如何干活
│ 5. 工具使用策略 Tool Policy  │ ← 工具选择优先级
│ 6. 领域知识 Domain Knowledge │ ← 按需加载，不预填
│ 7. 环境信息 Env Info         │ ← 运行时注入
│ 8. 关键提醒 Reminders        │ ← 重申最重要规则
├─────────────────────────────────────────────┤
│ [工具定义 — 系统自动注入]     │ ← 不可编辑，通常很长
├─────────────────────────────────────────────┤
│ [用户消息]                    │
└─────────────────────────────────────────────┘
```

### 2.2 为什么这个顺序

LLM 有 **U 形注意力曲线** —— 对开头和结尾最关注，中段容易"失忆"（"Lost in the Middle" 效应）。

- **身份 + 安全放开头**：primacy effect（首因效应）
- **核心工作流放中上段**：最重要的内容
- **工具定义由系统注入**：Claude Code 的工具定义约 11,438 tokens，会把你的自定义内容"推"回前面——反而提升依从性
- **关键提醒放结尾**：recency effect（近因效应）

Claude Code 把安全声明在开头和结尾各写一遍——不是工程师健忘，是懂 U 形注意力。

---

## 三、Helen agent 的提示词结构

### 3.1 完整示例

```helen
agent CodeReviewer {
    // ── 1. 身份 ──────────────────────────────────────
    description "Review code for correctness, security, and style"

    // ── 2-8. 完整 prompt ────────────────────────────
    prompt """
    You are a senior code reviewer with 20 years of experience.

    IMPORTANT: NEVER suggest changes that break backward compatibility.
    IMPORTANT: NEVER expose secrets, tokens, or credentials in code or output.

    ## Tone and style
    - Short, direct, technical. No flattery or filler.
    - Professional objectivity: prioritize truth over validating the user.
    - Use GitHub-flavored markdown.

    ## Core workflow (principles, not steps)
    - Understand before modifying — always read existing code first.
    - Minimal changes — only change what's necessary.
    - Verify — suggest how to test the changes.
    - Explain the "why" — every suggestion includes rationale.

    ## Tool usage
    - Use `read_file` to inspect code; avoid `shell_exec` for file inspection.
    - Use `search_files` to find references before suggesting renames.
    - If a tool call is denied, do NOT retry the same call — reconsider.

    ## Environment
    Working directory: {{cwd}}
    OS: {{os_name()}}
    Current time: {{now()}}
    Git branch: {{shell_exec("git branch --show-current")}}

    ## Reminders
    IMPORTANT: Minimal changes. Explain why. Never break compatibility.
    """

    tools = ["read_file", "search_files", "shell_exec"]
    model "qwen3.7-plus"
    temperature 0.3
    max-turns 10
    context {
        working-memory true
        compression "graduated"
        cache-aware true
    }

    main {
        return llm act "Review the changes in the current diff"
    }
}
```

### 3.2 Helen 字段映射

| 通用原则 | Helen 字段 | 说明 |
|---------|-----------|------|
| Identity | `description` | 1-3 句，锚定角色 |
| Safety / Tone / Workflow / … | `prompt` | 用 markdown 分段 |
| 工具策略 | `prompt` 内说明 + `tools` 列表 | 列表控制**能用什么**；prompt 控制**何时用** |
| 环境信息 | `prompt` 中用 `{{}}` 插值 | **永远注入，不要假设**（见 §7） |
| 按需知识 | `tools = [..., "load_skill"]` + `load_skill("xxx")` | 两层披露，不要知识倾倒 |
| 提醒 | `prompt` 末段 | 重申最重要的 2-3 条 |
| 上下文策略 | `context {}` 块 | 压缩、工作记忆、缓存感知 |

---

## 四、逐节写作指南

### 4.1 Identity — 是谁

**目标**：1-3 句话锚定角色。

```helen
// ✅ 好
description "Senior Rust engineer specializing in concurrent systems"

// ❌ 空泛
description "A helpful AI assistant"

// ❌ 太长（浪费 token）
description "You are a wise and experienced software engineer who has worked at many top tech companies and has deep knowledge of..."
```

### 4.2 Safety — 硬边界

**目标**：不可违反的行为约束。

```helen
prompt """
IMPORTANT: NEVER generate or guess URLs for the user.
IMPORTANT: NEVER execute `rm -rf` or other destructive shell commands without confirmation.
MUST NOT modify files outside the working directory.
"""
```

写作要点：
- 用 `IMPORTANT:` 前缀 — Claude 的指令层级训练对它有额外权重
- 用绝对语言：`NEVER` / `MUST NOT` / `Refuse to`
- 双向约束：同时说明**允许**和**禁止**
- 开头放一次、结尾再放一次（U 形注意力双保险）

### 4.3 Tone & Style — 输出形态

**目标**：具体可测试的行为规则。

```helen
prompt """
## Tone and style
- Short and concise. No filler phrases.
- Only use emojis if the user explicitly requests it.
- Use GitHub-flavored markdown.
- Professional objectivity: prioritize technical accuracy over validating the user's beliefs.
"""
```

**关键**：「专业客观性」这一段极其重要——它压制模型的"谄媚倾向"。如果 agent 要做判断（代码评审、架构选择、方案评估），必须有类似条款。

### 4.4 Core Workflow — 最重要的一节

**目标**：教模型**如何工作**——方法论，不是机械步骤。

核心原则：**给原则，不给流程**（Give principles, not procedures）。

```helen
// ✅ 原则（可泛化）
prompt """
Core workflow:
- Understand existing code before modifying it.
- Plan before executing complex changes.
- Make minimal changes — don't refactor while you're in there.
- Verify your changes work (run tests, lint).
"""

// ❌ 流程（僵化）
prompt """
Step 1: Read the file.
Step 2: Find the bug.
Step 3: Fix it.
Step 4: Run tests.
Step 5: Commit.
"""
```

原则可以泛化到模型没见过的场景；流程只能在预期内执行。

**例外**：当输出要被下游**机器**消费时（agent 间通信、API 响应格式），才用严格 schema——原则管行为，schema 管接口。

### 4.5 Tool Usage Policy — 消歧

**目标**：多个工具能做同一件事时，告诉模型优先选哪个。

```helen
prompt """
## Tool usage
- Use `read_file` for reading files instead of `shell_exec cat`.
- Use `patch_file` for small edits instead of `write_file` rewrite.
- Use `search_files` for content search instead of `shell_exec grep`.
- Call independent tools in parallel when possible.
- If a tool call is denied, do NOT re-attempt the exact same call.
  Think about why it was denied and adjust your approach.
"""
```

要点：
- 用 "A instead of B" 表达优先级
- 说明**为什么**优先（"reduces context usage"、"better user experience"）
- 定义并行策略（独立 → 并行，依赖 → 顺序）
- 处理工具被拒的场景——否则模型会无限重试

### 4.6 Domain Knowledge — 按需加载

**核心原则**：渐进披露，不要知识倾倒。

```helen
// ❌ 把 200 个 API 都塞进 prompt → token 爆炸
prompt "Here is the complete API documentation: ..."

// ✅ 让 agent 按需加载
agent Worker {
    tools = ["load_skill", "read_file"]
    main {
        let guide = load_skill("helen-testing")
        return llm act "Follow this guide: " + guide
    }
}
```

Helen 的 Skills 系统（两层披露）就是为此设计的：
- **Tier 1**：系统提示词里只注入**技能索引**（名字 + 描述 + 标签）
- **Tier 2**：agent 通过 `load_skill` 工具按需加载完整内容

### 4.7 Environment Info — 运行时事实

**核心原则**：**永远注入，永不假设**——agent 无法知道你未告知的事实。

```helen
// ✅ 注入真实值
agent DevAgent(cwd: str) {
    prompt """
    Working directory: {{cwd}}
    OS: {{os_name()}}
    Current time: {{now()}}
    Git branch: {{shell_exec("git branch --show-current")}}
    """
    main { return llm act "..." }
}

// ❌ 让 LLM 猜
prompt "You are a helpful engineer."
// LLM 不知道 cwd，会编一个听起来合理的
```

LLM 被训练成"必须回答"——缺上下文时它会自信地编造。注入事实把这个故障模式变成非问题。

详见 [[helen-agent-patterns § 最佳实践 7]]。

### 4.8 Reminders — 最后强化

只重申 2-3 条**最**重要的规则：

```helen
prompt """
[... 前面几节 ...]

## Reminders
IMPORTANT: Minimal changes only.
IMPORTANT: Explain the "why" for every suggestion.
IMPORTANT: NEVER break backward compatibility.
"""
```

---

## 五、Token 预算

### 5.1 推荐分配

| 章节 | 推荐 token | 说明 |
|------|-----------|------|
| Identity + Safety | 200-500 | 简洁但不可妥协 |
| Tone & Style | 300-800 | 规则必须具体 |
| Core Workflow | 500-2,000 | 最重要，值得花 token |
| Tool Usage Policy | 300-1,000 | 取决于工具数量 |
| Domain Knowledge | 0-1,000 | 优先按需加载 |
| Environment Info | 100-300 | 动态生成 |
| Reminders | 100-300 | 只重申 essentials |
| **你的部分合计** | **1,500-6,000** | |
| 工具定义（系统注入） | 5,000-15,000 | 不在你控制范围 |

### 5.2 上下文退化曲线

社区实测（Reddit u/CodeMonke_）的真实依从性退化：

| 上下文长度 | 依从性 |
|-----------|--------|
| < 80K tokens | 稳定 |
| 80K - 120K | 指令遵循开始退化 |
| > 120K | 显著退化——模型"忘记"早期指令 |
| > 180K | 严重退化 |

**200K 上下文窗口 ≠ 200K 有效上下文**。

Helen 的应对：
- `context { compression "graduated" }` — 五层渐进压缩
- `context { cache-aware true }` — 缓存感知，保留稳定前缀
- `context { working-memory true }` — 工作记忆自动跟踪关键信息

---

## 六、写作原则

### 6.1 原则优先，而非流程

```
❌ "Step 1: Read file. Step 2: Find bug. Step 3: Fix. Step 4: Test."
✅ "Always understand existing code before modifying it. Verify your changes work."
```

原则能泛化；流程只能机械执行，遇到意外就僵住。

### 6.2 硬约束用绝对语言

| 强度 | 用词 | 用于 |
|------|------|------|
| 绝对禁止 | `NEVER` / `MUST NOT` | 安全、不可逆操作 |
| 强要求 | `ALWAYS` / `MUST` | 核心工作流规则 |
| 推荐 | `recommended` / `prefer` | 有例外的最佳实践 |
| 建议 | `consider` / `you may` | 可选优化 |

### 6.3 用例子代替解释

```helen
prompt """
## Code references
When referencing code, use `file_path:line_number` format.

<example>
user: Where are client errors handled?
assistant: Clients are marked as failed in `connectToServer`
           at src/services/process.ts:712.
</example>
"""
```

一个例子胜过 100 字解释。用 `<example>` 标签包裹；同时提供正反例。

### 6.4 双向约束

```
✅ "Use `read_file` for reading files."
✅ "Do NOT use `shell_exec cat` for file inspection."
双向 → 清晰无歧义。
```

只说"做这个"→ 模型不知何时不该做；只说"别做这个"→ 模型不知该用什么替代。

### 6.5 解释 why，不只 what

```
❌ "Don't use `git commit --amend`."
✅ "Avoid `git commit --amend`. Reason: amending may overwrite others' commits.
    ONLY use --amend when you explicitly requested it."
```

解释 why 让模型能在边缘情况下做出正确判断。

### 6.6 结构优先于散文

- **Markdown 标题** (`##` / `###`) — 模型识别层级
- **列表** 优先于段落 — 每条规则独立可测
- **XML 标签** 包裹特殊内容：`<example>`、`<env>`
- **表格** 用于对比和映射

永远不要倾倒非结构化文本——结构化 prompt 在依从性测试中**始终**优于自然语言散文。

---

## 七、反模式——这些在浪费你的 token

### 7.1 伪装成 agent 的 prompt chain

```
❌ "First call tool A. Then tool B with result. Then format JSON. Then save."
```

这不是 agent prompt，是流水线脚本。模型会机械执行，失去自主规划能力。

**修复**：告诉模型**目标和约束**，让它自己决定步骤。

### 7.2 谄媚工程

```
❌ "You are an EXTREMELY TALENTED and INCREDIBLY EXPERIENCED senior engineer..."
```

赞美和最高级形容词**不提升输出质量**。模型没有自尊心需要哄。省这 15 个 token 写真正的规则。

### 7.3 知识倾倒

```
❌ "Here is the complete API documentation for our 200 endpoints..."
```

吃掉上下文窗口，加速上下文腐烂。

**修复**：按需加载——"use `load_skill` to retrieve documentation when needed."

### 7.4 重复工具定义

工具定义已经说"`read_file` reads a file"——不要在 prompt 里再说一遍。
只在 prompt 里写**工具定义没覆盖的内容**：何时用、为何优先、优先级。

### 7.5 缺失的失败处理

不告诉模型"工具被拒怎么办"，它就会无限重试失败的调用。

**必须包含**：
```
If a tool call is denied, do not re-attempt the exact same call.
Think about why it was denied and adjust your approach.
```

### 7.6 忽视上下文窗口衰减

200K 上下文 ≠ 200K 有效上下文。实测 80K 开始退化。

**必须有压缩策略**——Helen 的 `context { compression "graduated" }` 是默认行为，但你应该了解它在做什么。

---

## 八、动态注入——被忽视的利器

### 8.1 为什么需要

系统提示词只在对话开头出现一次。随着对话变长，模型对早期指令的依从性会衰减（80K+ tokens 明显）。**在对话中途注入提醒 = 通过近因效应刷新规则**。

心智模型：
- **系统提示词 = 宪法**：一次确立，长期权威
- **中途注入 = 备忘录**：定期发送，维持执行力度

### 8.2 Helen 的注入机制

Helen 通过多种方式实现中途注入：

| 机制 | 位置 | 触发 |
|------|------|------|
| `prompt` + `{{}}` 插值 | agent 启动时 | 每次 agent 调用 |
| `working-memory` | 系统消息内 | 自动跟踪文件/决策/TODO/错误 |
| `context { compression }` | 上下文压缩时 | 自动渐进压缩 |
| `load_skill` 工具 | 工具调用结果 | agent 按需 |
| 工具结果 | tool message | 每次工具返回 |

### 8.3 注入的最佳实践

- **用 XML 标签包裹**（`<system-reminder>`）— 模型能区分系统注入和用户发言
- **不要每条消息都注入**——每次注入都消耗 token，只在必要时注入
- **保持简短**——提醒不是第二个系统提示词，只重申 1-2 条关键规则
- **不要与系统提示词矛盾**——提醒是补充和强化，不是覆盖
- **用于动态切换**——plan mode、readonly mode、feature flags

### 8.4 System Prompt vs. 中途注入：分工

| 场景 | 系统提示词 | 中途注入 |
|------|----------|---------|
| 角色定义 | ✅ | ❌ |
| 安全约束 | ✅ 首次声明 | ✅ 周期性重复 |
| 工作流方法论 | ✅ | ❌ |
| 模式切换（plan mode） | ❌ | ✅ |
| 文件变更通知 | ❌ | ✅ |
| 日期 / 环境 | ✅ 初始值 | ✅ 更新值 |
| 行为纠正 | ❌ | ✅ |
| 工具使用提醒 | ✅ 规则定义 | ✅ 执行推动 |

---

## 九、Prompt Cache — 节省 90% 重复 token

### 9.1 关键数字

| 指标 | 值 |
|------|-----|
| Cache 命中成本 | 正常价的 10%（节省 90%） |
| Cache 写入成本 | 正常价的 125%（首次多 25%） |
| Cache TTL | 5 分钟 |
| 最小可缓存长度 | 1,024 tokens |
| 缓存粒度 | 前缀匹配 |

### 9.2 如何改变 prompt 设计

**核心原则**：静态内容在前，动态内容在后。

```
✅ Cache 友好布局：
System prompt (静态)             ← Cache breakpoint 1
Tool definitions (静态)          ← Cache breakpoint 2
Project rules (偶尔变)           ← Cache breakpoint 3
Conversation history           ← Breakpoint 4 滚动窗口

❌ Cache 破坏布局：
System prompt
  DYNAMIC TIMESTAMP             ← 每次请求都变，后面全部 cache miss
Tool definitions
Conversation history
```

**陷阱**：在系统提示词中间放动态时间戳，后面所有内容都变成 cache miss。一个放错位置的时间戳就能让你为几千 token 付全价。

### 9.3 设计建议

- 系统提示词里**不放高频动态值**——日期（每日变）可以，精确时间戳不行
- 动态上下文（git status 等）放**中途注入**，不要放系统提示词
- 保持工具定义稳定——不要运行时动态增删工具
- 对话历史用**滚动窗口**——缓存前 N 条，只有最新的是 cache miss

Helen 的 `context { cache-aware true }` 就是为此设计的——保留前 30% 消息作为稳定前缀，把缓存命中率从 10-20% 提到 70-80%。

---

## 十、Checklist

写完 agent prompt 后，对照此清单：

### 结构
- [ ] 身份（description）在最前面？
- [ ] 安全约束用 `IMPORTANT:` 标记，结尾重复？
- [ ] 各节用 `##` / `###` 清晰分隔？
- [ ] 例子用 `<example>` 标签包裹？

### Token 预算
- [ ] 你自己的部分 < 6,000 tokens？
- [ ] 没有重复工具定义已有的内容？
- [ ] 领域知识按需加载，不是预填？
- [ ] 没有冗长的角色背景故事？

### 规则质量
- [ ] 每条规则可 true/false 测试？
- [ ] 硬约束用绝对语言（NEVER/MUST）？
- [ ] 软建议用推荐语言（recommended/prefer）？
- [ ] 关键规则解释了 why，不只是 what？
- [ ] 双向约束（要做 + 不要做）？

### Agent 行为
- [ ] 给原则，不是 20 步机械流程？
- [ ] 处理了"工具调用被拒"场景？
- [ ] 处理了"遇到障碍"策略（不要暴力重试）？
- [ ] 有上下文管理策略（压缩阈值）？

### 不该有的
- [ ] 没有谄媚/最高级形容词？
- [ ] 没有多余的"you are a helpful AI"？
- [ ] 不是伪装成 agent 的 prompt chain？
- [ ] 没有用户没要求的功能？

---

## 十一、如果今天重新开始

作者（以及我们）的建议：

1. **前 3 行**就写完身份 + 安全。两句讲 agent 是谁；硬约束用 NEVER/MUST；结尾重复安全规则。
2. **核心工作流写成原则**，最多 4-5 条。软规则用 `recommended`/`prefer`，硬规则用 `NEVER`/`MUST`。
3. **你的部分预算 1,500-6,000 tokens**。工具定义会再加 5,000-15,000。超过 6K 说明你在倾倒应该按需加载的知识。
4. **一切结构化**——Markdown 标题、列表、XML 例子。结构化 prompt 始终胜过自然语言散文。
5. **从第一天就设计中途注入**——系统提示词里声明 `<system-reminder>` 标签；用它刷新关键规则、切换模式、更新上下文。
6. **为缓存设计**——静态在前、动态在后。永远不要在系统提示词主体里放高频变化值。

> **讽刺的是，最好的系统提示词都很短**。Claude Code 的自定义指令（不算工具定义）短得出人意料。每一行都挣到了它的位置。
>
> 提示词工程不是找巧妙窍门，而是纪律——说得更少、说得更准、相信模型自己想明白剩下的。
>
> **模型比你的提示词聪明。设计环境，而不是设计行为。**

---

## 参考

| 来源 | 关键洞察 |
|------|---------|
| Claude Code v2.0.14 系统提示词 | 完整生产 agent prompt 结构参考 |
| Reddit: Understanding Claude Code's 3 System Prompt Methods | Output Styles / --append / --system-prompt 深度解析；上下文腐烂实测数据 |
| shareAI-lab/learn-claude-code | "The model is the agent" 哲学；Harness 工程方法论 |
| Anthropic Prompt Engineering Docs | 官方 prompt 最佳实践 |
| DeepAgents Framework | 渐进披露中间件、Summarization 策略 |
| Feng Liu, "The Complete Guide to Writing Agent System Prompts", 2026-03-20 | 本文原始材料 |

## 相关 Helen 文档

- [[tutorial/05-agents]] — Helen agent 语法入门
- [[tutorial/11-building-agents]] — 多 agent 系统构建
- [[runtime/prompt-builder]] — Helen 提示词构建系统实现
- [[runtime/context-management]] — 上下文管理架构（权威文档）
- `helen-agent-patterns` 技能 — 设计模式与最佳实践
- `helen-agent-collaboration` 技能 — 多 agent 协作模式
