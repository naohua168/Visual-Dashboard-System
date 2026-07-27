"""季度达成页 — 设计理念参照月度达成（月度达成借鉴年度达成风格）

布局（参考月度达成页的年度达成风格）：
  [A] Hero大数字块 — 季度总目标 + 收入/回款进度条（可展开部门卡片）
  [B] 事业部完成度 — mini-rate 进度条×4部门（收入/回款双卡并排）
  [C] 季度内月度趋势 — Chart.js 柱状图（本季各月收入/回款）
  [D] 客户矩阵表 — cell-bg实色填充, 收入/回款Tab切换
"""
from __future__ import annotations

import json

import pandas as pd

from .base import BaseRenderer, rate_cls
from .utils import fmt_wan, safe_float

DEPARTMENTS = ["检测", "信息", "能源", "海外"]
CURRENT_YEAR = 2026


class QuarterlyPage(BaseRenderer):
    page_id = "quarterly"
    nav_name = "季度达成"

    def render(self, data) -> str:
        # ── 确定本季度（依据最新季度累计数据中的日期）──
        q_inc: pd.DataFrame | None = data.quarterly_income
        q_pay: pd.DataFrame | None = data.quarterly_payment

        if q_inc is None or q_inc.empty or q_pay is None or q_pay.empty:
            # 季度数据不可用，用收入/回款按季度过滤替代
            fallback_inc = data.income.copy()
            fallback_pay = data.payment.copy()
            fallback_inc["金额_万"] = fallback_inc["金额"].apply(safe_float) / 10000.0
            fallback_pay["金额_万"] = fallback_pay["金额"].apply(safe_float) / 10000.0
            # 取当前季度（7月 → Q2）
            q = 2
        else:
            q_inc = q_inc.copy(); q_pay = q_pay.copy()
            q_inc["金额_万"] = q_inc["金额"].apply(safe_float) / 10000.0
            q_pay["金额_万"] = q_pay["金额"].apply(safe_float) / 10000.0
            # 从日期推导季度
            latest_date = pd.to_datetime(q_inc["日期"].max(), errors="coerce")
            if pd.isna(latest_date):
                q = 2
            else:
                q = latest_date.quarter
            fallback_inc = q_inc; fallback_pay = q_pay

        q_label = f"Q{q}"
        month_map = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}
        # 用当年累计数据计算（季度累计 = 当年累计截止当前季度末）
        # 但当年累计是全年的，所以过滤到本季度
        all_inc = data.income.copy()
        all_pay = data.payment.copy()
        all_inc["金额_万"] = all_inc["金额"].apply(safe_float) / 10000.0
        all_pay["金额_万"] = all_pay["金额"].apply(safe_float) / 10000.0
        all_inc["月份"] = pd.to_datetime(all_inc["日期"], errors="coerce").dt.to_period("M").astype(str)
        all_pay["月份"] = pd.to_datetime(all_pay["日期"], errors="coerce").dt.to_period("M").astype(str)

        # 本季度月份
        q_start = (q - 1) * 3 + 1
        q_months = [f"{CURRENT_YEAR}-{m:02d}" for m in range(q_start, q_start + 3)]
        q_inc_filtered = all_inc[all_inc["月份"].isin(q_months)]
        q_pay_filtered = all_pay[all_pay["月份"].isin(q_months)]

        # ── 季度汇总 ──
        if q_inc is not None and not q_inc.empty:
            total_inc = float(q_inc["金额_万"].sum())
            total_pay = float(q_pay["金额_万"].sum())
            dept_inc = q_inc.groupby("事业部")["金额_万"].sum().to_dict()
            dept_pay = q_pay.groupby("事业部")["金额_万"].sum().to_dict()
        else:
            total_inc = float(q_inc_filtered["金额_万"].sum())
            total_pay = float(q_pay_filtered["金额_万"].sum())
            dept_inc = q_inc_filtered.groupby("事业部")["金额_万"].sum().to_dict()
            dept_pay = q_pay_filtered.groupby("事业部")["金额_万"].sum().to_dict()

        # ── 季度目标 = 年目标 / 4 ──
        tgt_df = data.total_targets
        inc_tgt = sum(safe_float(tgt_df[d].sum()) for d in DEPARTMENTS if d in tgt_df.columns) / 4.0
        pay_tgt = inc_tgt
        # 事业部季度目标
        dept_tgt: dict[str, float] = {}
        for d in DEPARTMENTS:
            dept_tgt[d] = safe_float(tgt_df[d].sum()) / 4.0 if d in tgt_df.columns else 0.0

        inc_r = total_inc / inc_tgt if inc_tgt else 0
        pay_r = total_pay / pay_tgt if pay_tgt else 0

        # ── 事业部实际（用于卡片B）──
        inc_totals = {d: safe_float(dept_inc.get(d, 0)) for d in DEPARTMENTS}
        pay_totals = {d: safe_float(dept_pay.get(d, 0)) for d in DEPARTMENTS}

        parts = []
        parts.append(self._hero_block(q_label, inc_tgt, pay_tgt, total_inc, total_pay, inc_r, pay_r))
        parts.append(self._dept_card(q_inc_filtered, q_pay_filtered, dept_tgt, inc_totals, pay_totals, q_label))
        parts.append(self._trend_chart(q_inc_filtered, q_pay_filtered, q_label))
        parts.append(self._customer_matrix(q_inc_filtered, q_pay_filtered, tgt_df, dept_tgt, q_label))
        return self.wrap_page("".join(parts))

    # ════════════════════════════════════════════════════════════
    # [A] Hero 大数字块 — 季度总目标 + 收入/回款进度条
    # ════════════════════════════════════════════════════════════
    def _hero_block(self, q_label: str, inc_tgt: float, pay_tgt: float,
                    total_inc: float, total_pay: float, inc_r: float, pay_r: float) -> str:
        """季度总目标 Hero — 收入/回款条，点击展开部门卡片"""
        total_tgt = inc_tgt + pay_tgt
        toggle_js = (
            "document.getElementById('quarterly-dept-wrap').classList.toggle('hidden');"
            "this.parentElement.querySelectorAll('.annual-hero-bar').forEach(b=>b.classList.remove('expanded'));"
            "this.classList.add('expanded')"
        )
        return f"""<div class="annual-hero">
  <div class="annual-hero-label">📊 季度总目标 · {q_label}</div>
  <div class="annual-hero-value">{fmt_wan(total_tgt)}<span class="annual-hero-unit">万元</span></div>
  <div class="annual-hero-bars">
    <div class="annual-hero-bar" onclick="{toggle_js}" style="cursor:pointer">
      <span class="annual-hero-name">收入</span>
      <div class="annual-hero-track"><div class="annual-hero-fill inc" style="width:{min(inc_r*100,100):.1f}%">{inc_r*100:.1f}%</div></div>
      <span class="annual-hero-val">{fmt_wan(total_inc)} <span style="font-size:10px;font-weight:400;color:#94a3b8">/ {fmt_wan(inc_tgt)}</span></span>
      <span class="annual-hero-arrow">▸</span>
    </div>
    <div class="annual-hero-bar" onclick="{toggle_js}" style="cursor:pointer">
      <span class="annual-hero-name">回款</span>
      <div class="annual-hero-track"><div class="annual-hero-fill pay" style="width:{min(pay_r*100,100):.1f}%">{pay_r*100:.1f}%</div></div>
      <span class="annual-hero-val">{fmt_wan(total_pay)} <span style="font-size:10px;font-weight:400;color:#94a3b8">/ {fmt_wan(pay_tgt)}</span></span>
      <span class="annual-hero-arrow">▸</span>
    </div>
  </div>
</div>"""

    # ════════════════════════════════════════════════════════════
    # [B] 事业部完成度 — mini-rate 双卡（收入/回款）
    # ════════════════════════════════════════════════════════════
    def _dept_card(self, df_inc: pd.DataFrame, df_pay: pd.DataFrame,
                   dept_tgt: dict[str, float],
                   inc_totals: dict[str, float], pay_totals: dict[str, float],
                   q_label: str) -> str:
        """2 张部门卡（收入+回款）并排，初始 hidden 由 Hero 展开"""
        return f"""<div class="hidden" id="quarterly-dept-wrap">
  <div class="cols-2">
    {self._one_metric(inc_totals, dept_tgt, "收入", q_label)}
    {self._one_metric(pay_totals, dept_tgt, "回款", q_label)}
  </div>
</div>"""

    def _one_metric(self, tot: dict[str, float], dept_tgt: dict[str, float],
                    metric: str, q_label: str) -> str:
        """单指标部门卡（mini-rate × 4部门 + 合计）"""
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
  <div class="card-title">{metric}完成度 · {q_label}</div>
  {rows}
