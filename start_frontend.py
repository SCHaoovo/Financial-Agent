#!/usr/bin/env python3
"""
财务报告系统 Flask 前端启动脚本
"""

import os
import sys
import subprocess
import time

def check_python_version():
    """检查Python版本"""
    if sys.version_info < (3, 8):
        print("❌ 错误: 需要Python 3.8或更高版本")
        print(f"   当前版本: {sys.version}")
        sys.exit(1)
    print(f"✅ Python版本检查通过: {sys.version}")

def install_dependencies():
    """安装依赖"""
    print("\n📦 正在安装Flask前端依赖...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", 
            "flask_frontend/requirements.txt"
        ])
        print("✅ 依赖安装完成")
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        sys.exit(1)

def create_directories():
    """创建必要的目录"""
    print("\n📁 创建必要目录...")
    directories = [
        "flask_frontend/uploads",
        "flask_frontend/downloads",
        "flask_frontend/static/css",
        "flask_frontend/static/js",
        "flask_frontend/static/images"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"   ✅ {directory}")

def check_backend_status():
    """检查FastAPI后端是否运行"""
    print("\n🔗 检查FastAPI后端状态...")
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ FastAPI后端运行正常")
            return True
    except:
        pass
    
    print("⚠️  警告: FastAPI后端未运行 (http://localhost:8000)")
    print("   请确保先启动FastAPI后端服务")
    return False

def start_flask_app():
    """启动Flask应用"""
    print("\n🚀 启动Flask前端应用...")
    print("=" * 50)
    print("🌐 Flask前端将在以下地址运行:")
    print("   本地访问: http://localhost:5000")
    print("   网络访问: http://0.0.0.0:5000")
    print("=" * 50)
    print("📝 日志输出:")
    print("-" * 50)
    
    try:
        # 切换到flask_frontend目录
        os.chdir("flask_frontend")
        
        # 启动Flask应用
        subprocess.call([sys.executable, "app.py"])
        
    except KeyboardInterrupt:
        print("\n\n🛑 Flask应用已停止")
    except Exception as e:
        print(f"\n❌ Flask应用启动失败: {e}")
        sys.exit(1)

def main():
    """主函数"""
    print("🏦 财务报告系统 - Flask前端启动脚本")
    print("=" * 50)
    
    # 检查Python版本
    check_python_version()
    
    # 安装依赖
    install_dependencies()
    
    # 创建目录
    create_directories()
    
    # 检查后端状态
    backend_running = check_backend_status()
    
    if not backend_running:
        choice = input("\n❓ 是否仍要启动Flask前端? (y/n): ").lower().strip()
        if choice not in ['y', 'yes', '是']:
            print("🛑 启动已取消")
            sys.exit(0)
    
    # 启动Flask应用
    start_flask_app()

if __name__ == "__main__":
    main() 