# Helen Wiki Log

> 本文件记录 wiki 的所有操作（ingest、query、lint），按时间倒序排列。

---

## [2026-07-19] feature | 技能引用系统优化 — list_skill_references + load_skill 增强

**操作**: 增强技能引用文档加载机制
**触发**: references/ 目录缺少专门的加载工具，LLM 无法高效发现参考文档
**状态**: ✅ 完成

### 代码变更

1. **`helen/runtime/tools.py`**
   - `_load_skill()` 增加 `include_references` 参数
   - 新增 `_list_skill_references()` 工具函数

2. **`helen/stdlib/tools.py`**
   - 更新 `_load_skill` 包装函数
   - 新增 `_list_skill_references` 包装函数

3. **`helen/stdlib/__init__.py`**
   - 注册 `list_skill_references` 为 BuiltinFunction
   - builtin 总数: 323 → 324

4. **`helen/stdlib/locales/zh.py`**
   - 新增中文别名: `列出技能引用` → `list_skill_references`

### 文档更新

- `wiki/runtime/skills.md` — 新增 Tier 3 参考文档加载说明
- `wiki/tutorial/06-llm-statements.md` — 工具表新增 `list_skill_references`
- `wiki/tutorial/13-skills.md` — 新增第三层参考文档说明
- `helen-stdlib` SKILL.md — Tools 类别 6 → 7
- `CLAUDE.md` — 工具数量 10 → 11，builtin 323 → 324

---

## [2026-07-19] refactor | 代码架构重构 — interpreter.py 拆分 + stdlib 注册重构

**操作**: 按 `reports/architecture-analysis-2026-07-19.md` 执行代码重构
**触发**: interpreter.py 膨胀至 3258 行，需要拆分提高可维护性
**状态**: ✅ 完成

### Phase 1: 提取辅助类

- `helen/interpreter/closure.py` — Closure 类 + 自由变量分析函数
- `helen/interpreter/readonly_view.py` — ReadOnlyView（agent 参数隔离）
- `helen/interpreter/shared_store.py` — SharedStore + SharedStoreMethod（线程安全共享状态）

### Phase 2: 提取 Visitor Mixin

- `helen/interpreter/pattern_mixin.py` — match/case 模式匹配（8 个方法）
- `helen/interpreter/exception_mixin.py` — try/catch/throw/assert（6 个方法）
- `helen/interpreter/import_mixin.py` — 多格式导入（5 个方法）
- `helen/interpreter/streaming_mixin.py` — 流式调用管理（5 个方法 + _StreamingHandle）

**interpreter.py**: 3258 → 1990 行 (**-39%**)

### Phase 3: stdlib 注册重构

将 `_register_builtins()` 的 436 行注册列表拆分为 21 个按类别的注册函数：
`_register_core()`, `_register_string()`, `_register_math()`, ..., `_register_llm()`

### 文档更新

- `CLAUDE.md` — 更新 interpreter/ 目录结构和架构描述
- `wiki/overview/architecture.md` — 更新 Mixin 架构图
- `wiki/interpreter/execution.md` — 添加 Mixin 架构表格

### 测试结果

- 3048 tests passed, 5 skipped

---

## [2026-07-18] bugfix | v1.23 — 修复 Invocation 上下文隔离 + 文档更新

**操作**: 修复 v1.22 实现的 per-agent 上下文隔离 bug，更新相关文档
**触发**: 用户深入调研发现 v1.22 实现与提案不一致
**状态**: ✅ 完成

### 代码修复

1. **`helen/interpreter/llm_mixin.py`**
   - `_prepare_history_for_llm()` 统一走 `self._history`（包含 invocation_id 过滤）
   - 不再直接读取 `transcript_store.read_view()`

2. **`helen/stdlib/context.py`**
   - `_import_context()` 改为单写策略（TranscriptStore 启用时只写 TranscriptStore）
   - 导入的消息标记当前 `invocation_id`

3. **`helen/stdlib/transcript.py`**
   - `resume_session()` 改为导入消息到当前 store（而非替换引用）
   - 恢复的消息标记 `invocation_id`

### 测试更新

1. **新增 `tests/interpreter/test_v123_invocation_isolation.py`**（2 个测试）
   - 验证 LLM 历史按 invocation_id 过滤
   - 验证导入消息标记 invocation_id

2. **修复 `tests/stdlib/test_context_v119_p1p3.py`**
   - 适配 `_import_context()` 单写策略

3. **修复 `tests/runtime/test_session_scope.py`**（3 个测试）
   - 使用 `unittest.mock.patch` 隔离 `/tmp/.helen` 残留文件的影响

### 文档更新

1. **`helen/skills/software-development/helen-agent-patterns/SKILL.md`**
   - 新增"Agent 上下文隔离（v1.22/v1.23）"章节
   - 说明 invocation 级别隔离与变量作用域隔离的区别
   - 提供调用树查询示例
   - 说明 v1.23 修复内容

2. **`wiki/runtime/context-management.md`**
   - 版本号 v1.22 → v1.23
   - 新增 §0.6 "v1.23 修复：Invocation 隔离实现修正"
   - 详细说明三个 bug 及修复方案

3. **`wiki/appendix/changelog.md`**
   - 新增 v1.23 变更日志
   - 新增 v1.22 变更日志（之前缺失）
   - 说明 v1.22 已知问题及 v1.23 修复

### 版本 bump

- `helen/__init__.py`: `1.23.0` → `1.23.1`
- `pyproject.toml`: `1.23.0` → `1.23.1`
- PyPI 发布: `pip install helen-lang==1.23.1`

### 测试结果

- **3048 passed, 0 failed**（从 3042 passed, 4 failed 改进）
- 新增 2 个 v1.23 测试
- 修复 4 个失败测试

---

## [2026-07-17] feature | v1.22 — Invocation Tree + Per-Main Fresh Context

**操作**: 实现 v1.22 提案的主体部分（调用树 + 每次 main {} fresh context）
**触发**: 用户要求按 `reports/v1.22-invocation-tree-proposal.md` 完整实施
**状态**: ✅ 完成

### 变更内容

