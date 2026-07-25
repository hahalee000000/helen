"""状态栏 - 显示模式、模型、Token 计数等"""

from rich.text import Text


class StatusBar:
    """底部状态栏"""

    def __init__(self):
        self.mode = "minimal"
        self.model = "qwen3.7-max"
        self.token_count = 0
        self.elapsed_time = 0.0
        self.custom_fields = {}

    def set_mode(self, mode: str):
        """设置当前模式"""
        self.mode = mode

    def set_model(self, model: str):
        """设置模型名称"""
        self.model = model

    def set_token_count(self, count: int):
        """设置 Token 计数"""
        self.token_count = count

    def set_elapsed_time(self, seconds: float):
        """设置执行时间"""
        self.elapsed_time = seconds

    def set_field(self, key: str, value: str):
        """设置自定义字段"""
        self.custom_fields[key] = value

    def render(self) -> Text:
        """渲染状态栏"""
        text = Text()
        text.append("\n")  # 空行分隔

        # 分隔线
        text.append("─" * 60, style="dim")
        text.append("\n")

        # 模式
        text.append("模式: ", style="dim")
        text.append(self.mode, style="bold cyan")
        text.append(" │ ", style="dim")

        # 模型
        text.append("模型: ", style="dim")
        text.append(self.model, style="cyan")
        text.append(" │ ", style="dim")

        # Token 计数
        text.append("Tokens: ", style="dim")
        text.append(f"{self.token_count:,}", style="yellow")
        text.append(" │ ", style="dim")

        # 执行时间
        text.append("时间: ", style="dim")
        text.append(f"{self.elapsed_time:.1f}s", style="green")

        # 自定义字段
        for key, value in self.custom_fields.items():
            text.append(" │ ", style="dim")
            text.append(f"{key}: ", style="dim")
            text.append(value, style="magenta")

        return text
