#!/usr/bin/env python3
"""
Web服务器 - 为H5控制面板提供API接口
提供岗位属性数据的CRUD操作
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
    """返回岗位管理控制面板页面"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    """获取所有岗位数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id, job_type, recruiting_unit, city, gender, age_requirement,
                special_requirements, accept_criminal_record, location, 
                longitude, latitude, urgent_capacity, working_hours,
                relevant_experience, full_time, salary, job_content,
                interview_time, trial_time, currently_recruiting,
                insurance_status, accommodation_status
            FROM job_positions 
            ORDER BY id
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        # 转换为字典列表
        jobs = []
        for row in rows:
            job_dict = {
                'id': row['id'],
                'job_type': row['job_type'],
                'recruiting_unit': row['recruiting_unit'],
                'city': row['city'],
                'gender': row['gender'],
                'age_requirement': row['age_requirement'],
                'special_requirements': row['special_requirements'],
                'accept_criminal_record': row['accept_criminal_record'],
                'location': row['location'],
                'longitude': row['longitude'],
                'latitude': row['latitude'],
                'urgent_capacity': row['urgent_capacity'],
                'working_hours': row['working_hours'],
                'relevant_experience': row['relevant_experience'],
                'full_time': row['full_time'],
                'salary': row['salary'],
                'job_content': row['job_content'],
                'interview_time': row['interview_time'],
                'trial_time': row['trial_time'],
                'currently_recruiting': row['currently_recruiting'],
                'insurance_status': row['insurance_status'],
                'accommodation_status': row['accommodation_status']
            }
            jobs.append(job_dict)
        
        return jsonify({
            'success': True,
            'data': jobs,
            'count': len(jobs)
        })
        
    except sqlite3.Error as e:
        return jsonify({
            'success': False,
            'error': f'数据库错误: {e}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'服务器错误: {e}'
        }), 500

