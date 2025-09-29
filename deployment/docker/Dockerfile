# 使用Python基础镜像
FROM python:3.11-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    bash \
    cron \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件和pip配置（变化频率低）
COPY requirements.txt .
COPY deployment/docker/pip.conf /etc/pip.conf

# 安装Python依赖
RUN pip install --upgrade pip && pip install -r requirements.txt

WORKDIR /app

# 复制整个应用目录
COPY app ./app

# 创建数据库目录（启动时会复制数据库文件）
RUN mkdir -p /app/app/database

# 暴露端口
EXPOSE 17263 5000

# 赋予脚本执行权限
RUN chmod +x /app/app/cronjob/start_services.sh /app/app/cronjob/start_incremental_sync_cron.sh /app/app/cronjob/sync_hive_jobs_incremental.py

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# 启动服务
CMD ["bash", "/app/app/cronjob/start_services.sh"]
