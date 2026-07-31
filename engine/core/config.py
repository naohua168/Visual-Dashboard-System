"""
配置加载器 — 读取 cleaning_config.json 和映射文件
"""
from __future__ import annotations

import calendar
import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
CONFIG_PATH = BASE_DIR / "config" / "清洗配置" / "cleaning_config.json"


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

def _last_day_of_month(year: int, month: int) -> int:
    """获取指定年月的最后一天（处理闰年）"""
    return calendar.monthrange(year, month)[1]


def _compute_last_full_month(now: datetime | None = None) -> dict:
    """计算上一个完整月的起止日期（不包含当前月）

    逻辑：以"now"所在月为当前月（未结束），往前推一个月为上一个完整月
    例如 now=2026-07-29 → 上一个完整月=2026-06 → 2026-06-01 ~ 2026-06-30
    """
    if now is None:
        now = datetime.now()
    if now.month == 1:
        prev_year, prev_month = now.year - 1, 12
    else:
        prev_year, prev_month = now.year, now.month - 1
    start = f"{prev_year}-{prev_month:02d}-01"
    last_day = _last_day_of_month(prev_year, prev_month)
    end = f"{prev_year}-{prev_month:02d}-{last_day:02d} 23:59:59"
    return {"start_date": start, "end_date": end}


def _compute_last_full_quarter(now: datetime | None = None) -> dict:
    """计算上一个完整季度的起止日期（不包含当前季度）

    逻辑：当前季度未结束时，往前推一个季度
    例如 now=2026-07-29（Q3 未结束）→ 上一个完整季度=Q2 → 2026-04-01 ~ 2026-06-30
    """
    if now is None:
        now = datetime.now()
    current_q = (now.month - 1) // 3 + 1  # 1..4
    if current_q == 1:
        # Q1 未结束时，上一完整季度是去年的 Q4
        prev_q, prev_year = 4, now.year - 1
    else:
        prev_q, prev_year = current_q - 1, now.year
    start_month = (prev_q - 1) * 3 + 1
    end_month = prev_q * 3
    start = f"{prev_year}-{start_month:02d}-01"
    last_day = _last_day_of_month(prev_year, end_month)
    end = f"{prev_year}-{end_month:02d}-{last_day:02d} 23:59:59"
    return {"start_date": start, "end_date": end}


_STRATEGY_REGISTRY = {
    "last_full_month": _compute_last_full_month,
    "last_full_quarter": _compute_last_full_quarter,
}


def resolve_time_range(range_spec: dict, now: datetime | None = None) -> dict:
    """解析时间范围配置

    支持两种模式：
    1. dynamic 模式（推荐）：`_mode: "dynamic"` + `_strategy` 指定计算策略
       - `_strategy: "last_full_month"` → 上一个完整月
       - `_strategy: "last_full_quarter"` → 上一个完整季度
    2. static 模式（向后兼容）：使用 start_date / end_date 硬编码值

    返回统一的 {"start_date": ..., "end_date": ...} 字典
    """
    if range_spec.get("_mode") == "dynamic":
        strategy = range_spec.get("_strategy")
        if strategy not in _STRATEGY_REGISTRY:
            raise ValueError(
                f"未知的动态策略: {strategy!r}，可选: {list(_STRATEGY_REGISTRY.keys())}"
            )
        result = _STRATEGY_REGISTRY[strategy](now)
        # 保留 start_date/end_date 字段（用于其他只读字段）
        result["_mode"] = "dynamic"
        result["_strategy"] = strategy
        result["_resolved"] = True
        return result

    # static 模式：直接使用配置值
    return {
        "start_date": range_spec["start_date"],
        "end_date": range_spec["end_date"],
        "_mode": "static",
        "_resolved": False,
    }


# ──────────────────────────────────────────────────────────────
# 时间范围读取（自动应用 dynamic / static 模式）
# ──────────────────────────────────────────────────────────────

def get_financial_time_range(config, now: datetime | None = None):
    """获取月度数据时间范围（自动解析 dynamic 模式）"""
    return resolve_time_range(config["时间范围"]["月度数据"], now)


def get_quarterly_time_range(config, now: datetime | None = None):
    """获取季度累计筛选时间范围（自动解析 dynamic 模式）"""
    spec = config["时间范围"].get("季度累计筛选", config["时间范围"]["月度数据"])
    return resolve_time_range(spec, now)


# ──────────────────────────────────────────────────────────────
# 统一的清洗参数加载（一次调用获取所有清洗所需参数）
# ──────────────────────────────────────────────────────────────

def load_clean_params(config, now: datetime | None = None):
    """加载清洗所需的所有参数

    返回: {
        "mapper": DepartmentMapper,
        "matcher": CustomerMatcher,
        "fin_range": 财务端时间范围 (dict: start_date, end_date),
        "quarter_range": 季度累计时间范围 (dict),
    }
    """
    from .mapping_loader import load_department_mapper, load_customer_list
    from .customer_matcher import CustomerMatcher

    mapper = load_department_mapper(config)
    customer_list = load_customer_list(config)
    matcher = CustomerMatcher(customer_list)
    fin_range = get_financial_time_range(config, now)
    quarter_range = get_quarterly_time_range(config, now)

    return {
        "mapper": mapper,
        "matcher": matcher,
        "fin_range": fin_range,
        "quarter_range": quarter_range,
    }
