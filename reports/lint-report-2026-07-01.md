# Helen Wiki Lint Report

**日期**: 2026-07-01  
**Wiki 版本**: v1.9  
**实际代码版本**: v1.10+ (根据 CLAUDE.md)

---

## 🚨 需要更新的内容

### 1. 版本信息不一致

**Wiki 显示**:
- 版本: v1.9
- 关键字: 89 (45 英文 + 44 中文)
- Token 类型: 78
- AST 节点: 50
- Visitor 方法: 47

**实际代码**:
- 版本: v1.10+ (CLAUDE.md 显示)
- 关键字: 88 (44 英文 + 44 中文)
- Token 类型: 83
- AST 节点: 63
- Visitor 方法: 58

**影响文件**:
- `wiki/index.md` - 版本信息
- `wiki/overview/language-spec.md` - 详细规格
- 所有教程文件中的版本引用

### 2. 关键字变化

**v1.10 新增**:
- `shared` / `共享` - 跨 agent 可见变量（v1.10）

**Wiki 缺失**:
- 需要添加 `shared` 关键字的文档
- 需要更新关键字计数（44 英文 + 44 中文 = 88 总计）

**影响文件**:
- `wiki/syntax/keywords.md`
- `wiki/overview/language-spec.md`
- `wiki/tutorial/*.md` - 相关教程

### 3. Agent 作用域隔离 (v1.10)

**新增特性**:
- `agent main {}` 在完全隔离的环境中运行
- 模块级 `let` 在 agent main 中**不可见**（编译时错误）
- 模块级 `const` 自动可见（只读共享）
- 使用 `shared let` 进行跨 agent 可见的可变变量
- Agent main 中的闭包可以捕获局部变量

**Wiki 缺失**:
- 没有关于 agent 作用域隔离的专门文档
- 教程中没有说明 `shared let` 的用法

**影响文件**:
- `wiki/tutorial/05-agents.md` - 需要添加作用域隔离章节
- `wiki/interpreter/execution.md` - 需要说明环境链变化
- `wiki/runtime/memory.md` - 需要说明内存可见性

### 4. 子脚本/字段赋值 (v1.10)

**新增特性**:
- `arr[i] = x` - 数组索引赋值
- `obj.field = x` - 对象字段赋值

**Wiki 缺失**:
- 语法规范中没有说明这些新的赋值目标
- 教程中没有示例

**影响文件**:
- `wiki/syntax/grammar.md` - 需要更新赋值语句语法
- `wiki/tutorial/02-variables-and-types.md` - 需要添加示例

### 5. 短路求值 (v1.10)

**新增特性**:
- `&&` 和 `||` 短路求值

**Wiki 缺失**:
- 控制流文档中没有说明短路行为
- 运算符优先级可能需要更新

**影响文件**:
- `wiki/tutorial/04-control-flow.md`
- `wiki/syntax/grammar.md`

### 6. 返回类型注解语法变化 (v1.10)

**变化**:
- 返回类型注解只使用 `:` 语法：`fn foo(): int {}`
- `->` 语法已移除

**Wiki 现状**:
- 需要检查是否还有 `->` 语法的引用

### 7. 异常处理增强 (v1.10)

**新增特性**:
- `RuntimeError` 现在包含包装的 stdlib Python 异常

**Wiki 缺失**:
- 异常层次文档需要更新
- 错误码参考需要添加新错误类型

**影响文件**:
- `wiki/appendix/exceptions.md`
- `wiki/appendix/error-codes.md`
- `wiki/interpreter/execution.md`

### 8. 异步 HTTP 支持 (v1.10)

**新增特性**:
- `act_async()` / `act_stream_async()` 通过 `httpx.AsyncClient`

**Wiki 缺失**:
- LLM 运行时文档需要添加异步方法
- 异步编程教程需要更新

**影响文件**:
- `wiki/runtime/llm-runtime.md`
- `wiki/tutorial/07-async-await.md`

### 9. 导入系统增强 (v1.10)

**新增特性**:
- 导入的 `shared let` 被正确跟踪

**Wiki 缺失**:
- 模块系统文档需要说明 shared let 的导入行为

