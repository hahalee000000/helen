# 教程 15: Python Bridge

> 让 Python 直接使用 Helen Agent

## 概述

Helen Python Bridge 允许 Python 开发者直接导入和使用 Helen Agent，就像使用普通的 Python 类一样。这是 Helen 与 Python 生态系统的深度集成方案。

> 📘 **双向集成全景图**：见 [[reference/python-integration]]（包含 FFI + Bridge + 混合使用模式）
>
> **反向（Helen → Python）**：见 [[tutorial/09-python-ffi|Python FFI 教程]]

## 快速开始

### 1. 创建 Helen Agent

创建 `translator.helen` 文件：

```helen
agent TranslatorAgent(text: str, target: str) {
    description "翻译文本到目标语言"
    prompt "Translate '{{text}}' to {{target}}"
    
    main {
        return llm act "Translate '{{text}}' to {{target}}"
    }
}
```

### 2. 在 Python 中使用

```python
from translator import TranslatorAgent

# 创建 agent 实例
agent = TranslatorAgent()

# 调用 agent
result = agent("Hello", "French")
print(result)  # "Bonjour"
```

就这么简单！Python 开发者无需学习 Helen 语法，可以像使用普通 Python 类一样使用 Helen Agent。

## 核心特性

### 自动导入

Python Bridge 使用 Import Hook 自动识别 `.helen` 文件：

```python
# 自动加载 translator.helen 文件
from translator import TranslatorAgent, SummarizerAgent
```

### 参数验证

```python
agent = TranslatorAgent()

# ✅ 正确调用
result = agent("Hello", target="French")

# ❌ 缺少必需参数
result = agent("Hello")  # TypeError: missing required argument

# ❌ 未知参数
result = agent("Hello", target="French", extra="value")  # TypeError
```

### 类型转换

自动在 Python 和 Helen 类型之间转换：

```python
# Python → Helen
agent(42, "text", [1, 2, 3], {"key": "value"})

# Helen → Python
result = agent(...)  # 自动转换为 Python 类型
```

支持的类型：
- 基本类型：`int`, `float`, `str`, `bool`
- 集合类型：`list`, `dict`
- 空值：`None`

### 异步调用

```python
import asyncio

async def main():
    agent = TranslatorAgent()
    result = await agent.async_call("Hello", "Spanish")
    print(result)

asyncio.run(main())
```

### 关键字参数

```python
agent = TranslatorAgent()

# 位置参数
result = agent("Hello", "French")

# 关键字参数
result = agent(text="Hello", target="French")

# 混合使用
result = agent("Hello", target="French")
```

## 高级用法

### 装饰器模式

使用 `@helen_agent` 装饰器简化调用：

```python
from helen.python_bridge import helen_agent

@helen_agent("translator.helen", "TranslatorAgent")
def translate(text: str, target: str) -> str:
    pass

result = translate("Hello", "French")
```

### 共享解释器

多个 agent 可以共享同一个解释器实例：

```python
from helen.interpreter import Interpreter
from helen.python_bridge import HelenAgentWrapper

# 创建共享解释器
interpreter = Interpreter()

# 多个 agent 共享
agent1 = HelenAgentWrapper("Agent1", "agents.helen", interpreter)
agent2 = HelenAgentWrapper("Agent2", "agents.helen", interpreter)
```

### 会话管理 (v1.24+)

Interpreter 支持 `session_id` 参数，可以恢复历史会话：

```python
from helen.interpreter import Interpreter

# 方式 1: 恢复指定 session
interp = Interpreter(session_id="session_xxx")

# 方式 2: 恢复最近的 session
from helen.runtime.session_manager import SessionManager
manager = SessionManager()
sessions = manager.list_sessions()
if sessions:
    latest_sid = sessions[0]["session_id"]
    interp = Interpreter(session_id=latest_sid)

# 方式 3: 默认创建新 session（向后兼容）
interp = Interpreter()
```

**典型用法**：在 Python 服务中持续跟踪对话

```python
from helen.interpreter import Interpreter
from helen.python_bridge import HelenAgentWrapper

class ChatService:
    def __init__(self, session_id: str | None = None):
        # 可以恢复之前的对话
        self.interp = Interpreter(session_id=session_id)
        self.agent = HelenAgentWrapper("ChatBot", "chat.helen", self.interp)

    def chat(self, message: str) -> str:
        return self.agent(message)

    @property
    def session_id(self) -> str:
        return self.interp._agent_context.session_id

# 使用
service = ChatService()
print(service.chat("你好"))
print(f"Session: {service.session_id}")

# 下次可以恢复
service2 = ChatService(session_id=service.session_id)
```

