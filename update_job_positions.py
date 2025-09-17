#!/usr/bin/env python3
"""
更新岗位属性数据表脚本
根据广州和深圳的需求CSV文件更新job_positions表：
1. 补齐每个站点对应的全部岗位
2. 根据数据表中已有的信息将新增的岗位信息补齐
3. 根据岗位缺口情况调整每个岗位的招聘状态
"""

import pandas as pd
import sqlite3
import os
from typing import Dict, List, Tuple, Optional
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 数据库文件路径
DB_FILE = 'stations.db'

# 岗位类型映射关系
JOB_TYPE_MAPPING = {
    # 广州CSV字段 -> 标准岗位类型
    '分拣员': '白班分拣员',
    '白班理货': '白班理货员',
    '夜班理货': '夜班理货员',
    '水产专员': '水产员',
    '果切员': '果切员',
    
    # 深圳CSV字段 -> 标准岗位类型
    '全职分拣': '白班分拣员',
    '全职白班': '白班理货员',
    '全职水产': '水产员',
    '全职夜班': '夜班理货员',
    '夜班分拣': '夜班理货员',
    # '果切员': '果切员',  # 已在上面定义
}

# 所有标准岗位类型
ALL_JOB_TYPES = [
    '白班分拣员',
    '白班理货员', 
    '夜班理货员',
    '水产员',
    '果切员'
]

def get_db_connection():
    """创建数据库连接"""
    if not os.path.exists(DB_FILE):
        raise FileNotFoundError(f"数据库文件不存在: {DB_FILE}")
    
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def read_guangzhou_data(file_path: str) -> pd.DataFrame:
    """读取广州需求数据"""
    logger.info(f"读取广州数据文件: {file_path}")
    
    df = pd.read_csv(file_path)
    
    # 过滤有效数据行（有门店名称的行）
    df_clean = df.dropna(subset=['门店名称']).copy()
    df_clean = df_clean[df_clean['门店名称'].str.contains('站', na=False)]
    
    logger.info(f"广州数据有效行数: {len(df_clean)}")
    return df_clean

def read_shenzhen_data(file_path: str) -> pd.DataFrame:
    """读取深圳需求数据"""
    logger.info(f"读取深圳数据文件: {file_path}")
    
    # 手动指定列名
    column_names = ['区域', '行政区', '站点', '站长', '联系方式', '全职分拣', '全职白班', 
                   '全职水产', '全职夜班', '夜班分拣', '果切员', '全职备注', '兼职备注', 
                   '面试地点', '入职报道', '门店地址']
    
    df = pd.read_csv(file_path, names=column_names, skiprows=2)
    
    # 过滤有效数据行（有站点名称的行）
    df_clean = df.dropna(subset=['站点']).copy()
    df_clean = df_clean[df_clean['站点'].str.contains('站', na=False)]
    
    logger.info(f"深圳数据有效行数: {len(df_clean)}")
    return df_clean

def parse_demand_data(df: pd.DataFrame, city: str) -> Dict[str, Dict[str, int]]:
    """解析需求数据，返回站点->岗位类型->需求数量的字典"""
    logger.info(f"解析{city}需求数据")
    
    demand_data = {}
    
    for _, row in df.iterrows():
        if city == '广州':
            station_name = row['门店名称']
            demand_fields = ['分拣员', '白班理货', '夜班理货', '水产专员', '果切员']
        else:  # 深圳
            station_name = row['站点']
            demand_fields = ['全职分拣', '全职白班', '全职水产', '全职夜班', '夜班分拣', '果切员']
        
        if pd.isna(station_name):
            continue
            
        station_demands = {}
        
        for field in demand_fields:
            if field in row and pd.notna(row[field]):
                try:
                    demand_count = int(float(row[field]))
                    job_type = JOB_TYPE_MAPPING.get(field, field)
                    
                    # 对于深圳数据，全职夜班和夜班分拣都映射到夜班理货员，需要合并
                    if job_type in station_demands:
                        station_demands[job_type] += demand_count
                    else:
                        station_demands[job_type] = demand_count
                except (ValueError, TypeError):
                    continue
        
        if station_demands:
            demand_data[station_name] = station_demands
    
    logger.info(f"{city}解析完成，共{len(demand_data)}个站点")
    return demand_data

