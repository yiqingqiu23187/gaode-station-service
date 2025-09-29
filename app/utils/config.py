#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简历管理应用配置文件
"""

import os

class Config:
    """基础配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-this-in-production'

    # 文件上传配置
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

    # 数据库配置
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'mysql://username:password@localhost:3306/resume_db'

    # MCP服务器配置
    MCP_SERVER_URL = os.environ.get('MCP_SERVER_URL') or 'http://152.136.8.68:3001/mcp'
    MCP_TIMEOUT = 50

    # 微信添加配置
    WECHAT_WAIT_TIME_PER_CONTACT = 30  # 每个联系人等待30秒

    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = 'resume_management.log'

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    # 使用SQLite作为默认数据库，避免MySQL连接问题
    DATABASE_URL = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///resume_dev.db'

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    # 生产环境应该从环境变量获取敏感信息
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'production-secret-key-change-this'
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'mysql://username:password@localhost:3306/resume_db'

class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DATABASE_URL = 'sqlite:///resume_test.db'

# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
