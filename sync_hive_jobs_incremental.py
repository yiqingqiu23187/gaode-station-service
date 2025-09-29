#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增量数据同步脚本 - 只更新招聘状态
"""

import pandas as pd
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from pytalos.client import AsyncTalosClient

# Hive配置信息
HIVE_CONFIG = {
    'host': 'talos.sankuai.com',
    'port': 443,
    'mis_username': 'huangzihao12',
    'session_id': '831c371003ee44be9c458185d723e061',
    'table_name': 'mart_mall_dm.topic_fdc_labor_prot_poi_dt'
}

# 目标城市和满编率阈值
CITY_THRESHOLDS = {
    '北京': 1.0,
    '广州': 0.9,
    '深圳': 0.9
}

# 岗位类型映射（映射到数据库中实际的岗位类型）
FULLTIME_JOB_MAPPING = {
    'ft_pick_req_hc': '白班分拣员',
    'ft_stock_clerk_pick_req_hc': '夜班理货员',
    'ft_aquatic_pick_req_hc': '水产专员（兼职）'  # 注意：数据库中水产是兼职
}

def log_info(message: str):
    """日志输出"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def connect_hive() -> Optional[AsyncTalosClient]:
    """连接Hive数据仓库"""
    try:
        from pytalos.client import AsyncTalosClient, SDKScene

        client = AsyncTalosClient(
            HIVE_CONFIG['mis_username'],
            HIVE_CONFIG['session_id'],
            sdk_scene=SDKScene.MIS
        )
        client.open_session()
        return client
    except Exception as e:
        log_info(f"Hive连接失败: {e}")
        return None

def query_hive_data_with_fallback(client, query_date: str) -> Optional[pd.DataFrame]:
    """查询指定日期的Hive数据"""
    try:
        city_filter = "', '".join(CITY_THRESHOLDS.keys())
        sql = f"""
        SELECT
            poi_id,
            poi_name,
            city_name,
            ft_onsite_emp_cnt,
            ft_req_hc,
            ft_pick_req_hc,
            ft_stock_clerk_pick_req_hc,
            ft_aquatic_pick_req_hc
        FROM {HIVE_CONFIG['table_name']}
        WHERE dt = '{query_date}'
        AND city_name IN ('{city_filter}')
        """

        log_info(f"尝试查询日期: {query_date}")

        # 提交查询
        qid = client.submit(statement=sql)

        # 等待查询完成
        while True:
            query_info = client.get_query_info(qid)
            status = query_info["status"]

            if status == "FINISHED":
                break
            elif status in ["QUERY_TIMEOUT", "FAILED", "KILLED"] or status.startswith("ERROR_"):
                log_info(f"查询日期 {query_date} 失败: {status}")
                return None

            time.sleep(3)

        # 获取结果
        result = client.fetch_all(qid)
        data = result["data"]

        if not data or len(data) == 0:
            log_info(f"日期 {query_date} 无数据")
            return None

        # 手动指定列名
        column_names = [
            'poi_id', 'poi_name', 'city_name', 'ft_onsite_emp_cnt', 'ft_req_hc',
            'ft_pick_req_hc', 'ft_stock_clerk_pick_req_hc', 'ft_aquatic_pick_req_hc'
        ]

        df = pd.DataFrame(data, columns=column_names)
        log_info(f"成功获取日期 {query_date} 的 {len(df)} 条站点数据")
        return df

    except Exception as e:
        log_info(f"查询日期 {query_date} 异常: {e}")
        return None

def query_hive_data(client) -> Optional[pd.DataFrame]:
    """查询Hive数据 - 先查昨天，失败则查前天"""

    # 优先查询昨天的数据
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    df = query_hive_data_with_fallback(client, yesterday)

    if df is not None:
        log_info(f"✅ 使用昨天数据: {yesterday}")
        return df

    # 昨天没有数据，尝试前天
    day_before_yesterday = (datetime.now() - timedelta(days=2)).strftime('%Y%m%d')
    df = query_hive_data_with_fallback(client, day_before_yesterday)

    if df is not None:
        log_info(f"⚠️ 昨天无数据，使用前天数据: {day_before_yesterday}")
        return df

    log_info(f"❌ 昨天({yesterday})和前天({day_before_yesterday})都无可用数据")
    return None

