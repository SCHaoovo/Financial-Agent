# Financial Reporting Agent

一个端到端的财务报告自动化系统，用于处理、分析和可视化财务数据，并生成专业报告。

## 项目概述

Financial Reporting Agent 是一个基于 FastAPI 的财务数据处理和报告生成系统，主要处理 Excel 格式的利润表(PL)和资产负债表(BS)数据。系统分为四个核心功能模块：

1. **财务数据汇总** - 读取和汇总多期间财务数据
2. **标准化数据生成** - 将原始数据转换为结构化 Excel 格式
3. **财务可视化分析** - 生成关键财务指标的可视化图表
4. **智能财务报告生成** - 利用 Anthropic API 生成专业财务分析报告
5. **一体化工作流** - 端到端的财务数据处理和报告生成流程

## 功能特点

- Excel 财务数据读取与处理
- 多期间财务数据汇总
- 结构化 Excel 数据库生成
- 财务指标可视化
- 同比、环比、预算差异分析
- 贷款分析与财务健康评估
- 基于 LLM 的智能报告生成
- RESTful API 接口

## 安装指南

### 环境要求

- Python 3.8+
- 依赖包（见 requirements.txt）

### 安装步骤

1. 克隆仓库
```bash
git clone https://github.com/yourusername/Financial_Backend.git
cd Financial_Backend
```

2. 创建并激活虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 配置环境变量
创建 `.env` 文件并添加以下内容：
```
OPENAI_API_KEY=your_api_key_here
```

## 使用方法

### 启动服务

```bash
uvicorn src.main:app --reload
```

服务将在 http://localhost:8000 启动，API 文档可在 http://localhost:8000/docs 访问。

### API 端点

- `/finance/summary` - 财务数据汇总相关API
- `/finance/database` - 财务数据库相关API
- `/finance/visualization` - 可视化相关API
- `/finance/reporting` - 分析报告相关API
- `/finance/workflow` - 一体化工作流相关API

## 项目结构

详细的项目结构请参见 [project_structure.md](project_structure.md)

## 许可证

[MIT](LICENSE)

## 联系方式

如有问题或建议，请联系：your-email@example.com 