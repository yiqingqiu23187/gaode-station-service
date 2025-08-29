from mcp.server.fastmcp import FastMCP
import sqlite3
from typing import Optional, List, Dict, Any
from amap_utils import get_coordinates, haversine_distance, generate_amap_web_url, get_bicycling_duration
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
            - address (str): 门店地址
            - longitude (float): 经度坐标
            - latitude (float): 纬度坐标
            - interview_contact_person (str): 面试联系人
            - contact_phone (str): 联系方式
            - site_info_str (str): 站点基本信息（区域、行政区、站点）
            - demand_info_str (str): 岗位需求信息（各岗位人数）
            - distance_km (float): 距离目标位置的公里数（保留2位小数）
            - amap_web_url (str): 高德地图网页链接，可直接打开查看站点位置
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

        def filter_demand_info(demand_info_str: str) -> str:
            if not demand_info_str:
                return ""
            parts = [p.strip() for p in demand_info_str.split(',') if p.strip()]
            kept = []
            for part in parts:
                if ':' not in part:
                    continue
                label, value = part.split(':', 1)
                value = value.strip()
                if value.lower() in {"nan", "n/a"} or value == "":
                    continue
                try:
                    # 过滤值为0或0.0
                    if float(value) == 0.0:
                        continue
                except Exception:
                    # 非数字则保留
                    pass
                kept.append(f"{label.strip()}: {value}")
            return ', '.join(kept)

        # 逐步扩大查询范围以满足k个有效站点
        result: List[Dict[str, Any]] = []
        fetch_limit = max(k * 3, 10)
        max_attempts = 4
        attempt = 0
        while len(result) < k and attempt < max_attempts:
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
            cursor.execute(query, (target_lon, target_lat, fetch_limit))
            rows = cursor.fetchall()

            # 清空并重新筛选，确保按距离顺序去重后取前k个有效
            filtered: List[Dict[str, Any]] = []
            for row in rows:
                station = dict(row)
                # 过滤岗位信息，将空缺为0的岗位移除
                original = station.get('demand_info_str', '')
                filtered_demand = filter_demand_info(original)
                if not filtered_demand:
                    # 整个站点没有岗位，丢弃
                    continue
                station['demand_info_str'] = filtered_demand
                # 添加高德链接
                if station.get('longitude') and station.get('latitude'):
                    amap_url = generate_amap_web_url(
                        station['longitude'], station['latitude'], station['station_name']
                    )
                    station['amap_web_url'] = amap_url
                filtered.append(station)

            # 去重并保留距离最近的前k个
            result = filtered[:k]
            attempt += 1
            fetch_limit *= 2  # 扩大范围再次尝试

        conn.close()
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
            - address (str): 门店地址
            - longitude (float): 经度坐标
            - latitude (float): 纬度坐标
            - interview_contact_person (str): 面试联系人
            - contact_phone (str): 联系方式
            - site_info_str (str): 站点基本信息（区域、行政区、站点）
            - demand_info_str (str): 岗位需求信息（各岗位人数）
            - amap_web_url (str): 高德地图网页链接，可直接打开查看站点位置
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
        
        # 为每个站点添加高德地图网页链接
        result = []
        for station in stations:
            station_dict = dict(station)
            # 如果站点有经纬度坐标，生成高德地图网页链接
            if station_dict.get('longitude') and station_dict.get('latitude'):
                station_lon = station_dict['longitude']
                station_lat = station_dict['latitude']
                station_name = station_dict['station_name']
                amap_url = generate_amap_web_url(station_lon, station_lat, station_name)
                station_dict['amap_web_url'] = amap_url
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
            - address (str): 门店地址
            - longitude (float): 经度坐标
            - latitude (float): 纬度坐标
            - interview_contact_person (str): 面试联系人
            - contact_phone (str): 联系方式
            - site_info_str (str): 站点基本信息（区域、行政区、站点）
            - demand_info_str (str): 岗位需求信息（各岗位人数）
            - amap_web_url (str): 高德地图网页链接，可直接打开查看站点位置
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM stations")
        stations = cursor.fetchall()
        conn.close()
        
        # 为每个站点添加高德地图网页链接
        result = []
        for station in stations:
            station_dict = dict(station)
            # 如果站点有经纬度坐标，生成高德地图网页链接
            if station_dict.get('longitude') and station_dict.get('latitude'):
                station_lon = station_dict['longitude']
                station_lat = station_dict['latitude']
                station_name = station_dict['station_name']
                amap_url = generate_amap_web_url(station_lon, station_lat, station_name)
                station_dict['amap_web_url'] = amap_url
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

