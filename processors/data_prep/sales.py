# Author: naohua168 <bai_bai168@qq.com>
"""销售达成页取数（3 卡片 + 客户/母公司聚合 + 待确认客户）

由 processors/page_data.py 拆分而来（按页面聚合：dataclass + prepare 函数）。
页面模块请 `from ..data_prep import prepare_xxx_data`，或沿用 processors.page_data 兼容层。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import pandas as pd
from engine.core.name_key import KeyedLookup, pair_key
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
    # 子公司→母公司（后写覆盖，仅用于无销售歧义时）；KeyedLookup：查表忽略全角半角/空白差异
    sub_to_parent: dict[str, str] = field(default_factory=KeyedLookup)
    # (子公司,销售)→父组，重叠客户按销售归属父组（键 = pair_key）
    sub_sales_to_parent: dict[tuple[str, str], str] = field(default_factory=lambda: KeyedLookup(pair_key))
    sc3_by_parent: dict = field(default_factory=dict)    # {sales: {parent: {sub: {inc/pay: {dept:val}}}}}
    sc3_tgts_by_parent: dict = field(default_factory=dict)   # {parent: {inc/pay: {dept:val}}}（全销售聚合，兼容）
    # 按销售拆分的母公司目标（销售详情弹窗/矩阵用）
    sc3_tgts_by_parent_by_sales: dict = field(default_factory=dict)  # {sales: {parent: {inc/pay: {dept:val,total}}}}
    sc3_parent_cfg_total: dict = field(default_factory=dict)  # {parent: 配置子公司总数}
    sales_owned_subs: dict = field(default_factory=dict)  # {销售: {母公司: 该销售在配置中拥有的子公司数}}
    # 待确认
    pending_count: int = 0                # pending_df 行数(按 客户+事业部+法人主体 三维拆分后)
    pending_cust_n: int = 0               # 去重的客户数(独立口径,用于"客户数/家"展示)
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
    """销售页数据准备。

    重要约定：渲染层在此**不进行任何销售二次分配 / override / 重映射**。
    所有金额、归属直接来自引擎层 `data/sheets/系统数据清理/销售收入|销售回款.xlsx`
    （= `engine/sales/run.py` 的产出）。本页只做 groupby 聚合（按销售、按销售+事业部、
    按销售+母公司+客户+事业部），供 card1/卡2/卡3 矩阵展示。

    特殊规则（比亚迪法人 override、比例拆分、跨父组法人选组、销售拆行键等）均由
    引擎层完成；销售页不二次判断"该客户该不该归某个销售"。
    """
    d = SalesData()

    d.sales_range = get_config_range(base_dir, "年度累计") or ""
    # 引擎层 sales_income / sales_payment 已含 (客户, 销售, 母公司) 字段；
    # 金额聚合只依赖 销售 / 事业部 两列,无需 consolidate 客户列(也不应在此做销售重映射)
    df_si = _add_wan(data.sales_income.copy())
    df_sp = _add_wan(data.sales_payment.copy())
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
    # 排序键加"姓名"做稳定次序（2026-10-10 修）：只按指标降序时，同指标销售的先后
    # 取决于上面那两个 set 的迭代顺序，会随进程哈希种子变化 → 每次渲染行序都不同。
    d.sales_list = sorted(
        [s for s in all_sales_inc if s],
        key=lambda x: (-d.sales_targets.get(x, 0), x)
    )
    d.pay_sales_list = sorted(
        [s for s in all_sales_pay if s],
        key=lambda x: (-d.sales_targets.get(x, 0), x)
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
                # 必须按确定性顺序遍历（2026-10-10 修）：sales_owned_subs 是"以销售为键"的字典，
                # 迭代 set 会让键序随进程哈希种子变化 → 销售页 JSON 每次渲染字节都不同。
                for s_name in sorted(sales_set):
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
    # 去重客户数(去掉同一客户在不同事业部/法人主体下的重复行,得到真实"几家客户未归属")
    d.pending_cust_n = int(pending["客户"].astype(str).str.strip().nunique())
    d.pending_total_inc = float(pending["金额_万_收入"].sum())
    d.pending_total_pay = float(pending["金额_万_回款"].sum())
    d.pending_df = pending

    d.df_si = df_si; d.df_sp = df_sp
    d.inc_tgt_df = inc_tgt; d.pay_tgt_df = pay_tgt
    return d
