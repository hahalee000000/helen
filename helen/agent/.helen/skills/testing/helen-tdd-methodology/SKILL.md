---
name: helen-tdd-methodology
description: Helen TDD 方法论 — red-green-refactor 循环、迭代策略、测试不变性、返回前自检
version: 1.0.0
tags: [tdd, testing, implementation, red-green-refactor, self-check]
---

# Helen TDD 方法论

## 核心原则

1. **测试是验收标准**：测试定义"完成"的含义，测试文件一旦由 TestBuilder 生成就不可修改
2. **最小实现**：每次只写让当前测试通过的最小代码量
3. **测试不可变性**：永远不要为了让测试通过而修改测试文件
4. **每次变更都验证**：每次修改后运行 `helen check` + `helen test`

## RED-GREEN-REFACTOR 循环

### Phase 1: RED（确认测试失败）

对每个测试函数：
1. 调用 `run_single_test(test_file, test_name)` 确认 FAIL
2. 如果测试意外 PASS → 说明测试本身有问题（记录但不修改测试）

### Phase 2: GREEN（写最小实现）

1. 调用 `apply_patch(file_path, old_code, new_code)` 或 `write_file()` 写代码
2. 只写让当前测试通过的最少代码
3. 不要为"未来可能的需求"写代码

### Phase 3: VERIFY（验证）

1. 调用 `verify_after_change(file_path, test_file)` 检查：
   - `helen check` 语法通过
   - 所有测试 PASS
2. 如果 FAIL → 回到 GREEN，修复后重新验证
3. 最多重试 3 次；3 次失败 → 返回当前状态让调用者判断

### Phase 4: REFACTOR（重构）

所有测试通过后：
1. 审视代码，消除重复
2. 改善命名
3. 提取公共逻辑
4. **重构后必须重新验证测试全部 PASS**

## 迭代策略

- 最多 15 轮（max-turns=15），每轮处理 1 个测试或重构步骤
- 每轮迭代的目标：要么新增 PASS 测试，要么重构现有代码
- 如果连续 3 轮没有进展 → 返回当前状态 + 诊断信息

## Helen 语法要点（从 helen-syntax / helen-stdlib 技能获取完整参考）

易错点特别提示：
- 入口点：`main { }`（不是 `fn main()`）
- 返回类型：`fn foo(): int { }`（不是 `-> int`）
- 异常捕获：`catch RuntimeError err { }`（不是 `catch ... as e`）
- 输入：`input("提示")`（不是 `_input` 或 `read_line`）
- 列表添加：`arr = arr + [item]`（没有 append）
- 逻辑运算符：`&&` `||` `!`（不是 `and`/`or`/`not`）
- 模式匹配：`match val { case pattern { } default { } }`

## 返回前自检规则（v4.3 完整性层 1）

**在返回实现结果前，必须对目标文件执行以下自检。自检失败 → 不返回，继续修复。**

### 自检清单

1. **禁止残留占位注释**：
   - 扫描文件中是否包含 `TODO` / `FIXME` / `HACK` / `XXX` 注释
   - 发现 → 移除或实现对应功能后再返回

2. **禁止空函数体**：
   - 检查每个 `fn` 声明 — 函数体不能只有：
     - 只有 docstring（`// docstring: ...`）没有实际代码
     - 只有 `return null` / `return ""` / `return 0`（无逻辑占位）
     - 只有 `...`（Ellipsis 占位符）
   - 空函数体 → 实现完整逻辑后再返回

3. **禁止未赋值的变量声明**：
   - 检查是否有 `let x` 没有后续赋值就使用
   - Helen 中 `let x = val` 必须立即初始化

4. **所有 public 函数必须有实际实现**：
   - 列出所有 `fn` 声明（非 `_` 前缀的内部函数）
   - 确认每个都有非空的实现体

### 自检流程

```
在准备返回 JSON 前：
1. read_file(source_path) 读取当前实现
2. 逐项检查上述 4 条规则
3. 若任何一条失败 → 继续修复，不返回
4. 全部通过 → 返回 {"status": "success", "implementation": ..., ...}
```

## 输出格式

返回 JSON：
```json
{
  "status": "success",
  "implementation": "<完整实现代码>",
  "tests_passed": true,
  "iterations": 3,
  "file_path": "<源文件路径>"
}
```

## 常见错误

- ❌ 修改测试文件让它通过
- ❌ 一次实现所有功能（违反"最小实现"原则）
- ❌ 不验证就返回（忘记运行 helen check / test）
- ❌ 返回含 TODO/pass 的代码
- ❌ 连续失败不汇报（应返回当前状态）
