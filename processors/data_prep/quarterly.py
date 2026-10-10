# Author: naohua168 <bai_bai168@qq.com>
"""季度达成页取数（季度窗口，口径同年度页）

由 processors/page_data.py 拆分而来（按页面聚合：dataclass + prepare 函数）。
页面模块请 `from ..data_prep import prepare_xxx_data`，或沿用 processors.page_data 兼容层。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import pandas as pd
from engine.core.utils import log_step
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
    # 季度累计为空 = 本季度还没有数据（财务端当月未更新 + 运营端未出季度内月份）。
    # 2026-10-09 起不再回退到「当年累计」：回退会把全年累计当季报（如 2026Q4 初期
    # 季度指标 2.1 亿 vs 全年累计 6.9 亿 → 328%），与月度页「无数据即空表」口径一致。
    EMPTY_COLS = ["事业部", "金额", "客户", "法人主体", "日期"]
    q_inc_raw = data.quarterly_income
    q_pay_raw = data.quarterly_payment
    for _label, _frame in (("季度累计收入", q_inc_raw), ("季度累计回款", q_pay_raw)):
        if _frame is None:
            log_step("渲染", f"{_label} 缺失 → 季度页按空表渲染（否决不回退当年累计）", "WARN")
        elif len(_frame) == 0:
            log_step("渲染", f"{_label} 无数据（本季度暂无财务端/运营端数据）→ 季度页按空表渲染", "WARN")
    if q_inc_raw is None or len(q_inc_raw) == 0:
        q_inc_raw = pd.DataFrame(columns=EMPTY_COLS)
    if q_pay_raw is None or len(q_pay_raw) == 0:
        q_pay_raw = pd.DataFrame(columns=EMPTY_COLS)

    # 南方韶关母公司行：法人主体=南方（韶关）且无销售归属的行 → 归入「南方韶关」
    q_inc = _consolidate_customers(_add_wan(q_inc_raw.copy()), "收入")
    q_pay = _consolidate_customers(_add_wan(q_pay_raw.copy()), "回款")

    inc_tgt = _consolidate_target(data.quarterly_income_targets.copy())
    pay_tgt = _consolidate_target(data.quarterly_payment_targets.copy())

    d.q_start, d.q_end = _parse_month_range(base_dir, "季度累计筛选")
    # 「第 N 季度」标签：有数据按数据实际月份，无数据按配置的季度窗口（原来无脑回退第 2 季度）
    latest_date = pd.to_datetime(q_inc["日期"].max(), errors="coerce")
    d.quarter = (int(latest_date.quarter) if pd.notna(latest_date)
                 else ((d.q_start - 1) // 3 + 1 if d.q_start else 2))
    if (d.q_start, d.q_end) == (1, 6):  # 未读到配置，推算
        d.q_start = (d.quarter - 1) * 3 + 1
        d.q_end = d.q_start + 2

    d.total_inc = float(q_inc["金额_万"].sum())
    d.total_pay = float(q_pay["金额_万"].sum())
    # Hero KPI 指标总数：优先用配置编辑器 KPI指标 覆盖值，未设置则用指标文件合计
    d.inc_tgt_total = _kpi_target(base_dir, "季度达成", "收入", _dept_target_sum(inc_tgt))
    d.pay_tgt_total = _kpi_target(base_dir, "季度达成", "回款", _dept_target_sum(pay_tgt))

    cur_year = 2026
    prev_year = _get_yearly_year(base_dir)
    d.yoy_period = f"{cur_year}年{d.q_start:02d}-{d.q_end:02d}月 vs {prev_year}年{d.q_start:02d}-{d.q_end:02d}月"
    # 季度同比需月份粒度（7-9月 vs 上年同季）；年基线无月份粒度时不显示
    d.yoy_inc = _yoy_from_yearly(data.yearly_income, d.total_inc, d.q_start, d.q_end, True)
    d.yoy_pay = _yoy_from_yearly(data.yearly_payment, d.total_pay, d.q_start, d.q_end, True)

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
    # 非指标客户一律折叠到「查看全部」（2026-09-21 用户口径）
    d.inc_customers, d.inc_rest = _resplit_priority(
        all_inc, base_dir, quarterly_filter, tgt=d.inc_tgt_grouped
    )
    d.pay_customers, d.pay_rest = _resplit_priority(
        all_pay, base_dir, quarterly_filter, tgt=d.pay_tgt_grouped
    )
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
