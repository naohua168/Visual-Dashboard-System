# Author: naohua168 <bai_bai168@qq.com>
"""比亚迪母公司归属：按法人主体区分（2026-09-28 用户口径）

规则 —— **只对同时在「比亚迪汽车工业有限公司」与「比亚迪电池」两个父组下出现的子公司**
做法人主体判断：

- 法人主体 == 广东汽车检测中心有限公司 → 归 **比亚迪汽车工业有限公司**
- 其他法人主体                          → 归 **比亚迪电池**

配套：销售引擎 `engine/sales/run.py` 的 BYD_SUB_COMPANIES 规则
（广东主体→黄浩浩=汽车工业组、非广东→周涵林=电池组）。

同时保证「子公司明细弹窗」与「客户矩阵行」口径一致
（多组子公司在抽屉里不再被两个父组重复计入）。
"""
import json
from pathlib import Path

import pandas as pd
import pytest

import processors.page_data_utils as pdu
from processors.page_data_utils import (
    BYD_PARENT_BATTERY,
    BYD_PARENT_INDUSTRY,
    GD_LEGAL_FILTER,
    _build_subs_detail,
    _build_subs_with_data,
    _byd_multi_subs,
    _consolidate_customers,
    _multi_group_subs,
    filter_byd_by_legal,
)

GD = GD_LEGAL_FILTER
OTHER_LEGAL = "中国汽车工程研究院股份有限公司"
MULTI = "多组客户有限公司"
BATTERY_SUB = "电池子公司"
INDUSTRY_SUB = "车企子公司"

REAL_JSON = Path(__file__).parent.parent / "config" / "清洗配置" / "客户销售归属.json"


@pytest.fixture
def byd_env(monkeypatch):
    """隔离配置与全局缓存：MULTI 为"两父组同时出现"的多组子公司"""
    monkeypatch.setattr(pdu, "_byd_multi_subs", lambda: {MULTI})
    monkeypatch.setattr(pdu, "_gd_multi_sub_to_keep", lambda: set())
    monkeypatch.setattr(pdu, "_SUB_TO_PARENT", {BATTERY_SUB: BYD_PARENT_BATTERY,
                                               INDUSTRY_SUB: BYD_PARENT_INDUSTRY})
    monkeypatch.setattr(pdu, "_SG_CHILDREN_SEEN", [])
    monkeypatch.setattr(pdu, "_load_sales_split", lambda: {})
    monkeypatch.setattr(pdu, "_load_sub_sales_to_parent", lambda: {})
    return {BYD_PARENT_BATTERY: [BATTERY_SUB, MULTI],
            BYD_PARENT_INDUSTRY: [INDUSTRY_SUB, MULTI]}


def _df(rows):
    return pd.DataFrame(rows, columns=["客户", "法人主体", "事业部", "金额"])


def _rows_actual():
    """多组客户：广东法人 100 万（→汽车工业）+ 其他法人 40 万（→电池）（金额单位：元）"""
    return [
        (MULTI, GD, "检测", 1_000_000.0),
        (MULTI, OTHER_LEGAL, "检测", 400_000.0),
        (BATTERY_SUB, OTHER_LEGAL, "能源", 100_000.0),
        (INDUSTRY_SUB, GD, "信息", 50_000.0),
    ]


