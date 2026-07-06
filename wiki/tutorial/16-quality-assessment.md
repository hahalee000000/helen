# 教程 16: 质量评估（7 维框架）

> Helen 内置 7 维质量评估框架，自动化质量分析

---

## 快速开始

### CLI 命令

```bash
# 基本评估
helen quality my_program.helen

# JSON 输出
helen quality my_program.helen --json

# 设置阈值（CI 集成）
helen quality my_program.helen --threshold 7.5

# 单维度评估
helen quality my_program.helen --dimension security
```

### 在 Helen 代码中使用

```helen
let source = read_file("my_program.helen")

// 获取代码指标
let metrics = analyze_code(source, "my_program.helen")
print("Functions: " + str(metrics["function_count"]))
print("Complexity: " + str(metrics["avg_complexity"]))

// 安全检查
let issues = check_security(source)
print("Security issues: " + str(len(issues)))

// 质量评分
let scores = quality_score(source, "my_program.helen")
print("Total score: " + str(scores["total"]))
print("Grade: " + scores["grade"])

// 完整报告
let report = quality_report(source, "my_program.helen")
print(report)
```

## 7 个维度

| 维度 | 权重 | 评估内容 |
|------|:----:|---------|
| **架构设计** | 20% | 函数长度、复杂度、嵌套深度、参数数量 |
| **代码质量** | 15% | 注释率、函数平均长度、平均复杂度 |
| **安全性** | 20% | 危险模式检测（eval、shell=True、未验证输入等） |
| **测试覆盖** | 15% | 测试文件存在性、测试/代码比 |
| **文档** | 10% | 函数 docstring 覆盖率 |
| **可维护性** | 10% | 长函数数量、高复杂度函数数量 |
| **工程规范** | 10% | 命名规范、文件大小 |

## 评分等级

| 等级 | 分数范围 | 含义 |
|:----:|:--------:|------|
| S | 9.0-10.0 | 生产就绪，exemplary |
| A | 7.5-8.9 | 良好，少量改进 |
| B | 6.0-7.4 | 可接受，需要改进 |
| C | 4.0-5.9 | 低于标准 |
| D | 0.0-3.9 | 不可接受 |

## 输出示例

```
============================================================
  HELEN QUALITY REPORT
============================================================
  File: calculator.helen

  Code Metrics:
    Total lines: 150
    Code lines: 120
    Comment lines: 25 (17%)
    Functions: 8
    Agents: 1
    Avg function length: 12.5 lines
    Max function length: 35 lines
    Avg complexity: 2.3
    Max complexity: 6

  Quality Scores (0-10):
    Architecture:      9.50 (20%)
    Code Quality:      8.00 (15%)
    Security:          10.00 (20%)
    Test Coverage:     6.00 (15%)
    Documentation:     7.50 (10%)
    Maintainability:   9.00 (10%)
    Engineering:       8.50 (10%)
    ─────────────────────────────
    TOTAL:             8.48
    GRADE:             A

  Recommendations:
    • Add test file for better coverage
    • Add docstrings to 2 undocumented functions

============================================================
```

## 安全检查

自动检测以下危险模式：

| 模式 | 严重度 | 说明 |
|------|:------:|------|
| `eval()` | HIGH | 可执行任意代码 |
| `exec()` | HIGH | 可执行任意代码 |
| `shell=true` | HIGH | 命令注入风险 |
| `import os` | MEDIUM | 系统资源访问 |
| `import subprocess` | MEDIUM | 命令执行 |
| `open(..., "w")` | MEDIUM | 无验证的文件写入 |
| `input()` | LOW | 用户输入需验证 |

## CI 集成

```bash
# 在 CI 中使用阈值
helen quality src/*.helen --threshold 7.0 --json > quality.json

# 检查是否达标
if [ $? -ne 0 ]; then
    echo "Quality threshold not met!"
    exit 1
fi
```

## API 参考

### `analyze_code(source, filename?)`

分析代码指标，返回：
- `total_lines`, `code_lines`, `comment_lines`, `blank_lines`
- `comment_ratio`, `function_count`, `agent_count`
- `avg_function_length`, `max_function_length`
- `avg_complexity`, `max_complexity`
- `functions[]` — 每个函数的详细信息

### `check_security(source)`

检查安全问题，返回问题列表：
- `line` — 行号
- `severity` — "high" / "medium" / "low"
- `pattern` — 匹配的模式
- `message` — 问题描述

### `quality_score(source, file_path?)`

计算 7 维评分，返回：
- `architecture`, `code_quality`, `security`
- `test_coverage`, `documentation`, `maintainability`, `engineering`
- `total` — 加权总分
- `grade` — 字母等级

### `quality_report(source, filename?)`

生成格式化的完整报告字符串。

## 练习

1. 对你写的 Helen 程序运行质量评估
2. 根据建议改进代码，提高评分
3. 在 CI 中设置质量阈值
4. 使用 `--dimension security` 专注安全改进
5. 对比改进前后的评分变化

---

> **相关文档**: [[toolchain/quality|质量评估工具参考]] | [[tutorial/12-testing|测试框架与 TDD]]
