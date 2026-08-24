"""Mock 测试 — 使用合成 DataFrame 测试数据层核心函数，无需真实 Excel 文件

覆盖:
  - _consolidate_customers (子公司→母公司归拢)
  - _customer_pivot (客户×事业部 pivot)
  - _sorted_customers (排序+优先拆分)
  - _dept_target_sum (部门目标合计)
  - _yoy_rate (同比率)
  - _yoy_from_yearly (年基线同比)
  - _group_by_parent (母公司归拢)
  - _add_wan (万元转换)
"""
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from processors.page_data_utils import (
    _add_wan,
    _build_subs_detail,
    _consolidate_customers,
    _consolidate_target,
    _customer_pivot,
    _data_max_month,
    _dept_target_sum,
    _group_by_parent,
    _parse_month_range,
    _resplit_priority,
    _sorted_customers,
    _yoy_from_yearly,
    _yoy_rate,
    DEPARTMENTS,
)


# ══════════════════════════════════════════════════════════════
# 测试 _add_wan
# ══════════════════════════════════════════════════════════════
class TestAddWan:
    def test_add_wan_column(self):
        df = pd.DataFrame({"金额": [10000, 20000, 0]})
        result = _add_wan(df)
        assert "金额_万" in result.columns
        assert result["金额_万"].tolist() == [1.0, 2.0, 0.0]

    def test_add_wan_empty(self):
        df = pd.DataFrame({"金额": []})
        result = _add_wan(df)
        assert len(result) == 0
        assert "金额_万" in result.columns


# ══════════════════════════════════════════════════════════════
# 测试 _dept_target_sum
# ══════════════════════════════════════════════════════════════
class TestDeptTargetSum:
    def test_simple_sum(self):
        tgt = pd.DataFrame({
            "客户": ["A", "B"],
            "检测": [100, 200],
            "信息": [50, 50],
            "能源": [30, 20],
            "海外": [10, 10],
        })
        assert _dept_target_sum(tgt) == 470

    def test_with_suffix_columns(self):
        tgt = pd.DataFrame({
            "客户": ["A"],
            "检测收入": [100],
            "信息回款": [50],
        })
        assert _dept_target_sum(tgt) == 150

    def test_empty(self):
        tgt = pd.DataFrame()
        assert _dept_target_sum(tgt) == 0


# ══════════════════════════════════════════════════════════════
# 测试 _yoy_rate
# ══════════════════════════════════════════════════════════════
class TestYoyRate:
    def test_positive(self):
        assert _yoy_rate(120, 100) == pytest.approx(0.2)

    def test_negative(self):
        assert _yoy_rate(80, 100) == pytest.approx(-0.2)

    def test_zero_prev(self):
        assert _yoy_rate(100, 0) is None


# ══════════════════════════════════════════════════════════════
# 测试 _yoy_from_yearly (mock 数据)
# ══════════════════════════════════════════════════════════════
class TestYoyFromYearly:
    def test_none_yearly(self):
        assert _yoy_from_yearly(None, 100, 1, 6) is None

    def test_empty_yearly(self):
        assert _yoy_from_yearly(pd.DataFrame(), 100, 1, 6) is None

    def test_summary_mode(self):
        """汇总模式：所有行同一月份 → 全量总计"""
        yi = pd.DataFrame({
            "日期": ["2025-07-01", "2025-07-01", "2025-07-01"],
            "金额": [500000, 300000, 200000],  # 合计 100万/10000 = 100万
        })
        # cur_val=120万, prev=100万 → +20%
        result = _yoy_from_yearly(yi, 120, 1, 6)
        assert result == pytest.approx(0.2)

    def test_monthly_mode(self):
        """逐月模式：按月份范围筛选"""
        yi = pd.DataFrame({
            "日期": ["2025-01-01", "2025-02-01", "2025-07-01"],
            "金额": [200000, 300000, 500000],
        })
        # 筛选 1~2月 → 50万/10000 = 50万
        result = _yoy_from_yearly(yi, 75, 1, 2)  # cur=75万, prev=50万 → +50%
        assert result == pytest.approx(0.5)


