"""数据层共享工具 — 从 page_data.py 拆分

提供所有 prepare_*_data() 共用的辅助函数，不依赖 DashboardData。
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .utils import safe_float, get_config_range
from .config_loader import CustomerFilter, get_value

# ── 客户合并：子公司 → 母公司
_SUB_TO_PARENT: dict[str, str] | None = None  # 懒加载
# 销售拆分：{母公司: {子公司: 销售}}  — 配置自 展示规则.json._销售拆分.客户矩阵
_SALES_SPLIT: dict[str, dict[str, str]] | None = None


def _load_sales_split(base_dir: Path | None = None) -> dict[str, dict[str, str]]:
    """加载销售拆分配置 → {母公司: {子公司: 销售}}

    读取 展示规则.json 的 _销售拆分.客户矩阵（母公司名列表），
    再从 客户销售归属.json 中该母公司的每个子公司的收入配置取归属销售。
    """
    global _SALES_SPLIT
    if _SALES_SPLIT is not None:
        return _SALES_SPLIT
    root = base_dir or Path(__file__).parent.parent
    split: dict[str, dict[str, str]] = {}
    try:
        import json
        rules_path = root / "config" / "前端渲染" / "展示规则.json"
        ownership_path = root / "config" / "清洗配置" / "客户销售归属.json"
        if rules_path.exists() and ownership_path.exists():
            rules = json.load(open(rules_path, "r", encoding="utf-8"))
            ownership = json.load(open(ownership_path, "r", encoding="utf-8"))
            split_cfg = rules.get("_销售拆分", {}).get("客户矩阵", [])
            ownership_groups = ownership.get("客户归属", {})
            for parent in split_cfg:
                group = ownership_groups.get(parent, {})
                sub_sales: dict[str, str] = {}
                for sub, sub_cfg in group.get("子公司", {}).items():
                    sub_key = sub.strip()
                    if not isinstance(sub_cfg, dict):
                        continue
                    # 收入配置：{部门: {销售: 比例}}，取首个销售
                    inc_cfg = sub_cfg.get("收入", {})
                    for dept_cfg in inc_cfg.values():
                        if isinstance(dept_cfg, dict) and dept_cfg:
                            sub_sales[sub_key] = list(dept_cfg.keys())[0]
                            break
                    if sub_key not in sub_sales:
                        pay_cfg = sub_cfg.get("回款", {})
                        for dept_cfg in pay_cfg.values():
                            if isinstance(dept_cfg, dict) and dept_cfg:
                                sub_sales[sub_key] = list(dept_cfg.keys())[0]
                                break
                if sub_sales:
                    split[parent] = sub_sales
    except Exception:
        pass
    _SALES_SPLIT = split
    return split


def _sub_to_sales_key(c: str, parent: str) -> str | None:
    """子公司 → '母公司·销售' 键（若母公司配置了销售拆分），否则 None"""
    split = _load_sales_split()
    sales_map = split.get(parent)
    if not sales_map:
        return None
    sales = sales_map.get(c)
    if not sales:
        return None
    return f"{parent}·{sales}"


def _sales_from_key(key: str, split_map: dict[str, dict[str, str]] | None = None) -> str | None:
    """从 '母公司·销售' 键提取销售名；非拆分键返回 None"""
    if "·" not in key:
        return None
    parent, sales = key.split("·", 1)
    split_map = split_map or _load_sales_split()
    if parent in split_map:
        return sales
    return None


def _expand_children_map(children_map: dict[str, list[str]]) -> dict[str, list[str]]:
    """扩展母公司→子公司列表：为销售拆分的母公司生成 '母公司·销售' → 该销售子公司列表"""
    split_map = _load_sales_split()
    if not split_map:
        return children_map
    expanded = dict(children_map)
    for parent, sales_map in split_map.items():
        all_subs = children_map.get(parent, [])
        sales_list: dict[str, list[str]] = {}
        for s in all_subs:
            sales = sales_map.get(s)
            if sales:
                sales_list.setdefault(sales, []).append(s)
        for sales, subs in sales_list.items():
            expanded[f"{parent}·{sales}"] = subs
    return expanded


def _load_sub_to_parent() -> dict[str, str]:
    """加载 子公司→母公司 映射（跳过1:1：子公司名=母公司名的不映射，随便展示哪个都行）"""
    import json
    path = Path(__file__).parent.parent / "config" / "清洗配置" / "客户销售归属.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    raw = {}
    for parent, group in data.get("客户归属", {}).items():
        subs = list(group.get("子公司", {}).keys())
        # 只对 N:1（子公司数 > 1）或客户名≠子公司名的关系建立映射
        for sub in subs:
            s = sub.strip()
            if s == parent:
                continue  # 1:1 自引用，跳过，随便展示哪个都行
            if s not in raw:
                raw[s] = parent
    return raw


def _load_children_map() -> dict[str, list[str]]:
    """加载 母公司 → 子公司列表（弹窗展示用）"""
    import json
    path = Path(__file__).parent.parent / "config" / "清洗配置" / "客户销售归属.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    children = {}
    for parent, group in data.get("客户归属", {}).items():
        for sub in group.get("子公司", {}):
            s = sub.strip()
            children.setdefault(parent, []).append(s)
    return children


def _consolidate_customers(df: pd.DataFrame) -> pd.DataFrame:
    """将子公司名替换为母公司名（3+子公司时聚合，或客户本身就是母公司）"""
    global _SUB_TO_PARENT
    if _SUB_TO_PARENT is None:
        _SUB_TO_PARENT = _load_sub_to_parent()
    df = df.copy()
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


DEPARTMENTS = ["检测", "信息", "能源", "海外"]


def _load_sub_sales_to_parent() -> dict[tuple[str, str], str]:
    """加载 (子公司, 销售) → 父组 映射 — 重叠客户（同子公司归属多父组）按销售区分

    例如 福龙马集团：配置中 福建市场→福龙马(江国川)、广东自有客户→福龙马(黎国键)
    → (福龙马, 江国川)→福建市场, (福龙马, 黎国键)→广东自有客户
    """
    import json
    path = Path(__file__).parent.parent / "config" / "清洗配置" / "客户销售归属.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    result: dict[tuple[str, str], str] = {}
    for parent, group in data.get("客户归属", {}).items():
        for sub, sub_cfg in group.get("子公司", {}).items():
            sub_key = sub.strip()
            if isinstance(sub_cfg, dict):
                for metric_cfg in sub_cfg.values():
                    if isinstance(metric_cfg, dict):
                        for dept_cfg in metric_cfg.values():
                            if isinstance(dept_cfg, dict):
                                for sales_name in dept_cfg.keys():
                                    result[(sub_key, str(sales_name).strip())] = parent
    return result


def _consolidate_target(tgt_df: pd.DataFrame) -> pd.DataFrame:
    """合并目标表：子公司名替换为母公司（复用 _consolidate_customers），然后按 (客户, 销售) 聚合部门指标

    重叠客户（同子公司归属多父组）先按 (客户, 销售) 归并到正确父组——
    指标表没有法人主体列，但销售列可区分（如 福龙马+黎国键→广东自有客户、福龙马+江国川→福建市场）
    """
    if len(tgt_df) == 0:
        return tgt_df
    df = tgt_df.copy()
    split_parents = set(_load_sales_split().keys())
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
        df = df.groupby(["客户", "销售"], as_index=False, dropna=False, sort=False)[dept_cols].sum()
    return df


def _build_subs_with_data(
    raw_actuals: list[pd.DataFrame],
    raw_targets: list[pd.DataFrame],
    children_map: dict[str, list[str]],
    parents: list[str],
) -> dict[str, list[str]]:
    """为每个母公司构建"有数据"的子公司列表（弹窗用）"""
    actual_custs: set[str] = set()
    for df in raw_actuals:
        if df is None or len(df) == 0 or "客户" not in df.columns:
            continue
        if "金额" in df.columns:
            g = df.groupby("客户")["金额"].sum()
            actual_custs.update(str(c).strip() for c in g[g > 0].index)
        else:
            actual_custs.update(str(c).strip() for c in df["客户"].unique())

    # 指标客户：任一部门指标 > 0 才算有数据（目标表可能有该客户但全为 0）
    dept_cols = [c for c in DEPARTMENTS if any(
        c in df.columns for df in raw_targets if df is not None)]
    target_custs: set[str] = set()
    for df in raw_targets:
        if df is None or len(df) == 0 or "客户" not in df.columns:
            continue
        for c, grp in df.groupby(df["客户"].astype(str).str.strip()):
            if any(safe_float(grp[d].sum()) > 0 for d in dept_cols if d in df.columns):
                target_custs.add(str(c))

    sub_data: dict[str, list[str]] = {}
    split_map = _load_sales_split()
    for p in parents:
        all_subs = children_map.get(p, [])
        subs = [s for s in all_subs if s != p]
        subs = [s for s in subs if s in actual_custs or s in target_custs]
        # 销售拆分键：'母公司·销售' → 只取该销售名下的子公司
        sales = _sales_from_key(p, split_map)
        if sales is not None:
            parent_name = p.split("·")[0]
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
    actual: dict[str, dict[str, float]] = {}
    if raw_actual is not None and len(raw_actual):
        df = _add_wan(raw_actual.copy())
        if "客户" in df.columns and "事业部" in df.columns:
            g = df.groupby(["客户", "事业部"], as_index=False, dropna=False)["金额_万"].sum()
            for _, row in g.iterrows():
                c = str(row["客户"]).strip()
                dpt = str(row["事业部"]).strip()
                if c and dpt:
                    actual.setdefault(c, {})[dpt] = safe_float(row["金额_万"])

    target: dict[str, dict[str, float]] = {}
    # 按 (客户, 销售) 拆分的目标：拆分母公司的"本部"行需按销售取各自目标（如 科技公司+王海龙）
    target_by_sales: dict[tuple[str, str], dict[str, float]] = {}
    if raw_target is not None and len(raw_target) and "客户" in raw_target.columns:
        dept_cols = [c for c in DEPARTMENTS if c in raw_target.columns]
        for _, row in raw_target.iterrows():
            c = str(row["客户"]).strip()
            if c:
                t = target.setdefault(c, {dpt: 0.0 for dpt in dept_cols})
                for dpt in dept_cols:
                    t[dpt] += safe_float(row[dpt])
                sales = str(row.get("销售", "")).strip()
                if sales and sales not in ("待确认", "", "nan"):
                    ts = target_by_sales.setdefault((c, sales), {dpt: 0.0 for dpt in dept_cols})
                    for dpt in dept_cols:
                        ts[dpt] += safe_float(row[dpt])

    result: dict[str, dict[str, dict[str, dict[str, float]]]] = {}
    split_map = _load_sales_split()
    for p in parents:
        sub_detail: dict[str, dict[str, dict[str, float]]] = {}
        # 销售拆分键：'母公司·销售' → 只统计该销售名下子公司的数据
        sales = _sales_from_key(p, split_map)
        parent_name = p.split("·")[0] if sales is not None else p
        sales_map = split_map.get(parent_name, {}) if sales is not None else {}

        # 1) 母公司本部（原始数据中直接挂在母公司名下、未拆分给任何子公司的金额）
        # 过滤：4部门全为0且无目标数据时不展示
        # 拆分键（如 科技公司·王海龙）：本部目标只取该销售名下的目标，避免两位销售互相混入
        parent_act_data = actual.get(parent_name, {})
        if sales is not None:
            parent_tgt_data = target_by_sales.get((parent_name, sales), {})
        else:
            parent_tgt_data = target.get(parent_name, {})
        parent_act_total = sum(parent_act_data.get(d, 0.0) for d in DEPARTMENTS)
        parent_tgt_total = sum(parent_tgt_data.get(d, 0.0) for d in DEPARTMENTS)
        if parent_act_total > 0 or parent_tgt_total > 0:
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

        # 2) 子公司明细（过滤：4部门act全为0的子公司不展示，仅当年累计有数据的）
        all_subs = children_map.get(parent_name, [])
        subs = [s for s in all_subs if s != parent_name]
        if sales is not None:
            subs = [s for s in subs if sales_map.get(s) == sales]
        for s in subs:
            row = {}
            total_act = total_tgt = 0.0
            for dpt in DEPARTMENTS:
                act = actual.get(s, {}).get(dpt, 0.0)
                tgt = target.get(s, {}).get(dpt, 0.0)
                row[dpt] = {"act": act, "tgt": tgt}
                total_act += act
                total_tgt += tgt
            row["合计"] = {"act": total_act, "tgt": total_tgt}
            # 仅展示有实际金额（4部门不全为0）或当年累计有目标的子公司
            if total_act > 0 or total_tgt > 0:
                sub_detail[s] = row

        if sub_detail:
            result[p] = sub_detail
    return result


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


def _add_wan(df: pd.DataFrame) -> pd.DataFrame:
    """原地添加 `金额_万` 列"""
    df["金额_万"] = df["金额"].apply(safe_float) / 10000.0
    return df


def _dept_target_sum(targets: pd.DataFrame) -> float:
    """汇总 4 部门指标合计，兼容 xxx / xxx收入 / xxx回款 三种列命名"""
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


def _yoy_from_yearly(yearly: pd.DataFrame | None, cur_val: float,
                     start_m: int, end_m: int) -> float | None:
    """从年基线计算同比"""
    if yearly is None or len(yearly) == 0:
        return None
    yi = yearly.copy()
    yi["月"] = pd.to_datetime(yi["日期"], errors="coerce").dt.month
    if yi["月"].nunique() <= 1:
        prev = float(yi["金额"].sum()) / 10000.0
    else:
        prev = float(yi[(yi["月"] >= start_m) & (yi["月"] <= end_m)]["金额"].sum()) / 10000.0
    return _yoy_rate(cur_val, prev)


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


def _build_cust_parent_map(base_dir: Path) -> dict[str, str]:
    """从客户销售归属.json 构建 子公司→母公司 映射"""
    import json
    path = base_dir / "config" / "清洗配置" / "客户销售归属.json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            ownership = json.load(f)
    except Exception:
        return {}
    parent_map: dict[str, str] = {}
    for parent, entry in ownership.get("客户归属", {}).items():
        for sub in entry.get("子公司", {}).keys():
            parent_map[sub] = parent
    return parent_map


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


def _resplit_priority(all_custs: list[str], base_dir: Path,
                      filt: CustomerFilter) -> tuple[list[str], list[str]]:
    """母公司归拢后重新拆分优先/其余"""
    if not filt.has_priority():
        return all_custs, []
    parent_map = _build_cust_parent_map(base_dir)
    pri_parents = {parent_map.get(s, s) for s in filt.get_priority_names(base_dir)}
    return [c for c in all_custs if c in pri_parents], [c for c in all_custs if c not in pri_parents]


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
    if filt and filt.has_priority() and base_dir:
        pri_set = filt.get_priority_names(base_dir)
        for c in pri_set:
            if c not in cs:
                cs.append(c)

    # ④ 排序：有指定展示顺序（优先展示配置非空）时按金额降序；
    #     无指定展示顺序时保持指标表原始顺序（cs 已按 tgt_p.index 指标表行序收集）
    if filt and filt.has_priority() and base_dir:
        def _sort_key(c):
            tgt = tgt_p.loc[c, "合计"] if c in tgt_p.index else 0
            act = piv.loc[c, "合计"] if piv is not None and c in piv.index else 0
            if tgt > 0:
                return (1, tgt, act)   # 指标>0：按目标降序
            if act > 0:
                return (0, act, 0)     # 无指标有实际：按实际降序
            return (-1, 0, 0)          # 无数据（仅优先展示）：最后
        cs.sort(key=_sort_key, reverse=True)
    if filt and (not filt.is_empty() or filt.max_rows > 0):
        cs = filt.apply(cs, piv, tgt_p, base_dir)

    # ⑤ 优先展示拆分
    if filt and filt.has_priority() and base_dir:
        pri_set = filt.get_priority_names(base_dir)
        pri: list[str] = [c for c in cs if c in pri_set]
        rest: list[str] = [c for c in cs if c not in pri_set]
        return pri, rest
    return cs, []
