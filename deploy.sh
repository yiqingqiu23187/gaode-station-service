#!/bin/bash

# 高德地图服务站点查询工具Docker部署脚本

echo "开始部署高德地图服务站点查询工具..."

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "错误: Docker未运行或未安装"
    exit 1
fi

# 检查是否已存在数据库文件
if [ ! -f "stations.db" ]; then
    echo "初始化数据库..."
    
    # 检查原始数据文件
    if [ ! -f "岗位位置信息底表.csv" ]; then
        echo "错误: 未找到原始数据文件 岗位位置信息底表.csv"
        exit 1
    fi
    
    # 运行数据初始化
    python3 add_coordinates.py
    python3 database_setup.py
    
    if [ ! -f "stations.db" ]; then
        echo "错误: 数据库初始化失败"
        exit 1
    fi
fi

# 停止现有容器
echo "停止现有容器..."
docker-compose down

# 构建并启动服务
echo "构建并启动服务..."
docker-compose up -d --build

# 等待服务启动
echo "等待服务启动..."
sleep 10

# 检查服务状态
if docker-compose ps | grep -q "Up"; then
    echo "✅ 部署成功！"
    echo "服务地址: http://localhost:17263"
    echo "查看日志: docker-compose logs -f"
    echo "停止服务: docker-compose down"
else
    echo "❌ 部署失败，请检查日志:"
    docker-compose logs
    exit 1
fi 