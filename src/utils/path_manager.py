"""
路径管理工具
统一处理本地开发和 Render.com 生产环境的路径差异
"""

import os
from pathlib import Path
from typing import Optional
from src.config import get_settings

class PathManager:
    """环境感知的路径管理器"""
    
    def __init__(self):
        self.settings = get_settings()
        self.is_production = os.getenv('ENVIRONMENT') == 'production'
    
    def get_upload_dir(self) -> Path:
        """获取上传目录路径"""
        if self.is_production:
            return Path('/tmp/financial_app/uploads')
        return Path('uploads')
    
    def get_download_dir(self) -> Path:
        """获取下载目录路径"""
        if self.is_production:
            return Path('/tmp/financial_app/downloads')
        return Path('downloads')
    
    def get_data_dir(self) -> Path:
        """获取数据根目录路径"""
        return Path(self.settings.DATA_DIR)
    
    def get_input_dir(self) -> Path:
        """获取输入数据目录路径"""
        return Path(self.settings.INPUT_DATA_DIR)
    
    def get_processed_dir(self, subdir: Optional[str] = None) -> Path:
        """获取处理后数据目录路径"""
        base_path = Path(self.settings.PROCESSED_DATA_DIR)
        if subdir:
            return base_path / subdir
        return base_path
    
    def ensure_dir_exists(self, path: Path) -> Path:
        """确保目录存在，如果不存在则创建"""
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def get_temp_dir(self) -> Path:
        """获取临时目录路径"""
        if self.is_production:
            return Path('/tmp/financial_app_temp')
        return Path('temp')
    
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """清理过期的临时文件"""
        import time
        temp_dir = self.get_temp_dir()
        
        if not temp_dir.exists():
            return
        
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)
        
        for file_path in temp_dir.rglob('*'):
            if file_path.is_file():
                try:
                    if file_path.stat().st_mtime < cutoff_time:
                        file_path.unlink()
                        print(f"已删除过期文件: {file_path}")
                except Exception as e:
                    print(f"删除文件失败 {file_path}: {e}")

# 全局实例
path_manager = PathManager()

def get_path_manager() -> PathManager:
    """获取路径管理器实例"""
    return path_manager 