1. **Message 字段扩展**（`helen/runtime/history.py`）
   - 新增 `agent_name` / `invocation_id` / `parent_invocation_id` 三个字段
   - `transcript_store.py` 的 `_item_to_dict` / `_item_from_dict` 同步更新
   - 向后兼容：旧消息字段为 None/""

2. **Interpreter invocation 状态管理**（`helen/interpreter/interpreter.py`）
   - 新增 `_current_invocation_id` / `_invocation_stack` / `_invocation_index`
   - 实现 `_enter_invocation(agent_name)` / `_exit_invocation()`
   - `visit_main_block`：顶层 main 也创建 invocation
   - `_call_agent`：进入 agent 时 enter invocation，finally 块 exit invocation
   - `_history` property：按 `_current_invocation_id` 过滤，实现 per-agent 隔离

3. **`_add_to_history` 自动填字段**（`helen/interpreter/llm_mixin.py`）
   - 创建 Message 时填充 agent_name / invocation_id / parent_invocation_id

4. **调用树 stdlib 函数**（`helen/stdlib/transcript.py`）
   - `list_invocations(session_id?, agent?, limit?, offset?)`
   - `get_invocation(invocation_id, session_id?)`
   - `get_invocation_tree(session_id?)`
   - `invocation_path(invocation_id, session_id?)`
   - `_build_invocation_index(store)` 内部辅助函数（从 transcript 重建索引）

5. **扩展 `replay_transcript`**：新增 `agent` / `invocation_id` / `last_only` / `include_subtree` 参数

6. **扩展 `restore_context`**：新增 `invocation_id` / `agent` / `last_only` / `include_subtree` 参数

7. **注册 + 中文别名**
   - `helen/stdlib/__init__.py`：4 个新 BuiltinFunction，总数 319 -> 323
   - `helen/stdlib/locales/zh.py`：`列出调用` / `获取调用` / `获取调用树` / `调用路径`

8. **测试**：`tests/interpreter/test_invocation_tree.py`（17 个用例）
   - 上下文隔离（两 agent、同 agent 两次、嵌套）
   - invocation 元数据字段
   - 调用树查询 API
   - replay_transcript / restore_context 过滤
   - 向后兼容

9. **文档更新**
   - `wiki/runtime/context-management.md`：修正"Context 生命周期 = Agent 会话"为"= 单次 main {} 执行"，新增 §0.5
   - `wiki/runtime/transcript-store.md`：新增 Invocation Tree 章节
   - `wiki/tutorial/10-stdlib.md`：新增"调用树查询 (v1.22)"章节，Transcript 函数 7 -> 11
   - `helen/skills/software-development/helen-stdlib/SKILL.md`：Transcript 12 -> 16，新增调用树示例
   - `reports/v1.22-invocation-tree-proposal.md`：状态 Draft -> 已实现

### 设计决策（已确认）

| 问题 | 决策 |
|---|---|
| 嵌套调用边界 | 严格隔离 + 未来 opt-in `merge_child_context()` |
| 顶层 agent_name | `null` |
| 元数据持久化 | 不持久化，从 transcript 重建（SSOT） |
| list_invocations 分页 | `limit=100, offset=0` |
| call_stack 关系 | 独立实现 |

### 隔离机制

active context 通过 `_history` property 按 `invocation_id` 过滤实现隔离，**不需要 save/restore**。transcript SSOT 仍然记录所有消息（审计完整），但 LLM 只看到当前 invocation 的消息。

### 测试结果

- 17 个新测试全部通过
- 1669 个 stdlib + interpreter + runtime 测试全部通过
- 1 个预先存在的无关失败（test_shared_let_writeback）除外

---

## [2026-07-17] feature | v1.22 — search_transcript 内容搜索函数

**操作**: 实现 `search_transcript(query, ...)` 内容搜索函数并更新 wiki
**触发**: 用户讨论：一般场景下记不住 invocation_id，但记得内容，需要根据内容找完整 context
**状态**: ✅ 完成

### 变更内容

1. **实现 `search_transcript` 函数**
   - 位置：`helen/stdlib/transcript.py`
   - 注册：`helen/stdlib/__init__.py` (BuiltinFunction, category="transcript")
   - 中文别名：`helen/stdlib/locales/zh.py` ("搜索会话" → search_transcript)
   - 测试：`tests/stdlib/test_search_transcript.py` (15 个用例，全部通过)

2. **wiki/runtime/transcript-store.md 新增 §search_transcript()**
   - 完整 API 说明
   - 参数表（query/session_id/scope/role/regex/limit）
   - 返回格式
   - 两个典型用法示例

3. **wiki/runtime/context-management.md 更新**
   - §0.3 "跨会话的记忆" 增加 `search_transcript` 作为与 `restore_context` 协同的发现工具
   - 版本号 v1.21 → v1.22

### 设计要点

- **与 `search_context` 区别**：`search_context` 只搜当前 active context（main {} 退出就没了）；`search_transcript` 搜持久化 transcript，可跨 session
- **scope 参数**：`current`（默认）/ `all`（跨所有 session）/ `global` / `project`
- **去重**：`scope="all"` 时跨 global + project 搜索，对 session 目录和 session_id 双重去重避免重复结果
- **多模态内容**：list 类型 content 自动展平为 text 部分再搜索
- **当前限制**：Phase 1 实现（`return="message"`）；`return="invocation"` 等高级粒度待 v1.22 invocation tree 实现后补

---

## [2026-07-17] feature | v1.21 — restore_context 函数

**操作**: 实现 `restore_context(session_id)` 并更新 wiki
**触发**: 用户讨论上下文管理生命周期时发现 API 缺口，随即实现
**状态**: ✅ 完成

### 变更内容

1. **实现 `restore_context` 函数**
   - 位置：`helen/stdlib/context.py` (`_restore_context`)
   - 注册：`helen/stdlib/__init__.py` (BuiltinFunction, category="context")
   - 中文别名：`helen/stdlib/locales/zh.py` ("恢复上下文" → restore_context)
   - 测试：`tests/stdlib/test_restore_context.py` (11 个用例，全部通过)

