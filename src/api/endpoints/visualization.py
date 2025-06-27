"""
财务数据可视化API端点
"""

import os
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
import tempfile
import shutil
from pydantic import BaseModel

from src.visualization.plot_summary_graphs import plot_summary_graphs
from src.config import get_settings

router = APIRouter()
settings = get_settings()


class VisualizationResponse(BaseModel):
    """可视化响应模型"""
    entity: str
    output_file: str
    status: str
    message: str


@router.post("/generate-visualization")
async def generate_visualization_api(
    entity: str = Form(..., description="公司名称"),
    database_file: UploadFile = File(..., description="财务数据库Excel文件"),
    output_filename: Optional[str] = Form(None, description="输出文件名（可选）")
):
    """
    生成财务数据可视化图表
    
    参数:
    - **entity**: 公司名称
    - **database_file**: 财务数据库Excel文件
    - **output_filename**: 输出文件名（可选）
    
    返回:
    - 可视化文档文件下载
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
            with open(database_path, "wb") as f:
                shutil.copyfileobj(database_file.file, f)
            
            # 设置输出文件路径
            if output_filename:
                output_file = output_filename
                if not output_file.endswith('.docx'):
                    output_file += '.docx'
            else:
                output_file = f"Visualization_{entity}.docx"
            
            # 使用processed目录下的visualization子目录
            visualization_dir = os.path.join(settings.PROCESSED_DATA_DIR, "visualization")
            os.makedirs(visualization_dir, exist_ok=True)
            output_path = os.path.join(visualization_dir, output_file)
            
            # 处理Excel文件 - 生成可视化图表
            try:
                output_file_path = plot_summary_graphs(
                    database_path,
                    entity,
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