@app.route('/api/jobs', methods=['POST'])
def create_job():
    """创建新岗位"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '没有提供数据'
            }), 400
        
        # 验证必填字段
        required_fields = ['job_type', 'recruiting_unit']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'缺少必填字段: {field}'
                }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 定义所有字段
        all_fields = [
            'job_type', 'recruiting_unit', 'city', 'gender', 'age_requirement',
            'special_requirements', 'accept_criminal_record', 'location',
            'longitude', 'latitude', 'urgent_capacity', 'working_hours',
            'relevant_experience', 'full_time', 'salary', 'job_content',
            'interview_time', 'trial_time', 'currently_recruiting',
            'insurance_status', 'accommodation_status'
        ]
        
        # 构建插入SQL
        insert_fields = []
        placeholders = []
        values = []
        
        for field in all_fields:
            insert_fields.append(field)
            placeholders.append('?')
            # 设置默认值
            if field == 'currently_recruiting':
                values.append(data.get(field, '是'))
            elif field == 'urgent_capacity':
                values.append(data.get(field, 0))
            elif field in ['longitude', 'latitude']:
                values.append(data.get(field, None))
            else:
                values.append(data.get(field, ''))
        
        insert_sql = f"""
            INSERT INTO job_positions ({', '.join(insert_fields)})
            VALUES ({', '.join(placeholders)})
        """
        
        cursor.execute(insert_sql, values)
        new_job_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'成功创建新岗位，ID: {new_job_id}',
            'job_id': new_job_id
        })
        
    except sqlite3.Error as e:
        return jsonify({
            'success': False,
            'error': f'数据库错误: {e}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'服务器错误: {e}'
        }), 500

@app.route('/api/jobs/search', methods=['GET'])
def search_jobs():
    """搜索岗位"""
    try:
        # 获取搜索参数
        recruiting_unit = request.args.get('recruiting_unit', '').strip()
        job_type = request.args.get('job_type', '').strip()
        city = request.args.get('city', '').strip()
        
        if not recruiting_unit and not job_type and not city:
            return jsonify({
                'success': False,
                'error': '请提供至少一个搜索条件'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 构建搜索条件
        where_conditions = []
        params = []
        
        if recruiting_unit:
            where_conditions.append("recruiting_unit LIKE ?")
            params.append(f"%{recruiting_unit}%")
            
        if job_type:
            where_conditions.append("job_type LIKE ?")
            params.append(f"%{job_type}%")
            
        if city:
            where_conditions.append("city LIKE ?")
            params.append(f"%{city}%")
        
        query = f"""
            SELECT 
                id, job_type, recruiting_unit, city, gender, age_requirement,
                special_requirements, accept_criminal_record, location, 
                longitude, latitude, urgent_capacity, working_hours,
                relevant_experience, full_time, salary, job_content,
                interview_time, trial_time, currently_recruiting,
                insurance_status, accommodation_status
            FROM job_positions 
            WHERE {' AND '.join(where_conditions)}
            ORDER BY urgent_capacity DESC, job_type ASC, recruiting_unit ASC
        """
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        # 转换为字典列表
        jobs = []
        for row in rows:
            job_dict = {
                'id': row['id'],
                'job_type': row['job_type'],
                'recruiting_unit': row['recruiting_unit'],
                'city': row['city'],
                'gender': row['gender'],
                'age_requirement': row['age_requirement'],
                'special_requirements': row['special_requirements'],
                'accept_criminal_record': row['accept_criminal_record'],
                'location': row['location'],
                'longitude': row['longitude'],
                'latitude': row['latitude'],
                'urgent_capacity': row['urgent_capacity'],
                'working_hours': row['working_hours'],
                'relevant_experience': row['relevant_experience'],
                'full_time': row['full_time'],
                'salary': row['salary'],
                'job_content': row['job_content'],
                'interview_time': row['interview_time'],
                'trial_time': row['trial_time'],
                'currently_recruiting': row['currently_recruiting'],
                'insurance_status': row['insurance_status'],
                'accommodation_status': row['accommodation_status']
            }
            jobs.append(job_dict)
        
        return jsonify({
            'success': True,
            'data': jobs,
            'count': len(jobs),
            'search_params': {
                'recruiting_unit': recruiting_unit,
                'job_type': job_type,
                'city': city
            }
        })
        
    except sqlite3.Error as e:
        return jsonify({
            'success': False,
            'error': f'数据库错误: {e}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'服务器错误: {e}'
        }), 500

@app.route('/api/jobs/<int:job_id>', methods=['PUT'])
def update_job(job_id):
    """更新单个岗位信息"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '没有提供数据'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 构建更新SQL
        update_fields = []
        params = []
        
        # 定义可更新的字段
        updatable_fields = [
            'job_type', 'recruiting_unit', 'city', 'gender', 'age_requirement',
            'special_requirements', 'accept_criminal_record', 'location',
            'longitude', 'latitude', 'urgent_capacity', 'working_hours',
            'relevant_experience', 'full_time', 'salary', 'job_content',
            'interview_time', 'trial_time', 'currently_recruiting',
            'insurance_status', 'accommodation_status'
        ]
        
        for field in updatable_fields:
            if field in data:
                update_fields.append(f"{field} = ?")
                params.append(data[field])
        
        if not update_fields:
            return jsonify({
                'success': False,
                'error': '没有提供有效的更新字段'
            }), 400
        
        params.append(job_id)
        
        update_sql = f"""
            UPDATE job_positions 
            SET {', '.join(update_fields)}
            WHERE id = ?
        """
        
        cursor.execute(update_sql, params)
        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({
                'success': False,
                'error': f'未找到ID为{job_id}的岗位'
            }), 404
        
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'岗位 {job_id} 更新成功'
        })
        
    except sqlite3.Error as e:
        return jsonify({
            'success': False,
            'error': f'数据库错误: {e}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'服务器错误: {e}'
        }), 500

