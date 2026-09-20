"""南方韶关母公司行测试

需求（2026-09-20 用户口径）：
- 南方韶关.xlsx 清洗后**无销售归属**的客户 → 看板归入母公司行「南方韶关」
- 子公司清单**动态生成**（每个批次可能不同，不写死在配置里）
- **不做销售归属**（这些客户在销售页仍是"待确认"）
- 只归拢**韶关来源**的行（法人主体=南方（韶关）…），不得吸收运营端/主表同名客户
"""
import json

import pandas as pd
import pytest

import processors.page_data_utils as pdu
from processors.page_data_utils import (
    SG_LEGAL_ENTITY,
    SG_PARENT,
    _consolidate_customers,
    _load_children_map,
    _load_sg_children,
    _load_sub_to_parent,
    filter_sg_by_legal,
)


@pytest.fixture
def sg_cache(tmp_path, monkeypatch):
    """把动态清单缓存指向临时文件（收入 2 家 / 回款 1 家，含重复项）"""
    cache = tmp_path / "无归属客户.json"
    cache.write_text(
        json.dumps(
            {
                "收入": {"客户": ["客户甲", "客户乙", "客户甲"], "行数": 3, "金额": 300.0},
                "回款": {"客户": ["客户丙"], "行数": 1, "金额": 50.0},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(pdu, "SG_CACHE_FILE", cache)
    return cache


class TestLoadSgChildren:
    def test_union_of_metrics_dedup(self, sg_cache):
        """收入+回款并集、去重、保持顺序"""
        assert _load_sg_children() == ["客户甲", "客户乙", "客户丙"]

    def test_missing_cache_is_graceful(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pdu, "SG_CACHE_FILE", tmp_path / "not-exists.json")
        assert _load_sg_children() == []

    def test_children_map_injected(self, sg_cache):
        """抽屉/弹窗：母公司 → 子客户列表"""
        cm = _load_children_map()
        assert cm[SG_PARENT] == ["客户甲", "客户乙", "客户丙"]

    def test_not_name_based_mapping(self, sg_cache):
        """⚠️ 不做客户名全局映射：否则运营端同名客户会被误并入南方韶关"""
        assert "客户甲" not in _load_sub_to_parent()


class TestFilterSgByLegal:
    def test_only_shaoguan_rows_renamed(self, sg_cache):
        df = pd.DataFrame(
            {
                "客户": ["客户甲", "客户甲", "客户丁"],
                "法人主体": [SG_LEGAL_ENTITY, "广东汽车检测中心有限公司", SG_LEGAL_ENTITY],
                "事业部": ["检测"] * 3,
                "金额": [100.0, 500.0, 7.0],
            }
        )
        out = filter_sg_by_legal(df)
        assert out.loc[0, "客户"] == SG_PARENT          # 韶关来源 + 在无归属清单 → 归拢
        assert out.loc[1, "客户"] == "客户甲"            # 其他法人 → 原样保留（跨来源不污染）
        assert out.loc[2, "客户"] == "客户丁"            # 韶关来源但不在清单（有销售归属）→ 原样

    def test_no_cache_no_change(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pdu, "SG_CACHE_FILE", tmp_path / "none.json")
        df = pd.DataFrame(
            {
                "客户": ["客户甲"],
                "法人主体": [SG_LEGAL_ENTITY],
                "事业部": ["检测"],
                "金额": [1.0],
            }
        )
        out = filter_sg_by_legal(df)
        assert out.loc[0, "客户"] == "客户甲"

    def test_missing_legal_column(self, sg_cache):
        df = pd.DataFrame({"客户": ["客户甲"], "金额": [1.0]})
        out = filter_sg_by_legal(df)
        assert out.loc[0, "客户"] == "客户甲"


class TestMonthlyOnlyScope:
    """归拢只在月度达成页生效（2026-09-20 用户口径）

    月度页组合 = `_consolidate_customers(filter_sg_by_legal(df))`；
    `_consolidate_customers` 本身不归拢 → 年度/季度/总览/同比保持原客户行。
    """

    def _df(self):
        return pd.DataFrame(
            {
                "客户": ["客户甲", "客户甲"],
                "法人主体": [SG_LEGAL_ENTITY, SG_LEGAL_ENTITY],
                "事业部": ["检测", "检测"],
                "金额": [100.0, 50.0],
            }
        )

    def test_consolidate_alone_keeps_names(self, sg_cache, monkeypatch):
        """不套 filter_sg_by_legal 时（年度/季度页）→ 客户名不变"""
        monkeypatch.setattr(pdu, "_SUB_TO_PARENT", {})
        monkeypatch.setattr(pdu, "_load_sales_split", lambda: {})
        out = _consolidate_customers(self._df())
        assert sorted(out["客户"].unique()) == ["客户甲"]

    def test_monthly_pipeline_renames(self, sg_cache, monkeypatch):
        """月度页组合 → 聚合成「南方韶关」（只有 1 家子客户也要聚合）"""
        monkeypatch.setattr(pdu, "_SUB_TO_PARENT", {})
        monkeypatch.setattr(pdu, "_load_sales_split", lambda: {})
        out = _consolidate_customers(filter_sg_by_legal(self._df()))
        assert list(out["客户"].unique()) == [SG_PARENT]

    def test_other_source_same_name_kept_separate(self, sg_cache, monkeypatch):
        """同名客户的其他来源数据不被吸入母公司行"""
        monkeypatch.setattr(pdu, "_SUB_TO_PARENT", {})
        monkeypatch.setattr(pdu, "_load_sales_split", lambda: {})
        df = pd.DataFrame(
            {
                "客户": ["客户甲", "客户甲"],
                "法人主体": [SG_LEGAL_ENTITY, "运营端某公司"],
                "事业部": ["检测", "检测"],
                "金额": [100.0, 999.0],
            }
        )
        out = _consolidate_customers(filter_sg_by_legal(df))
        assert sorted(out["客户"].unique()) == sorted([SG_PARENT, "客户甲"])


class TestTagSgUnattributed:
    """清洗层：识别无销售归属客户并写清单（不改客户名）"""

    def _df(self):
        return pd.DataFrame(
            {
                "客户": ["有归属客户", "无归属客户", "无归属客户"],
                "事业部": ["检测", "检测", "检测"],
                "金额": [100.0, 200.0, 50.0],
            }
        )

    def test_writes_cache_and_keeps_names(self, tmp_path, monkeypatch):
        import engine.income_payment.financial as fin

        cache = tmp_path / "sg.json"
        monkeypatch.setattr(fin, "_sg_cache_path", lambda: cache)
        monkeypatch.setattr(
            fin,
            "_load_attribution_groups",
            lambda: {"有归属客户": {"某父组": {"收入": {"检测": {"销售A": 1.0}}}}},
        )
        out = fin._tag_sg_unattributed(self._df(), "收入", "检测")
        # 客户名保持原样（看板弹窗仍按子公司展开明细）
        assert list(out["客户"]) == ["有归属客户", "无归属客户", "无归属客户"]
        data = json.loads(cache.read_text(encoding="utf-8"))
        assert data["收入"]["客户"] == ["无归属客户"]
        assert data["收入"]["行数"] == 2
        assert data["收入"]["金额"] == 250.0

    def test_attributed_customer_excluded(self, tmp_path, monkeypatch):
        import engine.income_payment.financial as fin

        cache = tmp_path / "sg.json"
        monkeypatch.setattr(fin, "_sg_cache_path", lambda: cache)
        monkeypatch.setattr(
            fin,
            "_load_attribution_groups",
            lambda: {"有归属客户": {"某父组": {"收入": {"检测": {"销售A": 1.0}}}}},
        )
        fin._tag_sg_unattributed(self._df().head(1), "收入", "检测")
        data = json.loads(cache.read_text(encoding="utf-8"))
        assert data["收入"]["客户"] == []

    def test_dept_mismatch_counts_as_unattributed(self, tmp_path, monkeypatch):
        """客户有配置但「检测」下无比例（韶关固定检测）→ 视为无归属"""
        import engine.income_payment.financial as fin

        cache = tmp_path / "sg.json"
        monkeypatch.setattr(fin, "_sg_cache_path", lambda: cache)
        monkeypatch.setattr(
            fin,
            "_load_attribution_groups",
            lambda: {"有归属客户": {"某父组": {"收入": {"信息": {"销售A": 1.0}}}}},
        )
        fin._tag_sg_unattributed(self._df().head(1), "收入", "检测")
        data = json.loads(cache.read_text(encoding="utf-8"))
        assert data["收入"]["客户"] == ["有归属客户"]

    def test_metric_specific(self, tmp_path, monkeypatch):
        """收入/回款分别判定：只写了收入比例 → 回款侧算无归属"""
        import engine.income_payment.financial as fin

        cache = tmp_path / "sg.json"
        monkeypatch.setattr(fin, "_sg_cache_path", lambda: cache)
        monkeypatch.setattr(
            fin,
            "_load_attribution_groups",
            lambda: {"有归属客户": {"某父组": {"收入": {"检测": {"销售A": 1.0}}}}},
        )
        fin._tag_sg_unattributed(self._df().head(1), "回款", "检测")
        data = json.loads(cache.read_text(encoding="utf-8"))
        assert data["回款"]["客户"] == ["有归属客户"]

    def test_keeps_other_metric_when_updating(self, tmp_path, monkeypatch):
        """写回时保留上一次另一口径的数据"""
        import engine.income_payment.financial as fin

        cache = tmp_path / "sg.json"
        cache.write_text(
            json.dumps({"收入": {"客户": ["旧客户"]}}, ensure_ascii=False), encoding="utf-8"
        )
        monkeypatch.setattr(fin, "_sg_cache_path", lambda: cache)
        monkeypatch.setattr(fin, "_load_attribution_groups", lambda: {})
        fin._tag_sg_unattributed(self._df().head(1), "回款", "检测")
        data = json.loads(cache.read_text(encoding="utf-8"))
        assert data["收入"]["客户"] == ["旧客户"]  # 未被清掉
        assert data["回款"]["客户"] == ["有归属客户"]
