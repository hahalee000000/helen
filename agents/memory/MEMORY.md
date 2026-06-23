# Helen Programming Agent — Memory

> Agent-level persistent memory. Updated automatically during interactions.

## 学习笔记

- Agent 初始化于 2026-06-23
- 技能系统采用 contract-first + TDD 模式实现
- 35 个 Python 测试覆盖所有契约函数

## 用户偏好

_待积累_

## 环境信息

- 系统：Linux (1.8GB RAM)
- Python: 3.11.15
- Helen 仓库: ~/helen/ (master 分支)

## Helen 语言不足（待改进）

_在开发过程中发现的 Helen 语言限制将记录在此。_

### ✅ 已修复：`join(sep, list)` 参数顺序
- **原问题**：separator 在前，list 在后。大多数语言是 `list.join(sep)`
- **修复**：改为 `join(list, sep)` — list 在前，separator 在后
- **状态**：已在 v1.8.1 修复

### ✅ 已修复：Regex 函数参数顺序不一致
- **原问题**：`regex_search(pattern, string)` 但 `regex_replace(string, pattern, replacement)` — 参数顺序不一致
- **修复**：统一所有 regex 函数为 pattern-first：
  - `regex_match(pattern, string)`
  - `regex_search(pattern, string)`
  - `regex_test(pattern, string)`
  - `regex_replace(pattern, string, replacement)`
  - `regex_split(pattern, string)`
  - `regex_findall(pattern, string)`
- **状态**：已在 v1.8.1 修复，与 Python `re` 模块一致

### ✅ 已修复：`True`/`False` 打印为 Python 风格
## Helen 语言不足（待改进）

_在开发过程中发现的 Helen 语言限制将记录在此。_

### ✅ 已修复：字符串插值
- **原问题**：没有字符串插值，长字符串拼接冗长
- **修复**：添加 `interpolate(template, vars)` 函数
- **示例**：
  ```helen
  let template = "Hello, {{name}}! You are {{age}} years old."
  let vars = {"name": "Alice", "age": 30}
  let result = interpolate(template, vars)
  // result = "Hello, Alice! You are 30 years old."
  ```
- **状态**：已在 v1.8.1 修复

### ✅ 已修复：多行字符串缩进处理
- **原问题**：三引号字符串保留所有缩进，影响代码可读性
- **修复**：自动去除公共前导空白（dedent）
- **示例**：
  ```helen
  let text = """
      Line 1
      Line 2
          Nested indentation preserved
  """
  // Result: "Line 1\nLine 2\n    Nested indentation preserved"
  ```
- **状态**：已在 v1.8.1 修复

## Helen 语言特性（已验证支持）

### ✅ 闭包（Closures）
- **语法**：`fn(params) { body }` 创建匿名函数
- **特性**：捕获定义时的环境，可在后续调用中访问
- **应用**：`map(list, fn(x) { ... })`, `filter(list, fn(x) { ... })`

### ✅ 逻辑非操作符 `!`
- **语法**：`!expression`
- **示例**：`if !path_exists(file)`, `if !confirmed`
- **注意**：不是 `not`，而是 `!`
