#!/usr/bin/env bash
set -euo pipefail

# 启动 MCP Server (SSE via uvicorn in mcp_server.py)
python mcp_server.py &
MCP_PID=$!

echo "MCP server started with PID ${MCP_PID}"

# 启动 控制面板 Web Server (Flask)
python web_server.py &
WEB_PID=$!

echo "Web control panel started with PID ${WEB_PID}"

# 优雅关闭
term_handler() {
  echo "Received termination signal, stopping services..."
  kill -TERM "$MCP_PID" "$WEB_PID" 2>/dev/null || true
  wait "$MCP_PID" 2>/dev/null || true
  wait "$WEB_PID" 2>/dev/null || true
  exit 0
}

trap term_handler SIGTERM SIGINT

# 任一子进程退出则退出容器，让 docker-compose 的重启策略接管
wait -n "$MCP_PID" "$WEB_PID" || true
echo "One of the services exited. Exiting container to trigger restart..."
exit 1