#!/usr/bin/env python3
"""
高德地图服务站点查询工具 - Python数据库同步脚本
功能：从远程服务器同步线上数据库到本地，支持增量同步和数据对比
"""

import os
import sys
import sqlite3
import subprocess
import shutil
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import argparse

# 配置信息
REMOTE_HOST = "49.232.253.3"
REMOTE_USER = "root"
REMOTE_PASSWORD = "Smj,`c6L2#E/UX"
REMOTE_PATH = "/opt/gaode-service"
REMOTE_DB_FILE = f"{REMOTE_PATH}/stations.db"
LOCAL_DB_FILE = "./stations.db"
LOCAL_DATA_DB_FILE = "./data/stations.db"
BACKUP_DIR = "./db_backups"

class DatabaseSyncer:
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.backup_dir = BACKUP_DIR
        
    def log(self, message: str, level: str = "INFO"):
        """日志输出"""
        if self.verbose:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            colors = {
                "INFO": "\033[0;32m",
                "WARNING": "\033[1;33m", 
                "ERROR": "\033[0;31m",
                "STEP": "\033[0;34m"
            }
            color = colors.get(level, "\033[0m")
            print(f"{color}[{level}]{timestamp} {message}\033[0m")
    
    def check_dependencies(self) -> bool:
        """检查依赖"""
        self.log("检查依赖...", "STEP")
        
        # 检查sshpass
        try:
            subprocess.run(["sshpass", "-V"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log("sshpass 未安装，请先安装", "ERROR")
            return False
            
        # 检查sqlite3
        try:
            subprocess.run(["sqlite3", "-version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log("sqlite3 未安装，请先安装", "ERROR")
            return False
            
        self.log("依赖检查完成 ✓")
        return True
    
    def test_remote_connection(self) -> bool:
        """测试远程连接"""
        self.log("测试远程服务器连接...", "STEP")
        
        try:
            # 测试SSH连接
            cmd = [
                "sshpass", "-p", REMOTE_PASSWORD,
                "ssh", "-o", "StrictHostKeyChecking=no",
                f"{REMOTE_USER}@{REMOTE_HOST}",
                "echo 'SSH连接测试成功'"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                self.log(f"SSH连接失败: {result.stderr}", "ERROR")
                return False
                
            # 检查远程数据库文件
            cmd = [
                "sshpass", "-p", REMOTE_PASSWORD,
                "ssh", "-o", "StrictHostKeyChecking=no",
                f"{REMOTE_USER}@{REMOTE_HOST}",
                f"test -f {REMOTE_DB_FILE}"
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            
            if result.returncode != 0:
                self.log(f"远程数据库文件不存在: {REMOTE_DB_FILE}", "ERROR")
                return False
                
            self.log("远程连接测试成功 ✓")
            return True
            
        except subprocess.TimeoutExpired:
            self.log("连接超时", "ERROR")
            return False
        except Exception as e:
            self.log(f"连接测试失败: {e}", "ERROR")
            return False
    
    def backup_local_database(self) -> List[str]:
        """备份本地数据库"""
        self.log("备份本地数据库...", "STEP")
        
        os.makedirs(self.backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_files = []
        
        # 备份根目录数据库
        if os.path.exists(LOCAL_DB_FILE):
            backup_file = f"{self.backup_dir}/stations_root_backup_{timestamp}.db"
            shutil.copy2(LOCAL_DB_FILE, backup_file)
            backup_files.append(backup_file)
            self.log(f"已备份根目录数据库: {backup_file}")
            
        # 备份data目录数据库
        if os.path.exists(LOCAL_DATA_DB_FILE):
            backup_file = f"{self.backup_dir}/stations_data_backup_{timestamp}.db"
            shutil.copy2(LOCAL_DATA_DB_FILE, backup_file)
            backup_files.append(backup_file)
            self.log(f"已备份data目录数据库: {backup_file}")
            
        self.log("本地数据库备份完成 ✓")
        return backup_files
    
    def download_remote_database(self) -> str:
        """下载远程数据库"""
        self.log("从远程服务器下载数据库...", "STEP")
        
        temp_db_file = "./stations_remote_temp.db"
        
        try:
            # 下载远程数据库
            cmd = [
                "sshpass", "-p", REMOTE_PASSWORD,
                "scp", "-o", "StrictHostKeyChecking=no",
                f"{REMOTE_USER}@{REMOTE_HOST}:{REMOTE_DB_FILE}",
                temp_db_file
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                self.log(f"数据库下载失败: {result.stderr}", "ERROR")
                return None
                
            # 验证数据库文件
            if not self.verify_database(temp_db_file):
                self.log("下载的数据库文件无效", "ERROR")
                os.remove(temp_db_file)
                return None
                
            self.log("远程数据库下载完成 ✓")
            return temp_db_file
            
        except subprocess.TimeoutExpired:
            self.log("下载超时", "ERROR")
            return None
        except Exception as e:
            self.log(f"下载失败: {e}", "ERROR")
            return None
    
    def verify_database(self, db_file: str) -> bool:
        """验证数据库文件"""
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # 检查数据库是否可读
            cursor.execute("SELECT COUNT(*) FROM sqlite_master")
            table_count = cursor.fetchone()[0]
            
            # 检查job_positions表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='job_positions'")
            has_job_table = cursor.fetchone() is not None
            
            if has_job_table:
                cursor.execute("SELECT COUNT(*) FROM job_positions")
                job_count = cursor.fetchone()[0]
                self.log(f"数据库验证通过: {table_count}个表, job_positions表有{job_count}条记录")
            else:
                self.log("警告: 未找到job_positions表", "WARNING")
                
            conn.close()
            return True
            
        except Exception as e:
            self.log(f"数据库验证失败: {e}", "ERROR")
            return False
    
    def get_database_stats(self, db_file: str) -> Dict:
        """获取数据库统计信息"""
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            stats = {}
            
            # 表数量
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            stats['table_count'] = cursor.fetchone()[0]
            
            # job_positions表统计
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='job_positions'")
            if cursor.fetchone():
                cursor.execute("SELECT COUNT(*) FROM job_positions")
                stats['total_jobs'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM job_positions WHERE currently_recruiting='是'")
                stats['recruiting_jobs'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(DISTINCT city) FROM job_positions")
                stats['cities'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(DISTINCT job_type) FROM job_positions")
                stats['job_types'] = cursor.fetchone()[0]
            
            conn.close()
            return stats
            
        except Exception as e:
            self.log(f"获取统计信息失败: {e}", "ERROR")
            return {}
    
    def compare_databases(self, local_db: str, remote_db: str) -> Dict:
        """比较本地和远程数据库差异"""
        self.log("比较数据库差异...", "STEP")
        
        local_stats = self.get_database_stats(local_db) if os.path.exists(local_db) else {}
        remote_stats = self.get_database_stats(remote_db)
        
        comparison = {
            'local': local_stats,
            'remote': remote_stats,
            'differences': {}
        }
        
        if local_stats and remote_stats:
            for key in remote_stats:
                if key in local_stats:
                    diff = remote_stats[key] - local_stats[key]
                    comparison['differences'][key] = diff
                    if diff != 0:
                        self.log(f"{key}: 本地={local_stats[key]}, 远程={remote_stats[key]}, 差异={diff:+d}")
        
        return comparison
    
    def replace_local_database(self, temp_db_file: str) -> bool:
        """替换本地数据库"""
        self.log("替换本地数据库...", "STEP")
        
        try:
            # 替换根目录数据库
            shutil.copy2(temp_db_file, LOCAL_DB_FILE)
            self.log(f"已更新根目录数据库: {LOCAL_DB_FILE}")
            
            # 替换data目录数据库
            if os.path.exists("./data"):
                os.makedirs("./data", exist_ok=True)
                shutil.copy2(temp_db_file, LOCAL_DATA_DB_FILE)
                self.log(f"已更新data目录数据库: {LOCAL_DATA_DB_FILE}")
            
            self.log("本地数据库替换完成 ✓")
            return True
            
        except Exception as e:
            self.log(f"替换数据库失败: {e}", "ERROR")
            return False
    
    def sync_database(self, compare_only: bool = False) -> bool:
        """执行数据库同步"""
        self.log("开始数据库同步...", "STEP")
        
        # 检查依赖
        if not self.check_dependencies():
            return False
            
        # 测试连接
        if not self.test_remote_connection():
            return False
            
        # 下载远程数据库
        temp_db_file = self.download_remote_database()
        if not temp_db_file:
            return False
            
        try:
            # 比较数据库
            comparison = self.compare_databases(LOCAL_DB_FILE, temp_db_file)
            
            if compare_only:
                self.log("仅比较模式，不执行同步")
                return True
                
            # 备份本地数据库
            backup_files = self.backup_local_database()
            
            # 替换本地数据库
            if not self.replace_local_database(temp_db_file):
                return False
                
            # 验证同步结果
            final_stats = self.get_database_stats(LOCAL_DB_FILE)
            self.log(f"同步完成，最终统计: {final_stats}")
            
            return True
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_db_file):
                os.remove(temp_db_file)

def main():
    parser = argparse.ArgumentParser(description="高德地图服务数据库同步工具")
    parser.add_argument("--compare-only", action="store_true", help="仅比较数据库差异，不执行同步")
    parser.add_argument("--quiet", action="store_true", help="静默模式")
    parser.add_argument("--dry-run", action="store_true", help="仅测试连接")
    
    args = parser.parse_args()
    
    syncer = DatabaseSyncer(verbose=not args.quiet)
    
    if args.dry_run:
        syncer.log("执行干运行模式...")
        success = syncer.check_dependencies() and syncer.test_remote_connection()
        syncer.log("干运行完成" if success else "干运行失败")
        return 0 if success else 1
    
    success = syncer.sync_database(compare_only=args.compare_only)
    
    if success:
        syncer.log("🎉 数据库同步完成！")
        return 0
    else:
        syncer.log("❌ 数据库同步失败！", "ERROR")
        return 1

if __name__ == "__main__":
    sys.exit(main())
