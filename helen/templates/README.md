# Helen Templates

Helen 内置模板库 — 常见模式的完整示例代码。

## 可用模板

| 模板 | 描述 | 用途 |
|------|------|------|
| `simple_agent` | 简单 agent 调用 | 单 agent 处理单任务 |
| `spawn_channel` | spawn + Channel 并发 | 后台执行，Channel 接收结果 |
| `spawn_with_transcript` | spawn + transcript 继承 | 子 agent 访问父对话历史 |
| `shared_store` | SharedStore 数据交换 | 多 agent 共享可变数据 |
| `context_object` | Context 对象聚合 | 多参数场景简化 |
| `pipeline` | Agent 管道（顺序处理） | 多步骤数据处理流水线 |

## 使用方法

### 命令行

```bash
# 列出所有模板
helen template --list

# 查看模板内容
helen template simple_agent
helen template spawn_channel

# 复制模板到当前目录
helen template simple_agent --copy
helen template spawn_channel --copy my_worker.helen
```

### REPL

```
helen> :template                    # 列出所有模板
helen> :template simple_agent       # 查看模板
```

## 设计原则

所有模板都遵循 **"调用者决定上下文"** 原则：

1. **显式传递** — agent 的所有上下文都通过参数传入
2. **隔离优先** — agent 不自动继承外层变量
3. **数据流清晰** — 每一步的输入输出都可见

## 相关文档

- `helen-agent-collaboration` skill — Agent 协作模式详解
- `helen-programming-methodology` skill §5 — 上下文接力模式
- `wiki/tutorial/05-agents.md` — Agent 编程教程
