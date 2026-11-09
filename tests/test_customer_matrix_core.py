# Author: naohua168 <bai_bai168@qq.com>
"""客户矩阵核心逻辑（scripts/customer_matrix_core.py）单元测试

覆盖：清单解析 / 母公司归拢 / 子公司单户 / 别名 / 简写顺序展开 / 未识别占位 /
父行去重 / 合计行 / 快照配对。全部用构造数据，不依赖 data/sheets。
"""
import pandas as pd
import pytest

from processors.data_utils import DEPARTMENTS
from scripts.customer_matrix_core import (
    ALIASES,
    REPEAT_GROUPS,
    build_rows_by_order,
    build_total_row,
    parse_customers,
    resolve_snapshot,
)


def _frame(data: dict[str, dict[str, float]]) -> pd.DataFrame:
    """构造透视表：index=客户，columns=4 部门 + 合计"""
    df = pd.DataFrame(data).T
    df["合计"] = df[DEPARTMENTS].sum(axis=1)
    return df


def _piv():
    return _frame({
        "甲集团": {"检测": 100.0, "信息": 0.0, "能源": 0.0, "海外": 0.0},
        "乙公司": {"检测": 0.0, "信息": 50.0, "能源": 0.0, "海外": 0.0},
    })


SUBS_ALL = {"甲集团": ["甲集团", "甲子公司"], "乙公司": ["乙公司"]}
DETAIL = {"甲集团": {"甲子公司": {
    "检测": {"act": 40.0, "tgt": 30.0}, "信息": {"act": 0.0, "tgt": 0.0},
    "能源": {"act": 0.0, "tgt": 0.0}, "海外": {"act": 0.0, "tgt": 0.0},
    "合计": {"act": 40.0, "tgt": 30.0},
}}}


class TestParseCustomers:
    def test_splits_newline_and_commas(self):
        assert parse_customers("甲\n乙,丙，丁;戊") == ["甲", "乙", "丙", "丁", "戊"]

    def test_keeps_duplicates_in_order(self):
        # 同名多次出现是「科技公司」顺序展开的用法，不能被去重
        assert parse_customers("科技公司\n科技公司") == ["科技公司", "科技公司"]

    def test_ignores_blank(self):
        assert parse_customers("\n\n 甲 \n\n") == ["甲"]


class TestBuildRows:
    def test_parent_row_aggregates(self):
        rows, trace = build_rows_by_order(["甲集团"], _piv(), _piv(), DETAIL, SUBS_ALL)
        assert rows[0]["合计_实际"] == 100.0
        assert rows[0]["合计_指标"] == 100.0
        assert trace[0]["口径"].startswith("母公司")

    def test_leaf_row_only_self(self):
        rows, _ = build_rows_by_order(["甲子公司"], _piv(), _piv(), DETAIL, SUBS_ALL)
        assert rows[0]["合计_实际"] == 40.0          # 只取子公司自身
        assert rows[0]["合计_指标"] == 30.0

    def test_alias_maps_to_system_name(self):
        alias, target = next(iter(ALIASES.items()))
        rows, trace = build_rows_by_order([alias], _piv(), _piv(), DETAIL, SUBS_ALL)
        assert trace[0]["系统实体"] == target
        assert "名单写法对应系统" in trace[0]["备注"]

    def test_repeat_group_expands_in_order(self):
        label = "科技公司"
        rows, trace = build_rows_by_order([label, label], _piv(), _piv(), DETAIL, SUBS_ALL)
        seq = REPEAT_GROUPS[label]
        assert trace[0]["系统实体"] == seq[0]
        assert trace[1]["系统实体"] == seq[1]

    def test_unknown_customer_keeps_placeholder_row(self):
        rows, trace = build_rows_by_order(["查无此客户"], _piv(), _piv(), DETAIL, SUBS_ALL)
        assert rows[0]["合计_实际"] == 0.0
        assert rows[0]["合计达成率"] is None         # 写进 Excel 显示「—」
        assert trace[0]["口径"] == "本期无数据/无指标"

    def test_parent_row_subtracts_listed_child(self):
        """母+子同时出现时，母行扣掉子行，避免指标算两遍"""
        rows, trace = build_rows_by_order(["甲集团", "甲子公司"], _piv(), _piv(), DETAIL, SUBS_ALL)
        assert rows[0]["合计_实际"] == pytest.approx(60.0)   # 100 - 40
        assert rows[0]["合计_指标"] == pytest.approx(70.0)   # 100 - 30
        assert "已扣除" in trace[0]["备注"]
        assert rows[1]["合计_实际"] == 40.0

    def test_row_count_matches_input(self):
        names = ["甲集团", "查无此客户", "乙公司"]
        rows, trace = build_rows_by_order(names, _piv(), _piv(), DETAIL, SUBS_ALL)
        assert len(rows) == len(names) == len(trace)


class TestTotalRow:
    def test_total_uses_full_pivot(self):
        total = build_total_row(_piv(), _piv())
        assert total["合计_实际"] == 150.0
        assert total["合计_指标"] == 150.0
        assert total["合计达成率"] == 1.0


class TestDefaultPath:
    def test_output_goes_to_own_category(self, tmp_path):
        """矩阵导出独立成类：output/客户矩阵/<年>/<月>/（2026-11-06 用户要求）"""
        from datetime import date

        from scripts.customer_matrix_core import default_out_file, matrix_root

        out = default_out_file(tmp_path, "客户矩阵_月季年")
        assert matrix_root(tmp_path) == tmp_path / "output" / "客户矩阵"
        assert out.parent == tmp_path / "output" / "客户矩阵" / f"{date.today():%Y}" / f"{date.today():%m}"
        assert out.name.startswith("客户矩阵_月季年_")


class TestResolveSnapshot:
    def test_data_file_passthrough(self, tmp_path):
        f = tmp_path / "data_20261106.xlsx"
        f.write_bytes(b"x")
        assert resolve_snapshot(f) == f

    def test_board_html_pairs_sibling_category(self, tmp_path):
        """看板在 看板/2026/11/，总表在 数据/2026/11/ —— 跨类别目录配对"""
        board = tmp_path / "看板" / "2026" / "11" / "看板_20261106.html"
        board.parent.mkdir(parents=True)
        board.write_text("<html></html>", encoding="utf-8")
        data = tmp_path / "数据" / "2026" / "11" / "data_20261106.xlsx"
        data.parent.mkdir(parents=True)
        data.write_bytes(b"x")
        assert resolve_snapshot(board) == data

    def test_missing_data_raises(self, tmp_path):
        board = tmp_path / "看板" / "2026" / "11" / "看板_20261106.html"
        board.parent.mkdir(parents=True)
        board.write_text("<html></html>", encoding="utf-8")
        with pytest.raises(FileNotFoundError):
            resolve_snapshot(board)
