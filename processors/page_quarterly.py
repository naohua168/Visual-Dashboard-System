"""季度达成页 — Hero + 部门卡 + 客户矩阵（纯视图层）
"""
from __future__ import annotations

from .base import BaseRenderer, hero_rings_html
from .utils import fmt_wan, range_banner_html
from .components import (
    cell_bg_html, cust_tab_bar, hidden_dept_card_wrapper, dept_card_html,
    children_modal_html, children_modal_js,
)
from .page_data import prepare_quarterly_data, DEPARTMENTS


class QuarterlyPage(BaseRenderer):
    page_id = "quarterly"
    nav_name = "季度达成"

    def render(self, data) -> str:
        d = prepare_quarterly_data(data, self.base_dir)

        parts = []
        if d.qtr_range:
            parts.append(range_banner_html(d.qtr_range))

        toggle_js = (
            "document.getElementById('quarterly-dept-wrap').classList.toggle('hidden');"
            "this.classList.add('expanded')"
        )
        parts.append(hero_rings_html(
            d.total_inc, d.inc_tgt_total, d.total_pay, d.pay_tgt_total,
            toggle_js, "收入", "回款",
            inc_yoy=d.yoy_inc, pay_yoy=d.yoy_pay, yoy_period=d.yoy_period,
            total_tgt=None, total_label="", show_cust_sales=False,
        ))

        parts.append(hidden_dept_card_wrapper(
            dept_card_html(d.df_inc, d.inc_tgt_df, DEPARTMENTS, "收入", f" · 第{d.quarter}季度")
            + dept_card_html(d.df_pay, d.pay_tgt_df, DEPARTMENTS, "回款", f" · 第{d.quarter}季度"),
            "quarterly-dept-wrap"
        ))

        inc_table = self._build_matrix(d.inc_piv, d.inc_tgt_grouped, d.inc_customers, d.inc_rest, tab="inc", subs_with_data=d.subs_with_data, subs_detail=d.subs_detail_inc)
        pay_table = self._build_matrix(d.pay_piv, d.pay_tgt_grouped, d.pay_customers, d.pay_rest, tab="pay", subs_with_data=d.subs_with_data, subs_detail=d.subs_detail_pay)
        parts.append(
            f'<div class="section-title sec-sky">客户季度达成 · 收入/回款（万元）</div>'
            + cust_tab_bar("q-cust-inc", "q-cust-pay")
            + f'<div id="q-cust-inc">{inc_table}</div>'
            f'<div id="q-cust-pay" class="hidden">{pay_table}</div>'
        )

        return self.wrap_page("".join(parts), d.date_range)

    def _build_matrix(self, piv, tgt_grouped, customers, rest_customers=None, tab="inc", subs_with_data=None, subs_detail=None) -> str:
        """纯 HTML 生成，支持折叠其余客户 + 点击母公司看子公司。tab="inc"/"pay" 区分收入/回款独立 ID。"""
        if rest_customers is None:
            rest_customers = []
        if subs_with_data is None:
            subs_with_data = {}
        if subs_detail is None:
            subs_detail = {}
        all_custs = customers + rest_customers
        if not all_custs:
            return '<div class="card"><p style="color:var(--text-muted);padding:20px;text-align:center">无季度目标数据</p></div>'
        matrix_id = f"qtr-{tab}-matrix"
        toggle_id = f"qtr-{tab}-toggle"
        uid = f"qtr_{tab}"

        h = f'<tr><th class="th-name">客户（{len(all_custs)}家）</th>' + "".join(
            f"<th>{d}</th>" for d in DEPARTMENTS
        ) + '<th class="th-name th-total">合计</th></tr>'

        tc = [f'<td class="td-name td-total">合计</td>']
        for d in DEPARTMENTS:
            a = sum(float(piv.loc[c, d]) for c in all_custs if c in piv.index and d in piv.columns) if all_custs else 0
            tg = sum(float(tgt_grouped.loc[c, d]) for c in all_custs
                     if c in tgt_grouped.index and d in tgt_grouped.columns)
            tc.append(cell_bg_html(a, tg))
        imp_total = sum(float(piv.loc[c, "合计"]) for c in all_custs if c in piv.index)
        imp_tgt = sum(float(tgt_grouped.loc[c, "合计"]) for c in all_custs if c in tgt_grouped.index)
        tc.append(cell_bg_html(imp_total, imp_tgt, is_total_col=True))
        tr = f'<tr class="row-total">{"".join(tc)}</tr>'

        def _r(cust_list, start_idx, cls="row-data"):
            out = ""
            for i, c in enumerate(cust_list):
                subs_in_table = subs_with_data.get(c, [])
                if subs_in_table:
                    cust_html = (
                        f'<td class="td-name td-name-clickable" '
                        f'onclick="{uid}_show(this,\'{c}\')" '
                        f'title="点击查看 {len(subs_in_table)} 家子公司" '
                        f'style="cursor:pointer;color:var(--accent)">'
                        f'<span class="row-num">{start_idx+i+1}</span>{c} '
                        f'<span class="expand-hint">▾ {len(subs_in_table)}家</span></td>'
                    )
                else:
                    cust_html = f'<td class="td-name"><span class="row-num">{start_idx+i+1}</span>{c}</td>'
                cs = [cust_html]
                for d in DEPARTMENTS:
                    a = float(piv.loc[c, d]) if c in piv.index and d in piv.columns else 0
                    tg = float(tgt_grouped.loc[c, d]) if c in tgt_grouped.index and d in tgt_grouped.columns else 0
                    cs.append(cell_bg_html(a, tg))
                a_t = float(piv.loc[c, "合计"]) if c in piv.index else 0
                tg_t = float(tgt_grouped.loc[c, "合计"]) if c in tgt_grouped.index else 0
                cs.append(cell_bg_html(a_t, tg_t, is_total_col=True))
                out += f'<tr class="{cls}">{"".join(cs)}</tr>'
            return out

        rows = _r(customers, 0)
        rest_rows = _r(rest_customers, len(customers), "row-data row-hidden") if rest_customers else ""
        toggle_btn = ""
        if rest_customers:
            toggle_btn = (
                f'<tr class="row-toggle"><td colspan="{len(DEPARTMENTS)+2}" style="text-align:center;padding:8px">'
                f'<button class="toggle-all-btn" id="{toggle_id}" onclick="var t=document.querySelectorAll(\'#{matrix_id} .row-hidden\');var b=document.getElementById(\'{toggle_id}\');var isCollapsed=b.textContent.indexOf(\'查看\')>=0;t.forEach(r=>r.style.display=isCollapsed?\'table-row\':\'none\');b.textContent=isCollapsed?\'收起\':\'查看全部 ({len(rest_customers)}家)\';b.classList.toggle(\'expanded\',isCollapsed)">'
                f'查看全部 ({len(rest_customers)}家)</button></td></tr>'
            )

        # 弹窗数据：仅展示有数据的子公司
        import json
        sub_data = {p: subs_detail[p] for p in all_custs if p in subs_detail}
        sub_json = json.dumps(sub_data, ensure_ascii=False)

        return (
            f'<div class="table-wrap ann-matrix-wrap no-collapse" id="{matrix_id}">'
            f'<table class="ann-matrix"><thead>{h}</thead><tbody>{tr}{rows}{rest_rows}{toggle_btn}</tbody></table>'
            f'</div>'
            f'<div style="font-size:11px;color:var(--text-muted);margin-top:6px">'
            f'每格：百分比 / 实际金额 / 目标金额</div>'
            f'{children_modal_html(uid)}'
            f'{children_modal_js(uid, sub_json)}'
        )
