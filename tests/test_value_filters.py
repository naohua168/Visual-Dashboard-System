# Author: naohua168 <bai_bai168@qq.com>
"""保留取值过滤 —— `保留取值 = {标准字段: [允许值, ...]}`：命中即保留，其余（含空值）剔除

2026-10-13 用户口径：
  - 财务端收入：`单据状态 = 已审核` **且** `委托类型 = 外部结算`
  - 财务端回款：`单据状态 = 已审核`（回款表无「委托类型」列，不配置该字段）

语义与「排除标记」（命中即剔除，列提取前按源列名过滤）相反；本过滤在列提取之后执行，
字段候选列名走「字段映射」sheet（配置编辑器）维护。
"""
import pandas as pd
import pytest

import engine.income_payment.financial as fin_mod
from engine.core.customer_matcher import CustomerMatcher
from engine.core.mapping_loader import DepartmentMapper
from engine.core.utils import filter_by_kept_values


# ──────────────────────────── 单元：filter_by_kept_values ────────────────────────────
def _spec(values_by_field):
    return {"保留取值": values_by_field}


def test_single_field_keep_hits_only():
    df = pd.DataFrame({"单据状态": ["已审核", "未审核", None], "金额": [1.0, 2.0, 3.0]})
    out = filter_by_kept_values(df, _spec({"单据状态": ["已审核"]}), "测试")
    assert list(out["金额"]) == [1.0]


def test_multi_field_is_and():
    df = pd.DataFrame({
        "单据状态": ["已审核", "已审核", "未审核"],
        "委托类型": ["外部结算", "内部结算", "外部结算"],
        "金额": [1.0, 2.0, 3.0],
    })
    out = filter_by_kept_values(df, _spec({"单据状态": ["已审核"], "委托类型": ["外部结算"]}), "测试")
    assert list(out["金额"]) == [1.0]


def test_value_whitespace_tolerance():
    df = pd.DataFrame({"单据状态": [" 已审核 ", "已审核"], "金额": [1.0, 2.0]})
    out = filter_by_kept_values(df, _spec({"单据状态": ["已审核"]}), "测试")
    assert len(out) == 2


def test_missing_field_skipped():
    """源表没有配置字段的列 → 跳过该字段筛选，不报错"""
    df = pd.DataFrame({"单据状态": ["已审核", "未审核"], "金额": [1.0, 2.0]})
    out = filter_by_kept_values(df, _spec({"委托类型": ["外部结算"]}), "测试")
    assert len(out) == 2


def test_not_configured_returns_unchanged():
    df = pd.DataFrame({"单据状态": ["未审核"], "金额": [1.0]})
    out = filter_by_kept_values(df, {"列映射": {}}, "测试")
    assert len(out) == 1


def test_empty_and_none_safe():
    assert filter_by_kept_values(None, _spec({"单据状态": ["已审核"]}), "测试") is None
    empty = pd.DataFrame(columns=["单据状态"])
    assert len(filter_by_kept_values(empty, _spec({"单据状态": ["已审核"]}), "测试")) == 0


# ──────────────────────────── 集成：财务端主表清洗 ────────────────────────────
def _cfg():
    return {
        "数据源": {"财务端": {"收入": {
            "Sheet": ["Sheet1"],
            "引擎": "openpyxl",
            "列映射": {
                "日期": ["创建时间"],
                "客户": ["客户.名称"],
                "金额": ["不含税金额"],
                "部门": ["成本中心.名称"],
                "法人主体": ["公司"],
                "排除标记": ["初始化"],
                "单据状态": ["单据状态"],
                "委托类型": ["委托类型"],
            },
            "过客户白名单": False,
            "可选字段": ["排除标记", "单据状态", "委托类型"],
            "保留取值": {"单据状态": ["已审核"], "委托类型": ["外部结算"]},
            "排除标记值": ["√"],
        }}},
    }


def _row(amt, cust="甲", status="已审核", entrust="外部结算", init=None, created="2026-10-08"):
    return {
        "创建时间": created, "客户.名称": cust, "不含税金额": amt,
        "成本中心.名称": "检测工程事业部", "公司": "广东汽车检测中心有限公司",
        "初始化": init, "单据状态": status, "委托类型": entrust,
    }


def _run(tmp_path, monkeypatch, rows, cfg=None):
    xlsx = tmp_path / "收入.xlsx"
    pd.DataFrame(rows).to_excel(xlsx, index=False)
    monkeypatch.setattr(fin_mod, "get_data_path", lambda *a, **k: xlsx)
    mapper = DepartmentMapper({"payment_mapping": {"检测工程事业部": "检测"}})
    matcher = CustomerMatcher([])
    time_range = {"start_date": "2026-10-01", "end_date": "2026-10-31"}
    return fin_mod.clean_financial_main(cfg or _cfg(), mapper, matcher, "收入", time_range)


class TestFinancialMainIntegration:
    def test_both_filters_apply(self, tmp_path, monkeypatch):
        rows = [
            _row(100, "甲"),                            # 通过
            _row(200, "乙", status="未审核"),           # 单据状态不通过
            _row(300, "丙", entrust="内部结算"),        # 委托类型不通过
            _row(400, "丁", status="", entrust=None),   # 空值不通过
        ]
        out = _run(tmp_path, monkeypatch, rows)
        assert list(out["客户"]) == ["甲"]
        assert float(out["金额"].sum()) == 100

    def test_exclude_marker_runs_first(self, tmp_path, monkeypatch):
        """初始化=√ 的期初行即使满足两个条件也要被剔除（排除标记优先）"""
        rows = [_row(100, "甲"), _row(200, "乙", init="√")]
        out = _run(tmp_path, monkeypatch, rows)
        assert list(out["客户"]) == ["甲"]

    def test_missing_entrust_column_degrades(self, tmp_path, monkeypatch):
        """源表没有「委托类型」列 → 只按单据状态过滤，不报错"""
        base = {"创建时间": "2026-10-08", "成本中心.名称": "检测工程事业部",
                "公司": "广东汽车检测中心有限公司", "初始化": None}
        rows = [
            {**base, "客户.名称": "甲", "不含税金额": 100, "单据状态": "已审核"},
            {**base, "客户.名称": "乙", "不含税金额": 200, "单据状态": "未审核"},
        ]
        out = _run(tmp_path, monkeypatch, rows)
        assert list(out["客户"]) == ["甲"]
