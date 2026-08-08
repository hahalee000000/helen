from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path


def _default_helen_path() -> str:
    """自动推断 helenagent 项目根目录

    查找策略：从 webui 目录向上遍历，找到包含 chat_tui.helen 的目录。
    如果找不到，默认返回 webui 的父目录（通常是 helenagent/）。
    """
    # 从本文件向上查找（webui/backend/app/config.py → helenagent/）
    here = Path(__file__).resolve()
    # parents[3] = helenagent/（webui 的父目录）
    candidate = here.parents[3]
    if (candidate / "chat_tui.helen").exists():
        return str(candidate)

    # 兜底：从当前工作目录向上查找
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if (parent / "chat_tui.helen").exists():
            return str(parent)

    # 最后兜底：webui 的父目录
    return str(here.parents[3])


def _backend_env_file() -> str:
    """返回 backend/.env 的绝对路径

    修复前 start-backend.sh 总是 cd 到 backend/ 目录，pydantic-settings 用相对路径 ".env" 能正确加载。
    修复后进程 cwd 是用户的真实工作目录，必须用绝对路径指向 backend/.env。
    """
    # 本文件位于 webui/backend/app/config.py，backend/ 是 parents[1]
    return str(Path(__file__).resolve().parents[1] / ".env")


class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "Helen Web UI"
    VERSION: str = "1.0"
    DEBUG: bool = False
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Helen 配置（默认自动推断，可通过环境变量或 .env 覆盖）
    HELEN_PATH: str = _default_helen_path()
    HELEN_TIMEOUT: int = 300

    # CORS 配置（允许 vite 常用端口 5173-5180）
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
        "http://localhost:5175", "http://127.0.0.1:5175",
        "http://localhost:5176", "http://127.0.0.1:5176",
        "http://localhost:5177", "http://127.0.0.1:5177",
        "http://localhost:5178", "http://127.0.0.1:5178",
        "http://localhost:5179", "http://127.0.0.1:5179",
        "http://localhost:5180", "http://127.0.0.1:5180",
    ]

    class Config:
        env_file = _backend_env_file()
        case_sensitive = True
        # v6.1 移除了 SQLite（transcript 作为 SSOT），保留 extra="ignore" 防止未来
        # .env 中的陈旧字段（如 DATABASE_URL）打断启动。
        extra = "ignore"

settings = Settings()
