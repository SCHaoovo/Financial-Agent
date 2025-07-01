import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


def calculate_financial_summary(pl_df: pd.DataFrame, bs_df: pd.DataFrame,
                                entity: str, financial_year: str) -> pd.DataFrame:
    """
    根据PL和BS数据框计算财务汇总表
    
    Args:
        pl_df: 利润表DataFrame
        bs_df: 资产负债表DataFrame
        entity: 实体名称
        financial_year: 财务年度
        
    Returns:
        财务汇总表DataFrame
    """
    logger.info(f"开始计算 {entity} {financial_year} 年度财务汇总")

    # 调试：打印数据框结构
    logger.info("=== PL表结构信息 ===")
    logger.info(f"PL表形状: {pl_df.shape}")
    logger.info(f"PL表列名: {list(pl_df.columns)}")
    logger.info(f"PL表前10行第一列内容:")
    for i in range(min(10, len(pl_df))):
        logger.info(f"  第{i}行: {pl_df.iloc[i, 0]}")

    logger.info("=== BS表结构信息 ===")
    logger.info(f"BS表形状: {bs_df.shape}")
    logger.info(f"BS表列名: {list(bs_df.columns)}")
    logger.info(f"BS表前10行第一列内容:")
    for i in range(min(10, len(bs_df))):
        logger.info(f"  第{i}行: {bs_df.iloc[i, 0]}")

    # 定义月份列（假设数据从7月开始到6月结束）
    months = ['July', 'August', 'September', 'October', 'November', 'December',
              'January', 'February', 'March', 'April', 'May', 'June']

    # 初始化汇总表
    summary_data = {}

    # 定义汇总项目
    summary_items = [
        'Revenue',
        'COS',
        'Administrative Expenses',
        'Loan Interest - NAB',
        'Loan Interest - Partners / Inter-co',
        'Other Income',
        'Net Profit/(Loss)',
        'Cash Balance',
        'Loan Payable - NAB',
        'Loan Payables - Partners / Inter-co Loan',
        'Total Equity'
    ]

    # 为每个汇总项目创建数据行
    for item in summary_items:
        summary_data[item] = {}

        # 为每个月份初始化数据
        for month in months:
            summary_data[item][month] = 0.0

        # 为Total和Adjustment Only初始化数据
        summary_data[item]['Total'] = 0.0
        summary_data[item]['Adjustment Only'] = 0.0

    try:
        # 提取PL数据
        logger.info("提取PL表数据...")

        # Revenue: PL表的Total Income
        logger.info("=== 开始匹配Revenue ===")
        revenue_row = find_row_by_keywords(pl_df, ['Total Income'])
        logger.info(f"Revenue匹配结果: 行索引={revenue_row}")
        if revenue_row is not None:
            logger.info(f"找到Revenue数据行: {pl_df.iloc[revenue_row, 0]}")
            extract_monthly_data(pl_df, revenue_row, summary_data['Revenue'], months, True)
        else:
            logger.warning("未找到Revenue匹配行")

        # COS: PL表的Total Cost Of Sales
        logger.info("=== 开始匹配COS ===")
        cos_row = find_row_by_keywords(pl_df, ['Total Cost Of Sales'])
        logger.info(f"COS匹配结果: 行索引={cos_row}")
        if cos_row is not None:
            logger.info(f"找到COS数据行: {pl_df.iloc[cos_row, 0]}")
            extract_monthly_data(pl_df, cos_row, summary_data['COS'], months, True)
        else:
            logger.warning("未找到COS匹配行")

        # Administrative Expenses: PL表的Total General & Administrative Exp
        logger.info("=== 开始匹配Administrative Expenses ===")
        admin_row = find_row_by_keywords(pl_df, ['Total General & Administrative Exp'])
        logger.info(f"Administrative Expenses匹配结果: 行索引={admin_row}")
        if admin_row is not None:
            logger.info(f"找到Administrative Expenses数据行: {pl_df.iloc[admin_row, 0]}")
            extract_monthly_data(pl_df, admin_row, summary_data['Administrative Expenses'], months, True)
        else:
            logger.warning("未找到Administrative Expenses匹配行")

        # Loan Interest - NAB: PL表所有包含"NAB"的项目
        logger.info("=== 开始匹配NAB ===")
        nab_rows = find_rows_by_keywords(pl_df, ['NAB'])
        logger.info(f"NAB匹配结果: 行索引列表={nab_rows}")
        for row_idx in nab_rows:
            logger.info(f"找到NAB数据行: {pl_df.iloc[row_idx, 0]}")
            add_monthly_data(pl_df, row_idx, summary_data['Loan Interest - NAB'], months, True)
        if not nab_rows:
            logger.warning("未找到NAB匹配行")

        # Loan Interest - Partners / Inter-co: PL表中"Interest expense (unit holders)"与"Interest expense (director / friendly loan)"
        logger.info("=== 开始匹配Partners/Inter-co ===")
        partner_rows = find_rows_by_keywords(pl_df, ['Interest expense (unit holders)',
                                                     'Interest expense (director / friendly loan)'])
        logger.info(f"Partners/Inter-co匹配结果: 行索引列表={partner_rows}")
        for row_idx in partner_rows:
            logger.info(f"找到Partners/Inter-co数据行: {pl_df.iloc[row_idx, 0]}")
            add_monthly_data(pl_df, row_idx, summary_data['Loan Interest - Partners / Inter-co'], months, True)
        if not partner_rows:
            logger.warning("未找到Partners/Inter-co匹配行")

        # Other Income: PL表的Total Other Income
        logger.info("=== 开始匹配Other Income ===")
        other_income_row = find_row_by_keywords(pl_df, ['Total Other Income'])
        logger.info(f"Other Income匹配结果: 行索引={other_income_row}")
        if other_income_row is not None:
            logger.info(f"找到Other Income数据行: {pl_df.iloc[other_income_row, 0]}")
            extract_monthly_data(pl_df, other_income_row, summary_data['Other Income'], months, True)
        else:
            logger.warning("未找到Other Income匹配行")

        # Net Profit/(Loss): PL表的Net Profit/(Loss)
        logger.info("=== 开始匹配Net Profit/(Loss) ===")
        net_profit_row = find_row_by_keywords(pl_df, ['Net Profit/(Loss)'])
        logger.info(f"Net Profit/(Loss)匹配结果: 行索引={net_profit_row}")
        if net_profit_row is not None and net_profit_row < len(pl_df):
            logger.info(f"找到Net Profit/(Loss)数据行: {pl_df.iloc[net_profit_row, 0]}")
            extract_monthly_data(pl_df, net_profit_row, summary_data['Net Profit/(Loss)'], months, True)
        else:
            logger.warning("未找到Net Profit/(Loss)匹配行或索引越界")

        # 提取BS数据
        logger.info("提取BS表数据...")

        # BS表数据匹配
        logger.info("=== 开始匹配BS表数据 ===")

        # Cash Balance: BS表的Total Cash On Hand
        logger.info("=== 开始匹配Cash Balance ===")
        cash_row = find_row_by_keywords(bs_df, ['Total Cash On Hand'])
        logger.info(f"Cash Balance匹配结果: 行索引={cash_row}")
        if cash_row is not None:
            logger.info(f"找到Cash Balance数据行: {bs_df.iloc[cash_row, 0]}")
            extract_monthly_data(bs_df, cash_row, summary_data['Cash Balance'], months, True)
        else:
            logger.warning("未找到Cash Balance匹配行")

        # Loan Payable - NAB: BS表中所有带NAB、且为负债类（不包括NAB Term Deposit）
        logger.info("=== 开始匹配Loan Payable - NAB ===")
        loan_rows = find_rows_by_keywords(bs_df, ['NAB'])
        # 过滤掉NAB Term Deposit (资产类)
        filtered_loan_rows = []
        for row_idx in loan_rows:
            row_text = str(bs_df.iloc[row_idx, 0]).strip().upper()
            # 排除NAB Term Deposit (这是资产类，不是负债类)
            if 'TERM DEPOSIT' not in row_text and 'DEPOSIT' not in row_text:
                filtered_loan_rows.append(row_idx)

        logger.info(f"Loan Payable - NAB匹配结果: 行索引列表={filtered_loan_rows}")
        for row_idx in filtered_loan_rows:
            logger.info(f"找到Loan Payable - NAB数据行: {bs_df.iloc[row_idx, 0]}")
            add_monthly_data(bs_df, row_idx, summary_data['Loan Payable - NAB'], months, True)
        if not filtered_loan_rows:
            logger.warning("未找到Loan Payable - NAB匹配行")

        # Loan Payables - Partners / Inter-co Loan: BS表的Total Long Term Liabilities和Total Other Long Term Liabilities
        logger.info("=== 开始匹配Loan Payables - Partners / Inter-co Loan ===")
        long_term_rows = find_rows_by_keywords(bs_df,
                                               ['Total Long Term Liabilities', 'Total Other Long Term Liabilities'])
        logger.info(f"Loan Payables - Partners / Inter-co Loan匹配结果: 行索引列表={long_term_rows}")
        for row_idx in long_term_rows:
            logger.info(f"找到Loan Payables - Partners / Inter-co Loan数据行: {bs_df.iloc[row_idx, 0]}")
            add_monthly_data(bs_df, row_idx, summary_data['Loan Payables - Partners / Inter-co Loan'], months, True)
        if not long_term_rows:
            logger.warning("未找到Loan Payables - Partners / Inter-co Loan匹配行")

        # Total Equity: BS表的Total Equity
        logger.info("=== 开始匹配Total Equity ===")
        equity_row = find_row_by_keywords(bs_df, ['Total Equity'])
        logger.info(f"Total Equity匹配结果: 行索引={equity_row}")
        if equity_row is not None and equity_row < len(bs_df):
            logger.info(f"找到Total Equity数据行: {bs_df.iloc[equity_row, 0]}")
            extract_monthly_data(bs_df, equity_row, summary_data['Total Equity'], months, True)
        else:
            logger.warning("未找到Total Equity匹配行或索引越界")

    except Exception as e:
        logger.warning(f"数据提取过程中出现警告: {e}")

    # 创建最终DataFrame
    result_df = create_summary_dataframe(summary_data, months)

    logger.info("财务汇总计算完成")
    return result_df


