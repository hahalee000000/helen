# Helen: 为 AI Agent 设计的 DSL

Helen 是一个专为 AI Agent 开发设计的领域特定语言（DSL），提供简洁的语法和强大的功能。现在通过 Python Bridge，Python 开发者可以直接导入和使用 Helen Agent，就像使用普通的 Python 类一样。

## ✨ 最新特性（v1.15）

### 🧠 上下文管理增强

Helen v1.15 引入了完整的上下文管理系统，类似于 Claude Code 的智能上下文处理：

- **Working Memory（工作记忆）**: 自动跟踪活跃文件、最近决策、待办事项、错误历史
- **Graduated Compression（渐进式压缩）**: 五层渐进式压缩（Layer 1-5，从 60% 到 95% 使用率）
- **Cache-Aware Compression（缓存感知压缩）**: 保留稳定前缀（30%），将缓存命中率从 10-20% 提升到 70-80%
- **Three-Channel Context（三通道上下文）**: 系统指令（15%）+ 工作记忆（50%）+ 对话历史（35%）

```helen
agent SmartAgent {
    context {
        compression "graduated"
        cache-aware true
        working-memory true
        working-memory-tokens 5000
    }
    
    main {
        return llm act "智能上下文管理"
    }
}
```

## 🚀 快速开始

### 安装

```bash
pip install helen
```

### 基本用法

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

2. 在 Python 中使用：

```python
from translator import TranslatorAgent

# 创建 agent 实例
agent = TranslatorAgent()

# 调用 agent
result = agent("Hello", "French")
print(result)  # "Bonjour"
```

## 📚 特性

### 1. 直接导入 Helen 文件

```python
# 自动识别并加载 .helen 文件
from my_agents import TranslatorAgent, SummarizerAgent
```

### 2. 类型提示支持

```python
from typing import Optional

def process_text(text: str, agent: TranslatorAgent) -> str:
    return agent(text, target="Chinese")
```

### 3. 异步调用

```python
import asyncio

async def main():
    agent = TranslatorAgent()
    result = await agent.async_call("Hello", "Spanish")
    print(result)

asyncio.run(main())
```

### 4. 装饰器模式

```python
from helen.python_bridge import helen_agent

@helen_agent("translator.helen", "TranslatorAgent")
def translate(text: str, target: str) -> str:
    pass

result = translate("Hello", "French")
```

### 5. 参数验证

```python
agent = TranslatorAgent()

# ✅ 正确
result = agent("Hello", target="French")

# ❌ 缺少必需参数
result = agent("Hello")  # TypeError: missing required argument: 'target'

# ❌ 未知参数
result = agent("Hello", target="French", extra="value")  # TypeError
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
- PyPI：https://pypi.org/project/helen

## 📚 文档

- [Wiki 文档](wiki/index.md) - 完整的技术文档
- [教程](docs/tutorial.md) - 从零开始学习 Helen
- [Python Bridge 教程](wiki/tutorial/15-python-bridge.md) - Python 集成指南
- [上下文管理](wiki/runtime/working_memory.md) - 智能上下文处理
- [技能系统](wiki/runtime/skills.md) - 技能加载和使用

## 🆕 版本历史

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
