#!/usr/bin/env python3
"""
测试API功能的脚本
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_get_stations():
    """测试获取所有站点数据"""
    print("测试获取所有站点数据...")
    response = requests.get(f"{BASE_URL}/api/stations")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 成功获取数据，共 {data['total']} 条记录")
        return data['data']
    else:
        print(f"❌ 获取数据失败: {response.status_code}")
        return None

def test_update_station(station_id, updates):
    """测试更新单个站点"""
    print(f"测试更新站点 ID {station_id}...")
    response = requests.put(
        f"{BASE_URL}/api/stations/{station_id}",
        json=updates,
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 更新成功: {result['message']}")
        return True
    else:
        print(f"❌ 更新失败: {response.status_code} - {response.text}")
        return False

def test_batch_update(updates):
    """测试批量更新"""
    print("测试批量更新...")
    response = requests.put(
        f"{BASE_URL}/api/stations/batch",
        json={'updates': updates},
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 批量更新成功: {result['message']}")
        return True
    else:
        print(f"❌ 批量更新失败: {response.status_code} - {response.text}")
        return False

def main():
    print("开始API功能测试...\n")
    
    # 1. 获取数据
    stations = test_get_stations()
    if not stations:
        return
    
    print(f"第一个站点信息: {stations[0]['station_name']}")
    print()
    
    # 2. 测试单个更新
    first_station = stations[0]
    original_manager = first_station.get('manager_name', '')
    test_manager = "测试站长"
    
    # 更新站长姓名
    if test_update_station(first_station['id'], {'manager_name': test_manager}):
        print("等待2秒后恢复原始数据...")
        import time
        time.sleep(2)
        
        # 恢复原始数据
        test_update_station(first_station['id'], {'manager_name': original_manager})
    
    print()
    
    # 3. 测试批量更新
    if len(stations) >= 2:
        batch_updates = [
            {
                'id': stations[0]['id'],
                'manager_name': '批量测试1'
            },
            {
                'id': stations[1]['id'], 
                'manager_name': '批量测试2'
            }
        ]
        
        if test_batch_update(batch_updates):
            print("等待2秒后恢复原始数据...")
            import time
            time.sleep(2)
            
            # 恢复原始数据
            restore_updates = [
                {
                    'id': stations[0]['id'],
                    'manager_name': stations[0].get('manager_name', '')
                },
                {
                    'id': stations[1]['id'],
                    'manager_name': stations[1].get('manager_name', '')
                }
            ]
            test_batch_update(restore_updates)
    
    print("\n✅ API功能测试完成！")

if __name__ == '__main__':
    main()
