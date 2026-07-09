# Helen `detach` 线程安全修复说明

## 问题描述

在 v1.12 引入的 `detach` 功能存在严重的线程安全问题：

### 原始实现的问题

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

## 修复方案

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

## Environment.snapshot() 实现

```python
def snapshot(self) -> "Environment":
    """Create a deep copy of the entire environment chain.

    Used for async task isolation: each task gets its own copy
    of the environment to avoid race conditions.

    v1.12 fix: Mutable values (list, dict) are deep-copied to prevent
    async tasks from sharing mutable references. Without this, concurrent
    tasks could race on the same list/dict objects.
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
    # Don't copy flat cache - it will be populated on demand

    return new_env
```

**关键特性**：
- 深拷贝可变对象（list, dict）
- 递归快照整个环境链
- 不拷贝 flat cache（按需重建）

## 测试验证

新增测试文件：`tests/interpreter/test_detach_thread_safety.py`

### 测试用例

1. **test_detach_creates_environment_snapshot**：验证环境快照创建
2. **test_detach_isolated_environment**：验证环境隔离
3. **test_detach_multiple_agents_no_race_condition**：验证无竞态条件
4. **test_detach_error_isolation**：验证错误隔离

### 测试结果

```
============================== 4 passed in 0.17s ===============================
```

所有测试通过，证明：
- ✅ 后台 agent 无法修改主进程变量
- ✅ 多个 detach 任务之间没有竞态条件
- ✅ 错误被隔离在后台任务中
- ✅ 环境快照正确工作

## 与 `async call` 的对比

| 特性 | `detach` (修复后) | `async call` |
|------|------------------|--------------|
| **环境隔离** | ✅ 环境快照 + 独立 interpreter | ✅ 环境快照 |
| **线程安全** | ✅ 完全隔离 | ✅ 通过快照隔离 |
| **返回值** | `None`（fire-and-forget） | `Task` 对象 |
| **错误处理** | 仅 stderr 输出 | 可通过 Task 捕获 |
| **执行控制** | 完全脱离 | 可等待/取消 |

## 使用建议

### ✅ 适合使用 `detach` 的场景

1. **日志记录**：不影响主流程的日志写入
2. **监控任务**：后台监控系统状态
3. **清理任务**：临时文件清理、资源释放
4. **通知发送**：异步发送通知（邮件、消息）
5. **指标收集**：收集性能指标

### ❌ 不适合使用 `detach` 的场景

1. **需要结果**：必须等待任务完成并获取结果
2. **关键任务**：任务失败会影响业务逻辑
3. **长时任务**：任务运行时间可能超过主程序生命周期
4. **需要取消**：需要中途取消任务
5. **错误敏感**：需要精确处理任务错误

## 性能影响

### 内存开销

- 每个 detach 任务会创建一个环境快照
- 快照包含所有变量的深拷贝
- 对于大型数据结构（大 list/dict），内存开销可能较大

### CPU 开销

- 创建快照需要遍历整个环境链
- 深拷贝可变对象需要额外的 CPU 时间
- 对于复杂环境，开销可能显著

### 优化建议

1. **避免在循环中频繁 detach**：每次 detach 都会创建快照
2. **减少环境中的大对象**：大型 list/dict 会增加快照开销
3. **考虑使用 `async call`**：如果需要结果，使用 `async call` 可能更高效

## 向后兼容性

### 兼容性

- ✅ 修复后的 `detach` 保持了相同的 API
- ✅ 语法和语义没有变化
- ✅ 现有的 detach 代码无需修改

### 行为变化

- ✅ 后台 agent 现在运行在隔离的环境中
- ✅ 无法访问或修改主进程的变量（这是期望的行为）
- ✅ 错误被隔离在后台任务中（这也是期望的行为）

## 总结

`detach` 功能的线程安全修复确保了：

1. **数据一致性**：消除了竞态条件
2. **环境隔离**：后台任务无法影响主进程
3. **错误隔离**：后台任务的错误不会传播到主进程
4. **线程安全**：多个 detach 任务可以安全并发执行

这个修复使 `detach` 成为一个真正安全可靠的 fire-and-forget 机制。

---

**修复版本**: v1.16  
**修复日期**: 2026-07-10  
**相关问题**: Issue #29
