"""
测试财务数据库API端点
"""

import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.main import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@patch("src.database.generate_financial_database.generate_financial_database")
def test_generate_database_endpoint(mock_generate_database, client):
    """测试生成财务数据库API端点"""
    # 模拟generate_financial_database函数的返回值
    test_output_file = "test_output.xlsx"
    mock_generate_database.return_value = test_output_file
    
    # 创建测试文件
    with open("test_summary1.xlsx", "wb") as f:
        f.write(b"test summary content 1")
    with open("test_summary2.xlsx", "wb") as f:
        f.write(b"test summary content 2")
    
    # 准备请求数据
    with open("test_summary1.xlsx", "rb") as summary_file1, open("test_summary2.xlsx", "rb") as summary_file2:
        files = [
            ("summary_files", ("test_summary1.xlsx", summary_file1, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
            ("summary_files", ("test_summary2.xlsx", summary_file2, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))
        ]
        data = {
            "entity": "测试公司",
        }
        
        # 发送请求
        response = client.post("/finance/database/generate-database", files=files, data=data)
    
    # 清理测试文件
    os.remove("test_summary1.xlsx")
    os.remove("test_summary2.xlsx")
    
    # 验证响应
    assert response.status_code == 200
    
    # 验证函数调用
    mock_generate_database.assert_called_once()
    args, kwargs = mock_generate_database.call_args
    assert kwargs["entity"] == "测试公司"
    assert len(args[0]) == 2  # 确认传入了两个文件路径