def safe_float(value, default=0.0):
    """安全转换为float，处理NULL值"""
    if value is None or value == 'NULL' or value == '':
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value, default=0):
    """安全转换为int，处理NULL值"""
    if value is None or value == 'NULL' or value == '':
        return default
    try:
        return int(float(value))  # 先转float再转int，处理小数
    except (ValueError, TypeError):
        return default

def calculate_recruitment_status(df: pd.DataFrame) -> List[Tuple[str, str, str]]:
    """
    计算招聘状态
    返回: [(招聘单位, 岗位类型, 当前招聘), ...]
    """
    recruitment_updates = []

    for _, row in df.iterrows():
        poi_name = str(row['poi_name'])
        city_name = str(row['city_name'])

        # 计算满编率
        onsite_count = safe_float(row.get('ft_onsite_emp_cnt', 0))
        required_hc = safe_float(row.get('ft_req_hc', 0))

        # 跳过空值或0值
        if onsite_count <= 0 or required_hc <= 0:
            log_info(f"跳过数据不完整的站点: {poi_name} (在职:{onsite_count}, 编制:{required_hc})")
            continue

        # 计算满编率
        staffing_ratio = onsite_count / required_hc
        threshold = CITY_THRESHOLDS.get(city_name, 1.0)

        # 判断是否招聘（满编率超过阈值则不招聘）
        is_recruiting = staffing_ratio <= threshold
        recruiting_status = "是" if is_recruiting else "否"

        log_info(f"站点: {poi_name}, 城市: {city_name}, 满编率: {staffing_ratio:.3f}, 阈值: {threshold}, 招聘状态: {recruiting_status}")

        # 处理每个全职岗位类型 - 不管需求人数多少，都要更新招聘状态
        for hive_field, job_type in FULLTIME_JOB_MAPPING.items():
            job_demand = safe_int(row.get(hive_field, 0))

            # 对所有全职岗位类型都更新招聘状态（基于站点满编率）
            recruitment_updates.append((poi_name, job_type, recruiting_status))
            log_info(f"  -> {job_type}: Hive需求{job_demand}人, 更新招聘状态为: {recruiting_status}")

    return recruitment_updates

def extract_station_name(full_name: str) -> str:
    """
    从完整站点名称中提取简化名称
    例如：小象超市-锦尚站-SZ0158 -> 锦尚站
    """
    import re

    # 使用正则表达式一步提取站点名称
    # 匹配模式：小象超市-{站点名}-{站点代码}
    match = re.match(r'^小象超市-(.+?)-[A-Z]{2}\d+$', full_name)
    if match:
        return match.group(1)

    # 如果不匹配标准格式，尝试其他处理
    # 去掉开头的"小象超市-"
    if full_name.startswith('小象超市-'):
        name_part = full_name[5:]  # 去掉"小象超市-"
        # 去掉结尾的站点代码（如-SZ0158, -BJ0226等）
        name_part = re.sub(r'-[A-Z]{2}\d+$', '', name_part)
        return name_part

    return full_name

