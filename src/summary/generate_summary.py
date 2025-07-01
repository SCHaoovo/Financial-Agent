"""
财务数据汇总模�?- 使用OpenAI API处理PL和BS数据
"""
import os
import logging
import time
import backoff
from dotenv import load_dotenv
from openai import OpenAI
from openai import APIError, RateLimitError
from typing import Optional
from src.config import get_settings
import uuid
import tempfile
import pandas as pd
import numpy as np
from src.utils.deterministic_calculator import calculate_financial_summary

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


def preprocess_financial_data(df_raw: pd.DataFrame, table_type: str) -> pd.DataFrame:
    """
    智能预处理财务数据
    
    Args:
        df_raw: 原始DataFrame
        table_type: 表类型 ("PL" 或 "BS")
    
    Returns:
        清理后的DataFrame
    """
    logger.info(f"开始预处理{table_type}表，原始形状: {df_raw.shape}")
    
    # 1. 找到表头行（包含月份信息的行）
    header_row = find_header_row(df_raw)
    if header_row is None:
        logger.warning(f"{table_type}表未找到标准月份表头行，尝试寻找包含'Account Name'的行")
        # 寻找包含"Account Name"的行作为表头
        for i in range(min(15, len(df_raw))):
            row_values = [str(val).strip() for val in df_raw.iloc[i] if pd.notna(val)]
            if any('Account Name' in val for val in row_values):
                header_row = i
                logger.info(f"{table_type}表找到Account Name表头行在第{header_row}行")
                break
        
        # 如果还是找不到，使用传统的跳过9行方法
        if header_row is None:
            logger.warning(f"{table_type}表使用传统方法跳过前9行")
            header_row = 9
    else:
        logger.info(f"{table_type}表找到月份表头行在第{header_row}行")
    
    # 2. 从表头行开始截取数据
    df = df_raw.iloc[header_row:].copy()
    
    # 3. 设置第一行为列名
    df.columns = df.iloc[0]
    df = df.drop(df.index[0])
    
    # 4. 删除完全空的列
    df = df.dropna(axis=1, how='all')
    
    # 5. 删除完全空的行
    df = df.dropna(axis=0, how='all')
    
    # 6. 标准化列名（去除空格、统一大小写）
    df.columns = [str(col).strip() if col is not None else f"Unnamed_{i}" 
                  for i, col in enumerate(df.columns)]
    
    # 7. 找到并删除无用的第一列（通常是序号列或空列）
    if len(df.columns) > 0:
        first_col = df.iloc[:, 0]
        # 如果第一列主要是数字序号或大量空值，则删除
        if (first_col.dropna().astype(str).str.match(r'^\d+$').sum() > len(first_col) * 0.7 or
            first_col.isna().sum() > len(first_col) * 0.7):
            df = df.iloc[:, 1:]
            logger.info(f"{table_type}表删除了无用的第一列")
    
    # 8. 重置索引
    df = df.reset_index(drop=True)
    
    # 9. 验证数据结构
    months = ['July', 'August', 'September', 'October', 'November', 'December',
              'January', 'February', 'March', 'April', 'May', 'June']
    found_months = [month for month in months if month in df.columns]
    logger.info(f"{table_type}表找到月份列: {found_months}")
    
    if len(found_months) < 6:  # 至少应该有一半的月份
        logger.warning(f"{table_type}表月份列较少，可能存在数据结构问题")
    
    logger.info(f"{table_type}表预处理完成，最终形状: {df.shape}")
    logger.info(f"{table_type}表最终列名: {list(df.columns)}")
    
    return df


