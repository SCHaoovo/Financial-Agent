"""
财务报告系统 Flask 前端应用 - 应用包初始化
"""

import os
from flask import Flask
from flask_frontend.app.config.config import Config

def create_app(config_class=Config):
    """创建并配置Flask应用"""
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    app.config.from_object(config_class)
    
    # 确保必要的目录存在
    ensure_directories(app)
    
    # 注册蓝图
    from flask_frontend.app.routes.main_routes import main_bp
    from flask_frontend.app.routes.api_routes import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # 注册错误处理器
    register_error_handlers(app)
    
    return app

def ensure_directories(app):
    """确保必要的目录存在"""
    directories = [
        app.config['UPLOAD_FOLDER'],
        app.config['DOWNLOADS_FOLDER']
    ]
    
    for directory in directories:
        try:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                app.logger.info(f"目录已创建: {directory}")
            else:
                app.logger.info(f"目录已存在: {directory}")
        except Exception as e:
            app.logger.error(f"创建目录失败 {directory}: {str(e)}")
            # 在云环境中，目录创建失败不应该阻止应用启动
            pass

def register_error_handlers(app):
    """注册错误处理器"""
    @app.errorhandler(404)
    def not_found_error(error):
        """404错误处理"""
        from flask import render_template
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        """500错误处理"""
        from flask import render_template
        return render_template('500.html'), 500 