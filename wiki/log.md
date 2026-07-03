# Helen Wiki Log

> 本文件记录 wiki 的所有操作（ingest、query、lint），按时间倒序排列。

---

## [2026-07-03] update | 中文类型别名 + main 关键字变更

**操作**: 添加 `列表`/`映射` 类型别名，`主` 改为 `主函`
**执行时间**: 2026-07-03
**状态**: ✅ 完成

### 变更内容

1. **类型别名 (helen/semantic/type_utils.py)**
   - `list` → 现在也接受 `列表`
   - `map` → 现在也接受 `映射`

2. **关键字变更 (helen/core/tokens.py)**
   - `main` 的中文关键字从 `主` 改为 `主函`（避免歧义）

3. **文档更新**
   - `wiki/syntax/keywords.md` — 关键字映射表更新
   - `wiki/tutorial/01-getting-started.md` — 中文示例更新
   - `wiki/tutorial/02-variables-and-types.md` — 添加中文类型别名说明
   - `docs/tutorial.md` — 同步更新
   - `tests/lexer/test_chinese_keywords.py` — 测试更新
   - `tests/lexer/test_chinese_punctuation.py` — 测试更新

---

## [2026-07-01] update | Phase 6 docs/ 和 skills/ 同步

**操作**: 同步教程和技能文档  
**执行时间**: 2026-07-01  
**状态**: ✅ 完成

### 更新的文件

1. **docs/tutorial.md**
   - 更新版本信息: v1.9 → v1.10
   - 更新目录表格，添加 v1.10 特性说明
   - 添加 "v1.10 新特性总结" 完整章节（~400 行）：
     - shared let — 跨 agent 可见变量
     - Agent 作用域隔离
     - 子脚本/字段赋值
     - 短路求值
     - 返回类型注解语法变化
     - 异常处理增强
     - 异步 HTTP 支持
     - 导入跟踪
     - 新增错误码
     - 完整示例（并发数据处理系统）
     - 迁移指南（从 v1.9 到 v1.10）

2. **skills/software-development/helen-syntax/SKILL.md**
   - 更新关键字计数: 89 → 88
   - 添加 `shared` / `共享` 关键字到映射表
   - 添加中文示例：`共享 let counter = 0`
   - 添加 "v1.10 新特性" 完整章节：
     - shared let 语法和作用域规则
     - 子脚本/字段赋值
     - 短路求值
     - 返回类型注解语法
     - 异步 HTTP 方法
     - 新增错误码表格

### 关键更新

**docs/tutorial.md**:
- ✅ 版本信息更新
- ✅ 目录表格更新（添加 v1.10 说明）
- ✅ v1.10 新特性完整总结
- ✅ 完整示例代码
- ✅ 迁移指南

**skills/helen-syntax**:
- ✅ 关键字计数更新
- ✅ shared let 关键字
- ✅ v1.10 新特性章节

### 同步完成

所有 wiki 更新已同步到：
- ✅ docs/tutorial.md（主教程文件）
- ✅ skills/software-development/helen-syntax/SKILL.md（语法技能）

### 最终状态

**Wiki 更新完成**:
- Phase 1-5: wiki/ 目录完整更新（18 文件）
- Phase 6: docs/ 和 skills/ 同步完成

**v1.10 特性完整覆盖**:
- ✅ 9 个主要新特性
- ✅ 3 个新增错误码
- ✅ 完整示例和迁移指南
- ✅ 技能文档同步

---

## [2026-07-01] update | Phase 5 附录更新

**操作**: 更新附录文档  
**执行时间**: 2026-07-01  
**状态**: ✅ 完成

### 更新的文件

1. **wiki/appendix/exceptions.md**
   - 添加 "v1.10 异常增强" 完整章节：
     - RuntimeError 包装 stdlib 异常机制
     - Python 代码实现
     - 3 个示例（int 转换、文件操作、网络请求）
     - 异常层次更新（添加 ScopeViolationError）
     - v1.10 新增异常：ScopeViolationError
     - 异常处理最佳实践（3 条）
     - 错误消息改进说明

