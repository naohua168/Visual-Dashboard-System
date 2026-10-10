# Author: naohua168 <bai_bai168@qq.com>
"""兼容层 —— 数据准备实现已按页面拆到 processors/data_prep/。

保留本模块只为让既有导入继续可用（页面模块 / 测试 / 外部脚本）：

    from processors.page_data import prepare_annual_data, DEPARTMENTS

它同时重新导出原先从这里可导入的工具名（`_sorted_customers` 等），
新代码请直接从 processors.data_prep / processors.page_data_utils 导入。
"""
from __future__ import annotations

from engine.core.name_key import KeyedLookup, pair_key
from engine.core.utils import log_step

from .config_loader import CustomerFilter
from .data_prep import (
    AnnualData,
    MonthlyData,
    OverviewData,
    QuarterlyData,
    SalesData,
    YoyData,
    prepare_annual_data,
    prepare_monthly_data,
    prepare_overview_data,
    prepare_quarterly_data,
    prepare_sales_data,
    prepare_yoy_data,
)
from .page_data_utils import (
    DEPARTMENTS,
    _add_wan,
    _build_subs_detail,
    _build_subs_with_data,
    _consolidate_customers,
    _consolidate_target,
    _customer_pivot,
    _data_max_month,
    _dept_target_sum,
    _expand_children_map,
    _get_yearly_year,
    _group_by_parent,
    _kpi_target,
    _load_children_map,
    _parse_month_range,
    _resplit_priority,
    _sorted_customers,
    _yoy_from_yearly,
    _yoy_rate,
    filter_gd_by_legal,
)
from .utils import get_config_range, safe_float

__all__ = [
    "OverviewData",
    "AnnualData",
    "MonthlyData",
    "QuarterlyData",
    "SalesData",
    "YoyData",
    "prepare_overview_data",
    "prepare_annual_data",
    "prepare_monthly_data",
    "prepare_quarterly_data",
    "prepare_sales_data",
    "prepare_yoy_data",
    "DEPARTMENTS",
    "CustomerFilter",
    "KeyedLookup",
    "pair_key",
    "log_step",
    "safe_float",
    "get_config_range",
    "filter_gd_by_legal",
]
