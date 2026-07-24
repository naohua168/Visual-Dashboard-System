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

from .base import BaseRenderer, rate_cls
from .utils import fmt_wan, safe_float

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

        parts = []
        parts.append(self._hero_block(latest, inc_tgt, pay_tgt, latest_inc, latest_pay, inc_r, pay_r))
        parts.append(self._dept_monthly_card(df_inc, df_pay, df_inc_tgt, df_pay_tgt, latest))
        parts.append(self._trend_chart(df_inc, df_pay))
        parts.append(self._customer_matrix(df_inc, df_pay, df_inc_tgt, df_pay_tgt))
        return self.wrap_page("".join(parts))

    # ── [A] Hero 大数字块 ──────────────────────────
    def _hero_block(self, month, inc_tgt, pay_tgt, latest_inc, latest_pay, inc_r, pay_r) -> str:
        """月度总目标 Hero — 收入/回款条可点击展开部门卡片"""
        total_tgt = inc_tgt + pay_tgt
        toggle_js = (
            "document.getElementById('monthly-dept-wrap').classList.toggle('hidden');"
            "this.parentElement.querySelectorAll('.annual-hero-bar').forEach(b=>b.classList.remove('expanded'));"
            "this.classList.add('expanded')"
        )
        return f"""<div class="annual-hero">
  <div class="annual-hero-label">📊 月度总目标 · {month}</div>
  <div class="annual-hero-value">{fmt_wan(total_tgt)}<span class="annual-hero-unit">万元</span></div>
  <div class="annual-hero-bars">
    <div class="annual-hero-bar" onclick="{toggle_js}" style="cursor:pointer">
      <span class="annual-hero-name">收入</span>
      <div class="annual-hero-track"><div class="annual-hero-fill inc" style="width:{min(inc_r*100,100):.1f}%">{inc_r*100:.1f}%</div></div>
      <span class="annual-hero-val">{fmt_wan(latest_inc)} <span style="font-size:10px;font-weight:400;color:#94a3b8">/ {fmt_wan(inc_tgt)}</span></span>
      <span class="annual-hero-arrow">▸</span>
    </div>
    <div class="annual-hero-bar" onclick="{toggle_js}" style="cursor:pointer">
      <span class="annual-hero-name">回款</span>
      <div class="annual-hero-track"><div class="annual-hero-fill pay" style="width:{min(pay_r*100,100):.1f}%">{pay_r*100:.1f}%</div></div>
      <span class="annual-hero-val">{fmt_wan(latest_pay)} <span style="font-size:10px;font-weight:400;color:#94a3b8">/ {fmt_wan(pay_tgt)}</span></span>
      <span class="annual-hero-arrow">▸</span>
    </div>
  </div>
</div>"""

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

    # ── [D] 月度趋势图 ──────────────────────────────
    def _trend_chart(self, df_inc, df_pay) -> str:
        """月度收入/回款柱状图（Chart.js）"""
        mi = df_inc.groupby("月份")["金额_万"].sum()
        mp = df_pay.groupby("月份")["金额_万"].sum()
        all_m = sorted(set(list(mi.index) + list(mp.index)))
        iv = [round(float(mi.get(m, 0)), 2) for m in all_m]
        pv = [round(float(mp.get(m, 0)), 2) for m in all_m]

        cid = "monthlyTrend"
        config = {
            "type": "bar", "data": {
                "labels": all_m,
                "datasets": [
                    {"label": "收入", "data": iv,
                     "backgroundColor": "#2563eb", "borderRadius": 4, "barPercentage": 0.6},
                    {"label": "回款", "data": pv,
                     "backgroundColor": "#f59e0b", "borderRadius": 4, "barPercentage": 0.6},
                ],
            },
            "options": {
                "responsive": True, "maintainAspectRatio": False,
                "interaction": {"mode": "index", "intersect": False},
                "plugins": {
                    "legend": {"position": "top", "labels": {"usePointStyle": True, "padding": 12}},
                    "tooltip": {
                        "callbacks": {
                            "label": "ctx => ctx.dataset.label + ': ' + ctx.parsed.y.toLocaleString('zh-CN',{minimumFractionDigits:2}) + ' 万元'"
                        }
                    },
                },
                "scales": {
                    "x": {"grid": {"display": False}},
                    "y": {
                        "beginAtZero": True, "grid": {"color": "rgba(148,163,184,0.15)"},
                        "ticks": {"callback": "v => v + '万'"},
                    },
                },
            },
        }
        return f"""<div class="chart-box"><div class="chart-title">月度收入/回款趋势（万元）</div>
<div style="height:200px;position:relative"><canvas id="{cid}"></canvas></div></div>
<script>
(function(){{ const e=document.getElementById('{cid}'); if(e) new Chart(e.getContext('2d'), {json.dumps(config, ensure_ascii=False)}); }})();
</script>"""

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
            """cell-bg 实色填充：左=百分比 / 右=完成+指标"""
            if act == 0 and tgt == 0:
                return '<td class="td-empty">—</td>'
            r = act / tgt if tgt else 0
            pct_num = min(r * 100, 100)
            pct_label = f"{r*100:.0f}%"
            pct_cls = " achieved" if r >= 1 else " low" if 0 < r < 0.5 else ""
            if is_total_col:
                return (f'<td class="cell-bg is-total"><div class="cell-text">'
                        f'<span class="cell-pct">{pct_label}</span>'
                        f'<div class="cell-main"><span class="cell-act">完成{fmt_wan(act)}</span>'
                        f'<span class="cell-tgt">指标{fmt_wan(tgt)}</span></div></div></td>')
            fill_var = "#22c55e" if r >= 1 else "#fb923c" if r >= 0.5 else "#fdba74" if r > 0 else "#f1f5f9"
            empty_cls = " is-empty" if r == 0 else ""
            return (f'<td class="cell-bg{empty_cls}" style="--pct:{pct_num:.1f}%;--fill:{fill_var}">'
                    f'<div class="fill-bg"></div><div class="cell-text">'
                    f'<span class="cell-pct{pct_cls}">{pct_label}</span>'
                    f'<div class="cell-main"><span class="cell-act">完成{fmt_wan(act)}</span>'
                    f'<span class="cell-tgt">指标{fmt_wan(tgt)}</span></div></div></td>')

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
                f'<table class="ann-matrix">{h}<tbody>{tr}{rows}</tbody></table>'
                f'</div>'
                f'<div style="font-size:11px;color:var(--text-muted);margin-top:6px">每格：实际金额 / 目标金额 / 达成率</div>')
