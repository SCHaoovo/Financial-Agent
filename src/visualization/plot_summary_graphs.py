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
                instructions="""你是一个擅长使用 Python、Pandas 和 Matplotlib 的资深金融数据可视化专家。
                
                你将接收到一个 Summary Table 格式的 Excel 文件，其中包含多个财务年度的月度财务数据。你的任务是读取、清洗并生成基础的趋势图表，并将结果导出为 Word 文件。
                
### 表格格式说明：

Excel 文件中包含一张或多张表格，表结构如下：

- 列（Columns）包括：
  - Entities（公司名）、Financial Year（如 FY24 Actual）、Account Description 1、Account Description 2
  - 各个月份：July 到 June（12列）
  - Total（全年合计）

- 行（Rows）是财务项目，以 Account Description 2 为主，示例如下：
  - Revenue、COS、Administrative Expenses、Net Profit/(Loss)、Cash Balance、Loan Payables、Total Equity 等

---

### 工作任务（请依步骤完成）

### 1. 数据读取与清洗
- 使用 Pandas 读取 Excel 文件；
- 按照 Financial Year 分组，提取以下四个字段的 12 个月数据：
  - Revenue
  - COS
  - Administrative Expenses
  - Net Profit/(Loss)

### 2. 图表生成
请使用 Matplotlib 生成以下图像，图表风格简洁、统一，横轴为月份（July ~ June）：
请生成一张图，包含 4 个子图，每个子图展示一个指标的“不同财年月度对比折线图”，要求如下：

####  图像结构
- 使用 `matplotlib` 的 subplot 排版为 2 行 × 2 列，共 4 个子图；
- 整张图大小设为 `figsize=(12, 8)`；
- 主标题使用 "Financial Metrics Monthly Comparison by Financial Year"，字号请比子标题大一些
- 字体统一使用Arial

####  背景与美观
- 整张图背景为白色（`fig.patch.set_facecolor("white")`）；
- 每个子图绘图区背景设置为浅灰色 `#f0f0f0`（使用 `ax.set_facecolor(...)`）；

####  主色调设置（每个指标固定颜色）：
- Revenue：红色
- COS：橙色
- Administrative Expenses：蓝色
- Net Profit/(Loss)：绿色

> 同一指标的不同财年：请使用**同一色系不同深浅** + **线型变化（如实线、虚线）** 进行区分；比如深红直线与浅红虚线
> 所有线条 `linewidth=2`，确保清晰可读；

#### ️ 坐标轴与标签
- 横轴为月份（July ~ June），如有重叠请使用 `plt.xticks(rotation=30)`；
- 总图的标题为"Monthly Comparison by Financial Year"
- 所有子图需有标题格式：“{变量名} Comparison”
- 图例放在图内右上角或右侧，使用 `ax.legend(title="Financial Year")`

### 3. Word 文件输出
- 文档可选封面，不强制图注；
- 使用 `docx` 标准样式即可，避免复杂排版。

### 输出要求

- 最终必须输出一个 Word 文件 `Visualization_{公司名}.docx`；
- 无论中间是否有数据缺失或图表部分失败，**都必须创建并返回 Word 文件对象**；
- 使用 `Code Interpreter` 工具生成文件，并**明确将该文件作为输出返回**，以便我在 response.output.annotations 中拿到 `cfile_id`；
- 请勿中断任务，也不要只输出图像或自然语言内容，**必须返回 Word 文件本体**。

---

### 注意事项

- 不要求添加表格汇总、统计指标；
- 请勿省略 Word 文件返回；
- 保持图像大小适中（避免高清过大）。

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
    database_file = "E:\Finance\Financial_Backend\data\processed\database\DB_Test0701.xlsx"
    entity = "Test0711"
    
    try:
        output_path = plot_summary_graphs(database_file, entity)
        print(f"可视化文件已保存至: {output_path}")
    except Exception as e:
        print(f"错误: {str(e)}")