#!/usr/bin/env python3
"""
北京原始数据处理脚本
处理北京文件夹中的各个信息文件，将信息汇总整理后添加到job_position表
"""

import pandas as pd
import sqlite3
import os
import logging
from typing import Dict, List, Tuple, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('beijing_data_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 数据库文件路径
DB_FILE = 'stations.db'

# 北京数据文件路径
BEIJING_DATA_DIR = '原始数据/北京'
POSITION_FILE = os.path.join(BEIJING_DATA_DIR, '位置信息.xlsx')
FULLTIME_DEMAND_FILE = os.path.join(BEIJING_DATA_DIR, '全职缺口.xlsx')
PARTTIME_DEMAND_FILE = os.path.join(BEIJING_DATA_DIR, '兼职缺口.xlsx')
ACCOMMODATION_FILE = os.path.join(BEIJING_DATA_DIR, '北京住宿情况.xlsx')
FULLTIME_REQUIREMENTS_FILE = os.path.join(BEIJING_DATA_DIR, '全职待遇及要求')
PARTTIME_REQUIREMENTS_FILE = os.path.join(BEIJING_DATA_DIR, '兼职待遇及要求')

# 岗位类型映射
JOB_TYPE_MAPPING = {
    '分拣员': '分拣打包员',
    '白班理货': '白班理货员',
    '夜班理货': '夜班理货员',
    '水产专员': '水产专员',
    '果切员': '果切员',
    '库管员': '库管员',
    '上架员': '上架员',
    '果蔬加工员': '果蔬加工员'
}

def get_db_connection():
    """获取数据库连接"""
    return sqlite3.connect(DB_FILE)

def read_position_data() -> Dict[str, Dict]:
    """读取位置信息数据"""
    logger.info("读取位置信息数据")

    try:
        df = pd.read_excel(POSITION_FILE)
        logger.info(f"位置信息文件列名: {df.columns.tolist()}")

        position_data = {}
        for _, row in df.iterrows():
            station_name = str(row.get('站点名称', row.get('站点', row.get('服务站', ''))))
            if station_name and station_name != 'nan':
                # 提取站点ID (例如: 小象超市-天桥站-BJ0129 -> BJ0129)
                station_id = station_name
                if '-BJ' in station_name:
                    parts = station_name.split('-BJ')
                    if len(parts) > 1:
                        station_id = 'BJ' + parts[1].split('-')[0]

                position_data[station_id] = {
                    'full_name': station_name,
                    'address': str(row.get('地址', row.get('门店地址', ''))),
                    'longitude': row.get('经度', row.get('longitude', None)),
                    'latitude': row.get('纬度', row.get('latitude', None)),
                    'contact_person': str(row.get('联系人', row.get('站长', ''))),
                    'contact_phone': str(row.get('联系电话', row.get('联系方式', '')))
                }

        logger.info(f"读取到{len(position_data)}个站点的位置信息")
        return position_data

    except Exception as e:
        logger.error(f"读取位置信息失败: {e}")
        return {}

def read_demand_data(file_path: str, job_type: str) -> Dict[str, Dict]:
    """读取岗位缺口数据"""
    logger.info(f"读取{job_type}缺口数据: {file_path}")

    try:
        # 先读取所有数据，然后找到正确的表头行
        df_raw = pd.read_excel(file_path, header=None)
        logger.info(f"原始文件形状: {df_raw.shape}")

        # 查找包含站点信息的行
        header_row = None
        station_col = None

        for i, row in df_raw.iterrows():
            row_str = ' '.join([str(cell) for cell in row if pd.notna(cell)])
            if '站点' in row_str or '服务站' in row_str:
                header_row = i
                # 找到站点列的位置
                for j, cell in enumerate(row):
                    if pd.notna(cell) and ('站点' in str(cell) or '服务站' in str(cell)):
                        station_col = j
                        break
                break

        if header_row is None:
            logger.warning(f"未找到表头行，尝试使用默认方式读取")
            # 尝试跳过前几行重新读取
            for skip_rows in [0, 1, 2, 3]:
                try:
                    df = pd.read_excel(file_path, skiprows=skip_rows)
                    if len(df) > 0:
                        logger.info(f"跳过{skip_rows}行后的列名: {df.columns.tolist()}")
                        break
                except:
                    continue
            else:
                return {}
        else:
            # 使用找到的表头行重新读取
            df = pd.read_excel(file_path, skiprows=header_row)
            logger.info(f"使用第{header_row}行作为表头，列名: {df.columns.tolist()}")

        demand_data = {}

        # 查找站点名称列
        station_column = None
        for col in df.columns:
            if '站点' in str(col) or '服务站' in str(col) or '门店' in str(col):
                station_column = col
                break

        if station_column is None:
            logger.warning("未找到站点名称列")
            return {}

        logger.info(f"使用列 '{station_column}' 作为站点名称")

        for _, row in df.iterrows():
            station_name = str(row.get(station_column, ''))
            if station_name and station_name != 'nan' and station_name.strip():
                # 清理站点名称
                station_name = station_name.strip()
                if station_name.startswith('小象超市-'):
                    station_name = station_name.replace('小象超市-', '').split('-')[0]

                # 提取各岗位的缺口数量
                station_demands = {}
                for col in df.columns:
                    col_str = str(col)
                    if any(keyword in col_str for keyword in ['分拣', '理货', '水产', '果切', '库管', '上架', '加工']):
                        demand_count = row.get(col, 0)
                        try:
                            if pd.notna(demand_count) and str(demand_count).strip() and demand_count != 0:
                                demand_num = int(float(demand_count))
                                if demand_num > 0:
                                    # 映射岗位类型
                                    if '分拣' in col_str:
                                        job_name = '分拣打包员'
                                    elif '白班' in col_str and '理货' in col_str:
                                        job_name = '白班理货员'
                                    elif '夜班' in col_str and '理货' in col_str:
                                        job_name = '夜班理货员'
                                    elif '水产' in col_str:
                                        job_name = '水产专员'
                                    elif '果切' in col_str:
                                        job_name = '果切员'
                                    elif '库管' in col_str:
                                        job_name = '库管员'
                                    elif '上架' in col_str:
                                        job_name = '上架员'
                                    elif '加工' in col_str:
                                        job_name = '果蔬加工员'
                                    else:
                                        job_name = col_str

                                    station_demands[job_name] = demand_num
                        except (ValueError, TypeError):
                            continue

                if station_demands:
                    demand_data[station_name] = station_demands
                    logger.debug(f"站点 {station_name} 的缺口: {station_demands}")

        logger.info(f"读取到{len(demand_data)}个站点的{job_type}缺口信息")
        return demand_data

    except Exception as e:
        logger.error(f"读取{job_type}缺口数据失败: {e}")
        return {}

def read_accommodation_data() -> Dict[str, str]:
    """读取住宿情况数据"""
    logger.info("读取住宿情况数据")

    try:
        df = pd.read_excel(ACCOMMODATION_FILE)
        logger.info(f"住宿情况文件列名: {df.columns.tolist()}")

        accommodation_data = {}

        # 查找可覆盖站点列
        station_column = None
        for col in df.columns:
            if '可覆盖站点' in str(col) or '站点' in str(col):
                station_column = col
                break

        if station_column is None:
            logger.warning("未找到站点列，使用默认住宿情况")
            return {}

        for _, row in df.iterrows():
            stations_str = str(row.get(station_column, ''))
            if stations_str and stations_str != 'nan' and stations_str.strip():
                # 解析可覆盖的站点
                stations = []
                if '，' in stations_str:
                    stations = [s.strip() for s in stations_str.split('，')]
                elif ',' in stations_str:
                    stations = [s.strip() for s in stations_str.split(',')]
                elif ' ' in stations_str:
                    stations = [s.strip() for s in stations_str.split(' ')]
                else:
                    stations = [stations_str.strip()]

                # 构建住宿信息
                accommodation_info = []

                # 住宿费用
                cost = row.get('住宿费/月', '')
                if pd.notna(cost) and str(cost).strip():
                    accommodation_info.append(f"住宿费{cost}元/月")

                # 房型
                room_type = row.get('房型\n（几人间）', '')
                if pd.notna(room_type) and str(room_type).strip():
                    accommodation_info.append(f"{room_type}")

                # 押金
                deposit = row.get('押金（什么时间退回）', '')
                if pd.notna(deposit) and str(deposit).strip():
                    accommodation_info.append(f"押金{deposit}")

                accommodation_status = '，'.join(accommodation_info) if accommodation_info else '提供住宿'

                # 为每个站点设置住宿情况
                for station in stations:
                    if station:
                        accommodation_data[station] = accommodation_status

        logger.info(f"读取到{len(accommodation_data)}个站点的住宿情况")
        return accommodation_data

    except Exception as e:
        logger.error(f"读取住宿情况数据失败: {e}")
        return {}

def read_requirements_data(file_path: str) -> Dict[str, Dict]:
    """读取待遇及要求数据"""
    logger.info(f"读取待遇及要求数据: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        requirements_data = {}
        
        # 解析全职待遇及要求
        if '全职' in file_path:
            # 分拣打包员
            if '【分拣打包员】' in content:
                requirements_data['分拣打包员'] = {
                    'job_content': '根据客户在线上下的订单，在货架上把货物找出来，清点好数量，用购物袋进行打包，放到指定取货台，让骑手来取',
                    'salary': '底薪2340元+职级0-700元/月+个人绩效400元+计件薪资约3800元/月，综合薪资：到手7000-9000元+',
                    'working_hours': '轮班制: 7:00-19:00/8:00-20:00/9:00-21:00，特殊班次除外，中间休息1-2小时，月休4-8天',
                    'full_time': '是',
                    'gender': '女',
                    'age_requirement': '18-45岁',
                    'special_requirements': '不戴眼镜，手脚麻利接受低温工作，不要暑假工，需要进冷库，有经验优先',
                    'insurance_status': '商业保险'
                }
            
            # 白班理货员
            if '【白班理货】' in content:
                requirements_data['白班理货员'] = {
                    'job_content': '超市货架空时，需要从库房拉货把货架补齐，查看商品生产日期，是否有破损，在岗时，需要货架饱满状态，遇到缺货时，及时找主管进行订货',
                    'salary': '底薪2340元+职级0-700元+个人绩效740元+理货提成约3340元/月，综合薪资元7500-8500元+',
                    'working_hours': '轮班制: 7:00-19:00/8:00-20:00/9:00-21:00，特殊班次除外，中间休息1-2小时，月休4-8天',
                    'full_time': '是',
                    'gender': '男',
                    'age_requirement': '18-45岁',
                    'insurance_status': '商业保险'
                }
            
            # 夜班理货员
            if '【夜班理货】' in content:
                requirements_data['夜班理货员'] = {
                    'job_content': '美团生鲜超市的搬运理货，整理货架，归纳，下架',
                    'salary': '底薪2340元+职级0-700元+夜班补贴780元+个人绩效740元+理货提成约3300元/月，综合薪资：7600-9000元+',
                    'working_hours': '轮班制: 19:00-7:00/20:00-8:00/21:00-9:00，特殊班次除外，中间休息1-2小时，月休4-8天',
                    'full_time': '是',
                    'gender': '男',
                    'age_requirement': '18-45岁',
                    'insurance_status': '商业保险'
                }
            
            # 水产专员
            if '【水产专员】' in content:
                requirements_data['水产专员'] = {
                    'job_content': '养鱼，杀鱼，捞虾(处理水产品)',
                    'salary': '底薪3120元+职级300-1500+个人绩效3545元，综合薪资：7000-8500元+',
                    'working_hours': '轮班制: 7:00-19:00/8:00-20:00/9:00-21:00，特殊班次除外，中间休息1-2小时，月休4-8天',
                    'full_time': '是',
                    'gender': '不限',
                    'age_requirement': '18-45岁',
                    'special_requirements': '有经验优先',
                    'insurance_status': '商业保险'
                }
        
        # 解析兼职待遇及要求
        elif '兼职' in file_path:
            requirements_data['兼职分拣员'] = {
                'job_content': '根据客户在线上下的订单，在货架上把货物找出来，清点好数量，用购物袋进行打包',
                'salary': '21元/小时，熟练之后效率高的话有计件提成，最高31元/小时',
                'working_hours': '16-23点之间上3-4小时即可或者周末全天6-8小时',
                'full_time': '否',
                'gender': '女',
                'age_requirement': '18-45岁'
            }
            
            requirements_data['兼职理货员'] = {
                'job_content': '超市货架空时，需要从库房拉货把货架补齐，查看商品生产日期，是否有破损',
                'salary': '21元/小时，熟练之后效率高的话有计件提成，最高31元/小时',
                'working_hours': '16-23点之间上3-4小时即可或者周末全天6-8小时',
                'full_time': '否',
                'gender': '男',
                'age_requirement': '18-45岁'
            }
        
        logger.info(f"解析到{len(requirements_data)}个岗位的待遇及要求信息")
        return requirements_data
        
    except Exception as e:
        logger.error(f"读取待遇及要求数据失败: {e}")
        return {}

def generate_job_records() -> List[Dict]:
    """生成完整的岗位记录"""
    logger.info("开始生成岗位记录")
    
    # 读取各类数据
    position_data = read_position_data()
    fulltime_demand_data = read_demand_data(FULLTIME_DEMAND_FILE, '全职')
    parttime_demand_data = read_demand_data(PARTTIME_DEMAND_FILE, '兼职')
    accommodation_data = read_accommodation_data()
    fulltime_requirements = read_requirements_data(FULLTIME_REQUIREMENTS_FILE)
    parttime_requirements = read_requirements_data(PARTTIME_REQUIREMENTS_FILE)
    
    job_records = []
    
    # 处理全职岗位
    for station_name, demands in fulltime_demand_data.items():
        station_info = position_data.get(station_name, {})
        accommodation_status = f"不包吃，{accommodation_data.get(station_name, '不提供住宿')}"
        
        for job_type, demand_count in demands.items():
            job_requirements = fulltime_requirements.get(job_type, {})
            
            job_record = {
                'job_type': job_type,
                'recruiting_unit': station_name,
                'city': '北京',
                'gender': job_requirements.get('gender', '不限'),
                'age_requirement': job_requirements.get('age_requirement', '18-45岁'),
                'special_requirements': job_requirements.get('special_requirements', ''),
                'accept_criminal_record': '否',
                'location': station_info.get('address', ''),
                'longitude': station_info.get('longitude'),
                'latitude': station_info.get('latitude'),
                'urgent_capacity': demand_count,
                'working_hours': job_requirements.get('working_hours', ''),
                'relevant_experience': '无需经验，有经验者优先',
                'full_time': job_requirements.get('full_time', '是'),
                'salary': job_requirements.get('salary', ''),
                'job_content': job_requirements.get('job_content', ''),
                'interview_time': '周一至周五14:00-16:00',
                'trial_time': '下午三点前',
                'currently_recruiting': '是' if demand_count > 0 else '否',
                'insurance_status': job_requirements.get('insurance_status', '商业保险'),
                'accommodation_status': accommodation_status
            }
            
            job_records.append(job_record)
    
    # 处理兼职岗位
    for station_name, demands in parttime_demand_data.items():
        station_info = position_data.get(station_name, {})
        accommodation_status = f"不包吃，{accommodation_data.get(station_name, '不提供住宿')}"
        
        for job_type, demand_count in demands.items():
            # 兼职岗位类型映射
            if '分拣' in job_type:
                parttime_job_type = '兼职分拣员'
            elif '理货' in job_type:
                parttime_job_type = '兼职理货员'
            else:
                parttime_job_type = f'兼职{job_type}'
            
            job_requirements = parttime_requirements.get(parttime_job_type, {})
            
            job_record = {
                'job_type': parttime_job_type,
                'recruiting_unit': station_name,
                'city': '北京',
                'gender': job_requirements.get('gender', '不限'),
                'age_requirement': job_requirements.get('age_requirement', '18-45岁'),
                'special_requirements': job_requirements.get('special_requirements', ''),
                'accept_criminal_record': '否',
                'location': station_info.get('address', ''),
                'longitude': station_info.get('longitude'),
                'latitude': station_info.get('latitude'),
                'urgent_capacity': demand_count,
                'working_hours': job_requirements.get('working_hours', ''),
                'relevant_experience': '无需经验',
                'full_time': job_requirements.get('full_time', '否'),
                'salary': job_requirements.get('salary', ''),
                'job_content': job_requirements.get('job_content', ''),
                'interview_time': '周一至周五14:00-16:00',
                'trial_time': '下午三点前',
                'currently_recruiting': '是' if demand_count > 0 else '否',
                'insurance_status': job_requirements.get('insurance_status', ''),
                'accommodation_status': accommodation_status
            }
            
            job_records.append(job_record)
    
    logger.info(f"生成了{len(job_records)}条岗位记录")
    return job_records

def insert_job_records(records: List[Dict]):
    """将岗位记录插入数据库"""
    logger.info("开始插入岗位记录到数据库")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 删除北京的现有岗位记录
        cursor.execute("DELETE FROM job_positions WHERE city = '北京'")
        logger.info("已删除北京的现有岗位记录")
        
        # 插入新记录
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
        logger.info(f"成功插入{len(records)}条北京岗位记录")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"插入岗位记录失败: {e}")
        raise
    finally:
        conn.close()

def main():
    """主函数"""
    logger.info("开始处理北京原始数据")
    
    try:
        # 检查文件是否存在
        required_files = [POSITION_FILE, FULLTIME_DEMAND_FILE, PARTTIME_DEMAND_FILE, 
                         ACCOMMODATION_FILE, FULLTIME_REQUIREMENTS_FILE, PARTTIME_REQUIREMENTS_FILE]
        
        for file_path in required_files:
            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                return
        
        # 生成岗位记录
        job_records = generate_job_records()
        
        if job_records:
            # 插入数据库
            insert_job_records(job_records)
            logger.info("北京数据处理完成")
        else:
            logger.warning("没有生成任何岗位记录")
            
    except Exception as e:
        logger.error(f"处理北京数据时发生错误: {e}")
        raise

if __name__ == '__main__':
    main()