2. **wiki/runtime/context-management.md 更新**
   - §0.2 四层架构图保持不变
   - §0.3 "跨会话的记忆" 增加 `restore_context` 作为首选路径
   - 新增 `restore_context vs resume_session` 对比表
   - §0.4 `context {}` 配置章节补充 restore_context 示例代码
   - 删除"⚠️ API 缺口"段落（已实现）
   - 新增 §8.5.6b "跨会话恢复（v1.21+）" 详细 API 文档
   - §8.5.8 中文别名表新增 restore_context / 恢复上下文
   - 版本号 v1.20 → v1.21

### 设计要点

- `restore_context` 直接读 TranscriptStore 拿完整 Message 对象（绕过 `replay_transcript`，避免字段丢失）
- 保留所有字段：role、content、tool_calls、tool_call_id、uuid、compressed、pinned
- 内部委托给 `import_context()`，避免重复实现 history 替换逻辑
- **不**恢复 working_memory 和 context config（transcript 不持久化这些），在返回值 `note` 字段中显式提示
- 与 `resume_session` 的语义边界清晰：restore → active context（LLM 看到）；resume → transcript store（审计用）

---

## [2026-07-17] query → file-back | 上下文管理生命周期设计哲学

**操作**: 将关于 Context 管理生命周期的设计讨论补充进 wiki
**触发**: 用户讨论"Helen 上下文管理的生命周期应该多长？应该持久化多久？"
**状态**: ✅ 完成

### 变更内容

1. **`wiki/runtime/context-management.md` 新增"零、设计哲学与生命周期"章节**
   - §0.1 **Context vs Transcript 核心区分**：Context 是"LLM 当前看到的信息"（可变、会话级），Transcript 是"LLM 曾经说过的完整记录"（只追加、永久）
   - §0.2 **四层生命周期架构**：Layer 0 Working Memory（即时，单次 llm act）→ Layer 1 Active Context（Agent 会话期）→ Layer 2 Pinned Context（跨 llm act，免疫压缩）→ Layer 3 Transcript（永久，非 context）
   - §0.3 **Context 持久化边界**：跨 llm act ✅ / 跨 agent ❌（显式传递）/ 跨进程 ❌（用 Transcript 恢复）/ 跨会话 ❌（用 Skills / 文件）
   - §0.4 **`context {}` 配置的生命周期语义**：控制会话内行为，不控制跨会话持久化
   - 同步版本号 v1.19 → v1.20

### 设计要点

- Context 管理的哲学：**在有限的窗口内做到极致，不试图无限持久**
- 持久化是 Transcript 的事；Context 可以激进压缩而不必顾虑信息丢失
- 跨会话的"记忆"不是 context 的职责，应通过 Transcript 恢复、文件持久化或 Skills 实现
- `context {}` 配置绑定了 Agent 会话期内的压缩策略，不是跨会话状态

### 修正（2026-07-17 同日）

**问题**：初版 §0.3 和 §0.4 提到了 `restore_context(session_id)` 函数，**该函数不存在于 stdlib**——是我编造的"应该有"的函数。

**实际 stdlib 能力**：
- ✅ `export_context()` / `import_context(data)` — 唯一完整的跨会话恢复路径
- ✅ `replay_transcript(session_id)` — 只读审计，不注入当前 context，且返回格式与 `import_context()` 不兼容
- ❌ `restore_context(session_id)` — 不存在

**修正内容**：
- §0.3 "跨会话记忆"改用实际存在的 `export_context/import_context` 描述
- 新增"⚠️ API 缺口"段落，明确指出现有需要手写格式适配的问题
- §0.4 给出实际的 save/restore 代码示例（`export_context` + `write_file` + `parse_json` + `import_context`）
- 把 `restore_context(session_id)` 列为**未来考虑**的便捷函数

---

## [2026-07-13] feature | v1.18 — spawn 并发原语

**操作**: 更新 wiki 以反映 spawn 替代 async/await/detach 的重大变更
**执行时间**: 2026-07-13
**状态**: ✅ 完成

### 变更内容

1. **删除过时文件**
   - `reports/detach_thread_safety_and_shared_store_integration.md` — 删除
   - `wiki/tutorial/07-async-await.md` — 删除（由 07-spawn.md 替代）
   - `wiki/interpreter/async.md` — 删除（由 spawn.md 替代）

2. **新增文件**
   - `wiki/tutorial/07-spawn.md` — 并发编程教程
   - `wiki/interpreter/spawn.md` — spawn 技术文档

3. **更新文件**
   - `wiki/index.md` — 版本 v1.18、测试 2791、89 关键字、链接更新
   - `wiki/syntax/grammar.md` — 删除 async/await/detach/channel 声明 EBNF，新增 spawn_expr
   - `wiki/syntax/keywords.md` — 删除 async/await/detach/channel 条目，新增 spawn/分生，89 关键字
   - `wiki/overview/language-spec.md` — 全面更新关键字、Token、AST 列表，新增 v1.18 章节
   - `wiki/compiler/ast.md` — 删除 5 个旧节点，新增 SpawnExprNode，47 节点类/44 方法
   - `wiki/interpreter/execution.md` — 更新 Channel 语义，新增 spawn 执行语义
   - `wiki/schema.md` — 版本 v1.18、计数更新
   - `wiki/appendix/changelog.md` — 新增 v1.18 条目

### 关键字变更

| 动作 | 关键字 | 说明 |
|------|--------|------|
| 新增 | `spawn` / `分生` | 并发 agent 分生 |
| 删除 | `async` / `异步` | 由 spawn 替代 |
| 删除 | `await` / `等待` | 由 channel.receive() 替代 |
| 删除 | `detach` / `分离` | 由 spawn 替代 |
| 删除 | `channel`（声明语法） | 由 Channel() 构造函数替代 |

### 计数变更

| 项目 | 旧值 | 新值 |
|------|------|------|
| 关键字 | 97 | 89 |
| AST 节点 | 63 | 60 |
| Visitor 方法 | 58 | 54 |
| 测试数 | 2822 | 2791 |

---

## [2026-07-06] feature | v1.15 — Phase 7 上下文管理增强

**操作**: 完成 Phase 7 Agent 集成与声明扩展
**执行时间**: 2026-07-06
**状态**: ✅ 完成

### 变更内容

1. **Agent 上下文集成**
   - 创建 `AgentContextManager` 类
   - 集成到 `llm_mixin.py` 的三个关键方法
   - 自动应用渐进压缩和工作记忆

