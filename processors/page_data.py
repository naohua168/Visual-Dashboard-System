"""数据层 — 纯数据计算，零 HTML

每个 prepare_*_data() 接收 DashboardData + base_dir，返回一个 typed dataclass。
页面渲染器 (page_*.py) 只负责 HTML 拼接，不再做 pandas 操作。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .utils import safe_float, get_config_range, extract_date_range
from .config_loader import CustomerFilter

DEPARTMENTS = ["检测", "信息", "能源", "海外"]


# ══════════════════════════════════════════════════════════════
# 共享工具函数
# ══════════════════════════════════════════════════════════════
def _add_wan(df: pd.DataFrame) -> pd.DataFrame:
    """原地添加 `金额_万` 列"""
    df["金额_万"] = df["金额"].apply(safe_float) / 10000.0
    return df


def _dept_target_sum(targets: pd.DataFrame) -> float:
    """汇总 4 部门指标合计"""
    return sum(safe_float(targets[d].sum()) for d in DEPARTMENTS if d in targets.columns)


def _yoy_rate(cur: float, prev: float) -> float | None:
    """计算同比率 (cur-prev)/prev，prev=0 时返回 None"""
    return (cur - prev) / prev if prev > 0 else None


def _parse_month_range(base_dir: Path, range_key: str) -> tuple[int, int]:
    """解析配置中的月份范围 "YYYY-MM~YYYY-MM" → (start_month, end_month)"""
    rng = get_config_range(base_dir, range_key)
    if rng and "~" in rng:
        try:
            s = int(rng.split("~")[0].strip().split("-")[1])
            e = int(rng.split("~")[1].strip().split("-")[1])
            return s, e
        except (IndexError, ValueError):
            pass
    return 1, 6


def _data_max_month(df: pd.DataFrame) -> int:
    """从数据中读取实际最大月份"""
    if len(df):
        dates = pd.to_datetime(df["日期"], errors="coerce").dropna()
        if len(dates):
            return int(dates.max().month)
    return 6


def _yoy_from_yearly(yearly: pd.DataFrame | None, cur_val: float,
                     start_m: int, end_m: int) -> float | None:
    """从年基线计算同比"""
    if yearly is None or len(yearly) == 0:
        return None
    yi = yearly.copy()
    yi["月"] = pd.to_datetime(yi["日期"], errors="coerce").dt.month
    prev = float(yi[(yi["月"] >= start_m) & (yi["月"] <= end_m)]["金额"].sum()) / 10000.0
    return _yoy_rate(cur_val, prev)


def _customer_pivot(df: pd.DataFrame, tgt: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """客户 × 事业部 pivot（实际+目标），返回 (pivot_df, target_grouped_df)"""
    piv = df.pivot_table(index="客户", columns="事业部", values="金额_万", aggfunc="sum", fill_value=0)
    av_cols = [d for d in DEPARTMENTS if d in tgt.columns]
    tgt_p = tgt.groupby("客户")[av_cols].sum()
    tgt_p["合计"] = tgt_p.sum(axis=1)
    piv["合计"] = piv.sum(axis=1)
    return piv, tgt_p


def _sorted_customers(tgt_p: pd.DataFrame,
                     filt: CustomerFilter | None = None,
                     piv: pd.DataFrame | None = None,
                     base_dir: Path | None = None) -> list[str]:
    """按目标合计降序排列，包含：有目标 或 有实际 的客户。可选 apply filter

    全部控制权归 filt：
    - filt 有 include → 展开组名 + 白名单匹配 + max_rows 截断
    - filt 无 include 但有 max_rows → 仅按 max_rows 截断
    - filt 完全无配置 → 不截断
    """
    # ① 有目标的客户
    cs = [c for c in tgt_p.index if tgt_p.loc[c, "合计"] > 0]
    # ② 补充：有实际但无目标的客户，避免矩阵合计与 Hero 全公司合计对不上
    if piv is not None:
        for c in piv.index:
            if piv.loc[c, "合计"] > 0 and c not in cs:
                cs.append(c)
    # ③ 排序：有目标按目标降序；无目标按实际降序排在后面
    cs.sort(key=lambda c: (tgt_p.loc[c, "合计"] if c in tgt_p.index else 0,
                           piv.loc[c, "合计"] if piv is not None and c in piv.index else 0),
            reverse=True)
    if filt and (not filt.is_empty() or filt.max_rows > 0):
        cs = filt.apply(cs, piv, tgt_p, base_dir)
    return cs


# ══════════════════════════════════════════════════════════════
# 1. 数据总览
# ══════════════════════════════════════════════════════════════
@dataclass
class OverviewData:
    t_inc: float = 0
    t_pay: float = 0
    t_inc_tgt: float = 0
    t_pay_tgt: float = 0
    yoy_inc: float | None = None
    yoy_pay: float | None = None
    yoy_period: str = ""
    annual_range: str = ""
    date_range: str = ""
    # 部门汇总
    dept_inc: dict[str, float] = field(default_factory=dict)
    dept_pay: dict[str, float] = field(default_factory=dict)
    dept_tgt_inc: dict[str, float] = field(default_factory=dict)
    # 销售 Top
    sales_inc_dict: dict[str, float] = field(default_factory=dict)
    sales_pay_dict: dict[str, float] = field(default_factory=dict)
    sales_tgt: dict[str, float] = field(default_factory=dict)
    sales_inc_total: float = 0
    sales_pay_total: float = 0
    # 原始 DataFrame（保留 for 灵活使用）
    df_inc: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_pay: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_si: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_sp: pd.DataFrame = field(default_factory=pd.DataFrame)


def prepare_overview_data(data, base_dir: Path) -> OverviewData:
    d = OverviewData()

    df_inc = _add_wan(data.income.copy())
    df_pay = _add_wan(data.payment.copy())
    df_si = _add_wan(data.sales_income.copy())
    df_sp = _add_wan(data.sales_payment.copy())
    inc_tgt_df = data.annual_income_targets.copy()
    pay_tgt_df = data.annual_payment_targets.copy()

    d.t_inc = float(df_inc["金额_万"].sum())
    d.t_pay = float(df_pay["金额_万"].sum())
    d.t_inc_tgt = _dept_target_sum(inc_tgt_df)
    d.t_pay_tgt = _dept_target_sum(pay_tgt_df)

    cur_start_m, cur_end_m = _parse_month_range(base_dir, "年度累计")
    cur_end_m = min(cur_end_m, _data_max_month(df_inc))
    cur_year = pd.Timestamp.now().year
    if len(df_inc):
        inc_dates = pd.to_datetime(df_inc["日期"], errors="coerce").dropna()
        if len(inc_dates):
            cur_year = int(inc_dates.min().year)
    d.yoy_period = f"{cur_year}年{cur_start_m:02d}-{cur_end_m:02d}月"
    d.yoy_inc = _yoy_from_yearly(data.yearly_income, d.t_inc, cur_start_m, cur_end_m)
    d.yoy_pay = _yoy_from_yearly(data.yearly_payment, d.t_pay, cur_start_m, cur_end_m)

    d.annual_range = get_config_range(base_dir, "年度累计") or ""
    d.date_range = extract_date_range(data.income)

    # 部门汇总
    for dpt in DEPARTMENTS:
        d.dept_inc[dpt] = float(df_inc[df_inc["事业部"] == dpt]["金额_万"].sum())
        d.dept_pay[dpt] = float(df_pay[df_pay["事业部"] == dpt]["金额_万"].sum())
        d.dept_tgt_inc[dpt] = safe_float(inc_tgt_df[dpt].sum()) if dpt in inc_tgt_df.columns else 0

    # 销售目标（从指标表汇总）
    for _, row in inc_tgt_df.iterrows():
        sales = str(row.get("销售", "")).strip()
        if not sales or sales in ("", "nan"):
            continue
        d.sales_tgt[sales] = d.sales_tgt.get(sales, 0) + sum(
            safe_float(row.get(dpt, 0)) for dpt in DEPARTMENTS
        )

    d.sales_inc_dict = df_si.groupby("销售")["金额_万"].sum().to_dict()
    d.sales_pay_dict = df_sp.groupby("销售")["金额_万"].sum().to_dict()
    d.sales_inc_total = float(df_si["金额_万"].sum())
    d.sales_pay_total = float(df_sp["金额_万"].sum())

    d.df_inc = df_inc; d.df_pay = df_pay; d.df_si = df_si; d.df_sp = df_sp
    return d


# ══════════════════════════════════════════════════════════════
# 2. 年度达成
# ══════════════════════════════════════════════════════════════
@dataclass
class AnnualData:
    t_inc: float = 0
    t_pay: float = 0
    t_inc_tgt: float = 0
    t_pay_tgt: float = 0
    yoy_inc: float | None = None
    yoy_pay: float | None = None
    yoy_period: str = ""
    annual_range: str = ""
    date_range: str = ""
    # 客户矩阵原始数据（收入/回款独立筛选）
    inc_piv: pd.DataFrame = field(default_factory=pd.DataFrame)
    inc_tgt_grouped: pd.DataFrame = field(default_factory=pd.DataFrame)
    pay_piv: pd.DataFrame = field(default_factory=pd.DataFrame)
    pay_tgt_grouped: pd.DataFrame = field(default_factory=pd.DataFrame)
    inc_customers: list[str] = field(default_factory=list)
    pay_customers: list[str] = field(default_factory=list)
    customers: list[str] = field(default_factory=list)
    # 部门卡用 DataFrame
    df_inc: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_pay: pd.DataFrame = field(default_factory=pd.DataFrame)
    inc_tgt_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    pay_tgt_df: pd.DataFrame = field(default_factory=pd.DataFrame)


def prepare_annual_data(data, base_dir: Path) -> AnnualData:
    d = AnnualData()

    df_inc = _add_wan(data.income.copy())
    df_pay = _add_wan(data.payment.copy())
    inc_tgt = data.annual_income_targets.copy()
    pay_tgt = data.annual_payment_targets.copy()

    d.t_inc = float(df_inc["金额_万"].sum())
    d.t_pay = float(df_pay["金额_万"].sum())
    d.t_inc_tgt = _dept_target_sum(inc_tgt)
    d.t_pay_tgt = _dept_target_sum(pay_tgt)

    cur_end_m = min(6, _data_max_month(df_inc))
    cur_year = pd.Timestamp.now().year
    if len(df_inc):
        inc_dates = pd.to_datetime(df_inc["日期"], errors="coerce").dropna()
        if len(inc_dates):
            cur_year = int(inc_dates.min().year)
    d.yoy_period = f"{cur_year}年01-{cur_end_m:02d}月 vs 2024年01-{cur_end_m:02d}月"
    d.yoy_inc = _yoy_from_yearly(data.yearly_income, d.t_inc, 1, cur_end_m)
    d.yoy_pay = _yoy_from_yearly(data.yearly_payment, d.t_pay, 1, cur_end_m)

    d.annual_range = get_config_range(base_dir, "年度累计") or ""
    d.date_range = extract_date_range(data.income)

    # 客户矩阵：最大行数完全从 配置.年度达成.客户矩阵.最大行数 读取（收入/回款独立筛选）
    d.inc_piv, d.inc_tgt_grouped = _customer_pivot(df_inc, inc_tgt)
    d.pay_piv, d.pay_tgt_grouped = _customer_pivot(df_pay, pay_tgt)
    annual_filter = CustomerFilter.from_config(base_dir, "年度达成", section="客户矩阵")
    d.inc_customers = _sorted_customers(
        d.inc_tgt_grouped, filt=annual_filter, piv=d.inc_piv, base_dir=base_dir
    )
    d.pay_customers = _sorted_customers(
        d.pay_tgt_grouped, filt=annual_filter, piv=d.pay_piv, base_dir=base_dir
    )
    d.customers = d.inc_customers

    d.df_inc = df_inc; d.df_pay = df_pay
    d.inc_tgt_df = inc_tgt; d.pay_tgt_df = pay_tgt
    return d


# ══════════════════════════════════════════════════════════════
# 3. 月度达成
# ══════════════════════════════════════════════════════════════
@dataclass
class MonthlyData:
    latest_month: str = ""
    latest_inc: float = 0
    latest_pay: float = 0
    inc_tgt: float = 0
    pay_tgt: float = 0
    yoy_inc: float | None = None
    yoy_pay: float | None = None
    yoy_period: str = ""
    month_range: str = ""
    date_range: str = ""
    # 客户矩阵（收入/回款独立筛选）
    inc_piv: pd.DataFrame = field(default_factory=pd.DataFrame)
    inc_tgt_grouped: pd.DataFrame = field(default_factory=pd.DataFrame)
    pay_piv: pd.DataFrame = field(default_factory=pd.DataFrame)
    pay_tgt_grouped: pd.DataFrame = field(default_factory=pd.DataFrame)
    inc_customers: list[str] = field(default_factory=list)
    pay_customers: list[str] = field(default_factory=list)
    customers: list[str] = field(default_factory=list)
    # 部门卡
    df_inc: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_pay: pd.DataFrame = field(default_factory=pd.DataFrame)
    inc_tgt_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    pay_tgt_df: pd.DataFrame = field(default_factory=pd.DataFrame)


def prepare_monthly_data(data, base_dir: Path) -> MonthlyData:
    d = MonthlyData()

    df_inc = _add_wan(data.income.copy())
    df_pay = _add_wan(data.payment.copy())
    inc_tgt = data.monthly_income_targets.copy()
    pay_tgt = data.monthly_payment_targets.copy()

    df_inc["月份"] = pd.to_datetime(df_inc["日期"], errors="coerce").dt.to_period("M").astype(str)
    df_pay["月份"] = pd.to_datetime(df_pay["日期"], errors="coerce").dt.to_period("M").astype(str)

    months = sorted(set(df_inc["月份"].dropna().tolist() + df_pay["月份"].dropna().tolist()))
    d.latest_month = months[-1] if months else "—"

    # 月度达成页全页统一为最新单月口径（Hero + 部门卡 + 客户矩阵）
    df_inc = df_inc[df_inc["月份"] == d.latest_month].copy()
    df_pay = df_pay[df_pay["月份"] == d.latest_month].copy()
    d.latest_inc = float(df_inc["金额_万"].sum())
    d.latest_pay = float(df_pay["金额_万"].sum())

    d.inc_tgt = _dept_target_sum(inc_tgt)
    d.pay_tgt = _dept_target_sum(pay_tgt)

    # 同比
    cur_year = int(d.latest_month.split('-')[0]) if d.latest_month and "-" in d.latest_month else 2026
    cur_month = int(d.latest_month.split('-')[1]) if d.latest_month and "-" in d.latest_month else 1
    d.yoy_period = f"{cur_year}年{cur_month:02d}月 vs 2024年{cur_month:02d}月"

    if data.yearly_income is not None and len(data.yearly_income):
        yi = data.yearly_income.copy()
        yi["月份"] = pd.to_datetime(yi["日期"], errors="coerce").dt.to_period("M").astype(str)
        latest_year = yi["月份"].str[:4].astype(int).max()
        target_key = f"{latest_year}-{d.latest_month.split('-')[1]}" if d.latest_month and "-" in d.latest_month else ""
        prev_inc = float(yi[yi["月份"] == target_key]["金额"].sum()) / 10000.0 if target_key else 0
        d.yoy_inc = _yoy_rate(d.latest_inc, prev_inc)

    if data.yearly_payment is not None and len(data.yearly_payment):
        yp = data.yearly_payment.copy()
        yp["月份"] = pd.to_datetime(yp["日期"], errors="coerce").dt.to_period("M").astype(str)
        latest_year = yp["月份"].str[:4].astype(int).max()
        target_key = f"{latest_year}-{d.latest_month.split('-')[1]}" if d.latest_month and "-" in d.latest_month else ""
        prev_pay = float(yp[yp["月份"] == target_key]["金额"].sum()) / 10000.0 if target_key else 0
        d.yoy_pay = _yoy_rate(d.latest_pay, prev_pay)

    d.month_range = get_config_range(base_dir, "月度数据") or ""
    d.date_range = extract_date_range(data.income)

    # 客户矩阵（收入/回款独立筛选）
    d.inc_piv, d.inc_tgt_grouped = _customer_pivot(df_inc, inc_tgt)
    d.pay_piv, d.pay_tgt_grouped = _customer_pivot(df_pay, pay_tgt)
    monthly_filter = CustomerFilter.from_config(base_dir, "月度达成", section="客户矩阵")
    d.inc_customers = _sorted_customers(
        d.inc_tgt_grouped, filt=monthly_filter, piv=d.inc_piv, base_dir=base_dir
    )
    d.pay_customers = _sorted_customers(
        d.pay_tgt_grouped, filt=monthly_filter, piv=d.pay_piv, base_dir=base_dir
    )
    d.customers = d.inc_customers

    d.df_inc = df_inc; d.df_pay = df_pay
    d.inc_tgt_df = inc_tgt; d.pay_tgt_df = pay_tgt
    return d


# ══════════════════════════════════════════════════════════════
# 4. 季度达成
# ══════════════════════════════════════════════════════════════
@dataclass
class QuarterlyData:
    quarter: int = 1
    q_start: int = 1
    q_end: int = 3
    total_inc: float = 0
    total_pay: float = 0
    inc_tgt_total: float = 0
    pay_tgt_total: float = 0
    yoy_inc: float | None = None
    yoy_pay: float | None = None
    yoy_period: str = ""
    qtr_range: str = ""
    date_range: str = ""
    # 客户矩阵（收入/回款独立筛选）
    inc_piv: pd.DataFrame = field(default_factory=pd.DataFrame)
    inc_tgt_grouped: pd.DataFrame = field(default_factory=pd.DataFrame)
    pay_piv: pd.DataFrame = field(default_factory=pd.DataFrame)
    pay_tgt_grouped: pd.DataFrame = field(default_factory=pd.DataFrame)
    inc_customers: list[str] = field(default_factory=list)
    pay_customers: list[str] = field(default_factory=list)
    customers: list[str] = field(default_factory=list)
    # 部门卡
    df_inc: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_pay: pd.DataFrame = field(default_factory=pd.DataFrame)
    inc_tgt_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    pay_tgt_df: pd.DataFrame = field(default_factory=pd.DataFrame)


def prepare_quarterly_data(data, base_dir: Path) -> QuarterlyData:
    d = QuarterlyData()

    q_inc = data.quarterly_income
    q_pay = data.quarterly_payment
    if q_inc is None or q_inc.empty or q_pay is None or q_pay.empty:
        q_inc = data.income.copy()
        q_pay = data.payment.copy()

    q_inc = _add_wan(q_inc.copy())
    q_pay = _add_wan(q_pay.copy())

    latest_date = pd.to_datetime(q_inc["日期"].max(), errors="coerce")
    d.quarter = int(latest_date.quarter) if pd.notna(latest_date) else 2

    inc_tgt = data.quarterly_income_targets.copy()
    pay_tgt = data.quarterly_payment_targets.copy()

    d.q_start, d.q_end = _parse_month_range(base_dir, "季度累计筛选")
    if (d.q_start, d.q_end) == (1, 6):  # 未读到配置，推算
        d.q_start = (d.quarter - 1) * 3 + 1
        d.q_end = d.q_start + 2

    d.total_inc = float(q_inc["金额_万"].sum())
    d.total_pay = float(q_pay["金额_万"].sum())
    d.inc_tgt_total = _dept_target_sum(inc_tgt)
    d.pay_tgt_total = _dept_target_sum(pay_tgt)

    cur_year = 2026
    d.yoy_period = f"{cur_year}年{d.q_start:02d}-{d.q_end:02d}月 vs 2024年{d.q_start:02d}-{d.q_end:02d}月"
    d.yoy_inc = _yoy_from_yearly(data.yearly_income, d.total_inc, d.q_start, d.q_end)
    d.yoy_pay = _yoy_from_yearly(data.yearly_payment, d.total_pay, d.q_start, d.q_end)

    d.qtr_range = get_config_range(base_dir, "季度累计筛选") or ""
    d.date_range = extract_date_range(data.quarterly_income)

    # 客户矩阵
    inc_tgt_grouped = inc_tgt.groupby("客户")[
        [c for c in DEPARTMENTS if c in inc_tgt.columns]
    ].sum()
    pay_tgt_grouped = pay_tgt.groupby("客户")[
        [c for c in DEPARTMENTS if c in pay_tgt.columns]
    ].sum()
    inc_tgt_grouped["合计"] = inc_tgt_grouped.sum(axis=1)
    pay_tgt_grouped["合计"] = pay_tgt_grouped.sum(axis=1)
    d.inc_piv, d.inc_tgt_grouped = _customer_pivot(q_inc, inc_tgt)
    d.inc_tgt_grouped = inc_tgt_grouped
    d.pay_piv, d.pay_tgt_grouped = _customer_pivot(q_pay, pay_tgt)
    d.pay_tgt_grouped = pay_tgt_grouped
    quarterly_filter = CustomerFilter.from_config(base_dir, "季度达成", section="客户矩阵")
    d.inc_customers = _sorted_customers(
        inc_tgt_grouped, filt=quarterly_filter, piv=d.inc_piv, base_dir=base_dir
    )
    d.pay_customers = _sorted_customers(
        pay_tgt_grouped, filt=quarterly_filter, piv=d.pay_piv, base_dir=base_dir
    )
    d.customers = d.inc_customers

    d.df_inc = q_inc; d.df_pay = q_pay
    d.inc_tgt_df = inc_tgt; d.pay_tgt_df = pay_tgt
    return d


# ══════════════════════════════════════════════════════════════
# 5. 销售达成
# ══════════════════════════════════════════════════════════════
@dataclass
class SalesData:
    total_target: float = 0
    # 全量（财务端当年累计，含待确认）
    total_inc: float = 0       # sales_income 全量（含待确认）
    total_pay: float = 0       # sales_payment 全量（含待确认）
    total_inc_all: float = 0   # data.income 总和（真正入账）
    total_pay_all: float = 0   # data.payment 总和（真正收款）
    total_inc_split: float = 0 # sales_income 已归属（不含待确认）
    total_pay_split: float = 0 # sales_payment 已归属（不含待确认）
    sales_range: str = ""
    date_range: str = ""
    # 销售目标 + 部门目标
    sales_targets: dict[str, float] = field(default_factory=dict)
    sales_dept_tgt: dict[str, dict[str, float]] = field(default_factory=dict)
    dept_inc_tgt_total: dict[str, float] = field(default_factory=dict)
    dept_pay_tgt_total: dict[str, float] = field(default_factory=dict)
    # 销售实际
    sales_inc: dict[str, float] = field(default_factory=dict)
    sales_pay: dict[str, float] = field(default_factory=dict)
    inc_by_sd: dict[str, dict[str, float]] = field(default_factory=dict)
    pay_by_sd: dict[str, dict[str, float]] = field(default_factory=dict)
    sales_list: list[str] = field(default_factory=list)
    # card3 销售×客户 明细
    sc3_data: dict = field(default_factory=dict)   # {sales: {cust: {inc: {dept:val,...}}}}
    sc3_tgts: dict = field(default_factory=dict)   # {cust: {inc: {dept:val,...}}}
    # 待确认
    pending_count: int = 0
    pending_total_inc: float = 0
    pending_total_pay: float = 0
    pending_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    # 保留给渲染的原始数据
    df_si: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_sp: pd.DataFrame = field(default_factory=pd.DataFrame)
    inc_tgt_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    pay_tgt_df: pd.DataFrame = field(default_factory=pd.DataFrame)

    # 同比
    yoy_inc: float | None = None
    yoy_pay: float | None = None
    yoy_period: str = ""


def prepare_sales_data(data, base_dir: Path) -> SalesData:
    from .sales_pending import build_pending_modal
    d = SalesData()

    d.sales_range = get_config_range(base_dir, "年度累计") or ""
    df_si = _add_wan(data.sales_income.copy())
    df_sp = _add_wan(data.sales_payment.copy())
    inc_tgt = data.annual_income_targets.copy()
    pay_tgt = data.annual_payment_targets.copy()

    # 去待确认
    si_ok = df_si[df_si["销售"] != "待确认"].copy()
    sp_ok = df_sp[df_sp["销售"] != "待确认"].copy()

    # 目标计算
    for _, row in inc_tgt.iterrows():
        sales = str(row.get("销售", "")).strip()
        if not sales or sales in ("待确认", "", "nan"):
            continue
        total = sum(safe_float(row.get(dpt, 0)) for dpt in DEPARTMENTS)
        d.sales_targets[sales] = d.sales_targets.get(sales, 0) + total
        if sales not in d.sales_dept_tgt:
            d.sales_dept_tgt[sales] = {dpt: 0.0 for dpt in DEPARTMENTS}
        for dpt in DEPARTMENTS:
            d.sales_dept_tgt[sales][dpt] += safe_float(row.get(dpt, 0))

    for dpt in DEPARTMENTS:
        d.dept_inc_tgt_total[dpt] = safe_float(inc_tgt[dpt].fillna(0).sum())
        d.dept_pay_tgt_total[dpt] = safe_float(pay_tgt[dpt].fillna(0).sum())

    d.total_target = sum(d.sales_targets.values())
    d.total_inc = float(df_si["金额_万"].sum())   # 销售全量
    d.total_pay = float(df_sp["金额_万"].sum())
    d.total_inc_split = float(si_ok["金额_万"].sum())  # 已归属（不含待确认）
    d.total_pay_split = float(sp_ok["金额_万"].sum())
    d.total_inc_all = float(_add_wan(data.income.copy())["金额_万"].sum())  # 真正入账
    d.total_pay_all = float(_add_wan(data.payment.copy())["金额_万"].sum())

    # 销售实际汇总
    d.sales_inc = si_ok.groupby("销售")["金额_万"].sum().to_dict()
    d.sales_pay = sp_ok.groupby("销售")["金额_万"].sum().to_dict()

    # 销售×事业部
    for _, r in si_ok.groupby(["销售", "事业部"])["金额_万"].sum().reset_index().iterrows():
        s = str(r["销售"]); dpt = str(r["事业部"])
        d.inc_by_sd.setdefault(s, {})[dpt] = safe_float(r["金额_万"])
    for _, r in sp_ok.groupby(["销售", "事业部"])["金额_万"].sum().reset_index().iterrows():
        s = str(r["销售"]); dpt = str(r["事业部"])
        d.pay_by_sd.setdefault(s, {})[dpt] = safe_float(r["金额_万"])

    d.sales_list = sorted(
        [s for s in d.sales_inc if s != "待确认"],
        key=lambda x: d.sales_inc.get(x, 0), reverse=True
    )

    # card3: 销售×客户×事业部 明细
    sc_inc = si_ok.groupby(["销售", "客户", "事业部"])["金额_万"].sum()
    sc_pay = sp_ok.groupby(["销售", "客户", "事业部"])["金额_万"].sum()
    for (s, c, dpt), v in sc_inc.items():
        d.sc3_data.setdefault(s, {}).setdefault(c, {}).setdefault("inc", {})[dpt] = int(round(v))
    for (s, c, dpt), v in sc_pay.items():
        d.sc3_data.setdefault(s, {}).setdefault(c, {}).setdefault("pay", {})[dpt] = int(round(v))
    # 补充 total
    for s_data in d.sc3_data.values():
        for c_data in s_data.values():
            for mt in ("inc", "pay"):
                if mt in c_data:
                    c_data[mt]["total"] = sum(c_data[mt].get(dpt, 0) for dpt in DEPARTMENTS)

    # card3 客户目标
    for _, row in inc_tgt.iterrows():
        cust = str(row.get("客户", "")).strip()
        if not cust:
            continue
        d.sc3_tgts.setdefault(cust, {}).setdefault("inc", {})
        for dpt in DEPARTMENTS:
            d.sc3_tgts[cust]["inc"][dpt] = d.sc3_tgts[cust]["inc"].get(dpt, 0) + int(round(safe_float(row.get(dpt, 0))))
    for _, row in pay_tgt.iterrows():
        cust = str(row.get("客户", "")).strip()
        if not cust:
            continue
        d.sc3_tgts.setdefault(cust, {}).setdefault("pay", {})
        for dpt in DEPARTMENTS:
            d.sc3_tgts[cust]["pay"][dpt] = d.sc3_tgts[cust]["pay"].get(dpt, 0) + int(round(safe_float(row.get(dpt, 0))))
    for c in d.sc3_tgts:
        for mt in ("inc", "pay"):
            if mt in d.sc3_tgts[c]:
                d.sc3_tgts[c][mt]["total"] = sum(d.sc3_tgts[c][mt].get(dpt, 0) for dpt in DEPARTMENTS)

    # 同比
    df_inc_annual = _add_wan(data.income.copy())
    cur_end_m = min(6, _data_max_month(df_inc_annual))
    t_inc_annual = float(df_inc_annual["金额_万"].sum())
    t_pay_annual = float(_add_wan(data.payment.copy())["金额_万"].sum())
    d.yoy_inc = _yoy_from_yearly(data.yearly_income, t_inc_annual, 1, cur_end_m)
    d.yoy_pay = _yoy_from_yearly(data.yearly_payment, t_pay_annual, 1, cur_end_m)
    cur_year = pd.Timestamp.now().year
    d.yoy_period = f"{cur_year}年01-{cur_end_m:02d}月 vs 2024年01-{cur_end_m:02d}月"
    d.date_range = extract_date_range(data.income)

    # 待确认
    pending_inc = df_si[df_si["销售"] == "待确认"].groupby(["客户", "事业部"])["金额_万"].sum().reset_index()
    pending_pay = df_sp[df_sp["销售"] == "待确认"].groupby(["客户", "事业部"])["金额_万"].sum().reset_index()
    pending = pending_inc.merge(pending_pay, on=["客户", "事业部"], how="outer",
                                suffixes=("_收入", "_回款")).fillna(0)
    pending["合计"] = pending["金额_万_收入"] + pending["金额_万_回款"]
    pending = pending.sort_values("合计", ascending=False)
    d.pending_count = len(pending)
    d.pending_total_inc = float(pending["金额_万_收入"].sum())
    d.pending_total_pay = float(pending["金额_万_回款"].sum())
    d.pending_df = pending

    d.df_si = df_si; d.df_sp = df_sp
    d.inc_tgt_df = inc_tgt; d.pay_tgt_df = pay_tgt
    return d


# ══════════════════════════════════════════════════════════════
# 6. 年度同比
# ══════════════════════════════════════════════════════════════
@dataclass
class YoyData:
    has_baseline: bool = True    # 是否有年基线，无则走降级方案
    cur_year: int = 2026
    period: str = ""
    annual_range: str = ""
    date_range: str = ""
    # 当前年 vs 往年 合计
    ci: float = 0
    pvi: float = 0
    cp: float = 0
    pvp: float = 0
    # 部门同比
    dept_yoy: list[dict] = field(default_factory=list)  # [{dept, ci, pi, cp, pp}]
    # 客户同比矩阵原始数据
    inc_cust_piv: pd.DataFrame = field(default_factory=pd.DataFrame)
    inc_prev_piv: pd.DataFrame | None = None
    pay_cust_piv: pd.DataFrame = field(default_factory=pd.DataFrame)
    pay_prev_piv: pd.DataFrame | None = None
    top_customers: list[str] = field(default_factory=list)
    top_n: int = 0  # 配置中的 max_rows，供视图层显示用
    # 降级用
    df_inc: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_pay: pd.DataFrame = field(default_factory=pd.DataFrame)


def prepare_yoy_data(data, base_dir: Path) -> YoyData:
    d = YoyData()

    d.annual_range = get_config_range(base_dir, "年度累计") or ""
    df_inc = _add_wan(data.income.copy())
    df_pay = _add_wan(data.payment.copy())

    d.df_inc = df_inc; d.df_pay = df_pay

    if not data.has_yearly_baseline:
        d.has_baseline = False
        d.ci = float(df_inc["金额_万"].sum())
        d.cp = float(df_pay["金额_万"].sum())
        d.date_range = extract_date_range(data.income)
        if len(df_inc):
            cur_dates = pd.to_datetime(df_inc["日期"], errors="coerce").dropna()
            if len(cur_dates):
                d.cur_year = int(cur_dates.min().year)
        # 降级模式下，top_n 也读自配置（默认 15）以保持显示一致
        yoy_filter = CustomerFilter.from_config(base_dir, "年度同比")
        d.top_n = yoy_filter.max_rows if yoy_filter.max_rows > 0 else 15
        return d

    # 解析月份范围
    cur_start_m, cur_end_m = _parse_month_range(base_dir, "年度累计")
    cur_dates = pd.to_datetime(df_inc["日期"], errors="coerce").dropna()
    d.cur_year = int(cur_dates.min().year) if len(cur_dates) else pd.Timestamp.now().year

    month_label = f"{cur_start_m}-{cur_end_m}月" if cur_start_m != cur_end_m else f"{cur_start_m}月"
    d.period = f"{d.cur_year}年{month_label} vs 2024年{month_label}"
    d.date_range = extract_date_range(data.income)

    cur_months = set(range(cur_start_m, cur_end_m + 1))

    pi = data.yearly_income.copy()
    pp = data.yearly_payment.copy()
    if cur_months and "日期" in pi.columns:
        pd_dates = pd.to_datetime(pi["日期"], errors="coerce")
        pi = pi[[pd.notna(x) and x.month in cur_months for x in pd_dates]].copy()
    if cur_months and "日期" in pp.columns:
        pd_dates = pd.to_datetime(pp["日期"], errors="coerce")
        pp = pp[[pd.notna(x) and x.month in cur_months for x in pd_dates]].copy()

    _add_wan(pi); _add_wan(pp)

    d.ci = float(df_inc["金额_万"].sum()); d.pvi = float(pi["金额_万"].sum())
    d.cp = float(df_pay["金额_万"].sum()); d.pvp = float(pp["金额_万"].sum())

    # 部门同比
    for dept in DEPARTMENTS:
        ci_d = float(df_inc[df_inc["事业部"] == dept]["金额_万"].sum()) if "事业部" in df_inc.columns else 0
        pi_d = float(pi[pi["事业部"] == dept]["金额_万"].sum()) if "事业部" in pi.columns else 0
        cp_d = float(df_pay[df_pay["事业部"] == dept]["金额_万"].sum()) if "事业部" in df_pay.columns else 0
        pp_d = float(pp[pp["事业部"] == dept]["金额_万"].sum()) if "事业部" in pp.columns else 0
        d.dept_yoy.append({"dept": dept, "ci": ci_d, "pi": pi_d, "cp": cp_d, "pp": pp_d})

    # 客户同比矩阵
    d.inc_cust_piv = df_inc.pivot_table(index="客户", columns="事业部", values="金额_万",
                                        aggfunc="sum", fill_value=0)
    d.inc_cust_piv["合计"] = d.inc_cust_piv.sum(axis=1)
    if "事业部" in pi.columns:
        d.inc_prev_piv = pi.pivot_table(index="客户", columns="事业部", values="金额_万",
                                        aggfunc="sum", fill_value=0)
        d.inc_prev_piv["合计"] = d.inc_prev_piv.sum(axis=1)
    d.pay_cust_piv = df_pay.pivot_table(index="客户", columns="事业部", values="金额_万",
                                        aggfunc="sum", fill_value=0)
    d.pay_cust_piv["合计"] = d.pay_cust_piv.sum(axis=1)
    if "事业部" in pp.columns:
        d.pay_prev_piv = pp.pivot_table(index="客户", columns="事业部", values="金额_万",
                                        aggfunc="sum", fill_value=0)
        d.pay_prev_piv["合计"] = d.pay_prev_piv.sum(axis=1)

    # Top 客户：从配置.年度同比.最大行数 读取（默认 15，0 = 不限）
    yoy_filter = CustomerFilter.from_config(base_dir, "年度同比")
    d.top_n = yoy_filter.max_rows if yoy_filter.max_rows > 0 else 15  # 默认 15
    sort_piv = d.inc_cust_piv.copy()
    if yoy_filter.sort_by == "达成率降序":
        # 同比页无目标概念（实际 vs 实际），达成率降序退化为实际金额降序
        sort_piv = sort_piv.sort_values("合计", ascending=False)
    else:
        sort_piv = sort_piv.sort_values("合计", ascending=False)
    d.top_customers = sort_piv.head(d.top_n if d.top_n > 0 else len(sort_piv)).index.tolist()
    # 应用同比页客户筛选规则（筛选优先级 > 排序）
    if not yoy_filter.is_empty():
        d.top_customers = yoy_filter.apply(d.top_customers, d.inc_cust_piv, None, base_dir)
    return d
