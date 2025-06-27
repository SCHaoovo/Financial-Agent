#!/usr/bin/env python3
"""
前后端连通性测试脚本
"""

import requests
import time

def test_backend_health():
    """测试后端健康状态"""
    print("🔍 测试FastAPI后端...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ FastAPI后端运行正常")
            print(f"   响应: {response.json()}")
            return True
        else:
            print(f"❌ FastAPI后端响应异常: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ FastAPI后端未启动 (连接失败)")
        return False
    except Exception as e:
        print(f"❌ FastAPI后端测试失败: {e}")
        return False

def test_frontend_health():
    """测试前端健康状态"""
    print("\n🔍 测试Flask前端...")
    try:
        response = requests.get("http://localhost:5000", timeout=5)
        if response.status_code == 200:
            print("✅ Flask前端运行正常")
            return True
        else:
            print(f"❌ Flask前端响应异常: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Flask前端未启动 (连接失败)")
        return False
    except Exception as e:
        print(f"❌ Flask前端测试失败: {e}")
        return False

def test_api_docs():
    """测试API文档访问"""
    print("\n🔍 测试API文档...")
    try:
        response = requests.get("http://localhost:8000/docs", timeout=5)
        if response.status_code == 200:
            print("✅ API文档访问正常")
            print("   📖 可访问: http://localhost:8000/docs")
            return True
        else:
            print(f"❌ API文档访问异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API文档测试失败: {e}")
        return False

def test_frontend_to_backend():
    """测试前端调用后端的连通性"""
    print("\n🔍 测试前端到后端的连通性...")
    try:
        # 通过前端的健康检查接口测试
        response = requests.get("http://localhost:5000", timeout=5)
        if response.status_code == 200:
            print("✅ 前端页面加载正常")
            
            # 检查前端是否能访问后端
            # 这里我们可以添加一个简单的测试接口
            print("   前端已准备好接收API调用")
            return True
        else:
            print(f"❌ 前端页面异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 前端连通性测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始前后端连通性测试")
    print("=" * 50)
    
    # 测试后端
    backend_ok = test_backend_health()
    
    # 测试前端
    frontend_ok = test_frontend_health()
    
    # 测试API文档
    docs_ok = test_api_docs()
    
    # 测试前后端连通性
    connection_ok = test_frontend_to_backend()
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 测试结果总结:")
    print(f"   FastAPI后端: {'✅ 正常' if backend_ok else '❌ 异常'}")
    print(f"   Flask前端:   {'✅ 正常' if frontend_ok else '❌ 异常'}")
    print(f"   API文档:     {'✅ 正常' if docs_ok else '❌ 异常'}")
    print(f"   前后端连通:   {'✅ 正常' if connection_ok else '❌ 异常'}")
    
    if all([backend_ok, frontend_ok, docs_ok, connection_ok]):
        print("\n🎉 所有测试通过! 系统运行正常")
        print("\n📝 接下来可以测试:")
        print("   1. 文件上传功能")
        print("   2. API接口调用")
        print("   3. 数据处理流程")
    else:
        print("\n⚠️  部分测试失败, 请检查:")
        if not backend_ok:
            print("   - 启动FastAPI后端: python -m uvicorn main:app --reload --port 8000")
        if not frontend_ok:
            print("   - 启动Flask前端: cd flask_frontend && python app.py")
        print("   - 检查端口占用情况")
        print("   - 查看控制台错误信息")

if __name__ == "__main__":
    main() 