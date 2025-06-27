"""
财务数据库生成模块 - 使用OpenAI API处理Summary数据
"""

import os
import logging
from dotenv import load_dotenv
from openai import OpenAI
from typing import Optional, List

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

def generate_financial_database(
    summary_file_paths: List[str],
    entity: str,
    output_file: Optional[str] = None
) -> str:
    """
    使用OpenAI处理多个Summary数据，生成标准化财务数据库
    
    Args:
        summary_file_paths: Summary Excel文件路径列表
        entity: 实体名称
        output_file: 输出文件路径，如果为None则使用默认路径
        
    Returns:
        输出文件的路径
    """
    try:
        logger.info(f"开始生成财务数据库: 实体={entity}")
        logger.info(f"输入文件数量: {len(summary_file_paths)}")
        
        # 初始化OpenAI客户端
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("未设置OPENAI_API_KEY环境变量")
        
        # 上传文件并获取file_id
        file_ids = []
        try:
            for file_path in summary_file_paths:
                logger.info(f"正在上传文件: {file_path}")
                # 使用上下文管理器确保文件正确关闭
                with open(file_path, "rb") as f:
                    resp = client.files.create(file=f, purpose="assistants")
                    file_ids.append(resp.id)
                    logger.info(f"文件上传成功: {os.path.basename(file_path)}, file_id: {resp.id}")
            
            logger.info(f"共上传了 {len(file_ids)} 个文件")
        except Exception as e:
            logger.error(f"文件上传失败: {str(e)}")
            # 清理已上传的文件
            for file_id in file_ids:
                try:
                    client.files.delete(file_id)
                    logger.info(f"已清理文件: {file_id}")
                except Exception as cleanup_error:
                    logger.warning(f"清理文件失败: {cleanup_error}")
            raise
        
        # 构建Code Interpreter请求
        try:
            response = client.responses.create(
                model="gpt-4o",
                instructions=f"""你是一个精通金融数据分析的工程师，熟练掌握Python，Pandas等数据分析工具。你的工作是输出符合用户需求的.xlxs格式的Data Base。
        输入是一个或多个{entity}公司的Summary Table，格式为.xlsx，
        输入表格的Rows的字段是：
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
        输入表格的Columns的字段是：
        Account Name, July, August, September, October, November, December, January, February, March, April, May, June, Adjustment Only, Total
        输出的DataBase表格的Columns的scheme是：
        Entities	Financial Year	Account Description 1	Account Description 2	July	August	September	October	November	December	January	February	March	April	May	June	Total
        共17列数据
        输出表中字段应该严格按照这个Scheme。
        其中Entities代表公司的名字，比如Lillico Corporation。Financial Year是年份，比如FY25 Forecast，FY25 Budget或者FY24 Actual。上面的Entities用户会在输入中给出命名，请你使用就可以。Financial Year请从输入文件名或内容中提取。
Account Description 1包括：
Revenue
COS
Administrative Expenses
Loan Interest
Loan Interest
Other Income
Net Profit/(Loss)
Cash Balance
Loan Payables
Loan Payables
Total Equity

Account Description 2包括：
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

请将输入表格的Account Name列对齐相应的Account Description 2
如果有多个输入文件，每个输入文件可能代表不同年份或不同类型的数据，
重要：请按照上面的格式合并所有数据到一个输出文件中。
注意，每个输入文件在输出文件中只占11行数据

最终文件输出为.xlxs文件。""",
                tools=[
                    {
                        "type": "code_interpreter",
                        "container": {
                            "type": "auto",
                            "file_ids": file_ids
                        }
                    }
                ],
                input=f"我给你了{len(summary_file_paths)}个内容是Summary Table的.xlsx文件，公司名称是{entity}，请给我一个合并的DB表格"
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
            # 使用processed目录下的database子目录
            database_dir = os.path.join(settings.PROCESSED_DATA_DIR, "database")
            os.makedirs(database_dir, exist_ok=True)
            output_file = os.path.join(database_dir, f"DB_{entity}.xlsx")
            logger.info(f"使用默认输出路径: {output_file}")
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        with open(output_file, "wb") as f:
            f.write(output_file_content.read())
        
        logger.info(f"已成功保存财务数据库文件: {output_file}")
        return output_file
        
    except Exception as e:
        logger.error(f"生成财务数据库时出错: {str(e)}")
        raise


# 示例用法
if __name__ == "__main__":
    # 示例调用
    summary_files = [
        "E:\Finance\Financial_Backend\data\processed\summary\PL&BS_Lillco Corporation_2024Actual.xlsx",
        "E:\Finance\Financial_Backend\data\processed\summary\PL&BS_Hao_2025Forecast.xlsx"
    ]
    entity = "Company"
    
    try:
        output_path = generate_financial_database(summary_files, entity)
        print(f"财务数据库文件已保存至: {output_path}")
    except Exception as e:
        print(f"错误: {str(e)}")