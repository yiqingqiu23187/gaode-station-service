#!/bin/bash

# 高德地图服务站点查询工具 - 一键更新部署脚本
# 功能：从本地CSV更新开始，到远程服务器部署完成的完整自动化流程

set -e  # 遇到错误立即退出

# === 配置信息 ===
REMOTE_HOST="49.232.253.3"
REMOTE_USER="root"
REMOTE_PASSWORD="Smj,\`c6L2#E/UX"
REMOTE_PATH="/opt/gaode-service"
LOCAL_ARCHIVE="gaode-updated.tar.gz"
CSV_FILE="岗位位置信息底表.csv"
VENV_PATH=".venv"

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# === 步骤1：检查本地环境和文件 ===
check_local_environment() {
    log_info "检查本地环境..."
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi
    
    # 检查并创建虚拟环境
    if [ ! -d "$VENV_PATH" ]; then
        log_info "创建虚拟环境..."
        python3 -m venv "$VENV_PATH"
        log_info "虚拟环境创建完成 ✓"
        
        # 安装依赖
        if [ -f "requirements.txt" ]; then
            log_info "安装Python依赖..."
            "$VENV_PATH/bin/pip" install --upgrade pip --quiet
            "$VENV_PATH/bin/pip" install -r requirements.txt --quiet
            log_info "依赖安装完成 ✓"
        fi
    else
        log_info "虚拟环境已存在，跳过创建 ✓"
        
        # 检查是否需要更新依赖
        if [ -f "requirements.txt" ]; then
            log_info "检查Python依赖是否需要更新..."
            "$VENV_PATH/bin/pip" install -r requirements.txt --quiet
            log_info "依赖检查完成 ✓"
        fi
    fi
    
    # 检查CSV文件
    if [ ! -f "$CSV_FILE" ]; then
        log_error "未找到CSV文件: $CSV_FILE"
        log_warning "请确保您已手动更新了岗位位置信息底表.csv文件"
        exit 1
    fi
    
    # 检查必要的Python脚本
    for script in "add_coordinates.py" "database_setup.py"; do
        if [ ! -f "$script" ]; then
            log_error "未找到必要脚本: $script"
            exit 1
        fi
    done
    
    # 检查sshpass是否安装（用于自动化SSH）
    if ! command -v sshpass &> /dev/null; then
        log_warning "sshpass 未安装，将尝试安装..."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            if command -v brew &> /dev/null; then
                brew install hudochenkov/sshpass/sshpass
            else
                log_error "请安装 Homebrew 或手动安装 sshpass"
                exit 1
            fi
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # Linux
            sudo apt-get update && sudo apt-get install -y sshpass
        else
            log_error "不支持的操作系统，请手动安装 sshpass"
            exit 1
        fi
    fi
    
    log_info "本地环境检查完成 ✓"
}

# === 步骤2：处理本地数据 ===
process_local_data() {
    log_info "开始处理本地数据..."
    
    # 确保虚拟环境已激活
    source "$VENV_PATH/bin/activate"
    
    # 备份旧的数据库文件（如果存在）
    if [ -f "stations.db" ]; then
        cp stations.db "stations.db.backup.$(date +%Y%m%d_%H%M%S)"
        log_info "已备份现有数据库文件"
    fi
    
    # 删除旧的处理文件
    if [ -f "岗位位置信息底表_with_coords.csv" ]; then
        rm "岗位位置信息底表_with_coords.csv"
        log_info "已删除旧的坐标文件"
    fi
    
    # 添加坐标信息
    log_info "正在为地址添加经纬度信息..."
    "$VENV_PATH/bin/python" add_coordinates.py
    
    if [ ! -f "岗位位置信息底表_with_coords.csv" ]; then
        log_error "坐标添加失败"
        exit 1
    fi
    log_info "坐标添加完成 ✓"
    
    # 创建数据库
    log_info "正在创建SQLite数据库..."
    "$VENV_PATH/bin/python" database_setup.py
    
    if [ ! -f "stations.db" ]; then
        log_error "数据库创建失败"
        exit 1
    fi
    log_info "数据库创建完成 ✓"
}

# === 步骤3：打包项目 ===
create_archive() {
    log_info "开始打包项目..."
    
    # 删除旧的压缩包
    if [ -f "$LOCAL_ARCHIVE" ]; then
        rm "$LOCAL_ARCHIVE"
    fi
    
    # 创建排除文件列表
    cat > .tar_exclude << EOF
*.tar.gz
.git
.venv
__pycache__
*.pyc
*.pyo
.DS_Store
.vscode
.idea
*.log
server.log
stations.db.backup.*
.gitignore
README.md
CLAUDE.md
EOF
    
    # 打包当前目录的内容（不包含目录本身）
    tar -czf "$LOCAL_ARCHIVE" \
        --exclude-from=.tar_exclude \
        -C . \
        .
    
    # 清理临时文件
    rm .tar_exclude
    
    if [ ! -f "$LOCAL_ARCHIVE" ]; then
        log_error "项目打包失败"
        exit 1
    fi
    
    log_info "项目打包完成 ✓ (文件: $LOCAL_ARCHIVE)"
}

