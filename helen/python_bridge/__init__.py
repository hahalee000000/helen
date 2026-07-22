"""Helen Python Bridge - 让 Python 直接导入和使用 Helen Agent"""

from .import_hook import install_import_hook, set_session_id, get_session_id
from .agent_wrapper import HelenAgentWrapper, generate_python_classes
from .decorators import helen_agent

__version__ = "0.1.0"
__all__ = [
    "install_import_hook",
    "set_session_id",
    "get_session_id",
    "HelenAgentWrapper",
    "generate_python_classes",
    "helen_agent",
]

# 自动安装 import hook
install_import_hook()
