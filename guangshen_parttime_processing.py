#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
广深兼职岗位数据处理脚本
功能：将广深兼职岗位数据添加到job_positions表
"""

import pandas as pd
import sqlite3
import os
from typing import List, Dict

def read_guangzhou_parttime_data() -> List[Dict]:
    """读取广州兼职岗位数据"""
    print("\n=== 读取广州兼职岗位数据 ===")
    
    gz_file = "原始数据/广深/9.17广州兼职需求.csv"
    if not os.path.exists(gz_file):
        print(f"文件不存在: {gz_file}")
        return []
    
    try:
        df = pd.read_csv(gz_file)
        print(f"成功读取广州兼职需求文件，共{len(df)}行数据")
        print(f"列名: {df.columns.tolist()}")
        
        # 读取广州兼职待遇信息
        gz_salary_file = "原始数据/广深/广州兼职待遇"
        with open(gz_salary_file, 'r', encoding='utf-8') as f:
            gz_salary_info = f.read().strip()
        
        gz_jobs = []
        
        for _, row in df.iterrows():
            # 跳过无效数据
            if pd.isna(row.get('门店名称')) or pd.isna(row.get('站点地址')):
                continue
            
            # 处理各种兼职岗位
            job_types = {
                '分拣员（兼职）': row.get('分拣员（兼职）', 0),
                '白班理货（兼职）': row.get('白班理货（兼职）', 0),
                '夜班理货（兼职）': row.get('夜班理货（兼职）', 0),
                '水产专员（兼职）': row.get('水产专员（兼职）', 0),
                '果切员（兼职）': row.get('果切员（兼职）', 0)
            }
            
            for job_type, count in job_types.items():
                if pd.notna(count) and count > 0:
                    try:
                        count = int(float(count))
                        if count > 0:
                            # 创建兼职岗位记录
                            job_record = {
                                'job_type': job_type,
                                'recruiting_unit': str(row.get('门店名称', '')),
                                'city': '广州',
                                'gender': '不限',  # 默认不限
                                'age_requirement': '18-45岁',
                                'special_requirements': '兼职岗位，时间灵活',
                                'accept_criminal_record': '否',
                                'location': str(row.get('站点地址', '')),
                                'longitude': None,  # 稍后从全职岗位匹配
                                'latitude': None,   # 稍后从全职岗位匹配
                                'urgent_capacity': count,
                                'working_hours': '周中4-6小时（下午四点开始），周末4-12小时，一周3-5天',
                                'relevant_experience': '无要求',
                                'full_time': '否',
                                'salary': '兼职时薪20-30元/小时，多劳多得，周度时薪会上涨',
                                'job_content': get_job_content_by_type(job_type),
                                'interview_time': None,  # 稍后从全职岗位匹配
                                'trial_time': '1-3天',
                                'currently_recruiting': '是',
                                'insurance_status': None,  # 稍后从全职岗位匹配
                                'accommodation_status': None  # 稍后从全职岗位匹配
                            }
                            
                            gz_jobs.append(job_record)
                    except:
                        continue
        
        print(f"成功提取{len(gz_jobs)}个广州兼职岗位")
        return gz_jobs
        
    except Exception as e:
        print(f"读取广州兼职岗位文件失败: {e}")
        return []

def read_shenzhen_parttime_data() -> List[Dict]:
    """读取深圳兼职岗位数据"""
    print("\n=== 读取深圳兼职岗位数据 ===")
    
    sz_file = "原始数据/广深/深圳兼职需求9.15-20250915.csv"
    if not os.path.exists(sz_file):
        print(f"文件不存在: {sz_file}")
        return []
    
    try:
        df = pd.read_csv(sz_file)
        print(f"成功读取深圳兼职需求文件，共{len(df)}行数据")
        print(f"列名: {df.columns.tolist()}")
        
        # 读取深圳兼职待遇信息
        sz_salary_file = "原始数据/广深/深圳兼职待遇"
        with open(sz_salary_file, 'r', encoding='utf-8') as f:
            sz_salary_info = f.read().strip()
        
        sz_jobs = []
        
        for _, row in df.iterrows():
            # 跳过无效数据
            if pd.isna(row.get('站点')) or pd.isna(row.get('门店地址')):
                continue
            
            # 处理各种兼职岗位
            job_types = {
                '夜班分拣员（兼职）': row.get('夜班分拣兼职', 0),
                '分拣员（兼职）': row.get('分拣兼职', 0),
                '水产专员（兼职）': row.get('水产兼职', 0),
                '果切员（兼职）': row.get('果切兼职', 0)
            }
            
            for job_type, count in job_types.items():
                if pd.notna(count) and count > 0:
                    try:
                        count = int(float(count))
                        if count > 0:
                            # 创建兼职岗位记录
                            job_record = {
                                'job_type': job_type,
                                'recruiting_unit': str(row.get('站点', '')),
                                'city': '深圳',
                                'gender': '不限',  # 默认不限
                                'age_requirement': '18-45岁',
                                'special_requirements': '兼职岗位，时间灵活',
                                'accept_criminal_record': '否',
                                'location': str(row.get('门店地址', '')),
                                'longitude': None,  # 稍后从全职岗位匹配
                                'latitude': None,   # 稍后从全职岗位匹配
                                'urgent_capacity': count,
                                'working_hours': '16-23点之间上3-4小时或周末全天6-8小时',
                                'relevant_experience': '无要求',
                                'full_time': '否',
                                'salary': '时效计薪，多劳多得，平均20元/小时，最高29元/小时，月结次月15号发放',
                                'job_content': get_job_content_by_type(job_type),
                                'interview_time': None,  # 稍后从全职岗位匹配
                                'trial_time': '1-3天',
                                'currently_recruiting': '是',
                                'insurance_status': None,  # 稍后从全职岗位匹配
                                'accommodation_status': None  # 稍后从全职岗位匹配
                            }
                            
                            sz_jobs.append(job_record)
                    except:
                        continue
        
        print(f"成功提取{len(sz_jobs)}个深圳兼职岗位")
        return sz_jobs
        
    except Exception as e:
        print(f"读取深圳兼职岗位文件失败: {e}")
        return []

def get_job_content_by_type(job_type: str) -> str:
    """根据岗位类型获取工作内容"""
    job_contents = {
        '分拣员（兼职）': '根据客户订单分拣商品，清点数量，用购物袋打包，放到指定取货台',
        '夜班分拣员（兼职）': '夜班时段根据客户订单分拣商品，清点数量，用购物袋打包，放到指定取货台',
        '白班理货（兼职）': '白班时段货架补货，检查商品日期和破损，保持货架饱满整洁',
        '夜班理货（兼职）': '夜班时段货架补货，检查商品日期和破损，保持货架饱满整洁',
        '水产专员（兼职）': '水产品处理，包括养鱼、杀鱼、捞虾等水产品相关工作',
        '果切员（兼职）': '水果切配工作，保证水果新鲜度和切配质量'
    }
    return job_contents.get(job_type, '兼职岗位，根据门店需求安排相应工作')

def match_info_from_fulltime(parttime_jobs: List[Dict]) -> List[Dict]:
    """从全职岗位匹配坐标、保险、面试时间、住宿等信息"""
    print("\n=== 匹配全职岗位信息 ===")

    conn = sqlite3.connect('stations.db')
    cursor = conn.cursor()

    # 获取所有全职岗位的完整信息
    cursor.execute('''
        SELECT DISTINCT recruiting_unit, location, longitude, latitude, city,
               insurance_status, interview_time, accommodation_status
        FROM job_positions
        WHERE full_time = '是' AND longitude IS NOT NULL AND latitude IS NOT NULL
    ''')
    fulltime_info = cursor.fetchall()

    # 创建信息匹配字典
    info_map = {}
    for unit, location, lon, lat, city, insurance, interview, accommodation in fulltime_info:
        key = f"{city}_{unit}"
        info_map[key] = {
            'longitude': lon,
            'latitude': lat,
            'location': location,
            'insurance_status': insurance,
            'interview_time': interview,
            'accommodation_status': accommodation
        }

    # 按城市获取默认信息（如果找不到精确匹配）
    city_defaults = {}
    for city in ['广州', '深圳']:
        cursor.execute('''
            SELECT insurance_status, interview_time, accommodation_status
            FROM job_positions
            WHERE full_time = '是' AND city = ?
            LIMIT 1
        ''', (city,))
        result = cursor.fetchone()
        if result:
            city_defaults[city] = {
                'insurance_status': result[0],
                'interview_time': result[1],
                'accommodation_status': result[2]
            }

    matched_count = 0
    for job in parttime_jobs:
        city = job['city']
        unit = job['recruiting_unit']

        # 尝试精确匹配
        key = f"{city}_{unit}"
        if key in info_map:
            info = info_map[key]
            job['longitude'] = info['longitude']
            job['latitude'] = info['latitude']
            job['insurance_status'] = info['insurance_status']
            job['interview_time'] = info['interview_time']
            job['accommodation_status'] = info['accommodation_status']
            matched_count += 1
        else:
            # 尝试模糊匹配（去掉站点后缀）
            unit_clean = unit.replace('站', '').strip()
            matched = False
            for map_key, info in info_map.items():
                if city in map_key and unit_clean in map_key:
                    job['longitude'] = info['longitude']
                    job['latitude'] = info['latitude']
                    job['insurance_status'] = info['insurance_status']
                    job['interview_time'] = info['interview_time']
                    job['accommodation_status'] = info['accommodation_status']
                    matched_count += 1
                    matched = True
                    break

            # 如果还是没匹配到，使用城市默认值
            if not matched and city in city_defaults:
                defaults = city_defaults[city]
                job['insurance_status'] = defaults['insurance_status']
                job['interview_time'] = defaults['interview_time']
                job['accommodation_status'] = defaults['accommodation_status']

    conn.close()
    print(f"成功匹配{matched_count}个兼职岗位的完整信息")
    return parttime_jobs

def insert_parttime_jobs_to_database(jobs_data: List[Dict]):
    """将兼职岗位数据插入到数据库"""
    print(f"\n=== 插入{len(jobs_data)}个兼职岗位到数据库 ===")

    conn = sqlite3.connect('stations.db')
    cursor = conn.cursor()

    # 插入数据到现有的job_positions表结构
    inserted_count = 0
    for job in jobs_data:
        try:
            cursor.execute("""
                INSERT INTO job_positions (
                    job_type, recruiting_unit, city, gender, age_requirement,
                    special_requirements, accept_criminal_record, location,
                    longitude, latitude, urgent_capacity, working_hours,
                    relevant_experience, full_time, salary, job_content,
                    interview_time, trial_time, currently_recruiting,
                    insurance_status, accommodation_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.get('job_type', ''),
                job.get('recruiting_unit', ''),
                job.get('city', ''),
                job.get('gender', ''),
                job.get('age_requirement', ''),
                job.get('special_requirements', ''),
                job.get('accept_criminal_record', ''),
                job.get('location', ''),
                job.get('longitude'),
                job.get('latitude'),
                job.get('urgent_capacity', 1),
                job.get('working_hours', ''),
                job.get('relevant_experience', ''),
                job.get('full_time', ''),
                job.get('salary', ''),
                job.get('job_content', ''),
                job.get('interview_time', ''),
                job.get('trial_time', ''),
                job.get('currently_recruiting', ''),
                job.get('insurance_status', ''),
                job.get('accommodation_status', '')
            ))
            inserted_count += 1
        except Exception as e:
            print(f"插入兼职岗位数据失败: {e}")
            print(f"问题数据: {job}")

    conn.commit()
    conn.close()

    print(f"成功插入{inserted_count}个兼职岗位到数据库")
    return inserted_count