def find_header_row(df: pd.DataFrame) -> Optional[int]:
    """
    智能查找包含月份信息的表头行
    
    Args:
        df: 原始DataFrame
        
    Returns:
        表头行索引，如果未找到则返回None
    """
    months = ['July', 'August', 'September', 'October', 'November', 'December',
              'January', 'February', 'March', 'April', 'May', 'June', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    for i in range(min(15, len(df))):  # 只检查前15行
        row_values = [str(val).strip() for val in df.iloc[i] if pd.notna(val)]
        
        # 计算该行包含多少个独立的月份列（排除合并的日期范围）
        independent_month_count = 0
        for val in row_values:
            val_clean = val.strip()
            # 检查是否是独立的月份名称（而不是日期范围）
            if val_clean in months:
                independent_month_count += 1
            # 排除包含"To"、"2023"、"2024"等的日期范围描述
            elif any(keyword in val_clean for keyword in ['To', '2023', '2024', '2025', '2026', '-']):
                continue
            # 检查是否只包含月份名称的简短字符串
            elif len(val_clean) <= 10 and any(month in val_clean for month in months):
                # 进一步验证：确保不是日期范围
                if not any(char.isdigit() for char in val_clean):
                    independent_month_count += 1
        
        # 如果包含3个或以上独立月份列，认为是表头行
        if independent_month_count >= 3:
            logger.info(f"第{i}行包含{independent_month_count}个独立月份列，认定为表头行")
            return i
        elif independent_month_count > 0:
            logger.info(f"第{i}行包含{independent_month_count}个月份列（不足3个）")
    
    # 如果没有找到标准的月份表头，返回None使用默认处理
    logger.warning("未找到包含足够月份列的表头行，将使用默认处理")
    return None


# 定义用于OpenAI API的指数退避装饰器
@backoff.on_exception(
    backoff.expo,
    (RateLimitError, APIError),
    max_tries=3,
    factor=2,
    jitter=backoff.full_jitter,
    on_backoff=lambda details: logger.warning(
        f"API请求失败，正在重试（第{details['tries']}次）。等待{details['wait']:.2f}秒.."
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
    使用确定性计算引擎处理PL和BS数据，然后用AI生成标准格式Excel文件
    
    Args:
        pl_file_path: 利润表Excel文件路径
        bs_file_path: 资产负债表Excel文件路径
        entity: 实体名称
        financial_year: 财务年度
        output_file: 输出文件路径，如果为None则使用默认路径
        
    Returns:
        输出文件的路径
    """
    request_id = str(uuid.uuid4())[:8]
    extracted_data = None  # Initialize at function start
    
    try:
        logger.info(f"[{request_id}] 开始处理财务数据汇总, 实体={entity}, 年份={financial_year}")
        logger.info(f"[{request_id}] 输入文件: PL={pl_file_path}, BS={bs_file_path}")
        
        # 使用确定性计算引擎
        try:
            logger.info(f"[{request_id}] 使用确定性计算引擎提取数据...")
            
            # 智能预处理PL表
            logger.info(f"[{request_id}] 开始智能预处理PL表...")
            pl_df_raw = pd.read_excel(pl_file_path)
            pl_df = preprocess_financial_data(pl_df_raw, "PL")
            
            # 智能预处理BS表  
            logger.info(f"[{request_id}] 开始智能预处理BS表...")
            bs_df_raw = pd.read_excel(bs_file_path)
            bs_df = preprocess_financial_data(bs_df_raw, "BS")
            
            logger.info(f"[{request_id}] 数据预处理完成")
            logger.info(f"[{request_id}] PL表处理后形状: {pl_df.shape}")
            logger.info(f"[{request_id}] BS表处理后形状: {bs_df.shape}")
            
            # 调用确定性计算引擎获取汇总数据
            summary_df = calculate_financial_summary(pl_df, bs_df, entity, financial_year)
            
            # 将DataFrame转换为可读的文本格式保存到extracted_data
            extracted_data = summary_df.to_string(index=False)
            
            logger.info(f"[{request_id}] 确定性计算引擎数据提取成功，将使用AI生成最终Excel文件")
            
        except Exception as deterministic_error:
            logger.error(f"[{request_id}] 确定性计算引擎失败: {deterministic_error}")
            raise
        
        # AI格式化处理
        logger.info(f"[{request_id}] 使用AI生成标准格式Excel文件...")
        
        # 初始化OpenAI客户端
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("未设置OPENAI_API_KEY环境变量")
        
        # 构建Code Interpreter请求
        try:
            logger.info(f"[{request_id}] 开始AI格式化处理")
            
            # 先将数据保存为临时Excel文件
            temp_dir = tempfile.mkdtemp()
            temp_data_file = os.path.join(temp_dir, f"temp_data_{request_id}.xlsx")
            
            # 将summary_df保存为Excel文件
            summary_df.to_excel(temp_data_file, index=False)
            logger.info(f"[{request_id}] 临时数据文件已保存: {temp_data_file}")
            
            # 上传文件到OpenAI
            with open(temp_data_file, "rb") as file:
                uploaded_file = client.files.create(
                    file=file,
                    purpose="assistants"
                )
            logger.info(f"[{request_id}] 文件已上传到OpenAI，文件ID: {uploaded_file.id}")
            
            # AI指令：处理上传的Excel文件
            ai_instructions = f"""
你是一个精通金融数据分析的工程师，熟练掌握Python，Pandas等数据分析工具。你的工作是输出符合用户需求的.xlxs格式的Summary表格。
输入是一个{entity}公司{financial_year}年的财务汇总数据Excel表格。

**任务要求：**
请使用Python代码完成
1. 读取上传的Excel文件
2. 重新整理数据，创建标准的财务汇总Excel表格，格式要求：
   - 列名：Account Name, July, August, September, October, November, December, January, February, March, April, May, June, Adjustment Only, Total
   - 行名：Revenue, COS, Administrative Expenses, Loan Interest - NAB, Loan Interest - Partners / Inter-co, Other Income, Net Profit/(Loss), Cash Balance, Loan Payable - NAB, Loan Payables - Partners / Inter-co Loan, Total Equity
   - Total列 = 前12个月份列的数据之和
# 3. 创建标准格式的数据框架
# 4. 保存为Excel文件
**关键要求：**
- 文件名必须是 `PL&BS_{entity}_{financial_year}.xlsx`
- 不要添加任何额外的文字说明，只执行代码
- 请你务必保证容器中能生成最终Excel文件，无论中途遇到任何数据清洗问题，都要以写出文件为最终目标。
- 在生成 summary 文件后，务必将该文件对象作为 Code Interpreter 的输出显式返回，以便我在 response.output.annotations 中拿到 cfile_id。
"""
            
            response = client.responses.create(
                model="gpt-4.1",
                instructions=ai_instructions,
                tools=[
                    {
                        "type": "code_interpreter",
                        "container": {
                            "type": "auto",
                            "file_ids": [uploaded_file.id]
                        }
                    }
                ],
                input=f"我给你{entity}公司{financial_year}年的数据，请给我一个汇总表格"
            )
            logger.info(f"[{request_id}] AI格式化处理完成，Response ID: {response.id}")
            
            # 清理临时文件
            try:
                os.remove(temp_data_file)
                os.rmdir(temp_dir)
                logger.info(f"[{request_id}] 临时文件已清理")
            except Exception as cleanup_error:
                logger.warning(f"[{request_id}] 清理临时文件失败: {cleanup_error}")

            # 打印详细的response结构用于调试
            logger.info(f"[{request_id}] Response结构详情:")
            logger.info(f"[{request_id}] Response内容: {response}")
            
            # 从responses API提取文件信息
            container_id = None
            cfile_id = None
            
            # 检查response.output结构中的文件信息（response.output是一个列表）
            if hasattr(response, 'output') and response.output:
                logger.info(f"[{request_id}] Response output: {response.output}")
                
                # 遍历output列表，寻找container_id和cfile_id
                for item in response.output:
                    logger.info(f"[{request_id}] Output item: {item}")
                    
                    # 提取container_id来自CodeInterpreterToolCall
                    if hasattr(item, "container_id") and item.container_id:
                        container_id = item.container_id
                        logger.info(f"[{request_id}] 找到container_id: {container_id}")
                    
                    # 提取cfile_id来自message中的annotations
                    if getattr(item, "type", "") == "message":
                        for block in getattr(item, "content", []):
                            if hasattr(block, "annotations"):
                                for ann in block.annotations:
                                    logger.info(f"[{request_id}] Annotation: {ann}")
                                    if hasattr(ann, "file_id") and ann.file_id.startswith("cfile_"):
                                        cfile_id = ann.file_id
                                        logger.info(f"[{request_id}] 从annotations找到file_id: {cfile_id}")
                                        break
                    
                    # 也检查其他可能的文件信息位置
                    if hasattr(item, 'annotations') and item.annotations:
                        for annotation in item.annotations:
                            logger.info(f"[{request_id}] Item annotation: {annotation}")
                            
                            # 检查文件下载注释
                            if hasattr(annotation, 'type') and annotation.type == 'file_download':
                                if hasattr(annotation, 'file_download') and hasattr(annotation.file_download, 'file_id'):
                                    cfile_id = annotation.file_download.file_id
                                    logger.info(f"[{request_id}] 从file_download注释找到file_id: {cfile_id}")
                            elif hasattr(annotation, 'file_id'):
                                cfile_id = annotation.file_id
                                logger.info(f"[{request_id}] 从注释找到file_id: {cfile_id}")
            
            # 校验提取结果
            if not container_id or not cfile_id:
                logger.warning(f"[{request_id}] 未能从response中提取container_id或cfile_id")
                logger.warning(f"[{request_id}] container_id: {container_id}, cfile_id: {cfile_id}")
                logger.warning(f"[{request_id}] 将使用确定性计算引擎的结果作为fallback")
                
                # 打印详细的response结构用于调试
                try:
                    if hasattr(response, 'model_dump'):
                        logger.info(f"[{request_id}] Response model_dump: {response.model_dump()}")
                    else:
                        logger.info(f"[{request_id}] Response vars: {vars(response)}")
                except Exception as dump_error:
                    logger.warning(f"[{request_id}] 无法打印response结构: {dump_error}")
                
                # 使用确定性计算引擎的结果作为fallback
                if output_file is None:
                    summary_dir = os.path.join(settings.PROCESSED_DATA_DIR, "summary")
                    os.makedirs(summary_dir, exist_ok=True)
                    output_file = os.path.join(summary_dir, f"PL&BS_{entity}_{financial_year}.xlsx")
                    logger.info(f"[{request_id}] 使用默认输出路径: {output_file}")
                
                # 确保输出目录存在
                output_dir = os.path.dirname(output_file)
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                
                # 直接保存确定性计算引擎的结果
                summary_df.to_excel(output_file, index=False)
                logger.info(f"[{request_id}] 已保存确定性计算引擎的结果到: {output_file}")
                return output_file

            # 成功提取到container_id和cfile_id，下载AI生成的文件
            logger.info(f"[{request_id}] 成功提取到container_id: {container_id}")
            logger.info(f"[{request_id}] 成功提取到cfile_id: {cfile_id}")
            
            # 下载并保存文件
            logger.info(f"[{request_id}] 步骤3: 开始下载生成的文件")
            try:
                # 使用container API下载文件（与database文件保持一致）
                output_file_content = client.containers.files.content.retrieve(
                    container_id=container_id, 
                    file_id=cfile_id
                )
                
                # 如果未提供输出文件路径，则使用默认路径
                if output_file is None:
                    # 使用processed目录下的summary子目录
                    summary_dir = os.path.join(settings.PROCESSED_DATA_DIR, "summary")
                    os.makedirs(summary_dir, exist_ok=True)
                    output_file = os.path.join(summary_dir, f"PL&BS_{entity}_{financial_year}.xlsx")
                    logger.info(f"[{request_id}] 使用默认输出路径: {output_file}")
                
                # 确保输出目录存在
                output_dir = os.path.dirname(output_file)
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                
                with open(output_file, "wb") as f:
                    f.write(output_file_content.read())
                
                logger.info(f"[{request_id}] 已成功保存AI生成的汇总文件: {output_file}")
                return output_file
                
            except Exception as download_error:
                logger.error(f"[{request_id}] 文件下载失败: {str(download_error)}")
                logger.warning(f"[{request_id}] 将使用确定性计算引擎的结果作为fallback")
                
                # 使用确定性计算引擎的结果作为fallback
                if output_file is None:
                    summary_dir = os.path.join(settings.PROCESSED_DATA_DIR, "summary")
                    os.makedirs(summary_dir, exist_ok=True)
                    output_file = os.path.join(summary_dir, f"PL&BS_{entity}_{financial_year}.xlsx")
                    logger.info(f"[{request_id}] 使用默认输出路径: {output_file}")
                
                # 确保输出目录存在
                output_dir = os.path.dirname(output_file)
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                
                # 直接保存确定性计算引擎的结果
                summary_df.to_excel(output_file, index=False)
                logger.info(f"[{request_id}] 已保存确定性计算引擎的结果到: {output_file}")
                return output_file
        
        except Exception as e:
            logger.error(f"[{request_id}] OpenAI API处理失败: {str(e)}")
            raise
    
    except Exception as e:
        logger.error(f"[{request_id}] 生成财务数据汇总时出错: {str(e)}")
        raise


# 示例用法
if __name__ == "__main__":
    # 示例调用
    from src.config import get_settings
    import os
    
    settings = get_settings()
    
    pl_file = os.path.join(settings.INPUT_DATA_DIR, "PL25.xlsx")
    bs_file = os.path.join(settings.INPUT_DATA_DIR, "BS25.xlsx")
    entity = "3"
    year = "2025Forecast"
    
    try:
        output_path = generate_summary(pl_file, bs_file, entity, year)
        print(f"汇总文件已保存到: {output_path}")
    except Exception as e:
        print(f"错误: {str(e)}")
