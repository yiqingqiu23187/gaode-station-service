# 服务站点查询工具


mcp ：
 ```
 # 注意替换 PATH 
      "station-location-service": {
        "command": "python",
        "args": ["PATH/gaode/mcp_server.py"],
        "cwd": "PATH/gaode",
        "env": {
          "PYTHONPATH": "PATH/gaode"
        }
      }

 ```
本项目是一个命令行工具，用于查询高德地图服务站点信息。您可以根据地址查找附近的站点，或通过名称进行模糊搜索。

该工具利用了 `uv` 的脚本运行功能，实现了无需手动管理虚拟环境和依赖的便捷体验。

## 项目结构

```
gaode/
├── station_cli.py              # 主命令行工具 (使用 uv run 执行)
├── database_setup.py           # (初始化) 从 CSV 创建数据库
├── add_coordinates.py          # (初始化) 为 CSV 数据添加经纬度
├── amap_utils.py               # 高德地图 API 相关工具函数
├── mcp_server.py               # [可选] 基于 FastMCP 的网络服务
├── create_archive.sh           # 用于打包项目的脚本
├── stations.db                 # SQLite 数据库文件
├── 岗位位置信息底表.csv        # 原始数据文件
└── 岗位位置信息底表_with_coords.csv # 处理后带坐标的数据文件
```

- **核心工具**: `station_cli.py` 是您日常使用的主要工具。
- **初始化脚本**: `add_coordinates.py` 和 `database_setup.py` 仅需在初次设置或数据更新时运行。
- **可选服务**: `mcp_server.py` 提供了一个可以通过网络 API 访问的备用方式。

## 环境要求

- **Python** (>= 3.10)
- **uv**: 一个极速的 Python 包安装和解析器。

如果您尚未安装 `uv`，可以根据其[官方文档](https://github.com/astral-sh/uv)进行安装。例如：
```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 初始化与设置

在使用本工具前，您需要执行一次性的数据初始化步骤。

### 步骤 1: 为地址数据添加经纬度

首先，运行 `add_coordinates.py` 脚本。它会读取原始的 `岗位位置信息底表.csv`，通过高德地图 API 为每一条地址获取经纬度，并生成一个新的文件 `岗位位置信息底表_with_coords.csv`。

**注意**: 此步骤需要调用网络 API，处理所有地址可能需要几分钟时间。API Key 已硬编码在 `amap_utils.py` 文件中。

```bash
python3 add_coordinates.py
```

### 步骤 2: 创建数据库

接下来，运行 `database_setup.py` 脚本。它会读取上一步生成的带坐标的 CSV 文件，并创建一个名为 `stations.db` 的 SQLite 数据库文件。

此脚本会将**站点数据**（状态、区域等）和**需求数据**（全职、兼职需求等）分别合并成两个单独的文本字段，以简化数据结构。

```bash
python3 database_setup.py
```

完成以上步骤后，`stations.db` 文件就包含了所有可供查询的数据。

## 使用方法

初始化完成后，您就可以通过 `uv` 直接运行 `station_cli.py` 命令行工具了。

### 常用命令

#### 1. 查找最近的站点

使用 `find-nearest` 命令，并提供一个中心地址。您还可以通过 `--k` 选项指定返回站点的数量。

```bash
uv run station_cli.py find-nearest "苏州市工业园区唯新路" --k 1
```

**输出示例:**
```
'苏州市工业园区唯新路' 附近最近的 1 个服务站点:

  服务站      唯新站 (4.01 公里)
  核心数据    站长: 梁鑫 (15850029330)
              面试: 唯新站 (对接人: 梁鑫 / 15850029330.0)
              地址: 苏州市工业园区唯新路133号2号楼1 层101室
  站点数据    状态: 营业中, 区域: 苏州一区, 服务站: 唯新站, 站长姓名: 梁鑫, 联系方式: 15850029330
  需求数据    全职总计: 5.0, 分拣员: 3.0, 白班理货: 2.0, 水产专员: nan, 夜班理货: nan, 副站长: nan, 资深副站长: nan, 兼职总计: 4.0, 兼职-分拣员: 1.0, 兼职-白班理货: 1.0, 兼职-夜班理货: 1.0, 兼职-水产专员: 1.0
```

#### 2. 按名称搜索站点

使用 `search` 命令，并提供一个站点名称的关键词。

```bash
uv run station_cli.py search "唯新"
```

#### 3. 获取帮助

查看所有可用命令和选项。

```bash
uv run station_cli.py --help
```

## [可选] 使用 MCP 网络服务

除了命令行工具，您也可以选择启动 `mcp_server.py` 来提供网络服务。

**注意**: 由于数据库结构已简化，`mcp_server.py` 现在会返回包含 `site_info_str` 和 `demand_info_str` 字段的数据，而不是之前分散的多个字段。任何依赖此服务旧数据结构的客户端都需要进行相应更新。

1.  **启动服务** (它会在后台运行):
    ```bash
    python3 mcp_server.py &
    ```
2.  **调用服务** (需要 `mcp` 客户端):
    ```bash
    mcp station-location-service find_nearest_stations --address "苏州市工业园区唯新路" --k 3
    ```

## 打包项目

如果您需要将整个项目文件夹打包成一个压缩文件，可以运行 `create_archive.sh` 脚本。

```bash
bash create_archive.sh
```
这将在当前目录的上一级目录生成一个 `gaode.tar.gz` 文件。 