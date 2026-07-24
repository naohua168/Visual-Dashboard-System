"""年度同比页 — 事业部同比 + 重要客户同比"""
from __future__ import annotations

import pandas as pd

from .base import BaseRenderer, yoy_html
from .utils import fmt_wan, fmt_yoy, safe_float

DEPARTMENTS = ["检测", "信息", "能源", "海外"]


def yoy_arrow(cur: float, prev: float) -> str:
    """生成同比趋势箭头 SVG：↑ 增长 / ↓ 下降 / − 持平"""
    if prev == 0 and cur == 0:
        return '<span class="yoy-arrow flat">−</span>'
    if cur > prev:
        return '<span class="yoy-arrow up">▲</span>'
    if cur < prev:
        return '<span class="yoy-arrow down">▼</span>'
    return '<span class="yoy-arrow flat">−</span>'


class YoyPage(BaseRenderer):
    page_id = "yoy"
    nav_name = "年度同比"

    def render(self, data) -> str:
        df_inc = data.income.copy()
        df_pay = data.payment.copy()
        df_inc["金额_万"] = df_inc["金额"].apply(safe_float) / 10000.0
        df_pay["金额_万"] = df_pay["金额"].apply(safe_float) / 10000.0

        if not data.has_yearly_baseline:
            return self.wrap_page(
                self.section("同比分析", "sec-purple")
                + '<div class="empty">⚠️ 年基线数据（2024）未就绪</div>'
            )

        cur_dates = pd.to_datetime(df_inc["日期"], errors="coerce").dropna()
        cur_months = set(d.month for d in cur_dates)
        cur_year = int(cur_dates.dt.year.min())
        sm = sorted(cur_months)
        ml = "、".join("%d月" % m for m in sm) if len(sm) <= 3 else "%d月~%d月" % (sm[0], sm[-1])

        pi = data.yearly_income.copy()
        pp = data.yearly_payment.copy()
        if len(cur_months) > 0 and "日期" in pi.columns:
            pd_dates = pd.to_datetime(pi["日期"], errors="coerce")
            mask = [pd.notna(d) and d.month in cur_months for d in pd_dates]
            pi = pi[mask].copy()
        if len(cur_months) > 0 and "日期" in pp.columns:
            pd_dates = pd.to_datetime(pp["日期"], errors="coerce")
            mask = [pd.notna(d) and d.month in cur_months for d in pd_dates]
            pp = pp[mask].copy()

        pi["金额_万"] = pi["金额"].apply(safe_float) / 10000.0
        pp["金额_万"] = pp["金额"].apply(safe_float) / 10000.0
        ci = df_inc["金额_万"].sum(); pvi = pi["金额_万"].sum()
        cp = df_pay["金额_万"].sum(); pvp = pp["金额_万"].sum()

        period = f"{cur_year}年{ml} vs 2024年{ml}"

        # ── 顶部：4 卡 KPI ──
        kpi = self._kpi_block(ci, pvi, cp, pvp, cur_year)
        # ── 同比周期标识 ──
        period_chip = f"""<div class="period-chip">
  <span class="period-tag">同比周期</span>
  <span class="period-text">{period}</span>
</div>"""
        # ── 事业部同比表（增强版带箭头） ──
        dt = self._dept_table(df_inc, pi, df_pay, pp, ci, pvi, cp, pvp, cur_year)
        # ── 客户同比矩阵（收入/回款 tab 切换） ──
        ct_inc = self._cust_matrix(df_inc, pi, cur_year, "收入")
        ct_pay = self._cust_matrix(df_pay, pp, cur_year, "回款")
        ct_tabs = (
            f'<div class="yoy-cust-tabs">'
            f'<div class="tab-header">'
            f'<button class="tab-btn active" data-tab="yoy-inc" onclick="switchTab(this)">📈 收入同比</button>'
            f'<button class="tab-btn" data-tab="yoy-pay" onclick="switchTab(this)">💰 回款同比</button>'
            f'</div>'
            f'<div id="yoy-inc" class="tab-panel active">{ct_inc}</div>'
            f'<div id="yoy-pay" class="tab-panel">{ct_pay}</div>'
            f'</div>'
        )
        return self.wrap_page(kpi + period_chip + dt + ct_tabs)

    def _kpi_block(self, ci, pvi, cp, pvp, cy) -> str:
        """2 张同比对比卡：增长=红色，下降=绿色"""
        yoy_inc_pct = ((ci - pvi) / pvi * 100) if pvi else 0
        yoy_pay_pct = ((cp - pvp) / pvp * 100) if pvp else 0
        inc_cls = "up" if yoy_inc_pct > 0 else "down" if yoy_inc_pct < 0 else "flat"
        pay_cls = "up" if yoy_pay_pct > 0 else "down" if yoy_pay_pct < 0 else "flat"
        inc_pct_color = "#dc2626" if yoy_inc_pct > 0 else "#16a34a" if yoy_inc_pct < 0 else "#64748b"
        pay_pct_color = "#dc2626" if yoy_pay_pct > 0 else "#16a34a" if yoy_pay_pct < 0 else "#64748b"
        inc_bar_cls = "up" if yoy_inc_pct > 0 else "down"
        pay_bar_cls = "up" if yoy_pay_pct > 0 else "down"
        return f"""<div class="cols-2">
  <div class="kpi yoy-big-card {inc_cls}">
    <div class="yoy-big-label">收入同比</div>
    <div class="yoy-big-pct" style="color:{inc_pct_color}">{yoy_inc_pct:+.1f}%</div>
    <div class="yoy-big-arrow">{yoy_arrow(ci, pvi)}</div>
    <div class="yoy-big-compare">
      <div class="yoy-cmp-item">
        <div class="yoy-cmp-label">{cy}年</div>
        <div class="yoy-cmp-val">{fmt_wan(ci)}<span class="yoy-cmp-unit">万</span></div>
        <div class="yoy-cmp-bar"><div class="yoy-cmp-fill cur {inc_bar_cls}" style="width:100%"></div></div>
      </div>
      <div class="yoy-cmp-item prev">
        <div class="yoy-cmp-label">2024年</div>
        <div class="yoy-cmp-val">{fmt_wan(pvi)}<span class="yoy-cmp-unit">万</span></div>
        <div class="yoy-cmp-bar"><div class="yoy-cmp-fill prev {inc_bar_cls}" style="width:{pvi/ci*100 if ci else 0:.0f}%"></div></div>
      </div>
    </div>
  </div>
  <div class="kpi yoy-big-card {pay_cls}">
    <div class="yoy-big-label">回款同比</div>
    <div class="yoy-big-pct" style="color:{pay_pct_color}">{yoy_pay_pct:+.1f}%</div>
    <div class="yoy-big-arrow">{yoy_arrow(cp, pvp)}</div>
    <div class="yoy-big-compare">
      <div class="yoy-cmp-item">
        <div class="yoy-cmp-label">{cy}年</div>
        <div class="yoy-cmp-val">{fmt_wan(cp)}<span class="yoy-cmp-unit">万</span></div>
        <div class="yoy-cmp-bar"><div class="yoy-cmp-fill cur {pay_bar_cls}" style="width:100%"></div></div>
      </div>
      <div class="yoy-cmp-item prev">
        <div class="yoy-cmp-label">2024年</div>
        <div class="yoy-cmp-val">{fmt_wan(pvp)}<span class="yoy-cmp-unit">万</span></div>
        <div class="yoy-cmp-bar"><div class="yoy-cmp-fill prev {pay_bar_cls}" style="width:{pvp/cp*100 if cp else 0:.0f}%"></div></div>
      </div>
    </div>
  </div>
</div>"""

    def _dept_table(self, di, dpi, dp, dpp, ci, pvi, cp, pvp, cy) -> str:
        """事业部同比表 — 清晰双维度对比：收入组+回款组"""
        rows = ""
        for d in DEPARTMENTS:
            ci_d = float(di[di["事业部"]==d]["金额_万"].sum()) if "事业部" in di.columns else 0
            pi_d = float(dpi[dpi["事业部"]==d]["金额_万"].sum()) if "事业部" in dpi.columns else 0
            cp_d = float(dp[dp["事业部"]==d]["金额_万"].sum()) if "事业部" in dp.columns else 0
            pp_d = float(dpp[dpp["事业部"]==d]["金额_万"].sum()) if "事业部" in dpp.columns else 0

            # 收入同比计算
            inc_pct = (ci_d - pi_d) / pi_d * 100 if pi_d else 0
            inc_cls = "up" if inc_pct > 0 else "down" if inc_pct < 0 else "flat"
            inc_arrow = yoy_arrow(ci_d, pi_d)
            # 回款同比计算
            pay_pct = (cp_d - pp_d) / pp_d * 100 if pp_d else 0
            pay_cls = "up" if pay_pct > 0 else "down" if pay_pct < 0 else "flat"
            pay_arrow = yoy_arrow(cp_d, pp_d)

            inc_big = ' data-big="true"' if abs(inc_pct) >= 50 else ""
            pay_big = ' data-big="true"' if abs(pay_pct) >= 50 else ""
            rows += (
                '<tr>'
                f'<td class="dept-name"><strong>{d}</strong></td>'
                # ── 收入组 ──
                f'<td class="num-cell">{fmt_wan(ci_d)}</td>'
                f'<td class="num-cell muted">{fmt_wan(pi_d)}</td>'
                f'<td class="yoy-cell {inc_cls}"{inc_big}>'
                f'<span class="yoy-pct">{inc_arrow}{inc_pct:+.0f}%</span>'
                f'</td>'
                # ── 回款组 ──
                f'<td class="num-cell">{fmt_wan(cp_d)}</td>'
                f'<td class="num-cell muted">{fmt_wan(pp_d)}</td>'
                f'<td class="yoy-cell {pay_cls}"{pay_big}>'
                f'<span class="yoy-pct">{pay_arrow}{pay_pct:+.0f}%</span>'
                f'</td>'
                '</tr>'
            )

        h = (
            "<tr>"
            "<th rowspan='2'>事业部</th>"
            "<th colspan='3' class='group-header inc-group'>📈 收入</th>"
            "<th colspan='3' class='group-header pay-group'>💰 回款</th>"
            "</tr>"
            "<tr>"
            f"<th>{cy}年</th><th>2024年</th><th>同比</th>"
            f"<th>{cy}年</th><th>2024年</th><th>同比</th>"
            "</tr>"
        )
        return (
            self.section("事业部同比对比（万元）", "sec-purple")
            + f'''<div class="table-wrap no-collapse">
<table class="yoy-dept-table">
<thead>{h}</thead>
<tbody>{rows}</tbody>
</table>
</div>'''
        )

    def _cust_matrix(self, di, dpi, cy, label: str) -> str:
        """客户同比矩阵 — 每格：同比徽章+当期金额"""
        cp = di.pivot_table(index="客户", columns="事业部", values="金额_万", aggfunc="sum", fill_value=0)
        cp["合计"] = cp.sum(axis=1)
        pp = dpi.pivot_table(index="客户", columns="事业部", values="金额_万", aggfunc="sum", fill_value=0) if "事业部" in dpi.columns else None
        if pp is not None:
            pp["合计"] = pp.sum(axis=1)
        top = cp.sort_values("合计", ascending=False).head(15).index.tolist()
        if not top:
            return ""

        def mcell(cur, prev):
            """矩阵单元格：同比徽章 + 当期金额"""
            if cur == 0 and prev == 0:
                return '<td class="td-empty">—</td>'
            pct = (cur - prev) / prev * 100 if prev else 0
            cls = "up" if pct > 0 else "down" if pct < 0 else "flat"
            arrow = yoy_arrow(cur, prev)
            big = abs(pct) >= 50
            return (
                f'<td class="mx-cell {cls}"{" data-big" if big else ""}>'
                f'<span class="mx-badge">{arrow}{pct:+.0f}%</span>'
                f'<span class="mx-val">{fmt_wan(cur)}</span>'
                f'</td>'
            )

        # 合计行
        tc = [f"<td>合计（前15）</td>"]
        for d in DEPARTMENTS:
            cv = sum(float(cp.loc[c, d]) for c in top if c in cp.index and d in cp.columns)
            pv = sum(float(pp.loc[c, d]) for c in top if pp is not None and c in pp.index and d in pp.columns)
            tc.append(mcell(cv, pv))
        cv_t = sum(float(cp.loc[c, "合计"]) for c in top if c in cp.index)
        pv_t = sum(float(pp.loc[c, "合计"]) for c in top if pp is not None and c in pp.index)
        tc.append(mcell(cv_t, pv_t))
        tr = f'<tr class="row-total">{"".join(tc)}</tr>'

        rows = ""
        for i, c in enumerate(top, 1):
            cs = [f'<td class="td-name"><span class="row-num">{i}</span>{c}</td>']
            for d in DEPARTMENTS:
                cv = float(cp.loc[c, d]) if c in cp.index and d in cp.columns else 0
                pv = float(pp.loc[c, d]) if pp is not None and c in pp.index and d in pp.columns else 0
                cs.append(mcell(cv, pv))
            cv_t = float(cp.loc[c, "合计"]) if c in cp.index else 0
            pv_t = float(pp.loc[c, "合计"]) if pp is not None and c in pp.index else 0
            cs.append(mcell(cv_t, pv_t))
            rows += f"<tr class='row-data'>{''.join(cs)}</tr>"
        h = f"<tr><th>客户</th>" + "".join(f"<th>{d}</th>" for d in DEPARTMENTS) + "<th>合计</th></tr>"
        return (
            self.section(f"重要客户{label}同比 · 按事业部分列（万元，前 15）", "sec-purple")
            + f'''<div class="table-wrap no-collapse">
<table class="yoy-matrix-table">
<thead>{h}</thead>
<tbody>{tr}{rows}</tbody>
</table>
</div>'''
        )
