"""测试渲染页面模块 — 6 页看板"""
import pytest
from tests.conftest import BASE_DIR, has_sheets
from processors.data_loader import load_all
from processors.page_overview import OverviewPage
from processors.page_annual import AnnualPage
from processors.page_monthly import MonthlyPage
from processors.page_sales import SalesPage
from processors.page_yoy import YoyPage
from processors.page_quarterly import QuarterlyPage


pytestmark = pytest.mark.skipif(not has_sheets(), reason="data/sheets/ data incomplete")

PAGE_CLASSES = [
    (OverviewPage, "overview", "数据总览"),
    (AnnualPage, "annual", "年度达成"),
    (MonthlyPage, "monthly", "月度达成"),
    (SalesPage, "sales", "销售达成"),
    (YoyPage, "yoy", "年度同比"),
    (QuarterlyPage, "quarterly", "季度达成"),
]


class TestPageIds:
    def test_all_ids_unique(self):
        ids = [c.page_id for c, _, _ in PAGE_CLASSES]
        assert len(ids) == len(set(ids))


@pytest.fixture(scope="module")
def shared_data():
    return load_all(BASE_DIR)


class TestPageRender:
    @pytest.mark.parametrize("cls,page_id,nav_name", PAGE_CLASSES)
    def test_page_renders_html(self, shared_data, cls, page_id, nav_name):
        page = cls()
        page.base_dir = BASE_DIR  # 与 processors/run.py 生产用法一致
        assert page.page_id == page_id
        assert page.nav_name == nav_name
        html = page.render(shared_data)
        assert isinstance(html, str) and len(html) > 0
