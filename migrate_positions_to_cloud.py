#!/usr/bin/env python3
"""
岗位数据迁移脚本
功能：将 SQLite 数据库中的 job_positions 表数据导入到 MySQL 云数据库的 position 表
"""

import sqlite3
import pymysql
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import sys
import os

# ============ 配置信息 ============

# SQLite 本地数据库配置
SQLITE_DB_PATH = "app/database/stations.db"

# MySQL 云数据库配置（请填写实际的连接信息）
MYSQL_CONFIG = {
    "host": "bj-cynosdbmysql-grp-5eypnf9y.sql.tencentcdb.com",  # 例如: "bj-cynosdbmysql-grp-xxxxx.sql.tencentcdb.com"
    "port": 26606,   # 例如: 26606
    "user": "root",  # 例如: "root"
    "password": "Gn123456",  # 数据库密码
    "database": "recruit-db_bak",  # 例如: "recruit-db"
    "charset": "utf8mb4"
}

# 批量插入的批次大小
BATCH_SIZE = 100

# 测试模式：如果为 True，只导入1条数据用于测试
TEST_MODE = False
TEST_LIMIT = 1  # 测试模式下导入的记录数

# ============ 颜色输出 ============

class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color

def log_info(msg: str):
    print(f"{Colors.GREEN}[INFO]{Colors.NC} {msg}")

def log_warning(msg: str):
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {msg}")

def log_error(msg: str):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}")

def log_step(msg: str):
    print(f"{Colors.BLUE}[STEP]{Colors.NC} {msg}")

def log_success(msg: str):
    print(f"{Colors.CYAN}[SUCCESS]{Colors.NC} {msg}")

# ============ 数据转换函数 ============

def convert_gender(gender_text: Optional[str]) -> Optional[str]:
    """
    转换性别字段
    SQLite: "男"/"女"/"不限" -> MySQL ENUM: "male"/"female"/"no_limit"
    """
    if not gender_text:
        return None

    gender_map = {
        "男": "male",
        "女": "female",
        "不限": "no_limit",
        "无要求": "no_limit",
        "男女不限": "no_limit"
    }

    return gender_map.get(gender_text.strip(), "no_limit")

def convert_boolean(text: Optional[str]) -> Optional[bool]:
    """
    转换布尔字段
    SQLite: "是"/"否" -> MySQL BOOLEAN: True/False
    """
    if not text:
        return None

    text = text.strip()
    if text == "是":
        return True
    elif text == "否":
        return False
    return None

def convert_urgency_level(urgent_capacity: Optional[int]) -> Optional[str]:
    """
    转换紧急程度
    SQLite: INTEGER (0-N) -> MySQL ENUM: "low"/"medium"/"high"/"urgent"
    """
    if urgent_capacity is None:
        return None

    if urgent_capacity == 0:
        return "low"
    elif urgent_capacity <= 5:
        return "medium"
    elif urgent_capacity <= 10:
        return "high"
    else:
        return "urgent"

def convert_employment_type(full_time_text: Optional[str]) -> Optional[str]:
    """
    转换雇佣类型
    SQLite: TEXT -> MySQL ENUM: "full_time"/"part_time"/"temporary"/"flexible"
    """
    if not full_time_text:
        return None

    text = full_time_text.strip().lower()

    if "全职" in text or "full" in text:
        return "full_time"
    elif "兼职" in text or "part" in text:
        return "part_time"
    elif "临时" in text or "temp" in text:
        return "temporary"
    elif "灵活" in text or "flexible" in text:
        return "flexible"
    else:
        return "full_time"  # 默认全职

def convert_decimal(value: Optional[float]) -> Optional[Decimal]:
    """
    转换浮点数为 Decimal
    """
    if value is None:
        return None
    return Decimal(str(value))

# ============ 数据库操作函数 ============

def check_sqlite_database() -> Tuple[bool, int]:
    """
    检查 SQLite 数据库
    返回: (是否成功, 记录数)
    """
    try:
        if not os.path.exists(SQLITE_DB_PATH):
            log_error(f"SQLite 数据库文件不存在: {SQLITE_DB_PATH}")
            return False, 0

        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()

        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='job_positions'")
        if not cursor.fetchone():
            log_error("job_positions 表不存在")
            conn.close()
            return False, 0

        # 获取记录数
        cursor.execute("SELECT COUNT(*) FROM job_positions")
        count = cursor.fetchone()[0]

        conn.close()
        return True, count

    except Exception as e:
        log_error(f"检查 SQLite 数据库失败: {e}")
        return False, 0

def check_mysql_connection() -> bool:
    """
    检查 MySQL 数据库连接
    """
    try:
        # 检查配置是否填写
        if not MYSQL_CONFIG["host"] or not MYSQL_CONFIG["user"]:
            log_error("MySQL 配置信息未填写，请先配置数据库连接信息")
            return False

        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()

        # 检查 position 表是否存在
        cursor.execute("SHOW TABLES LIKE 'position'")
        if not cursor.fetchone():
            log_error("position 表不存在，请先运行数据库迁移")
            conn.close()
            return False

        conn.close()
        return True

    except Exception as e:
        log_error(f"连接 MySQL 数据库失败: {e}")
        return False

