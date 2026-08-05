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


def infer_company_type(entity):
    """根据法人主体名推断公司类型 (is_gd, is_sz)

    Args:
        entity: 法人主体全称字符串

    Returns:
        (is_gd, is_sz): ("是"/"", "是"/"")
        - "广东汽车检测中心有限公司" → ("是", "")
        - 含"深圳" → ("", "是")
        - 其他 → ("", "")
    """
    if pd.isna(entity):
        return "", ""
    e = str(entity).strip()
    if e == "广东汽车检测中心有限公司":
        return "是", ""
    if "深圳" in e:
        return "", "是"
    return "", ""


def standardize_output(df):
    """标准化输出列顺序"""
    std_cols = ["事业部", "金额", "客户", "法人主体", "日期"]
    for col in std_cols:
        if col not in df.columns:
            df[col] = ""
    return df[std_cols].copy()
