# Helen Wiki Schema

> 本文件定义 Helen 语言 wiki 的结构、约定和维护流程。

---

## Wiki 结构

```
wiki/
├── index.md              # 内容索引（按类别组织）
├── log.md                # 操作日志（按时间倒序）
├── schema.md             # 本文件（wiki 约定）
├── lint-report-*.md      # Lint 报告（按需生成）
│
├── overview/             # 语言概述
│   ├── design-philosophy.md
│   ├── language-spec.md
│   └── architecture.md
│
├── syntax/               # 前端编译
│   ├── lexical.md        # 词法分析
│   ├── grammar.md        # 语法规范
│   └── keywords.md       # 关键字参考
│
├── compiler/             # 中间表示与语义
│   ├── ast.md            # AST 节点定义
│   ├── semantic.md       # 语义分析
│   └── types.md          # 类型系统
│
├── interpreter/          # 解释执行
│   ├── execution.md      # 执行引擎
│   ├── llm-integration.md # LLM 集成
│   └── spawn.md     # 并发与 spawn
│
├── runtime/              # 运行时系统
│   ├── llm-runtime.md    # LLM 运行时
│   ├── prompt-builder.md # 提示词构建
│   ├── memory.md         # 内存系统
│   ├── history.md        # 历史管理
│   ├── import.md         # 模块系统
│   └── skills.md         # 技能系统
│
├── toolchain/            # 工具链
│   ├── cli.md            # 命令行工具
│   ├── testing.md        # 测试框架
│   ├── quality.md        # 质量评估
│   ├── lsp.md            # 语言服务器
│   ├── vscode.md         # VS Code 扩展
│   ├── stdlib.md         # 标准库
│   └── error-format.md   # 错误格式化
│
├── tutorial/             # 教程（17 章）
│   ├── 01-getting-started.md
│   ├── 02-variables-and-types.md
│   ├── 03-functions.md
│   ├── 04-control-flow.md
│   ├── 05-agents.md
│   ├── 06-llm-statements.md
│   ├── 07-spawn.md
│   ├── 08-modules.md
│   ├── 09-python-ffi.md
│   ├── 10-stdlib.md
│   ├── 11-building-agents.md
│   ├── 12-testing.md
│   ├── 13-skills.md
│   ├── 14-observability.md
│   ├── 15-python-bridge.md
│   └── 16-quality-assessment.md
│
└── appendix/             # 附录
    ├── error-codes.md    # 错误码参考
    ├── exceptions.md     # 异常层次
    ├── changelog.md      # 版本历史
    └── hld-compliance.md # HLD 合规
```

---

## 页面约定

每个 wiki 页面应包含：

### YAML Frontmatter

```yaml
---
title: 页面标题
type: entity | concept | reference | tutorial | appendix
created: YYYY-MM-DD
updated: YYYY-MM-DD
version: v1.18
sources: []  # 贡献的源代码文件
---
```

### 正文结构

1. **标题和简介** - 一句话说明
2. **核心内容** - 分章节组织
3. **示例** - 代码示例（Helen 语法）
4. **相关页面** - Wikilinks 到相关概念

### Wikilinks

使用 `[[path/to/page]]` 或 `[[path/to/page|显示文本]]` 语法。

**常用链接**:
- `[[syntax/keywords]]` - 关键字参考
- `[[compiler/types]]` - 类型系统
- `[[runtime/llm-runtime]]` - LLM 运行时
- `[[tutorial/05-agents]]` - Agent 编程教程

---

## 维护流程

### 1. Lint（健康检查）

**触发条件**:
- 定期（建议每月一次）
- Helen 语言大版本更新后
- 发现文档不一致时

**检查项目**:
- 版本号一致性
- 关键字计数和列表
- Token/AST/Visitor 计数
- 新特性是否已文档化
- 跨页面引用是否正确
- 过时内容标记

**输出**:
- `lint-report-YYYY-MM-DD.md` - 详细报告
- 更新 `log.md` - 记录操作

### 2. Update（更新）

**触发条件**:
- Helen 语言代码变更
- Lint 报告发现问题
- 用户请求

