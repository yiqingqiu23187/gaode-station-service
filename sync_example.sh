#!/bin/bash

# 数据库同步使用示例脚本
# 演示如何使用数据库同步工具

echo "========================================"
echo "  高德地图服务数据库同步工具"
echo "  使用示例脚本"
echo "========================================"
echo ""

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[示例]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[步骤]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[提示]${NC} $1"
}

# 检查工具是否存在
check_tools() {
    log_step "检查同步工具..."
    
    if [ ! -f "./sync_database.sh" ]; then
        echo "错误: 未找到 sync_database.sh"
        exit 1
    fi
    
    if [ ! -f "./sync_database.py" ]; then
        echo "错误: 未找到 sync_database.py"
        exit 1
    fi
    
    log_info "同步工具检查完成 ✓"
}

# 显示使用选项
show_options() {
    echo ""
    log_step "请选择要执行的操作:"
    echo ""
    echo "1) 测试连接 (Bash脚本)"
    echo "2) 测试连接 (Python脚本)"
    echo "3) 仅比较数据库差异"
    echo "4) 执行完整同步 (Bash脚本)"
    echo "5) 执行完整同步 (Python脚本)"
    echo "6) 查看备份文件"
    echo "7) 查看本地数据库统计"
    echo "8) 显示帮助信息"
    echo "0) 退出"
    echo ""
}

# 测试连接 - Bash
test_connection_bash() {
    log_step "使用Bash脚本测试连接..."
    ./sync_database.sh --dry-run
}

# 测试连接 - Python
test_connection_python() {
    log_step "使用Python脚本测试连接..."
    python3 sync_database.py --dry-run
}

# 比较数据库差异
compare_databases() {
    log_step "比较本地和远程数据库差异..."
    python3 sync_database.py --compare-only
}

# 完整同步 - Bash
full_sync_bash() {
    log_step "使用Bash脚本执行完整同步..."
    log_warning "这将替换本地数据库，确认继续吗? (y/N)"
    read -r confirm
    if [[ $confirm =~ ^[Yy]$ ]]; then
        ./sync_database.sh
    else
        log_info "已取消同步操作"
    fi
}

# 完整同步 - Python
full_sync_python() {
    log_step "使用Python脚本执行完整同步..."
    log_warning "这将替换本地数据库，确认继续吗? (y/N)"
    read -r confirm
    if [[ $confirm =~ ^[Yy]$ ]]; then
        python3 sync_database.py
    else
        log_info "已取消同步操作"
    fi
}

# 查看备份文件
show_backups() {
    log_step "查看备份文件..."
    
    if [ -d "./db_backups" ]; then
        echo ""
        echo "备份文件列表:"
        ls -la ./db_backups/
        echo ""
        
        backup_count=$(ls -1 ./db_backups/*.db 2>/dev/null | wc -l)
        log_info "共找到 $backup_count 个备份文件"
    else
        log_info "备份目录不存在，尚未执行过同步操作"
    fi
}

# 查看本地数据库统计
show_local_stats() {
    log_step "查看本地数据库统计..."
    
    if [ -f "./stations.db" ]; then
        echo ""
        echo "=== 根目录数据库统计 (./stations.db) ==="
        
        # 表数量
        table_count=$(sqlite3 ./stations.db "SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
        echo "表数量: $table_count"
        
        # 检查job_positions表
        if sqlite3 ./stations.db "SELECT name FROM sqlite_master WHERE type='table' AND name='job_positions';" | grep -q job_positions; then
            job_count=$(sqlite3 ./stations.db "SELECT COUNT(*) FROM job_positions;")
            recruiting_count=$(sqlite3 ./stations.db "SELECT COUNT(*) FROM job_positions WHERE currently_recruiting='是';")
            city_count=$(sqlite3 ./stations.db "SELECT COUNT(DISTINCT city) FROM job_positions;")
            
            echo "总岗位数: $job_count"
            echo "正在招聘: $recruiting_count"
            echo "涉及城市: $city_count"
        else
            echo "未找到job_positions表"
        fi
    else
        log_info "根目录数据库文件不存在"
    fi
    
    if [ -f "./data/stations.db" ]; then
        echo ""
        echo "=== data目录数据库统计 (./data/stations.db) ==="
        
        table_count=$(sqlite3 ./data/stations.db "SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
        echo "表数量: $table_count"
        
        if sqlite3 ./data/stations.db "SELECT name FROM sqlite_master WHERE type='table' AND name='job_positions';" | grep -q job_positions; then
            job_count=$(sqlite3 ./data/stations.db "SELECT COUNT(*) FROM job_positions;")
            recruiting_count=$(sqlite3 ./data/stations.db "SELECT COUNT(*) FROM job_positions WHERE currently_recruiting='是';")
            city_count=$(sqlite3 ./data/stations.db "SELECT COUNT(DISTINCT city) FROM job_positions;")
            
            echo "总岗位数: $job_count"
            echo "正在招聘: $recruiting_count"
            echo "涉及城市: $city_count"
        else
            echo "未找到job_positions表"
        fi
    else
        log_info "data目录数据库文件不存在"
    fi
}

# 显示帮助信息
show_help() {
    log_step "显示帮助信息..."
    echo ""
    echo "=== Bash脚本帮助 ==="
    ./sync_database.sh --help
    echo ""
    echo "=== Python脚本帮助 ==="
    python3 sync_database.py --help
}

# 主循环
main_loop() {
    while true; do
        show_options
        read -p "请输入选项 (0-8): " choice
        echo ""
        
        case $choice in
            1)
                test_connection_bash
                ;;
            2)
                test_connection_python
                ;;
            3)
                compare_databases
                ;;
            4)
                full_sync_bash
                ;;
            5)
                full_sync_python
                ;;
            6)
                show_backups
                ;;
            7)
                show_local_stats
                ;;
            8)
                show_help
                ;;
            0)
                log_info "退出程序"
                exit 0
                ;;
            *)
                echo "无效选项，请重新选择"
                ;;
        esac
        
        echo ""
        echo "按回车键继续..."
        read -r
        echo ""
    done
}

# 主函数
main() {
    check_tools
    
    log_info "数据库同步工具使用示例"
    log_warning "请确保已阅读 DATABASE_SYNC_README.md 文档"
    
    main_loop
}

# 执行主函数
main "$@"
