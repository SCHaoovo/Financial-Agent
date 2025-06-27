"""
测试财务数据汇总API端点
"""

import os
import pytest
from fastapi.testclient import TestClient
import tempfile
import shutil
from unittest.mock import patch

from src.main import app
from src.api.endpoints.summary import generate_summary_api

client = TestClient(app)


@pytest.fixture
def test_files():
    """创建测试文件"""
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


@patch("src.api.endpoints.summary.generate_summary")
def test_generate_summary_api(mock_generate_summary, test_files):
    """测试生成汇总API端点"""
    # 设置模拟函数返回值
    mock_generate_summary.return_value = "/path/to/output.xlsx"
    
    # 准备测试文件
    pl_file_path = test_files["pl_file"]
    bs_file_path = test_files["bs_file"]
    
    # 发送请求
    with open(pl_file_path, "rb") as pl_file, open(bs_file_path, "rb") as bs_file:
        response = client.post(
            "/finance/summary/generate",
            data={
                "entity": "TestCompany",
                "financial_year": "2023"
            },
            files={
                "pl_file": ("test_pl.xlsx", pl_file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                "bs_file": ("test_bs.xlsx", bs_file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            }
        )
    
    # 验证响应
    assert response.status_code == 200
    data = response.json()
    assert data["entity"] == "TestCompany"
    assert data["financial_year"] == "2023"
    assert data["status"] == "success"
    
    # 验证模拟函数调用
    mock_generate_summary.assert_called_once()
    args, _ = mock_generate_summary.call_args
    assert "test_pl.xlsx" in args[0]
    assert "test_bs.xlsx" in args[1]
    assert args[2] == "TestCompany"
    assert args[3] == "2023"


@patch("os.path.exists")
@patch("os.listdir")
@patch("os.stat")
def test_list_summaries(mock_stat, mock_listdir, mock_exists):
    """测试列出汇总文件API端点"""
    # 设置模拟函数
    mock_exists.return_value = True
    mock_listdir.return_value = ["file1.xlsx", "file2.xlsx", "file3.txt"]
    
    # 模拟文件状态
    class MockStat:
        st_size = 1024
        st_ctime = 1609459200  # 2021-01-01
    
    mock_stat.return_value = MockStat()
    
    # 发送请求
    response = client.get("/finance/summary/list")
    
    # 验证响应
    assert response.status_code == 200
    data = response.json()
    assert "files" in data
    assert len(data["files"]) == 2  # 只有两个.xlsx文件
    assert data["files"][0]["name"] == "file1.xlsx"
    assert data["files"][1]["name"] == "file2.xlsx"


@patch("os.path.exists")
def test_download_summary_not_found(mock_exists):
    """测试下载不存在的汇总文件"""
    # 设置模拟函数
    mock_exists.return_value = False
    
    # 发送请求
    response = client.get("/finance/summary/download/nonexistent.xlsx")
    
    # 验证响应
    assert response.status_code == 404
    assert "不存在" in response.json()["detail"] 