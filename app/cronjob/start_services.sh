#!/usr/bin/env bash
set -euo pipefail

# 初始化数据库（如果还没有创建的话）
echo "检查并初始化数据库..."
if [ ! -f "/app/app/database/stations.db" ]; then
    echo "数据库不存在，正在创建数据库并导入数据..."
    echo "注意: 需要确保有数据库初始化脚本或预先创建好数据库文件"
else
    echo "数据库已存在，跳过初始化"
fi

# 设置增量数据定时同步
echo "设置增量数据定时同步..."
chmod +x /app/app/cronjob/start_incremental_sync_cron.sh
bash /app/app/cronjob/start_incremental_sync_cron.sh

# 启动 MCP Server (SSE via uvicorn in mcp_server.py)
cd /app && python app/servers/mcp_server.py &
MCP_PID=$!

echo "MCP server started with PID ${MCP_PID}"

# 启动 控制面板 Web Server (Flask)
cd /app && python app/servers/web_server.py &
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