def fetch_sqlite_data() -> List[Dict]:
    """
    从 SQLite 读取所有岗位数据
    """
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM job_positions")
        rows = cursor.fetchall()

        data = [dict(row) for row in rows]
        conn.close()

        return data

    except Exception as e:
        log_error(f"读取 SQLite 数据失败: {e}")
        return []

def transform_data(sqlite_row: Dict) -> Dict:
    """
    转换单条数据从 SQLite 格式到 MySQL 格式
    """
    return {
        "id": str(uuid.uuid4()),
        "position_type": sqlite_row.get("job_type"),
        "recruiting_unit": sqlite_row.get("recruiting_unit"),
        "city": sqlite_row.get("city"),
        "gender_requirement": convert_gender(sqlite_row.get("gender")),
        "special_requirements": sqlite_row.get("special_requirements"),
        "accept_criminal_record": convert_boolean(sqlite_row.get("accept_criminal_record")),
        "work_location": sqlite_row.get("location"),
        "longitude": convert_decimal(sqlite_row.get("longitude")),
        "latitude": convert_decimal(sqlite_row.get("latitude")),
        "urgency_level": convert_urgency_level(sqlite_row.get("urgent_capacity")),
        "working_hours": sqlite_row.get("working_hours"),
        "required_experience": sqlite_row.get("relevant_experience"),
        "employment_type": convert_employment_type(sqlite_row.get("full_time")),
        "salary": sqlite_row.get("salary"),
        "advance_payment_method": None,  # SQLite 中没有此字段
        "job_description": sqlite_row.get("job_content"),
        "interview_time": sqlite_row.get("interview_time"),
        "interview_notes": None,  # SQLite 中没有此字段
        "trial_period": sqlite_row.get("trial_time"),
        "currently_recruiting": convert_boolean(sqlite_row.get("currently_recruiting")),
        "insurance_info": sqlite_row.get("insurance_status"),
        "accommodation_info": sqlite_row.get("accommodation_status"),
        "meal_info": None,  # SQLite 中没有此字段
        "resignation_conditions": None,  # SQLite 中没有此字段
        "onboarding_guidance": None,  # SQLite 中没有此字段
        "create_time": datetime.now(),
        "update_time": datetime.now(),
        "deleted": 0
    }

def insert_batch_to_mysql(conn: pymysql.connections.Connection, batch_data: List[Dict]) -> Tuple[int, int]:
    """
    批量插入数据到 MySQL
    返回: (成功数, 失败数)
    """
    success_count = 0
    fail_count = 0

    cursor = conn.cursor()

    insert_sql = """
    INSERT INTO position (
        id, position_type, recruiting_unit, city, gender_requirement,
        special_requirements, accept_criminal_record, work_location,
        longitude, latitude, urgency_level, working_hours,
        required_experience, employment_type, salary,
        advance_payment_method, job_description, interview_time,
        interview_notes, trial_period, currently_recruiting,
        insurance_info, accommodation_info, meal_info,
        resignation_conditions, onboarding_guidance,
        create_time, update_time, deleted
    ) VALUES (
        %(id)s, %(position_type)s, %(recruiting_unit)s, %(city)s, %(gender_requirement)s,
        %(special_requirements)s, %(accept_criminal_record)s, %(work_location)s,
        %(longitude)s, %(latitude)s, %(urgency_level)s, %(working_hours)s,
        %(required_experience)s, %(employment_type)s, %(salary)s,
        %(advance_payment_method)s, %(job_description)s, %(interview_time)s,
        %(interview_notes)s, %(trial_period)s, %(currently_recruiting)s,
        %(insurance_info)s, %(accommodation_info)s, %(meal_info)s,
        %(resignation_conditions)s, %(onboarding_guidance)s,
        %(create_time)s, %(update_time)s, %(deleted)s
    )
    """

    for data in batch_data:
        try:
            cursor.execute(insert_sql, data)
            success_count += 1
        except Exception as e:
            fail_count += 1
            log_warning(f"插入失败 (岗位: {data.get('position_type')} - {data.get('recruiting_unit')}): {e}")

    conn.commit()
    cursor.close()

    return success_count, fail_count

def clear_existing_data(conn: pymysql.connections.Connection) -> int:
    """
    清空 position 表中的现有数据
    返回: 删除的记录数
    """
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM position WHERE deleted = 0")
        count = cursor.fetchone()[0]

        if count > 0:
            cursor.execute("DELETE FROM position WHERE deleted = 0")
            conn.commit()
            log_info(f"已清空 {count} 条现有数据")

        cursor.close()
        return count

    except Exception as e:
        log_error(f"清空现有数据失败: {e}")
        return 0

# ============ 主流程 ============

