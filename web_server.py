#!/usr/bin/env python3
"""
Web服务器 - 为H5控制面板提供API接口
提供站点数据的CRUD操作
"""

from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
import sqlite3
import os
import json
from typing import Dict, List, Any

# 获取脚本所在目录的绝对路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(SCRIPT_DIR, 'stations.db')

app = Flask(__name__)
CORS(app)  # 允许跨域请求

def get_db_connection():
    """创建数据库连接"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    """返回控制面板页面"""
    return render_template_string(HTML_TEMPLATE)

def parse_demand_info(demand_info_str):
    """解析需求信息字符串，提取各个岗位的数量"""
    demand_data = {
        'fulltime_total': '0',
        'sorter': '0',
        'day_handler': '0',
        'aquatic_specialist': '0',
        'night_handler': '0',
        'deputy_manager': '0',
        'senior_deputy_manager': '0',
        'parttime_total': '0',
        'parttime_sorter': '0',
        'parttime_day_handler': '0',
        'parttime_night_handler': '0',
        'parttime_aquatic_specialist': '0'
    }

    if not demand_info_str:
        return demand_data

    # 解析字符串，格式如: "全职总计: 8, 分拣员: 5.0, 白班理货: 0, ..."
    items = demand_info_str.split(', ')
    for item in items:
        if ':' in item:
            key, value = item.split(':', 1)
            key = key.strip()
            value = value.strip()

            # 映射中文字段名到英文字段名
            field_mapping = {
                '全职总计': 'fulltime_total',
                '分拣员': 'sorter',
                '白班理货': 'day_handler',
                '水产专员': 'aquatic_specialist',
                '夜班理货': 'night_handler',
                '副站长': 'deputy_manager',
                '资深副站长': 'senior_deputy_manager',
                '兼职总计': 'parttime_total',
                '兼职-分拣员': 'parttime_sorter',
                '兼职-白班理货': 'parttime_day_handler',
                '兼职-夜班理货': 'parttime_night_handler',
                '兼职-水产专员': 'parttime_aquatic_specialist'
            }

            if key in field_mapping:
                demand_data[field_mapping[key]] = value

    return demand_data

def build_demand_info_string(demand_data):
    """根据需求数据构建需求信息字符串"""
    field_mapping = {
        'fulltime_total': '全职总计',
        'sorter': '分拣员',
        'day_handler': '白班理货',
        'aquatic_specialist': '水产专员',
        'night_handler': '夜班理货',
        'deputy_manager': '副站长',
        'senior_deputy_manager': '资深副站长',
        'parttime_total': '兼职总计',
        'parttime_sorter': '兼职-分拣员',
        'parttime_day_handler': '兼职-白班理货',
        'parttime_night_handler': '兼职-夜班理货',
        'parttime_aquatic_specialist': '兼职-水产专员'
    }

    items = []
    for field, chinese_name in field_mapping.items():
        value = demand_data.get(field, '0')
        items.append(f"{chinese_name}: {value}")

    return ', '.join(items)

@app.route('/api/stations', methods=['GET'])
def get_all_stations():
    """获取所有站点数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM stations ORDER BY id")
        raw_stations = [dict(row) for row in cursor.fetchall()]
        conn.close()

        # 处理每个站点数据，解析需求信息
        stations = []
        for station in raw_stations:
            # 解析需求信息
            demand_data = parse_demand_info(station.get('demand_info_str', ''))

            # 合并站点基本信息和解析后的需求信息
            processed_station = {
                'id': station['id'],
                'station_name': station['station_name'],
                'address': station['address'],
                'longitude': station['longitude'],
                'latitude': station['latitude'],
                'manager_name': station['manager_name'],
                'contact_phone': station['contact_phone'],
                'interview_location': station['interview_location'],
                'interview_contact_person': station['interview_contact_person'],
                'interview_contact_phone': station['interview_contact_phone'],
                # 不包含 site_info_str，添加解析后的需求字段
                **demand_data
            }
            stations.append(processed_station)

        return jsonify({
            'success': True,
            'data': stations,
            'total': len(stations)
        })
    except sqlite3.Error as e:
        return jsonify({
            'success': False,
            'error': f'数据库错误: {str(e)}'
        }), 500

