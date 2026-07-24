"""季度分析页 — 6区数据仪表盘

可视化方案（基于2026-07-23 EDA报告）：
  [A] KPI卡片行         — 年累计收入/回款 + 当季值 + 整体回款率
  [B] 事业部构成环形图   — 收入占比 + 中心汇总数字
  [C] 事业部分组柱状图   — 收入vs回款 + 柱顶差额标注
  [D] 帕累托双轴图       — Top客户条形(左轴) + 累计占比折线(右轴)
  [E] 回款率热力矩阵     — 事业部×Top客户色阶矩阵
  [F] 详细数据表格       — 排名/回款率徽章/差额/可排序
"""
from __future__ import annotations

import json
import math

import pandas as pd

from .base import BaseRenderer, rate_cls
from .utils import fmt_wan, safe_float

DEPARTMENTS = ["检测", "信息", "能源", "海外"]
DEPT_COLORS_CSS = ["#2563eb", "#059669", "#d97706", "#dc2626"]
DEPT_LABELS_CN = ["蓝", "绿", "橙", "红"]

# ── Helper: 回款率等级色阶 ──────────────────────────
def _pay_rate_level(rate: float) -> dict:
    """返回回款率对应的等级信息"""
    if rate >= 120:    return {"level": "high", "cls": "rate-high",  "hex": "#059669", "label": "超收"}
    if rate >= 95:     return {"level": "ok",   "cls": "rate-ok",    "hex": "#16a34a", "label": "健康"}
    if rate >= 70:     return {"level": "mid",  "cls": "rate-mid",   "hex": "#f59e0b", "label": "正常"}
    if rate >= 50:     return {"level": "low",  "cls": "rate-mid",   "hex": "#f97316", "label": "预警"}
    return {"level": "danger", "cls": "rate-low", "hex": "#dc2626", "label": "风险"}


def _rate_hex(rate_str: str) -> str:
    """
    rate_str 是 rate-badge 的 class 名（如 'rate-high', 'rate-ok' 等）
    返回对应的十六进制颜色字符串
    """
    mapping = {
        "rate-high": "#059669",
        "rate-ok": "#16a34a",
        "rate-mid": "#f59e0b",
        "rate-low": "#dc2626",
    }
    return mapping.get(rate_str, "#94a3b8")


def _quarter(ts: pd.Timestamp) -> str:
    m = ts.month
    return "Q1" if m <= 3 else "Q2" if m <= 6 else "Q3" if m <= 9 else "Q4"


def _qtr_order(q: str) -> int:
    return {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}.get(q, 0)


# ── Chart.js 配色常量 ────────────────────────────────
CHART_COLORS = {
    "income": "#2563eb",
    "payment": "#f59e0b",
    "income_fill": "rgba(37,99,235,0.1)",
    "payment_fill": "rgba(245,158,11,0.1)",
    "grid": "rgba(148,163,184,0.15)",
    "text": "#64748b",
    "dept": "#2563eb",
    "pareto_line": "#dc2626",
}


