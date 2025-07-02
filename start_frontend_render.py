#!/usr/bin/env python3
"""
Financial Frontend for Render.com deployment
"""

import os
import sys
from pathlib import Path

def ensure_render_directories():
    """确保 Render.com 环境下的必要目录存在"""
    if os.getenv('ENVIRONMENT') == 'production':
        # 创建临时目录结构
        base_dir = Path('/tmp/financial_app')
        data_dir = Path('/tmp/data')
        
        # 创建必要的目录
        directories = [
            base_dir / 'uploads',
            base_dir / 'downloads',
            data_dir / 'input',
            data_dir / 'processed' / 'summary',
            data_dir / 'processed' / 'database',
            data_dir / 'processed' / 'visualization',
            data_dir / 'processed' / 'reporting'
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"✓ 目录已创建: {directory}")

def main():
    """主函数"""
    print("🚀 Starting Flask frontend for Render deployment...")
    
    # 确保 Render 环境目录存在
    ensure_render_directories()
    
    # 获取环境变量
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    print(f"🌐 Host: {host}")
    print(f"🔌 Port: {port}")
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"🐍 Python path: {sys.path}")
    
    # 切换到 flask_frontend 目录
    flask_dir = os.path.join(os.getcwd(), 'flask_frontend')
    if os.path.exists(flask_dir):
        os.chdir(flask_dir)
        print(f"📂 Changed to directory: {flask_dir}")
    else:
        print(f"⚠️  flask_frontend directory not found at: {flask_dir}")
        print(f"📋 Current directory contents: {os.listdir('.')}")
    
    # 添加当前目录到 Python 路径
    current_dir = os.getcwd()
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    # 添加父目录到 Python 路径
    parent_dir = os.path.dirname(current_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    print(f"🔧 Updated Python path: {sys.path[:3]}...")  # 只显示前3个路径
    
    try:
        # 导入并启动 Flask 应用
        from app import app
        print("✅ Successfully imported Flask app")
        
        # 确保在 Render 环境中使用正确的启动配置
        print(f"🚀 Starting Flask app on {host}:{port}")
        app.run(
            host=host,
            port=port,
            debug=False,
            threaded=True,  # 启用多线程
            use_reloader=False  # 在生产环境中禁用重载
        )
    except ImportError as e:
        print(f"❌ Failed to import app: {e}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Files in current directory: {os.listdir('.')}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to start Flask app: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main() 