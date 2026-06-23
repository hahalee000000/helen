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
- **原问题**：Helen 代码中写 `true`/`false`（小写），但 `print(true)` 输出 `True`（首字母大写）
- **修复**：`print()` 现在输出 `true`/`false`（小写），与 Helen 代码风格一致
- **状态**：已在 v1.8.1 修复

### 4. 字符串拼接冗长
- **问题**：没有字符串插值（string interpolation），只能 `+` 拼接
- **影响**：构建长字符串（如 SKILL.md 内容）时代码可读性差
- **建议**：支持 `"Hello {{name}}"` 模板语法或 `f"Hello {name}"` 语法

### 5. 无多行字符串的缩进处理
- **问题**：多行字符串 `"""..."""` 保留所有缩进空格
- **影响**：在 agent block 中写 prompt 时，缩进会混入内容
- **变通**：手动 trim 或不在缩进处写多行字符串

## Helen 语言特性（已验证支持）

### ✅ 闭包（Closures）
- **语法**：`fn(params) { body }` 创建匿名函数
- **特性**：捕获定义时的环境，可在后续调用中访问
- **应用**：`map(list, fn(x) { ... })`, `filter(list, fn(x) { ... })`

### ✅ 逻辑非操作符 `!`
- **语法**：`!expression`
- **示例**：`if !path_exists(file)`, `if !confirmed`
- **注意**：不是 `not`，而是 `!`
