# 版本历史

> Helen v1.21 (开发中) — `on_tool_end` 回调：工具执行后注入 hint 到 agentic loop

---

## v1.21: on_tool_end 回调 — Agentic Loop 中间注入提示 (开发中)

**核心特性**: `llm act` 新增 `on_tool_end` 回调，在每个工具执行完毕后调用用户回调，返回值注入为 LLM 可见的消息。

### 新增语法

```helen
llm act "task"
    on_tool_end fn(tool_name: str, tool_result: str): str | dict | null {
        if tool_name == "write_file" {
            return "文件已写入，下一步可以运行测试验证"
        }
        if tool_name == "shell_exec" {
            return {"role": "system", "content": "禁止执行危险命令"}
        }
        return null  // 不注入
    }
```

### 回调行为

- 返回 `str` → 注入为 `user` 消息，带 `[System Hint]` 前缀
- 返回 `dict` → `{"role": "user"|"system", "content": "..."}`，完全控制消息格式
- 返回 `null` → 不注入
- 回调异常不影响 agentic loop（non-fatal，debug 级别日志）

### 中文别名补齐

所有 `llm act` 回调现在都有中文别名：

| 英文 | 中文别名 | 版本 |
|------|----------|------|
| `on_chunk` | `逐块处理` | v1.21 补齐 |
| `on_complete` | `完成` | v1.21 补齐 |
| `on_tool_end` | `工具结束` | v1.21 新增 |
| `on_media` | `处理媒体` | v1.17 已有 |
| `on_generate` | `生成` | v1.17 已有 |

### 架构变更

- `LlmActExprNode` 新增 `on_tool_end: ExpressionNode | None` 字段
- Parser: `_llm_act_expr()` 和 `_llm_act_stmt()` 支持解析 `on_tool_end` 及中文别名
- `http_llm.py`: `act()` 和 `act_stream()` 新增 `on_tool_end_fn` 参数，在工具结果 append 后、reactive compaction 前调用
- `llm_mixin.py`: 提取并传递 `on_tool_end_fn` 到 runtime
- `act_stream()` 额外 yield `{"type": "hint", ...}` 事件

### 测试

- 新增 12 个 parser 测试（`tests/parser/test_llm_on_tool_end.py`）
- 新增 7 个 runtime 测试（`tests/runtime/test_on_tool_end.py`）
- 全部 2942 测试通过，0 failures

---

## v1.20: Transcript 会话作用域 + PyPI 发布 (当前)

**发布日期**: 2026-07-15
**核心特性**: transcripts 默认按应用目录隔离；**PyPI 正式上线**

### PyPI 发布 🎉

**Helen 语言现在可以通过 pip 安装！**

```bash
pip install helen-lang
```

发布准备（7 项清理）：
1. 包名 `helen` → `helen-lang`（PyPI 上 `helen` 已被占用）
2. 版本号对齐：`pyproject.toml` 与 `helen/__init__.py` 统一为 `1.20.0`
3. 作者邮箱更新为 `2229855189@qq.com`
4. 新增 MIT LICENSE 文件
5. README 重写（反映 v1.20 + PyPI badges + 安装命令）
6. Skills 移入包内：`skills/` → `helen/skills/`（wheel 自动包含）
7. MANIFEST.in 创建，包含 LICENSE/skills/py.typed
8. 新增 `py.typed` 标记（PEP 561，支持 mypy 等类型检查器）

**本地验证**：
- ✅ 隔离 Python 3.12 环境 `pip install helen-lang` 成功
- ✅ `helen --version` → "Helen 1.20.0"
- ✅ 17 个内置 skills 从 site-packages 正确加载
- ✅ 全部 2917 测试通过

### 设计原则

**Transcripts 是应用数据，不是语言基础设施**。v1.20 之前所有 transcripts 都在全局 `~/.helen/sessions/`，导致：
- 应用 A 和 B 的 transcripts 混在一起，归属不清
- 清理困难（需从一堆 UUID 里筛选）
- 不可移植（mv 应用目录不带走 transcripts）
- 容器化不友好（需要挂载 `~/.helen`）

v1.20 引入"会话作用域"概念：transcripts 可以按应用隔离。

### 新增配置项

```yaml
# ~/.helen/config.yaml
transcript:
  session_scope: "auto"           # "auto" (默认) | "global" | "project"
  session_dir: "~/.helen/sessions"            # scope=global 时使用
  project_session_dir: ".helen/sessions"      # scope=project 时使用
```

### 三种作用域模式

| 模式 | 路径 | 适用场景 |
|------|------|----------|
| `global` | `~/.helen/sessions/` | REPL 探索、跨项目共享 |
| `project` | `<project>/.helen/sessions/` | 长期应用、生产部署 |
| `auto` (默认) | 检测项目目录，有则 project，无则 global | 推荐默认 |

### 项目检测

通过向上查找以下标记之一检测项目根目录：
- `.helen/`（目录）—— 但排除 `~/.helen`（用户全局配置）
- `helen.yaml` / `helen.yml` / `helen.toml`

### 环境变量覆盖

`HELEN_SESSION_DIR` 强制指定 transcripts 路径，优先级最高：

```bash
HELEN_SESSION_DIR=/data/myapp/sessions helen myapp.helen
```

### 新增 stdlib 函数（2 个）

```helen
// 查询当前会话目录
let info = get_session_dir()
// {session_dir: "...", scope: "global"|"project"|"env_override", project_dir: "..."|None}

// 运行时切换（仅当前进程，不修改 config.yaml）
set_session_dir("./my_app_sessions")
```

**中文别名**: `获取会话目录`, `设置会话目录`

### 兼容性

- **默认行为变更**: v1.20 之前默认全局；v1.20 默认 auto（自动检测）。在没有项目标记的目录下运行时，行为与 v1.19 一致（全局）。
- 显式 `session_scope: "global"` 可强制恢复旧行为。
- `HELEN_SESSION_DIR` 环境变量始终优先。

### 测试

- 新增 28 个测试覆盖作用域检测、路径解析、环境变量、stdlib 函数
- 全部测试通过，向后兼容

---

## v1.19: 上下文管理 API 完善

**发布日期**: 2026-07-15
**核心特性**: 补齐上下文管理的"检查"与"细粒度写入"两个维度，让 Agent 能**看见**并**操作**自己的上下文

### 主要变更

Helen v1.19 共新增 **24 个 stdlib 函数**（上下文类从 3 个扩展到 27 个），按优先级分 P0/P1/P2/P3 四批实现：

#### P0：Inspection + 细粒度基础（6 个）
```helen
context_stats()           // 上下文统计（消息数/token/占用率/角色分布）
context_usage()           // 占用率（0.0–1.0+）
get_message(uuid)         // 按 UUID 读取消息
delete_message(uuid)      // 按 UUID 逻辑删除
pin_message(uuid)         // 钉住消息（免疫 5 层压缩）
unpin_message(uuid)       // 取消钉住
```

#### P1：Working Memory + Lifecycle Hooks（6 个）
```helen
working_memory_get(key?)  // 读工作记忆（task/active_files/decisions/todos/errors）
working_memory_set(k, v)  // 写工作记忆
working_memory_remove(k)  // 移除
working_memory_clear()    // 清空
on_compression(callback)  // 压缩事件回调
on_context_overflow(cb)   // 溢出回调（预留）
```

#### P2：Fine-grained Mutation + Runtime Config + Transfer（11 个）
```helen
// Mutation
insert_message(role, content, position?)  // 插入消息
replace_message(uuid, new_content)        // 替换消息

// Runtime Configuration (v1.19 之前只能在 agent context {} 声明)
set_compression_strategy(strategy)        // "graduated" | "traditional" | "none"
set_context_window(tokens)                // 设置上下文窗口大小
set_working_memory_enabled(bool)          // 开关工作记忆
set_cache_aware(bool)                     // 开关缓存感知
get_context_config()                      // 查询配置

// Multi-Agent Transfer
export_context()                          // 导出为 dict
import_context(data)                      // 导入替换
fork_context()                            // 深拷贝
```

#### P3：Query + Extras（2 个）
```helen
search_context(query, role?, limit?)      // 全文搜索
context_slice(start?, end?, role?)        // 提取切片
```

### Pinned 消息免疫压缩

