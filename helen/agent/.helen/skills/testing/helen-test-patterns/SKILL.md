---
name: helen-test-patterns
description: Helen 测试生成方法论 — 覆盖维度、命名约定、arrange-act-assert、独立性、覆盖率暴露死代码
version: 1.0.0
tags: [testing, patterns, coverage, tdd, dead-code-detection]
---

# Helen 测试生成方法论

## 核心原则

1. **覆盖维度全面**：每个函数至少覆盖以下 4 个维度：
   - **正常路径**：典型输入、预期输出
   - **边界条件**：空值、零值、最大值、空字符串、空列表
   - **错误处理**：无效输入、异常路径、错误码
   - **状态变化**：涉及状态修改的函数，测试修改前后状态
2. **测试独立性**：
   - 每个测试必须可以独立运行，不依赖其他测试的执行顺序
   - 每个测试自建 fixture（准备数据）和 teardown（清理数据）
   - 不使用全局状态（除非是 shared let 的显式测试）
3. **命名约定**：
   - 测试函数名以 `test_` 开头（英文）
   - 命名格式：`test_<function>_<scenario>` — 如 `test_sort_empty_list`、`test_divide_by_zero`
4. **结构约定**：Arrange-Act-Assert (AAA)
   ```helen
   fn test_sort_empty_list() {
       // Arrange
       let input = []
       // Act
       let result = sort(input)
       // Assert
       assert(result == [])
   }
   ```
5. **快速执行**：每个测试 < 1 秒；避免网络/文件 IO

## 测试框架参考

从 `load_skill("helen-testing")` 获取完整测试 API。基本结构：

```helen
fn test_example() {
    // Arrange
    let input = "hello"
    // Act
    let result = upper(input)
    // Assert
    assert(result == "HELLO")
}
```

## Helen 测试语法要点

- 测试函数以 `test_` 前缀命名
- 使用 `assert(condition)` 断言
- 测试文件路径：源码 `src/main.helen` → 测试 `tests/test_main.helen`
- 运行：`helen test tests/test_main.helen`
- 单测过滤：`helen test tests/test_main.helen --filter test_sort`

## 覆盖率分析暴露死代码（v4.3 完整性层 2）

**核心思想**：测试覆盖率分析不仅能检测测试充分性，还能暴露死代码。

### 规则

1. 生成测试后，审视源码中**未被任何测试直接或间接调用的函数/类**
2. 这些未被覆盖的符号是**疑似死代码**候选
3. 在返回的 JSON 中增加 `uncovered_symbols` 字段，列出疑似死代码

### 检查步骤

1. 列出源码中所有 public 函数/类定义
2. 列出所有测试中（直接或间接）调用的函数/类
3. 差集 = 未被覆盖的符号
4. 区分"library 公共 API"和"真正死代码"：
   - 如果符号在 main() / 入口点可达，不是死代码
   - 如果符号既无测试覆盖，也不在 main 可达路径上 → 疑似死代码
5. 死代码占比 > 5% → 在 JSON 输出中标记 `dead_code_warning: true`

### 输出格式

在 JSON 中增加：
```json
{
  "uncovered_symbols": ["unused_function", "DeadClass"],
  "dead_code_warning": true,
  "dead_code_ratio": "8%"
}
```

## 测试生成策略（按输入优先级）

1. **有契约** → 为契约中的每个函数生成测试
2. **有源码但无契约** → 为源码中的每个 public 函数生成测试
3. **只有需求** → 根据需求推断需要实现的功能并生成测试
4. **都没有** → 返回错误

## 输出格式

返回 JSON：
```json
{
  "status": "success",
  "test_code": "<完整测试代码>",
  "test_count": 5,
  "file_path": "<测试文件路径>",
  "uncovered_symbols": [],
  "dead_code_warning": false
}
```

## 常见错误

- ❌ 测试依赖执行顺序
- ❌ 一个测试覆盖多个不相关场景
- ❌ 断言太弱（只检查不抛异常，不检查具体值）
- ❌ 没有边界条件测试
- ❌ 测试文件路径不对（应放在 tests/ 目录）
