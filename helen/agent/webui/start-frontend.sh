#!/bin/bash

# Helen Web UI - 前端启动脚本

set -e

echo "🚀 Starting Helen Web UI Frontend..."

# 确定用户工作目录（优先 HELEN_WEBUI_CWD 环境变量，其次当前目录）
USER_CWD="${HELEN_WEBUI_CWD:-$(pwd)}"

# 读取 token 文件（如果存在），导出为环境变量供 vite 使用
TOKEN_FILE="$USER_CWD/.helen/webui_token"
if [ -f "$TOKEN_FILE" ]; then
    export HELEN_WEBUI_TOKEN=$(cat "$TOKEN_FILE")
    echo "🔑 Token loaded from $TOKEN_FILE"
else
    echo "ℹ️  No token file found at $TOKEN_FILE (auth may be disabled)"
fi

# 进入前端目录
cd "$(dirname "$0")/frontend"

# 检查 node_modules 是否完整（关键二进制是否存在）
# 仅检查目录存在不可靠 —— 中断的安装会留下空壳 node_modules
NEED_INSTALL=0
if [ ! -d "node_modules" ]; then
    NEED_INSTALL=1
elif [ ! -x "node_modules/.bin/vite" ]; then
    echo "⚠️  node_modules 不完整（缺少 vite），重新安装..."
    NEED_INSTALL=1
elif [ "package.json" -nt "node_modules/.package-lock.json" ] 2>/dev/null; then
    echo "⚠️  package.json 已更新，重新安装依赖..."
    NEED_INSTALL=1
fi

if [ "$NEED_INSTALL" -eq 1 ]; then
    echo "📦 Installing dependencies..."
    # npm ci 严格根据 package-lock.json 安装，自动清理残留的不完整 node_modules
    # 比 npm install 更快、更可靠，适合 CI 和开发环境
    if ! npm ci --prefer-offline 2>/dev/null; then
        # 如果 package-lock.json 和 package.json 不同步，回退到 npm install
        echo "⚠️  npm ci 失败，回退到 npm install..."
        npm install
    fi
    echo "✅ Dependencies installed"
fi

# 启动开发服务器（用 exec 替换进程，使信号能正确传递）
echo "✅ Starting Vite dev server..."
echo "🌐 Frontend will be available at http://localhost:5173"
echo ""

exec npm run dev
