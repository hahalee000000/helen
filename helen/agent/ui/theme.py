"""
主题系统 - 定义 UI 颜色和样式

支持自定义主题，可以通过修改 THEME 字典来自定义颜色和样式。
"""

from typing import Dict

# 默认主题（Claude Code 风格）
THEME = {
    # Agent 状态
    "agent.running": "bold blue",
    "agent.done": "bold green",
    "agent.error": "bold red",
    "agent.pending": "dim",

    # 工具调用
    "tool.call": "cyan",
    "tool.success": "green",
    "tool.error": "red",
    "tool.args": "dim",

    # 状态消息
    "status.info": "dim",
    "status.success": "bold green",
    "status.warning": "bold yellow",
    "status.error": "bold red",

    # 流式文本
    "text.normal": "",
    "text.code": "cyan",
    "text.dim": "dim",

    # 状态栏
    "statusbar.mode": "bold cyan",
    "statusbar.model": "cyan",
    "statusbar.tokens": "yellow",
    "statusbar.time": "green",
    "statusbar.separator": "dim",

    # 进度条
    "progress.bar": "cyan",
    "progress.text": "bold",
    "progress.percentage": "cyan",

    # 输入提示
    "input.prompt": "bold cyan",
    "input.cursor": "reverse",
}

# 备用主题：深色（高对比度）
THEME_DARK = {
    "agent.running": "bold bright_blue",
    "agent.done": "bold bright_green",
    "agent.error": "bold bright_red",
    "agent.pending": "bright_black",

    "tool.call": "bright_cyan",
    "tool.success": "bright_green",
    "tool.error": "bright_red",
    "tool.args": "bright_black",

    "status.info": "bright_black",
    "status.success": "bold bright_green",
    "status.warning": "bold bright_yellow",
    "status.error": "bold bright_red",

    "text.normal": "",
    "text.code": "bright_cyan",
    "text.dim": "bright_black",

    "statusbar.mode": "bold bright_cyan",
    "statusbar.model": "bright_cyan",
    "statusbar.tokens": "bright_yellow",
    "statusbar.time": "bright_green",
    "statusbar.separator": "bright_black",

    "progress.bar": "bright_cyan",
    "progress.text": "bold",
    "progress.percentage": "bright_cyan",

    "input.prompt": "bold bright_cyan",
    "input.cursor": "reverse",
}

# 备用主题：浅色
THEME_LIGHT = {
    "agent.running": "bold blue",
    "agent.done": "bold green",
    "agent.error": "bold red",
    "agent.pending": "dim",

    "tool.call": "blue",
    "tool.success": "green",
    "tool.error": "red",
    "tool.args": "dim",

    "status.info": "dim",
    "status.success": "green",
    "status.warning": "yellow",
    "status.error": "red",

    "text.normal": "",
    "text.code": "blue",
    "text.dim": "dim",

    "statusbar.mode": "bold blue",
    "statusbar.model": "blue",
    "statusbar.tokens": "magenta",
    "statusbar.time": "green",
    "statusbar.separator": "dim",

    "progress.bar": "blue",
    "progress.text": "bold",
    "progress.percentage": "blue",

    "input.prompt": "bold blue",
    "input.cursor": "reverse",
}


def get_theme(name: str = "default") -> Dict[str, str]:
    """
    获取主题

    Args:
        name: 主题名称 ("default", "dark", "light")

    Returns:
        主题字典
    """
    if name == "dark":
        return THEME_DARK.copy()
    elif name == "light":
        return THEME_LIGHT.copy()
    else:
        return THEME.copy()


def get_style(element: str, theme: Dict[str, str] = None) -> str:
    """
    获取元素样式

    Args:
        element: 元素名称（如 "agent.running"）
        theme: 主题字典（可选，默认使用 THEME）

    Returns:
        Rich 样式字符串
    """
    if theme is None:
        theme = THEME
    return theme.get(element, "")
