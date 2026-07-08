# TranscriptStore SSOT 用户指南

> **Helen v1.16 新功能：TranscriptStore 作为消息唯一真实来源**

## 概述

TranscriptStore 是 Helen v1.16 引入的核心特性，它将所有对话消息持久化存储，提供完整的审计追踪和会话恢复能力。

### 核心特性

- ✅ **自动持久化**：所有对话自动保存到 `~/.helen/sessions/`
- ✅ **双后端支持**：JSONL（简单）或 SQLite（高性能）
- ✅ **内存高效**：LRU 缓存，10K 消息仅 ~10MB 内存
- ✅ **UUID 寻址**：O(1) 查找，无列表索引依赖
- ✅ **非破坏性压缩**：完整审计追踪，可回溯任意历史视图
- ✅ **会话管理**：创建、列表、恢复、清理会话

## 快速开始

### 1. 默认启用

TranscriptStore 默认启用，无需额外配置。启动 Helen REPL 或运行程序时，自动创建会话：

```bash
$ helen repl
Helen REPL v1.16

> let x = 42
> :session_id
Current session: session_1783492628_d9d9c0aa
```

### 2. 查看当前会话

```bash
> :transcript
Current transcript view (3 messages):
  [1] [user] let x = 42
  [2] [assistant] OK
  [3] [user] :session_id

Stats: 3 total items, 3 messages, 0 compression boundaries
```

### 3. 列出所有会话

```bash
> :sessions
Transcript sessions (5 total):
  [1] session_1783492628_d9d9c0aa
       Modified: 2026-07-08 15:30:00, Size: 2.5 KB, Messages: ~50
  [2] session_1783492600_abc12345
       Modified: 2026-07-08 14:00:00, Size: 1.2 KB, Messages: ~20
  ...
```

## 配置

### 基本配置

编辑 `~/.helen/config.yaml`：

```yaml
transcript:
  enabled: true              # 启用 TranscriptStore（默认：true）
  backend: "sqlite"          # 后端类型："jsonl" 或 "sqlite"
  session_dir: "~/.helen/sessions"  # 会话存储目录
  max_memory_items: 1000     # LRU 缓存大小（默认：1000）
```

### 后端选择

**JSONL 后端**（默认）：
- ✅ 简单、人类可读
- ✅ 崩溃安全（append-only）
- ✅ 易于 tail/grep 调试
- ⚠️ 无索引，大量消息时查询较慢

**SQLite 后端**：
- ✅ WAL 模式，高性能写入（<1ms/消息）
- ✅ UUID 索引，O(1) 查找
- ✅ 事务安全，支持并发读
- ⚠️ 二进制格式，不易直接查看

```yaml
# 使用 SQLite 后端
transcript:
  backend: "sqlite"
```

### 内存优化

对于长会话（>10K 消息），调整 LRU 缓存：

```yaml
transcript:
  max_memory_items: 500      # 减少内存占用
```

**内存使用示例**：
- 100 消息: ~1MB
- 1K 消息: ~10MB
- 10K 消息: ~10MB (LRU 缓存生效)
- 100K 消息: ~50MB (LRU 缓存生效)

## REPL 命令

### :transcript

显示当前会话的有效视图（应用压缩后）：

```bash
> :transcript
Current transcript view (15 messages):
  [1] [user] Hello
  [2] [assistant] Hi there
  ...

Stats: 20 total items, 15 messages, 5 compression boundaries
```

**选项**：
- `:transcript --full`：显示完整 transcript（包括压缩的消息）
- `:transcript --audit`：显示压缩审计追踪

### :transcript --full

显示完整 transcript，包括所有 BoundaryMarker：

```bash
> :transcript --full
Full transcript (25 items):
  [1] [user] Hello
  [2] [assistant] Hi
  [3] --- Compression Boundary (auto_compact) ---
       Range: abc123..def456
       Summary: Compressed first 10 messages
  [4] [user] How are you?
  ...
```

### :transcript --audit

显示所有压缩事件的审计追踪：

```bash
> :transcript --audit
Compression audit (3 events):

  [1] Layer: auto_compact
      UUID: a1b2c3d4e5f6
      Range: abc123..def456
      Anchor: ghi789
      Tokens: 500 -> 100
      Summary: Compressed conversation...

  [2] Layer: graduated_layer3
      ...
```

### :sessions

列出所有会话，按修改时间排序（最新在前）：

```bash
> :sessions
Transcript sessions (10 total):
  [1] session_1783492628_d9d9c0aa
       Modified: 2026-07-08 15:30:00, Size: 2.5 KB, Messages: ~50
  [2] session_1783492600_abc12345
       Modified: 2026-07-08 14:00:00, Size: 1.2 KB, Messages: ~20
  ...
```

### :session_id

显示当前会话 ID：

```bash
> :session_id
Current session: session_1783492628_d9d9c0aa
```

## Stdlib 函数

### get_session_id()

获取当前会话 ID：

```helen
let session = get_session_id()
print("Current session: {session}")
// Output: Current session: session_1783492628_d9d9c0aa
```

### list_sessions()

列出所有会话：

```helen
let sessions = list_sessions()
for s in sessions {
    print("{s.session_id}: {s.size_bytes} bytes, {s.message_count} messages")
}
```

### replay_transcript()

回放会话消息：

```helen
// 回放当前会话
let messages = replay_transcript()
for msg in messages {
    print("[{msg.role}] {msg.content}")
}

// 回放指定会话，包括压缩的消息
let full = replay_transcript("session_1783492628_d9d9c0aa", true)
```

### export_transcript()

导出 transcript 到文件：

