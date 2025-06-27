"""
可视化模块 - 使用OpenAI API生成财务数据可视化图表
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

def plot_summary_graphs(
    database_file_path: str,
    entity: str,
    output_file: Optional[str] = None
) -> str:
    """
    使用OpenAI处理财务数据库文件，生成可视化图表
    
    Args:
        database_file_path: 财务数据库Excel文件路径
        entity: 实体名称
        output_file: 输出文件路径，如果为None则使用默认路径
        
    Returns:
        输出文件的路径
    """
    try:
        logger.info(f"开始生成财务数据可视化: 实体={entity}")
        logger.info(f"输入文件: 数据库={database_file_path}")
        
        # 初始化OpenAI客户端
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("未设置OPENAI_API_KEY环境变量")
        
        # 上传文件并获取file_id
        try:
            resp = client.files.create(file=open(database_file_path, "rb"), purpose="assistants")
            file_ids = [resp.id]
            logger.info(f"文件上传成功，获取到file_ids: {file_ids}")
        except Exception as e:
            logger.error(f"文件上传失败: {str(e)}")
            raise
        
        # 构建Code Interpreter请求
        try:
            response = client.responses.create(
                model="gpt-4o",
                instructions="""你是一个精通金融数据分析的工程师，熟练掌握Python，Pandas，Matplotlib等数据分析与可视化工具。
首先你将会被输入一个或多个Summary Table数据，输入格式为.xlxs文件，这个文件中可能有多个表格的数据。请你使用Python进行数据的读取。
PL的Schema中，Column包含：
Entities
Financial Year
Account Description 1
Account Description 2
July
August
September
October
November
December
January
February
March
April
May
June
Total
前面是公司名称、年份和项目名称，之后是月份数据比如January，February等，最后一列是Total数据，是前面月份的累加和。
Row是字段，以Account Description 2下的字段为主，比如：
Revenue
COS
Administrative Expenses
Loan Interest - NAB
Loan Interest - Partners / Inter-co
Other Income
Net Profit/(Loss)
Cash Balance
Loan Payable - NAB
Loan Payables - Partners / Inter-co Loan
Total Equity
区分这个表格中的数据是否是同一张表主要通过Financial Year判断。
你的工作是需要对输入的这个表格进行可视化分析，主要通过Matplotlib来绘制4张图，这个时候请确保你已经获得了充分的数据。可视化非常简单，y-axis是变量的amount，x-axis是月份。其中默认4个Account Description 2下的变量，分别是Revenue，Administrative Expenses，Net Profit/(Loss)，Cash vs Loans。其中不同的线代表不同表格的数据比如FY25 Actual, FY24 Actual等，此处的名字来自于Financial Year栏。
最终输出在一个Word文档中，文档的命名请参考公司名称。""",
                tools=[
                    {
                        "type": "code_interpreter",
                        "container": {
                            "type": "auto",
                            "file_ids": file_ids
                        }
                    }
                ],
                input=f"我给你了一个内容是Summary Table的.xlsx格式的DB文件，公司名称是{entity}，请给我一个word文件，里面有可视化的表格数据图像"
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
            # 使用processed目录下的visualization子目录
            visualization_dir = os.path.join(settings.PROCESSED_DATA_DIR, "visualization")
            os.makedirs(visualization_dir, exist_ok=True)
            output_file = os.path.join(visualization_dir, f"Visualization_{entity}.docx")
            logger.info(f"使用默认输出路径: {output_file}")
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        with open(output_file, "wb") as f:
            f.write(output_file_content.read())
        
        logger.info(f"已成功保存可视化文件: {output_file}")
        return output_file
        
    except Exception as e:
        logger.error(f"生成可视化图表时出错: {str(e)}")
        raise

# 示例用法
if __name__ == "__main__":
    # 示例调用
    database_file = "E:\Finance\Financial_Backend\data\processed\database\DB_Company.xlsx"
    entity = "Lillco"
    
    try:
        output_path = plot_summary_graphs(database_file, entity)
        print(f"可视化文件已保存至: {output_path}")
    except Exception as e:
        print(f"错误: {str(e)}")