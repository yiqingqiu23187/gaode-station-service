import pandas as pd
import time
from amap_utils import get_coordinates, API_KEY


def process_csv(input_file, output_file, address_column_name):
    """
    读取 CSV 文件，为地址列添加经纬度，并保存到新文件。

    Args:
        input_file (str): 输入的 CSV 文件路径.
        output_file (str): 输出的 CSV 文件路径.
        address_column_name (str): 包含地址信息的列名.
    """
    try:
        # header=1 表示将文件的第二行作为列标题
        df = pd.read_csv(input_file, header=1)
    except FileNotFoundError:
        print(f"错误: 文件 '{input_file}' 未找到。")
        return
    except Exception as e:
        print(f"错误: 读取 CSV 文件 '{input_file}' 时出错. 异常: {e}")
        return

    # 清理列名中可能存在的多余空格
    df.columns = df.columns.str.strip()

    # 应用函数获取经纬度，并创建一个包含经纬度的临时 DataFrame
    # 为了避免超过API的QPS限制，这里可以加入延时
    coords_list = []
    for address in df[address_column_name]:
        coords_list.append(get_coordinates(address, API_KEY))
        # 考虑到API限制和重试逻辑，这里的延时可以适当调整或移除
        time.sleep(0.1)

    # 将经纬度列表转换为 DataFrame
    coords_df = pd.DataFrame(coords_list, index=df.index, columns=['longitude', 'latitude'])

    # 将经纬度列合并到原始 DataFrame
    df = pd.concat([df, coords_df], axis=1)

    # 调整列的顺序，将经纬度放在地址列后面
    cols = df.columns.tolist()
    # 找到地址列的索引
    try:
        address_idx = cols.index(address_column_name)
        # 移除最后两列（刚添加的经纬度）
        new_cols_order = cols[:-2]
        # 将经纬度插入到地址列后面
        new_cols_order.insert(address_idx + 1, 'latitude')
        new_cols_order.insert(address_idx + 1, 'longitude')
        df = df[new_cols_order]
    except ValueError:
        print(f"警告: 在列中未找到地址列 '{address_column_name}'。经纬度将被添加到末尾。")


    # 保存到新的 CSV 文件
    try:
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n处理完成！结果已保存至 '{output_file}'")
    except Exception as e:
        print(f"错误: 写入到文件 '{output_file}' 时出错. 异常: {e}")

if __name__ == "__main__":
    INPUT_CSV = '岗位位置信息底表.csv'
    OUTPUT_CSV = '岗位位置信息底表_with_coords.csv'
    # CSV 文件中包含地址的列名
    ADDRESS_COLUMN = '门店地址'
    
    process_csv(INPUT_CSV, OUTPUT_CSV, ADDRESS_COLUMN) 