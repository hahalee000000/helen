# Async Interpreter Implementation Plan

## 目标
实现真正的 Phase 1b：单线程 asyncio 并发执行，LLM 调用不阻塞线程。

## 核心挑战
解释器是同步 visitor 模式，async 是传染性的。要让 LLM 调用真正异步，需要整个调用链支持 async。

## 策略：渐进式异步化

### Phase 1: 契约定义（Contract）
定义 async visitor 接口，不改变现有同步代码。

### Phase 2: 测试驱动（TDD）
编写测试验证异步行为，所有测试先失败。

### Phase 3: 实现（Implementation）
逐步实现 async visitor，让测试通过。

---

## 详细计划

### 1. 契约层（Contract）

**文件：** `helen/interpreter/async_visitor.py`

```python
class AsyncVisitor(Visitor[object]):
    """Async version of Visitor that can return coroutines."""
    
    # 所有 visit_* 方法返回 Any | Coroutine[Any, Any, Any]
    # 具体实现可以选择同步或异步执行
```

**关键契约：**
- `visit_llm_act_stmt` 必须调用 `await self.llm_runtime.act_async()`
- `visit_llm_if_stmt` 必须调用 `await self.llm_runtime.route_async()`
- `_execute_stmts_async` 能执行 async 语句
- `Task.execute_async()` 直接执行 async 解释器，不用 `asyncio.to_thread()`

### 2. 测试层（Tests）

**文件：** `tests/interpreter/test_async_interpreter.py`

**测试用例：**
1. `test_llm_act_calls_async_version` - 验证 LLM 调用使用 act_async()
2. `test_concurrent_llm_calls` - 验证多个 LLM 调用真正并发
3. `test_async_environment_isolation` - 验证环境隔离
4. `test_async_error_propagation` - 验证错误正确传播
5. `test_mixed_sync_async_execution` - 验证同步和异步代码混合执行

### 3. 实现层（Implementation）

**步骤 3.1: 添加 AsyncInterpreter 类**
- 继承 Interpreter
- 重写 LLM 相关方法为 async
- 添加 `_execute_stmts_async()` 方法

**步骤 3.2: 修改 Task.execute_async()**
- 使用 AsyncInterpreter 执行
- 直接 await，不用 asyncio.to_thread()

**步骤 3.3: 修改 _await_tasks()**
- 纯 asyncio.gather()，无线程池
- 所有 task 在单线程中并发执行

### 4. 验证

**性能测试：**
- 3 个 LLM 调用（各 0.1s）应该在 ~0.1s 内完成（并发）
- 内存使用：不随 task 数量增长

**功能测试：**
- 所有现有测试通过（888 个）
- 新增 async 测试通过

---

## 风险与缓解

**风险 1: async 传染性**
- 问题：一旦某个方法变成 async，调用者也要 async
- 缓解：只在 LLM 调用路径上使用 async，其他代码保持同步

**风险 2: 环境隔离**
- 问题：多个协程共享解释器状态
- 缓解：每个 task 使用独立的 AsyncInterpreter 实例

**风险 3: 向后兼容**
- 问题：现有同步代码可能不兼容
- 缓解：AsyncInterpreter 继承 Interpreter，同步代码继续工作

---

## 时间估计

- Phase 1（契约）：30 分钟
- Phase 2（测试）：1 小时
- Phase 3（实现）：2-3 小时
- 验证和优化：1 小时

**总计：4-5 小时**

---

## 成功标准

1. ✅ LLM 调用使用 `act_async()`，不阻塞线程
2. ✅ 3 个并发 LLM 调用在 ~0.1s 内完成
3. ✅ 内存使用不随 task 数量增长
4. ✅ 所有 888 个现有测试通过
5. ✅ 新增 async 测试全部通过
