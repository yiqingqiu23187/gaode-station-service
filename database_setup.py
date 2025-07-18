import pandas as pd
import sqlite3
import os

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
        print(f"错误: CSV文件 '{csv_file}' 未找到。请先运行 'add_coordinates.py' 生成该文件。")
        return
    except Exception as e:
        print(f"读取CSV文件时出错: {e}")
        return

    # 数据清洗：移除经纬度为空的行
    df.dropna(subset=['longitude', 'latitude'], inplace=True)
    
    # 将所有列转换为字符串类型，以避免拼接时出错
    for col in df.columns:
        df[col] = df[col].astype(str).fillna('N/A')

    # 定义要拼接的列
    site_info_cols = ['状态', '区域', '服务站', '站长姓名', '联系方式']
    demand_info_cols = [
        '全职总计', '分拣员', '白班理货', '水产专员', '夜班理货', '副站长', '资深副站长',
        '兼职总计', '兼职-分拣员', '兼职-白班理货', '兼职-夜班理货', '兼职-水产专员'
    ]

    # 创建站点信息和需求信息的字符串
    def create_combined_string(row, cols):
        return ', '.join([f"{col}: {row[col]}" for col in cols if col in row and row[col] != 'N/A'])

    df['site_info_str'] = df.apply(lambda row: create_combined_string(row, site_info_cols), axis=1)
    df['demand_info_str'] = df.apply(lambda row: create_combined_string(row, demand_info_cols), axis=1)
    
    # 重命名核心数据列
    df.rename(columns={
        '服务站': 'station_name',
        '门店地址（本站点地址非面试站点地址）': 'address',
        '站长姓名': 'manager_name',
        '联系方式': 'contact_phone',
        '面试地点': 'interview_location',
        '面试对接人': 'interview_contact_person',
        '面试对接人联系方式/站点座机号': 'interview_contact_phone',
    }, inplace=True)

    # 选择需要的列
    columns_to_keep = [
        'station_name', 'address', 'longitude', 'latitude', 'manager_name', 'contact_phone',
        'interview_location', 'interview_contact_person', 'interview_contact_phone',
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
            manager_name TEXT,
            contact_phone TEXT,
            interview_location TEXT,
            interview_contact_person TEXT,
            interview_contact_phone TEXT,
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

if __name__ == '__main__':
    setup_database() 