def find_row_by_keywords(df: pd.DataFrame, keywords: list) -> Optional[int]:
    """
    根据关键词查找行索引，使用精确匹配
    """
    # 先进行精确匹配
    for idx, row in df.iterrows():
        row_text = str(row.iloc[0]).strip()
        for keyword in keywords:
            if row_text == keyword:
                logger.info(f"精确匹配找到: '{row_text}' 匹配关键词 '{keyword}'")
                return idx

    # 如果精确匹配失败，尝试包含匹配，但排除明显的标题行
    for idx, row in df.iterrows():
        row_text = str(row.iloc[0]).strip()

        # 跳过明显的标题行（单独的词语，如"Income", "Assets"等）
        if len(row_text.split()) <= 1:
            continue

        for keyword in keywords:
            if keyword.upper() in row_text.upper():
                logger.info(f"包含匹配找到: '{row_text}' 包含关键词 '{keyword}'")
                return idx

    return None


def find_rows_by_keywords(df: pd.DataFrame, keywords: list) -> list:
    """
    根据关键词查找所有匹配的行索引
    """
    matching_rows = []
    for idx, row in df.iterrows():
        row_text = str(row.iloc[0]).upper()
        for keyword in keywords:
            if keyword.upper() in row_text:
                matching_rows.append(idx)
                break
    return matching_rows