**影响文件**:
- `wiki/runtime/import.md`
- `wiki/tutorial/08-modules.md`

### 10. 内置函数数量

**Wiki 显示**: 185 builtins  
**需要验证**: 实际 stdlib 函数数量

---

## 🔍 需要检查的文档

### 高优先级

1. **wiki/index.md**
   - 更新版本号
   - 检查所有链接

2. **wiki/overview/language-spec.md**
   - 更新关键字计数
   - 添加 `shared` 关键字
   - 更新 Token/AST 计数

3. **wiki/syntax/grammar.md**
   - 添加子脚本/字段赋值语法
   - 更新短路求值说明
   - 移除 `->` 返回类型语法

4. **wiki/tutorial/05-agents.md**
   - 添加 agent 作用域隔离章节
   - 说明 `shared let` 用法
   - 添加示例

### 中优先级

5. **wiki/interpreter/execution.md**
   - 更新环境链说明（agent 隔离）
   - 添加子脚本/字段赋值执行逻辑

6. **wiki/runtime/llm-runtime.md**
   - 添加异步方法文档

7. **wiki/tutorial/07-async-await.md**
   - 添加 HTTP 异步示例

8. **wiki/appendix/exceptions.md**
   - 更新异常层次

### 低优先级

9. **wiki/appendix/changelog.md**
   - 添加 v1.10 变更记录

10. **wiki/runtime/memory.md**
    - 说明 shared let 的内存可见性

---

## 📋 同步任务

### Wiki 更新

- [ ] 更新所有文件中的版本号 (v1.9 → v1.10)
- [ ] 添加 `shared` 关键字文档
- [ ] 更新关键字计数 (88 总计)
- [ ] 更新 Token 类型计数 (83)
- [ ] 更新 AST 节点计数 (63)
- [ ] 更新 Visitor 方法计数 (58)
- [ ] 添加 agent 作用域隔离文档
- [ ] 添加子脚本/字段赋值语法
- [ ] 添加短路求值说明
- [ ] 移除 `->` 返回类型语法引用
- [ ] 更新异常层次
- [ ] 添加异步 HTTP 方法文档

### docs/ 教程同步

- [ ] 更新 `docs/tutorial.md` 中的版本信息
- [ ] 添加 `shared let` 教程章节
- [ ] 添加 agent 作用域隔离示例
- [ ] 添加子脚本/字段赋值示例
- [ ] 更新异步编程章节（HTTP 异步）

### skills/ 同步

- [ ] 检查 `skills/` 中的技能文档是否反映新特性
- [ ] 更新 `hellen-consistency-checker` 技能的检查规则
- [ ] 确保技能模板包含新语法示例

---

## 🎯 建议的更新顺序

1. **Phase 1: 基础信息更新** (1-2 小时)
   - 更新版本号和计数
   - 添加 `shared` 关键字
   - 更新 language-spec.md

2. **Phase 2: 语法和语义更新** (2-3 小时)
   - 更新 grammar.md（赋值、短路）
   - 更新 keywords.md
   - 更新 semantic.md

3. **Phase 3: 运行时更新** (2-3 小时)
   - 更新 execution.md（agent 隔离）
   - 更新 llm-runtime.md（异步方法）
   - 更新 import.md（shared let）

4. **Phase 4: 教程更新** (3-4 小时)
   - 更新 tutorial/05-agents.md（作用域隔离）
   - 更新 tutorial/04-control-flow.md（短路）
   - 更新 tutorial/07-async-await.md（HTTP 异步）
   - 更新 tutorial/02-variables-and-types.md（子脚本赋值）

5. **Phase 5: 附录更新** (1-2 小时)
   - 更新 changelog.md
   - 更新 exceptions.md
   - 更新 error-codes.md

6. **Phase 6: docs/ 和 skills/ 同步** (2-3 小时)
   - 同步 docs/tutorial.md
   - 更新 skills/ 文档

**总计**: 11-17 小时工作量

---

## 📝 下一步行动

建议立即执行 **Phase 1**，更新最关键的版本信息和基础数据。然后按优先级逐步完成其他阶段。

需要我立即开始更新吗？还是您想先审查这个 lint 报告？
