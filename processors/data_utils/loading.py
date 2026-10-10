# Author: naohua168 <bai_bai168@qq.com>
"""归属与映射加载 —— 客户销售归属、子公司→母公司、部门子公司在配置中的展开

由 processors/page_data_utils.py 拆分而来（拆包前后行为逐字节一致，见 logs/_refactor_verify.py）。
可变缓存与读写它的函数被刻意保留在同一模块：跨模块重绑定模块级变量不会互相可见。
"""
from __future__ import annotations

from pathlib import Path
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
from .constants import PROJECT_ROOT, SG_PARENT, _SG_CHILDREN_SEEN


def _load_sales_split(base_dir: Path | None = None) -> dict[str, dict[str, str]]:
    """加载销售拆分配置 → {母公司: {子公司: 销售}}

    读取 客户销售归属.json 的 _销售拆分.客户矩阵（母公司名列表），
    再从该 JSON 的客户归属中取每个子公司的归属销售。
    （兼容旧位置：展示规则.json._销售拆分，存在时作为回退。）
    """
    global _SALES_SPLIT
    if _SALES_SPLIT is not None:
        return _SALES_SPLIT
    root = base_dir or PROJECT_ROOT
    split: dict[str, dict[str, str]] = {}
    try:
        import json
        ownership_path = root / "config" / "清洗配置" / "客户销售归属.json"
        rules_path = root / "config" / "前端渲染" / "展示规则.json"
        if ownership_path.exists():
            ownership = json.load(open(ownership_path, "r", encoding="utf-8"))
            ownership_groups = ownership.get("客户归属", {})
            split_cfg = ownership.get("_销售拆分", {}).get("客户矩阵", [])
            if not split_cfg and rules_path.exists():
                # 兼容回退：旧位置（展示规则.json._销售拆分.客户矩阵）
                rules = json.load(open(rules_path, "r", encoding="utf-8"))
                split_cfg = rules.get("_销售拆分", {}).get("客户矩阵", [])
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


def _load_attribution_flat():
    """客户销售归属.json → {客户: {父组: {收入/回款: {部门: {销售: 比例}}}}}

    与 engine/sales/run.py::_load_attribution 同口径，用于判断"该行是否有销售归属"。
    返回 KeyedLookup：查表按匹配键（全角半角/空白差异不影响），遍历仍是配置里的原写法。
    """
    global _ATTRIBUTION_FLAT
    if _ATTRIBUTION_FLAT is not None:
        return _ATTRIBUTION_FLAT
    import json
    path = PROJECT_ROOT / "config" / "清洗配置" / "客户销售归属.json"
    flat = KeyedLookup()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for parent, group in data.get("客户归属", {}).items():
            for sub, sub_data in group.get("子公司", {}).items():
                key = match_key(sub)
                if not key:
                    continue
                bucket = flat.get(sub)
                if bucket is None:
                    bucket = {}
                    flat.add(sub, bucket)
                bucket[parent] = sub_data or {}
    except Exception:
        flat = KeyedLookup()
    _ATTRIBUTION_FLAT = flat
    return flat


def _has_sales_attribution(cust, dept: str, metric: str, attr: dict | None = None) -> bool:
    """该客户在「该口径（收入/回款）+ 该部门」下是否配置了销售比例"""
    groups = (attr if attr is not None else _load_attribution_flat()).get(str(cust).strip())
    if not groups:
        return False
    return any((sd.get(metric, {}) or {}).get(dept) for sd in groups.values())


def _expand_children_map(children_map) -> KeyedLookup:
    """扩展母公司→子公司列表：为销售拆分的母公司生成 '母公司·销售' → 该销售子公司列表

    返回 KeyedLookup：查表（含 '母公司·销售' 键）自动忽略全角半角/空白差异。
    """
    split_map = _load_sales_split()
    expanded = KeyedLookup()
    for name in children_map:
        expanded.add(name, children_map.get(name))
    if not split_map:
        return expanded
    for parent, sales_map in split_map.items():
        all_subs = children_map.get(parent, [])
        sales_list: dict[str, list[str]] = {}
        for s in all_subs:
            sales = sales_map.get(s)
            if sales:
                sales_list.setdefault(sales, []).append(s)
        for sales, subs in sales_list.items():
            expanded.add(f"{parent}·{sales}", subs)
    return expanded


def _load_sub_to_parent():
    """加载 子公司→母公司 映射（跳过1:1：子公司名=母公司名的不映射，随便展示哪个都行）

    返回 KeyedLookup：`映射.get(客户名)` 自动忽略全角半角/空白差异，值仍是配置里的母公司名。
    """
    import json
    path = PROJECT_ROOT / "config" / "清洗配置" / "客户销售归属.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    raw = KeyedLookup()
    for parent, group in data.get("客户归属", {}).items():
        subs = list(group.get("子公司", {}).keys())
        # 只对 N:1（子公司数 > 1）或客户名≠子公司名的关系建立映射
        for sub in subs:
            if match_key(sub) == match_key(parent):
                continue  # 1:1 自引用，跳过，随便展示哪个都行
            if sub not in raw:
                raw.add(sub, parent)
    return raw


def _load_children_map():
    """加载 母公司 → 子公司列表（弹窗展示用）

    返回 KeyedLookup：`children.get(客户/母公司名)` 自动忽略全角半角/空白差异。
    """
    import json
    path = PROJECT_ROOT / "config" / "清洗配置" / "客户销售归属.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    children = KeyedLookup()
    for parent, group in data.get("客户归属", {}).items():
        for sub in group.get("子公司", {}):
            bucket = children.get(parent)
            if bucket is None:
                bucket = []
                children.add(parent, bucket)
            bucket.append(sub.strip())
    # 南方韶关：注入被归入的子客户（动态，来自 _consolidate_customers）
    if _SG_CHILDREN_SEEN:
        bucket = children.get(SG_PARENT)
        if bucket is None:
            bucket = []
            children.add(SG_PARENT, bucket)
        for c in _SG_CHILDREN_SEEN:
            if c not in bucket:
                bucket.append(c)
    return children


def _load_sub_sales_to_parent() -> dict[tuple[str, str], str]:
    """加载 (子公司, 销售) → 父组 映射 — 重叠客户（同子公司归属多父组）按销售区分

    例如 福龙马集团：配置中 福建市场→福龙马(江国川)、广东自有客户→福龙马(黎国键)
    → (福龙马, 江国川)→福建市场, (福龙马, 黎国键)→广东自有客户
    """
    import json
    path = PROJECT_ROOT / "config" / "清洗配置" / "客户销售归属.json"
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


def _group_by_key(groups: dict, name: str) -> dict:
    """按匹配键取父组配置（父组名写法不同也能取到）"""
    for p, grp in groups.items():
        if match_key(p) == match_key(name):
            return grp
    return {}


_SALES_SPLIT: dict[str, dict[str, str]] | None = None


_ATTRIBUTION_FLAT: dict | None = None


def _build_cust_parent_map(base_dir: Path):
    """从客户销售归属.json 构建 子公司→母公司 映射

    返回 KeyedLookup：`映射.get(客户名)` 自动忽略全角半角/空白差异（2026-09-29）。
    """
    import json
    path = base_dir / "config" / "清洗配置" / "客户销售归属.json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            ownership = json.load(f)
    except Exception:
        return KeyedLookup()
    parent_map = KeyedLookup()
    for parent, entry in ownership.get("客户归属", {}).items():
        for sub in entry.get("子公司", {}).keys():
            parent_map.add(sub, parent)
    return parent_map