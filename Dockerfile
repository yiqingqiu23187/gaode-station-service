# 使用Debian基础镜像（指定x86架构）
FROM --platform=linux/amd64 python:3.11-slim

# 更换为清华大学镜像源（兼容新版Debian）
RUN echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    bash \
    cron \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件和pip配置（变化频率低）
COPY requirements.txt .
COPY pip.conf /etc/pip.conf

# 安装Python依赖 (使用国内镜像源)
RUN pip install --upgrade pip && pip install -r requirements.txt

WORKDIR /app

# 只复制必要的应用文件
COPY mcp_server.py web_server.py amap_utils.py start_services.sh sync_hive_jobs_incremental.py start_incremental_sync_cron.sh ./

# 暴露端口
EXPOSE 17263 5000

# 赋予脚本执行权限
RUN chmod +x /app/start_services.sh /app/start_incremental_sync_cron.sh /app/sync_hive_jobs_incremental.py

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# 启动服务
CMD ["bash", "/app/start_services.sh"] 