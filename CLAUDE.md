# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a geocoding and location-based service project that processes store location data using Amap (高德地图) API. The project includes:

- **Geocoding functionality**: Converts Chinese addresses to GPS coordinates
- **Database management**: Creates SQLite database from CSV location data
- **MCP server**: Provides a Model Context Protocol server for integration
- **Distance calculations**: Uses haversine formula for distance between coordinates
- **Ride-hailing integration**: Generates Amap URI for taxi booking between locations

## Key Components

### Data Processing Pipeline
1. **add_coordinates.py**: Processes CSV files to add GPS coordinates using Amap API
2. **database_setup.py**: Creates SQLite database from processed CSV data
3. **amap_utils.py**: Core utilities for Amap API interaction and coordinate calculations
4. **mcp_server.py**: FastMCP server for diagnostic/testing purposes

### Data Files
- `岗位位置信息底表.csv`: Raw CSV with store locations (Chinese addresses)
- `岗位位置信息底表_with_coords.csv`: Processed CSV with added GPS coordinates
- `stations.db`: SQLite database containing processed location data

## Setup and Development

### Prerequisites
- Python 3.x
- Required packages: pandas, requests, mcp

### Initial Setup
```bash
# Install dependencies
pip install "mcp[cli]" pandas requests

# Process raw CSV to add coordinates
python add_coordinates.py

# Create database from processed CSV
python database_setup.py

# Run MCP server for testing
mcp dev mcp_server.py
```

### Working with Location Data

The project uses Chinese address data in CSV format. Key fields:
- `服务站`: Store name
- `门店地址（本站点地址非面试站点地址）`: Store address (used for geocoding)
- `站长姓名`: Manager name
- `联系方式`: Contact phone

### API Configuration
- **Amap API Key**: `7d2a69204c7a8340ac59834fc5d945df` (hardcoded in amap_utils.py)
- **Rate limiting**: Built-in delays (0.1s between requests) and retry logic (5 retries)

### Common Operations

#### Process new location data
1. Place CSV file as `岗位位置信息底表.csv`
2. Run: `python add_coordinates.py` (adds GPS coordinates)
3. Run: `python database_setup.py` (creates SQLite database)

#### Query location data
Use the SQLite database (`stations.db`) with table structure:
```sql
CREATE TABLE stations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_name TEXT NOT NULL,
    address TEXT,
    longitude REAL NOT NULL,
    latitude REAL NOT NULL,
    manager_name TEXT,
    contact_phone TEXT
);
```

#### Geocoding addresses
Use the `get_coordinates()` function from `amap_utils.py` to convert addresses to coordinates.

#### Calculate distances
Use `haversine_distance(lon1, lat1, lon2, lat2)` from `amap_utils.py` to calculate distances between coordinates.

#### Generate ride-hailing links
Use `generate_ride_hailing_uri(slon, slat, sname, dlon, dlat, dname)` to create Amap taxi booking links.

## MCP Server Features

### Available Tools
- **find_nearest_station**: Find the nearest service station from address or coordinates
- **search_stations_by_name**: Search stations by name (partial match)
- **geocode_address**: Convert Chinese address to GPS coordinates
- **calculate_distance**: Calculate distance between two GPS coordinates

### Available Resources
- **stations://all**: Get all stations from the database
- **stations://count**: Get total count of stations

### Testing

Test the geocoding functionality:
```python
from amap_utils import get_coordinates
coords = get_coordinates("北京市朝阳区阜通东大街6号")
print(coords)  # Returns: (longitude, latitude)
```

Test MCP server:
```bash
# Run the MCP server
mcp dev mcp_server.py

# Test with MCP Inspector
# The server will provide tools for:
# - Finding nearest stations
# - Searching stations by name
# - Geocoding addresses
# - Calculating distances
```