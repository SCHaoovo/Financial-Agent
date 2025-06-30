"""
财务数据汇总API端点
"""

import os
import time
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
import tempfile
import shutil
import logging

from src.summary.generate_summary import generate_summary
from src.config import get_settings

router = APIRouter()
settings = get_settings()

# 设置日志
logger = logging.getLogger(__name__)


def safe_cleanup_temp_dir(temp_dir: str, max_retries: int = 3, delay: float = 0.5):
    """安全清理临时目录，处理Windows文件锁定问题"""
    for attempt in range(max_retries):
        try:
            if os.path.exists(temp_dir):
                # 等待一小段时间，确保文件句柄被释放
                time.sleep(delay)
                shutil.rmtree(temp_dir)
                logger.info(f"成功清理临时目录: {temp_dir}")
                return
        except PermissionError as e:
            if attempt < max_retries - 1:
                logger.warning(f"清理临时目录失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                time.sleep(delay * (attempt + 1))  # 逐步增加延迟
            else:
                logger.error(f"清理临时目录最终失败: {e}")
        except Exception as e:
            logger.error(f"清理临时目录时发生意外错误: {e}")
            break


class SummaryResponse(BaseModel):
    """汇总响应模型"""
    entity: str
    financial_year: str
    output_file: str
    status: str
    message: str


@router.post("/generate")
async def generate_summary_api(
    pl_file: UploadFile = File(..., description="利润表Excel文件"),
    bs_file: UploadFile = File(..., description="资产负债表Excel文件"),
    entity: str = Form(..., description="公司名称"),
    financial_year: str = Form(..., description="财务年度")
):
    """
    根据上传的PL和BS文件生成财务数据汇总
    
    参数:
    - **pl_file**: 利润表Excel文件
    - **bs_file**: 资产负债表Excel文件
    - **entity**: 公司名称
    - **financial_year**: 财务年度
    
    返回:
    - 汇总结果信息
    """
    temp_dir = None
    pl_file_path = None
    bs_file_path = None
    
    try:
        # 创建临时文件保存上传的文件
        temp_dir = tempfile.mkdtemp(prefix="summary_")
        logger.info(f"创建临时目录: {temp_dir}")
        
        # 保存PL文件
        pl_file_path = os.path.join(temp_dir, f"pl_{pl_file.filename}")
        with open(pl_file_path, "wb") as f:
            content = await pl_file.read()
            f.write(content)
        logger.info(f"PL文件已保存: {pl_file_path}")
        
        # 保存BS文件
        bs_file_path = os.path.join(temp_dir, f"bs_{bs_file.filename}")
        with open(bs_file_path, "wb") as f:
            content = await bs_file.read()
            f.write(content)
        logger.info(f"BS文件已保存: {bs_file_path}")
        
        # 确保文件句柄已关闭
        await pl_file.close()
        await bs_file.close()
        
        # 等待一小段时间确保文件系统同步
        time.sleep(0.1)
        
        # 生成汇总文件
        logger.info("开始生成汇总文件...")
        output_file = generate_summary(
            pl_file_path,
            bs_file_path,
            entity,
            financial_year
        )
        logger.info(f"汇总文件生成完成: {output_file}")
        
        # 提取文件名用于下载链接
        filename = os.path.basename(output_file)
        
        return SummaryResponse(
            entity=entity,
            financial_year=financial_year,
            output_file=filename,  # 只返回文件名，不是完整路径
            status="success",
            message=f"已成功生成{financial_year}年财务数据汇总。下载链接: /finance/summary/download/{filename}"
        )
    
    except Exception as e:
        logger.error(f"生成汇总时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # 安全清理临时文件
        if temp_dir:
            safe_cleanup_temp_dir(temp_dir)


@router.get("/download/{filename}")
async def download_summary(filename: str):
    """
    下载生成的汇总文件
    
    参数:
    - **filename**: 文件名
    
    返回:
    - 文件下载响应
    """
    try:
        # 构建文件路径
        file_path = os.path.join(settings.PROCESSED_DATA_DIR, "summary", filename)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"文件不存在: {filename}")
        
        # 添加更多的响应头支持
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Expose-Headers": "Content-Disposition",
                "Cache-Control": "no-cache"
            }
        )
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"下载文件时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_summaries():
    """
    列出所有可用的汇总文件
    
    返回:
    - 汇总文件列表
    """
    try:
        # 构建目录路径
        dir_path = os.path.join(settings.PROCESSED_DATA_DIR, "summary")
        
        # 确保目录存在
        os.makedirs(dir_path, exist_ok=True)
        
        # 获取文件列表
        files = []
        for file in os.listdir(dir_path):
            if file.endswith(".xlsx"):
                file_path = os.path.join(dir_path, file)
                file_stat = os.stat(file_path)
                files.append({
                    "name": file,
                    "size": file_stat.st_size,
                    "created_at": file_stat.st_ctime,
                    "path": file_path
                })
        
        return {"files": files}
    
    except Exception as e:
        logger.error(f"列出汇总文件时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))