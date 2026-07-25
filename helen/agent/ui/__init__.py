"""
HelenAgent Rich UI - Claude Code 风格的终端界面

核心组件：
- UIRenderer: 主渲染器，管理 Rich Live 显示
- EventConsumer: 事件消费和分发
- Components: AgentPanel, StreamingText, ToolCall, StatusBar
- InputHandler: 交互式输入（ESC + 斜杠命令）

注：Rich UI 相关组件需要 rich 库，stream_emitter 独立工作（无 rich 依赖）。
"""

# Rich UI 组件（可选依赖）
try:
    from .renderer import UIRenderer
    from .event_consumer import EventConsumer
    from .input_handler import InputHandler
    _RICH_AVAILABLE = True
except ImportError:
    _RICH_AVAILABLE = False
    UIRenderer = None
    EventConsumer = None
    InputHandler = None

# stream_emitter 始终可用（不依赖 rich，用于流式事件传递）
from . import stream_emitter

if _RICH_AVAILABLE:
    __all__ = ['UIRenderer', 'EventConsumer', 'InputHandler', 'stream_emitter']
else:
    __all__ = ['stream_emitter']

__version__ = '0.1.0'