`Message.pinned: bool` 字段加入 `history.py`。所有 5 层渐进压缩（Layer 1 Budget Reduction、Layer 2 Snip、Layer 3 Microcompact、Layer 4 Context Collapse、Layer 5 Auto-Compact）都已更新为跳过 pinned 消息。

### 内部化 `classify_message`

`classify_message` 从 stdlib 公开 API 中移除，内部化为 `_classify_message`。中文别名"消息分类"同步移除。

### 中文别名（v1.19 新增 24 个）

详见 `helen/stdlib/locales/zh.py` 和 `wiki/runtime/context-management.md § 8.5.8`。

### 兼容性

- 完全向后兼容。所有 2853 个既有测试通过。
- 新增 57 个测试覆盖新函数与 pinned 压缩免疫行为（总测试 2889）。
- 原 `classify_message` 调用会报"未找到函数"错误——这是**故意**的 breaking change（该函数本就是内部件，不应被外部使用）。

### stdlib 总数

- 255 → 267 → **285 builtins**（v1.19 本轮 +18）
- Context 类：3 → 9 → **27 个函数**

---

## v1.18: spawn 并发原语

**发布日期**: 2026-07-13

> Helen v1.18 | spawn 并发原语 — `spawn` + Channel 消息队列替代 `async/await/detach`，snapshot 全部深复制，89 关键字

---

## v1.18: spawn 并发原语 (当前)

**发布日期**: 2026-07-13  
**核心特性**: `spawn` + Channel 消息队列统一并发与通信模型，替代旧的 `async/await/detach`

### 主要变更

#### 1. spawn 并发原语

```helen
agent Worker(task: str, reply: Channel) {
    description "后台工作 agent"
    main {
        let result = llm act "处理" + task
        reply.send(result)
    }
}

main {
    let mailbox = spawn Worker("数据分析")
    let result = mailbox.receive()
    print(result)
}
```

- `spawn` 返回 `Channel` 类型（邮箱）
- spawned agent 最后一个参数接收通信 channel（自动注入）
- 支持双向通信、流式进度、竞争模式

#### 2. Channel 消息队列

- `Channel` 运行时类型（`helen/runtime/channel.py`）
- 双队列设计：`_to_spawned` + `_from_spawned`
- `send(msg)` / `receive(timeout?)` / `try_receive()` / `cancel()` / `close()` / `is_closed()`
- 中文方法别名：`发送`/`接收`/`尝试接收`/`取消`/`关闭`/`已关闭`
- `Channel()` 构造函数创建独立 channel
- `mailbox_select([channels])` stdlib 多路复用

#### 3. snapshot 语义变更

- **全部深复制，无例外**（包括 SharedStore）
- `SharedStore.__deepcopy__`：fields 深复制，methods 不复制
- 共享通过 channel 显式传递引用

#### 4. 删除清单

| 删除 | 替代 |
|------|------|
| `async` / `await` / `detach` 关键字 | `spawn` / `分生` |
| `AsyncCallStmtNode` / `AsyncCallExprNode` / `DetachStmtNode` | `SpawnExprNode` |
| `ChannelDeclNode` / `channel X { fields }` | `Channel()` 构造函数 |
| `ForAwaitStmtNode` | `on_chunk` 回调 |
| `AsyncLLMInterpreter` (`async_interpreter.py`) | 新 Interpreter + Thread |
| `Task` 类 (`task.py`) | Channel 端点 |
| `act_async()` / `act_stream_async()` / `route_async()` | spawn |

#### 5. 关键字变更

- 新增：`spawn` / `分生`
- 删除：`async` / `异步`、`await` / `等待`、`detach` / `分离`、`channel`（声明）/ `通道`（声明）
- 总数：97 → 89（44.5 英文 + 44.5 中文）

#### 6. 迁移指南

```helen
// 旧：detach + shared store 轮询
shared store Result { let done = false; let data = "" }
detach Worker("task")
循环 { 如果 Result.done { 跳出 } sleep(100) }

// 新：spawn + channel
let m = spawn Worker("task")
let data = m.receive()

// 旧：async/await
let t = async Agent("task")
let result = await t

// 新：spawn + receive
let m = spawn Agent("task")
let result = m.receive()

// 旧：channel 声明语法
channel EventBus { let last_event = "" }

// 新：shared store（带锁结构体）或 Channel（消息队列）
shared store EventBus { let last_event = "" }
```

### 测试

- 新增测试：`test_spawn.py`、`test_channel.py`、`test_mailbox_select.py` 等
- 总测试数：2791 passed

---

## v1.17: 多模态格式适配器 stdlib (当前)

**发布日期**: 2026-07-09  
**核心特性**: 将 provider 格式转换作为 stdlib 纯函数暴露，程序员不再需要手写 provider 特定 JSON 形状

### 背景

v1.17-alpha 引入了 `MediaPart` 数据类型和 `on_media`/`on_generate` 回调机制，采用"回调即适配器"设计。但 provider 格式知识仅存在于提案文档和 skill 中，程序员在 `on_media` 回调中必须从零手写 JSON 格式。本次更新将这些知识提升为 stdlib 函数。

### 新增 stdlib 函数 (8)

#### 格式适配器

| 函数 | 中文别名 | 说明 |
|------|---------|------|
| `to_openai_parts(parts)` | `转OpenAI格式(parts)` | MediaPart[] → OpenAI content_parts 格式 |
| `to_claude_parts(parts)` | `转Claude格式(parts)` | MediaPart[] → Anthropic content_blocks 格式 |
| `to_gemini_parts(parts)` | `转Gemini格式(parts)` | MediaPart[] → Gemini inline_data 格式 |

#### 媒体工具

| 函数 | 中文别名 | 说明 |
|------|---------|------|
| `media_to_base64(part)` | `媒体转base64(part)` | 任意 source → 纯 base64 字符串 |
| `save_media(part, path?)` | `保存媒体(part, path?)` | 保存 MediaPart 到文件，返回路径 |

#### 类型谓词

| 函数 | 中文别名 | 说明 |
|------|---------|------|
| `is_image(value)` | `是图片(value)` | 是否为图片 MediaPart |
| `is_video(value)` | `是视频(value)` | 是否为视频 MediaPart |
| `is_audio(value)` | `是音频(value)` | 是否为音频 MediaPart |

### 内部重构

- `_default_media_adapter`（`llm_mixin.py`）从 77 行内联代码重构为委托调用 `_to_openai_parts()`
- 行为 100% 一致，现有测试无回归

### 使用效果

```helen
# 重构前：手写 15 行 JSON 构造
on_media fn(parts, provider) {
    parts.map(fn(p) {
        {type: "image", source: {type: "base64", media_type: p.mime, data: ???}}
    })
}

# 重构后：一行
on_media fn(parts, provider) { 转Claude格式(parts) }
```

### 测试

- 53 个新测试（8 个测试类），总计 2875 passed

### 设计原则

stdlib 提供**确定性数据变换**（纯函数），skill 教授**编排模式**（HTTP 调用、轮询、错误恢复）。`to_claude_parts()` 之于"回调即适配器"，正如 `json_parse()` 之于"HTTP 由用户处理"——不违反设计原则。

---

## v1.16: TranscriptStore SSOT

**发布日期**: 2026-07-08  
**核心特性**: 将 TranscriptStore 作为所有对话消息的唯一真实来源（Single Source of Truth）

### 主要变更

#### Phase 1: 启用 + 持久化 ✅

- **TranscriptStore 默认启用**: `transcript_store_enabled=True`
- **SessionManager**: 会话生命周期管理，自动创建/恢复会话
- **JSONLBackend**: 崩溃安全的持久化后端（append-only）
- **配置支持**: `~/.helen/config.yaml` 添加 `transcript` 配置段
- **Stdlib 函数**: 6 个新函数
  - `get_session_id()` — 获取当前会话 ID
  - `list_sessions()` — 列出所有会话
  - `replay_transcript()` — 回放会话消息
  - `export_transcript()` — 导出 transcript（JSON/Markdown/Text）
  - `get_compression_audit()` — 获取压缩审计追踪
  - `resume_session()` — 恢复到指定会话