**与 `resume_session()` 的区别**：

| 特性 | `Interpreter(session_id=...)` | `resume_session()` |
|------|------------------------------|-------------------|
| 时机 | 创建解释器时 | 运行时调用 |
| 行为 | 直接复用指定 session | 导入历史消息到当前新 session |
| transcript 文件 | 一个 | 两个 |
| 适用场景 | Python 服务持续对话 | 代码中切换上下文 |

### Import Hook 的 Session 复用 (v1.24.1+)

显式构造 `Interpreter(session_id=...)` 需要自己管理解释器实例。但 import hook 场景
（`from chat_tui import TUIChatAgent`）是隐式创建解释器的，无法在 import 语句中传参。

v1.24.1（Issue #16）为 import hook 增加了 session_id 检测链，按优先级解析：

```
1. set_session_id() 显式设置        （最高优先级，进程内动态控制）
2. 环境变量 HELEN_SESSION_ID          （跨进程重启恢复）
3. memento 文件 .helen/current_session_id  （相对 cwd，自动持久化）
4. None                              （默认，创建新 session）
```

#### 方式 1：显式 API（多 session 进程）

一个进程同时服务多个用户/会话时，每个用不同 session_id：

```python
from helen.python_bridge import set_session_id

# 必须在 import .helen 文件之前调用
set_session_id("session_user_alice")
from chat_tui import TUIChatAgent   # 复用 alice 的 session

# 切换到另一个 session（下次 import 生效）
set_session_id("session_user_bob")
```

#### 方式 2：环境变量（跨进程重启）

```bash
# 启动时指定 session
export HELEN_SESSION_ID=session_1784706227_daa6c8d4
python app.py
```

```python
# app.py
from chat_tui import TUIChatAgent   # 自动复用环境变量指定的 session
```

#### 方式 3：memento 文件（自动持久化）

将 session_id 写入 `.helen/current_session_id`（相对 cwd），import hook 自动读取：

```python
from pathlib import Path

# 首次启动：创建 session 后保存
from chat_tui import TUIChatAgent
agent = TUIChatAgent()
sid = agent.__interpreter__._agent_context.session_id

memento = Path(".helen/current_session_id")
memento.parent.mkdir(exist_ok=True)
memento.write_text(sid, encoding="utf-8")

# 进程重启后：import hook 自动读取 memento，复用同一 session
from chat_tui import TUIChatAgent   # 自动复用 memento 中的 session
```

#### 检测当前生效的 session_id

```python
from helen.python_bridge import get_session_id

print(get_session_id())  # 按优先级解析后的 session_id，或 None
```

**适用场景对照**：

| 场景 | 推荐方式 |
|------|---------|
| Web 服务多用户（同进程多 session）| `set_session_id()` |
| 跨进程重启恢复 | 环境变量 `HELEN_SESSION_ID` |
| 本地开发自动持久化 | memento 文件 |
| 一次性脚本 | 不设置（默认新 session）|

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

## 使用场景

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

## API 参考

### HelenAgentWrapper

```python
class HelenAgentWrapper:
    def __init__(self, agent_name: str, helen_file: str, interpreter=None):
        """
        初始化包装器
        
        Args:
            agent_name: Agent 名称
            helen_file: Helen 文件路径
            interpreter: 可选的解释器实例（用于共享）
        """
    
    def __call__(self, *args, **kwargs) -> Any:
        """调用 agent"""
    
    async def async_call(self, *args, **kwargs) -> Any:
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

## 限制

- 需要 Python 3.10+（因为 Helen 使用 match 语句）
- 当前只支持 agent 调用，不支持 Helen 的其他特性
- 类型转换目前只支持基本类型（int, float, str, bool, list, dict）

## 未来计划

- 支持更多 Helen 特性（函数、类等）
- 改进类型转换（支持自定义类型）
- 添加类型提示生成
- 支持 Helen 模块系统

## 示例代码

完整示例请查看 `examples/python_bridge/` 目录：

- `translator.helen`: Helen agent 定义
- `example_usage.py`: 完整使用示例
- `test_simple.py`: 简单测试

## 总结

Helen Python Bridge 让 Helen 成为 Python 的"原生扩展"，Python 开发者可以像使用 `numpy`、`pandas` 一样使用 Helen Agent，这会让 Helen 在 Python 生态系统中获得最大的采用率。

---

> **相关文档**：
> - [[reference/python-integration|Helen ↔ Python 双向集成全景图]] — 混合使用示例 + 选择指南
> - [[tutorial/09-python-ffi|Python FFI]] — 反向：在 Helen 中调用 Python 库
