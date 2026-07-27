# CLAUDE.md 过时 / 重复 / 错误内容审计报告

> 审计时间: 2026-07-27
> 对照 Helen 版本: v1.29.3 (实际代码状态)
> 当前测试数: 3246

---

## 一、过时数字 (多处)

### 1.1 关键字数量 — 文档 vs 实际不一致

| 位置 | 文档声称 | 实际状态 | 建议 |
|------|---------|---------|------|
| L48 `Lexer` 描述 | "89 bilingual keywords" | 代码注释写"95 entries",但 Python 实测 `_KEYWORD_MAP` **唯一键 91 个**(45 English + 46 Chinese) | 改为 91 或 95(对齐代码注释) |
| L154 `Chinese support` | "89 bilingual keywords (44.5 English + 44.5 Chinese)" | 实际 45 English / 46 Chinese | 改为 "91 bilingual keywords (45 English + 46 Chinese)" |
| L148 `spawn resume` 段落 | "bilingual keyword count stays at 89" | 过时 | 删除该数字或改为当前值 |
| L263 skill 表 `helen-syntax` | "89 keywords" | 同上 | 同步更新 |

**根因**: CLAUDE.md 长期未更新关键字数,v1.10 时是 89,v1.27 加 resume 没改,v1.29 加 `transcript` / `记录` 后实际应 ≥ 90。

### 1.2 测试数量

| 位置 | 文档声称 | 实际 |
|------|---------|------|
| L27 `pytest` 注释 | "2791+ tests" | **3246** |
| L239 `Testing Architecture` 末尾 | "2791+ tests passing" | **3246** |

差异达 **455 个测试**,完全过时。

### 1.3 stdlib 函数数量

| 位置 | 文档声称 | 实际 |
|------|---------|------|
| L88 `stdlib/` 注释 | "324 built-in functions (21 categories)" | **330 functions (21 categories)** |
| L264 skill 表 `helen-stdlib` | "203 built-in functions" | **330** |

`helen-stdlib` 技能表里那个"203"严重过时,差了 127 个函数。

### 1.4 中文别名数量

| 位置 | 文档声称 | 实际 |
|------|---------|------|
| L90 `locales/zh.py` 注释 | "287 Chinese aliases" | **329** (418 行文件) |

### 1.5 AST 节点数

| 位置 | 文档声称 | 实际 |
|------|---------|------|
| L50 `AST` 描述 | "64 frozen dataclass nodes" | **61** (通过 `accept` 方法识别) |

---

## 二、已删除文件 / 功能的残留引用

### 2.1 `helen_assistant.helen` — 已删除

**L95**:
```
├── agent/         # Helen assistant program (helen_assistant.helen)
```

**实际情况**: `helen_assistant.helen` 在 v1.28 已被删除(依赖实质 broken,被新 `:ask` 三层架构取代)。当前 `helen/agent/` 目录下有 14 个 .helen 文件:
- `chat_session_actor.helen`、`chat_tui.helen`、`commands.helen`、`context.helen`、`context_manager.helen`、`json_utils.helen`、`memory_utils.helen`、`output.helen`、`session_stats.helen`、`system_reminders.helen`、`task_manager.helen`、`ui_bridge.helen`、`ui_event_queue.helen`、`utils.helen`

**建议**: 改为 `# Helen agent components (chat_session_actor, chat_tui, task_manager, etc.)`

### 2.2 `hellen-consistency-checker` 技能 — 已不存在

**L101**:
```
└── devops/                # github, hellen-consistency-checker
```

**L272** (skill 表):
```
| hellen-consistency-checker | 1041 | Design document consistency checking |
```

**实际情况**: `helen/skills/devops/` 下**只有 `github/`**(1 个 skill),没有 `hellen-consistency-checker`。全仓库 grep 也找不到这个技能目录。整个 devops 分类目前只有 1 个 skill,总共 15 个 skill(14 software-development + 1 devops),不是 16。

**附加问题**: "hellen" 拼写错误(多了个 l),正确应为 "helen"。

**建议**: 删除该行,L101 改为 `└── devops/  # github`,L258/L251 的 "16 built-in skills" 改为 "15"。

### 2.3 `multimodal-providers` 技能 — 不存在

**L145**:
```
**Companion skill**: `multimodal-providers` provides standard callback templates...
```

**实际情况**: 整个 `helen/skills/` 目录里找不到 `multimodal-providers`。这个技能要么从未发布,要么已删除。

**建议**: 删除该行或改为描述实际存在的相关技能。

---

## 三、重复 / 冗余内容

