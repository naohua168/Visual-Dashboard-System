"""数据层 — 纯数据计算，零 HTML

每个 prepare_*_data() 接收 DashboardData + base_dir，返回一个 typed dataclass。
页面渲染器 (page_*.py) 只负责 HTML 拼接，不再做 pandas 操作。

共享工具已拆分为 page_data_utils.py，此文件只保留 6 个 dataclass + 6 个 prepare 函数。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .utils import safe_float, get_config_range
from .config_loader import CustomerFilter
from .page_data_utils import (
    _add_wan, _build_subs_detail, _build_subs_with_data,
    _consolidate_customers, _consolidate_target, _customer_pivot,
    _data_max_month, _dept_target_sum, _expand_children_map,
    _get_yearly_year, _group_by_parent, _load_children_map,
    _parse_month_range, _resplit_priority, _sorted_customers,
    _yoy_from_yearly, _yoy_rate, DEPARTMENTS,
)


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

    df_inc = _consolidate_customers(_add_wan(data.income.copy()))
    df_pay = _consolidate_customers(_add_wan(data.payment.copy()))
    df_si = _consolidate_customers(_add_wan(data.sales_income.copy()))
    df_sp = _consolidate_customers(_add_wan(data.sales_payment.copy()))
    inc_tgt_df = _consolidate_target(data.annual_income_targets.copy())
    pay_tgt_df = _consolidate_target(data.annual_payment_targets.copy())

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
    d.date_range = d.annual_range

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
    inc_rest: list[str] = field(default_factory=list)
    pay_customers: list[str] = field(default_factory=list)
    pay_rest: list[str] = field(default_factory=list)
    customers: list[str] = field(default_factory=list)
    # 弹窗：母公司→有数据的子公司列表
    subs_with_data: dict = field(default_factory=dict)
    # 弹窗：母公司→子公司×4部门实际/目标明细
    subs_detail_inc: dict = field(default_factory=dict)
    subs_detail_pay: dict = field(default_factory=dict)
    # 左侧列表：母公司→全量子公司名列表（来自 children_map）
    subs_all: dict = field(default_factory=dict)
    # 部门卡用 DataFrame
    df_inc: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_pay: pd.DataFrame = field(default_factory=pd.DataFrame)
    inc_tgt_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    pay_tgt_df: pd.DataFrame = field(default_factory=pd.DataFrame)


def prepare_annual_data(data, base_dir: Path) -> AnnualData:
    d = AnnualData()

    df_inc = _consolidate_customers(_add_wan(data.income.copy()))
    df_pay = _consolidate_customers(_add_wan(data.payment.copy()))
    inc_tgt = _consolidate_target(data.annual_income_targets.copy())
    pay_tgt = _consolidate_target(data.annual_payment_targets.copy())

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
    prev_year = _get_yearly_year(base_dir)
    d.yoy_period = f"{cur_year}年01-{cur_end_m:02d}月 vs {prev_year}年01-{cur_end_m:02d}月"
    d.yoy_inc = _yoy_from_yearly(data.yearly_income, d.t_inc, 1, cur_end_m)
    d.yoy_pay = _yoy_from_yearly(data.yearly_payment, d.t_pay, 1, cur_end_m)

    d.annual_range = get_config_range(base_dir, "年度累计") or ""
    d.date_range = d.annual_range

    # 客户矩阵：最大行数完全从 配置.年度达成.客户矩阵.最大行数 读取（收入/回款独立筛选）
    d.inc_piv, d.inc_tgt_grouped = _customer_pivot(df_inc, inc_tgt)
    d.pay_piv, d.pay_tgt_grouped = _customer_pivot(df_pay, pay_tgt)
    annual_filter = CustomerFilter.from_config(base_dir, "年度达成", section="客户矩阵")
    d.inc_customers, d.inc_rest = _sorted_customers(
        d.inc_tgt_grouped, filt=annual_filter, piv=d.inc_piv, base_dir=base_dir
    )
    d.pay_customers, d.pay_rest = _sorted_customers(
        d.pay_tgt_grouped, filt=annual_filter, piv=d.pay_piv, base_dir=base_dir
    )

    # 母公司归拢（合并 + 分组 + 重新拆分优先/其余）
    d.inc_piv, d.inc_tgt_grouped, all_inc = _group_by_parent(
        d.inc_piv, d.inc_tgt_grouped, d.inc_customers + d.inc_rest, base_dir
    )
    d.pay_piv, d.pay_tgt_grouped, all_pay = _group_by_parent(
        d.pay_piv, d.pay_tgt_grouped, d.pay_customers + d.pay_rest, base_dir
    )
    d.inc_customers, d.inc_rest = _resplit_priority(all_inc, base_dir, annual_filter)
    d.pay_customers, d.pay_rest = _resplit_priority(all_pay, base_dir, annual_filter)
    d.customers = d.inc_customers

    # 弹窗：构建"有数据"的子公司列表（去重合并 inc/pay 客户表）
    children_map = _expand_children_map(_load_children_map())
    all_parents = list({*d.inc_customers, *d.inc_rest, *d.pay_customers, *d.pay_rest})
    d.subs_all = children_map  # 左侧列表：全量子公司名（配置来源）
    d.subs_with_data = _build_subs_with_data(
        [data.income, data.payment],
        [data.annual_income_targets, data.annual_payment_targets],
        children_map, all_parents,
    )
    d.subs_detail_inc = _build_subs_detail(
        data.income, data.annual_income_targets, children_map, all_parents
    )
    d.subs_detail_pay = _build_subs_detail(
        data.payment, data.annual_payment_targets, children_map, all_parents
    )

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
    inc_rest: list[str] = field(default_factory=list)
    pay_customers: list[str] = field(default_factory=list)
    pay_rest: list[str] = field(default_factory=list)
    customers: list[str] = field(default_factory=list)
    # 弹窗：母公司→有数据的子公司列表
    subs_with_data: dict = field(default_factory=dict)
    # 弹窗：母公司→子公司×4部门实际/目标明细
    subs_detail_inc: dict = field(default_factory=dict)
    subs_detail_pay: dict = field(default_factory=dict)
    # 左侧列表：母公司→全量子公司名列表（来自 children_map）
    subs_all: dict = field(default_factory=dict)
    # 部门卡
    df_inc: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_pay: pd.DataFrame = field(default_factory=pd.DataFrame)
    inc_tgt_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    pay_tgt_df: pd.DataFrame = field(default_factory=pd.DataFrame)


def prepare_monthly_data(data, base_dir: Path) -> MonthlyData:
    d = MonthlyData()

    # ── 月明细数据（清洗引擎已按月度配置时间窗口过滤好） ──
    raw_inc = data.monthly_income_detail
    raw_pay = data.monthly_payment_detail

    # 月明细为空 → 当月无源数据（财务端未更新），显示空表
    if raw_inc is None:
        raw_inc = pd.DataFrame(columns=["事业部", "金额", "客户", "法人主体", "日期"])
    if raw_pay is None:
        raw_pay = pd.DataFrame(columns=["事业部", "金额", "客户", "法人主体", "日期"])

    df_inc = _consolidate_customers(_add_wan(raw_inc.copy()))
    df_pay = _consolidate_customers(_add_wan(raw_pay.copy()))
    inc_tgt = _consolidate_target(data.monthly_income_targets.copy())
    pay_tgt = _consolidate_target(data.monthly_payment_targets.copy())

    # 月明细已按配置窗口过滤 → 直接汇总即为当月数据
    d.latest_inc = float(df_inc["金额_万"].sum())
    d.latest_pay = float(df_pay["金额_万"].sum())
    d.latest_month = "—"

    # 从月明细推断实际月份（用于同比标签）
    if len(df_inc):
        dates = pd.to_datetime(df_inc["日期"], errors="coerce").dropna()
        if len(dates):
            d.latest_month = f"{dates.min().year}-{int(dates.min().month):02d}"
    elif len(df_pay):
        dates = pd.to_datetime(df_pay["日期"], errors="coerce").dropna()
        if len(dates):
            d.latest_month = f"{dates.min().year}-{int(dates.min().month):02d}"

    d.inc_tgt = _dept_target_sum(inc_tgt)
    d.pay_tgt = _dept_target_sum(pay_tgt)

    # 同比
    cur_year = int(d.latest_month.split('-')[0]) if d.latest_month and "-" in d.latest_month else 2026
    cur_month = int(d.latest_month.split('-')[1]) if d.latest_month and "-" in d.latest_month else 1
    prev_year = _get_yearly_year(base_dir)
    d.yoy_period = f"{cur_year}年{cur_month:02d}月 vs {prev_year}年{cur_month:02d}月"

    if data.yearly_income is not None and len(data.yearly_income):
        yi = data.yearly_income.copy()
        yi["月份"] = pd.to_datetime(yi["日期"], errors="coerce").dt.to_period("M").astype(str)
        if yi["月份"].nunique() > 1:
            latest_year = yi["月份"].str[:4].astype(int).max()
            target_key = f"{latest_year}-{d.latest_month.split('-')[1]}" if d.latest_month and "-" in d.latest_month else ""
            prev_inc = float(yi[yi["月份"] == target_key]["金额"].sum()) / 10000.0 if target_key else 0
            d.yoy_inc = _yoy_rate(d.latest_inc, prev_inc)

    if data.yearly_payment is not None and len(data.yearly_payment):
        yp = data.yearly_payment.copy()
        yp["月份"] = pd.to_datetime(yp["日期"], errors="coerce").dt.to_period("M").astype(str)
        if yp["月份"].nunique() > 1:
            latest_year = yp["月份"].str[:4].astype(int).max()
            target_key = f"{latest_year}-{d.latest_month.split('-')[1]}" if d.latest_month and "-" in d.latest_month else ""
            prev_pay = float(yp[yp["月份"] == target_key]["金额"].sum()) / 10000.0 if target_key else 0
            d.yoy_pay = _yoy_rate(d.latest_pay, prev_pay)

    d.month_range = get_config_range(base_dir, "月度数据") or ""
    d.date_range = d.month_range or "—"

    # 客户矩阵（收入/回款独立筛选）
    d.inc_piv, d.inc_tgt_grouped = _customer_pivot(df_inc, inc_tgt)
    d.pay_piv, d.pay_tgt_grouped = _customer_pivot(df_pay, pay_tgt)
    monthly_filter = CustomerFilter.from_config(base_dir, "月度达成", section="客户矩阵")
    d.inc_customers, d.inc_rest = _sorted_customers(
        d.inc_tgt_grouped, filt=monthly_filter, piv=d.inc_piv, base_dir=base_dir
    )
    d.pay_customers, d.pay_rest = _sorted_customers(
        d.pay_tgt_grouped, filt=monthly_filter, piv=d.pay_piv, base_dir=base_dir
    )

    # 母公司归拢
    d.inc_piv, d.inc_tgt_grouped, all_inc = _group_by_parent(
        d.inc_piv, d.inc_tgt_grouped, d.inc_customers + d.inc_rest, base_dir
    )
    d.pay_piv, d.pay_tgt_grouped, all_pay = _group_by_parent(
        d.pay_piv, d.pay_tgt_grouped, d.pay_customers + d.pay_rest, base_dir
    )
    d.inc_customers, d.inc_rest = _resplit_priority(all_inc, base_dir, monthly_filter)
    d.pay_customers, d.pay_rest = _resplit_priority(all_pay, base_dir, monthly_filter)
    d.customers = d.inc_customers

    # 弹窗：构建"有数据"的子公司列表（含销售拆分键，如 科技公司·王海龙 → 只列该销售子公司）
    children_map = _expand_children_map(_load_children_map())
    all_parents = list({*d.inc_customers, *d.inc_rest, *d.pay_customers, *d.pay_rest})
    d.subs_all = children_map  # 左侧列表：全量子公司名（配置来源）
    d.subs_with_data = _build_subs_with_data(
        [raw_inc, raw_pay],
        [data.monthly_income_targets, data.monthly_payment_targets],
        children_map, all_parents,
    )
    d.subs_detail_inc = _build_subs_detail(
        raw_inc, data.monthly_income_targets, children_map, all_parents
    )
    d.subs_detail_pay = _build_subs_detail(
        raw_pay, data.monthly_payment_targets, children_map, all_parents
    )

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
    inc_rest: list[str] = field(default_factory=list)
    pay_customers: list[str] = field(default_factory=list)
    pay_rest: list[str] = field(default_factory=list)
    customers: list[str] = field(default_factory=list)
    # 弹窗：母公司→有数据的子公司列表
    subs_with_data: dict = field(default_factory=dict)
    # 弹窗：母公司→子公司×4部门实际/目标明细
    subs_detail_inc: dict = field(default_factory=dict)
    subs_detail_pay: dict = field(default_factory=dict)
    # 左侧列表：母公司→全量子公司名列表（来自 children_map）
    subs_all: dict = field(default_factory=dict)
    # 部门卡
    df_inc: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_pay: pd.DataFrame = field(default_factory=pd.DataFrame)
    inc_tgt_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    pay_tgt_df: pd.DataFrame = field(default_factory=pd.DataFrame)


def prepare_quarterly_data(data, base_dir: Path) -> QuarterlyData:
    d = QuarterlyData()

    # 保留原始数据（未 consolidate）供子公司弹窗使用
    q_inc_raw = data.quarterly_income
    q_pay_raw = data.quarterly_payment
    if q_inc_raw is None or q_inc_raw.empty or q_pay_raw is None or q_pay_raw.empty:
        q_inc_raw = data.income.copy()
        q_pay_raw = data.payment.copy()

    q_inc = _consolidate_customers(_add_wan(q_inc_raw.copy()))
    q_pay = _consolidate_customers(_add_wan(q_pay_raw.copy()))

    latest_date = pd.to_datetime(q_inc["日期"].max(), errors="coerce")
    d.quarter = int(latest_date.quarter) if pd.notna(latest_date) else 2

    inc_tgt = _consolidate_target(data.quarterly_income_targets.copy())
    pay_tgt = _consolidate_target(data.quarterly_payment_targets.copy())

    d.q_start, d.q_end = _parse_month_range(base_dir, "季度累计筛选")
    if (d.q_start, d.q_end) == (1, 6):  # 未读到配置，推算
        d.q_start = (d.quarter - 1) * 3 + 1
        d.q_end = d.q_start + 2

    d.total_inc = float(q_inc["金额_万"].sum())
    d.total_pay = float(q_pay["金额_万"].sum())
    d.inc_tgt_total = _dept_target_sum(inc_tgt)
    d.pay_tgt_total = _dept_target_sum(pay_tgt)

    cur_year = 2026
    prev_year = _get_yearly_year(base_dir)
    d.yoy_period = f"{cur_year}年{d.q_start:02d}-{d.q_end:02d}月 vs {prev_year}年{d.q_start:02d}-{d.q_end:02d}月"
    d.yoy_inc = _yoy_from_yearly(data.yearly_income, d.total_inc, d.q_start, d.q_end)
    d.yoy_pay = _yoy_from_yearly(data.yearly_payment, d.total_pay, d.q_start, d.q_end)

    d.qtr_range = get_config_range(base_dir, "季度累计筛选") or ""
    d.date_range = d.qtr_range

    # 客户矩阵 — 指标值+客户列表均用季度目标（sort=False 保留指标表顺序）
    inc_tgt_grouped = inc_tgt.groupby("客户", sort=False)[
        [c for c in DEPARTMENTS if c in inc_tgt.columns]
    ].sum()
    pay_tgt_grouped = pay_tgt.groupby("客户", sort=False)[
        [c for c in DEPARTMENTS if c in pay_tgt.columns]
    ].sum()
    inc_tgt_grouped["合计"] = inc_tgt_grouped.sum(axis=1)
    pay_tgt_grouped["合计"] = pay_tgt_grouped.sum(axis=1)
    d.inc_piv, d.inc_tgt_grouped = _customer_pivot(q_inc, inc_tgt)
    d.inc_tgt_grouped = inc_tgt_grouped
    d.pay_piv, d.pay_tgt_grouped = _customer_pivot(q_pay, pay_tgt)
    d.pay_tgt_grouped = pay_tgt_grouped

    quarterly_filter = CustomerFilter.from_config(base_dir, "季度达成", section="客户矩阵")
    d.inc_customers, d.inc_rest = _sorted_customers(
        inc_tgt_grouped, filt=quarterly_filter, piv=d.inc_piv, base_dir=base_dir
    )
    d.pay_customers, d.pay_rest = _sorted_customers(
        pay_tgt_grouped, filt=quarterly_filter, piv=d.pay_piv, base_dir=base_dir
    )

    # 母公司归拢
    d.inc_piv, d.inc_tgt_grouped, all_inc = _group_by_parent(
        d.inc_piv, d.inc_tgt_grouped, d.inc_customers + d.inc_rest, base_dir
    )
    d.pay_piv, d.pay_tgt_grouped, all_pay = _group_by_parent(
        d.pay_piv, d.pay_tgt_grouped, d.pay_customers + d.pay_rest, base_dir
    )
    d.inc_customers, d.inc_rest = _resplit_priority(all_inc, base_dir, quarterly_filter)
    d.pay_customers, d.pay_rest = _resplit_priority(all_pay, base_dir, quarterly_filter)
    d.customers = d.inc_customers

    # 弹窗：构建"有数据"的子公司列表（用原始未 consolidate 数据，保留子公司独立行；
    # 含销售拆分键，如 科技公司·王海龙 → 只列该销售子公司）
    children_map = _expand_children_map(_load_children_map())
    all_parents = list({*d.inc_customers, *d.inc_rest, *d.pay_customers, *d.pay_rest})
    d.subs_all = children_map  # 左侧列表：全量子公司名（配置来源）
    d.subs_with_data = _build_subs_with_data(
        [q_inc_raw, q_pay_raw],
        [data.quarterly_income_targets, data.quarterly_payment_targets],
        children_map, all_parents,
    )
    d.subs_detail_inc = _build_subs_detail(
        q_inc_raw, data.quarterly_income_targets, children_map, all_parents
    )
    d.subs_detail_pay = _build_subs_detail(
        q_pay_raw, data.quarterly_payment_targets, children_map, all_parents
    )

    d.df_inc = q_inc; d.df_pay = q_pay
    d.inc_tgt_df = inc_tgt; d.pay_tgt_df = pay_tgt
    return d


# ══════════════════════════════════════════════════════════════
# 5. 销售达成
# ══════════════════════════════════════════════════════════════
@dataclass
class SalesData:
    total_target: float = 0         # 年度收入指标按销售聚合的总额（卡片1收入合计分母）
    total_pay_target: float = 0     # 年度回款指标按销售聚合的总额（卡片1回款合计分母）
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
    sales_targets: dict[str, float] = field(default_factory=dict)        # 销售→年度收入指标 4 部门合计
    sales_payment_targets: dict[str, float] = field(default_factory=dict)  # 销售→年度回款指标 4 部门合计
    sales_dept_tgt: dict[str, dict[str, float]] = field(default_factory=dict)
    dept_inc_tgt_total: dict[str, float] = field(default_factory=dict)
    dept_pay_tgt_total: dict[str, float] = field(default_factory=dict)
    # 销售实际
    sales_inc: dict[str, float] = field(default_factory=dict)
    sales_pay: dict[str, float] = field(default_factory=dict)
    inc_by_sd: dict[str, dict[str, float]] = field(default_factory=dict)
    pay_by_sd: dict[str, dict[str, float]] = field(default_factory=dict)
    sales_list: list[str] = field(default_factory=list)
    pay_sales_list: list[str] = field(default_factory=list)
    # card3 销售×客户 明细
    sc3_data: dict = field(default_factory=dict)   # {sales: {cust: {inc: {dept:val,...}}}}
    sc3_tgts: dict = field(default_factory=dict)   # {cust: {inc: {dept:val,...}}}（全销售聚合，兼容）
    # 按销售拆分的客户目标（销售详情弹窗/矩阵用）
    sc3_tgts_by_sales: dict = field(default_factory=dict)  # {sales: {cust: {inc/pay: {dept:val,total}}}}
    # card3 母公司聚合
    sub_to_parent: dict[str, str] = field(default_factory=dict)   # 子公司→母公司（后写覆盖，仅用于无销售歧义时）
    sub_sales_to_parent: dict[tuple[str, str], str] = field(default_factory=dict)  # (子公司,销售)→父组，重叠客户按销售归属父组
    sc3_by_parent: dict = field(default_factory=dict)    # {sales: {parent: {sub: {inc/pay: {dept:val}}}}}
    sc3_tgts_by_parent: dict = field(default_factory=dict)   # {parent: {inc/pay: {dept:val}}}（全销售聚合，兼容）
    # 按销售拆分的母公司目标（销售详情弹窗/矩阵用）
    sc3_tgts_by_parent_by_sales: dict = field(default_factory=dict)  # {sales: {parent: {inc/pay: {dept:val,total}}}}
    sc3_parent_cfg_total: dict = field(default_factory=dict)  # {parent: 配置子公司总数}
    sales_owned_subs: dict = field(default_factory=dict)  # {销售: {母公司: 该销售在配置中拥有的子公司数}}
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
    df_si = _consolidate_customers(_add_wan(data.sales_income.copy()))
    df_sp = _consolidate_customers(_add_wan(data.sales_payment.copy()))
    inc_tgt = _consolidate_target(data.annual_income_targets.copy())
    pay_tgt = _consolidate_target(data.annual_payment_targets.copy())

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

    # 年度回款指标按销售聚合（卡片1回款列分母 — 与收入指标独立）
    for _, row in pay_tgt.iterrows():
        sales = str(row.get("销售", "")).strip()
        if not sales or sales in ("待确认", "", "nan"):
            continue
        total = sum(safe_float(row.get(dpt, 0)) for dpt in DEPARTMENTS)
        d.sales_payment_targets[sales] = d.sales_payment_targets.get(sales, 0) + total

    for dpt in DEPARTMENTS:
        d.dept_inc_tgt_total[dpt] = safe_float(inc_tgt[dpt].fillna(0).sum())
        d.dept_pay_tgt_total[dpt] = safe_float(pay_tgt[dpt].fillna(0).sum())

    d.total_target = sum(d.sales_targets.values())
    d.total_pay_target = sum(d.sales_payment_targets.values())
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

    # 销售列表 = 指标表里的销售 ∪ 实际数据里出现过的销售（去重 + 排"待确认"），保证 0 指标销售也展示
    all_sales_inc = set(d.sales_inc.keys()) | set(d.sales_targets.keys()) | set(d.sales_payment_targets.keys())
    all_sales_pay = set(d.sales_pay.keys()) | set(d.sales_targets.keys()) | set(d.sales_payment_targets.keys())
    all_sales_inc.discard("待确认")
    all_sales_pay.discard("待确认")
    d.sales_list = sorted(
        [s for s in all_sales_inc if s],
        key=lambda x: d.sales_targets.get(x, 0), reverse=True
    )
    d.pay_sales_list = sorted(
        [s for s in all_sales_pay if s],
        key=lambda x: d.sales_targets.get(x, 0), reverse=True
    )

    # card3: 销售×母公司×客户×事业部 明细（用未consolidate的原始数据，保留子公司独立行）
    # "母公司"列由拆分引擎写入（重叠子公司按法人主体选择父组）
    si_raw = _add_wan(data.sales_income.copy())
    sp_raw = _add_wan(data.sales_payment.copy())
    si_raw_ok = si_raw[si_raw["销售"] != "待确认"].copy()
    sp_raw_ok = sp_raw[sp_raw["销售"] != "待确认"].copy()

    def _grp_key(df):
        keys = ["销售", "客户", "事业部"]
        if "母公司" in df.columns:
            keys.insert(1, "母公司")
        return keys

    sc_inc = si_raw_ok.groupby(_grp_key(si_raw_ok))["金额_万"].sum()
    sc_pay = sp_raw_ok.groupby(_grp_key(sp_raw_ok))["金额_万"].sum()
    for idx, v in sc_inc.items():
        if "母公司" in si_raw_ok.columns:
            s, parent, c, dpt = idx
        else:
            s, c, dpt = idx
            parent = d.sub_to_parent.get(c, c)
        d.sc3_by_parent.setdefault(s, {}).setdefault(parent, {}).setdefault(c, {}).setdefault("inc", {})[dpt] = int(round(v))
    for idx, v in sc_pay.items():
        if "母公司" in sp_raw_ok.columns:
            s, parent, c, dpt = idx
        else:
            s, c, dpt = idx
            parent = d.sub_to_parent.get(c, c)
        d.sc3_by_parent.setdefault(s, {}).setdefault(parent, {}).setdefault(c, {}).setdefault("pay", {})[dpt] = int(round(v))
    # 补充 total
    for s_data in d.sc3_by_parent.values():
        for p_data in s_data.values():
            for c_data in p_data.values():
                for mt in ("inc", "pay"):
                    if mt in c_data:
                        c_data[mt]["total"] = sum(c_data[mt].get(dpt, 0) for dpt in DEPARTMENTS)

    # card3 客户目标（全销售聚合 + 按销售拆分两版本）
    # 注意：直接读原始指标表（不经过 _consolidate_target），客户键保留子公司原名，
    # 与 sc3_by_parent（来自销售拆分实际数据、按子公司名组织）对齐，避免合并后
    # 客户键变成 '科技公司·王海龙' 导致矩阵子公司行匹配不到目标。
    raw_inc_tgt = data.annual_income_targets
    raw_pay_tgt = data.annual_payment_targets
    for _, row in raw_inc_tgt.iterrows():
        cust = str(row.get("客户", "")).strip()
        sales = str(row.get("销售", "")).strip()
        if not cust:
            continue
        d.sc3_tgts.setdefault(cust, {}).setdefault("inc", {})
        # 按销售拆分：目标归属到销售名下（销售个人目标 = 该客户该部门的个人指标）
        if sales and sales not in ("待确认", "", "nan"):
            s_tgt = d.sc3_tgts_by_sales.setdefault(sales, {}).setdefault(cust, {}).setdefault("inc", {})
            for dpt in DEPARTMENTS:
                v = int(round(safe_float(row.get(dpt, 0))))
                d.sc3_tgts[cust]["inc"][dpt] = d.sc3_tgts[cust]["inc"].get(dpt, 0) + v
                s_tgt[dpt] = s_tgt.get(dpt, 0) + v
        else:
            for dpt in DEPARTMENTS:
                d.sc3_tgts[cust]["inc"][dpt] = d.sc3_tgts[cust]["inc"].get(dpt, 0) + int(round(safe_float(row.get(dpt, 0))))
    for _, row in raw_pay_tgt.iterrows():
        cust = str(row.get("客户", "")).strip()
        sales = str(row.get("销售", "")).strip()
        if not cust:
            continue
        d.sc3_tgts.setdefault(cust, {}).setdefault("pay", {})
        if sales and sales not in ("待确认", "", "nan"):
            s_tgt = d.sc3_tgts_by_sales.setdefault(sales, {}).setdefault(cust, {}).setdefault("pay", {})
            for dpt in DEPARTMENTS:
                v = int(round(safe_float(row.get(dpt, 0))))
                d.sc3_tgts[cust]["pay"][dpt] = d.sc3_tgts[cust]["pay"].get(dpt, 0) + v
                s_tgt[dpt] = s_tgt.get(dpt, 0) + v
        else:
            for dpt in DEPARTMENTS:
                d.sc3_tgts[cust]["pay"][dpt] = d.sc3_tgts[cust]["pay"].get(dpt, 0) + int(round(safe_float(row.get(dpt, 0))))
    for c in d.sc3_tgts:
        for mt in ("inc", "pay"):
            if mt in d.sc3_tgts[c]:
                d.sc3_tgts[c][mt]["total"] = sum(d.sc3_tgts[c][mt].get(dpt, 0) for dpt in DEPARTMENTS)
    # 按销售版本补 total
    for s_data in d.sc3_tgts_by_sales.values():
        for cust_data in s_data.values():
            for mt in ("inc", "pay"):
                if mt in cust_data:
                    cust_data[mt]["total"] = sum(cust_data[mt].get(dpt, 0) for dpt in DEPARTMENTS)

    # card3 母公司聚合：子公司→母公司 + 按母公司汇总实际/目标
    import json as _json
    attr_path = base_dir / "config" / "清洗配置" / "客户销售归属.json"
    if attr_path.exists():
        with open(attr_path, "r", encoding="utf-8") as _f:
            _attr = _json.load(_f)
        for parent, group in _attr.get("客户归属", {}).items():
            # 母公司配置的子公司总数（含母公司自身，若配置列出）
            d.sc3_parent_cfg_total[parent] = len(group.get("子公司", {}))
            for sub, sub_cfg in group.get("子公司", {}).items():
                sub_key = sub.strip()
                d.sub_to_parent[sub_key] = parent
                # 该子公司归属哪些销售（从配置的部门销售分配读取）
                sales_set: set[str] = set()
                if isinstance(sub_cfg, dict):
                    for metric_cfg in sub_cfg.values():
                        if isinstance(metric_cfg, dict):
                            for dept_cfg in metric_cfg.values():
                                if isinstance(dept_cfg, dict):
                                    sales_set.update(str(s).strip() for s in dept_cfg.keys())
                # 记录 (子公司, 销售) → 父组：重叠客户（同子公司归属多父组）按销售区分
                for s_name in sales_set:
                    d.sub_sales_to_parent[(sub_key, s_name)] = parent
                    d.sales_owned_subs.setdefault(s_name, {}).setdefault(parent, 0)
                    d.sales_owned_subs[s_name][parent] += 1

    # 按母公司汇总目标（全销售聚合版本，不含 total，后面统一补）
    for cust, cust_data in d.sc3_tgts.items():
        parent = d.sub_to_parent.get(cust, cust)
        p_data = d.sc3_tgts_by_parent.setdefault(parent, {})
        for mt in ("inc", "pay"):
            if mt not in cust_data:
                continue
            p_mt = p_data.setdefault(mt, {})
            for dpt, val in cust_data[mt].items():
                if dpt != "total":
                    p_mt[dpt] = p_mt.get(dpt, 0) + val
    for p_data in d.sc3_tgts_by_parent.values():
        for mt in ("inc", "pay"):
            if mt in p_data:
                p_data[mt]["total"] = sum(p_data[mt].get(dpt, 0) for dpt in DEPARTMENTS)

    # 按销售拆分版本：母公司目标聚合（{销售: {母公司: {inc/pay: {dept}}}}）
    # 重叠客户（同子公司归属多父组）时按 (客户,销售) 查父组，如 福龙马+黎国键→广东自有客户、福龙马+江国川→福建市场
    for sales, s_data in d.sc3_tgts_by_sales.items():
        for cust, cust_data in s_data.items():
            parent = d.sub_sales_to_parent.get((cust, sales)) or d.sub_to_parent.get(cust, cust)
            p_data = d.sc3_tgts_by_parent_by_sales.setdefault(sales, {}).setdefault(parent, {})
            for mt in ("inc", "pay"):
                if mt not in cust_data:
                    continue
                p_mt = p_data.setdefault(mt, {})
                for dpt, val in cust_data[mt].items():
                    if dpt != "total":
                        p_mt[dpt] = p_mt.get(dpt, 0) + val
    for s_data in d.sc3_tgts_by_parent_by_sales.values():
        for p_data in s_data.values():
            for mt in ("inc", "pay"):
                if mt in p_data:
                    p_data[mt]["total"] = sum(p_data[mt].get(dpt, 0) for dpt in DEPARTMENTS)

    # 同比
    df_inc_annual = _add_wan(data.income.copy())
    cur_end_m = min(6, _data_max_month(df_inc_annual))
    t_inc_annual = float(df_inc_annual["金额_万"].sum())
    t_pay_annual = float(_add_wan(data.payment.copy())["金额_万"].sum())
    d.yoy_inc = _yoy_from_yearly(data.yearly_income, t_inc_annual, 1, cur_end_m)
    d.yoy_pay = _yoy_from_yearly(data.yearly_payment, t_pay_annual, 1, cur_end_m)
    cur_year = pd.Timestamp.now().year
    prev_year = _get_yearly_year(base_dir)
    d.yoy_period = f"{cur_year}年01-{cur_end_m:02d}月 vs {prev_year}年01-{cur_end_m:02d}月"
    d.annual_range = get_config_range(base_dir, "年度累计") or ""
    d.date_range = d.annual_range

    # 待确认 — 按 (客户, 事业部, 法人主体) 拆分，同客户同事业部下不同法人主体分行展示
    si_p = df_si[df_si["销售"] == "待确认"].copy()
    sp_p = df_sp[df_sp["销售"] == "待确认"].copy()
    grp_keys = ["客户", "事业部", "法人主体"] if "法人主体" in si_p.columns else ["客户", "事业部"]
    pending_inc = si_p.groupby(grp_keys, dropna=False)["金额_万"].sum().reset_index()
    pending_pay = sp_p.groupby(grp_keys, dropna=False)["金额_万"].sum().reset_index()
    pending = pending_inc.merge(pending_pay, on=grp_keys, how="outer",
                                suffixes=("_收入", "_回款")).fillna(0)
    pending["合计"] = pending["金额_万_收入"] + pending["金额_万_回款"]
    pending = pending.sort_values("合计", ascending=False).reset_index(drop=True)
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
    prev_year: int = 2024        # 配置中的往年基准年份
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
    top_rest: list[str] = field(default_factory=list)
    top_n: int = 0  # 配置中的 max_rows，供视图层显示用
    # 降级用
    df_inc: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_pay: pd.DataFrame = field(default_factory=pd.DataFrame)


def prepare_yoy_data(data, base_dir: Path) -> YoyData:
    d = YoyData()
    d.prev_year = _get_yearly_year(base_dir)

    d.annual_range = get_config_range(base_dir, "年度累计") or ""
    df_inc = _consolidate_customers(_add_wan(data.income.copy()))
    df_pay = _consolidate_customers(_add_wan(data.payment.copy()))

    d.df_inc = df_inc; d.df_pay = df_pay

    if not data.has_yearly_baseline:
        d.has_baseline = False
        d.ci = float(df_inc["金额_万"].sum())
        d.cp = float(df_pay["金额_万"].sum())
        d.date_range = d.annual_range
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
    prev_year = _get_yearly_year(base_dir)
    d.period = f"{d.cur_year}年{month_label} vs {prev_year}年{month_label}"
    d.date_range = d.annual_range
    cur_months = set(range(cur_start_m, cur_end_m + 1))

    pi = data.yearly_income.copy()
    pp = data.yearly_payment.copy()
    # 往年数据筛选：汇总模式（所有行同一月份）→ 直接全量；逐月模式 → 按 cur_months 筛选
    _yi_months = pd.to_datetime(pi["日期"], errors="coerce").dt.month if "日期" in pi.columns else pd.Series(dtype=float)
    _yp_months = pd.to_datetime(pp["日期"], errors="coerce").dt.month if "日期" in pp.columns else pd.Series(dtype=float)
    if cur_months and "日期" in pi.columns and _yi_months.nunique() > 1:
        pi = pi[[pd.notna(x) and x.month in cur_months for x in pd.to_datetime(pi["日期"], errors="coerce")]].copy()
    if cur_months and "日期" in pp.columns and _yp_months.nunique() > 1:
        pp = pp[[pd.notna(x) and x.month in cur_months for x in pd.to_datetime(pp["日期"], errors="coerce")]].copy()

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

    # Top 客户：从年度收入指标获取客户列表（与季度页一致）
    yoy_filter = CustomerFilter.from_config(base_dir, "年度同比")
    d.top_n = yoy_filter.max_rows if yoy_filter.max_rows > 0 else 15  # 默认 15
    annual_tgt = _consolidate_target(data.annual_income_targets.copy())
    annual_tgt_g = annual_tgt.groupby("客户")[
        [c for c in DEPARTMENTS if c in annual_tgt.columns]
    ].sum()
    annual_tgt_g["合计"] = annual_tgt_g.sum(axis=1)
    d.top_customers, d.top_rest = _sorted_customers(
        annual_tgt_g, filt=yoy_filter, piv=d.inc_cust_piv, base_dir=base_dir
    )

    # 母公司归拢（同比页 pivot 变量名不同）
    if d.top_customers or d.top_rest:
        all_top = d.top_customers + d.top_rest
        d.inc_cust_piv, _, all_top = _group_by_parent(
            d.inc_cust_piv, pd.DataFrame(), all_top, base_dir
        )
        d.top_customers, d.top_rest = _resplit_priority(all_top, base_dir, yoy_filter)
        if d.inc_prev_piv is not None:
            d.inc_prev_piv, _, _ = _group_by_parent(
                d.inc_prev_piv, pd.DataFrame(), [], base_dir
            )
        d.pay_cust_piv, _, _ = _group_by_parent(
            d.pay_cust_piv, pd.DataFrame(), [], base_dir
        )
        if d.pay_prev_piv is not None:
            d.pay_prev_piv, _, _ = _group_by_parent(
                d.pay_prev_piv, pd.DataFrame(), [], base_dir
            )
    return d
