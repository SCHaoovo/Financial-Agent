"""
财务报告系统 Flask 前端应用 - 配置
"""

import os

class Config:
    """应用配置类"""
    # 密钥配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')  # 生产环境中应该使用环境变量
    
    # 文件上传配置
    UPLOAD_FOLDER = 'uploads'
    DOWNLOADS_FOLDER = 'downloads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB 最大文件大小
    
    # 后端API配置
    BACKEND_URL = os.environ.get('BACKEND_URL', 'http://localhost:8000')
    
    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    
class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    
class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DEBUG = True
    # 测试用的文件夹
    UPLOAD_FOLDER = 'test_uploads'
    DOWNLOADS_FOLDER = 'test_downloads'

# 根据环境变量选择配置
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}

# 默认使用开发环境配置
Config = config_by_name.get(os.environ.get('FLASK_ENV', 'development'), DevelopmentConfig) 