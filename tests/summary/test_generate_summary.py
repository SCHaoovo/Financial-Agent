"""
测试财务数据汇总模块
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import tempfile
import shutil

from src.summary.generate_summary import generate_summary


class TestGenerateSummary(unittest.TestCase):
    """测试财务数据汇总功能"""
    
    def setUp(self):
        """测试前准备工作"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        
        # 创建测试文件
        self.pl_file = os.path.join(self.temp_dir, "test_pl.xlsx")
        self.bs_file = os.path.join(self.temp_dir, "test_bs.xlsx")
        
        # 创建空文件用于测试
        with open(self.pl_file, "wb") as f:
            f.write(b"test")
        with open(self.bs_file, "wb") as f:
            f.write(b"test")
    
    def tearDown(self):
        """测试后清理工作"""
        # 删除临时目录
        shutil.rmtree(self.temp_dir)
    
    @patch("src.summary.generate_summary.OpenAI")
    def test_generate_summary(self, mock_openai):
        """测试使用OpenAI生成财务数据汇总"""
        # 模拟OpenAI客户端
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # 模拟文件上传响应
        mock_resp1 = MagicMock()
        mock_resp1.id = "file-1"
        mock_resp2 = MagicMock()
        mock_resp2.id = "file-2"
        mock_client.files.create.side_effect = [mock_resp1, mock_resp2]
        
        # 模拟OpenAI响应
        mock_response = MagicMock()
        mock_client.responses.create.return_value = mock_response
        
        # 模拟output
        mock_item1 = MagicMock()
        mock_item1.container_id = "container-1"
        mock_item1.type = "tool_call"
        
        mock_annotation = MagicMock()
        mock_annotation.file_id = "cfile-1"
        
        mock_block = MagicMock()
        mock_block.annotations = [mock_annotation]
        
        mock_item2 = MagicMock()
        mock_item2.type = "message"
        mock_item2.content = [mock_block]
        
        mock_response.output = [mock_item1, mock_item2]
        
        # 模拟文件下载
        mock_file_content = MagicMock()
        mock_file_content.read.return_value = b"test content"
        mock_client.containers.files.content.retrieve.return_value = mock_file_content
        
        # 调用函数
        output_file = os.path.join(self.temp_dir, "output.xlsx")
        result = generate_summary(
            self.pl_file,
            self.bs_file,
            "测试公司",
            "2024",
            output_file
        )
        
        # 验证结果
        self.assertEqual(result, output_file)
        self.assertTrue(os.path.exists(output_file))
        
        # 验证调用
        mock_client.files.create.assert_any_call(file=unittest.mock.ANY, purpose="assistants")
        mock_client.responses.create.assert_called_once()
        mock_client.containers.files.content.retrieve.assert_called_once_with(
            container_id="container-1", 
            file_id="cfile-1"
        )


if __name__ == "__main__":
    unittest.main() 