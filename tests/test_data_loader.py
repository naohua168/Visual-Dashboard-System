"""测试数据加载器"""
import pandas as pd
import pytest

from tests.conftest import BASE_DIR, has_sheets
from processors.data_loader import DashboardData, load_all


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
    assert isinstance(data.annual_income_targets, pd.DataFrame)
    assert isinstance(data.annual_payment_targets, pd.DataFrame)
    assert isinstance(data.quarterly_income_targets, pd.DataFrame)
    assert isinstance(data.quarterly_payment_targets, pd.DataFrame)
    assert isinstance(data.monthly_income_targets, pd.DataFrame)
    assert isinstance(data.monthly_payment_targets, pd.DataFrame)


def test_income_columns():
    data = load_all(BASE_DIR)
    expected = ["事业部", "金额", "客户", "法人主体", "日期"]
    for col in expected:
        assert col in data.income.columns, f"收入表缺少列: {col}"


def test_sales_income_has_sales_column():
    data = load_all(BASE_DIR)
    assert "销售" in data.sales_income.columns


def test_yearly_baseline_property():
    data = load_all(BASE_DIR)
    assert isinstance(data.has_yearly_baseline, bool)


def test_data_not_empty():
    data = load_all(BASE_DIR)
    assert len(data.income) > 0
    assert len(data.payment) > 0
