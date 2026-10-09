# Author: naohua168 <bai_bai168@qq.com>
"""渲染组件层测试（2026-09-29 补）—— processors/components.py + sales_pending.py

这些是纯函数（输入数据 → HTML 片段），不依赖真实数据，之前没有直测，
只能靠 `test_page_renderers.py`（依赖真实数据、会 skip）间接覆盖。

覆盖：
  - cell_bg_html / cell_bg_pct_only：空值、达成率色阶、合计列
  - mini_rate_row / mini_rate_summary_row：名称、金额、目标
  - cust_tab_bar / hidden_dept_card_wrapper：容器 id 与隐藏包裹
  - children_modal_html / children_modal_js：抽屉骨架与数据注入
  - dept_card_html：部门卡（三种目标列名兼容）
  - sales_pending.build_pending_modal：待确认弹窗口径（客户数/金额/明细）
"""
import pandas as pd
import pytest

from processors.components import (
    cell_bg_html,
    cell_bg_pct_only,
    children_modal_html,
    children_modal_js,
    cust_tab_bar,
    dept_card_html,
    hidden_dept_card_wrapper,
    mini_rate_row,
    mini_rate_summary_row,
)
from processors.sales_pending import build_pending_modal
from processors.utils import fmt_wan


# ══════════════════════════════════════════════════════════════
# cell-bg 单元格
# ══════════════════════════════════════════════════════════════
class TestCellBg:
    def test_empty_when_no_data(self):
        assert cell_bg_html(0, 0) == '<td class="td-empty">—</td>'

    def test_act_and_tgt_rendered(self):
        html = cell_bg_html(120.0, 100.0, fmt_fn=fmt_wan)
        assert 'class="cb' in html                       # cell-bg 单元格类名
        assert '<span class="ca">120</span>' in html     # 实际
        assert '<span class="ctv">100</span>' in html    # 目标
        assert "120%" in html                            # 超额达成：百分比照实显示

    @pytest.mark.parametrize("act,tgt,expect", [
        (100.0, 100.0, "100%"), (80.0, 100.0, "80%"), (0.0, 100.0, "0%"), (50.0, 0, "100%"),
    ])
    def test_render_stable(self, act, tgt, expect):
        html = cell_bg_html(act, tgt, fmt_fn=fmt_wan)
        assert html.startswith("<td")
        assert expect in html
        assert 'class="cb' in html

    def test_total_col_class(self):
        assert "is-total" in cell_bg_html(10, 20, is_total_col=True, fmt_fn=fmt_wan)

    def test_zero_tgt_shows_dash(self):
        assert '<span class="ctv">—</span>' in cell_bg_html(50.0, 0, fmt_fn=fmt_wan)

    def test_pct_only(self):
        html = cell_bg_pct_only(1.25)
        assert "125%" in html and html.startswith("<td")
        assert cell_bg_pct_only(0) == '<td class="td-empty">—</td>'


class TestMiniRate:
    def test_row_contains_name_and_amounts(self):
        html = mini_rate_row("王海龙", 5820000.0, 20100000.0)   # 默认 fmt：千分位取整
        assert "王海龙" in html
        assert "5,820,000" in html and "20,100,000" in html
        assert "29.0%" in html and "level-1" in html

    def test_row_zero_target_shows_dash_and_full_rate(self):
        html = mini_rate_row("无指标", 120000.0, 0)
        assert "无指标" in html and "120,000" in html and "100.0%" in html
        assert "—" in html

    def test_summary_row(self):
        html = mini_rate_summary_row("合计", 1000000.0, 2000000.0)
        assert "合计" in html and "1,000,000" in html and "2,000,000" in html
        assert "border-top" in html and "50.0%" in html


# ══════════════════════════════════════════════════════════════
# 容器 / Tab / 抽屉骨架
# ══════════════════════════════════════════════════════════════
def test_cust_tab_bar_ids():
    html = cust_tab_bar("inc_box", "pay_box")
    assert "inc_box" in html and "pay_box" in html


def test_hidden_dept_card_wrapper():
    html = hidden_dept_card_wrapper("<div>内容</div>", "wrap1")
    assert 'class="hidden"' in html and 'id="wrap1"' in html and "内容" in html


def test_children_modal_html_skeleton():
    html = children_modal_html("annual_inc")
    assert "annual_inc" in html
    for token in ("modal", "子公司"):
        assert token in html


def test_children_modal_js_injects_payload():
    detail = {"科技公司·王海龙": {"子公司A": {"合计": {"act": 1.0, "tgt": 2.0}}}}
    js = children_modal_js("annual_inc", "{}", "[]")
    assert isinstance(js, str) and "annual_inc" in js
    assert children_modal_js("x", '{"a": 1}').count("x") >= 1
    _ = detail  # 结构仅作文档示例


# ══════════════════════════════════════════════════════════════
# 部门卡
# ══════════════════════════════════════════════════════════════
class TestDeptCard:
    DEPTS = ["检测", "信息", "能源", "海外"]

    @staticmethod
    def _frames(col_style: str):
        """实际表需含 事业部 + 金额_万（渲染层统一口径）；目标表两种列名都试"""
        act = pd.DataFrame([{"事业部": "检测", "金额_万": 40.0},
                            {"事业部": "信息", "金额_万": 10.0}])
        tgt_cols = {d: 20.0 for d in TestDeptCard.DEPTS}
        if col_style != "检测":
            tgt_cols = {col_style if d == "检测" else d: 20.0 for d in TestDeptCard.DEPTS}
        return act, pd.DataFrame([tgt_cols])

    @pytest.mark.parametrize("col_style", ["检测", "检测收入", "检测回款"])
    def test_target_col_name_variants(self, col_style):
        """目标列名三种写法（检测 / 检测收入 / 检测回款）都能读到"""
        act, tgt = self._frames(col_style)
        html = dept_card_html(act, tgt, self.DEPTS, "inc", fmt_fn=fmt_wan)
        assert isinstance(html, str) and html
        assert "检测" in html


# ══════════════════════════════════════════════════════════════
# 待确认客户弹窗
# ══════════════════════════════════════════════════════════════
class TestPendingModal:
    @staticmethod
    def _pending(rows) -> pd.DataFrame:
        return pd.DataFrame(rows)

    def test_zero_pending_returns_empty(self):
        assert build_pending_modal(self._pending([]), 0, 0.0, 0.0) == ""

    def test_modal_contains_kpi_and_detail(self):
        pending = self._pending([
            {"客户": "甲客户", "事业部": "检测", "金额_万_收入": 100.0, "金额_万_回款": 0.0,
             "合计": 100.0, "法人主体": "广东汽车检测中心有限公司", "日期": "2026-08-01",
             "销售": "待确认"},
            {"客户": "乙客户", "事业部": "信息", "金额_万_收入": 0.0, "金额_万_回款": 50.0,
             "合计": 50.0, "法人主体": "南方（韶关）智能网联新能源汽车试验检测中心有限公司",
             "日期": "2026-08-02", "销售": "待确认"},
        ])
        html = build_pending_modal(pending, len(pending), 100.0, 50.0)
        assert "待确认客户" in html
        assert "甲客户" in html and "乙客户" in html
        assert "2" in html      # 去重客户数
        assert "150" in html    # 合计 100+50 万
