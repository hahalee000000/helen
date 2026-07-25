"""工具调用显示"""

from rich.text import Text
from rich.panel import Panel
from rich.syntax import Syntax
import json


class ToolCallDisplay:
    """工具调用可视化"""

    def __init__(self):
        self.current_tool = None
        self.tool_history = []

    def start_tool(self, tool_name: str, args: dict):
        """开始工具调用"""
        self.current_tool = {
            "name": tool_name,
            "args": args,
            "status": "calling"
        }

    def finish_tool(self, status: str, result: str = ""):
        """完成工具调用"""
        if self.current_tool:
            self.current_tool["status"] = status
            self.current_tool["result"] = result
            self.tool_history.append(self.current_tool)
            self.current_tool = None

    def render_current(self) -> Text:
        """渲染当前工具调用"""
        if not self.current_tool:
            return Text("")

        text = Text()
        tool = self.current_tool

        # 工具名称
        text.append("⚙ ", style="bold cyan")
        text.append(tool["name"], style="bold cyan")

        # 状态
        if tool["status"] == "calling":
            text.append(" 调用中...", style="dim cyan")
        elif tool["status"] == "success":
            text.append(" ✓", style="bold green")
        elif tool["status"] == "error":
            text.append(" ✗", style="bold red")

        # 参数预览
        if tool["args"]:
            args_str = json.dumps(tool["args"], ensure_ascii=False, indent=2)
            if len(args_str) > 150:
                args_str = args_str[:150] + "..."
            text.append("\n")
            text.append(args_str, style="dim")

        return text

    def render_history(self, limit: int = 5) -> Text:
        """渲染工具调用历史"""
        text = Text()

        for tool in self.tool_history[-limit:]:
            text.append("⚙ ", style="cyan")
            text.append(tool["name"], style="cyan")

            if tool["status"] == "success":
                text.append(" ✓", style="green")
            else:
                text.append(" ✗", style="red")

            text.append("\n")

        return text
