#!/usr/bin/env python3
"""
Helen Web UI 后端

提供 ChatSessionActor 的导入接口，Web UI 通过这个模块调用 Helen。
v1.0：actor 成为唯一模式，移除非 actor 路径。
"""

import sys
import os

# Helen agent 项目目录
HELEN_AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

# 确保可以导入 helenagent 模块
sys.path.insert(0, HELEN_AGENT_DIR)

# 安装 Python Bridge import hook
try:
    from helen.python_bridge import install_import_hook
    install_import_hook()
except ImportError as e:
    print(f"✗ Python Bridge 不可用: {e}", file=sys.stderr)
    print("请确保已安装 Helen: pip install helen", file=sys.stderr)
    sys.exit(1)

# 导入 actor 接口（从 chat_tui.helen）
from chat_tui import (
    spawn_chat_actor,
    tui_chat_handler_actor,
    TUIChatAgent,
    exit_chat_actor,
    is_chat_actor_running,
)


def is_actor_mode_available() -> bool:
    """长驻 actor 模式是否可用"""
    return True


__all__ = [
    'spawn_chat_actor',
    'tui_chat_handler_actor',
    'TUIChatAgent',
    'exit_chat_actor',
    'is_chat_actor_running',
    'is_actor_mode_available',
]