**更新顺序**:
1. 基础信息（版本号、计数）
2. 语法和语义（关键字、语法规范）
3. 运行时（执行引擎、LLM 集成）
4. 教程（示例、说明）
5. 附录（错误码、异常、变更日志）
6. 同步 docs/ 和 skills/

**更新内容**:
- 修改相关 wiki 页面
- 更新 `index.md`（如有新页面）
- 更新 `log.md` - 记录操作

### 3. Ingest（摄入新内容）

**触发条件**:
- 添加新教程
- 添加新特性文档
- 添加新的参考材料

**流程**:
1. 读取新内容
2. 提取关键信息
3. 更新相关页面
4. 更新 `index.md`
5. 更新 `log.md`

### 4. Query（查询）

**触发条件**:
- 用户提问
- 需要综合分析

**流程**:
1. 读取 `index.md` 找到相关页面
2. 读取相关页面
3. 综合答案
4. 如有价值，可反馈为新页面

---

## 同步任务

### wiki/ → docs/（自动生成）

`docs/tutorial.md` 由 `scripts/build_tutorial.py` 从 `wiki/tutorial/*.md` 自动生成。

当教程内容变化时：
```bash
python3 scripts/build_tutorial.py
```

不要手动编辑 `docs/tutorial.md`——编辑 `wiki/tutorial/` 下的文件，然后重新生成。

### wiki/ → skills/

当 wiki 更新时，检查是否需要同步到 `skills/`：
- 语法变化影响技能模板
- 新特性需要在技能中体现
- `hellen-consistency-checker` 检查规则更新

### 代码 → wiki

当 Helen 代码更新时：
1. 检查 `helen/core/tokens.py` - 关键字变化
2. 检查 `helen/core/ast.py` - AST 节点变化
3. 检查 `helen/interpreter/` - 执行逻辑变化
4. 检查 `helen/runtime/` - 运行时变化
5. 检查 `helen/stdlib/` - 内置函数变化
6. 更新相关 wiki 页面

---

## 版本追踪

当前版本: **v1.18**

**版本历史**:
- v1.8: 函数式编程增强（管道操作符、模式匹配增强）
- v1.9: 中文关键字、基础 agent 支持
- v1.10: shared let、agent 作用域隔离、子脚本赋值、短路求值、异步 HTTP
- v1.12: 隔离装饰器、shared store/channel、ReadOnlyView
- v1.13: channel 通道、中文关键字补全
- v1.14: llm stream 合并到 llm act、流式回调
- v1.15: Phase 1-7 上下文管理（工作记忆、渐进压缩、缓存感知、三通道上下文）
- v1.16: TranscriptStore SSOT（SQLite/JSONL 后端、LRU 缓存、UUID 寻址）
- v1.17: 多模态格式适配器 stdlib
- v1.18: spawn 并发原语（替代 async/await/detach）、Channel 消息队列、snapshot 全部深复制

**需要追踪的特性**:
- 关键字列表（英文 + 中文）: 89 (44.5 + 44.5)
- Token 类型数量: 83
- AST 节点数量: 60
- Visitor 方法数量: 54
- 内置函数数量: 255（255 中文别名）
- 新特性列表（见 changelog.md）

---

## 质量标准

### 准确性

- 所有数据必须与实际代码一致
- 代码示例必须可运行
- 链接必须有效

### 完整性

- 所有关键字都有文档
- 所有特性都有说明
- 所有示例都有注释

### 一致性

- 术语统一（如 "agent" vs "智能体"）
- 格式统一（代码块、标题层级）
- 版本信息统一

### 可读性

- 清晰的章节结构
- 适当的代码示例
- 有用的 wikilinks

---

## 工具

### 使用的工具

- `llm-wiki` skill - wiki 维护
- `Read` / `Write` / `Edit` - 文件操作
- `Bash` - 代码分析
- `grep` / `find` - 搜索

### 自动化脚本

可以创建脚本自动检查：
- 版本号一致性
- 关键字计数
- 链接有效性

---

## 参考

- **Karpathy LLM Wiki Pattern**: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- **Helen CLAUDE.md**: 项目指令
- **Helen HLD**: 高层设计文档（如有）

---

**最后更新**: 2026-07-13  
**维护者**: LLM (Claude)  
**版本**: v1.18
