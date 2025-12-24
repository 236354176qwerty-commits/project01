#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
武术赛事管理系统 - 配置文件
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """应用配置类"""
    
    # Flask 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # 数据库配置
    DB_HOST = os.environ.get('DB_HOST') or 'mysql2.sqlpub.com'
    DB_PORT = int(os.environ.get('DB_PORT') or 3307)
    DB_USER = os.environ.get('DB_USER') or 'dvg_hnk'
    DB_PASSWORD = os.environ.get('DB_PASSWORD') or ''
    DB_NAME = os.environ.get('DB_NAME') or 'wu_shu'
    # 数据库连接池配置
    DB_POOL_NAME = os.environ.get('DB_POOL_NAME') or 'wushu_pool'
    DB_POOL_SIZE = int(os.environ.get('DB_POOL_SIZE') or 10)
    
    # 服务器配置
    HOST = os.environ.get('HOST') or '0.0.0.0'
    PORT = int(os.environ.get('PORT') or 5000)
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    # Session 配置
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = False  # 生产环境应设为 True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # 文件上传配置
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}
    
    # 分页配置
    ITEMS_PER_PAGE = 20
    
    # 邮件配置（如需要）
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = os.environ.get('LOG_FILE') or 'wushu_system.log'
    
    # 安全配置
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # CSRF token 有效期 1 小时
    
    # 系统配置
    SYSTEM_NAME = '武术赛事管理系统'
    SYSTEM_VERSION = '1.0.0'
    SYSTEM_AUTHOR = '武术赛事管理团队'
    
    # 用户角色权限配置（按权限级别排序）
    ROLE_PERMISSIONS = {
        'super_admin': [
            'manage_users',        # 管理用户（包括修改角色）
            'manage_events',       # 管理赛事
            'manage_participants', # 管理参赛者
            'manage_scoring',      # 管理评分
            'view_reports',        # 查看报告
            'system_settings'      # 系统设置
        ],
        'admin': [
            'manage_events',       # 管理赛事
            'manage_participants', # 管理参赛者
            'manage_scoring',      # 管理评分
            'view_reports'         # 查看报告
        ],
        'judge': [
            'view_events',         # 查看赛事
            'manage_scoring',      # 管理评分
            'view_participants'    # 查看参赛者
        ],
        'user': [
            'view_events',         # 查看赛事
            'register_events',     # 报名参赛
            'view_results'         # 查看成绩
        ]
    }
    
    # 角色层级定义（数字越大权限越高）
    ROLE_HIERARCHY = {
        'user': 1,
        'judge': 2,
        'admin': 3,
        'super_admin': 4
    }
    
    # 评分配置
    SCORING_CONFIG = {
        'technique_max': 10.0,      # 技术分最高分
        'performance_max': 10.0,    # 表现分最高分
        'deduction_max': 5.0,       # 最大扣分
        'decimal_places': 2,        # 小数位数
        'min_judges': 3,            # 最少裁判数
        'max_judges': 9,            # 最多裁判数
        'drop_highest': True,       # 是否去掉最高分
        'drop_lowest': True,        # 是否去掉最低分
    }
    
    # 赛事配置
    EVENT_CONFIG = {
        'categories': [
            '长拳', '太极拳', '南拳', '剑术', '刀术', '枪术', '棍术',
            '双器械', '软器械', '拳术', '器械'
        ],
        'weight_classes': [
            '48kg以下', '48-52kg', '52-56kg', '56-60kg', '60-65kg',
            '65-70kg', '70-75kg', '75-80kg', '80kg以上'
        ],
        'age_groups': [
            '儿童组(6-12岁)', '少年组(13-17岁)', '青年组(18-35岁)',
            '中年组(36-50岁)', '老年组(51岁以上)'
        ]
    }
    
    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        # 确保上传目录存在
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        
        # 设置日志
        import logging
        logging.basicConfig(
            level=getattr(logging, Config.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(Config.LOG_FILE, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'wushu-competition-system-2024-secret-key'
    DB_NAME = 'wushu_competition_dev'

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    WTF_CSRF_ENABLED = True
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # 生产环境数据库配置（从环境变量获取）
    DB_HOST = os.environ.get('PROD_DB_HOST') or 'localhost'
    DB_USER = os.environ.get('PROD_DB_USER') or 'wushu_user'
    DB_PASSWORD = os.environ.get('PROD_DB_PASSWORD') or ''
    DB_NAME = os.environ.get('PROD_DB_NAME') or 'wushu_competition_prod'

class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    WTF_CSRF_ENABLED = False
    DB_NAME = 'wushu_competition_test'

# 配置映射
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
