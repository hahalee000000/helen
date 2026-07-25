#!/bin/bash

# Helen Web UI - 后端启动脚本
# 使用 helenagent 共享的虚拟环境（~/.venv），确保能 import helen

set -e

echo "🚀 Starting Helen Web UI Backend..."

# ── 关键：保持用户的真实工作目录作为进程 cwd ──
#
# 设计背景：
#   - Helen TranscriptStore 用 os.getcwd() 决定 .helen/sessions/ 位置
#   - Web UI 的"目录 = 会话边界"语义要求不同目录有独立的 DB / session / memory
#   - 旧实现 cd 到 backend/ 目录，导致所有目录共享同一个 DB 和 session
#     （修复前：~/helenagent/webui/backend/.helen/webui.db 永远被使用）
#
# 修复策略：
#   1. 用绝对路径把 webui/backend 加入 PYTHONPATH（不改 cwd）
#   2. 进程 cwd 保持用户启动 start-web.sh 时的目录
#   3. 用 python -c "import os; os.chdir(...); uvicorn.run(...)" 启动，
#      确保在 import app 之前就切到正确目录
#
# 兜底：如果 HELEN_WEBUI_CWD 环境变量已设置（外部传入），用它覆盖
USER_CWD="${HELEN_WEBUI_CWD:-$(pwd)}"

# 解析为绝对路径（处理相对路径和 ~）
USER_CWD="$(cd "$USER_CWD" 2>/dev/null && pwd)" || {
    echo "❌ 工作目录不存在或不可访问: $USER_CWD"
    exit 1
}

# 后端代码目录（绝对路径，加入 PYTHONPATH 后无需 cd）
BACKEND_DIR="$(cd "$(dirname "$0")/backend" && pwd)"

echo "📂 用户工作目录: $USER_CWD"
echo "🔧 后端代码目录: $BACKEND_DIR"

# 使用 helenagent 共享的虚拟环境（包含 helen + webui 依赖）
HELEN_VENV="${HELEN_VENV:-$HOME/.venv}"

if [ ! -f "$HELEN_VENV/bin/python" ]; then
    echo "❌ 共享虚拟环境不存在: $HELEN_VENV"
    echo "   请先创建: uv venv $HELEN_VENV && source $HELEN_VENV/bin/activate"
    echo "   并安装 helen (cd ~/helen && uv pip install -e .)"
    exit 1
fi

echo "🔧 Using shared venv: $HELEN_VENV"
PYTHON="$HELEN_VENV/bin/python"

# 把 backend 目录加入 PYTHONPATH（这样 import app.xxx 能解析到）
export PYTHONPATH="$BACKEND_DIR:${PYTHONPATH:-}"

# 防御层：把用户 cwd 通过环境变量传给 Python 进程
# 即使 os.chdir 失败，directory_manager.py 仍可读到 HELEN_WEBUI_CWD
export HELEN_WEBUI_CWD="$USER_CWD"

# 同时把 backend 下的 .env 文件路径告诉 pydantic-settings
# （因为我们不再 cd 到 backend 目录，.env 自动加载会失败）
if [ -f "$BACKEND_DIR/.env" ]; then
    export ENV_FILE="$BACKEND_DIR/.env"
fi

# 确保依赖已安装（快速检查，缺失才装）
echo "📦 Checking dependencies..."
$PYTHON -c "import fastapi, uvicorn, sqlalchemy, pydantic_settings" 2>/dev/null || {
    echo "   Installing webui dependencies into $HELEN_VENV..."
    uv pip install --python "$PYTHON" -q -r "$BACKEND_DIR/requirements.txt"
}

# 复制环境变量文件（如果不存在，用绝对路径）
if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo "📝 Creating .env file..."
    if [ -f "$BACKEND_DIR/.env.example" ]; then
        cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    else
        touch "$BACKEND_DIR/.env"
    fi
fi

# 启动服务
echo "✅ Starting FastAPI server..."
echo "🌐 API will be available at http://localhost:8000"
echo "📚 Documentation at http://localhost:8000/docs"
echo ""

# 关键：用 Python 先 os.chdir 到用户目录，再启动 uvicorn
# 这样 Helen TranscriptStore、directory_manager 的 os.getcwd() 都对
# 关闭热重载（reload=False），防止 LLM 修改工作目录文件时触发重启
exec "$PYTHON" -c "
import os, sys
os.chdir('$USER_CWD')
# 让 uvicorn 能找到 app.main（PYTHONPATH 已包含 backend 目录）
import uvicorn
uvicorn.run(
    'app.main:app',
    host='0.0.0.0',
    port=8000,
    reload=False,
)
"
