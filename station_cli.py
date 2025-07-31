#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "requests",
#   "typer",
#   "rich",
# ]
# ///

import typer
from typing_extensions import Annotated
import sqlite3
from typing import Optional, List, Dict, Any
import os
import math
import requests
import time
from urllib.parse import urlencode
from amap_utils import generate_amap_web_url

# --- 配置和全局变量 ---

# 高德地图 API Key
AMAP_API_KEY = "7d2a69204c7a8340ac59834fc5d945df"
GEOCODE_URL = "https://restapi.amap.com/v3/geocode/geo"

# 获取脚本所在目录的绝对路径，以确保能正确找到数据库文件
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(SCRIPT_DIR, 'stations.db')

# 初始化 Typer 应用
app = typer.Typer(
    help="一个用于查询服务站点的命令行工具。",
    context_settings={"help_option_names": ["-h", "--help"]},
    add_completion=False
)

# --- 核心工具函数 (从 amap_utils.py 和 mcp_server.py 移植) ---

def get_coordinates(address: str, api_key: str = AMAP_API_KEY, max_retries: int = 3, retry_delay: int = 1) -> Optional[tuple[float, float]]:
    """使用高德地图 API 将地址转换为经纬度，并包含重试逻辑。"""
    if not isinstance(address, str) or not address.strip():
        return None
    params = {'key': api_key, 'address': address, 'output': 'json'}
    for attempt in range(max_retries):
        try:
            response = requests.get(GEOCODE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get('status') == '1' and data.get('geocodes'):
                location = data['geocodes'][0]['location']
                longitude, latitude = map(float, location.split(','))
                return longitude, latitude
            else:
                return None
        except requests.exceptions.RequestException:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            continue
    return None

def haversine_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """使用 Haversine 公式计算两个经纬度坐标之间的距离（公里）。"""
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # 地球半径
    return c * r

def get_db_connection() -> sqlite3.Connection:
    """创建并返回数据库连接。"""
    if not os.path.exists(DB_FILE):
        raise typer.Exit(f"错误: 数据库文件 '{DB_FILE}' 不存在。请先运行 'database_setup.py'。")
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# --- 命令行接口定义 ---

@app.command(name="find-nearest", help="根据地址查找最近的 K 个服务站。")
def find_nearest_stations_cli(
    address: Annotated[str, typer.Argument(help="要查询的中心地址，例如 '苏州市工业园区'。")],
    k: Annotated[int, typer.Option("--k", "-k", help="要查找的站点数量。")] = 3
):
    """
    根据输入的地址，查找并显示最近的 K 个服务站点及其详细信息。
    """
    from rich.console import Console
    from rich.table import Table

    console = Console()

    with console.status(f"[bold green]正在查询地址 '{address}' 的坐标...", spinner="dots") as status:
        coords = get_coordinates(address)
        if not coords:
            console.print(f"[bold red]错误: 无法解析地址 '{address}'，请确认地址是否正确。[/bold red]")
            raise typer.Exit()
        target_lon, target_lat = coords
        status.update(f"[bold green]坐标获取成功: {target_lon}, {target_lat}。正在查询数据库...")

        try:
            conn = get_db_connection()
            conn.create_function("haversine", 4, haversine_distance)
            cursor = conn.cursor()
            query = "SELECT *, ROUND(haversine(?, ?, longitude, latitude), 2) as distance_km FROM stations ORDER BY distance_km LIMIT ?"
            cursor.execute(query, (target_lon, target_lat, k))
            stations = [dict(row) for row in cursor.fetchall()]
            conn.close()
        except sqlite3.Error as e:
            console.print(f"[bold red]数据库查询失败: {e}[/bold red]")
            raise typer.Exit()
    
    if not stations:
        console.print(f"[yellow]在地址 '{address}' 附近没有找到服务站。[/yellow]")
        return

    console.print(f"\n[bold blue]'{address}' 附近最近的 {len(stations)} 个服务站点:[/bold blue]")

    for station in stations:
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("[bold]服务站[/bold]", f"[bold green]{station['station_name']} ({station['distance_km']:.2f} 公里)[/bold green]")
        table.add_row("核心数据", f"站长: {station.get('manager_name', 'N/A')} ({station.get('contact_phone', 'N/A')})")
        table.add_row("", f"面试: {station.get('interview_location', 'N/A')} (对接人: {station.get('interview_contact_person', 'N/A')} / {station.get('interview_contact_phone', 'N/A')})")
        table.add_row("", f"地址: {station.get('address', 'N/A')}")
        
        # 生成高德地图网页链接
        if station.get('longitude') and station.get('latitude'):
            station_lon = station['longitude']
            station_lat = station['latitude']
            station_name = station['station_name']
            
            # 生成高德地图网页链接
            amap_url = generate_amap_web_url(station_lon, station_lat, station_name)
            table.add_row("地图链接", f"[link={amap_url}]高德地图网页版[/link]")
        
        table.add_row("站点数据", station.get('site_info_str', '无'))
        table.add_row("需求数据", station.get('demand_info_str', '无'))

        console.print(table)
        console.print() # 添加空行

@app.command(name="search", help="根据名称模糊搜索服务站。")
def search_stations_by_name_cli(
    name_query: Annotated[str, typer.Argument(help="要搜索的服务站名称关键词。")]
):
    """
    根据输入的关键词，模糊匹配并显示所有相关的服务站点。
    """
    from rich.console import Console
    from rich.table import Table
    import rich

    console = Console()

    with console.status(f"[bold green]正在搜索名称包含 '{name_query}' 的站点...", spinner="dots"):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM stations WHERE station_name LIKE ?", (f"%{name_query}%",))
            stations = [dict(row) for row in cursor.fetchall()]
            conn.close()
        except sqlite3.Error as e:
            console.print(f"[bold red]数据库查询失败: {e}[/bold red]")
            raise typer.Exit()

    if not stations:
        console.print(f"[yellow]没有找到名称中包含 '{name_query}' 的服务站。[/yellow]")
        return

    console.print(f"\n[bold blue]找到 {len(stations)} 个名称匹配 '{name_query}' 的站点:[/bold blue]")
    
    table = Table(title="搜索结果", box=rich.box.MINIMAL_DOUBLE_HEAD)
    table.add_column("ID", style="dim")
    table.add_column("服务站名称", style="bold green")
    table.add_column("站点数据", style="cyan")
    table.add_column("地址", style="magenta")
    
    for station in stations:
        table.add_row(
            str(station['id']),
            station['station_name'],
            station.get('site_info_str', 'N/A'),
            station.get('address', 'N/A')
        )
    
    console.print(table)


if __name__ == "__main__":
    app() 