def main():
    """主函数"""
    print("开始处理广深兼职岗位数据...")

    # 读取广州兼职岗位数据
    gz_jobs = read_guangzhou_parttime_data()

    # 读取深圳兼职岗位数据
    sz_jobs = read_shenzhen_parttime_data()

    # 合并所有兼职岗位
    all_parttime_jobs = gz_jobs + sz_jobs

    if not all_parttime_jobs:
        print("没有找到兼职岗位数据")
        return

    # 匹配全职岗位信息（坐标、保险、面试时间、住宿等）
    all_parttime_jobs = match_info_from_fulltime(all_parttime_jobs)

    # 插入到数据库
    inserted_count = insert_parttime_jobs_to_database(all_parttime_jobs)

    print(f"\n=== 处理完成 ===")
    print(f"成功处理{inserted_count}个兼职岗位")

    # 统计信息
    cities = {}
    job_types = {}
    for job in all_parttime_jobs:
        city = job.get('city', '未知')
        job_type = job.get('job_type', '未知')
        cities[city] = cities.get(city, 0) + 1
        job_types[job_type] = job_types.get(job_type, 0) + 1

    print(f"\n城市分布:")
    for city, count in cities.items():
        print(f"  {city}: {count}个岗位")

    print(f"\n岗位类型分布:")
    for job_type, count in job_types.items():
        print(f"  {job_type}: {count}个岗位")

if __name__ == "__main__":
    main()
