# Author: naohua168 <bai_bai168@qq.com>
"""页面数据准备包 —— 每页一个模块（dataclass + prepare_*_data）。

    overview   数据总览页取数（Hero 双指标 + 部门矩阵 + 销售榜单）
    annual     年度达成页取数（当年累计 + 部门卡 + 客户矩阵 + 同比）
    monthly    月度达成页取数（当月窗口，口径同年度页）
    quarterly  季度达成页取数（季度窗口，口径同年度页）
    sales      销售达成页取数（3 卡片 + 客户/母公司聚合 + 待确认客户）
    yoy        年度同比页取数（事业部同比 + 客户同比矩阵 + 年基线）

约定：只做数据计算（纯 pandas），不得引入 HTML/CSS；
输出 dataclass 供 processors/pages/ 各页渲染使用。
"""
from __future__ import annotations

from .overview import OverviewData, prepare_overview_data
from .annual import AnnualData, prepare_annual_data
from .monthly import MonthlyData, prepare_monthly_data
from .quarterly import QuarterlyData, prepare_quarterly_data
from .sales import SalesData, prepare_sales_data
from .yoy import YoyData, prepare_yoy_data

__all__ = [
    "OverviewData",
    "prepare_overview_data",
    "AnnualData",
    "prepare_annual_data",
    "MonthlyData",
    "prepare_monthly_data",
    "QuarterlyData",
    "prepare_quarterly_data",
    "SalesData",
    "prepare_sales_data",
    "YoyData",
    "prepare_yoy_data",
]
