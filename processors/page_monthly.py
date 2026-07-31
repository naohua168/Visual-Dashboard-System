"""月度达成页 — 基于年度达成设计风格

布局（参考年度达成页）：
  [A] Hero大数字块 — 月度总目标 + 收入/回款进度条（可展开部门卡片）
  [B] 事业部完成度 — mini-rate 进度条×4部门
  [C] 客户矩阵表 — cell-bg实色填充, 收入/回款Tab切换
  [D] 月度趋势图 — (可选) 柱状图展示月度变化
"""
from __future__ import annotations

import json

import pandas as pd

from .base import BaseRenderer, rate_cls, hero_rings_html
from .utils import fmt_wan, safe_float, extract_date_range, get_config_range, range_banner_html

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

        # 月度目标（按事业部列求和）
        inc_tgt = sum(safe_float(df_inc_tgt[d].sum()) for d in DEPARTMENTS if d in df_inc_tgt.columns)
        pay_tgt = sum(safe_float(df_pay_tgt[d].sum()) for d in DEPARTMENTS if d in df_pay_tgt.columns)

        inc_r = latest_inc / inc_tgt if inc_tgt else 0
        pay_r = latest_pay / pay_tgt if pay_tgt else 0

        # 同比 (vs 年基线数据中最新的同月)
        yoy_inc = None
        yoy_pay = None
        yoy_label_inc = ""
        yoy_label_pay = ""
        cur_year = int(latest.split('-')[0]) if latest and "-" in latest else 2026
        cur_month = int(latest.split('-')[1]) if latest and "-" in latest else 1
        if data.yearly_income is not None and len(data.yearly_income):
            yi = data.yearly_income.copy()
            yi["月份"] = pd.to_datetime(yi["日期"], errors="coerce").dt.to_period("M").astype(str)
            # 取年基线中最新的年份的同月
            latest_year_in_yi = yi["月份"].str[:4].astype(int).max()
            if latest and "-" in latest:
                target_key = f"{latest_year_in_yi}-{latest.split('-')[1]}"
                prev_inc = float(yi[yi["月份"] == target_key]["金额"].sum()) / 10000.0
                if prev_inc > 0:
                    yoy_inc = (latest_inc - prev_inc) / prev_inc
                    yoy_label_inc = f"{cur_year}年{cur_month:02d}月 vs {latest_year_in_yi}年{cur_month:02d}月"
        if data.yearly_payment is not None and len(data.yearly_payment):
            yp = data.yearly_payment.copy()
            yp["月份"] = pd.to_datetime(yp["日期"], errors="coerce").dt.to_period("M").astype(str)
            latest_year_in_yp = yp["月份"].str[:4].astype(int).max()
            if latest and "-" in latest:
                target_key = f"{latest_year_in_yp}-{latest.split('-')[1]}"
                prev_pay = float(yp[yp["月份"] == target_key]["金额"].sum()) / 10000.0
                if prev_pay > 0:
                    yoy_pay = (latest_pay - prev_pay) / prev_pay
                    yoy_label_pay = f"{cur_year}年{cur_month:02d}月 vs {latest_year_in_yp}年{cur_month:02d}月"
        # 使用相同的基准标签
        yoy_period = yoy_label_inc or yoy_label_pay

        # 客户数/销售数（从销售拆分数据）
        inc_cust = pay_cust = inc_sales = pay_sales = 0
        if data.sales_income is not None and len(data.sales_income):
            si = data.sales_income.copy()
            si["月份"] = pd.to_datetime(si["日期"], errors="coerce").dt.to_period("M").astype(str)
            si_l = si[si["月份"] == latest]
            inc_cust = int(si_l["客户"].nunique()) if "客户" in si_l.columns else 0
            inc_sales = int(si_l["销售"].nunique()) if "销售" in si_l.columns else 0
        if data.sales_payment is not None and len(data.sales_payment):
            sp = data.sales_payment.copy()
            sp["月份"] = pd.to_datetime(sp["日期"], errors="coerce").dt.to_period("M").astype(str)
            sp_l = sp[sp["月份"] == latest]
            pay_cust = int(sp_l["客户"].nunique()) if "客户" in sp_l.columns else 0
            pay_sales = int(sp_l["销售"].nunique()) if "销售" in sp_l.columns else 0

        parts = []
        parts.append(self._hero_block(
            latest, inc_tgt, pay_tgt, latest_inc, latest_pay, inc_r, pay_r,
            yoy_inc=yoy_inc, yoy_pay=yoy_pay,
            inc_cust=inc_cust, pay_cust=pay_cust,
            inc_sales=inc_sales, pay_sales=pay_sales,
            yoy_period=yoy_period,
            show_cust_sales=False,
        ))
        parts.append(self._dept_monthly_card(df_inc, df_pay, df_inc_tgt, df_pay_tgt, latest))
        parts.append(self._customer_matrix(df_inc, df_pay, df_inc_tgt, df_pay_tgt))
        date_range = extract_date_range(data.income)
        # 月度数据范围（从配置文件读取）
        month_range = get_config_range(self.base_dir, "月度数据")
        banner = range_banner_html(month_range or date_range)
        return self.wrap_page(banner + "".join(parts), date_range)

    # ── [A] Hero 大数字块 ──────────────────────────
    def _hero_block(self, month, inc_tgt, pay_tgt, latest_inc, latest_pay, inc_r, pay_r,
                    yoy_inc=None, yoy_pay=None,
                    inc_cust=0, pay_cust=0, inc_sales=0, pay_sales=0,
                    yoy_period="", show_cust_sales=True) -> str:
        """月度 Hero — 信息丰富版：同比 + 差额（不含客户/销售）"""
        toggle_js = (
            "document.getElementById('monthly-dept-wrap').classList.toggle('hidden');"
            "this.classList.add('expanded')"
        )
        # 月度总指标 = 月度收入指标 + 月度回款指标
        month_total_tgt = inc_tgt + pay_tgt
        return hero_rings_html(
            latest_inc, inc_tgt, latest_pay, pay_tgt, toggle_js, "收入", "回款",
            inc_yoy=yoy_inc, pay_yoy=yoy_pay,
            inc_cust=inc_cust, pay_cust=pay_cust,
            inc_sales=inc_sales, pay_sales=pay_sales,
            yoy_period=yoy_period,
            total_tgt=month_total_tgt, total_label="月度总指标",
            show_cust_sales=show_cust_sales,
        )

    # ── [B] 事业部完成度 ────────────────────────────
    def _dept_monthly_card(self, df_inc, df_pay, df_inc_tgt, df_pay_tgt, month) -> str:
        """2 张部门卡（收入+回款）并排，初始 hidden 由 Hero 展开"""
        return f"""<div class="hidden" id="monthly-dept-wrap">
  <div class="cols-2">
    {self._one_metric(df_inc, df_inc_tgt, "收入", month)}
    {self._one_metric(df_pay, df_pay_tgt, "回款", month)}
  </div>
</div>"""

    def _one_metric(self, df, df_tgt, metric: str, month: str) -> str:
        """单指标部门卡（mini-rate × 4部门 + 合计）"""
        total_act = sum(float(df[df["事业部"] == d]["金额_万"].sum()) for d in DEPARTMENTS) if df is not None else 0
        total_tgt = sum(safe_float(df_tgt[d].sum()) for d in DEPARTMENTS if d in df_tgt.columns)
        total_rate = total_act / total_tgt if total_tgt else 0
        total_cls = rate_cls(total_rate)

        rows = ""
        for d in DEPARTMENTS:
            act = float(df[df["事业部"] == d]["金额_万"].sum()) if df is not None and "事业部" in df.columns else 0
            tgt = safe_float(df_tgt[d].sum()) if d in df_tgt.columns else 0
            r = act / tgt if tgt else 0
            cls = rate_cls(r)
            rows += f"""<div class="mini-rate">
  <span style="width:48px;font-weight:600">{d}</span>
  <div class="bar"><div class="bar-fill {cls}" style="width:{min(r*100,100):.1f}%"><span class="bar-pct {cls}">{r*100:.1f}%</span></div></div>
  <span class="val">{fmt_wan(act)}</span>
  <span style="color:var(--text-muted);font-size:11px">/{fmt_wan(tgt)}</span>
</div>"""

        # 合计行
        rows += f"""<div class="mini-rate" style="border-top:2px solid var(--border);padding-top:8px;margin-top:4px">
  <span style="width:48px;font-weight:700">合计</span>
  <div class="bar"><div class="bar-fill {total_cls}" style="width:{min(total_rate*100,100):.1f}%"><span class="bar-pct {total_cls}">{total_rate*100:.1f}%</span></div></div>
  <span class="val">{fmt_wan(total_act)}</span>
  <span style="color:var(--text-muted);font-size:11px">/{fmt_wan(total_tgt)}</span>
</div>"""
        return f"""<div class="card">
  <div class="card-title">{metric}完成度 · {month}</div>
  {rows}
</div>"""

    # ── [C] 客户矩阵表（cell-bg 风格，收入/回款 Tab） ──
    def _customer_matrix(self, df_inc, df_pay, df_inc_tgt, df_pay_tgt) -> str:
        """收入/回款 Tab 切换 · 目标/实际/达成率 cell-bg 风格"""
        inc_table = self._build_matrix(df_inc, df_inc_tgt, "收入")
        pay_table = self._build_matrix(df_pay, df_pay_tgt, "回款")

        return f"""<div class="section-title sec-sky">客户月度达成 · 收入/回款（万元）</div>
<div class="cust-tabs">
  <span class="cust-tab active inc" onclick="document.getElementById('monthly-cust-inc').classList.remove('hidden');document.getElementById('monthly-cust-pay').classList.add('hidden');this.parentElement.querySelectorAll('.cust-tab').forEach(t=>t.classList.remove('active'));this.classList.add('active')">收入</span>
  <span class="cust-tab pay" onclick="document.getElementById('monthly-cust-inc').classList.add('hidden');document.getElementById('monthly-cust-pay').classList.remove('hidden');this.parentElement.querySelectorAll('.cust-tab').forEach(t=>t.classList.remove('active'));this.classList.add('active')">回款</span>
</div>
<div id="monthly-cust-inc">{inc_table}</div>
<div id="monthly-cust-pay" class="hidden">{pay_table}</div>"""

    def _build_matrix(self, df, df_tgt, label: str) -> str:
        """单指标矩阵（cell-bg 实色填充 · 年度达成风格）"""
        tgt_p = df_tgt.groupby("客户")[[d for d in DEPARTMENTS if d in df_tgt.columns]].sum()
        tgt_p["合计"] = tgt_p.sum(axis=1)
        piv = df.pivot_table(index="客户", columns="事业部", values="金额_万", aggfunc="sum", fill_value=0)
        piv["合计"] = piv.sum(axis=1)
        customers = [c for c in tgt_p.index if tgt_p.loc[c, "合计"] > 0]
        customers.sort(key=lambda c: tgt_p.loc[c, "合计"], reverse=True)
        if not customers:
            return '<div class="card"><p style="color:var(--text-muted);padding:20px;text-align:center">无月度目标数据</p></div>'

        def _cell(act, tgt, is_total_col=False):
            """cell-bg 半透明数据条填充：左=百分比 / 右=完成+指标（合计列也按达成度显示条）"""
            if act == 0 and tgt == 0:
                return '<td class="td-empty">—</td>'
            r = act / tgt if tgt else 0
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
                    f'<span class="cell-tgt-val">{fmt_wan(tgt)}</span>'
                    f'</span></div></div></td>')

        # 合计行
        cells = [f'<td class="td-name td-total">合计（{len(customers)}家）</td>']
        for d in DEPARTMENTS:
            a = sum(float(piv.loc[c, d]) for c in customers if c in piv.index and d in piv.columns) if customers else 0
            tg = sum(float(tgt_p.loc[c, d]) for c in customers if c in tgt_p.index)
            cells.append(_cell(a, tg))
        imp_total = sum(float(piv.loc[c, "合计"]) for c in customers if c in piv.index)
        imp_tgt = sum(float(tgt_p.loc[c, "合计"]) for c in customers)
        cells.append(_cell(imp_total, imp_tgt, is_total_col=True))
        tr = f'<tr class="row-total">{"".join(cells)}</tr>'

        # 数据行
        rows = ""
        for i, c in enumerate(customers):
            cs = [f'<td class="td-name"><span class="row-num">{i+1}</span>{c}</td>']
            for d in DEPARTMENTS:
                a = float(piv.loc[c, d]) if c in piv.index and d in piv.columns else 0
                tg = float(tgt_p.loc[c, d]) if c in tgt_p.index else 0
                cs.append(_cell(a, tg))
            a_t = float(piv.loc[c, "合计"]) if c in piv.index else 0
            tg_t = float(tgt_p.loc[c, "合计"]) if c in tgt_p.index else 0
            cs.append(_cell(a_t, tg_t, is_total_col=True))
            rows += f'<tr class="row-data">{"".join(cs)}</tr>'

        h = f'<tr><th class="th-name">客户</th>' + "".join(f"<th>{d}</th>" for d in DEPARTMENTS) + '<th class="th-name th-total">合计</th></tr>'
        return (f'<div class="table-wrap ann-matrix-wrap no-collapse">'
                f'<table class="ann-matrix"><thead>{h}</thead><tbody>{tr}{rows}</tbody></table>'
                f'</div>'
                f'<div style="font-size:11px;color:var(--text-muted);margin-top:6px">每格：实际金额 / 目标金额 / 达成率</div>')
