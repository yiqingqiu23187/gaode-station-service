#!/bin/bash

# 从远程服务器拉取最新的 stations.db 数据库
# 功能：下载远程数据库并备份本地旧数据库

set -e  # 遇到错误立即退出

# === 配置信息 ===
REMOTE_HOST="49.232.253.3"
REMOTE_USER="root"
REMOTE_PASSWORD="Smj,\`c6L2#E/UX"
REMOTE_DB_PATH="/opt/gaode-service/stations.db/stations.db"
LOCAL_DB_PATH="app/database/stations.db"
BACKUP_DIR="app/database/db_backups"

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

# === 步骤1：检查依赖 ===
check_dependencies() {
    log_step "检查依赖工具..."

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

    # 检查sqlite3是否安装
    if ! command -v sqlite3 &> /dev/null; then
        log_error "sqlite3 未安装，请先安装 sqlite3"
        exit 1
    fi

    log_info "依赖检查完成 ✓"
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

    # 检查远程数据库文件是否存在
    log_info "检查远程数据库文件..."
    if ! sshpass -p "$REMOTE_PASSWORD" ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" "test -f $REMOTE_DB_PATH"; then
        log_error "远程数据库文件不存在: $REMOTE_DB_PATH"
        exit 1
    fi

    # 获取远程数据库文件大小
    REMOTE_SIZE=$(sshpass -p "$REMOTE_PASSWORD" ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" "du -h $REMOTE_DB_PATH | cut -f1")
    log_info "远程数据库文件大小: $REMOTE_SIZE"

    log_info "远程连接测试成功 ✓"
}

# === 步骤3：备份本地数据库 ===
backup_local_database() {
    log_step "备份本地数据库..."

    # 创建备份目录
    mkdir -p "$BACKUP_DIR"

    # 检查本地数据库是否存在
    if [ -f "$LOCAL_DB_PATH" ]; then
        # 生成备份文件名（带时间戳）
        TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
        BACKUP_FILE="$BACKUP_DIR/stations_backup_$TIMESTAMP.db"

        # 备份本地数据库
        cp "$LOCAL_DB_PATH" "$BACKUP_FILE"
        log_info "已备份本地数据库: $BACKUP_FILE"

        # 显示本地数据库统计信息
        if sqlite3 "$LOCAL_DB_PATH" "SELECT COUNT(*) FROM job_positions;" > /dev/null 2>&1; then
            LOCAL_COUNT=$(sqlite3 "$LOCAL_DB_PATH" "SELECT COUNT(*) FROM job_positions;")
            log_info "本地数据库记录数: $LOCAL_COUNT"
        fi
    else
        log_warning "本地数据库不存在，跳过备份"
    fi

    log_info "本地数据库备份完成 ✓"
}

# === 步骤4：从远程服务器下载数据库 ===
download_remote_database() {
    log_step "从远程服务器下载数据库..."

    # 下载远程数据库文件到临时位置
    TEMP_DB_FILE="./stations_remote_temp.db"

    log_info "正在下载远程数据库文件..."
    if ! sshpass -p "$REMOTE_PASSWORD" scp -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DB_PATH" "$TEMP_DB_FILE"; then
        log_error "数据库文件下载失败"
        exit 1
    fi

    # 验证下载的数据库文件
    log_info "验证下载的数据库文件..."
    if ! sqlite3 "$TEMP_DB_FILE" "SELECT COUNT(*) FROM sqlite_master;" > /dev/null 2>&1; then
        log_error "下载的数据库文件损坏或无效"
        rm -f "$TEMP_DB_FILE"
        exit 1
    fi

    # 检查数据库表结构
    TABLE_COUNT=$(sqlite3 "$TEMP_DB_FILE" "SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
    log_info "数据库包含 $TABLE_COUNT 个表"

    # 检查job_positions表的记录数
    if sqlite3 "$TEMP_DB_FILE" "SELECT name FROM sqlite_master WHERE type='table' AND name='job_positions';" | grep -q job_positions; then
        JOB_COUNT=$(sqlite3 "$TEMP_DB_FILE" "SELECT COUNT(*) FROM job_positions;")
        log_info "job_positions表包含 $JOB_COUNT 条记录"

        # 显示招聘状态统计
        RECRUITING_COUNT=$(sqlite3 "$TEMP_DB_FILE" "SELECT COUNT(*) FROM job_positions WHERE currently_recruiting='是';")
        log_info "正在招聘的岗位: $RECRUITING_COUNT"

        # 显示城市统计
        CITY_COUNT=$(sqlite3 "$TEMP_DB_FILE" "SELECT COUNT(DISTINCT city) FROM job_positions;")
        log_info "涉及城市数量: $CITY_COUNT"
    else
        log_warning "未找到job_positions表"
    fi

    log_info "远程数据库下载完成 ✓"
}

# === 步骤5：替换本地数据库 ===
replace_local_database() {
    log_step "替换本地数据库..."

    TEMP_DB_FILE="./stations_remote_temp.db"

    # 确保目标目录存在
    mkdir -p "$(dirname "$LOCAL_DB_PATH")"

    # 替换本地数据库文件
    if [ -f "$TEMP_DB_FILE" ]; then
        cp "$TEMP_DB_FILE" "$LOCAL_DB_PATH"
        log_info "已更新本地数据库: $LOCAL_DB_PATH"
    else
        log_error "临时数据库文件不存在"
        exit 1
    fi

    # 清理临时文件
    rm -f "$TEMP_DB_FILE"

    log_info "本地数据库替换完成 ✓"
}

# === 步骤6：验证同步结果 ===
verify_sync_result() {
    log_step "验证同步结果..."

    if [ -f "$LOCAL_DB_PATH" ]; then
        # 检查本地数据库
        TABLE_COUNT=$(sqlite3 "$LOCAL_DB_PATH" "SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
        log_info "本地数据库包含 $TABLE_COUNT 个表"

        if sqlite3 "$LOCAL_DB_PATH" "SELECT name FROM sqlite_master WHERE type='table' AND name='job_positions';" | grep -q job_positions; then
            JOB_COUNT=$(sqlite3 "$LOCAL_DB_PATH" "SELECT COUNT(*) FROM job_positions;")
            log_info "本地job_positions表包含 $JOB_COUNT 条记录"

            # 显示一些统计信息
            CITY_COUNT=$(sqlite3 "$LOCAL_DB_PATH" "SELECT COUNT(DISTINCT city) FROM job_positions;")
            RECRUITING_COUNT=$(sqlite3 "$LOCAL_DB_PATH" "SELECT COUNT(*) FROM job_positions WHERE currently_recruiting='是';")

            log_info "涉及城市数量: $CITY_COUNT"
            log_info "正在招聘的岗位: $RECRUITING_COUNT"

            # 显示前3条记录作为样例
            echo ""
            log_info "数据样例（前3条）:"
            sqlite3 -header -column "$LOCAL_DB_PATH" "SELECT id, job_type, recruiting_unit, city, currently_recruiting FROM job_positions LIMIT 3;"
        fi
    fi

    log_info "同步结果验证完成 ✓"
}

# === 步骤7：清理和总结 ===
cleanup_and_summary() {
    log_step "清理和总结..."

    # 清理临时文件
    rm -f ./stations_remote_temp.db

    # 显示备份文件位置
    if [ -d "$BACKUP_DIR" ]; then
        BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/*.db 2>/dev/null | wc -l)
        log_info "备份文件保存在: $BACKUP_DIR (共 $BACKUP_COUNT 个备份)"
    fi

    log_info "清理完成 ✓"
}

# === 主函数 ===
main() {
    echo "========================================"
    echo "  高德地图服务站点查询工具"
    echo "  数据库拉取脚本 v1.0"
    echo "========================================"
    echo ""

    log_info "开始从远程服务器拉取数据库..."
    echo ""

    check_dependencies
    echo ""

    test_remote_connection
    echo ""

    backup_local_database
    echo ""

    download_remote_database
    echo ""

    replace_local_database
    echo ""

    verify_sync_result
    echo ""

    cleanup_and_summary
    echo ""

    echo "========================================"
    log_info "🎉 数据库拉取完成！"
    echo ""
    log_info "本地数据库路径: $LOCAL_DB_PATH"
    log_info "备份目录: $BACKUP_DIR"
    echo "========================================"
}

# 执行主函数
main "$@"