def get_existing_job_data() -> Dict[str, Dict[str, Dict]]:
    """获取现有的岗位数据，返回站点->岗位类型->岗位信息的字典"""
    logger.info("获取现有岗位数据")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT recruiting_unit, job_type, city, gender, age_requirement,
               special_requirements, accept_criminal_record, location,
               longitude, latitude, urgent_capacity, working_hours,
               relevant_experience, full_time, salary, job_content,
               interview_time, trial_time, currently_recruiting,
               insurance_status, accommodation_status
        FROM job_positions
        ORDER BY recruiting_unit, job_type
    """)
    
    existing_data = {}
    for row in cursor.fetchall():
        station = row['recruiting_unit']
        job_type = row['job_type']
        
        if station not in existing_data:
            existing_data[station] = {}
        
        existing_data[station][job_type] = dict(row)
    
    conn.close()
    logger.info(f"获取到{len(existing_data)}个站点的现有岗位数据")
    return existing_data

def generate_complete_job_records(all_demands: Dict[str, Dict[str, int]],
                                existing_data: Dict[str, Dict[str, Dict]],
                                guangzhou_demands: Dict[str, Dict[str, int]],
                                shenzhen_demands: Dict[str, Dict[str, int]]) -> List[Dict]:
    """生成完整的岗位记录"""
    logger.info("生成完整的岗位记录")

    complete_records = []
    all_stations = set(all_demands.keys()) | set(existing_data.keys())

    for station in all_stations:
        station_demands = all_demands.get(station, {})
        station_existing = existing_data.get(station, {})

        # 确定城市
        city = get_city_from_demand_data(station, guangzhou_demands, shenzhen_demands)

        # 为每个岗位类型生成记录
        for job_type in ALL_JOB_TYPES:
            demand_count = station_demands.get(job_type, 0)
            existing_job = station_existing.get(job_type, {})

            # 设置招聘状态：缺口大于0则招聘，否则不招聘
            currently_recruiting = '是' if demand_count > 0 else '否'

            # 创建岗位记录
            job_record = {
                'job_type': job_type,
                'recruiting_unit': station,
                'city': city,
                'gender': existing_job.get('gender', '不限'),
                'age_requirement': existing_job.get('age_requirement', '18-35'),
                'special_requirements': existing_job.get('special_requirements', ''),
                'accept_criminal_record': existing_job.get('accept_criminal_record', '否'),
                'location': existing_job.get('location', ''),
                'longitude': existing_job.get('longitude'),
                'latitude': existing_job.get('latitude'),
                'urgent_capacity': demand_count,  # 使用需求数量作为紧急程度
                'working_hours': existing_job.get('working_hours', ''),
                'relevant_experience': existing_job.get('relevant_experience', '无需经验'),
                'full_time': existing_job.get('full_time', '是'),
                'salary': existing_job.get('salary', ''),
                'job_content': existing_job.get('job_content', ''),
                'interview_time': existing_job.get('interview_time', ''),
                'trial_time': existing_job.get('trial_time', ''),
                'currently_recruiting': currently_recruiting,
                'insurance_status': existing_job.get('insurance_status', ''),
                'accommodation_status': existing_job.get('accommodation_status', '')
            }

            complete_records.append(job_record)

    logger.info(f"生成了{len(complete_records)}条完整岗位记录")
    return complete_records

def update_job_positions_table(records: List[Dict]):
    """更新job_positions表"""
    logger.info("开始更新job_positions表")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 清空现有数据
        cursor.execute("DELETE FROM job_positions")
        logger.info("已清空现有岗位数据")

        # 插入新数据
        insert_sql = """
            INSERT INTO job_positions (
                job_type, recruiting_unit, city, gender, age_requirement,
                special_requirements, accept_criminal_record, location,
                longitude, latitude, urgent_capacity, working_hours,
                relevant_experience, full_time, salary, job_content,
                interview_time, trial_time, currently_recruiting,
                insurance_status, accommodation_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        for record in records:
            cursor.execute(insert_sql, (
                record['job_type'],
                record['recruiting_unit'],
                record['city'],
                record['gender'],
                record['age_requirement'],
                record['special_requirements'],
                record['accept_criminal_record'],
                record['location'],
                record['longitude'],
                record['latitude'],
                record['urgent_capacity'],
                record['working_hours'],
                record['relevant_experience'],
                record['full_time'],
                record['salary'],
                record['job_content'],
                record['interview_time'],
                record['trial_time'],
                record['currently_recruiting'],
                record['insurance_status'],
                record['accommodation_status']
            ))

        conn.commit()
        logger.info(f"成功插入{len(records)}条岗位记录")

    except Exception as e:
        conn.rollback()
        logger.error(f"更新数据库失败: {e}")
        raise
    finally:
        conn.close()

def get_city_from_demand_data(station: str, guangzhou_data: Dict, shenzhen_data: Dict) -> str:
    """根据需求数据判断站点所属城市"""
    if station in guangzhou_data:
        return '广州'
    elif station in shenzhen_data:
        return '深圳'
    else:
        # 默认根据站点名称判断
        return '广州' if '广州' in station else '深圳'

def main():
    """主函数"""
    logger.info("开始更新岗位属性数据表")

    try:
        # 读取CSV数据
        guangzhou_df = read_guangzhou_data('9.15广州最新需求.csv')
        shenzhen_df = read_shenzhen_data('深圳需求9.15-20250915.csv')

        # 解析需求数据
        guangzhou_demands = parse_demand_data(guangzhou_df, '广州')
        shenzhen_demands = parse_demand_data(shenzhen_df, '深圳')

        # 合并需求数据
        all_demands = {**guangzhou_demands, **shenzhen_demands}
        logger.info(f"总共处理{len(all_demands)}个站点的需求数据")

        # 获取现有岗位数据
        existing_data = get_existing_job_data()

        # 生成完整的岗位记录
        complete_records = generate_complete_job_records(
            all_demands, existing_data, guangzhou_demands, shenzhen_demands
        )

        # 更新数据库
        update_job_positions_table(complete_records)

        # 统计结果
        recruiting_count = sum(1 for r in complete_records if r['currently_recruiting'] == '是')
        not_recruiting_count = len(complete_records) - recruiting_count

        logger.info("更新完成！")
        logger.info(f"总岗位数: {len(complete_records)}")
        logger.info(f"招聘中岗位: {recruiting_count}")
        logger.info(f"不招聘岗位: {not_recruiting_count}")
        logger.info(f"涉及站点数: {len(set(all_demands.keys()) | set(existing_data.keys()))}")

    except Exception as e:
        logger.error(f"更新失败: {e}")
        raise

if __name__ == '__main__':
    main()
