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
