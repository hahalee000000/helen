# Helen Python Bridge

Helen Python Bridge 允许 Python 开发者直接导入和使用 Helen Agent，就像使用普通的 Python 类一样。

## 安装

```bash
pip install helen
```

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

## 特性

### 自动导入

```python
# 自动识别并加载 .helen 文件
from my_agents import Agent1, Agent2, Agent3
```

### 类型提示

```python
from typing import Optional

def process_text(text: str, agent: TranslatorAgent) -> str:
    return agent(text, target="Chinese")
```

### 异步调用

```python
import asyncio

async def main():
    agent = TranslatorAgent()
    result = await agent.async_call("Hello", "Spanish")
    print(result)

asyncio.run(main())
```

### FFI 回调与 asyncio（线程安全，重要）

Helen 通过 FFI 调用 Python 回调时，回调是**同步**执行的，并且发生在
**Helen 的执行线程**里——该线程**没有 asyncio event loop**。这一点在把
Helen agent 集成进异步应用（如 FastAPI / Web UI 后端）时极易踩坑。

```python
# ❌ 错误：回调跑在 Helen 线程，没有 running event loop
def emit_stream_event(chunk: str):
    asyncio.create_task(queue.put(chunk))   # RuntimeError: no running event loop
    # 或：await queue.put(chunk)             # 同样报错（且回调是同步的，不能 await）

agent = TranslatorAgent()
agent.on_chunk = emit_stream_event          # Helen 在自己的线程里同步调用它
agent("Hello", target="French")
```

正确做法是用 `loop.call_soon_threadsafe` 把事件**投递回** asyncio loop 所在线程：

```python
import asyncio

class StreamBridge:
    def __init__(self, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue):
        self._loop = loop
        self._queue = queue

    # Helen 在其执行线程中同步调用此回调
    def emit_stream_event(self, chunk: str):
        self._loop.call_soon_threadsafe(self._queue.put_nowait, chunk)

async def run():
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    bridge = StreamBridge(loop, queue)

    agent = TranslatorAgent()
    agent.on_chunk = bridge.emit_stream_event

    # async_call 在线程池里跑 Helen 的同步 __call__；
    # 期间 Helen 线程同步回调 emit_stream_event -> call_soon_threadsafe -> 主 loop
    task = asyncio.create_task(agent.async_call("Hello", target="French"))
    while True:
        chunk = await queue.get()
        if chunk is None:
            break
        print("chunk:", chunk)
    await task
```

要点：

- **回调方向 vs 调用方向**：`async_call` 解决的是「Python 异步地调用 Helen」
  （用线程池跑 Helen 的同步 `__call__`）；它**不解决**「Helen 回调 Python」
  这一方向的线程安全问题。两个方向都要单独处理。
- **`spawn` 的 agent 一样适用**：`spawn` 出来的 agent 跑在独立线程里，它
  通过 FFI 调用的 Python 回调同样没有 event loop，仍需 `call_soon_threadsafe`。
- **同步回调不能 `await`**：FFI 回调签名是普通同步函数，体内不可 `await`；
  要把异步工作调度回 loop 用 `call_soon_threadsafe` / `create_task`（后者需
  在 loop 线程内，故仍要走 `call_soon_threadsafe`）。
- **取消**：流式推理中断可用 `Channel.cancel()`（spawn 场景）或
  `cancel_llm_call()` / Ctrl+C（REPL 场景），详见 v1.18 流式中断文档。

### 参数验证

```python
agent = TranslatorAgent()

# ✅ 正确
result = agent("Hello", target="French")

# ❌ 缺少必需参数
result = agent("Hello")  # TypeError

# ❌ 未知参数
result = agent("Hello", target="French", extra="value")  # TypeError
```

### 装饰器模式

```python
from helen.python_bridge import helen_agent

@helen_agent("translator.helen", "TranslatorAgent")
def translate(text: str, target: str) -> str:
    pass

result = translate("Hello", "French")
```

## API 参考

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

## 使用场景

### AI Agent 开发

```python
from agents import ResearchAgent, AnalysisAgent

researcher = ResearchAgent()
findings = researcher("quantum computing", depth="deep")

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

## 高级用法

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

## 实现原理

1. **Import Hook**: 使用 Python 的 `sys.meta_path` 拦截模块导入
2. **动态类生成**: 解析 Helen 文件，为每个 agent 动态创建 Python 类
3. **类型转换**: 自动在 Python 和 Helen 类型之间转换
4. **参数验证**: 检查参数类型和必需参数
5. **异步支持**: 提供 `async_call` 方法用于异步调用

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

完整示例请查看 `examples/python_bridge/` 目录。