@mcp.tool()
def find_best_job(
    user_latitude: float,
    user_longitude: float,
    user_gender: str,
    k: int = 2000
) -> List[Dict[str, Any]]:
    """
    根据用户信息在job_positions表中筛选并推荐合适的工作岗位。
    
    Args:
        user_latitude (float): 用户所在位置的纬度
        user_longitude (float): 用户所在位置的经度
        user_gender (str): 用户性别，可选值："男", "女", "不限"
        k (int): 返回的最大岗位数量，默认2000个
    
    Returns:
        List[Dict[str, Any]]: 推荐的岗位列表，每个字典包含：
            - job_type (str): 岗位类型
            - recruiting_unit (str): 招聘单位
            - city (str): 城市
            - gender (str): 性别要求
            - age_requirement (str): 年龄要求
            - special_requirements (str): 特殊要求
            - accept_criminal_record (str): 是否接受有犯罪记录
            - location (str): 位置
            - longitude (float): 岗位经度坐标
            - latitude (float): 岗位纬度坐标
            - urgent_capacity (int): 运力紧急情况（1表示紧急，0表示普通）
            - working_hours (str): 工作时间
            - relevant_experience (str): 相关经验
            - full_time (str): 全职
            - salary (str): 薪资
            - job_content (str): 工作内容
            - interview_time (str): 面试时间
            - trial_time (str): 试岗时间
            - currently_recruiting (str): 当前是否招聘
            - insurance_status (str): 保险情况
            - accommodation_status (str): 吃住情况
            - distance_km (float): 距离用户的公里数
            - bicycling_duration_minutes (int): 骑行时间（分钟）
    """
    try:
        conn = get_db_connection()
        
        # 检查job_positions表是否存在
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='job_positions'")
        table_exists = cursor.fetchone()
        if not table_exists:
            conn.close()
            return [{"error": "job_positions表不存在，请先运行数据库初始化"}]
        
        # 注册距离计算函数
        conn.create_function("haversine", 4, haversine_distance)
        
        # 构建SQL查询
        # 1. 剔除currently_recruiting != '是'的岗位
        # 2. 根据性别筛选
        # 3. 计算距离并排序
        gender_condition = ""
        if user_gender in ["男", "女"]:
            gender_condition = "AND (gender = ? OR gender = '不限')"
        
        query = f"""
        SELECT 
            job_type,
            recruiting_unit,
            city,
            gender,
            age_requirement,
            special_requirements,
            accept_criminal_record,
            location,
            longitude,
            latitude,
            urgent_capacity,
            working_hours,
            relevant_experience,
            full_time,
            salary,
            job_content,
            interview_time,
            trial_time,
            currently_recruiting,
            insurance_status,
            accommodation_status,
            ROUND(haversine(?, ?, longitude, latitude), 2) as distance_km
        FROM 
            job_positions
        WHERE 
            currently_recruiting = '是'
            AND longitude IS NOT NULL 
            AND latitude IS NOT NULL
            {gender_condition}
        ORDER BY 
            urgent_capacity DESC,
            distance_km ASC
        LIMIT ?
        """
        
        # 准备查询参数
        params = [user_longitude, user_latitude]
        if user_gender in ["男", "女"]:
            params.append(user_gender)
        params.append(k)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        # 格式化结果
        result = []
        for row in rows:
            job_dict = {
                "job_type": row["job_type"],
                "recruiting_unit": row["recruiting_unit"],
                "city": row["city"],
                "gender": row["gender"],
                "age_requirement": row["age_requirement"],
                "special_requirements": row["special_requirements"],
                "accept_criminal_record": row["accept_criminal_record"],
                "location": row["location"],
                "longitude": row["longitude"],
                "latitude": row["latitude"],
                "urgent_capacity": row["urgent_capacity"],
                "working_hours": row["working_hours"],
                "relevant_experience": row["relevant_experience"],
                "full_time": row["full_time"],
                "salary": row["salary"],
                "job_content": row["job_content"],
                "interview_time": row["interview_time"],
                "trial_time": row["trial_time"],
                "currently_recruiting": row["currently_recruiting"],
                "insurance_status": row["insurance_status"],
                "accommodation_status": row["accommodation_status"],
                "distance_km": row["distance_km"]
            }
            
            # 获取骑行时间
            if row["longitude"] and row["latitude"]:
                bicycling_info = get_bicycling_duration(
                    user_longitude, user_latitude,
                    row["longitude"], row["latitude"]
                )
                
                if "error" not in bicycling_info:
                    job_dict["bicycling_duration_minutes"] = bicycling_info.get("duration_minutes", 0)
                else:
                    # 如果API调用失败，设置为默认值
                    job_dict["bicycling_duration_minutes"] = 0
                    print(f"获取骑行时间失败: {bicycling_info.get('error', '未知错误')}")
            else:
                # 如果没有有效经纬度，设置为默认值
                job_dict["bicycling_duration_minutes"] = 0
            
            result.append(job_dict)
        
        return result
        
    except sqlite3.Error as e:
        return [{"error": f"数据库错误: {e}"}]
    except Exception as e:
        return [{"error": f"查询过程中发生错误: {e}"}]