class QuarterlyPage(BaseRenderer):
    page_id = "quarterly"
    nav_name = "季度分析"

    def render(self, data) -> str:
        if not data.has_quarterly_data:
            return self.wrap_page(
                '<div class="card"><div class="card-title">季度分析</div>'
                '<p style="color:var(--text-muted);text-align:center;padding:40px">'
                '季度数据暂未就绪</p></div>'
            )
        df_inc = data.quarterly_income.copy()
        df_pay = data.quarterly_payment.copy()
        df_inc["金额_万"] = df_inc["金额"].apply(safe_float) / 10000.0
        df_pay["金额_万"] = df_pay["金额"].apply(safe_float) / 10000.0
        df_inc["季度"] = pd.to_datetime(df_inc["日期"], errors="coerce").apply(_quarter)
        df_pay["季度"] = pd.to_datetime(df_pay["日期"], errors="coerce").apply(_quarter)
        quarters = sorted(df_inc["季度"].dropna().unique(), key=_qtr_order)
        if not quarters:
            return self.wrap_page('<p>无季度数据</p>')
        latest_q = quarters[-1]
        q_inc = df_inc[df_inc["季度"] == latest_q].copy()
        q_pay = df_pay[df_pay["季度"] == latest_q].copy()

        parts = []
        parts.append(self._kpi_cards(df_inc, df_pay, quarters))
        parts.append(self._dept_doughnut_and_grouped_bar(df_inc, df_pay, latest_q))
        parts.append(self._pareto_chart(df_inc, df_pay))
        parts.append(self._heat_matrix(df_inc, df_pay))
        parts.append(self._detail_table(df_inc, df_pay))
        return self.wrap_page("".join(parts))

    # ══════════════════════════════════════════════════
    # [A] KPI 卡片行（5卡）
    # ══════════════════════════════════════════════════
    def _kpi_cards(self, df_inc, df_pay, quarters) -> str:
        totals_inc = float(df_inc["金额_万"].sum())
        totals_pay = float(df_pay["金额_万"].sum())
        latest_q = quarters[-1]
        q_inc_v = float(df_inc[df_inc["季度"] == latest_q]["金额_万"].sum())
        q_pay_v = float(df_pay[df_pay["季度"] == latest_q]["金额_万"].sum())

        # 整体回款率
        pay_rate_all = totals_pay / totals_inc * 100 if totals_inc else 0
        pr_level = _pay_rate_level(pay_rate_all)

        # 卡片数据 + 各自样式
        cards = [
            {"label": "年累计收入", "value": fmt_wan(totals_inc), "sub": "万元", "cls_span": "kpi-inc"},
            {"label": "年累计回款", "value": fmt_wan(totals_pay), "sub": "万元", "cls_span": "kpi-pay"},
            {"label": f"整体回款率", "value": f"{pay_rate_all:.1f}%",
             "sub": f"差额 {fmt_wan(totals_pay - totals_inc)} 万", "cls_span": "kpi-rate"},
            {"label": f"{latest_q} 收入", "value": fmt_wan(q_inc_v), "sub": "万元", "cls_span": "kpi-tgt"},
            {"label": f"{latest_q} 回款", "value": fmt_wan(q_pay_v), "sub": "万元", "cls_span": "kpi-pay"},
        ]
        html_cards = ""
        for c in cards:
            html_cards += f"""<div class="kpi {c['cls_span']}"><div class="kpi-label">{c['label']}</div>
  <div class="kpi-value">{c['value']}</div><div class="kpi-sub">{c['sub']}</div></div>"""
        return f'<div class="kpi-grid cols-9" style="grid-template-columns:repeat(5,1fr)">{html_cards}</div>'

    # ══════════════════════════════════════════════════
    # [B] 事业部环形图 + [C] 分组柱状图（左右并排）
    # ══════════════════════════════════════════════════
    def _dept_doughnut_and_grouped_bar(self, df_inc, df_pay, latest_q) -> str:
        """左: 事业部收入环形图; 右: 收入vs回款分组柱状图"""
        if "事业部" not in df_inc.columns:
            return '<div class="card"><div class="card-title">事业部数据不可用</div></div>'

        # 聚合数据
        dept_inc = df_inc.groupby("事业部")["金额_万"].sum().reindex(DEPARTMENTS, fill_value=0)
        dept_pay = df_pay.groupby("事业部")["金额_万"].sum().reindex(DEPARTMENTS, fill_value=0)
        total_inc = float(dept_inc.sum())

        # ── B: 环形图配置 ──
        doughnut_id = "qtrDoughnut"
        dnut_config = {
            "type": "doughnut",
            "data": {
                "labels": DEPARTMENTS,
                "datasets": [{
                    "data": [round(float(v), 2) for v in dept_inc.values],
                    "backgroundColor": DEPT_COLORS_CSS,
                    "borderWidth": 0,
                    "hoverOffset": 10,
                }],
            },
            "options": {
                "responsive": True,
                "maintainAspectRatio": False,
                "cutout": "65%",
                "plugins": {
                    "legend": {
                        "position": "right",
                        "labels": {"usePointStyle": True, "padding": 12, "boxWidth": 10, "font": {"size": 11}},
                    },
                    "tooltip": {
                        "callbacks": {
                            "label": ("ctx => {const v=ctx.parsed; const t=v / " + str(total_inc) + " * 100; "
                                      "return ctx.label + ': ' + v.toLocaleString('zh-CN',{minimumFractionDigits:2})"
                                      "+ ' 万元 (' + t.toFixed(1) + '%)';}")
                        }
                    },
                },
            },
        }

        # ── C: 分组柱状图（带差额标注） ──
        bar_chart_id = "qtrBarDept"
        dept_inc_list = [round(float(v), 2) for v in dept_inc.values]
        dept_pay_list = [round(float(v), 2) for v in dept_pay.values]
        gaps = [round(p - i, 2) for i, p in zip(dept_inc_list, dept_pay_list)]
        bar_config = {
            "type": "bar",
            "data": {
                "labels": DEPARTMENTS,
                "datasets": [
                    {
                        "label": "收入",
                        "data": dept_inc_list,
                        "backgroundColor": CHART_COLORS["income"],
                        "borderRadius": 4,
                        "barPercentage": 0.35,
                    },
                    {
                        "label": "回款",
                        "data": dept_pay_list,
                        "backgroundColor": CHART_COLORS["payment"],
                        "borderRadius": 4,
                        "barPercentage": 0.35,
                    },
                ],
            },
            "options": {
                "responsive": True,
                "maintainAspectRatio": False,
                "plugins": {
                    "legend": {"position": "top", "labels": {"usePointStyle": True, "padding": 12}},
                    "tooltip": {
                        "callbacks": {
                            "label": ("ctx => {const v=ctx.parsed.y; "
                                      "const gap = v - " + json.dumps(dept_inc_list) + "[ctx.dataIndex]; "
                                      "return ctx.dataset.label + ': ' + v.toLocaleString('zh-CN',{minimumFractionDigits:2})"
                                      "+ ' 万元 (差额:' + (gap>=0?'+':'') + gap.toFixed(2) + ')';}")
                        }
                    },
                    "datalabels": {"display": False},
                },
                "scales": {
                    "x": {"grid": {"display": False}},
                    "y": {
                        "beginAtZero": True,
                        "grid": {"color": CHART_COLORS["grid"]},
                        "ticks": {"callback": "v => v.toLocaleString('zh-CN', {maximumFractionDigits:0})"},
                        "title": {"display": True, "text": "万元"},
                    },
                },
            },
        }

        # 手算差额行
        gap_rows = ""
        for d, g in zip(DEPARTMENTS, gaps):
            color = "#059669" if g >= 0 else "#dc2626"
            gap_rows += f"<span style='color:{color};font-weight:700;font-size:13px'>{'+' if g>=0 else ''}{g:,.0f}万</span> "

        return f"""<div class="cols-2" style="gap:12px">
  <div class="card">
    <div class="card-title">事业部收入构成</div>
    <div style="height:240px;position:relative"><canvas id="{doughnut_id}"></canvas></div>
  </div>
  <div class="card">
    <div class="card-title">{latest_q} 收入 vs 回款</div>
    <div style="height:240px;position:relative"><canvas id="{bar_chart_id}"></canvas></div>
    <div style="margin-top:8px;display:flex;justify-content:space-around;font-size:11px;color:var(--text-muted)">
      <span>差额: {gap_rows}</span>
    </div>
  </div>
</div>
<script>
(function(){{
  var e1 = document.getElementById('{doughnut_id}'); if(e1) new Chart(e1.getContext('2d'), {json.dumps(dnut_config, ensure_ascii=False)});
  var e2 = document.getElementById('{bar_chart_id}'); if(e2) new Chart(e2.getContext('2d'), {json.dumps(bar_config, ensure_ascii=False)});
}})();
</script>"""

    # ══════════════════════════════════════════════════
    # [D] 帕累托双轴图（条形 + 累计折线）
    # ══════════════════════════════════════════════════
    def _pareto_chart(self, df_inc, df_pay) -> str:
        """Top 客户帕累托分析：水平条形(左轴) + 累计占比折线(右轴)"""
        cust_inc = df_inc.groupby("客户")["金额_万"].sum().sort_values(ascending=False)
        total = float(cust_inc.sum())
        top = cust_inc.head(15)
        cum = top.cumsum() / total * 100

        if len(top) == 0:
            return ""
        pareto_id = "qtrPareto"
        labels = [c[:10] + ("…" if len(c)>10 else "") for c in top.index]
        values = [round(float(v), 2) for v in top.values]
        cums = [round(float(v), 2) for v in cum.values]
        pareto_config = {
            "type": "bar",
            "data": {
                "labels": labels,
                "datasets": [
                    {
                        "label": "收入(万元)",
                        "data": values,
                        "backgroundColor": CHART_COLORS["income"],
                        "borderRadius": 3,
                        "order": 2,
                        "yAxisID": "y",
                    },
                    {
                        "type": "line",
                        "label": "累计占比%",
                        "data": cums,
                        "borderColor": CHART_COLORS["pareto_line"],
                        "backgroundColor": CHART_COLORS["pareto_line"],
                        "pointRadius": 4,
                        "pointBackgroundColor": CHART_COLORS["pareto_line"],
                        "tension": 0.3,
                        "order": 1,
                        "yAxisID": "y1",
                        "fill": False,
                    },
                ],
            },
            "options": {
                "responsive": True,
                "maintainAspectRatio": False,
                "plugins": {
                    "legend": {"position": "top", "labels": {"usePointStyle": True, "padding": 16}},
                    "tooltip": {"mode": "index", "intersect": False},
                },
                "scales": {
                    "x": {"grid": {"display": False}, "ticks": {"font": {"size": 10}}},
                    "y": {
                        "position": "left",
                        "beginAtZero": True,
                        "grid": {"color": CHART_COLORS["grid"]},
                        "ticks": {"callback": "v => v.toLocaleString('zh-CN',{maximumFractionDigits:0})"},
                        "title": {"display": True, "text": "收入(万元)", "font": {"size": 11}},
                    },
                    "y1": {
                        "position": "right",
                        "min": 0,
                        "max": 100,
                        "grid": {"drawOnChartArea": False},
                        "ticks": {"callback": "v => v.toFixed(0) + '%'", "font": {"size": 11}},
                        "title": {"display": True, "text": "累计占比%", "font": {"size": 11}},
                    },
                },
            },
        }

        # 80% 参考线 & 帕累托计数
        pareto_count = (cum <= 80).sum() + 1
        pareto_pct = pareto_count / len(cust_inc) * 100 if len(cust_inc) else 0
        return f"""<div class="card">
  <div class="card-title">Top {len(top)} 客户帕累托分析
    <span style="font-size:11px;color:var(--text-muted);font-weight:400">
      {pareto_count}家贡献80%收入 · 占客户总数{pareto_pct:.1f}%
    </span>
  </div>
  <div style="height:{max(len(top)*24+40, 200)}px;position:relative"><canvas id="{pareto_id}"></canvas></div>
</div>
<script>
(function(){{
  var e = document.getElementById('{pareto_id}'); if(!e) return;
  new Chart(e.getContext('2d'), {json.dumps(pareto_config, ensure_ascii=False)});
}})();
</script>"""

    # ══════════════════════════════════════════════════
    # [E] 回款率热力矩阵（事业部×客户）
    # ══════════════════════════════════════════════════
    def _heat_matrix(self, df_inc, df_pay) -> str:
        """事业部×Top客户回款率色阶矩阵"""
        # 取 Top 10 收入客户
        cust_inc = df_inc.groupby("客户")["金额_万"].sum().sort_values(ascending=False).head(10)
        if len(cust_inc) == 0 or "事业部" not in df_inc.columns:
            return ""

        thead = "<tr><th>客户</th>"
        for d in DEPARTMENTS:
            thead += f'<th style="background:{DEPT_COLORS_CSS[DEPARTMENTS.index(d)]};color:#fff;text-align:center">{d}</th>'
        thead += '<th style="background:#1e293b;color:#fff;text-align:center">综合回款率</th></tr>'

        rows = ""
        for rank, (cust, _) in enumerate(cust_inc.items(), 1):
            cells = ""
            total_i = float(df_inc[df_inc["客户"] == cust]["金额_万"].sum())
            total_p = float(df_pay[df_pay["客户"] == cust]["金额_万"].sum())
            overall_rate = total_p / total_i * 100 if total_i > 0 else 0
            overall_lvl = _pay_rate_level(overall_rate)

            for d in DEPARTMENTS:
                di = float(df_inc[(df_inc["客户"] == cust) & (df_inc["事业部"] == d)]["金额_万"].sum())
                dp = float(df_pay[(df_pay["客户"] == cust) & (df_pay["事业部"] == d)]["金额_万"].sum())
                if di == 0:
                    cells += '<td style="background:#f1f5f9;color:#94a3b8;text-align:center;font-size:11px">—</td>'
                else:
                    dr = dp / di * 100
                    dlvl = _pay_rate_level(dr)
                    cells += f'<td style="background:{dlvl["hex"]}22;color:{dlvl["hex"]};text-align:center;font-weight:700;font-size:13px">{dr:.0f}%</td>'

            # 综合回款率
            cells += f'<td style="background:{overall_lvl["hex"]}22;color:{overall_lvl["hex"]};text-align:center;font-weight:800;font-size:14px">{overall_rate:.0f}%</td>'
            cls_rank = "rank-top" if rank <= 3 else ""
            rows += f'<tr class="{cls_rank}"><td style="text-align:left;padding-left:12px"><span class="rank rank-{rank if rank<=3 else "n"}" style="margin-right:6px">{rank}</span>{cust}</td>{cells}</tr>'

        return self.section("回款率热力矩阵（事业部 × Top 客户）", "sec-teal") + f"""
<div class="card" style="margin-top:8px">
  <div class="table-wrap no-collapse">
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead>{thead}</thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
  <div style="margin-top:8px;display:flex;gap:16px;font-size:11px;color:var(--text-muted);justify-content:center">
    <span style="display:flex;align-items:center;gap:4px"><span style="width:12px;height:12px;background:#05966922;border:2px solid #059669;border-radius:2px"></span>超收≥120%</span>
    <span style="display:flex;align-items:center;gap:4px"><span style="width:12px;height:12px;background:#16a34a22;border:2px solid #16a34a;border-radius:2px"></span>健康95-119%</span>
    <span style="display:flex;align-items:center;gap:4px"><span style="width:12px;height:12px;background:#f59e0b22;border:2px solid #f59e0b;border-radius:2px"></span>正常70-94%</span>
    <span style="display:flex;align-items:center;gap:4px"><span style="width:12px;height:12px;background:#f9731622;border:2px solid #f97316;border-radius:2px"></span>预警50-69%</span>
    <span style="display:flex;align-items:center;gap:4px"><span style="width:12px;height:12px;background:#dc262622;border:2px solid #dc2626;border-radius:2px"></span>风险&lt;50%</span>
  </div>
</div>"""

    # ══════════════════════════════════════════════════
    # [F] 详细数据表格
    # ══════════════════════════════════════════════════
    def _detail_table(self, df_inc, df_pay) -> str:
        """Top 15 客户明细表：排名 | 客户 | 收入 | 回款 | 差额 | 回款率"""
        inc_top = df_inc.groupby("客户")["金额_万"].sum().sort_values(ascending=False)
        pay_top = df_pay.groupby("客户")["金额_万"].sum()

        all_cust = inc_top.head(15).index.tolist()
        if not all_cust:
            return ""
        thead = ("<tr><th>#</th><th>客户</th><th>累计收入</th>"
                 "<th>累计回款</th><th>差额</th><th>回款率</th></tr>")
        rows = ""
        for i, c in enumerate(all_cust, 1):
            vi = float(inc_top.get(c, 0))
            vp = float(pay_top.get(c, 0))
            gap = vp - vi
            rate = vp / vi * 100 if vi > 0 else 0
            rate_lvl = _pay_rate_level(rate)
            rank_cls = "rank-top" if i <= 3 else ""
            gap_color = "#059669" if gap >= 0 else "#dc2626"
            rows += (
                f'<tr class="{rank_cls}">'
                f'<td><span class="rank rank-{i if i<=3 else "n"}">{i}</span></td>'
                f"<td style=\"text-align:left\">{c}</td>"
                f"<td>{fmt_wan(vi)}</td>"
                f"<td>{fmt_wan(vp)}</td>"
                f"<td style=\"color:{gap_color};font-weight:700\">"
                f"{'+' if gap>=0 else ''}{fmt_wan(gap)}</td>"
                f'<td><span class="rate-badge {rate_lvl["cls"]}">{rate:.1f}%</span></td>'
                "</tr>"
            )
        return (self.section("客户明细排名 Top 15", "sec-blue")
                + f'<div class="table-wrap no-collapse">'
                  f'<table class="ann-matrix"><thead>{thead}</thead><tbody>{rows}</tbody></table></div>')