- **REPL 命令**: 6 个新命令
  - `:transcript` — 显示当前 transcript 视图
  - `:transcript --full` — 显示完整 transcript
  - `:transcript --audit` — 显示压缩审计
  - `:sessions` — 列出所有会话
  - `:session_id` — 显示当前会话 ID
  - `:resume <session_id>` — 恢复到指定会话
- **CLI 参数**: `--transcript-log <path>` — 自定义 transcript 输出路径

#### Phase 2: SSOT 切换 ✅

- **_history 变为只读视图**: `_history` 从 `list` 改为 `@property`，返回 `transcript_store.read_view()`
- **删除双写逻辑**: `_add_to_history()` 只写入 TranscriptStore，不再双写
- **删除 UUID 匹配方法**: 删除 74 行的 `_record_transcript_compression()` 方法，改为内联直接调用
- **_interpreter_history**: 作为 TranscriptStore 禁用时的回退存储

#### Phase 3: 非破坏性压缩 ✅

- **删除就地替换**: 删除 `self._history[:] = trimmed` 破坏性逻辑
- **BoundaryMarker**: 压缩只追加 BoundaryMarker，不修改原始消息
- **视图缓存**: dirty flag + 缓存，O(1) 读取
- **_prepare_history_for_llm()**: 使用 `transcript_store.read_view()` 获取压缩后视图

#### Phase 4: 内存卸载 ✅

- **SQLiteBackend**: WAL 模式，UUID 索引，高性能写入（<1ms/消息）
- **UUID 寻址**: `get(uuid)` 方法，O(1) 查找
- **LRU 缓存**: 可配置 `max_memory_items`（默认 1000），自动驱逐旧消息
- **内存优化**: 10K 消息 ~10MB（原来 ~200MB）

### 性能指标

| 场景 | 内存使用 | 磁盘使用 | 写入延迟 |
|------|---------|---------|---------|
| 100 消息 | ~1MB | ~100KB | <1ms |
| 1K 消息 | ~10MB | ~1MB | <1ms |
| 10K 消息 | ~10MB (LRU) | ~10MB | <1ms |
| 100K 消息 | ~50MB (LRU) | ~100MB | <1ms |

### 测试覆盖

- **新增测试**: 50 个（Phase 1-4）
- **总测试数**: 2750+ 全部通过
- **测试文件**:
  - `tests/runtime/test_transcript_persistence.py` (10 tests)
  - `tests/runtime/test_session_manager.py` (10 tests)
  - `tests/stdlib/test_transcript.py` (9 tests)
  - `tests/integration/test_phase1_ssot.py` (9 tests)
  - `tests/runtime/test_phase4_features.py` (12 tests)

### 配置文件

```yaml
# ~/.helen/config.yaml
transcript:
  enabled: true              # 默认启用
  backend: "sqlite"          # 或 "jsonl"
  session_dir: "~/.helen/sessions"
  max_memory_items: 1000     # LRU 缓存大小
```

### 架构变更

**之前**:
```
TranscriptStore (disabled, in-memory, dual-write)
→ 无持久化
→ 破坏性压缩
```

**之后**:
```
TranscriptStore (enabled, SSOT)
→ JSONLBackend / SQLiteBackend (持久化)
→ SessionManager (会话管理)
→ LRU Cache (内存优化)
→ UUID Addressing (O(1) 查找)
→ BoundaryMarkers (非破坏性压缩)
→ _history (只读视图)
```

### 向后兼容性

- ✅ **100% 向后兼容**: 所有现有代码无需修改
- ✅ **可选禁用**: 设置 `transcript.enabled: false` 回退到旧行为
- ✅ **回退存储**: TranscriptStore 禁用时使用 `_interpreter_history`

### 相关文档

- [[runtime/transcript-store|TranscriptStore SSOT]] — 完整架构文档
- [[docs/transcript_store_user_guide|用户指南]] — 使用教程
- [[docs/transcript_store_ssot_plan|设计文档]] — RFC 计划（已完成）

---

## v1.15: 系统提示词增强

参考 Claude Code 和 Hermes 的系统提示词设计，全面提升 LLM agent 的行为指导和执行质量。

### P0+P1: 框架指令 (Framework Instructions)

新增 `<framework_instructions>` 块，在所有 agent 的系统提示词中自动注入行为规则：

```xml
<framework_instructions>
You are a Helen agent with tools and skills available. Follow these rules:

## 1. Tool Use (CRITICAL)
You MUST use your tools to take action — do not describe what you would do
without actually doing it. When tools are available, use them instead of
telling the user what you would do. Execute, don't describe.

## 2. Skills (CRITICAL)
Before replying, scan <available_skills> below. If any skill matches or is
even partially relevant to your task, you MUST load it with load_skill and
follow its instructions. Err on the side of loading.

## 3. Parallel Tool Calls
When you need multiple independent pieces of information, request them
together in a single response instead of one tool call per turn. Independent
reads, searches, and read-only commands should be batched.

## 4. Completion Criteria
The deliverable is a working artifact backed by real tool output — not a
description of one. Keep working until you have actually exercised the code
or produced the requested result. Don't stop at "I would do X" — actually do X.

## 5. Memory Management
Save durable, reusable knowledge — skip transient or trivial details.

**Save** (high-value, persistent):
- Language features, APIs, patterns discovered
- User preferences, project conventions
- Environment details, tool configurations
- Recurring problems and solutions

**Skip** (low-value, transient):
- One-time task details
- Temporary debugging info
- Session-specific context
- Information already in skills/docs

**Principle**: If it won't be useful in the next session, don't save it.
</framework_instructions>
```

**改进内容**:

| 优先级 | 改进项 | 说明 |
|--------|--------|------|
| P0 | 工具使用强制 | MUST use tools, not describe |
| P0 | 技能加载强制 | MUST load relevant skills |
| P1 | 并行工具调用 | Batch independent tool calls |
| P1 | 完成准则 | Working artifact, not description |
| P1 | 记忆管理 | Save durable facts, skip trivial |

### P2: System/User 角色分离

重构提示词架构，实现 system prompt 和 user prompt 的清晰分离：

**改进前**:
```
System: framework + conventions + [agent prompt] ❌ + skill_index
User:   llm act expression

问题：Agent prompt 被错误地放在 system 中，角色混乱
```

**改进后**:
```
System: framework + conventions + description + skill_index ✅
User:   [agent prompt] + llm act expression ✅

效果：角色清晰，符合 LLM 最佳实践
```

**System Prompt 结构**:
1. Framework Instructions (P0+P1 行为规则)
2. Helen Language Conventions (语言规范)
3. Agent Description (角色定义)
4. Skill Index (技能索引 + 使用指令)

**User Prompt 结构**:
1. Rendered Agent Prompt (任务描述，如果存在)
2. LLM Act Expression (实际查询)

### 技能索引强化

强化 `<available_skills>` 的使用指令：

```
Before replying, scan skills below. If a skill matches or is
even partially relevant to your task, you MUST load it with
load_skill and follow its instructions. Err on the side of loading.
```

### 工具改进

**web_search**:
- 从 Wikipedia API 切换到 Bing.com 搜索
- 支持中国网络环境（无需翻墙）
- 支持通用网页搜索（不仅限于 Wikipedia）
- 支持 gzip/deflate 内容解压

**web_fetch**:
- 支持 gzip/deflate 内容解压
- 修复访问压缩网站时的乱码问题
- Python.org 等网站正常显示

**shell_exec**:
- 默认 `shell=True`，支持完整 shell 语法（`&&`、`||`、`|`、`>`、`<`、`;`、`$()`、`{}` 等）
- 使用 `/bin/bash` 执行（而非 `/bin/sh`），支持 brace expansion
- 简化实现：移除智能检测逻辑，代码从 15 行减少到 5 行
- 提供 `shell=False` 选项用于安全敏感场景

### stdlib 新增：上下文管理 (v1.15)

新增 2 个上下文管理函数，用于长对话 agent 的上下文控制：

**clear_context()** — 清空当前对话上下文
```helen
let result = clear_context()
// 返回: {"status": "ok", "cleared_messages": 5, "cleared_tokens": 1200}
```

**compress_context(strategy)** — 压缩当前对话上下文
```helen
let result = compress_context("auto")
// 策略: "auto" | "summarize" | "truncate" | "none"
// 返回: {"status": "ok", "original_tokens": 2000, "compressed_tokens": 1000}
```

