# Author: naohua168 <bai_bai168@qq.com>
"""拆分键与名称归一 —— 「母公司·销售」拆分键、点号父组、客户名归一

由 processors/page_data_utils.py 拆分而来（拆包前后行为逐字节一致，见 logs/_refactor_verify.py）。
可变缓存与读写它的函数被刻意保留在同一模块：跨模块重绑定模块级变量不会互相可见。
"""
from __future__ import annotations

from .constants import PROJECT_ROOT

import re
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
from .loading import _load_sales_split


def split_key_parts(c, parents=None) -> tuple[str, str] | None:
    """解析 '母公司<任意分隔符>销售' → (母公司, 销售)；不是拆分键则 None

    分隔符容忍：· • ・ － - – — − ／ / \\ | , ， 、 ; ； : ： . 。 ~ 空格…
    parents: 允许的母公司集合；默认取配置里的销售拆分母公司（_销售拆分.客户矩阵）

    ⚠ 只处理"老的拆分母公司"；「父组名自带销售」归一化见 normalize_known_parent()
    """
    s = str(c).strip()
    if not s:
        return None
    plist = tuple(parents) if parents is not None else tuple(_load_sales_split().keys())
    pattern = _split_key_regex(plist)
    if pattern is None:
        return None
    m = pattern.match(s)
    if not m:
        return None
    sales = m.group("sales").strip()
    return (m.group("parent"), sales) if sales else None


def _split_key_regex(parents: tuple[str, ...]) -> re.Pattern | None:
    """构建 `^(母公司A|母公司B)(分隔符+)(销售)$` 匹配器（按 parents 缓存）"""
    if parents in _SPLIT_KEY_RE_CACHE:
        return _SPLIT_KEY_RE_CACHE[parents]
    names = sorted({str(p).strip() for p in parents if str(p).strip()},
                   key=len, reverse=True)
    pattern = (
        re.compile(
            rf"^(?P<parent>{'|'.join(re.escape(n) for n in names)})"
            rf"[{_SPLIT_SEP}]+(?P<sales>.+)$"
        )
        if names else None
    )
    _SPLIT_KEY_RE_CACHE[parents] = pattern
    return pattern


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


def _parent_from_key(key: str, split_map: dict | None = None) -> str:
    """'母公司·销售' → 母公司（分隔符容错）；非拆分键 → 原样返回"""
    parts = split_key_parts(key, split_map.keys() if split_map else None)
    return parts[0] if parts else str(key)


def _sales_from_key(key: str, split_map: dict[str, dict[str, str]] | None = None) -> str | None:
    """从 '母公司·销售' 键提取销售名（分隔符容错）；非拆分键返回 None"""
    split_map = split_map or _load_sales_split()
    parts = split_key_parts(key, split_map.keys())
    return parts[1] if parts else None


def is_sales_key(c) -> bool:
    """该客户行是否"带销售"（老的 `母公司·销售` 拆分键，或新的「父组名自带销售」）

    用于 max_rows 截断保护：这类行即使金额小也不该被挤出榜单。
    """
    return _sales_from_key(c) is not None or sales_of_dotted_parent(c) is not None


def normalize_split_cust(c) -> str:
    """客户名归一化：'科技公司-王海龙' / '科技公司 王海龙' → '科技公司·王海龙'

    两条路都走一遍：
      1) 老的拆分母公司（`_销售拆分.客户矩阵`）：'母公司<任意分隔符>销售'
      2) 新的「父组名自带销售」（归属表里的 `母公司·销售`，2026-09-29 起）：
         任意分隔符、甚至漏打分隔符，都归一到归属表里的规范写法
    """
    parts = split_key_parts(c)
    if parts:
        return f"{parts[0]}·{parts[1]}"
    canon = normalize_known_parent(c)
    return canon or str(c).strip()


def normalize_known_parent(c, patterns=None) -> str | None:
    """客户名等于「父组名自带销售」的任意分隔符写法 → 返回归属表里的规范名，否则 None"""
    return _normalize_known_parent(
        c, _dotted_parent_patterns(_dotted_names()) if patterns is None else patterns
    )


def sales_of_dotted_parent(c) -> str | None:
    """「父组名自带销售」→ 销售名（= 规范名的最后一段）；不是则 None"""
    canon = normalize_known_parent(c)
    return canon.split("·")[-1] if canon else None


def dotted_parent_patterns(names=None) -> tuple[tuple[str, re.Pattern], ...]:
    """归属表里「父组名自带 ·销售」的 (规范名, 匹配器) 列表（名字与匹配器都缓存）

    names=None → 用归属表里的名字（只读一次）；调用方也可注入（测试用）。
    """
    return _dotted_parent_patterns(_dotted_names() if names is None else names)


def _dotted_names() -> tuple[str, ...]:
    """读一次 客户销售归属.json，取「父组名自带 ·销售」的母公司名（进程内缓存）

    ⚠ 这个函数在"逐客户名调用"的热路径上，绝不能每次调用都读文件。
    """
    global _DOTTED_NAMES
    if _DOTTED_NAMES is None:
        try:
            import json
            path = PROJECT_ROOT / "config" / "清洗配置" / "客户销售归属.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            _DOTTED_NAMES = dotted_parent_names(data.get("客户归属", {}))
        except Exception:
            _DOTTED_NAMES = ()
    return _DOTTED_NAMES


_SPLIT_KEY_RE_CACHE: dict[tuple[str, ...], re.Pattern | None] = {}


_SPLIT_SEP = SPLIT_SEP


_DOTTED_NAMES: tuple[str, ...] | None = None