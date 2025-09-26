#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
根据满编率数据更新广州岗位的招聘状态
满编率1.0以上的岗位改为不招聘
"""

import sqlite3
import pandas as pd
import os
from typing import Dict, List, Tuple

def read_staffing_rate_data() -> pd.DataFrame:
    """读取满编率数据"""
    staffing_file = "原始数据/满编率/满编率.csv"
    
    if not os.path.exists(staffing_file):
        raise FileNotFoundError(f"满编率文件不存在: {staffing_file}")
    
    print(f"读取满编率数据: {staffing_file}")
    df = pd.read_csv(staffing_file, encoding='utf-8')
    
    # 过滤广州的数据
    guangzhou_data = df[df['城市'] == '广州'].copy()
    
    # 过滤掉满编率为NULL的记录
    guangzhou_data = guangzhou_data[guangzhou_data['全职满编率'] != 'NULL']
    guangzhou_data = guangzhou_data[pd.notna(guangzhou_data['全职满编率'])]
    
    # 转换满编率为数值类型
    guangzhou_data['全职满编率'] = pd.to_numeric(guangzhou_data['全职满编率'], errors='coerce')
    
    print(f"找到 {len(guangzhou_data)} 条广州满编率数据")
    return guangzhou_data

def get_db_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    db_path = "stations.db"
    if not os.path.exists(db_path):
        db_path = "data/stations.db"
    
    if not os.path.exists(db_path):
        raise FileNotFoundError("找不到数据库文件")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def extract_station_code(station_name: str) -> str:
    """从站点名称中提取站点代码 (如 GZ0191)"""
    import re
    # 匹配模式: GZ + 数字
    match = re.search(r'GZ\d+', station_name)
    return match.group(0) if match else ""

def find_matching_jobs(staffing_data: pd.DataFrame) -> List[Tuple[str, float, List[str]]]:
    """找到需要更新的岗位"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 获取所有广州的岗位
    cursor.execute("""
        SELECT DISTINCT recruiting_unit, currently_recruiting
        FROM job_positions 
        WHERE city = '广州'
        ORDER BY recruiting_unit
    """)
    
    job_units = cursor.fetchall()
    conn.close()
    
    matches = []
    
    for _, row in staffing_data.iterrows():
        station_name = row['站点名称']
        staffing_rate = row['全职满编率']
        station_code = extract_station_code(station_name)
        
        if staffing_rate > 1.0:
            # 查找匹配的招聘单位
            matching_units = []

            # 提取站点关键词进行匹配
            station_keywords = extract_station_keywords(station_name)

            for job_unit in job_units:
                unit_name = job_unit['recruiting_unit']

                # 匹配逻辑：
                # 1. 直接匹配站点关键词
                # 2. 或者包含站点代码
                matched = False

                # 尝试关键词匹配
                for keyword in station_keywords:
                    if keyword in unit_name:
                        matching_units.append(unit_name)
                        matched = True
                        break

                # 如果关键词匹配失败，尝试站点代码匹配
                if not matched and station_code and station_code in unit_name:
                    matching_units.append(unit_name)

            if matching_units:
                matches.append((station_name, staffing_rate, matching_units))
    
    return matches

def extract_station_keywords(station_name: str) -> List[str]:
    """从站点名称中提取关键词用于匹配"""
    # 移除常见前缀和后缀
    name = station_name.replace('小象超市-', '')

    # 移除站点代码部分 (如 -GZ0191)
    import re
    name = re.sub(r'-GZ\d+$', '', name)

    # 如果还有"站"字，保留它作为关键词的一部分
    if '站' in name:
        # 直接返回清理后的名称作为主要关键词
        return [name]
    else:
        # 分割并过滤短词
        keywords = [word.strip() for word in name.split('-') if len(word.strip()) > 1]
        return keywords

def backup_database():
    """备份数据库"""
    import shutil
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"stations_backup_before_staffing_update_{timestamp}.db"
    
    source = "stations.db"
    if not os.path.exists(source):
        source = "data/stations.db"
    
    shutil.copy2(source, backup_name)
    print(f"数据库已备份到: {backup_name}")
    return backup_name

def update_recruitment_status(matching_jobs: List[Tuple[str, float, List[str]]]) -> int:
    """更新招聘状态"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    total_updated = 0
    
    print("\n=== 开始更新招聘状态 ===")
    
    for station_name, staffing_rate, unit_names in matching_jobs:
        print(f"\n站点: {station_name} (满编率: {staffing_rate:.2f})")
        
        for unit_name in unit_names:
            # 检查当前状态
            cursor.execute("""
                SELECT COUNT(*) as total, 
                       SUM(CASE WHEN currently_recruiting = '是' THEN 1 ELSE 0 END) as recruiting
                FROM job_positions 
                WHERE city = '广州' AND recruiting_unit = ?
            """, (unit_name,))
            
            result = cursor.fetchone()
            total_jobs = result['total']
            recruiting_jobs = result['recruiting']
            
            if recruiting_jobs > 0:
                # 更新为不招聘
                cursor.execute("""
                    UPDATE job_positions 
                    SET currently_recruiting = '否'
                    WHERE city = '广州' 
                      AND recruiting_unit = ? 
                      AND currently_recruiting = '是'
                """, (unit_name,))
                
                updated_count = cursor.rowcount
                total_updated += updated_count
                
                print(f"  - {unit_name}: {updated_count}/{recruiting_jobs} 个岗位改为不招聘")
            else:
                print(f"  - {unit_name}: 已经是不招聘状态")
    
    conn.commit()
    conn.close()
    
    return total_updated

def main():
    """主函数"""
    print("=== 根据满编率更新广州岗位招聘状态 ===")
    print("满编率 > 1.0 的岗位将改为不招聘\n")
    
    try:
        # 1. 读取满编率数据
        staffing_data = read_staffing_rate_data()
        
        # 显示满编率 > 1.0 的站点
        high_staffing = staffing_data[staffing_data['全职满编率'] > 1.0]
        print(f"满编率 > 1.0 的广州站点数量: {len(high_staffing)}")
        
        if len(high_staffing) == 0:
            print("没有找到满编率 > 1.0 的广州站点，无需更新")
            return
        
        print("\n满编率 > 1.0 的站点:")
        for _, row in high_staffing.iterrows():
            print(f"  - {row['站点名称']}: {row['全职满编率']:.2f}")
        
        # 2. 找到匹配的岗位
        print("\n=== 查找匹配的岗位 ===")
        matching_jobs = find_matching_jobs(high_staffing)
        
        if not matching_jobs:
            print("没有找到匹配的岗位，无需更新")
            return
        
        print(f"找到 {len(matching_jobs)} 个需要更新的站点:")
        for station_name, rate, units in matching_jobs:
            print(f"  - {station_name} ({rate:.2f}): {len(units)} 个招聘单位")
        
        # 3. 确认更新
        response = input(f"\n是否继续更新这些岗位的招聘状态？(y/N): ")
        if response.lower() != 'y':
            print("操作已取消")
            return
        
        # 4. 备份数据库
        backup_file = backup_database()
        
        # 5. 执行更新
        updated_count = update_recruitment_status(matching_jobs)
        
        print(f"\n=== 更新完成 ===")
        print(f"总共更新了 {updated_count} 个岗位的招聘状态")
        print(f"备份文件: {backup_file}")
        
    except Exception as e:
        print(f"错误: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
