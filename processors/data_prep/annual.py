# Author: naohua168 <bai_bai168@qq.com>
"""年度达成页取数（当年累计 + 部门卡 + 客户矩阵 + 同比）

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

    # 南方韶关母公司行：法人主体=南方（韶关）且无销售归属的行 → 归入「南方韶关」
    df_inc = _consolidate_customers(_add_wan(data.income.copy()), "收入")
    df_pay = _consolidate_customers(_add_wan(data.payment.copy()), "回款")
    inc_tgt = _consolidate_target(data.annual_income_targets.copy())
    pay_tgt = _consolidate_target(data.annual_payment_targets.copy())

    d.t_inc = float(df_inc["金额_万"].sum())
    d.t_pay = float(df_pay["金额_万"].sum())
    # Hero KPI 指标总数：优先用配置编辑器 KPI指标 覆盖值，未设置则用指标文件合计
    d.t_inc_tgt = _kpi_target(base_dir, "年度达成", "收入", _dept_target_sum(inc_tgt))
    d.t_pay_tgt = _kpi_target(base_dir, "年度达成", "回款", _dept_target_sum(pay_tgt))

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
    # 非指标客户一律折叠到「查看全部」（2026-09-21 用户口径）→ 传归拢后的指标表，与优先展示无关
    d.inc_customers, d.inc_rest = _resplit_priority(
        all_inc, base_dir, annual_filter, tgt=d.inc_tgt_grouped
    )
    d.pay_customers, d.pay_rest = _resplit_priority(
        all_pay, base_dir, annual_filter, tgt=d.pay_tgt_grouped
    )
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
