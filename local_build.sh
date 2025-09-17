#!/bin/bash

# 高德地图服务站点查询工具 - 本地构建脚本
# 功能：数据处理、Docker镜像构建和打包

set -e  # 遇到错误立即退出

# === 配置信息 ===
IMAGE_NAME="gaode-station-service"
IMAGE_TAG="latest"
IMAGE_TAR="${IMAGE_NAME}-${IMAGE_TAG}.tar"
COMPOSE_FILE="docker-compose.prod.yml"
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

# === 步骤1：检查本地环境 ===
check_local_environment() {
    log_step "检查本地环境..."

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi

    # 检查Docker是否运行
    if ! docker info &> /dev/null; then
        log_error "Docker 未运行，请启动 Docker"
        exit 1
    fi

    # 检查Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi

    # 检查带坐标的CSV文件
    COORDS_CSV="岗位位置信息底表_with_coords.csv"
    if [ ! -f "$COORDS_CSV" ]; then
        log_error "未找到带坐标的CSV文件: $COORDS_CSV"
        exit 1
    fi

    # 检查必要文件
    for file in "Dockerfile" "requirements.txt" "database_setup.py"; do
        if [ ! -f "$file" ]; then
            log_error "未找到必要文件: $file"
            exit 1
        fi
    done

    log_info "本地环境检查完成 ✓"
}

