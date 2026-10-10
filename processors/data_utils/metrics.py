# Author: naohua168 <bai_bai168@qq.com>
"""指标与口径工具 —— 万元换算、指标合计、月份范围、同比、客户透视与排序

由 processors/page_data_utils.py 拆分而来（拆包前后行为逐字节一致，见 logs/_refactor_verify.py）。
可变缓存与读写它的函数被刻意保留在同一模块：跨模块重绑定模块级变量不会互相可见。
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd
from ..utils import safe_float, get_config_range
from ..config_loader import SORT_DEFAULT, CustomerFilter, get_value
from engine.core.name_key import (
    SPLIT_SEP,
    KeyedLookup,
    dotted_parent_names,
    dotted_parent_patterns as _dotted_parent_patterns,
    key_set,
    match_key,
    normalize_known_parent as _normalize_known_parent,
    pair_key,
)
from .constants import DEPARTMENTS
from .keys import is_sales_key
from .loading import _build_cust_parent_map


def _add_wan(df: pd.DataFrame) -> pd.DataFrame:
    """原地添加 `金额_万` 列"""
    df["金额_万"] = df["金额"].apply(safe_float) / 10000.0
    return df


def _dept_target_sum(targets: pd.DataFrame) -> float:
    """汇总 4 部门指标合计，部门列名兼容三种命名：'检测' / '检测收入' / '检测回款'"""
    cols = targets.columns
    return sum(
        safe_float(targets[c].sum())
        for d in DEPARTMENTS
        for c in [d, f"{d}收入", f"{d}回款"] if c in cols
    )


def _kpi_target(base_dir: Path, page: str, metric: str, fallback: float) -> float:
    """Hero KPI 卡片指标总数（万元）。

    优先用 展示规则.json 中该页面 `KPI指标.{metric}` 的覆盖值；
    未设置（None/空/缺失）时回退到指标文件合计（fallback）。
    只影响 Hero 圆环指标总数，不影响表格/矩阵/部门卡明细指标。
    """
    try:
        val = get_value(base_dir, page, f"KPI指标.{metric}")
        if val is not None and str(val).strip() not in ("", "nan"):
            return float(val)
    except Exception:
        pass
    return float(fallback)


def _yoy_rate(cur: float, prev: float) -> float | None:
    """计算同比率 (cur-prev)/prev，prev=0 时返回 None"""
    return (cur - prev) / prev if prev > 0 else None


def _yoy_from_yearly(yearly: pd.DataFrame | None, cur_val: float,
                     start_m: int, end_m: int,
                     require_month_granularity: bool = False) -> float | None:
    """从年基线计算同比。

    - 年基线有月份粒度（nunique>1）：按 [start_m, end_m] 月份范围取去年同期
    - 年基线无月份粒度（nunique<=1，如"上年 1-N 月全量"单值）：
      - require_month_granularity=False（年度页）：退化用整年值比较（1-12月 vs 上年整年合理）
      - require_month_granularity=True（月度/季度页）：返回 None（无法算月份粒度同比，不显示）
    """
    if yearly is None or len(yearly) == 0:
        return None
    yi = yearly.copy()
    yi["月"] = pd.to_datetime(yi["日期"], errors="coerce").dt.month
    if yi["月"].nunique() <= 1:
        if require_month_granularity:
            return None  # 需要月份粒度但基线无 → 不显示同比
        prev = float(yi["金额"].sum()) / 10000.0
    else:
        prev = float(yi[(yi["月"] >= start_m) & (yi["月"] <= end_m)]["金额"].sum()) / 10000.0
    return _yoy_rate(cur_val, prev)


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


def _get_yearly_year(base_dir: Path) -> int:
    """从 cleaning_config.json 读取年基线年份"""
    import json
    cfg_path = base_dir / "config" / "清洗配置" / "cleaning_config.json"
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return int(cfg.get("时间范围", {}).get("年基线数据", {}).get("年份", 2024))
    except Exception:
        return 2024


def _customer_pivot(df: pd.DataFrame, tgt: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """客户 × 事业部 pivot（实际+目标），返回 (pivot_df, target_grouped_df)"""
    cols = tgt.columns
    av_cols = []
    dept_map = {}
    for d in DEPARTMENTS:
        for c in [d, f"{d}收入", f"{d}回款"]:
            if c in cols:
                av_cols.append(c)
                dept_map[d] = c
                break
    piv = df.pivot_table(index="客户", columns="事业部", values="金额_万", aggfunc="sum", fill_value=0, sort=False)
    if av_cols:
        # sort=False：保留指标表行序（客户矩阵展示顺序 = 指标表顺序）
        tgt_p = tgt.groupby("客户", sort=False)[av_cols].sum()
        rename = {v: k for k, v in dept_map.items() if v != k}
        if rename:
            tgt_p = tgt_p.rename(columns=rename)
        tgt_p["合计"] = tgt_p.sum(axis=1)
    else:
        tgt_p = pd.DataFrame(columns=DEPARTMENTS + ["合计"])
    piv["合计"] = piv.sum(axis=1)
    return piv, tgt_p


def _sorted_customers(tgt_p: pd.DataFrame,
                     filt: CustomerFilter | None = None,
                     piv: pd.DataFrame | None = None,
                     base_dir: Path | None = None) -> tuple[list[str], list[str]]:
    """按目标合计降序排列，返回 (优先客户, 其余客户)

    筛选规则（年度/月度/季度统一）：
    1. **指标客户**：指标合计 > 0 → 展示
    2. **非指标客户**：指标=0 或无指标，但有实际金额（>0）→ 展示
    3. **优先展示母公司**（filt.priority 配置）→ 无论如何都展示（即使无指标无实际）
    4. 其余（无指标 且 无实际）→ 不展示

    收入/回款分开判定（调用方分别传入各自的 piv/tgt）。

    优先逻辑：
    - filt.priority 有配置 → 优先名单内客户排前面，其余折叠在"查看全部"
    - filt.priority 为空 → 全部进入优先列表，其余为空
    """
    # ① 指标客户收集（无指定展示顺序时按指标表行序）：
    #   - 指标表中所有客户（无论指标是否>0）只要"有指标或实际"就按指标表顺序收录
    #   - 非指标表客户（指标表无记录但有实际）追加到末尾
    # 说明：指标表中 指标合计=0 但有实际 的客户（如广汽系子公司在月度表无目标）
    #   也应保持其在指标表中的位置，而不是按实际数据顺序插入
    tgt_set = set(tgt_p.index)
    has_pri = bool(filt and filt.has_priority() and base_dir)
    if has_pri:
        # 有指定展示顺序：指标>0 客户在前（按指标表行序），其余按实际金额
        cs = [c for c in tgt_p.index if tgt_p.loc[c, "合计"] > 0]
        if piv is not None and len(piv):
            for c in piv.index:
                if c in cs:
                    continue  # 已在指标客户中
                act = piv.loc[c, "合计"]
                if act > 0:
                    cs.append(c)
    else:
        # 无指定展示顺序：所有指标表客户（有指标或有实际）按指标表行序
        cs = []
        for c in tgt_p.index:
            has_tgt = tgt_p.loc[c, "合计"] > 0
            act = piv.loc[c, "合计"] if piv is not None and c in piv.index else 0
            if has_tgt or act > 0:
                cs.append(c)
        # 非指标表客户（有实际）：追加末尾
        if piv is not None and len(piv):
            for c in piv.index:
                if c in tgt_set or c in cs:
                    continue
                act = piv.loc[c, "合计"]
                if act > 0:
                    cs.append(c)

    # ③ 优先展示母公司：无论如何都展示（即使无指标无实际）
    # 注意：这里必须按**配置书写顺序**遍历（get_priority_names_ordered）。
    # 直接迭代 set 会随进程哈希种子变化 → 同一份配置每次渲染的客户行序都不同（2026-10-10 修）。
    if filt and filt.has_priority() and base_dir:
        cs_keys = key_set(cs)  # 比较走匹配键（全角半角/空白差异不算差异）
        for c in filt.get_priority_names_ordered(base_dir):
            if match_key(c) not in cs_keys:
                cs.append(c)

    # ④ 排序：有指定展示顺序（优先展示配置非空）时按金额降序；
    #     无指定展示顺序时保持指标表原始顺序（cs 已按 tgt_p.index 指标表行序收集）；
    #     配置「不排序」（filt.sort_none）时同样保持指标表原始顺序（优先展示只决定可见性）
    if filt and filt.has_priority() and base_dir and not filt.sort_none:
        def _sort_key(c):
            tgt = tgt_p.loc[c, "合计"] if c in tgt_p.index else 0
            act = piv.loc[c, "合计"] if piv is not None and c in piv.index else 0
            if tgt > 0:
                return (1, tgt, act)   # 指标>0：按目标降序
            if act > 0:
                return (0, act, 0)     # 无指标有实际：按实际降序
            return (-1, 0, 0)          # 无数据（仅优先展示）：最后
        cs.sort(key=_sort_key, reverse=True)
    # 只要配置了客户筛选 / 行数上限 / 非默认排序，就走 apply()（排序选项才会生效）
    if filt and (not filt.is_empty() or filt.max_rows > 0 or filt.sort_by != SORT_DEFAULT):
        # 销售拆分键保护：截断前提取，保证 科技公司·王海龙 / 科技公司·李巍 不被 max_rows 挤出
        split_keys = [c for c in cs if is_sales_key(c)]
        before_cs = list(cs)  # 截断前完整列表（用于收集被截断的客户）
        cs = filt.apply(cs, piv, tgt_p, base_dir)
        missing = [k for k in split_keys if k not in cs]
        if missing:
            cs = cs + missing
            # 追加后保持排行榜按当年累计金额降序（拆分键插到正确位置）
            if piv is not None:
                cs.sort(
                    key=lambda c: (float(piv.loc[c, "合计"]) if c in piv.index else 0),
                    reverse=True,
                )
        # 被 max_rows 截断的客户 → rest（供"查看全部"折叠展示），按当年金额降序
        rest_all = [c for c in before_cs if c not in cs]
        if piv is not None:
            rest_all.sort(
                key=lambda c: (float(piv.loc[c, "合计"]) if c in piv.index else 0),
                reverse=True,
            )
    else:
        rest_all: list[str] = []

    # ⑤ 优先展示拆分
    if filt and filt.has_priority() and base_dir:
        pri_keys = key_set(filt.get_priority_names(base_dir))
        pri: list[str] = [c for c in cs if match_key(c) in pri_keys]
        rest: list[str] = [c for c in cs if match_key(c) not in pri_keys]
        return pri, rest
    return cs, rest_all


def _resplit_priority(all_custs: list[str], base_dir: Path,
                      filt: CustomerFilter,
                      piv: pd.DataFrame | None = None,
                      tgt: pd.DataFrame | None = None) -> tuple[list[str], list[str]]:
    """母公司归拢后重新拆分「主表 / 折叠（查看全部）」

    **规则优先级（2026-09-21 用户口径）**：
    1. **有「优先展示」配置** → 按优先展示折叠：名单内进主表（含非指标客户），其余折叠
    2. **无「优先展示」配置** → 按指标折叠：**非指标客户（该口径指标合计=0）一律折叠**，
       主表 = 指标客户（顺序 = 指标表行序）；`max_rows>0` 只截断指标客户（销售拆分键不截断）
    3. 未传 tgt（无指标数据）且无优先展示 → 退化为 max_rows 截断（按 piv 金额降序），0 = 不折叠
    """
    # ── ① 优先展示优先 ──
    if filt is not None and filt.has_priority():
        parent_map = _build_cust_parent_map(base_dir)
        pri_parents = {parent_map.get(s, s) for s in filt.get_priority_names(base_dir)}
        pri_keys = key_set(pri_parents)  # 比较走匹配键（全角半角/空白差异不算差异）
        return ([c for c in all_custs if match_key(c) in pri_keys],
                [c for c in all_custs if match_key(c) not in pri_keys])

    # ── ② 无优先展示 → 非指标客户折叠 ──
    if tgt is None or len(tgt) == 0:
        if filt is not None and filt.max_rows > 0 and piv is not None and len(all_custs) > filt.max_rows:
            cs = list(all_custs)
            cs.sort(
                key=lambda c: (float(piv.loc[c, "合计"]) if c in piv.index else 0),
                reverse=True,
            )
            # 销售拆分键保护：保证 科技公司·王海龙 / 科技公司·李巍 不被截断
            split_keys = [c for c in cs if is_sales_key(c)]
            top_n = cs[: filt.max_rows]
            rest = [c for c in cs[filt.max_rows :] if c not in split_keys]
            for k in split_keys:
                if k not in top_n:
                    top_n.append(k)
            return top_n, rest
        return all_custs, []

    has_tgt = {
        c for c in all_custs
        if c in tgt.index and float(tgt.loc[c, "合计"]) > 0
    }
    main = [c for c in all_custs if c in has_tgt]
    rest = [c for c in all_custs if c not in has_tgt]
    if filt is not None and filt.max_rows > 0 and len(main) > filt.max_rows:
        split_keys = [c for c in main if is_sales_key(c)]
        top_n = main[: filt.max_rows]
        moved = [c for c in main[filt.max_rows :] if c not in split_keys]
        for k in split_keys:
            if k not in top_n:
                top_n.append(k)
        return top_n, moved + rest
    return main, rest
