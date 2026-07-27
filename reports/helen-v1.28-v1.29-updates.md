# Helen v1.28 – v1.29.3 更新总结

> 时间跨度: 2026-07-26 → 2026-07-27
> 版本跨度: v1.28.0 → v1.29.3
> 测试数: 3246 → 3246

---

## v1.29: Agent 级 Transcript 控制 ⭐ 重磅特性

### v1.29.0 — 语法与解析器

**新增关键字**: `transcript` / `记录`(中英双语,关键字数 94 → 95)

在 agent 声明中新增 transcript 子句,控制 transcript 记录行为:

```helen
agent 审计Agent {
    description "审计任务"
    model "qwen3.7-plus"
    transcript "persistent"  // 完整持久化到磁盘
    
    main {
        llm act "执行审计"
    }
}
```

**三个级别**:

| 级别 | 英文值 | 中文别名 | 行为 | 适用场景 |
|------|--------|---------|------|---------|
| `none` | `"none"` | `"无"` | 完全不记录 transcript | 简单脚本、批处理、性能敏感(默认) |
| `memory` | `"memory"` | `"内存"` | 仅内存记录,不写磁盘 | 调试、临时分析、会话追踪 |
| `persistent` | `"persistent"` | `"持久"` | 完整持久化到 `.helen/sessions/` | 长运行 agent、审计追踪、会话恢复 |

**改动文件**:
- `helen/core/tokens.py`: 新增 `TRANSCRIPT` TokenType,`_KEYWORD_MAP` 加 `transcript` / `记录`(并修复了之前缺失的 `protocol`/`impl`/`is`/`shared`/`alias`/`store` 重复条目)
- `helen/core/ast.py`: `AgentDeclNode` 新增 `transcript: str = "none"` 字段
- `helen/core/parser.py`: 解析 agent 声明里的 `transcript "..."` 子句,校验合法值
- `wiki/tutorial/05-agents.md`: 新增 Transcript Control 章节
- 技能文档 `helen-agent-patterns` / `helen-syntax` 同步更新

### v1.29.1 — helenagent 同步

同步 `ChatSessionActor` 从 helenagent 仓库。

### v1.29.2 — Runtime 实现 ⭐

**核心改动**:

1. **`_enter_invocation(agent_name, transcript_level="persistent")`**: 签名扩展,invocation 元数据新增 `transcript_level` 字段
2. **`_call_agent`**: 从 `agent.transcript` 读取级别,传入 invocation
3. **顶层 main 默认 `transcript="none"`**: 避免工作目录 session 文件堆积
4. **`_add_to_history`(llm_mixin.py)**: 根据当前 invocation 的 transcript_level 决定行为
   - `none`: 不写 TranscriptStore,用 fallback `_interpreter_history`
   - `memory`: 写 TranscriptStore,`persist=False`
   - `persistent`: 写 TranscriptStore,`persist=True`
5. **`TranscriptStore.append(message, persist=True)`**: 新增 `persist` 参数,`persist=False` 时跳过 backend 写入

**设计意义**: 之前所有 agent 都会创建 session 文件,导致项目目录污染。新机制让开发者显式控制每个 agent 的 transcript 行为,默认 `none` 实现零开销 + 干净目录。

### v1.29.3 — helenagent logo / Web UI 同步

纯同步更新,无语言核心改动。

---

## v1.28: :ask REPL 助手三层增强(详见 [helen-v1-28-update](../memory/helen-v1-28-update.md))

v1.28.0 重写 `:ask` 命令,三层架构:L1 REPL 上下文注入 / L2 REPL 状态工具 / L3 多轮对话。

### v1.28.1 — :ask streaming 修复
修复 `:ask` 流式输出,从 typed dict 事件中正确提取 `content` 字段。

### v1.28.2 — agent tools 声明 bug 修复
修复 `tools = CONST_NAME` 声明缺失 `=` 导致 LLM 无法调用工具的 bug。

### v1.28.3 — :ask 两个 bug 修复
修复 `:ask` 的 `session_id` 错误和 tool schema 格式问题。

### v1.28.4 — /compress token 计数变通(Issue #23)
修复 `/compress` 命令中 token 计数问题。

### v1.28.5 — stdlib 改进 + 解析器增强 ⭐

**新增 stdlib 函数**:
- `find_from(s, sub, start)` / `从位置查找`:基于位置的字符串搜索
- `json_parse_lenient(text)` / `json宽松解析`: 自动剥离 LLM 输出的 markdown 代码围栏

**解析器陷阱检测**:
- 检测 `if (a || b) && c { }` 这类布尔表达式陷阱(括号用错)
- 提供清晰的错误提示,建议使用双括号
- 同时应用到 `if` 和 `while`

**文档**: 更新 `helen-stdlib` 技能,增加 `regex_split` 示例和中文别名;wiki stdlib 参考更新至 292 个函数。

### v1.28.6 — Unicode 转义序列修复
修复 `\uNNNN` Unicode 转义解析 bug:
- 之前 `"一"` 被错误解析为字面量 `"4e00"`(长度 4)
- 现在正确产出 Unicode 字符 `一`(长度 1)
- 在 `lexer._parse_escape()` 中新增 `\uNNNN` 解析,模式同 `\xNN`

---

## 整体趋势

1. **显式优于隐式** 原则继续深化: v1.29 的 transcript 控制让 agent 的 transcript 行为显式可配置,而非隐式创建文件
2. **开发者体验持续优化**: 解析器陷阱检测、`\u` 转义修复、`json_parse_lenient` 等都在消除常见痛点
3. **helenagent 集成趋于稳定**: v1.26 集成 → v1.27 spawn resume → v1.28 助手三层增强 → v1.29 logo/UI 同步
4. **关键字数**: 94 → 95(新增 `transcript` / `记录`)
5. **测试数**: 3235 → 3246

---

## 待更新 Memory

- 创建 `helen-v1-29-update.md`
- 更新 `MEMORY.md` 索引