# ──────────────────────────────────────────────────────────────
# 规则本身
# ──────────────────────────────────────────────────────────────
class TestFilterBydByLegal:
    def test_gd_legal_to_industry_others_to_battery(self, byd_env):
        out = filter_byd_by_legal(_df(_rows_actual()))
        assert list(out["客户"]) == [BYD_PARENT_INDUSTRY, BYD_PARENT_BATTERY,
                                     BATTERY_SUB, INDUSTRY_SUB]

    def test_non_multi_customer_untouched(self, byd_env):
        out = filter_byd_by_legal(_df([("普通客户", GD, "检测", 1.0)]))
        assert list(out["客户"]) == ["普通客户"]

    def test_no_legal_column_no_change(self, byd_env):
        df = pd.DataFrame([(MULTI, "检测", 1.0)], columns=["客户", "事业部", "金额"])
        assert list(filter_byd_by_legal(df)["客户"]) == [MULTI]

    def test_empty_multi_set_no_change(self, monkeypatch):
        """只挂单边（两父组未同时出现）→ 不做法人判断，保持原样"""
        monkeypatch.setattr(pdu, "_byd_multi_subs", lambda: set())
        df = _df([(MULTI, GD, "检测", 1.0)])
        assert list(filter_byd_by_legal(df)["客户"]) == [MULTI]

    def test_applied_inside_consolidate_customers(self, byd_env):
        out = _consolidate_customers(_df(_rows_actual()))
        assert out.loc[out["金额"] == 1_000_000.0, "客户"].iloc[0] == BYD_PARENT_INDUSTRY
        assert out.loc[out["金额"] == 400_000.0, "客户"].iloc[0] == BYD_PARENT_BATTERY

    def test_multi_group_subs_union(self, byd_env, monkeypatch):
        monkeypatch.setattr(pdu, "_gd_multi_sub_to_keep", lambda: {"广东多组客户"})
        assert _multi_group_subs() == {MULTI, "广东多组客户"}


# ──────────────────────────────────────────────────────────────
# 弹窗（子公司明细）与矩阵行口径一致
# ──────────────────────────────────────────────────────────────
class TestDrawerMatchesOwnership:
    def _detail(self, byd_env, parent):
        detail = _build_subs_detail(_df(_rows_actual()), None, byd_env, [parent])
        return detail.get(parent, {})

    def test_battery_keeps_only_other_legal_rows(self, byd_env):
        """电池组：多组客户只算非广东法人那部分（40，不含广东的 100）"""
        rows = self._detail(byd_env, BYD_PARENT_BATTERY)
        assert rows[MULTI]["检测"]["act"] == 40.0
        assert rows[BATTERY_SUB]["能源"]["act"] == 10.0

    def test_industry_keeps_only_gd_legal_rows(self, byd_env):
        """汽车工业组：多组客户只算广东法人那部分（100）"""
        rows = self._detail(byd_env, BYD_PARENT_INDUSTRY)
        assert rows[MULTI]["检测"]["act"] == 100.0
        assert rows[INDUSTRY_SUB]["信息"]["act"] == 5.0

    def test_no_double_counting(self, byd_env):
        """两父组抽屉相加 = 原始总额（不重不漏）"""
        b = self._detail(byd_env, BYD_PARENT_BATTERY)
        i = self._detail(byd_env, BYD_PARENT_INDUSTRY)
        assert sum(r["合计"]["act"] for r in b.values()) == 50.0
        assert sum(r["合计"]["act"] for r in i.values()) == 105.0

    def test_with_data_lists_multi_sub_under_both(self, byd_env):
        """多组子公司在两个父组下都"有数据"（各自只算自己那部分）"""
        got = _build_subs_with_data(
            [_df(_rows_actual())], [], byd_env,
            [BYD_PARENT_BATTERY, BYD_PARENT_INDUSTRY],
        )
        assert MULTI in got[BYD_PARENT_BATTERY]
        assert MULTI in got[BYD_PARENT_INDUSTRY]
        assert INDUSTRY_SUB not in got[BYD_PARENT_BATTERY]
        assert BATTERY_SUB not in got[BYD_PARENT_INDUSTRY]


# ──────────────────────────────────────────────────────────────
# 真实配置：多组集合 =「两父组子公司」交集
# ──────────────────────────────────────────────────────────────
@pytest.mark.skipif(not REAL_JSON.exists(), reason="客户销售归属.json 不存在")
class TestRealConfig:
    def test_multi_subs_is_intersection(self):
        groups = json.loads(REAL_JSON.read_text(encoding="utf-8"))["客户归属"]
        industry = set(groups.get(BYD_PARENT_INDUSTRY, {}).get("子公司", {}).keys())
        battery = set(groups.get(BYD_PARENT_BATTERY, {}).get("子公司", {}).keys())
        assert _byd_multi_subs() == {s.strip() for s in industry & battery}

    def test_both_parents_configured(self):
        groups = json.loads(REAL_JSON.read_text(encoding="utf-8"))["客户归属"]
        assert BYD_PARENT_INDUSTRY in groups
        assert BYD_PARENT_BATTERY in groups
