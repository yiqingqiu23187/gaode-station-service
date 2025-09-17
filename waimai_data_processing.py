#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
外卖岗位数据处理脚本
功能：将广深骑手外卖岗位数据添加到job_positions表
"""

import pandas as pd
import sqlite3
import os
from typing import List, Dict

def read_waimai_data() -> List[Dict]:
    """读取外卖岗位数据"""
    print("\n=== 读取外卖岗位数据 ===")
    
    waimai_file = "原始数据/广深骑手/美团外卖岗位属性.csv"
    if not os.path.exists(waimai_file):
        print(f"文件不存在: {waimai_file}")
        return []
    
    try:
        df = pd.read_csv(waimai_file)
        print(f"成功读取外卖岗位文件，共{len(df)}行数据")
        print(f"列名: {df.columns.tolist()}")
        
        # 显示前几行数据
        print(f"前3行数据:")
        print(df.head(3))
        
        waimai_jobs = []
        
        for _, row in df.iterrows():
            # 跳过无效数据
            if pd.isna(row.get('岗位类型')) or pd.isna(row.get('招聘单位')):
                continue
            
            # 处理经纬度数据
            longitude = None
            latitude = None
            try:
                if pd.notna(row.get('经度')):
                    longitude = float(row.get('经度'))
                if pd.notna(row.get('维度')):  # 注意原数据中是"维度"不是"纬度"
                    latitude = float(row.get('维度'))
            except:
                pass
            
            # 处理年龄要求
            age_requirement = str(row.get('年龄要求（区间）', '18~45')).replace('~', '-')
            
            # 处理特殊要求
            special_requirements = str(row.get('特殊要求', ''))
            
            # 处理薪资信息
            salary_info = str(row.get('薪资', ''))
            
            # 处理工作内容
            job_content = str(row.get('工作内容', ''))
            
            # 处理工作时间
            working_hours = str(row.get('工作时间', ''))
            
            # 处理面试时间
            interview_time = str(row.get('面试时间', ''))
            
            # 处理试岗时间
            trial_time = str(row.get('试岗时间', ''))
            
            job_record = {
                'job_type': row.get('岗位类型', ''),
                'recruiting_unit': row.get('招聘单位', ''),
                'city': row.get('城市', ''),
                'gender': row.get('性别', ''),
                'age_requirement': age_requirement,
                'special_requirements': special_requirements,
                'accept_criminal_record': '否' if row.get('是否接受有犯罪记录') == '否' else '是',
                'location': row.get('位置', ''),
                'longitude': longitude,
                'latitude': latitude,
                'urgent_capacity': 1,  # 外卖岗位默认急需人数为1
                'working_hours': working_hours,
                'relevant_experience': '无要求',
                'full_time': '是',  # 外卖岗位按全职处理
                'salary': salary_info,
                'job_content': job_content,
                'interview_time': interview_time if interview_time and interview_time != 'nan' else '上午9-11点，下午2-4点',
                'trial_time': trial_time if trial_time and trial_time != 'nan' else '1-3天',
                'currently_recruiting': '是' if row.get('是否招聘') == '是' else '否',
                'insurance_status': '商业保险',
                'accommodation_status': '不包吃, 不包住'  # 外卖岗位默认不包吃住
            }
            
            waimai_jobs.append(job_record)
        
        print(f"成功提取{len(waimai_jobs)}个外卖岗位")
        return waimai_jobs
        
    except Exception as e:
        print(f"读取外卖岗位文件失败: {e}")
        return []

def insert_waimai_jobs_to_database(jobs_data: List[Dict]):
    """将外卖岗位数据插入到数据库"""
    print(f"\n=== 插入{len(jobs_data)}个外卖岗位到数据库 ===")
    
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
            print(f"插入外卖岗位数据失败: {e}")
            print(f"问题数据: {job}")
    
    conn.commit()
    conn.close()
    
    print(f"成功插入{inserted_count}个外卖岗位到数据库")
    return inserted_count

def main():
    """主函数"""
    print("开始处理外卖岗位数据...")
    
    # 读取外卖岗位数据
    waimai_jobs = read_waimai_data()
    
    if not waimai_jobs:
        print("没有找到外卖岗位数据")
        return
    
    # 插入到数据库
    inserted_count = insert_waimai_jobs_to_database(waimai_jobs)
    
    print(f"\n=== 处理完成 ===")
    print(f"成功处理{inserted_count}个外卖岗位")
    
    # 统计信息
    cities = {}
    for job in waimai_jobs:
        city = job.get('city', '未知')
        cities[city] = cities.get(city, 0) + 1
    
    print(f"城市分布:")
    for city, count in cities.items():
        print(f"  {city}: {count}个岗位")

if __name__ == "__main__":
    main()
