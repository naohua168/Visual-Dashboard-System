# Author: naohua168 <bai_bai168@qq.com>
"""配置编辑器实现包 —— Excel 编辑层 ↔ JSON 事实源的解析/写回/模板生成。

    paths          路径常量（配置文件与工作簿位置）
    constants      取值常量（时间键/策略/中英映射/日期格式）
    time_config    时间配置解析与写回
    display_rules  展示规则与 KPI 指标解析与写回
    attribution    销售归属解析与写回
    template       --init 系列：生成/刷新工作簿
    cli            main() 命令行入口

入口仍是 scripts/config_excel_to_json.py（可直接 python 运行）。
"""
from __future__ import annotations

from .paths import BASE_DIR, EXCEL_PATH, CLEANING_CFG, DISPLAY_RULES_CFG, ATTRIBUTION_CFG
from .constants import TIME_KEYS, DYNAMIC_STRATEGIES, MODE_ALIASES, STRATEGY_ALIASES, MODE_LABELS, STRATEGY_LABELS, DATE_CELL_FMT, BASE_DIR, EXCEL_PATH, CLEANING_CFG, DISPLAY_RULES_CFG, ATTRIBUTION_CFG, TIME_KEYS, DYNAMIC_STRATEGIES, MODE_LABELS, MODE_ALIASES, STRATEGY_LABELS, STRATEGY_ALIASES, HEADERS, RULE_PAGES, ATT_HEADERS, METRIC_SEP, METRIC_VALUES, METRIC_BOTH, DEPT_VALUES, KPI_PAGES, KPI_METRICS, KPI_HEADERS, GROUP_NOTE_LINES, UNIT_NOTE_LINES, NAME_NOTE_LINES, OUTPUT_NOTE_LINES, BIZ_NOTE_LINES, DATE_CELL_FMT, _STALE_NOTE_RE
from .parsing import split_metric_value, _parse_cell
from .time_config import _parse_month_range, _date_cell_value, excel_to_time_config, update_cleaning_config
from .display_rules import _render_value, _render_time_range_block, _replace_time_range_block, _merge_notes, update_display_rules, update_kpi_rules, excel_to_kpi
from .attribution import excel_to_attribution, report_dup_names, update_attribution
from .template import _cell_fill, init_excel_template, _note_blocks, _sync_note_block, refresh_note_sheet
from .cli import main

__all__ = [
    "BASE_DIR",
    "EXCEL_PATH",
    "CLEANING_CFG",
    "DISPLAY_RULES_CFG",
    "ATTRIBUTION_CFG",
    "TIME_KEYS",
    "DYNAMIC_STRATEGIES",
    "MODE_ALIASES",
    "STRATEGY_ALIASES",
    "MODE_LABELS",
    "STRATEGY_LABELS",
    "DATE_CELL_FMT",
    "BASE_DIR",
    "EXCEL_PATH",
    "CLEANING_CFG",
    "DISPLAY_RULES_CFG",
    "ATTRIBUTION_CFG",
    "TIME_KEYS",
    "DYNAMIC_STRATEGIES",
    "MODE_LABELS",
    "MODE_ALIASES",
    "STRATEGY_LABELS",
    "STRATEGY_ALIASES",
    "HEADERS",
    "RULE_PAGES",
    "ATT_HEADERS",
    "METRIC_SEP",
    "METRIC_VALUES",
    "METRIC_BOTH",
    "DEPT_VALUES",
    "KPI_PAGES",
    "KPI_METRICS",
    "KPI_HEADERS",
    "GROUP_NOTE_LINES",
    "UNIT_NOTE_LINES",
    "NAME_NOTE_LINES",
    "OUTPUT_NOTE_LINES",
    "BIZ_NOTE_LINES",
    "DATE_CELL_FMT",
    "_STALE_NOTE_RE",
    "split_metric_value",
    "_parse_cell",
    "_parse_month_range",
    "_date_cell_value",
    "excel_to_time_config",
    "update_cleaning_config",
    "_render_value",
    "_render_time_range_block",
    "_replace_time_range_block",
    "_merge_notes",
    "update_display_rules",
    "update_kpi_rules",
    "excel_to_kpi",
    "excel_to_attribution",
    "report_dup_names",
    "update_attribution",
    "_cell_fill",
    "init_excel_template",
    "_note_blocks",
    "_sync_note_block",
    "refresh_note_sheet",
    "main",
]
