# RFC: TranscriptStore 全面启用方案

> **把 TranscriptStore 作为消息唯一真实来源（SSOT）的架构重构方案**

| 字段 | 内容 |
|------|------|
| **文档状态** | Draft |
| **版本** | v1.0 |
| **创建日期** | 2026-07-08 |
| **作者** | Helen Core Team |
| **审核人** | TBD |
| **关联模块** | `helen/runtime/transcript_store.py`, `helen/interpreter/agent_context.py`, `helen/interpreter/llm_mixin.py`, `helen/runtime/history.py` |
| **关联 PR** | TBD |
| **关联 Issue** | TranscriptStore 半成品清理 |

---

## 目录

1. [概述](#1-概述)
2. [背景与问题陈述](#2-背景与问题陈述)
3. [目标与非目标](#3-目标与非目标)
4. [现状分析](#4-现状分析)
5. [目标架构设计](#5-目标架构设计)
6. [分阶段迁移路径](#6-分阶段迁移路径)
7. [详细设计](#7-详细设计)
8. [测试策略](#8-测试策略)
9. [性能影响分析](#9-性能影响分析)
10. [风险与回滚方案](#10-风险与回滚方案)
11. [时间线与里程碑](#11-时间线与里程碑)
12. [附录](#12-附录)

---

## 1. 概述

### 1.1 一句话描述

将 Helen 的对话历史管理从"双写 + 有损压缩"架构重构为"TranscriptStore 单写 + 非破坏性压缩 + 持久化"架构，让 TranscriptStore 成为所有对话消息的唯一真实来源（Single Source of Truth, SSOT）。

### 1.2 核心价值

- **数据一致性**：消除 `_history` 与 `TranscriptStore` 的双写分叉
- **可逆压缩**：压缩变为追加 BoundaryMarker，完整对话可随时回放
- **跨会话持久化**：REPL 会话可恢复、Agent 崩溃可续跑、审计日志可导出
- **内存卸载**：长会话从 O(n) 内存降到 O(window) 内存
- **调试能力质变**：错误发生时可回溯"LLM 看到了什么 vs 原始对话是什么"

### 1.3 影响范围

- **核心模块**：6 个（transcript_store, agent_context, llm_mixin, history, prompt_builder, context）
- **改动行数**：约 1500-2000 行（含测试）
- **测试影响**：约 30-40 个现有测试需更新
- **兼容性**：外部 FFI 直接访问 `_history` 的代码需要兼容层

---

## 2. 背景与问题陈述

### 2.1 TranscriptStore 的历史

`TranscriptStore` 在 Phase 10（v1.12）引入，设计目标是作为对话历史的"事件溯源"层：
- 所有消息 append-only，永不修改/删除
- 压缩事件记录为 `BoundaryMarker`，而非就地改写
- `read_view()` 从 marker 重建"压缩后的有效视图"

**代码量**：366 行，包含完整的数据结构（`BoundaryMarker` + `TranscriptStore`）、序列化（`to_dict/from_dict`）、审计（`get_compression_audit`）。

**测试覆盖**：`tests/runtime/test_transcript_store.py`（228 行单元测试）。

### 2.2 当前问题

#### 问题 1：默认禁用，无启用入口

```python
# helen/interpreter/agent_context.py:86
def __init__(self, ..., transcript_store_enabled: bool = False, ...):
    ...
    self._transcript_store = None
    if transcript_store_enabled:
        from helen.runtime.transcript_store import TranscriptStore
        self._transcript_store = TranscriptStore()
```

- `Interpreter.__init__` 默认 `transcript_store_enabled=False`（`interpreter.py:746`）
- 所有 4 处生产调用点（`cli/__main__.py:80, 442`、`cli/repl.py:175, 405`）都未传此参数
- 无 CLI flag、无 config.yaml 选项、无 agent 声明语法支持

#### 问题 2：无生产消费者

grep 全代码库：
- `read_view()` 和 `get_compression_audit()` **仅在测试中被调用**
- 生产代码唯一消费点是 `get_stats()`（`agent_context.py:703-708`），只报告 item/boundary 计数
- `append_many()`、`from_dict()` 全代码库零调用

#### 问题 3：双写架构的脆弱性

`_add_to_history()`（`llm_mixin.py:868-898`）执行双写：

```python
self._history.append(msg)          # 写入 #1：可变 list
if agent_ctx.transcript_store is not None:
    agent_ctx.transcript_store.append(msg)  # 写入 #2：append-only
```

但两者**语义不一致**：
- `_history` 是 list，经过 `self._history[:] = trimmed`（L898）**就地替换**
- TranscriptStore 保持 append-only，用 BoundaryMarker 记录压缩
- 没有一致性校验：如果 TranscriptStore 记录了压缩事件，但 `_history` 的替换用了不同算法，两者会分叉

#### 问题 4：脆弱的逆推逻辑

`_record_transcript_compression()`（`agent_context.py:381-454`）的 74 行代码，通过 UUID 集合匹配"猜测"哪些消息被压缩了——这是 SSOT 缺失导致的补丁逻辑。

#### 问题 5：内存压力

所有消息对象（Message dataclass + tool_calls list）常驻内存。128K context window 下，长会话可能包含 1000+ 条消息，每条消息 `estimate_tokens()` 都缓存 `_token_count`。TranscriptStore 又保留全部未压缩消息，内存翻倍。

---

## 3. 目标与非目标

### 3.1 目标（In Scope）

| 编号 | 目标 | 优先级 |
|------|------|--------|
| G1 | TranscriptStore 成为消息唯一真实来源 | P0 |
| G2 | 压缩操作非破坏化（只追加 BoundaryMarker） | P0 |
| G3 | Transcript 持久化到磁盘（JSONL/SQLite） | P0 |
| G4 | 提供 REPL 调试命令（`:transcript`、`:compression_audit`） | P1 |
| G5 | 提供会话恢复能力（REPL `:resume`、Agent checkpoint） | P1 |
| G6 | 内存卸载（长会话 O(window) 内存） | P2 |
| G7 | 提供 `replay_transcript()` stdlib 函数 | P2 |

### 3.2 非目标（Out of Scope）

- **不改变 LLM API 调用格式**：仍然使用 OpenAI-compatible message list
- **不改变压缩算法本身**：graduated/traditional/cache-aware 压缩逻辑保持不变
- **不支持分布式 transcript**：单用户场景，不涉及多节点同步
- **不引入新的压缩策略**：现有 5 层压缩已足够

---

## 4. 现状分析

### 4.1 当前数据流

```
┌─────────────────────────────────────────────────────────────────┐
│                      LLM 调用路径                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User Input                                                     │
│      │                                                          │
│      ▼                                                          │
│  _add_to_history()  ─────────────────────────────┐             │
│      │                                            │             │
│      ├─> self._history.append(msg)  (写入 #1)     │             │
│      │                                            │             │
│      └─> transcript_store.append(msg) (写入 #2,   │             │
│           if enabled)                              │             │
│                                                   │             │
│  _prepare_history_for_llm()                       │             │
│      │                                            │             │
│      ├─> _compress_history(history)               │             │
│      │       │                                    │             │
│      │       └─> graduated_compress()             │             │
│      │               │                            │             │
│      │               └─> return new_list          │             │
│      │                                            │             │
│      ├─> self._history[:] = new_list  (就地替换)  │             │
│      │                                            │             │
│      └─> _record_transcript_compression()         │             │
│              │                                    │             │
│              └─> UUID 集合匹配 (逆推哪些被压缩)   │             │
│                                                     │             │
│  LLM API Call (with compressed history)            │             │
│                                                     │             │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 关键代码位置

| 功能 | 文件 | 行号 | 说明 |
|------|------|------|------|
| TranscriptStore 定义 | `runtime/transcript_store.py` | 118-356 | 366 行 |
| BoundaryMarker 定义 | `runtime/transcript_store.py` | 51-111 | 61 行 |
| 启用开关 | `interpreter/agent_context.py` | 86 | `transcript_store_enabled=False` |
| 双写逻辑 | `interpreter/llm_mixin.py` | 868-898 | `_add_to_history()` |
| 压缩路径 | `interpreter/agent_context.py` | 319-454 | `_compress_history()` |
| 逆推逻辑 | `interpreter/agent_context.py` | 381-454 | `_record_transcript_compression()` |
| 就地替换 | `interpreter/llm_mixin.py` | 898 | `self._history[:] = trimmed` |
| 缓存感知压缩 | `interpreter/agent_context.py` | 489-554 | `_apply_cache_aware_wrap()` |
| 序列化 | `runtime/transcript_store.py` | 305-356 | `to_dict/from_dict` |
| 测试 | `tests/runtime/test_transcript_store.py` | 全文件 | 228 行 |

### 4.3 依赖关系图

```
┌─────────────────┐
│  Interpreter    │
│  (llm_mixin)    │
└────────┬────────┘
         │
         ├─> AgentContext
         │       │
         │       ├─> _history (list)  ─────────────┐
         │       │                                  │
         │       └─> TranscriptStore (if enabled)   │
         │                                          │
         └─> HistoryManager                         │
                 │                                  │
                 └─> enforce_limit() ───────────────┘
                         │
                         └─> _summarize_compress()
                                 │
                                 └─> return new_list (destructive)
```

---

## 5. 目标架构设计

### 5.1 核心原则

1. **单一写入点**：所有消息只写入 TranscriptStore，`_history` 变为只读派生视图
2. **非破坏性压缩**：压缩只追加 BoundaryMarker，不修改/删除已有消息
3. **持久化优先**：Transcript 异步写入磁盘（JSONL 或 SQLite），内存只保留活跃窗口
4. **UUID 寻址**：所有消息通过 UUID 标识，不再依赖 list 索引
5. **渐进式迁移**：分阶段推进，每个阶段可独立交付和回滚

### 5.2 目标数据流

```
┌─────────────────────────────────────────────────────────────────┐
│                      LLM 调用路径 (重构后)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User Input                                                     │
│      │                                                          │
│      ▼                                                          │
│  transcript_store.append(msg)  ──────┐                          │
│      │                                │                          │
│      └─> 异步写入磁盘 (JSONL/SQLite)  │                          │
│                                       │                          │
│  _prepare_history_for_llm()           │                          │
│      │                                │                          │
│      ├─> transcript_store.read_view() │                          │
│      │       │                        │                          │
│      │       └─> 应用 BoundaryMarker  │                          │
│      │               │                │                          │
│      │               └─> return view  │                          │
│      │                                │                          │
│      ├─> _compress_history(view)      │                          │
│      │       │                        │                          │
│      │       └─> transcript_store     │                          │
│      │           .record_compression()│                          │
│      │                                │                          │
│      └─> return compressed_view       │                          │
│                                       │                          │
│  LLM API Call (with compressed_view)  │                          │
│                                       │                          │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 关键变化

| 组件 | 当前 | 目标 |
|------|------|------|
| **消息写入** | 双写（`_history` + TranscriptStore） | 单写（只写 TranscriptStore） |
| **`_history` 角色** | 主存储（可变 list） | 只读派生视图（`read_view()` 的缓存） |
| **压缩操作** | 破坏性（返回新 list，就地替换） | 非破坏性（追加 BoundaryMarker） |
| **消息寻址** | list 索引 `_history[i]` | UUID `transcript_store.get(uuid)` |
| **持久化** | 无（全在内存） | JSONL/SQLite（异步写入） |
| **内存模型** | O(n) 全量驻留 | O(window) 活跃窗口 + LRU cache |

### 5.4 新增组件

#### 5.4.1 TranscriptStoreBackend（抽象后端）

```python
class TranscriptStoreBackend(ABC):
    """Abstract backend for transcript persistence."""
    
    @abstractmethod
    async def append(self, item: Message | BoundaryMarker) -> None:
        """Append item to persistent storage."""
        pass
    
    @abstractmethod
    async def load_all(self) -> list[Message | BoundaryMarker]:
        """Load all items from persistent storage."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close backend connection."""
        pass


class JSONLBackend(TranscriptStoreBackend):
    """JSONL file backend for transcript persistence."""
    
    def __init__(self, path: Path):
        self.path = path
        self._writer: Optional[aiofiles.threaded.TextIOWrapper] = None
    
    async def append(self, item: Message | BoundaryMarker) -> None:
        if self._writer is None:
            self._writer = await aiofiles.open(self.path, mode='a')
        await self._writer.write(json.dumps(item.to_dict()) + '\n')
        await self._writer.flush()
    
    async def load_all(self) -> list[Message | BoundaryMarker]:
        if not self.path.exists():
            return []
        items = []
        async with aiofiles.open(self.path, mode='r') as f:
            async for line in f:
                data = json.loads(line)
                if data['type'] == 'message':
                    items.append(Message.from_dict(data))
                elif data['type'] == 'boundary_marker':
                    items.append(BoundaryMarker.from_dict(data))
        return items
    
    async def close(self) -> None:
        if self._writer:
            await self._writer.close()


class SQLiteBackend(TranscriptStoreBackend):
    """SQLite backend for transcript persistence (Phase 4)."""
    # TODO: Implement in Phase 4
    pass
```

#### 5.4.2 SessionManager（会话管理）

```python
class SessionManager:
    """Manages transcript sessions and persistence."""
    
    def __init__(self, base_dir: Path = Path.home() / ".helen" / "sessions"):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def create_session(self, session_id: Optional[str] = None) -> str:
        """Create a new transcript session."""
        if session_id is None:
            session_id = f"session_{int(time.time())}_{uuid4().hex[:8]}"
        session_dir = self.base_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_id
    
    def get_session_path(self, session_id: str) -> Path:
        """Get transcript file path for a session."""
        return self.base_dir / session_id / "transcript.jsonl"
    
    def list_sessions(self) -> list[dict[str, Any]]:
        """List all sessions with metadata."""
        sessions = []
        for session_dir in self.base_dir.iterdir():
            if session_dir.is_dir():
                transcript_path = session_dir / "transcript.jsonl"
                if transcript_path.exists():
                    stat = transcript_path.stat()
                    sessions.append({
                        "session_id": session_dir.name,
                        "created_at": stat.st_ctime,
                        "modified_at": stat.st_mtime,
                        "size_bytes": stat.st_size,
                    })
        return sorted(sessions, key=lambda s: s["modified_at"], reverse=True)
    
    def delete_session(self, session_id: str) -> None:
        """Delete a session and its transcript."""
        session_dir = self.base_dir / session_id
        if session_dir.exists():
            import shutil
            shutil.rmtree(session_dir)
```

#### 5.4.3 新增 stdlib 函数

```python
# helen/stdlib/transcript.py

def get_session_id() -> str:
    """Get current transcript session ID."""
    # Returns current session ID or empty string if not enabled
    pass

def list_sessions() -> list[dict]:
    """List all transcript sessions."""
    pass

def resume_session(session_id: str) -> bool:
    """Resume a previous transcript session."""
    pass

def replay_transcript(
    session_id: Optional[str] = None,
    include_compressed: bool = False,
) -> list[dict]:
    """Replay transcript messages.
    
    Args:
        session_id: Session to replay (default: current session)
        include_compressed: Whether to include compressed messages
    
    Returns:
        List of message dicts
    """
    pass

def export_transcript(
    output_path: str,
    format: str = "json",  # json | markdown | text
) -> str:
    """Export transcript to file."""
    pass

def get_compression_audit() -> list[dict]:
    """Get audit trail of all compression events."""
    pass
```

---

## 6. 分阶段迁移路径

### 6.1 阶段概览

```
┌────────────────────────────────────────────────────────────────┐
│  Phase 1        │  Phase 2        │  Phase 3       │  Phase 4  │
│  启用+持久化     │  SSOT 切换      │  非破坏压缩     │  内存卸载  │
│  (2-3 周)       │  (2 周)         │  (3 周)        │  (2 周)   │
│                 │                 │                │           │
│  ────────────   │  ────────────   │  ────────────  │  ──────   │
│  • 默认启用     │  • 单写 TS      │  • 删除就地替换 │  • SQLite │
│  • JSONL 持久化  │  • _history 变  │  • 压缩只追加  │  • UUID   │
│  • 会话管理     │    派生视图     │    Boundary     │    寻址   │
│  • REPL 命令    │  • 删除双写     │  • 可逆压缩   │  • LRU    │
│                 │  • 删除逆推逻辑  │                │           │
│                 │                 │                │           │
│  回滚: 改回     │  回滚: 保留     │  回滚: 兼容    │  回滚:    │
│  False          │  _history cache │  开关         │  降级 JSONL│
└────────────────────────────────────────────────────────────────┘
```

### 6.2 Phase 1：启用 TranscriptStore + 持久化（2-3 周）

**目标**：让 TranscriptStore 成为事实上的 audit log，但不改变现有压缩路径。

**改动范围**：
- `interpreter/agent_context.py`：`transcript_store_enabled` 默认改为 `True`
- `runtime/transcript_store.py`：添加 `JSONLBackend`，append 时异步写盘
- 新增 `runtime/session_manager.py`：会话管理
- 新增 `stdlib/transcript.py`：stdlib 函数
- `cli/repl.py`：添加 `:transcript`、`:compression_audit`、`:sessions` 命令
- `cli/__main__.py`：添加 `--transcript-log` CLI flag

**测试**：
- 新增 `tests/runtime/test_transcript_persistence.py`
- 新增 `tests/runtime/test_session_manager.py`
- 新增 `tests/stdlib/test_transcript.py`
- 现有测试不受影响

**回滚方案**：将 `transcript_store_enabled` 改回 `False` 即可。

**验收标准**：
- [ ] TranscriptStore 默认启用，所有消息自动记录
- [ ] Transcript 持久化到 `~/.helen/sessions/<session_id>/transcript.jsonl`
- [ ] REPL `:transcript` 命令可显示完整 transcript
- [ ] REPL `:compression_audit` 命令可显示压缩历史
- [ ] 会话恢复（`:resume <session_id>`）可工作
- [ ] 所有现有测试通过

### 6.3 Phase 2：SSOT 切换（2 周）

**目标**：`read_view()` 成为 LLM 调用的唯一入口，删除双写逻辑。

**改动范围**：
- `interpreter/llm_mixin.py`：
  - `_add_to_history()` 改为只 `transcript_store.append(msg)`，删除 `_history.append(msg)`
  - `_history` 属性改为 `return self._agent_context.transcript_store.read_view()`
- `interpreter/agent_context.py`：
  - 删除 `_record_transcript_compression()` 的 UUID 匹配逻辑（74 行）
  - `_compress_history()` 改为直接调用 `transcript_store.record_compression()`
- `runtime/history.py`：
  - `enforce_limit()` 改为返回新 list **不修改原 list**（纯函数化）

**测试**：
- 现有 2624 个测试中，约 30 个涉及 `_history` 直接操作的需更新
- 重点测试 `_prepare_history_for_llm()` 路径

**回滚方案**：保留 `_history` 作为 read-through cache，写入仍走 TranscriptStore。

**验收标准**：
- [ ] 所有消息只写入 TranscriptStore
- [ ] `_history` 变为只读派生视图
- [ ] 删除双写逻辑（`llm_mixin.py:868-898` 简化）
- [ ] 删除 `_record_transcript_compression()` 的 UUID 匹配逻辑
- [ ] 所有现有测试通过（约 30 个测试更新后）

### 6.4 Phase 3：非破坏性压缩（3 周）

**目标**：删除 `_history[:] = trimmed` 就地替换，压缩只追加 BoundaryMarker。

**改动范围**：
- `interpreter/agent_context.py`：
  - `_compress_history()` 删除 `return compressed`，改为 `self._transcript_store.record_compression(...)`
- `runtime/history.py`：
  - `_summarize_compress()` 和 `_truncate_compress()` 不再返回新 list，而是返回 BoundaryMarker 参数供 TranscriptStore 记录
- `runtime/transcript_store.py`：
  - `read_view()` 已是非破坏性的，只需优化性能（添加 dirty flag + 缓存）
- `interpreter/agent_context.py`：
  - `_apply_cache_aware_wrap()` 需要完全重写为 SSOT-aware

**测试**：
- cache-aware 测试需要重写（`_apply_cache_aware_wrap` 不再返回新 list）
- 重点测试可逆压缩（`:history --diff <boundary_uuid>`）

**回滚方案**：添加 `compression_mode="destructive"` 兼容开关。

**验收标准**：
- [ ] 压缩操作只追加 BoundaryMarker，不修改已有消息
- [ ] `read_view()` 正确重建压缩后的有效视图
- [ ] 可逆压缩（REPL `:history --full` 显示完整 transcript）
- [ ] 所有压缩策略（graduated/traditional/cache-aware）都正确记录 BoundaryMarker
- [ ] 所有现有测试通过

### 6.5 Phase 4：内存卸载 + UUID 寻址（2 周）

**目标**：TranscriptStore 迁移到 SQLite，所有索引访问改为 UUID 寻址。

**改动范围**：
- `runtime/transcript_store.py`：添加 `SQLiteBackend`（WAL 模式）
- `runtime/history.py`：`search()` / `get_tool_history()` 改为 UUID-based
- 全局搜索 `_history[` 和 `history[` 索引访问，逐一替换
- 添加 LRU cache（只保留最近 N 条消息在内存）

**测试**：
- 端到端集成测试
- 性能测试（100K 消息长会话）

**回滚方案**：SQLite 后端可降级回 JSONL。

**验收标准**：
- [ ] SQLite 后端工作正常（WAL 模式，写入 <1ms/行）
- [ ] 所有 `_history[i]` 索引访问改为 UUID 寻址
- [ ] 100K 消息长会话内存 <50MB
- [ ] 所有现有测试通过

---

## 7. 详细设计

### 7.1 TranscriptStore 重构

#### 7.1.1 添加 Backend 抽象

```python
class TranscriptStore:
    def __init__(self, backend: Optional[TranscriptStoreBackend] = None):
        self.transcript: list[Message | BoundaryMarker] = []
        self._uuid_index: dict[str, int] = {}
        self._backend = backend
        self._dirty = False  # dirty flag for view caching
        self._cached_view: Optional[list[Message]] = None
    
    async def append_async(self, message: Message) -> Message:
        """Async append with persistence."""
        if not message.uuid:
            message.uuid = _generate_uuid()
        
        index = len(self.transcript)
        self.transcript.append(message)
        self._uuid_index[message.uuid] = index
        self._dirty = True
        
        if self._backend:
            await self._backend.append(message)
        
        return message
    
    def append(self, message: Message) -> Message:
        """Sync append (wraps async for backward compatibility)."""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # If already in async context, schedule append
            return asyncio.ensure_future(self.append_async(message))
        except RuntimeError:
            # No running loop, use sync wrapper
            return asyncio.run(self.append_async(message))
```

#### 7.1.2 优化 read_view() 性能

```python
def read_view(self) -> list[Message]:
    """Reconstruct the current effective message list (cached)."""
    if not self._dirty and self._cached_view is not None:
        return self._cached_view
    
    # ... existing read_view logic ...
    
    self._cached_view = result
    self._dirty = False
    return result
```

### 7.2 AgentContext 重构

#### 7.2.1 删除 `_record_transcript_compression()`

```python
# BEFORE (74 lines of UUID matching logic)
def _record_transcript_compression(self, original_history, compressed_history, layer):
    original_uuids = {msg.uuid for msg in original_history if hasattr(msg, 'uuid')}
    compressed_uuids = {msg.uuid for msg in compressed_history if hasattr(msg, 'uuid')}
    removed_uuids = original_uuids - compressed_uuids
    # ... complex matching logic ...

# AFTER (direct call to transcript_store)
def _compress_history(self, history, max_tokens):
    # ... compression logic ...
    if self._transcript_store is not None:
        self._transcript_store.record_compression(
            head_uuid=compressed_range[0].uuid,
            tail_uuid=compressed_range[-1].uuid,
            anchor_uuid=anchor.uuid,
            summary=summary_text,
            layer=layer_name,
            original_token_count=original_tokens,
            compressed_token_count=compressed_tokens,
        )
```

#### 7.2.2 添加 Session 管理

```python
class AgentContext:
    def __init__(
        self,
        ...,
        transcript_store_enabled: bool = True,  # CHANGED: default True
        session_id: Optional[str] = None,
    ):
        ...
        self._session_id = session_id
        self._transcript_store = None
        
        if transcript_store_enabled:
            from helen.runtime.transcript_store import TranscriptStore
            from helen.runtime.session_manager import SessionManager
            
            if session_id is None:
                session_manager = SessionManager()
                session_id = session_manager.create_session()
            
            self._session_id = session_id
            transcript_path = session_manager.get_session_path(session_id)
            
            from helen.runtime.transcript_store import JSONLBackend
            backend = JSONLBackend(transcript_path)
            
            self._transcript_store = TranscriptStore(backend=backend)
```

### 7.3 llm_mixin 重构

#### 7.3.1 `_add_to_history()` 简化

```python
# BEFORE (dual-write)
def _add_to_history(self, message):
    self._history.append(message)
    if agent_ctx.transcript_store is not None:
        agent_ctx.transcript_store.append(message)

# AFTER (single-write)
def _add_to_history(self, message):
    agent_ctx = self._agent_context
    if agent_ctx.transcript_store is not None:
        agent_ctx.transcript_store.append(message)
    else:
        # Fallback for backward compatibility (Phase 1 only)
        self._history.append(message)
```

#### 7.3.2 `_history` 属性改为派生视图

```python
# BEFORE
@property
def _history(self):
    return self._agent_context._interpreter_history

# AFTER (Phase 2+)
@property
def _history(self):
    agent_ctx = self._agent_context
    if agent_ctx.transcript_store is not None:
        return agent_ctx.transcript_store.read_view()
    else:
        return agent_ctx._interpreter_history  # fallback
```

### 7.4 REPL 命令扩展

```python
# helen/cli/repl.py

def _handle_transcript(self, args: str):
    """:transcript [--full] [--audit]"""
    agent_ctx = self.interpreter._agent_context
    
    if agent_ctx.transcript_store is None:
        print("TranscriptStore is not enabled.")
        return
    
    if "--audit" in args:
        audit = agent_ctx.transcript_store.get_compression_audit()
        for event in audit:
            print(f"[{event['layer']}] {event['head_uuid'][:8]}..{event['tail_uuid'][:8]}")
            print(f"  Tokens: {event['original_token_count']} -> {event['compressed_token_count']}")
            print(f"  Summary: {event['summary'][:100]}...")
    elif "--full" in args:
        # Show complete transcript (including compressed messages)
        for item in agent_ctx.transcript_store.transcript:
            if isinstance(item, Message):
                print(f"[{item.role}] {item.content[:200]}...")
            elif isinstance(item, BoundaryMarker):
                print(f"--- Compression Boundary ({item.layer}) ---")
    else:
        # Show current effective view
        view = agent_ctx.transcript_store.read_view()
        for msg in view:
            print(f"[{msg.role}] {msg.content[:200]}...")

def _handle_sessions(self, args: str):
    """:sessions"""
    from helen.runtime.session_manager import SessionManager
    manager = SessionManager()
    sessions = manager.list_sessions()
    
    for session in sessions[:10]:  # Show last 10
        print(f"{session['session_id']}  "
              f"Modified: {time.ago(session['modified_at'])}  "
              f"Size: {session['size_bytes']} bytes")

def _handle_resume(self, session_id: str):
    """:resume <session_id>"""
    # TODO: Implement session resume logic
    pass
```

### 7.5 配置扩展

#### 7.5.1 `~/.helen/config.yaml`

```yaml
llm:
  base_url: "..."
  api_key: "..."
  model: "..."

transcript:
  enabled: true                  # Enable TranscriptStore (default: true)
  backend: "jsonl"               # jsonl | sqlite (Phase 4)
  session_dir: "~/.helen/sessions"
  max_memory_items: 1000         # LRU cache size (Phase 4)
```

#### 7.5.2 Agent 声明语法扩展

```helen
agent MyAgent {
  description "..."
  model "..."
  
  // New: transcript configuration
  transcript {
    enabled true
    session_id "my_session"      // Optional: reuse session
  }
  
  main {
    // ...
  }
}
```

---

## 8. 测试策略

### 8.1 测试分层

```
┌────────────────────────────────────────────────────────────┐
│  Level 4: Integration Tests                                │
│  • 端到端 LLM 调用路径                                      │
│  • 会话恢复流程                                             │
│  • 长会话（10K+ 消息）压力测试                              │
└────────────────────────────────────────────────────────────┘
                          ▲
┌────────────────────────────────────────────────────────────┐
│  Level 3: Component Tests                                  │
│  • AgentContext 压缩路径                                    │
│  • llm_mixin history 读写                                   │
│  • REPL 命令（:transcript, :sessions, :resume）             │
└────────────────────────────────────────────────────────────┘
                          ▲
┌────────────────────────────────────────────────────────────┐
│  Level 2: Unit Tests                                       │
│  • TranscriptStore append/read_view/record_compression      │
│  • JSONLBackend / SQLiteBackend                             │
│  • SessionManager                                           │
│  • stdlib transcript functions                              │
└────────────────────────────────────────────────────────────┘
                          ▲
┌────────────────────────────────────────────────────────────┐
│  Level 1: Existing Tests (Regression)                      │
│  • 2624 个现有测试必须全部通过                              │
│  • 约 30 个测试需更新（Phase 2-3）                          │
└────────────────────────────────────────────────────────────┘
```

### 8.2 新增测试清单

#### Phase 1 测试

| 测试文件 | 测试内容 | 行数估计 |
|---------|---------|---------|
| `tests/runtime/test_transcript_persistence.py` | JSONLBackend 读写、崩溃恢复 | ~150 |
| `tests/runtime/test_session_manager.py` | 会话创建/列表/删除 | ~100 |
| `tests/stdlib/test_transcript.py` | stdlib 函数（get_session_id, list_sessions, replay_transcript） | ~120 |
| `tests/cli/test_repl_transcript.py` | REPL 命令（:transcript, :sessions） | ~80 |

#### Phase 2 测试

| 测试文件 | 测试内容 | 行数估计 |
|---------|---------|---------|
| `tests/interpreter/test_ssot.py` | SSOT 切换后 LLM 调用路径 | ~200 |
| `tests/runtime/test_history_pure.py` | 纯函数化后的 enforce_limit() | ~100 |

#### Phase 3 测试

| 测试文件 | 测试内容 | 行数估计 |
|---------|---------|---------|
| `tests/runtime/test_non_destructive_compression.py` | 非破坏性压缩、可逆压缩 | ~180 |
| `tests/interpreter/test_cache_aware_ssot.py` | cache-aware 压缩 SSOT-aware | ~120 |

#### Phase 4 测试

| 测试文件 | 测试内容 | 行数估计 |
|---------|---------|---------|
| `tests/runtime/test_sqlite_backend.py` | SQLite 后端（WAL 模式） | ~150 |
| `tests/performance/test_transcript_memory.py` | 100K 消息内存压力测试 | ~100 |

### 8.3 测试更新清单（Phase 2-3）

需要更新的现有测试（约 30 个）：

| 测试文件 | 测试函数 | 更新原因 |
|---------|---------|---------|
| `tests/runtime/test_history.py` | `test_enforce_limit_*` (约 10 个) | `enforce_limit()` 改为纯函数 |
| `tests/interpreter/test_agent_context.py` | `test_compress_history_*` (约 8 个) | `_compress_history()` 不再返回新 list |
| `tests/interpreter/test_llm_mixin.py` | `test_add_to_history_*` (约 5 个) | 删除双写逻辑 |
| `tests/runtime/test_agent_context.py` | `test_cache_aware_*` (约 7 个) | `_apply_cache_aware_wrap()` 重写 |

---

## 9. 性能影响分析

### 9.1 内存影响

| 场景 | 当前 | Phase 1-2 | Phase 3-4 |
|------|------|-----------|-----------|
| 短会话（100 消息） | ~10MB | ~20MB（transcript 复制） | ~10MB（LRU cache） |
| 长会话（10K 消息） | ~200MB | ~400MB（transcript 复制） | ~50MB（LRU cache） |
| 超长会话（100K 消息） | OOM 风险 | OOM 风险 | ~100MB（SQLite + LRU） |

**分析**：
- Phase 1-2 内存翻倍（transcript + _history），需要尽快推进 Phase 3-4
- Phase 4 内存卸载是关键，100K 消息从 OOM 降到 100MB

### 9.2 CPU 影响

| 操作 | 当前 | Phase 1-2 | Phase 3-4 |
|------|------|-----------|-----------|
| 消息追加 | O(1) | O(1) + 磁盘 IO（异步） | O(1) + 磁盘 IO |
| read_view() | N/A | O(n) 遍历 transcript | O(n) + dirty flag 缓存 |
| 压缩 | O(n) | O(n) + record_compression | O(n) + append BoundaryMarker |
| LLM 调用准备 | O(n) | O(n) + read_view() | O(n) + cached view |

**分析**：
- `read_view()` 已是 O(n)，与当前 list 遍历同量级
- 添加 dirty flag + 缓存后，只有 append/compress 时重建 view
- 磁盘 IO 用异步写入（`aiofiles`），不阻塞主路径
- SQLite WAL 模式写入延迟 <1ms/行

### 9.3 磁盘 IO 影响

| 操作 | 频率 | 数据量 | 延迟 |
|------|------|--------|------|
| JSONL append | 每次消息追加 | ~1KB/消息 | <1ms（SSD） |
| JSONL load_all | 会话恢复 | ~1MB/1K 消息 | ~10ms（SSD） |
| SQLite insert | 每次消息追加 | ~1KB/消息 | <1ms（WAL 模式） |
| SQLite query | read_view() | 取决于查询 | <5ms（索引） |

**分析**：
- 磁盘 IO 不是瓶颈，SSD 延迟 <1ms
- JSONL 简单可靠，SQLite 更适合复杂查询（Phase 4）

---

## 10. 风险与回滚方案

### 10.1 风险矩阵

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| **内存翻倍（Phase 1-2）** | 高 | 中 | 尽快推进 Phase 3-4；添加 `max_memory_items` LRU |
| **磁盘 IO 阻塞主路径** | 中 | 高 | 异步写入（`aiofiles`）；失败时降级到内存 |
| **UUID 碰撞** | 低 | 高 | 使用 12 位 hex UUID（16^12 ≈ 2.8×10^14），碰撞概率极低 |
| **现有测试大量失败** | 中 | 中 | 分阶段推进，每阶段只影响 ~30 个测试 |
| **外部 FFI 代码 break** | 低 | 高 | 提供 `_history` 兼容层（`history_by_index()`） |
| **会话文件损坏** | 低 | 中 | JSONL 是 append-only，损坏只影响最后一条；SQLite 有 WAL 保护 |
| **性能退化** | 中 | 中 | 性能测试（Phase 4）；dirty flag 缓存优化 |

### 10.2 回滚方案

#### Phase 1 回滚

```python
# 将 transcript_store_enabled 改回 False
# helen/interpreter/agent_context.py:86
def __init__(self, ..., transcript_store_enabled: bool = False, ...):  # REVERT
```

**影响**：TranscriptStore 再次禁用，回到当前状态。

#### Phase 2 回滚

```python
# 保留 _history 作为 read-through cache
# helen/interpreter/llm_mixin.py
@property
def _history(self):
    return self._agent_context._interpreter_history  # REVERT
```

**影响**：恢复双写逻辑，但 TranscriptStore 仍然启用。

#### Phase 3 回滚

```yaml
# ~/.helen/config.yaml
transcript:
  compression_mode: "destructive"  # 兼容开关
```

**影响**：恢复破坏性压缩，但 TranscriptStore 仍然记录 BoundaryMarker。

#### Phase 4 回滚

```yaml
# ~/.helen/config.yaml
transcript:
  backend: "jsonl"  # 降级回 JSONL
```

**影响**：SQLite 后端降级回 JSONL，内存卸载失效。

---

## 11. 时间线与里程碑

### 11.1 总体时间线

```
Week 1-3    │ Phase 1: 启用 + 持久化
            │ • TranscriptStore 默认启用
            │ • JSONL 持久化
            │ • REPL 命令（:transcript, :sessions）
            │ • stdlib 函数
            │
Week 4-5    │ Phase 2: SSOT 切换
            │ • 删除双写逻辑
            │ • _history 变为派生视图
            │ • 删除 _record_transcript_compression() 逆推逻辑
            │
Week 6-8    │ Phase 3: 非破坏性压缩
            │ • 压缩只追加 BoundaryMarker
            │ • 可逆压缩（REPL :history --full）
            │ • cache-aware 压缩 SSOT-aware
            │
Week 9-10   │ Phase 4: 内存卸载
            │ • SQLite 后端
            │ • UUID 寻址
            │ • LRU cache
            │ • 性能测试（100K 消息）
```

### 11.2 里程碑

| 里程碑 | 日期 | 验收标准 |
|--------|------|---------|
| **M1: Phase 1 完成** | Week 3 结束 | TranscriptStore 默认启用，REPL `:transcript` 可工作 |
| **M2: Phase 2 完成** | Week 5 结束 | 所有消息只写 TranscriptStore，删除双写逻辑 |
| **M3: Phase 3 完成** | Week 8 结束 | 非破坏性压缩，可逆压缩可工作 |
| **M4: Phase 4 完成** | Week 10 结束 | SQLite 后端，100K 消息内存 <100MB |
| **M5: 正式发布** | Week 12 | Helen v1.16 发布，包含 TranscriptStore SSOT 架构 |

### 11.3 依赖关系

```
Phase 1 ─────> Phase 2 ─────> Phase 3 ─────> Phase 4
(启用+持久化)   (SSOT 切换)    (非破坏压缩)    (内存卸载)
     │              │              │              │
     └──────────────┴──────────────┴──────────────┘
                    每个阶段可独立交付和回滚
```

---

## 12. 附录

### 12.1 术语表

| 术语 | 定义 |
|------|------|
| **SSOT** | Single Source of Truth，唯一真实来源 |
| **TranscriptStore** | Helen 的 append-only 对话历史存储 |
| **BoundaryMarker** | 压缩边界标记，记录压缩事件 |
| **read_view()** | 从 TranscriptStore 重建压缩后的有效消息列表 |
| **JSONL** | JSON Lines，每行一个 JSON 对象的文本格式 |
| **WAL** | Write-Ahead Logging，SQLite 的写入模式 |
| **LRU** | Least Recently Used，缓存淘汰策略 |

### 12.2 参考资料

- [Event Sourcing Pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing)
- [Helen Phase 10 设计文档](./project/helen/phase10_design.md)
- [Helen TranscriptStore 代码](./helen/runtime/transcript_store.py)
- [Helen AgentContext 代码](./helen/interpreter/agent_context.py)

### 12.3 变更日志

| 日期 | 版本 | 变更内容 | 作者 |
|------|------|---------|------|
| 2026-07-08 | v1.0 | 初始版本 | Helen Core Team |

---

**文档结束**