# ══════════════════════════════════════════════════════════════
# 测试 _data_max_month
# ══════════════════════════════════════════════════════════════
class TestDataMaxMonth:
    def test_normal(self):
        df = pd.DataFrame({"日期": ["2026-01-01", "2026-03-15", "2026-07-20"]})
        assert _data_max_month(df) == 7

    def test_empty(self):
        assert _data_max_month(pd.DataFrame()) == 6


# ══════════════════════════════════════════════════════════════
# 测试 _customer_pivot
# ══════════════════════════════════════════════════════════════
class TestCustomerPivot:
    def test_basic_pivot(self):
        df = pd.DataFrame({
            "客户": ["A", "A", "B"],
            "事业部": ["检测", "信息", "检测"],
            "金额_万": [10, 20, 30],
        })
        tgt = pd.DataFrame({
            "客户": ["A", "B"],
            "检测": [50, 100],
            "信息": [30, 0],
        })
        piv, tgt_g = _customer_pivot(df, tgt)
        assert "检测" in piv.columns
        assert "合计" in piv.columns
        assert piv.loc["A", "检测"] == 10
        assert piv.loc["B", "检测"] == 30
        assert "合计" in tgt_g.columns

    def test_empty_target(self):
        df = pd.DataFrame({"客户": ["A"], "事业部": ["检测"], "金额_万": [10]})
        tgt = pd.DataFrame()
        piv, tgt_g = _customer_pivot(df, tgt)
        assert "合计" in piv.columns
        assert list(tgt_g.columns) == DEPARTMENTS + ["合计"]


# ══════════════════════════════════════════════════════════════
# 测试 _sorted_customers
# ══════════════════════════════════════════════════════════════
class TestSortedCustomers:
    def test_basic_sort(self):
        tgt = pd.DataFrame(
            {"合计": [300, 100, 200]},
            index=["A", "B", "C"],
        )
        pri, rest = _sorted_customers(tgt)
        assert pri == ["A", "C", "B"]  # 按目标降序
        assert rest == []

    def test_with_priority(self):
        tgt = pd.DataFrame(
            {"合计": [300, 100, 200]},
            index=["比亚迪", "小公司", "广汽"],
        )
        piv = pd.DataFrame(
            {"合计": [250, 50, 180]},
            index=["比亚迪", "小公司", "广汽"],
        )
        # 无 filter → 全部在 priority
        pri, rest = _sorted_customers(tgt)
        assert len(pri) == 3
        assert pri[0] == "比亚迪"

    def test_zero_target_excluded(self):
        tgt = pd.DataFrame(
            {"合计": [100, 0, 200]},
            index=["A", "B", "C"],
        )
        pri, rest = _sorted_customers(tgt)
        assert "B" not in pri  # 指标=0 且无实际 → 排除
        assert len(pri) == 2


# ══════════════════════════════════════════════════════════════
# 测试 _consolidate_customers (需要客户归属 JSON mock)
# ══════════════════════════════════════════════════════════════
class TestConsolidateCustomers:
    def test_no_consolidation_needed(self):
        """无归属映射时客户名不变"""
        df = pd.DataFrame({
            "客户": ["公司A", "公司B", "公司C"],
            "金额": [100, 200, 300],
        })
        result = _consolidate_customers(df)
        assert list(result["客户"]) == ["公司A", "公司B", "公司C"]


