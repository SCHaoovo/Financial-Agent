# Financial Reporting Agent - 项目架构

## 项目概述
构建一个端到端的Financial Reporting Agent，处理Excel格式的财务数据（PL利润表和BS资产负债表），实现数据汇总、标准化、可视化分析和自动报告生成。所有核心功能通过FastAPI暴露为API接口，便于系统集成和远程调用。智能分析和报告生成功能通过Anthropic API实现，利用大型语言模型增强财务洞察能力。

## 目录结构
```
Financial_Backend/
├── src/                      # 源代码目录
│   ├── api/                  # API接口模块
│   │   ├── __init__.py
│   │   └── endpoints/        # API端点定义
│   │       ├── __init__.py
│   │       ├── summary.py    # 数据汇总API
│   │       ├── database.py   # 数据库API
│   │       ├── visualization.py  # 可视化API
│   │       ├── reporting.py  # 报告生成API
│   │       └── workflow.py   # 一体化工作流API
│   ├── summary/              # 数据汇总模块
│   │   ├── __init__.py
│   │   └── generate_summary.py  # 数据汇总功能
│   ├── database/             # 结构化数据模块
│   │   └── generate_financial_database.py  # 结构化Excel生成
│   ├── visualization/        # 可视化模块
│   │   └── plot_summary_graphs.py  # 图表生成
│   ├── reporting/            # 报告生成模块
│   │   └── generate_report_analysis.py  # 报告生成
│   ├── main.py               # FastAPI应用主入口
│   └── config.py             # 应用配置
├── data/                     # 数据目录
│   ├── input/                # 输入数据
│   └── processed/            # 处理后的数据
├── tests/                    # 测试代码
├── requirements.txt          # 项目依赖
└── README.md                 # 项目说明
```

## 核心模块设计

### 1. 财务数据汇总模块 (Step 1)
- **generate_summary.py**: 实现数据汇总功能，处理不同格式的PL和BS表
- **API端点**: `/finance/summary` 路由下的各种端点

### 2. 标准化Excel数据生成模块 (Step 2)
- **generate_financial_database.py**: 实现结构化的Excel文件生成
- **API端点**: `/finance/database` 路由下的各种端点

### 3. 财务可视化分析模块 (Step 3)
- **plot_summary_graphs.py**: 实现各类财务图表绘制功能
- **API端点**: `/finance/visualization` 路由下的各种端点

### 4. 智能财务报告生成模块 (Step 4)
- **generate_report_analysis.py**: 实现财务分析和报告生成功能
- **API端点**: `/finance/reporting` 路由下的各种端点

### 5. 一体化工作流模块
- **workflow.py**: 实现端到端的一体化工作流程
- **API端点**: `/finance/workflow` 路由下的各种端点

### API模块
- **endpoints/**: 定义所有API路由和处理函数
- 主要路由:
  - `/finance/summary`: 数据汇总相关API
  - `/finance/database`: 财务数据库相关API
  - `/finance/visualization`: 可视化相关API
  - `/finance/reporting`: 分析报告相关API
  - `/finance/workflow`: 一体化工作流相关API

### 应用配置模块
- **config.py**: 应用配置和环境设置
- 主要功能:
  - 路径配置
  - API配置
  - Anthropic API配置
  - 日志配置

## 技术栈
- Python 3.8+
- FastAPI: API框架
- Uvicorn: ASGI服务器
- pandas: 数据处理
- openpyxl/xlrd: Excel文件处理
- matplotlib/seaborn/plotly: 数据可视化
- jinja2: 报告模板
- python-docx/pdfkit/weasyprint: 文档生成
- anthropic: 大型语言模型集成
- httpx: HTTP客户端
- python-dotenv: 环境变量管理
- loguru: 日志系统
- pydantic: 数据验证