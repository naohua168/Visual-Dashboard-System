"""销售达成页 — 聚焦销售个人收入回款达成情况

布局：
  [A] KPI卡片 — 总收入/总回款/人数（含整体回款率）
  [B] 销售榜单 — 22人排名+收入+回款率色阶
  [C] 排名柱状图 — Chart.js水平条形 Top 15
  [D] 销售明细表 — 排名/销售/收入/回款/差额/回款率
"""
from __future__ import annotations

import json

from .base import BaseRenderer, rate_cls
from .utils import fmt_wan, safe_float

DEPARTMENTS = ["检测", "信息", "能源", "海外"]


class SalesPage(BaseRenderer):
    page_id = "sales"
    nav_name = "销售达成"

    def render(self, data) -> str:
        df_si = data.sales_income.copy()
        df_sp = data.sales_payment.copy()
        df_si["金额_万"] = df_si["金额"].apply(safe_float) / 10000.0
        df_sp["金额_万"] = df_sp["金额"].apply(safe_float) / 10000.0

        total_inc = float(df_si["金额_万"].sum())
        total_pay = float(df_sp["金额_万"].sum())
        sales_cnt = df_si[df_si["销售"] != "待确认"]["销售"].nunique()

        parts = []
        parts.append(self._kpi_row(total_inc, total_pay, sales_cnt))
        parts.append(self._sales_roster(df_si, df_sp))
        parts.append(self._ranking_chart(df_si, df_sp))
        parts.append(self._detail_table(df_si, df_sp))
        return self.wrap_page("".join(parts))

    # ── [A] KPI 卡片 ──────────────────────────────
    def _kpi_row(self, total_inc, total_pay, sales_cnt) -> str:
        pay_rate = total_pay / total_inc * 100 if total_inc else 0
        gap = total_pay - total_inc
        return f"""<div class="kpi-grid cols-9" style="grid-template-columns:repeat(3,1fr)">
  <div class="kpi kpi-inc">
    <div class="kpi-label">销售总收入</div>
    <div class="kpi-value">{fmt_wan(total_inc)}<span class="kpi-unit">万元</span></div>
  </div>
  <div class="kpi kpi-pay">
    <div class="kpi-label">销售总回款</div>
    <div class="kpi-value">{fmt_wan(total_pay)}<span class="kpi-unit">万元</span></div>
  </div>
  <div class="kpi kpi-growth">
    <div class="kpi-label">销售人数</div>
    <div class="kpi-value">{sales_cnt}<span class="kpi-unit">人</span></div>
    <div class="kpi-sub">整体回款率 <span style="color:#059669;font-weight:700">{pay_rate:.1f}%</span> · 超收{fmt_wan(gap)}万</div>
  </div>
</div>"""

    # ── [B] 销售榜单 ──────────────────────────────
    def _sales_roster(self, df_si, df_sp) -> str:
        si_p = df_si.groupby("销售")["金额_万"].sum()
        sp_p = df_sp.groupby("销售")["金额_万"].sum()
        all_s = [s for s in si_p.sort_values(ascending=False).index if s != "待确认"]

        chips = ""
        for i, s in enumerate(all_s, 1):
            vi = float(si_p.get(s, 0))
            vp = float(sp_p.get(s, 0))
            rate = vp / vi * 100 if vi > 0 else 0
            badge_cls = "rate-high" if rate >= 95 else "rate-mid" if rate >= 70 else "rate-low"
            chips += (
                f'<div class="sales-chip">'
                f'<span class="rank rank-{i if i<=3 else "n"}" style="min-width:22px">{i}</span>'
                f'<span class="sales-name">{s}</span>'
                f'<span class="sales-amt"><span class="sales-unit">万元</span>{fmt_wan(vi)}</span>'
                f'<span class="sales-rate {badge_cls}" title="回款率=累计回款÷累计收入">{rate:.0f}%</span>'
                f'</div>'
            )

        return f"""<div class="card">
  <div class="card-title">销售榜单 · {len(all_s)} 人</div>
  <div class="sales-roster-head">
    <span style="flex:0 0 22px"></span>
    <span style="flex:1;font-weight:600">销售</span>
    <span class="sales-amt-head">累计收入(万元)</span>
    <span class="sales-rate-head">回款率</span>
  </div>
  <div class="sales-roster">{chips}</div>
  <div class="legend" style="margin-top:0;border-left-color:#f59e0b">
    <span class="legend-item"><b>累计收入</b> = 该销售所有客户的回款前确认收入总额</span>
    <span class="legend-item"><b>回款率</b> = 累计回款÷累计收入 · <span style="color:#16a34a">≥95%</span> / <span style="color:#ea580c">70-94%</span> / <span style="color:#dc2626">&lt;70%</span></span>
  </div>
</div>"""

    # ── [C] 排名柱状图 ──────────────────────────
    def _ranking_chart(self, df_si, df_sp) -> str:
        si_p = df_si.groupby("销售")["金额_万"].sum()
        sp_p = df_sp.groupby("销售")["金额_万"].sum()
        all_s = [s for s in si_p.sort_values(ascending=False).index if s != "待确认"][:15]
        if not all_s:
            return ""
        labels = [s[:5] + ("…" if len(s) > 5 else "") for s in all_s]
        i_data = [round(float(si_p.get(s, 0)), 2) for s in all_s]
        p_data = [round(float(sp_p.get(s, 0)), 2) for s in all_s]

        chart_id = "salesRankChart"
        config = {
            "type": "bar",
            "data": {
                "labels": labels,
                "datasets": [
                    {"label": "收入", "data": i_data, "backgroundColor": "#2563eb", "borderRadius": 3},
                    {"label": "回款", "data": p_data, "backgroundColor": "#f59e0b", "borderRadius": 3},
                ],
            },
            "options": {
                "indexAxis": "y", "responsive": True, "maintainAspectRatio": False,
                "plugins": {
                    "legend": {"position": "top", "labels": {"usePointStyle": True, "padding": 12}},
                    "tooltip": {"callbacks": {"label": "ctx => ctx.dataset.label + ': ' + ctx.parsed.x.toLocaleString('zh-CN',{minimumFractionDigits:2}) + ' 万元'"}},
                },
                "scales": {
                    "x": {"beginAtZero": True, "grid": {"color": "rgba(148,163,184,0.15)"},
                          "ticks": {"callback": "v => v.toLocaleString('zh-CN',{maximumFractionDigits:0})"},
                          "title": {"display": True, "text": "万元"}},
                    "y": {"grid": {"display": False}, "ticks": {"font": {"size": 10}}},
                },
            },
        }
        height = min(len(all_s) * 30 + 50, 420)
        return f"""<div class="card">
  <div class="card-title">Top {len(all_s)} 销售 · 收入 vs 回款</div>
  <div style="height:{height}px;position:relative"><canvas id="{chart_id}"></canvas></div>
</div>
<script>(function(){{ var e=document.getElementById('{chart_id}'); if(e) new Chart(e.getContext('2d'), {json.dumps(config, ensure_ascii=False)}); }})();</script>"""

    # ── [D] 销售明细表 ──────────────────────────
    def _detail_table(self, df_si, df_sp) -> str:
        si_p = df_si.groupby("销售")["金额_万"].sum()
        sp_p = df_sp.groupby("销售")["金额_万"].sum()
        all_s = [s for s in si_p.sort_values(ascending=False).index if s != "待确认"]

        def _rh(rate):
            return "#059669" if rate >= 120 else "#16a34a" if rate >= 95 else "#f59e0b" if rate >= 70 else "#dc2626"
        def _rc(rate):
            return "rate-high" if rate >= 120 else "rate-ok" if rate >= 95 else "rate-mid" if rate >= 70 else "rate-low"

        thead = "<tr><th>#</th><th>销售</th><th>收入金额</th><th>回款金额</th><th>差额</th><th>回款率</th></tr>"
        rows = ""
        t_inc = t_pay = 0.0
        for i, s in enumerate(all_s, 1):
            vi = float(si_p.get(s, 0))
            vp = float(sp_p.get(s, 0))
            t_inc += vi; t_pay += vp
            gap = vp - vi
            rate = vp / vi * 100 if vi > 0 else 0
            gap_color = "#059669" if gap >= 0 else "#dc2626"
            rh = _rh(rate); rc = _rc(rate)
            rank_tag = f'<span class="rank rank-{i if i<=3 else "n"}">{i}</span>'
            rows += (
                f"<tr><td>{rank_tag}</td>"
                f"<td style=\"text-align:left;font-weight:600\">{s}</td>"
                f"<td style=\"font-weight:700\">{fmt_wan(vi)}</td>"
                f"<td>{fmt_wan(vp)}</td>"
                f"<td style=\"color:{gap_color};font-weight:700\">{"+" if gap>=0 else ""}{fmt_wan(gap)}</td>"
                f"<td><span class=\"rate-badge {rc}\" style=\"background:{rh}22;color:{rh}\">{rate:.1f}%</span></td>"
                f"</tr>"
            )

        # 合计
        t_gap = t_pay - t_inc
        t_rate = t_pay / t_inc * 100 if t_inc else 0
        trh = _rh(t_rate); trc = _rc(t_rate)
        total_row = (
            f'<tr class="total"><td></td><td>合计（{len(all_s)}人）</td>'
            f"<td>{fmt_wan(t_inc)}</td><td>{fmt_wan(t_pay)}</td>"
            f"<td style=\"color:{"#059669" if t_gap>=0 else "#dc2626"};font-weight:700\">{"+" if t_gap>=0 else ""}{fmt_wan(t_gap)}</td>"
            f"<td><span class=\"rate-badge {trc}\" style=\"background:{trh}22;color:{trh}\">{t_rate:.1f}%</span></td>"
            f"</tr>"
        )

        # 待确认
        pending_inc = float(si_p.get("待确认", 0))
        pending_cust = len(df_si[df_si["销售"] == "待确认"]["客户"].unique()) if "待确认" in df_si["销售"].values else 0

        return self.section("销售排名明细", "sec-blue") + f"""
<div class="table-wrap no-collapse"><table class="ann-matrix"><thead>{thead}</thead><tbody>{total_row}{rows}</tbody></table></div>
<div style="margin-top:6px;display:flex;justify-content:space-between;font-size:11px;color:var(--text-muted)">
  <span>□ <span style="color:#059669">≥120%超收</span> · <span style="color:#16a34a">95-119%健康</span> · <span style="color:#f59e0b">70-94%正常</span> · <span style="color:#dc2626">&lt;70%预警</span></span>
  <span>待确认收入 {fmt_wan(pending_inc)}万 · {pending_cust}家客户待归属</span>
</div>"""
