"""测试数据加载器"""
from pathlib import Path

import pandas as pd
import pytest

from processors.data_loader import DashboardData, load_all

BASE_DIR = Path(__file__).parent.parent


def has_sheets():
    sheets = BASE_DIR / "data" / "sheets"
    required = ["当年累计收入/当年累计收入.xlsx", "当年累计回款/当年累计回款.xlsx",
                "销售收入/销售收入.xlsx", "销售回款/销售回款.xlsx",
                "总指标/总指标.xlsx",
                "月度收入指标/月度收入指标.xlsx", "月度回款指标/月度回款指标.xlsx"]
    return all((sheets / r).exists() for r in required)


pytestmark = pytest.mark.skipif(not has_sheets(), reason="data/sheets/ 不完整")


def test_load_all_returns_dashboard_data():
    data = load_all(BASE_DIR)
    assert isinstance(data, DashboardData)


def test_data_has_required_dataframes():
    data = load_all(BASE_DIR)
    assert isinstance(data.income, pd.DataFrame)
    assert isinstance(data.payment, pd.DataFrame)
    assert isinstance(data.sales_income, pd.DataFrame)
    assert isinstance(data.sales_payment, pd.DataFrame)
    assert isinstance(data.total_targets, pd.DataFrame)
    assert isinstance(data.monthly_income_targets, pd.DataFrame)
    assert isinstance(data.monthly_payment_targets, pd.DataFrame)


def test_income_columns():
    data = load_all(BASE_DIR)
    expected = ["事业部", "金额", "客户", "日期", "是否为广东公司", "是否为深圳公司"]
    for col in expected:
        assert col in data.income.columns, f"收入表缺少列: {col}"


def test_sales_income_has_sales_column():
    data = load_all(BASE_DIR)
    assert "销售" in data.sales_income.columns


def test_yearly_baseline_property():
    data = load_all(BASE_DIR)
    # 年基线可能未就绪，但属性必须存在
    assert isinstance(data.has_yearly_baseline, bool)


def test_data_not_empty():
    data = load_all(BASE_DIR)
    assert len(data.income) > 0
    assert len(data.payment) > 0
