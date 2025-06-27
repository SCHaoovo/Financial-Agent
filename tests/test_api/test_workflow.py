"""
财务数据处理工作流API端点测试
"""

import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import tempfile
import shutil

from src.main import app
from src.api.endpoints.workflow import workflow_tasks

client = TestClient(app)


@pytest.fixture
def temp_test_files():
    """创建临时测试文件"""
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    
    # 创建测试PL文件
    pl_file_path = os.path.join(temp_dir, "test_pl.xlsx")
    with open(pl_file_path, "wb") as f:
        f.write(b"Test PL file content")
    
    # 创建测试BS文件
    bs_file_path = os.path.join(temp_dir, "test_bs.xlsx")
    with open(bs_file_path, "wb") as f:
        f.write(b"Test BS file content")
    
    yield {"temp_dir": temp_dir, "pl_file": pl_file_path, "bs_file": bs_file_path}
    
    # 清理
    shutil.rmtree(temp_dir)


def test_start_workflow(temp_test_files):
    """测试启动工作流API"""
    with patch("src.api.endpoints.workflow.process_workflow") as mock_process:
        # 设置模拟函数
        mock_process.return_value = None
        
        # 准备测试文件
        pl_file_path = temp_test_files["pl_file"]
        bs_file_path = temp_test_files["bs_file"]
        
        # 发送请求
        with open(pl_file_path, "rb") as pl_file, open(bs_file_path, "rb") as bs_file:
            response = client.post(
                "/finance/workflow/start-workflow",
                data={
                    "entity": "TestCompany",
                    "financial_year": "2023"
                },
                files=[
                    ("pl_files", ("test_pl.xlsx", pl_file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
                    ("bs_files", ("test_bs.xlsx", bs_file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))
                ]
            )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "pending"
        
        # 验证任务创建
        assert data["task_id"] in workflow_tasks
        assert workflow_tasks[data["task_id"]]["status"] == "pending"


def test_start_workflow_missing_files():
    """测试缺少文件时的错误处理"""
    # 测试缺少PL文件
    response = client.post(
        "/finance/workflow/start-workflow",
        data={
            "entity": "TestCompany",
            "financial_year": "2023"
        },
        files=[
            ("bs_files", ("test_bs.xlsx", b"test content", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))
        ]
    )
    assert response.status_code == 400
    assert "利润表" in response.json()["detail"]
    
    # 测试缺少BS文件
    response = client.post(
        "/finance/workflow/start-workflow",
        data={
            "entity": "TestCompany",
            "financial_year": "2023"
        },
        files=[
            ("pl_files", ("test_pl.xlsx", b"test content", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))
        ]
    )
    assert response.status_code == 400
    assert "资产负债表" in response.json()["detail"]


@patch("uuid.uuid4")
def test_get_workflow_status(mock_uuid, temp_test_files):
    """测试获取工作流状态API"""
    # 设置模拟UUID
    mock_uuid.return_value = "test-task-id"
    
    # 创建测试任务
    workflow_tasks["test-task-id"] = {
        "status": "processing",
        "progress": "步骤2/4: 生成财务数据库"
    }
    
    # 发送请求
    response = client.get("/finance/workflow/workflow-status/test-task-id")
    
    # 验证响应
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "test-task-id"
    assert data["status"] == "processing"
    assert data["progress"] == "步骤2/4: 生成财务数据库"
    
    # 测试不存在的任务ID
    response = client.get("/finance/workflow/workflow-status/non-existent-id")
    assert response.status_code == 404


@patch("uuid.uuid4")
def test_get_workflow_result(mock_uuid):
    """测试获取工作流结果API"""
    # 设置模拟UUID
    mock_uuid.return_value = "test-result-id"
    
    # 创建测试任务结果
    workflow_tasks["test-result-id"] = {
        "status": "completed",
        "result": {
            "summary_files": ["path/to/summary1.xlsx", "path/to/summary2.xlsx"],
            "database_file": "path/to/database.xlsx",
            "visualization_file": "path/to/visualization.pdf",
            "report_file": "path/to/report.docx"
        }
    }
    
    # 发送请求
    response = client.get("/finance/workflow/workflow-result/test-result-id")
    
    # 验证响应
    assert response.status_code == 200
    data = response.json()
    assert "summary_files" in data
    assert "database_file" in data
    assert "visualization_file" in data
    assert "report_file" in data
    
    # 测试未完成的任务
    workflow_tasks["incomplete-id"] = {
        "status": "processing"
    }
    response = client.get("/finance/workflow/workflow-result/incomplete-id")
    assert response.status_code == 400


@patch("uuid.uuid4")
@patch("shutil.rmtree")
def test_delete_workflow(mock_rmtree, mock_uuid):
    """测试删除工作流API"""
    # 设置模拟UUID
    mock_uuid.return_value = "test-delete-id"
    
    # 创建测试任务
    temp_dir = tempfile.mkdtemp()
    workflow_tasks["test-delete-id"] = {
        "status": "completed",
        "temp_dir": temp_dir
    }
    
    # 发送请求
    response = client.delete("/finance/workflow/workflow/test-delete-id")
    
    # 验证响应
    assert response.status_code == 200
    assert "test-delete-id" not in workflow_tasks
    
    # 验证临时目录清理
    mock_rmtree.assert_called_once_with(temp_dir)
    
    # 测试不存在的任务ID
    response = client.delete("/finance/workflow/workflow/non-existent-id")
    assert response.status_code == 404 