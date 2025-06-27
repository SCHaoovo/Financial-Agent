"""
文件管理工具 - 优化 Render.com 上的文件存储
"""

import os
import shutil
import tempfile
import logging
from typing import Optional, Dict, Any
from pathlib import Path
import time
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class RenderFileManager:
    """Render.com 环境下的文件管理器"""
    
    def __init__(self):
        self.temp_dir = Path("/tmp/financial_app")
        self.temp_dir.mkdir(exist_ok=True)
        
    @contextmanager
    def temporary_workspace(self, prefix: str = "session_"):
        """创建临时工作空间，自动清理"""
        session_dir = None
        try:
            # 创建会话专用目录
            session_dir = self.temp_dir / f"{prefix}{int(time.time())}"
            session_dir.mkdir(exist_ok=True)
            
            logger.info(f"创建临时工作空间: {session_dir}")
            yield session_dir
            
        except Exception as e:
            logger.error(f"工作空间错误: {e}")
            raise
        finally:
            # 自动清理
            if session_dir and session_dir.exists():
                try:
                    shutil.rmtree(session_dir)
                    logger.info(f"清理工作空间: {session_dir}")
                except Exception as e:
                    logger.warning(f"清理失败: {e}")
    
    def process_uploaded_files_in_memory(self, files_dict: Dict[str, Any]) -> Dict[str, bytes]:
        """在内存中处理上传的文件"""
        processed_files = {}
        
        for key, file_obj in files_dict.items():
            if hasattr(file_obj, 'read'):
                # 读取文件内容到内存
                file_content = file_obj.read()
                processed_files[key] = file_content
                
                # 重置文件指针以备后用
                if hasattr(file_obj, 'seek'):
                    file_obj.seek(0)
                    
                logger.info(f"文件 {key} 已读取到内存 ({len(file_content)} 字节)")
        
        return processed_files
    
    def save_result_to_temp(self, content: bytes, filename: str, session_dir: Path) -> Path:
        """保存处理结果到临时目录"""
        file_path = session_dir / filename
        
        with open(file_path, 'wb') as f:
            f.write(content)
            
        logger.info(f"结果已保存: {file_path}")
        return file_path
    
    def cleanup_old_files(self, max_age_hours: int = 1):
        """清理超过指定时间的旧文件"""
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)
        
        for item in self.temp_dir.iterdir():
            if item.is_dir():
                try:
                    # 检查目录创建时间
                    dir_time = item.stat().st_mtime
                    if dir_time < cutoff_time:
                        shutil.rmtree(item)
                        logger.info(f"清理过期目录: {item}")
                except Exception as e:
                    logger.warning(f"清理目录失败 {item}: {e}")
    
    def get_storage_info(self) -> Dict[str, Any]:
        """获取存储使用情况"""
        try:
            stat = shutil.disk_usage(self.temp_dir)
            total_gb = stat.total / (1024**3)
            free_gb = stat.free / (1024**3)
            used_gb = (stat.total - stat.free) / (1024**3)
            
            return {
                "total_gb": round(total_gb, 2),
                "used_gb": round(used_gb, 2),
                "free_gb": round(free_gb, 2),
                "usage_percent": round((used_gb / total_gb) * 100, 2)
            }
        except Exception as e:
            logger.error(f"获取存储信息失败: {e}")
            return {"error": str(e)}

# 全局实例
file_manager = RenderFileManager()


def memory_based_file_processor(files_dict: Dict[str, Any]) -> Dict[str, Any]:
    """基于内存的文件处理器示例"""
    
    with file_manager.temporary_workspace("processing_") as workspace:
        # 1. 将文件读取到内存
        file_contents = file_manager.process_uploaded_files_in_memory(files_dict)
        
        # 2. 处理逻辑（示例）
        results = {}
        for filename, content in file_contents.items():
            # 这里是你的实际处理逻辑
            # 例如：Excel 分析、报告生成等
            processed_content = process_file_content(content)
            
            # 3. 如果需要，保存临时结果
            if processed_content:
                result_path = file_manager.save_result_to_temp(
                    processed_content, 
                    f"result_{filename}", 
                    workspace
                )
                results[filename] = result_path
        
        return results


def process_file_content(content: bytes) -> Optional[bytes]:
    """文件内容处理逻辑占位符"""
    # 这里实现你的具体处理逻辑
    # 例如：pandas.read_excel(io.BytesIO(content))
    logger.info(f"处理文件内容 ({len(content)} 字节)")
    return content  # 占位符返回 