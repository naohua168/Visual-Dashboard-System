"""月累计明细页 — 月度累计可视化仪表盘

基于数据探索发现（2026-07-23）：
  - 月收入301行/69客户, 月回款245行/43客户
  - 收入16,642万, 回款27,890万（超收67.6%）
  - 检测占63%收入, 客户高度集中(TOP11贡献80%)

布局：
  [A] KPI卡片行 — 累计收入/回款/回款率/客户数/边际客户
  [B] 部分组柱状图 — 收入vs回款 × 4事业部
  [C] 客户帕累托双轴图 — 条形 + 累计占比折线
  [D] 客户明细表 — 排名/事业部/收入/回款/差额/回款率
"""
from __future__ import annotations

import json

import pandas as pd

from .base import BaseRenderer, rate_cls
from .utils import fmt_wan, safe_float

DEPARTMENTS = ["检测", "信息", "能源", "海外"]


class MonthlyCumulPage(BaseRenderer):
    page_id = "monthly_cumul"
    nav_name = "月累计明细"

    def render(self, data) -> str:
        df_mi = data.monthly_income_detail
        df_mp = data.monthly_payment_detail

        has_inc = df_mi is not None and len(df_mi) > 0
        has_pay = df_mp is not None and len(df_mp) > 0
        if not has_inc and not has_pay:
            return self.wrap_page(
                '<div class="card"><div class="card-title">暂无月累计数据</div>'
                '<p style="color:var(--text-muted)">月收入.xlsx / 月回款.xlsx 数据尚未生成。</p></div>'
            )

        # 预处理
        if has_inc:
            df_mi = df_mi.copy()
            df_mi["金额_万"] = df_mi["金额"].apply(safe_float) / 10000.0
            df_mi["月份"] = pd.to_datetime(df_mi["日期"], errors="coerce").dt.to_period("M").astype(str)
        if has_pay:
            df_mp = df_mp.copy()
            df_mp["金额_万"] = df_mp["金额"].apply(safe_float) / 10000.0
            df_mp["月份"] = pd.to_datetime(df_mp["日期"], errors="coerce").dt.to_period("M").astype(str)

        parts = []
        parts.append(self._kpi_row(df_mi if has_inc else None, df_mp if has_pay else None))
        parts.append(self._dept_chart(df_mi if has_inc else None, df_mp if has_pay else None))
        parts.append(self._pareto_chart(df_mi if has_inc else None, df_mp if has_pay else None))
        parts.append(self._detail_table(df_mi if has_inc else None, df_mp if has_pay else None))
        return self.wrap_page("".join(parts))

    # ── [A] KPI卡片行 ──────────────────────────────
    def _kpi_row(self, df_mi, df_mp) -> str:
        cumul_inc = float(df_mi["金额_万"].sum()) if df_mi is not None else 0
        cumul_pay = float(df_mp["金额_万"].sum()) if df_mp is not None else 0
        gap = cumul_pay - cumul_inc
        rate = cumul_pay / cumul_inc * 100 if cumul_inc else 0
        all_custs = set()
        if df_mi is not None:
            all_custs |= set(df_mi["客户"].astype(str).unique())
        if df_mp is not None:
            all_custs |= set(df_mp["客户"].astype(str).unique())
        # 仅有收入无回款的客户数（边际客户）
        inc_only = set(df_mi["客户"].astype(str).unique()) - set(df_mp["客户"].astype(str).unique()) if (df_mi is not None and df_mp is not None) else set()

        cards = [
            {"label": "月累计收入", "value": fmt_wan(cumul_inc), "sub": "万元", "cls": "kpi kpi-inc"},
            {"label": "月累计回款", "value": fmt_wan(cumul_pay), "sub": "万元", "cls": "kpi kpi-pay"},
            {"label": "回款率", "value": f"{rate:.1f}%",
             "sub": f"超收 {fmt_wan(gap)} 万", "cls": "kpi kpi-rate"},
            {"label": "覆盖客户", "value": f"{len(all_custs)}", "sub": f"回款 {len(set(df_mp['客户'].astype(str).unique()) if df_mp is not None else [])} 家",
             "cls": "kpi kpi-growth"},
            {"label": "收入独有客户", "value": f"{len(inc_only)}", "sub": "有收入无回款", "cls": "kpi kpi-tgt"},
        ]
        html_cards = "\n".join(
            f'<div class="{c["cls"]}"><div class="kpi-label">{c["label"]}</div>'
            f'<div class="kpi-value">{c["value"]}</div>'
            f'<div class="kpi-sub">{c["sub"]}</div></div>'
            for c in cards
        )
        return f'<div class="kpi-grid cols-9" style="grid-template-columns:repeat(5,1fr)">{html_cards}</div>'

    # ── [B] 部门分组柱状图 ──────────────────────────
    def _dept_chart(self, df_mi, df_mp) -> str:
        if df_mi is None or "事业部" not in df_mi.columns:
            return ""
        dept_i = df_mi.groupby("事业部")["金额_万"].sum().reindex(DEPARTMENTS, fill_value=0)
        dept_p = df_mp.groupby("事业部")["金额_万"].sum().reindex(DEPARTMENTS, fill_value=0)

        labels = DEPARTMENTS
        i_data = [round(float(dept_i.get(d, 0)), 2) for d in labels]
        p_data = [round(float(dept_p.get(d, 0)), 2) for d in labels]
        gaps = [round(p - i, 2) for i, p in zip(i_data, p_data)]
        gap_row = "".join(
            f'<span style="color:{"#059669" if g>=0 else "#dc2626"};font-weight:700;font-size:13px">{"+" if g>=0 else ""}{g:,.0f}万</span> '
            for g in gaps
        )

        chart_id = "cumulDeptChart"
        config = {
            "type": "bar",
            "data": {
                "labels": labels,
                "datasets": [
                    {"label": "收入", "data": i_data,
                     "backgroundColor": "#2563eb", "borderRadius": 4, "barPercentage": 0.35},
                    {"label": "回款", "data": p_data,
                     "backgroundColor": "#f59e0b", "borderRadius": 4, "barPercentage": 0.35},
                ],
            },
            "options": {
                "responsive": True, "maintainAspectRatio": False,
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
                        "ticks": {"callback": "v => v.toLocaleString('zh-CN',{maximumFractionDigits:0})"},
                        "title": {"display": True, "text": "万元"},
                    },
                },
            },
        }
        return f"""<div class="card">
  <div class="card-title">事业部月累计 · 收入 vs 回款</div>
  <div style="height:240px;position:relative"><canvas id="{chart_id}"></canvas></div>
  <div style="margin-top:8px;display:flex;justify-content:space-around;font-size:11px;color:var(--text-muted)">
    <span>差额: {gap_row}</span>
  </div>
</div>
<script>(function(){{ var e=document.getElementById('{chart_id}'); if(e) new Chart(e.getContext('2d'), {json.dumps(config, ensure_ascii=False)}); }})();</script>"""

    # ── [C] 客户帕累托双轴图 ────────────────────────
    def _pareto_chart(self, df_mi, df_mp) -> str:
        if df_mi is None:
            return ""
        cust_i = df_mi.groupby("客户")["金额_万"].sum().sort_values(ascending=False)
        total = float(cust_i.sum())
        top = cust_i.head(15)
        cum = top.cumsum() / total * 100
        pareto_n = int((cum <= 80).sum()) + 1
        pareto_pct = pareto_n / len(cust_i) * 100 if len(cust_i) else 0

        labels = [c[:10] + ("…" if len(c) > 10 else "") for c in top.index]
        values = [round(float(v), 2) for v in top.values]
        cums = [round(float(v), 2) for v in cum.values]
        gap_label = "收入(万元)"
        chart_id = "cumulPareto"
        config = {
            "type": "bar",
            "data": {
                "labels": labels,
                "datasets": [
                    {"label": gap_label, "data": values, "backgroundColor": "#2563eb",
                     "borderRadius": 3, "order": 2, "yAxisID": "y"},
                    {"type": "line", "label": "累计占比%", "data": cums,
                     "borderColor": "#dc2626", "backgroundColor": "#dc2626",
                     "pointRadius": 4, "pointBackgroundColor": "#dc2626",
                     "tension": 0.3, "order": 1, "yAxisID": "y1", "fill": False},
                ],
            },
            "options": {
                "responsive": True, "maintainAspectRatio": False,
                "plugins": {
                    "legend": {"position": "top", "labels": {"usePointStyle": True, "padding": 12}},
                    "tooltip": {"mode": "index", "intersect": False},
                },
                "scales": {
                    "x": {"grid": {"display": False}, "ticks": {"font": {"size": 10}}},
                    "y": {"position": "left", "beginAtZero": True, "grid": {"color": "rgba(148,163,184,0.15)"},
                          "ticks": {"callback": "v => v.toLocaleString('zh-CN',{maximumFractionDigits:0})"},
                          "title": {"display": True, "text": "收入(万元)"}},
                    "y1": {"position": "right", "min": 0, "max": 100,
                           "grid": {"drawOnChartArea": False},
                           "ticks": {"callback": "v => v.toFixed(0) + '%'"},
                           "title": {"display": True, "text": "累计占比%"}},
                },
            },
        }
        return self.section("客户收入集中度 · 帕累托分析", "sec-amber") + f"""
<div class="card" style="margin-top:8px">
  <div class="card-title">Top 15 客户 · {pareto_n}家贡献80%收入（占客户{pareto_pct:.1f}%）</div>
  <div style="height:{max(len(top)*24+40, 200)}px;position:relative"><canvas id="{chart_id}"></canvas></div>
</div>
<script>(function(){{ var e=document.getElementById('{chart_id}'); if(e) new Chart(e.getContext('2d'), {json.dumps(config, ensure_ascii=False)}); }})();</script>"""

    # ── [D] 客户明细表（cell-bg 风格） ────────────────
    def _detail_table(self, df_mi, df_mp) -> str:
        if df_mi is None:
            return ""
        # 聚合客户数据
        inc_s = df_mi.groupby("客户")["金额_万"].sum()
        pay_s = df_mp.groupby("客户")["金额_万"].sum() if df_mp is not None else pd.Series(dtype=float)
        # 事业部收入列
        dept_piv = df_mi.pivot_table(index="客户", columns="事业部", values="金额_万", aggfunc="sum", fill_value=0)
        for d in DEPARTMENTS:
            if d not in dept_piv.columns:
                dept_piv[d] = 0.0

        all_c = sorted(inc_s.index, key=lambda c: inc_s.get(c, 0), reverse=True)[:30]
        if not all_c:
            return ""

        thead = ("<tr><th>#</th><th>客户</th>"
                 + "".join(f"<th>{d}</th>" for d in DEPARTMENTS)
                 + "<th>累计收入</th><th>累计回款</th><th>差额</th><th>回款率</th></tr>")

        def _rate_hex(rate: float) -> str:
            if rate >= 120: return "#059669"
            if rate >= 95:  return "#16a34a"
            if rate >= 70:  return "#f59e0b"
            if rate >= 50:  return "#f97316"
            return "#dc2626"

        def _rate_class(rate: float) -> str:
            if rate >= 120: return "rate-high"
            if rate >= 95:  return "rate-ok"
            if rate >= 70:  return "rate-mid"
            return "rate-low"

        rows = ""
        for i, c in enumerate(all_c, 1):
            vi = float(inc_s.get(c, 0))
            vp = float(pay_s.get(c, 0))
            gap = vp - vi
            rate = vp / vi * 100 if vi > 0 else 0
            cls_rank = "rank-top" if i <= 3 else ""

            # 事业部格子
            dept_cells = ""
            for d in DEPARTMENTS:
                dv = float(dept_piv.loc[c, d]) if c in dept_piv.index else 0
                if dv > 0:
                    pct = dv / vi * 100 if vi else 0
                    dept_cells += f'<td style="text-align:center"><span style="font-weight:600">{fmt_wan(dv)}</span><br><span style="font-size:10px;color:var(--text-muted)">{pct:.0f}%</span></td>'
                else:
                    dept_cells += '<td style="text-align:center;color:#cbd5e1">—</td>'

            gap_color = "#059669" if gap >= 0 else "#dc2626"
            rate_hex = _rate_hex(rate)
            rate_cl = _rate_class(rate)
            rows += (
                f'<tr class="{cls_rank}">'
                f'<td><span class="rank rank-{i if i<=3 else "n"}">{i}</span></td>'
                f'<td style="text-align:left;font-weight:600">{c}</td>'
                f'{dept_cells}'
                f'<td style="font-weight:700">{fmt_wan(vi)}</td>'
                f'<td>{fmt_wan(vp)}</td>'
                f'<td style="color:{gap_color};font-weight:700">{"+" if gap>=0 else ""}{fmt_wan(gap)}</td>'
                f'<td><span class="rate-badge {rate_cl}" style="background:{rate_hex}22;color:{rate_hex}">{rate:.1f}%</span></td>'
                f'</tr>'
            )

        # 合计行
        t_inc = sum(float(inc_s.get(c, 0)) for c in all_c)
        t_pay = sum(float(pay_s.get(c, 0)) for c in all_c)
        t_gap = t_pay - t_inc
        t_rate = t_pay / t_inc * 100 if t_inc else 0
        t_rate_hex = _rate_hex(t_rate)
        t_rate_cl = _rate_class(t_rate)
        t_dept_cells = ""
        for d in DEPARTMENTS:
            dv = sum(float(dept_piv.loc[c, d]) for c in all_c if c in dept_piv.index)
            if dv > 0:
                pct = dv / t_inc * 100 if t_inc else 0
                t_dept_cells += f'<td style="text-align:center;font-weight:700">{fmt_wan(dv)}<br><span style="font-size:10px;color:var(--text-muted)">{pct:.0f}%</span></td>'
            else:
                t_dept_cells += '<td style="text-align:center;color:#cbd5e1">—</td>'
        total_row = (
            f'<tr class="total">'
            f'<td></td><td>合计（{len(all_c)}家）</td>'
            f'{t_dept_cells}'
            f'<td>{fmt_wan(t_inc)}</td><td>{fmt_wan(t_pay)}</td>'
            f'<td style="color:{"#059669" if t_gap>=0 else "#dc2626"};font-weight:700">{"+" if t_gap>=0 else ""}{fmt_wan(t_gap)}</td>'
            f'<td><span class="rate-badge {t_rate_cl}" style="background:{t_rate_hex}22;color:{t_rate_hex}">{t_rate:.1f}%</span></td>'
            f'</tr>'
        )

        return self.section("客户月累计明细 · Top 30（万元）", "sec-blue") + f"""
<div class="table-wrap no-collapse"><table class="ann-matrix">
  <thead>{thead}</thead>
  <tbody>{total_row}{rows}</tbody>
</table></div>
<div style="font-size:11px;color:var(--text-muted);margin-top:4px">
  每单元格: 金额 / 占客户收入比 · 回款率色阶: <span style="color:#059669">≥120%超收</span> <span style="color:#16a34a">95-119%健康</span> <span style="color:#f59e0b">70-94%正常</span> <span style="color:#dc2626">&lt;70%预警</span>
</div>"""
