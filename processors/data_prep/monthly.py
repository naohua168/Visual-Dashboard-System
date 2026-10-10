# Author: naohua168 <bai_bai168@qq.com>
"""月度达成页取数（当月窗口，口径同年度页）

由 processors/page_data.py 拆分而来（按页面聚合：dataclass + prepare 函数）。
页面模块请 `from ..data_prep import prepare_xxx_data`，或沿用 processors.page_data 兼容层。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import pandas as pd
from ..utils import safe_float, get_config_range
from ..config_loader import CustomerFilter
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

    # 南方韶关母公司行：法人主体=南方（韶关）且无销售归属的行 → 归入「南方韶关」
    df_inc = _consolidate_customers(_add_wan(raw_inc.copy()), "收入")
    df_pay = _consolidate_customers(_add_wan(raw_pay.copy()), "回款")
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

    # Hero KPI 指标总数：优先用配置编辑器 KPI指标 覆盖值，未设置则用指标文件合计
    d.inc_tgt = _kpi_target(base_dir, "月度达成", "收入", _dept_target_sum(inc_tgt))
    d.pay_tgt = _kpi_target(base_dir, "月度达成", "回款", _dept_target_sum(pay_tgt))

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
    # 非指标客户一律折叠到「查看全部」（2026-09-21 用户口径）
    d.inc_customers, d.inc_rest = _resplit_priority(
        all_inc, base_dir, monthly_filter, tgt=d.inc_tgt_grouped
    )
    d.pay_customers, d.pay_rest = _resplit_priority(
        all_pay, base_dir, monthly_filter, tgt=d.pay_tgt_grouped
    )
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
