"""年度同比页 — 事业部同比 + 重要客户同比（纯视图层）
"""
from __future__ import annotations

import pandas as pd

from .base import BaseRenderer
from .utils import fmt_wan, fmt_yoy, safe_float, extract_date_range, range_banner_html
from .page_data import prepare_yoy_data, DEPARTMENTS


def yoy_arrow(cur: float, prev: float) -> str:
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
        d = prepare_yoy_data(data, self.base_dir)
        banner = range_banner_html(d.annual_range)

        if not d.has_baseline:
            return self.wrap_page(
                banner + self._fallback_no_baseline(d), d.date_range
            )

        kpi = self._kpi_block(d.ci, d.pvi, d.cp, d.pvp, d.cur_year)
        period_chip = f"""<div class="period-chip">
  <span class="period-tag">同比周期</span>
  <span class="period-text">{d.period}</span>
</div>"""
        dt = self._dept_table(d.dept_yoy, d.cur_year)
        ct_inc = self._cust_matrix(d.inc_cust_piv, d.inc_prev_piv, d.top_customers, d.cur_year, "收入", d.top_n)
        ct_pay = self._cust_matrix(d.pay_cust_piv, d.pay_prev_piv, d.top_customers, d.cur_year, "回款", d.top_n)
        ct_tabs = (
            f'<div class="yoy-cust-tabs">'
            f'<div class="tab-header">'
            f'<button class="tab-btn active" data-tab="yoy-inc" onclick="switchTab(this)">收入同比</button>'
            f'<button class="tab-btn" data-tab="yoy-pay" onclick="switchTab(this)">回款同比</button>'
            f'</div>'
            f'<div id="yoy-inc" class="tab-panel active">{ct_inc}</div>'
            f'<div id="yoy-pay" class="tab-panel">{ct_pay}</div>'
            f'</div>'
        )

        return self.wrap_page(banner + kpi + period_chip + dt + ct_tabs, d.date_range)

    def _fallback_no_baseline(self, d) -> str:
        """降级方案：无年基线时展示当前年数据"""
        dept_rows = ""
        for dept_data in d.dept_yoy or []:
            dept_rows += (
                f'<tr><td class="dept-name"><strong>{dept_data["dept"]}</strong></td>'
                f'<td class="num-cell">{fmt_wan(dept_data["ci"])}</td>'
                f'<td class="num-cell muted">—</td>'
                f'<td class="yoy-cell flat"><span class="yoy-pct">N/A</span></td>'
                f'<td class="num-cell">{fmt_wan(dept_data["cp"])}</td>'
                f'<td class="num-cell muted">—</td>'
                f'<td class="yoy-cell flat"><span class="yoy-pct">N/A</span></td></tr>'
            )
        if not dept_rows:
            for dpt in DEPARTMENTS:
                iv = float(d.df_inc[d.df_inc["事业部"] == dpt]["金额_万"].sum()) if "事业部" in d.df_inc.columns else 0
                pv = float(d.df_pay[d.df_pay["事业部"] == dpt]["金额_万"].sum()) if "事业部" in d.df_pay.columns else 0
                dept_rows += (
                    f'<tr><td class="dept-name"><strong>{dpt}</strong></td>'
                    f'<td class="num-cell">{fmt_wan(iv)}</td><td class="num-cell muted">—</td>'
                    f'<td class="yoy-cell flat"><span class="yoy-pct">N/A</span></td>'
                    f'<td class="num-cell">{fmt_wan(pv)}</td><td class="num-cell muted">—</td>'
                    f'<td class="yoy-cell flat"><span class="yoy-pct">N/A</span></td></tr>'
                )

        h = ("<tr><th rowspan='2'>事业部</th>"
             "<th colspan='3' class='group-header inc-group'>收入</th>"
             "<th colspan='3' class='group-header pay-group'>回款</th></tr>"
             f"<tr><th>{d.cur_year}年</th><th>2024年</th><th>同比</th>"
             f"<th>{d.cur_year}年</th><th>2024年</th><th>同比</th></tr>")

        return (
            f'<div class="alert-banner" style="background:#fff7ed;border-left:4px solid #f59e0b">'
            f'<span style="font-size:14px">&#9888;</span>'
            f'<div style="flex:1"><strong>同比分析暂不可用</strong><br>'
            f'<span style="font-size:11px;color:var(--text-secondary)">缺少 2024 年基线数据，以下展示 {d.cur_year} 年各部门实际数据。</span></div>'
            f'</div>'
            + f'<div class="cols-3 kpi-strip">'
            f'<div class="card text-center"><div class="label-text">{d.cur_year}年收入</div><div class="kpi-value">{fmt_wan(d.ci)}<span class="unit">万</span></div></div>'
            f'<div class="card text-center"><div class="label-text">{d.cur_year}年回款</div><div class="kpi-value">{fmt_wan(d.cp)}<span class="unit">万</span></div></div>'
            f'<div class="card text-center"><div class="label-text">数据状态</div><div class="kpi-value" style="font-size:16px;color:var(--orange)">无对比基准</div></div>'
            f'</div>'
            + f'<div class="section-title sec-purple">事业部年度数据（万元）</div>'
            f'<div class="table-wrap no-collapse"><table class="yoy-dept-table"><thead>{h}</thead><tbody>{dept_rows}</tbody></table></div>'
        )

    def _kpi_block(self, ci, pvi, cp, pvp, cy) -> str:
        yoy_inc_pct = ((ci - pvi) / pvi * 100) if pvi else 0
        yoy_pay_pct = ((cp - pvp) / pvp * 100) if pvp else 0
        inc_cls = "up" if yoy_inc_pct > 0 else "down" if yoy_inc_pct < 0 else "flat"
        pay_cls = "up" if yoy_pay_pct > 0 else "down" if yoy_pay_pct < 0 else "flat"
        max_inc = max(ci, pvi) or 1; max_pay = max(cp, pvp) or 1
        return f"""<div class="cols-2">
  <div class="yoy-big-card {inc_cls}">
    <div class="yoy-big-info">
      <div class="yoy-big-label">收入同比</div>
      <div class="yoy-big-pct">
        <span class="yoy-arrow {inc_cls}">{yoy_arrow(ci, pvi)}</span>
        <span class="yoy-big-pct-num">{yoy_inc_pct:+.1f}%</span>
      </div>
    </div>
    <div class="yoy-big-compare">
      <div class="yoy-cmp-item">
        <div class="yoy-cmp-header">
          <span class="yoy-cmp-label">{cy}年（当期）</span>
          <span class="yoy-cmp-val">{fmt_wan(ci)}<span class="yoy-cmp-unit">万</span></span>
        </div>
        <div class="yoy-cmp-bar"><div class="yoy-cmp-fill cur {inc_cls}" style="width:{ci/max_inc*100:.1f}%"></div></div>
      </div>
      <div class="yoy-cmp-item">
        <div class="yoy-cmp-header">
          <span class="yoy-cmp-label">2024年（同期）</span>
          <span class="yoy-cmp-val">{fmt_wan(pvi)}<span class="yoy-cmp-unit">万</span></span>
        </div>
        <div class="yoy-cmp-bar"><div class="yoy-cmp-fill prev" style="width:{pvi/max_inc*100:.1f}%"></div></div>
      </div>
    </div>
  </div>
  <div class="yoy-big-card {pay_cls}">
    <div class="yoy-big-info">
      <div class="yoy-big-label">回款同比</div>
      <div class="yoy-big-pct">
        <span class="yoy-arrow {pay_cls}">{yoy_arrow(cp, pvp)}</span>
        <span class="yoy-big-pct-num">{yoy_pay_pct:+.1f}%</span>
      </div>
    </div>
    <div class="yoy-big-compare">
      <div class="yoy-cmp-item">
        <div class="yoy-cmp-header">
          <span class="yoy-cmp-label">{cy}年（当期）</span>
          <span class="yoy-cmp-val">{fmt_wan(cp)}<span class="yoy-cmp-unit">万</span></span>
        </div>
        <div class="yoy-cmp-bar"><div class="yoy-cmp-fill cur {pay_cls}" style="width:{cp/max_pay*100:.1f}%"></div></div>
      </div>
      <div class="yoy-cmp-item">
        <div class="yoy-cmp-header">
          <span class="yoy-cmp-label">2024年（同期）</span>
          <span class="yoy-cmp-val">{fmt_wan(pvp)}<span class="yoy-cmp-unit">万</span></span>
        </div>
        <div class="yoy-cmp-bar"><div class="yoy-cmp-fill prev" style="width:{pvp/max_pay*100:.1f}%"></div></div>
      </div>
    </div>
  </div>
</div>"""

    def _dept_table(self, dept_yoy: list[dict], cy) -> str:
        rows = ""
        for d in dept_yoy:
            ci_d, pi_d = d["ci"], d["pi"]
            cp_d, pp_d = d["cp"], d["pp"]
            inc_pct = (ci_d - pi_d) / pi_d * 100 if pi_d else 0
            inc_cls = "up" if inc_pct > 0 else "down" if inc_pct < 0 else "flat"
            pay_pct = (cp_d - pp_d) / pp_d * 100 if pp_d else 0
            pay_cls = "up" if pay_pct > 0 else "down" if pay_pct < 0 else "flat"
            inc_big = ' data-big="true"' if abs(inc_pct) >= 50 else ""
            pay_big = ' data-big="true"' if abs(pay_pct) >= 50 else ""
            rows += (
                f'<tr><td class="dept-name"><strong>{d["dept"]}</strong></td>'
                f'<td class="num-cell">{fmt_wan(ci_d)}</td>'
                f'<td class="num-cell muted">{fmt_wan(pi_d)}</td>'
                f'<td class="yoy-cell {inc_cls}"{inc_big}><span class="yoy-pct">{yoy_arrow(ci_d, pi_d)}{inc_pct:+.0f}%</span></td>'
                f'<td class="num-cell">{fmt_wan(cp_d)}</td>'
                f'<td class="num-cell muted">{fmt_wan(pp_d)}</td>'
                f'<td class="yoy-cell {pay_cls}"{pay_big}><span class="yoy-pct">{yoy_arrow(cp_d, pp_d)}{pay_pct:+.0f}%</span></td></tr>'
            )

        h = ("<tr><th rowspan='2'>事业部</th>"
             "<th colspan='3' class='group-header inc-group'>收入</th>"
             "<th colspan='3' class='group-header pay-group'>回款</th></tr>"
             f"<tr><th>{cy}年</th><th>2024年</th><th>同比</th><th>{cy}年</th><th>2024年</th><th>同比</th></tr>")

        return (
            self.section("事业部同比对比（万元）", "sec-purple")
            + f'<div class="table-wrap no-collapse"><table class="yoy-dept-table"><thead>{h}</thead><tbody>{rows}</tbody></table></div>'
        )

    def _cust_matrix(self, cp, pp, top, cy, label, top_n) -> str:
        """客户同比矩阵 — 纯 HTML 生成"""
        if not top:
            return ""

        # 顶部合计行标签：取自配置（展示规则.json.年度同比.最大行数）
        if top_n and top_n > 0:
            top_label = f"前 {top_n}"
        else:
            top_label = "全部"

        def _amount_cell(cur, prev):
            if cur == 0 and prev == 0:
                return '<td class="mx-amount-cell td-empty">—</td>'
            return (
                f'<td class="mx-amount-cell">'
                f'<div class="mx-amount-pair">'
                f'<div class="mx-amt-row mx-cur-row"><span class="mx-amt-label">当年</span><span class="mx-amt-val">{fmt_wan(cur)}</span></div>'
                f'<div class="mx-amt-row mx-prev-row"><span class="mx-amt-label">往年</span><span class="mx-amt-val">{fmt_wan(prev)}</span></div>'
                f'</div></td>'
            )

        def _yoy_cell(cur, prev):
            if cur == 0 and prev == 0:
                return '<td class="mx-yoy-cell td-empty">—</td>'
            pct = (cur - prev) / prev * 100 if prev else 0
            cls = "up" if pct > 0 else "down" if pct < 0 else "flat"
            mag = abs(pct)
            sev = "x" if mag >= 100 else "l" if mag >= 50 else "m" if mag >= 10 else "s"
            arrow = "▲" if cls == "up" else "▼" if cls == "down" else "−"
            return (
                f'<td class="mx-yoy-cell {cls} sev-{sev}"><div class="mx-yoy-fill"></div>'
                f'<div class="mx-badge"><span class="mx-arrow">{arrow}</span><span class="mx-pct">{pct:+.0f}%</span></div></td>'
            )

        def _mcell(cur, prev):
            return _amount_cell(cur, prev) + _yoy_cell(cur, prev)

        # 合计行
        tc = [f'<td class="row-total-label">合计（{top_label}）</td>']  # noqa: E501
        for dpt in DEPARTMENTS:
            cv = sum(float(cp.loc[c, dpt]) for c in top if c in cp.index and dpt in cp.columns)
            pv = sum(float(pp.loc[c, dpt]) for c in top if pp is not None and c in pp.index and dpt in pp.columns) if pp is not None else 0
            tc.append(_mcell(cv, pv))
        cv_t = sum(float(cp.loc[c, "合计"]) for c in top if c in cp.index)
        pv_t = sum(float(pp.loc[c, "合计"]) for c in top if pp is not None and c in pp.index) if pp is not None else 0
        tc.append(_mcell(cv_t, pv_t))
        tr = f'<tr class="row-total">{"".join(tc)}</tr>'

        # 数据行
        rows = ""
        for i, c in enumerate(top, 1):
            cs = [f'<td class="td-name"><span class="row-num">{i}</span>{c}</td>']
            for dpt in DEPARTMENTS:
                cv = float(cp.loc[c, dpt]) if c in cp.index and dpt in cp.columns else 0
                pv = float(pp.loc[c, dpt]) if pp is not None and c in pp.index and dpt in pp.columns else 0
                cs.append(_mcell(cv, pv))
            cv_t = float(cp.loc[c, "合计"]) if c in cp.index else 0
            pv_t = float(pp.loc[c, "合计"]) if pp is not None and c in pp.index else 0
            cs.append(_mcell(cv_t, pv_t))
            rows += f"<tr class='row-data'>{''.join(cs)}</tr>"

        h_row1 = '<tr><th rowspan="2" class="th-name">客户</th>'
        for dpt in DEPARTMENTS:
            h_row1 += f'<th colspan="2" class="th-dept-group">{dpt}</th>'
        h_row1 += '<th colspan="2" class="th-dept-group th-dept-total">合计</th></tr>'
        h_row2 = '<tr>' + ''.join(
            '<th class="th-sub th-sub-amount">金额</th><th class="th-sub th-sub-yoy">同比</th>'
            for _ in range(len(DEPARTMENTS) + 1)
        ) + '</tr>'

        return (
            self.section(f"重要客户{label}同比 · 按事业部分列（万元，{top_label}）", "sec-purple")
            + f'<div class="table-wrap no-collapse"><table class="yoy-matrix-table"><thead>{h_row1}{h_row2}</thead><tbody>{tr}{rows}</tbody></table></div>'
        )
