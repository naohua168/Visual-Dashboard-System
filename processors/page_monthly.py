"""月度达成页 — 月度目标 + 部门卡 + 客户矩阵"""
from __future__ import annotations

import pandas as pd

from .base import BaseRenderer, hero_rings_html
from .utils import fmt_wan, safe_float, extract_date_range, get_config_range, range_banner_html
from .components import (
    cell_bg_html, cust_tab_bar, hidden_dept_card_wrapper, dept_card_html,
)

DEPARTMENTS = ["检测", "信息", "能源", "海外"]


class MonthlyPage(BaseRenderer):
    page_id = "monthly"
    nav_name = "月度达成"

    def render(self, data) -> str:
        df_inc = data.income.copy()
        df_pay = data.payment.copy()
        df_inc_tgt = data.monthly_income_targets.copy()
        df_pay_tgt = data.monthly_payment_targets.copy()
        df_inc["金额_万"] = df_inc["金额"].apply(safe_float) / 10000.0
        df_pay["金额_万"] = df_pay["金额"].apply(safe_float) / 10000.0
        df_inc["月份"] = pd.to_datetime(df_inc["日期"], errors="coerce").dt.to_period("M").astype(str)
        df_pay["月份"] = pd.to_datetime(df_pay["日期"], errors="coerce").dt.to_period("M").astype(str)

        months = sorted(df_inc["月份"].dropna().unique())
        latest = months[-1] if months else "—"
        latest_inc = float(df_inc[df_inc["月份"] == latest]["金额_万"].sum())
        latest_pay = float(df_pay[df_pay["月份"] == latest]["金额_万"].sum())

        inc_tgt = sum(safe_float(df_inc_tgt[d].sum()) for d in DEPARTMENTS if d in df_inc_tgt.columns)
        pay_tgt = sum(safe_float(df_pay_tgt[d].sum()) for d in DEPARTMENTS if d in df_pay_tgt.columns)

        # 同比 vs 年基线同月
        yoy_inc = yoy_pay = None
        yoy_period = ""
        cur_year = int(latest.split('-')[0]) if latest and "-" in latest else 2026
        cur_month = int(latest.split('-')[1]) if latest and "-" in latest else 1
        yoy_period = f"{cur_year}年{cur_month:02d}月 vs 2024年{cur_month:02d}月"
        if data.yearly_income is not None and len(data.yearly_income):
            yi = data.yearly_income.copy()
            yi["月份"] = pd.to_datetime(yi["日期"], errors="coerce").dt.to_period("M").astype(str)
            latest_year = yi["月份"].str[:4].astype(int).max()
            target_key = f"{latest_year}-{latest.split('-')[1]}" if latest and "-" in latest else ""
            prev_inc = float(yi[yi["月份"] == target_key]["金额"].sum()) / 10000.0 if target_key else 0
            if prev_inc > 0:
                yoy_inc = (latest_inc - prev_inc) / prev_inc
        if data.yearly_payment is not None and len(data.yearly_payment):
            yp = data.yearly_payment.copy()
            yp["月份"] = pd.to_datetime(yp["日期"], errors="coerce").dt.to_period("M").astype(str)
            latest_year = yp["月份"].str[:4].astype(int).max()
            target_key = f"{latest_year}-{latest.split('-')[1]}" if latest and "-" in latest else ""
            prev_pay = float(yp[yp["月份"] == target_key]["金额"].sum()) / 10000.0 if target_key else 0
            if prev_pay > 0:
                yoy_pay = (latest_pay - prev_pay) / prev_pay

        toggle_js = (
            "document.getElementById('monthly-dept-wrap').classList.toggle('hidden');"
            "this.classList.add('expanded')"
        )
        hero = hero_rings_html(
            latest_inc, inc_tgt, latest_pay, pay_tgt, toggle_js, "收入", "回款",
            inc_yoy=yoy_inc, pay_yoy=yoy_pay,
            yoy_period=yoy_period,
            total_tgt=None, total_label="",
            show_cust_sales=False,
        )

        dept_cards = hidden_dept_card_wrapper(
            dept_card_html(df_inc, df_inc_tgt, DEPARTMENTS, "收入",
                           f" · {latest}月")
            + dept_card_html(df_pay, df_pay_tgt, DEPARTMENTS, "回款",
                             f" · {latest}月"),
            "monthly-dept-wrap"
        )

        # 客户矩阵
        inc_table = self._build_matrix(df_inc, df_inc_tgt)
        pay_table = self._build_matrix(df_pay, df_pay_tgt)
        matrix = (
            f'<div class="section-title sec-sky">客户月度达成 · 收入/回款（万元）</div>'
            + cust_tab_bar("monthly-cust-inc", "monthly-cust-pay")
            + f'<div id="monthly-cust-inc">{inc_table}</div>'
            f'<div id="monthly-cust-pay" class="hidden">{pay_table}</div>'
        )

        date_range = extract_date_range(data.income)
        month_range = get_config_range(self.base_dir, "月度数据")
        return self.wrap_page(
            range_banner_html(month_range or date_range) + hero + dept_cards + matrix,
            date_range
        )

    def _build_matrix(self, df, df_tgt) -> str:
        """单指标客户矩阵（cell-bg 实色填充）"""
        tgt_p = df_tgt.groupby("客户")[[d for d in DEPARTMENTS if d in df_tgt.columns]].sum()
        tgt_p["合计"] = tgt_p.sum(axis=1)
        piv = df.pivot_table(index="客户", columns="事业部", values="金额_万", aggfunc="sum", fill_value=0)
        piv["合计"] = piv.sum(axis=1)

        customers = [c for c in tgt_p.index if tgt_p.loc[c, "合计"] > 0]
        customers.sort(key=lambda c: tgt_p.loc[c, "合计"], reverse=True)
        if not customers:
            return '<div class="card"><p style="color:var(--text-muted);padding:20px;text-align:center">无月度目标数据</p></div>'

        h = '<tr><th class="th-name">客户</th>' + "".join(
            f"<th>{d}</th>" for d in DEPARTMENTS
        ) + '<th class="th-name th-total">合计</th></tr>'

        # 合计行
        tc = [f'<td class="td-name td-total">合计（{len(customers)}家）</td>']
        for d in DEPARTMENTS:
            a = sum(float(piv.loc[c, d]) for c in customers
                    if c in piv.index and d in piv.columns) if customers else 0
            tg = sum(float(tgt_p.loc[c, d]) for c in customers if c in tgt_p.index)
            tc.append(cell_bg_html(a, tg))
        imp_total = sum(float(piv.loc[c, "合计"]) for c in customers if c in piv.index)
        imp_tgt = sum(float(tgt_p.loc[c, "合计"]) for c in customers)
        tc.append(cell_bg_html(imp_total, imp_tgt, is_total_col=True))
        tr = f'<tr class="row-total">{"".join(tc)}</tr>'

        # 数据行
        rows = ""
        for i, c in enumerate(customers):
            cs = [f'<td class="td-name"><span class="row-num">{i+1}</span>{c}</td>']
            for d in DEPARTMENTS:
                a = float(piv.loc[c, d]) if c in piv.index and d in piv.columns else 0
                tg = float(tgt_p.loc[c, d]) if c in tgt_p.index else 0
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
