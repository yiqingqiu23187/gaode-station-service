#!/usr/bin/env python3
"""
修复job_positions表中缺失的经纬度数据
通过recruiting_unit字段关联stations表来获取经纬度信息
"""

import sqlite3
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_FILE = 'stations.db'

def fix_job_coordinates():
    """修复job_positions表中缺失的经纬度数据"""
    logger.info("开始修复job_positions表中缺失的经纬度数据")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # 查询需要修复的岗位数量
        cursor.execute("""
            SELECT COUNT(*) 
            FROM job_positions 
            WHERE longitude IS NULL OR latitude IS NULL
        """)
        missing_count = cursor.fetchone()[0]
        logger.info(f"发现{missing_count}个岗位缺失经纬度数据")
        
        if missing_count == 0:
            logger.info("所有岗位都已有经纬度数据，无需修复")
            return
        
        # 通过recruiting_unit关联stations表更新经纬度
        update_sql = """
            UPDATE job_positions 
            SET longitude = (
                SELECT s.longitude 
                FROM stations s 
                WHERE s.station_name = job_positions.recruiting_unit
            ),
            latitude = (
                SELECT s.latitude 
                FROM stations s 
                WHERE s.station_name = job_positions.recruiting_unit
            )
            WHERE (longitude IS NULL OR latitude IS NULL)
            AND recruiting_unit IN (
                SELECT station_name FROM stations 
                WHERE longitude IS NOT NULL AND latitude IS NOT NULL
            )
        """
        
        cursor.execute(update_sql)
        updated_count = cursor.rowcount
        
        conn.commit()
        logger.info(f"成功更新{updated_count}个岗位的经纬度数据")
        
        # 检查修复后的状态
        cursor.execute("""
            SELECT COUNT(*) 
            FROM job_positions 
            WHERE longitude IS NULL OR latitude IS NULL
        """)
        remaining_missing = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM job_positions 
            WHERE currently_recruiting = '是' 
            AND longitude IS NOT NULL 
            AND latitude IS NOT NULL
        """)
        recruiting_with_coords = cursor.fetchone()[0]
        
        logger.info(f"修复完成！")
        logger.info(f"仍缺失经纬度的岗位: {remaining_missing}")
        logger.info(f"招聘中且有经纬度的岗位: {recruiting_with_coords}")
        
        # 显示仍然缺失经纬度的站点
        if remaining_missing > 0:
            cursor.execute("""
                SELECT DISTINCT recruiting_unit 
                FROM job_positions 
                WHERE longitude IS NULL OR latitude IS NULL
            """)
            missing_stations = [row[0] for row in cursor.fetchall()]
            logger.warning(f"以下站点仍缺失经纬度数据: {missing_stations}")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"修复失败: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    fix_job_coordinates()