</div>"""

    # ════════════════════════════════════════════════════════════
    # [C] 季度内月度趋势 — Chart.js 柱状图
    # ════════════════════════════════════════════════════════════
    def _trend_chart(self, df_inc: pd.DataFrame, df_pay: pd.DataFrame, q_label: str) -> str:
        """本季度各月收入/回款柱状图"""
        mi = df_inc.groupby("月份")["金额_万"].sum()
        mp = df_pay.groupby("月份")["金额_万"].sum()
        all_m = sorted(set(list(mi.index) + list(mp.index)))
        iv = [round(float(mi.get(m, 0)), 2) for m in all_m]
        pv = [round(float(mp.get(m, 0)), 2) for m in all_m]

        if not all_m:
            return ""

        cid = "quarterlyTrend"
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
        return f"""<div class="chart-box"><div class="chart-title">{q_label} 月度收入/回款趋势（万元）</div>
<div style="height:200px;position:relative"><canvas id="{cid}"></canvas></div></div>
<script>
(function(){{ const e=document.getElementById('{cid}'); if(e) new Chart(e.getContext('2d'), {json.dumps(config, ensure_ascii=False)}); }})();
</script>"""

    # ════════════════════════════════════════════════════════════
    # [D] 客户矩阵表 — cell-bg 收入/回款 Tab
    # ════════════════════════════════════════════════════════════
    def _customer_matrix(self, df_inc: pd.DataFrame, df_pay: pd.DataFrame,
                         tgt_df: pd.DataFrame, dept_tgt: dict[str, float],
                         q_label: str) -> str:
        """收入/回款 Tab 切换 · 目标/实际/达成率 cell-bg 风格

        客户季度目标 = 年度总指标中该客户分部门目标 / 4
        """
        inc_table = self._build_matrix(df_inc, tgt_df, "收入")
        pay_table = self._build_matrix(df_pay, tgt_df, "回款")

        return f"""<div class="section-title sec-sky">{q_label} 客户达成 · 收入/回款（万元）</div>
