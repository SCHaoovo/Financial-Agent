"""
报告生成模块 - 使用OpenAI API生成财务数据分析报告
"""

import os
import logging
from dotenv import load_dotenv
from openai import OpenAI
from typing import Optional

from src.config import get_settings

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 获取设置
settings = get_settings()

def generate_report_analysis(
    database_file_path: str,
    output_file: Optional[str] = None
) -> str:
    """
    使用OpenAI处理财务数据库文件，生成财务分析报告
    
    Args:
        database_file_path: 财务数据库Excel文件路径
        output_file: 输出文件路径，如果为None则使用默认路径
        
    Returns:
        输出文件的路径
    """
    try:
        logger.info(f"开始生成财务分析报告")
        logger.info(f"输入文件: 数据库={database_file_path}")
        
        # 初始化OpenAI客户端
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("未设置OPENAI_API_KEY环境变量")
        
        # 上传文件并获取file_id
        try:
            logger.info(f"准备上传文件路径: {database_file_path}")
            logger.info(f"文件是否存在: {os.path.exists(database_file_path)}")
            logger.info(f"文件路径长度: {len(database_file_path)}")
            logger.info(f"文件路径repr: {repr(database_file_path)}")
            
            with open(database_file_path, "rb") as f:
                resp = client.files.create(file=f, purpose="assistants")
            file_ids = [resp.id]
            logger.info(f"文件上传成功，获取到file_ids: {file_ids}")
        except Exception as e:
            logger.error(f"文件上传失败: {str(e)}")
            logger.error(f"失败时的文件路径: {repr(database_file_path)}")
            raise
        
        # 构建Code Interpreter请求
        try:
            response = client.responses.create(
                model="gpt-4o",
                instructions="""
    你是一个精通金融数据分析的工程师，你的任务是是对数据进行细致的report分析，你已经拥有了世界顶尖金融公司分析，极其专业的金融报告分析方法。用户的输入通常有一个包含数据的.xlsx文件，你能够获取的数据通常像下面这个样子：
$	FY25 YTD **	FY25 Forecast	FY25 Budget	FY24 Actual
Total Revenue	7,559,458	9,103,639	7,452,733	13,678,503
Total COS	4,495,889	5,603,824	6,123,846	9,910,229
Total Admin Expenses	212,817	291,157	394,680	526,493
Total Interest - NAB	271,764	271,764	401,965	694,388
Total Interest - Partners	150,121	173,432	133,410	242,237
Total Other Income	578,493	648,463	29,169	599,787
Total Net Profit	3,007,359	3,411,925	428,003	2,904,944
Cash Balance	279,830	1,987,359	(2,454,762)	360,399
Loan Payables - NAB	-	-	3,389,399	3,985,730
Loan Payables - Partners	1,100,000	1,100,000	-	1,600,000
对其进行深刻的分析，解析报表结构、调用对比逻辑、生成摘要评价，涵盖同比、预算差异、贷款分析等指标，最终输出一个word文档
公司名称请从文件中的Entities列提取。
重要：请将使用的Token控制在25000以内""",
                tools=[
                    {
                        "type": "code_interpreter",
                        "container": {
                            "type": "auto",
                            "file_ids": file_ids
                        }
                    }
                ],
                input=f"我给你了一个内容是Summary Table的.xlsx格式的DB文件，请给我一个word文件，在里面对报表做深刻的分析"
            )
            logger.info(f"OpenAI请求成功，Response ID: {response.id}")
        except Exception as e:
            logger.error(f"OpenAI请求失败: {str(e)}")
            raise
        
        # 初始化变量
        container_id = None
        cfile_id = None
        
        # 遍历output结构，寻找container_id和cfile_id
        for item in response.output:
            # 提取container_id来自CodeInterpreterToolCall
            if hasattr(item, "container_id") and item.container_id:
                container_id = item.container_id
            
            # 提取cfile_id来自message中的annotations
            if getattr(item, "type", "") == "message":
                for block in getattr(item, "content", []):
                    if hasattr(block, "annotations"):
                        for ann in block.annotations:
                            if hasattr(ann, "file_id") and ann.file_id.startswith("cfile_"):
                                cfile_id = ann.file_id
                                break
        
        # 校验提取结果
        if not container_id or not cfile_id:
            logger.error("未能从response中提取container_id或cfile_id")
            raise ValueError("未能从response中提取container_id或cfile_id")
        
        logger.info(f"提取到container_id: {container_id}")
        logger.info(f"提取到cfile_id: {cfile_id}")
        
        # 下载并保存文件
        output_file_content = client.containers.files.content.retrieve(
            container_id=container_id, 
            file_id=cfile_id
        )
        
        # 如果未提供输出文件路径，则使用默认路径
        if output_file is None:
            # 获取文件名作为输出文件名的一部分
            base_filename = os.path.basename(database_file_path)
            file_name_without_ext = os.path.splitext(base_filename)[0]
            
            # 使用processed目录下的reports子目录
            reports_dir = os.path.join(settings.PROCESSED_DATA_DIR, "reports")
            os.makedirs(reports_dir, exist_ok=True)
            output_file = os.path.join(reports_dir, f"Report_{file_name_without_ext}.docx")
            logger.info(f"使用默认输出路径: {output_file}")
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        with open(output_file, "wb") as f:
            f.write(output_file_content.read())
        
        logger.info(f"已成功保存分析报告: {output_file}")
        return output_file
        
    except Exception as e:
        logger.error(f"生成分析报告时出错: {str(e)}")
        raise

# 示例用法
if __name__ == "__main__":
    # 示例调用
    database_file = "E:\Finance\Financial_Backend\data\processed\database\DB_Company.xlsx"
    
    try:
        output_path = generate_report_analysis(database_file)
        print(f"分析报告已保存至: {output_path}")
    except Exception as e:
        print(f"错误: {str(e)}")