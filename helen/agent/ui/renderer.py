"""
UI 渲染器 - TUI 模式（Claude Code 风格）

支持两种模式：
1. TUI 模式（全屏，输出在上，输入在下）— 推荐
2. 简单模式（直接打印，无全屏）— 降级方案
"""

from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text
from typing import List, Dict, Any, Optional, Callable
import sys


class UIRenderer:
    """UI 渲染器（支持 TUI 模式）"""

    def __init__(self, use_tui: bool = True):
        """
        初始化渲染器

        Args:
            use_tui: 是否使用 TUI 模式（全屏）
        """
        self.use_tui = use_tui
        self.console = Console()
        self._current_agent = None
        self._streaming = False
        self._last_chunk_was_newline = False
        self._tui_app = None

        # 如果启用 TUI 模式，尝试创建 TUI 应用
        if use_tui:
            try:
                from .tui_app import TUIApp
                self._tui_app = TUIApp()
                print("✓ TUI 模式已启用", file=sys.stderr)
            except ImportError as e:
                print(f"⚠ TUI 模式不可用，降级到简单模式: {e}", file=sys.stderr)
                self.use_tui = False
                self._tui_app = None

    def start(self):
        """启动 UI"""
        if self._tui_app:
            # TUI 模式在 run() 中启动
            pass

    def stop(self):
        """停止 UI"""
        if self._streaming:
            print()
            self._streaming = False

    def pause(self):
        """暂停 UI（TUI 模式无需暂停）"""
        pass

    def resume(self):
        """恢复 UI（TUI 模式无需恢复）"""
        pass

    def render_events(self, events: List[Dict[str, Any]]):
        """渲染一批事件"""
        for event in events:
            event_type = event.get("type")

            if event_type == "agent_start":
                self._render_agent_start(event["agent"])
            elif event_type == "agent_end":
                self._render_agent_end(event["agent"], event.get("duration_ms", 0))
            elif event_type == "llm_chunk":
                self._render_llm_chunk(event.get("chunk", ""))
            elif event_type == "tool_call":
                self._render_tool_call(event["tool"], event.get("args", {}))
            elif event_type == "tool_result":
                self._render_tool_result(
                    event["tool"],
                    event.get("status", "success"),
                    event.get("result", "")
                )
            elif event_type == "status":
                self._render_status(event["message"], event.get("level", "info"))
            elif event_type == "abort":
                self._render_abort()

    def _render_agent_start(self, agent_name: str):
        """渲染 Agent 开始执行"""
        if self._tui_app:
            self._tui_app.render_agent_start(agent_name)
        else:
            text = Text()
            text.append("⎿  ", style="bold blue")
            text.append(agent_name, style="bold blue")
            text.append(" 执行中...", style="blue")
            self.console.print(text)
            self._current_agent = agent_name

    def _render_agent_end(self, agent_name: str, duration_ms: int):
        """渲染 Agent 执行完成"""
        if self._tui_app:
            self._tui_app.render_agent_end(agent_name, duration_ms)
        else:
            duration_s = duration_ms / 1000.0
            text = Text()
            text.append("⎿  ", style="bold green")
            text.append("✓ ", style="bold green")
            text.append(agent_name, style="green")
            text.append(f" ({duration_s:.1f}s)", style="dim green")
            self.console.print(text)
            self._current_agent = None

    def _render_llm_chunk(self, chunk: str):
        """渲染 LLM 流式输出"""
        if self._tui_app:
            self._tui_app.render_llm_chunk(chunk)
        else:
            print(chunk, end='', flush=True)
            self._streaming = True
            self._last_chunk_was_newline = chunk.endswith('\n')

    def _render_tool_call(self, tool: str, args: Dict[str, Any]):
        """渲染工具调用"""
        if self._tui_app:
            self._tui_app.render_tool_call(tool, args)
        else:
            if self._streaming and not self._last_chunk_was_newline:
                print()
                self._streaming = False

            args_str = ", ".join(f"{k}={v}" for k, v in args.items())
            if len(args_str) > 60:
                args_str = args_str[:57] + "..."

            self.console.print(f"⎿  🔧 [cyan]{tool}[/cyan]([dim]{args_str}[/dim])")

    def _render_tool_result(self, tool: str, status: str, result: str):
        """渲染工具结果"""
        if self._tui_app:
            self._tui_app.render_tool_result(tool, status, result)
        else:
            if status == "success":
                icon = "✓"
                style = "green"
            else:
                icon = "✗"
                style = "red"

            if len(result) > 100:
                result = result[:97] + "..."

            self.console.print(f"⎿  [{style}]{icon}[/{style}] [dim]{result}[/dim]")

    def _render_status(self, message: str, level: str):
        """渲染状态消息"""
        if self._tui_app:
            self._tui_app.render_status(message, level)
        else:
            if level == "success":
                self.console.print(f"[bold green]✓[/bold green] {message}")
            elif level == "warning":
                self.console.print(f"[bold yellow]⚠[/bold yellow] {message}")
            elif level == "error":
                self.console.print(f"[bold red]✗[/bold red] {message}")
            else:
                self.console.print(f"[dim]ℹ[/dim] {message}")

    def _render_abort(self):
        """渲染中止消息"""
        if self._tui_app:
            self._tui_app.append_output("\n⚠ 已中止\n")
        else:
            if self._streaming:
                print()
                self._streaming = False
            self.console.print("[bold yellow]⚠ 已中止[/bold yellow]")

    def print_message(self, message: str):
        """直接打印消息（支持 Markdown）"""
        if self._tui_app:
            self._tui_app.render_markdown(message)
        else:
            if self._streaming and not self._last_chunk_was_newline:
                print()
                self._streaming = False

            try:
                if message.strip():
                    self.console.print(Markdown(message))
                else:
                    self.console.print(message)
            except Exception:
                self.console.print(message)

    def clear(self):
        """清空显示"""
        if self._tui_app:
            self._tui_app.clear_output()

    def is_started(self) -> bool:
        """检查是否已启动"""
        return True

    def run_tui(self):
        """运行 TUI 应用（如果启用）"""
        if self._tui_app:
            self._tui_app.run()
        else:
            print("⚠ TUI 模式未启用", file=sys.stderr)

    def get_tui_app(self):
        """获取 TUI 应用实例"""
        return self._tui_app
