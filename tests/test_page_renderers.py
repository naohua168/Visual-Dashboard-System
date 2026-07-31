"""测试渲染页面模块 — 6 页看板"""
from pathlib import Path
import pytest
from processors.data_loader import load_all
from processors.page_overview import OverviewPage
from processors.page_annual import AnnualPage
from processors.page_monthly import MonthlyPage
from processors.page_sales import SalesPage
from processors.page_yoy import YoyPage
from processors.page_quarterly import QuarterlyPage

BASE_DIR = Path(__file__).parent.parent

def has_sheets():
    sheets = BASE_DIR / "data" / "sheets"
    required = ["当年累计收入/当年累计收入.xlsx", "当年累计回款/当年累计回款.xlsx",
                "销售收入/销售收入.xlsx", "销售回款/销售回款.xlsx"]
    man = sheets / "手动维护"
    required_man = ["年度收入总指标", "月度收入指标", "月度回款指标"]
    return (all((sheets / r).exists() for r in required)
            and all(list((man / d).glob("*.xlsx")) for d in required_man))

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
        assert page.page_id == page_id
        assert page.nav_name == nav_name
        html = page.render(shared_data)
        assert isinstance(html, str) and len(html) > 0
