"""测试通用工具函数"""
import pandas as pd
import pytest

from engine.core.utils import filter_by_date, init_company_type, standardize_output, log_step


class TestFilterByDate:
    def test_basic_filter(self):
        df = pd.DataFrame({"日期": ["2026-06-01", "2026-07-01", "2026-06-15"]})
        result = filter_by_date(df, "日期", "2026-06-01", "2026-06-30")
        assert len(result) == 2

    def test_inclusive_bounds(self):
        df = pd.DataFrame({"日期": ["2026-06-01", "2026-06-30"]})
        result = filter_by_date(df, "日期", "2026-06-01", "2026-06-30")
        assert len(result) == 2  # 边界值包含

    def test_invalid_dates_dropped(self):
        df = pd.DataFrame({"日期": ["2026-06-01", "not-a-date", "abc"]})
        result = filter_by_date(df, "日期", "2026-01-01", "2026-12-31")
        assert len(result) == 1  # 非法日期被 coerce 成 NaT 后过滤


class TestInitCompanyType:
    def test_adds_columns(self):
        df = pd.DataFrame({"客户": ["A"]})
        result = init_company_type(df)
        assert "是否为广东公司" in result.columns
        assert "是否为深圳公司" in result.columns
        assert (result["是否为广东公司"] == "").all()


class TestStandardizeOutput:
    def test_column_order(self):
        df = pd.DataFrame({
            "客户": ["A"], "金额": [100], "事业部": ["检测"],
            "日期": ["2026-06-01"], "是否为广东公司": ["是"], "是否为深圳公司": [""]
        })
        result = standardize_output(df)
        assert list(result.columns) == ["事业部", "金额", "客户", "日期", "是否为广东公司", "是否为深圳公司"]

    def test_adds_missing_columns(self):
        df = pd.DataFrame({"客户": ["A"]})
        result = standardize_output(df)
        for col in ["事业部", "金额", "客户", "日期", "是否为广东公司", "是否为深圳公司"]:
            assert col in result.columns


def test_log_step(capsys):
    log_step("源", "消息", "OK")
    captured = capsys.readouterr()
    assert "源" in captured.out
    assert "消息" in captured.out