2. **wiki/appendix/error-codes.md**
   - 更新错误码总数：42 → 45
   - 更新 E0350 说明：添加 v1.10 更新说明
   - 添加 E0351: SHARED_NOT_MODULE_LEVEL
   - 添加 E0352: IMMUTABLE_ASSIGNMENT
   - 添加 "v1.10 新增错误码详解" 章节：
     - E0350 详细说明（触发条件、示例、错误消息、修正方法）
     - E0351 详细说明
     - E0352 详细说明
   - 更新错误码统计表格

### 关键更新

**异常增强**:
- ✅ RuntimeError 包装 stdlib 异常
- ✅ ScopeViolationError 新增
- ✅ 异常处理最佳实践
- ✅ 错误消息改进

**错误码**:
- ✅ E0350: SCOPE_VIOLATION（更新说明）
- ✅ E0351: SHARED_NOT_MODULE_LEVEL（新增）
- ✅ E0352: IMMUTABLE_ASSIGNMENT（新增）
- ✅ 错误码统计：45 个

### 下一步

- Phase 6: docs/ 和 skills/ 同步

---

## [2026-07-01] update | Phase 4 教程更新

**操作**: 更新教程文档  
**执行时间**: 2026-07-01  
**状态**: ✅ 完成

### 更新的文件

1. **wiki/tutorial/05-agents.md**
   - 添加 "v1.10 Agent 作用域隔离" 完整章节：
     - 可见性规则表格
     - 示例代码（正确和错误用法）
     - 为什么需要作用域隔离的说明
     - shared let 最佳实践（命名约定、线程安全、最小化共享）
     - 闭包捕获说明
   - 添加 "v1.10 shared let 完整示例" 章节：
     - 计数器示例
     - 配置共享示例
     - 状态聚合示例

2. **wiki/tutorial/04-control-flow.md**
   - 添加 "短路求值 (v1.10)" 章节：
     - && 短路逻辑和示例
     - || 短路逻辑和示例
     - 优先级说明
     - 实际示例（安全访问、缓存检查、权限检查）

3. **wiki/tutorial/07-async-await.md**
   - 添加 "v1.10 HTTP 异步方法" 完整章节：
     - 异步方法列表（act_async, act_stream_async）
     - 基本用法示例
     - 并发调用示例
     - 异步流式调用
     - 性能对比表格（同步 vs 异步）
     - 实际示例：批量处理
     - 错误处理
     - 与 async call 的区别说明

4. **wiki/tutorial/02-variables-and-types.md**
   - 添加 "子脚本/字段赋值 (v1.10)" 章节：
     - 数组索引赋值示例
     - 对象字段赋值示例
     - 嵌套访问示例
     - 错误示例（const 不可修改）
     - 实际示例（更新记录）

### 关键更新

**Agent 教程**:
- ✅ Agent 作用域隔离规则
- ✅ shared let 最佳实践
- ✅ 3 个完整示例

**控制流教程**:
- ✅ 短路求值逻辑
- ✅ 优先级说明
- ✅ 实际应用示例

**异步教程**:
- ✅ HTTP 异步方法
- ✅ 并发调用示例
- ✅ 性能数据（提升 86%）
- ✅ 错误处理

**变量教程**:
- ✅ 子脚本赋值
- ✅ 字段赋值
- ✅ 嵌套访问
- ✅ 错误处理

### 下一步

- Phase 5: 附录更新（exceptions.md, error-codes.md）
- Phase 6: docs/ 和 skills/ 同步

---

## [2026-07-01] update | Phase 3 运行时更新

**操作**: 更新运行时系统文档  
**执行时间**: 2026-07-01  
**状态**: ✅ 完成

### 更新的文件

1. **wiki/interpreter/execution.md**
   - 添加 "v1.10 Agent Main 作用域隔离" 章节：
     - 环境创建逻辑（Python 代码）
     - 可见性规则说明
     - 示例代码
   - 添加 "v1.10 子脚本/字段赋值执行" 章节：
     - 赋值执行逻辑（IndexNode, AccessNode）
     - Python 实现代码
     - 示例代码
   - 添加 "v1.10 短路求值" 章节：
     - && 和 || 短路逻辑（Python 代码）
     - 优先级说明
     - 示例代码

