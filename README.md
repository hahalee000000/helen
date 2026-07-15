# Helen — 为 AI Agent 设计的提示词优先编程语言

[![PyPI version](https://img.shields.io/pypi/v/helen-lang.svg)](https://pypi.org/project/helen-lang/)
[![Python](https://img.shields.io/pypi/pyversions/helen-lang.svg)](https://pypi.org/project/helen-lang/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-2917%20passed-green.svg)](https://github.com/hahalee000000/helen)

**Helen** 是一门专为 AI Agent 开发设计的 AI 原生 DSL（领域特定语言）。它将确定性构造（变量、函数、控制流）与一等 LLM 原语（`llm act`、`llm if`）融合为一门语言。

## ✨ 为什么选择 Helen？

- **Prompt-first**：`agent` 是一等公民，Agent 即语言构造而非库模式
- **287 个内置 stdlib 函数**：287 个中英文双语函数覆盖 AI 应用开发全链路
- **5 层渐进压缩 + 工作记忆**：长对话 Agent 自动管理上下文，无需手工调优
- **Transcript SSOT**：会话记录以 SQLite/JSONL 持久化，支持审计与回放
- **多 Agent 并发**：`spawn` + Channel 消息队列，内置 mailbox_select 多选
- **Python 双向集成**：Helen → Python FFI + Python → Helen Bridge
- **89 个双语关键字**：44.5 英文 + 44.5 中文，原生中文编程支持

## 🚀 快速开始

### 安装

```bash
pip install helen-lang
```

### Hello Helen

创建 `hello.helen`：

```helen
agent Greeter(name: str) {
    description "A friendly greeter"
    prompt "Greet {{name}} warmly in one sentence"
    
    main {
        return llm act "Greet {{name}} warmly"
    }
}

main {
    let g = Greeter("World")
    print(g)
}
```

运行：

```bash
helen hello.helen
# Hello, World! It's wonderful to meet you!
```

### REPL 交互

```bash
helen repl
> let x = 1 + 2
> print(x)
3
> :help
```

### Python Bridge 用法

Helen Agent 可以通过 Python Bridge 直接在 Python 中使用，就像使用普通的 Python 类：

1. 创建 Helen Agent 文件 `translator.helen`：

```helen
agent TranslatorAgent(text: str, target: str) {
    description "翻译文本到目标语言"
    prompt "Translate '{{text}}' to {{target}}"
    
    main {
        return llm act "Translate '{{text}}' to {{target}}"
    }
}
```

2. 在 Python 中导入并调用：

```python
from translator import TranslatorAgent

agent = TranslatorAgent()
result = agent("Hello", "French")
print(result)  # "Bonjour"
```

### Python 集成特性

- **直接导入 .helen 文件**：`from my_agents import TranslatorAgent`
- **类型提示支持**：IDE 自动补全 Helen Agent
- **异步调用**：`await agent.async_call(...)`
- **装饰器模式**：`@helen_agent` 装饰 Python 函数
- **参数验证**：Helen 自动校验 Agent 参数类型

```python
from helen.python_bridge import helen_agent

@helen_agent("translator.helen", "TranslatorAgent")
def translate(text: str, target: str) -> str:
    pass

result = translate("Hello", "French")
```

## 🎯 使用场景

### AI Agent 开发

```python
from agents import ResearchAgent, AnalysisAgent

# 研究阶段
researcher = ResearchAgent()
findings = researcher("quantum computing", depth="deep")

# 分析阶段
analyzer = AnalysisAgent()
insights = analyzer(findings)
```

### 多 Agent 协作

```python
from workflow import PlannerAgent, ExecutorAgent, ReviewerAgent

planner = PlannerAgent()
plan = planner("Build a web app")

executor = ExecutorAgent()
result = executor(plan)

reviewer = ReviewerAgent()
feedback = reviewer(result)
```

### LLM 应用

```python
from llm_agents import ChatBot, Summarizer, Translator

chatbot = ChatBot()
response = chatbot("What is AI?")

summarizer = Summarizer()
summary = summarizer(long_text)

translator = Translator()
translated = translator(summary, target="Chinese")
```

## 🛠️ API 参考

### HelenAgentWrapper

```python
class HelenAgentWrapper:
    def __init__(self, agent_name: str, helen_file: str, interpreter=None)
    
    def __call__(self, *args, **kwargs) -> Any
        """调用 agent"""
    
    async def async_call(self, *args, **kwargs) -> Any
        """异步调用 agent"""
```

### 装饰器

```python
@helen_agent(helen_file: str, agent_name: str = None)
def my_function(...):
    """将函数包装为 Helen agent 调用"""

@helen_module(helen_file: str)
class MyModule:
    """将类包装为 Helen agents 集合"""
```

### Import Hook

```python
from helen.python_bridge import install_import_hook

# 自动安装（默认）
install_import_hook()

# 手动卸载
from helen.python_bridge import uninstall_import_hook
uninstall_import_hook()
```

## 📖 更多示例

### 批量处理

```python
from agents import TranslatorAgent

agent = TranslatorAgent()
texts = ["Hello", "World", "AI"]

results = [agent(text, target="French") for text in texts]
print(results)  # ["Bonjour", "Monde", "IA"]
```

### 错误处理

```python
from agents import TranslatorAgent

agent = TranslatorAgent()

try:
    result = agent("Hello", target="French")
except TypeError as e:
    print(f"参数错误: {e}")
except Exception as e:
    print(f"执行错误: {e}")
```

### 共享解释器

```python
from helen.interpreter import Interpreter
from helen.python_bridge import HelenAgentWrapper

# 创建共享解释器
interpreter = Interpreter()

# 多个 agent 共享同一个解释器
agent1 = HelenAgentWrapper("Agent1", "agents.helen", interpreter)
agent2 = HelenAgentWrapper("Agent2", "agents.helen", interpreter)
```

## 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

## 📄 许可证

MIT License

## 🔗 链接

- 文档：https://helen.readthedocs.io
- GitHub：https://github.com/hahalee000000/helen
- PyPI：https://pypi.org/project/helen-lang

## 📚 文档

- [Wiki 文档](wiki/index.md) - 完整的技术文档
- [教程](docs/tutorial.md) - 从零开始学习 Helen
- [Python Bridge 教程](wiki/tutorial/15-python-bridge.md) - Python 集成指南
- [上下文管理](wiki/runtime/context-management.md) - 智能上下文处理（v1.20）
- [技能系统](wiki/runtime/skills.md) - 技能加载和使用

## 🆕 版本历史

### v1.20 - Transcript 会话作用域
- Transcripts 默认按应用隔离在 `.helen/sessions/`（REPL 场景 opt-in 全局）
- `session_scope` 配置：`auto` | `global` | `project`
- `HELEN_SESSION_DIR` 环境变量强制指定路径
- 新增 `get_session_dir()` / `set_session_dir()` stdlib 函数

### v1.19 - 上下文管理 API 完善
- 补齐 6 维度 API（Inspection/Working Memory/Fine-grained Mutation/Runtime Config/Query/Multi-agent Transfer）
- 新增 24 个 stdlib 函数：`context_stats`/`context_usage`/`pin_message`/`working_memory_*`/`export_context` 等
- `Message.pinned: bool` 字段，pinned 消息免疫全部 5 层压缩
- 内部化 `classify_message`

### v1.18 - spawn 并发原语
- `spawn Agent(...)` 返回 Channel，替代 `async/await/detach`
- Channel 消息队列：`send/receive/try_receive/cancel/close`
- `mailbox_select()` 多选原语
- 流式中断：`on_chunk` 回调返回 `false` 停止流式；Ctrl+C 中断

### v1.16 - TranscriptStore SSOT
- 对话历史 SSOT，SQLite/JSONL 双后端
- LRU 缓存（10K messages ~10MB）
- UUID 寻址，O(1) 查找
- 非破坏性压缩（BoundaryMarker 审计）

### v1.15 - 上下文管理增强
- Working Memory（工作记忆）
- Graduated Compression（渐进式压缩）
- Cache-Aware Compression（缓存感知压缩）
- Three-Channel Context（三通道上下文）
- Agent context configuration


### v1.14 - LLM 流式支持
- `llm act` 支持流式输出（on_chunk/on_complete 回调）
- `llm stream` 已删除（功能合并到 `llm act`）

### v1.13 - Python Bridge
- Python 直接导入和使用 Helen Agent
- 双向 FFI（Helen ↔ Python）

### v1.12 - Agent 隔离增强
- Agent 隔离级别（@open, @strict, @sandbox）
- Shared store 和 channel
- ReadOnlyView
- 闭包值捕获

### v1.10 - 核心特性
- Agent 作用域隔离
- 短路求值
- 下标/字段赋值
- 别名语句

## 🤝 社区与贡献

- **GitHub**: https://github.com/hahalee000000/helen — 报告 issue、提交 PR、参与讨论
- **License**: MIT — 商业友好、开源友好
- **Python**: 3.12+ required
- **平台**: Linux / macOS / Windows

欢迎贡献！可以查看 [CLAUDE.md](CLAUDE.md) 了解开发流程，或 [wiki/index.md](wiki/index.md) 查看完整文档。

## 📊 项目数据

- **代码规模**：~40,000 行 Python（96 个源文件）
- **测试覆盖**：2917 个测试，137 个测试文件
- **内置 stdlib**：287 个函数，287 个中文别名
- **内置 skills**：17 个（helen-syntax、helen-stdlib、code-quality、github 等）
- **双语关键字**：89 个（44.5 英文 + 44.5 中文）
