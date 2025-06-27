"""
测试财务数据可视化API端点
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


@patch("src.visualization.plot_summary_graphs.plot_summary_graphs")
def test_generate_visualization_endpoint(mock_plot_graphs, client):
    """测试生成财务数据可视化API端点"""
    # 模拟plot_summary_graphs函数的返回值
    test_output_file = "test_visualization.docx"
    mock_plot_graphs.return_value = test_output_file
    
    # 创建测试文件
    with open("test_database.xlsx", "wb") as f:
        f.write(b"test database content")
    
    # 准备请求数据
    with open("test_database.xlsx", "rb") as database_file:
        files = {
            "database_file": ("test_database.xlsx", database_file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        }
        data = {
            "entity": "测试公司",
        }
        
        # 发送请求
        response = client.post("/finance/visualization/generate-visualization", files=files, data=data)
    
    # 清理测试文件
    os.remove("test_database.xlsx")
    
    # 验证响应
    assert response.status_code == 200
    
    # 验证函数调用
    mock_plot_graphs.assert_called_once()
    args, kwargs = mock_plot_graphs.call_args
    assert args[0].endswith("test_database.xlsx")
    assert args[1] == "测试公司" 