#!/usr/bin/env python3
"""
测试新的API结构
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
        
        # 显示第一条记录的结构
        if data['data']:
            first_station = data['data'][0]
            print(f"第一个站点: {first_station['station_name']}")
            print("需求信息字段:")
            demand_fields = [
                'fulltime_total', 'sorter', 'day_handler', 'aquatic_specialist',
                'night_handler', 'deputy_manager', 'senior_deputy_manager',
                'parttime_total', 'parttime_sorter', 'parttime_day_handler',
                'parttime_night_handler', 'parttime_aquatic_specialist'
            ]
            for field in demand_fields:
                print(f"  {field}: {first_station.get(field, 'N/A')}")
        
        return data['data']
    else:
        print(f"❌ 获取数据失败: {response.status_code}")
        return None

def test_update_demand_fields():
    """测试更新需求字段"""
    print("\n测试更新需求字段...")
    
    # 获取第一个站点
    stations = test_get_stations()
    if not stations:
        return
    
    first_station = stations[0]
    station_id = first_station['id']
    
    # 测试更新需求字段
    updates = {
        'fulltime_total': '10',
        'sorter': '5',
        'day_handler': '2',
        'aquatic_specialist': '1',
        'night_handler': '2'
    }
    
    print(f"更新站点 {station_id} 的需求信息...")
    response = requests.put(
        f"{BASE_URL}/api/stations/{station_id}",
        json=updates,
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 更新成功: {result['message']}")
        
        # 验证更新结果
        print("验证更新结果...")
        verify_response = requests.get(f"{BASE_URL}/api/stations")
        if verify_response.status_code == 200:
            verify_data = verify_response.json()
            updated_station = next((s for s in verify_data['data'] if s['id'] == station_id), None)
            if updated_station:
                print("更新后的需求信息:")
                for field, expected_value in updates.items():
                    actual_value = updated_station.get(field, 'N/A')
                    status = "✅" if str(actual_value) == expected_value else "❌"
                    print(f"  {field}: {actual_value} {status}")
        
        # 恢复原始数据
        print("恢复原始数据...")
        original_updates = {
            'fulltime_total': first_station.get('fulltime_total', '0'),
            'sorter': first_station.get('sorter', '0'),
            'day_handler': first_station.get('day_handler', '0'),
            'aquatic_specialist': first_station.get('aquatic_specialist', '0'),
            'night_handler': first_station.get('night_handler', '0')
        }
        
        restore_response = requests.put(
            f"{BASE_URL}/api/stations/{station_id}",
            json=original_updates,
            headers={'Content-Type': 'application/json'}
        )
        
        if restore_response.status_code == 200:
            print("✅ 数据已恢复")
        else:
            print("❌ 数据恢复失败")
            
    else:
        print(f"❌ 更新失败: {response.status_code} - {response.text}")

def main():
    print("开始测试新的API结构...\n")
    test_update_demand_fields()
    print("\n✅ 测试完成！")

if __name__ == '__main__':
    main()
