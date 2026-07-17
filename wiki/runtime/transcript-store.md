# TranscriptStore SSOT

> **v1.16 新特性** — 消息唯一真实来源（Single Source of Truth）

TranscriptStore 是 Helen v1.16 引入的核心运行时组件，它将所有对话消息持久化存储，提供完整的审计追踪和会话恢复能力。

---

## 📋 目录

- [设计目标](#设计目标)
- [架构概览](#架构概览)
- [核心组件](#核心组件)
- [使用指南](#使用指南)
- [配置详解](#配置详解)
- [性能优化](#性能优化)
- [最佳实践](#最佳实践)

---

## 设计目标

### 为什么需要 TranscriptStore？

在 v1.16 之前，Helen 的对话历史管理存在以下问题：

1. **双写分叉**：`_history` 和 `TranscriptStore` 双写，语义不一致
2. **破坏性压缩**：压缩就地替换，丢失完整对话历史
3. **无持久化**：所有消息常驻内存，长会话内存压力大
4. **调试困难**：无法回溯"LLM 看到了什么 vs 原始对话是什么"

### TranscriptStore 的解决方案

| 问题 | 解决方案 |
|------|---------|
| 双写分叉 | **单一写入点**：所有消息只写入 TranscriptStore |
| 破坏性压缩 | **非破坏性**：压缩只追加 BoundaryMarker，不修改消息 |
| 无持久化 | **持久化优先**：JSONL/SQLite 后端，内存只保留活跃窗口 |
| 调试困难 | **完整审计**：可回溯任意历史视图 |

---

## 架构概览

### 四层架构

```
┌─────────────────────────────────────────┐
│  Layer 4: 用户接口                       │
│  • REPL 命令 (:transcript, :sessions)   │
│  • Stdlib 函数 (get_session_id, etc.)   │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  Layer 3: 视图层                         │
│  • read_view() 重建压缩后视图            │
│  • View Cache (dirty flag + 缓存)       │
│  • UUID 索引 (O(1) 查找)                │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  Layer 2: 存储层                         │
│  • TranscriptStore (内存)               │
│  • LRU Cache (max_memory_items)         │
│  • BoundaryMarker (压缩记录)            │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  Layer 1: 持久化层                       │
│  • JSONLBackend (append-only)           │
│  • SQLiteBackend (WAL mode, indexed)    │
└─────────────────────────────────────────┘
```

### 数据流

```
User Input
    ↓
_add_to_history()
    ↓
TranscriptStore.append()  ← SSOT (唯一写入点)
    ↓
Backend.append()  ← 持久化
    ↓
LRU Eviction (if needed)  ← 内存优化

LLM Call
    ↓
_prepare_history_for_llm()
    ↓
TranscriptStore.read_view()  ← 应用 BoundaryMarker
    ↓
View Cache (O(1) if no changes)
    ↓
LLM API Call
```

---

## 核心组件

### 1. TranscriptStore

**位置**: `helen/runtime/transcript_store.py`

TranscriptStore 是消息的唯一真实来源（SSOT），负责：

- **消息存储**: append-only 列表，永不修改/删除
- **UUID 索引**: O(1) 查找 via `get(uuid)`
- **视图重建**: `read_view()` 应用 BoundaryMarker
- **压缩记录**: `record_compression()` 追加 BoundaryMarker
- **LRU 缓存**: 自动驱逐旧消息到后端

**关键属性**:

```python
class TranscriptStore:
    transcript: list[Message | BoundaryMarker]  # append-only
    _uuid_index: dict[str, int]                 # UUID → index
    _backend: TranscriptStoreBackend            # 持久化后端
    _max_memory_items: int                      # LRU 缓存大小
    _offloaded_count: int                       # 已驱逐到后端的数量
    _dirty: bool                                # 视图缓存失效标志
    _cached_view: list[Message] | None          # 缓存的视图
```

**核心方法**:

| 方法 | 说明 | 时间复杂度 |
|------|------|-----------|
| `append(msg)` | 追加消息，分配 UUID | O(1) |
| `get(uuid)` | UUID 查找 | O(1) |
| `read_view()` | 重建压缩后视图 | O(n) 首次, O(1) 缓存 |
| `record_compression(...)` | 记录压缩事件 | O(1) |
| `get_compression_audit()` | 获取压缩审计 | O(b), b=边界数 |

### 2. BoundaryMarker

**位置**: `helen/runtime/transcript_store.py`

BoundaryMarker 记录压缩事件，不修改原始消息：

```python
@dataclass
class BoundaryMarker:
    uuid: str                          # 边界标记 UUID
    anchor_uuid: str                   # 锚点消息 UUID（压缩后第一条）
    head_uuid: str                     # 压缩范围起始 UUID
    tail_uuid: str                     # 压缩范围结束 UUID
    summary: str                       # 压缩摘要
    layer: str                         # 压缩层名称
    timestamp: float                   # 压缩时间戳
    original_token_count: int          # 压缩前 token 数
    compressed_token_count: int        # 压缩后 token 数
```

**工作原理**:

```
原始消息: [msg1] [msg2] [msg3] [msg4] [msg5]
                ↓ 压缩 msg1-msg3
Transcript: [msg1] [msg2] [msg3] [msg4] [msg5] [BoundaryMarker]
                                                  ↓
read_view(): [summary] [msg4] [msg5]
```

### 3. Backend（持久化后端）

#### JSONLBackend

**特点**:
- ✅ 简单、人类可读（每行一个 JSON）
- ✅ 崩溃安全（append-only）
- ✅ 易于 tail/grep 调试
- ⚠️ 无索引，大量消息时查询较慢

**格式**:
```json
{"type": "message", "role": "user", "content": "Hello", "uuid": "abc123", ...}
{"type": "boundary_marker", "uuid": "marker1", "layer": "auto_compact", ...}
```

#### SQLiteBackend

**特点**:
- ✅ WAL 模式，高性能写入（<1ms/消息）
- ✅ UUID 索引，O(1) 查找
- ✅ 事务安全，支持并发读
- ⚠️ 二进制格式，不易直接查看

**Schema**:
```sql
CREATE TABLE transcript (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL,  -- 'message' or 'boundary_marker'
    data TEXT NOT NULL,  -- JSON
    timestamp REAL NOT NULL
);
CREATE INDEX idx_uuid ON transcript(uuid);
CREATE INDEX idx_timestamp ON transcript(timestamp);
```

### 4. SessionManager

**位置**: `helen/runtime/session_manager.py`

SessionManager 管理会话生命周期：

```python
class SessionManager:
    def create_session(self) -> str:
        """创建新会话，返回 session_id"""
        
    def get_session_path(self, session_id: str) -> Path:
        """获取会话 transcript 文件路径"""
        
    def list_sessions(self) -> list[dict]:
        """列出所有会话（按修改时间排序）"""
        
    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        
    def cleanup_old_sessions(self, keep_count: int = 100) -> int:
        """清理旧会话，保留最近 N 个"""
```

**会话目录结构**:
```
~/.helen/sessions/
├── session_1783492628_d9d9c0aa/
│   └── transcript.jsonl  (或 transcript.db)
├── session_1783492600_abc12345/
│   └── transcript.jsonl
└── ...
```

### 4.5 会话作用域 (Session Scope, v1.20)

v1.20 之前，所有 transcripts 都放在 `~/.helen/sessions/`（全局）。v1.20 引入**作用域**概念：transcripts 可以按应用隔离在各自的项目目录中。

#### 作用域模式

| 模式 | 路径 | 适用场景 |
|------|------|----------|
| `global` | `~/.helen/sessions/` | REPL 探索、跨项目共享、短脚本 |
| `project` | `<project>/.helen/sessions/` | 长期应用、生产部署、容器化 |
| `auto` (默认) | 检测项目目录，有则 project，无则 global | 推荐默认 |

#### 项目检测

通过向上查找以下标记之一检测项目根目录：
- `.helen/`（目录）—— 但排除用户全局的 `~/.helen/`
- `helen.yaml` / `helen.yml` / `helen.toml`

#### 优先级

1. **`HELEN_SESSION_DIR` 环境变量**：绝对优先，强制指定路径
2. **`session_scope` 配置**：`auto` (默认) / `global` / `project`
3. **回退到 `~/.helen/sessions/`**

#### 配置

```yaml
# ~/.helen/config.yaml
transcript:
  enabled: true
  backend: "sqlite"
  session_scope: "auto"          # "auto" | "global" | "project"
  session_dir: "~/.helen/sessions"             # 仅 scope=global 时
  project_session_dir: ".helen/sessions"       # 仅 scope=project 时
  max_memory_items: 1000
```

#### 运行时查询与修改

```helen
// 查看当前会话目录
let info = get_session_dir()
print("路径: " + info["session_dir"])
print("作用域: " + info["scope"])
print("项目根: " + str(info["project_dir"]))

// 运行时切换（不修改 config.yaml，仅当前进程）
set_session_dir("./my_app_sessions")
```

#### 设计原则

**Transcripts 是应用数据，不是语言基础设施**。让 transcripts 跟随应用而非语言安装：
- 应用即目录，`rm -rf .helen/` 清理全部状态
- 复制/mv 应用目录时 transcripts 随之移动
- 容器化场景：`WORKDIR` 自带 transcripts，无需挂载 `~/.helen`
- 多应用机器：每个应用 transcripts 自然隔离

REPL 等交互场景显式 `session_scope: "global"` 保持跨项目历史延续。

### 4.6 会话删除 (Session Deletion, v1.21)

v1.21 新增三个 stdlib 函数，用于永久删除 TranscriptStore 会话数据。

#### 设计原则

Helen 采用**审计追踪优先**的删除策略：

| 操作类型 | 函数 | 是否删除持久化数据 |
|---------|------|:----------------:|
| 逻辑删除（消息级） | `delete_message(uuid)` | ❌ 保留 |
| 逻辑清空（会话级） | `clear_context()` | ❌ 保留（添加 BoundaryMarker） |
| 永久删除（会话级） | `delete_session(id)` | ✅ 删除 |
| 永久删除（当前会话） | `delete_current_session()` | ✅ 删除 |
| 批量清理 | `cleanup_sessions()` | ✅ 删除 |

逻辑删除保留持久化数据用于审计，永久删除才真正释放磁盘空间。

#### delete_session(session_id)

永久删除指定会话的所有数据：

```helen
let r = delete_session("session_1720435200_a1b2c3d4")
// {"status": "ok", "session_id": "...", "freed_bytes": 10240, "message": "..."}
```

**安全限制**：不能删除当前会话，需使用 `delete_current_session()`。

#### delete_current_session(confirm?)

永久删除当前会话，需要显式确认：

```helen
// 第一步：查看确认提示
let r = delete_current_session()
// {"status": "error", "message": "Set confirm=true to delete current session"}

// 第二步：确认删除
let r = delete_current_session(confirm=true)
// {"status": "ok", "session_id": "...", "freed_bytes": 8192}
```

删除后，解释器继续运行，但当前 TranscriptStore 被清空，后续消息会写入新会话。

#### cleanup_sessions(keep_count?, older_than_days?)

批量清理旧会话，支持两种策略：

```helen
// 策略 1：保留最近 N 个会话
let r = cleanup_sessions(keep_count=50)
// {"status": "ok", "deleted_count": 15, "freed_bytes": 1536000}

// 策略 2：删除 N 天前的会话
let r = cleanup_sessions(older_than_days=30)

// 策略 3：组合使用（同时满足两个条件才删除）
let r = cleanup_sessions(keep_count=50, older_than_days=30)
```

**安全限制**：当前会话永远不会被清理，即使它不在保留范围内。

#### 使用场景

| 场景 | 推荐函数 |
|------|---------|
| 长期运行 Agent 的定期清理 | `cleanup_sessions(keep_count=100)` |
| 隐私合规（GDPR 被遗忘权） | `delete_session(user_session_id)` |
| 测试环境清空 | `cleanup_sessions(keep_count=0)` |
| 重置当前会话 | `delete_current_session(confirm=true)` |

#### 中文别名

| 英文 | 中文 |
|------|------|
| `delete_session` | `删除会话` |
| `delete_current_session` | `删除当前会话` |
| `cleanup_sessions` | `清理会话` |

### 5. LRU Cache

**工作原理**:

```python
# 追加消息时检查
if len(self.transcript) > self._max_memory_items:
    self._evict_old_items()

def _evict_old_items(self):
    # 保留 80% 以避免频繁驱逐
    target_size = int(self._max_memory_items * 0.8)
    items_to_evict = len(self.transcript) - target_size
    
    # 驱逐最旧的消息（已在后端）
    evicted = self.transcript[:items_to_evict]
    self.transcript = self.transcript[items_to_evict:]
    self._offloaded_count += len(evicted)
    
    # 更新 UUID 索引
    self._uuid_index.clear()
    for i, item in enumerate(self.transcript):
        self._uuid_index[item.uuid] = i
```

**内存使用**:

| 场景 | 内存使用 | 说明 |
|------|---------|------|
| 100 消息 | ~1MB | 全部在内存 |
| 1K 消息 | ~10MB | 全部在内存 |
| 10K 消息 | ~10MB | LRU 缓存生效 |
| 100K 消息 | ~50MB | LRU 缓存生效 |

---

## 使用指南

### REPL 命令

#### :transcript

显示当前会话的有效视图（应用压缩后）：

```bash
> :transcript
Current transcript view (15 messages):
  [1] [user] Hello
  [2] [assistant] Hi there
  ...

Stats: 20 total items, 15 messages, 5 compression boundaries
```

**选项**:
- `:transcript --full` — 显示完整 transcript（包括压缩的消息）
- `:transcript --audit` — 显示压缩审计追踪

#### :sessions

列出所有会话：

```bash
> :sessions
Transcript sessions (5 total):
  [1] session_1783492628_d9d9c0aa
       Modified: 2026-07-08 15:30:00, Size: 2.5 KB, Messages: ~50
  [2] session_1783492600_abc12345
       Modified: 2026-07-08 14:00:00, Size: 1.2 KB, Messages: ~20
```

#### :session_id

显示当前会话 ID：

```bash
> :session_id
Current session: session_1783492628_d9d9c0aa
```

### Stdlib 函数

#### get_session_id()

```helen
let session = get_session_id()
print("Current session: {session}")
```

#### list_sessions()

```helen
let sessions = list_sessions()
for s in sessions {
    print("{s.session_id}: {s.size_bytes} bytes")
}
```

#### replay_transcript()

```helen
// 回放当前会话
let messages = replay_transcript()
for msg in messages {
    print("[{msg.role}] {msg.content}")
}

// 回放指定会话，包括压缩的消息
let full = replay_transcript("session_1783492628_d9d9c0aa", true)
```

#### export_transcript()

```helen
// 导出为 JSON
export_transcript("my_chat.json", "json")

// 导出为 Markdown
export_transcript("my_chat.md", "markdown")

// 导出为纯文本
export_transcript("my_chat.txt", "text")
```

#### search_transcript() (v1.22+)

按**内容**搜索持久化 transcript。与 `search_context()`（只搜当前 active context）不同，`search_transcript()` 能跨会话、跨 agent 搜索历史。

```helen
// 当前 session 内搜
let matches = search_transcript("认证 bug")

// 跨所有 session 搜（跨会话发现）
let matches = search_transcript("数据库 schema", scope="all")

// 正则匹配
let matches = search_transcript("fix.*bug", regex=true)

// 只搜 user 消息
let matches = search_transcript("TODO", role="user")

// 限定结果数
let matches = search_transcript("TODO", limit=20)

// 中文别名
let matches = 搜索会话("认证 bug")
```

**返回格式**：

```helen
// 每个匹配包含：
{
    session_id: "session_xxx",
    message_uuid: "uuid-...",
    role: "user",
    content: "完整消息内容",
    snippet: "...匹配位置周围的片段...",
    match_position: 42,
}
```

**参数说明**：

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `query` | str | (必填) | 搜索内容，substring 或 regex |
| `session_id` | str? | null | 指定 session（`scope="all"` 时忽略） |
| `scope` | str | `"current"` | `"current"` / `"all"` / `"global"` / `"project"` |
| `role` | str | `""` | 按角色过滤：`"user"` / `"assistant"` / `"tool"` / `""` (全部) |
| `regex` | bool | `false` | 是否按正则匹配 |
| `limit` | int | `50` | 最大返回数 |

**典型用法**：

```helen
// 场景 1：跨会话找某次讨论
let matches = search_transcript("数据库 schema", scope="all", limit=5)
for m in matches {
    print("Session {m.session_id}: {m.snippet}")
}

// 场景 2：找完后恢复完整上下文
if len(matches) > 0 {
    restore_context(matches[0].session_id)
}
```

#### Invocation Tree（调用树）(v1.22+)

每条消息带三个新字段，构成调用树：
- `agent_name`：产生该消息的 agent 名（顶层为 `None`）
- `invocation_id`：本次 `main {}` 执行的唯一 ID
- `parent_invocation_id`：父调用的 invocation_id

**查询函数**：

```helen
// 列出所有 invocation（可按 agent 过滤、分页）
let invs = list_invocations()
// [{invocation_id, agent_name, parent_invocation_id, message_count, ...}, ...]

let a_runs = list_invocations(agent="Researcher", limit=10)

// 查单个 invocation 元数据
let info = get_invocation("inv_1784272795_a61bcdaf")
// {agent_name: "A", message_count: 4, parent_invocation_id: "inv_top", ...}

// 获取完整调用树（嵌套结构）
let tree = get_invocation_tree()
// {
//   invocation_id: "inv_top", agent_name: null, children: [
//     {invocation_id: "inv_1", agent_name: "A", children: [...]},
//     {invocation_id: "inv_2", agent_name: "B", children: []},
//   ]
// }

// 调用路径字符串（调试用）
print(invocation_path("inv_3"))
// "top -> A -> C"

// 中文别名
列出调用()
获取调用("inv_xxx")
获取调用树()
调用路径("inv_xxx")
```

**扩展的 `replay_transcript` 过滤**：

```helen
// 只看 agent A 的消息
let a_msgs = replay_transcript(agent="A")

// 只看 A 的最后一次运行
let last_run = replay_transcript(agent="A", last_only=true)

// 看某个 invocation 及其子调用
let subtree = replay_transcript(invocation_id="inv_1", include_subtree=true)
```

**扩展的 `restore_context` 过滤**：

```helen
// 只恢复 agent A 的最近一次运行到 active context
restore_context("session_xxx", agent="A", last_only=true)

// 恢复某个 invocation 及其子树
restore_context("session_xxx", invocation_id="inv_1", include_subtree=true)
```

**隔离语义**：active context 按 `invocation_id` 过滤，每个 agent `main {}` 调用都是 fresh。详见 [[runtime/context-management|上下文管理架构 §0.5]]。

#### get_compression_audit()

```helen
let audit = get_compression_audit()
for event in audit {
    print("{event.layer}: {event.original_token_count} -> {event.compressed_token_count}")
}
```

---

## 配置详解

### 基本配置

编辑 `~/.helen/config.yaml`：

```yaml
transcript:
  enabled: true              # 启用 TranscriptStore（默认：true）
  backend: "sqlite"          # 后端类型："jsonl" 或 "sqlite"
  session_dir: "~/.helen/sessions"  # 会话存储目录
  max_memory_items: 1000     # LRU 缓存大小（默认：1000）
```

### 后端选择指南

| 场景 | 推荐后端 | 原因 |
|------|---------|------|
| 开发调试 | JSONL | 人类可读，易于 tail/grep |
| 生产环境 | SQLite | 高性能，索引优化 |
| 长会话 (>10K) | SQLite | WAL 模式，内存高效 |
| 快速原型 | JSONL | 无需额外依赖 |

### 内存优化

对于长会话，调整 LRU 缓存：

```yaml
transcript:
  max_memory_items: 500      # 减少内存占用
```

**内存使用公式**:
```
内存 ≈ max_memory_items × 平均消息大小
     ≈ 1000 × 10KB
     ≈ 10MB
```

---

## 性能优化

### 写入性能

| 后端 | 延迟 | 吞吐量 | 说明 |
|------|------|--------|------|
| JSONL | <1ms | 1000 msg/s | append-only，快速 |
| SQLite WAL | <1ms | 2000 msg/s | 批量提交，并发读 |

### 读取性能

| 操作 | 时间复杂度 | 说明 |
|------|-----------|------|
| `get(uuid)` | O(1) | UUID 索引 |
| `read_view()` | O(1) | 视图缓存 |
| `read_view()` (首次) | O(n) | 重建视图 |

### 内存优化

- **LRU 驱逐**: 自动驱逐旧消息到后端
- **视图缓存**: dirty flag + 缓存，避免重复计算
- **按需加载**: 从后端加载时只加载最近的消息

---

## 最佳实践

### 1. 生产环境使用 SQLite

```yaml
transcript:
  backend: "sqlite"
  max_memory_items: 1000
```

**优势**:
- 高性能写入（WAL 模式）
- UUID 索引（O(1) 查找）
- 事务安全

### 2. 定期清理旧会话

```helen
// 在长时间运行的应用中
let sessions = list_sessions()
if len(sessions) > 100 {
    // TODO: 添加 cleanup_sessions() stdlib 函数
    // 或使用 SessionManager.cleanup_old_sessions()
}
```

### 3. 导出重要会话

```helen
// 会话结束时导出
export_transcript("important_session.json", "json")
```

### 4. 监控压缩效率

```helen
let audit = get_compression_audit()
let total_saved = 0
for event in audit {
    total_saved += event.original_token_count - event.compressed_token_count
}
print("Total tokens saved: {total_saved}")
```

### 5. 调试时使用 JSONL

```yaml
transcript:
  backend: "jsonl"  # 易于 tail -f 和 grep
```

```bash
# 实时查看 transcript
tail -f ~/.helen/sessions/*/transcript.jsonl

# 搜索特定消息
grep "error" ~/.helen/sessions/*/transcript.jsonl
```

---

## 故障排除

### TranscriptStore 未启用

**检查配置**:
```yaml
# ~/.helen/config.yaml
transcript:
  enabled: true  # 确保为 true
```

### 会话文件未创建

**检查权限**:
```bash
ls -la ~/.helen/sessions/
```

确保 Helen 有写入权限。

### 内存占用过高

**减少 LRU 缓存**:
```yaml
transcript:
  max_memory_items: 500  # 减少到 500
```

### 会话恢复失败

**检查会话是否存在**:
```bash
ls ~/.helen/sessions/<session_id>/
```

确保 transcript 文件完整。

---

## 技术细节

### 压缩流程

```
Compression Trigger (usage > threshold)
    ↓
graduated_compress() / traditional_compress()
    ↓
Return compressed list
    ↓
TranscriptStore.record_compression(
    head_uuid=compressed_msgs[0].uuid,
    tail_uuid=compressed_msgs[-1].uuid,
    anchor_uuid=anchor.uuid,
    summary=summary_text,
    layer=layer_name,
    original_token_count=original_tokens,
    compressed_token_count=compressed_tokens,
)
    ↓
Append BoundaryMarker to transcript
    ↓
Invalidate view cache (_dirty = True)
```

### 视图重建算法

```python
def read_view(self) -> list[Message]:
    # 1. 收集所有 BoundaryMarker
    compressed_ranges = []
    for item in self.transcript:
        if isinstance(item, BoundaryMarker):
            compressed_ranges.append((
                item.head_uuid, item.tail_uuid, 
                item.anchor_uuid, item.summary
            ))
    
    # 2. 构建压缩 UUID 集合
    compressed_uuids = set()
    for head, tail, anchor, summary in compressed_ranges:
        for i in range(head_idx, tail_idx + 1):
            compressed_uuids.add(self.transcript[i].uuid)
    
    # 3. 重建视图（跳过压缩消息，插入摘要）
    result = []
    for item in self.transcript:
        if isinstance(item, Message):
            if item.uuid not in compressed_uuids:
                result.append(item)
            elif item.uuid == anchor:
                result.append(Message(role="system", content=summary))
    
    return result
```

### UUID 生成

```python
def _generate_uuid() -> str:
    """生成 12 位 hex UUID (16^12 ≈ 2.8×10^14)"""
    return uuid4().hex[:12]
```

**碰撞概率**:
- 1M 消息: ~0.0000002% (极低)
- 1B 消息: ~0.2% (仍可接受)

---

## 相关文档

- [[runtime/context-management|上下文管理架构]] — 统一压缩入口
- [[runtime/history|历史管理]] — Token 预算、截断策略
- [[toolchain/stdlib|标准库]] — transcript 函数
- [[toolchain/cli|命令行工具]] — REPL 命令

---

**最后更新**: 2026-07-08 | **版本**: v1.16 | **状态**: ✅ 生产就绪