@app.route('/api/jobs/batch', methods=['PUT'])
def batch_update_jobs():
    """批量更新岗位信息"""
    try:
        data = request.get_json()
        if not data or 'updates' not in data:
            return jsonify({
                'success': False,
                'error': '没有提供更新数据'
            }), 400
        
        updates = data['updates']
        if not isinstance(updates, list) or len(updates) == 0:
            return jsonify({
                'success': False,
                'error': '更新数据格式不正确'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        updated_count = 0
        
        # 定义可更新的字段
        updatable_fields = [
            'job_type', 'recruiting_unit', 'city', 'gender', 'age_requirement',
            'special_requirements', 'accept_criminal_record', 'location',
            'longitude', 'latitude', 'urgent_capacity', 'working_hours',
            'relevant_experience', 'full_time', 'salary', 'job_content',
            'interview_time', 'trial_time', 'currently_recruiting',
            'insurance_status', 'accommodation_status'
        ]
        
        for update_item in updates:
            if 'id' not in update_item:
                continue
            
            job_id = update_item['id']
            
            # 构建更新SQL
            update_fields = []
            params = []
            
            for field in updatable_fields:
                if field in update_item:
                    update_fields.append(f"{field} = ?")
                    params.append(update_item[field])
            
            if update_fields:
                params.append(job_id)
                
                update_sql = f"""
                    UPDATE job_positions 
                    SET {', '.join(update_fields)}
                    WHERE id = ?
                """
                
                cursor.execute(update_sql, params)
                if cursor.rowcount > 0:
                    updated_count += 1
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'成功更新 {updated_count} 个岗位',
            'updated_count': updated_count
        })
        
    except sqlite3.Error as e:
        return jsonify({
            'success': False,
            'error': f'数据库错误: {e}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'服务器错误: {e}'
        }), 500

