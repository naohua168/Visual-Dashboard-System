"""销售达成页 — 3 卡片 × 收入/回款 双视图（纯视图层）
"""
from __future__ import annotations

import json

from .base import BaseRenderer, rate_cls, hero_rings_html
from .utils import fmt_wan, safe_float, range_banner_html
from .components import cell_bg_html, cust_tab_bar, mini_rate_row
from .page_data import prepare_sales_data, DEPARTMENTS
from .sales_pending import build_pending_modal


class SalesPage(BaseRenderer):
    page_id = "sales"
    nav_name = "销售达成"

    def render(self, data) -> str:
        d = prepare_sales_data(data, self.base_dir)

        hero = hero_rings_html(
            d.total_inc, d.total_target, d.total_pay, d.total_target,
            "", "收入", "回款",
            inc_yoy=d.yoy_inc, pay_yoy=d.yoy_pay, yoy_period=d.yoy_period,
            total_tgt=d.total_target, total_label="年度总指标",
            show_cust_sales=False,
        )

        parts = [range_banner_html(d.sales_range) + hero]

        # 卡片 1
        parts.append(self._card1(d))
        # 卡片 2
        parts.append(self._card2(d))
        # 卡片 3
        parts.append(self._card3(d))
        # 待确认
        if d.pending_count > 0:
            pending_html = build_pending_modal(
                d.pending_df, d.pending_count, d.pending_total_inc, d.pending_total_pay
            )
            if pending_html:
                parts.append(pending_html)

        return self.wrap_page("".join(parts), d.date_range)

    def _card1(self, d) -> str:
        """销售年度达成 — 左右双列：收入 | 回款，按各自完成度排序"""
        def _sorted_sales(by_sales):
            return sorted(
                [s for s in by_sales.keys() if d.sales_targets.get(str(s), 0) > 0],
                key=lambda s: float(by_sales.get(s, 0)) / d.sales_targets.get(str(s), 0),
                reverse=True,
            )

        def _col(by_sales, title):
            sales_sorted = _sorted_sales(by_sales)
            rows = ""
            for s_name in sales_sorted:
                ti = d.sales_targets.get(str(s_name), 0)
                act = float(by_sales.get(s_name, 0))
                rate = (act / ti) if ti else 0
                pct = round(rate * 100)
                if rate >= 0.8:
                    bar_cls = 'level-4'
                elif rate >= 0.5:
                    bar_cls = 'level-3'
                elif rate >= 0.3:
                    bar_cls = 'level-2'
                else:
                    bar_cls = 'level-1'
                rows += (
                    f'<div class="mini-rate">'
                    f'<span style="width:72px;font-weight:600">{s_name}</span>'
                    f'<div class="bar"><div class="bar-fill {bar_cls}" style="width:{min(rate*100,100):.1f}%"><span class="bar-pct">{pct}%</span></div></div>'
                    f'<span class="val">{fmt_wan(act)}</span>'
                    f'<span class="tgt">/{fmt_wan(ti)}</span>'
                    f'</div>'
                )
            return (
                f'<div class="card1-col">'
                f'<div class="card1-col-title">{title}</div>'
                f'<div class="mini-rate-list">{rows}</div></div>'
            )

        return (
            f'<div class="section-title sec-green">销售年度达成 · 个人收入/回款 vs 年度目标（按各自完成度排序）</div>'
            f'<div class="card back-white"><div class="card1-flex">'
            f'{_col(d.sales_inc, "收入（不含税）")}'
            f'{_col(d.sales_pay, "回款（含税）")}'
            f'</div></div>'
            f'<style>.card1-flex{{display:flex;gap:24px;padding:12px 16px}} .card1-col{{flex:1;min-width:0}} .card1-col-title{{font-weight:700;font-size:13px;margin-bottom:8px;padding-bottom:6px;border-bottom:2px solid var(--border);color:var(--text)}} .card1-col:nth-child(1) .card1-col-title{{border-color:#3b82f6}} .card1-col:nth-child(2) .card1-col-title{{border-color:#22c55e}}</style>'
        )

    def _card2(self, d) -> str:
        """销售 × 事业部 cell-bg 矩阵"""
        def _matrix(piv_data, all_sales):
            h = '<tr><th class="th-name">销售</th>' + "".join(
                f"<th>{dpt}</th>" for dpt in DEPARTMENTS
            ) + '<th class="th-name th-total">合计</th></tr>'
            rows = ""
            dept_tgt_sum = sum(d.dept_inc_tgt_total.values()) or 1

            for s_name in all_sales:
                s_total_tgt = d.sales_targets.get(str(s_name), 0)
                if s_total_tgt == 0:
                    continue
                cs = [f'<td class="td-name">{s_name}</td>']
                for dpt in DEPARTMENTS:
                    act = piv_data.get(str(s_name), {}).get(dpt, 0) if isinstance(piv_data, dict) else 0
                    prop = d.dept_inc_tgt_total.get(dpt, 0) / dept_tgt_sum
                    tgt_part = s_total_tgt * prop
                    cs.append(cell_bg_html(act, tgt_part, fmt_fn=fmt_wan))
                act_t = sum(piv_data.get(str(s_name), {}).get(dpt, 0) for dpt in DEPARTMENTS) if isinstance(piv_data, dict) else 0
                cs.append(cell_bg_html(act_t, s_total_tgt, is_total_col=True, fmt_fn=fmt_wan))
                rows += f'<tr class="row-data">{"".join(cs)}</tr>'

            if not rows:
                return '<p style="color:var(--text-muted);padding:20px;text-align:center">无销售目标数据</p>'
            return (
                f'<div class="table-wrap ann-matrix-wrap no-collapse">'
                f'<table class="ann-matrix"><thead>{h}</thead><tbody>{rows}</tbody></table></div>'
            )

        inc_matrix = _matrix(d.inc_by_sd, d.sales_list)
        pay_matrix = _matrix(d.pay_by_sd, d.sales_list)
        return (
            f'<div class="section-title sec-purple">事业部完成度 · 销售 × 事业部 矩阵</div>'
            + cust_tab_bar("sales-card2-inc", "sales-card2-pay")
            + f'<div id="sales-card2-inc"><div class="card">{inc_matrix}</div></div>'
            f'<div id="sales-card2-pay" class="hidden"><div class="card">{pay_matrix}</div></div>'
        )

    def _card3(self, d) -> str:
        """销售×客户达成度 — JS 驱动下拉"""
        all_sales = sorted(set(d.sales_list))
        sc3_json = json.dumps(d.sc3_data, ensure_ascii=False)
        tgt_json = json.dumps(d.sc3_tgts, ensure_ascii=False)

        kpi_html = (
            f'<div class="card3-kpi">'
            f'<span>收入实际 <b>{fmt_wan(d.total_inc)}</b>万</span><span class="dot">·</span>'
            f'<span>收入目标 <b>{fmt_wan(d.total_target)}</b>万</span><span class="dot">·</span>'
            f'<span>回款实际 <b>{fmt_wan(d.total_pay)}</b>万</span><span class="dot">·</span>'
            f'<span>回款目标 <b>{fmt_wan(d.total_target)}</b>万</span></div>'
        )

        js_script = _card3_js_script(sc3_json, tgt_json)

        return (
            f'<div class="section-title sec-green">销售客户达成 · 个人 × 客户 × 事业部 矩阵</div>'
            f'<div class="card">{kpi_html}'
            f'<div style="margin-bottom:8px;display:flex;align-items:center;gap:8px">'
            f'<label style="font-size:12px;color:var(--text-muted)">选择销售：</label>'
            f'<select id="sc3SalesSel" onchange="switchSc3Sales()">'
            + "".join(f'<option value="{s}">{s}</option>' for s in sorted(all_sales))
            + f'</select>'
            + cust_tab_bar("sc3-inc-matrix", "sc3-pay-matrix")
            + f'</div>'
            f'<div id="sc3-inc-matrix"><div class="table-wrap ann-matrix-wrap no-collapse">'
            f'<table class="ann-matrix" id="sc3IncTable"></table></div></div>'
            f'<div id="sc3-pay-matrix" class="hidden"><div class="table-wrap ann-matrix-wrap no-collapse">'
            f'<table class="ann-matrix" id="sc3PayTable"></table></div></div>'
            f'</div>'
            + js_script
        )


