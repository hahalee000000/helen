"""
事件消费者 - 处理 UI 事件并更新组件状态
"""

from typing import Dict, List, Any
from rich.console import Group
from rich.text import Text
from .components.agent_panel import AgentPanel
from .components.streaming_text import StreamingText
from .components.status_bar import StatusBar


class EventConsumer:
    """消费 UI 事件，更新组件状态"""

    def __init__(self):
        self.agent_panels: Dict[str, AgentPanel] = {}
        self.streaming_text = StreamingText()
        self.status_bar = StatusBar()
        self.status_messages: List[Dict[str, Any]] = []

    def process(self, event: Dict[str, Any]):
        """处理单个事件"""
        event_type = event.get("type")

        if event_type == "agent_start":
            agent_name = event["agent"]
            self.agent_panels[agent_name] = AgentPanel(agent_name)
            self.agent_panels[agent_name].start()

        elif event_type == "agent_end":
            agent_name = event["agent"]
            duration_ms = event.get("duration_ms", 0)
            if agent_name in self.agent_panels:
                self.agent_panels[agent_name].finish(duration_ms)

        elif event_type == "llm_chunk":
            chunk = event["chunk"]
            self.streaming_text.append(chunk)

        elif event_type == "tool_call":
            tool = event["tool"]
            args = event.get("args", {})
            self.streaming_text.append(f"\n[cyan]⚙ {tool}[/cyan] ")

        elif event_type == "tool_result":
            tool = event["tool"]
            status = event.get("status", "success")
            result = event.get("result", "")
            icon = "✓" if status == "success" else "✗"
            color = "green" if status == "success" else "red"
            self.streaming_text.append(f"[{color}]{icon}[/{color}] ")

        elif event_type == "status":
            message = event["message"]
            level = event.get("level", "info")
            self.status_messages.append({"message": message, "level": level})
            # 只保留最近 5 条状态消息
            if len(self.status_messages) > 5:
                self.status_messages = self.status_messages[-5:]

        elif event_type == "user_input_request":
            # 输入请求由 InputHandler 处理
            pass

        elif event_type == "abort":
            self.streaming_text.append("\n[bold yellow]⚠ 已中止[/bold yellow]\n")

    def render(self):
        """渲染所有组件为 Rich 可渲染的内容"""
        renderables = []

        # 渲染 Agent 面板（已经是 Text 对象）
        for panel in self.agent_panels.values():
            panel_render = panel.render()
            if panel_render:
                renderables.append(panel_render)

        # 渲染流式文本（已经是 Rich 对象：Markdown 或 Text）
        streaming_render = self.streaming_text.render()
        if streaming_render:
            renderables.append(streaming_render)

        # 渲染状态消息
        for msg in self.status_messages:
            level = msg["level"]
            message = msg["message"]
            if level == "success":
                renderables.append(Text.from_markup(f"[bold green]✓[/bold green] {message}"))
            elif level == "warning":
                renderables.append(Text.from_markup(f"[bold yellow]⚠[/bold yellow] {message}"))
            elif level == "error":
                renderables.append(Text.from_markup(f"[bold red]✗[/bold red] {message}"))
            else:
                renderables.append(Text.from_markup(f"[dim]ℹ[/dim] {message}"))

        # 渲染状态栏（已经是 Text 对象）
        status_render = self.status_bar.render()
        if status_render:
            renderables.append(status_render)

        # 使用 Group 组合所有渲染对象
        if renderables:
            return Group(*renderables)
        else:
            return Text("")

    def clear_completed_agents(self):
        """清除已完成的 Agent 面板（可选）"""
        self.agent_panels = {
            name: panel for name, panel in self.agent_panels.items()
            if not panel.is_finished()
        }

    def reset(self):
        """重置所有状态"""
        self.agent_panels.clear()
        self.streaming_text.reset()
        self.status_messages.clear()
