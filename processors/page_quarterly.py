"""季度达成页 — 季度指标 + 部门卡 + 客户矩阵"""
from __future__ import annotations

import pandas as pd

from .base import BaseRenderer, hero_rings_html
from .utils import fmt_wan, safe_float, extract_date_range, get_config_range, range_banner_html
from .components import (
    cell_bg_html, cust_tab_bar, hidden_dept_card_wrapper, dept_card_html,
)

DEPARTMENTS = ["检测", "信息", "能源", "海外"]
CURRENT_YEAR = 2026


class QuarterlyPage(BaseRenderer):
    page_id = "quarterly"
    nav_name = "季度达成"

    def render(self, data) -> str:
        q_inc: pd.DataFrame | None = data.quarterly_income
        q_pay: pd.DataFrame | None = data.quarterly_payment

        if q_inc is None or q_inc.empty or q_pay is None or q_pay.empty:
            q_inc = data.income.copy()
            q_pay = data.payment.copy()

        q_inc = q_inc.copy(); q_pay = q_pay.copy()
        latest_date = pd.to_datetime(q_inc["日期"].max(), errors="coerce")
        q = int(latest_date.quarter) if pd.notna(latest_date) else 2

        q_inc_tgt = data.quarterly_income_targets.copy()
        q_pay_tgt = data.quarterly_payment_targets.copy()

        q_inc["金额_万"] = q_inc["金额"].apply(safe_float) / 10000.0
        q_pay["金额_万"] = q_pay["金额"].apply(safe_float) / 10000.0

        # 起止月份
        qtr_range = get_config_range(self.base_dir, "季度累计筛选")
        try:
            q_start = int(qtr_range.split("~")[0].strip().split("-")[1])
            q_end = int(qtr_range.split("~")[1].strip().split("-")[1])
        except (IndexError, ValueError, AttributeError):
            q_start = (q - 1) * 3 + 1
            q_end = q_start + 2

        total_inc = float(q_inc["金额_万"].sum())
        total_pay = float(q_pay["金额_万"].sum())
        inc_tgt_total = sum(safe_float(q_inc_tgt[d].sum()) for d in DEPARTMENTS if d in q_inc_tgt.columns)
        pay_tgt_total = sum(safe_float(q_pay_tgt[d].sum()) for d in DEPARTMENTS if d in q_pay_tgt.columns)

        # 同比 vs 2024 同季度
        yoy_inc = yoy_pay = None
        yoy_period = f"{CURRENT_YEAR}年{q_start:02d}-{q_end:02d}月 vs 2024年{q_start:02d}-{q_end:02d}月"
        if data.yearly_income is not None and len(data.yearly_income):
            yi = data.yearly_income.copy()
            yi["月"] = pd.to_datetime(yi["日期"], errors="coerce").dt.month
            prev_inc = float(yi[(yi["月"] >= q_start) & (yi["月"] <= q_end)]["金额"].sum()) / 10000.0
            if prev_inc > 0:
                yoy_inc = (total_inc - prev_inc) / prev_inc
        if data.yearly_payment is not None and len(data.yearly_payment):
            yp = data.yearly_payment.copy()
            yp["月"] = pd.to_datetime(yp["日期"], errors="coerce").dt.month
            prev_pay = float(yp[(yp["月"] >= q_start) & (yp["月"] <= q_end)]["金额"].sum()) / 10000.0
            if prev_pay > 0:
                yoy_pay = (total_pay - prev_pay) / prev_pay

        parts = []
        if qtr_range:
            parts.append(range_banner_html(qtr_range))

        toggle_js = (
            "document.getElementById('quarterly-dept-wrap').classList.toggle('hidden');"
            "this.classList.add('expanded')"
        )
        parts.append(hero_rings_html(
            total_inc, inc_tgt_total, total_pay, pay_tgt_total,
            toggle_js, "收入", "回款",
            inc_yoy=yoy_inc, pay_yoy=yoy_pay,
            yoy_period=yoy_period,
            total_tgt=None, total_label="",
            show_cust_sales=False,
        ))

        parts.append(hidden_dept_card_wrapper(
            dept_card_html(q_inc, q_inc_tgt, DEPARTMENTS, "收入", f" · 第{q}季度")
            + dept_card_html(q_pay, q_pay_tgt, DEPARTMENTS, "回款", f" · 第{q}季度"),
            "quarterly-dept-wrap"
        ))

        # 客户矩阵
        q_inc_tgt_cust = q_inc_tgt.groupby("客户")[[d for d in DEPARTMENTS if d in q_inc_tgt.columns]].sum()
        q_pay_tgt_cust = q_pay_tgt.groupby("客户")[[d for d in DEPARTMENTS if d in q_pay_tgt.columns]].sum()
        inc_table = self._build_q_matrix(q_inc, q_inc_tgt_cust)
        pay_table = self._build_q_matrix(q_pay, q_pay_tgt_cust)
        parts.append(
            f'<div class="section-title sec-sky">客户季度达成 · 收入/回款（万元）</div>'
            + cust_tab_bar("q-cust-inc", "q-cust-pay")
            + f'<div id="q-cust-inc">{inc_table}</div>'
            f'<div id="q-cust-pay" class="hidden">{pay_table}</div>'
        )

        return self.wrap_page("".join(parts), extract_date_range(data.quarterly_income))

    def _build_q_matrix(self, df: pd.DataFrame, tgt_p: pd.DataFrame) -> str:
        """单指标客户矩阵（季度指标）"""
        piv = df.pivot_table(index="客户", columns="事业部", values="金额_万", aggfunc="sum", fill_value=0)
        piv["合计"] = piv.sum(axis=1)
        tgt_p["合计"] = tgt_p.sum(axis=1)

        customers = [c for c in tgt_p.index if tgt_p.loc[c, "合计"] > 0]
        customers.sort(key=lambda c: tgt_p.loc[c, "合计"], reverse=True)
        if not customers:
            return '<div class="card"><p style="color:var(--text-muted);padding:20px;text-align:center">无季度目标数据</p></div>'

        h = '<tr><th class="th-name">客户</th>' + "".join(
            f"<th>{d}</th>" for d in DEPARTMENTS
        ) + '<th class="th-name th-total">合计</th></tr>'

        # 合计行
        tc = [f'<td class="td-name td-total">合计（{len(customers)}家）</td>']
        for d in DEPARTMENTS:
            a = sum(float(piv.loc[c, d]) for c in customers
                    if c in piv.index and d in piv.columns) if customers else 0
            tg = sum(float(tgt_p.loc[c, d]) for c in customers
                     if c in tgt_p.index and d in tgt_p.columns)
            tc.append(cell_bg_html(a, tg))
        imp_total = sum(float(piv.loc[c, "合计"]) for c in customers if c in piv.index)
        imp_tgt = sum(float(tgt_p.loc[c, "合计"]) for c in customers if c in tgt_p.index)
        tc.append(cell_bg_html(imp_total, imp_tgt, is_total_col=True))
        tr = f'<tr class="row-total">{"".join(tc)}</tr>'

        rows = ""
        for i, c in enumerate(customers):
            cs = [f'<td class="td-name"><span class="row-num">{i+1}</span>{c}</td>']
            for d in DEPARTMENTS:
                a = float(piv.loc[c, d]) if c in piv.index and d in piv.columns else 0
                tg = float(tgt_p.loc[c, d]) if c in tgt_p.index and d in tgt_p.columns else 0
                cs.append(cell_bg_html(a, tg))
            a_t = float(piv.loc[c, "合计"]) if c in piv.index else 0
            tg_t = float(tgt_p.loc[c, "合计"]) if c in tgt_p.index else 0
            cs.append(cell_bg_html(a_t, tg_t, is_total_col=True))
            rows += f'<tr class="row-data">{"".join(cs)}</tr>'

        return (
            f'<div class="table-wrap ann-matrix-wrap no-collapse">'
            f'<table class="ann-matrix"><thead>{h}</thead><tbody>{tr}{rows}</tbody></table>'
            f'</div>'
            f'<div style="font-size:11px;color:var(--text-muted);margin-top:6px">'
            f'每格：百分比 / 实际金额 / 目标金额</div>'
        )
