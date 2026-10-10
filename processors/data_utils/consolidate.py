# Author: naohua168 <bai_bai168@qq.com>
"""母公司归并 —— 广东/比亚迪/韶关法人过滤、客户与指标归拢、弹窗子公司明细

由 processors/page_data_utils.py 拆分而来（拆包前后行为逐字节一致，见 logs/_refactor_verify.py）。
可变缓存与读写它的函数被刻意保留在同一模块：跨模块重绑定模块级变量不会互相可见。
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd
from ..utils import safe_float, get_config_range
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
from engine.core.business_rules import is_gd_legal, is_sg_legal
from .constants import PROJECT_ROOT, SG_PARENT, _SG_CHILDREN_SEEN, GD_PARENT_FILTER, OTHER_PARENT_FILTER, BYD_PARENT_INDUSTRY, BYD_PARENT_BATTERY, DEPARTMENTS
from .keys import split_key_parts, _sub_to_sales_key, _parent_from_key, _sales_from_key, normalize_split_cust, normalize_known_parent
from .loading import _load_sales_split, _load_attribution_flat, _has_sales_attribution, _load_sub_to_parent, _load_sub_sales_to_parent, _group_by_key, _build_cust_parent_map
from .metrics import _add_wan


def filter_sg_by_legal(df: pd.DataFrame, metric: str):
    """法人主体=南方（韶关）… 且该行无销售归属 → 客户名改为母公司「南方韶关」

    Returns:
        (处理后的 df, 被归入的客户名列表)；无命中时原样返回、列表为空

    metric: "收入" / "回款"（对应客户销售归属.json 的口径键）
    """
    if df is None or len(df) == 0:
        return df, []
    if not {"客户", "法人主体", "事业部"} <= set(df.columns):
        return df, []
    # 法人主体按匹配键判定（全角半角/空白差异不影响，2026-09-29）
    sg_rows = df[df["法人主体"].map(is_sg_legal)]
    if len(sg_rows) == 0:
        return df, []

    attr = _load_attribution_flat()
    idx = [
        i
        for i, row in sg_rows.iterrows()
        if not _has_sales_attribution(row["客户"], str(row["事业部"]).strip(), metric, attr)
    ]
    if not idx:
        return df, []
    absorbed = list(dict.fromkeys(str(df.at[i, "客户"]).strip() for i in idx))
    out = df.copy()
    out.loc[idx, "客户"] = SG_PARENT
    return out, absorbed


def filter_gd_by_legal(df: pd.DataFrame) -> pd.DataFrame:
    """广东自有客户组中"多组配置"的子公司按法人重映射（而非删除）

    - 法人 == 广东汽车检测中心有限公司 → 客户名保持原样（后续 _consolidate_customers 归"广东自有客户"组）
    - 法人 != 广东汽车检测中心有限公司 → 客户名改为该子公司的"其他父组"名（优先"零部件客户"；
      否则取第一个非广东自有组），使金额进入对应父组而不是凭空消失

    与销售拆分引擎 `_select_parent_group` 口径一致：法人=广东→广东自有组，否则→优先零部件客户。
    此过滤在 _consolidate_customers 之前调用，使聚合后的"广东自有客户"行金额等于
    销售拆分后"广东自有客户"组的金额（口径对齐）。
    """
    if df is None or len(df) == 0:
        return df
    if "客户" not in df.columns or "法人主体" not in df.columns:
        return df
    multi = _gd_multi_sub_to_keep()  # 匹配键集合
    if not multi:
        return df
    import json
    cfg_path = PROJECT_ROOT / "config" / "清洗配置" / "客户销售归属.json"
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        return df

    # 子公司匹配键 → 出现的父组名列表（一次遍历建好，避免逐子公司全表扫描）
    sub_parents: dict[str, list[str]] = {}
    for p, grp in cfg.get("客户归属", {}).items():
        for s in grp.get("子公司", {}):
            sub_parents.setdefault(match_key(s), []).append(p)

    # 构建 多组子公司(键) → 其"其他父组"（优先零部件客户）
    other_parent_pref = match_key(OTHER_PARENT_FILTER)
    sub_other_parent: dict[str, str] = {}
    for sub_key in multi:
        others = [p for p in sub_parents.get(sub_key, [])
                  if match_key(p) != match_key(GD_PARENT_FILTER)]
        if not others:
            continue
        sub_other_parent[sub_key] = (
            OTHER_PARENT_FILTER
            if any(match_key(p) == other_parent_pref for p in others)
            else others[0]
        )

    cust_keys = df["客户"].map(match_key)
    not_gd_legal = ~df["法人主体"].map(is_gd_legal)
    is_multi = cust_keys.isin(sub_other_parent)
    remap_mask = is_multi & not_gd_legal

    n_remap = int(remap_mask.sum())
    if n_remap == 0:
        return df
    df = df.copy()
    df.loc[remap_mask, "客户"] = cust_keys[remap_mask].map(sub_other_parent)
    import logging
    logging.getLogger("vd.filter").info(
        f"广东自有法人重映射: {n_remap} 行非广东法人子公司 → 归入其其他父组（零部件客户等）"
    )
    return df


def _gd_multi_sub_to_keep() -> set[str]:
    """广东自有客户组中"多组配置"的子公司集合（这些公司按法人主体过滤）

    仅广东自有配置的子公司（不在其他任何组中）→ 无歧义，全部保留。
    返回**匹配键集合**（全角半角/空白差异不影响比对，2026-09-29）。
    """
    import json
    path = PROJECT_ROOT / "config" / "清洗配置" / "客户销售归属.json"
    if not path.exists():
        return set()
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    groups = cfg.get("客户归属", {})
    gd_keys = key_set(_group_by_key(groups, GD_PARENT_FILTER).get("子公司", {}).keys())
    all_other: set[str] = set()
    for p, grp in groups.items():
        if match_key(p) == match_key(GD_PARENT_FILTER):
            continue
        all_other |= key_set(grp.get("子公司", {}).keys())
    return gd_keys & all_other


def _byd_multi_subs() -> set[str]:
    """同时配置在「比亚迪汽车工业有限公司」与「比亚迪电池」两个父组下的子公司（配置驱动）

    返回**匹配键集合**（两侧写法不同的同一家公司也能识别，2026-09-29）。
    """
    import json
    path = PROJECT_ROOT / "config" / "清洗配置" / "客户销售归属.json"
    if not path.exists():
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        return set()
    groups = cfg.get("客户归属", {})
    industry = key_set(_group_by_key(groups, BYD_PARENT_INDUSTRY).get("子公司", {}).keys())
    battery = key_set(_group_by_key(groups, BYD_PARENT_BATTERY).get("子公司", {}).keys())
    return industry & battery


def _multi_group_subs() -> set[str]:
    """需要按规则判定唯一归属的"多组配置"子公司（广东自有组多组 + 比亚迪多组）"""
    return _gd_multi_sub_to_keep() | _byd_multi_subs()


def filter_byd_by_legal(df: pd.DataFrame) -> pd.DataFrame:
    """比亚迪"多组配置"子公司按法人主体归到唯一母公司（客户名直接改为父组名）

    - 法人主体 == 广东汽车检测中心有限公司 → 「比亚迪汽车工业有限公司」
    - 其他法人主体 → 「比亚迪电池」

    仅在子公司同时出现在这两个父组下时生效（`_byd_multi_subs`）。
    """
    if df is None or len(df) == 0:
        return df
    if "客户" not in df.columns or "法人主体" not in df.columns:
        return df
    multi = _byd_multi_subs()  # 匹配键集合
    if not multi:
        return df
    mask = df["客户"].map(match_key).isin(multi)
    if not mask.any():
        return df
    is_gd = df["法人主体"].map(is_gd_legal)
    df = df.copy()
    df.loc[mask & is_gd, "客户"] = BYD_PARENT_INDUSTRY
    df.loc[mask & ~is_gd, "客户"] = BYD_PARENT_BATTERY
    import logging
    logging.getLogger("vd.filter").info(
        f"比亚迪法人重映射: {int(mask.sum())} 行 "
        f"（广东主体→{BYD_PARENT_INDUSTRY}, 其他→{BYD_PARENT_BATTERY}）"
    )
    return df


def _consolidate_customers(df: pd.DataFrame, metric: str | None = None) -> pd.DataFrame:
    """将子公司名替换为母公司名（3+子公司时聚合，或客户本身就是母公司）

    metric: "收入" / "回款" 时额外执行南方韶关归拢
            （法人主体=南方（韶关）… 且该行无销售归属 → 母公司「南方韶关」）；
            总览/同比等不传 → 不做该归拢。
    """
    global _SUB_TO_PARENT
    if _SUB_TO_PARENT is None:
        _SUB_TO_PARENT = _load_sub_to_parent()
    df = df.copy()
    # 广东自有客户组中"多组配置"子公司按法人过滤（法人=广东汽车检测中心→广东自有组，否则→其他组）
    # 统一所有页面（数据总览/年度/月度/季度/销售/同比）口径，与销售拆分引擎一致
    df = filter_gd_by_legal(df)
    # 比亚迪：两个父组下同时出现的子公司按法人主体归到唯一母公司（广东→汽车工业，其他→电池）
    df = filter_byd_by_legal(df)
    # 南方韶关：法人主体=南方（韶关）且无销售归属的行 → 归入母公司「南方韶关」
    # （有销售归属的韶关行走销售；法人非南方韶关的不归拢。仅年/月/季度页传 metric）
    if metric:
        df, absorbed = filter_sg_by_legal(df, metric)
        for c in absorbed:
            if c not in _SG_CHILDREN_SEEN:
                _SG_CHILDREN_SEEN.append(c)
    SUFFIXES = ('有限公司', '科技', '股份有限公司', '有限责任公司', '公司')

    def _strip(s):
        n = str(s)
        changed = True
        while changed:
            changed = False
            for sf in SUFFIXES:
                if n.endswith(sf) and len(n) > len(sf):
                    n = n[:-len(sf)]
                    changed = True
        return n

    stripped_map = {}
    for sub, parent in _SUB_TO_PARENT.items():
        stripped_map.setdefault(_strip(sub), parent)

    def _map(c):
        c = str(c)
        if c in _SUB_TO_PARENT:
            return _SUB_TO_PARENT[c]
        s = _strip(c)
        if s in stripped_map:
            return stripped_map[s]
        # 模糊子串匹配：仅当双方去后缀名都 >=4 字符时才做，避免"科技公司"这类
        # 短占位名（去后缀后="科技"）被任意含"科技"的子公司名误映射到其母公司
        # （如 福建市场→国鸿氢能科技...广州氢能研发中心，导致指标错误归并）
        for sub, parent in sorted(_SUB_TO_PARENT.items(), key=lambda x: -len(x[0])):
            sub_st = _strip(sub)
            if len(sub_st) >= 4 and len(s) >= 4 and (sub_st in s or s in sub_st):
                return parent
        return c

    # 先试映射，统计每个母公司下出现了几个子公司
    all_custs = set(df["客户"].unique())
    parent_children: dict[str, set[str]] = {}
    for c in all_custs:
        p = _map(c)
        parent_children.setdefault(p, set()).add(c)

    # 只有 3+ 子公司 | 或该客户本身就是母公司名 时才聚合
    consolidate = set()
    for p, children in parent_children.items():
        if p in all_custs or len(children) >= 3:
            consolidate.add(p)
    # 配置了销售拆分的母公司：即使当月/当季数据中只出现 <3 家子公司也聚合按销售拆分
    # （如月度回款 科技公司 当月仅 2 家有数据，否则会被 _group_by_parent 退回母公司名，两位销售数据混在一起）
    consolidate |= set(_load_sales_split().keys())

    def _smart_map(c):
        # 已经是（或近似）'母公司·销售' 复合键 → 归一化分隔符后原样返回，不再做子公司映射
        parts = split_key_parts(c)
        if parts:
            return f"{parts[0]}·{parts[1]}"
        # 父组名自带销售（科技公司·王海龙）：任意分隔符写法 → 归属表里的规范名
        canon = normalize_known_parent(c)
        if canon:
            return canon
        p = _map(c)
        if p in consolidate:
            # 配置了销售拆分的母公司：子公司映射为 '母公司·销售'，矩阵按销售拆行
            split_key = _sub_to_sales_key(str(c), p)
            if split_key:
                return split_key
            return p
        return c

    df["客户"] = df["客户"].map(_smart_map)
    return df


def _row_parents(df: pd.DataFrame) -> list[str]:
    """逐行算出「矩阵里最终归入的母公司名」（复用 _consolidate_customers 的归属规则）

    子公司明细弹窗用它把"多组配置"子公司（广东自有组 / 比亚迪两父组）按法人主体
    拆到唯一父组，保证「抽屉子行合计 = 矩阵行」（否则同一子公司会在两个父组重复计入）。
    """
    if df is None or len(df) == 0:
        return []
    cols = [c for c in ("客户", "法人主体") if c in df.columns]
    tmp = df[cols].copy()
    return [str(v).strip() for v in _consolidate_customers(tmp)["客户"]]


def _target_parent_map(custs) -> dict[str, str]:
    """指标表 客户名 → 母公司名（批量；指标表无 法人主体 列）

    多组子公司的销售侧判定见调用处（按 (子公司, 销售) 配置映射）。
    """
    uniq = list(dict.fromkeys(str(c).strip() for c in custs))
    if not uniq:
        return {}
    parents = _row_parents(pd.DataFrame({"客户": uniq}))
    return dict(zip(uniq, parents))


def _consolidate_target(tgt_df: pd.DataFrame) -> pd.DataFrame:
    """合并目标表：子公司名替换为母公司（复用 _consolidate_customers），然后按 (客户, 销售) 聚合部门指标

    重叠客户（同子公司归属多父组）先按 (客户, 销售) 归并到正确父组——
    指标表没有法人主体列，但销售列可区分（如 福龙马+黎国键→广东自有客户、福龙马+江国川→福建市场）
    """
    if len(tgt_df) == 0:
        return tgt_df
    df = tgt_df.copy()
    split_parents = set(_load_sales_split().keys())
    # 客户名归一化：'科技公司-王海龙' / '科技公司 王海龙' → '科技公司·王海龙'（分隔符容错）
    if "客户" in df.columns:
        df["客户"] = df["客户"].map(normalize_split_cust)
    if "销售" in df.columns:
        sub_sales_to_parent = _load_sub_sales_to_parent()
        for idx, row in df.iterrows():
            cust = str(row.get("客户", "")).strip()
            sales = str(row.get("销售", "")).strip()
            parent = sub_sales_to_parent.get((cust, sales))
            if parent:
                # 拆分母公司 → '母公司·销售'；否则 → 母公司
                if parent in split_parents:
                    df.at[idx, "客户"] = f"{parent}·{sales}" if sales else parent
                else:
                    df.at[idx, "客户"] = parent
            elif cust in split_parents and sales and sales not in ("待确认", "", "nan"):
                # 客户名本身就是拆分母公司（如月度/季度指标表按 客户='科技公司' + 销售 粒度维护）
                # → 拆成 '母公司·销售'，保证与实际数据按销售拆分口径一致（两个销售相加 = 全部）
                df.at[idx, "客户"] = f"{cust}·{sales}"
    df = _consolidate_customers(df)
    dept_cols = [c for c in DEPARTMENTS if c in df.columns]
    if dept_cols:
        # sort=False 保留指标表原始行序（聚合后的公司顺序 = 指标表首次出现顺序）
        # 销售列可缺省（2026-09-24 用户口径：客户列直接写 '母公司·销售' 时不需要销售列）
        keys = ["客户"] + (["销售"] if "销售" in df.columns else [])
        df = df.groupby(keys, as_index=False, dropna=False, sort=False)[dept_cols].sum()
    return df


def _build_subs_with_data(
    raw_actuals: list[pd.DataFrame],
    raw_targets: list[pd.DataFrame],
    children_map: dict[str, list[str]],
    parents: list[str],
) -> dict[str, list[str]]:
    """为每个母公司构建"有数据"的子公司列表（弹窗用）

    "多组配置"子公司（广东自有组 / 比亚迪两父组）按法人主体归到唯一父组后再判断
    （与矩阵行口径一致，避免同一子公司在两个父组同时出现）。
    """
    multi_subs = _multi_group_subs()
    actual_custs: set[str] = set()                   # 归属唯一的子公司
    actual_scoped: set[tuple[str, str]] = set()      # (母公司, 子公司) → 多组子公司
    for df in raw_actuals:
        if df is None or len(df) == 0 or "客户" not in df.columns:
            continue
        work = df
        # 保留 法人主体 列：多组子公司（比亚迪等）需按法人主体判定归属（2026-09-28）
        keys = ["客户"] + (["法人主体"] if "法人主体" in work.columns else [])
        if "金额" in work.columns:
            # 金额非 0（无论正负）都算"有数据"（2026-09-18 用户口径）
            work = work.groupby(keys, as_index=False, dropna=False)["金额"].sum()
            work = work[work["金额"] != 0]
        if len(work) == 0:
            continue
        parents_of = _row_parents(work)
        for sub, parent in zip(work["客户"].astype(str).str.strip(), parents_of):
            if match_key(sub) in multi_subs:
                actual_scoped.add((parent, sub))
            else:
                actual_custs.add(sub)

    # 指标客户：任一部门指标 > 0 才算有数据（目标表可能有该客户但全为 0）
    dept_cols = [c for c in DEPARTMENTS if any(
        c in df.columns for df in raw_targets if df is not None)]
    target_custs: set[str] = set()
    target_scoped: set[tuple[str, str]] = set()
    sub_sales_to_parent = _load_sub_sales_to_parent()
    for df in raw_targets:
        if df is None or len(df) == 0 or "客户" not in df.columns:
            continue
        has_sales = "销售" in df.columns
        for c, grp in df.groupby(df["客户"].map(normalize_split_cust)):
            if not any(safe_float(grp[d].sum()) > 0 for d in dept_cols if d in df.columns):
                continue
            name = str(c).strip()
            if match_key(name) in multi_subs:
                fallback = _target_parent_map([name]).get(name, name)
                owners = {
                    sub_sales_to_parent.get((name, str(s).strip())) or fallback
                    for s in (grp["销售"] if has_sales else [""])
                }
                target_scoped.update((o, name) for o in owners if o)
            else:
                target_custs.add(name)

    sub_data: dict[str, list[str]] = {}
    split_map = _load_sales_split()
    for p in parents:
        all_subs = children_map.get(p, [])
        subs = [s for s in all_subs if s != p]
        subs = [
            s for s in subs
            if (p, s) in actual_scoped or (p, s) in target_scoped
            or (match_key(s) not in multi_subs and (s in actual_custs or s in target_custs))
        ]
        # 销售拆分键：'母公司·销售' → 只取该销售名下的子公司
        sales = _sales_from_key(p, split_map)
        if sales is not None:
            parent_name = _parent_from_key(p, split_map)
            sales_map = split_map.get(parent_name, {})
            subs = [s for s in subs if sales_map.get(s) == sales]
        if subs:
            sub_data[p] = subs
    return sub_data


def _build_subs_detail(
    raw_actual: pd.DataFrame | None,
    raw_target: pd.DataFrame | None,
    children_map: dict[str, list[str]],
    parents: list[str],
) -> dict[str, dict[str, dict[str, dict[str, float]]]]:
    """为每个母公司构建子公司×4部门实际/目标明细（弹窗表格用）。

    返回结构：
    {
      "母公司": {
        "子公司": {
          "检测": {"act": 100, "tgt": 200},
          ...
          "合计": {"act": 400, "tgt": 800}
        }
      }
    }
    """
    multi_subs = _multi_group_subs()
    actual: dict[str, dict[str, float]] = {}
    # (母公司, 子公司) → 多组子公司按法人主体归属后的金额（广东自有组 / 比亚迪两父组）
    act_scoped: dict[tuple[str, str], dict[str, float]] = {}
    if raw_actual is not None and len(raw_actual):
        df = _add_wan(raw_actual.copy())
        if "客户" in df.columns and "事业部" in df.columns:
            keys = ["客户", "事业部"] + (["法人主体"] if "法人主体" in df.columns else [])
            g = df.groupby(keys, as_index=False, dropna=False)["金额_万"].sum()
            for (_, row), owner in zip(g.iterrows(), _row_parents(g)):
                c = str(row["客户"]).strip()
                dpt = str(row["事业部"]).strip()
                if not (c and dpt):
                    continue
                amt = safe_float(row["金额_万"])
                if match_key(c) in multi_subs:
                    d = act_scoped.setdefault((owner, c), {})
                    d[dpt] = d.get(dpt, 0.0) + amt
                else:
                    actual.setdefault(c, {})[dpt] = actual.setdefault(c, {}).get(dpt, 0.0) + amt

    # 南方韶关：子客户金额只统计「法人主体=南方（韶关）」的行
    # （保证弹窗子行合计 = 矩阵母公司行；避免同名客户在其他来源/法人的金额混入）
    sg_children = set(_SG_CHILDREN_SEEN)
    sg_actual: dict[str, dict[str, float]] = {}
    if (sg_children and raw_actual is not None and len(raw_actual)
            and "法人主体" in raw_actual.columns):
        sdf = _add_wan(raw_actual.copy())
        sdf = sdf[sdf["法人主体"].map(is_sg_legal)]
        if len(sdf) and "客户" in sdf.columns and "事业部" in sdf.columns:
            g2 = sdf.groupby(["客户", "事业部"], as_index=False, dropna=False)["金额_万"].sum()
            for _, r2 in g2.iterrows():
                c2 = str(r2["客户"]).strip()
                dpt2 = str(r2["事业部"]).strip()
                if c2 and dpt2:
                    sg_actual.setdefault(c2, {})[dpt2] = safe_float(r2["金额_万"])

    target: dict[str, dict[str, float]] = {}
    # (母公司, 子公司) → 多组子公司的目标（指标表无 法人主体 列 → 按 (子公司, 销售) 配置判定）
    tgt_scoped: dict[tuple[str, str], dict[str, float]] = {}
    tgt_owner_cache: dict[str, str] = {}
    sub_sales_to_parent = _load_sub_sales_to_parent()
    # 按 (客户, 销售) 拆分的目标：拆分母公司的"本部"行需按销售取各自目标（如 科技公司+王海龙）
    target_by_sales: dict[tuple[str, str], dict[str, float]] = {}
    if raw_target is not None and len(raw_target) and "客户" in raw_target.columns:
        dept_cols = [c for c in DEPARTMENTS if c in raw_target.columns]
        for _, row in raw_target.iterrows():
            c = normalize_split_cust(row["客户"])
            if c:
                t = target.setdefault(c, {dpt: 0.0 for dpt in dept_cols})
                for dpt in dept_cols:
                    t[dpt] += safe_float(row[dpt])
                # 目标归属键：客户列写 '母公司·销售' → (母公司, 销售)；
                # 客户列写 母公司 + 销售列 → (母公司, 销售)。两种写法口径一致
                parts = split_key_parts(c)
                sales = str(row.get("销售", "")).strip()
                if match_key(c) in multi_subs:
                    owner = (sub_sales_to_parent.get((c, sales))
                             or tgt_owner_cache.setdefault(
                                 c, _target_parent_map([c]).get(c, c)))
                    ty = tgt_scoped.setdefault((owner, c), {dpt: 0.0 for dpt in dept_cols})
                    for dpt in dept_cols:
                        ty[dpt] += safe_float(row[dpt])
                if parts:
                    by_key = parts
                elif sales and sales not in ("待确认", "", "nan"):
                    by_key = (c, sales)
                else:
                    by_key = None
                if by_key:
                    ts = target_by_sales.setdefault(by_key, {dpt: 0.0 for dpt in dept_cols})
                    for dpt in dept_cols:
                        ts[dpt] += safe_float(row[dpt])

    result: dict[str, dict[str, dict[str, dict[str, float]]]] = {}
    split_map = _load_sales_split()
    for p in parents:
        sub_detail: dict[str, dict[str, dict[str, float]]] = {}
        # 销售拆分键：'母公司·销售' → 只统计该销售名下子公司的数据
        sales = _sales_from_key(p, split_map)
        parent_name = _parent_from_key(p, split_map) if sales is not None else p
        sales_map = split_map.get(parent_name, {}) if sales is not None else {}

        # 1) 母公司本部（原始数据中直接挂在母公司名下、未拆分给任何子公司的金额）
        # 展示规则（2026-09-18 用户最终口径）：**只要有数据无论正负都展示**；
        # 仅"4 部门金额全为 0 且无任何指标"才隐藏。负数（红冲/退款）、正负抵消都算有数据。
        # 拆分键（如 科技公司·王海龙）：本部目标只取该销售名下的目标，避免两位销售互相混入
        parent_act_data = actual.get(parent_name, {})
        if sales is not None:
            # ① (母公司, 销售) 目标（客户列=母公司+销售列 或 客户列=母公司·销售 均已登记）；
            # ② 回退：客户列本身写成复合键的行
            parent_tgt_data = target_by_sales.get((parent_name, sales)) or target.get(p, {})
        else:
            parent_tgt_data = target.get(parent_name, {})
        parent_act_total = sum(parent_act_data.get(d, 0.0) for d in DEPARTMENTS)
        parent_tgt_total = sum(parent_tgt_data.get(d, 0.0) for d in DEPARTMENTS)
        parent_has_data = any(parent_act_data.get(d, 0.0) != 0 for d in DEPARTMENTS)
        parent_has_tgt = any(parent_tgt_data.get(d, 0.0) != 0 for d in DEPARTMENTS)
        if parent_has_data or parent_has_tgt:
            row: dict[str, dict[str, float]] = {}
            total_act = total_tgt = 0.0
            for dpt in DEPARTMENTS:
                act = parent_act_data.get(dpt, 0.0)
                tgt = parent_tgt_data.get(dpt, 0.0)
                row[dpt] = {"act": act, "tgt": tgt}
                total_act += act
                total_tgt += tgt
            row["合计"] = {"act": total_act, "tgt": total_tgt}
            sub_detail[f"{parent_name}（本部）"] = row

        # 2) 子公司明细
        # 展示规则（2026-09-18 用户最终口径）：**只要有数据无论正负都展示**（逐部门看金额 ≠ 0）；
        # 仅"4 部门金额全为 0 且无任何指标"才隐藏（负数、正负抵消同样视为有数据）。
        all_subs = children_map.get(parent_name, [])
        subs = [s for s in all_subs if s != parent_name]
        if sales is not None:
            subs = [s for s in subs if sales_map.get(s) == sales]
        for s in subs:
            row = {}
            total_act = total_tgt = 0.0
            has_data = has_tgt = False
            # 多组子公司（广东自有组 / 比亚迪两父组）取"按法人/销售归属到本父组"的部分
            if s in sg_children:
                act_map = sg_actual.get(s, {})
            elif match_key(s) in multi_subs:
                act_map = act_scoped.get((parent_name, s), {})
            else:
                act_map = actual.get(s, {})
            tgt_map = (tgt_scoped.get((parent_name, s), {})
                       if match_key(s) in multi_subs else target.get(s, {}))
            for dpt in DEPARTMENTS:
                act = act_map.get(dpt, 0.0)
                tgt = tgt_map.get(dpt, 0.0)
                if act != 0:
                    has_data = True
                if tgt != 0:
                    has_tgt = True
                row[dpt] = {"act": act, "tgt": tgt}
                total_act += act
                total_tgt += tgt
            row["合计"] = {"act": total_act, "tgt": total_tgt}
            if has_data or has_tgt:
                sub_detail[s] = row

        if sub_detail:
            result[p] = sub_detail
    return result


_SUB_TO_PARENT: dict[str, str] | None = None


def _group_by_parent(piv: pd.DataFrame, tgt_g: pd.DataFrame, customers: list[str],
                     base_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """将客户矩阵数据按母公司归拢"""
    parent_map = _build_cust_parent_map(base_dir)
    if not parent_map:
        return piv, tgt_g, customers

    def _remap(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        df = df.copy()
        new_idx = [parent_map.get(c, c) for c in df.index]
        df.index = new_idx
        # sort=False：归拢后仍保持指标表顺序
        return df.groupby(df.index, sort=False).sum()

    piv_out = _remap(piv)
    tgt_out = _remap(tgt_g)

    seen: set[str] = set()
    parent_custs: list[str] = []
    for c in customers:
        p = parent_map.get(c, c)
        if p not in seen:
            seen.add(p)
            parent_custs.append(p)

    return piv_out, tgt_out, parent_custs