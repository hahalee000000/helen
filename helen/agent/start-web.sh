#!/bin/bash

# Helen Web UI - 一键启动脚本（从项目根目录运行）
# 正确清理整个进程树，避免端口泄漏

set -e

echo "🎉 Starting Helen Web UI..."
echo ""

# 获取脚本目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEBUI_DIR="$SCRIPT_DIR/webui"

# 预检：清理残留进程，避免端口冲突
echo "🔍 Checking ports..."
PORTS=(8000 5173 5174 5175)
CLEANED=0
for port in "${PORTS[@]}"; do
    pids=$(lsof -ti :$port 2>/dev/null || true)
    if [ -n "$pids" ]; then
        # 可能有多个 PID，逐个处理
        for pid in $pids; do
            cmd=$(ps -p $pid -o comm= 2>/dev/null || echo "unknown")
            echo "   ⚠️  Port $port occupied by $cmd (PID: $pid), stopping..."
            kill $pid 2>/dev/null || true
        done
        CLEANED=$((CLEANED + 1))
    fi
done
if [ $CLEANED -gt 0 ]; then
    sleep 1
    # 兜底：强制 kill 仍在占用的进程
    for port in "${PORTS[@]}"; do
        pids=$(lsof -ti :$port 2>/dev/null || true)
        if [ -n "$pids" ]; then
            for pid in $pids; do
                kill -9 $pid 2>/dev/null || true
            done
        fi
    done
    sleep 1
fi
echo ""

# 启动后端（后台运行）
# stderr 重定向到日志文件，避免 uvicorn 正常关闭时的 CancelledError traceback 污染终端
# 真实错误仍可通过日志文件排查
echo "🔧 Starting backend..."
BACKEND_LOG="$(mktemp /tmp/helen-backend-XXXXXX.log)"
"$WEBUI_DIR/start-backend.sh" > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

# 等待后端启动
sleep 3

# 启动前端
echo "🎨 Starting frontend..."
"$WEBUI_DIR/start-frontend.sh" &
FRONTEND_PID=$!

echo ""
echo "✅ Helen Web UI is starting..."
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both services"
echo ""

# 清理函数：杀掉整个进程树
# 使用标志防止重复执行
CLEANUP_DONE=0
cleanup() {
    # 防止重复执行
    if [ $CLEANUP_DONE -eq 1 ]; then
        return
    fi
    CLEANUP_DONE=1

    echo ""
    echo "🛑 Stopping services..."

    # 优雅关闭：先发 SIGTERM，给进程 2 秒清理时间
    if [ -n "$BACKEND_PID" ]; then
        kill -TERM $BACKEND_PID 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill -TERM $FRONTEND_PID 2>/dev/null || true
    fi
    sleep 2

    # 强制关闭仍在运行的进程
    if [ -n "$BACKEND_PID" ]; then
        kill -- -$BACKEND_PID 2>/dev/null || true
        kill -9 $BACKEND_PID 2>/dev/null || true
        pkill -P $BACKEND_PID 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill -- -$FRONTEND_PID 2>/dev/null || true
        kill -9 $FRONTEND_PID 2>/dev/null || true
        pkill -P $FRONTEND_PID 2>/dev/null || true
    fi

    # 确保端口释放
    sleep 1
    for port in 8000 5173; do
        pids=$(lsof -ti :$port 2>/dev/null || true)
        if [ -n "$pids" ]; then
            for pid in $pids; do
                kill -9 $pid 2>/dev/null || true
            done
        fi
    done

    # 检查后端日志是否有真正的错误（忽略正常关闭的 CancelledError）
    if [ -n "$BACKEND_LOG" ] && [ -f "$BACKEND_LOG" ]; then
        if grep -q "Error\|Traceback\|Exception" "$BACKEND_LOG" 2>/dev/null; then
            # 过滤掉正常关闭时 uvicorn 的 CancelledError
            real_errors=$(grep -v "CancelledError\|connection closed\|Shutting down\|Finished server\|Stopping reloader\|Application startup complete\|Uvicorn running\|Waiting for application\|Started server\|Started reloader" "$BACKEND_LOG" | grep -E "Error|Traceback|Exception" | head -5)
            if [ -n "$real_errors" ]; then
                echo "⚠️  后端日志中发现错误（完整日志: $BACKEND_LOG）:"
                echo "$real_errors" | head -5
            fi
        fi
        # 如果没有错误，清理日志文件
        if [ -z "$real_errors" ]; then
            rm -f "$BACKEND_LOG" 2>/dev/null
        fi
    fi

    echo "✅ All services stopped"
}

# 捕获 Ctrl+C (INT)、终止 (TERM) 和退出 (EXIT) 信号
trap cleanup INT TERM EXIT

# 等待，直到收到信号或子进程退出
# 使用循环等待，避免 wait -n 的兼容性问题
while true; do
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
    # 如果 wait 返回，说明子进程退出或收到信号
    # 检查是否还有进程在运行
    if ! kill -0 $BACKEND_PID 2>/dev/null && ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "⚠️  Both services have exited"
        break
    fi
    # 如果只有一个退出，也退出（简化逻辑）
    if ! kill -0 $BACKEND_PID 2>/dev/null || ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "⚠️  One service has exited, stopping all services..."
        break
    fi
done

# cleanup 会通过 trap EXIT 自动调用
