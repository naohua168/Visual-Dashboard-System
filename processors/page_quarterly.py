"""季度达成页 — 基于季度指标 + 季度实际数据

布局（参考月度达成页的年度达成风格）：
  [A] Hero大数字块 — 季度总目标 + 收入/回款进度条（可展开部门卡片）
  [B] 事业部完成度 — mini-rate 进度条×4部门（收入/回款双卡并排）
  [C] 客户矩阵表 — cell-bg实色填充, 收入/回款Tab切换
"""
from __future__ import annotations

import json

import pandas as pd

from .base import BaseRenderer, rate_cls, hero_rings_html
from .utils import fmt_wan, safe_float, extract_date_range, get_config_range, range_banner_html

DEPARTMENTS = ["检测", "信息", "能源", "海外"]
CURRENT_YEAR = 2026


class QuarterlyPage(BaseRenderer):
    page_id = "quarterly"
    nav_name = "季度达成"

    def render(self, data) -> str:
        # 直接使用清洗后的季度累计数据
        q_inc: pd.DataFrame | None = data.quarterly_income
        q_pay: pd.DataFrame | None = data.quarterly_payment

        if q_inc is None or q_inc.empty or q_pay is None or q_pay.empty:
            fallback_inc = data.income.copy()
            fallback_pay = data.payment.copy()
            q = 2
        else:
            q_inc = q_inc.copy(); q_pay = q_pay.copy()
            latest_date = pd.to_datetime(q_inc["日期"].max(), errors="coerce")
            q = int(latest_date.quarter) if pd.notna(latest_date) else 2
            fallback_inc = q_inc; fallback_pay = q_pay

        q_label = "本期"

        # 季度指标（客户×销售 → 按客户汇总）
        q_inc_tgt: pd.DataFrame = data.quarterly_income_targets.copy()
        q_pay_tgt: pd.DataFrame = data.quarterly_payment_targets.copy()
        q_inc_tgt_cust = q_inc_tgt.groupby("客户")[[d for d in DEPARTMENTS if d in q_inc_tgt.columns]].sum()
        q_pay_tgt_cust = q_pay_tgt.groupby("客户")[[d for d in DEPARTMENTS if d in q_pay_tgt.columns]].sum()

        # 清洗数据已有金额单位（元），直接 /10000 即可
        q_inc["金额_万"] = q_inc["金额"].apply(safe_float) / 10000.0
        q_pay["金额_万"] = q_pay["金额"].apply(safe_float) / 10000.0
        q_inc["月份"] = pd.to_datetime(q_inc["日期"], errors="coerce").dt.to_period("M").astype(str)
        q_pay["月份"] = pd.to_datetime(q_pay["日期"], errors="coerce").dt.to_period("M").astype(str)

        # 本季度起止月份
        qtr_range = get_config_range(self.base_dir, "季度累计筛选")
        try:
            q_start = int(qtr_range.split("~")[0].strip().split("-")[1])
            q_end = int(qtr_range.split("~")[1].strip().split("-")[1])
        except (IndexError, ValueError, AttributeError):
            q_start = (q - 1) * 3 + 1
            q_end = q_start + 2

        # ── 季度汇总 ──
        total_inc = float(q_inc["金额_万"].sum())
        total_pay = float(q_pay["金额_万"].sum())
        dept_inc = q_inc.groupby("事业部")["金额_万"].sum().to_dict()
        dept_pay = q_pay.groupby("事业部")["金额_万"].sum().to_dict()

        # ── 季度目标（按事业部汇总）──
        inc_tgt_total = sum(safe_float(q_inc_tgt[d].sum()) for d in DEPARTMENTS if d in q_inc_tgt.columns)
        pay_tgt_total = sum(safe_float(q_pay_tgt[d].sum()) for d in DEPARTMENTS if d in q_pay_tgt.columns)
        dept_inc_tgt = {d: safe_float(q_inc_tgt[d].sum()) for d in DEPARTMENTS if d in q_inc_tgt.columns}
        dept_pay_tgt = {d: safe_float(q_pay_tgt[d].sum()) for d in DEPARTMENTS if d in q_pay_tgt.columns}

        inc_totals = {d: safe_float(dept_inc.get(d, 0)) for d in DEPARTMENTS}
        pay_totals = {d: safe_float(dept_pay.get(d, 0)) for d in DEPARTMENTS}

        # 同比 vs 2024 同季度
        yoy_inc = None
        yoy_pay = None
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

        inc_rate = total_inc / inc_tgt_total if inc_tgt_total else 0
        pay_rate = total_pay / pay_tgt_total if pay_tgt_total else 0

        parts = []
        if qtr_range:
            parts.append(range_banner_html(qtr_range))

        # Hero：有目标 → 参考月度达成页样式
        yoy_period = f"{CURRENT_YEAR}年{q_start:02d}-{q_end:02d}月 vs 2024年{q_start:02d}-{q_end:02d}月"
        quarter_total_tgt = inc_tgt_total + pay_tgt_total
        toggle_js = (
            "document.getElementById('quarterly-dept-wrap').classList.toggle('hidden');"
            "this.classList.add('expanded')"
        )
        parts.append(hero_rings_html(
            total_inc, inc_tgt_total, total_pay, pay_tgt_total, toggle_js, "收入", "回款",
            inc_yoy=yoy_inc, pay_yoy=yoy_pay,
            yoy_period=yoy_period,
            total_tgt=quarter_total_tgt, total_label=f"{q_label}总指标",
            show_cust_sales=False,
        ))
        # 部门卡片
        parts.append(self._quarterly_dept_card(
            q_inc, q_pay, dept_inc_tgt, dept_pay_tgt, inc_totals, pay_totals, q_label
        ))
        # 客户矩阵
        parts.append(self._quarterly_cust_matrix(
            q_inc, q_pay, q_inc_tgt_cust, q_pay_tgt_cust
        ))
        date_range = extract_date_range(data.quarterly_income)
        return self.wrap_page("".join(parts), date_range)

    # ════════════════════════════════════════════════════════════
    # [B] 部门卡片 — mini-rate 双卡（收入/回款），初始 hidden
    # ════════════════════════════════════════════════════════════
    def _quarterly_dept_card(self, q_inc, q_pay,
                             dept_inc_tgt: dict, dept_pay_tgt: dict,
                             inc_totals: dict, pay_totals: dict,
                             q_label: str) -> str:
        return f"""<div class="hidden" id="quarterly-dept-wrap">
  <div class="cols-2">
    {self._q_one_metric(inc_totals, dept_inc_tgt, "收入", q_label)}
    {self._q_one_metric(pay_totals, dept_pay_tgt, "回款", q_label)}
  </div>
</div>"""

    def _q_one_metric(self, tot: dict, dept_tgt: dict, metric: str, q_label: str) -> str:
        total_act = sum(tot.get(d, 0) for d in DEPARTMENTS)
        total_tgt = sum(dept_tgt.get(d, 0) for d in DEPARTMENTS)
        total_rate = total_act / total_tgt if total_tgt else 0
        total_cls = rate_cls(total_rate)
        rows = ""
        for d in DEPARTMENTS:
            act = tot.get(d, 0)
            tgt = dept_tgt.get(d, 0)
            r = act / tgt if tgt else 0
            cls = rate_cls(r)
            rows += f"""<div class="mini-rate">
  <span style="width:48px;font-weight:600">{d}</span>
  <div class="bar"><div class="bar-fill {cls}" style="width:{min(r*100,100):.1f}%"><span class="bar-pct {cls}">{r*100:.1f}%</span></div></div>
  <span class="val">{fmt_wan(act)}</span>
  <span style="color:var(--text-muted);font-size:11px">/{fmt_wan(tgt)}</span>
</div>"""
        rows += f"""<div class="mini-rate" style="border-top:2px solid var(--border);padding-top:8px;margin-top:4px">
  <span style="width:48px;font-weight:700">合计</span>
  <div class="bar"><div class="bar-fill {total_cls}" style="width:{min(total_rate*100,100):.1f}%"><span class="bar-pct {total_cls}">{total_rate*100:.1f}%</span></div></div>
  <span class="val">{fmt_wan(total_act)}</span>
  <span style="color:var(--text-muted);font-size:11px">/{fmt_wan(total_tgt)}</span>
</div>"""
        return f"""<div class="card">
  <div class="card-title">{metric}完成度</div>
  {rows}
</div>"""

    # ════════════════════════════════════════════════════════════
    # [C] 客户矩阵表 — cell-bg 收入/回款 Tab
    # ════════════════════════════════════════════════════════════
    def _quarterly_cust_matrix(self, df_inc, df_pay,
                                inc_tgt_cust: pd.DataFrame,
                                pay_tgt_cust: pd.DataFrame) -> str:
        inc_table = self._build_q_matrix(df_inc, inc_tgt_cust, "收入")
        pay_table = self._build_q_matrix(df_pay, pay_tgt_cust, "回款")
        return f"""<div class="section-title sec-sky">客户季度达成 · 收入/回款（万元）</div>
<div class="cust-tabs">
  <span class="cust-tab active inc" onclick="document.getElementById('q-cust-inc').classList.remove('hidden');document.getElementById('q-cust-pay').classList.add('hidden');this.parentElement.querySelectorAll('.cust-tab').forEach(t=>t.classList.remove('active'));this.classList.add('active')">收入</span>
  <span class="cust-tab pay" onclick="document.getElementById('q-cust-inc').classList.add('hidden');document.getElementById('q-cust-pay').classList.remove('hidden');this.parentElement.querySelectorAll('.cust-tab').forEach(t=>t.classList.remove('active'));this.classList.add('active')">回款</span>
</div>
<div id="q-cust-inc">{inc_table}</div>
<div id="q-cust-pay" class="hidden">{pay_table}</div>"""

    def _build_q_matrix(self, df: pd.DataFrame, tgt_p: pd.DataFrame, label: str) -> str:
        """单指标矩阵 — 使用季度指标而非年度/4"""
        piv = df.pivot_table(index="客户", columns="事业部", values="金额_万", aggfunc="sum", fill_value=0)
        piv["合计"] = piv.sum(axis=1)
        tgt_p["合计"] = tgt_p.sum(axis=1)
        customers = [c for c in tgt_p.index if tgt_p.loc[c, "合计"] > 0]
        customers.sort(key=lambda c: tgt_p.loc[c, "合计"], reverse=True)
        if not customers:
            return '<div class="card"><p style="color:var(--text-muted);padding:20px;text-align:center">无季度目标数据</p></div>'

        def _cell(act, tgt_v, is_total_col=False):
            if tgt_v == 0:
                return '<td class="td-empty">—</td>'
            r = act / tgt_v
            pct_num = min(r * 100, 100)
            pct_label = f"{r*100:.0f}%"
            if r >= 1:
                pct_cls, fill_var = " achieved", "#22c55e"
            elif r >= 0.5:
                pct_cls, fill_var = "", "#fb923c"
            elif r > 0:
                pct_cls, fill_var = " low", "#fdba74"
            else:
                pct_cls, fill_var = "", "#f1f5f9"
            empty_cls = " is-empty" if r == 0 else ""
            total_cls = " is-total" if is_total_col else ""
            return (f'<td class="cell-bg{empty_cls}{total_cls}" style="--pct:{pct_num:.1f}%;--fill:{fill_var}">'
                    f'<div class="fill-bg"></div><div class="cell-text">'
                    f'<span class="cell-pct{pct_cls}">{pct_label}</span>'
                    f'<div class="cell-main"><span class="cell-compact">'
                    f'<span class="cell-act-val">{fmt_wan(act)}</span>'
                    f'<span class="sep">/</span>'
                    f'<span class="cell-tgt-val">{fmt_wan(tgt_v)}</span>'
                    f'</span></div></div></td>')

        cells = [f'<td class="td-name td-total">合计（{len(customers)}家）</td>']
        for d in DEPARTMENTS:
            a = sum(float(piv.loc[c, d]) for c in customers if c in piv.index and d in piv.columns) if customers else 0
            tg = sum(float(tgt_p.loc[c, d]) for c in customers if c in tgt_p.index and d in tgt_p.columns)
            cells.append(_cell(a, tg))
        imp_total = sum(float(piv.loc[c, "合计"]) for c in customers if c in piv.index)
        imp_tgt = sum(float(tgt_p.loc[c, "合计"]) for c in customers if c in tgt_p.index)
        cells.append(_cell(imp_total, imp_tgt, is_total_col=True))
        tr = f'<tr class="row-total">{"".join(cells)}</tr>'

        rows = ""
        for i, c in enumerate(customers):
            cs = [f'<td class="td-name"><span class="row-num">{i+1}</span>{c}</td>']
            for d in DEPARTMENTS:
                a = float(piv.loc[c, d]) if c in piv.index and d in piv.columns else 0
                tg = float(tgt_p.loc[c, d]) if c in tgt_p.index and d in tgt_p.columns else 0
                cs.append(_cell(a, tg))
            a_t = float(piv.loc[c, "合计"]) if c in piv.index else 0
            tg_t = float(tgt_p.loc[c, "合计"]) if c in tgt_p.index else 0
            cs.append(_cell(a_t, tg_t, is_total_col=True))
            rows += f'<tr class="row-data">{"".join(cs)}</tr>'

        h = (f'<tr><th class="th-name">客户</th>'
             + "".join(f"<th>{d}</th>" for d in DEPARTMENTS)
             + '<th class="th-name th-total">合计</th></tr>')
        return (f'<div class="table-wrap ann-matrix-wrap no-collapse">'
                f'<table class="ann-matrix"><thead>{h}</thead><tbody>{tr}{rows}</tbody></table>'
                f'</div>'
                f'<div style="font-size:11px;color:var(--text-muted);margin-top:6px">每格：百分比 / 实际金额 / 目标金额</div>')

