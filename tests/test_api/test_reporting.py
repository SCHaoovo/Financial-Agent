"""
测试财务分析报告API端点
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


@patch("src.reporting.generate_report_analysis.generate_report_analysis")
def test_generate_report_endpoint(mock_generate_report, client):
    """测试生成财务分析报告API端点"""
    # 模拟generate_report_analysis函数的返回值
    test_output_file = "test_report.docx"
    mock_generate_report.return_value = test_output_file
    
    # 创建测试文件
    with open("test_database.xlsx", "wb") as f:
        f.write(b"test database content")
    
    # 准备请求数据
    with open("test_database.xlsx", "rb") as database_file:
        files = {
            "database_file": ("test_database.xlsx", database_file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        }
        
        # 发送请求
        response = client.post("/finance/reporting/generate-report", files=files)
    
    # 清理测试文件
    os.remove("test_database.xlsx")
    
    # 验证响应
    assert response.status_code == 200
    
    # 验证函数调用
    mock_generate_report.assert_called_once()
    args, kwargs = mock_generate_report.call_args
    assert args[0].endswith("test_database.xlsx") 