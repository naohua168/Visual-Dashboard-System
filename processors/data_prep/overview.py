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
    # 部门 × 客户明细（点击部门行打开的弹窗）：部门 → [[客户, 收入实际, 收入指标, 回款实际, 回款指标], ...]
    dept_customers: dict[str, list[list]] = field(default_factory=dict)
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


def _pivot_actual(df: pd.DataFrame) -> pd.DataFrame:
    """清洗表 → 客户 × 事业部（金额_万）"""
    if df is None or len(df) == 0 or "客户" not in df.columns:
        return pd.DataFrame(columns=DEPARTMENTS)
    g = df.copy()
    g["客户"] = g["客户"].astype(str).str.strip()
    return g.groupby(["客户", "事业部"])["金额_万"].sum().unstack(fill_value=0.0)


def _pivot_target(df_tgt: pd.DataFrame) -> pd.DataFrame:
    """指标表 → 客户 × 部门（万元；指标表每个部门一列）"""
    if df_tgt is None or len(df_tgt) == 0 or "客户" not in df_tgt.columns:
        return pd.DataFrame(columns=DEPARTMENTS)
    cols = [c for c in DEPARTMENTS if c in df_tgt.columns]
    if not cols:
        return pd.DataFrame(columns=DEPARTMENTS)
    g = df_tgt.copy()
    g["客户"] = g["客户"].astype(str).str.strip()
    return g.groupby("客户")[cols].sum()


def _val_of(m: pd.DataFrame, dept: str, name: str) -> float:
    """取 客户×部门 的金额（万元），缺失按 0"""
    if dept not in m.columns or name not in m.index:
        return 0.0
    return round(safe_float(m.at[name, dept]), 1)


def _dept_customer_rows(df_inc, df_pay, inc_tgt_df, pay_tgt_df,
                        raw_inc=None, raw_pay=None,
                        raw_inc_tgt=None, raw_pay_tgt=None) -> dict[str, list[list]]:
    """部门 → 客户明细行（万元），按「收入实际 + 回款实际」降序

    每行 `[客户, 收入实际, 收入指标, 回款实际, 回款指标, 子公司明细?]`；
    有子公司时追加第 6 项：`[[子公司, 收入实际, 收入指标, 回款实际, 回款指标], ...]`
    （母公司行是归拢后的数，子行是归拢前的原始数，二者都由同一份清洗结果算出）。

    只保留该部门有实际或有指标的客户（指标>0 说明该客户被分配了该部门目标）。
    """
    inc_act = _pivot_actual(df_inc)
    pay_act = _pivot_actual(df_pay)
    inc_tgt = _pivot_target(inc_tgt_df)
    pay_tgt = _pivot_target(pay_tgt_df)
    # 归拢前的原始透视（用于拆子公司）
    raw_ia = _pivot_actual(raw_inc) if raw_inc is not None else None
    raw_pa = _pivot_actual(raw_pay) if raw_pay is not None else None
    raw_it = _pivot_target(raw_inc_tgt) if raw_inc_tgt is not None else None
    raw_pt = _pivot_target(raw_pay_tgt) if raw_pay_tgt is not None else None
    children = _load_children_map()

    out: dict[str, list[list]] = {}
    for dept in DEPARTMENTS:
        names: set[str] = set()
        for m in (inc_act, pay_act, inc_tgt, pay_tgt):
            if dept in m.columns:
                col = pd.to_numeric(m[dept], errors="coerce").fillna(0.0)
                names |= {str(i) for i in col.index[col != 0]}

        rows: list[list] = []
        for name in names:
            row = [name, _val_of(inc_act, dept, name), _val_of(inc_tgt, dept, name),
                   _val_of(pay_act, dept, name), _val_of(pay_tgt, dept, name)]
            subs = children.get(name) or []
            sub_rows: list[list] = []
            for sub in subs:
                sub = str(sub).strip()
                if not sub or sub == name:
                    continue
                vals = [
                    _val_of(raw_ia, dept, sub) if raw_ia is not None else 0.0,
                    _val_of(raw_it, dept, sub) if raw_it is not None else 0.0,
                    _val_of(raw_pa, dept, sub) if raw_pa is not None else 0.0,
                    _val_of(raw_pt, dept, sub) if raw_pt is not None else 0.0,
                ]
                if any(vals):                       # 该部门没数就不列这家子公司
                    sub_rows.append([sub, vals[0], vals[1], vals[2], vals[3]])
            if sub_rows:
                sub_rows.sort(key=lambda r: (-(r[1] + r[3]), r[0]))
                row.append(sub_rows)
            rows.append(row)

        rows.sort(key=lambda r: (-(r[1] + r[3]), -r[2], r[0]))
        out[dept] = rows
    return out


def prepare_overview_data(data, base_dir: Path) -> OverviewData:
    d = OverviewData()

    # 归拢前保留一份（部门弹窗要拆子公司）；_consolidate_* 一律用副本，避免原地改动
    raw_inc = _add_wan(data.income.copy())
    raw_pay = _add_wan(data.payment.copy())
    raw_inc_tgt = data.annual_income_targets.copy()
    raw_pay_tgt = data.annual_payment_targets.copy()
    df_inc = _consolidate_customers(raw_inc.copy())
    df_pay = _consolidate_customers(raw_pay.copy())
    df_si = _consolidate_customers(_add_wan(data.sales_income.copy()))
    df_sp = _consolidate_customers(_add_wan(data.sales_payment.copy()))
    inc_tgt_df = _consolidate_target(raw_inc_tgt.copy())
    pay_tgt_df = _consolidate_target(raw_pay_tgt.copy())

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

    d.dept_customers = _dept_customer_rows(
        df_inc, df_pay, inc_tgt_df, pay_tgt_df,
        raw_inc=raw_inc, raw_pay=raw_pay,
        raw_inc_tgt=raw_inc_tgt, raw_pay_tgt=raw_pay_tgt,
    )

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
