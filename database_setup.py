import pandas as pd
import sqlite3
import os

def setup_job_positions_table(csv_file='岗位属性.csv', db_file='stations.db'):
    """
    从岗位属性CSV文件中读取岗位信息，并将其存入SQLite数据库的job_positions表。
    """
    try:
        # 读取岗位属性CSV文件
        df = pd.read_csv(csv_file)
        print(f"成功读取岗位属性CSV文件: '{csv_file}'")
    except FileNotFoundError:
        print(f"错误: 岗位属性CSV文件 '{csv_file}' 未找到。")
        return
    except Exception as e:
        print(f"读取岗位属性CSV文件时出错: {e}")
        return

    # 重命名列以匹配数据库字段
    column_mapping = {
        '岗位类型': 'job_type',
        '招聘单位': 'recruiting_unit', 
        '城市': 'city',
        '性别': 'gender',
        '年龄要求': 'age_requirement',
        '特殊要求': 'special_requirements',
        '是否接受有犯罪记录': 'accept_criminal_record',
        '位置': 'location',
        '经度': 'longitude',
        '维度': 'latitude',
        '运力紧急情况': 'urgent_capacity',
        '工作时间': 'working_hours',
        '相关经验': 'relevant_experience',
        '全职': 'full_time',
        '薪资': 'salary',
        '工作内容': 'job_content',
        '面试时间': 'interview_time',
        '试岗时间': 'trial_time',
        '当前是否招聘': 'currently_recruiting',
        '保险情况': 'insurance_status',
        '吃住情况': 'accommodation_status'
    }
    
    df.rename(columns=column_mapping, inplace=True)
    
    # 数据清洗：填充空值
    for col in df.columns:
        if col in ['longitude', 'latitude']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        elif col == 'urgent_capacity':
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        else:
            df[col] = df[col].astype(str).fillna('N/A')

    try:
        # 连接到SQLite数据库
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        # 创建岗位属性表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_type TEXT NOT NULL,
            recruiting_unit TEXT,
            city TEXT,
            gender TEXT,
            age_requirement TEXT,
            special_requirements TEXT,
            accept_criminal_record TEXT,
            location TEXT,
            longitude REAL,
            latitude REAL,
            urgent_capacity INTEGER DEFAULT 0,
            working_hours TEXT,
            relevant_experience TEXT,
            full_time TEXT,
            salary TEXT,
            job_content TEXT,
            interview_time TEXT,
            trial_time TEXT,
            currently_recruiting TEXT,
            insurance_status TEXT,
            accommodation_status TEXT
        )
        ''')
        print("成功创建 'job_positions' 表。")

        # 清空现有数据
        cursor.execute('DELETE FROM job_positions')
        
        # 将数据写入数据库
        df.to_sql('job_positions', conn, if_exists='append', index=False)
        
        conn.commit()
        conn.close()

        print(f"岗位属性数据成功导入到数据库 '{db_file}'。共导入 {len(df)} 条记录。")

    except sqlite3.Error as e:
        print(f"岗位属性数据库操作失败: {e}")
    except Exception as e:
        print(f"岗位属性数据导入过程中发生未知错误: {e}")

def setup_database(csv_file='岗位位置信息底表_with_coords.csv', db_file='stations.db'):
    """
    从 CSV 文件中读取站点信息，并将其存入 SQLite 数据库。
    如果数据库文件已存在，则会先删除旧文件，重新创建。
    """
    # 如果数据库文件已存在，则删除，以确保每次都是最新的数据
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"已删除旧数据库文件: '{db_file}'")

    try:
        # 读取包含经纬度的CSV文件
        df = pd.read_csv(csv_file)
        print(f"成功读取CSV文件: '{csv_file}'")
    except FileNotFoundError:
        print(f"错误: CSV文件 '{csv_file}' 未找到。")
        return
    except Exception as e:
        print(f"读取CSV文件时出错: {e}")
        return

    # 数据清洗：移除经纬度为空的行
    df.dropna(subset=['longitude', 'latitude'], inplace=True)
    
    # 将所有列转换为字符串类型，以避免拼接时出错
    # 对于数值型列，将空值填充为 '0'；对于其他列，填充为 'N/A'
    for col in df.columns:
        if col in ['全职分拣', '全职白班', '全职水产', '全职夜班', '夜班分拣', '资深副站长', '副站长', 
                   '果切员', '库管员', '上架员', '果蔬加工员']:
            # 对于岗位需求相关的数值列，将空值填充为 '0'
            df[col] = df[col].astype(str).fillna('0')
        else:
            # 对于其他列，保持原有的 'N/A' 填充
            df[col] = df[col].astype(str).fillna('N/A')

    # 定义要拼接的列
    site_info_cols = ['区域', '行政区', '站点']
    demand_info_cols = [
        '全职分拣', '全职白班', '全职水产', '全职夜班', '夜班分拣', '资深副站长', '副站长',
        '果切员', '库管员', '上架员', '果蔬加工员'
    ]

    # 创建站点信息和需求信息的字符串
    def create_combined_string(row, cols):
        result = []
        for col in cols:
            if col in row:
                value = row[col]
                # 对于岗位需求相关的数值列，如果值为空字符串或'N/A'，则显示为'0'
                if col in ['全职分拣', '全职白班', '全职水产', '全职夜班', '夜班分拣', '资深副站长', '副站长',
                          '果切员', '库管员', '上架员', '果蔬加工员']:
                    if value == '' or value == 'N/A' or value == 'nan':
                        result.append(f"{col}: 0")
                    else:
                        result.append(f"{col}: {value}")
                else:
                    if value != 'N/A':
                        result.append(f"{col}: {value}")
        return ', '.join(result)

    df['site_info_str'] = df.apply(lambda row: create_combined_string(row, site_info_cols), axis=1)
    df['demand_info_str'] = df.apply(lambda row: create_combined_string(row, demand_info_cols), axis=1)
    
    # 重命名核心数据列
    df.rename(columns={
        '站点': 'station_name',
        '门店地址': 'address',
        '面试联系人': 'interview_contact_person',
        '联系方式': 'contact_phone',
    }, inplace=True)

    # 选择需要的列
    columns_to_keep = [
        'station_name', 'address', 'longitude', 'latitude', 'interview_contact_person', 'contact_phone',
        'site_info_str', 'demand_info_str'
    ]
    df_selected = df[columns_to_keep].copy()

    try:
        # 连接到SQLite数据库
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        # 创建站点表
        cursor.execute('''
        CREATE TABLE stations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_name TEXT NOT NULL,
            address TEXT,
            longitude REAL NOT NULL,
            latitude REAL NOT NULL,
            interview_contact_person TEXT,
            contact_phone TEXT,
            site_info_str TEXT,
            demand_info_str TEXT
        )
        ''')
        print("成功创建 'stations' 表。")

        # 将数据写入数据库
        df_selected.to_sql('stations', conn, if_exists='append', index=False)
        
        conn.commit()
        conn.close()

        print(f"数据成功导入到数据库 '{db_file}'。共导入 {len(df_selected)} 条记录。")

    except sqlite3.Error as e:
        print(f"数据库操作失败: {e}")
    except Exception as e:
        print(f"数据导入过程中发生未知错误: {e}")

def setup_all_databases():
    """
    设置所有数据库表：站点信息表和岗位属性表
    """
    print("开始设置数据库...")
    
    # 设置站点信息表
    setup_database()
    
    # 设置岗位属性表  
    setup_job_positions_table()
    
    print("所有数据库表设置完成！")

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == 'stations':
            setup_database()
        elif sys.argv[1] == 'jobs':
            setup_job_positions_table()
        elif sys.argv[1] == 'all':
            setup_all_databases()
        else:
            print("用法: python database_setup.py [stations|jobs|all]")
            print("  stations - 只设置站点信息表")
            print("  jobs - 只设置岗位属性表")
            print("  all - 设置所有表")
    else:
        setup_all_databases() 