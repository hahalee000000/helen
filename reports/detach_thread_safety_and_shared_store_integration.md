# Helen `detach` 线程安全修复与 Shared Store 集成

## 版本历史

- **v1.16** (2026-07-10): 线程安全修复 — 环境快照 + 独立 interpreter
- **v1.17** (2026-07-10): Shared Store/Channel 集成 — detached agent 可访问共享状态

---

## 问题描述（v1.12 - v1.15）

### 原始实现的线程安全问题

```python
def visit_detach_stmt(self, node: DetachStmtNode) -> object:
    import threading

    def run_detached():
        try:
            node.call.accept(self)  # ❌ 共享同一个 interpreter 实例
        except Exception as e:
            print(f"[detach] Background task error: {e}", file=sys.stderr)

    thread = threading.Thread(target=run_detached, daemon=True)
    thread.start()
    return None
```

**问题**：
- ❌ 后台 agent 使用与主进程相同的 interpreter 实例
- ❌ 共享同一个 environment，没有隔离
- ❌ 存在竞态条件：多个线程可以同时读写同一个变量
- ❌ 没有环境快照，后台任务可以修改主进程的变量

### 危险场景示例

```helen
let counter = 0

agent IncrementCounter {
    main {
        counter = counter + 1  // 竞态条件！
    }
}

// 主进程
counter = 0
detach IncrementCounter()  // 后台线程访问 counter
detach IncrementCounter()  // 另一个后台线程也访问 counter
print(counter)  // 可能输出 0、1 或 2（不确定！）
```

---

## v1.16 修复方案：环境快照隔离

### 修复后的实现

```python
def visit_detach_stmt(self, node: DetachStmtNode) -> object:
    import threading
    import copy

    # ✅ 创建环境快照用于线程安全（防止竞态条件）
    env_snapshot = self.environment.snapshot()

    def run_detached():
        try:
            # ✅ 创建新的 interpreter 实例，使用快照环境
            detached_interpreter = Interpreter(
                errors=self.errors,
                llm_runtime=self.llm_runtime,
                import_resolver=self.import_resolver,
            )
            # ✅ 替换为新创建的环境快照
            detached_interpreter.environment = env_snapshot

            # ✅ 在隔离的 interpreter 中执行
            node.call.accept(detached_interpreter)
        except Exception as e:
            import sys
            print(f"[detach] Background task error: {e}", file=sys.stderr)

    thread = threading.Thread(target=run_detached, daemon=True)
    thread.start()
    return None
```

### 关键改进

1. **环境快照**：使用 `self.environment.snapshot()` 创建环境的深拷贝
2. **独立 Interpreter**：为每个 detach 任务创建新的 Interpreter 实例
3. **完全隔离**：后台 agent 运行在独立的环境中，无法访问或修改主进程的变量
4. **线程安全**：消除了竞态条件，保证数据一致性

### Environment.snapshot() 实现（v1.16）

```python
def snapshot(self) -> "Environment":
    """Create a deep copy of the entire environment chain.

    v1.12 fix: Mutable values (list, dict) are deep-copied to prevent
    async tasks from sharing mutable references.
    """
    import copy

    # First, snapshot the parent chain (if any)
    parent_snapshot = None
    if self.parent is not None:
        parent_snapshot = self.parent.snapshot()

    # Create a new environment with deep-copied store and consts
    new_env = Environment(parent=parent_snapshot)
    # Deep copy mutable values to prevent cross-task mutation
    new_store: dict = {}
    for key, value in self._store.items():
        if isinstance(value, (list, dict)):
            new_store[key] = copy.deepcopy(value)
        else:
            new_store[key] = value
    new_env._store = new_store
    new_env._consts = copy.copy(self._consts)

    return new_env
```

**关键特性**：
- 深拷贝可变对象（list, dict）
- 递归快照整个环境链
- 不拷贝 flat cache（按需重建）

### v1.16 测试结果

```
============================== 4 passed in 0.17s ===============================
```

所有测试通过，证明：
- ✅ 后台 agent 无法修改主进程变量
- ✅ 多个 detach 任务之间没有竞态条件
- ✅ 错误被隔离在后台任务中
- ✅ 环境快照正确工作

---

## v1.17 增强：Shared Store/Channel 集成

### 问题：完全隔离导致共享状态不可用

v1.16 的修复虽然解决了线程安全问题，但带来了一个副作用：**detached agent 无法访问 shared store 和 channel**。