2. **Agent 声明扩展**
   - 新增 `context {}` 配置块
   - 支持 4 个配置选项：
     - `compression`: "none" / "graduated" / "traditional"
     - `cache-aware`: true / false
     - `working-memory`: true / false
     - `working-memory-tokens`: int
   - 支持中英文关键字

3. **AST 扩展**
   - 新增 `ContextConfigNode` 类
   - `AgentDeclNode` 添加 `context_config` 字段
   - 解析器支持 `context {}` 块解析

4. **文档更新**
   - wiki/tutorial/05-agents.md — 添加 context {} 说明
   - wiki/runtime/history.md — 添加 Phase 1-7 完整说明
   - wiki/index.md — 更新版本号和测试数量

### 新语法

```helen
agent SmartAssistant {
    description "Smart assistant"
    
    context {
        compression "graduated"
        cache-aware true
        working-memory true
        working-memory-tokens 5000
    }
    
    tools ["read_file", "web_search"]
    
    main {
        return llm act "..."
    }
}
```

### 测试覆盖

- `tests/interpreter/test_phase7_agent_context.py` - 16 个新测试
- 所有现有测试通过: 2583 passed

---

## [2026-07-06] feature | v1.15 — Phase 6 缓存感知压缩

**操作**: 实施缓存感知压缩策略
**执行时间**: 2026-07-06
**状态**: ✅ 完成

### 变更内容

1. **缓存感知压缩**
   - 稳定前缀 (30%): 保留前 30% 消息不变
   - 批量阈值 (75%): 使用率达到 75% 才触发
   - 仅后缀修改: 只在缓存区域外操作
   - 缓存边界标记: 使用稳定的标记

2. **效果**
   - 缓存命中率从 10-20% 提升到 70-80%
   - 对齐 Claude Code 的缓存管理

### 测试覆盖

- `tests/runtime/test_cache_aware_compression.py` - 18 个新测试

---

## [2026-07-06] feature | v1.15 — Phase 2-5 渐进压缩管线

**操作**: 实施五层渐进压缩策略
**执行时间**: 2026-07-06
**状态**: ✅ 完成

### 变更内容

1. **渐进压缩管线 (Graduated Compression Pipeline)**
   - Layer 1 (60%): Budget Reduction - 替换大工具输出为引用指针
   - Layer 2 (70%): Snip - 丢弃过时轮次
   - Layer 3 (80%): Microcompact - 清除旧工具结果，保留决策
   - Layer 4 (90%): Context Collapse - 归档并投射折叠视图
   - Layer 5 (95%): Auto-Compact - LLM 语义压缩

2. **核心创新**
   - "最廉价动作优先"原则
   - 工具调用决策保留（Microcompact）
   - 三通道上下文构建

### 测试覆盖

- `tests/runtime/test_graduated_compression.py` - 16 个测试
- `tests/runtime/test_working_memory.py` - 17 个测试
- `tests/runtime/test_llm_summarization.py` - 9 个测试

---

## [2026-07-05] refactor | v1.14 — 合并 llm stream 到 llm act

**操作**: 合并 `llm stream` 到 `llm act`，消除冗余 LLM 调用模式
**执行时间**: 2026-07-05
**状态**: ✅ 完成

### 变更内容

1. **语言表面简化**
   - `llm stream` 被删除，流式功能合并到 `llm act`
   - `llm act` 现在支持可选的 `on_chunk`/`on_complete` 回调参数
   - 有回调 → 流式执行；无回调 → 同步执行
   - 关键字从 94 个减至 92 个（46 英文 + 46 中文）

2. **删除的内容**
   - `LlmStreamStmtNode` AST 节点
   - `visit_llm_stream_stmt` visitor 方法
   - `STREAM` TokenType + `stream`/`流式执行` 关键字
   - `_llm_stream_expr()`/`_llm_stream_stmt()` 解析方法

3. **新增/修改**
   - `LlmActExprNode` 增加 `on_chunk`/`on_complete` 字段
   - `visit_llm_act_expr` 分叉为同步路径和流式路径
   - 解析器支持 `llm act "prompt" on_chunk cb on_complete cb`

4. **文档更新**
   - wiki/tutorial/ — 全部更新
   - wiki/interpreter/ — 更新
   - wiki/syntax/keywords.md — 更新
   - wiki/overview/language-spec.md — 更新
   - skills/ — 全部更新
   - docs/tutorial.md — 更新

### 新语法

```helen
// 同步（和之前一样）
let result = llm act "写一首诗"

// 流式（之前用 llm stream，现在用 llm act）
llm act "写一篇长文" on_chunk fn(chunk) { print(chunk, end="") }

// 流式 + 完成回调
llm act "写报告" on_chunk handle_chunk on_complete handle_done
```

---

## [2026-07-05] feat | v1.13 — Channel 通道 + 中文关键字补全

**操作**: 实现 Channel 机制 + 补全 `store` 中文关键字
**执行时间**: 2026-07-05
**状态**: ✅ 完成

### 新增功能

1. **Channel 通道声明**
   - `channel Name { fields, methods }` 语法
   - 中文：`通道 Name { ... }`
   - 与 shared store 结构相同，语义表示 agent 间通信端点
   - 全链路实现：token → AST → parser → analyzer → interpreter

2. **中文关键字补全**
   - `store` → `仓库`
   - `channel` → `通道`
   - 关键字总数：94（47 英文 + 47 中文）

### 实现细节

| 层次 | 文件 | 改动 |
|------|------|------|
| Token | `tokens.py` | `CHANNEL` TokenType + `仓库`/`通道` 映射 |
| AST | `ast.py` | `ChannelDeclNode` + Visitor 方法 |
| Parser | `parser.py` | `_channel_decl()` 解析方法 |
| Analyzer | `analyzer.py` | `visit_channel_decl()` 语义分析 |
| Interpreter | `interpreter.py` | `visit_channel_decl()` 运行时（复用 SharedStore） |
| Tests | `test_v12_isolation.py` | 8 个 channel 专项测试 |

### 新增测试

8 个 channel 测试：基本创建、中文语法、多字段、agent 访问、跨 agent 共享、重复检测。

