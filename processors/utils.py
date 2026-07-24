"""渲染辅助工具 — 金额格式化、百分比计算"""
from __future__ import annotations

import math


def fmt_wan(amount: float | int | None) -> str:
    """金额格式化为万元展示（保留 2 位小数 + 千分位）

    输入金额单位：原始元值（财务/运营）或万元（广东/湖南）
    本函数不处理单位换算，仅按"万元"展示数字本身。
    实际调用方在传入前应已统一为万元（÷10000）。
    """
    if amount is None or (isinstance(amount, float) and math.isnan(amount)):
        return "—"
    try:
        v = float(amount)
    except (TypeError, ValueError):
        return "—"
    if v == 0:
        return "0.00"
    return f"{v:,.2f}"


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
