"""
财务数据处理工作流API端点 - 集成所有处理步骤
"""

import os
from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
import tempfile
import shutil
from pydantic import BaseModel
import logging
import uuid

from src.summary.generate_summary import generate_summary
from src.database.generate_financial_database import generate_financial_database
from src.visualization.plot_summary_graphs import plot_summary_graphs
from src.reporting.generate_report_analysis import generate_report_analysis
from src.config import get_settings

router = APIRouter()
settings = get_settings()

# 设置日志
logger = logging.getLogger(__name__)


class WorkflowResponse(BaseModel):
    """工作流响应模型"""
    task_id: str
    status: str
    message: str


class WorkflowResult(BaseModel):
    """工作流结果模型"""
    summary_files: List[str]
    database_file: str
    visualization_file: str
    report_file: str


# 存储任务状态和结果
workflow_tasks = {}


async def process_workflow(
    task_id: str,
    pl_file_paths: List[str],
    bs_file_paths: List[str],
    entity: str,
    financial_year: str,
    temp_dir: str
):
    """
    后台处理工作流任务
    
    Args:
        task_id: 任务ID
        pl_file_paths: 利润表文件路径列表
        bs_file_paths: 资产负债表文件路径列表
        entity: 实体名称
        financial_year: 财务年度
        temp_dir: 临时目录路径
    """
    try:
        logger.info(f"=== 开始后台处理工作流任务 {task_id} ===")
        logger.info(f"文件路径: PL={pl_file_paths}, BS={bs_file_paths}")
        logger.info(f"参数: entity={entity}, financial_year={financial_year}")
        
        workflow_tasks[task_id]["status"] = "processing"
        workflow_tasks[task_id]["progress"] = "步骤1/4: 生成汇总表"
        logger.info("步骤1/4: 开始生成汇总表")
        
        # 步骤1: 生成汇总表 - 成对处理PL和BS文件
        summary_files = []
        for i in range(min(len(pl_file_paths), len(bs_file_paths))):
            try:
                logger.info(f"处理文件对 {i+1}: PL={pl_file_paths[i]}, BS={bs_file_paths[i]}")
                summary_file = generate_summary(
                    pl_file_paths[i], 
                    bs_file_paths[i], 
                    entity, 
                    financial_year
                )
                summary_files.append(summary_file)
                logger.info(f"成功生成汇总表 {i+1}/{min(len(pl_file_paths), len(bs_file_paths))}: {summary_file}")
            except Exception as e:
                logger.error(f"处理文件对 {i+1} 时出错: {str(e)}")
                logger.exception(f"文件对 {i+1} 详细错误信息:")
                raise
        
        logger.info(f"汇总表生成完成，共生成 {len(summary_files)} 个文件")
        workflow_tasks[task_id]["progress"] = "步骤2/4: 生成财务数据库"
        logger.info("步骤2/4: 开始生成财务数据库")
        
        # 步骤2: 生成财务数据库
        database_file = generate_financial_database(summary_files, entity)
        logger.info(f"财务数据库生成完成: {database_file}")
        
        workflow_tasks[task_id]["progress"] = "步骤3/4: 生成可视化图表"
        logger.info("步骤3/4: 开始生成可视化图表")
        
        # 步骤3: 生成可视化图表
        visualization_file = plot_summary_graphs(database_file, entity)
        logger.info(f"可视化图表生成完成: {visualization_file}")
        
        workflow_tasks[task_id]["progress"] = "步骤4/4: 生成分析报告"
        logger.info("步骤4/4: 开始生成分析报告")
        
        # 步骤4: 生成分析报告
        report_file = generate_report_analysis(database_file)
        logger.info(f"分析报告生成完成: {report_file}")
        
        # 更新任务状态和结果
        workflow_tasks[task_id]["status"] = "completed"
        workflow_tasks[task_id]["result"] = {
            "summary_files": summary_files,
            "database_file": database_file,
            "visualization_file": visualization_file,
            "report_file": report_file
        }
        workflow_tasks[task_id]["progress"] = "完成"
        
        logger.info(f"=== 工作流任务 {task_id} 完成 ===")
        logger.info(f"结果: {workflow_tasks[task_id]['result']}")
        
    except Exception as e:
        logger.error(f"工作流处理出错 (任务ID: {task_id}): {str(e)}")
        logger.exception("工作流处理详细错误信息:")
        workflow_tasks[task_id]["status"] = "failed"
        workflow_tasks[task_id]["error"] = str(e)


