# 多阶段构建 - 构建阶段（指定x86架构）
FROM --platform=linux/amd64 python:3.11-alpine AS builder

# 安装构建时依赖
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    python3-dev

WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir --user \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --trusted-host pypi.tuna.tsinghua.edu.cn \
    -r requirements.txt

# 生产阶段
FROM python:3.11-alpine

WORKDIR /app

# 安装运行时依赖
RUN apk add --no-cache curl bash

# 从构建阶段复制Python包
COPY --from=builder /root/.local /usr/local

# 只复制必要的应用文件
COPY mcp_server.py web_server.py amap_utils.py database_setup.py start_services.sh ./

# 暴露端口
EXPOSE 17263 5000

# 赋予启动脚本执行权限
RUN chmod +x /app/start_services.sh

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# 启动服务
CMD ["bash", "/app/start_services.sh"] 