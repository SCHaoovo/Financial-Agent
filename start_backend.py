#!/usr/bin/env python3
"""
Financial Backend for Render.com deployment
"""

import os
import sys
import uvicorn
from src.main import app

def main():
    """启动 FastAPI 应用"""
    # 获取 Render 提供的端口，默认 8000
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    
    print(f"🚀 启动 Financial Backend 在 {host}:{port}")
    
    # 启动应用
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main() 