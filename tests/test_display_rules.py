# Author: naohua168 <bai_bai168@qq.com>
"""测试展示规则加载 + 组名展开 + 客户筛选引擎 — 2026-08-04 新增
"""
import pandas as pd
from pathlib import Path

from processors.config_loader import (
    SORT_DEFAULT,
    SORT_NONE,
    SORT_OPTIONS,
    CustomerFilter,
    expand_to_customer_names,
    get_value,
)
from processors.page_data import _sorted_customers


BASE_DIR = Path(__file__).parent.parent


# ═══════════════════════════════════════════════════════════
# 组名展开
# ═══════════════════════════════════════════════════════════
class TestExpandParentToChildren:
    def test_expand_known_parent_groups(self):
        """已知母公司组名应展开为所有子客户"""
        result = expand_to_customer_names(
            BASE_DIR,
            ["广汽系", "比亚迪电池"]
        )
        # 广汽系 7 个， 比亚迪电池 30 个 → 37 个不重复
        assert len(result) >= 30, f"应至少展开 30 个客户，实际 {len(result)}"

    def test_expand_keeps_leaf_customers(self):
        """叶子客户名（非组名）应原样保留"""
        result = expand_to_customer_names(
            BASE_DIR,
            ["华为数字能源技术有限公司"]   # 作为叶子名
        )
        assert "华为数字能源技术有限公司" in result

    def test_empty_input(self):
        """空输入应返回空集合"""
        assert expand_to_customer_names(BASE_DIR, []) == set()

    def test_whitespace_stripped(self):
        """前后空白应被忽略"""
        result = expand_to_customer_names(BASE_DIR, ["  广汽系  "])
        assert len(result) > 0


# ═══════════════════════════════════════════════════════════
# CustomerFilter 配置加载
# ═══════════════════════════════════════════════════════════
class TestCustomerFilterFromConfig:
    def test_loads_annual_filter(self):
        """从配置加载年度达成过滤器（已改为显示全部客户）"""
        f = CustomerFilter.from_config(BASE_DIR, "年度达成", section="客户矩阵")
        assert f.is_empty(), "年度达成应无 include 列表（显示全部客户）"
        assert f.max_rows == 0, f"应读到 max_rows=0，实际 {f.max_rows}"

    def test_loads_overview_topn(self):
        """读取销售TopN"""
        topn = get_value(BASE_DIR, "数据总览", "销售TopN", 10)
        assert isinstance(topn, int) and topn > 0

    def test_loads_yoy_max_rows(self):
        """读取年度同比最大行数"""
        f = CustomerFilter.from_config(BASE_DIR, "年度同比")
        assert f.max_rows > 0, "应有 max_rows 配置"

    def test_loads_monthly_no_filter(self):
        """月度达成应为空筛选"""
        f = CustomerFilter.from_config(BASE_DIR, "月度达成", section="客户矩阵")
        assert f.is_empty(), "月度达成应无 include 列表"
        assert f.max_rows == 0


# ═══════════════════════════════════════════════════════════
# CustomerFilter.apply() 行为
# ═══════════════════════════════════════════════════════════
class TestCustomerFilterApply:
    def _make_piv(self, names, values):
        return pd.DataFrame({"合计": values}, index=names)

    def test_apply_expands_groups(self):
        """白名单含组名 → 子客户全部保留"""
        all_customers = [
            "广汽集团A", "广汽集团B", "比亚迪电池-1", "比亚迪电池-2",
            "其他客户X", "其他客户Y",
        ]
        f = CustomerFilter(include=["广汽系", "比亚迪电池"], max_rows=0)
        piv = self._make_piv(all_customers, [100] * len(all_customers))
        out = f.apply(all_customers, piv, piv, base_dir=BASE_DIR)
        for c in out:
            assert c != "其他客户X" and c != "其他客户Y", f"无关客户不应保留: {c}"

    def test_apply_max_rows_truncates(self):
        """max_rows > 0 时应截断"""
        customers = [f"客户{i}" for i in range(50)]
        piv = self._make_piv(customers, list(range(50)))
        f = CustomerFilter(include=[], max_rows=5)
        out = f.apply(customers, piv, piv)
        assert len(out) == 5

    def test_apply_no_filter_returns_all(self):
        """无 include + max_rows=0 应返回全部"""
        customers = [f"客户{i}" for i in range(20)]
        f = CustomerFilter(include=[], max_rows=0)
        out = f.apply(customers, None, None, base_dir=BASE_DIR)
        assert len(out) == 20

    def test_apply_sort_by_amount_desc(self):
        """排序方式 = 实际金额降序"""
        customers = ["低", "高", "中"]
        piv = self._make_piv(["低", "高", "中"], [10, 100, 50])
        f = CustomerFilter(include=[], max_rows=0, sort_by="实际金额降序")
        out = f.apply(customers, piv, piv, base_dir=BASE_DIR)
        assert out == ["高", "中", "低"]

    def test_apply_sort_by_rate_desc(self):
        """排序方式 = 达成率降序"""
        customers = ["差", "优", "中"]
        piv = self._make_piv(["差", "优", "中"], [10, 100, 50])  # 实际
        tgt = self._make_piv(["差", "优", "中"], [100, 100, 100])  # 目标相同
        f = CustomerFilter(include=[], max_rows=0, sort_by="达成率降序")
        out = f.apply(customers, piv, tgt, base_dir=BASE_DIR)
        assert out == ["优", "中", "差"]

    def test_apply_sort_none_keeps_order(self):
        """排序方式 = 不排序 → 完全保持传入（指标表）顺序"""
        customers = ["丙", "甲", "乙"]
        piv = self._make_piv(customers, [10, 100, 50])
        f = CustomerFilter(include=[], max_rows=0, sort_by=SORT_NONE)
        assert f.sort_none is True
        out = f.apply(customers, piv, piv, base_dir=BASE_DIR)
        assert out == customers

    def test_sort_options_match_sheet_choices(self):
        """排序取值与「展示规则」sheet 下拉一致（防止两处漂移）"""
        from scripts.display_rules_sheet import SORT_CHOICES

        assert list(SORT_OPTIONS) == list(SORT_CHOICES)
        assert SORT_DEFAULT == SORT_CHOICES[0]
        assert SORT_NONE in SORT_CHOICES


