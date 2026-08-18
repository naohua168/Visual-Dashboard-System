"""
通用工具函数
"""
import pandas as pd


def log_step(source, message, level="INFO"):
    """打印清洗日志"""
    prefix = {"INFO": "  ", "WARN": "  ⚠️ ", "ERROR": "  ❌ ", "OK": "  ✅ "}
    print(f"{prefix.get(level, '  ')}[{source}] {message}")


def read_excel_with_fallback(file_path, sheet_candidates, engine):
    """按候选 sheet 列表读取 Excel，命中第一个存在的 sheet。

    配置中 Sheet 可能为候选数组（如 ["Sheet1", "列表数据"]），
    当第一个不存在时回退到后续候选，全部不存在时取第一个 sheet。

    Args:
        file_path: Excel 文件路径
        sheet_candidates: sheet 名候选列表（或单个字符串）
        engine: pandas 读取引擎（"openpyxl"/"xlrd"/"calamine"）

    Returns:
        读取到的 DataFrame
    """
    if isinstance(sheet_candidates, str):
        sheet_candidates = [sheet_candidates]

    # 若配置为 dict（按 收入/回款 分 sheet），取当前表对应的第一个值
    if isinstance(sheet_candidates, dict):
        sheet_candidates = list(sheet_candidates.values())[0]

    if not sheet_candidates:
        return pd.read_excel(file_path, engine=engine)

    for name in sheet_candidates:
        try:
            return pd.read_excel(file_path, sheet_name=name, engine=engine)
        except (ValueError, KeyError):
            continue

    # 全部候选未命中 → 读取第一个存在的 sheet
    log_step("读取", f"候选 sheet 均未命中 {sheet_candidates}，使用第一个 sheet", "WARN")
    return pd.read_excel(file_path, sheet_name=0, engine=engine)


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