def main():
    """
    主函数
    """
    print("=" * 60)
    print("  岗位数据迁移脚本")
    print("  SQLite (job_positions) -> MySQL (position)")
    print("=" * 60)
    print()

    # 步骤1: 检查 SQLite 数据库
    log_step("步骤1: 检查 SQLite 数据库...")
    success, sqlite_count = check_sqlite_database()
    if not success:
        log_error("SQLite 数据库检查失败")
        sys.exit(1)

    log_info(f"SQLite 数据库: {SQLITE_DB_PATH}")
    log_info(f"待迁移记录数: {sqlite_count}")
    print()

    # 步骤2: 检查 MySQL 连接
    log_step("步骤2: 检查 MySQL 数据库连接...")
    if not check_mysql_connection():
        log_error("MySQL 数据库连接失败")
        sys.exit(1)

    log_info(f"MySQL 数据库: {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}")
    print()

    # 步骤3: 确认是否继续
    log_step("步骤3: 确认迁移操作...")

    if TEST_MODE:
        log_warning(f"⚠️  测试模式已启用，只会导入 {TEST_LIMIT} 条记录")
        actual_count = min(TEST_LIMIT, sqlite_count)
    else:
        actual_count = sqlite_count

    log_warning(f"即将迁移 {actual_count} 条记录到云数据库")
    log_warning("此操作将清空 position 表中的现有数据")

    response = input(f"{Colors.YELLOW}是否继续？(yes/no): {Colors.NC}")
    if response.lower() not in ['yes', 'y']:
        log_info("操作已取消")
        sys.exit(0)
    print()

    # 步骤4: 读取 SQLite 数据
    log_step("步骤4: 读取 SQLite 数据...")
    sqlite_data = fetch_sqlite_data()
    if not sqlite_data:
        log_error("未读取到任何数据")
        sys.exit(1)

    log_info(f"成功读取 {len(sqlite_data)} 条记录")
    print()

    # 步骤5: 转换数据
    log_step("步骤5: 转换数据格式...")
    transformed_data = []
    conversion_errors = []

    # 如果是测试模式，只处理指定数量的数据
    data_to_process = sqlite_data[:TEST_LIMIT] if TEST_MODE else sqlite_data

    for i, row in enumerate(data_to_process, 1):
        try:
            transformed = transform_data(row)
            transformed_data.append(transformed)

            if i % 100 == 0:
                print(f"  已转换: {i}/{len(data_to_process)}", end='\r')
        except Exception as e:
            conversion_errors.append((i, row.get('job_type'), str(e)))

    print(f"  已转换: {len(transformed_data)}/{len(sqlite_data)}")

    if conversion_errors:
        log_warning(f"转换过程中有 {len(conversion_errors)} 条记录出错")
        for idx, job_type, error in conversion_errors[:5]:  # 只显示前5个错误
            log_warning(f"  记录 {idx} ({job_type}): {error}")

    log_info(f"成功转换 {len(transformed_data)} 条记录")
    print()

    # 步骤6: 连接 MySQL 并清空现有数据
    log_step("步骤6: 连接 MySQL 数据库...")
    try:
        mysql_conn = pymysql.connect(**MYSQL_CONFIG)
        log_info("MySQL 连接成功")

        # 清空现有数据
        cleared_count = clear_existing_data(mysql_conn)
        print()

    except Exception as e:
        log_error(f"连接 MySQL 失败: {e}")
        sys.exit(1)

    # 步骤7: 批量插入数据
    log_step("步骤7: 批量插入数据到 MySQL...")
    total_success = 0
    total_fail = 0

    for i in range(0, len(transformed_data), BATCH_SIZE):
        batch = transformed_data[i:i + BATCH_SIZE]
        success, fail = insert_batch_to_mysql(mysql_conn, batch)

        total_success += success
        total_fail += fail

        progress = min(i + BATCH_SIZE, len(transformed_data))
        print(f"  进度: {progress}/{len(transformed_data)} (成功: {total_success}, 失败: {total_fail})", end='\r')

    print(f"  进度: {len(transformed_data)}/{len(transformed_data)} (成功: {total_success}, 失败: {total_fail})")
    print()

    # 步骤8: 验证结果
    log_step("步骤8: 验证迁移结果...")
    try:
        cursor = mysql_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM position WHERE deleted = 0")
        mysql_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT city) FROM position WHERE deleted = 0")
        city_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM position WHERE currently_recruiting = 1 AND deleted = 0")
        recruiting_count = cursor.fetchone()[0]

        cursor.close()
        mysql_conn.close()

        log_info(f"MySQL 数据库记录数: {mysql_count}")
        log_info(f"涉及城市数量: {city_count}")
        log_info(f"正在招聘的岗位: {recruiting_count}")

    except Exception as e:
        log_error(f"验证失败: {e}")

    print()

    # 总结
    print("=" * 60)
    if total_fail == 0:
        log_success(f"🎉 迁移完成！成功迁移 {total_success} 条记录")
    else:
        log_warning(f"⚠️  迁移完成，但有 {total_fail} 条记录失败")
        log_success(f"成功迁移 {total_success} 条记录")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        log_warning("操作被用户中断")
        sys.exit(1)
    except Exception as e:
        log_error(f"发生未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
