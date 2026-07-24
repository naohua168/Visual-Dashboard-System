"""
通用工具函数
"""
import pandas as pd


def log_step(source, message, level="INFO"):
    """打印清洗日志"""
    prefix = {"INFO": "  ", "WARN": "  ⚠️ ", "ERROR": "  ❌ ", "OK": "  ✅ "}
    print(f"{prefix.get(level, '  ')}[{source}] {message}")


def filter_by_date(df, date_col, start_date, end_date):
    """日期范围筛选"""
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    mask = (df[date_col] >= start) & (df[date_col] <= end)
    return df[mask].copy()


def init_company_type(df):
    """初始化公司类型列为空字符串"""
    df = df.copy()
    df["是否为广东公司"] = ""
    df["是否为深圳公司"] = ""
    return df


def standardize_output(df):
    """标准化输出列顺序"""
    std_cols = ["事业部", "金额", "客户", "日期", "是否为广东公司", "是否为深圳公司"]
    for col in std_cols:
        if col not in df.columns:
            df[col] = ""
    return df[std_cols].copy()
