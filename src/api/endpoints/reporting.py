"""
财务分析报告API端点
"""

import os
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
import tempfile
import shutil
from pydantic import BaseModel

from src.reporting.generate_report_analysis import generate_report_analysis
from src.config import get_settings

router = APIRouter()
settings = get_settings()


class ReportResponse(BaseModel):
    """报告响应模型"""
    output_file: str
    status: str
    message: str


@router.post("/generate-report")
async def generate_report_api(
    database_file: UploadFile = File(..., description="财务数据库Excel文件"),
    output_filename: Optional[str] = Form(None, description="输出文件名（可选）")
):
    """
    生成财务分析报告
    
    参数:
    - **database_file**: 财务数据库Excel文件
    - **output_filename**: 输出文件名（可选）
    
    返回:
    - 分析报告文档文件下载
    """
    try:
        # 检查是否有上传文件
        if not database_file:
            raise HTTPException(status_code=400, detail="请上传财务数据库Excel文件")
            
        # 创建临时目录保存上传的文件
        with tempfile.TemporaryDirectory() as temp_dir:
            # 保存数据库文件
            file_name = database_file.filename
            database_path = os.path.join(temp_dir, file_name)
            
            # 确保文件正确保存并关闭句柄
            with open(database_path, "wb") as f:
                shutil.copyfileobj(database_file.file, f)
            
            # 确保上传文件的句柄被关闭
            database_file.file.close()
            
            # 设置输出文件路径
            if output_filename:
                output_file = output_filename
                if not output_file.endswith('.docx'):
                    output_file += '.docx'
            else:
                # 使用输入文件名作为输出文件名的一部分
                file_name_without_ext = os.path.splitext(file_name)[0]
                output_file = f"Report_{file_name_without_ext}.docx"
            
            # 使用processed目录下的reports子目录
            reports_dir = os.path.join(settings.PROCESSED_DATA_DIR, "reports")
            os.makedirs(reports_dir, exist_ok=True)
            output_path = os.path.join(reports_dir, output_file)
            
            # 处理Excel文件 - 生成分析报告
            try:
                output_file_path = generate_report_analysis(
                    database_path,
                    output_path
                )
                
                # 返回文件下载
                return FileResponse(
                    path=output_file_path, 
                    filename=os.path.basename(output_file_path),
                    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"处理Excel文件时出错: {str(e)}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 