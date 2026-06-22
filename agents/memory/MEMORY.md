# Helen Programming Agent — Memory

## 学习笔记

- Helen 语言支持 agent 块，包含 description、model、temperature、tools、prompt、functions、main 等属性
- agent 的 prompt 支持 {{variable}} 语法进行变量替换
- Helen 不支持闭包，需要用命名函数替代
- Helen 使用 || 和 && 而不是 or 和 and
- Helen 的字符串切片使用 substring() 方法而不是 [start:end] 语法

## 用户偏好

- 编码风格：函数式优先
- 测试框架：test_suite/test_case API
- 质量要求：7 维评分 ≥ 7.5
- Git 工作流：commit + push 一步完成

## 环境信息

- 系统：Linux (1.8GB RAM)
- Python: 3.11.15
- Helen 仓库: ~/helen/ (master 分支)
- 测试分批运行以避免 OOM

## Helen 语言限制（待改进）

1. 字符串切片语法不够直观（使用 substring() 而不是 [start:end]）
2. 逻辑运算符使用 || 和 && 而不是 or 和 and（虽然更明确，但与 Python 不一致）
3. 缺少泛型支持（v1.8 已取消）

**注意**: Helen 已支持闭包和匿名函数（v1.7+），语法为 `fn(params) { body }`
