---
name: helen-python-bridge
description: Helen Python Bridge 使用指南 — 让 Python 直接使用 Helen Agent 和函数，实现双向 FFI
version: 1.1.0
author: Helen Team
tags: [python, ffi, bridge, integration, agent, interoperability, function]
---

# Helen Python Bridge

Helen Python Bridge 允许 Python 开发者直接导入和使用 Helen Agent 与函数，就像使用普通的 Python 类和函数一样。这是 Helen 与 Python 生态系统的深度集成方案。

## 概述

Python Bridge 实现了 Helen 与 Python 的双向 FFI：

1. **Helen → Python (FFI)**：在 Helen 中使用 Python 库（已有）
2. **Python → Helen (Bridge)**：在 Python 中使用 Helen Agent 和函数（新增）

这让 Helen 成为 Python 生态系统的"原生扩展"，Python 开发者可以像使用 `numpy`、`pandas` 一样使用 Helen Agent 和函数。

> 📘 **想看双向集成全貌？** 见 `wiki/reference/python-integration.md` — 架构图 + 混合使用示例

## Helen → Python（FFI）速查

本文档侧重 **Python → Helen** 方向。如果你需要的是 **Helen → Python**（在 Helen 中调用 Python 库），核心语法如下：

```helen
// 导入 Python 模块（无扩展名 = Python 模块）
import "math" as math
import "json" as json
import "mylib.renderer" as PyRenderer

// 调用函数 / 访问常量
let s = json.dumps({"k": "v"})
let pi = math.pi

// 实例化 Python 类 + 调用方法
let encoder = json.JSONEncoder()
let result = encoder.encode({"x": 1})        // 自然方法调用（推荐）
let result2 = encoder.call("encode", {"x": 1})  // 按方法名调用（动态场景）
```

**要点：**
- 类实例化：`PyModule.ClassName()` — 类是可调用的
- 方法调用：优先用 `obj.method()`；`obj.call("method")` 用于动态方法名
- 嵌套导入：被导入的 `.helen` 模块中的 Python 导入完全可用

→ 详细教程：`wiki/tutorial/09-python-ffi.md`

## 快速开始

### 1. 创建 Helen Agent

```helen
// translator.helen
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

## 核心特性

### 自动导入

Python Bridge 使用 Import Hook 自动识别 `.helen` 文件（v1.23.6+ 支持函数导入）：

```python
# 安装 import hook（一次性）
from helen.python_bridge.import_hook import install_import_hook
install_import_hook()

# 自动加载 translator.helen 文件中的 agent 和 function
from translator import TranslatorAgent, SummarizerAgent, format_text
```

**Helen 文件示例：**

```helen
// translator.helen
const default_lang = "English"

// 普通函数（纯计算，无 LLM 调用）
fn format_text(text: str): str {
    返回 text.strip().capitalize()
}

// Agent（需要 LLM 推理）
agent TranslatorAgent(text: str, target: str) {
    description "翻译文本到目标语言"
    prompt "Translate '{{text}}' to {{target}}"
    
    main {
        return llm act "Translate '{{text}}' to {{target}}"
    }
}
```

**Python 调用：**

```python
from translator import TranslatorAgent, format_text

# 直接调用函数
formatted = format_text("  hello world  ")  # "Hello world"

# 调用 agent
agent = TranslatorAgent()
result = agent("Hello", "French")  # "Bonjour"
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

Interpreter 支持 `session_id` 参数，可以恢复历史会话，实现跨进程对话持久化：

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

**Web 服务中的典型用法**：

```python
from helen.interpreter import Interpreter
from helen.python_bridge import HelenAgentWrapper

class ChatService:
    """支持跨请求对话持久化的聊天服务"""

    def __init__(self, user_id: str, session_id: str | None = None):
        self.user_id = user_id
        # 恢复之前的对话，或创建新对话
        self.interp = Interpreter(session_id=session_id)
        self.agent = HelenAgentWrapper("ChatBot", "chat.helen", self.interp)

    def chat(self, message: str) -> str:
        return self.agent(message)

    @property
    def session_id(self) -> str:
        """返回当前 session_id，客户端保存后可用于下次恢复"""
        return self.interp._agent_context.session_id

# Flask/FastAPI Web 服务示例
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.post("/chat")
def chat():
    data = request.json
    service = ChatService(
        user_id=data["user_id"],
        session_id=data.get("session_id"),  # 可选：恢复历史对话
    )
    response = service.chat(data["message"])
    return jsonify({
        "response": response,
        "session_id": service.session_id,  # 客户端保存，下次传入
    })
```

**`Interpreter(session_id=...)` vs `resume_session()`**：

| 特性 | `Interpreter(session_id=...)` | `resume_session()` |
|------|------------------------------|-------------------|
| 时机 | 创建解释器时 | 运行时调用 |
| 行为 | 直接复用指定 session | 导入历史消息到当前新 session |
| transcript 文件 | 一个 | 两个 |
| 适用场景 | Python 服务持续对话 | 代码中切换上下文 |

### Import Hook 的 Session 复用 (v1.24.1+，Issue #16)