原因：`Environment.snapshot()` 会深拷贝所有变量，包括 `SharedStore` 实例。这导致 detached agent 拿到的是副本而非引用，无法更新主线程的共享状态。

```helen
shared store Counter {
    let count: int = 0
    fn increment() { count = count + 1 }
}

// v1.16 的问题
detach Counter.increment()  // ❌ 修改的是快照副本，主线程看不到
```

### v1.17 解决方案：SharedStore 保持引用

修改 `Environment.snapshot()` 方法，让 `SharedStore` 实例**不被深拷贝**，而是保持引用。

```python
def snapshot(self) -> "Environment":
    """Create a deep copy of the entire environment chain.

    v1.17 fix: SharedStore instances (shared store/channel) are NOT deep-copied.
    They maintain reference semantics to allow detached agents to access and
    update shared state. Thread safety is guaranteed by SharedStore's internal
    RLock mechanism.
    """
    import copy
    # Import here to avoid circular dependency
    from helen.interpreter.interpreter import SharedStore

    # First, snapshot the parent chain (if any)
    parent_snapshot = None
    if self.parent is not None:
        parent_snapshot = self.parent.snapshot()

    # Create a new environment with deep-copied store and consts
    new_env = Environment(parent=parent_snapshot)
    new_store: dict = {}
    for key, value in self._store.items():
        if isinstance(value, SharedStore):
            # ✅ SharedStore 保持引用（线程安全设计）
            new_store[key] = value
        elif isinstance(value, (list, dict)):
            new_store[key] = copy.deepcopy(value)
        else:
            new_store[key] = value
    new_env._store = new_store
    new_env._consts = copy.copy(self._consts)

    return new_env
```

**关键改进**：
- ✅ `SharedStore` 实例保持引用（不被深拷贝）
- ✅ 普通变量（list, dict）仍然深拷贝（保证隔离）
- ✅ 线程安全由 `SharedStore` 内部的 `RLock` 保证

### v1.17 功能验证

```helen
shared store Counter {
    let count: int = 0
    fn increment() { count = count + 1 }
}

// v1.17: detached agent 可以访问和更新 shared store
detach Counter.increment()
detach Counter.increment()
detach Counter.increment()

sleep(100)  // 等待后台任务
print(Counter.count)  // ✅ 输出: 3（主线程可见）
```

### v1.17 测试结果

```
============================== 6 passed in 1.49s ===============================
```

新增测试文件：`tests/interpreter/test_detach_shared_store.py`

测试用例：
1. ✅ `test_detach_can_update_shared_store`: detached agent 能更新 shared store
2. ✅ `test_detach_can_call_shared_store_methods`: detached agent 能调用 shared store 方法
3. ✅ `test_multiple_detaches_share_same_store`: 多个 detached 操作共享同一个 store
4. ✅ `test_detach_can_access_channel`: detached agent 能访问 channel
5. ✅ `test_channel_thread_safety`: channel 操作线程安全（10 次并发更新）
6. ✅ `test_regular_variables_still_isolated`: 普通变量仍然隔离

---

## 线程安全机制

### SharedStore 的 RLock 保护

```python
class SharedStore:
    def __init__(self, name: str, fields: dict[str, object], methods: dict[str, object]):
        object.__setattr__(self, '_name', name)
        object.__setattr__(self, '_fields', dict(fields))
        object.__setattr__(self, '_methods', dict(methods))
        object.__setattr__(self, '_lock', threading.RLock())  # ✅ 可重入锁

    def __setattr__(self, name: str, value: object) -> None:
        # ...
        if name in fields:
            lock = object.__getattribute__(self, '_lock')
            with lock:  # ✅ 所有字段访问在锁内
                fields[name] = value
            return
```

**保证**：
- ✅ 多个 detached agent 并发调用方法时，自动序列化执行
- ✅ 主线程和 detached agent 可以同时安全访问同一个 SharedStore
- ✅ 无竞态条件，数据一致性得到保证

### 并发访问示例

```helen
channel TaskQueue {
    let tasks: list = []
    
    fn add(task: str) {
        tasks.append(task)  // ✅ 自动加锁
    }
    
    fn count(): int {
        return len(tasks)  // ✅ 自动加锁
    }
}

// 10 个 detached agent 并发更新
for (let i = 0; i < 10; i = i + 1) {
    detach TaskQueue.add("task-" + str(i))
}

sleep(200)
print(TaskQueue.count())  // ✅ 输出: 10（无竞态条件）
```

---

## 使用建议

### ✅ 适合使用 `detach` 的场景

