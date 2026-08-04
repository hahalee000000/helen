# Helen Agent Memory 系统 vs Claude Code 对比分析

> 分析时间: 2026-08-03
> 对照 Helen 版本: v1.30.11
> 分析范围: ChatSessionActor memory 架构 + Claude Code CLAUDE.md / memory 机制

---

## 目录

1. [Helen Agent Memory 架构概览](#一helen-agent-memory-架构概览)
2. [功能角色对齐](#二功能角色对齐两个系统各有三层结构)
3. [静态指令层: CLAUDE.md vs 硬编码 prompt](#三静态指令层-claudemd-vs-硬编码-prompt)
4. [项目知识层: memory/*.md vs MEMORY.md](#四项目知识层-memorymd-vs-memorymd)
5. [用户偏好层: memory/ type=user/feedback vs USER.md](#五用户偏好层-memory-typeuserfeedback-vs-usermd)
6. [Claude Code 的维护机制](#六claude-code-的维护机制)
7. [架构核心差异](#七架构核心差异)
8. [Helen 缺失 CLAUDE.md 等价物的问题](#八helen-缺失-claudemd-等价物的问题)
9. [对 Helen 的改进建议](#九对-helen-的改进建议)

---

## 一、Helen Agent Memory 架构概览

Helen 的 memory 系统由三部分组成：

```
.helen/
├── MEMORY.md    (≤ 5KB) — Agent 记忆（历史知识）
├── USER.md      (≤ 2KB) — 用户偏好
└── archive/
    └── YYYY-MM.md  — 归档（当文件超限时）
```

**核心代码位置**：

| 文件 | 职责 |
|------|------|
| `helen/agent/memory_utils.helen` | 读写逻辑 + 5 个核心函数 |
| `helen/agent/context.helen` | env_context XML 构建 |
| `helen/agent/chat_tui.helen` (line 33-60) | spawn 时组装 env_context |
| `helen/agent/chat_session_actor.helen` (line 43-68) | `{{env_context}}` 模板注入 |
| `helen/agent/commands.helen` (line 298-315) | `/memory` 斜杠命令 |
| `helen/agent/contracts/contracts.helen` | CHAT_TOOLS 列表（含 update_memory） |

### 1.1 核心函数

```helen
// memory_utils.helen

fn load_memory(): str                         // 读取 .helen/MEMORY.md
fn load_user_preferences(): str               // 读取 .helen/USER.md
fn build_memory_context(): str                // 构建记忆上下文（注入 prompt）
fn update_memory(category, key, value): map   // 追加/更新 MEMORY.md 条目
fn update_user_preference(category, pref): map // 追加 USER.md 条目
```

### 1.2 MEMORY.md 格式

```markdown
# HelenAgent Unified Context

> Agent 启动时加载的统一上下文入口。

## error_patterns
- **shared_let_write_back**: Agent 内修改 shared let 后...
- **transcript_session_mismatch**: spawn resume 时...

## helen_syntax
- **chinese_keywords**: 91 bilingual keywords...
```

### 1.3 USER.md 格式

```markdown
# User Preferences

> Captured during interactions.

## coding_style
- 偏好简洁输出
- 中文回复
```

### 1.4 注入路径

```helen
// chat_tui.helen:33-60
let all_facts = collect_all_facts()
let env_ctx = build_full_context_xml(all_facts)        // <context> XML
let proj_ctx = build_project_context_xml(proj_facts)   // <project_context> XML
let memory_ctx = build_memory_context()                // "## Agent 记忆" + "## 用户偏好"

full_env_context = env_ctx + "\n" + proj_ctx + "\n" + memory_ctx

// 作为参数传给 spawn ChatSessionActor(..., full_env_context)
mailbox = spawn ChatSessionActor(get_cwd(), sid, full_env_context) resume(child_sid)
```

```helen
// chat_session_actor.helen:62-68
agent ChatSessionActor(cwd, session_id, env_context, reply) {
    prompt """
    ## Identity
    You are HelenAgent...
    {{env_context}}        // <-- memory 在此注入
    <framework_instructions>...</framework_instructions>
    ...
    """
}
```

### 1.5 关键设计特征

- **Spawn 时一次性注入** —— 会话中途不动态重载
- **全量注入** —— 整个 MEMORY.md 内容拼入 prompt，每轮 LLM 调用都重发
- **硬性大小限制** —— MEMORY.md ≤ 5KB, USER.md ≤ 2KB
- **手动归档** —— 超限需手动归档到 `.helen/archive/YYYY-MM.md`
- **Exit 提醒** —— `pre_exit_check()` 检查大小并提示"如本次会话有重要学习，请调用 update_memory 保存"
- **斜杠命令** —— `/memory` 只显示文件大小，不显示内容、不提供搜索

---

## 二、功能角色对齐：两个系统各有三层结构

```
Claude Code                          Helen Agent
─────────────                        ─────────────
① 静态项目指令  → CLAUDE.md          → chat_session_actor.helen 的硬编码 prompt
② 项目知识记忆  → memory/*.md        → .helen/MEMORY.md
③ 用户偏好      → memory/ (type=user)→ .helen/USER.md
                   + type=feedback
```

**关键发现**：Helen 没有 CLAUDE.md 的等价物 —— 它的"项目指令"是硬编码在 agent 源码里的。这是两个架构最根本的区别。

| 角色 | Claude Code | Helen Agent |
|------|-------------|-------------|
| **静态项目指令** | `CLAUDE.md`（用户可编辑，分层加载） | `prompt """..."""`（硬编码在 .helen 源码） |
| **项目知识积累** | `memory/*.md`（多文件 + frontmatter + 按需召回） | `.helen/MEMORY.md`（单文件 + 全量注入 + 5KB 限制） |
| **用户偏好** | `memory/*.md` 中 `type=user/feedback`（与项目知识共用机制） | `.helen/USER.md`（独立文件 + 全量注入 + 2KB 限制） |

---

## 三、静态指令层: CLAUDE.md vs 硬编码 prompt

### 3.1 Claude Code 的 CLAUDE.md

- 用户/维护者用**纯 Markdown 编辑**
- 每次对话**自动注入** system prompt（无需重新编译/重启）
- **分层加载**：`~/CLAUDE.md`（全局）→ `project/CLAUDE.md`（项目）→ 子目录 `CLAUDE.md`
- 改完即生效 —— 零部署成本

### 3.2 Helen Agent 的硬编码 prompt

```helen
// chat_session_actor.helen:62-195
prompt """
## Identity
You are HelenAgent, an AI programming assistant running on the Helen language runtime.
You help users write, debug, and understand Helen programs.
...
{{env_context}}

<framework_instructions>
    <P0 name="grounding">
        NEVER assume environmental facts...
    </P0>
    <P0 name="diagnosis">
        Before proposing a fix, MUST complete root cause investigation...
    </P0>
</framework_instructions>

## Security & Safety
## Tone & Style
## Development Workflow
## Debugging Workflow
## Core Workflow
## Tool Usage Policy
## Automatic Memory Management
## Memory Size Management
- .helen/MEMORY.md: ≤ 5KB
- .helen/USER.md: ≤ 2KB
...
"""
```

### 3.3 对比

| 维度 | CLAUDE.md | Helen 硬编码 prompt |
|------|-----------|---------------------|
| **谁改** | 用户/维护者 | 语言开发者 |
| **怎么改** | 编辑 .md 文件 | 改 .helen 源码 |
| **生效速度** | 下次对话立刻生效 | 需要重新部署 Helen agent |
| **粒度** | 每个项目/子目录可定制 | 所有项目共享同一份 prompt |
| **表达力** | Markdown 自由格式 | 模板 + XML + 变量 |
| **版本控制** | 随项目 git 提交 | 随 Helen 源码发布 |

---

## 四、项目知识层: memory/*.md vs MEMORY.md

### 4.1 Claude Code memory/（项目知识）

每个记忆是一个**独立 .md 文件**，带 frontmatter：

```markdown
---
name: helen-top-level-restriction
description: v1.17 E0355: 只允许声明+main{}在顶层
metadata:
  type: project
---

正文内容...

相关记忆: [[helen-layer-discipline]], [[verify-before-claiming]]
```

`MEMORY.md` 是**索引文件**（每行一个记忆的一行摘要）：

```markdown
- [Helen 顶层裸代码禁令](helen-top-level-restriction.md) - v1.17 E0355: 只允许声明+main{}在顶层
- [Helen Skill SSOT 规则](helen-skills-ssot.md) - helen/skills/ 是真源，.claude/skills/ 是派生镜像
- [论断架构前必须 grep 源码](verify-before-claiming.md) - 禁止凭印象推断 Helen 能力
```

**加载机制**：
- `MEMORY.md` 索引在对话开始注入 `system-reminder`（用户 auto-memory 区）
- 每行只显示标题 + 一句话 hook，不加载全文
- 对话中 Claude 根据当前任务判断相关性，按需 `Read` 具体文件

### 4.2 Helen `.helen/MEMORY.md`（项目知识）

**单文件、扁平结构** —— `## category` + `- **key**: value`

```markdown
# HelenAgent Unified Context

> Agent 启动时加载的统一上下文入口。

## error_patterns
- **shared_let_write_back**: Agent 内修改 shared let 后...
- **transcript_session_mismatch**: spawn resume 时...

## helen_syntax
- **chinese_keywords**: 91 bilingual keywords...
```

**加载机制**：
- **全量注入** —— 整个文件内容在 spawn 时拼入 prompt，每轮 LLM 调用都重发
- **无按需召回** —— 全部塞入 context
- **硬性 5KB 上限** —— `pre_exit_check` 检查，超限要手动归档到 `.helen/archive/`

### 4.3 对比

| 维度 | Claude Code memory/ | Helen MEMORY.md |
|------|--------------------|-----------------|
| **结构** | 多文件 + frontmatter + 链接图 | 单文件 + 分类 Markdown |
| **加载** | 索引常驻，内容按需 | 全量注入 |
| **上限** | 无硬限制 | 5KB |
| **召回** | 相关性自动召回 | 无（全量） |
| **维护** | LLM 用 Write 创建文件 + 改索引 | `update_memory(cat, key, val)` 工具 |
| **链接** | `[[name]]` 互联 | 无 |
| **过期** | 7 天自动过期（scheduled tasks） | 永不过期，需手动归档 |
| **元数据** | frontmatter（name/description/type） | 无（仅分类名） |

---

## 五、用户偏好层: memory/ type=user/feedback vs USER.md

### 5.1 Claude Code

- 用户偏好和项目知识**共用同一套文件机制**
- 通过 frontmatter 的 `type: user` 或 `type: feedback` 区分
- 在 `MEMORY.md` 索引里统一展示（`- [Title](file.md) - hook`）
- 在 system-reminder 中以 `(user's auto-memory)` 统一注入

### 5.2 Helen `.helen/USER.md`

- **独立文件**，与 MEMORY.md 物理分离
- 写入工具是 `update_user_preference(category, preference)`
- **硬性 2KB 上限**
- 在 `build_memory_context()` 中单独拼接为 `## 用户偏好` section

### 5.3 对比

| 维度 | Claude Code (type=user/feedback) | Helen USER.md |
|------|----------------------------------|---------------|
| **物理隔离** | 否（与项目记忆共用文件） | 是（独立文件） |
| **区分方式** | frontmatter `type` 字段 | 文件路径 |
| **写入** | `Write` 工具创建 `memory/<name>.md` | `update_user_preference()` 工具 |
| **注入位置** | `auto-memory` section | `## 用户偏好` section |
| **大小限制** | 无 | 2KB |
| **跨项目** | 支持（`~/.claude/memory/` 全局层） | 不支持（严格项目隔离） |

---

## 六、Claude Code 的维护机制

### 6.1 CLAUDE.md 的维护

**谁维护**：用户/维护者（人类）+ Claude（辅助）

**三种维护方式**：

1. **手动编辑** —— 用户直接写 Markdown，git commit 提交
   - 最常见的模式：开发者在项目中写 "我们用 pytest，不用 unittest"

2. **/init 命令** —— 让 Claude 扫描项目结构，自动生成初始 CLAUDE.md
   - 之后用户手动精修

3. **对话中请求 Claude 更新** —— "把这条规则加到 CLAUDE.md 里"
   - Claude 用 Edit 工具修改文件

**分层结构**：

```
~/CLAUDE.md                    ← 全局（所有项目生效）
  project/CLAUDE.md            ← 项目根（该项目生效）
    project/subdir/CLAUDE.md   ← 子目录（该目录下生效）
```

- 每次对话，匹配到的 CLAUDE.md **全部**注入 system prompt（不按需召回）
- 类似 `.gitignore` 的分层逻辑 —— 越具体越优先

**CLAUDE.md 的内容特征**：

- 声明式（"我们用 X"、"禁止 Y"）
- 很少变化（项目级约定相对固定）
- 不记录"学到的知识" —— 那是 memory 的职责

### 6.2 Memory 的维护

**谁维护**：Claude（主要） + 用户（偶尔手动编辑）

#### 6.2.1 写入触发条件

Claude 在以下情况主动写入 memory：

| 触发场景 | 示例 | type |
|----------|------|------|
| 用户明确说"记住这个" | "记住我喜欢用 single quotes" | `user` |
| 用户纠正 Claude 行为 | "别用 tab，用 space" | `feedback` |
| Claude 发现重要项目事实 | "这个项目用 ARM64，pytest 要加 -m" | `project` |
| 调试中解决疑难问题 | "E0355 是顶层裸代码禁令" | `project` |
| 外部资源链接 | "API 文档在 https://..." | `reference` |

#### 6.2.2 写入流程

```
1. Claude 决定写入
   └─ 根据对话上下文判断是否值得记住

2. Write 工具创建 memory/<name>.md
   └─ 文件名 = kebab-case slug（如 helen-top-level-restriction.md）
   └─ frontmatter 定义元数据：
      ---
      name: helen-top-level-restriction
      description: v1.17 E0355: 只允许声明+main{}在顶层
      metadata:
        type: project
      ---
      正文（Markdown 自由格式）

3. 更新 MEMORY.md 索引
   └─ 加一行：- [标题](文件名) - 一句话 hook
   └─ 如：- [Helen 顶层裸代码禁令](helen-top-level-restriction.md) - v1.17 E0355...

4. 跨记忆链接（可选）
   └─ 正文中用 [[other-name]] 链接其他记忆
   └─ 链接目标不存在也 OK —— 标记"未来值得记录"
```

#### 6.2.3 召回机制

```
对话开始：
  MEMORY.md 索引 → 注入 system-reminder（用户 auto-memory 区）
  每行只显示标题 + 一句话 hook，不加载全文

对话中：
  Claude 根据当前任务判断相关性
  → 用 Read 工具加载具体 memory/<name>.md 全文
  → 注入当前对话上下文
```

**关键**：MEMORY.md 索引是"菜单"，具体文件是"菜品"。每次对话只点相关的菜。

#### 6.2.4 维护动作

| 动作 | 谁做 | 怎么做 |
|------|------|--------|
| **新增** | Claude | Write 新 `.md` + Edit `MEMORY.md` 加行 |
| **更新** | Claude | Edit 具体 `.md` 文件（保持 frontmatter） |
| **删除** | Claude | 删除 `.md` + Edit `MEMORY.md` 删行 |
| **合并** | Claude | 两个记忆重复时合并为一个 |
| **清理过期** | 系统 | 7 天自动过期（仅 scheduled tasks） |
| **手动整理** | 用户 | 直接编辑 `memory/` 目录 |

### 6.3 两者的维护边界

```
CLAUDE.md 的职责：                    Memory 的职责：
─────────────────                    ────────────────
✓ 项目约定（"我们用 pytest"）          ✓ 学到的知识（"ARM64 上 pytest 要加 -m"）
✓ 工作流规则（"提交前跑 flake8"）      ✓ 调试经验（"E0355 是顶层裸代码禁令"）
✓ 工具偏好（"用 uv 不是 pip"）         ✓ 用户偏好（"喜欢 single quotes"）
✓ 架构说明（"三层 pipeline"）          ✓ 工作反馈（"别凭印象断言，先 grep"）
✓ 外部链接（"文档在 https://..."）     ✓ 外部引用（"API docs 在这个 URL"）

✗ 不记录具体学到的知识点               ✗ 不声明项目级规则
✗ 不记录用户个人偏好                   ✗ 不写"我们用 X"这种约定
✗ 不作为"规则"被强制执行               ✗ 不随项目 git 提交（个人化）
```

**核心分界**：

- **CLAUDE.md = 规则**（"必须/禁止"）→ 项目级、团队共享、git 提交
- **Memory = 知识**（"学到了/记住了"）→ 个人化、经验积累、可不提交

### 6.4 维护的实际成本

**CLAUDE.md**：

- 一次性投入，长期受益
- 变化频率低（项目约定很少变）
- 维护者：项目 owner / 团队

**Memory**：

- 持续累积，需要定期整理
- MEMORY.md 索引会随时间变长 → 召回可能变慢/不准
- Claude 自己维护，但质量依赖 Claude 的判断
- 用户偶尔需要手动删除过时记忆

---

## 七、架构核心差异

### 7.1 哲学差异

**Claude Code：文件即配置 + 按需召回**

```
CLAUDE.md  ──→ 静态指令（用户可编辑，每次对话注入）
memory/    ──→ 动态知识（LLM 写入，按需召回）
  ├── 项目知识  (type=project)
  ├── 用户偏好  (type=user)
  ├── 工作反馈  (type=feedback)
  └── 外部引用  (type=reference)
```

- CLAUDE.md 和 memory/ 职责清晰：一个是"规则"（不可变），一个是"知识"（可积累）
- memory/ 内部分类用元数据（frontmatter），不是文件路径

**Helen：硬编码指令 + 双文件全量注入**

```
prompt 硬编码  ──→ 静态指令（开发者改 .helen 源码）
.helen/
├── MEMORY.md  ──→ 项目知识（全量注入，5KB）
└── USER.md    ──→ 用户偏好（全量注入，2KB）
```

- 没有用户可编辑的指令文件 —— 相当于没有 CLAUDE.md
- MEMORY.md 和 USER.md 按文件路径区分，而不是元数据
- 两者都是全量注入，共享 context window 预算

### 7.2 核心哲学差异

| | Helen | Claude Code |
|--|-------|-------------|
| **假设** | Memory 内容**小且高度相关**，可以全量注入 | Memory 内容**可能很大**，需要按需检索 |
| **策略** | 全量注入 + 大小限制 | 索引 + 按需召回 |
| **风险** | 超出 5KB 就爆掉 context | 召回不精准导致遗漏 |

### 7.3 Helen 的独特优势

1. **显式双文件分离**：MEMORY.md（项目知识）和 USER.md（用户偏好）物理隔离，职责清晰
2. **硬性大小限制 + 归档机制**：避免 memory 膨胀成无用的大文件
3. **工具化写入**：`update_memory(category, key, value)` 是 LLM 工具，结构化程度高
4. **Exit 时显式提醒**：`pre_exit_check()` 强制 LLM 思考是否需要保存
5. **与 transcript 系统集成**：memory 更新可以结合 `search_transcript()` 回溯决策

### 7.4 Claude Code 的独特优势

1. **按需召回**：不占满 context window，只在相关时注入
2. **frontmatter 元数据**：name/description/type 让检索更精准
3. **跨项目全局记忆**：`~/.claude/memory/` 适用于所有项目
4. **`[[name]]` 链接**：记忆之间形成网络，而非扁平列表
5. **自动触发 recall**：system-reminder 中根据当前任务自动注入相关记忆
6. **无大小硬限制**：靠 LLM 自行维护质量，不会因超 5KB 报错
7. **分层指令**：CLAUDE.md 支持全局/项目/子目录三层

---

## 八、Helen 缺失 CLAUDE.md 等价物的问题

### 问题 1：无法按项目定制行为

Claude Code 用户可以在项目根目录放一个 `CLAUDE.md` 说"这个项目用 pytest，别用 unittest"，立即生效。Helen 的 agent 对所有项目用完全相同的硬编码 prompt —— 项目特异性只能通过 `env_context` 中的项目事实（project_type、helen_version 等）来条件化，**无法表达"这个项目应该怎么做"的指令**。

### 问题 2：维护者 vs 用户的边界模糊

CLAUDE.md 是用户/维护者写给 AI 的"工作说明"，与 AI 自己积累的 memory 是分开的。Helen 把两者都塞进了 memory —— 如果用户想让 agent 记住"这个项目要先跑 lint"，只能走 `update_memory("project_conventions", ...)` 混在 agent 自己学到的知识里。

### 问题 3：prompt 修改需要发布新版本

Claude Code 用户改一行 CLAUDE.md 就能调整 AI 行为。Helen 要改 `chat_session_actor.helen` 的 prompt 块，改完等于修改了 Helen agent 的源码 —— 需要重新安装、重新部署。

### 问题 4：全量注入的 scalability 限制

5KB 硬限制在知识积累到一定程度后成为瓶颈 —— 用户必须在"保留所有知识"和"不超限"之间做选择，而归档是手动的、痛苦的。Claude Code 的按需召回机制可以支持任意规模的 memory，因为它只加载相关部分。

### 问题 5：会话中途无法更新 memory 视图

Helen 的 memory 在 spawn 时一次性注入到 prompt，中途 `update_memory` 后 **LLM 在当前 session 内看不到更新后的文件内容**（除非重启 actor）。Claude Code 的 memory 可以通过重新读取文件获取最新版本。

---

## 九、对 Helen 的改进建议

### 短期改进（保持现有架构）

1. **动态重载**：目前 memory 在 spawn 时一次性注入，中途 `update_memory` 后 LLM 看不到更新。可以让 LLM 工具 `load_memory()` 返回最新内容，或在每轮 LLM 调用前重新注入。

2. **`/memory show`**：当前 `/memory` 只显示文件大小，应该支持显示完整内容。

3. **`/memory search <query>`**：支持在记忆内容中搜索。

4. **跨 session 记忆持久化**：当前 actor 重启后 memory 文件仍在，但没有机制让新 actor "知道"哪些记忆是近期更新的。

### 中期改进（引入 CLAUDE.md 等价物）

5. **添加 `.helen/INSTRUCTIONS.md`（或类似文件）**：
   - 用户可编辑的项目级指令
   - spawn 时与 MEMORY.md、USER.md 一起注入
   - 内容与硬编码 prompt 分离 —— 规则归 INSTRUCTIONS.md，知识归 MEMORY.md

6. **分层指令加载**：
   ```
   ~/.helen/INSTRUCTIONS.md           ← 全局
   <project>/.helen/INSTRUCTIONS.md   ← 项目
   ```

### 长期改进（按需召回架构）

7. **记忆索引化**：MEMORY.md 改为"索引"，每个记忆独立文件 + frontmatter：
   ```
   .helen/memory/
   ├── INDEX.md                      ← 索引（每行一个记忆）
   ├── error-patterns/
   │   └── shared-let-write-back.md  ← 具体记忆（带 frontmatter）
   └── helen-syntax/
       └── chinese-keywords.md
   ```

8. **按需召回**：LLM 调用 `recall_memory(query)` 工具获取相关记忆，而不是全量注入。

9. **结构化元数据**：给每个记忆加 frontmatter（name/description/type/created_at/source_session）。

10. **跨项目全局记忆**：添加 `~/.helen/memory/` 全局层，存用户的通用偏好（编码风格、常用工具等）。

11. **记忆链接**：支持 `[[name]]` 语法互联记忆。

### 改进优先级

| 优先级 | 改进 | 收益 | 成本 |
|--------|------|------|------|
| P0 | 动态重载 | 解决"中途更新不可见"问题 | 低 |
| P0 | `/memory show/search` | 提升可观测性 | 低 |
| P1 | `.helen/INSTRUCTIONS.md` | 支持项目级定制 | 中 |
| P1 | 分层指令加载 | 支持全局/项目两级 | 中 |
| P2 | 记忆索引化 | 突破 5KB 限制 | 高 |
| P2 | 按需召回 | 支持任意规模 memory | 高 |
| P3 | 跨项目全局记忆 | 通用偏好复用 | 中 |
| P3 | 记忆链接 | 形成知识网络 | 低 |

---

## 附录：关键代码引用

### memory_utils.helen 核心函数

```helen
// helen/agent/memory_utils.helen

fn load_memory(): str {
    let path = ".helen/MEMORY.md"
    if !path_exists(path) { return "" }
    return read_file(path)
}

fn load_user_preferences(): str {
    let path = ".helen/USER.md"
    if !path_exists(path) { return "" }
    return read_file(path)
}

fn build_memory_context(): str {
    let memory_content = load_memory()
    let user_prefs_content = load_user_preferences()
    let ctx = ""
    if memory_content != "" {
        ctx = ctx + "## Agent 记忆（历史知识）\n" + memory_content + "\n\n"
    }
    if user_prefs_content != "" {
        ctx = ctx + "## 用户偏好\n" + user_prefs_content + "\n\n"
    }
    if ctx == "" {
        ctx = "（暂无记忆，会在交互中逐步学习）\n"
    }
    return ctx
}

fn update_memory(category: str, key: str, value: str): map {
    let path = ".helen/MEMORY.md"
    let content = ""
    if path_exists(path) {
        content = read_file(path)
    } else {
        content = "# HelenAgent Unified Context\n\n> Agent 启动时加载的统一上下文入口。\n\n"
    }
    let section_header = "## " + category
    if !contains(content, section_header) {
        content = content + "\n" + section_header + "\n\n"
    }
    let entry_marker = "### " + key
    if contains(content, entry_marker) {
        content = content + "\n- **" + key + "** (更新): " + value + "\n"
    } else {
        content = content + "\n- **" + key + "**: " + value + "\n"
    }
    try {
        write_file(path, content)
        return {"status": "success", "message": "记忆已更新"}
    } catch {
        return {"status": "error", "message": "写入记忆失败"}
    }
}

fn update_user_preference(category: str, preference: str): map {
    let path = ".helen/USER.md"
    let content = ""
    if path_exists(path) {
        content = read_file(path)
    } else {
        content = "# User Preferences\n\n> Captured during interactions.\n\n"
    }
    let section_header = "## " + category
    if !contains(content, section_header) {
        content = content + "\n" + section_header + "\n\n"
    }
    content = content + "- " + preference + "\n"
    try {
        write_file(path, content)
        return {"status": "success", "message": "用户偏好已更新"}
    } catch {
        return {"status": "error", "message": "更新用户偏好失败"}
    }
}
```

### chat_session_actor.helen 的 pre_exit_check

```helen
// helen/agent/chat_session_actor.helen:557-581

fn pre_exit_check(): map {
    let warnings = []
    let stats = {"message_count": 0, "skill_eval_status": "idle"}
    let memory_status = {"memory_md_ok": true, "user_md_ok": true}

    try {
        let mem_size = len(read_file(".helen/MEMORY.md"))
        if mem_size > 5120 {
            warnings = warnings + [".helen/MEMORY.md 超过 5KB，请整理并归档到 .helen/archive/"]
            memory_status["memory_md_ok"] = false
        }
    } catch {}
    try {
        let user_size = len(read_file(".helen/USER.md"))
        if user_size > 2048 {
            warnings = warnings + [".helen/USER.md 超过 2KB，请精简用户偏好"]
            memory_status["user_md_ok"] = false
        }
    } catch {}

    return {
        "warnings": warnings, "session_stats": stats, "memory_status": memory_status,
        "reminder": "如本次会话有重要学习，请调用 update_memory 保存"
    }
}
```

### commands.helen 的 /memory 命令

```helen
// helen/agent/commands.helen:298-315

/** /memory - 显示记忆系统状态 */
fn _cmd_memory(): str {
    let text = "## 记忆系统状态\n\n"
    if path_exists(".helen/MEMORY.md") {
        let mc = read_file(".helen/MEMORY.md")
        text = text + "- Agent 记忆: " + str(len(mc)) + " 字符\n"
    } else {
        text = text + "- Agent 记忆: （空）\n"
    }
    if path_exists(".helen/USER.md") {
        let up = read_file(".helen/USER.md")
        text = text + "- 用户偏好: " + str(len(up)) + " 字符\n"
    } else {
        text = text + "- 用户偏好: （空）\n"
    }
    text = text + "\n记忆文件: .helen/MEMORY.md, .helen/USER.md\n"
    return text
}
```