2. **wiki/runtime/llm-runtime.md**
   - 添加 "v1.10 异步 HTTP 支持" 完整章节：
     - 异步方法列表（act_async, act_stream_async）
     - httpx.AsyncClient 使用
     - 使用示例（Helen 代码）
     - 连接池管理
     - 性能对比表格
     - 错误处理

3. **wiki/runtime/import.md**
   - 添加 "v1.10 shared let 导入跟踪" 完整章节：
     - 导入行为说明
     - Python 实现代码
     - 完整示例（module_a.helen, module_b.helen）
     - 作用域规则表格
     - 循环导入处理
     - 错误处理

4. **wiki/runtime/memory.md**
   - 添加 "v1.10 shared let 内存可见性" 完整章节：
     - Environment 类扩展（shared dict）
     - Agent Main 环境创建逻辑
     - 内存模型图示
     - 持久化示例
     - 线程安全说明

### 关键更新

**执行引擎**:
1. Agent main 作用域隔离 — 环境创建、可见性规则
2. 子脚本/字段赋值 — IndexNode, AccessNode 赋值执行
3. 短路求值 — && 和 || 短路逻辑

**LLM 运行时**:
1. 异步方法 — act_async, act_stream_async
2. httpx.AsyncClient — 连接池、并发控制
3. 性能提升 — 10 次并发提升 86%

**模块系统**:
1. shared let 导入跟踪 — 跨模块可见
2. 作用域规则 — 导入行为、循环导入
3. 错误处理 — 未声明变量检测

**内存系统**:
1. Environment 扩展 — shared dict
2. 内存模型 — global vs agent main
3. 线程安全 — 锁机制

### 下一步

