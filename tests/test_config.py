"""测试配置加载 — cleaning_config.json 和映射/规则文件可读"""
import json
from datetime import datetime
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / "config" / "清洗配置" / "cleaning_config.json"


def test_config_exists():
    assert CONFIG_PATH.exists(), f"配置文件不存在: {CONFIG_PATH}"


def test_config_valid_json():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)


def test_config_required_sections():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    # 必需的顶层字段
    for key in ["数据源", "映射文件", "时间范围", "输出"]:
        assert key in data, f"配置缺少顶层字段: {key}"


def test_config_data_sources():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    src = data["数据源"]
    assert "财务端" in src and "运营端" in src
    # 财务端必需的子源
    for sub in ["收入", "回款", "广东公司", "湖南公司"]:
        assert sub in src["财务端"], f"财务端缺少子源: {sub}"
    # 运营端必需的子源
    for sub in ["收入", "回款"]:
        assert sub in src["运营端"], f"运营端缺少子源: {sub}"


def test_config_output_paths():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    out = data["输出"]
    for key in ["月收入", "月回款", "当年累计收入", "当年累计回款", "销售收入", "销售回款"]:
        assert key in out, f"输出缺少: {key}"
        assert out[key].endswith("/"), f"输出路径应以/结尾: {out[key]}"


def test_mappings_exist():
    """映射和规则 JSON 文件均存在且有效（2份在 data/mappings/ + 2份在 config/清洗配置/）"""
    # data/mappings/ 下的清洗映射
    # 部门事业部映射: dict；客户名单: 客户名白名单数组（list）
    for folder, filename, allowed in [
        ("部门事业部映射", "部门事业部映射.json", (dict,)),
        ("客户名单", "客户名单.json", (list, dict)),
    ]:
        path = BASE_DIR / "data" / "mappings" / folder / filename
        assert path.exists(), f"映射文件不存在: {path}"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, allowed), f"{filename} 结构应为 {allowed}"


def test_dept_mapping_structure():
    """部门事业部映射包含 4 大事业部"""
    path = BASE_DIR / "data" / "mappings" / "部门事业部映射" / "部门事业部映射.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "income_mapping" in data
    assert "payment_mapping" in data
    # 4 大事业部在 income_mapping 的值中
    valid_depts = {"检测", "信息", "能源", "海外"}
    income_values = {v for k, v in data["income_mapping"].items() if not k.startswith("_")}
    assert income_values.issubset(valid_depts), f"收入映射值异常: {income_values}"

# ──────────────────────────────────────────────────────────────
# 动态时间范围解析测试（dynamic / static 模式）
# ──────────────────────────────────────────────────────────────
from engine.core.config import (
    _compute_last_full_month,
    _compute_last_full_quarter,
    resolve_time_range,
    get_quarterly_time_range,
)


def test_last_full_month_mid_year():
    """7月中旬 → 上一个完整月应为6月"""
    now = datetime(2026, 7, 29)
    r = _compute_last_full_month(now)
    assert r["start_date"] == "2026-06-01"
    assert r["end_date"] == "2026-06-30 23:59:59"


def test_last_full_month_year_boundary():
    """1月 → 上一个完整月应为去年12月，年份正确切换"""
    now = datetime(2026, 1, 15)
    r = _compute_last_full_month(now)
    assert r["start_date"] == "2025-12-01"
    assert r["end_date"] == "2025-12-31 23:59:59"


def test_last_full_month_february_leap():
    """2月（29天）→ 上一个完整月应为1月"""
    now = datetime(2024, 2, 10)
    r = _compute_last_full_month(now)
    assert r["start_date"] == "2024-01-01"
    assert r["end_date"] == "2024-01-31 23:59:59"


def test_last_full_quarter_q3_unfinished():
    """7月 → 上一个完整季度应为Q2（4-6月）"""
    now = datetime(2026, 7, 29)
    r = _compute_last_full_quarter(now)
    assert r["start_date"] == "2026-04-01"
    assert r["end_date"] == "2026-06-30 23:59:59"


def test_last_full_quarter_q1_year_boundary():
    """2月（Q1未结束）→ 上一个完整季度应为去年Q4"""
    now = datetime(2026, 2, 15)
    r = _compute_last_full_quarter(now)
    assert r["start_date"] == "2025-10-01"
    assert r["end_date"] == "2025-12-31 23:59:59"


def test_last_full_quarter_q4_november():
    """11月 → 上一个完整季度应为Q3（7-9月）"""
    now = datetime(2026, 11, 30)
    r = _compute_last_full_quarter(now)
    assert r["start_date"] == "2026-07-01"
    assert r["end_date"] == "2026-09-30 23:59:59"


def test_resolve_dynamic_last_full_month():
    """dynamic + last_full_month 模式解析"""
    spec = {
        "_mode": "dynamic",
        "_strategy": "last_full_month",
        "start_date": "2026-06-01",  # 静态值应被覆盖
        "end_date": "2026-06-30 23:59:59",
    }
    r = resolve_time_range(spec, datetime(2026, 7, 29))
    assert r["start_date"] == "2026-06-01"
    assert r["end_date"] == "2026-06-30 23:59:59"
    assert r["_mode"] == "dynamic"
    assert r["_strategy"] == "last_full_month"
    assert r["_resolved"] is True


def test_resolve_static_passthrough():
    """static 模式直接使用配置值"""
    spec = {
        "start_date": "2025-12-01",
        "end_date": "2025-12-31 23:59:59",
    }
    r = resolve_time_range(spec)
    assert r["start_date"] == "2025-12-01"
    assert r["end_date"] == "2025-12-31 23:59:59"
    assert r["_mode"] == "static"
    assert r["_resolved"] is False


def test_resolve_unknown_strategy_raises():
    """未知策略应抛错（fail-fast）"""
    spec = {"_mode": "dynamic", "_strategy": "unknown"}
    with pytest.raises(ValueError, match="未知的动态策略"):
        resolve_time_range(spec)


def test_quarterly_time_range_uses_config():
    """读取 cleaning_config.json 后，季度范围从配置读取（手动模式）"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    r = get_quarterly_time_range(config, datetime(2026, 7, 29))
    # 手动模式：直接使用配置中的日期
    assert r["start_date"] == "2026-07-01"
    assert r["_mode"] == "static"


def test_current_config_uses_static_mode():
    """当前 cleaning_config.json 的时间范围必须使用手动模式（用户偏好）

    2026-07-31 起明确：所有时间范围手动配置，不使用 dynamic 推导。
    """
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    time_range = config["时间范围"]
    for key in ["年度累计", "月度数据", "季度累计筛选"]:
        spec = time_range[key]
        assert spec.get("_mode") != "dynamic", f"{key} 不应使用 dynamic 模式"
        assert "start_date" in spec and "end_date" in spec
    assert time_range["月度数据"]["start_date"] == "2026-08-01"
    assert time_range["季度累计筛选"]["start_date"] == "2026-07-01"
