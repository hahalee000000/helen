---
name: helen-code-integrity
description: Helen 代码完整性检查规则 — 作为 QualityGate Gate 1，跨文件扫描完整性/可达性/一致性
version: 1.0.0
tags: [code-quality, integrity, completeness, reachability, consistency, dead-code]
---

# Helen 代码完整性检查规则

> 作为 QualityGate 的第 1 道 gate（Gate 0 = 语法检查，Gate 1 = 本规则，Gate 2 = 7 维打分）。
> 任一检查 FAIL → 立即返回，所有维度 0 分，附带 issues 列表。

## 检查流程（按顺序执行，任一 FAIL 立即返回）

### Check 1: 完整性（Completeness）

扫描目标文件及所有直接相关模块：

**禁止项**：
- ❌ 残留 `TODO` / `FIXME` / `HACK` / `XXX` 注释
- ❌ 空函数体 — 函数体只有以下情况之一：
  - 只有 docstring（`// docstring: ...`）
  - 只有 `return null` / `return ""` / `return 0`（无逻辑占位）
  - 只有 `...`（Ellipsis 占位符）
  - 函数体为空
- ❌ 未赋值的变量声明（`let x` 后无 `= value`）
- ❌ `...`（Ellipsis）占位符

**要求**：
- ✅ 所有 public 函数（非 `_` 前缀）必须有实际实现
- ✅ 所有声明的 Protocol 方法在 impl 中有对应实现

**检测方法**：
1. 逐行扫描目标文件
2. 对每个 `fn` 声明，检查函数体是否包含实质代码
3. 对每个 `protocol` 声明，检查 `impl` 是否实现了所有方法
4. 正则匹配 `TODO|FIXME|HACK|XXX`（大小写不敏感）

### Check 2: 可达性（Reachability）

构建跨文件调用图，检测死代码：

**步骤**：
1. 列出目标文件 + 其 import 的所有模块中定义的函数/类
2. 从 `main {}` 入口点出发做可达性分析（BFS/DFS）
3. 标记所有未被任何可达路径调用的函数/类
4. 区分"死代码"和"library 公共 API"：
   - Library 项目（无 main 入口）：只标记完全无引用的符号
   - Application 项目（有 main 入口）：标记 main 不可达的符号

**阈值**：
- 死代码占比 > 5% → **FAIL**
- 死代码占比 ≤ 5% → **PASS（带 warning）**
- Library 项目阈值放宽到 10%

**注意**：
- 被 `load_skill` / `tools` 引用的函数名不算死代码
- 被 `protocol` 声明但 impl 实现的方法不算死代码
- 被 `export` / `@public` 注解标记的不算死代码（如果支持）

**检测方法**：
1. 解析所有 `fn` 声明，收集函数名集合
2. 从 main 入口出发，递归收集所有调用的函数名（包括 import 模块的函数）
3. 差集 = 死代码候选
4. 过滤掉 library API（如果项目没有 main 入口则标记为 library）

### Check 3: 一致性（Consistency）

跨模块对比，检测签名/常量冲突：

**检查项**：
1. **函数签名一致性**：
   - 函数定义处的参数名、参数类型、返回类型
   - 必须与所有调用处一致
   - 例如：`fn foo(x: int, y: str): bool` 定义 → 调用处必须传 int + str 两个参数
   
2. **常量一致性**：
   - 同名 const 在不同文件中必须值相同
   - 例如：`const MAX = 100` 在 A 文件 → `const MAX = 200` 在 B 文件 → FAIL

3. **Protocol 完整性**：
   - Protocol 声明的所有方法在 impl 中必须全部实现
   - 不能只实现部分方法

4. **Error code / 阈值一致性**：
   - contracts.helen 中定义的错误码/阈值
   - 使用处必须引用同一个 const，不能硬编码

**检测方法**：
1. 解析目标文件 + 其 import 模块
2. 收集所有函数签名，与调用点对比
3. 收集所有 const 声明，检查同名冲突
4. 对比 protocol 声明与 impl 实现

## 输出格式

```json
{
  "integrity_verdict": "PASS" | "FAIL",
  "issues": [
    {
      "type": "completeness",
      "file": "src/main.helen",
      "line": 42,
      "desc": "TODO comment found: TODO implement caching"
    },
    {
      "type": "completeness",
      "file": "src/main.helen",
      "line": 55,
      "desc": "Empty function body: fn process_data() has no implementation"
    },
    {
      "type": "reachability",
      "file": "src/utils.helen",
      "symbols": ["unused_helper", "dead_function"],
      "desc": "2 unreachable symbols (8% of total)"
    },
    {
      "type": "consistency",
      "file": "src/service.helen",
      "line": 10,
      "conflict_with": "contracts/contracts.helen:15",
      "desc": "Function signature mismatch: process(x: str) vs process(x: int)"
    },
    {
      "type": "consistency",
      "file": "src/config.helen",
      "line": 5,
      "conflict_with": "src/service.helen:3",
      "desc": "Constant MAX_RETRIES defined differently: 3 vs 5"
    }
  ]
}
```

## 扫描范围

- **目标文件**：QualityGate 评估的主文件
- **直接依赖**：目标文件 import 的所有模块
- **契约文件**：contracts/contracts.helen（如存在）
- **不做全项目分析**：避免性能问题

## 性能考虑

- 仅对目标文件 + 直接依赖做扫描（不做全项目分析）
- 扫描应在 < 1 秒内完成（纯文本分析，不构建 AST）
- 如果文件数 > 20，只扫描目标文件本身

## 与三层防御的关系

| 层次 | 位置 | 职责 |
|------|------|------|
| 层 1 | Implementer 自检（`helen-tdd-methodology`） | 单文件返回前自检 TODO/pass/空函数体 |
| 层 2 | TestBuilder 间接检测（`helen-test-patterns`） | 覆盖率分析暴露死代码 |
| **层 3** | **QualityGate Gate 1（本 skill）** | **跨文件完整性 + 可达性 + 一致性检查** |

三层互为补充：层 1 在生成时防止，层 2 在测试时暴露，层 3 在评审时拦截。
