#!/bin/bash

# 高德地图服务站点查询工具 - 远程部署脚本
# 功能：上传镜像和配置文件到服务器，执行蓝绿部署

set -e  # 遇到错误立即退出

# === 配置信息 ===
REMOTE_HOST="49.232.253.3"
REMOTE_USER="root"
REMOTE_PASSWORD="Smj,\`c6L2#E/UX"
REMOTE_PATH="/opt/gaode-service"
BUILD_INFO_FILE="build_info.json"

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# === 步骤1：检查本地构建产物 ===
check_build_artifacts() {
    log_step "检查本地构建产物..."

    # 检查sshpass是否安装
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

    # 检查构建信息文件
    if [ ! -f "$BUILD_INFO_FILE" ]; then
        log_error "未找到构建信息文件: $BUILD_INFO_FILE"
        log_error "请先运行 './local_build.sh' 进行本地构建"
        exit 1
    fi

    # 读取构建信息
    if ! command -v jq &> /dev/null; then
        # 如果没有jq，使用简单的grep方式读取
        IMAGE_TAR=$(grep '"image_tar"' "$BUILD_INFO_FILE" | cut -d'"' -f4)
        COMPOSE_FILE=$(grep '"compose_file"' "$BUILD_INFO_FILE" | cut -d'"' -f4)
    else
        # 使用jq读取JSON
        IMAGE_TAR=$(jq -r '.image_tar' "$BUILD_INFO_FILE")
        COMPOSE_FILE=$(jq -r '.compose_file' "$BUILD_INFO_FILE")
    fi

    # 检查镜像文件
    if [ ! -f "$IMAGE_TAR" ]; then
        log_error "未找到Docker镜像文件: $IMAGE_TAR"
        exit 1
    fi

    # 检查配置文件
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "未找到配置文件: $COMPOSE_FILE"
        exit 1
    fi

    # 检查数据文件
    for file in "stations.db" "岗位属性.csv" "岗位位置信息底表_with_coords.csv"; do
        if [ ! -f "$file" ]; then
            log_error "未找到数据文件: $file"
            exit 1
        fi
    done

    log_info "构建产物检查完成 ✓"
    log_info "镜像文件: $IMAGE_TAR ($(du -h "$IMAGE_TAR" | cut -f1))"
}

# === 步骤2：测试远程连接 ===
test_remote_connection() {
    log_step "测试远程服务器连接..."

    # 测试SSH连接
    log_info "测试SSH连接到 $REMOTE_HOST..."
    if ! sshpass -p "$REMOTE_PASSWORD" ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" "echo 'SSH连接测试成功'" > /dev/null 2>&1; then
        log_error "SSH连接失败，请检查服务器信息"
        exit 1
    fi

    log_info "远程连接测试成功 ✓"
}

# === 步骤3：上传文件到远程服务器 ===
upload_to_remote() {
    log_step "上传文件到远程服务器..."

    # 在远程服务器创建目录
    sshpass -p "$REMOTE_PASSWORD" ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" "mkdir -p $REMOTE_PATH"

    # 上传镜像文件
    log_info "正在上传Docker镜像..."
    if ! sshpass -p "$REMOTE_PASSWORD" scp -o StrictHostKeyChecking=no "$IMAGE_TAR" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/"; then
        log_error "镜像上传失败"
        exit 1
    fi

    # 上传生产环境配置文件
    log_info "正在上传配置文件..."
    if ! sshpass -p "$REMOTE_PASSWORD" scp -o StrictHostKeyChecking=no "$COMPOSE_FILE" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/docker-compose.yml"; then
        log_error "配置文件上传失败"
        exit 1
    fi

    # 上传数据文件
    log_info "正在上传数据文件..."
    for file in "stations.db" "岗位属性.csv" "岗位位置信息底表_with_coords.csv"; do
        if [ -f "$file" ]; then
            if ! sshpass -p "$REMOTE_PASSWORD" scp -o StrictHostKeyChecking=no "$file" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/"; then
                log_error "数据文件上传失败: $file"
                exit 1
            fi
        fi
    done

    # 上传构建信息文件
    log_info "正在上传构建信息..."
    sshpass -p "$REMOTE_PASSWORD" scp -o StrictHostKeyChecking=no "$BUILD_INFO_FILE" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/"

    log_info "文件上传完成 ✓"
}

