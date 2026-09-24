# Author: naohua168 <bai_bai168@qq.com>
"""拆分键分隔符容错 —— '母公司<任意分隔符>销售' 归一化（2026-09-24 用户口径）

场景：月度/季度指标表**不需要「销售」列**，客户列直接写 `科技公司·王海龙`；
      中间分隔符无论打成 - / － / 空格 / 斜杠 / 顿号… 都应匹配到该销售行。
覆盖：
  - normalize_split_cust / split_key_parts（分隔符容错）
  - _consolidate_target：无销售列不报错、复合键保持、旧写法行为不变
  - _build_subs_detail：客户列写复合键时弹窗「（本部）」目标可取到
"""
import pandas as pd
import pytest

from processors import page_data_utils as u
from processors.page_data_utils import (
    _build_subs_detail,
    _consolidate_target,
    _sales_from_key,
    normalize_split_cust,
    split_key_parts,
)

SPLIT = {"科技公司": {"子公司A": "王海龙", "子公司B": "李巍"}}


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    """隔离配置与全局缓存：只保留 科技公司 一个拆分母公司"""
    monkeypatch.setattr(u, "_load_sales_split", lambda *a, **k: SPLIT)
    monkeypatch.setattr(u, "_load_sub_sales_to_parent", lambda *a, **k: {})
    monkeypatch.setattr(
        u, "_SUB_TO_PARENT", {"子公司A": "科技公司", "子公司B": "科技公司"}
    )


# ══════════════════════════════════════════════════════════════
# 分隔符容错
# ══════════════════════════════════════════════════════════════
@pytest.mark.parametrize(
    "sep",
    ["·", "-", "－", "—", "–", "−", "/", "／", "|", " ", "   ", "、", ",", "，",
     ":", "：", "。", "~", "_", "•", "・"],
)
def test_normalize_any_separator(sep):
    assert normalize_split_cust(f"科技公司{sep}王海龙") == "科技公司·王海龙"


def test_normalize_bare_parent_unchanged():
    assert normalize_split_cust("科技公司") == "科技公司"


def test_normalize_plain_customer_unchanged():
    assert normalize_split_cust("某某科技股份有限公司") == "某某科技股份有限公司"


def test_parent_without_separator_is_not_split_key():
    """母公司名后直接跟销售名（无分隔符）→ 不视为拆分键"""
    assert split_key_parts("科技公司王海龙") is None


def test_sales_from_key_tolerates_separator():
    assert _sales_from_key("科技公司·王海龙") == "王海龙"
    assert _sales_from_key("科技公司-王海龙") == "王海龙"
    assert _sales_from_key("科技公司") is None


# ══════════════════════════════════════════════════════════════
# 指标表：无销售列
# ══════════════════════════════════════════════════════════════
def test_consolidate_target_without_sales_column():
    """客户列直接写复合键、没有销售列 → 不报 KeyError，键归一化后保留"""
    tgt = pd.DataFrame([
        {"客户": "科技公司·王海龙", "检测": 100, "信息": 30, "能源": 0, "海外": 0},
        {"客户": "科技公司-李巍", "检测": 50, "信息": 20, "能源": 0, "海外": 0},
    ])
    out = _consolidate_target(tgt)
    assert set(out["客户"]) == {"科技公司·王海龙", "科技公司·李巍"}
    assert float(out.loc[out["客户"] == "科技公司·王海龙", "检测"].iloc[0]) == 100
    assert float(out.loc[out["客户"] == "科技公司·李巍", "信息"].iloc[0]) == 20


def test_consolidate_target_with_sales_column_unchanged():
    """保留销售列的旧写法行为不变（客户=科技公司 + 销售列）"""
    tgt = pd.DataFrame([
        {"客户": "科技公司", "销售": "王海龙", "检测": 100, "信息": 0, "能源": 0, "海外": 0},
        {"客户": "科技公司", "销售": "李巍", "检测": 50, "信息": 0, "能源": 0, "海外": 0},
    ])
    out = _consolidate_target(tgt)
    assert set(out["客户"]) == {"科技公司·王海龙", "科技公司·李巍"}


def test_consolidate_target_sub_customer_without_sales_column():
    """子公司名 + 无销售列 → 按配置归属推出 '母公司·销售'"""
    tgt = pd.DataFrame([{"客户": "子公司A", "检测": 80, "信息": 0, "能源": 0, "海外": 0}])
    out = _consolidate_target(tgt)
    assert list(out["客户"]) == ["科技公司·王海龙"]


# ══════════════════════════════════════════════════════════════
# 弹窗明细：复合键的「（本部）」目标
# ══════════════════════════════════════════════════════════════
def test_build_subs_detail_parent_target_from_composite_key():
    raw_tgt = pd.DataFrame([
        {"客户": "科技公司-王海龙", "检测": 100, "信息": 0, "能源": 0, "海外": 0},
    ])
    raw_act = pd.DataFrame([{"客户": "子公司A", "事业部": "检测", "金额": 1_000_000.0}])
    detail = _build_subs_detail(
        raw_act, raw_tgt, {"科技公司": ["子公司A", "子公司B"]}, ["科技公司·王海龙"]
    )
    assert "科技公司·王海龙" in detail
    row = detail["科技公司·王海龙"]
    assert row["科技公司（本部）"]["合计"]["tgt"] == 100
    assert row["子公司A"]["合计"]["act"] == 100.0


def test_build_subs_detail_parent_target_from_sales_column():
    """旧写法（客户=科技公司 + 销售列）弹窗本部目标同样正常"""
    raw_tgt = pd.DataFrame([
        {"客户": "科技公司", "销售": "王海龙", "检测": 100, "信息": 0, "能源": 0, "海外": 0},
        {"客户": "科技公司", "销售": "李巍", "检测": 70, "信息": 0, "能源": 0, "海外": 0},
    ])
    raw_act = pd.DataFrame([{"客户": "子公司B", "事业部": "检测", "金额": 2_000_000.0}])
    detail = _build_subs_detail(
        raw_act, raw_tgt, {"科技公司": ["子公司A", "子公司B"]},
        ["科技公司·王海龙", "科技公司·李巍"],
    )
    assert detail["科技公司·王海龙"]["科技公司（本部）"]["合计"]["tgt"] == 100
    assert detail["科技公司·李巍"]["科技公司（本部）"]["合计"]["tgt"] == 70