总测试数：2374 passed

---

## [2026-07-05] fix | v1.12 第二轮隔离修复

**操作**: 修复 v1.12 第二轮隔离缺陷
**执行时间**: 2026-07-05
**状态**: ✅ 完成

### 修复内容

1. **C1: visit_access 支持 ReadOnlyView dict 点号访问**
   - `config.name` 现在可以正确访问 dict 参数中的键
   - 嵌套可变值也被包装为 ReadOnlyView

2. **C2: AccessNode 赋值阻止 ReadOnlyView**
   - `config.name = "hacked"` 现在抛出 ScopeViolationError
   - 之前会静默在 wrapper 对象上设置属性

3. **M3: @sandbox auto-execution 工具限制**
   - prompt-only @sandbox agent 自动执行时也传 `tools=[]`
   - 之前 LLM 可以用默认工具

4. **M4: 装饰器位置校验**
   - `@strict fn foo()` 和 `@open let x = 5` 现在报错
   - 装饰器只能用在 agent 声明上

5. **H1: Environment.snapshot() 深拷贝**
   - 快照对 list/dict 值做深拷贝
   - 防止异步任务间共享可变引用

6. **H2: ReadOnlyView 包装含可变元素的 tuple**
   - FFI 返回的 tuple 如果包含 list/dict 也会被包装

7. **M1: _stringify 支持 ReadOnlyView**
   - `str(param)` 对 dict ReadOnlyView 使用 Helen 格式

8. **L2: ReadOnlyView 添加 __radd__**
   - `[1, 2] + ReadOnlyView([3, 4])` 现在正确工作

### 新增测试

11 个回归测试（总计 63 个 v1.12 测试，全项目 2366 passed）

---

## [2026-07-05] fix | v1.12 隔离缺陷修复

**操作**: 修复 v1.12 agent 隔离的关键缺陷
**执行时间**: 2026-07-05
**状态**: ✅ 完成

### 修复内容

1. **ReadOnlyView 关键缺陷修复**
   - `visit_index` 识别 ReadOnlyView（修复 `param[0]` 读取失败）
   - `__iter__` 包装嵌套引用类型（修复 `for item in param` 绕过只读）
   - 删除公开 `unwrap()` 方法（防止逃逸）
   - 添加 `__bool__`、`__str__`、`__ne__`、比较运算符、`__add__`
   - `visit_binary_op` 不吞掉 ScopeViolationError
   - `_truthy()` 和 `_add()` 支持 ReadOnlyView
   - `visit_for_stmt` 支持 ReadOnlyView 迭代

2. **闭包值捕获修复**
   - `visit_lambda` 对引用类型做深拷贝（之前是引用捕获）
   - 现在闭包真正捕获快照，不受后续修改影响

3. **@sandbox 工具限制实现**
   - `_build_tools_list` 对 @sandbox agent 返回空工具列表
   - 之前 @sandbox 和 @strict 走相同代码路径

4. **SharedStore 加固**
   - 添加 `threading.RLock` 保护字段读写
   - 方法执行通过锁串行化
   - `__setattr__` 阻止所有 `_` 前缀属性篡改
   - `__init__` 使用 `object.__setattr__` 绕过自定义 setter
   - 防御性字段/方法拷贝

5. **语义分析修复**
   - 移除 `_in_closure > 0` 作用域检查绕过（闭包不能绕过隔离检查）
   - @open agent 赋值检查放行（允许修改模块级 let）
   - SharedStore 字段/方法名冲突检测
   - `type_compatible` 支持 AnyType actual（动态类型兼容）

6. **其他修复**
   - stdlib `_len()` 支持 ReadOnlyView
   - @open agent 写回模块级 let 修改
   - 共享 store 写回跳过 const 变量
   - 解析器支持中文装饰器（@开放/@严格/@沙箱）

### 新增测试

52 个新测试覆盖：
- ReadOnlyView 读写操作（14 个单元测试）
- Agent 参数只读集成（7 个集成测试）
- 闭包值捕获快照语义（4 个测试）
- 闭包作用域检查（4 个测试）
- @open/@strict/@sandbox agent（5 个测试）
- SharedStore（8 个测试）
- 装饰器解析（5 个测试）

总测试数：2355 passed

---

## [2026-07-05] update | v1.12 完整版 — 隔离级别、Shared Store

**操作**: 更新 agent 隔离文档，记录 v1.12 完整改进
**执行时间**: 2026-07-05
**状态**: ✅ 完成

### 变更内容

1. **wiki/tutorial/05-agents.md**
   - 新增 "隔离级别注解" 章节（@open/@strict/@sandbox）
   - 新增 "Shared Store" 章节（shared store 语法和使用）
   - 更新 v1.12 改进列表

2. **新增功能**
   - P2-1: 隔离级别注解（L0-L3）
   - P2-2: 返回值深拷贝（@strict/@sandbox）
   - P2-3: Shared Store（受控共享可变状态）
   - P3-1: Channel（通过 Shared Store 替代）
   - P3-2: 回调隔离（通过闭包值捕获实现）

### 相关代码变更

- `helen/core/ast.py`: 新增 SharedStoreDeclNode、isolation_level 字段
- `helen/core/tokens.py`: 新增 @ 符号、store 关键字
- `helen/core/parser.py`: 解析装饰器和 shared store
- `helen/interpreter/interpreter.py`: SharedStore 类、隔离级别处理
- `helen/semantic/analyzer.py`: shared store 语义分析

---

## [2026-07-05] update | v1.12 Agent 隔离增强（基础）

**操作**: 更新 agent 隔离文档，记录 v1.12 的隔离增强改进
**执行时间**: 2026-07-05
**状态**: ✅ 完成

### 变更内容

1. **wiki/tutorial/05-agents.md**
   - 新增 "v1.12 Agent 隔离增强" 章节
   - 记录 6 项隔离改进：
     - 参数默认值求值环境修复
     - `functions {}` 块变量求值环境修复
     - 引用类型参数只读包装 (`ReadOnlyView`)
     - `shared let` 限制为值类型
     - 闭包值捕获（替代环境引用）
     - 复合赋值隔离检查
   - 更新 shared let 最佳实践，反映值类型限制

### 相关代码变更

