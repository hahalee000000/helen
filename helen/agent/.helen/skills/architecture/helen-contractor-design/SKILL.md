---
name: helen-contractor-design
description: Helen 契约设计方法论 — 接口最小化、类型安全、可测试性、设计决策记录
version: 1.0.0
tags: [architecture, design, protocol, contract, interface]
---

# Helen 契约设计方法论

## 核心原则

1. **接口最小化**：只暴露必要的方法；私有实现细节不暴露
   - 每个 public 方法必须回答："调用者真的需要这个吗？"
   - 内部辅助函数不要放入 Protocol
2. **类型安全**：禁止 `any`，所有参数和返回值必须有明确类型
   - `str` / `int` / `float` / `bool` / `list` / `map` — 基本类型
   - 自定义 protocol 作为复杂类型
   - 不允许模糊类型（如"返回一个东西"）
3. **可测试性**：每个 public 方法的输入/输出必须可断言
   - 输入：明确的参数类型和约束
   - 输出：确定的返回类型，无副作用（或副作用在 docstring 中声明）
4. **组合优于继承**：优先用小 Protocol 组合，不用大 Protocol 继承
   - Helen 没有继承，但可以在一个文件中定义多个小 Protocol

## 设计流程

1. **读已有 contract**：先调用 `read_existing_contracts()` 了解已设计的接口，避免重复
2. **读源码**：调用 `read_source_files()` 了解项目结构和已有实现
3. **从 requirement 提取核心概念**：识别名词（实体）和动词（行为）
4. **为每个概念设计最小 Protocol**：
   - 每个 Protocol 只描述一个内聚的职责
   - 方法签名 = 参数列表 + 返回类型 + 行为契约（docstring）
5. **自审清单**：
   - [ ] 每个方法是否有明确类型？（无 `any`）
   - [ ] 每个方法是否可测试？（输入/输出可断言）
   - [ ] 是否最小化？（有无可以去掉的方法？）
   - [ ] 是否考虑了错误情况？（返回码 / 异常）

## 设计决策记录

每个设计决策在 contract 注释中写 "why"，不只是 "what"：

```helen
// DECISION: 使用 Result<T, E> 模式而非 throw 是因为...
// DECISION: 将 Cache 独立为 Protocol 而非嵌入 Service 是因为...
// DECISION: 使用 list<str> 而非单字符串是因为...
```

## Protocol 语法参考

Helen Protocol 定义（从 `load_skill("helen-syntax")` 获取完整语法）：

```helen
protocol ServiceContract {
    fn method_name(param: type, ...): return_type
    fn another_method(param: type): return_type
}
```

- Protocol 只声明方法签名，不实现
- `impl` 块实现 Protocol
- Protocol 方法不能有默认实现

## 输出格式

返回 JSON：
```json
{
  "status": "success",
  "contract": "<完整契约代码>",
  "modules": ["模块1", "模块2"],
  "file_path": "<契约文件路径>"
}
```

## 常见错误

- ❌ 把实现细节放入接口（如内部数据结构）
- ❌ 使用 `any` 类型
- ❌ 方法签名不包含错误处理
- ❌ 一个 Protocol 承担多个职责（违反单一职责）
- ❌ 没有写设计决策注释
