from mcp.server.fastmcp import FastMCP
import sqlite3
from typing import Optional, List, Dict, Any
from amap_utils import get_coordinates, haversine_distance, get_bicycling_duration
import os

# Create a FastMCP server
mcp = FastMCP("Station Location Service", dependencies=["sqlite3"])

# --- 调试代码 ---
# 获取当前工作目录
# CWD = os.getcwd()
# 构造数据库文件的绝对路径
# DB_FILE = os.path.join(CWD, 'stations.db')

# 获取脚本所在目录的绝对路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 构造数据库文件的绝对路径
DB_FILE = os.path.join(SCRIPT_DIR, 'stations.db')


print(f"--- [Debug Info] ---")
# print(f"Server is running in: {CWD}")
print(f"Server script directory is: {SCRIPT_DIR}")
print(f"Attempting to connect to DB at: {DB_FILE}")
print(f"DB file exists: {os.path.exists(DB_FILE)}")
print(f"--------------------")


def get_db_connection():
    """Create and return a database connection"""
    conn = sqlite3.connect(DB_FILE)
    
    # --- More Debugging ---
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stations'")
        table_exists = cursor.fetchone()
        print(f"DEBUG: 'stations' table exists in DB? {'Yes' if table_exists else 'No'}")
        cursor.close()
    except Exception as e:
        print(f"DEBUG: Error checking for table: {e}")
    # --- End Debugging ---

    conn.row_factory = sqlite3.Row
    return conn

@mcp.tool()
def find_nearest_stations(
    address: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    k: int = 3
) -> List[Dict[str, Any]]:
    """
    Find the K nearest service stations based on address or coordinates.

    Args:
        address (Optional[str]): The address to search from (e.g., "北京市中关村").
        latitude (Optional[float]): The latitude to search from.
        longitude (Optional[float]): The longitude to search from.
        k (int): The number of nearest stations to return. Defaults to 3.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each containing:
            - id (int): 站点唯一标识符
            - station_name (str): 服务站名称
            - address (str): 门店地址（本站点地址非面试站点地址）
            - longitude (float): 经度坐标
            - latitude (float): 纬度坐标
            - manager_name (str): 站长姓名
            - contact_phone (str): 联系方式
            - interview_location (str): 面试地点
            - interview_contact_person (str): 面试对接人
            - interview_contact_phone (str): 面试对接人联系方式/站点座机号
            - site_info_str (str): 站点基本信息（状态、区域、服务站、站长姓名、联系方式）
            - demand_info_str (str): 岗位需求信息（全职/兼职各岗位人数）
            - distance_km (float): 距离目标位置的公里数（保留2位小数）
            - bicycling_duration_minutes (int): 从起点到该站点的骑车时间（分钟）
            - bicycling_distance_meters (int): 从起点到该站点的骑车距离（米）
    """
    if latitude is not None and longitude is not None:
        # Use provided coordinates
        target_lat, target_lon = latitude, longitude
    elif address:
        # Geocode the address
        coords = get_coordinates(address)
        if not coords:
            return {"error": f"Could not geocode address: {address}"}
        target_lon, target_lat = coords # Correctly assign target_lon and target_lat
    else:
        return {"error": "Please provide either address or latitude/longitude"}
    
    try:
        conn = get_db_connection()
        
        # Register the Python haversine function for use in SQL
        conn.create_function("haversine", 4, haversine_distance)

        cursor = conn.cursor()
        
        # The new query calculates distance, orders by it, and limits to k results
        query = """
        SELECT 
            *,
            ROUND(haversine(?, ?, longitude, latitude), 2) as distance_km
        FROM 
            stations
        ORDER BY 
            distance_km
        LIMIT ?
        """
        
        cursor.execute(query, (target_lon, target_lat, k))
        stations = cursor.fetchall()
        conn.close()
        
        # 为每个站点添加骑车时间
        result = []
        for row in stations:
            station_dict = dict(row)
            # 如果站点有经纬度坐标，获取骑车时间
            if station_dict.get('longitude') and station_dict.get('latitude'):
                station_lon = station_dict['longitude']
                station_lat = station_dict['latitude']
                
                # 获取从起点到该站点的骑车时间
                bicycling_info = get_bicycling_duration(
                    target_lon, target_lat, 
                    station_lon, station_lat
                )
                
                if 'error' not in bicycling_info:
                    station_dict['bicycling_duration_minutes'] = bicycling_info.get('duration_minutes')
                    station_dict['bicycling_distance_meters'] = bicycling_info.get('distance_meters')
                else:
                    station_dict['bicycling_duration_minutes'] = None
                    station_dict['bicycling_distance_meters'] = None
            result.append(station_dict)
        
        return result

    except sqlite3.Error as e:
        return [{"error": f"Database error: {e}"}]

