#!/usr/bin/env python3
"""
财务报告系统服务启动检查脚本
用于检查Render服务状态并启动本地前端
"""

import requests
import time
import os
import sys
from urllib.parse import urlparse

# 配置服务地址
BACKEND_URL = os.getenv('BACKEND_URL', 'https://your-backend-url.onrender.com')
FRONTEND_PORT = os.getenv('PORT', 5000)


def check_backend_status(max_retries=10):
    """检查后端服务状态"""
    print(f"🔍 检查后端服务状态: {BACKEND_URL}")
    
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=10)
            if response.status_code == 200:
                print("✅ 后端服务已启动并正常运行")
                return True
        except requests.exceptions.RequestException as e:
            print(f"⏳ 尝试 {attempt + 1}/{max_retries}: 后端服务启动中...")
            if attempt < max_retries - 1:
                time.sleep(30)  # 等待30秒后重试
    
    print("❌ 后端服务启动失败或超时")
    return False

def start_frontend():
    """启动前端服务"""
    print(f"🚀 启动前端服务，端口: {FRONTEND_PORT}")
    print(f"📱 前端地址: http://localhost:{FRONTEND_PORT}")
    print("🎯 使用Ctrl+C停止服务")
    
    # 设置环境变量
    os.environ['BACKEND_URL'] = BACKEND_URL
    os.environ['PORT'] = str(FRONTEND_PORT)
    
    # 启动Flask应用
    try:
        os.chdir('flask_frontend')
        os.system(f'python app.py')
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
    except Exception as e:
        print(f"❌ 启动前端失败: {e}")

def main():
    """主函数"""
    print("=" * 50)
    print("🏦 财务报告系统启动器")
    print("=" * 50)
    
    # 检查后端服务
    if not check_backend_status():
        print("\n💡 解决方案:")
        print("1. 访问Render Dashboard手动启动后端服务")
        print("2. 等待3-5分钟后重新运行此脚本")
        print("3. 检查BACKEND_URL环境变量是否正确")
        sys.exit(1)
    
    # 启动前端服务
    start_frontend()

if __name__ == "__main__":
    main() 