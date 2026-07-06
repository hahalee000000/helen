---
name: helen-quality
description: "Helen 7 维质量评估使用指南 — 代码分析、安全评分、CI 集成"
version: 1.0.0
author: Helen Team
license: MIT
metadata:
  hermes:
    tags: [helen, quality, assessment, security, ci]
---

# Helen 质量评估

## 概述

Helen 内置 7 维质量评估框架，自动化分析 Helen 程序的质量。

## 快速开始

### CLI

```bash
helen quality my_program.helen
helen quality my_program.helen --json
helen quality my_program.helen --threshold 7.5
helen quality my_program.helen --dimension security
```

### 在代码中

```helen
let source = read_file("my_program.helen")
let scores = quality_score(source, "my_program.helen")
print("Grade: " + scores["grade"])
```

## 7 个维度

| 维度 | 权重 | 评估内容 |
|------|:----:|---------|
| 架构设计 | 20% | 函数长度、复杂度、嵌套、参数 |
| 代码质量 | 15% | 注释率、函数长度、复杂度 |
| 安全性 | 20% | 危险模式检测 |
| 测试覆盖 | 15% | 测试文件存在性 |
| 文档 | 10% | docstring 覆盖率 |
| 可维护性 | 10% | 长函数、高复杂度函数 |
| 工程规范 | 10% | 命名、文件大小 |

## 评分等级

| 等级 | 范围 |
|:----:|:----:|
| S | 9.0-10.0 |
| A | 7.5-8.9 |
| B | 6.0-7.4 |
| C | 4.0-5.9 |
| D | 0.0-3.9 |

## API

### `analyze_code(source, filename?)`

代码指标：
- `total_lines`, `code_lines`, `comment_lines`
- `function_count`, `agent_count`
- `avg_complexity`, `max_complexity`
- `functions[]`

### `check_security(source)`

安全问题：
- `line`, `severity`, `pattern`, `message`

### `quality_score(source, file_path?)`

7 维评分：
- `architecture`, `code_quality`, `security`
- `test_coverage`, `documentation`, `maintainability`, `engineering`
- `total`, `grade`

### `quality_report(source, filename?)`

格式化报告字符串。

## 安全检查

| 模式 | 严重度 |
|------|:------:|
| `eval()` | HIGH |
| `exec()` | HIGH |
| `shell=true` | HIGH |
| `import os` | MEDIUM |
| `import subprocess` | MEDIUM |
| `input()` | LOW |

## 测试覆盖评分详解

测试覆盖维度（权重 15%）基于文件位置启发式评分，按最高得分命中：

| 策略 | 得分 | 条件 |
|------|:----:|------|
| `// @test-location:` 注解 | **8.0** | 源文件中包含注解指向已有测试文件 |
| 同级测试文件 | **8.0** | 存在 `<name>_test.helen` 或 `test_<name>.helen` |
| 父级 `tests/` 匹配 | **7.0** | 父级 `tests/` 目录中有文件名包含源文件 stem 的 `*.py` |
| 同级 `tests/` 目录 | **6.0** | 源文件旁有 `tests/` 目录含任意测试文件 |
| 无测试 | **2.0** | 未找到任何测试 |

### `// @test-location:` 注解

Agent 密集型程序的集成测试通常放在独立的 `tests/` 目录，文件名与源文件 stem 不一定匹配，容易落入 6.0 上限。使用注解可以显式声明测试位置，直接得 8.0：

```helen
// @test-location: tests/integration/test_programmer.py

agent Programmer {
    description "代码编写助手"
    main {
        llm act "编写代码"
    }
}
```

注解路径支持绝对路径和相对路径（相对于源文件），文件必须实际存在。

## CI 集成

```bash
helen quality src/*.helen --threshold 7.0 --json > quality.json
```

## 相关文档

- [教程](../../docs/tutorial.md#质量评估)
- [Wiki](../../../wiki/helen/toolchain/quality.md)
- [示例](../../examples/quality_example.helen)
