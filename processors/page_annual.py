"""年度达成页 — Hero + 部门卡 + 客户矩阵（纯视图层）
"""
from __future__ import annotations

from .base import BaseRenderer, hero_rings_html
from .utils import fmt_wan, range_banner_html
from .components import (
    cell_bg_html, cust_tab_bar, hidden_dept_card_wrapper, dept_card_html,
)
from .page_data import prepare_annual_data, DEPARTMENTS


class AnnualPage(BaseRenderer):
    page_id = "annual"
    nav_name = "年度达成"

    def render(self, data) -> str:
        d = prepare_annual_data(data, self.base_dir)

        toggle_js = (
            "document.getElementById('annual-dept-wrap').classList.toggle('hidden');"
            "this.classList.add('expanded')"
        )
        hero = hero_rings_html(
            d.t_inc, d.t_inc_tgt, d.t_pay, d.t_pay_tgt, toggle_js, "收入", "回款",
            inc_yoy=d.yoy_inc, pay_yoy=d.yoy_pay, yoy_period=d.yoy_period,
            total_tgt=None, total_label="", show_cust_sales=False,
        )

        dept_cards = hidden_dept_card_wrapper(
            dept_card_html(d.df_inc, d.inc_tgt_df, DEPARTMENTS, "收入", " · 年度目标")
            + dept_card_html(d.df_pay, d.pay_tgt_df, DEPARTMENTS, "回款", " · 年度目标"),
            "annual-dept-wrap"
        )

        inc_table = self._build_matrix(d.inc_piv, d.inc_tgt_grouped, d.inc_customers, d.t_inc)
        pay_table = self._build_matrix(d.pay_piv, d.pay_tgt_grouped, d.pay_customers, d.t_pay)
        matrix = (
            f'<div class="section-title sec-sky">重要客户年度达成 · 收入/回款（万元）</div>'
            + cust_tab_bar("annual-cust-inc", "annual-cust-pay")
            + f'<div id="annual-cust-inc">{inc_table}</div>'
            f'<div id="annual-cust-pay" class="hidden">{pay_table}</div>'
        )

        return self.wrap_page(
            range_banner_html(d.annual_range) + hero + dept_cards + matrix, d.date_range
        )

    def _build_matrix(self, piv, tgt_grouped, customers, t_all) -> str:
        """纯 HTML 生成 — 接收已 pivoted 的 DataFrame"""
        h = f'<tr><th class="th-name">客户（{len(customers)}家）</th>' + "".join(
            f"<th>{d}</th>" for d in DEPARTMENTS
        ) + '<th class="th-name th-total">合计</th></tr>'

        # 横合计行
        tc = [f'<td class="td-name td-total">合计</td>']
        for d in DEPARTMENTS:
            a = sum(float(piv.loc[c, d]) for c in customers if c in piv.index and d in piv.columns) if customers else 0
            tg = sum(float(tgt_grouped.loc[c, d]) for c in customers if c in tgt_grouped.index)
            tc.append(cell_bg_html(a, tg))
        imp_total = sum(float(piv.loc[c, "合计"]) for c in customers if c in piv.index)
        imp_tgt = sum(float(tgt_grouped.loc[c, "合计"]) for c in customers if c in tgt_grouped.index)
        tc.append(cell_bg_html(imp_total, imp_tgt, is_total_col=True))
        tr = f'<tr class="row-total">{"".join(tc)}</tr>'

        rows = ""
        for i, c in enumerate(customers):
            cs = [f'<td class="td-name"><span class="row-num">{i+1}</span>{c}</td>']
            for d in DEPARTMENTS:
                a = float(piv.loc[c, d]) if c in piv.index and d in piv.columns else 0
                tg = float(tgt_grouped.loc[c, d]) if c in tgt_grouped.index else 0
                cs.append(cell_bg_html(a, tg))
            a_t = float(piv.loc[c, "合计"]) if c in piv.index else 0
            tg_t = float(tgt_grouped.loc[c, "合计"]) if c in tgt_grouped.index else 0
            cs.append(cell_bg_html(a_t, tg_t, is_total_col=True))
            rows += '<tr class="row-data">' + "".join(cs) + '</tr>'

        return (
            f'<div class="table-wrap ann-matrix-wrap no-collapse">'
            f'<table class="ann-matrix"><thead>{h}</thead><tbody>{tr}{rows}</tbody></table>'
            f'</div>'
            f'<div style="font-size:11px;color:var(--text-muted);margin-top:6px">'
            f'每格：百分比 / 实际金额 / 目标金额 · 全公司合计 '
            f'<strong style="color:var(--accent)">{fmt_wan(t_all)}</strong> 万</div>'
        )