# ═══════════════════════════════════════════════════════════════
# 卡片 3 JS 生成器（独立函数）
# ═══════════════════════════════════════════════════════════════
def _card3_js_script(sc3_json: str, tgt_json: str) -> str:
    depts = json.dumps(DEPARTMENTS)
    return f'''<script>
const __SC3D = {sc3_json};
const __SC3T = {tgt_json};
const __SC3_DEPS = {depts};
let __sc3Metric = "inc";

function switchSc3Sales() {{
    const sel = document.getElementById("sc3SalesSel");
    const s = sel.value;
    const custs = __SC3D[s] || {{}};
    __sc3Build(custs);
}}

function switchSc3Metric(metric) {{
    __sc3Metric = metric;
    switchSc3Sales();
    document.querySelectorAll("#sc3-inc-matrix, #sc3-pay-matrix").forEach(el => el.classList.add("hidden"));
    document.getElementById(metric === "inc" ? "sc3-inc-matrix" : "sc3-pay-matrix").classList.remove("hidden");
}}

function __sc3Build(custs) {{
    const metric = __sc3Metric, deps = __SC3_DEPS;
    let h = "<tr><th class=\\u0027th-name\\u0027>客户</th>" +
        deps.map(d => `<th>${{d}}</th>`).join("") +
        '<th class="th-name th-total">合计</th></tr>';
    const sorted = Object.keys(custs).sort((a, b) => {{
        const tga = (__SC3T[a] && __SC3T[a][metric] && __SC3T[a][metric].total) || 0;
        const tgb = (__SC3T[b] && __SC3T[b][metric] && __SC3T[b][metric].total) || 0;
        return tgb - tga;
    }});
    let tRow = ['<td class="td-name td-total">合计（' + sorted.length + '家）</td>'];
    let allTotal = 0, allTgt = 0;
    deps.forEach(d => {{
        let sa = 0, st = 0;
        sorted.forEach(c => {{
            const v = custs[c] && custs[c][metric] ? (custs[c][metric][d] || 0) : 0;
            const t = __SC3T[c] && __SC3T[c][metric] ? (__SC3T[c][metric][d] || 0) : 0;
            sa += v; st += t;
        }});
        tRow.push(__sc3Cell(sa, st, false));
        allTotal += sa; allTgt += st;
    }});
    tRow.push(__sc3Cell(allTotal, allTgt, true));
    let body = '<tr class="row-total">' + tRow.join("") + '</tr>';
    sorted.forEach((c, i) => {{
        let row = [`<td class="td-name"><span class="row-num">${{i + 1}}</span>${{c}}</td>`];
        let rTotal = 0, rTgt = 0;
        deps.forEach(d => {{
            const v = custs[c] && custs[c][metric] ? (custs[c][metric][d] || 0) : 0;
            const t = __SC3T[c] && __SC3T[c][metric] ? (__SC3T[c][metric][d] || 0) : 0;
            row.push(__sc3Cell(v, t, false));
            rTotal += v; rTgt += t;
        }});
        row.push(__sc3Cell(rTotal, rTgt, true));
        body += '<tr class="row-data">' + row.join("") + '</tr>';
    }});
    const html = '<thead>' + h + '</thead><tbody>' + body + '</tbody>';
    document.getElementById("sc3IncTable").innerHTML = metric === "inc" ? html : "";
    document.getElementById("sc3PayTable").innerHTML = metric === "pay" ? html : "";
}}

function __sc3Cell(act, tgt, isTotal) {{
    const _fmt = v => v ? Number(v).toLocaleString("zh-CN", {{maximumFractionDigits: 0}}) : "—";
    if (act === 0 && tgt === 0) return '<td class="td-empty">—</td>';
    const rate = tgt > 0 ? act / tgt : 0;
    const pct = Math.min(rate * 100, 100);
    const pctLab = Math.round(rate * 100) + "%";
    let fill = "#f1f5f9", pctCls = "";
    if (rate >= 1) {{ fill = "#22c55e"; pctCls = " achieved"; }}
    else if (rate >= 0.5) {{ fill = "#fb923c"; }}
    else if (rate > 0) {{ fill = "#fdba74"; pctCls = " low"; }}
    const totalCls = isTotal ? " is-total" : "";
    const emptyCls = rate === 0 ? " is-empty" : "";
    return `<td class="cell-bg${{emptyCls}}${{totalCls}}" style="--pct:${{pct}}%;--fill:${{fill}}">`
        + `<div class="fill-bg"></div><div class="cell-text">`
        + `<span class="cell-pct${{pctCls}}">${{pctLab}}</span>`
        + `<div class="cell-main"><span class="cell-compact"><span class="cell-act-val">${{_fmt(act)}}</span>`
        + `<span class="sep">/</span><span class="cell-tgt-val">${{_fmt(tgt)}}</span></span></div></div></td>`;
}}

document.addEventListener("DOMContentLoaded", () => {{
    if (document.getElementById("sc3SalesSel") && document.getElementById("sc3SalesSel").value) {{
        switchSc3Sales();
    }}
}});
</script>'''
