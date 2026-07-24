"""
配置加载器 — 读取 cleaning_config.json 和映射文件

增强功能：
  - 支持模板化时间范围（自动推导当前月份）
  - 统一配置读取入口，所有消费方通过此模块获取配置
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).parent.parent.parent
CONFIG_PATH = BASE_DIR / "config" / "cleaning_config.json"

# 当前系统年月（用于模板解析）
_NOW = datetime.now()
_CUR_YEAR = _NOW.year
_CUR_MONTH = _NOW.month


def load_config():
    """加载清洗配置文件"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_mapping(file_key, config):
    """加载映射文件"""
    rel_path = config["映射文件"][file_key]
    abs_path = BASE_DIR / rel_path
    with open(abs_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_data_path(config, source, sub_key=None):
    """获取数据源文件路径"""
    folder = config["数据源"][source]["文件夹"]
    if sub_key:
        filename = config["数据源"][source][sub_key]["文件名"]
        return BASE_DIR / folder / filename
    return BASE_DIR / folder


def get_output_path(config, table_name):
    """获取输出路径（支持文件夹路径，自动查找唯一xlsx文件）"""
    raw = config["输出"][table_name]
    base = BASE_DIR / raw
    # 如果路径已经是文件，直接返回
    if base.is_file():
        return base
    # 如果是文件夹，自动查找唯一的 .xlsx 文件
    if base.is_dir():
        xlsx_files = list(base.glob("*.xlsx"))
        if len(xlsx_files) == 1:
            return xlsx_files[0]
        elif len(xlsx_files) == 0:
            # 文件夹存在但无文件，返回文件夹/文件名.xlsx（用于写入时创建）
            return base / f"{table_name}.xlsx"
        else:
            # 多个文件时，优先找与table_name同名的
            for f in xlsx_files:
                if f.stem == table_name:
                    return f
            return xlsx_files[0]
    # 路径不存在，按文件夹/文件名.xlsx 返回（用于写入时创建）
    return base / f"{table_name}.xlsx"


# ──────────────────────────────────────────────────────────────
# 动态时间范围解析
# ──────────────────────────────────────────────────────────────

def _resolve_template(template_value, year=None, month=None):
    """解析模板化时间值

    支持格式：
      "auto"           → 自动推导为上月（财务端数据是当月导出上月）
      {"_mode": "dynamic"}  → 自动推导上月
      {"start_date": "2026-06-01", "end_date": "..."}  → 静态，保持原样

    返回: {"start_date": str, "end_date": str} 或 直接字符串
    """
    if year is None:
        year = _CUR_YEAR
    if month is None:
        month = _CUR_MONTH

    # 动态模式取上月（财务端数据是当月导出上月数据）
    # 如7月运行→取6月数据，8月运行→取7月数据
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year

    # 字符串模式
    if isinstance(template_value, str):
        if template_value == "auto":
            start = f"{prev_year}-{prev_month:02d}-01"
            if prev_month == 12:
                end = f"{prev_year+1}-01-01 00:00:00"
            else:
                end = f"{prev_year}-{prev_month+1:02d}-01 00:00:00"
            return {"start_date": start, "end_date": end}
        return template_value

    # 字典模式
    if isinstance(template_value, dict):
        mode = template_value.get("_mode", "static")
        if mode == "dynamic":
            start = f"{prev_year}-{prev_month:02d}-01"
            if prev_month == 12:
                end = f"{prev_year+1}-01-01 00:00:00"
            else:
                end = f"{prev_year}-{prev_month+1:02d}-01 00:00:00"
            return {"start_date": start, "end_date": end}
        # 静态模式，保留原值
        return template_value

    return template_value


def get_time_range(config, range_key, year=None, month=None):
    """获取时间范围（支持模板化配置）

    Args:
        config: 配置字典
        range_key: 时间范围键名
        year: 指定年份（默认当前年）
        month: 指定月份（默认当前月）

    Returns:
        解析后的时间范围值（dict 或 str）
    """
    raw = config["时间范围"][range_key]
    return _resolve_template(raw, year=year, month=month)


def get_financial_time_range(config):
    """获取财务端筛选时间范围（自动推导当前月）"""
    return get_time_range(config, "财务端筛选")


def get_ops_fixed_date(config):
    """获取运营端固定日期（返回字符串，用于运营端日期回退）"""
    raw = config["时间范围"]["运营端固定日期"]
    resolved = _resolve_template(raw)
    # dynamic 模式返回dict，取start_date作为固定日期字符串
    if isinstance(resolved, dict):
        return resolved.get("start_date", f"{_CUR_YEAR}-01-01")
    return resolved


# ──────────────────────────────────────────────────────────────
# 统一的清洗参数加载（一次调用获取所有清洗所需参数）
# ──────────────────────────────────────────────────────────────

def load_clean_params(config):
    """加载清洗所需的所有参数

    返回: {
        "mapper": DepartmentMapper,
        "matcher": CustomerMatcher,
        "fin_range": 财务端时间范围,
        "ops_fixed_date": 运营端固定日期,
    }
    """
    from .mapping_loader import load_department_mapper, load_customer_list
    from .customer_matcher import CustomerMatcher

    mapper = load_department_mapper(config)
    customer_list = load_customer_list(config)
    matcher = CustomerMatcher(customer_list)
    fin_range = get_financial_time_range(config)
    ops_fixed_date = get_ops_fixed_date(config)

    return {
        "mapper": mapper,
        "matcher": matcher,
        "fin_range": fin_range,
        "ops_fixed_date": ops_fixed_date,
    }
