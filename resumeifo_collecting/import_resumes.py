#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简历数据导入脚本
从Excel文件导入蓝领应聘者简历到数据库
"""

import pandas as pd
import pymysql
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('import_resumes.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ResumeImporter:
    def __init__(self, database_url: str, success_ids_file: str = "successful_resume_ids.txt"):
        """
        初始化导入器
        
        Args:
            database_url: 数据库连接URL，格式：mysql://user:password@host:port/database
            success_ids_file: 保存成功导入简历ID的文件路径
        """
        self.database_url = database_url
        self.connection = None
        self.success_ids_file = success_ids_file
        self.successful_ids = []
        
    def parse_database_url(self) -> Dict[str, str]:
        """解析数据库URL"""
        # 移除 mysql:// 前缀
        url = self.database_url.replace('mysql://', '')
        
        # 分割用户名密码和主机信息
        auth_part, host_part = url.split('@')
        username, password = auth_part.split(':')
        
        # 分割主机、端口和数据库
        host_port_db = host_part.split('/')
        host_port = host_port_db[0]
        database = host_port_db[1].split('?')[0]  # 移除查询参数
        
        # 分割主机和端口
        if ':' in host_port:
            host, port = host_port.split(':')
        else:
            host = host_port
            port = '3306'
            
        return {
            'host': host,
            'port': int(port),
            'user': username,
            'password': password,
            'database': database,
            'charset': 'utf8mb4'
        }
    
    def connect_database(self):
        """连接数据库"""
        try:
            db_config = self.parse_database_url()
            self.connection = pymysql.connect(**db_config)
            logger.info("数据库连接成功")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def close_database(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            logger.info("数据库连接已关闭")
    
    def read_excel_data(self, file_path: str) -> pd.DataFrame:
        """
        读取Excel文件数据
        
        Args:
            file_path: Excel文件路径
            
        Returns:
            DataFrame: 读取的数据
        """
        try:
            df = pd.read_excel(file_path)
            logger.info(f"成功读取Excel文件，共 {len(df)} 条记录")
            return df
        except Exception as e:
            logger.error(f"读取Excel文件失败: {e}")
            raise
    
    def map_excel_to_resume(self, row: pd.Series) -> Dict[str, Any]:
        """
        将Excel行数据映射到简历表字段
        
        Args:
            row: Excel行数据
            
        Returns:
            Dict: 映射后的简历数据
        """
        # 基础字段映射（使用数据库实际字段名）
        resume_data = {
            'id': str(uuid.uuid4()),
            'name': str(row.get('姓名', '')).strip(),
            'phone': str(row.get('手机号', '')).strip() if pd.notna(row.get('手机号')) else None,
            'wechat': str(row.get('微信号', '')).strip() if pd.notna(row.get('微信号')) else None,
            'source': 'INTERNAL',  # 使用内部来源
            'deleted': 0,
            'create_time': datetime.now(),
            'update_time': datetime.now()
        }
        
        # 处理年龄字段转换（从"18~30岁"格式转换为"27岁"格式）
        if pd.notna(row.get('年龄')):
            age_str = str(row.get('年龄')).strip()
            # 提取年龄范围并计算平均值
            if '~' in age_str and '岁' in age_str:
                try:
                    # 提取数字部分，如"18~30岁" -> ["18", "30"]
                    age_parts = age_str.replace('岁', '').split('~')
                    if len(age_parts) == 2:
                        min_age = int(age_parts[0])
                        max_age = int(age_parts[1])
                        avg_age = (min_age + max_age) // 2
                        resume_data['age'] = f"{avg_age}岁"
                    else:
                        resume_data['age'] = age_str
                except (ValueError, IndexError):
                    resume_data['age'] = age_str
            else:
                resume_data['age'] = age_str
        
        # 处理居住城市或工作城市作为期望地点（兼容两种表头格式）
        location = None
        if pd.notna(row.get('居住城市')):
            location = str(row.get('居住城市')).strip()
        elif pd.notna(row.get('工作城市')):
            location = str(row.get('工作城市')).strip()
        
        if location:
            resume_data['expect_location'] = location

        # 处理应聘岗位作为期望职位（从"分拣员"格式转换为["分拣员"]格式）
        if pd.notna(row.get('应聘岗位')):
            position = str(row.get('应聘岗位')).strip()
            expect_positions = [position]
            resume_data['expect_positions'] = json.dumps(expect_positions, ensure_ascii=False)
        
        # externalId留空
        resume_data['external_id'] = None
        
        # 设置经验字段为默认值
        resume_data['experience'] = '不限'
        
        return resume_data
    
    def validate_resume_data(self, resume_data: Dict[str, Any]) -> bool:
        """
        验证简历数据
        
        Args:
            resume_data: 简历数据
            
        Returns:
            bool: 验证是否通过
        """
        # 必填字段检查
        if not resume_data.get('name'):
            logger.warning(f"姓名为空，跳过记录")
            return False
            
        if not resume_data.get('phone'):
            logger.warning(f"手机号为空，跳过记录: {resume_data.get('name')}")
            return False
        
        return True
    
    def check_existing_resume(self, phone: str) -> Optional[str]:
        """
        检查数据库中是否已存在相同手机号的简历
        
        Args:
            phone: 手机号
            
        Returns:
            Optional[str]: 如果存在返回简历ID，否则返回None
        """
        try:
            cursor = self.connection.cursor()
            sql = "SELECT id FROM resume WHERE phone = %s AND deleted = 0"
            cursor.execute(sql, (phone,))
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                return result[0]
            return None
            
        except Exception as e:
            logger.error(f"检查已存在简历失败: {e}")
            return None
            
    def update_resume(self, existing_id: str, resume_data: Dict[str, Any]) -> bool:
        """
        更新已存在的简历记录

        Args:
            existing_id: 已存在简历的ID
            resume_data: 新的简历数据

        Returns:
            bool: 更新是否成功
        """
        try:
            cursor = self.connection.cursor()

            # 准备更新的字段，排除id和create_time
            update_fields = {}
            for key, value in resume_data.items():
                if key not in ['id', 'create_time']:
                    update_fields[key] = value

            # 构建更新SQL
            set_clauses = []
            values = []
            for field, value in update_fields.items():
                set_clauses.append(f"`{field}` = %s")
                values.append(value)

            sql = f"UPDATE resume SET {', '.join(set_clauses)} WHERE id = %s"
            values.append(existing_id)

            cursor.execute(sql, values)
            self.connection.commit()
            cursor.close()
            
            logger.info(f"成功更新简历: {resume_data['name']} ({resume_data['phone']}) - ID: {existing_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新简历失败: {resume_data.get('name', 'Unknown')} - {e}")
            self.connection.rollback()
            return False
    
    def upsert_resume(self, resume_data: Dict[str, Any]) -> bool:
        """
        插入或更新简历数据到数据库

        Args:
            resume_data: 简历数据

        Returns:
            bool: 操作是否成功
        """
        try:
            phone = resume_data.get('phone')
            if not phone:
                logger.error(f"手机号为空，无法进行插入或更新操作")
                return False

            # 检查是否已存在相同手机号的记录
            existing_id = self.check_existing_resume(phone)

            if existing_id:
                # 更新已存在的记录
                success = self.update_resume(existing_id, resume_data)
                if success:
                    self.successful_ids.append(existing_id)
                return success
            else:
                # 插入新记录
                cursor = self.connection.cursor()

                # 构建插入SQL
                fields = list(resume_data.keys())
                placeholders = ', '.join(['%s'] * len(fields))
                field_names = ', '.join([f'`{field}`' for field in fields])

                sql = f"""
                    INSERT INTO resume ({field_names})
                    VALUES ({placeholders})
                """

                values = list(resume_data.values())
                cursor.execute(sql, values)
                self.connection.commit()
                cursor.close()

                # 保存成功的简历ID
                resume_id = resume_data['id']
                self.successful_ids.append(resume_id)

                logger.info(f"成功插入简历: {resume_data['name']} ({resume_data['phone']}) - ID: {resume_id}")
                return True

        except Exception as e:
            logger.error(f"插入或更新简历失败: {resume_data.get('name', 'Unknown')} - {e}")
            if hasattr(self, 'connection') and self.connection:
                self.connection.rollback()
            return False

    def save_successful_ids(self):
        """保存成功导入的简历ID到文件"""
        try:
            with open(self.success_ids_file, 'w', encoding='utf-8') as f:
                for resume_id in self.successful_ids:
                    f.write(f"{resume_id}\n")
            logger.info(f"成功保存 {len(self.successful_ids)} 个简历ID到文件: {self.success_ids_file}")
        except Exception as e:
            logger.error(f"保存成功ID文件失败: {e}")
    
    def import_resumes(self, excel_file_path: str, dry_run: bool = True):
        """
        导入简历数据
        
        Args:
            excel_file_path: Excel文件路径
            dry_run: 是否为试运行（不实际插入数据）
        """
        try:
            # 读取Excel数据
            df = self.read_excel_data(excel_file_path)
            
            if dry_run:
                logger.info("=== 试运行模式，不会实际插入数据 ===")
            else:
                logger.info("=== 正式运行模式，将实际插入数据 ===")
                self.connect_database()
            
            success_count = 0
            error_count = 0
            
            for index, row in df.iterrows():
                try:
                    # 映射数据
                    resume_data = self.map_excel_to_resume(row)
                    
                    # 验证数据
                    if not self.validate_resume_data(resume_data):
                        error_count += 1
                        continue
                    
                    if dry_run:
                        # 试运行模式，只打印数据
                        logger.info(f"试运行 - 将插入或更新简历: {resume_data['name']} ({resume_data['phone']})")
                        logger.info(f"  年龄: {resume_data.get('age', 'N/A')}")
                        logger.info(f"  期望地点: {resume_data.get('expect_location', 'N/A')}")
                        logger.info(f"  期望职位: {resume_data.get('expect_positions', 'N/A')}")
                        logger.info(f"  微信号: {resume_data.get('wechat', 'N/A')}")
                        success_count += 1
                    else:
                        # 正式运行模式，插入或更新数据
                        if self.upsert_resume(resume_data):
                            success_count += 1
                        else:
                            error_count += 1
                            
                except Exception as e:
                    logger.error(f"处理第 {index + 1} 行数据时出错: {e}")
                    error_count += 1
            
            logger.info(f"导入完成 - 成功: {success_count}, 失败: {error_count}")
            
            # 保存成功导入的简历ID
            if not dry_run and self.successful_ids:
                self.save_successful_ids()
            
        except Exception as e:
            logger.error(f"导入过程中发生错误: {e}")
            raise
        finally:
            if not dry_run:
                self.close_database()


def main():
    """主函数"""
    # 数据库连接URL - 请在这里填入实际的数据库连接信息
    DATABASE_URL = "mysql://root:Gn123456@bj-cynosdbmysql-grp-5eypnf9y.sql.tencentcdb.com:26606/recruit-db_bak?serverTimezone=Asia%2FShanghai"
    
    # Excel文件路径
    EXCEL_FILE_PATH = "9.29北广线索2.xlsx"
    
    # 创建导入器实例
    importer = ResumeImporter(DATABASE_URL)
    
    try:
        # 先进行试运行
        logger.info("开始试运行...")
        importer.import_resumes(EXCEL_FILE_PATH, dry_run=False)
        
        # 询问是否继续正式运行
        print("\n" + "="*50)
        print("试运行完成！请检查日志文件 'import_resumes.log' 确认数据正确性。")
        print("如果数据正确，请修改脚本中的 dry_run=False 来执行正式导入。")
        print("="*50)
        
        # 如果要正式运行，取消下面的注释
        # importer.import_resumes(EXCEL_FILE_PATH, dry_run=False)
        
    except Exception as e:
        logger.error(f"程序执行失败: {e}")


if __name__ == "__main__":
    main()
