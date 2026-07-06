# Helen 语言 Wiki 索引

> **Helen** — A Prompt-first Agent Programming Language
> 版本: v1.10 | 状态: Phase 0-10 全部实现 + 中文语法 + Agent 作用域隔离 | 测试: 1500+ passed

---

## 📖 快速导航

### 一、语言概述
- [[overview/design-philosophy|设计哲学]] — 为什么需要 Agent 编程语言
- [[overview/language-spec|语言规格]] — 90 关键字 (45 英文 + 45 中文)、Token、AST 节点一览
- [[overview/architecture|整体架构]] — 3 层架构 (Core / Runtime / Toolchain)

### 二、前端编译
- [[syntax/lexical|词法分析]] — 89 Token 类型、Maximal Munch、三引号字符串、CJK 字符集
- [[syntax/grammar|语法规范]] — EBNF 完整语法、Pratt Parsing 10 级优先级
- [[syntax/keywords|关键字参考]] — 89 关键字分类与用法（含中文关键字映射表）

### 三、中间表示与语义
- [[compiler/ast|AST 节点定义]] — 49 节点类、Visitor 模式 (46 方法)
- [[compiler/semantic|语义分析]] — 符号表、作用域、类型检查
- [[compiler/types|类型系统]] — 14 种类型、渐进式类型检查

### 四、解释执行
- [[interpreter/execution|执行引擎]] — AST 遍历解释器、Environment 作用域链
- [[interpreter/llm-integration|LLM 集成]] — `llm act/if/choose`、对话历史
- [[interpreter/async|异步与并发]] — `async call`、`await`、Promise.all

### 五、运行时系统
- [[runtime/llm-runtime|LLM 运行时]] — route/choose/act 接口、取消机制
- [[runtime/prompt-builder|提示词构建]] — 两层渐进式披露、模板渲染
- [[runtime/memory|内存系统]] — FileMemoryProvider、InMemoryProvider
- [[runtime/history|历史管理]] — Token 预算、截断策略、conversation_summary
- [[runtime/import|模块系统]] — 多格式导入、循环检测、路径安全
- [[runtime/skills|技能系统]] — 三层搜索架构、两层披露机制

### 六、工具链
- [[toolchain/cli|命令行工具]] — `helen <file>/check/test/quality/repl/doc/init/lsp`
- [[toolchain/testing|测试框架]] — TDD 支持、断言 API、`--watch` 监听
- [[toolchain/quality|质量评估]] — 7 维框架、安全评分、CI 集成
- [[toolchain/lsp|语言服务器]] — `helen lsp`、JSON-RPC 2.0、诊断/补全/跳转
- [[toolchain/vscode|VS Code 扩展]] — 语法高亮、LSP 集成、代码补全、跳转定义
- [[toolchain/stdlib|标准库]] — 195 builtins (230+ 中文别名) (core/string/data/collection/network/time/math/file/system/crypto/io/test/quality)
- [[toolchain/error-format|错误格式化]] — HLD 3.11.2 诊断输出

### 七、教程
- [[tutorial/01-getting-started|入门指南]] — 安装、配置、Hello World、REPL
- [[tutorial/02-variables-and-types|变量与类型]] — let/const、类型注解
- [[tutorial/03-functions|函数]] — fn 声明、参数、返回值
- [[tutorial/04-control-flow|控制流]] — if/for/while/match/try-catch
- [[tutorial/05-agents|Agent 编程]] — agent 声明、description、prompt
- [[tutorial/06-llm-statements|LLM 语句]] — act/if/choose 实战
- [[tutorial/07-async-await|异步编程]] — async call、await、错误聚合
- [[tutorial/08-modules|模块与导入]] — import、跨文件复用
- [[tutorial/09-python-ffi|Python FFI]] — Python 库导入、类型转换
- [[tutorial/10-stdlib|标准库参考]] — 195 个内置函数（230+ 中文别名）
- [[tutorial/11-building-agents|构建多 Agent 系统]] — 完整案例
- [[tutorial/13-skills|技能系统]] — 三层搜索、两层披露、LLM 感知
- [[tutorial/14-observability|AI 原生可观测性]] — assert、debug()、trace、LLM 审计
- [[tutorial/15-python-bridge|Python Bridge]] — 让 Python 直接使用 Helen Agent

### 八、附录
- [[appendix/error-codes|错误码参考]] — 42 ErrorCode 完整列表
- [[appendix/exceptions|异常层次]] — 异常类继承树
- [[appendix/changelog|版本历史]] — Phase 0-10 变更记录
- [[appendix/hld-compliance|HLD 合规]] — 17 模块实现状态
