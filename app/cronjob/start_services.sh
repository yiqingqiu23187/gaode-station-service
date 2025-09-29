#!/usr/bin/env bash
set -euo pipefail

# 确保PYTHONPATH变量有默认值
export PYTHONPATH="${PYTHONPATH:-}"

# 初始化数据库文件
echo "初始化数据库文件..."

# 确保数据库目录存在
mkdir -p /app/app/database

# 从挂载位置复制数据库文件
if [ -f "/tmp/stations.db" ]; then
    echo "从临时位置复制数据库文件..."
    cp /tmp/stations.db /app/app/database/stations.db
    DB_SIZE=$(du -h /app/app/database/stations.db | cut -f1)
    echo "数据库文件复制完成 ✓ (大小: $DB_SIZE)"
else
    echo "警告: 未找到数据库文件 /tmp/stations.db"
    echo "请确保数据库文件已正确挂载"
fi

# 设置增量数据定时同步
echo "设置增量数据定时同步..."
chmod +x /app/app/cronjob/start_incremental_sync_cron.sh
bash /app/app/cronjob/start_incremental_sync_cron.sh

# 设置Python路径以正确导入模块
export PYTHONPATH="/app:${PYTHONPATH}"

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