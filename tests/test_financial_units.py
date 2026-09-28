# Author: naohua168 <bai_bai168@qq.com>
"""财务端独立格式来源（广东/湖南/南方韶关）金额单位换算 — 配置驱动 `金额乘数`

背景（2026-09-28）：`data/raw/财务端数据/南方韶关.xlsx` 的**收入 Sheet 金额单位由「万元」改为「元」**，
不能再写死 ×10000。现由 `数据源.财务端.<来源>.金额乘数` 决定，支持：
  · 数值：该来源所有 Sheet 相同（如 10000 = 万元）
  · 字典：按 Sheet/指标分别配置（如 {"收入": 1, "回款": 10000} = 收入已是元、回款仍是万元）

覆盖：
  - _amount_multiplier：数值 / 字典 / 缺省 / 非法值 / 字符串
  - clean_shaoguan：收入 ×1 保持元量级；回款 ×10000 换算为元
"""
import pandas as pd
import pytest

from engine.income_payment import financial as fin
from engine.income_payment.financial import _amount_multiplier, clean_shaoguan

TIME_RANGE = {"start_date": "2026-09-01", "end_date": "2026-09-30"}
INCOME_AMOUNTS = [7547.17, 87613.21]

SHAOGUAN_CFG = {
    "数据源": {"财务端": {"南方韶关": {
        "Sheet": {"收入": ["收入"], "回款": ["回款"]},
        "引擎": "openpyxl",
        "列映射": {"客户": ["客户"], "日期": ["日期"], "金额": ["金额"]},
        "金额乘数": {"收入": 1, "回款": 10000},
        "事业部固定": "检测",
    }}}
}


# ══════════════════════════════════════════════════════════════
# _amount_multiplier
# ══════════════════════════════════════════════════════════════
def test_multiplier_scalar_applies_to_all_sheets():
    cfg = {"金额乘数": 10000}
    assert _amount_multiplier(cfg, "收入") == 10000.0
    assert _amount_multiplier(cfg, "回款") == 10000.0


def test_multiplier_dict_per_sheet():
    cfg = {"金额乘数": {"收入": 1, "回款": 10000}}
    assert _amount_multiplier(cfg, "收入") == 1.0
    assert _amount_multiplier(cfg, "回款") == 10000.0


def test_multiplier_dict_missing_key_falls_back():
    assert _amount_multiplier({"金额乘数": {"收入": 1}}, "回款") == 10000.0


def test_multiplier_missing_or_invalid_defaults_to_wan():
    assert _amount_multiplier({}, "收入") == 10000.0
    assert _amount_multiplier({"金额乘数": None}, "收入") == 10000.0
    assert _amount_multiplier({"金额乘数": "abc"}, "收入") == 10000.0


def test_multiplier_string_number_ok():
    assert _amount_multiplier({"金额乘数": "1"}, "收入") == 1.0


# ══════════════════════════════════════════════════════════════
# clean_shaoguan：按 Sheet 使用不同乘数
# ══════════════════════════════════════════════════════════════
@pytest.fixture
def sg_file(tmp_path, monkeypatch):
    """造一个含 收入/回款 两个 Sheet 的南方韶关文件，并把读取/白名单/命中日志打桩"""
    p = tmp_path / "南方韶关.xlsx"
    df = pd.DataFrame({
        "客户": ["客户甲", "客户乙"],
        "日期": ["2026-09-10", "2026-09-11"],
        "金额": INCOME_AMOUNTS,
    })
    with pd.ExcelWriter(p, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="收入", index=False)
        df.to_excel(w, sheet_name="回款", index=False)

    monkeypatch.setattr(fin, "get_data_path", lambda *a, **k: p)
    monkeypatch.setattr(fin, "_filter_by_whitelist", lambda df, *a, **k: df)
    monkeypatch.setattr(fin, "print_hit_columns", lambda *a, **k: None)
    return p


def test_shaoguan_income_keeps_yuan_scale(sg_file):
    """收入 Sheet 已是「元」（乘数 1）→ 不得被放大 10000 倍"""
    out = clean_shaoguan(SHAOGUAN_CFG, None, TIME_RANGE, "收入")
    assert len(out) == 2
    assert round(float(out["金额"].sum()), 2) == round(sum(INCOME_AMOUNTS), 2)


def test_shaoguan_payment_converts_wan_to_yuan(sg_file):
    """回款 Sheet 仍为「万元」（乘数 10000）→ 换算为元"""
    out = clean_shaoguan(SHAOGUAN_CFG, None, TIME_RANGE, "回款")
    assert len(out) == 2
    assert round(float(out["金额"].sum()), 2) == round(sum(INCOME_AMOUNTS) * 10000, 2)


def test_shaoguan_empty_payment_sheet_returns_empty(tmp_path, monkeypatch):
    """回款 Sheet 为空 → 返回空表（不报错）"""
    p = tmp_path / "南方韶关.xlsx"
    pd.DataFrame(columns=["客户", "日期", "金额"]).to_excel(p, sheet_name="回款", index=False)
    monkeypatch.setattr(fin, "get_data_path", lambda *a, **k: p)
    monkeypatch.setattr(fin, "_filter_by_whitelist", lambda df, *a, **k: df)
    monkeypatch.setattr(fin, "print_hit_columns", lambda *a, **k: None)
    out = clean_shaoguan(SHAOGUAN_CFG, None, TIME_RANGE, "回款")
    assert len(out) == 0
