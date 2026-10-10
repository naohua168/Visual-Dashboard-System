# Author: naohua168 <bai_bai168@qq.com>
"""数据层共享工具包 —— 拆分键 / 归属加载 / 母公司归并 / 指标口径。

    keys         拆分键与名称归一
    loading      归属与映射加载
    consolidate  母公司归并
    metrics      指标与口径工具
    constants    部门与各类名单常量（供其它模块 import）

对外只暴露纯函数与常量；可变缓存保留在各自模块内，不要跨模块重绑定。
"""
from __future__ import annotations

from .keys import split_key_parts, _split_key_regex, _sub_to_sales_key, _parent_from_key, _sales_from_key, is_sales_key, normalize_split_cust, normalize_known_parent, sales_of_dotted_parent, dotted_parent_patterns, _dotted_names, _SPLIT_KEY_RE_CACHE, _SPLIT_SEP, _DOTTED_NAMES
from .loading import _load_sales_split, _load_attribution_flat, _has_sales_attribution, _expand_children_map, _load_sub_to_parent, _load_children_map, _load_sub_sales_to_parent, _group_by_key, _SALES_SPLIT, _ATTRIBUTION_FLAT, _build_cust_parent_map
from .consolidate import filter_sg_by_legal, filter_gd_by_legal, _gd_multi_sub_to_keep, _byd_multi_subs, _multi_group_subs, filter_byd_by_legal, _consolidate_customers, _row_parents, _target_parent_map, _consolidate_target, _build_subs_with_data, _build_subs_detail, _SUB_TO_PARENT, _group_by_parent
from .metrics import _add_wan, _dept_target_sum, _kpi_target, _yoy_rate, _yoy_from_yearly, _parse_month_range, _data_max_month, _get_yearly_year, _customer_pivot, _sorted_customers, _resplit_priority
from .constants import (
    GD_LEGAL_FILTER,
    SG_LEGAL_ENTITY,
    BYD_PARENT_BATTERY,
    BYD_PARENT_INDUSTRY,
    DEPARTMENTS,
    GD_PARENT_FILTER,
    OTHER_PARENT_FILTER,
    SG_PARENT,
    _SG_CHILDREN_SEEN,
)

__all__ = [
    "GD_LEGAL_FILTER",
    "SG_LEGAL_ENTITY",
    "BYD_PARENT_BATTERY",
    "BYD_PARENT_INDUSTRY",
    "DEPARTMENTS",
    "GD_PARENT_FILTER",
    "OTHER_PARENT_FILTER",
    "SG_PARENT",
    "_SG_CHILDREN_SEEN",
    "split_key_parts",
    "_split_key_regex",
    "_sub_to_sales_key",
    "_parent_from_key",
    "_sales_from_key",
    "is_sales_key",
    "normalize_split_cust",
    "normalize_known_parent",
    "sales_of_dotted_parent",
    "dotted_parent_patterns",
    "_dotted_names",
    "_SPLIT_KEY_RE_CACHE",
    "_SPLIT_SEP",
    "_DOTTED_NAMES",
    "_load_sales_split",
    "_load_attribution_flat",
    "_has_sales_attribution",
    "_expand_children_map",
    "_load_sub_to_parent",
    "_load_children_map",
    "_load_sub_sales_to_parent",
    "_group_by_key",
    "_SALES_SPLIT",
    "_ATTRIBUTION_FLAT",
    "_build_cust_parent_map",
    "filter_sg_by_legal",
    "filter_gd_by_legal",
    "_gd_multi_sub_to_keep",
    "_byd_multi_subs",
    "_multi_group_subs",
    "filter_byd_by_legal",
    "_consolidate_customers",
    "_row_parents",
    "_target_parent_map",
    "_consolidate_target",
    "_build_subs_with_data",
    "_build_subs_detail",
    "_SUB_TO_PARENT",
    "_group_by_parent",
    "_add_wan",
    "_dept_target_sum",
    "_kpi_target",
    "_yoy_rate",
    "_yoy_from_yearly",
    "_parse_month_range",
    "_data_max_month",
    "_get_yearly_year",
    "_customer_pivot",
    "_sorted_customers",
    "_resplit_priority",
]
