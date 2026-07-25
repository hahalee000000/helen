# Skill Index (Auto-generated — 禁止手工编辑)

> 由 SkillEvaluator.refresh_skill_index() 维护。
> 最后更新: 2026-07-15

## 项目级技能（5 + 1）

| 类别 | 技能名称 | 描述 |
|------|---------|------|
| `architecture/` | `helen-contractor-design` | Helen 契约设计方法论 — 接口最小化、类型安全、可测试性、设计决策记录 |
| `testing/` | `helen-test-patterns` | Helen 测试生成方法论 — 覆盖维度、命名约定、arrange-act-assert、覆盖率暴露死代码 |
| `testing/` | `helen-tdd-methodology` | Helen TDD 方法论 — red-green-refactor 循环、迭代策略、返回前自检 |
| `code-quality/` | `helen-quality-rubrics` | Helen 7 维质量评分规则 — 每维 0-10 分评分细则、PASS/FAIL 判定 |
| `code-quality/` | `helen-code-integrity` | Helen 代码完整性检查规则 — 跨文件完整性/可达性/一致性（QualityGate Gate 1） |
| `agent-patterns/` | `multi-agent-orchestration` | 多 Agent 编排模式 — 多角色顺序讨论、历史累积、综合结论 |

## 使用方式

Agent 通过 `load_skill("skill-name")` 加载技能内容到 prompt 上下文：

```helen
// 在 agent prompt 中引导 LLM 加载技能
prompt """
## Domain Knowledge
- MANDATORY: load_skill("helen-tdd-methodology") — TDD 方法论
- MANDATORY: load_skill("helen-test-patterns") — 测试模式
"""
```

## 技能目录结构

```
.helen/skills/
├── SKILL_INDEX.md              ← 本文件（自动生成）
├── architecture/
│   └── helen-contractor-design/SKILL.md
├── testing/
│   ├── helen-test-patterns/SKILL.md
│   └── helen-tdd-methodology/SKILL.md
├── code-quality/
│   ├── helen-quality-rubrics/SKILL.md
│   └── helen-code-integrity/SKILL.md
└── agent-patterns/
    └── multi-agent-orchestration/SKILL.md
```

## 禁止事项

- ❌ 禁止手工编辑本文件
- ❌ 禁止修改 `~/.helen/skills/` 或 `~/helen/skills/`（Helen 内置技能目录）
- ✅ 项目级技能只能存放在 `.helen/skills/` 下