**使用场景**:
- 长对话 agent 定期压缩上下文（避免 token 超限）
- 用户要求"重新开始"时清空上下文
- 错误恢复时重置上下文

**实现细节**:
- 通过 `_set_interpreter_context()` 注入解释器的 `_history` 和 `_history_manager`
- `clear_context()` 直接清空 `_history` 列表
- `compress_context()` 调用 `HistoryManager` 的压缩方法
- 11 个单元测试全部通过

### 实现变更

- `prompt_builder.py`: 新增 `_build_framework_instructions()` 方法
- `llm_mixin.py`: 重构 `visit_llm_act_expr` 的提示词构建逻辑
- `tools.py`: 改进 `web_search` (Bing)、`web_fetch` (gzip 支持)、`shell_exec` (默认 shell=True)
- `stdlib/context.py`: 新增上下文管理模块（`clear_context`、`compress_context`）
- `interpreter.py`: 注入解释器上下文到 stdlib（`_set_interpreter_context`）
- 测试：2395 个测试全部通过（新增 11 个上下文管理测试），无回归

### Token 预算

| 组件 | Token 数量 | 占比 |
|------|-----------|------|
| Framework Instructions | ~250 | 2.5% |
| Helen Conventions | ~800 | 8% |
| Agent Description | ~50 | 0.5% |
| Skill Index | ~200 | 2% |
| **总计** | **~1300** | **13%** |

在典型 32k-128k 上下文窗口中，系统提示词占比 <5%，完全可接受。

---

## v1.14: 合并 llm stream 到 llm act

**Breaking change**: `llm stream` 关键字已删除，流式功能合并到 `llm act`。

### 语言表面简化

| 改动 | 说明 |
|------|------|
| `llm stream` 删除 | 流式功能合并到 `llm act` |
| `llm act` 增加回调 | 支持可选 `on_chunk`/`on_complete` 参数 |
| 关键字减少 | 94 → 92（46 英文 + 46 中文） |
| `stream`/`流式执行` 关键字删除 | 不再是语言关键字 |

### 迁移指南

```helen
// 旧语法（v1.13 及以前）
llm stream "写一首诗"
llm stream "写长文" on_chunk handle_chunk

// 新语法（v1.14+）
llm act "写一首诗"
llm act "写长文" on_chunk handle_chunk
```

### 实现变更

- `LlmStreamStmtNode` 删除，`LlmActExprNode` 增加 `on_chunk`/`on_complete` 字段
- `visit_llm_stream_stmt` 删除，`visit_llm_act_expr` 分叉为同步/流式路径
- `STREAM` TokenType 删除

---

## v1.13: Channel 通道 + 中文关键字补全

### Channel 声明

新增 `channel`（中文：`通道`）声明，为 agent 间通信提供类型安全的结构化方式：

```helen
// 英文语法
channel Counter {
    count: int = 0
    fn increment() { count += 1 }
    fn get(): int { return count }
}

// 中文语法
通道 计数器 {
    计数: int = 0
    fn 增加() { 计数 += 1 }
    fn 获取(): int { 返回 计数 }
}
```

**Channel vs Shared Store**:

| 特性 | Shared Store | Channel |
|------|-------------|---------|
| 关键字 | `shared store` | `channel` |
| 中文 | `共享 仓库` | `通道` |
| 语义 | 共享状态容器 | 通信端点 |
| 运行时实现 | `SharedStore` 类 | 复用 `SharedStore` |
| 线程安全 | RLock | RLock |
| 私有字段 | `_` 前缀 | `_` 前缀 |

### 中文关键字补全

新增关键字：
- `store` → `仓库`
- `channel` → `通道`

关键字总数：94（47 英文 + 47 中文）

### 实现变更

- `tokens.py`: 新增 `CHANNEL` TokenType + `仓库`/`通道` 映射
- `ast.py`: 新增 `ChannelDeclNode` + Visitor 方法
- `parser.py`: 新增 `_channel_decl()` 方法
- `analyzer.py`: 新增 `visit_channel_decl()` 方法
- `interpreter.py`: 新增 `visit_channel_decl()`（运行时复用 `SharedStore` 类）

---

## v1.12: Agent 隔离增强 + Shared Store + 上下文管理

### 隔离改进

| 改动 | 说明 | 优先级 |
|------|------|--------|
| 参数默认值求值环境修复 | 默认值在 agent env 中求值，防止模块变量泄露 | P0 |
| `functions{}` 变量求值环境修复 | 初始化在 agent env 中求值 | P0 |
| `function_vars` 语义分析补全 | 类型检查 + 作用域检查 | P0 |
| 复合赋值隔离检查 | `arr[i]=x`/`obj.field=x` 现在正确检查作用域 | P0 |
| 引用类型参数只读包装 | list/dict 参数自动 `ReadOnlyView` 包装 | P1 |
| 闭包值捕获 | 替代环境引用捕获，防止 agent 环境逃逸 | P1 |
| `shared let` 值类型限制 | 只能使用 int/float/str/bool | P1 |
| 隔离级别注解 | `@open`/`@strict`/`@sandbox` | P2 |
| Shared Store | 结构化共享可变状态 | P2 |

### `@sandbox` 隔离注解 (P2)

```helen
@sandbox agent SafeWorker {
    // 只能访问 params 和 const
    // 不能调用任何外部工具
    main { ... }
}
```

| 隔离级别 | 模块 let | 模块 const | shared let | 外部工具 |
|----------|----------|------------|------------|----------|
| 标准 (默认) | ❌ | ✅ | ✅ | ✅ |
| `@open` | ✅ | ✅ | ✅ | ✅ |
| `@strict` | ❌ | ✅ | ✅ (深拷贝) | ✅ |
| `@sandbox` | ❌ | ✅ | ❌ | ❌ |

### Shared Store (P2)

`shared store` 为跨 agent 共享可变引用类型提供结构化方式：

```helen
shared store Cache {
    data: dict = {}
    _lock_count: int = 0  // 私有字段（_前缀），agent 不可直接访问

    fn get(key): any { return data[key] }
    fn set(key, value) { data[key] = value }
    fn size(): int { return len(data) }
}

agent Worker(cache: Cache) {
    main {
        cache.set("key", "value")  // ✅ 通过方法访问
        // cache.data = {}          // ❌ 可以（公共字段）
        // cache._lock_count = 0    // ❌ ScopeViolationError
    }
}
```

### Bug 修复

- **参数默认值环境**: 修复默认值在 caller 环境中求值的问题
- **闭包捕获**: 闭包采用值快照而非环境引用，防止 agent 环境逃逸

### 上下文管理优化

| 改动 | 说明 | 优先级 |
|------|------|--------|
| user 消息去重 | 修复 `act()` 重复追加 user 消息的代码味道 | P0 |
| bare form system_prompt 修复 | 不再将 prompt 模板同时放入 system 和 user message | P0 |
| Tool calling 上下文可见 | `_history` 记录 tool 调用摘要，后续 `llm act` 可引用 | P1 |
| act_stream 网络重试 | 流式调用增加指数退避重试（5xx/429/网络错误） | P2 |
| PromptBuilder 统一 | 单一来源：嵌套访问 + mtime 缓存 + 描述截断 | P2 |
| Token 估算改进 | 可选 tiktoken 精确计数 | P3 |
| History 压缩优化 | 三种压缩模式（summarize/truncate/none） | P3 |
| History 持久化 | `save_history()` / `load_history()` 跨会话保留对话 | P4 |
| History 检索 | `search_history()` / `get_tool_history()` 多条件查询 | P4 |
| 上下文可视化 | REPL `:stats` 命令 + 进度条 + 角色分布 | P4 |

---

## v1.11: shared let 写回 + 异常层级修复

| 改动 | 说明 | 状态 |
|------|------|------|
| shared let 写回 | Agent 内部修改 `shared let` 后，调用者可见修改后的值 | ✅ |
| 异常层级修复 | `LLMError`/`RuntimeError`/`ToolError`/`AssertionError`/`AggregateError` 统一继承 `AnyError` | ✅ |
| catch AnyError | `catch AnyError` 现在可以捕获所有 Helen 异常类型 | ✅ |
| 异常路径写回 | agent 抛异常时，shared let 修改仍通过 `finally` 写回 | ✅ |

