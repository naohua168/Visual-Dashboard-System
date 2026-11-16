# Author: naohua168 <bai_bai168@qq.com>
"""测试渲染页面模块 — 6 页看板"""
import json
import re

import pytest
from tests.conftest import BASE_DIR, has_sheets
from processors.data_loader import load_all
from processors.data_prep import prepare_overview_data
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


@pytest.fixture(scope="module")
def overview_html(shared_data):
    """总览页渲染结果（弹窗断言共用，module 级只渲染一次）"""
    page = OverviewPage()
    page.base_dir = BASE_DIR
    return page.render(shared_data)


class TestDeptDetailModal:
    """部门完成度矩阵 → 客户明细弹窗（点整行打开）"""

    def test_rows_are_clickable(self, overview_html):
        assert overview_html.count('class="dept-row"') == 4          # 4 个部门行
        # 每行同时挂 onclick 与 onkeydown（Enter/Space 打开），故 >= 4
        assert overview_html.count("openDeptDetail('") >= 4
        assert 'tabindex="0"' in overview_html

    def test_modal_skeleton(self, overview_html):
        for token in ('id="deptDetail"', 'id="ddBody"', 'id="ddFoot"', 'id="ddSearch"',
                      "dept-detail-table", "deptDetailFilter", "closeDeptDetail"):
            assert token in overview_html, f"弹窗骨架缺少 {token}"

    def test_inline_data_shape(self, overview_html):
        m = re.search(r"window\.DEPT_CUSTOMERS=(\{.*?\});</script>", overview_html, re.S)
        assert m, "缺少内联数据 window.DEPT_CUSTOMERS"
        data = json.loads(m.group(1))
        assert set(data) == {"检测", "信息", "能源", "海外"}
        with_subs = 0
        for dept, rows in data.items():
            assert rows, f"{dept} 没有客户行"
            for row in rows:
                # [客户, 收入实际, 收入指标, 回款实际, 回款指标] (+ 可选子公司明细)
                assert len(row) in (5, 6)
                assert isinstance(row[0], str) and row[0]
                if len(row) == 6:
                    subs = row[5]
                    assert subs and all(len(s) == 5 for s in subs)
                    with_subs += 1
        assert with_subs > 0, "没有任何客户带子公司明细（母公司入口会全部失效）"

    def test_dept_totals_match_matrix(self, overview_html, shared_data):
        """弹窗各行的加总 = 矩阵「实际」列（万元；逐行四舍五入带来的误差按 0.1% 容忍）"""
        d = prepare_overview_data(shared_data, BASE_DIR)
        data = json.loads(
            re.search(r"window\.DEPT_CUSTOMERS=(\{.*?\});</script>", overview_html, re.S).group(1)
        )
        for dept in ("检测", "信息", "能源", "海外"):
            inc = sum(r[1] for r in data[dept])
            pay = sum(r[3] for r in data[dept])
            assert inc == pytest.approx(d.dept_inc[dept], rel=0.001), f"{dept} 收入合计与矩阵不一致"
            assert pay == pytest.approx(d.dept_pay[dept], rel=0.001), f"{dept} 回款合计与矩阵不一致"