# HTML模板 - 完整的H5岗位管理控制面板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>岗位管理控制面板</title>
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
            flex-direction: column;
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .search-section {
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
        }
        
        .action-section {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }
        
        .search-input {
            padding: 10px 15px;
            border: 2px solid #e9ecef;
            border-radius: 6px;
            font-size: 14px;
            min-width: 200px;
            flex: 1;
            max-width: 300px;
        }
        
        .search-input:focus {
            outline: none;
            border-color: #4a90e2;
            box-shadow: 0 0 0 2px rgba(74, 144, 226, 0.2);
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

        .btn-success {
            background-color: #28a745;
            color: white;
            border: 1px solid #28a745;
        }

        .btn-success:hover {
            background-color: #218838;
            border-color: #218838;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(40, 167, 69, 0.3);
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
            font-size: 12px;
        }

        th {
            background-color: #4a90e2;
            color: white;
            padding: 10px 8px;
            text-align: left;
            font-weight: 600;
            position: sticky;
            top: 0;
            z-index: 10;
            white-space: nowrap;
            border-bottom: 2px solid #357abd;
            font-size: 11px;
        }

        td {
            padding: 8px 6px;
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
            font-size: 11px;
            font-family: inherit;
            resize: vertical;
        }
        
        .editable[type="text"], .editable[type="number"] {
            min-width: 100px;
        }
        
        .editable textarea {
            min-height: 50px;
            min-width: 150px;
        }
        
        .editable select {
            min-width: 80px;
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
                font-size: 1.2rem;
            }

            .search-section, .action-section {
                flex-direction: column;
            }

            .btn {
                width: 100%;
            }
            
            .search-input {
                min-width: 100%;
                max-width: 100%;
            }

            table {
                font-size: 10px;
            }

            th, td {
                padding: 6px 4px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>岗位管理控制面板</h1>
        </div>

        <div class="controls">
            <div class="search-section">
                <input type="text" id="searchInput" placeholder="搜索招聘单位..." class="search-input">
                <button id="searchBtn" class="btn btn-secondary">🔍 搜索</button>
                <button id="clearSearchBtn" class="btn btn-secondary">❌ 清除</button>
            </div>
            <div class="action-section">
                <button id="addJobBtn" class="btn btn-success">➕ 新增岗位</button>
                <button id="reloadBtn" class="btn btn-secondary">🔄 刷新数据</button>
                <button id="refreshBtn" class="btn btn-secondary">🔄 重置数据</button>
                <button id="submitBtn" class="btn btn-primary" disabled>💾 提交修改</button>
            </div>
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
                            <th>岗位类型</th>
                            <th>招聘单位</th>
                            <th>城市</th>
                            <th>性别要求</th>
                            <th>年龄要求</th>
                            <th>特殊要求</th>
                            <th>接受犯罪记录</th>
                            <th>工作地点</th>
                            <th>经度</th>
                            <th>纬度</th>
                            <th>紧急程度</th>
                            <th>工作时间</th>
                            <th>相关经验</th>
                            <th>全职</th>
                            <th>薪资</th>
                            <th>工作内容</th>
                            <th>面试时间</th>
                            <th>试岗时间</th>
                            <th>当前招聘</th>
                            <th>保险情况</th>
                            <th>吃住情况</th>
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
        class JobManager {
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
                
                document.getElementById('addJobBtn').addEventListener('click', () => {
                    this.addNewJob();
                });
                
                document.getElementById('searchBtn').addEventListener('click', () => {
                    this.searchJobs();
                });
                
                document.getElementById('clearSearchBtn').addEventListener('click', () => {
                    this.clearSearch();
                });
                
                // 搜索框回车事件
                document.getElementById('searchInput').addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        this.searchJobs();
                    }
                });
            }

            async loadData() {
                try {
                    this.showLoading(true);
                    const response = await fetch('/api/jobs');
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
                        <td><input type="text" class="editable" data-field="job_type" data-index="${index}" value="${this.escapeHtml(row.job_type || '')}"></td>
                        <td><input type="text" class="editable" data-field="recruiting_unit" data-index="${index}" value="${this.escapeHtml(row.recruiting_unit || '')}"></td>
                        <td><input type="text" class="editable" data-field="city" data-index="${index}" value="${this.escapeHtml(row.city || '')}"></td>
                        <td><select class="editable" data-field="gender" data-index="${index}">
                            <option value="男" ${row.gender === '男' ? 'selected' : ''}>男</option>
                            <option value="女" ${row.gender === '女' ? 'selected' : ''}>女</option>
                            <option value="不限" ${row.gender === '不限' ? 'selected' : ''}>不限</option>
                        </select></td>
                        <td><input type="text" class="editable" data-field="age_requirement" data-index="${index}" value="${this.escapeHtml(row.age_requirement || '')}"></td>
                        <td><textarea class="editable" data-field="special_requirements" data-index="${index}" rows="2">${this.escapeHtml(row.special_requirements || '')}</textarea></td>
                        <td><select class="editable" data-field="accept_criminal_record" data-index="${index}">
                            <option value="是" ${row.accept_criminal_record === '是' ? 'selected' : ''}>是</option>
                            <option value="否" ${row.accept_criminal_record === '否' ? 'selected' : ''}>否</option>
                        </select></td>
                        <td><textarea class="editable" data-field="location" data-index="${index}" rows="2">${this.escapeHtml(row.location || '')}</textarea></td>
                        <td><input type="number" step="any" class="editable" data-field="longitude" data-index="${index}" value="${row.longitude || ''}"></td>
                        <td><input type="number" step="any" class="editable" data-field="latitude" data-index="${index}" value="${row.latitude || ''}"></td>
                        <td><select class="editable" data-field="urgent_capacity" data-index="${index}">
                            <option value="0" ${row.urgent_capacity === 0 ? 'selected' : ''}>普通</option>
                            <option value="1" ${row.urgent_capacity === 1 ? 'selected' : ''}>紧急</option>
                        </select></td>
                        <td><textarea class="editable" data-field="working_hours" data-index="${index}" rows="2">${this.escapeHtml(row.working_hours || '')}</textarea></td>
                        <td><input type="text" class="editable" data-field="relevant_experience" data-index="${index}" value="${this.escapeHtml(row.relevant_experience || '')}"></td>
                        <td><select class="editable" data-field="full_time" data-index="${index}">
                            <option value="是" ${row.full_time === '是' ? 'selected' : ''}>是</option>
                            <option value="否" ${row.full_time === '否' ? 'selected' : ''}>否</option>
                        </select></td>
                        <td><textarea class="editable" data-field="salary" data-index="${index}" rows="2">${this.escapeHtml(row.salary || '')}</textarea></td>
                        <td><textarea class="editable" data-field="job_content" data-index="${index}" rows="3">${this.escapeHtml(row.job_content || '')}</textarea></td>
                        <td><input type="text" class="editable" data-field="interview_time" data-index="${index}" value="${this.escapeHtml(row.interview_time || '')}"></td>
                        <td><input type="text" class="editable" data-field="trial_time" data-index="${index}" value="${this.escapeHtml(row.trial_time || '')}"></td>
                        <td><select class="editable" data-field="currently_recruiting" data-index="${index}">
                            <option value="是" ${row.currently_recruiting === '是' ? 'selected' : ''}>是</option>
                            <option value="否" ${row.currently_recruiting === '否' ? 'selected' : ''}>否</option>
                        </select></td>
                        <td><input type="text" class="editable" data-field="insurance_status" data-index="${index}" value="${this.escapeHtml(row.insurance_status || '')}"></td>
                        <td><input type="text" class="editable" data-field="accommodation_status" data-index="${index}" value="${this.escapeHtml(row.accommodation_status || '')}"></td>
                    `;
                    tbody.appendChild(tr);
                });

                // 绑定输入事件
                document.querySelectorAll('.editable').forEach(element => {
                    // 为不同类型的元素绑定合适的事件
                    if (element.tagName === 'SELECT') {
                        element.addEventListener('change', (e) => {
                            this.handleInputChange(e);
                        });
                    } else {
                        element.addEventListener('input', (e) => {
                            this.handleInputChange(e);
                        });
                    }
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
                    'job_type', 'recruiting_unit', 'city', 'gender', 'age_requirement',
                    'special_requirements', 'accept_criminal_record', 'location',
                    'longitude', 'latitude', 'urgent_capacity', 'working_hours',
                    'relevant_experience', 'full_time', 'salary', 'job_content',
                    'interview_time', 'trial_time', 'currently_recruiting',
                    'insurance_status', 'accommodation_status'
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

                    const response = await fetch('/api/jobs/batch', {
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

            async addNewJob() {
                try {
                    // 创建新岗位的默认数据
                    const newJobData = {
                        job_type: '新岗位',
                        recruiting_unit: '请输入招聘单位',
                        city: '',
                        gender: '不限',
                        age_requirement: '',
                        special_requirements: '',
                        accept_criminal_record: '否',
                        location: '',
                        longitude: null,
                        latitude: null,
                        urgent_capacity: 0,
                        working_hours: '',
                        relevant_experience: '',
                        full_time: '是',
                        salary: '',
                        job_content: '',
                        interview_time: '',
                        trial_time: '',
                        currently_recruiting: '是',
                        insurance_status: '',
                        accommodation_status: ''
                    };
                    
                    const response = await fetch('/api/jobs', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(newJobData)
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        this.showMessage(`成功创建新岗位，ID: ${result.job_id}`, 'success');
                        // 重新加载数据以显示新岗位
                        await this.loadData();
                    } else {
                        throw new Error(result.error);
                    }
                } catch (error) {
                    this.showMessage('创建新岗位失败: ' + error.message, 'error');
                }
            }
            
            async searchJobs() {
                const searchTerm = document.getElementById('searchInput').value.trim();
                if (!searchTerm) {
                    this.showMessage('请输入搜索关键词', 'error');
                    return;
                }
                
                try {
                    this.showLoading(true);
                    const response = await fetch(`/api/jobs/search?recruiting_unit=${encodeURIComponent(searchTerm)}`);
                    const result = await response.json();
                    
                    if (result.success) {
                        this.originalData = result.data;
                        this.currentData = JSON.parse(JSON.stringify(result.data));
                        this.renderTable();
                        this.updateStatus();
                        this.showMessage(`搜索完成，找到 ${result.count} 个岗位`, 'success');
                    } else {
                        throw new Error(result.error);
                    }
                } catch (error) {
                    this.showMessage('搜索失败: ' + error.message, 'error');
                } finally {
                    this.showLoading(false);
                }
            }
            
            clearSearch() {
                document.getElementById('searchInput').value = '';
                this.loadData(); // 重新加载所有数据
                this.showMessage('已清除搜索条件', 'success');
            }

            escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
        }

        // 页面加载完成后初始化
        document.addEventListener('DOMContentLoaded', () => {
            new JobManager();
        });
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    # 检查数据库文件是否存在
    if not os.path.exists(DB_FILE):
        print(f"错误: 数据库文件不存在: {DB_FILE}")
        print("请先运行 database_setup.py 创建数据库")
        exit(1)
    
    print(f"启动岗位管理Web服务器...")
    print(f"数据库文件: {DB_FILE}")
    print(f"访问地址: http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
