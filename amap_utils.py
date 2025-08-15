import requests
import time
from urllib.parse import urlencode
import math

# 您提供的高德地图 Web 服务 API Key
API_KEY = "7d2a69204c7a8340ac59834fc5d945df"
# 地理编码 API 地址
GEOCODE_URL = "https://restapi.amap.com/v3/geocode/geo"


def get_coordinates(address, api_key=API_KEY, max_retries=5, retry_delay=1):
    """
    使用高德地图 API 将地址转换为经纬度，并包含重试逻辑。

    Args:
        address (str): 需要查询的地址.
        api_key (str): 高德地图的 API Key.
        max_retries (int): 最大重试次数.
        retry_delay (int): 每次重试前的等待时间（秒）.

    Returns:
        tuple: (经度, 纬度) 或者 (None, None) 如果查询失败.
    """
    # 如果地址为空或不是字符串，则直接返回
    if not isinstance(address, str) or not address.strip():
        return None, None

    params = {
        'key': api_key,
        'address': address,
        'output': 'json'
    }

    for attempt in range(max_retries):
        try:
            response = requests.get(GEOCODE_URL, params=params)
            response.raise_for_status()  # 如果请求失败则抛出异常
            data = response.json()

            if data.get('status') == '1' and data.get('geocodes'):
                location = data['geocodes'][0]['location']
                longitude, latitude = map(float, location.split(','))
                print(f"成功转换地址 '{address}': 经度={longitude}, 纬度={latitude}")
                return longitude, latitude
            else:
                error_info = data.get('info', '未知错误')
                if 'CUQPS_HAS_EXCEEDED_THE_LIMIT' in error_info:
                    print(f"警告: 地址 '{address}' 查询超限，正在进行第 {attempt + 1}/{max_retries} 次重试...")
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"错误：无法解析地址 '{address}'. 原因: {error_info}")
                    return None, None
        except requests.exceptions.RequestException as e:
            print(f"错误: 请求 API 失败，地址 '{address}'. 异常: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            continue
        except Exception as e:
            print(f"错误: 处理地址 '{address}' 时发生未知异常. 异常: {e}")
            return None, None

    print(f"错误: 达到最大重试次数后，仍无法解析地址 '{address}'。")
    return None, None


def haversine_distance(lon1, lat1, lon2, lat2):
    """
    使用 Haversine 公式计算两个经纬度坐标之间的距离（单位：公里）。
    """
    # 将经纬度从度数转换为弧度
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

    # Haversine 公式
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # 地球平均半径（单位：公里）
    return c * r

def generate_amap_web_url(longitude, latitude, name=""):
    """
    根据经纬度和地点名称生成高德地图网页链接。

    Args:
        longitude (float): 经度
        latitude (float): 纬度
        name (str): 地点名称

    Returns:
        str: 高德地图网页链接
    """
    # 使用高德地图的 URI API 生成网页链接
    # 格式: https://uri.amap.com/marker?position=经度,纬度&name=地点名称
    from urllib.parse import quote
    encoded_name = quote(name) if name else ""
    url = f"https://uri.amap.com/marker?position={longitude},{latitude}"
    if encoded_name:
        url += f"&name={encoded_name}"
    return url

def generate_navigation_url(longitude, latitude, name="", mode="car"):
    """
    根据经纬度和地点名称生成高德地图导航链接。

    Args:
        longitude (float): 经度
        latitude (float): 纬度
        name (str): 地点名称
        mode (str): 导航模式，可选值: car(驾车), walk(步行), bus(公交)

    Returns:
        str: 高德地图导航链接
    """
    from urllib.parse import quote
    encoded_name = quote(name) if name else ""
    url = f"https://uri.amap.com/navigation?to={longitude},{latitude}"
    if encoded_name:
        url += f",{encoded_name}"
    url += f"&mode={mode}&policy=1"
    return url

def generate_ride_hailing_uri(slon, slat, sname, dlon, dlat, dname):
    """
    根据起点和终点信息，生成一个用于唤起高德地图客户端进行打车的 URI。

    Args:
        slon (float): 起点经度.
        slat (float): 起点纬度.
        sname (str): 起点名称.
        dlon (float): 终点经度.
        dlat (float): 终点纬度.
        dname (str): 终点名称.

    Returns:
        str: 拼装好的客户端唤醒 URI.
    """
    params = {
        'slat': slat,
        'slon': slon,
        'sname': sname,
        'dlat': dlat,
        'dlon': dlon,
        'dname': dname,
        't': 2,  # t=2 表示打车
        'dev': 0 # 0:代表gcj02坐标 1:代表wgs84坐标
    }
    # 使用 urlencode 来确保参数被正确编码
    query_string = urlencode(params)
    uri = f"amap://route/plan/?{query_string}"
    return uri

def get_bicycling_duration(origin_lon, origin_lat, dest_lon, dest_lat, api_key=API_KEY, max_retries=3, retry_delay=1):
    """
    使用高德地图骑行路径规划API获取两点间的骑车时间。
    
    Args:
        origin_lon (float): 起点经度
        origin_lat (float): 起点纬度
        dest_lon (float): 终点经度
        dest_lat (float): 终点纬度
        api_key (str): 高德地图的API Key
        max_retries (int): 最大重试次数
        retry_delay (int): 每次重试前的等待时间（秒）
    
    Returns:
        dict: 包含骑行时间的字典，格式为 {"duration_minutes": int, "distance_meters": int} 或 {"error": str}
    """
    # 骑行路径规划API地址
    BICYCLING_URL = "https://restapi.amap.com/v4/direction/bicycling"
    
    params = {
        'key': api_key,
        'origin': f"{origin_lon},{origin_lat}",
        'destination': f"{dest_lon},{dest_lat}"
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(BICYCLING_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get('errcode') == 0 and data.get('data', {}).get('paths'):
                # 获取第一条路径的骑行时间和距离
                path = data['data']['paths'][0]
                duration_seconds = path.get('duration', 0)  # 骑行时间（秒）
                distance_meters = path.get('distance', 0)   # 骑行距离（米）
                
                # 转换为分钟
                duration_minutes = round(duration_seconds / 60)
                
                print(f"成功获取骑行路径: 时间={duration_minutes}分钟, 距离={distance_meters}米")
                return {
                    "duration_minutes": duration_minutes,
                    "distance_meters": distance_meters
                }
            else:
                error_info = data.get('errmsg', '未知错误')
                if 'CUQPS_HAS_EXCEEDED_THE_LIMIT' in error_info:
                    print(f"警告: 骑行路径查询超限，正在进行第 {attempt + 1}/{max_retries} 次重试...")
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"错误：无法获取骑行路径. 原因: {error_info}")
                    return {"error": f"API错误: {error_info}"}
                    
        except requests.exceptions.RequestException as e:
            print(f"错误: 请求骑行路径API失败. 异常: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            continue
        except Exception as e:
            print(f"错误: 处理骑行路径查询时发生未知异常. 异常: {e}")
            return {"error": f"未知错误: {str(e)}"}
    
    print(f"错误: 达到最大重试次数后，仍无法获取骑行路径。")
    return {"error": "达到最大重试次数，无法获取骑行路径"}

if __name__ == '__main__':
    # --- 测试地址转经纬度 ---
    test_address = "北京市朝阳区阜通东大街6号"
    coords = get_coordinates(test_address)
    if coords:
        print(f"地址 '{test_address}' 的经纬度是: {coords}")
        
        # 测试生成高德地图网页链接
        longitude, latitude = coords
        amap_url = generate_amap_web_url(longitude, latitude, test_address)
        print(f"高德地图网页链接: {amap_url}")
        
        # 测试生成导航链接
        nav_url = generate_navigation_url(longitude, latitude, test_address, "car")
        print(f"驾车导航链接: {nav_url}")
    
    print("\n" + "="*30 + "\n")

    # --- 测试生成打车链接 ---
    start_lon, start_lat = 116.478346, 39.997361
    start_name = "方恒国际中心"
    dest_lon, dest_lat = 116.310003, 39.991957
    dest_name = "中关村"

    ride_uri = generate_ride_hailing_uri(start_lon, start_lat, start_name, dest_lon, dest_lat, dest_name)
    print(f"从 '{start_name}' 到 '{dest_name}' 的打车链接是:")
    print(ride_uri)

    print("\n" + "="*30 + "\n")

    # --- 测试距离计算 ---
    dist = haversine_distance(start_lon, start_lat, dest_lon, dest_lat)
    print(f"从 '{start_name}' 到 '{dest_name}' 的直线距离是: {dist:.2f} 公里") 