@router.post("/start-workflow", response_model=WorkflowResponse)
async def start_workflow_api(
    background_tasks: BackgroundTasks,
    entity: str = Form(..., description="公司名称"),
    financial_year: str = Form(..., description="财务年度"),
    pl_files: List[UploadFile] = File(..., description="利润表Excel文件列表"),
    bs_files: List[UploadFile] = File(..., description="资产负债表Excel文件列表")
):
    """
    启动完整的财务数据处理工作流
    
    参数:
    - **entity**: 公司名称
    - **financial_year**: 财务年度
    - **pl_files**: 利润表Excel文件列表
    - **bs_files**: 资产负债表Excel文件列表
    
    返回:
    - 任务ID和状态信息
    """
    try:
        # 检查是否有上传文件
        if not pl_files or len(pl_files) == 0:
            raise HTTPException(status_code=400, detail="请至少上传一个利润表Excel文件")
        if not bs_files or len(bs_files) == 0:
            raise HTTPException(status_code=400, detail="请至少上传一个资产负债表Excel文件")
        
        # 检查PL和BS文件数量是否匹配
        if len(pl_files) != len(bs_files):
            logger.warning(f"利润表和资产负债表文件数量不匹配: PL={len(pl_files)}, BS={len(bs_files)}")
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 创建临时目录保存上传的文件
        temp_dir = tempfile.mkdtemp()
        
        # 保存所有PL文件
        pl_file_paths = []
        for i, pl_file in enumerate(pl_files):
            file_path = os.path.join(temp_dir, f"pl_{i}_{pl_file.filename}")
            with open(file_path, "wb") as f:
                shutil.copyfileobj(pl_file.file, f)
            # 确保上传文件的句柄被关闭
            pl_file.file.close()
            pl_file_paths.append(file_path)
        
        # 保存所有BS文件
        bs_file_paths = []
        for i, bs_file in enumerate(bs_files):
            file_path = os.path.join(temp_dir, f"bs_{i}_{bs_file.filename}")
            with open(file_path, "wb") as f:
                shutil.copyfileobj(bs_file.file, f)
            # 确保上传文件的句柄被关闭
            bs_file.file.close()
            bs_file_paths.append(file_path)
        
        # 初始化任务状态
        workflow_tasks[task_id] = {
            "status": "pending",
            "progress": "初始化中",
            "temp_dir": temp_dir
        }
        
        # 启动后台任务
        background_tasks.add_task(
            process_workflow,
            task_id,
            pl_file_paths,
            bs_file_paths,
            entity,
            financial_year,
            temp_dir
        )
        
        return WorkflowResponse(
            task_id=task_id,
            status="pending",
            message="工作流已启动，请使用任务ID查询进度"
        )
        
    except Exception as e:
        logger.error(f"启动工作流时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute-workflow", response_model=WorkflowResponse)
