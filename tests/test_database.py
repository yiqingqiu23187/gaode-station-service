#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接测试脚本
"""

import os
import sqlite3
import pandas as pd
from datetime import datetime
from config import config

def test_database_connection():
    """测试数据库连接"""
    print("🔍 测试数据库连接...")

    # 获取配置
    app_config = config['development']()
    database_url = app_config.DATABASE_URL

    print(f"数据库URL: {database_url}")

    try:
        if database_url.startswith('sqlite:///'):
            # SQLite测试
            db_path = database_url.replace('sqlite:///', '')
            print(f"连接SQLite数据库: {db_path}")

            # 连接数据库
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # 创建测试表
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS test_resumes (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT,
                create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            cursor.execute(create_table_sql)

            # 插入测试数据
            test_data = {
                'id': 'test-001',
                'name': '测试用户',
                'phone': '13800138000',
                'create_time': datetime.now()
            }

            cursor.execute(
                "INSERT OR REPLACE INTO test_resumes (id, name, phone, create_time) VALUES (?, ?, ?, ?)",
                (test_data['id'], test_data['name'], test_data['phone'], test_data['create_time'])
            )

            # 查询数据
            cursor.execute("SELECT * FROM test_resumes WHERE id = ?", (test_data['id'],))
            result = cursor.fetchone()

            conn.commit()
            conn.close()

            if result:
                print("✅ SQLite数据库连接测试成功！")
                print(f"   插入的数据: {result}")
                return True
            else:
                print("❌ SQLite数据库测试失败：无法查询到插入的数据")
                return False

        else:
            print("❌ 暂不支持MySQL连接测试（需要配置真实的MySQL服务器）")
            return False

    except Exception as e:
        print(f"❌ 数据库连接测试失败: {e}")
        return False

def test_excel_processing():
    """测试Excel文件处理"""
    print("\n📊 测试Excel文件处理...")

    try:
        # 创建测试Excel文件
        test_data = {
            '姓名': ['张三', '李四'],
            '手机号': ['13800138000', '13900139000'],
            '年龄': ['25~30岁', '30~35岁'],
            '居住城市': ['北京', '上海'],
            '应聘岗位': ['分拣员', '配送员'],
            '微信号': ['zhangsan123', 'lisi456']
        }

        df = pd.DataFrame(test_data)
        test_file = 'test_resume.xlsx'
        df.to_excel(test_file, index=False)

        print(f"✅ 创建测试Excel文件: {test_file}")

        # 读取Excel文件
        df_read = pd.read_excel(test_file)
        print(f"✅ 成功读取Excel文件，共 {len(df_read)} 条记录")

        # 清理测试文件
        os.remove(test_file)
        print("✅ 清理测试文件完成")

        return True

    except Exception as e:
        print(f"❌ Excel文件处理测试失败: {e}")
        return False

def test_mcp_connection():
    """测试MCP连接（简化版）"""
    print("\n🌐 测试MCP服务器连接...")

    try:
        import requests

        app_config = config['development']()
        mcp_url = app_config.MCP_SERVER_URL

        print(f"MCP服务器URL: {mcp_url}")

        # 简单的HTTP连接测试
        response = requests.get(mcp_url, timeout=5)

        if response.status_code == 200:
            print("✅ MCP服务器连接测试成功！")
            return True
        else:
            print(f"⚠️  MCP服务器响应状态码: {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ MCP服务器连接测试失败: {e}")
        return False
    except ImportError:
        print("⚠️  requests库未安装，跳过MCP连接测试")
        return False

def main():
    """主测试函数"""
    print("🧪 简历管理应用 - 数据库连接测试")
    print("=" * 50)

    results = []

    # 测试数据库连接
    results.append(("数据库连接", test_database_connection()))

    # 测试Excel处理
    results.append(("Excel处理", test_excel_processing()))

    # 测试MCP连接
    results.append(("MCP连接", test_mcp_connection()))

    # 汇总结果
    print("\n📋 测试结果汇总")
    print("=" * 50)

    all_passed = True
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name:15} {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 所有测试通过！应用可以正常运行。")
    else:
        print("⚠️  部分测试失败，请检查相关配置。")

    return all_passed

if __name__ == "__main__":
    main()