# ═══════════════════════════════════════════════════════════
# _sorted_customers：优先展示 × 排序方式
# ═══════════════════════════════════════════════════════════
class TestSortedCustomersSortMode:
    NAMES = ["甲", "乙", "丙"]          # 指标表行序
    TGT = [300.0, 100.0, 200.0]         # 目标：甲 > 丙 > 乙
    ACT = [10.0, 100.0, 50.0]           # 实际：乙 > 丙 > 甲

    def _piv(self, values):
        return pd.DataFrame({"合计": values}, index=self.NAMES)

    def _tgt_df(self):
        return pd.DataFrame(
            {"合计": self.TGT, "检测": self.TGT, "信息": [0.0] * 3,
             "能源": [0.0] * 3, "海外": [0.0] * 3},
            index=self.NAMES,
        )

    def _run(self, sort_by, priority):
        filt = CustomerFilter(priority=priority, sort_by=sort_by)
        return _sorted_customers(self._tgt_df(), filt=filt, piv=self._piv(self.ACT),
                                 base_dir=BASE_DIR)

    def test_priority_default_sorts_by_target(self):
        """默认「目标合计降序」：按目标降序（300 > 200 > 100）"""
        main, _ = self._run(SORT_DEFAULT, ["甲", "乙", "丙"])
        assert main == ["甲", "丙", "乙"]

    def test_priority_with_sort_none_keeps_table_order(self):
        """不排序：完全按指标表行序（优先展示只决定可见性，不改顺序）"""
        filt = CustomerFilter(priority=["甲", "乙", "丙"], sort_by=SORT_NONE)
        assert filt.sort_none is True
        main, _ = self._run(SORT_NONE, ["甲", "乙", "丙"])
        assert main == ["甲", "乙", "丙"]

    def test_sort_by_amount_desc_wins(self):
        """实际金额降序：按实际降序（100 > 50 > 10）"""
        main, _ = self._run("实际金额降序", ["甲", "乙", "丙"])
        assert main == ["乙", "丙", "甲"]

    def test_priority_subset_folds_others(self):
        """优先展示只列部分客户时：命中者进主表、其余折叠（两者各自保持指标表序）"""
        main, rest = self._run(SORT_NONE, ["丙"])
        assert main == ["丙"]
        assert rest == ["甲", "乙"]


# ═══════════════════════════════════════════════════════════
# _sorted_customers 行为
# ═══════════════════════════════════════════════════════════
class TestSortedCustomers:
    def _make_df(self, names, values):
        return pd.DataFrame({"合计": values}, index=names)

    def test_non_target_above_50w_shown(self):
        """非指标客户：实际>0 就展示（无金额阈值）"""
        tgt = self._make_df(["A", "B"], [100, 50])
        piv = self._make_df(["A", "B", "C", "D"], [80, 30, 60, 30])
        pri, rest = _sorted_customers(tgt, piv=piv)
        assert "C" in pri, "非指标但有实际60万的客户 C 应展示"
        assert "D" in pri, "非指标但有实际30万的客户 D 应展示"
        # 指标客户在前：A(100), B(50)；非指标有实际在后：C(60), D(30)
        assert pri == ["A", "B", "C", "D"]

    def test_target_all_zero_excluded(self):
        """指标全为0且无实际：不展示"""
        tgt = self._make_df(["A", "B"], [100, 0])
        piv = self._make_df([], [])
        pri, rest = _sorted_customers(tgt, piv=piv)
        assert "B" not in pri, "指标全为0且无实际的客户 B 应排除"
        assert "A" in pri

    def test_target_zero_but_has_actual_shown(self):
        """指标=0但有实际金额（>0）：展示"""
        tgt = self._make_df(["A", "B"], [100, 0])
        piv = self._make_df(["A", "B", "C"], [80, 60, 30])
        pri, rest = _sorted_customers(tgt, piv=piv)
        assert "B" in pri, "指标=0但有实际60万的客户 B 应展示"
        assert "C" in pri, "无指标但有实际30万的客户 C 应展示"

    def test_no_target_no_actual_excluded(self):
        """无指标且无实际：不展示"""
        tgt = self._make_df(["A"], [100])
        piv = self._make_df(["A", "D"], [80, 0])
        pri, rest = _sorted_customers(tgt, piv=piv)
        assert "D" not in pri, "无指标且无实际的客户 D 不应展示"

    def test_empty_piv_still_works(self):
        """piv 为空时只返回有目标的客户"""
        tgt = self._make_df(["A", "B"], [100, 50])
        piv = self._make_df([], [])
        pri, rest = _sorted_customers(tgt, piv=piv)
        assert pri == ["A", "B"]
