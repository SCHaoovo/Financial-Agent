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
    """启动 Flask 前端应用"""
    # 获取 Render 提供的端口，默认 5000
    port = int(os.environ.get("PORT", 5000))
    host = "0.0.0.0"
    
    print(f"🚀 启动 Financial Frontend 在 {host}:{port}")
    
    # 设置环境变量
    os.environ["FLASK_ENV"] = os.environ.get("FLASK_ENV", "production")
    
    # 确保目录存在
    ensure_render_directories()
    
    # 切换到 flask_frontend 目录
    sys.path.insert(0, 'flask_frontend')
    os.chdir('flask_frontend')
    
    # 导入并启动 Flask 应用
    from app import app
    
    app.run(
        host=host,
        port=port,
        debug=False
    )

if __name__ == "__main__":
    main() 