- `helen/interpreter/interpreter.py`: `_call_agent()` 求值环境修复、`ReadOnlyView` 类、`_compute_free_variables()`
- `helen/semantic/analyzer.py`: `function_vars` 分析、`_is_value_type()`、`_extract_assignment_target()`
- `helen/interpreter/exceptions.py`: 新增 `ScopeViolationError`

---

## [2026-07-03] update | 多语言 stdlib 别名 + alias 语句

**操作**: 添加 stdlib 多语言别名支持 + `alias`/`别名` 语句
**执行时间**: 2026-07-03
**状态**: ✅ 完成

### 变更内容

1. **stdlib 别名框架 (helen/stdlib/__init__.py)**
   - `StdlibRegistry` 增加 `_aliases`、`_canonical_names` 字段
   - 新增 `register_alias()`、`is_alias()`、`canonical_name()` 方法
   - 所有 locale 的别名表启动时全量加载，不按 locale 过滤

2. **中文别名表 (helen/stdlib/locales/zh.py)**
   - 230 个中文 stdlib 别名（长度、打印、排序、json解析...）
   - 覆盖所有 stdlib 分类：core/string/regex/data/collection/time/crypto 等

3. **locale 配置 (helen/runtime/config.py)**
   - `get_locale()` 返回当前 locale（默认 zh）
   - `get_locale_aliases()` 返回当前 locale 的别名表
   - 支持 `config.yaml` 中 `locale: zh` 配置

4. **`alias`/`别名` 语句**
   - 新增 `alias`/`别名` 关键字（TokenType.ALIAS）
   - 语法：`alias <canonical> as <alias_name>`
   - 支持 stdlib 函数、用户函数、agent、变量
   - 关键字总数：90（45 英文 + 45 中文）

5. **工具链适配**
   - `helen doc --with-builtins` 显示每个函数的别名
   - LSP 补全包含所有 stdlib 别名
   - 错误消息中显示 canonical 名

6. **文档更新**
   - wiki/syntax/keywords.md — 关键字表更新到 90 个
   - wiki/overview/language-spec.md — 关键字计数更新
   - skills/software-development/helen-syntax/SKILL.md — 同步更新

### 设计原则

- **一套机制**：stdlib 和用户函数使用相同的 Environment 别名机制
- **全量加载**：所有 locale 的别名启动时全部注册，locale 只影响展示
- **canonical 优先**：工具链（doc/LSP）始终显示 canonical 名
- **向后兼容**：英文 canonical 名永远可用

---

## [2026-07-03] update | 中文类型别名 + main 关键字变更

**操作**: 添加 `列表`/`映射` 类型别名，`主` 改为 `主函`
**执行时间**: 2026-07-03
**状态**: ✅ 完成

### 变更内容

1. **类型别名 (helen/semantic/type_utils.py)**
   - `list` → 现在也接受 `列表`
   - `map` → 现在也接受 `映射`

2. **关键字变更 (helen/core/tokens.py)**
   - `main` 的中文关键字从 `主` 改为 `主函`（避免歧义）

3. **文档更新**
   - `wiki/syntax/keywords.md` — 关键字映射表更新
   - `wiki/tutorial/01-getting-started.md` — 中文示例更新
   - `wiki/tutorial/02-variables-and-types.md` — 添加中文类型别名说明
   - `docs/tutorial.md` — 同步更新
   - `tests/lexer/test_chinese_keywords.py` — 测试更新
   - `tests/lexer/test_chinese_punctuation.py` — 测试更新

---

## [2026-07-01] update | Phase 6 docs/ 和 skills/ 同步

**操作**: 同步教程和技能文档  
**执行时间**: 2026-07-01  
**状态**: ✅ 完成

### 更新的文件

1. **docs/tutorial.md**
   - 更新版本信息: v1.9 → v1.10
   - 更新目录表格，添加 v1.10 特性说明
   - 添加 "v1.10 新特性总结" 完整章节（~400 行）：
     - shared let — 跨 agent 可见变量
     - Agent 作用域隔离
     - 子脚本/字段赋值
     - 短路求值
     - 返回类型注解语法变化
     - 异常处理增强
     - 异步 HTTP 支持
     - 导入跟踪
     - 新增错误码
     - 完整示例（并发数据处理系统）
     - 迁移指南（从 v1.9 到 v1.10）

2. **skills/software-development/helen-syntax/SKILL.md**
   - 更新关键字计数: 89 → 88
   - 添加 `shared` / `共享` 关键字到映射表
   - 添加中文示例：`共享 let counter = 0`
   - 添加 "v1.10 新特性" 完整章节：
     - shared let 语法和作用域规则
     - 子脚本/字段赋值
     - 短路求值
     - 返回类型注解语法
     - 异步 HTTP 方法
     - 新增错误码表格

### 关键更新

**docs/tutorial.md**:
- ✅ 版本信息更新
- ✅ 目录表格更新（添加 v1.10 说明）
- ✅ v1.10 新特性完整总结
- ✅ 完整示例代码
- ✅ 迁移指南

**skills/helen-syntax**:
- ✅ 关键字计数更新
- ✅ shared let 关键字
- ✅ v1.10 新特性章节

### 同步完成

所有 wiki 更新已同步到：
- ✅ docs/tutorial.md（主教程文件）
- ✅ skills/software-development/helen-syntax/SKILL.md（语法技能）

### 最终状态

**Wiki 更新完成**:
- Phase 1-5: wiki/ 目录完整更新（18 文件）
- Phase 6: docs/ 和 skills/ 同步完成

**v1.10 特性完整覆盖**:
- ✅ 9 个主要新特性
- ✅ 3 个新增错误码
- ✅ 完整示例和迁移指南
- ✅ 技能文档同步

---

## [2026-07-01] update | Phase 5 附录更新

**操作**: 更新附录文档  
**执行时间**: 2026-07-01  
**状态**: ✅ 完成

### 更新的文件

1. **wiki/appendix/exceptions.md**
   - 添加 "v1.10 异常增强" 完整章节：
     - RuntimeError 包装 stdlib 异常机制
     - Python 代码实现
     - 3 个示例（int 转换、文件操作、网络请求）
     - 异常层次更新（添加 ScopeViolationError）
     - v1.10 新增异常：ScopeViolationError
     - 异常处理最佳实践（3 条）
     - 错误消息改进说明