@app.route('/api/stations/<int:station_id>', methods=['PUT'])
def update_station(station_id):
    """更新单个站点数据"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '无效的JSON数据'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 构建更新SQL语句
        update_fields = []
        values = []
        
        # 允许更新的基本字段
        basic_fields = [
            'station_name', 'address', 'longitude', 'latitude',
            'manager_name', 'contact_phone', 'interview_location',
            'interview_contact_person', 'interview_contact_phone'
        ]

        # 需求信息字段
        demand_fields = [
            'fulltime_total', 'sorter', 'day_handler', 'aquatic_specialist',
            'night_handler', 'deputy_manager', 'senior_deputy_manager',
            'parttime_total', 'parttime_sorter', 'parttime_day_handler',
            'parttime_night_handler', 'parttime_aquatic_specialist'
        ]

        # 处理基本字段
        for field in basic_fields:
            if field in data:
                update_fields.append(f"{field} = ?")
                values.append(data[field])

        # 处理需求信息字段
        demand_data = {}
        has_demand_updates = False
        for field in demand_fields:
            if field in data:
                demand_data[field] = data[field]
                has_demand_updates = True

        # 如果有需求信息更新，需要重新构建demand_info_str
        if has_demand_updates:
            # 先获取当前记录的需求信息
            cursor.execute("SELECT demand_info_str FROM stations WHERE id = ?", (station_id,))
            current_row = cursor.fetchone()
            if current_row:
                current_demand = parse_demand_info(current_row['demand_info_str'])
                # 更新修改的字段
                current_demand.update(demand_data)
                # 重新构建字符串
                new_demand_str = build_demand_info_string(current_demand)
                update_fields.append("demand_info_str = ?")
                values.append(new_demand_str)
        
        if not update_fields:
            return jsonify({
                'success': False,
                'error': '没有提供有效的更新字段'
            }), 400
        
        values.append(station_id)
        sql = f"UPDATE stations SET {', '.join(update_fields)} WHERE id = ?"
        
        cursor.execute(sql, values)
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({
                'success': False,
                'error': f'未找到ID为{station_id}的站点'
            }), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'站点ID {station_id} 更新成功'
        })
        
    except sqlite3.Error as e:
        return jsonify({
            'success': False,
            'error': f'数据库错误: {str(e)}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500

@app.route('/api/stations/batch', methods=['PUT'])
def batch_update_stations():
    """批量更新站点数据"""
    try:
        data = request.get_json()
        if not data or 'updates' not in data:
            return jsonify({
                'success': False,
                'error': '无效的JSON数据格式'
            }), 400
        
        updates = data['updates']
        if not isinstance(updates, list):
            return jsonify({
                'success': False,
                'error': 'updates必须是数组格式'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        success_count = 0
        error_count = 0
        errors = []
        
        # 允许更新的基本字段
        basic_fields = [
            'station_name', 'address', 'longitude', 'latitude',
            'manager_name', 'contact_phone', 'interview_location',
            'interview_contact_person', 'interview_contact_phone'
        ]

        # 需求信息字段
        demand_fields = [
            'fulltime_total', 'sorter', 'day_handler', 'aquatic_specialist',
            'night_handler', 'deputy_manager', 'senior_deputy_manager',
            'parttime_total', 'parttime_sorter', 'parttime_day_handler',
            'parttime_night_handler', 'parttime_aquatic_specialist'
        ]

        for update_item in updates:
            try:
                if 'id' not in update_item:
                    error_count += 1
                    errors.append('缺少站点ID')
                    continue

                station_id = update_item['id']

                # 构建更新SQL语句
                update_fields = []
                values = []

                # 处理基本字段
                for field in basic_fields:
                    if field in update_item:
                        update_fields.append(f"{field} = ?")
                        values.append(update_item[field])

                # 处理需求信息字段
                demand_data = {}
                has_demand_updates = False
                for field in demand_fields:
                    if field in update_item:
                        demand_data[field] = update_item[field]
                        has_demand_updates = True

                # 如果有需求信息更新，需要重新构建demand_info_str
                if has_demand_updates:
                    # 先获取当前记录的需求信息
                    cursor.execute("SELECT demand_info_str FROM stations WHERE id = ?", (station_id,))
                    current_row = cursor.fetchone()
                    if current_row:
                        current_demand = parse_demand_info(current_row['demand_info_str'])
                        # 更新修改的字段
                        current_demand.update(demand_data)
                        # 重新构建字符串
                        new_demand_str = build_demand_info_string(current_demand)
                        update_fields.append("demand_info_str = ?")
                        values.append(new_demand_str)
                
                if not update_fields:
                    error_count += 1
                    errors.append(f'站点ID {station_id}: 没有提供有效的更新字段')
                    continue
                
                values.append(station_id)
                sql = f"UPDATE stations SET {', '.join(update_fields)} WHERE id = ?"
                
                cursor.execute(sql, values)
                
                if cursor.rowcount == 0:
                    error_count += 1
                    errors.append(f'未找到ID为{station_id}的站点')
                else:
                    success_count += 1
                    
            except Exception as e:
                error_count += 1
                errors.append(f'处理站点更新时出错: {str(e)}')
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'批量更新完成: 成功{success_count}条，失败{error_count}条',
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors
        })
        
    except sqlite3.Error as e:
        return jsonify({
            'success': False,
            'error': f'数据库错误: {str(e)}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500

# HTML模板 - 完整的H5控制面板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>站点管理控制面板</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f8f9fa;
            min-height: 100vh;
            color: #2c3e50;
        }

        .container {
            max-width: 100%;
            margin: 0 auto;
            padding: 20px;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }

        .header {
            background-color: #4a90e2;
            color: white;
            padding: 25px;
            border-radius: 8px;
            margin-bottom: 25px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .header h1 {
            font-size: 1.4rem;
            font-weight: 500;
            text-align: center;
            margin: 0;
        }

        .controls {
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
            flex-wrap: wrap;
            justify-content: flex-start;
        }

        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .btn-primary {
            background-color: #4a90e2;
            color: white;
            border: 1px solid #4a90e2;
        }

        .btn-primary:hover {
            background-color: #357abd;
            border-color: #357abd;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(74, 144, 226, 0.3);
        }

        .btn-secondary {
            background-color: #6c757d;
            color: white;
            border: 1px solid #6c757d;
        }

        .btn-secondary:hover {
            background-color: #5a6268;
            border-color: #5a6268;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(108, 117, 125, 0.3);
        }

        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .table-container {
            flex: 1;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border: 1px solid #e9ecef;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }

        .table-wrapper {
            flex: 1;
            overflow: auto;
            position: relative;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }

        th {
            background-color: #4a90e2;
            color: white;
            padding: 14px 10px;
            text-align: left;
            font-weight: 600;
            position: sticky;
            top: 0;
            z-index: 10;
            white-space: nowrap;
            border-bottom: 2px solid #357abd;
        }

        td {
            padding: 12px 10px;
            border-bottom: 1px solid #e9ecef;
            vertical-align: top;
        }

        tr:nth-child(even) {
            background-color: #f8f9fa;
        }

        tr:hover {
            background-color: #e8f4fd;
        }

        .editable {
            background: transparent;
            border: 1px solid transparent;
            padding: 4px;
            border-radius: 3px;
            width: 100%;
            min-width: 80px;
            font-size: 13px;
        }

        .editable:focus {
            outline: none;
            border-color: #4a90e2;
            background: white;
            box-shadow: 0 0 0 2px rgba(74, 144, 226, 0.2);
        }

        .editable.modified {
            background-color: #fff8e1;
            border-color: #ff9800;
        }

        .status-bar {
            padding: 16px 20px;
            background-color: #f8f9fa;
            border-top: 1px solid #dee2e6;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 14px;
            color: #6c757d;
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: #6c757d;
        }

        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 6px;
            margin: 10px 0;
        }

        .success {
            background: #d4edda;
            color: #155724;
            padding: 15px;
            border-radius: 6px;
            margin: 10px 0;
        }

        /* 自定义滚动条 */
        .table-wrapper::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }

        .table-wrapper::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 4px;
        }

        .table-wrapper::-webkit-scrollbar-thumb {
            background-color: #6c757d;
            border-radius: 4px;
        }

        .table-wrapper::-webkit-scrollbar-thumb:hover {
            background-color: #5a6268;
        }

        /* 响应式设计 */
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }

            .header h1 {
                font-size: 1.5rem;
            }

            .controls {
                flex-direction: column;
            }

            .btn {
                width: 100%;
            }

            table {
                font-size: 12px;
            }

            th, td {
                padding: 8px 4px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>站点管理控制面板</h1>
        </div>

        <div class="controls">
            <button id="reloadBtn" class="btn btn-secondary">🔄 刷新数据</button>
            <button id="refreshBtn" class="btn btn-secondary">🔄 重置数据</button>
            <button id="submitBtn" class="btn btn-primary" disabled>💾 提交修改</button>
        </div>

        <div id="messageArea"></div>

        <div class="table-container">
            <div class="table-wrapper">
                <div id="loadingArea" class="loading">
                    <p>正在加载数据...</p>
                </div>
                <table id="dataTable" style="display: none;">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>站点名称</th>
                            <th>地址</th>
                            <th>经度</th>
                            <th>纬度</th>
                            <th>站长姓名</th>
                            <th>联系电话</th>
                            <th>面试地点</th>
                            <th>面试联系人</th>
                            <th>面试联系电话</th>
                            <th>全职总计</th>
                            <th>分拣员</th>
                            <th>白班理货</th>
                            <th>水产专员</th>
                            <th>夜班理货</th>
                            <th>副站长</th>
                            <th>资深副站长</th>
                            <th>兼职总计</th>
                            <th>兼职-分拣员</th>
                            <th>兼职-白班理货</th>
                            <th>兼职-夜班理货</th>
                            <th>兼职-水产专员</th>
                        </tr>
                    </thead>
                    <tbody id="tableBody">
                    </tbody>
                </table>
            </div>
            <div class="status-bar">
                <span id="recordCount">总记录数: 0</span>
                <span id="modifiedCount">已修改: 0</span>
            </div>
        </div>
    </div>

    <script>
        class StationManager {
            constructor() {
                this.originalData = [];
                this.currentData = [];
                this.modifiedRows = new Set();
                this.init();
            }

            init() {
                this.bindEvents();
                this.loadData();
            }

            bindEvents() {
                document.getElementById('reloadBtn').addEventListener('click', () => {
                    this.loadData();
                });

                document.getElementById('refreshBtn').addEventListener('click', () => {
                    this.resetData();
                });

                document.getElementById('submitBtn').addEventListener('click', () => {
                    this.submitChanges();
                });
            }

            async loadData() {
                try {
                    this.showLoading(true);
                    const response = await fetch('/api/stations');
                    const result = await response.json();

                    if (result.success) {
                        this.originalData = result.data;
                        this.currentData = JSON.parse(JSON.stringify(result.data));
                        this.renderTable();
                        this.updateStatus();
                        this.showMessage('数据加载成功', 'success');
                    } else {
                        throw new Error(result.error);
                    }
                } catch (error) {
                    this.showMessage('加载数据失败: ' + error.message, 'error');
                } finally {
                    this.showLoading(false);
                }
            }

            renderTable() {
                const tbody = document.getElementById('tableBody');
                tbody.innerHTML = '';

                this.currentData.forEach((row, index) => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${row.id}</td>
                        <td><input type="text" class="editable" data-field="station_name" data-index="${index}" value="${this.escapeHtml(row.station_name || '')}"></td>
                        <td><input type="text" class="editable" data-field="address" data-index="${index}" value="${this.escapeHtml(row.address || '')}"></td>
                        <td><input type="number" step="any" class="editable" data-field="longitude" data-index="${index}" value="${row.longitude || ''}"></td>
                        <td><input type="number" step="any" class="editable" data-field="latitude" data-index="${index}" value="${row.latitude || ''}"></td>
                        <td><input type="text" class="editable" data-field="manager_name" data-index="${index}" value="${this.escapeHtml(row.manager_name || '')}"></td>
                        <td><input type="text" class="editable" data-field="contact_phone" data-index="${index}" value="${this.escapeHtml(row.contact_phone || '')}"></td>
                        <td><input type="text" class="editable" data-field="interview_location" data-index="${index}" value="${this.escapeHtml(row.interview_location || '')}"></td>
                        <td><input type="text" class="editable" data-field="interview_contact_person" data-index="${index}" value="${this.escapeHtml(row.interview_contact_person || '')}"></td>
                        <td><input type="text" class="editable" data-field="interview_contact_phone" data-index="${index}" value="${this.escapeHtml(row.interview_contact_phone || '')}"></td>
                        <td><input type="number" class="editable" data-field="fulltime_total" data-index="${index}" value="${row.fulltime_total || '0'}"></td>
                        <td><input type="number" class="editable" data-field="sorter" data-index="${index}" value="${row.sorter || '0'}"></td>
                        <td><input type="number" class="editable" data-field="day_handler" data-index="${index}" value="${row.day_handler || '0'}"></td>
                        <td><input type="number" class="editable" data-field="aquatic_specialist" data-index="${index}" value="${row.aquatic_specialist || '0'}"></td>
                        <td><input type="number" class="editable" data-field="night_handler" data-index="${index}" value="${row.night_handler || '0'}"></td>
                        <td><input type="number" class="editable" data-field="deputy_manager" data-index="${index}" value="${row.deputy_manager || '0'}"></td>
                        <td><input type="number" class="editable" data-field="senior_deputy_manager" data-index="${index}" value="${row.senior_deputy_manager || '0'}"></td>
                        <td><input type="number" class="editable" data-field="parttime_total" data-index="${index}" value="${row.parttime_total || '0'}"></td>
                        <td><input type="number" class="editable" data-field="parttime_sorter" data-index="${index}" value="${row.parttime_sorter || '0'}"></td>
                        <td><input type="number" class="editable" data-field="parttime_day_handler" data-index="${index}" value="${row.parttime_day_handler || '0'}"></td>
                        <td><input type="number" class="editable" data-field="parttime_night_handler" data-index="${index}" value="${row.parttime_night_handler || '0'}"></td>
                        <td><input type="number" class="editable" data-field="parttime_aquatic_specialist" data-index="${index}" value="${row.parttime_aquatic_specialist || '0'}"></td>
                    `;
                    tbody.appendChild(tr);
                });

                // 绑定输入事件
                document.querySelectorAll('.editable').forEach(input => {
                    input.addEventListener('input', (e) => {
                        this.handleInputChange(e);
                    });
                });

                document.getElementById('dataTable').style.display = 'table';
            }

            handleInputChange(event) {
                const input = event.target;
                const index = parseInt(input.dataset.index);
                const field = input.dataset.field;
                const newValue = input.value;

                // 更新当前数据
                this.currentData[index][field] = newValue;

                // 检查是否与原始数据不同
                const originalValue = this.originalData[index][field] || '';
                const isModified = newValue !== originalValue;

                if (isModified) {
                    input.classList.add('modified');
                    this.modifiedRows.add(index);
                } else {
                    input.classList.remove('modified');
                    // 检查该行是否还有其他修改
                    const rowHasModifications = this.checkRowModifications(index);
                    if (!rowHasModifications) {
                        this.modifiedRows.delete(index);
                    }
                }

                this.updateStatus();
            }

            checkRowModifications(index) {
                const fields = [
                    'station_name', 'address', 'longitude', 'latitude', 'manager_name',
                    'contact_phone', 'interview_location', 'interview_contact_person',
                    'interview_contact_phone', 'fulltime_total', 'sorter', 'day_handler',
                    'aquatic_specialist', 'night_handler', 'deputy_manager', 'senior_deputy_manager',
                    'parttime_total', 'parttime_sorter', 'parttime_day_handler',
                    'parttime_night_handler', 'parttime_aquatic_specialist'
                ];

                return fields.some(field => {
                    const currentValue = this.currentData[index][field] || '';
                    const originalValue = this.originalData[index][field] || '';
                    return currentValue !== originalValue;
                });
            }

            async submitChanges() {
                if (this.modifiedRows.size === 0) {
                    this.showMessage('没有需要提交的修改', 'error');
                    return;
                }

                try {
                    document.getElementById('submitBtn').disabled = true;

                    const updates = Array.from(this.modifiedRows).map(index => {
                        return {
                            id: this.currentData[index].id,
                            ...this.currentData[index]
                        };
                    });

                    const response = await fetch('/api/stations/batch', {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ updates })
                    });

                    const result = await response.json();

                    if (result.success) {
                        this.showMessage(result.message, 'success');
                        // 重新加载数据以确保同步
                        await this.loadData();
                        this.modifiedRows.clear();
                    } else {
                        throw new Error(result.error);
                    }
                } catch (error) {
                    this.showMessage('提交失败: ' + error.message, 'error');
                } finally {
                    document.getElementById('submitBtn').disabled = false;
                }
            }

            resetData() {
                this.currentData = JSON.parse(JSON.stringify(this.originalData));
                this.modifiedRows.clear();
                this.renderTable();
                this.updateStatus();
                this.showMessage('数据已重置', 'success');
            }

            updateStatus() {
                document.getElementById('recordCount').textContent = `总记录数: ${this.currentData.length}`;
                document.getElementById('modifiedCount').textContent = `已修改: ${this.modifiedRows.size}`;
                document.getElementById('submitBtn').disabled = this.modifiedRows.size === 0;
            }

            showLoading(show) {
                document.getElementById('loadingArea').style.display = show ? 'block' : 'none';
                document.getElementById('dataTable').style.display = show ? 'none' : 'table';
            }

            showMessage(message, type) {
                const messageArea = document.getElementById('messageArea');
                messageArea.innerHTML = `<div class="${type}">${message}</div>`;
                setTimeout(() => {
                    messageArea.innerHTML = '';
                }, 5000);
            }

            escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
        }

        // 页面加载完成后初始化
        document.addEventListener('DOMContentLoaded', () => {
            new StationManager();
        });
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    # 检查数据库文件是否存在
    if not os.path.exists(DB_FILE):
        print(f"错误: 数据库文件 {DB_FILE} 不存在")
        print("请先运行 database_setup.py 创建数据库")
        exit(1)
    
    print(f"启动Web服务器...")
    print(f"数据库文件: {DB_FILE}")
    print(f"访问地址: http://localhost:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