显式构造 `Interpreter(session_id=...)` 需要自己管理解释器实例。但 import hook 场景
（`from chat_tui import TUIChatAgent`）是**隐式**创建解释器的，无法在 import 语句中传参。

v1.24.1 为 import hook 增加了 session_id 检测链，按优先级解析：

```
1. set_session_id() 显式设置              （最高优先级，进程内动态控制）
2. 环境变量 HELEN_SESSION_ID                （跨进程重启恢复）
3. memento 文件 .helen/current_session_id   （相对 cwd，自动持久化）
4. None                                    （默认，创建新 session）
```

```python
# 方式 1: 显式 API（多 session 进程，必须在 import 前调用）
from helen.python_bridge import set_session_id
set_session_id("session_user_alice")
from chat_tui import TUIChatAgent   # 复用 alice 的 session

# 方式 2: 环境变量（跨进程重启）
#   export HELEN_SESSION_ID=session_xxx && python app.py
from chat_tui import TUIChatAgent   # 自动复用环境变量指定的 session

# 方式 3: memento 文件（自动持久化）
#   echo "session_xxx" > .helen/current_session_id
from chat_tui import TUIChatAgent   # 自动读取 memento 复用 session

# 检测当前生效的 session_id
from helen.python_bridge import get_session_id
print(get_session_id())
```

**适用场景**：

| 场景 | 推荐方式 |
|------|---------|
| Web 服务多用户（同进程多 session）| `set_session_id()` |
| 跨进程重启恢复 | 环境变量 `HELEN_SESSION_ID` |
| 本地开发自动持久化 | memento 文件 |
| 一次性脚本 | 不设置（默认新 session）|

### 调用 Helen 函数 (v1.23.6+)

除了调用 agent，Python Bridge 还支持直接调用 Helen 的普通函数（`fn`）：

```python
from helen.python_bridge.function_wrapper import HelenFunctionWrapper, load_helen_functions

# 方法 1: 调用单个函数
add = HelenFunctionWrapper("add", "utils.helen")
result = add(10, 32)  # 42

greet = HelenFunctionWrapper("greet", "utils.helen")
result = greet("Python")  # "Hello, Python!"

# 方法 2: 加载所有函数
functions = load_helen_functions("utils.helen")
# {'add': <HelenFunctionWrapper>, 'greet': <HelenFunctionWrapper>, ...}

result = functions['add'](100, 200)  # 300
result = functions['greet']("World")  # "Hello, World!"
```

**何时使用函数 vs Agent：**
- **函数 (fn)**：纯计算、工具函数、数据处理（无 LLM 调用）
- **Agent**：需要 LLM 推理、工具调用、上下文管理

**混合使用：**
```python
from helen.python_bridge.agent_wrapper import HelenAgentWrapper
from helen.python_bridge.function_wrapper import HelenFunctionWrapper

# 同一个 Helen 文件中的 agent 和函数
agent = HelenAgentWrapper("translator", "app.helen")
utils = HelenFunctionWrapper("format_text", "app.helen")

# 先用函数处理数据，再用 agent 推理
processed = utils("raw text")
result = agent(processed)
```

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

## 实现原理

1. **Import Hook**：使用 Python 的 `sys.meta_path` 拦截模块导入
2. **动态类生成**：解析 Helen 文件，为每个 agent 动态创建 Python 类
3. **类型转换**：自动在 Python 和 Helen 类型之间转换
4. **参数验证**：检查参数类型和必需参数
5. **异步支持**：提供 `async_call` 方法用于异步调用

## 限制

- 需要 Python 3.10+（因为 Helen 使用 match 语句）
- 当前只支持 agent 调用，不支持 Helen 的其他特性
- 类型转换目前只支持基本类型（int, float, str, bool, list, dict）

## 未来计划

- 支持更多 Helen 特性（函数、类等）
- 改进类型转换（支持自定义类型）
- 添加类型提示生成
- 支持 Helen 模块系统

## 相关资源

- 完整教程：[[tutorial/15-python-bridge]]
- 示例代码：`examples/python_bridge/`
- Python FFI 教程：[[tutorial/09-python-ffi]]

## 最佳实践

### 1. 使用共享解释器

当需要创建多个 agent 实例时，使用共享解释器可以提高性能：

```python
from helen.interpreter import Interpreter
from helen.python_bridge import HelenAgentWrapper

interpreter = Interpreter()
agent1 = HelenAgentWrapper("Agent1", "agents.helen", interpreter)
agent2 = HelenAgentWrapper("Agent2", "agents.helen", interpreter)
```

### 2. 批量处理

对于大量数据处理，使用列表推导式进行批量调用：

```python
results = [agent(item) for item in items]
```

### 3. 错误处理

始终使用 try-except 捕获可能的错误：

```python
try:
    result = agent(data)
except TypeError as e:
    print(f"参数错误: {e}")
except Exception as e:
    print(f"执行错误: {e}")
```

### 4. 异步调用

对于耗时的 agent 调用，使用异步方式避免阻塞：

```python
result = await agent.async_call(data)
```

### 5. 类型提示

使用类型提示提高代码可读性：

```python
def process_data(data: list, agent: TranslatorAgent) -> str:
    return agent(data)
```
