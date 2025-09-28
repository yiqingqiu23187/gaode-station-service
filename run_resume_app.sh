#!/bin/bash

# 简历管理应用启动脚本

echo "🚀 启动简历管理Web应用..."

# 检查Python版本
python_version=$(python3 --version 2>&1)
echo "Python版本: $python_version"

# 检查是否存在虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "📚 安装依赖包..."
pip install -r requirements_resume_app.txt

# 创建必要的目录
echo "📁 创建必要目录..."
mkdir -p uploads
mkdir -p logs

# 设置环境变量（如果.env文件不存在）
if [ ! -f ".env" ]; then
    echo "⚙️  创建环境配置文件..."
    cat > .env << EOF
# 数据库配置
DATABASE_URL=mysql://username:password@localhost:3306/resume_db

# MCP服务器配置
MCP_SERVER_URL=http://152.136.8.68:3001/mcp

# Flask配置
SECRET_KEY=your-secret-key-change-this-in-production
FLASK_ENV=development

# 日志级别
LOG_LEVEL=INFO
EOF
    echo "⚠️  请编辑 .env 文件配置正确的数据库连接信息"
fi

# 检查数据库连接（可选）
echo "🔍 检查配置..."
if command -v mysql &> /dev/null; then
    echo "✅ MySQL客户端已安装"
else
    echo "⚠️  MySQL客户端未安装，请确保数据库可访问"
fi

# 启动应用
echo "🌟 启动Web应用..."
echo "访问地址: http://localhost:5000"
echo "按 Ctrl+C 停止应用"
echo ""

# 加载环境变量并启动
export $(cat .env | grep -v '^#' | xargs)
python app.py
