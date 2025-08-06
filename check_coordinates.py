#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import sqlite3
import requests
import time
from typing import Dict, List, Tuple
import json

# 高德地图 API 配置
API_KEY = "7d2a69204c7a8340ac59834fc5d945df"
GEOCODE_URL = "https://restapi.amap.com/v3/geocode/geo"

def get_coordinates_from_api(address: str) -> Tuple[float, float, Dict]:
    """从高德地图API获取地址的经纬度"""
    params = {
        'key': API_KEY, 
        'address': address, 
        'output': 'json'
    }
    
    try:
        response = requests.get(GEOCODE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') == '1' and data.get('geocodes'):
            location = data['geocodes'][0]['location']
            longitude, latitude = map(float, location.split(','))
            return longitude, latitude, data['geocodes'][0]
        else:
            return None, None, None
    except Exception as e:
        print(f"API调用失败: {e}")
        return None, None, None

def haversine_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """计算两个经纬度坐标之间的距离（公里）"""
    import math
    
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # 地球半径
    return c * r

def check_all_stations():
    """检查所有站点的坐标准确性"""
    
    # 连接数据库
    conn = sqlite3.connect('stations.db')
    cursor = conn.cursor()
    cursor.execute("SELECT station_name, address, longitude, latitude FROM stations")
    stations = cursor.fetchall()
    conn.close()
    
    print("=" * 80)
    print("站点坐标准确性检查报告")
    print("=" * 80)
    
    anomalies = []
    total_stations = len(stations)
    checked_stations = 0
    
    for station_name, address, db_lon, db_lat in stations:
        checked_stations += 1
        print(f"\n[{checked_stations}/{total_stations}] 检查站点: {station_name}")
        print(f"地址: {address}")
        print(f"数据库坐标: {db_lon}, {db_lat}")
        
        # 从API重新获取坐标
        api_lon, api_lat, geocode_info = get_coordinates_from_api(address)
        
        if api_lon is None or api_lat is None:
            print("❌ API无法解析地址")
            anomalies.append({
                'station_name': station_name,
                'address': address,
                'db_coords': (db_lon, db_lat),
                'api_coords': None,
                'issue': 'API无法解析地址'
            })
            continue
        
        print(f"API解析坐标: {api_lon}, {api_lat}")
        
        # 计算距离差异
        distance = haversine_distance(db_lon, db_lat, api_lon, api_lat)
        print(f"坐标差异: {distance:.2f} 公里")
        
        # 检查解析的地址信息
        if geocode_info:
            formatted_address = geocode_info.get('formatted_address', '')
            district = geocode_info.get('district', '')
            street = geocode_info.get('street', '')
            print(f"API解析地址: {formatted_address}")
            print(f"区域: {district}, 街道: {street}")
        
        # 判断是否为异常点
        is_anomaly = False
        anomaly_reasons = []
        
        # 1. 距离差异过大（超过5公里）
        if distance > 5:
            is_anomaly = True
            anomaly_reasons.append(f"坐标差异过大({distance:.2f}公里)")
        
        # 2. 解析的地址与原始地址差异很大
        if geocode_info:
            original_city = "苏州市" if "苏州市" in address else ""
            api_city = geocode_info.get('city', '')
            api_district = geocode_info.get('district', '')
            
            if original_city and api_city != original_city:
                is_anomaly = True
                anomaly_reasons.append(f"城市解析错误(原始:{original_city}, API:{api_city})")
            
            # 检查是否解析到了常熟市（苏州市下属县级市）
            if "常熟市" in api_district and "常熟" not in address:
                is_anomaly = True
                anomaly_reasons.append("错误解析到常熟市")
        
        if is_anomaly:
            print(f"🚨 发现异常: {', '.join(anomaly_reasons)}")
            anomalies.append({
                'station_name': station_name,
                'address': address,
                'db_coords': (db_lon, db_lat),
                'api_coords': (api_lon, api_lat),
                'distance_diff': distance,
                'geocode_info': geocode_info,
                'issues': anomaly_reasons
            })
        else:
            print("✅ 坐标正常")
        
        # 避免API调用过于频繁
        time.sleep(0.5)
    
    # 生成异常报告
    print("\n" + "=" * 80)
    print("异常站点汇总")
    print("=" * 80)
    
    if not anomalies:
        print("✅ 所有站点坐标都正常！")
    else:
        print(f"🚨 发现 {len(anomalies)} 个异常站点:")
        
        for i, anomaly in enumerate(anomalies, 1):
            print(f"\n{i}. {anomaly['station_name']}")
            print(f"   地址: {anomaly['address']}")
            print(f"   数据库坐标: {anomaly['db_coords']}")
            if anomaly['api_coords']:
                print(f"   API坐标: {anomaly['api_coords']}")
                print(f"   坐标差异: {anomaly['distance_diff']:.2f} 公里")
            print(f"   问题: {', '.join(anomaly['issues'])}")
            
            if 'geocode_info' in anomaly and anomaly['geocode_info']:
                geocode = anomaly['geocode_info']
                print(f"   API解析地址: {geocode.get('formatted_address', 'N/A')}")
                print(f"   解析区域: {geocode.get('district', 'N/A')}")
    
    return anomalies

if __name__ == "__main__":
    check_all_stations() 