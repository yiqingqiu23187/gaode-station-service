FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    bash \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件（变化频率低）
COPY requirements.txt .

# 安装Python依赖 (使用国内镜像源)
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn -r requirements.txt

# 最后复制应用代码（变化频率高）
COPY . .

# 暴露端口
EXPOSE 17263
EXPOSE 5000

# 赋予启动脚本执行权限并作为容器入口
RUN chmod +x /app/start_services.sh || true

# 同时启动 MCP 服务与控制面板服务
CMD ["bash", "/app/start_services.sh"] 