"""季度分析页 — 3 卡片设计

卡片1 — 本季度完成情况（收入/回款/达成度/同比）
卡片2 — 各部门收入回款完成度 + 去年同期差异
卡片3 — 重点大客户收入回款详情
"""
from __future__ import annotations

import pandas as pd

from .base import BaseRenderer, completion_html, rate_cls
from .utils import fmt_wan, safe_float

DEPARTMENTS = ["检测", "信息", "能源", "海外"]
DEPT_COLORS = {"检测": "#2563eb", "信息": "#8b5cf6", "能源": "#f59e0b", "海外": "#0d9488"}
CURRENT_Q_LABEL = "Q2"


class QuarterlyPage(BaseRenderer):
    page_id = "quarterly"
    nav_name = "季度分析"

    def render(self, data) -> str:
        # ── 2026 Q2 数据（当年累计 = Q2）──
        df_inc = data.income.copy()
        df_pay = data.payment.copy()
        df_inc["万"] = df_inc["金额"].apply(safe_float) / 10000.0
        df_pay["万"] = df_pay["金额"].apply(safe_float) / 10000.0

        # ── 2024 年基线数据 ──
        y_inc_2024 = data.yearly_income.copy() if data.has_yearly_baseline else None
        y_pay_2024 = data.yearly_payment.copy() if data.has_yearly_baseline else None
        if y_inc_2024 is not None:
            y_inc_2024["万"] = y_inc_2024["金额"].apply(safe_float) / 10000.0
            y_inc_2024["季度"] = pd.to_datetime(y_inc_2024["日期"]).dt.quarter
        if y_pay_2024 is not None:
            y_pay_2024["万"] = y_pay_2024["金额"].apply(safe_float) / 10000.0
            y_pay_2024["季度"] = pd.to_datetime(y_pay_2024["日期"]).dt.quarter

        # ── 年度目标 ──
        tgt = data.total_targets.copy()
        dept_cols = DEPARTMENTS
        total_target = sum(safe_float(tgt[d].sum()) for d in dept_cols if d in tgt.columns)
        dept_targets = {}
        for d in dept_cols:
            dept_targets[d] = safe_float(tgt[d].fillna(0).sum())

        # ── 2026 Q2 汇总 ──
        q_inc_total = float(df_inc["万"].sum())
        q_pay_total = float(df_pay["万"].sum())
        q_inc_dept = df_inc.groupby("事业部")["万"].sum().to_dict()
        q_pay_dept = df_pay.groupby("事业部")["万"].sum().to_dict()

        # ── 2024 Q2 汇总 ──
        last_q_inc_total = 0.0
        last_q_pay_total = 0.0
        last_q_inc_dept: dict[str, float] = {}
        last_q_pay_dept: dict[str, float] = {}
        if y_inc_2024 is not None:
            yq2 = y_inc_2024[y_inc_2024["季度"] == 2]
            last_q_inc_total = float(yq2["万"].sum())
            last_q_inc_dept = dict(yq2.groupby("事业部")["万"].sum())
        if y_pay_2024 is not None:
            yq2 = y_pay_2024[y_pay_2024["季度"] == 2]
            last_q_pay_total = float(yq2["万"].sum())
            last_q_pay_dept = dict(yq2.groupby("事业部")["万"].sum())

        # ── 客户维度 ──
        c_inc = df_inc.groupby("客户")["万"].sum().sort_values(ascending=False)
        c_pay = df_pay.groupby("客户")["万"].sum()
        all_cust = c_inc.head(15).index.tolist()

        # 2024 Q2 客户收入
        c_last_inc: dict[str, float] = {}
        c_last_pay: dict[str, float] = {}
        if y_inc_2024 is not None:
            yq2 = y_inc_2024[y_inc_2024["季度"] == 2]
            c_last_inc = dict(yq2.groupby("客户")["万"].sum())
        if y_pay_2024 is not None:
            yq2 = y_pay_2024[y_pay_2024["季度"] == 2]
            c_last_pay = dict(yq2.groupby("客户")["万"].sum())

        # ── 组装页面 ──
        parts = [
            self._kpi_row(q_inc_total, q_pay_total, total_target,
                          last_q_inc_total, last_q_pay_total),
            self._card1(q_inc_total, q_pay_total, total_target,
                        last_q_inc_total, last_q_pay_total),
            self._card2(q_inc_dept, q_pay_dept, last_q_inc_dept, last_q_pay_dept,
                        dept_targets),
            self._card3(all_cust, c_inc, c_pay, c_last_inc, c_last_pay,
                        df_inc, df_pay),
        ]
        return self.wrap_page("".join(parts))

    # ════════════════════════════════════════════════════════════
    # KPI 行
    # ════════════════════════════════════════════════════════════
    def _kpi_row(self, q_inc, q_pay, tgt, last_inc, last_pay) -> str:
        rate = q_inc / tgt * 100 if tgt else 0
        inc_yoy = (q_inc - last_inc) / last_inc * 100 if last_inc else 0
        pay_yoy = (q_pay - last_pay) / last_pay * 100 if last_pay else 0
        return f"""<div class="kpi-grid" style="grid-template-columns:repeat(3,1fr)">
  <div class="kpi kpi-inc">
    <div class="kpi-label">{CURRENT_Q_LABEL} 收入</div>
    <div class="kpi-value">{fmt_wan(q_inc)}<span class="kpi-unit">万元</span></div>
    <div class="kpi-sub">同比 {"+" if inc_yoy>=0 else ""}{inc_yoy:.1f}%</div>
  </div>
  <div class="kpi kpi-pay">
    <div class="kpi-label">{CURRENT_Q_LABEL} 回款</div>
    <div class="kpi-value">{fmt_wan(q_pay)}<span class="kpi-unit">万元</span></div>
    <div class="kpi-sub">同比 {"+" if pay_yoy>=0 else ""}{pay_yoy:.1f}%</div>
  </div>
  <div class="kpi kpi-tgt">
    <div class="kpi-label">年度目标达成</div>
    <div class="kpi-value">{rate:.1f}<span class="kpi-unit">%</span></div>
    <div class="kpi-sub">目标 {fmt_wan(tgt)} 万</div>
  </div>
</div>"""

    # ════════════════════════════════════════════════════════════
    # 卡片1: 本季度完成情况
    # ════════════════════════════════════════════════════════════
    def _card1(self, q_inc, q_pay, tgt, last_inc, last_pay) -> str:
        rate = q_inc / tgt * 100 if tgt else 0
        pay_rate_achieved = q_pay / tgt * 100 if tgt else 0
        inc_yoy = (q_inc - last_inc) / last_inc * 100 if last_inc else 0
        pay_yoy = (q_pay - last_pay) / last_pay * 100 if last_pay else 0

        def bar(label, pct, val, sub, color):
            cls = rate_cls(pct / 100) if pct <= 100 else "level-4"
            return f"""<div class="mini-rate">
  <span style="width:90px;font-weight:600">{label}</span>
  <div class="bar"><div class="bar-fill {cls}" style="width:{min(pct,100):.1f}%"><span class="bar-pct">{pct:.1f}%</span></div></div>
  <span class="val">{fmt_wan(val)}</span>
  <span style="color:var(--text-muted);font-size:11px">{sub}</span>
</div>"""

        return self.section(f"卡片1 · {CURRENT_Q_LABEL} 完成情况", "sec-blue") + f"""<div class="card">
  <div class="card-title">{CURRENT_Q_LABEL} 收入 vs 年度目标 · 同比去年同季</div>
  {bar("收入目标达成", rate, q_inc, f"年度目标{fmt_wan(tgt)}", "#2563eb")}
  {bar("回款目标达成", pay_rate_achieved, q_pay, f"年度目标{fmt_wan(tgt)}", "#16a34a")}
  {"" if last_inc == 0 else bar("收入同比去年", inc_yoy, q_inc, f"去年{CURRENT_Q_LABEL} {fmt_wan(last_inc)}", "#8b5cf6")}
  {"" if last_pay == 0 else bar("回款同比去年", pay_yoy, q_pay, f"去年{CURRENT_Q_LABEL} {fmt_wan(last_pay)}", "#f59e0b")}
</div>"""

    # ════════════════════════════════════════════════════════════
    # 卡片2: 部门完成度 + 同比差异
    # ════════════════════════════════════════════════════════════
    def _card2(self, q_inc_dept, q_pay_dept, last_inc_dept, last_pay_dept,
               dept_targets) -> str:
        """事业部本季 vs 去年同季 — 双层表头（收入组/回款组并列）"""

        def yoy_arrow(cur, prev):
            if prev == 0 and cur == 0:
                return '<span class="yoy-arrow flat">−</span>'
            if cur > prev:
                return '<span class="yoy-arrow up">▲</span>'
            if cur < prev:
                return '<span class="yoy-arrow down">▼</span>'
            return '<span class="yoy-arrow flat">−</span>'

        def yoy_pct_cell(cur, prev):
            """同比格子：箭头 + 百分比"""
            if prev == 0 and cur == 0:
                return '<td class="yoy-cell flat"><span class="yoy-pct">—</span></td>'
            pct = (cur - prev) / prev * 100 if prev else 0
            cls = "up" if pct > 0 else "down" if pct < 0 else "flat"
            arrow = yoy_arrow(cur, prev)
            big = abs(pct) >= 50
            return (
                f'<td class="yoy-cell {cls}"{" data-big=true" if big else ""}>'
                f'<span class="yoy-pct">{arrow}{pct:+.0f}%</span></td>'
            )

        rows = ""
        t_inc = t_last_i = t_pay = t_last_p = 0.0
        for d in DEPARTMENTS:
            inc = safe_float(q_inc_dept.get(d, 0))
            pay = safe_float(q_pay_dept.get(d, 0))
            li = safe_float(last_inc_dept.get(d, 0))
            lp = safe_float(last_pay_dept.get(d, 0))
            t_inc += inc; t_last_i += li; t_pay += pay; t_last_p += lp

            rows += (
                f'<tr>'
                f'<td class="dept-name"><strong>{d}</strong></td>'
                f'<td class="num-cell">{fmt_wan(inc)}</td>'
                f'<td class="num-cell muted">{fmt_wan(li)}</td>'
                + yoy_pct_cell(inc, li) +
                f'<td class="num-cell">{fmt_wan(pay)}</td>'
                f'<td class="num-cell muted">{fmt_wan(lp)}</td>'
                + yoy_pct_cell(pay, lp) +
                '</tr>'
            )
        # 合计行
        rows += (
            f'<tr class="row-total">'
            f'<td class="dept-name" style="background:linear-gradient(90deg,#1e293b,#334155);color:#fff;border-left-color:#fbbf24"><strong>合计（4部门）</strong></td>'
            f'<td class="num-cell" style="background:#dbeafe;font-weight:800">{fmt_wan(t_inc)}</td>'
            f'<td class="num-cell muted" style="background:#dbeafe">{fmt_wan(t_last_i)}</td>'
            + yoy_pct_cell(t_inc, t_last_i) +
            f'<td class="num-cell" style="background:#dcfce7;font-weight:800">{fmt_wan(t_pay)}</td>'
            f'<td class="num-cell muted" style="background:#dcfce7">{fmt_wan(t_last_p)}</td>'
            + yoy_pct_cell(t_pay, t_last_p) +
            '</tr>'
        )

        h = (
            "<tr>"
            "<th rowspan='2'>事业部</th>"
            "<th colspan='3' class='group-header inc-group'>📈 收入</th>"
            "<th colspan='3' class='group-header pay-group'>💰 回款</th>"
            "</tr>"
            "<tr>"
            f"<th>{CURRENT_Q_LABEL} 2026</th><th>{CURRENT_Q_LABEL} 2024</th><th>同比</th>"
            f"<th>{CURRENT_Q_LABEL} 2026</th><th>{CURRENT_Q_LABEL} 2024</th><th>同比</th>"
            "</tr>"
        )
        return (
            self.section("卡片2 · 事业部本季收入回款 vs 去年同季", "sec-purple")
            + f'''<div class="table-wrap no-collapse">
<table class="yoy-dept-table">
<thead>{h}</thead>
<tbody>{rows}</tbody>
</table>
</div>'''
        )

    # ════════════════════════════════════════════════════════════
    # 卡片3: 重点客户本季收入回款详情（yoy-matrix-table UI风格）
    # ════════════════════════════════════════════════════════════
    def _card3(self, all_cust, c_inc, c_pay, c_last_inc, c_last_pay,
               df_inc, df_pay) -> str:
        if not all_cust:
            return ""

        # 客户的事业部明细
        inc_dept = df_inc.groupby(["客户", "事业部"])["万"].sum().reset_index()
        pay_dept = df_pay.groupby(["客户", "事业部"])["万"].sum().reset_index()

        def dept_chips(cust):
            """生成事业部+金额小标签（带颜色编码）"""
            chips = ""
            for _, r in inc_dept[inc_dept["客户"] == cust].iterrows():
                d = str(r["事业部"])
                v = float(r["万"])
                color = DEPT_COLORS.get(d, "#94a3b8")
                chips += (
                    f'<span style="font-size:10px;color:{color};background:{color}18;'
                    f'padding:1px 5px;border-radius:3px;margin:0 2px 2px 0;display:inline-block;'
                    f'font-weight:600">{d} {fmt_wan(v)}</span>'
                )
            return chips if chips else '<span style="color:#cbd5e1">—</span>'

        # —— 表头（yoy-matrix-style 深色渐变） ——
        thead = (
            '<tr>'
            '<th style="width:36px;text-align:center">#</th>'
            '<th class="th-name" style="text-align:left">客户</th>'
            '<th style="text-align:right">本季收入</th>'
            '<th style="text-align:right">本季回款</th>'
            '<th style="text-align:right">差额</th>'
            '<th style="text-align:center">收入 vs 2024' + CURRENT_Q_LABEL + '</th>'
            '<th style="text-align:left">细分（事业部/收入）</th>'
            '</tr>'
        )

        rows = ""
        t_inc = t_pay = 0.0
        for i, c in enumerate(all_cust, 1):
            inc = safe_float(c_inc.get(c, 0))
            pay = safe_float(c_pay.get(c, 0))
            last_i = safe_float(c_last_inc.get(c, 0))
            gap = pay - inc
            t_inc += inc; t_pay += pay

            # 差额着色
            gap_color = "#16a34a" if gap >= 0 else "#dc2626"
            gap_str = ("+" if gap >= 0 else "") + fmt_wan(gap)

            # 收入增长
            if last_i > 0:
                r = (inc - last_i) / last_i * 100
                grow_cls = "up" if r >= 0 else "down"
                arrow = "▲" if r >= 0 else "▼"
                big = ' data-big="true"' if abs(r) >= 50 else ""
                grow_html = (
                    f'<td class="mx-cell {grow_cls}"{big}>'
                    f'<span class="mx-badge">{arrow}{r:+.0f}%</span>'
                    f'<span class="mx-val">{fmt_wan(last_i)}</span>'
                    f'</td>'
                )
            elif inc > 0 and last_i == 0:
                grow_html = (
                    '<td class="mx-cell up">'
                    '<span class="mx-badge">★新增</span>'
                    '<span class="mx-val">—</span>'
                    '</td>'
                )
            else:
                grow_html = '<td class="mx-cell flat"><span class="mx-badge" style="background:#f1f5f9;color:#64748b">—</span></td>'

            rows += (
                f'<tr class="row-data">'
                f'<td style="text-align:center"><span class="rank rank-{i if i<=3 else "n"}">{i}</span></td>'
                f'<td class="td-name" style="font-weight:700">{c}</td>'
                f'<td style="text-align:right;font-weight:700">{fmt_wan(inc)}</td>'
                f'<td style="text-align:right">{fmt_wan(pay)}</td>'
                f'<td style="text-align:right;color:{gap_color};font-weight:700">{gap_str}</td>'
                + grow_html +
                f'<td>{dept_chips(c)}</td>'
                f'</tr>'
            )

        # 合计行
        t_gap = t_pay - t_inc
        t_gap_color = "#16a34a" if t_gap >= 0 else "#dc2626"
        t_gap_str = ("+" if t_gap >= 0 else "") + fmt_wan(t_gap)
        rows += (
            f'<tr class="row-total">'
            f'<td></td><td style="text-align:left;font-weight:800">合计（{len(all_cust)}家）</td>'
            f'<td style="text-align:right;font-weight:800">{fmt_wan(t_inc)}</td>'
            f'<td style="text-align:right;font-weight:800">{fmt_wan(t_pay)}</td>'
            f'<td style="text-align:right;color:{t_gap_color};font-weight:800">{t_gap_str}</td>'
            f'<td></td><td></td>'
            f'</tr>'
        )

        return (
            self.section("卡片3 · 重点客户本季收入回款 vs 去年同季", "sec-green")
            + f"""<div class="card" style="padding:10px 14px">
  <div class="table-wrap no-collapse"><table class="yoy-matrix-table">
    <thead>{thead}</thead>
    <tbody>{rows}</tbody>
  </table></div>
  <div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:12px;font-size:11px;color:var(--text-muted)">
    <span>■ <span style="color:#dc2626;font-weight:700">红↑ = 增长</span> · <span style="color:#16a34a;font-weight:700">绿↓ = 下降</span></span>
    <span>■ 差额 = 回款 - 收入</span>
    <span>■ 增长 vs 2024年{CURRENT_Q_LABEL}</span>
  </div>
</div>"""
        )
