#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简历管理Web应用 - 主应用文件
整合简历导入、微信添加和外呼任务功能
"""

import os
import json
import time
import uuid
import asyncio
import logging
import pandas as pd
import pymysql
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename

# MCP相关导入
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# 导入配置
from config import config

def create_app(config_name=None):
    """应用工厂函数"""
    app = Flask(__name__)

    # 加载配置
    config_name = config_name or os.environ.get('FLASK_ENV', 'default')
    app.config.from_object(config[config_name])

    # 确保上传目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # 配置日志
    logging.basicConfig(
        level=getattr(logging, app.config['LOG_LEVEL']),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(app.config['LOG_FILE'], encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    return app

# 创建应用实例
app = create_app()
logger = logging.getLogger(__name__)

class ResumeManager:
    def __init__(self, app):
        self.app = app
        self.connection = None
        self.mcp_session = None
        self.mcp_streams_context = None
        self.mcp_session_context = None

    def parse_database_url(self) -> Dict[str, str]:
        """解析数据库URL"""
        url = self.app.config['DATABASE_URL'].replace('mysql://', '')
        auth_part, host_part = url.split('@')
        username, password = auth_part.split(':')
        host_port_db = host_part.split('/')
        host_port = host_port_db[0]
        database = host_port_db[1].split('?')[0]

        if ':' in host_port:
            host, port = host_port.split(':')
        else:
            host = host_port
            port = '3306'

        return {
            'host': host,
            'port': int(port),
            'user': username,
            'password': password,
            'database': database,
            'charset': 'utf8mb4'
        }

    def connect_database(self):
        """连接数据库"""
        try:
            db_config = self.parse_database_url()
            self.connection = pymysql.connect(**db_config)
            logger.info("数据库连接成功")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise

    def close_database(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            logger.info("数据库连接已关闭")

    async def connect_mcp_server(self):
        """连接到MCP服务器"""
        try:
            logger.info(f"正在连接到MCP服务器: {self.app.config['MCP_SERVER_URL']}")

            self.mcp_streams_context = streamablehttp_client(
                url=self.app.config['MCP_SERVER_URL'],
                headers={},
            )
            read_stream, write_stream, _ = await self.mcp_streams_context.__aenter__()

            self.mcp_session_context = ClientSession(read_stream, write_stream)
            self.mcp_session = await self.mcp_session_context.__aenter__()

            await self.mcp_session.initialize()
            logger.info("成功连接到MCP服务器")

        except Exception as e:
            logger.error(f"连接MCP服务器失败: {e}")
            raise

    async def disconnect_mcp_server(self):
        """断开MCP服务器连接"""
        try:
            if self.mcp_session_context:
                await self.mcp_session_context.__aexit__(None, None, None)
            if self.mcp_streams_context:
                await self.mcp_streams_context.__aexit__(None, None, None)
            logger.info("已断开MCP服务器连接")
        except Exception as e:
            logger.error(f"断开MCP服务器连接时发生错误: {e}")

    def import_resumes_from_excel(self, file_path: str) -> Dict[str, Any]:
        """从Excel导入简历"""
        try:
            # 读取Excel文件
            df = pd.read_excel(file_path)
            logger.info(f"成功读取Excel文件，共 {len(df)} 条记录")

            # 连接数据库
            self.connect_database()
            cursor = self.connection.cursor()

            successful_ids = []
            failed_records = []

            for index, row in df.iterrows():
                try:
                    # 映射Excel数据到简历字段
                    resume_id = str(uuid.uuid4())
                    resume_data = {
                        'id': resume_id,
                        'name': str(row.get('姓名', '')).strip(),
                        'phone': str(row.get('手机号', '')).strip() if pd.notna(row.get('手机号')) else None,
                        'wechat': str(row.get('微信号', '')).strip() if pd.notna(row.get('微信号')) else None,
                        'source': 'INTERNAL',
                        'deleted': 0,
                        'create_time': datetime.now(),
                        'update_time': datetime.now()
                    }

                    # 处理年龄
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

                    # 处理期望职位
                    if pd.notna(row.get('应聘岗位')):
                        position = str(row.get('应聘岗位')).strip()
                        expect_positions = [position]
                        resume_data['expect_positions'] = json.dumps(expect_positions, ensure_ascii=False)

                    # 插入数据库
                    columns = ', '.join(resume_data.keys())
                    placeholders = ', '.join(['%s'] * len(resume_data))
                    sql = f"INSERT INTO resumes ({columns}) VALUES ({placeholders})"

                    cursor.execute(sql, list(resume_data.values()))
                    successful_ids.append(resume_id)

                except Exception as e:
                    logger.error(f"导入第 {index + 1} 行数据失败: {e}")
                    failed_records.append({
                        'row': index + 1,
                        'name': str(row.get('姓名', '')),
                        'error': str(e)
                    })

            # 提交事务
            self.connection.commit()
            cursor.close()
            self.close_database()

            # 保存成功的简历ID
            with open('successful_resume_ids.txt', 'w', encoding='utf-8') as f:
                for resume_id in successful_ids:
                    f.write(f"{resume_id}\n")

            return {
                'success': True,
                'total_records': len(df),
                'successful_count': len(successful_ids),
                'failed_count': len(failed_records),
                'successful_ids': successful_ids,
                'failed_records': failed_records
            }

        except Exception as e:
            logger.error(f"导入简历失败: {e}")
            if self.connection:
                self.connection.rollback()
                self.close_database()
            return {
                'success': False,
                'error': str(e)
            }

    async def add_wechat_contacts(self, file_path: str) -> Dict[str, Any]:
        """批量添加微信联系人"""
        try:
            # 读取Excel文件
            df = pd.read_excel(file_path)
            phone_data = []

            for index, row in df.iterrows():
                if pd.notna(row.get('手机号')):
                    phone_data.append({
                        'index': index + 1,
                        'name': str(row.get('姓名', '')).strip(),
                        'phone': str(row.get('手机号')).strip()
                    })

            # 连接MCP服务器
            await self.connect_mcp_server()

            results = []
            wait_time = 0

            for contact in phone_data:
                try:
                    logger.info(f"正在添加联系人: {contact['name']} ({contact['phone']})")

                    # 调用MCP工具创建添加联系人任务
                    tool_args = {
                        "phoneNumber": contact['phone'],
                        "name": contact['name']
                    }

                    result = await self.mcp_session.call_tool("createAddContactTask", tool_args)

                    if result.isError:
                        error_message = f"MCP调用失败: {result.content}"
                        logger.error(error_message)
                        results.append({
                            'index': contact['index'],
                            'name': contact['name'],
                            'phone': contact['phone'],
                            'success': False,
                            'message': error_message
                        })
                    else:
                        success_message = f"任务已创建: {result.content}"
                        logger.info(f"✓ MCP调用成功: {success_message}")
                        results.append({
                            'index': contact['index'],
                            'name': contact['name'],
                            'phone': contact['phone'],
                            'success': True,
                            'message': success_message
                        })

                        # 累计等待时间
                        wait_time += self.app.config['WECHAT_WAIT_TIME_PER_CONTACT']

                    # 添加延迟避免频繁调用
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.error(f"添加联系人失败: {contact['name']} ({contact['phone']}) - {e}")
                    results.append({
                        'index': contact['index'],
                        'name': contact['name'],
                        'phone': contact['phone'],
                        'success': False,
                        'message': str(e)
                    })

            # 断开MCP连接
            await self.disconnect_mcp_server()

            successful_count = sum(1 for r in results if r['success'])

            return {
                'success': True,
                'total_contacts': len(phone_data),
                'successful_count': successful_count,
                'failed_count': len(phone_data) - successful_count,
                'results': results,
                'estimated_wait_time': wait_time
            }

        except Exception as e:
            logger.error(f"添加微信联系人失败: {e}")
            if self.mcp_session:
                await self.disconnect_mcp_server()
            return {
                'success': False,
                'error': str(e)
            }

    async def add_waihu_tasks(self, file_path: str, job_id: str) -> Dict[str, Any]:
        """批量添加外呼任务"""
        try:
            # 读取简历ID
            with open('successful_resume_ids.txt', 'r', encoding='utf-8') as f:
                resume_ids = [line.strip() for line in f if line.strip()]

            # 读取Excel数据
            df = pd.read_excel(file_path)

            # 匹配简历ID与手机号
            matched_data = []
            excel_index = 0

            for resume_id in resume_ids:
                while excel_index < len(df):
                    row = df.iloc[excel_index]
                    if pd.notna(row.get('手机号')):
                        phone = str(row.get('手机号')).strip()
                        name = str(row.get('姓名', '')).strip()

                        matched_data.append({
                            'resumeId': resume_id,
                            'phone': phone,
                            'name': name,
                            'excel_index': excel_index + 1
                        })
                        excel_index += 1
                        break
                    excel_index += 1

            # 连接MCP服务器
            await self.connect_mcp_server()

            results = []

            for task_data in matched_data:
                try:
                    logger.info(f"正在添加外呼任务: {task_data['name']} ({task_data['phone']}) - 简历ID: {task_data['resumeId']}")

                    # 调用MCP工具添加外呼任务
                    tool_args = {
                        "resumeId": task_data['resumeId'],
                        "jobId": job_id,
                        "phone": task_data['phone']
                    }

                    result = await self.mcp_session.call_tool("addWaihuTask", tool_args)

                    if result.isError:
                        error_message = f"MCP调用失败: {result.content}"
                        logger.error(error_message)
                        results.append({
                            'resumeId': task_data['resumeId'],
                            'phone': task_data['phone'],
                            'name': task_data['name'],
                            'success': False,
                            'message': error_message
                        })
                    else:
                        success_message = f"外呼任务已创建: {result.content}"
                        logger.info(f"✓ MCP调用成功: {success_message}")
                        results.append({
                            'resumeId': task_data['resumeId'],
                            'phone': task_data['phone'],
                            'name': task_data['name'],
                            'success': True,
                            'message': success_message
                        })

                    # 添加延迟避免频繁调用
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.error(f"添加外呼任务失败: {task_data['name']} ({task_data['phone']}) - {e}")
                    results.append({
                        'resumeId': task_data['resumeId'],
                        'phone': task_data['phone'],
                        'name': task_data['name'],
                        'success': False,
                        'message': str(e)
                    })

            # 断开MCP连接
            await self.disconnect_mcp_server()

            successful_count = sum(1 for r in results if r['success'])

            return {
                'success': True,
                'total_tasks': len(matched_data),
                'successful_count': successful_count,
                'failed_count': len(matched_data) - successful_count,
                'results': results
            }

        except Exception as e:
            logger.error(f"添加外呼任务失败: {e}")
            if self.mcp_session:
                await self.disconnect_mcp_server()
            return {
                'success': False,
                'error': str(e)
            }

# 全局变量
resume_manager = ResumeManager(app)
current_task_status = {
    'step': 'idle',  # idle, importing, adding_wechat, waiting, adding_waihu, completed
    'progress': 0,
    'message': '',
    'wait_until': None,
    'results': {}
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('index.html', status=current_task_status)

@app.route('/upload', methods=['POST'])
def upload_file():
    global current_task_status

    if 'file' not in request.files:
        flash('没有选择文件')
        return redirect(request.url)

    file = request.files['file']
    job_id = request.form.get('job_id', '0')  # 默认职位ID为0

    if file.filename == '':
        flash('没有选择文件')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # 重置状态
        current_task_status.update({
            'step': 'idle',
            'progress': 0,
            'message': '准备开始处理...',
            'wait_until': None,
            'results': {}
        })

        # 启动异步处理（在新线程中运行）
        def run_async_workflow():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(process_resume_workflow(file_path, job_id))
            except Exception as e:
                logger.error(f"异步工作流程执行失败: {e}")
                global current_task_status
                current_task_status.update({
                    'step': 'error',
                    'message': f"处理失败: {str(e)}"
                })
            finally:
                loop.close()

        # 在后台线程中运行异步任务
        thread = threading.Thread(target=run_async_workflow)
        thread.daemon = True
        thread.start()

        return redirect(url_for('status'))
    else:
        flash('请上传Excel文件 (.xlsx 或 .xls)')
        return redirect(request.url)

@app.route('/status')
def status():
    return render_template('status.html', status=current_task_status)

@app.route('/api/status')
def api_status():
    return jsonify(current_task_status)

async def process_resume_workflow(file_path: str, job_id: str):
    """处理完整的简历工作流程"""
    global current_task_status

    try:
        # 步骤1: 导入简历
        current_task_status.update({
            'step': 'importing',
            'progress': 10,
            'message': '正在导入简历数据...'
        })

        import_result = resume_manager.import_resumes_from_excel(file_path)

        if not import_result['success']:
            current_task_status.update({
                'step': 'error',
                'message': f"简历导入失败: {import_result['error']}"
            })
            return

        current_task_status['results']['import'] = import_result

        # 步骤2: 添加微信联系人
        current_task_status.update({
            'step': 'adding_wechat',
            'progress': 30,
            'message': '正在添加微信联系人...'
        })

        wechat_result = await resume_manager.add_wechat_contacts(file_path)

        if not wechat_result['success']:
            current_task_status.update({
                'step': 'error',
                'message': f"添加微信联系人失败: {wechat_result['error']}"
            })
            return

        current_task_status['results']['wechat'] = wechat_result

        # 步骤3: 等待时间
        wait_time = wechat_result.get('estimated_wait_time', 0)
        wait_until = datetime.now() + timedelta(seconds=wait_time)

        current_task_status.update({
            'step': 'waiting',
            'progress': 60,
            'message': f'等待微信添加完成，预计等待 {wait_time} 秒...',
            'wait_until': wait_until.isoformat()
        })

        # 等待指定时间
        await asyncio.sleep(wait_time)

        # 步骤4: 添加外呼任务
        current_task_status.update({
            'step': 'adding_waihu',
            'progress': 80,
            'message': '正在添加外呼任务...'
        })

        waihu_result = await resume_manager.add_waihu_tasks(file_path, job_id)

        if not waihu_result['success']:
            current_task_status.update({
                'step': 'error',
                'message': f"添加外呼任务失败: {waihu_result['error']}"
            })
            return

        current_task_status['results']['waihu'] = waihu_result

        # 完成
        current_task_status.update({
            'step': 'completed',
            'progress': 100,
            'message': '所有任务已完成！'
        })

    except Exception as e:
        logger.error(f"处理工作流程失败: {e}")
        current_task_status.update({
            'step': 'error',
            'message': f"处理失败: {str(e)}"
        })

if __name__ == '__main__':
    app.run(debug=app.config.get('DEBUG', False),
            host='0.0.0.0',
            port=int(os.environ.get('PORT', 5000)))