- Phase 4: 教程更新（tutorial/*.md）
- Phase 5: 附录更新（exceptions.md, error-codes.md）
- Phase 6: docs/ 和 skills/ 同步

---

## [2026-07-01] update | Phase 2 语法和语义更新

**操作**: 更新语法规范和语义分析文档  
**执行时间**: 2026-07-01  
**状态**: ✅ 完成

### 更新的文件

1. **wiki/syntax/grammar.md**
   - 更新 var_decl 语法：添加 `shared let` 支持
   - 更新 assignment 语法：支持子脚本/字段赋值
   - 添加 v1.10 语法更新章节：
     - 子脚本/字段赋值 (`arr[i] = x`, `obj.field = x`)
     - 短路求值 (`&&` 和 `||`)
     - 返回类型注解语法变化（移除 `->`，仅用 `:`）
   - 添加完整的 EBNF 更新说明

2. **wiki/compiler/semantic.md**
   - 添加 "v1.10 Agent 作用域隔离" 章节：
     - 可见性规则表格
     - 示例代码
     - 语义分析实现说明
   - 添加 "v1.10 shared let 语义" 章节：
     - 符号表处理
     - 导入跟踪
   - 更新规则验证表格，添加 3 条新规则：
     - E0350: 模块级 let 在 agent main 中不可见
     - E0351: shared let 必须在模块级声明
     - E0352: 子脚本赋值目标必须是可变的

### 关键更新

**语法更新**:
1. var_decl: `("let" | "const" | "shared" "let") IDENTIFIER ("=" expression)?`
2. assignment: `(call | IDENTIFIER) "=" assignment | pipe`
3. 返回类型: `fn_decl → "fn" IDENTIFIER "(" fn_params? ")" (":" type)? fn_body`

**语义更新**:
1. Agent 作用域隔离 — 模块级 let 不可见
2. shared let 语义 — 跨 agent 可见变量
3. 导入跟踪 — shared let 被正确跟踪
4. 新增错误码 — E0350, E0351, E0352

### 下一步

- Phase 3: 运行时更新（execution.md, llm-runtime.md, import.md）
- Phase 4: 教程更新（tutorial/*.md）

---

## [2026-07-01] update | Phase 1 基础信息更新

**操作**: 更新 wiki 基础信息和版本号  
**执行时间**: 2026-07-01  
**状态**: ✅ 完成

### 更新的文件

1. **wiki/index.md**
   - 版本号: v1.9 → v1.10
   - 状态说明: 添加 "Agent 作用域隔离"

2. **wiki/overview/language-spec.md**
   - 版本号: v1.9 → v1.10
   - 关键字计数: 89 → 88 (44 英文 + 44 中文)
   - Token 类型: 78 → 83
   - AST 节点: 50 → 63
   - Visitor 方法: 47 → 58
   - 添加 `shared` / `共享` 关键字到表格
   - 更新 Token 类型列表（添加 SHARED, PROTOCOL, IMPL, IS, WILDCARD）
   - 架构图数字更新
   - 添加 "v1.10 新特性" 完整章节（7 个新特性）

3. **wiki/syntax/keywords.md**
   - 版本号: v1.9 → v1.10
   - 关键字计数: 89 → 88
   - 添加 `shared` / `共享` 关键字到中文关键字表格
   - 添加 `shared` 关键字详细说明（包含作用域规则）
   - 添加中文示例：`共享 let counter = 0`

4. **wiki/appendix/changelog.md**
   - 版本号: v1.9 → v1.10
   - 添加 v1.10 变更记录（8 项改进）
   - 添加 Agent 作用域隔离规则说明
   - 添加完整代码示例

### 关键更新

**v1.10 新特性**:
1. `shared` / `共享` 关键字 — 跨 agent 可见变量
2. Agent 作用域隔离 — agent main 在隔离环境运行
3. 子脚本/字段赋值 — `arr[i] = x` 和 `obj.field = x`
4. 短路求值 — `&&` 和 `||`
5. 返回类型语法变化 — 移除 `->`，仅用 `:`
6. 异常处理增强 — RuntimeError 包装 stdlib 异常
7. 异步 HTTP — `act_async()` / `act_stream_async()`
8. 导入跟踪 — shared let 被正确跟踪

### 下一步

- Phase 2: 语法和语义更新（grammar.md, semantic.md）
- Phase 3: 运行时更新（execution.md, llm-runtime.md）
- Phase 4: 教程更新（tutorial/*.md）

---

## [2026-07-01] lint | 初始健康检查

**操作**: 对 wiki 进行全面健康检查  
**触发**: 用户要求使用 llm-wiki 技能维护 wiki，并同步更新 docs/ 和 skills/

### 发现的问题

1. **版本信息不一致**
   - Wiki 显示 v1.9，实际代码为 v1.10+
   - 关键字计数：89 → 88（44 英文 + 44 中文）
   - Token 类型：78 → 83
   - AST 节点：50 → 63
   - Visitor 方法：47 → 58

2. **v1.10 新特性未文档化**
   - `shared` / `共享` 关键字（跨 agent 可见变量）
   - Agent 作用域隔离（agent main 在隔离环境中运行）
   - 子脚本/字段赋值（`arr[i] = x`、`obj.field = x`）
   - 短路求值（`&&` 和 `||`）
   - 返回类型注解语法变化（移除 `->`，仅用 `:`）
   - RuntimeError 包装 stdlib 异常
   - 异步 HTTP 方法（`act_async()` / `act_stream_async()`）
   - 导入的 shared let 跟踪

3. **docs/ 和 skills/ 需要同步**
   - `docs/tutorial.md` 需要更新
   - `skills/` 中的技能文档需要检查

### 生成的报告

- 详细报告：`wiki/lint-report-2026-07-01.md`
- 建议更新顺序：6 个阶段，预计 11-17 小时

### 下一步

等待用户审查报告后，按优先级执行更新。

---

## [2026-07-01] init | Wiki 初始化

**操作**: 建立 wiki 维护流程  
**说明**: 用户要求使用 llm-wiki 技能维护 Helen 语言文档，包括：
- 维护 wiki/ 目录下的文档
- 同步更新 docs/ 教程
- 同步更新 skills/ 内置技能

建立了以下流程：
1. 定期执行 lint 检查
2. 当 Helen 语言更新时，同步更新 wiki、docs、skills
3. 使用 log.md 记录所有操作