### Bug 修复：shared let 写回

**问题**：Agent 内部对 `shared let` 变量的修改不影响外部。Agent 调用结束后，shared let 恢复原值。

**根因**：Agent 隔离 Environment 在创建时，将 shared let 的**值拷贝**到自己的 `_store`。Agent 内部的赋值只修改本地副本，返回时没有写回 caller。

**修复**：在 `_call_agent()` 的 `finally` 块中，遍历 `_shared_vars`，将 agent 环境中修改过的 shared let 值写回到调用者的作用域链。

```helen
shared let counter = 0

agent ModifyShared() {
    main {
        counter = 999  // agent 内部修改
        return "done"
    }
}

main {
    counter = 100
    ModifyShared()
    print(counter)  // ✅ 输出 999（之前是 100）
}
```

**嵌套 agent 也正确工作**：内层 agent 修改 shared let → 写回到外层 agent 环境 → 外层 agent 返回时再写回到模块级环境。

**异常路径**：即使 agent 抛出异常，`finally` 块中的写回逻辑仍会执行，确保已完成的修改不会丢失。

**质量**: 11 个新测试（基础写回、累加、嵌套、字典修改、异常路径、隔离保持等）

### Bug 修复：异常层级

**问题**：`catch AnyError` 无法捕获 `AgentError`、`RuntimeError`、`ToolError` 等异常。文档说 `AnyError` 是 catch-all，但实际这些异常类直接继承 `HelenRuntimeError`，跳过了 `AnyError`。

**修复**：所有 Helen 可捕获异常统一继承 `AnyError`：

```
HelenRuntimeError (Python 基类, visit_try_stmt 捕获)
└── AnyError (Helen catch-all)
    ├── LLMError
    │   ├── TimeoutError
    │   ├── ModelError
    │   └── AgentError
    ├── ToolError
    ├── RuntimeError
    ├── AssertionError
    └── AggregateError
```

`catch AnyError` 现在可以捕获所有 Helen 异常，符合文档承诺。

---

## v1.10: 上下文窗口保护 (HLD 3.12)

| 改动 | 说明 | 状态 |
|------|------|------|
| 两层授权模型 | `functions {}` 声明能力；`tools = [...]` 是 LLM 可见的唯一白名单 | ✅ |
| 不写 tools = 无工具 | Agent 不声明 `tools` 时，LLM 没有任何工具（仅 `load_skill`） | ✅ |
| tools 统一命名空间 | `tools` 列表同时支持 Helen 函数（来自 `functions {}`）和 Python 工具（来自 `runtime/tools.py`）| ✅ |
| tools = CONST_NAME | tools 可引用模块级 const（静态可审计，安全边界清晰）| ✅ |
| 禁止重复 tools 声明 | 重复 tools 编译期报错（之前静默只取第一个）| ✅ |
| 解析器接受 `=` | Agent 属性现在支持 `description = "..."` / `tools = [...]` 语法 | ✅ |
| AgentError 异常 | agent 调用失败抛出 `AgentError`（携带 agent_name/args/cause）| ✅ |
| AgentError 继承 LLMError | `catch LLMError` 一并捕获 agent 失败 | ✅ |
| 嵌套 AgentError 透传 | 嵌套 agent 失败不双层包装，保留最内层完整上下文 | ✅ |

### 两层授权（Breaking Change）

**之前**：`functions {}` 里的函数自动暴露给 LLM，不写 `tools` 时默认注入 `web_search`/`read_file` 等 6 个内建工具。

**现在**：
- `functions {}` 块声明 agent 的**全部能力**——`main {}` 的 Helen 代码可以调用其中任意函数，但 LLM 看不到它们，除非在 `tools = [...]` 里显式列出。
- `tools = [...]` 是 **LLM 可见性的唯一白名单**。名字先在 `functions {}` 里查，找不到再查 Python 工具注册表。
- 不写 `tools` 时，LLM 没有任何工具可用（除始终包含的 `load_skill`）。
- 解析器现在接受 `description = "..."`、`tools = [...]` 等带 `=` 的写法（之前只支持无 `=` 形式）。

```helen
agent Assistant {
    description "Helpful assistant"
    tools = ["web_search", "summarize"]     // LLM 可以调用这两个
    functions {
        fn summarize(text: str): str { ... }   // LLM 可见（在 tools 里）
        fn internal_helper(): str { ... }      // LLM 不可见（不在 tools 里）
    }
    main {
        internal_helper()                       // ✅ main 可以调
        return llm act "..."                    // LLM 只能调 web_search/summarize
    }
}
```

**迁移指南**：老代码里 `functions {}` 块中希望 LLM 调用的函数，需要显式加到 `tools = [...]` 里。

### tools = CONST_NAME

`tools` 可引用模块级 const，工具集**静态可审计**（安全边界清晰）：

```helen
// 项目顶部定义一次
const FILE_TOOLS = ["read_file", "write_file", "path_exists"]
const RESEARCH_TOOLS = ["web_search", "web_fetch", "read_file"]

agent Contractor {
    tools = FILE_TOOLS                  // ✅ 复用
    ...
}

agent Researcher {
    tools = RESEARCH_TOOLS              // ✅ 复用
    ...
}
```

**严格校验**（编译期）：
- ✅ `tools = CONST_NAME` — 模块级 const
- ✅ `tools = ["...", ...]` — 字面量列表
- ❌ `tools = my_var` — 可变变量
- ❌ `tools = my_fn` — 函数
- ❌ `tools = OtherAgent` — agent
- ❌ `tools = UNKNOWN` — 未定义标识符
- ❌ 两次 `tools = ...` — 重复声明

### AgentError

Agent 调用失败抛出 `AgentError`，携带结构化上下文：

```helen
try {
    let result = Contractor(req, dir)
} catch AgentError err {
    // err.message    — "Agent 'Contractor' failed: ..."
    // err.agent_name — "Contractor"
    // err.agent_args — {req: "...", dir: "..."}
    // err.cause      — 底层异常
    error("契约设计失败: " + err.message)
} catch LLMError err {
    // 也可用 catch LLMError 一并捕获（AgentError 继承 LLMError）
}
```

嵌套 agent 调用时，内层 AgentError 透传不双层包装，保留最内层完整上下文。

---

## v1.10: CLI 参数支持

| 改进 | 说明 | 状态 |
|------|------|------|
| `argv` 预定义常量 | `const list<str>`，包含命令行参数 | ✅ |
| `get_cli_args()` | 标准库函数，返回与 argv 相同的列表 | ✅ |
| `parse_cli_args()` | 结构化解析 CLI 参数（自动模式 + spec 模式） | ✅ |
| CLI 参数传递 | `helen <file> [args...]` 传递参数给程序 | ✅ |
| Agent 作用域传播 | `argv` 作为 const 自动在 agent 隔离环境中可见 | ✅ |
| shared let 跨模块访问 | 导入模块的函数可访问其自身模块的 const 和 shared let | ✅ |
| 模块级 Environment | 每个导入模块拥有独立作用域链 | ✅ |
| shared let 初始化引用 const | shared let 可以在初始化时引用同模块的 const 常量 | ✅ |

### shared let 初始化引用 const 修复 (Issue #10)

**问题**：在模块中定义 `const` 常量后，`shared let` 初始化时引用该常量会报错 `Undefined variable`。

```helen
const OUTPUT_NORMAL = 1
shared let _output_level = OUTPUT_NORMAL  // ❌ 编译期错误
```

**根因**：`_register_imported_shared_vars()` 方法在创建 `module_env` 之前就被调用，导致在求值 `shared let` 初始化表达式时，`const` 常量还没有被定义到任何环境中。

**修复**：
- 调整调用顺序：将 `_register_imported_shared_vars()` 的调用移到创建 `module_env` 之后
- 修改 `_register_imported_consts_and_shared()` 方法接受 `module_env` 参数，在求值初始化表达式时使用 `module_env` 作为上下文环境
- 对于别名导入，也确保在创建 `module_env` 之后再注册 shared let