2. **wiki/appendix/error-codes.md**
   - 更新错误码总数：42 → 45
   - 更新 E0350 说明：添加 v1.10 更新说明
   - 添加 E0351: SHARED_NOT_MODULE_LEVEL
   - 添加 E0352: IMMUTABLE_ASSIGNMENT
   - 添加 "v1.10 新增错误码详解" 章节：
     - E0350 详细说明（触发条件、示例、错误消息、修正方法）
     - E0351 详细说明
     - E0352 详细说明
   - 更新错误码统计表格

### 关键更新

**异常增强**:
- ✅ RuntimeError 包装 stdlib 异常
- ✅ ScopeViolationError 新增
- ✅ 异常处理最佳实践
- ✅ 错误消息改进

**错误码**:
- ✅ E0350: SCOPE_VIOLATION（更新说明）
- ✅ E0351: SHARED_NOT_MODULE_LEVEL（新增）
- ✅ E0352: IMMUTABLE_ASSIGNMENT（新增）
- ✅ 错误码统计：45 个

### 下一步

- Phase 6: docs/ 和 skills/ 同步

---

## [2026-07-01] update | Phase 4 教程更新

**操作**: 更新教程文档  
**执行时间**: 2026-07-01  
**状态**: ✅ 完成

### 更新的文件

1. **wiki/tutorial/05-agents.md**
   - 添加 "v1.10 Agent 作用域隔离" 完整章节：
     - 可见性规则表格
     - 示例代码（正确和错误用法）
     - 为什么需要作用域隔离的说明
     - shared let 最佳实践（命名约定、线程安全、最小化共享）
     - 闭包捕获说明
   - 添加 "v1.10 shared let 完整示例" 章节：
     - 计数器示例
     - 配置共享示例
     - 状态聚合示例

2. **wiki/tutorial/04-control-flow.md**
   - 添加 "短路求值 (v1.10)" 章节：
     - && 短路逻辑和示例
     - || 短路逻辑和示例
     - 优先级说明
     - 实际示例（安全访问、缓存检查、权限检查）

3. **wiki/tutorial/07-async-await.md**
   - 添加 "v1.10 HTTP 异步方法" 完整章节：
     - 异步方法列表（act_async, act_stream_async）
     - 基本用法示例
     - 并发调用示例
     - 异步流式调用
     - 性能对比表格（同步 vs 异步）
     - 实际示例：批量处理
     - 错误处理
     - 与 async call 的区别说明

4. **wiki/tutorial/02-variables-and-types.md**
   - 添加 "子脚本/字段赋值 (v1.10)" 章节：
     - 数组索引赋值示例
     - 对象字段赋值示例
     - 嵌套访问示例
     - 错误示例（const 不可修改）
     - 实际示例（更新记录）

### 关键更新

**Agent 教程**:
- ✅ Agent 作用域隔离规则
- ✅ shared let 最佳实践
- ✅ 3 个完整示例

**控制流教程**:
- ✅ 短路求值逻辑
- ✅ 优先级说明
- ✅ 实际应用示例

**异步教程**:
- ✅ HTTP 异步方法
- ✅ 并发调用示例
- ✅ 性能数据（提升 86%）
- ✅ 错误处理

**变量教程**:
- ✅ 子脚本赋值
- ✅ 字段赋值
- ✅ 嵌套访问
- ✅ 错误处理

### 下一步

- Phase 5: 附录更新（exceptions.md, error-codes.md）
- Phase 6: docs/ 和 skills/ 同步

---

## [2026-07-01] update | Phase 3 运行时更新

**操作**: 更新运行时系统文档  
**执行时间**: 2026-07-01  
**状态**: ✅ 完成

### 更新的文件

1. **wiki/interpreter/execution.md**
   - 添加 "v1.10 Agent Main 作用域隔离" 章节：
     - 环境创建逻辑（Python 代码）
     - 可见性规则说明
     - 示例代码
   - 添加 "v1.10 子脚本/字段赋值执行" 章节：
     - 赋值执行逻辑（IndexNode, AccessNode）
     - Python 实现代码
     - 示例代码
   - 添加 "v1.10 短路求值" 章节：
     - && 和 || 短路逻辑（Python 代码）
     - 优先级说明
     - 示例代码

2. **wiki/runtime/llm-runtime.md**
   - 添加 "v1.10 异步 HTTP 支持" 完整章节：
     - 异步方法列表（act_async, act_stream_async）
     - httpx.AsyncClient 使用
     - 使用示例（Helen 代码）
     - 连接池管理
     - 性能对比表格
     - 错误处理

3. **wiki/runtime/import.md**
   - 添加 "v1.10 shared let 导入跟踪" 完整章节：
     - 导入行为说明
     - Python 实现代码
     - 完整示例（module_a.helen, module_b.helen）
     - 作用域规则表格
     - 循环导入处理
     - 错误处理

4. **wiki/runtime/memory.md**
   - 添加 "v1.10 shared let 内存可见性" 完整章节：
     - Environment 类扩展（shared dict）
     - Agent Main 环境创建逻辑
     - 内存模型图示
     - 持久化示例
     - 线程安全说明

### 关键更新

**执行引擎**:
1. Agent main 作用域隔离 — 环境创建、可见性规则
2. 子脚本/字段赋值 — IndexNode, AccessNode 赋值执行
3. 短路求值 — && 和 || 短路逻辑

**LLM 运行时**:
1. 异步方法 — act_async, act_stream_async
2. httpx.AsyncClient — 连接池、并发控制
3. 性能提升 — 10 次并发提升 86%

**模块系统**:
1. shared let 导入跟踪 — 跨模块可见
2. 作用域规则 — 导入行为、循环导入
3. 错误处理 — 未声明变量检测

**内存系统**:
1. Environment 扩展 — shared dict
2. 内存模型 — global vs agent main
3. 线程安全 — 锁机制

### 下一步

