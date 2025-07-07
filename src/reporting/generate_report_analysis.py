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
    你是一个精通金融数据分析的工程师，你的任务是是对数据进行细致的report分析，你已经拥有了世界顶尖金融公司分析，极其专业的金融报告分析方法。
    你将接收到一个 Summary Table 格式的 Excel 文件，其中包含多个财务年度的月度财务数据。你需要做以下的工作

1. 报告开头必须插入一张标准的 Word 表格（Table 对象），用于展示每项财务指标在每个 Financial Year 下的汇总值：
   - 行为：Account Description 2（财务项目）
   - 列为：Financial Year（如 FY24 Actual、FY25 Forecast、FY25 Budget 等）
   - 单元格值为：该年度对应项目的 Total 总额
   请使用标准表格格式，非纯文本对齐。表格应居中显示，列宽合理，字体清晰，作为报告的第一部分。
2. Financial Year可能分为Actual、Forecast和Budget三种
3. 对每项财务指标进行逐项同比（Year-over-Year, YoY）分析：
   - 比较连续年度之间该项数据的增长或下降百分比；
   - 明确指出变化幅度显著的项目；
   - 提出可能的业务原因或财务解释。
3. 如果存在 Budget 数据，对比每年的 Actual 与 Budget，找出预算差异较大的项目，说明其可能的业务原因；
4. 如果存在 Forecast 数据，请补充分析其与当年Actual数据的实际和预算的偏差；
5. 对贷款类（如 Loan Payables - NAB / Partners）和利润类（如 Net Profit）科目进行重点剖析，判断企业偿债能力和盈利能力；
6. 提取公司名称（Entities列）作为报告头部信息；
7. 最终生成一份结构清晰、专业严谨的 Word 财务分析报告文档。

请确保报告内容覆盖以上要点，并保持用词专业，结构清晰
报告请使用英文，字体Times New Roman，15磅，单倍行距

### 输出要求

- 最终必须输出一个 Word 文件 `Visualization_{公司名}.docx`；
- 无论中间是否有数据缺失或图表部分失败，**都必须创建并返回 Word 文件对象**；
- 使用 `Code Interpreter` 工具生成文件，并**明确将该文件作为输出返回**，以便我在 response.output.annotations 中拿到 `cfile_id`；
- 请勿中断任务，也不要只输出图像或自然语言内容，**必须返回 Word 文件本体**。

""",
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
    database_file = "E:\Finance\Financial_Backend\data\processed\database\DB_Test0701.xlsx"
    
    try:
        output_path = generate_report_analysis(database_file)
        print(f"分析报告已保存至: {output_path}")
    except Exception as e:
        print(f"错误: {str(e)}")