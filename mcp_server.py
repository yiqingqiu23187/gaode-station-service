from mcp.server.fastmcp import FastMCP
import sqlite3
from typing import Optional, List, Dict, Any
from amap_utils import get_coordinates, haversine_distance
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
        List[Dict[str, Any]]: A list of dictionaries, each containing station info and distance.
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
        
        return [dict(row) for row in stations]

    except sqlite3.Error as e:
        return [{"error": f"Database error: {e}"}]

@mcp.tool()
def search_stations_by_name(name_query: str) -> List[Dict[str, Any]]:
    """
    Search for stations by name (partial match).
    
    Args:
        name_query: Part of the station name to search for
    
    Returns:
        List of matching stations
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
        
        return [dict(station) for station in stations]
    except sqlite3.Error as e:
        return [{"error": f"Database error: {e}"}]

@mcp.resource("stations://all")
def get_all_stations() -> List[Dict[str, Any]]:
    """
    Get all stations from the database.
    
    Returns:
        List of all stations
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM stations")
        stations = cursor.fetchall()
        conn.close()
        
        return [dict(station) for station in stations]
    except sqlite3.Error as e:
        return [{"error": f"Database error: {e}"}]

@mcp.resource("stations://count")
def get_station_count() -> Dict[str, int]:
    """
    Get the total count of stations in the database.
    
    Returns:
        Dictionary with station count
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
        address: The address to geocode
    
    Returns:
        Dictionary with longitude and latitude
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
    Calculate the distance between two GPS coordinates.
    
    Args:
        from_latitude: Starting latitude
        from_longitude: Starting longitude
        to_latitude: Destination latitude
        to_longitude: Destination longitude
    
    Returns:
        Dictionary with distance in kilometers
    """
    distance = haversine_distance(
        from_longitude, from_latitude,
        to_longitude, to_latitude
    )
    return {"distance_km": round(distance, 2)}

if __name__ == "__main__":
    # For testing the server
    import os
    os.environ["FASTMCP_HOST"] = "0.0.0.0"
    os.environ["FASTMCP_PORT"] = "17263"
    mcp.run(transport="sse")