def extract_monthly_data(df, row_idx, target_dict, months, include_adjustment=False):
    """从DataFrame行中提取月度数据"""
    if row_idx >= len(df):
        logger.warning(f"行索引 {row_idx} 超出DataFrame范围 (总行数: {len(df)})")
        return

    row_data = df.iloc[row_idx]
    logger.info(f"正在提取行数据: {row_data.iloc[0]}")

    # 提取月度数据
    monthly_values = []
    for month in months:
        if month in df.columns:
            value = row_data[month]
            if pd.isna(value) or value == '':
                value = 0.0
            else:
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    logger.warning(f"无法转换 {month} 的值 '{value}' 为数字，使用0")
                    value = 0.0
            target_dict[month] = value
            monthly_values.append(value)
            logger.info(f"  {month}: {value}")
        else:
            target_dict[month] = 0.0
            monthly_values.append(0.0)
            logger.warning(f"  {month}: 列不存在，使用0")

    # 计算Total - 所有12个月的总和
    target_dict['Total'] = sum(monthly_values)
    logger.info(f"  计算Total: {target_dict['Total']} (12个月总和)")

    # 处理Adjustment Only列
    if include_adjustment and 'Adjustment Only' in df.columns:
        adj_value = row_data['Adjustment Only']
        if pd.isna(adj_value) or adj_value == '':
            adj_value = 0.0
        else:
            try:
                adj_value = float(adj_value)
            except (ValueError, TypeError):
                logger.warning(f"无法转换Adjustment Only的值 '{adj_value}' 为数字，使用0")
                adj_value = 0.0
        target_dict['Adjustment Only'] = adj_value
        logger.info(f"  Adjustment Only: {adj_value}")
    else:
        target_dict['Adjustment Only'] = 0.0
        if include_adjustment:
            logger.warning("  Adjustment Only列不存在，使用0")