1. **日志记录**：不影响主流程的日志写入
2. **监控任务**：后台监控系统状态
3. **清理任务**：临时文件清理、资源释放
4. **通知发送**：异步发送通知（邮件、消息）
5. **指标收集**：收集性能指标
6. **共享状态更新**：更新 shared store/channel（v1.17+）

### ❌ 不适合使用 `detach` 的场景

1. **需要结果**：必须等待任务完成并获取结果 → 用 `async call` + `await`
2. **关键任务**：任务失败会影响业务逻辑 → 用 `async call` + `try-catch`
3. **长时任务**：任务运行时间可能超过主程序生命周期
4. **需要取消**：需要中途取消任务 → 用 `async call` + `Task.cancel()`
5. **错误敏感**：需要精确处理任务错误 → 用 `async call` + `Task.exception`

### 最佳实践（v1.17+）

```helen
// ✅ 好：使用 shared store 进行后台状态更新
shared store Metrics {
    let requestCount: int = 0
    fn increment() { requestCount = requestCount + 1 }
}

agent RequestHandler(request: str) {
    main {
        // 处理请求...
        detach Metrics.increment()  // 后台更新指标
        return "OK"
    }
}

// ✅ 好：使用 channel 进行异步消息传递
channel EventLog {
    let events: list = []
    fn log(event: str) { events.append(event) }
}

detach EventLog.log("user-login")
detach EventLog.log("data-processed")

// ✅ 好：结合 async/await 和 detach
shared store TaskCounter {
    let completed: int = 0
    fn increment() { completed = completed + 1 }
}

// 并发执行，后台更新计数器
let task1 = async Worker("task-1")
let task2 = async Worker("task-2")
detach TaskCounter.increment()  // 后台更新

await [task1, task2]
```

---

## 性能影响

### 内存开销

- 每个 detach 任务会创建一个环境快照
- 快照包含所有变量的深拷贝（除 SharedStore 外）
- SharedStore 保持引用，不会增加额外内存开销
- 对于大型数据结构（大 list/dict），内存开销可能较大

### CPU 开销

- 创建快照需要遍历整个环境链
- 深拷贝可变对象需要额外的 CPU 时间
- SharedStore 引用传递是 O(1) 操作

### 优化建议

1. **避免在循环中频繁 detach**：每次 detach 都会创建快照
2. **减少环境中的大对象**：大型 list/dict 会增加快照开销
3. **优先使用 shared store**：SharedStore 保持引用，不会增加快照开销
4. **考虑使用 `async call`**：如果需要结果，使用 `async call` 可能更高效

---

## 向后兼容性

### v1.16 兼容性

- ✅ 修复后的 `detach` 保持了相同的 API
- ✅ 语法和语义没有变化
- ✅ 现有的 detach 代码无需修改

### v1.17 兼容性

- ✅ SharedStore 保持引用是新增行为
- ✅ 现有代码不会受影响（之前 detached agent 无法访问 shared store）
- ✅ 新代码可以利用这个特性进行受控的跨线程通信

### 行为变化总结

| 版本 | 行为 |
|------|------|
| v1.12-v1.15 | ❌ 线程不安全（竞态条件） |
| v1.16 | ✅ 线程安全，但完全隔离（无法访问 shared store） |
| v1.17+ | ✅ 线程安全 + shared store 可访问（受控共享） |

---

## 总结

`detach` 功能的演进：

1. **v1.16**: 线程安全修复 — 环境快照 + 独立 interpreter
   - 消除了竞态条件
   - 后台任务完全隔离

2. **v1.17**: Shared Store/Channel 集成 — 受控的跨线程通信
   - SharedStore 保持引用（不被深拷贝）
   - Detached agent 可以访问和更新共享状态
   - 线程安全由 SharedStore 的 RLock 保证

**最终效果**：
- ✅ **数据一致性**：消除了竞态条件
- ✅ **环境隔离**：普通变量无法跨线程访问
- ✅ **受控共享**：SharedStore/Channel 提供安全的跨线程通信
- ✅ **错误隔离**：后台任务的错误不会传播到主进程
- ✅ **线程安全**：多个 detach 任务可以安全并发执行

这个演进使 `detach` 成为一个真正安全可靠的 fire-and-forget 机制，同时支持受控的跨线程通信。

---

**修复版本**: v1.16 (线程安全), v1.17 (shared store 集成)  
**修复日期**: 2026-07-10  
**相关问题**: Issue #29  
**测试文件**: `tests/interpreter/test_detach_thread_safety.py`, `tests/interpreter/test_detach_shared_store.py`