### 3.1 TranscriptStore 配置块重复

**L188-197** (Language Concepts → TranscriptStore SSOT → Configuration):
```yaml
transcript:
  enabled: true
  backend: "sqlite"
  session_scope: "auto"
  session_dir: "~/.helen/sessions"
  project_session_dir: ".helen/sessions"
  max_memory_items: 1000
```

**L208-214** (Configuration 章节): 完全相同的配置块又出现一次。

**建议**: 保留 Configuration 章节的版本,L188-197 改为简短引用 `See Configuration section below`。

### 3.2 REPL `:ask` 描述分散

**L62-65** (Architecture → REPL 子弹点) 详细描述了 `:ask` 的三层架构(L1/L2/L3)。
但 Language Concepts 章节没有提到 `:ask` 的任何内容。

实际上 `:ask` 是 REPL 功能,放在 Architecture 里是合适的;但 L62 的 REPL 命令列表里只写了 `:ask`,没有体现 L1/L2/L3 分层。目前文档是**散乱的** — L62 提命令名,L63-65 解释分层。可以整合为一段。

### 3.3 spawn + Channel 与 Channel message queue 段落重叠

**L117-124** "Channel message queue (v1.18)" 段落描述了 spawn + Channel + mailbox_select。
**L147** "spawn + Channel (v1.18)" 又描述了一遍相同内容(spawn 返回 Channel、隔离、mailbox_select)。

两段内容高度重叠,建议合并为一个段落。

### 3.4 Chinese aliases 列表重复

多个 bullet 都列了 Chinese aliases,风格不统一:
- L121 `发送()`, `接收()` 等
- L124 `取消大模型调用` 等
- L138 `逐块处理`(on_chunk)、`完成`(on_complete) 等
- L146 `媒体()`, `媒体base64()` 等

建议统一为一个小节或附录,而不是散落在每个特性 bullet 里。

---

## 四、Skill 表行数过时

L261-282 的 skill 表里 `Lines` 列与实际文件行数对比:

| Skill | 文档声称 | 实际行数 | 变化 |
|-------|---------|---------|------|
| helen-syntax | 632 | 661 | +29 |
| helen-stdlib | 739 | 867 | **+128** |
| helen-testing | 705 | 704 | -1 |
| helen-quality | 133 | 135 | +2 |
| helen-agent-patterns | 815 | 848 | +33 |
| helen-agent-collaboration | 545 | 567 | +22 |
| helen-language-development | 674 | 674 | ✓ |
| helen-programming-methodology | 383 | 438 | +55 |
| helen-python-bridge | 576 | 576 | ✓ |
| code-quality | 402 | 402 | ✓ |
| debugging | 610 | 610 | ✓ |
| planning | 330 | 330 | ✓ |
| test-driven-development | 354 | 354 | ✓ |
| subagent-driven-development | 624 | 624 | ✓ |
| github | 323 | 323 | ✓ |

**`helen-stdlib` 增长了 128 行**(从 739 到 867),因为 v1.28.5 / v1.25 等新增了大量函数文档。

**建议**: 要么更新数字,要么**删除 Lines 列**(行数随每次提交变化,维护成本高且价值低)。

---

## 五、v1.29 / v1.28 新特性缺失

CLAUDE.md 完全没有反映 v1.28 和 v1.29 的变化:

### 5.1 缺失 v1.29 内容

- ❌ **Agent 级 transcript 控制**:`transcript "none"|"memory"|"persistent"` 子句
- ❌ 新关键字 `transcript` / `记录`(关键字 94 → 95)
- ❌ `TranscriptStore.append(message, persist=...)` 新增 `persist` 参数
- ❌ 顶层 main 默认 `transcript="none"` 的设计变更

### 5.2 缺失 v1.28 内容

- ❌ **`:ask` 三层架构**:L1 REPL 上下文注入 / L2 REPL 状态工具 / L3 多轮对话(L63-65 只是简略提了)
- ❌ v1.28.5 新增 stdlib:`find_from(s, sub, start)`、`json_parse_lenient(text)`
- ❌ v1.28.5 解析器增强:`if (a || b) && c {}` 布尔陷阱检测
- ❌ v1.28.6 `\uNNNN` Unicode 转义修复

### 5.3 缺失 v1.27 内容

- ❌ `spawn resume("<session_id>")` 子句 — **L148 其实有提到,但夹杂在长段落里,且关键字数声称"stays at 89"是错的**

### 5.4 缺失 v1.26 内容

- ❌ helenagent 集成(`helen/agent/` 下的 14 个 .helen 文件)