async def execute_workflow_api(
    background_tasks: BackgroundTasks,
    entity: str = Form(..., description="公司名称"),
    financial_year: str = Form(None, description="财务年度（可选）"),
    # 支持单个文件输入（前端兼容性）
    pl_file: Optional[UploadFile] = File(None, description="利润表Excel文件"),
    bs_file: Optional[UploadFile] = File(None, description="资产负债表Excel文件"),
    # 支持文件列表输入
    pl_files: Optional[List[UploadFile]] = File(None, description="利润表Excel文件列表"),
    bs_files: Optional[List[UploadFile]] = File(None, description="资产负债表Excel文件列表")
):
    """
    执行完整的财务数据处理工作流（与start-workflow功能相同，用于兼容前端调用）
    
    参数:
    - **entity**: 公司名称
    - **financial_year**: 财务年度（可选）
    - **pl_file**: 利润表Excel文件（单个文件）
    - **bs_file**: 资产负债表Excel文件（单个文件）
    - **pl_files**: 利润表Excel文件列表
    - **bs_files**: 资产负债表Excel文件列表
    
    返回:
    - 任务ID和状态信息
    """
    try:
        logger.info(f"=== 开始执行工作流 ===")
        logger.info(f"接收到的参数: entity={entity}, financial_year={financial_year}")
        logger.info(f"单个文件: pl_file={pl_file.filename if pl_file else None}, bs_file={bs_file.filename if bs_file else None}")
        logger.info(f"文件列表: pl_files数量={len(pl_files) if pl_files else 0}, bs_files数量={len(bs_files) if bs_files else 0}")
        
        # 处理文件输入 - 支持单个文件或文件列表
        final_pl_files = []
        final_bs_files = []
        
        # 如果提供了单个文件，将其转换为列表
        if pl_file and bs_file:
            final_pl_files = [pl_file]
            final_bs_files = [bs_file]
            logger.info("使用单个文件输入模式")
        # 如果提供了文件列表，使用文件列表
        elif pl_files and bs_files:
            final_pl_files = pl_files
            final_bs_files = bs_files
            logger.info("使用文件列表输入模式")
        else:
            logger.error("未提供有效的文件输入")
            raise HTTPException(status_code=400, detail="请提供PL和BS文件（单个文件或文件列表）")
        
        # 检查文件数量
        if not final_pl_files or len(final_pl_files) == 0:
            logger.error("PL文件列表为空")
            raise HTTPException(status_code=400, detail="请至少上传一个利润表Excel文件")
        if not final_bs_files or len(final_bs_files) == 0:
            logger.error("BS文件列表为空")
            raise HTTPException(status_code=400, detail="请至少上传一个资产负债表Excel文件")
        
        logger.info(f"最终文件数量: PL={len(final_pl_files)}, BS={len(final_bs_files)}")
        
        # 检查PL和BS文件数量是否匹配
        if len(final_pl_files) != len(final_bs_files):
            logger.warning(f"利润表和资产负债表文件数量不匹配: PL={len(final_pl_files)}, BS={len(final_bs_files)}")
        
        # 如果没有提供财务年度，使用默认值
        if not financial_year:
            financial_year = "2024"
            logger.info(f"未提供财务年度，使用默认值: {financial_year}")
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        logger.info(f"生成任务ID: {task_id}")
        
        # 创建临时目录保存上传的文件
        temp_dir = tempfile.mkdtemp()
        logger.info(f"创建临时目录: {temp_dir}")
        
        # 保存所有PL文件
        pl_file_paths = []
        for i, pl_file_item in enumerate(final_pl_files):
            file_path = os.path.join(temp_dir, f"pl_{i}_{pl_file_item.filename}")
            logger.info(f"保存PL文件 {i+1}: {file_path}")
            with open(file_path, "wb") as f:
                shutil.copyfileobj(pl_file_item.file, f)
            # 确保上传文件的句柄被关闭
            pl_file_item.file.close()
            pl_file_paths.append(file_path)
            logger.info(f"PL文件 {i+1} 保存成功")
        
        # 保存所有BS文件
        bs_file_paths = []
        for i, bs_file_item in enumerate(final_bs_files):
            file_path = os.path.join(temp_dir, f"bs_{i}_{bs_file_item.filename}")
            logger.info(f"保存BS文件 {i+1}: {file_path}")
            with open(file_path, "wb") as f:
                shutil.copyfileobj(bs_file_item.file, f)
            # 确保上传文件的句柄被关闭
            bs_file_item.file.close()
            bs_file_paths.append(file_path)
            logger.info(f"BS文件 {i+1} 保存成功")
        
        # 初始化任务状态
        workflow_tasks[task_id] = {
            "status": "pending",
            "progress": "初始化中",
            "temp_dir": temp_dir
        }
        logger.info(f"初始化任务状态: {workflow_tasks[task_id]}")
        
        # 启动后台任务
        logger.info("启动后台处理任务")
        background_tasks.add_task(
            process_workflow,
            task_id,
            pl_file_paths,
            bs_file_paths,
            entity,
            financial_year,
            temp_dir
        )
        
        logger.info(f"工作流启动成功，任务ID: {task_id}")
        return WorkflowResponse(
            task_id=task_id,
            status="pending",
            message="工作流已启动，请使用任务ID查询进度"
        )
        
    except Exception as e:
        logger.error(f"执行工作流时出错: {str(e)}")
        logger.exception("详细错误信息:")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflow-status/{task_id}")
async def get_workflow_status(task_id: str):
    """
    获取工作流任务状态
    
    参数:
    - **task_id**: 任务ID
    
    返回:
    - 任务状态和进度信息
    """
    if task_id not in workflow_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task_info = workflow_tasks[task_id]
    
    response = {
        "task_id": task_id,
        "status": task_info["status"],
        "progress": task_info.get("progress", "")
    }
    
    # 如果任务完成，添加结果链接
    if task_info["status"] == "completed" and "result" in task_info:
        response["result"] = task_info["result"]
    
    # 如果任务失败，添加错误信息
    if task_info["status"] == "failed" and "error" in task_info:
        response["error"] = task_info["error"]
    
    return response


@router.get("/workflow-result/{task_id}")
async def get_workflow_result(task_id: str):
    """
    获取工作流任务结果
    
    参数:
    - **task_id**: 任务ID
    
    返回:
    - 任务结果，包含所有生成的文件路径
    """
    if task_id not in workflow_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task_info = workflow_tasks[task_id]
    
    if task_info["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"任务尚未完成，当前状态: {task_info['status']}")
    
    if "result" not in task_info:
        raise HTTPException(status_code=500, detail="任务结果不可用")
    
    return task_info["result"]


@router.delete("/workflow/{task_id}")
async def delete_workflow(task_id: str):
    """
    删除工作流任务及其资源
    
    参数:
    - **task_id**: 任务ID
    
    返回:
    - 操作结果
    """
    if task_id not in workflow_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task_info = workflow_tasks[task_id]
    
    # 清理临时目录
    if "temp_dir" in task_info and os.path.exists(task_info["temp_dir"]):
        try:
            shutil.rmtree(task_info["temp_dir"])
        except Exception as e:
            logger.error(f"清理临时目录时出错: {str(e)}")
    
    # 从字典中删除任务
    del workflow_tasks[task_id]
    
    return {"message": "任务已删除"} 