def update_database_recruitment_status(recruitment_updates: List[Tuple[str, str, str]]) -> bool:
    """
    更新数据库中的招聘状态
    支持格式兼容匹配
    """
    if not recruitment_updates:
        log_info("没有需要更新的招聘状态")
        return True

    try:
        conn = sqlite3.connect('stations.db')
        cursor = conn.cursor()

        updated_count = 0
        not_found_count = 0

        for recruiting_unit, job_type, currently_recruiting in recruitment_updates:
            # 方式1：直接匹配完整名称
            cursor.execute("""
                SELECT id FROM job_positions
                WHERE recruiting_unit = ? AND job_type = ?
            """, (recruiting_unit, job_type))

            records = cursor.fetchall()

            # 方式2：如果直接匹配失败，尝试提取站点名称进行匹配
            if not records:
                station_name = extract_station_name(recruiting_unit)
                cursor.execute("""
                    SELECT id FROM job_positions
                    WHERE recruiting_unit = ? AND job_type = ?
                """, (station_name, job_type))
                records = cursor.fetchall()

                if records:
                    log_info(f"格式兼容匹配成功: {recruiting_unit} -> {station_name}")

            if records:
                # 更新招聘状态（使用数据库中的实际名称）
                cursor.execute("""
                    SELECT DISTINCT recruiting_unit FROM job_positions
                    WHERE recruiting_unit IN (?, ?) AND job_type = ?
                """, (recruiting_unit, extract_station_name(recruiting_unit), job_type))

                db_recruiting_unit = cursor.fetchone()[0]

                cursor.execute("""
                    UPDATE job_positions
                    SET currently_recruiting = ?
                    WHERE recruiting_unit = ? AND job_type = ?
                """, (currently_recruiting, db_recruiting_unit, job_type))

                affected_rows = cursor.rowcount
                updated_count += affected_rows

                log_info(f"更新 {db_recruiting_unit} - {job_type}: {currently_recruiting} (影响{affected_rows}条记录)")
            else:
                not_found_count += 1
                log_info(f"未找到匹配记录: {recruiting_unit} -> {extract_station_name(recruiting_unit)} - {job_type}")

        conn.commit()
        conn.close()

        log_info(f"数据库更新完成: 成功更新{updated_count}条记录, 未找到{not_found_count}条记录")
        return True

    except Exception as e:
        log_info(f"数据库更新失败: {e}")
        return False

def get_database_stats():
    """获取数据库统计信息"""
    try:
        conn = sqlite3.connect('stations.db')
        cursor = conn.cursor()

        # 总岗位数
        cursor.execute("SELECT COUNT(*) FROM job_positions")
        total_jobs = cursor.fetchone()[0]

        # 正在招聘的岗位数
        cursor.execute("SELECT COUNT(*) FROM job_positions WHERE currently_recruiting = '是'")
        recruiting_jobs = cursor.fetchone()[0]

        # 按城市统计
        cursor.execute("""
            SELECT city,
                   COUNT(*) as total,
                   SUM(CASE WHEN currently_recruiting='是' THEN 1 ELSE 0 END) as recruiting
            FROM job_positions
            GROUP BY city
            ORDER BY total DESC
        """)
        city_stats = cursor.fetchall()

        conn.close()

        log_info(f"数据库统计: 总岗位{total_jobs}个, 正在招聘{recruiting_jobs}个")
        for city, total, recruiting in city_stats:
            log_info(f"  {city}: {total}个岗位, {recruiting}个在招聘")

    except Exception as e:
        log_info(f"获取统计信息失败: {e}")

def main():
    """主函数"""
    log_info("=== 开始增量数据同步 ===")

    # 1. 连接Hive
    log_info("步骤1: 连接Hive数据仓库...")
    client = connect_hive()
    if not client:
        log_info("❌ Hive连接失败")
        return False

    # 2. 查询数据
    log_info("步骤2: 查询Hive数据...")
    df = query_hive_data(client)
    if df is None or len(df) == 0:
        log_info("❌ 未获取到有效数据")
        return False

    # 3. 计算招聘状态
    log_info("步骤3: 计算招聘状态...")
    recruitment_updates = calculate_recruitment_status(df)

    if not recruitment_updates:
        log_info("❌ 没有生成任何招聘状态更新")
        return False

    log_info(f"生成{len(recruitment_updates)}个招聘状态更新")

    # 4. 更新数据库
    log_info("步骤4: 更新数据库...")
    success = update_database_recruitment_status(recruitment_updates)

    if not success:
        log_info("❌ 数据库更新失败")
        return False

    # 5. 显示统计信息
    log_info("步骤5: 显示最新统计...")
    get_database_stats()

    log_info("✅ 增量数据同步成功")
    log_info("=== 数据同步结束 ===")
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
