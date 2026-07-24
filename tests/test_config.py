"""测试配置加载 — cleaning_config.json 和 4 份 mappings 文件可读"""
import json
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / "config" / "cleaning_config.json"


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
    for key in ["数据源", "映射文件", "时间范围", "客户匹配", "输出"]:
        assert key in data, f"配置缺少顶层字段: {key}"


def test_config_data_sources():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    src = data["数据源"]
    assert "财务端" in src and "运营端" in src
    # 财务端必需的子源
    for sub in ["客户名单", "收入", "回款", "广东公司", "湖南公司"]:
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
    """4 份 mappings JSON 文件均存在且有效"""
    mappings_dir = BASE_DIR / "data" / "mappings"
    expected = {
        "部门事业部映射": "部门事业部映射.json",
        "客户名单": "客户名单.json",
        "客户统称名单": "客户统称名单.json",
        "客户销售对应规则": "客户销售对应规则.json",
    }
    for folder, filename in expected.items():
        path = mappings_dir / folder / filename
        assert path.exists(), f"映射文件不存在: {path}"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)  # 必须 JSON 有效
        assert isinstance(data, dict)


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


def test_customer_list_count():
    """客户白名单数量 > 0"""
    path = BASE_DIR / "data" / "mappings" / "客户名单" / "客户名单.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    customers = data.get("customers", [])
    assert len(customers) > 0, "客户白名单为空"
    # 不应有重复
    no_space = [c.replace(" ", "") for c in customers]
    assert len(no_space) == len(set(no_space)), "客户白名单有重复（去空格后）"


def test_sales_rules_structure():
    """销售规则包含 4 个层级"""
    path = BASE_DIR / "data" / "mappings" / "客户销售对应规则" / "客户销售对应规则.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for layer in ["广东公司规则", "深圳公司规则", "其他规则", "默认规则"]:
        assert layer in data, f"销售规则缺少层级: {layer}"
        assert isinstance(data[layer], dict)
