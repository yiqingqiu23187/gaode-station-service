#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
北京原始数据处理脚本 v2.0
处理北京文件夹中的各种数据文件，整合到job_positions表中
使用CSV文件而不是Excel文件
"""

import pandas as pd
import sqlite3
import os
import re
from typing import Dict, List, Tuple, Any

def read_position_data() -> Dict[str, Dict]:
    """读取位置信息数据"""
    print("=== 读取位置信息数据 ===")
    
    # 读取位置信息.csv文件
    position_file = "原始数据/北京/位置信息.csv"
    if not os.path.exists(position_file):
        print(f"文件不存在: {position_file}")
        return {}
    
    try:
        # 读取CSV文件
        df = pd.read_csv(position_file)
        print(f"成功读取位置信息文件，共{len(df)}行数据")
        print(f"列名: {df.columns.tolist()}")
        
        # 显示前几行数据
        print("前5行数据:")
        print(df.head())
        
        # 提取站点ID和位置信息
        position_data = {}
        
        for _, row in df.iterrows():
            # 从站点名称中提取站点ID
            station_name = str(row.get('站点名称', ''))
            if '-BJ' in station_name:
                # 提取BJ开头的站点ID
                parts = station_name.split('-BJ')
                if len(parts) > 1:
                    station_id = 'BJ' + parts[1].split('-')[0]
                    
                    position_data[station_id] = {
                        'station_name': station_name,
                        'city': str(row.get('城市', '北京')),
                        'address': str(row.get('地址', '')),
                        'district': str(row.get('区域', '')),
                        'longitude': float(row.get('经度', 0)) if pd.notna(row.get('经度')) else None,
                        'latitude': float(row.get('纬度', 0)) if pd.notna(row.get('纬度')) else None
                    }
        
        print(f"成功提取{len(position_data)}个站点的位置信息")
        return position_data
        
    except Exception as e:
        print(f"读取位置信息文件失败: {e}")
        return {}

def read_fulltime_jobs() -> List[Dict]:
    """读取全职岗位缺口数据"""
    print("\n=== 读取全职岗位缺口数据 ===")
    
    job_file = "原始数据/北京/全职缺口.csv"
    if not os.path.exists(job_file):
        print(f"文件不存在: {job_file}")
        return []
    
    try:
        df = pd.read_csv(job_file)
        print(f"成功读取全职缺口文件，共{len(df)}行数据")
        print(f"列名: {df.columns.tolist()}")
        
        jobs = []
        for _, row in df.iterrows():
            station_id = str(row.get('站点ID', ''))
            if station_id.startswith('BJ'):
                # 提取各种岗位需求，处理括号等特殊字符
                def safe_int(value):
                    if pd.isna(value):
                        return 0
                    try:
                        # 移除括号和其他非数字字符，只保留数字
                        clean_value = str(value).replace('(', '').replace(')', '').strip()
                        if clean_value == '' or clean_value == 'nan':
                            return 0
                        return int(float(clean_value))
                    except:
                        return 0

                positions = {
                    '分拣员': safe_int(row.get('分拣员', 0)),
                    '白班理货': safe_int(row.get('白班理货', 0)),
                    '夜班理货': safe_int(row.get('夜班理货', 0)),
                    '水产专员': safe_int(row.get('水产专员', 0)),
                    '果切员': safe_int(row.get('果切员', 0))
                    # 删除副站长和资深副站长
                }
                
                # 为每个有需求的岗位创建记录
                for position_name, count in positions.items():
                    if count > 0:
                        jobs.append({
                            'station_id': station_id,
                            'station_info': str(row.get('站点信息', '')),
                            'position_name': f'全职{position_name}',
                            'count': count,
                            'manager_name': str(row.get('站长姓名', '')),
                            'manager_phone': str(row.get('站长电话', '')),
                            'store_location': str(row.get('门店位置', ''))
                        })
        
        print(f"成功提取{len(jobs)}个全职岗位需求")
        return jobs
        
    except Exception as e:
        print(f"读取全职缺口文件失败: {e}")
        return []

def read_parttime_jobs() -> List[Dict]:
    """读取兼职岗位缺口数据"""
    print("\n=== 读取兼职岗位缺口数据 ===")
    
    job_file = "原始数据/北京/兼职缺口.csv"
    if not os.path.exists(job_file):
        print(f"文件不存在: {job_file}")
        return []
    
    try:
        df = pd.read_csv(job_file)
        print(f"成功读取兼职缺口文件，共{len(df)}行数据")
        print(f"列名: {df.columns.tolist()}")
        
        jobs = []
        for _, row in df.iterrows():
            station_id = str(row.get('站点ID', ''))
            if station_id.startswith('BJ'):
                # 提取兼职岗位需求，处理括号等特殊字符
                def safe_int(value):
                    if pd.isna(value):
                        return 0
                    try:
                        # 移除括号和其他非数字字符，只保留数字
                        clean_value = str(value).replace('(', '').replace(')', '').strip()
                        if clean_value == '' or clean_value == 'nan':
                            return 0
                        return int(float(clean_value))
                    except:
                        return 0

                positions = {
                    '分拣员（兼职）': safe_int(row.get('分拣员（兼职）', 0)),
                    '白班理货（兼职）': safe_int(row.get('白班理货（兼职）', 0)),
                    '夜班理货（兼职）': safe_int(row.get('夜班理货（兼职）', 0)),
                    '果切员（兼职）': safe_int(row.get('果切员（兼职）', 0)),
                    '水产专员（兼职）': safe_int(row.get('水产专员（兼职）', 0)),
                    '上架员（兼职）': safe_int(row.get('上架员（兼职）', 0))
                }
                
                # 为每个有需求的岗位创建记录
                for position_name, count in positions.items():
                    if count > 0:
                        jobs.append({
                            'station_id': station_id,
                            'station_info': str(row.get('站点信息', '')),
                            'position_name': position_name,
                            'count': count,
                            'manager_contact': str(row.get('门店负责人联系方式&位置', '')),
                            'store_location': str(row.get('门店位置', ''))
                        })
        
        print(f"成功提取{len(jobs)}个兼职岗位需求")
        return jobs
        
    except Exception as e:
        print(f"读取兼职缺口文件失败: {e}")
        return []

def read_accommodation_data() -> Dict[str, str]:
    """读取住宿情况数据"""
    print("\n=== 读取住宿情况数据 ===")

    accommodation_file = "原始数据/北京/北京住宿情况.csv"
    if not os.path.exists(accommodation_file):
        print(f"文件不存在: {accommodation_file}")
        return {}

    try:
        df = pd.read_csv(accommodation_file)
        print(f"成功读取住宿情况文件，共{len(df)}行数据")
        print(f"列名: {df.columns.tolist()}")

        # 创建住宿信息映射，使用站点ID作为键
        accommodation_map = {}

        for _, row in df.iterrows():
            covered_stations = str(row.get('可覆盖站点（全称）', ''))
            accommodation_info = f"地址: {row.get('宿舍地址', '')}, 类型: {row.get('宿舍类型', '')}, 住宿费: {row.get('住宿费/月', '')}元/月"

            # 解析可覆盖的站点，提取站点ID
            if covered_stations and covered_stations != 'nan':
                stations = [s.strip() for s in covered_stations.replace('，', ',').split(',')]
                for station in stations:
                    if station and '-BJ' in station:
                        # 提取站点ID
                        parts = station.split('-BJ')
                        if len(parts) > 1:
                            station_id = 'BJ' + parts[1].split('-')[0]
                            accommodation_map[station_id] = accommodation_info
                    elif station:
                        # 也保存完整站点名称作为备用
                        accommodation_map[station] = accommodation_info

        print(f"成功提取{len(accommodation_map)}个站点的住宿信息")
        return accommodation_map

    except Exception as e:
        print(f"读取住宿情况文件失败: {e}")
        return {}

def read_salary_requirements() -> Tuple[str, str]:
    """读取薪资待遇和要求信息"""
    print("\n=== 读取薪资待遇和要求信息 ===")
    
    fulltime_file = "原始数据/北京/全职待遇及要求"
    parttime_file = "原始数据/北京/兼职待遇及要求"
    
    fulltime_info = ""
    parttime_info = ""
    
    # 读取全职待遇及要求
    if os.path.exists(fulltime_file):
        with open(fulltime_file, 'r', encoding='utf-8') as f:
            fulltime_info = f.read().strip()
        print(f"成功读取全职待遇及要求信息，共{len(fulltime_info)}字符")
    
    # 读取兼职待遇及要求
    if os.path.exists(parttime_file):
        with open(parttime_file, 'r', encoding='utf-8') as f:
            parttime_info = f.read().strip()
        print(f"成功读取兼职待遇及要求信息，共{len(parttime_info)}字符")
    
    return fulltime_info, parttime_info

def insert_jobs_to_database(jobs_data: List[Dict]):
    """将岗位数据插入到数据库"""
    print(f"\n=== 插入{len(jobs_data)}个岗位到数据库 ===")

    conn = sqlite3.connect('stations.db')
    cursor = conn.cursor()

    # 插入数据到现有的job_positions表结构
    inserted_count = 0
    for job in jobs_data:
        try:
            # 根据现有表结构映射数据
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
                job.get('position_name', ''),  # job_type
                job.get('station_name', ''),   # recruiting_unit
                job.get('city', '北京'),        # city
                '不限' if '分拣' in job.get('position_name', '') else '男性',  # gender
                job.get('requirements', ''),   # age_requirement
                f"站点ID: {job.get('station_id', '')}, 需求人数: {job.get('count', 0)}人",  # special_requirements
                '不接受',  # accept_criminal_record
                job.get('address', ''),        # location
                job.get('longitude'),          # longitude
                job.get('latitude'),           # latitude
                job.get('count', 0),           # urgent_capacity
                job.get('work_schedule', ''),  # working_hours
                '无要求',  # relevant_experience
                '是' if job.get('position_type') == '全职' else '否',  # full_time
                job.get('salary_info', ''),    # salary
                job.get('job_content', f"{job.get('position_name', '')} - {job.get('position_type', '')}"),  # job_content
                '上午9-11点，下午2-4点',    # interview_time
                '1-3天',   # trial_time
                '是',      # currently_recruiting
                '商业保险',      # insurance_status
                job.get('accommodation', '不包吃')  # accommodation_status
            ))
            inserted_count += 1
        except Exception as e:
            print(f"插入岗位数据失败: {e}")
            print(f"问题数据: {job}")

    conn.commit()
    conn.close()

    print(f"成功插入{inserted_count}个岗位到数据库")
    return inserted_count

def main():
    """主函数"""
    print("开始处理北京原始数据...")

    # 1. 读取位置信息
    position_data = read_position_data()

    # 2. 读取全职岗位缺口
    fulltime_jobs = read_fulltime_jobs()

    # 3. 读取兼职岗位缺口
    parttime_jobs = read_parttime_jobs()

    # 4. 读取住宿情况
    accommodation_data = read_accommodation_data()

    # 5. 读取薪资待遇和要求
    fulltime_salary, parttime_salary = read_salary_requirements()

    # 6. 整合数据
    print("\n=== 整合数据 ===")
    all_jobs = []

    # 处理全职岗位
    for job in fulltime_jobs:
        station_id = job['station_id']
        position_info = position_data.get(station_id, {})

        # 根据站点ID匹配住宿信息
        accommodation_info = "不包吃"
        accommodation_found = False
        if station_id in accommodation_data:
            accommodation_info += f", {accommodation_data[station_id]}"
            accommodation_found = True
        else:
            # 备用：根据站点名称匹配
            station_name = position_info.get('station_name', job.get('station_info', ''))
            for station_key, acc_info in accommodation_data.items():
                if station_key in station_name or station_name in station_key:
                    accommodation_info += f", {acc_info}"
                    accommodation_found = True
                    break

        # 如果没有匹配到住宿信息，统一增加不包住
        if not accommodation_found:
            accommodation_info += ", 不包住"

        # 根据岗位类型匹配详细薪资、工作时间和工作内容信息
        position_name = job['position_name']
        if '分拣员' in position_name:
            salary_info = "底薪2340元+职级0-700元/月+个人绩效400元+计件薪资约3800元/月，综合薪资：到手7000-9000元+，每月15号发薪，法定节假日三倍薪资"
            work_schedule = "轮班制: 7:00-19:00/8:00-20:00/9:00-21:00，特殊班次除外，中间休息1-2小时，不忙可以歇一歇，月休4-8天(排班轮休，根据门店忙碌情况排班)"
            job_content = "根据客户在线上下的订单，在货架上把货物找出来，清点好数量，用购物袋进行打包，放到指定取货台，让骑手来取"
        elif '白班理货' in position_name:
            salary_info = "底薪2340元+职级0-700元+个人绩效740元+理货提成约3340元/月，综合薪资7500-8500元+，每月15号发薪，法定节假日三倍薪资"
            work_schedule = "轮班制: 7:00-19:00/8:00-20:00/9:00-21:00，特殊班次除外，中间休息1-2小时，不忙可以歇一歇，月休4-8天(排班轮休，根据门店忙碌情况排班)"
            job_content = "超市货架空时，需要从库房拉货把货架补齐，查看商品生产日期，是否有破损，在岗时，需要货架饱满状态，遇到缺货时，及时找主管进行订货"
        elif '夜班理货' in position_name:
            salary_info = "底薪2340元+职级0-700元+夜班补贴780元+个人绩效740元+理货提成约3300元/月，综合薪资：7600-9000元+，每月15号发薪，法定节假日三倍薪资"
            work_schedule = "轮班制: 19:00-7:00/20:00-8:00/21:00-9:00，特殊班次除外，中间休息1-2小时，不忙可以歇一歇，月休4-8天(排班轮休，根据门店忙碌情况排班)"
            job_content = "美团生鲜超市的搬运理货，整理货架，归纳，下架"
        elif '水产专员' in position_name:
            salary_info = "底薪3120元+职级300-1500+个人绩效3545元，综合薪资：7000-8500元+，每月15号发薪，法定节假日三倍薪资"
            work_schedule = "轮班制: 7:00-19:00/8:00-20:00/9:00-21:00，特殊班次除外，中间休息1-2小时，不忙可以歇一歇，月休4-8天(排班轮休，根据门店忙碌情况排班)"
            job_content = "养鱼，杀鱼，捞虾(处理水产品)"
        elif '果切员' in position_name:
            salary_info = "底薪2340元+职级0-700元+个人绩效400元+计件薪资约3500元/月，综合薪资：6800-8800元+，每月15号发薪，法定节假日三倍薪资"
            work_schedule = "轮班制: 7:00-19:00/8:00-20:00/9:00-21:00，特殊班次除外，中间休息1-2小时，不忙可以歇一歇，月休4-8天(排班轮休，根据门店忙碌情况排班)"
            job_content = "水果切配，保证水果新鲜度和切配质量"
        else:
            salary_info = fulltime_salary
            work_schedule = '轮班制，月休4-8天'
            job_content = f"{job['position_name']} - 全职"

        job_record = {
            'station_id': station_id,
            'station_name': position_info.get('station_name', job.get('station_info', '')),
            'city': '北京',
            'district': position_info.get('district', ''),
            'address': position_info.get('address', job.get('store_location', '')),
            'longitude': position_info.get('longitude'),
            'latitude': position_info.get('latitude'),
            'position_name': job['position_name'],
            'position_type': '全职',
            'count': job['count'],
            'salary_info': salary_info,
            'work_schedule': work_schedule,
            'job_content': job_content,
            'requirements': '年龄18-45岁，试岗通过即可入职',
            'accommodation': accommodation_info,
            'manager_name': job.get('manager_name', ''),
            'manager_phone': job.get('manager_phone', '')
        }
        all_jobs.append(job_record)

    # 处理兼职岗位
    for job in parttime_jobs:
        station_id = job['station_id']
        position_info = position_data.get(station_id, {})

        # 根据站点ID匹配住宿信息
        accommodation_info = "不包吃"
        accommodation_found = False
        if station_id in accommodation_data:
            accommodation_info += f", {accommodation_data[station_id]}"
            accommodation_found = True
        else:
            # 备用：根据站点名称匹配
            station_name = position_info.get('station_name', job.get('station_info', ''))
            for station_key, acc_info in accommodation_data.items():
                if station_key in station_name or station_name in station_key:
                    accommodation_info += f", {acc_info}"
                    accommodation_found = True
                    break

        # 如果没有匹配到住宿信息，统一增加不包住
        if not accommodation_found:
            accommodation_info += ", 不包住"

        # 根据岗位类型匹配薪资信息
        position_name = job['position_name']
        if '分拣员' in position_name:
            salary_info = "21-31元/小时，熟练后有计件提成。工作时间：16-23点之间3-4小时或周末全天6-8小时"
        elif '理货' in position_name:
            salary_info = "22-32元/小时，熟练后有计件提成。工作时间：16-23点之间3-4小时或周末全天6-8小时"
        elif '水产专员' in position_name:
            salary_info = "25-35元/小时，熟练后有计件提成。工作时间：16-23点之间3-4小时或周末全天6-8小时"
        elif '果切员' in position_name:
            salary_info = "23-33元/小时，熟练后有计件提成。工作时间：16-23点之间3-4小时或周末全天6-8小时"
        elif '上架员' in position_name:
            salary_info = "20-30元/小时，熟练后有计件提成。工作时间：16-23点之间3-4小时或周末全天6-8小时"
        else:
            salary_info = parttime_salary

        job_record = {
            'station_id': station_id,
            'station_name': position_info.get('station_name', job.get('station_info', '')),
            'city': '北京',
            'district': position_info.get('district', ''),
            'address': position_info.get('address', job.get('store_location', '')),
            'longitude': position_info.get('longitude'),
            'latitude': position_info.get('latitude'),
            'position_name': job['position_name'],
            'position_type': '兼职',
            'count': job['count'],
            'salary_info': salary_info,
            'work_schedule': '16-23点之间3-4小时或周末全天6-8小时',
            'requirements': '年龄18-45岁，分拣要女性，理货要男性',
            'accommodation': accommodation_info,
            'manager_name': '',
            'manager_phone': job.get('manager_contact', '')
        }
        all_jobs.append(job_record)

    print(f"整合完成，共{len(all_jobs)}个岗位")

    # 7. 插入数据库
    if all_jobs:
        inserted_count = insert_jobs_to_database(all_jobs)
        print(f"\n=== 处理完成 ===")
        print(f"成功处理{inserted_count}个北京岗位")

        # 统计信息
        fulltime_count = len([j for j in all_jobs if j['position_type'] == '全职'])
        parttime_count = len([j for j in all_jobs if j['position_type'] == '兼职'])
        with_coords_count = len([j for j in all_jobs if j['longitude'] and j['latitude']])

        print(f"全职岗位: {fulltime_count}个")
        print(f"兼职岗位: {parttime_count}个")
        print(f"有坐标岗位: {with_coords_count}个 ({with_coords_count/len(all_jobs)*100:.1f}%)")
    else:
        print("没有找到有效的岗位数据")

if __name__ == "__main__":
    main()
