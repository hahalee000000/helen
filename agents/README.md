# Helen Programming Agent

一个用纯 Helen 语言编写的编程代理，支持 TDD 开发和 7 维质量评估。

## 架构

```
HelenProgrammer (主编排器)
├── CodeAnalyzer      — 代码分析（质量指标、安全检查）
├── TestRunner        — 测试运行（执行测试、分析失败）
├── CodeGenerator     — 代码生成（LLM 驱动）
└── QualityGate       — 质量门禁（阈值检查、改进建议）
```

## 工作流程

```
1. 分析当前状态 → CodeAnalyzer
2. 生成/修改代码 → CodeGenerator
3. 生成测试     → CodeGenerator
4. 运行测试     → TestRunner
5. 质量检查     → QualityGate
6. 迭代改进     → 循环 2-5（最多 5 次）
```

## 使用方法

### 基本用法

```bash
# 运行默认示例
helen agents/helen_programmer.helen

# 自定义任务和文件
helen agents/helen_programmer.helen --task "实现排序算法" --file "examples/sort.helen"
```

### 在 REPL 中使用

```helen
helen> import "agents/helen_programmer.helen"

helen> let result = HelenProgrammer(
    task="Create a string utility module",
    target_file="examples/string_utils.helen"
)

helen> print(result["quality"]["scores"]["grade"])
```

## Agent 详解

### CodeAnalyzer

分析 Helen 源代码的质量和安全性。

```helen
let analysis = CodeAnalyzer(
    source="fn add(a, b) { return a + b }",
    filename="test.helen"
)

// 返回:
// - analysis: 质量评分、安全问题的 map
// - report: 格式化的文本报告
// - insights: LLM 生成的改进建议
```

### TestRunner

运行 Helen 测试并分析结果。

```helen
let result = TestRunner(test_file="examples/test_calculator.helen")

// 返回:
// - results: 测试结果的 JSON
// - summary: 文本摘要
// - analysis: LLM 分析的失败原因
// - all_passed: 是否全部通过
```

### CodeGenerator

使用 LLM 生成或修改 Helen 代码。

```helen
let code = CodeGenerator(
    task="Implement binary search",
    context="Existing code: ..."
)

// LLM 生成符合 Helen 语法的代码
// 遵循 snake_case、docstring、函数长度 < 30 行等规范
```

### QualityGate

检查代码是否达到质量阈值。

```helen
let gate = QualityGate(
    file_path="examples/calculator.helen",
    threshold=7.5
)

// 返回:
// - status: "PASS" 或 "FAIL"
// - scores: 7 维评分
// - suggestions: 改进建议（如果 FAIL）
```

### HelenProgrammer

主编排器，协调所有子 Agent。

```helen
let result = HelenProgrammer(
    task="Create a calculator with add/subtract/multiply/divide",
    target_file="examples/calculator.helen"
)

// 执行流程:
// 1. 分析现有代码
// 2. 生成新代码
// 3. 生成测试
// 4. 运行测试
// 5. 质量检查
// 6. 迭代改进（最多 5 次）

// 返回:
// - file: 生成的代码文件
// - test_file: 生成的测试文件
// - quality: 最终质量评分
// - tests: 测试结果
// - iterations: 迭代次数
```

## 7 维质量评估

| 维度 | 权重 | 评估内容 |
|------|:----:|---------|
| 架构设计 | 20% | 函数长度、复杂度、嵌套深度 |
| 代码质量 | 15% | 注释率、函数平均长度 |
| 安全性 | 20% | 危险模式检测 |
| 测试覆盖 | 15% | 测试文件存在性 |
| 文档 | 10% | docstring 覆盖率 |
| 可维护性 | 10% | 长函数、高复杂度函数 |
| 工程规范 | 10% | 命名规范、文件大小 |

**评分等级**: S (9.0+) / A (7.5+) / B (6.0+) / C (4.0+) / D (<4.0)

## 配置

在 `helen_programmer.helen` 顶部修改常量：

```helen
const QUALITY_THRESHOLD = 7.5  // 质量阈值
const MAX_ITERATIONS = 5       // 最大迭代次数
```

## 示例输出

```
🚀 Helen Programmer starting...
   Task: Create a calculator module
   Target: examples/calculator.helen

📊 Phase 1: Analyzing current state...
   File does not exist, will create new.

🔨 Phase 2: Generating/modifying code...
   Code written to examples/calculator.helen

🧪 Phase 3: Generating tests...
   Tests written to examples/test_calculator.helen

▶ Phase 4: Running tests...
   Tests: 5/5 passed

🔍 Phase 5: Quality gate...
   Status: PASS
   Score: 8.2/10

============================================================
✅ SUCCESS! Code meets quality threshold.
============================================================
```

## 限制

1. **无闭包** — Helen 不支持闭包，Agent 间通信通过返回值
2. **无匿名函数** — 必须使用命名函数
3. **LLM 依赖** — 需要配置 LLM API（`~/.helen/config.yaml`）
4. **迭代上限** — 最多 5 次迭代，避免无限循环

## 扩展

可以添加新的 Agent 来扩展功能：

```helen
agent DocumentationGenerator(file: str) {
    description "Generate API documentation"
    prompt "Generate markdown documentation for..."
    main {
        // ...
    }
}

agent RefactorAgent(file: str, pattern: str) {
    description "Refactor code based on pattern"
    prompt "Apply refactoring pattern..."
    main {
        // ...
    }
}
```

## 相关文件

- `agents/helen_programmer.helen` — 主 Agent 实现
- `helen/stdlib/test.py` — 测试框架
- `helen/stdlib/quality.py` — 质量评估
- `docs/tutorial.md` — Helen 语言教程
