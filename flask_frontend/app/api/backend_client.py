"""
财务报告系统 Flask 前端应用 - 后端API客户端
"""

import os
import requests
from flask import current_app as app

class BackendClient:
    """后端API客户端类"""
    
    def __init__(self, base_url=None):
        """初始化客户端
        
        Args:
            base_url: 后端API的基础URL，默认使用配置中的BACKEND_URL
        """
        self.base_url = base_url or app.config['BACKEND_URL']
    
    def generate_summary(self, pl_file_path, bs_file_path, entity, financial_year):
        """调用后端API生成汇总
        
        Args:
            pl_file_path: PL文件路径
            bs_file_path: BS文件路径
            entity: 实体名称
            financial_year: 财务年度
            
        Returns:
            dict: API响应结果
        """
        app.logger.info(f"调用后端API生成汇总: entity={entity}, financial_year={financial_year}")
        
        # 准备文件和表单数据
        with open(pl_file_path, 'rb') as pl_f, open(bs_file_path, 'rb') as bs_f:
            pl_filename = os.path.basename(pl_file_path)
            bs_filename = os.path.basename(bs_file_path)
            
            files = {
                'pl_file': (pl_filename, pl_f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                'bs_file': (bs_filename, bs_f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            }
            
            data = {
                'entity': entity,
                'financial_year': financial_year
            }
            
            # 调用API
            response = requests.post(
                f'{self.base_url}/finance/summary/generate',
                files=files,
                data=data,
                timeout=300
            )
        
        # 处理响应
        if response.status_code == 200:
            try:
                return {
                    'success': True,
                    'data': response.json(),
                    'status_code': response.status_code
                }
            except ValueError:
                return {
                    'success': True,
                    'content': response.content,
                    'status_code': response.status_code,
                    'content_type': response.headers.get('content-type')
                }
        else:
            return {
                'success': False,
                'error': response.text,
                'status_code': response.status_code
            }
    
    def generate_database(self, summary_files, entity, financial_year):
        """调用后端API生成数据库
        
        Args:
            summary_files: 汇总文件路径列表
            entity: 实体名称
            financial_year: 财务年度
            
        Returns:
            dict: API响应结果
        """
        app.logger.info(f"调用后端API生成数据库: entity={entity}, financial_year={financial_year}")
        
        # 准备文件和表单数据
        files_to_send = []
        file_handles = []
        
        try:
            # 打开所有文件
            for file_path in summary_files:
                file_handle = open(file_path, 'rb')
                file_handles.append(file_handle)
                
                filename = os.path.basename(file_path)
                files_to_send.append(
                    ('summary_files', (filename, file_handle, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'))
                )
            
            data = {
                'entity': entity,
                'financial_year': financial_year
            }
            
            # 调用API
            response = requests.post(
                f'{self.base_url}/finance/database/generate-database',
                files=files_to_send,
                data=data,
                timeout=300
            )
            
            # 处理响应
            if response.status_code == 200:
                try:
                    return {
                        'success': True,
                        'data': response.json(),
                        'status_code': response.status_code
                    }
                except ValueError:
                    return {
                        'success': True,
                        'content': response.content,
                        'status_code': response.status_code,
                        'content_type': response.headers.get('content-type')
                    }
            else:
                return {
                    'success': False,
                    'error': response.text,
                    'status_code': response.status_code
                }
                
        finally:
            # 关闭所有文件句柄
            for handle in file_handles:
                handle.close()
    
    def generate_visualization(self, database_file_path, entity, financial_year):
        """调用后端API生成可视化
        
        Args:
            database_file_path: 数据库文件路径
            entity: 实体名称
            financial_year: 财务年度
            
        Returns:
            dict: API响应结果
        """
        app.logger.info(f"调用后端API生成可视化: entity={entity}, financial_year={financial_year}")
        
        # 准备文件和表单数据
        with open(database_file_path, 'rb') as f:
            filename = os.path.basename(database_file_path)
            
            files = {
                'database_file': (filename, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            }
            
            data = {
                'entity': entity,
                'financial_year': financial_year
            }
            
            # 调用API
            response = requests.post(
                f'{self.base_url}/finance/visualization/generate-visualization',
                files=files,
                data=data,
                timeout=300
            )
        
        # 处理响应
        if response.status_code == 200:
            try:
                return {
                    'success': True,
                    'data': response.json(),
                    'status_code': response.status_code
                }
            except ValueError:
                return {
                    'success': True,
                    'content': response.content,
                    'status_code': response.status_code,
                    'content_type': response.headers.get('content-type')
                }
        else:
            return {
                'success': False,
                'error': response.text,
                'status_code': response.status_code
            }
    
    def generate_report(self, database_file_path, entity, financial_year):
        """调用后端API生成报告
        
        Args:
            database_file_path: 数据库文件路径
            entity: 实体名称
            financial_year: 财务年度
            
        Returns:
            dict: API响应结果
        """
        app.logger.info(f"调用后端API生成报告: entity={entity}, financial_year={financial_year}")
        
        # 准备文件和表单数据
        with open(database_file_path, 'rb') as f:
            filename = os.path.basename(database_file_path)
            
            files = {
                'database_file': (filename, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            }
            
            data = {
                'entity': entity,
                'financial_year': financial_year
            }
            
            # 调用API
            response = requests.post(
                f'{self.base_url}/finance/reporting/generate-report',
                files=files,
                data=data,
                timeout=300
            )
        
        # 处理响应
        if response.status_code == 200:
            return {
                'success': True,
                'content': response.content,
                'status_code': response.status_code,
                'content_type': response.headers.get('content-type')
            }
        else:
            return {
                'success': False,
                'error': response.text,
                'status_code': response.status_code
            }
    
    def execute_workflow(self, pl_file_path, bs_file_path, entity, financial_year):
        """调用后端API执行工作流
        
        Args:
            pl_file_path: PL文件路径
            bs_file_path: BS文件路径
            entity: 实体名称
            financial_year: 财务年度
            
        Returns:
            dict: API响应结果
        """
        app.logger.info(f"调用后端API执行工作流: entity={entity}, financial_year={financial_year}")
        
        # 准备文件和表单数据
        with open(pl_file_path, 'rb') as pl_f, open(bs_file_path, 'rb') as bs_f:
            pl_filename = os.path.basename(pl_file_path)
            bs_filename = os.path.basename(bs_file_path)
            
            files = {
                'pl_file': (pl_filename, pl_f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                'bs_file': (bs_filename, bs_f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            }
            
            data = {
                'entity': entity,
                'financial_year': financial_year
            }
            
            # 调用API
            response = requests.post(
                f'{self.base_url}/finance/workflow/execute-workflow',
                files=files,
                data=data,
                timeout=600
            )
        
        # 处理响应
        if response.status_code == 200:
            try:
                return {
                    'success': True,
                    'data': response.json(),
                    'status_code': response.status_code
                }
            except ValueError:
                return {
                    'success': True,
                    'content': response.content,
                    'status_code': response.status_code,
                    'content_type': response.headers.get('content-type')
                }
        else:
            return {
                'success': False,
                'error': response.text,
                'status_code': response.status_code
            }
    
    def get_workflow_status(self, task_id):
        """获取工作流状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            dict: API响应结果
        """
        app.logger.info(f"获取工作流状态: task_id={task_id}")
        
        # 调用API
        response = requests.get(
            f'{self.base_url}/finance/workflow/workflow-status/{task_id}',
            timeout=30
        )
        
        # 处理响应
        if response.status_code == 200:
            try:
                return {
                    'success': True,
                    'data': response.json(),
                    'status_code': response.status_code
                }
            except ValueError:
                return {
                    'success': False,
                    'error': '无效的JSON响应',
                    'status_code': response.status_code
                }
        else:
            return {
                'success': False,
                'error': response.text,
                'status_code': response.status_code
            } 