# === 步骤4：上传到远程服务器 ===
upload_to_remote() {
    log_info "开始上传到远程服务器..."
    
    # 测试SSH连接
    log_info "测试SSH连接..."
    if ! sshpass -p "$REMOTE_PASSWORD" ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" "echo 'SSH连接测试成功'" > /dev/null 2>&1; then
        log_error "SSH连接失败，请检查服务器信息"
        exit 1
    fi
    
    # 在远程服务器创建目录
    sshpass -p "$REMOTE_PASSWORD" ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" "mkdir -p $REMOTE_PATH"
    
    # 上传压缩包
    log_info "正在上传压缩包..."
    if ! sshpass -p "$REMOTE_PASSWORD" scp -o StrictHostKeyChecking=no "$LOCAL_ARCHIVE" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/"; then
        log_error "文件上传失败"
        exit 1
    fi
    
    log_info "文件上传完成 ✓"
}

# === 步骤5：远程部署 ===
deploy_on_remote() {
    log_info "开始远程部署..."
    
    # 创建远程部署脚本
    REMOTE_DEPLOY_SCRIPT=$(cat << 'DEPLOY_EOF'
#!/bin/bash
set -e

ARCHIVE_NAME="gaode-updated.tar.gz"
SERVICE_DIR="/opt/gaode-service"

echo "开始远程部署流程..."

# 创建部署目录
mkdir -p "$SERVICE_DIR"
cd "$SERVICE_DIR"

# 停止现有服务
echo "停止现有Docker服务..."
if [ -f "docker-compose.yml" ]; then
    docker-compose down || true
fi

# 清理旧容器（如果存在）
echo "清理旧容器..."
docker stop gaode-station-service || true
docker rm gaode-station-service || true

# 解压新版本
echo "解压新版本..."
tar -xzf "$ARCHIVE_NAME"

# 检查必要文件
if [ ! -f "docker-compose.yml" ] || [ ! -f "Dockerfile" ] || [ ! -f "stations.db" ]; then
    echo "错误: 缺少必要的部署文件"
    exit 1
fi

# 构建并启动服务
echo "构建并启动Docker服务..."
docker-compose up -d

# 等待服务启动
echo "等待服务启动..."
sleep 15

# 检查服务状态
if docker-compose ps | grep -q "Up"; then
    echo "✅ 远程部署成功！"
    echo "服务地址: http://$(hostname -I | awk '{print $1}'):17263"
    echo "查看日志: cd $SERVICE_DIR && docker-compose logs -f"
else
    echo "❌ 远程部署失败，查看日志:"
    docker-compose logs
    exit 1
fi

# 清理
echo "清理临时文件..."
cd "$SERVICE_DIR"
rm -f "$ARCHIVE_NAME"

echo "远程部署完成！"
DEPLOY_EOF
)
    
    # 执行远程部署
    if ! sshpass -p "$REMOTE_PASSWORD" ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" "$REMOTE_DEPLOY_SCRIPT"; then
        log_error "远程部署失败"
        exit 1
    fi
    
    log_info "远程部署完成 ✓"
}

# === 步骤6：清理本地文件 ===
cleanup_local() {
    log_info "清理本地临时文件..."
    
    # 删除压缩包
    if [ -f "$LOCAL_ARCHIVE" ]; then
        rm "$LOCAL_ARCHIVE"
        log_info "已删除本地压缩包"
    fi
}

# === 主函数 ===
main() {
    echo "========================================"
    echo "  高德地图服务站点查询工具"
    echo "  一键更新部署脚本"
    echo "========================================"
    echo ""
    
    log_info "开始执行一键更新部署..."
    
    check_local_environment
    echo ""
    
    process_local_data
    echo ""
    
    create_archive
    echo ""
    
    upload_to_remote
    echo ""
    
    deploy_on_remote
    echo ""
    
    cleanup_local
    echo ""
    
    echo "========================================"
    log_info "🎉 一键更新部署完成！"
    echo ""
    log_info "服务地址: http://$REMOTE_HOST:17263"
    log_info "查看远程日志: ssh $REMOTE_USER@$REMOTE_HOST 'cd $REMOTE_PATH && docker-compose logs -f'"
    echo "========================================"
}

# 执行主函数
main "$@" 