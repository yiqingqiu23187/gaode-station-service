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

if __name__ == '__main__':
    setup_database() 