@mcp.tool()
def search_stations_by_name(name_query: str) -> List[Dict[str, Any]]:
    """
    Search for stations by name (partial match).
    
    Args:
        name_query (str): Part of the station name to search for
    
    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each containing:
            - id (int): 站点唯一标识符
            - station_name (str): 服务站名称
            - address (str): 门店地址（本站点地址非面试站点地址）
            - longitude (float): 经度坐标
            - latitude (float): 纬度坐标
            - manager_name (str): 站长姓名
            - contact_phone (str): 联系方式
            - interview_location (str): 面试地点
            - interview_contact_person (str): 面试对接人
            - interview_contact_phone (str): 面试对接人联系方式/站点座机号
            - site_info_str (str): 站点基本信息（状态、区域、服务站、站长姓名、联系方式）
            - demand_info_str (str): 岗位需求信息（全职/兼职各岗位人数）
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM stations WHERE station_name LIKE ?",
            (f"%{name_query}%",)
        )
        stations = cursor.fetchall()
        conn.close()
        
        # 直接返回站点信息
        result = []
        for station in stations:
            station_dict = dict(station)
            result.append(station_dict)
        
        return result
    except sqlite3.Error as e:
        return [{"error": f"Database error: {e}"}]

@mcp.resource("stations://all")
def get_all_stations() -> List[Dict[str, Any]]:
    """
    Get all stations from the database.
    
    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each containing:
            - id (int): 站点唯一标识符
            - station_name (str): 服务站名称
            - address (str): 门店地址（本站点地址非面试站点地址）
            - longitude (float): 经度坐标
            - latitude (float): 纬度坐标
            - manager_name (str): 站长姓名
            - contact_phone (str): 联系方式
            - interview_location (str): 面试地点
            - interview_contact_person (str): 面试对接人
            - interview_contact_phone (str): 面试对接人联系方式/站点座机号
            - site_info_str (str): 站点基本信息（状态、区域、服务站、站长姓名、联系方式）
            - demand_info_str (str): 岗位需求信息（全职/兼职各岗位人数）
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM stations")
        stations = cursor.fetchall()
        conn.close()
        
        # 直接返回站点信息
        result = []
        for station in stations:
            station_dict = dict(station)
            result.append(station_dict)
        
        return result
    except sqlite3.Error as e:
        return [{"error": f"Database error: {e}"}]

@mcp.resource("stations://count")
def get_station_count() -> Dict[str, int]:
    """
    Get the total count of stations in the database.
    
    Returns:
        Dict[str, int]: A dictionary containing:
            - total_stations (int): 数据库中站点的总数量
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM stations")
        result = cursor.fetchone()
        conn.close()
        
        return {"total_stations": result['count']}
    except sqlite3.Error as e:
        return {"error": f"Database error: {e}"}

@mcp.tool()
def geocode_address(address: str) -> Dict[str, float]:
    """
    Convert a Chinese address to GPS coordinates using Amap API.
    
    Args:
        address (str): The address to geocode (e.g., "北京市中关村")
    
    Returns:
        Dict[str, float]: A dictionary containing:
            - longitude (float): 经度坐标
            - latitude (float): 纬度坐标
            - error (str): 错误信息（如果地址解析失败）
    """
    coords = get_coordinates(address)
    if coords:
        longitude, latitude = coords
        return {"longitude": longitude, "latitude": latitude}
    else:
        return {"error": "Could not geocode address"}

@mcp.tool()
def calculate_distance(
    from_latitude: float,
    from_longitude: float,
    to_latitude: float,
    to_longitude: float
) -> Dict[str, float]:
    """
    Calculate the distance between two GPS coordinates using Haversine formula.
    
    Args:
        from_latitude (float): Starting latitude
        from_longitude (float): Starting longitude
        to_latitude (float): Destination latitude
        to_longitude (float): Destination longitude
    
    Returns:
        Dict[str, float]: A dictionary containing:
            - distance_km (float): 两点间的距离，单位为公里（保留2位小数）
    """
    distance = haversine_distance(
        from_longitude, from_latitude,
        to_longitude, to_latitude
    )
    return {"distance_km": round(distance, 2)}

if __name__ == "__main__":
    # 本地测试时使用
    import os
    import uvicorn
    
    print("Starting MCP server for local testing...")
    
    # 使用FastMCP的sse_app()方法获取Starlette应用
    app = mcp.sse_app()
    
    # 使用uvicorn启动服务器
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=17263,
        log_level="info"
    )