# ══════════════════════════════════════════════════════════════
# 测试 _consolidate_target
# ══════════════════════════════════════════════════════════════
class TestConsolidateTarget:
    def test_empty(self):
        result = _consolidate_target(pd.DataFrame())
        assert len(result) == 0

    def test_group_by_customer_sales(self):
        tgt = pd.DataFrame({
            "客户": ["A", "A"],
            "销售": ["张三", "张三"],
            "检测": [10, 20],
            "信息": [5, 5],
        })
        result = _consolidate_target(tgt)
        assert len(result) == 1
        assert result.iloc[0]["检测"] == 30


    def test_split_parent_with_sales_maps_to_split_key(self, monkeypatch):
        """客户名=拆分母公司本身 + 销售列 → 拆成 '母公司·销售'（月度/季度指标表按 客户=科技公司 + 销售 维护）"""
        monkeypatch.setattr(
            "processors.page_data_utils._load_sales_split",
            lambda: {"科技公司": {"子公司A": "王海龙", "子公司B": "李巍"}},
        )
        monkeypatch.setattr("processors.page_data_utils._load_sub_sales_to_parent", lambda: {})
        tgt = pd.DataFrame({
            "客户": ["科技公司", "科技公司"],
            "销售": ["王海龙", "李巍"],
            "检测": [100, 50],
            "信息": [30, 20],
            "能源": [0, 0],
            "海外": [0, 0],
        })
        result = _consolidate_target(tgt)
        assert set(result["客户"]) == {"科技公司·王海龙", "科技公司·李巍"}
        whl = result[result["客户"] == "科技公司·王海龙"].iloc[0]
        assert whl["检测"] == 100
        lw = result[result["客户"] == "科技公司·李巍"].iloc[0]
        assert lw["信息"] == 20

    def test_sub_customer_still_maps_to_split_key(self, monkeypatch):
        """子公司行仍按 (子公司,销售)→母公司 拆成 '母公司·销售'"""
        monkeypatch.setattr(
            "processors.page_data_utils._load_sales_split",
            lambda: {"科技公司": {"子公司A": "王海龙", "子公司B": "李巍"}},
        )
        monkeypatch.setattr(
            "processors.page_data_utils._load_sub_sales_to_parent",
            lambda: {("子公司A", "王海龙"): "科技公司"},
        )
        tgt = pd.DataFrame({
            "客户": ["子公司A"],
            "销售": ["王海龙"],
            "检测": [100],
            "信息": [0],
            "能源": [0],
            "海外": [0],
        })
        result = _consolidate_target(tgt)
        assert list(result["客户"]) == ["科技公司·王海龙"]
        assert result.iloc[0]["检测"] == 100


# ══════════════════════════════════════════════════════════════
# 测试 _build_subs_detail（弹窗：拆分键本部目标按销售过滤）
# ══════════════════════════════════════════════════════════════
class TestBuildSubsDetailSplitParent:
    def test_head_office_target_filtered_by_sales(self, monkeypatch):
        """拆分键（科技公司·王海龙）的弹窗本部目标只取该销售，不混入另一位销售"""
        monkeypatch.setattr(
            "processors.page_data_utils._load_sales_split",
            lambda: {"科技公司": {"子公司A": "王海龙", "子公司B": "李巍"}},
        )
        raw_actual = pd.DataFrame(columns=["客户", "事业部", "金额"])
        raw_target = pd.DataFrame({
            "客户": ["科技公司", "科技公司"],
            "销售": ["王海龙", "李巍"],
            "检测": [100, 50],
            "信息": [30, 20],
            "能源": [0, 0],
            "海外": [0, 0],
        })
        children_map = {"科技公司": ["子公司A", "子公司B"]}
        result = _build_subs_detail(
            raw_actual, raw_target, children_map, ["科技公司·王海龙"]
        )
        detail = result["科技公司·王海龙"]
        ho = detail.get("科技公司（本部）")
        assert ho is not None
        assert ho["合计"]["tgt"] == 130  # 100+30，只含王海龙
        # 李巍 本部目标不被混入
        assert ho["合计"]["tgt"] != 180  # 100+30+50+20 合计值


# ══════════════════════════════════════════════════════════════
# 测试 _group_by_parent (需要 base_dir mock)
# ══════════════════════════════════════════════════════════════
class TestGroupByParent:
    def test_empty_parent_map(self):
        """无客户归属 JSON 时返回原数据"""
        with tempfile.TemporaryDirectory() as tmp:
            piv = pd.DataFrame(
                {"检测": [10], "合计": [10]},
                index=["公司A"],
            )
            tgt = pd.DataFrame(
                {"检测": [50], "合计": [50]},
                index=["公司A"],
            )
            result_piv, result_tgt, result_custs = _group_by_parent(
                piv, tgt, ["公司A"], Path(tmp)
            )
            assert result_custs == ["公司A"]
            assert result_piv.equals(piv)