```helen
// 导出为 JSON
export_transcript("my_chat.json", "json")

// 导出为 Markdown
export_transcript("my_chat.md", "markdown")

// 导出为纯文本
export_transcript("my_chat.txt", "text")
```

### get_compression_audit()

获取压缩审计追踪：

```helen
let audit = get_compression_audit()
for event in audit {
    print("{event.layer}: {event.original_token_count} -> {event.compressed_token_count}")
    print("  Summary: {event.summary}")
}
```

## 会话管理

### 会话生命周期

1. **自动创建**：启动 Helen 时自动创建新会话
2. **持久化**：所有消息实时写入磁盘
3. **恢复**：可通过 UUID 恢复任意历史会话
4. **清理**：使用 `SessionManager.cleanup_old_sessions()` 清理旧会话

### 会话目录结构

```
~/.helen/sessions/
├── session_1783492628_d9d9c0aa/
│   └── transcript.jsonl  (或 transcript.db)
├── session_1783492600_abc12345/
│   └── transcript.jsonl
└── ...
```

### 手动管理会话

```python
from helen.runtime.session_manager import SessionManager

manager = SessionManager()

# 列出所有会话
sessions = manager.list_sessions()
for s in sessions:
    print(f"{s['session_id']}: {s['size_bytes']} bytes")

# 删除旧会话
manager.delete_session("session_1783492600_abc12345")

# 清理旧会话（保留最近 100 个）
manager.cleanup_old_sessions(keep_count=100)
```

## 压缩与审计

### 非破坏性压缩

TranscriptStore 使用 BoundaryMarker 记录压缩事件，不删除原始消息：

```
Transcript:
  [msg1] [msg2] [msg3] [msg4] [msg5]
                ↓ 压缩 msg1-msg3
  [msg1] [msg2] [msg3] [msg4] [msg5] [BoundaryMarker]
                                      ↓
                                read_view() 返回:
                                [summary] [msg4] [msg5]
```

### 审计追踪

每次压缩都会记录：
- `head_uuid`：压缩范围起始 UUID
- `tail_uuid`：压缩范围结束 UUID
- `anchor_uuid`：锚点消息 UUID
- `summary`：压缩摘要
- `layer`：压缩层名称
- `original_token_count`：压缩前 token 数
- `compressed_token_count`：压缩后 token 数

## 性能优化

### 内存优化

- **LRU 缓存**：只保留最近 N 条消息在内存
- **自动驱逐**：超过 `max_memory_items` 时自动驱逐旧消息
- **按需加载**：从后端加载时只加载最近的消息

### 磁盘 IO 优化

- **JSONL**：append-only，快速写入（<1ms/消息）
- **SQLite WAL**：批量提交，并发读支持
- **延迟刷盘**：JSONL 使用 flush()，SQLite 使用事务

### 查找优化

- **UUID 索引**：O(1) 查找 via `get(uuid)`
- **SQLite 索引**：UUID、timestamp 字段建立索引
- **视图缓存**：dirty flag + 缓存，避免重复计算

## 故障排除

### TranscriptStore 未启用

检查配置：
```yaml
# ~/.helen/config.yaml
transcript:
  enabled: true  # 确保为 true
```

### 会话文件未创建

检查权限：
```bash
ls -la ~/.helen/sessions/
```

确保 Helen 有写入权限。

### 内存占用过高

减少 LRU 缓存大小：
```yaml
transcript:
  max_memory_items: 500  # 减少到 500
```

### 会话恢复失败

检查会话是否存在：
```bash
ls ~/.helen/sessions/<session_id>/
```

确保 transcript 文件完整。

## 最佳实践

### 1. 定期清理旧会话

```helen
// 在长时间运行的应用中
let sessions = list_sessions()
if len(sessions) > 100 {
    // 清理旧会话
    // TODO: 添加 cleanup_sessions() stdlib 函数
}
```

### 2. 导出重要会话

```helen
// 会话结束时导出
export_transcript("important_session.json", "json")
```

### 3. 监控压缩效率

```helen
let audit = get_compression_audit()
let total_saved = 0
for event in audit {
    total_saved += event.original_token_count - event.compressed_token_count
}
print("Total tokens saved: {total_saved}")
```

### 4. 使用 SQLite 后端提升性能

对于生产环境或长会话，推荐使用 SQLite：

```yaml
transcript:
  backend: "sqlite"
```

## 技术细节

### 架构

```
TranscriptStore (SSOT)
  ↓
Backend (JSONL | SQLite)
  ↓
LRU Cache (max_memory_items)
  ↓
UUID Index (O(1) lookups)
  ↓
View Cache (dirty flag)
```

### 数据流

```
User Input
  ↓
_add_to_history()
  ↓
TranscriptStore.append()  (SSOT)
  ↓
Backend.append()  (持久化)
  ↓
LRU Eviction (if needed)

LLM Call
  ↓
_prepare_history_for_llm()
  ↓
TranscriptStore.read_view()  (应用 BoundaryMarker)
  ↓
View Cache (O(1) if no changes)
  ↓
LLM API Call
```

### 压缩流程

```
Compression Trigger
  ↓
graduated_compress() / traditional_compress()
  ↓
Return compressed list
  ↓
TranscriptStore.record_compression()
  ↓
Append BoundaryMarker
  ↓
View Cache invalidated
```

## 总结

TranscriptStore SSOT 为 Helen 提供了：

- ✅ **数据一致性**：消除双写分叉
- ✅ **可逆压缩**：完整审计追踪
- ✅ **跨会话持久化**：会话可恢复
- ✅ **内存卸载**：长会话 O(window) 内存
- ✅ **调试能力**：回溯"LLM 看到了什么"

**立即开始使用 TranscriptStore，享受更强大、更可靠的对话管理！**
