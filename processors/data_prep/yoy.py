# Author: naohua168 <bai_bai168@qq.com>
"""年度同比页取数（事业部同比 + 客户同比矩阵 + 年基线）

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
    # 当年/基线数据：广东自有客户组中"多组配置"子公司按法人过滤（与销售拆分引擎口径对齐）
    # 法人=广东汽车检测中心 → 广东自有组；其他法人 → 不归广东自有组（走其他配置组）
    data_income_filtered = filter_gd_by_legal(data.income.copy())
    data_payment_filtered = filter_gd_by_legal(data.payment.copy())
    yearly_income_filtered = filter_gd_by_legal(data.yearly_income.copy())
    yearly_payment_filtered = filter_gd_by_legal(data.yearly_payment.copy())
    df_inc = _consolidate_customers(_add_wan(data_income_filtered))
    df_pay = _consolidate_customers(_add_wan(data_payment_filtered))

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

    # 往年基线：与当年同一聚合逻辑（年度页 _consolidate_customers 母公司归拢+销售拆分），
    # 保证 科技公司·王海龙/李巍 等拆分键在当年/往年粒度一致，同比才有意义
    # 基线也按当年同样的口径做广东自有法人过滤（与销售拆分引擎对齐）
    pi = _consolidate_customers(_add_wan(yearly_income_filtered))
    pp = _consolidate_customers(_add_wan(yearly_payment_filtered))
    # 往年数据筛选：汇总模式（所有行同一月份）→ 直接全量；逐月模式 → 按 cur_months 筛选
    _yi_months = pd.to_datetime(pi["日期"], errors="coerce").dt.month if "日期" in pi.columns else pd.Series(dtype=float)
    _yp_months = pd.to_datetime(pp["日期"], errors="coerce").dt.month if "日期" in pp.columns else pd.Series(dtype=float)
    if cur_months and "日期" in pi.columns and _yi_months.nunique() > 1:
        pi = pi[[pd.notna(x) and x.month in cur_months for x in pd.to_datetime(pi["日期"], errors="coerce")]].copy()
    if cur_months and "日期" in pp.columns and _yp_months.nunique() > 1:
        pp = pp[[pd.notna(x) and x.month in cur_months for x in pd.to_datetime(pp["日期"], errors="coerce")]].copy()

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
        d.top_customers, d.top_rest = _resplit_priority(
            all_top, base_dir, yoy_filter, piv=d.inc_cust_piv
        )
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