**示例**：
```helen
// output.helen
const OUTPUT_NORMAL = 1
const OUTPUT_VERBOSE = 2
shared let _output_level = OUTPUT_NORMAL  // ✅ 现在可以正常工作

fn get_level(): int { return _output_level }

// main.helen
import "output.helen" as output
main {
    print(output.get_level())  // 输出: 1
}
```

**质量**: 4 个新测试用例，2250+ 测试通过，0 regression

### shared let 跨模块访问修复

**问题**：导入模块（尤其是别名导入 `import "x.helen" as m`）的函数无法访问其模块自身定义的 `const` 和 `shared let`，导致 `Undefined variable` 运行时错误。

**根因**：
1. `import_resolver._register_helen()` 的过滤条件 `not stmt.mutable` 排除了 `shared let`（mutable=True）
2. 别名导入路径未注册 shared let 到当前环境
3. `visit_access` 对 `__data__` 中存储的 AST 节点未求值
4. 模块函数调用使用调用方环境作为父作用域，无法看到模块级变量

**修复**：
- `import_resolver.py`：过滤条件改为 `not stmt.mutable or stmt.shared`
- `interpreter.py`：为每个导入模块创建独立的模块级 `Environment`，在调用模块函数时作为父作用域传入
- `analyzer.py`：语义分析阶段也注册 `shared let` 到符号表

**示例**：

```helen
// output.helen
const LEVEL = 1
shared let _use_colors = true
fn colorize(t: str): str {
    if _use_colors { return "[C]" + t }
    return t
}

// main.helen
import "output.helen" as output
main {
    output.colorize("hi")   // ✅ 现在正常工作
}
```

**用法**：

```bash
$ helen my_tool.helen --verbose --output=json --port=8080 input.txt
```

```helen
// 1. 直接访问 argv
print(argv)  // ["--verbose", "--output=json", "--port=8080", "input.txt"]

// 2. 自动解析
let parsed = parse_cli_args()
// {verbose: true, output: "json", port: "8080", _positional: ["input.txt"]}

// 3. 结构化解析（带类型和默认值）
let spec = {
    "verbose": {"type": "flag", "default": false},
    "output": {"type": "string", "default": "text"},
    "port": {"type": "int", "default": 3000}
}
let config = parse_cli_args(spec)
// {verbose: true, output: "json", port: 8080, _positional: ["input.txt"]}
```

**实现细节**：
- CLI 层 (`cli/__main__.py`)：`main()` 将 `argv[1:]` 传递给 `run_command()` → `Interpreter(program_args=...)`
- 解释器层：`argv` 作为 `const` 注入全局 Environment，自动传播到 agent 隔离作用域
- 语义分析层：`argv` 注册为 `kind="const"` 符号，重赋值在分析阶段报错
- 标准库层：`get_cli_args()` / `parse_cli_args()` 通过模块级 `_cli_args` 存储访问参数

**新增 stdlib 函数**：2 个（`get_cli_args`, `parse_cli_args`），总计 **195** 个内置函数

**质量**: 71 个新测试（41 execution + 30 stdlib），2211+ 测试通过，0 regression

---

## v1.10: Agent 作用域隔离

| 改进 | 说明 | 状态 |
|------|------|------|
| `shared` 关键字 | 跨 agent 可见变量 (`shared` / `共享`) | ✅ |
| Agent 作用域隔离 | `agent main {}` 在隔离环境中运行 | ✅ |
| 子脚本/字段赋值 | `arr[i] = x` 和 `obj.field = x` | ✅ |
| 短路求值 | `&&` 和 `\|\|` 短路求值 | ✅ |
| 返回类型语法 | 仅支持 `:` 语法，移除 `->` | ✅ |
| 异常包装 | RuntimeError 包装 stdlib Python 异常 | ✅ |
| 异步 HTTP | `act_async()` / `act_stream_async()` | ✅ |
| 导入跟踪 | 导入的 `shared let` 被正确跟踪 | ✅ |
| List 拼接 | `list + list` 支持（`_add()` 新增 list 分支） | ✅ |
| Agent 函数返回值 | `functions {}` 中 return 正确解包给 LLM | ✅ |
| 工具输出 Unicode | 工具返回 JSON 正确显示中文（`ensure_ascii=False`） | ✅ |

**Agent 作用域隔离规则**:
- 模块级 `let` 在 agent main 中**不可见**（编译时错误）
- 模块级 `const` 自动可见（只读共享）
- 使用 `shared let` 显式声明跨 agent 可见的可变变量
- Agent main 中的闭包可以捕获局部变量

**示例**:

```helen
shared let counter = 0
const CONFIG = { "debug": true }

agent Worker {
  main {
    // let moduleVar  // ❌ 编译错误
    CONFIG  // ✅ 只读访问
    counter += 1  // ✅ 可读写 shared let
  }
}

// 子脚本/字段赋值
let arr = [1, 2, 3]
arr[0] = 10  // ✅

let obj = { name: "Alice" }
obj.name = "Bob"  // ✅

// 短路求值
let x = false && expensiveCall()  // 不会执行
let y = true || expensiveCall()   // 不会执行

// 返回类型注解
fn add(a: int, b: int): int {  // ✅ 仅支持此语法
  return a + b
}

// 异步 HTTP
agent AsyncAgent {
  main {
    await llm act_async "task"
  }
}

// List 拼接（v1.10 修复）
let items = []
items = items + ["a", "b"]        // ✅ 之前报 "Cannot add list and list"
let merged = [1, 2] + [3, 4]      // ✅ [1, 2, 3, 4]
```

**Bug 修复**:
- **List 拼接**：`_add()` 新增 `list + list` 分支，之前 `arr = arr + [item]` 会报 `RuntimeError: Cannot add list and list`
- **Agent 函数返回值**：`_execute_agent_function()` 现在会解包 `ReturnSentinel`，LLM 工具调用结果不再显示 `ReturnSentinel(...)` 字符串
- **工具 Unicode 输出**：27 处 `json.dumps()` 全部加上 `ensure_ascii=False`，工具返回的中文不再显示为 `\uXXXX` 转义

**质量**: 1500+ 测试通过

---

## v1.10: 上下文窗口保护 (HLD 3.12)

| 改动 | 说明 | 状态 |
|------|------|------|
| Model-aware MAX_TOKENS | 40+ 模型的 context window 表（Qwen/GPT/Claude/Gemini），自动选择正确上限 | ✅ |
| 字符类型感知 token 估算 | CJK（1.2 字符/token）vs 拉丁（4 字符/token），误差从 ~40% 降至 ~15% | ✅ |
| History 自动传入 LLM | `llm act` / `llm stream` 现在将裁剪后的对话历史传给 API | ✅ |
| 工具结果上限强制 | `MAX_TOOL_RESULTS_PER_TURN = 10`（之前声明未用，现已强制执行） | ✅ |
| 上下文超限自动恢复 | API 返回 context-too-large 错误时自动删除最老消息并重试 | ✅ |
| History 自动压缩 | 超过 context window 80% 时，旧消息压缩成摘要，防 REPL 长会话内存泄漏 | ✅ |

### 为什么需要上下文窗口保护

之前 `llm act` 和 `llm stream` 的实现存在三个问题：

1. **History 没传给 LLM**：`_history` 列表只在内存中累积，从未作为 `history=` 参数传给 `llm_runtime.act()`。LLM 每次调用都是"失忆"的。
2. **死代码**：`HistoryManager.check_budget()` 和 `trim_history()` 定义了但从没被调用。`MAX_TOOL_RESULTS_PER_TURN` 常量声明了但没使用。
3. **撑爆 context window 无保护**：当工具循环累积太多结果时，API 返回 context-too-large 错误后直接抛异常，没有自动恢复。

### 现在的实现

#### Model-aware context window

`HistoryManager` 初始化时根据模型名查找对应的 context window 大小：

```python
from helen.runtime.history import get_model_context_window

get_model_context_window("qwen3.7-plus")       # 131072
get_model_context_window("gpt-4o-mini")         # 128000
get_model_context_window("claude-opus-4")       # 200000
get_model_context_window("gpt-4o-mini-2024-07-18")  # 128000（前缀匹配）
get_model_context_window("unknown-model")       # 128000（默认值）
```

支持精确匹配 + 前缀匹配（带日期后缀的模型名也能正确识别）。

#### 字符类型感知 token 估算