# === 步骤2：处理本地数据 ===
process_local_data() {
    log_step "处理本地数据..."

    # 创建虚拟环境（用于数据处理）
    if [ ! -d ".venv" ]; then
        log_info "创建虚拟环境..."
        python3 -m venv .venv

        if [ -f "requirements.txt" ]; then
            log_info "安装Python依赖..."
            .venv/bin/pip install --upgrade pip --quiet
            .venv/bin/pip install -r requirements.txt --quiet
        fi
    fi

    # 激活虚拟环境并处理数据
    source .venv/bin/activate

    # 检查现有数据库是否包含完整数据
    if [ -f "stations.db" ]; then
        log_info "检查现有数据库..."

        # 检查数据库中的岗位数量
        JOB_COUNT=$(python3 -c "
import sqlite3
try:
    conn = sqlite3.connect('stations.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM job_positions')
    count = cursor.fetchone()[0]
    conn.close()
    print(count)
except:
    print(0)
" 2>/dev/null || echo "0")

        # 检查是否有北京数据
        BEIJING_COUNT=$(python3 -c "
import sqlite3
try:
    conn = sqlite3.connect('stations.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM job_positions WHERE city = \"北京\"')
    count = cursor.fetchone()[0]
    conn.close()
    print(count)
except:
    print(0)
" 2>/dev/null || echo "0")

        # 检查是否有外卖数据
        WAIMAI_COUNT=$(python3 -c "
import sqlite3
try:
    conn = sqlite3.connect('stations.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM job_positions WHERE job_type = \"美团外卖骑手\"')
    count = cursor.fetchone()[0]
    conn.close()
    print(count)
except:
    print(0)
" 2>/dev/null || echo "0")

        log_info "现有数据库统计: 总岗位${JOB_COUNT}个, 北京${BEIJING_COUNT}个, 外卖${WAIMAI_COUNT}个"

        # 如果数据库包含完整数据（>1000个岗位，包含北京和外卖数据），则跳过重建
        if [ "$JOB_COUNT" -gt 1000 ] && [ "$BEIJING_COUNT" -gt 500 ] && [ "$WAIMAI_COUNT" -gt 70 ]; then
            log_info "检测到完整数据库，跳过重建，直接使用现有数据库 ✓"
            deactivate
            log_info "本地数据处理完成 ✓"
            return
        else
            log_warning "数据库不完整，将重新创建"
            # 备份旧的数据库文件
            cp stations.db "stations.db.backup.$(date +%Y%m%d_%H%M%S)"
            log_info "已备份现有数据库文件"
        fi
    fi

    # 创建数据库
    log_info "正在创建SQLite数据库..."
    python database_setup.py

    if [ ! -f "stations.db" ]; then
        log_error "数据库创建失败"
        exit 1
    fi

    # 检查是否需要添加北京数据和外卖数据
    log_info "检查是否需要添加额外数据..."

    # 检查北京数据
    BEIJING_AFTER=$(python3 -c "
import sqlite3
try:
    conn = sqlite3.connect('stations.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM job_positions WHERE city = \"北京\"')
    count = cursor.fetchone()[0]
    conn.close()
    print(count)
except:
    print(0)
" 2>/dev/null || echo "0")

    if [ "$BEIJING_AFTER" -eq 0 ] && [ -f "beijing_data_processing_v2.py" ]; then
        log_info "添加北京岗位数据..."
        python beijing_data_processing_v2.py
    fi

    # 检查外卖数据
    WAIMAI_AFTER=$(python3 -c "
import sqlite3
try:
    conn = sqlite3.connect('stations.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM job_positions WHERE job_type LIKE \"%外卖%\"')
    count = cursor.fetchone()[0]
    conn.close()
    print(count)
except:
    print(0)
" 2>/dev/null || echo "0")

    if [ "$WAIMAI_AFTER" -eq 0 ] && [ -f "waimai_data_processing.py" ]; then
        log_info "添加外卖岗位数据..."
        python waimai_data_processing.py

        # 修正外卖岗位类型
        python3 -c "
import sqlite3
conn = sqlite3.connect('stations.db')
cursor = conn.cursor()
cursor.execute('UPDATE job_positions SET job_type = \"美团外卖骑手\" WHERE job_type = \"美团外卖\"')
conn.commit()
conn.close()
print('已修正外卖岗位类型')
"
    fi

    deactivate  # 退出虚拟环境
    log_info "本地数据处理完成 ✓"
}

# === 步骤3：创建生产环境docker-compose文件 ===
create_production_compose() {
    log_step "创建生产环境配置文件..."

    cat > "$COMPOSE_FILE" << EOF
version: '3.8'

services:
  gaode-station-service:
    image: ${IMAGE_NAME}:${IMAGE_TAG}
    ports:
      - "17263:17263"
      - "5000:5000"
    restart: unless-stopped
    container_name: gaode-station-service
    volumes:
      - ./stations.db:/app/stations.db
      - ./岗位属性.csv:/app/岗位属性.csv
      - ./岗位位置信息底表_with_coords.csv:/app/岗位位置信息底表_with_coords.csv
    environment:
      - FASTMCP_HOST=0.0.0.0
      - FASTMCP_PORT=17263
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
EOF

    log_info "生产环境配置文件创建完成 ✓"
}

# === 步骤4：本地构建Docker镜像 ===
build_docker_image() {
    log_step "开始构建Docker镜像..."

    log_info "正在构建镜像 ${IMAGE_NAME}:${IMAGE_TAG}..."

    # 构建镜像（指定x86架构）
    if ! docker build --platform linux/amd64 -t "${IMAGE_NAME}:${IMAGE_TAG}" .; then
        log_error "Docker镜像构建失败"
        exit 1
    fi

    log_info "Docker镜像构建完成 ✓"

    # 显示镜像信息
    docker images "${IMAGE_NAME}:${IMAGE_TAG}"
}

# === 步骤5：保存镜像为tar文件 ===
save_docker_image() {
    log_step "保存Docker镜像..."

    # 删除旧的镜像文件
    if [ -f "$IMAGE_TAR" ]; then
        rm "$IMAGE_TAR"
    fi

    log_info "正在保存镜像为 $IMAGE_TAR..."
    if ! docker save "${IMAGE_NAME}:${IMAGE_TAG}" -o "$IMAGE_TAR"; then
        log_error "镜像保存失败"
        exit 1
    fi

    # 显示文件大小
    IMAGE_SIZE=$(du -h "$IMAGE_TAR" | cut -f1)
    log_info "镜像保存完成 ✓ (大小: $IMAGE_SIZE)"
}

# === 步骤6：生成构建信息 ===
generate_build_info() {
    log_step "生成构建信息..."

    # 获取镜像信息
    IMAGE_ID=$(docker images --format "{{.ID}}" "${IMAGE_NAME}:${IMAGE_TAG}")
    BUILD_TIME=$(date "+%Y-%m-%d %H:%M:%S")
    IMAGE_SIZE=$(du -h "$IMAGE_TAR" | cut -f1)

    # 生成构建信息JSON
    cat > "$BUILD_INFO_FILE" << EOF
{
  "image_name": "${IMAGE_NAME}",
  "image_tag": "${IMAGE_TAG}",
  "image_id": "${IMAGE_ID}",
  "image_tar": "${IMAGE_TAR}",
  "compose_file": "${COMPOSE_FILE}",
  "build_time": "${BUILD_TIME}",
  "image_size": "${IMAGE_SIZE}",
  "data_files": [
    "stations.db",
    "岗位属性.csv",
    "岗位位置信息底表_with_coords.csv"
  ]
}
EOF

    log_info "构建信息已保存到 $BUILD_INFO_FILE"
}

# === 主函数 ===
main() {
    echo "========================================"
    echo "  高德地图服务站点查询工具"
    echo "  本地构建脚本 v2.0"
    echo "========================================"
    echo ""

    log_info "开始执行本地构建..."

    check_local_environment
    echo ""

    process_local_data
    echo ""

    create_production_compose
    echo ""

    build_docker_image
    echo ""

    save_docker_image
    echo ""

    generate_build_info
    echo ""

    echo "========================================"
    log_info "🎉 本地构建完成！"
    echo ""
    log_info "构建产物："
    log_info "  - Docker镜像: ${IMAGE_NAME}:${IMAGE_TAG}"
    log_info "  - 镜像文件: $IMAGE_TAR"
    log_info "  - 配置文件: $COMPOSE_FILE"
    log_info "  - 构建信息: $BUILD_INFO_FILE"
    log_info "  - 数据库文件: stations.db"
    echo ""
    log_info "下一步: 运行 './remote_deploy.sh' 进行远程部署"
    echo "========================================"
}

# 执行主函数
main "$@"