<div class="cust-tabs">
  <span class="cust-tab active inc" onclick="document.getElementById('q-cust-inc').classList.remove('hidden');document.getElementById('q-cust-pay').classList.add('hidden');this.parentElement.querySelectorAll('.cust-tab').forEach(t=>t.classList.remove('active'));this.classList.add('active')">收入</span>
  <span class="cust-tab pay" onclick="document.getElementById('q-cust-inc').classList.add('hidden');document.getElementById('q-cust-pay').classList.remove('hidden');this.parentElement.querySelectorAll('.cust-tab').forEach(t=>t.classList.remove('active'));this.classList.add('active')">回款</span>
</div>
<div id="q-cust-inc">{inc_table}</div>
<div id="q-cust-pay" class="hidden">{pay_table}</div>"""

    def _build_matrix(self, df: pd.DataFrame, tgt_df: pd.DataFrame, label: str) -> str:
        """单指标矩阵（cell-bg 实色填充 · 年度达成风格）

        从总指标中提取客户级的季度目标（年 / 4）。
        """
        # 客户季度目标 = 总指标中按客户汇总的部门目标 / 4
        tgt_p = tgt_df.groupby("客户")[[d for d in DEPARTMENTS if d in tgt_df.columns]].sum() / 4.0
        tgt_p["合计"] = tgt_p.sum(axis=1)

        # 实际数据透视
        piv = df.pivot_table(index="客户", columns="事业部", values="金额_万", aggfunc="sum", fill_value=0)
        piv["合计"] = piv.sum(axis=1)

        customers = [c for c in tgt_p.index if tgt_p.loc[c, "合计"] > 0]
        customers.sort(key=lambda c: tgt_p.loc[c, "合计"], reverse=True)
        if not customers:
            return '<div class="card"><p style="color:var(--text-muted);padding:20px;text-align:center">无季度目标数据</p></div>'

        def _cell(act, tgt_v, is_total_col=False):
            """cell-bg 实色填充：左=百分比 / 右=完成+指标"""
            if act == 0 and tgt_v == 0:
                return '<td class="td-empty">—</td>'
            r = act / tgt_v if tgt_v else 0
            pct_num = min(r * 100, 100)
            pct_label = f"{r*100:.0f}%"
            pct_cls = " achieved" if r >= 1 else " low" if 0 < r < 0.5 else ""
            if is_total_col:
                return (f'<td class="cell-bg is-total"><div class="cell-text">'
                        f'<span class="cell-pct">{pct_label}</span>'
                        f'<div class="cell-main"><span class="cell-act">完成{fmt_wan(act)}</span>'
                        f'<span class="cell-tgt">指标{fmt_wan(tgt_v)}</span></div></div></td>')
            fill_var = "#22c55e" if r >= 1 else "#fb923c" if r >= 0.5 else "#fdba74" if r > 0 else "#f1f5f9"
            empty_cls = " is-empty" if r == 0 else ""
            return (f'<td class="cell-bg{empty_cls}" style="--pct:{pct_num:.1f}%;--fill:{fill_var}">'
                    f'<div class="fill-bg"></div><div class="cell-text">'
                    f'<span class="cell-pct{pct_cls}">{pct_label}</span>'
                    f'<div class="cell-main"><span class="cell-act">完成{fmt_wan(act)}</span>'
                    f'<span class="cell-tgt">指标{fmt_wan(tgt_v)}</span></div></div></td>')

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

        h = (f'<tr><th class="th-name">客户</th>'
             + "".join(f"<th>{d}</th>" for d in DEPARTMENTS)
             + '<th class="th-name th-total">合计</th></tr>')
        return (f'<div class="table-wrap ann-matrix-wrap no-collapse">'
                f'<table class="ann-matrix">{h}<tbody>{tr}{rows}</tbody></table>'
                f'</div>'
                f'<div style="font-size:11px;color:var(--text-muted);margin-top:6px">每格：百分比 / 实际金额 / 目标金额</div>')
