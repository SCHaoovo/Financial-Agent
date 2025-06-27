"""
Financial Reporting Agent 配置模块
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    """应用设置"""
    
    # API配置
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Financial Reporting Agent"
    
    # 环境检测
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # 路径配置 - 适应 Render 部署环境
    BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
    
    # 在 Render 上使用临时目录
    if ENVIRONMENT == "production":
        DATA_DIR: str = "/tmp/data"
    else:
        DATA_DIR: str = os.path.join(os.path.dirname(BASE_DIR), "data")
    
    INPUT_DATA_DIR: str = os.path.join(DATA_DIR, "input")
    PROCESSED_DATA_DIR: str = os.path.join(DATA_DIR, "processed")
    CONFIG_DIR: str = os.path.join(os.path.dirname(BASE_DIR), "config")
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    
    # API配置 - 支持多个 AI 服务
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # 代理配置（生产环境中通常不需要）
    HTTP_PROXY: Optional[str] = None if ENVIRONMENT == "production" else os.getenv("HTTP_PROXY")
    HTTPS_PROXY: Optional[str] = None if ENVIRONMENT == "production" else os.getenv("HTTPS_PROXY")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """获取缓存的设置实例"""
    return Settings()

# 创建必要的目录
def create_directories():
    """创建必要的目录"""
    settings = get_settings()
    try:
        os.makedirs(settings.INPUT_DATA_DIR, exist_ok=True)
        os.makedirs(settings.PROCESSED_DATA_DIR, exist_ok=True)
        print(f"✅ 目录创建成功: {settings.DATA_DIR}")
    except Exception as e:
        print(f"⚠️ 目录创建警告: {e}")

# 在模块导入时创建目录
create_directories() 