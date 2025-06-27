"""
财务数据库生成API端点
"""

import os
from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
import tempfile
import shutil
from pydantic import BaseModel

from src.database.generate_financial_database import generate_financial_database
from src.config import get_settings

router = APIRouter()
settings = get_settings()


class DatabaseResponse(BaseModel):
    """数据库响应模型"""
    entity: str
    output_file: str
    status: str
    message: str


@router.post("/generate-database")
async def generate_database_api(
    entity: str = Form(..., description="公司名称"),
    summary_files: List[UploadFile] = File(..., description="汇总Excel文件列表"),
    output_filename: Optional[str] = Form(None, description="输出文件名（可选）")
):
    """
    生成标准化财务数据库
    
    参数:
    - **entity**: 公司名称
    - **summary_files**: 汇总Excel文件列表（可上传多个文件）
    - **output_filename**: 输出文件名（可选）
    
    返回:
    - 数据库文件下载
    """
    try:
        # 检查是否有上传文件
        if not summary_files or len(summary_files) == 0:
            raise HTTPException(status_code=400, detail="请至少上传一个汇总Excel文件")
            
        # 创建临时目录保存上传的文件
        with tempfile.TemporaryDirectory() as temp_dir:
            # 保存所有Summary文件
            summary_paths = []
            for i, summary_file in enumerate(summary_files):
                # 使用原始文件名，避免文件名冲突
                file_name = f"{i}_{summary_file.filename}"
                summary_path = os.path.join(temp_dir, file_name)
                with open(summary_path, "wb") as f:
                    shutil.copyfileobj(summary_file.file, f)
                summary_paths.append(summary_path)
            
            # 设置输出文件路径
            if output_filename:
                output_file = output_filename
                if not output_file.endswith('.xlsx'):
                    output_file += '.xlsx'
            else:
                output_file = f"DB_{entity}.xlsx"
            
            # 使用processed目录下的database子目录
            database_dir = os.path.join(settings.PROCESSED_DATA_DIR, "database")
            os.makedirs(database_dir, exist_ok=True)
            output_path = os.path.join(database_dir, output_file)
            
            # 处理Excel文件 - 生成财务数据库
            try:
                output_file_path = generate_financial_database(
                    summary_paths,
                    entity,
                    output_path
                )
                
                # 返回文件下载
                return FileResponse(
                    path=output_file_path, 
                    filename=os.path.basename(output_file_path),
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"处理Excel文件时出错: {str(e)}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))