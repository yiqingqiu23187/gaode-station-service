#!/bin/bash

# 增量数据同步定时任务
# 每天早上7点自动同步招聘状态

# 确保PYTHONPATH变量有默认值
export PYTHONPATH="${PYTHONPATH:-}"

echo "🚀 设置增量数据同步定时任务..."

# 安装cron（如果没有）
if ! command -v cron &> /dev/null; then
    echo "安装cron..."
    apt-get update -qq && apt-get install -y -qq cron
fi

# 激活虚拟环境的路径（如果需要）
VENV_PATH="/app/.venv"
if [ -d "$VENV_PATH" ]; then
    PYTHON_CMD="source $VENV_PATH/bin/activate && python3"
else
    PYTHON_CMD="python3"
fi

# 创建增量同步cron任务 - 每天早上7点执行
CRON_JOB="0 7 * * * cd /app && export PYTHONPATH='/app' && $PYTHON_CMD app/cronjob/sync_hive_jobs_incremental.py >> /app/incremental_sync.log 2>&1"

# 备份当前crontab（如果存在）
crontab -l > /tmp/current_crontab 2>/dev/null || true

# 删除旧的增量同步任务（如果有）
grep -v "sync_hive_jobs_incremental.py" /tmp/current_crontab > /tmp/new_crontab 2>/dev/null || true

# 添加新的增量同步任务
echo "$CRON_JOB" >> /tmp/new_crontab

# 安装新的crontab
crontab /tmp/new_crontab

# 清理临时文件
rm -f /tmp/current_crontab /tmp/new_crontab

# 启动cron服务
service cron start

echo "✅ 增量同步定时任务已设置: 每天早上7:00执行"
echo "📋 任务详情: $CRON_JOB"
echo "📋 查看日志: tail -f /app/incremental_sync.log"
echo "📋 查看所有任务: crontab -l"

# 手动执行一次（可选）
if [ "$1" = "--run-now" ]; then
    echo "🔄 立即执行一次增量同步..."
    cd /app && export PYTHONPATH="/app" && python3 app/cronjob/sync_hive_jobs_incremental.py
fi

echo ""
echo "🔍 当前定时任务列表:"
crontab -l