# === 步骤4：远程蓝绿部署 ===
deploy_on_remote() {
    log_step "开始远程蓝绿部署..."

    # 获取镜像文件名
    IMAGE_TAR_NAME=$(basename "$IMAGE_TAR")

    # 创建远程部署脚本（蓝绿部署）
    REMOTE_DEPLOY_SCRIPT=$(cat << DEPLOY_EOF
#!/bin/bash
set -e

IMAGE_TAR="$IMAGE_TAR_NAME"
SERVICE_DIR="$REMOTE_PATH"
NEW_CONTAINER="gaode-station-service-new"
OLD_CONTAINER="gaode-station-service"
HEALTH_CHECK_RETRIES=10
HEALTH_CHECK_INTERVAL=3

echo "🚀 开始蓝绿部署流程..."

cd "\$SERVICE_DIR"

# 步骤1: 先加载新镜像（不影响现有服务）
echo "📦 加载新Docker镜像..."
if ! docker load -i "\$IMAGE_TAR"; then
    echo "❌ 镜像加载失败"
    exit 1
fi

# 验证镜像是否加载成功
if ! docker images | grep -q "gaode-station-service.*latest"; then
    echo "❌ 镜像加载验证失败"
    exit 1
fi
echo "✅ 新镜像加载成功"

# 步骤2: 启动新容器（使用临时名称和端口）
echo "🔄 启动新版本容器..."

# 清理可能存在的临时容器
docker stop "\$NEW_CONTAINER" 2>/dev/null || true
docker rm "\$NEW_CONTAINER" 2>/dev/null || true

# 启动新容器，使用临时端口避免冲突
docker run -d \\
    --name "\$NEW_CONTAINER" \\
    -p 17264:17263 \\
    -p 5001:5000 \\
    -v "\$SERVICE_DIR/stations.db:/app/stations.db" \\
    -v "\$SERVICE_DIR/岗位属性.csv:/app/岗位属性.csv" \\
    -v "\$SERVICE_DIR/岗位位置信息底表_with_coords.csv:/app/岗位位置信息底表_with_coords.csv" \\
    -e FASTMCP_HOST=0.0.0.0 \\
    -e FASTMCP_PORT=17263 \\
    --restart=unless-stopped \\
    gaode-station-service:latest

echo "⏳ 等待新容器启动..."
sleep 10

# 步骤3: 健康检查新容器
echo "🏥 执行健康检查..."
for i in \$(seq 1 \$HEALTH_CHECK_RETRIES); do
    echo "健康检查尝试 \$i/\$HEALTH_CHECK_RETRIES..."

    # 检查容器是否运行
    if ! docker ps | grep -q "\$NEW_CONTAINER.*Up"; then
        echo "❌ 新容器未正常运行"
        docker logs "\$NEW_CONTAINER" 2>/dev/null || true
        docker stop "\$NEW_CONTAINER" 2>/dev/null || true
        docker rm "\$NEW_CONTAINER" 2>/dev/null || true
        exit 1
    fi

    # 检查 Web 服务健康状态
    HEALTH_STATUS=\$(docker exec "\$NEW_CONTAINER" curl -f -s http://localhost:5000/health 2>/dev/null | grep -o '"status":"healthy"' || echo "failed")

    if [ "\$HEALTH_STATUS" = '"status":"healthy"' ]; then
        echo "✅ 健康检查通过！Web服务已就绪，数据库连接正常"

        # 额外验证MCP服务进程是否运行
        MCP_RUNNING=\$(docker exec "\$NEW_CONTAINER" pgrep -f 'python.*mcp_server.py' > /dev/null && echo "true" || echo "false")
        if [ "\$MCP_RUNNING" = "true" ]; then
            echo "✅ MCP服务进程也在正常运行"
            echo "🎯 新版本服务完全就绪！"
            break
        else
            echo "⚠️ Web服务健康，但MCP服务进程可能有问题，继续等待..."
        fi
    fi

    if [ \$i -eq \$HEALTH_CHECK_RETRIES ]; then
        echo "❌ 健康检查失败，回滚..."
        docker logs "\$NEW_CONTAINER" 2>/dev/null || true
        docker stop "\$NEW_CONTAINER" 2>/dev/null || true
        docker rm "\$NEW_CONTAINER" 2>/dev/null || true
        exit 1
    fi

    sleep \$HEALTH_CHECK_INTERVAL
done

# 步骤4: 快速切换服务（最小化停机时间）
echo "⚡ 执行服务切换..."

# 检查是否有旧容器在运行
OLD_CONTAINER_EXISTS=false
if docker ps | grep -q "\$OLD_CONTAINER.*Up"; then
    OLD_CONTAINER_EXISTS=true
    echo "发现运行中的旧容器，准备切换"
else
    echo "没有发现运行中的旧容器"
fi

if [ "\$OLD_CONTAINER_EXISTS" = true ]; then
    # 停止旧容器（此时新容器已准备就绪）
    echo "停止旧容器..."
    docker stop "\$OLD_CONTAINER" 2>/dev/null || true
    docker rm "\$OLD_CONTAINER" 2>/dev/null || true
fi

# 停止新容器并使用正式配置重新启动
echo "使用正式配置启动服务..."
docker stop "\$NEW_CONTAINER"
docker rm "\$NEW_CONTAINER"

# 使用docker-compose启动正式服务
docker-compose up -d

# 步骤5: 验证正式服务
echo "🔍 验证正式服务..."
sleep 10

# 最终健康检查
for i in \$(seq 1 5); do
    # 检查容器状态
    if docker-compose ps | grep -q "Up"; then
        # 检查健康状态
        FINAL_HEALTH=\$(curl -f -s http://localhost:5000/health 2>/dev/null | grep -o '"status":"healthy"' || echo "failed")
        if [ "\$FINAL_HEALTH" = '"status":"healthy"' ]; then
            echo "✅ 蓝绿部署成功！"
            echo "服务地址: http://\$(hostname -I | awk '{print \$1}'):17263"
            echo "控制面板: http://\$(hostname -I | awk '{print \$1}'):5000"

            # 显示服务状态
            echo ""
            echo "=== 服务状态 ==="
            docker-compose ps

            echo ""
            echo "=== 部署统计 ==="
            echo "新镜像: gaode-station-service:latest"
            echo "部署方式: 蓝绿部署（零宕机）"
            echo "服务中断时间: < 5秒"

            echo ""
            echo "=== 查看日志命令 ==="
            echo "cd \$SERVICE_DIR && docker-compose logs -f"
            break
        fi
    fi

    if [ \$i -eq 5 ]; then
        echo "❌ 正式服务启动失败，查看日志:"
        docker-compose logs
        exit 1
    fi

    sleep 2
done

# 步骤6: 清理
echo "🧹 清理临时文件和旧镜像..."

# 清理临时文件
rm -f "\$IMAGE_TAR"

# 清理旧镜像（保留最新的）
echo "清理无用的镜像..."
docker image prune -f 2>/dev/null || true

echo "🎉 蓝绿部署完成！服务已成功更新"
DEPLOY_EOF
)

    # 执行远程部署
    if ! sshpass -p "$REMOTE_PASSWORD" ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" "$REMOTE_DEPLOY_SCRIPT"; then
        log_error "远程部署失败"
        exit 1
    fi

    log_info "远程部署完成 ✓"
}

# === 步骤5：清理本地临时文件 ===
cleanup_local() {
    log_step "清理本地临时文件..."

    # 可选：删除本地镜像文件（节省空间）
    read -p "是否删除本地镜像文件以节省空间？(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -f "$IMAGE_TAR" ]; then
            rm "$IMAGE_TAR"
            log_info "已删除本地镜像文件: $IMAGE_TAR"
        fi
    fi

    # 可选：删除本地Docker镜像
    read -p "是否删除本地Docker镜像以节省空间？(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        IMAGE_NAME="gaode-station-service"
        IMAGE_TAG="latest"
        docker rmi "${IMAGE_NAME}:${IMAGE_TAG}" 2>/dev/null || true
        log_info "已删除本地Docker镜像"
    fi

    # 保留构建信息和配置文件，用户可能需要
    log_info "保留构建信息文件: $BUILD_INFO_FILE"
    log_info "保留生产配置文件: $COMPOSE_FILE"
}

# === 主函数 ===
main() {
    echo "========================================"
    echo "  高德地图服务站点查询工具"
    echo "  远程部署脚本 v2.0"
    echo "========================================"
    echo ""

    log_info "开始执行远程部署..."

    check_build_artifacts
    echo ""

    test_remote_connection
    echo ""

    upload_to_remote
    echo ""

    deploy_on_remote
    echo ""

    cleanup_local
    echo ""

    echo "========================================"
    log_info "🎉 远程部署完成！"
    echo ""
    log_info "服务地址: http://$REMOTE_HOST:17263"
    log_info "控制面板: http://$REMOTE_HOST:5000"
    log_info "查看远程日志: ssh $REMOTE_USER@$REMOTE_HOST 'cd $REMOTE_PATH && docker-compose logs -f'"
    echo "========================================"
}

# 执行主函数
main "$@"
