#!/usr/bin/env python3
"""
Web服务器 - 为H5控制面板提供API接口
提供岗位属性数据的CRUD操作
"""

from flask import Flask, jsonify, request, render_template_string, redirect, url_for
from flask_cors import CORS
import sqlite3
import os
import json
import pandas as pd
import pymysql
import uuid
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from werkzeug.utils import secure_filename
from contextlib import AsyncExitStack
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
import logging

# 获取脚本所在目录的绝对路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 构造数据库文件的绝对路径，优先使用data目录中的数据库
DATA_DB_FILE = os.path.join(SCRIPT_DIR, 'data', 'stations.db')
ROOT_DB_FILE = os.path.join(SCRIPT_DIR, 'stations.db')

# 选择存在的数据库文件（优先data目录，兼容Docker环境）
DB_FILE = DATA_DB_FILE if os.path.exists(DATA_DB_FILE) else ROOT_DB_FILE

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 文件上传配置
UPLOAD_FOLDER = os.path.join(SCRIPT_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit

# 确保上传文件夹存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 简历导入相关配置
RESUME_DATABASE_CONFIG = {
    "host": "bj-cynosdbmysql-grp-5eypnf9y.sql.tencentcdb.com",
    "port": 26606,
    "user": "root",
    "password": "Gn123456",
    "database": "recruit-db_bak",
    "charset": "utf8mb4"
}

# MCP服务器配置
MCP_CONFIG = {
    "url": "http://152.136.8.68:3001/mcp",
    "headers": {},
    "timeout": 50
}

# 默认岗位ID (可以通过页面配置)
DEFAULT_JOB_ID = "fd9d46ec-1f06-4504-a034-122347e92239"

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局进度存储
progress_store = {}

def get_db_connection():
    """创建数据库连接"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_mysql_connection():
    """创建MySQL数据库连接"""
    try:
        connection = pymysql.connect(**RESUME_DATABASE_CONFIG)
        return connection
    except Exception as e:
        logger.error(f"MySQL连接失败: {e}")
        raise

async def connect_to_mcp_server():
    """连接到MCP服务器"""
    try:
        logger.info(f"正在连接到MCP服务器: {MCP_CONFIG['url']}")

        streams_context = streamablehttp_client(
            url=MCP_CONFIG['url'],
            headers=MCP_CONFIG['headers'],
        )
        read_stream, write_stream, _ = await streams_context.__aenter__()

        session_context = ClientSession(read_stream, write_stream)
        session = await session_context.__aenter__()

        await session.initialize()
        logger.info("成功连接到MCP服务器")

        return session, session_context, streams_context

    except Exception as e:
        logger.error(f"连接MCP服务器失败: {e}")
        raise

def map_excel_to_resume(row: pd.Series) -> Dict[str, Any]:
    """将Excel行数据映射到简历表字段"""
    resume_data = {
        'id': str(uuid.uuid4()),
        'name': str(row.get('姓名', '')).strip(),
        'phone': str(row.get('手机号', '')).strip() if pd.notna(row.get('手机号')) else None,
        'wechat': str(row.get('微信号', '')).strip() if pd.notna(row.get('微信号')) else None,
        'source': 'INTERNAL',
        'deleted': 0,
        'create_time': datetime.now(),
        'update_time': datetime.now()
    }

    # 处理年龄字段
    if pd.notna(row.get('年龄')):
        age_str = str(row.get('年龄')).strip()
        if '~' in age_str and '岁' in age_str:
            try:
                age_parts = age_str.replace('岁', '').split('~')
                if len(age_parts) == 2:
                    min_age = int(age_parts[0])
                    max_age = int(age_parts[1])
                    avg_age = (min_age + max_age) // 2
                    resume_data['age'] = f"{avg_age}岁"
                else:
                    resume_data['age'] = age_str
            except (ValueError, IndexError):
                resume_data['age'] = age_str
        else:
            resume_data['age'] = age_str

    # 处理期望地点
    location = None
    if pd.notna(row.get('居住城市')):
        location = str(row.get('居住城市')).strip()
    elif pd.notna(row.get('工作城市')):
        location = str(row.get('工作城市')).strip()

    if location:
        resume_data['expect_location'] = location

    # 处理应聘岗位
    if pd.notna(row.get('应聘岗位')):
        position = str(row.get('应聘岗位')).strip()
        expect_positions = [position]
        resume_data['expect_positions'] = json.dumps(expect_positions, ensure_ascii=False)

    resume_data['external_id'] = None
    resume_data['experience'] = '不限'

    return resume_data

def validate_resume_data(resume_data: Dict[str, Any]) -> bool:
    """验证简历数据"""
    if not resume_data.get('name'):
        return False
    if not resume_data.get('phone'):
        return False
    return True

@app.route('/health')
def health_check():
    """健康检查端点"""
    try:
        # 检查数据库连接
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()

        return jsonify({
            'status': 'healthy',
            'service': 'web_server',
            'database': 'connected',
            'timestamp': str(datetime.now())
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'service': 'web_server',
            'error': str(e),
            'timestamp': str(datetime.now())
        }), 503

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

@app.route('/resume-import')
def resume_import_page():
    """返回简历导入页面"""
    return render_template_string(RESUME_IMPORT_HTML_TEMPLATE)

@app.route('/api/resume-import', methods=['POST'])
def upload_and_process_resume():
    """处理简历文件上传和导入流程"""
    try:
        # 检查是否有文件上传
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '没有选择文件'
            }), 400

        file = request.files['file']
        job_id = request.form.get('job_id', DEFAULT_JOB_ID)

        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '没有选择文件'
            }), 400

        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': '不支持的文件格式，请上传.xlsx或.xls文件'
            }), 400

        # 保存上传的文件
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # 返回任务ID，让前端通过SSE获取进度
        task_id = timestamp

        # 在后台启动处理任务
        import threading
        def background_task():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    process_resume_import_workflow_with_progress(filepath, job_id, task_id)
                )
            finally:
                loop.close()
                # 清理上传的文件
                if os.path.exists(filepath):
                    os.remove(filepath)

        thread = threading.Thread(target=background_task)
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': '任务已开始，请通过SSE获取进度'
        })

    except Exception as e:
        logger.error(f"简历导入处理失败: {e}")
        return jsonify({
            'success': False,
            'error': f'处理失败: {str(e)}'
        }), 500

@app.route('/api/resume-import/progress/<task_id>')
def get_import_progress(task_id):
    """通过SSE推送处理进度"""
    def generate_progress():
        """生成进度事件流"""
        try:
            # 检查任务是否存在
            if task_id not in progress_store:
                yield f"data: {json.dumps({'error': '任务不存在'})}\n\n"
                return

            # 持续推送进度更新
            last_step = None
            while True:
                progress_data = progress_store.get(task_id, {})

                if not progress_data:
                    time.sleep(1)
                    continue

                # 发送进度更新
                yield f"data: {json.dumps(progress_data)}\n\n"

                # 如果任务完成，结束流
                if progress_data.get('completed', False):
                    # 清理进度数据
                    if task_id in progress_store:
                        del progress_store[task_id]
                    break

                time.sleep(1)  # 每秒检查一次

        except Exception as e:
            logger.error(f"SSE进度推送错误: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return app.response_class(
        generate_progress(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Cache-Control'
        }
    )

async def process_resume_import_workflow_with_progress(filepath: str, job_id: str, task_id: str) -> Dict[str, Any]:
    """处理完整的简历导入工作流程（带进度推送）"""
    # 初始化进度存储
    progress_store[task_id] = {
        'success': False,
        'completed': False,
        'current_step': 1,
        'steps': {
            'import_resumes': {'completed': False, 'success': False, 'message': '等待开始...', 'data': {}},
            'add_wechat': {'completed': False, 'success': False, 'message': '等待开始...', 'data': {}},
            'add_waihu': {'completed': False, 'success': False, 'message': '等待开始...', 'data': {}}
        },
        'summary': {}
    }

    try:
        # 步骤1: 导入简历到数据库
        logger.info("开始步骤1: 导入简历到数据库")
        progress_store[task_id]['current_step'] = 1
        progress_store[task_id]['steps']['import_resumes']['message'] = '正在导入简历到数据库...'

        import_result = await import_resumes_to_database(filepath)
        progress_store[task_id]['steps']['import_resumes'] = import_result

        if not import_result['success']:
            progress_store[task_id]['summary'] = {'message': '简历导入失败，流程终止', 'total_processed': 0}
            progress_store[task_id]['completed'] = True
            return

        successful_resume_ids = import_result['data'].get('successful_ids', [])
        if not successful_resume_ids:
            progress_store[task_id]['summary'] = {'message': '没有成功导入的简历，流程终止', 'total_processed': 0}
            progress_store[task_id]['completed'] = True
            return

        # 步骤2: 添加微信联系人
        logger.info("开始步骤2: 添加微信联系人")
        progress_store[task_id]['current_step'] = 2
        progress_store[task_id]['steps']['add_wechat']['message'] = '正在添加微信联系人...'

        wechat_result = await add_wechat_contacts_from_excel(filepath)
        progress_store[task_id]['steps']['add_wechat'] = wechat_result

        # 步骤3: 添加外呼任务
        logger.info("开始步骤3: 添加外呼任务")
        progress_store[task_id]['current_step'] = 3
        progress_store[task_id]['steps']['add_waihu']['message'] = '正在创建外呼任务...'

        waihu_result = await add_waihu_tasks_for_resumes(filepath, successful_resume_ids, job_id)
        progress_store[task_id]['steps']['add_waihu'] = waihu_result

        # 生成总结
        total_processed = len(successful_resume_ids)
        wechat_success = wechat_result['data'].get('success_count', 0)
        waihu_success = waihu_result['data'].get('success_count', 0)

        progress_store[task_id]['success'] = True
        progress_store[task_id]['completed'] = True
        progress_store[task_id]['summary'] = {
            'message': f'工作流程完成',
            'total_processed': total_processed,
            'resume_imported': total_processed,
            'wechat_added': wechat_success,
            'waihu_created': waihu_success
        }

    except Exception as e:
        logger.error(f"简历导入工作流程失败: {e}")
        progress_store[task_id]['summary'] = {'message': f'工作流程失败: {str(e)}', 'total_processed': 0}
        progress_store[task_id]['completed'] = True

async def process_resume_import_workflow(filepath: str, job_id: str) -> Dict[str, Any]:
    """处理完整的简历导入工作流程"""
    workflow_results = {
        'success': False,
        'steps': {
            'import_resumes': {'completed': False, 'success': False, 'message': '', 'data': {}},
            'add_wechat': {'completed': False, 'success': False, 'message': '', 'data': {}},
            'add_waihu': {'completed': False, 'success': False, 'message': '', 'data': {}}
        },
        'summary': {}
    }

    try:
        # 步骤1: 导入简历到数据库
        logger.info("开始步骤1: 导入简历到数据库")
        import_result = await import_resumes_to_database(filepath)
        workflow_results['steps']['import_resumes'] = import_result

        if not import_result['success']:
            workflow_results['summary'] = {'message': '简历导入失败，流程终止', 'total_processed': 0}
            return workflow_results

        successful_resume_ids = import_result['data'].get('successful_ids', [])
        if not successful_resume_ids:
            workflow_results['summary'] = {'message': '没有成功导入的简历，流程终止', 'total_processed': 0}
            return workflow_results

        # 步骤2: 添加微信联系人
        logger.info("开始步骤2: 添加微信联系人")
        wechat_result = await add_wechat_contacts_from_excel(filepath)
        workflow_results['steps']['add_wechat'] = wechat_result

        # 步骤3: 添加外呼任务
        logger.info("开始步骤3: 添加外呼任务")
        waihu_result = await add_waihu_tasks_for_resumes(filepath, successful_resume_ids, job_id)
        workflow_results['steps']['add_waihu'] = waihu_result

        # 生成总结
        total_processed = len(successful_resume_ids)
        wechat_success = wechat_result['data'].get('success_count', 0)
        waihu_success = waihu_result['data'].get('success_count', 0)

        workflow_results['success'] = True
        workflow_results['summary'] = {
            'message': f'工作流程完成',
            'total_processed': total_processed,
            'resume_imported': total_processed,
            'wechat_added': wechat_success,
            'waihu_created': waihu_success
        }

        return workflow_results

    except Exception as e:
        logger.error(f"简历导入工作流程失败: {e}")
        workflow_results['summary'] = {'message': f'工作流程失败: {str(e)}', 'total_processed': 0}
        return workflow_results

async def import_resumes_to_database(filepath: str) -> Dict[str, Any]:
    """导入简历到数据库"""
    try:
        # 读取Excel数据
        df = pd.read_excel(filepath)
        logger.info(f"读取Excel文件，共 {len(df)} 条记录")

        # 连接MySQL数据库
        connection = get_mysql_connection()

        successful_ids = []
        success_count = 0
        error_count = 0

        for index, row in df.iterrows():
            try:
                # 映射数据
                resume_data = map_excel_to_resume(row)

                # 验证数据
                if not validate_resume_data(resume_data):
                    error_count += 1
                    continue

                # 检查是否已存在
                existing_id = check_existing_resume_by_phone(connection, resume_data['phone'])

                if existing_id:
                    # 更新已存在的记录
                    if update_existing_resume(connection, existing_id, resume_data):
                        successful_ids.append(existing_id)
                        success_count += 1
                    else:
                        error_count += 1
                else:
                    # 插入新记录
                    if insert_new_resume(connection, resume_data):
                        successful_ids.append(resume_data['id'])
                        success_count += 1
                    else:
                        error_count += 1

            except Exception as e:
                logger.error(f"处理第 {index + 1} 行数据时出错: {e}")
                error_count += 1

        connection.close()

        return {
            'completed': True,
            'success': success_count > 0,
            'message': f'简历导入完成 - 成功: {success_count}, 失败: {error_count}',
            'data': {
                'successful_ids': successful_ids,
                'success_count': success_count,
                'error_count': error_count
            }
        }

    except Exception as e:
        logger.error(f"导入简历到数据库失败: {e}")
        return {
            'completed': True,
            'success': False,
            'message': f'导入简历失败: {str(e)}',
            'data': {}
        }

def check_existing_resume_by_phone(connection, phone: str) -> Optional[str]:
    """检查数据库中是否已存在相同手机号的简历"""
    try:
        cursor = connection.cursor()
        sql = "SELECT id FROM resume WHERE phone = %s AND deleted = 0"
        cursor.execute(sql, (phone,))
        result = cursor.fetchone()
        cursor.close()

        if result:
            return result[0]
        return None

    except Exception as e:
        logger.error(f"检查已存在简历失败: {e}")
        return None

def update_existing_resume(connection, existing_id: str, resume_data: Dict[str, Any]) -> bool:
    """更新已存在的简历记录"""
    try:
        cursor = connection.cursor()

        # 准备更新的字段，排除id和create_time
        update_fields = {}
        for key, value in resume_data.items():
            if key not in ['id', 'create_time']:
                update_fields[key] = value

        # 构建更新SQL
        set_clauses = []
        values = []
        for field, value in update_fields.items():
            set_clauses.append(f"`{field}` = %s")
            values.append(value)

        sql = f"UPDATE resume SET {', '.join(set_clauses)} WHERE id = %s"
        values.append(existing_id)

        cursor.execute(sql, values)
        connection.commit()
        cursor.close()

        logger.info(f"成功更新简历: {resume_data['name']} ({resume_data['phone']}) - ID: {existing_id}")
        return True

    except Exception as e:
        logger.error(f"更新简历失败: {resume_data.get('name', 'Unknown')} - {e}")
        connection.rollback()
        return False

def insert_new_resume(connection, resume_data: Dict[str, Any]) -> bool:
    """插入新的简历记录"""
    try:
        cursor = connection.cursor()

        # 构建插入SQL
        fields = list(resume_data.keys())
        placeholders = ', '.join(['%s'] * len(fields))
        field_names = ', '.join([f'`{field}`' for field in fields])

        sql = f"""
            INSERT INTO resume ({field_names})
            VALUES ({placeholders})
        """

        values = list(resume_data.values())
        cursor.execute(sql, values)
        connection.commit()
        cursor.close()

        logger.info(f"成功插入简历: {resume_data['name']} ({resume_data['phone']}) - ID: {resume_data['id']}")
        return True

    except Exception as e:
        logger.error(f"插入简历失败: {resume_data.get('name', 'Unknown')} - {e}")
        connection.rollback()
        return False

async def add_wechat_contacts_from_excel(filepath: str) -> Dict[str, Any]:
    """从Excel文件添加微信联系人"""
    try:
        # 连接到MCP服务器
        session, session_context, streams_context = await connect_to_mcp_server()

        # 读取Excel数据
        df = pd.read_excel(filepath)

        success_count = 0
        error_count = 0
        results = []

        for index, row in df.iterrows():
            try:
                if pd.notna(row.get('手机号')):
                    phone_data = {
                        'index': index + 1,
                        'name': str(row.get('姓名', '')).strip(),
                        'phone': str(row.get('手机号')).strip()
                    }

                    logger.info(f"正在添加微信联系人: {phone_data['name']} ({phone_data['phone']})")

                    # 调用MCP工具创建添加联系人任务
                    tool_args = {
                        "phoneNumber": phone_data['phone'],
                        "name": phone_data['name']
                    }

                    result = await session.call_tool("createAddContactTask", tool_args)

                    if result.isError:
                        error_count += 1
                        logger.error(f"添加微信联系人失败: {phone_data['name']} - {result.content}")
                    else:
                        success_count += 1
                        logger.info(f"成功添加微信联系人: {phone_data['name']}")

                    results.append({
                        'name': phone_data['name'],
                        'phone': phone_data['phone'],
                        'success': not result.isError,
                        'message': result.content
                    })

                    # 添加延迟避免请求过于频繁
                    await asyncio.sleep(2)

            except Exception as e:
                error_count += 1
                logger.error(f"处理微信联系人时出错: {e}")

        # 断开MCP服务器连接
        await session_context.__aexit__(None, None, None)
        await streams_context.__aexit__(None, None, None)

        return {
            'completed': True,
            'success': success_count > 0,
            'message': f'微信联系人添加完成 - 成功: {success_count}, 失败: {error_count}',
            'data': {
                'success_count': success_count,
                'error_count': error_count,
                'results': results
            }
        }

    except Exception as e:
        logger.error(f"添加微信联系人失败: {e}")
        return {
            'completed': True,
            'success': False,
            'message': f'添加微信联系人失败: {str(e)}',
            'data': {}
        }

async def add_waihu_tasks_for_resumes(filepath: str, resume_ids: List[str], job_id: str) -> Dict[str, Any]:
    """为简历添加外呼任务"""
    try:
        # 连接到MCP服务器
        session, session_context, streams_context = await connect_to_mcp_server()

        # 读取Excel数据获取手机号
        df = pd.read_excel(filepath)

        success_count = 0
        error_count = 0
        results = []

        # 匹配简历ID与手机号
        excel_index = 0
        for resume_id in resume_ids:
            try:
                # 在Excel中查找对应的记录
                while excel_index < len(df):
                    row = df.iloc[excel_index]
                    if pd.notna(row.get('手机号')):
                        phone = str(row.get('手机号')).strip()
                        name = str(row.get('姓名', '')).strip()

                        logger.info(f"正在创建外呼任务: {name} ({phone}) - 简历ID: {resume_id}")

                        # 调用MCP工具创建外呼任务
                        tool_args = {
                            "resumeId": resume_id,
                            "jobId": job_id,
                            "phone": phone
                        }

                        result = await session.call_tool("addWaihuTask", tool_args)

                        if result.isError:
                            error_count += 1
                            logger.error(f"创建外呼任务失败: {name} - {result.content}")
                        else:
                            success_count += 1
                            logger.info(f"成功创建外呼任务: {name}")

                        results.append({
                            'resumeId': resume_id,
                            'name': name,
                            'phone': phone,
                            'jobId': job_id,
                            'success': not result.isError,
                            'message': result.content
                        })

                        excel_index += 1
                        break
                    excel_index += 1
                else:
                    logger.warning(f"简历ID {resume_id} 无法匹配到对应的Excel记录")
                    error_count += 1

                # 添加延迟避免请求过于频繁
                await asyncio.sleep(2)

            except Exception as e:
                error_count += 1
                logger.error(f"处理外呼任务时出错: {e}")

        # 断开MCP服务器连接
        await session_context.__aexit__(None, None, None)
        await streams_context.__aexit__(None, None, None)

        return {
            'completed': True,
            'success': success_count > 0,
            'message': f'外呼任务创建完成 - 成功: {success_count}, 失败: {error_count}',
            'data': {
                'success_count': success_count,
                'error_count': error_count,
                'results': results
            }
        }

    except Exception as e:
        logger.error(f"创建外呼任务失败: {e}")
        return {
            'completed': True,
            'success': False,
            'message': f'创建外呼任务失败: {str(e)}',
            'data': {}
        }

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
                <button onclick="window.location.href='/resume-import'" class="btn btn-success">📁 简历导入</button>
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

# 简历导入页面HTML模板
RESUME_IMPORT_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>简历导入系统</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #333;
        }

        .container {
            max-width: 800px;
            width: 90%;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 16px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
            padding: 40px;
        }

        .header {
            text-align: center;
            margin-bottom: 40px;
        }

        .header h1 {
            font-size: 2.5rem;
            color: #4a90e2;
            margin-bottom: 10px;
            font-weight: 600;
        }

        .header p {
            color: #666;
            font-size: 1.1rem;
        }

        .upload-section {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            border: 2px dashed #ddd;
            text-align: center;
            transition: all 0.3s ease;
        }

        .upload-section.drag-over {
            border-color: #4a90e2;
            background: rgba(74, 144, 226, 0.05);
        }

        .upload-icon {
            font-size: 4rem;
            color: #4a90e2;
            margin-bottom: 20px;
        }

        .upload-text {
            font-size: 1.2rem;
            color: #666;
            margin-bottom: 20px;
        }

        .file-input {
            display: none;
        }

        .upload-btn {
            display: inline-block;
            padding: 12px 30px;
            background: #4a90e2;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
        }

        .upload-btn:hover {
            background: #357abd;
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(74, 144, 226, 0.3);
        }

        .config-section {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        }

        .config-section h3 {
            color: #4a90e2;
            margin-bottom: 20px;
            font-size: 1.3rem;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 500;
        }

        .form-group input {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            font-size: 1rem;
            transition: all 0.3s ease;
        }

        .form-group input:focus {
            outline: none;
            border-color: #4a90e2;
            box-shadow: 0 0 0 3px rgba(74, 144, 226, 0.1);
        }

        .selected-file {
            background: #e8f4fd;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #4a90e2;
        }

        .selected-file .file-name {
            font-weight: 600;
            color: #4a90e2;
        }

        .selected-file .file-size {
            color: #666;
            font-size: 0.9rem;
        }

        .process-btn {
            width: 100%;
            padding: 15px;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 20px;
        }

        .process-btn:hover:not(:disabled) {
            background: #218838;
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(40, 167, 69, 0.3);
        }

        .process-btn:disabled {
            background: #6c757d;
            cursor: not-allowed;
            transform: none;
        }

        .back-btn {
            display: inline-block;
            padding: 10px 20px;
            background: #6c757d;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            transition: all 0.3s ease;
        }

        .back-btn:hover {
            background: #5a6268;
            text-decoration: none;
            color: white;
        }

        .progress-section {
            display: none;
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        }

        .progress-section h3 {
            color: #4a90e2;
            margin-bottom: 20px;
        }

        .step {
            display: flex;
            align-items: center;
            padding: 15px;
            margin-bottom: 10px;
            background: #f8f9fa;
            border-radius: 8px;
            transition: all 0.3s ease;
        }

        .step.active {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
        }

        .step.completed {
            background: #d4edda;
            border-left: 4px solid #28a745;
        }

        .step.error {
            background: #f8d7da;
            border-left: 4px solid #dc3545;
        }

        .step-icon {
            width: 30px;
            height: 30px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 15px;
            font-weight: bold;
            color: white;
        }

        .step.active .step-icon {
            background: #ffc107;
        }

        .step.completed .step-icon {
            background: #28a745;
        }

        .step.error .step-icon {
            background: #dc3545;
        }

        .step-icon.loading {
            border: 2px solid #f3f3f3;
            border-top: 2px solid #ffc107;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .step-content {
            flex: 1;
        }

        .step-title {
            font-weight: 600;
            margin-bottom: 5px;
        }

        .step-message {
            color: #666;
            font-size: 0.9rem;
        }

        .results-section {
            display: none;
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        }

        .results-section h3 {
            color: #4a90e2;
            margin-bottom: 20px;
        }

        .summary-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }

        .summary-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }

        .stat-item {
            text-align: center;
            padding: 15px;
            background: white;
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }

        .stat-number {
            font-size: 2rem;
            font-weight: bold;
            color: #4a90e2;
        }

        .stat-label {
            color: #666;
            font-size: 0.9rem;
        }

        .message {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }

        .message.error {
            background: #f8d7da;
            color: #721c24;
            border-left: 4px solid #dc3545;
        }

        .message.success {
            background: #d4edda;
            color: #155724;
            border-left: 4px solid #28a745;
        }

        @media (max-width: 768px) {
            .container {
                width: 95%;
                padding: 20px;
            }

            .header h1 {
                font-size: 2rem;
            }

            .upload-section, .config-section {
                padding: 20px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📋 简历导入系统</h1>
            <p>上传简历Excel文件，自动完成导入、添加微信、创建外呼任务</p>
        </div>

        <div id="uploadArea" class="upload-section">
            <div class="upload-icon">📁</div>
            <div class="upload-text">拖拽Excel文件到此处，或点击选择文件</div>
            <input type="file" id="fileInput" class="file-input" accept=".xlsx,.xls">
            <label for="fileInput" class="upload-btn">选择文件</label>
        </div>

        <div class="config-section">
            <h3>⚙️ 配置选项</h3>
            <div class="form-group">
                <label for="jobId">岗位ID（用于外呼任务）</label>
                <input type="text" id="jobId" value="fd9d46ec-1f06-4504-a034-122347e92239" placeholder="输入岗位ID">
            </div>
        </div>

        <div id="selectedFile" class="selected-file" style="display: none;">
            <div class="file-name"></div>
            <div class="file-size"></div>
        </div>

        <button id="processBtn" class="process-btn" disabled>
            🚀 开始处理
        </button>

        <div class="progress-section" id="progressSection">
            <h3>📊 处理进度</h3>

            <div class="step" id="step1">
                <div class="step-icon">1</div>
                <div class="step-content">
                    <div class="step-title">导入简历到数据库</div>
                    <div class="step-message">等待开始...</div>
                </div>
            </div>

            <div class="step" id="step2">
                <div class="step-icon">2</div>
                <div class="step-content">
                    <div class="step-title">添加微信联系人</div>
                    <div class="step-message">等待开始...</div>
                </div>
            </div>

            <div class="step" id="step3">
                <div class="step-icon">3</div>
                <div class="step-content">
                    <div class="step-title">创建外呼任务</div>
                    <div class="step-message">等待开始...</div>
                </div>
            </div>
        </div>

        <div class="results-section" id="resultsSection">
            <h3>📈 处理结果</h3>
            <div id="resultsSummary" class="summary-card">
                <div class="summary-stats">
                    <div class="stat-item">
                        <div class="stat-number" id="resumeCount">0</div>
                        <div class="stat-label">简历导入</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="wechatCount">0</div>
                        <div class="stat-label">微信添加</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="waihuCount">0</div>
                        <div class="stat-label">外呼创建</div>
                    </div>
                </div>
            </div>
            <div id="resultsMessage"></div>
        </div>

        <div style="text-align: center; margin-top: 30px;">
            <a href="/" class="back-btn">← 返回岗位管理</a>
        </div>
    </div>

    <script>
        class ResumeImporter {
            constructor() {
                this.selectedFile = null;
                this.init();
            }

            init() {
                this.bindEvents();
                this.setupDragAndDrop();
            }

            bindEvents() {
                const fileInput = document.getElementById('fileInput');
                const processBtn = document.getElementById('processBtn');

                fileInput.addEventListener('change', (e) => {
                    this.handleFileSelect(e.target.files[0]);
                });

                processBtn.addEventListener('click', () => {
                    this.startProcessing();
                });
            }

            setupDragAndDrop() {
                const uploadArea = document.getElementById('uploadArea');

                uploadArea.addEventListener('dragover', (e) => {
                    e.preventDefault();
                    uploadArea.classList.add('drag-over');
                });

                uploadArea.addEventListener('dragleave', () => {
                    uploadArea.classList.remove('drag-over');
                });

                uploadArea.addEventListener('drop', (e) => {
                    e.preventDefault();
                    uploadArea.classList.remove('drag-over');

                    const files = e.dataTransfer.files;
                    if (files.length > 0) {
                        this.handleFileSelect(files[0]);
                    }
                });
            }

            handleFileSelect(file) {
                if (!file) return;

                // 验证文件类型
                const allowedTypes = [
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'application/vnd.ms-excel'
                ];

                if (!allowedTypes.includes(file.type) && !file.name.match(/\.(xlsx|xls)$/i)) {
                    this.showMessage('请选择Excel文件（.xlsx或.xls格式）', 'error');
                    return;
                }

                // 验证文件大小（16MB限制）
                if (file.size > 16 * 1024 * 1024) {
                    this.showMessage('文件大小不能超过16MB', 'error');
                    return;
                }

                this.selectedFile = file;
                this.displaySelectedFile(file);
                document.getElementById('processBtn').disabled = false;
            }

            displaySelectedFile(file) {
                const selectedFileDiv = document.getElementById('selectedFile');
                const fileName = selectedFileDiv.querySelector('.file-name');
                const fileSize = selectedFileDiv.querySelector('.file-size');

                fileName.textContent = `📄 ${file.name}`;
                fileSize.textContent = `文件大小: ${this.formatFileSize(file.size)}`;
                selectedFileDiv.style.display = 'block';
            }

            formatFileSize(bytes) {
                if (bytes < 1024) return bytes + ' B';
                if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
                return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
            }

             async startProcessing() {
                 if (!this.selectedFile) {
                     this.showMessage('请先选择文件', 'error');
                     return;
                 }

                 const jobId = document.getElementById('jobId').value.trim();
                 if (!jobId) {
                     this.showMessage('请输入岗位ID', 'error');
                     return;
                 }

                 // 显示进度区域
                 document.getElementById('progressSection').style.display = 'block';
                 document.getElementById('resultsSection').style.display = 'none';
                 document.getElementById('processBtn').disabled = true;

                 // 重置步骤状态
                 this.resetSteps();

                 try {
                     // 准备表单数据
                     const formData = new FormData();
                     formData.append('file', this.selectedFile);
                     formData.append('job_id', jobId);

                     // 开始处理
                     this.updateStep('step1', 'active', '正在上传文件...', true);

                     const response = await fetch('/api/resume-import', {
                         method: 'POST',
                         body: formData
                     });

                     const result = await response.json();

                     if (result.success && result.task_id) {
                         // 使用SSE接收实时进度
                         this.connectToProgressStream(result.task_id);
                     } else {
                         this.handleErrorResult(result.error || '未知错误');
                     }

                 } catch (error) {
                     this.handleErrorResult('处理过程中发生错误: ' + error.message);
                 }
             }

             connectToProgressStream(taskId) {
                 const eventSource = new EventSource(`/api/resume-import/progress/${taskId}`);

                 eventSource.onmessage = (event) => {
                     try {
                         const progressData = JSON.parse(event.data);

                         if (progressData.error) {
                             this.handleErrorResult(progressData.error);
                             eventSource.close();
                             return;
                         }

                         this.updateProgressFromStream(progressData);

                         if (progressData.completed) {
                             eventSource.close();
                             document.getElementById('processBtn').disabled = false;
                         }
                     } catch (error) {
                         console.error('解析进度数据失败:', error);
                     }
                 };

                 eventSource.onerror = (error) => {
                     console.error('SSE连接错误:', error);
                     this.handleErrorResult('进度连接断开，请刷新页面重试');
                     eventSource.close();
                     document.getElementById('processBtn').disabled = false;
                 };
             }

             updateProgressFromStream(progressData) {
                 const { steps, current_step, summary, completed } = progressData;

                 // 更新当前步骤状态
                 if (current_step === 1) {
                     this.updateStep('step1', 'active', steps.import_resumes.message, !steps.import_resumes.completed);
                     if (steps.import_resumes.completed) {
                         const status = steps.import_resumes.success ? 'completed' : 'error';
                         this.updateStep('step1', status, steps.import_resumes.message);
                     }
                 }

                 if (current_step >= 2) {
                     this.updateStep('step2', 'active', steps.add_wechat.message, !steps.add_wechat.completed);
                     if (steps.add_wechat.completed) {
                         const status = steps.add_wechat.success ? 'completed' : 'error';
                         this.updateStep('step2', status, steps.add_wechat.message);
                     }
                 }

                 if (current_step >= 3) {
                     this.updateStep('step3', 'active', steps.add_waihu.message, !steps.add_waihu.completed);
                     if (steps.add_waihu.completed) {
                         const status = steps.add_waihu.success ? 'completed' : 'error';
                         this.updateStep('step3', status, steps.add_waihu.message);
                     }
                 }

                 // 如果任务完成，显示结果
                 if (completed && summary) {
                     this.displayResults(summary);
                     this.showMessage('处理完成！', 'success');
                 }
             }

            resetSteps() {
                ['step1', 'step2', 'step3'].forEach(stepId => {
                    const step = document.getElementById(stepId);
                    step.className = 'step';
                    const icon = step.querySelector('.step-icon');
                    icon.className = 'step-icon';
                    icon.textContent = stepId.charAt(4); // 1, 2, 3
                    step.querySelector('.step-message').textContent = '等待开始...';
                });
            }

            updateStep(stepId, status, message, loading = false) {
                const step = document.getElementById(stepId);
                const icon = step.querySelector('.step-icon');
                const messageEl = step.querySelector('.step-message');

                step.className = `step ${status}`;
                messageEl.textContent = message;

                if (loading) {
                    icon.className = 'step-icon loading';
                    icon.textContent = '';
                } else {
                    icon.className = 'step-icon';
                    if (status === 'completed') {
                        icon.textContent = '✓';
                    } else if (status === 'error') {
                        icon.textContent = '✗';
                    } else {
                        icon.textContent = stepId.charAt(4);
                    }
                }
            }

            handleSuccessResult(result) {
                // 更新各步骤状态
                const steps = result.steps;

                // 步骤1：导入简历
                if (steps.import_resumes.completed) {
                    const status = steps.import_resumes.success ? 'completed' : 'error';
                    this.updateStep('step1', status, steps.import_resumes.message);
                }

                // 步骤2：添加微信
                if (steps.add_wechat.completed) {
                    const status = steps.add_wechat.success ? 'completed' : 'error';
                    this.updateStep('step2', status, steps.add_wechat.message);
                }

                // 步骤3：添加外呼
                if (steps.add_waihu.completed) {
                    const status = steps.add_waihu.success ? 'completed' : 'error';
                    this.updateStep('step3', status, steps.add_waihu.message);
                }

                // 显示结果
                this.displayResults(result.summary);
                this.showMessage('处理完成！', 'success');
            }

            handleErrorResult(errorMessage) {
                this.updateStep('step1', 'error', errorMessage);
                this.showMessage(errorMessage, 'error');
            }

            displayResults(summary) {
                document.getElementById('resumeCount').textContent = summary.resume_imported || 0;
                document.getElementById('wechatCount').textContent = summary.wechat_added || 0;
                document.getElementById('waihuCount').textContent = summary.waihu_created || 0;

                const messageDiv = document.getElementById('resultsMessage');
                messageDiv.innerHTML = `
                    <div class="message success">
                        <strong>✅ 处理完成</strong><br>
                        ${summary.message || '所有步骤已完成'}
                    </div>
                `;

                document.getElementById('resultsSection').style.display = 'block';
            }

            showMessage(message, type) {
                // 简单的消息显示，可以根据需要扩展
                console.log(`[${type.toUpperCase()}] ${message}`);
            }
        }

        // 初始化应用
        document.addEventListener('DOMContentLoaded', () => {
            new ResumeImporter();
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
