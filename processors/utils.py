"""渲染辅助工具 — 金额格式化、百分比计算"""
from __future__ import annotations

import math


def fmt_wan(amount: float | int | None) -> str:
    """金额格式化为万元展示（千分位、无小数）

    输入金额单位：万元（page_data_utils._add_wan 已做 ÷10000 转换）
    本函数仅做千分位格式化，不改变数值。
    """
    if amount is None or (isinstance(amount, float) and math.isnan(amount)):
        return "—"
    try:
        v = float(amount)
    except (TypeError, ValueError):
        return "—"
    if v == 0:
        return "0"
    return f"{v:,.0f}"


def fmt_pct(numerator: float | int | None, denominator: float | int | None) -> str:
    """达成率百分比：numerator/denominator × 100，保留 1 位小数

    分母为 0 或缺失时返回 "—"
    """
    if not denominator or denominator == 0:
        return "—"
    if numerator is None or (isinstance(numerator, float) and math.isnan(numerator)):
        return "—"
    try:
        rate = float(numerator) / float(denominator) * 100
    except (TypeError, ValueError, ZeroDivisionError):
        return "—"
    return f"{rate:.1f}%"


def fmt_yoy(current: float | None, previous: float | None) -> str:
    """同比增长率：(current - previous) / previous × 100，保留 1 位小数

    前值为 0/缺失/None 时返回 "—"
    """
    if previous is None or previous == 0:
        return "—"
    if current is None:
        return "—"
    try:
        rate = (float(current) - float(previous)) / float(previous) * 100
    except (TypeError, ValueError, ZeroDivisionError):
        return "—"
    sign = "+" if rate >= 0 else ""
    return f"{sign}{rate:.1f}%"


def safe_float(v) -> float:
    """安全转 float，None/NaN/非数字返回 0.0"""
    if v is None:
        return 0.0
    try:
        f = float(v)
        if math.isnan(f):
            return 0.0
        return f
    except (TypeError, ValueError):
        return 0.0


def extract_date_range(df, col: str = "日期") -> str:
    """从 DataFrame 日期列提取起止日期

    返回: "YYYY-MM-DD ~ YYYY-MM-DD" 或空字符串
    """
    import pandas as pd
    if df is None or df.empty or col not in df.columns:
        return ""
    try:
        dts = pd.to_datetime(df[col], errors="coerce").dropna()
        if len(dts) == 0:
            return ""
        d_min = dts.min().strftime("%Y-%m-%d")
        d_max = dts.max().strftime("%Y-%m-%d")
        if d_min == d_max:
            return d_min
        return f"{d_min} ~ {d_max}"
    except Exception:
        return ""


def get_config_range(base_dir, key: str) -> str:
    """从 cleaning_config.json 读取配置的时间范围

    key: "月度数据" | "季度累计筛选"
    返回: "YYYY-MM-DD ~ YYYY-MM-DD" 或空字符串
    """
    import json
    from pathlib import Path
    config_path = base_dir / "config" / "清洗配置" / "cleaning_config.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        tr = cfg.get("时间范围", {}).get(key, {})
        start = tr.get("start_date", "")
        end = tr.get("end_date", "")
        # 去掉 end_date 中的时间部分（如 " 23:59:59"）
        end = end.split(" ")[0] if end else ""
        if start and end:
            return f"{start} ~ {end}"
        return ""
    except Exception:
        return ""


def range_banner_html(range_text: str) -> str:
    """生成数据范围 banner HTML（页面内容区顶部）"""
    if not range_text:
        return ""
    return f'<div class="range-banner">数据范围 · {range_text}</div>'
