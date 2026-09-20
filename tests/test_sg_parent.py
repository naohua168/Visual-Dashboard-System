"""南方韶关母公司行测试（2026-09-20 用户口径）

规则 —— **按行判定，不需要维护客户名单**：
- 法人主体 == 南方（韶关）… 且 该行（客户 × 该口径 × 部门）**无销售归属**
  → 客户名改为母公司「南方韶关」聚合展示
- 有销售归属的韶关行 → 保持原客户行（走销售）
- 法人主体 ≠ 南方（韶关）→ 不归拢（走销售）

适用范围：年/月/季度达成页（`_consolidate_customers(df, metric)`）；
总览/同比不传 metric → 不做该归拢。
"""
import pandas as pd
import pytest

import processors.page_data_utils as pdu
from processors.page_data_utils import (
    SG_LEGAL_ENTITY,
    SG_PARENT,
    _consolidate_customers,
    _has_sales_attribution,
    _load_children_map,
    filter_sg_by_legal,
)

SG = SG_LEGAL_ENTITY


@pytest.fixture
def attr(monkeypatch):
    """隔离配置与全局缓存：客户甲（收入+检测有销售）、客户乙（仅信息有销售）"""
    fake = {
        "客户甲": {"某父组": {"收入": {"检测": {"销售A": 1.0}}}},
        "客户乙": {"某父组": {"收入": {"信息": {"销售B": 1.0}}}},
    }
    monkeypatch.setattr(pdu, "_ATTRIBUTION_FLAT", fake)
    monkeypatch.setattr(pdu, "_SG_CHILDREN_SEEN", [])
    monkeypatch.setattr(pdu, "_SUB_TO_PARENT", {})
    monkeypatch.setattr(pdu, "_load_sales_split", lambda: {})
    return fake


def _df(rows):
    return pd.DataFrame(rows, columns=["客户", "法人主体", "事业部", "金额"])


class TestFilterSgByLegal:
    def test_unattributed_shaoguan_row_absorbed(self, attr):
        """法人=韶关 且 无归属 → 归入「南方韶关」"""
        out, names = filter_sg_by_legal(_df([("客户丙", SG, "检测", 100.0)]), "收入")
        assert list(out["客户"]) == [SG_PARENT]
        assert names == ["客户丙"]

    def test_attributed_shaoguan_row_kept(self, attr):
        """法人=韶关 但 检测下有销售比例 → 保持原客户行（走销售）"""
        out, names = filter_sg_by_legal(_df([("客户甲", SG, "检测", 100.0)]), "收入")
        assert list(out["客户"]) == ["客户甲"]
        assert names == []

    def test_dept_mismatch_counts_as_unattributed(self, attr):
        """客户乙只有「信息」有比例 → 检测行无归属 → 归入"""
        out, names = filter_sg_by_legal(_df([("客户乙", SG, "检测", 50.0)]), "收入")
        assert list(out["客户"]) == [SG_PARENT]
        assert names == ["客户乙"]

    def test_metric_specific(self, attr):
        """回款口径未配置（即使收入有）→ 归入"""
        out, names = filter_sg_by_legal(_df([("客户甲", SG, "检测", 100.0)]), "回款")
        assert list(out["客户"]) == [SG_PARENT]

    def test_non_shaoguan_legal_kept(self, attr):
        """法人非南方韶关 → 不归拢（走销售）"""
        out, names = filter_sg_by_legal(
            _df([("客户丙", "广东汽车检测中心有限公司", "检测", 100.0)]), "收入"
        )
        assert list(out["客户"]) == ["客户丙"]
        assert names == []

    def test_mixed_rows(self, attr):
        """同帧混合：无归属韶关行归入、有归属韶关行保留、非韶关行保留"""
        df = _df(
            [
                ("客户丙", SG, "检测", 100.0),
                ("客户甲", SG, "检测", 200.0),
                ("客户丙", "广东汽车检测中心有限公司", "检测", 300.0),
            ]
        )
        out, names = filter_sg_by_legal(df, "收入")
        assert list(out["客户"]) == [SG_PARENT, "客户甲", "客户丙"]
        assert names == ["客户丙"]

    def test_empty_and_missing_columns(self, attr):
        assert filter_sg_by_legal(pd.DataFrame(), "收入")[1] == []
        assert filter_sg_by_legal(pd.DataFrame({"客户": ["A"]}), "收入")[1] == []


class TestConsolidateScope:
    """年/月/季度页组合：_consolidate_customers(df, metric)"""

    def test_creates_parent_row_and_records_child(self, attr):
        df = _df([("客户丙", SG, "检测", 100.0), ("客户丙", SG, "检测", 50.0)])
        out = _consolidate_customers(df, "收入")
        assert list(out["客户"].unique()) == [SG_PARENT]
        assert pdu._SG_CHILDREN_SEEN == ["客户丙"]

    def test_metric_none_skips_sg(self, attr):
        """总览/同比不传 metric → 不归拢"""
        out = _consolidate_customers(_df([("客户丙", SG, "检测", 100.0)]))
        assert list(out["客户"].unique()) == ["客户丙"]
        assert pdu._SG_CHILDREN_SEEN == []

    def test_children_map_injected(self, attr):
        """抽屉/弹窗：母公司「南方韶关」→ 被归入的子客户"""
        _consolidate_customers(_df([("客户丙", SG, "检测", 100.0)]), "收入")
        assert _load_children_map()[SG_PARENT] == ["客户丙"]


class TestHasSalesAttribution:
    def test_no_config(self, attr):
        assert _has_sales_attribution("不存在的客户", "检测", "收入") is False

    def test_dept_and_metric(self, attr):
        assert _has_sales_attribution("客户甲", "检测", "收入") is True
        assert _has_sales_attribution("客户甲", "信息", "收入") is False
        assert _has_sales_attribution("客户甲", "检测", "回款") is False
