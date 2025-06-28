"""
财务数据汇总模块 - 使用OpenAI API处理PL和BS数据
"""

import os
import logging
import time
import random
import backoff
import json

from dotenv import load_dotenv
from openai import OpenAI
from openai import APIError, RateLimitError
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


# 定义用于OpenAI API的指数退避装饰器
@backoff.on_exception(
    backoff.expo,
    (RateLimitError, APIError),
    max_tries=5,
    factor=2,
    jitter=backoff.full_jitter,
    on_backoff=lambda details: logger.warning(
        f"API请求失败，正在重试（第{details['tries']}次）。等待{details['wait']:.2f}秒..."
    )
)
def api_request_with_backoff(func, *args, **kwargs):
    """使用指数退避策略执行API请求"""
    return func(*args, **kwargs)


def generate_summary(
    pl_file_path: str, 
    bs_file_path: str, 
    entity: str, 
    financial_year: str,
    output_file: Optional[str] = None
) -> str:
    """
    使用OpenAI处理PL和BS数据，生成财务数据汇总
    
    Args:
        pl_file_path: 利润表Excel文件路径
        bs_file_path: 资产负债表Excel文件路径
        entity: 实体名称
        financial_year: 财务年度
        output_file: 输出文件路径，如果为None则使用默认路径
        
    Returns:
        输出文件的路径
    """
    try:
        logger.info(f"开始处理财务数据汇总: 实体={entity}, 年份={financial_year}")
        logger.info(f"输入文件: PL={pl_file_path}, BS={bs_file_path}")
        
        # 初始化OpenAI客户端
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("未设置OPENAI_API_KEY环境变量")
        
        # 上传文件并获取file_id，使用指数退避
        try:
            # 使用指数退避上传第一个文件 - 使用上下文管理器确保文件正确关闭
            with open(pl_file_path, "rb") as pl_file:
                resp1 = api_request_with_backoff(
                    client.files.create,
                    file=pl_file,
                    purpose="assistants"
                )
            
            # 添加短暂延迟，避免连续请求
            time.sleep(1.5)
            
            # 使用指数退避上传第二个文件 - 使用上下文管理器确保文件正确关闭
            with open(bs_file_path, "rb") as bs_file:
                resp2 = api_request_with_backoff(
                    client.files.create,
                    file=bs_file,
                    purpose="assistants"
                )
            
            file_ids = [resp1.id, resp2.id]
            logger.info(f"文件上传成功，获取到file_ids: {file_ids}")
        except Exception as e:
            logger.error(f"文件上传失败: {str(e)}")
            raise

        # 构建Code Interpreter请求，使用指数退避
        try:
            response = api_request_with_backoff(
                client.responses.create,
                model="gpt-4o",
                instructions=f"""
你是一个精通金融数据分析的工程师。我上传了两个Excel文件，分别是{entity}公司{financial_year}年的PL表和BS表。请你完成以下任务：

1. 使用Pandas库读取这两个文件。
PL的Schema中Column是月份，比如January，February等等，Row是字段，比如：
Account Name
Income
Contract Revenue (Stage 1)
Contract Revenue (adj) - Stage 1
Contract Revenue (allocation) - Stage 1
Contract Revenue - Rebate (Stage 1)
Contract Revenue (Stage 2)
Contract Revenue (adj) - Stage 2
Contract Revenue (allocation) - Stage 2
Contract Revenue - Rebate (Stage 2)
Total Income
Cost Of Sales
2b - Estate signage/Identity/Logo
2q Local Sales Agent Commission
3a Roadworks and Drainage
3e Sewer Pump Station
3f Water Main Extention
3g Electrical
3h Telecommunications
3j Landscaping
3n Demolition
3r Construction spare 2
4a Town Planning
4b Urban Design
4c Engineering
4d Survey
4i Other Consultants
4j Drainage Engineer
4k Flora & Fauna
4m Arborist
4n Landscaping consultant
4p Permit Fees (council and authorities)
4v Geotechnical
5a Authjority fees & charges
5b Sewarage & Water
6d Council fees and charges
7a Council rates
7c Water Rates
8a Settlement large parcel
8b Admin and settlement of lot
Common Cost - Transfer/ Deferral
Stamp Duty & Land Registry Fee
Total Cost Of Sales
Gross Profit
Expenses
General & Administrative Exp
ASIC
Bank Charges
Accounting Fees
Management Fee
Director Fee
Professional fee
Marketing
Entertainment - Non Deductible
Local - Travel & Accomodation
Council Rates and Charges
Electricity
Insurance
Land Tax
Total General & Administrative Exp
Total Expenses
Operating Profit
Other Income
Interest Income
Other Income
Other Income - Reimbursement from Authority
Rental income
Total Other Income
Other Expenses
Interest expense (unit holders)
Interest Expense - NAB Loan (7481)
Interest Expense - NAB OD (5239)
Interest Expense - NAB Loan (9177)
Interest Expense - NAB Loan (9538)
Interest expense (director / friendly loan)
Interest Expense - NAB Loan (1047)
Total Other Expenses
Net Profit/(Loss)
对于BS表来说，Column也是月份，Row的字段为：
Account Name
Assets
Current Assets
Cash On Hand
ANZ CMA (53789)
NAB Term Deposit (5014)
Sales Clearing Account
Total Cash On Hand
Other receivables
Formation Expenses
Company Incorporation
Amortisation of formation cost
Total Formation Expenses
Loan to Others
Loan to Waranu
Land
234 Lillico Road, Warragul
Land at Cost - PP $4.5M
Stamp Duty
Land Registry Fee
Authority/Statutory Fees
Construction Works
Professional Fees
Legal Fees
Landscape
Rates and Taxes
Arborist
Land - Transfer to Cost of Sales
Transfer to Cost of Sales
Total 234 Lillico Road, Warragul
230 Lillico Road, Warragul
Land at Cost - PP $2.65M
Total Land
Stage 1 Development Costs
Construction Costs - Civil Works (S1)
Professional Fees (S1)
Statutory Authority Fee (S1)
Legal Costs (S1)
Transfer to Cost of Sale (S1)
Total Stage 1 Development Costs
Stage 2 Development Costs
Construction Costs - Civil Works (S2)
Professional Fees (S2)
Statutory Authority Fees (S2)
Rates and Taxes (S2)
Legal Costs (S2)
Transfer to Cost of Sale (S2)
Total Stage 2 Development Costs
Stage 3 Development Costs
Construction Costs - Civil Works (S3)
Professional Fees (S3)
Statutory Authority Fees (S3)
Legal Costs (S3)
Transfer to Cost of Sale (S3)
Total Stage 3 Development Costs
Stage 4 Development Costs
Construction Costs - Civil Works (S4)
Professional Fees (S4)
Statutory Authority Fees (S4)
Legal Costs (S4)
Total Stage 4 Development Costs
Stage 5 Development Costs
Professional Fees (S5)
Total Stage 5 Development Costs
Inventories
Sub-division Land Lots
Total Inventories
Total Assets
Liabilities
Current Liabilities
Trade Creditors
Other Payables
Bond/deposit received (payable)
Total Current Liabilities
GST Liabilities
GST Collected
GST Paid
Nett GST
Total GST Liabilities
Payroll Liabilities
PAYG Withholding Payable
Total Payroll Liabilities
Long Term Liabilities
Loan from L Track
Loan from Khor Gok Hong
Loan from Joshua
Loan from Peh Family
Total Long Term Liabilities
Bank Loan
NAB Overdraft
NAB Construction Loan (9538)
NAB Business Markets Loan (1047)
Total Liabilities
Net Assets
Equity
Unitholders Equity
Unitholding - Janeliza
Unitholding - Eastgate
Unitholding - Aldinga FC
Unitholding - Quadrant
Unitholding - Chuan Jun Yeap
Unitholding - Nai Yan Yeap
Unitholding - Sky East
Unitholding - Epiros
Unitholding - Sau Bing Yeap
Unitholding - G&J Avon
Unitholding - Plenti Corp
Unitholding - Apreg Pty Ltd
Unitholding - Nancy Ang
Unitholding - JY for Wei Yeap
Unitholding - Unicol Pty Ltd
Unitholding - Amanda Fung
Unitholding - Nicholas Fung
Distribution/Capital Return to unitholder
Unit Premium
Total Unitholders Equity
Retained Earnings
Current Year Earnings
Total Equity
2. 按照如下对应关系从PL和BS中提取汇总字段：

- Revenue: PL表的Total Income
- COS: PL表的Total Cost Of Sales
- Administrative Expenses: PL表的Total General & Administrative Exp
- Loan Interest - NAB: PL表所有包含"NAB"的项目（如NAB Loan、NAB OD等）
- Loan Interest - Partners / Inter-co: PL表中"Interest expense (unit holders)"与"Interest expense (director / friendly loan)"
- Other Income: PL表的Total Other Income
- Net Profit/(Loss): PL表的Net Profit/(Loss)
- Cash Balance: BS表的Total Cash On Hand
- Loan Payable - NAB: BS表中所有带NAB、且为负债类（不包括NAB Term Deposit）
- Loan Payables - Partners / Inter-co Loan: BS表的Total Long Term Liabilities 和 Total Other Long Term Liabilities之和
- Total Equity: BS表的Total Equity
你需要做的是根据以上对应关系利用代码从PL或BS表得到对应的数据，并做计算。

3. 汇总表格格式为：

- 列名（Columns）: Account Name, July, August, September, October, November, December, January, February, March, April, May, June, Adjustment Only, Total（共15列）
其中，Total列的数据值等于前面12个月份列的数据的和
- 行名（Rows）: 11个汇总项目（如上2.中所列）
请遵循该格式，设置正确的列与行。

4. 汇总表格月份内数据与对应字段相应月份数据相同，Total数据为十二个月数据的和

5. **极其重要：无论你是否完全成功提取出所有数据，你都必须最终在代码解释器中执行以下步骤：**

- 创建一个 DataFrame 作为最终输出表格
- 使用 `pandas` 将其保存为 `PL&BS_{financial_year}.xlsx`
- 将该文件写入容器返回给用户

6. 你不需要生成任何自然语言输出，最终输出结果只需要容器中的Excel文件。

请你务必保证容器中能生成最终Excel文件，无论中途遇到任何数据清洗问题，都要以写出文件为最终目标。
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
                input=f"我给你了两个.xlsx文件，分别是{entity}公司{financial_year}年的PL表和BS表，请给我一个汇总表格"
            )
            logger.info(f"OpenAI请求成功，Response ID: {response.id}")
            
            # 打印完整的response结构，用于调试
            logger.info("Response结构详情:")
            # logger.info(f"Response类型: {type(response)}")
            # logger.info(f"Response属性: {dir(response)}")
            logger.info(f"Response内容: {response}")
            
            # 打印output结构
            logger.info("Output结构详情:")
            if hasattr(response, 'output'):
                # logger.info(f"Output类型: {type(response.output)}")
                # logger.info(f"Output长度: {len(response.output)}")
                for i, item in enumerate(response.output):
                    # logger.info(f"Output[{i}]类型: {type(item)}")
                    # logger.info(f"Output[{i}]属性: {dir(item)}")
                    # logger.info(f"Output[{i}]内容: {item}")
                    
                    # 如果item是message类型，打印其content
                    if getattr(item, "type", "") == "message" and hasattr(item, "content"):
                        for j, block in enumerate(item.content):
                            # logger.info(f"Output[{i}].content[{j}]类型: {type(block)}")
                            # logger.info(f"Output[{i}].content[{j}]属性: {dir(block)}")
                            if hasattr(block, "annotations"):
                                logger.info(f"Annotations: {block.annotations}")
            else:
                logger.info("Response没有output属性")
                
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
        
        # 下载并保存文件，使用指数退避
        output_file_content = api_request_with_backoff(
            client.containers.files.content.retrieve,
            container_id=container_id, 
            file_id=cfile_id
        )
        
        # 如果未提供输出文件路径，则使用默认路径
        if output_file is None:
            # 使用processed目录下的summary子目录
            summary_dir = os.path.join(settings.PROCESSED_DATA_DIR, "summary")
            os.makedirs(summary_dir, exist_ok=True)
            output_file = os.path.join(summary_dir, f"PL&BS_{entity}_{financial_year}.xlsx")
            logger.info(f"使用默认输出路径: {output_file}")
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        with open(output_file, "wb") as f:
            f.write(output_file_content.read())
        
        logger.info(f"已成功保存汇总文件: {output_file}")
        return output_file
        
    except Exception as e:
        logger.error(f"生成财务数据汇总时出错: {str(e)}")
        raise


# 示例用法
if __name__ == "__main__":
    # 示例调用
    from src.config import get_settings
    import os
    
    settings = get_settings()
    
    pl_file = os.path.join(settings.INPUT_DATA_DIR, "PL25.xlsx")
    bs_file = os.path.join(settings.INPUT_DATA_DIR, "BS25.xlsx")
    entity = "Hao"
    year = "2026Forecast"
    
    try:
        output_path = generate_summary(pl_file, bs_file, entity, year)
        print(f"汇总文件已保存至: {output_path}")
    except Exception as e:
        print(f"错误: {str(e)}")