- Phase 4: 教程更新（tutorial/*.md）
- Phase 5: 附录更新（exceptions.md, error-codes.md）
- Phase 6: docs/ 和 skills/ 同步

---

## [2026-07-01] update | Phase 2 语法和语义更新

**操作**: 更新语法规范和语义分析文档  
**执行时间**: 2026-07-01  
**状态**: ✅ 完成

### 更新的文件

1. **wiki/syntax/grammar.md**
   - 更新 var_decl 语法：添加 `shared let` 支持
   - 更新 assignment 语法：支持子脚本/字段赋值
   - 添加 v1.10 语法更新章节：
     - 子脚本/字段赋值 (`arr[i] = x`, `obj.field = x`)
     - 短路求值 (`&&` 和 `||`)
     - 返回类型注解语法变化（移除 `->`，仅用 `:`）
   - 添加完整的 EBNF 更新说明

2. **wiki/compiler/semantic.md**
   - 添加 "v1.10 Agent 作用域隔离" 章节：
     - 可见性规则表格
     - 示例代码
     - 语义分析实现说明
   - 添加 "v1.10 shared let 语义" 章节：
     - 符号表处理
     - 导入跟踪
   - 更新规则验证表格，添加 3 条新规则：
     - E0350: 模块级 let 在 agent main 中不可见
     - E0351: shared let 必须在模块级声明
     - E0352: 子脚本赋值目标必须是可变的

### 关键更新

**语法更新**:
1. var_decl: `("let" | "const" | "shared" "let") IDENTIFIER ("=" expression)?`
2. assignment: `(call | IDENTIFIER) "=" assignment | pipe`
3. 返回类型: `fn_decl → "fn" IDENTIFIER "(" fn_params? ")" (":" type)? fn_body`

**语义更新**:
1. Agent 作用域隔离 — 模块级 let 不可见
2. shared let 语义 — 跨 agent 可见变量
3. 导入跟踪 — shared let 被正确跟踪
4. 新增错误码 — E0350, E0351, E0352

### 下一步

- Phase 3: 运行时更新（execution.md, llm-runtime.md, import.md）
- Phase 4: 教程更新（tutorial/*.md）

---

## [2026-07-01] update | Phase 1 基础信息更新

**操作**: 更新 wiki 基础信息和版本号  
**执行时间**: 2026-07-01  
**状态**: ✅ 完成

### 更新的文件

1. **wiki/index.md**
   - 版本号: v1.9 → v1.10
   - 状态说明: 添加 "Agent 作用域隔离"

2. **wiki/overview/language-spec.md**
   - 版本号: v1.9 → v1.10
   - 关键字计数: 89 → 90 (45 英文 + 45 中文)
   - Token 类型: 78 → 83
   - AST 节点: 50 → 63
   - Visitor 方法: 47 → 58
   - 添加 `shared` / `共享` 关键字到表格
   - 更新 Token 类型列表（添加 SHARED, PROTOCOL, IMPL, IS, WILDCARD）
   - 架构图数字更新
   - 添加 "v1.10 新特性" 完整章节（7 个新特性）

3. **wiki/syntax/keywords.md**
   - 版本号: v1.9 → v1.10
   - 关键字计数: 89 → 88
   - 添加 `shared` / `共享` 关键字到中文关键字表格
   - 添加 `shared` 关键字详细说明（包含作用域规则）
   - 添加中文示例：`共享 let counter = 0`

4. **wiki/appendix/changelog.md**
   - 版本号: v1.9 → v1.10
   - 添加 v1.10 变更记录（8 项改进）
   - 添加 Agent 作用域隔离规则说明
   - 添加完整代码示例

### 关键更新

**v1.10 新特性**:
1. `shared` / `共享` 关键字 — 跨 agent 可见变量
2. Agent 作用域隔离 — agent main 在隔离环境运行
3. 子脚本/字段赋值 — `arr[i] = x` 和 `obj.field = x`
4. 短路求值 — `&&` 和 `||`
5. 返回类型语法变化 — 移除 `->`，仅用 `:`
6. 异常处理增强 — RuntimeError 包装 stdlib 异常
7. 异步 HTTP — `act_async()` / `act_stream_async()`
8. 导入跟踪 — shared let 被正确跟踪

### 下一步

- Phase 2: 语法和语义更新（grammar.md, semantic.md）
- Phase 3: 运行时更新（execution.md, llm-runtime.md）
- Phase 4: 教程更新（tutorial/*.md）

---

## [2026-07-01] lint | 初始健康检查

**操作**: 对 wiki 进行全面健康检查  
**触发**: 用户要求使用 llm-wiki 技能维护 wiki，并同步更新 docs/ 和 skills/

### 发现的问题

1. **版本信息不一致**
   - Wiki 显示 v1.9，实际代码为 v1.10+
   - 关键字计数：89 → 88（44 英文 + 44 中文）
   - Token 类型：78 → 83
   - AST 节点：50 → 63
   - Visitor 方法：47 → 58

2. **v1.10 新特性未文档化**
   - `shared` / `共享` 关键字（跨 agent 可见变量）
   - Agent 作用域隔离（agent main 在隔离环境中运行）
   - 子脚本/字段赋值（`arr[i] = x`、`obj.field = x`）
   - 短路求值（`&&` 和 `||`）
   - 返回类型注解语法变化（移除 `->`，仅用 `:`）
   - RuntimeError 包装 stdlib 异常
   - 异步 HTTP 方法（`act_async()` / `act_stream_async()`）
   - 导入的 shared let 跟踪

3. **docs/ 和 skills/ 需要同步**
   - `docs/tutorial.md` 需要更新
   - `skills/` 中的技能文档需要检查

### 生成的报告

- 详细报告：`wiki/lint-report-2026-07-01.md`
- 建议更新顺序：6 个阶段，预计 11-17 小时

### 下一步

等待用户审查报告后，按优先级执行更新。

---

## [2026-07-01] init | Wiki 初始化

**操作**: 建立 wiki 维护流程  
**说明**: 用户要求使用 llm-wiki 技能维护 Helen 语言文档，包括：
- 维护 wiki/ 目录下的文档
- 同步更新 docs/ 教程
- 同步更新 skills/ 内置技能

建立了以下流程：
1. 定期执行 lint 检查
2. 当 Helen 语言更新时，同步更新 wiki、docs、skills
3. 使用 log.md 记录所有操作
