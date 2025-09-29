# 数据库同步工具使用说明

本项目提供了两个数据库同步工具，用于从远程服务器同步线上数据库到本地环境。

## 工具概述

### 1. sync_database.sh (Bash脚本)
- **功能**: 基础的数据库同步功能
- **特点**: 简单易用，依赖少
- **适用场景**: 快速同步，基础操作

### 2. sync_database.py (Python脚本)  
- **功能**: 高级数据库同步功能
- **特点**: 支持数据对比、增量分析、详细统计
- **适用场景**: 需要详细分析和对比的场景

## 环境要求

### 系统依赖
- **sshpass**: 用于SSH密码认证
- **sqlite3**: 用于数据库操作
- **Python 3.6+**: 仅Python脚本需要

### 安装依赖

#### macOS
```bash
# 安装sshpass
brew install hudochenkov/sshpass/sshpass

# 安装sqlite3 (通常已预装)
brew install sqlite3
```

#### Ubuntu/Debian
```bash
# 安装依赖
sudo apt-get update
sudo apt-get install -y sshpass sqlite3 python3
```

#### CentOS/RHEL
```bash
# 安装依赖
sudo yum install -y sshpass sqlite python3
```

## 使用方法

### 方法一: 使用Bash脚本 (推荐新手)

#### 基本同步
```bash
# 执行完整同步
./sync_database.sh
```

#### 测试连接
```bash
# 仅测试连接，不执行同步
./sync_database.sh --dry-run
```

#### 查看帮助
```bash
./sync_database.sh --help
```

### 方法二: 使用Python脚本 (推荐高级用户)

#### 完整同步
```bash
# 执行完整同步
python3 sync_database.py
```

#### 仅比较差异
```bash
# 只比较本地和远程数据库差异，不执行同步
python3 sync_database.py --compare-only
```

#### 测试连接
```bash
# 仅测试连接
python3 sync_database.py --dry-run
```

#### 静默模式
```bash
# 静默执行，减少输出
python3 sync_database.py --quiet
```

## 同步流程

### 自动执行的步骤

1. **环境检查**
   - 检查sshpass和sqlite3是否安装
   - 验证必要的依赖

2. **连接测试**
   - 测试SSH连接到远程服务器
   - 验证远程数据库文件存在

3. **本地备份**
   - 自动备份现有的本地数据库
   - 备份文件保存在`./db_backups/`目录
   - 备份文件名包含时间戳

4. **下载远程数据库**
   - 从远程服务器下载最新数据库
   - 验证下载文件的完整性

5. **数据对比** (仅Python脚本)
   - 比较本地和远程数据库的差异
   - 显示记录数量变化

6. **替换本地数据库**
   - 更新根目录的`stations.db`
   - 更新`data/`目录的`stations.db`

7. **验证同步结果**
   - 检查同步后的数据库完整性
   - 显示统计信息

## 配置信息

### 远程服务器配置
```bash
REMOTE_HOST="49.232.253.3"
REMOTE_USER="root"
REMOTE_PATH="/opt/gaode-service"
```

### 本地文件路径
```bash
LOCAL_DB_FILE="./stations.db"           # 根目录数据库
LOCAL_DATA_DB_FILE="./data/stations.db" # data目录数据库
BACKUP_DIR="./db_backups"               # 备份目录
```

## 安全注意事项

1. **密码安全**: 脚本中包含远程服务器密码，请确保文件权限安全
2. **备份重要**: 同步前会自动备份，但建议定期手动备份重要数据
3. **网络安全**: 确保在安全的网络环境中执行同步操作

## 故障排除

### 常见问题

#### 1. SSH连接失败
```bash
# 检查网络连接
ping 49.232.253.3

# 手动测试SSH连接
ssh root@49.232.253.3
```

#### 2. sshpass未安装
```bash
# macOS
brew install hudochenkov/sshpass/sshpass

# Ubuntu
sudo apt-get install sshpass
```

#### 3. 权限问题
```bash
# 确保脚本有执行权限
chmod +x sync_database.sh
chmod +x sync_database.py
```

#### 4. 数据库文件损坏
- 检查`./db_backups/`目录中的备份文件
- 手动恢复备份文件

### 恢复备份

如果同步后发现问题，可以从备份恢复：

```bash
# 查看备份文件
ls -la ./db_backups/

# 恢复根目录数据库
cp ./db_backups/stations_root_backup_YYYYMMDD_HHMMSS.db ./stations.db

# 恢复data目录数据库
cp ./db_backups/stations_data_backup_YYYYMMDD_HHMMSS.db ./data/stations.db
```

## 日志和监控

### 查看同步日志
- Bash脚本: 输出到终端，可重定向到文件
- Python脚本: 带时间戳的彩色日志输出

### 保存日志到文件
```bash
# Bash脚本
./sync_database.sh 2>&1 | tee sync_log_$(date +%Y%m%d_%H%M%S).log

# Python脚本  
python3 sync_database.py 2>&1 | tee sync_log_$(date +%Y%m%d_%H%M%S).log
```

## 自动化同步

### 设置定时任务 (crontab)

```bash
# 编辑crontab
crontab -e

# 添加定时任务 (每天凌晨2点同步)
0 2 * * * cd /path/to/gaode-station-service && ./sync_database.sh >> /var/log/db_sync.log 2>&1
```

### 设置系统服务 (systemd)

创建服务文件 `/etc/systemd/system/db-sync.service`:
```ini
[Unit]
Description=Database Sync Service
After=network.target

[Service]
Type=oneshot
WorkingDirectory=/path/to/gaode-station-service
ExecStart=/path/to/gaode-station-service/sync_database.sh
User=your-user

[Install]
WantedBy=multi-user.target
```

创建定时器文件 `/etc/systemd/system/db-sync.timer`:
```ini
[Unit]
Description=Run Database Sync Daily
Requires=db-sync.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

启用定时器:
```bash
sudo systemctl enable db-sync.timer
sudo systemctl start db-sync.timer
```

## 技术支持

如遇到问题，请检查：
1. 网络连接是否正常
2. 远程服务器是否可访问
3. 依赖软件是否正确安装
4. 文件权限是否正确设置

更多技术支持，请查看项目文档或联系开发团队。