@mcp.tool()
def search_job_by_unit_type(
    recruiting_unit: Optional[str] = None,
    job_type: Optional[str] = None,
    user_latitude: Optional[float] = None,
    user_longitude: Optional[float] = None,
    k: int = 100
) -> List[Dict[str, Any]]:
    """
    根据招聘单位和岗位类型在job_positions表中搜索对应岗位的详细信息。
    支持模糊搜索，可以单独或组合使用搜索条件。
    
    Args:
        recruiting_unit (Optional[str]): 招聘单位名称，支持部分匹配（模糊搜索）
        job_type (Optional[str]): 岗位类型名称，支持部分匹配（模糊搜索）
        user_latitude (Optional[float]): 用户所在位置的纬度（可选，用于计算距离）
        user_longitude (Optional[float]): 用户所在位置的经度（可选，用于计算距离）
        k (int): 返回的最大岗位数量，默认100个
    
    Returns:
        List[Dict[str, Any]]: 搜索到的岗位列表，每个字典包含：
            - job_type (str): 岗位类型
            - recruiting_unit (str): 招聘单位
            - city (str): 城市
            - gender (str): 性别要求
            - age_requirement (str): 年龄要求
            - special_requirements (str): 特殊要求
            - accept_criminal_record (str): 是否接受有犯罪记录
            - location (str): 位置
            - longitude (float): 岗位经度坐标
            - latitude (float): 岗位纬度坐标
            - urgent_capacity (int): 运力紧急情况（1表示紧急，0表示普通）
            - working_hours (str): 工作时间
            - relevant_experience (str): 相关经验
            - full_time (str): 全职
            - salary (str): 薪资
            - job_content (str): 工作内容
            - interview_time (str): 面试时间
            - trial_time (str): 试岗时间
            - currently_recruiting (str): 当前是否招聘
            - insurance_status (str): 保险情况
            - accommodation_status (str): 吃住情况
            - distance_km (float): 距离用户的公里数（如果提供用户坐标）
            - bicycling_duration_minutes (int): 骑行时间（分钟，如果提供用户坐标）
    """
    try:
        # 验证输入参数
        if not recruiting_unit and not job_type:
            return [{"error": "请至少提供招聘单位或岗位类型中的一个搜索条件"}]
        
        conn = get_db_connection()
        
        # 检查job_positions表是否存在
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='job_positions'")
        table_exists = cursor.fetchone()
        if not table_exists:
            conn.close()
            return [{"error": "job_positions表不存在，请先运行数据库初始化"}]
        
        # 构建搜索条件
        where_conditions = ["currently_recruiting = '是'"]
        params = []
        
        # 添加招聘单位模糊搜索条件
        if recruiting_unit:
            where_conditions.append("recruiting_unit LIKE ?")
            params.append(f"%{recruiting_unit}%")
        
        # 添加岗位类型模糊搜索条件
        if job_type:
            where_conditions.append("job_type LIKE ?")
            params.append(f"%{job_type}%")
        
        # 确定是否需要计算距离
        calculate_distance = user_latitude is not None and user_longitude is not None
        
        if calculate_distance:
            # 注册距离计算函数
            conn.create_function("haversine", 4, haversine_distance)
            
            # 包含距离计算的查询
            query = f"""
            SELECT 
                job_type,
                recruiting_unit,
                city,
                gender,
                age_requirement,
                special_requirements,
                accept_criminal_record,
                location,
                longitude,
                latitude,
                urgent_capacity,
                working_hours,
                relevant_experience,
                full_time,
                salary,
                job_content,
                interview_time,
                trial_time,
                currently_recruiting,
                insurance_status,
                accommodation_status,
                ROUND(haversine(?, ?, longitude, latitude), 2) as distance_km
            FROM 
                job_positions
            WHERE 
                {' AND '.join(where_conditions)}
                AND longitude IS NOT NULL 
                AND latitude IS NOT NULL
            ORDER BY 
                urgent_capacity DESC,
                distance_km ASC
            LIMIT ?
            """
            # 将用户坐标添加到参数列表开头
            query_params = [user_longitude, user_latitude] + params + [k]
        else:
            # 不计算距离的查询
            query = f"""
            SELECT 
                job_type,
                recruiting_unit,
                city,
                gender,
                age_requirement,
                special_requirements,
                accept_criminal_record,
                location,
                longitude,
                latitude,
                urgent_capacity,
                working_hours,
                relevant_experience,
                full_time,
                salary,
                job_content,
                interview_time,
                trial_time,
                currently_recruiting,
                insurance_status,
                accommodation_status
            FROM 
                job_positions
            WHERE 
                {' AND '.join(where_conditions)}
            ORDER BY 
                urgent_capacity DESC,
                job_type ASC,
                recruiting_unit ASC
            LIMIT ?
            """
            query_params = params + [k]
        
        cursor.execute(query, query_params)
        rows = cursor.fetchall()
        conn.close()
        
        # 格式化结果
        result = []
        for row in rows:
            job_dict = {
                "job_type": row["job_type"],
                "recruiting_unit": row["recruiting_unit"],
                "city": row["city"],
                "gender": row["gender"],
                "age_requirement": row["age_requirement"],
                "special_requirements": row["special_requirements"],
                "accept_criminal_record": row["accept_criminal_record"],
                "location": row["location"],
                "longitude": row["longitude"],
                "latitude": row["latitude"],
                "urgent_capacity": row["urgent_capacity"],
                "working_hours": row["working_hours"],
                "relevant_experience": row["relevant_experience"],
                "full_time": row["full_time"],
                "salary": row["salary"],
                "job_content": row["job_content"],
                "interview_time": row["interview_time"],
                "trial_time": row["trial_time"],
                "currently_recruiting": row["currently_recruiting"],
                "insurance_status": row["insurance_status"],
                "accommodation_status": row["accommodation_status"]
            }
            
            # 如果计算了距离，添加距离字段
            if calculate_distance:
                job_dict["distance_km"] = row["distance_km"]
                
                # 获取骑行时间
                if row["longitude"] and row["latitude"]:
                    bicycling_info = get_bicycling_duration(
                        user_longitude, user_latitude,
                        row["longitude"], row["latitude"]
                    )
                    
                    if "error" not in bicycling_info:
                        job_dict["bicycling_duration_minutes"] = bicycling_info.get("duration_minutes", 0)
                    else:
                        # 如果API调用失败，设置为默认值
                        job_dict["bicycling_duration_minutes"] = 0
                        print(f"获取骑行时间失败: {bicycling_info.get('error', '未知错误')}")
                else:
                    # 如果没有有效经纬度，设置为默认值
                    job_dict["bicycling_duration_minutes"] = 0
            else:
                # 如果没有用户坐标，设置距离相关字段为默认值
                job_dict["distance_km"] = None
                job_dict["bicycling_duration_minutes"] = None
            
            result.append(job_dict)
        
        return result
        
    except sqlite3.Error as e:
        return [{"error": f"数据库错误: {e}"}]
    except Exception as e:
        return [{"error": f"查询过程中发生错误: {e}"}]

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