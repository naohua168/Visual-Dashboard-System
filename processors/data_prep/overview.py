# Author: naohua168 <bai_bai168@qq.com>
"""数据总览页取数（Hero 双指标 + 部门矩阵 + 销售榜单）

由 processors/page_data.py 拆分而来（按页面聚合：dataclass + prepare 函数）。
页面模块请 `from ..data_prep import prepare_xxx_data`，或沿用 processors.page_data 兼容层。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import pandas as pd
from ..utils import safe_float, get_config_range
from ..data_utils import (
    _add_wan, _build_subs_detail, _build_subs_with_data,
    _consolidate_customers, _consolidate_target, _customer_pivot,
    _data_max_month, _dept_target_sum, _expand_children_map,
    _get_yearly_year, _group_by_parent, _kpi_target, _load_children_map,
    _parse_month_range, _resplit_priority, _sorted_customers,
    _yoy_from_yearly, _yoy_rate, DEPARTMENTS,
    filter_gd_by_legal,
)


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
    # 数据总览页的年度 KPI 跟随「年度达成」的 KPI指标 覆盖；未设置则用指标文件合计
    d.t_inc_tgt = _kpi_target(base_dir, "年度达成", "收入", _dept_target_sum(inc_tgt_df))
    d.t_pay_tgt = _kpi_target(base_dir, "年度达成", "回款", _dept_target_sum(pay_tgt_df))

    cur_start_m, cur_end_m = _parse_month_range(base_dir, "年度累计")
    cur_end_m = min(cur_end_m, _data_max_month(df_inc))
    cur_year = pd.Timestamp.now().year
    if len(df_inc):
        inc_dates = pd.to_datetime(df_inc["日期"], errors="coerce").dropna()
        if len(inc_dates):
            cur_year = int(inc_dates.min().year)
    d.yoy_period = f"{cur_year}年{cur_start_m:02d}-{cur_end_m:02d}月"
    # 数据总览同比需月份粒度（1-8月 vs 上年同月）；年基线无月份粒度时不显示
    d.yoy_inc = _yoy_from_yearly(data.yearly_income, d.t_inc, cur_start_m, cur_end_m, True)
    d.yoy_pay = _yoy_from_yearly(data.yearly_payment, d.t_pay, cur_start_m, cur_end_m, True)

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
