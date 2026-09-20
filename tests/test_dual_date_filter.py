# -*- coding: utf-8 -*-
"""回款「双日期」口径 + 可选字段测试

2026-09-18 新增口径：财务端回款需「业务日期」与「收款日期」**同时**落在时间范围内才收录。
"""
import pandas as pd
import pytest

import engine.income_payment.financial as fin_mod
from engine.core.column_resolver import extract_columns, find_column_safe
from engine.core.customer_matcher import CustomerMatcher
from engine.core.mapping_loader import DepartmentMapper


class TestOptionalFields:
    """extract_columns 的「可选字段」行为"""

    def test_missing_optional_field_skipped(self):
        df = pd.DataFrame({"业务日期": ["2026-09-10"], "客户": ["A"]})
        out = extract_columns(df, {"日期": ["业务日期"], "收款日期": ["收款日期"]},
                              optional_fields={"收款日期"})
        assert list(out.columns) == ["日期"]
        assert out.attrs["_missing_optional"] == ["收款日期"]
        assert "收款日期" not in out.attrs["_hit_columns"]

    def test_optional_field_present_records_hit(self):
        df = pd.DataFrame({"业务日期": ["2026-09-10"], "收款日期": ["2026-09-12"]})
        out = extract_columns(df, {"日期": ["业务日期"], "收款日期": ["收款日期"]},
                              optional_fields={"收款日期"})
        assert list(out.columns) == ["日期", "收款日期"]
        assert out.attrs["_missing_optional"] == []
        assert out.attrs["_hit_columns"]["收款日期"] == "收款日期"

    def test_required_field_still_raises(self):
        df = pd.DataFrame({"业务日期": ["2026-09-10"]})
        with pytest.raises(KeyError):
            extract_columns(df, {"金额": ["应收金额"]})

    def test_no_optional_fields_keeps_old_behavior(self):
        df = pd.DataFrame({"日期": ["2026-09-10"]})
        out = extract_columns(df, {"日期": ["日期"]})
        assert out.attrs["_missing_optional"] == []

    def test_find_column_safe(self):
        df = pd.DataFrame({"业务日期": ["x"]})
        assert find_column_safe(df, ["业务日期"]) == "业务日期"
        assert find_column_safe(df, ["不存在", "也不存在"]) is None


def _cfg():
    return {
        "数据源": {"财务端": {"回款": {
            "Sheet": ["Sheet1"],
            "引擎": "openpyxl",
            "列映射": {
                "日期": ["业务日期"],
                "客户": ["付款人(客户).名称"],
                "金额": ["应收金额"],
                "部门": ["成本中心.名称"],
                "收款日期": ["收款日期"],
            },
            "过客户白名单": False,
            "可选字段": ["收款日期"],
            "日期字段组": ["日期", "收款日期"],
        }}},
    }


def _run(tmp_path, monkeypatch, rows, cfg=None):
    xlsx = tmp_path / "回款.xlsx"
    pd.DataFrame(rows).to_excel(xlsx, index=False)
    monkeypatch.setattr(fin_mod, "get_data_path", lambda *a, **k: xlsx)
    mapper = DepartmentMapper({"payment_mapping": {"检测工程事业部": "检测"}})
    matcher = CustomerMatcher([])
    time_range = {"start_date": "2026-09-01", "end_date": "2026-09-30"}
    return fin_mod.clean_financial_main(cfg or _cfg(), mapper, matcher, "回款", time_range)


def _row(biz, rec, amt, cust="甲"):
    return {
        "业务日期": biz, "收款日期": rec, "付款人(客户).名称": cust,
        "应收金额": amt, "成本中心.名称": "检测工程事业部",
    }


class TestDualDateFilter:
    """集成测试：两个日期都必须在窗口内"""

    def test_both_in_window_kept(self, tmp_path, monkeypatch):
        out = _run(tmp_path, monkeypatch, [_row("2026-09-05", "2026-09-06", 100, "甲")])
        assert len(out) == 1 and float(out["金额"].sum()) == 100

    def test_collection_date_outside_window_dropped(self, tmp_path, monkeypatch):
        rows = [
            _row("2026-09-05", "2026-09-06", 100, "甲"),   # 都通过
            _row("2026-09-05", "2026-08-31", 200, "乙"),   # 收款日期在窗口外 → 排除
            _row("2026-08-05", "2026-09-06", 300, "丙"),   # 业务日期在窗口外 → 排除
        ]
        out = _run(tmp_path, monkeypatch, rows)
        assert len(out) == 1 and float(out["金额"].sum()) == 100
        assert set(out["客户"]) == {"甲"}

    def test_missing_collection_date_excluded(self, tmp_path, monkeypatch):
        rows = [
            _row("2026-09-05", None, 100, "甲"),           # 无收款日期 → 不满足"都是本月"
            _row("2026-09-05", "2026-09-06", 200, "乙"),
        ]
        out = _run(tmp_path, monkeypatch, rows)
        assert len(out) == 1 and float(out["金额"].sum()) == 200

    def test_absent_column_falls_back_to_single_date(self, tmp_path, monkeypatch):
        """源表没有「收款日期」列时不报错，降级为单日期筛选"""
        rows = [{"业务日期": "2026-09-05", "付款人(客户).名称": "甲",
                 "应收金额": 100, "成本中心.名称": "检测工程事业部"}]
        out = _run(tmp_path, monkeypatch, rows)
        assert len(out) == 1

    def test_single_date_config_unchanged(self, tmp_path, monkeypatch):
        """未配置「日期字段组」时维持原有单日期行为（收入侧）"""
        cfg = _cfg()
        del cfg["数据源"]["财务端"]["回款"]["日期字段组"]
        del cfg["数据源"]["财务端"]["回款"]["可选字段"]
        del cfg["数据源"]["财务端"]["回款"]["列映射"]["收款日期"]
        rows = [_row("2026-09-05", "2026-08-31", 100, "甲")]
        out = _run(tmp_path, monkeypatch, rows, cfg=cfg)
        assert len(out) == 1  # 只看业务日期 → 保留