---

## 六、`helen/core/tokens.py` 中的重复条目(代码 bug)

虽然不直接是 CLAUDE.md 问题,但影响文档中声称的"95 keywords":

```python
# helen/core/tokens.py lines 171-183
"store": TokenType.STORE,     # line 171 (第一次)
"protocol": TokenType.PROTOCOL,  # line 172
"impl": TokenType.IMPL,       # line 173
"is": TokenType.IS,           # line 174
"shared": TokenType.SHARED,   # line 175
"alias": TokenType.ALIAS,     # line 176
"transcript": TokenType.TRANSCRIPT,  # line 177
"store": TokenType.STORE,     # line 178 ❌ 重复
"仓库": TokenType.STORE,      # line 179
"alias": TokenType.ALIAS,     # line 180 ❌ 重复
"protocol": TokenType.PROTOCOL,  # line 181 ❌ 重复
"impl": TokenType.IMPL,       # line 182 ❌ 重复
"is": TokenType.IS,           # line 183 ❌ 重复
# ...
"shared": TokenType.SHARED,   # line 236 ❌ 与 line 175 重复
```

**v1.29 的 commit 添加了新关键字,但没注意到这些 English 关键字已在更早位置定义**。结果:
- 代码注释写 "95 entries",但实际唯一键只有 **91 个**(Python dict 自动去重)
- 6 个重复:`store`、`alias`、`protocol`、`impl`、`is`、`shared`

**建议**: 清理 tokens.py 的重复条目,统一注释的"95 entries"为真实数字。

---

## 七、拼写 / 小问题

### 7.1 `hellen-consistency-checker` 拼写错误
- L101、L272: `hellen` → 应为 `helen`(但整个 skill 都已不存在,见第二节)

### 7.2 Language Concepts bullet 顺序混乱
- L130 🎯 First Principle 用 emoji 高亮,但位置夹在 ReadOnlyView 和 Agent scope isolation 之间,不够显眼
- L148 spawn resume 是 v1.27 的新特性,但紧挨着 v1.18 的 spawn + Channel,中间没有版本过渡说明

### 7.3 L93 `cli/` 描述不全
```
├── cli/           # __main__.py (entry point), repl.py, formatter.py, docgen.py
```
**实际 `cli/` 还有**: `ask_assistant.py`(v1.28 新增)等。建议补充。

---

## 八、修复建议优先级

### P0 — 必须修复
1. ✅ 测试数量 2791+ → **3246**(L27, L239)
2. ✅ 关键字数 89 → **91**(L48, L154, L148, L263)
3. ✅ stdlib 函数数 324 → **330**(L88);203 → **330**(L264)
4. ✅ 中文别名 287 → **329**(L90)
5. ✅ AST 节点 64 → **61**(L50)
6. ✅ Skill 数 16 → **15**(L96, L251, L258),并删除已不存在的 `hellen-consistency-checker`(L101, L272)
7. ✅ 删除 `helen_assistant.helen` 引用(L95)
8. ✅ 清理 `helen/core/tokens.py` 的 6 个重复 keyword 条目

### P1 — 强烈建议
9. 新增 v1.29 Agent 级 transcript 控制章节
10. 新增 v1.28.5-6 内容(`find_from`/`json_parse_lenient`/Unicode 修复)
11. 删除不存在的 `multimodal-providers` 技能引用(L145)
12. 删除 skill 表的 `Lines` 列(维护成本高、价值低)
13. 合并 "Channel message queue" 和 "spawn + Channel" 重叠段落(L117-124 vs L147)
14. 删除重复的 TranscriptStore 配置块(L188-197)

### P2 — 锦上添花
15. 补充 `cli/ask_assistant.py` 到 L93 的目录描述
16. 统一 Chinese aliases 列表风格(集中在一个小节)
17. 重新组织 Language Concepts 段落顺序(按版本或逻辑分组)
18. 修正 `hellen` 拼写(如保留该 skill)

---

## 九、总结

CLAUDE.md 自 v1.25 后基本未更新,导致:
- **7 处数字过时**(关键字、测试、stdlib、别名、AST、skill 数、行数)
- **3 个已删除内容残留引用**(`helen_assistant.helen`、`hellen-consistency-checker`、`multimodal-providers`)
- **2 处重复配置块 / 段落重叠**
- **完全缺失 v1.26–v1.29 的新特性描述**
- **代码层 `tokens.py` 有 6 个 keyword 重复**(v1.29 commit 引入)

建议做一次全面的"CLAUDE.md 同步 PR",优先处理 P0 项。