之前的 `len(text) // 4` 对中文误差极大（中文 1 个字符 ≈ 1-2 tokens，不是 0.25）。新实现区分 CJK 和拉丁字符：

```python
estimate_tokens("hello world")  # ~3 tokens（11 chars / 4）
estimate_tokens("你好世界")       # ~4 tokens（4 CJK chars / 1.2）
```

误差从 ~40% 降至 ~15%（对比真实 tokenizer）。

#### History 自动裁剪并传入 LLM

`visit_llm_act_expr` 和 `visit_llm_stream_stmt` 现在：

1. 调用 `_prepare_history_for_llm(system_prompt, prompt)`
2. 该方法内部：`check_budget()` 计算可用空间 → `trim_history()` 裁剪到预算内 → 转换为 API 格式
3. 把结果作为 `history=` 参数传给 `act()` / `act_stream()`

```helen
// 多轮对话现在 LLM 能看到之前的上下文
agent Chat {
    main {
        llm act "记住：我的名字是 Alice"   // 写入 history
        llm act "我叫什么名字？"           // LLM 能看到上一轮，回答 "Alice"
    }
}
```

#### 工具结果上限强制

`MAX_TOOL_RESULTS_PER_TURN = 10` 在 `act()` 和 `act_stream()` 的工具执行前强制执行。当 LLM 一次请求超过 10 个工具调用时，只保留前 10 个。

#### 上下文超限自动恢复

当 API 返回 context-too-large 错误时：

1. 检测到 10+ 种错误标记（OpenAI/Anthropic/DashScope 各家格式）
2. 自动删除最老的 2 条非系统消息
3. 重试一次

`act_stream()` 的 HTTPStatusError 处理器也支持同样的恢复逻辑。

#### History 自动压缩（防 REPL 长会话内存泄漏）

`_add_to_history()` 每次添加消息后调用 `enforce_limit()`。当历史总 token 超过 context window 的 80% 时：

1. 保留最近的几条消息（占 75% 预算）
2. 更早的消息压缩成一条 `[Previous conversation summary]` 系统消息（占 25% 预算）
3. 返回新的 `[summary_msg, ...recent_msgs]`

这样即使在 REPL 会话中做几百轮 `llm act`，内存也不会无限增长。

### 迁移指南

这些改动对现有代码**向后兼容**。如果之前发现 `llm act` 在多轮调用中"失忆"，现在会自动修复。如果想手动控制：

```helen
// 显式重置历史（REPL 中 :reset 也会清）
// Python API: interpreter.clear_history()
```

**质量**: 2272 测试通过（新增 48 个上下文保护测试）

---

## v1.9: 中文语法支持

| 改进 | 说明 | 状态 |
|------|------|------|
| 中文关键字 | 44 个中文关键字映射到相同 TokenType | ✅ |
| 中文标识符 | CJK 统一表意文字支持（变量名、函数名） | ✅ |
| 中英混合 | 中英文关键字可自由混用 | ✅ |
| 零侵入 | 解析器、解释器、AST 零改动 | ✅ |

**设计**：中文关键字在词法层直接映射到英文 TokenType（如 `让` → `LET`），下游完全无感知。仅修改 `tokens.py`（+44 行映射）和 `lexer.py`（+30 行 CJK 字符集）。

**示例**：

```helen
// 纯中文
函数 斐波那契(n: int): int {
    如果 n <= 1 {
        返回 n
    } 否则 {
        返回 斐波那契(n - 1) + 斐波那契(n - 2)
    }
}

// 中英混合
设 结果 = 斐波那契(10)
const LIMIT = 100
如果 结果 < LIMIT {
    print("OK")
}
```

**质量**: 30 个新测试，1480+ 核心测试通过，0 regression

---

## v1.8: 函数式编程增强 (当前)

| 改进 | 说明 | 状态 |
|------|------|------|
| 管道操作符 `\|>` | `value \|> fn` 等价于 `fn(value)` | ✅ |
| 通配符模式 | `case _ { }` 匹配任何值 | ✅ |
| 变量绑定模式 | `case x { }` 绑定值到变量 | ✅ |
| 类型模式 | `case is Type { }` 检查类型 | ✅ |
| 类型模式带绑定 | `case is Type name { }` | ✅ |

**新增语法**：

```helen
// 管道操作符
let result = "hello" |> upper |> strip
let doubled = 5 |> double

// 通配符模式
match value {
    case 1 { print("one") }
    case _ { print("other") }  // 匹配任何值
}

// 变量绑定
match value {
    case n if n > 0 { print("positive: " + str(n)) }
    case n if n < 0 { print("negative: " + str(n)) }
    case _ { print("zero") }
}

// 类型模式
match value {
    case is String { print("it's a string") }
    case is Int { print("it's an int") }
    case _ { print("unknown type") }
}

// 类型模式带绑定
match value {
    case is String s { print("string: " + s) }
    case _ { print("not a string") }
}
```

**质量**: 19 个新测试，307+ 核心测试通过

---

## v1.7: 闭包与协议

| 改进 | 说明 | 状态 |
|------|------|------|
| 闭包/匿名函数 | `fn(x, y) { return x + y }` | ✅ |
| 词法作用域 | 闭包捕获定义时环境 | ✅ |
| 协议声明 | `protocol Name { fn method() }` | ✅ |
| 协议实现 | `impl Name for Type { }` | ✅ |

**新增语法**：

```helen
// 匿名函数
let add = fn(x, y) { return x + y }
print(add(1, 2))  // 3

// 闭包
fn make_counter() {
    let count = 0
    return fn() {
        count = count + 1
        return count
    }
}

let counter = make_counter()
print(counter())  // 1
print(counter())  // 2

// 协议声明
protocol Printable {
    fn to_string(self) -> String
}

// 协议实现（鸭子类型）
struct Point {
    x: Int
    y: Int
}

impl Printable for Point {
    fn to_string(self) -> String {
        return "Point(" + str(self.x) + ", " + str(self.y) + ")"
    }
}
```

**质量**: 22 个新测试，148 passed, 4 xfailed

---

## v1.6: 短期改进

| 改进 | 说明 | 状态 |
|------|------|------|
| 模块导入函数访问 | `import "module.helen" as mod` 后可访问 `mod.fn()` | ✅ |
| 错误信息增强 | 更清晰的错误提示和建议 | ✅ |

**质量**: 测试全部通过

---

## v1.5: 语言增强

| 改进 | 说明 | 状态 |
|------|------|------|
| 移除 `skills` 保留字 | `skills` 不再是关键字，可用作变量名 | ✅ |
| Agent functions 块变量 | `functions {}` 支持 `let`/`const` 声明 | ✅ |
| List 方法 | 自动支持 Python list 所有方法 | ✅ |
| Match 范围匹配 | `case 1..10 { }` 语法 | ✅ |
| Match 守卫条件 | `case x if x > 5 { }` 语法 | ✅ |

**新增语法**：

```helen
// skills 可用作变量名
let skills = ["coding", "testing"]
print(skills)

// Agent functions 块中的变量
agent MyAgent {
    functions {
        let config = "default"
        const MAX_RETRIES = 3
        
        fn get_config() -> str {
            return config
        }
    }
}

// List 方法
let items = [1, 2, 3]
items.append(4)
items.sort()
items.reverse()

// Match 范围匹配
let score = 85
match score {
    case 90..100 { print("A") }
    case 80..89 { print("B") }
    default { print("F") }
}

// Match 守卫条件
match x {
    case 1..100 if x == 42 { print("the answer") }
    case 1..100 { print("in range") }
    default { print("out of range") }
}
```

**质量**: 25 个新测试，309 个核心测试通过

---

## Phase 10: AI 原生可观测性

| 模块 | 交付 | 状态 |
|---|---|---|
| Observability | `helen/runtime/observability.py` | ✅ |
| assert 语句 | Token + AST + Parser + Interpreter | ✅ |
| debug() 内置函数 | `helen/stdlib/__init__.py` | ✅ |
| REPL 调试命令 | `:trace`, `:last_error`, `:llm_log` | ✅ |
| LLM 审计日志 | `helen/interpreter/llm_mixin.py` | ✅ |

