# Author: naohua168 <bai_bai168@qq.com>
"""
通用工具函数
"""
from pathlib import Path

import pandas as pd

from .config import end_of_day
from .name_key import is_gd_legal, is_sz_legal

# 项目根目录（engine/core/utils.py → 上三级）；供 rel_path() 计算相对显示路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent


def rel_path(p) -> str:
    """路径 → 相对项目根显示（日志/提示专用；不在项目根下时原样返回）

    交付验收要求「日志中不出现宿主机的 F:\\... 等绝对路径」（docs/部署指南.md），
    运行时的真实读写仍用传入的完整路径，本函数只影响显示文本。
    """
    try:
        return str(Path(p).relative_to(BASE_DIR))
    except (ValueError, TypeError):
        return str(p)


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
    """日期范围筛选（结束时间只写到「日」时补到当天 23:59:59，避免漏掉当天数据）"""
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_of_day(end_date))
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
    # 按匹配键判定（全角半角/空白差异不影响，2026-09-29）
    if is_gd_legal(entity):
        return "是", ""
    if is_sz_legal(entity):
        return "", "是"
    return "", ""


def clean_customer_name(name) -> str:
    """清理客户名：去首尾空白 + 去尾部多余括号（全/半角）+ 去空括号对 + 重复空格

    例：
      "新丰县国防动员办公室）"  → "新丰县国防动员办公室"
      " 某某（测试）公司 "       → "某某（测试）公司"
      "某公司（）"               → "某公司"
    """
    if pd.isna(name):
        return ""
    s = str(name).strip()
    # 去掉尾部多余的右括号（全角） ），只保留左括号开头的成对内容
    while s.endswith("）") or s.endswith(")"):
        # 统计成对数量：若整串右括号多于左括号，说明尾部有多余右括号
        open_cnt = s.count("（") + s.count("(")
        close_cnt = s.count("）") + s.count(")")
        if close_cnt > open_cnt:
            s = s[:-1]
        else:
            break
    # 去掉空括号对（如 某公司（） / 某公司() ）
    import re
    s = re.sub(r"（\s*）", "", s)
    s = re.sub(r"\(\s*\)", "", s)
    # 合并连续空白
    s = re.sub(r"\s+", " ", s).strip()
    return s


# 标准输出列（清洗结果统一口径；空的/失败的来源也按这套列返回，下游 concat 才安全）
STD_COLUMNS = ["事业部", "金额", "客户", "法人主体", "日期"]


def empty_standard_df() -> pd.DataFrame:
    """空的标准输出表（读取失败 / 空表时用）"""
    return pd.DataFrame(columns=STD_COLUMNS)


def standardize_output(df):
    """标准化输出列顺序，并对客户列做名称清理"""
    for col in STD_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    if "客户" in df.columns:
        df["客户"] = df["客户"].apply(clean_customer_name)
    return df[STD_COLUMNS].copy()