def add_monthly_data(df, row_idx, target_dict, months, include_adjustment=False):
    """将月度数据累加到目标字典"""
    if row_idx >= len(df):
        logger.warning(f"行索引 {row_idx} 超出DataFrame范围 (总行数: {len(df)})")
        return

    row_data = df.iloc[row_idx]
    logger.info(f"正在累加行数据: {row_data.iloc[0]}")

    # 累加月度数据
    monthly_values = []
    for month in months:
        if month in df.columns:
            value = row_data[month]
            if pd.isna(value) or value == '':
                value = 0.0
            else:
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    logger.warning(f"无法转换 {month} 的值 '{value}' 为数字，使用0")
                    value = 0.0
            target_dict[month] = target_dict.get(month, 0.0) + value
            monthly_values.append(value)
            logger.info(f"  {month}: 当前值={value}, 累计值={target_dict[month]}")
        else:
            logger.warning(f"  {month}: 列不存在，跳过")
            monthly_values.append(0.0)

    # 重新计算Total - 所有12个月的累计总和
    total_sum = sum(target_dict[month] for month in months)
    target_dict['Total'] = total_sum
    logger.info(f"  重新计算Total: {total_sum} (12个月累计总和)")

    # 处理Adjustment Only列
    if include_adjustment and 'Adjustment Only' in df.columns:
        adj_value = row_data['Adjustment Only']
        if pd.isna(adj_value) or adj_value == '':
            adj_value = 0.0
        else:
            try:
                adj_value = float(adj_value)
            except (ValueError, TypeError):
                logger.warning(f"无法转换Adjustment Only的值 '{adj_value}' 为数字，使用0")
                adj_value = 0.0
        target_dict['Adjustment Only'] = target_dict.get('Adjustment Only', 0.0) + adj_value
        logger.info(f"  Adjustment Only: 当前值={adj_value}, 累计值={target_dict['Adjustment Only']}")
    elif include_adjustment:
        logger.warning("  Adjustment Only列不存在，跳过")


def create_summary_dataframe(summary_data: dict, months: list) -> pd.DataFrame:
    """
    创建最终的汇总DataFrame
    """
    # 准备数据
    rows = []

    for account_name, monthly_data in summary_data.items():
        row = {'Account Name': account_name}

        # 添加月份数据
        total = 0.0
        for month in months:
            value = monthly_data.get(month, 0.0)
            row[month] = value
            total += value

        # 添加调整列（从原始数据中提取，如果没有则为0）
        adjustment_value = monthly_data.get('Adjustment Only', 0.0)
        row['Adjustment Only'] = adjustment_value

        # Total = 12个月的总和
        row['Total'] = total

        rows.append(row)

    # 创建DataFrame
    columns = ['Account Name'] + months + ['Adjustment Only', 'Total']
    df = pd.DataFrame(rows, columns=columns)

    return df