**新增**:
- `helen.runtime.observability` — AI 原生可观测性模块（CallStackTracker、ExecutionTracer、ErrorSnapshot、LLMAuditLog、ObservabilityManager）
- `assert` 语句 — 运行时假设验证，失败自动捕获结构化错误上下文
- `debug(message, data?)` — 结构化调试输出到 stderr（JSON 格式）
- `trace_on()` / `trace_off()` / `get_trace(n)` — 程序化执行追踪控制
- REPL `:trace on|off|show` — 执行追踪 REPL 命令
- REPL `:last_error` — 显示上次错误的结构化上下文（人类可读格式）
- REPL `:llm_log [n]` — 显示 LLM 调用审计日志
- LLM 审计 — `llm act` 和 `llm stream` 自动记录调用详情（prompt/response/tokens/耗时/tool_calls）
- `AssertionError` — 新增预定义异常类型

**设计理念**: 放弃传统交互式 Debugger（断点/单步），转向 AI 原生可观测性。AI 不需要暂停/恢复，而是需要结构化的、可机器消费的上下文（JSON 错误快照、调用栈、追踪日志、LLM 审计）。REPL 中 `:last_error` 显示人类可读格式，编程访问可通过 `snapshot.to_json()` 获取 JSON 格式。

**质量**: 273+ tests passing, 新增 24 个 observability 测试

---

## Phase 9: 质量提升与架构优化

| 模块 | 交付 | 状态 |
|---|---|---|
| LLM Mixin 拆分 | `helen/interpreter/llm_mixin.py` | ✅ |
| CI/CD | `.github/workflows/ci.yml` | ✅ |
| 技能系统独立化 | `~/.helen/skills/` (145 skills) | ✅ |

**新增**:
- `helen.interpreter.llm_mixin` — LlmMixin 类，从 Interpreter 拆分 LLM 相关方法（visit_llm_act/if/stream、工具构建、历史管理、模板渲染）
- `.github/workflows/ci.yml` — GitHub Actions CI/CD（pytest + flake8 + coverage）
- `~/.helen/skills/` — 9 个 Helen 原生技能 + 136 个 Hermes fallback = 145 个技能
- `ATTRIBUTION.md` + `LICENSE-THIRD-PARTY.md` — MIT 协议归属声明

**代码质量**:
- flake8 警告从 571 → **0**
- 清理死代码：`visit_binary_op` 不可达分支、空 `_check_llm_usage`/`_check_async_usage` 方法
- 修复静默异常：15+ 处 `except Exception` 添加 `logging.debug()`
- 修复 F821：移除 `parser.py` 中 `AsyncCallExprNode` 未定义名称
- 消除代码重复：统一 `_type_from_typenode()`、`Message` 类
- 新增 344 个测试用例（interpreter/runtime 覆盖率提升）

**质量**: 1,805 tests, flake8 0 warnings, 综合评分 7.93/10

---

## Phase 8: 独立运行时

| 模块 | 交付 | 状态 |
|---|---|---|
| Config 系统 | `helen/runtime/config.py` | ✅ |
| 内置工具 | `helen/runtime/tools.py` (7 工具) | ✅ |
| 模糊匹配 | `helen/runtime/fuzzy_match.py` (9 策略) | ✅ |
| Function Calling | 多轮工具调用 + nudge | ✅ |
| `helen init` | 配置初始化 CLI 命令 | ✅ |

**新增**:
- `helen init` — 初始化 `~/.helen/` 配置目录
- `helen.runtime.config` — 独立配置管理（YAML + .env，4 级优先级）
- `helen.runtime.tools` — 7 个内置工具（web_search/web_fetch/read_file/write_file/patch_file/shell_exec/calculate）
- `helen.runtime.fuzzy_match` — 从 Hermes 集成的模糊匹配引擎（9 策略，860 行）
- Function Calling 多轮循环 + nudge 机制
- Agent `prompt` 字段作为 `system_prompt` 注入 LLM 调用
- 脚本模式直接使用 `HttpLLMRuntime`（不再 Mock）

**独立化**:
- `~/.helen/config.yaml` — Helen 独立 LLM 配置
- `~/.helen/skills/` — Helen 原生 skill 目录
- `fuzzy_match.py` — 模糊匹配引擎内置，无需 Hermes
- 向后兼容 `~/.hermes/.env` 和 `~/.hermes/skills/`

**质量**: 904 tests, 全部通过

---

## Phase 7: 工具链完善

| 模块 | 交付 | 状态 |
|---|---|---|
| M12 LSP Server | 诊断/补全/跳转 | ✅ |
| M13 VS Code Extension | TextMate 语法高亮 | ✅ |
| M15 Standard Library | 24 builtins | ✅ |

**新增**:
- `HelenHermesRuntime` — 完整 Runtime ABC 实现
- `cancel_llm_call` — LLM 调用取消机制
- `_get_context()` — 对话历史集成 HistoryManager
- `helen doc` — 文档生成子命令
- VS Code 扩展：语法高亮、括号配对、自动闭合

**质量**: 811 tests, 86.29% coverage, flake8 0 errors

---

## Phase 6: CLI 与 REPL

| 模块 | 交付 |
|---|---|
| M11 CLI | `helen run/check/repl` |
| M10 Error Formatter | HLD 3.11.2 格式输出 |

---

## Phase 5: 运行时基础设施

| 模块 | 交付 |
|---|---|
| M7 Runtime ABC | 12 抽象方法 |
| M6 PromptBuilder | 两层渐进式披露 |
| M16 HistoryManager | Token 预算/截断/摘要 |
| M17 StructuredOutput | LLM 路由 function calling |

---

## Phase 4: 解释执行与 LLM 集成

| 模块 | 交付 |
|---|---|
| M5 Interpreter | AST 遍历执行 |
| M8 ImportResolver | 多格式/路径安全/循环检测 |
| M14 Test Framework | pytest 集成 |

**关键实现**:
- `Environment` 作用域链
- `_call_agent()` 隔离 Environment
- `async call` + `await [list]` Promise.all
- `AggregateError` 并发错误聚合
- Agent 参数接口声明

---

## Phase 3: 语义分析

| 模块 | 交付 |
|---|---|
| M4 SemanticAnalyzer | 符号表/作用域/类型检查 |
| M9 Type System | 14 种类型 |

**关键实现**:
- 6 种作用域 (global/agent/fn/block/catch/loop)
- 46 Visitor 方法全部实现
- Agent 边界检查
- const 赋值保护

---

## Phase 2: AST 与错误处理

| 模块 | 交付 |
|---|---|
| M3 AST Nodes | 49 节点类 |
| M10 Errors | 42 ErrorCode |

**关键实现**:
- Visitor 模式 (46 抽象方法)
- SourceSpan 全链路
- `@dataclass(frozen=True)` 不可变节点

---

## Phase 1: 语法分析

| 模块 | 交付 |
|---|---|
| M2 Parser | Pratt Parsing × 10 级 |

**关键实现**:
- EBNF 392 行完整语法
- Panic mode 错误恢复
- `llm` 上下文关键字消歧
- `async` 前缀处理
- Agent 参数解析

---

## Phase 0: 词法分析

| 模块 | 交付 |
|---|---|
| M1 Lexer | 手写扫描器 |

**关键实现**:
- 42 关键字 (39 + true/false/null)
- 77 Token 类型
- Maximal Munch
- 三引号字符串
- 连字符关键字消歧 (`sub-agents`/`max-turns`)
- SourceSpan

---

## 质量指标演进

| Phase | 测试数 | 覆盖率 | flake8 |
|---|---|---|---|
| Phase 0-1 | 276 | 91.23% | 0 |
| Phase 0-2 | 535 | 89% | 0 |
| Phase 0-4 | 554 | 88% | 0 |
| Phase 0-5 | 604 | 88% | 0 |
| Phase 0-6 | 638 | 88% | 0 |
| Phase 0-7 (CLI) | 670 | 87% | 0 |
| Phase 0-7 (全部) | 811 | 86.29% | 0 |
| **Phase 0-8 (独立运行时)** | **904** | **—** | **0** |
| Phase 0-8 (stdlib 扩展) | 1,030 | — | 0 |
| Phase 0-9 (质量提升) | 1,461 | — | 0 |
| **Phase 0-9 (最终)** | **1,805** | **—** | **0** |
