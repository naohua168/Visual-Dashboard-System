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
            total_tgt=None, total_label="",
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
        """销售年度达成 — 左右双列：收入 | 回款，按各自完成度排序。整行可点击弹出客户详情"""

        def _sorted_sales(by_sales):
            return sorted(
                [s for s in by_sales.keys() if d.sales_targets.get(str(s), 0) > 0],
                key=lambda s: float(by_sales.get(s, 0)) / d.sales_targets.get(str(s), 0),
                reverse=True,
            )

        def _col(by_sales, title, total_act, total_tgt, metric):
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
                    f'<div class="mini-rate sales-clickable"'
                    f' data-sales="{s_name}" data-metric="{metric}"'
                    f' onclick="openSalesModal(this, \'{s_name}\',\'{metric}\')"'
                    f' title="点击查看 {s_name} 客户达成详情">'
                    f'<span class="sales-name">{s_name}</span>'
                    f'<div class="bar"><div class="bar-fill {bar_cls}" style="width:{min(rate*100,100):.1f}%"><span class="bar-pct">{pct}%</span></div></div>'
                    f'<span class="val">{fmt_wan(act)}</span>'
                    f'<span class="tgt">/{fmt_wan(ti)}</span>'
                    f'</div>'
                )
            # 合计行
            total_rate = total_act / total_tgt if total_tgt else 0
            rpct = round(total_rate * 100)
            summary = (
                f'<div class="mini-rate summary-rate">'
                f'<span class="sales-name" style="font-weight:700">合计</span>'
                f'<div class="bar"><div class="bar-fill level-4" style="width:{min(total_rate*100,100):.1f}%"><span class="bar-pct">{rpct}%</span></div></div>'
                f'<span class="val">{fmt_wan(total_act)}</span>'
                f'<span class="tgt">/{fmt_wan(total_tgt)}</span>'
                f'</div>'
            )
            return (
                f'<div class="card1-col">'
                f'<div class="card1-col-title">{title}</div>'
                f'<div class="mini-rate-list">{summary}{rows}</div></div>'
            )

        return (
            f'<div class="section-title sec-green">销售年度达成 · 个人收入/回款 vs 年度目标（点击销售查看客户达成详情）</div>'
            f'<div class="card back-white"><div class="card1-flex">'
            f'{_col(d.sales_inc, "收入（不含税）", d.total_inc_split, d.total_target, "inc")}'
            f'{_col(d.sales_pay, "回款（含税）", d.total_pay_split, d.total_target, "pay")}'
            f'</div></div>'
            + _sales_modal_css()
            + _sales_modal_html()
        )

    def _card2(self, d) -> str:
        """销售 × 事业部 cell-bg 矩阵 — 目标直接用 sales_dept_tgt（按销售×部门精确指标）"""
        def _matrix(piv_data, all_sales):
            h = '<tr><th class="th-name">销售</th>' + "".join(
                f"<th>{dpt}</th>" for dpt in DEPARTMENTS
            ) + '<th class="th-name th-total">合计</th></tr>'
            rows = ""

            for s_name in all_sales:
                s_total_tgt = d.sales_targets.get(str(s_name), 0)
                if s_total_tgt == 0:
                    continue
                s_dept_tgt = d.sales_dept_tgt.get(str(s_name), {})
                cs = [f'<td class="td-name">{s_name}</td>']
                for dpt in DEPARTMENTS:
                    act = piv_data.get(str(s_name), {}).get(dpt, 0) if isinstance(piv_data, dict) else 0
                    tgt_part = s_dept_tgt.get(dpt, 0)
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
        pay_matrix = _matrix(d.pay_by_sd, d.pay_sales_list)
        return (
            f'<div class="section-title sec-purple">事业部完成度 · 销售 × 事业部 矩阵</div>'
            + cust_tab_bar("sales-card2-inc", "sales-card2-pay")
            + f'<div id="sales-card2-inc"><div class="card">{inc_matrix}</div></div>'
            f'<div id="sales-card2-pay" class="hidden"><div class="card">{pay_matrix}</div></div>'
        )

    def _card3(self, d) -> str:
        """销售×客户达成度 — 母公司→子公司 聚合视图（JS 驱动下拉）"""
        all_sales = sorted(set(d.sales_list))
        parent_json = json.dumps(d.sc3_by_parent, ensure_ascii=False)
        sub_tgt_json = json.dumps(d.sc3_tgts, ensure_ascii=False)
        parent_tgt_json = json.dumps(d.sc3_tgts_by_parent, ensure_ascii=False)

        kpi_html = (
            f'<div class="card3-kpi">'
            f'<span>收入实际 <b>{fmt_wan(d.total_inc)}</b>万</span><span class="dot">·</span>'
            f'<span>收入目标 <b>{fmt_wan(d.total_target)}</b>万</span><span class="dot">·</span>'
            f'<span>回款实际 <b>{fmt_wan(d.total_pay)}</b>万</span><span class="dot">·</span>'
            f'<span>回款目标 <b>{fmt_wan(d.total_target)}</b>万</span></div>'
        )

        js_script = _card3_js_script(parent_json, sub_tgt_json, parent_tgt_json)

        return (
            f'<div class="section-title sec-green">销售客户达成 · 母公司→子公司 矩阵（子公司合计 = 母公司合计）</div>'
            f'<div class="card">{kpi_html}'
            f'<div style="margin-bottom:8px;display:flex;align-items:center;gap:8px">'
            f'<label style="font-size:12px;color:var(--text-muted)">选择销售：</label>'
            f'<select id="sc3SalesSel" onchange="switchSc3Sales()">'
            + "".join(f'<option value="{s}">{s}</option>' for s in sorted(all_sales))
            + f'</select>'
            + '<div class="cust-tabs">'
            + '<span class="cust-tab active inc" onclick="switchSc3Metric(\'inc\');document.getElementById(\'sc3-inc-matrix\').classList.remove(\'hidden\');document.getElementById(\'sc3-pay-matrix\').classList.add(\'hidden\');this.parentElement.querySelectorAll(\'.cust-tab\').forEach(t=>t.classList.remove(\'active\'));this.classList.add(\'active\')">收入</span>'
            + '<span class="cust-tab pay" onclick="switchSc3Metric(\'pay\');document.getElementById(\'sc3-inc-matrix\').classList.add(\'hidden\');document.getElementById(\'sc3-pay-matrix\').classList.remove(\'hidden\');this.parentElement.querySelectorAll(\'.cust-tab\').forEach(t=>t.classList.remove(\'active\'));this.classList.add(\'active\')">回款</span>'
            + '</div>'
            + f'</div>'
            f'<div id="sc3-inc-matrix"><div class="table-wrap ann-matrix-wrap no-collapse">'
            f'<table class="ann-matrix" id="sc3IncTable"></table></div></div>'
            f'<div id="sc3-pay-matrix" class="hidden"><div class="table-wrap ann-matrix-wrap no-collapse">'
            f'<table class="ann-matrix" id="sc3PayTable"></table></div></div>'
            f'</div>'
            + js_script
        )


# ═══════════════════════════════════════════════════════════════
# 卡片 3 JS 生成器（母公司→子公司聚合视图）
# ═══════════════════════════════════════════════════════════════
def _card3_js_script(parent_json: str, sub_tgt_json: str, parent_tgt_json: str) -> str:
    depts = json.dumps(DEPARTMENTS)
    return f'''<script>
window.__SC3P = {parent_json};   // 升级为全局变量，弹窗复用
window.__SC3ST = {sub_tgt_json};
window.__SC3PT = {parent_tgt_json};
const __SC3_DEPS = {depts};
let __sc3Metric = "inc";

function switchSc3Sales() {{
    const sel = document.getElementById("sc3SalesSel");
    const s = sel.value;
    const parents = __SC3P[s] || {{}};
    __sc3Build(parents);
}}

function switchSc3Metric(metric) {{
    __sc3Metric = metric;
    switchSc3Sales();
    document.querySelectorAll("#sc3-inc-matrix, #sc3-pay-matrix").forEach(el => el.classList.add("hidden"));
    document.getElementById(metric === "inc" ? "sc3-inc-matrix" : "sc3-pay-matrix").classList.remove("hidden");
}}

function __sc3Build(parents) {{
    const metric = __sc3Metric, deps = __SC3_DEPS;
    // 母公司按目标降序排列
    const parentKeys = Object.keys(parents).sort((a, b) => {{
        const ta = (__SC3PT[a] && __SC3PT[a][metric] && __SC3PT[a][metric].total) || 0;
        const tb = (__SC3PT[b] && __SC3PT[b][metric] && __SC3PT[b][metric].total) || 0;
        return tb - ta;
    }});

    let allSubs = 0;
    parentKeys.forEach(p => {{ allSubs += Object.keys(parents[p]).length; }});

    let h = "<tr><th class=\\u0027th-name\\u0027>母公司 / 子公司（" + allSubs + "家子公司）</th>" +
        deps.map(d => `<th>${{d}}</th>`).join("") +
        '<th class="th-name th-total">合计</th></tr>';
    let body = '';

    parentKeys.forEach(p => {{
        const subs = parents[p];
        const subKeys = Object.keys(subs).sort((a, b) => {{
            const ta = (__SC3ST[a] && __SC3ST[a][metric] && __SC3ST[a][metric].total) || 0;
            const tb = (__SC3ST[b] && __SC3ST[b][metric] && __SC3ST[b][metric].total) || 0;
            return tb - ta;
        }});
        if (subKeys.length === 0) return;

        // 母公司标题行
        let pTarget = (__SC3PT[p] && __SC3PT[p][metric] && __SC3PT[p][metric].total) || 0;
        let pRow = [`<td class="td-name parent-name" colspan="${{deps.length + 2}}" style="text-align:left;font-weight:800;color:#0f172a;background:#f1f5f9;padding:6px 8px;font-size:13px">${{p}} (${{subKeys.length}}家子公司)</td>`];
        body += '<tr class="row-parent">' + pRow.join("") + '</tr>';

        // 子公司行
        let parentTotalAct = 0, parentTotalTgt = 0;
        let parentDepsAct = deps.map(() => 0);
        let parentDepsTgt = deps.map(() => 0);

        subKeys.forEach((c, i) => {{
            let row = [`<td class="td-name"><span class="row-num" style="color:#94a3b8">${{i + 1}}</span>${{c}}</td>`];
            let rTotal = 0, rTgt = 0;
            deps.forEach((d, di) => {{
                const v = subs[c] && subs[c][metric] ? (subs[c][metric][d] || 0) : 0;
                const t = __SC3ST[c] && __SC3ST[c][metric] ? (__SC3ST[c][metric][d] || 0) : 0;
                row.push(__sc3Cell(v, t, false));
                rTotal += v; rTgt += t;
                parentDepsAct[di] += v;
                parentDepsTgt[di] += t;
            }});
            row.push(__sc3Cell(rTotal, rTgt, true));
            parentTotalAct += rTotal;
            parentTotalTgt += rTgt;
            body += '<tr class="row-data">' + row.join("") + '</tr>';
        }});

        // 母公司合计行
        let pSubRow = [`<td class="td-name" style="font-weight:700;background:#f8fafc">└ 母公司合计</td>`];
        deps.forEach((d, di) => {{
            pSubRow.push(__sc3Cell(parentDepsAct[di], parentDepsTgt[di], false));
        }});
        pSubRow.push(__sc3Cell(parentTotalAct, parentTotalTgt, true));
        body += '<tr class="row-data row-parent-total" style="background:#f8fafc">' + pSubRow.join("") + '</tr>';
    }});

    if (!body) {{
        body = '<tr><td colspan="' + (deps.length + 2) + '" style="text-align:center;padding:20px;color:var(--text-muted)">该销售当前无数据</td></tr>';
    }}
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
    let fc = "fy", pctCls = "";
    if (rate >= 1) {{ fc = "fg"; pctCls = " achieved"; }}
    else if (rate >= 0.5) {{ fc = "fo"; }}
    else if (rate > 0) {{ fc = "fl"; pctCls = " low"; }}
    const totalCls = isTotal ? " is-total" : "";
    const emptyCls = rate === 0 ? " is-empty" : "";
    return `<td class="cb${{emptyCls}}${{totalCls}} ${{fc}}" style="--pct:${{pct}}%">`
        + `<div class="ct"><span class="cp${{pctCls}}">${{pctLab}}</span>`
        + `<div class="cm"><span class="cc"><span class="ca">${{_fmt(act)}}</span>`
        + `<span class="s">/</span><span class="ctv">${{_fmt(tgt)}}</span></span></div></div></td>`;
}}

document.addEventListener("DOMContentLoaded", () => {{
    if (document.getElementById("sc3SalesSel") && document.getElementById("sc3SalesSel").value) {{
        switchSc3Sales();
    }}
}});
</script>'''


# ═══════════════════════════════════════════════════════════════
# 销售客户详情弹窗 — CSS / HTML / JS
# ═══════════════════════════════════════════════════════════════
def _sales_modal_css() -> str:
    return '''<style>
/* 卡片1 布局 */
.card1-flex{display:flex;gap:24px;padding:12px 16px} .card1-col{flex:1;min-width:0}
.card1-col-title{font-weight:700;font-size:13px;margin-bottom:8px;padding-bottom:6px;border-bottom:2px solid var(--border);color:var(--text)}
.card1-col:nth-child(1) .card1-col-title{border-color:#3b82f6} .card1-col:nth-child(2) .card1-col-title{border-color:#22c55e}
.mini-rate.summary-rate{border-bottom:2px solid var(--border);padding-bottom:6px;margin-bottom:8px}
.summary-rate .bar{height:16px} .summary-rate .bar-pct{font-weight:700}

/* 可点击销售行 */
.sales-clickable { cursor: pointer; border-radius: 4px; transition: background 0.15s; }
.sales-clickable:hover { background: rgba(59,130,246,0.06); }
.sales-name { width: 72px; font-weight: 600; user-select: none; }

/* 当前激活的销售行（高亮锚点） */
.sales-clickable.sales-active {
    background: rgba(59,130,246,0.10);
    box-shadow: 0 0 0 1px rgba(59,130,246,0.35);
}

/* 抽屉遮罩 — 半透明，点击关闭 */
.sales-modal-overlay {
    display: block; position: fixed; inset: 0; z-index: 20000;
    background: rgba(0,0,0,0.35);
    opacity: 0; pointer-events: none;
    transition: opacity 0.25s ease;
}
.sales-modal-overlay.show { opacity: 1; pointer-events: auto; }

/* 抽屉面板 — 右侧滑入 */
.sales-modal {
    position: fixed; right: 0; top: 0;
    width: min(96vw, 900px); height: 100vh;
    transform: translateX(100%);
    z-index: 20001;
    background: #fff; border-radius: 14px 0 0 14px;
    display: flex; flex-direction: column;
    overflow: hidden;
    box-shadow: -10px 0 40px rgba(0,0,0,0.18);
    transition: transform 0.3s cubic-bezier(0.16,1,0.3,1);
}
.sales-modal.show { transform: translateX(0); }

/* 抽屉头部 */
.sales-modal-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 16px 20px 12px; border-bottom: 1px solid #e2e8f0; flex-shrink: 0;
}
.sales-modal-title { font-size: 16px; font-weight: 700; color: #0f172a; }
.sales-modal-sub { font-size: 12px; color: #64748b; margin-top: 2px; }
.sales-modal-close {
    width: 32px; height: 32px; border: none; background: none;
    font-size: 20px; color: #94a3b8; cursor: pointer; border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.15s;
}
.sales-modal-close:hover { background: #f1f5f9; color: #0f172a; }

/* 抽屉 Tab 栏 */
.sales-modal-tabs { display: flex; gap: 0; border-bottom: 2px solid #e2e8f0; flex-shrink: 0; }
.sales-modal-tab {
    padding: 10px 24px; font-size: 13px; font-weight: 600; cursor: pointer;
    border: none; background: none; color: #94a3b8; transition: all 0.15s;
    border-bottom: 2px solid transparent; margin-bottom: -2px;
}
.sales-modal-tab:hover { color: #64748b; }
.sales-modal-tab.active { color: #3b82f6; border-bottom-color: #3b82f6; }
.sales-modal-tab.pay.active { color: #22c55e; border-bottom-color: #22c55e; }

/* 抽屉内容区 */
.sales-modal-body { flex: 1 1 auto; padding: 12px 0; min-height: 0; overflow-y: auto; overflow-x: auto; }

/* 弹窗 KPI */
.modal-kpi {
    display: flex; gap: 16px; padding: 8px 20px; font-size: 12px; color: #64748b;
    border-bottom: 1px solid #f1f5f9; flex-wrap: wrap;
}
.modal-kpi b { color: #0f172a; }

/* 弹窗内表格 不嵌套滚动框 */
.sales-modal-body .ann-matrix-wrap { overflow: visible; }
.sales-modal-body .ann-matrix { width: 100%; border-collapse: collapse; font-size: 12px; }
.sales-modal-body .ann-matrix th {
    position: sticky; top: 0; z-index: 2; background: #f8fafc;
    padding: 8px 6px; font-size: 11px; color: #64748b; white-space: nowrap;
}
.sales-modal-body .ann-matrix td { padding: 4px 6px; white-space: nowrap; }
.sales-modal-body .ann-matrix .td-name { white-space: normal; }
.sales-modal-body .ann-matrix .parent-name {
    font-weight: 800; font-size: 12px; color: #0f172a;
    background: #f1f5f9; padding: 6px 8px;
}
.sales-modal-body .row-parent-total td { background: #f8fafc; font-weight: 600; }
.sales-modal-body .highlight-row td { background: rgba(59,130,246,0.04) !important; }
.sales-modal-empty { text-align: center; padding: 40px; color: #94a3b8; font-size: 13px; }
</style>'''


def _sales_modal_html() -> str:
    """弹窗 HTML + JS"""
    deps_json = json.dumps(DEPARTMENTS)
    return f'''<div id="salesModalOverlay" class="sales-modal-overlay">
<div class="sales-modal" id="salesModal">
    <div class="sales-modal-header">
        <div>
            <div class="sales-modal-title" id="salesModalTitle">销售客户详情</div>
            <div class="sales-modal-sub" id="salesModalSub">—</div>
        </div>
        <button class="sales-modal-close" onclick="closeSalesModal()" title="关闭">&times;</button>
    </div>
    <div class="sales-modal-tabs" id="salesModalTabs">
        <button class="sales-modal-tab active" data-metric="inc" onclick="switchSalesModalMetric('inc')">收入</button>
        <button class="sales-modal-tab pay" data-metric="pay" onclick="switchSalesModalMetric('pay')">回款</button>
    </div>
    <div class="sales-modal-body" id="salesModalBody"></div>
</div>
</div>
<script>
(() => {{
    const _DEPS = {deps_json};
    let _curSales = '', _curMetric = 'inc', _activeAnchor = null;

    const _overlay = document.getElementById('salesModalOverlay');
    const _modal = document.getElementById('salesModal');
    let _bodyOverflow = '';

    // ── 打开抽屉 ──
    window.openSalesModal = function(anchor, salesName, metric) {{
        _curSales = salesName;
        _curMetric = metric;
        document.getElementById('salesModalTitle').textContent = salesName;
        document.getElementById('salesModalSub').textContent = '收入/回款客户达成详情';
        // 高亮当前锚点
        if (_activeAnchor) _activeAnchor.classList.remove('sales-active');
        _activeAnchor = anchor;
        if (anchor) anchor.classList.add('sales-active');
        // 更新 Tab 高亮
        const tabs = document.querySelectorAll('#salesModalTabs .sales-modal-tab');
        tabs.forEach(t => t.classList.toggle('active', t.dataset.metric === metric));
        _renderModal();

        // 锁定背景滚动
        _bodyOverflow = document.body.style.overflow;
        document.body.style.overflow = 'hidden';

        _overlay.classList.add('show');
        _modal.classList.add('show');
    }}

    // ── 关闭抽屉 ──
    window.closeSalesModal = function() {{
        _modal.classList.remove('show');
        _overlay.classList.remove('show');
        // 恢复背景滚动
        document.body.style.overflow = _bodyOverflow || '';
        if (_activeAnchor) {{
            _activeAnchor.classList.remove('sales-active');
            _activeAnchor = null;
        }}
    }}

    // ── 点击遮罩关闭 ──
    _overlay.addEventListener('mousedown', function(e) {{
        if (e.target === _overlay) closeSalesModal();
    }});

    // ── 点击抽屉内部不冒泡到遮罩 ──
    _modal.addEventListener('mousedown', function(e) {{
        e.stopPropagation();
    }});

    // ── Tab 切换 ──
    window.switchSalesModalMetric = function(metric) {{
        _curMetric = metric;
        const tabs = document.querySelectorAll('#salesModalTabs .sales-modal-tab');
        tabs.forEach(t => t.classList.toggle('active', t.dataset.metric === metric));
        _renderModal();
    }}

    // ── 计算某母公司的总实际/总目标 ──
    function _parentTotals(parents, p) {{
        let act = 0, tgt = 0;
        const subs = parents[p] || {{}};
        Object.keys(subs).forEach(c => {{
            _DEPS.forEach(d => {{
                act += subs[c] && subs[c][_curMetric] ? (subs[c][_curMetric][d] || 0) : 0;
                tgt += window.__SC3ST[c] && window.__SC3ST[c][_curMetric] ? (window.__SC3ST[c][_curMetric][d] || 0) : 0;
            }});
        }});
        return [act, tgt];
    }}

    // ── 构建内容：母公司→子公司矩阵，按完成度降序 ──
    function _renderModal() {{
        const parents = (window.__SC3P && window.__SC3P[_curSales]) || {{}};
        // 按完成度降序排列母公司
        const parentKeys = Object.keys(parents).sort((a, b) => {{
            const [aA, aT] = _parentTotals(parents, a);
            const [bA, bT] = _parentTotals(parents, b);
            const ra = aT > 0 ? aA / aT : 0;
            const rb = bT > 0 ? bA / bT : 0;
            return rb - ra;
        }});

        if (parentKeys.length === 0) {{
            document.getElementById('salesModalBody').innerHTML = '<div class="sales-modal-empty">该销售暂无客户数据</div>';
            return;
        }}

        let totalAct = 0, totalTgt = 0, totalSubs = 0;
        let h = '<thead><tr><th class="th-name">客户</th>' + _DEPS.map(d => `<th>${{d}}</th>`).join('') + '<th class="th-name th-total">合计</th></tr></thead>';
        let body = '';

        parentKeys.forEach(p => {{
            const subs = parents[p];
            const subKeys = Object.keys(subs);
            if (subKeys.length === 0) return;

            body += `<tr class="row-parent"><td class="parent-name" colspan="${{_DEPS.length + 2}}">${{p}} (${{subKeys.length}}家子公司)</td></tr>`;

            let pActAll = 0, pTgtAll = 0;
            subKeys.forEach(c => {{
                let row = [`<td class="td-name">${{c}}</td>`];
                let rAct = 0, rTgt = 0;
                _DEPS.forEach(d => {{
                    const v = subs[c] && subs[c][_curMetric] ? (subs[c][_curMetric][d] || 0) : 0;
                    const t = window.__SC3ST[c] && window.__SC3ST[c][_curMetric] ? (window.__SC3ST[c][_curMetric][d] || 0) : 0;
                    row.push(_modalCell(v, t));
                    rAct += v; rTgt += t;
                }});
                row.push(_modalCell(rAct, rTgt, true));
                pActAll += rAct; pTgtAll += rTgt;
                body += '<tr class="row-data">' + row.join('') + '</tr>';
            }});

            // 母公司合计行
            let pSumRow = [`<td class="td-name" style="font-weight:700;background:#f8fafc">母公司合计</td>`];
            _DEPS.forEach(d => {{
                let dAct = 0, dTgt = 0;
                subKeys.forEach(c => {{
                    dAct += subs[c] && subs[c][_curMetric] ? (subs[c][_curMetric][d] || 0) : 0;
                    dTgt += window.__SC3ST[c] && window.__SC3ST[c][_curMetric] ? (window.__SC3ST[c][_curMetric][d] || 0) : 0;
                }});
                pSumRow.push(_modalCell(dAct, dTgt));
            }});
            pSumRow.push(_modalCell(pActAll, pTgtAll, true));
            body += '<tr class="row-data row-parent-total">' + pSumRow.join('') + '</tr>';

            totalAct += pActAll; totalTgt += pTgtAll;
            totalSubs += subKeys.length;
        }});

        if (!body) {{
            body = '<tr><td colspan="' + (_DEPS.length + 2) + '" style="text-align:center;padding:20px;color:#94a3b8">无数据</td></tr>';
        }}

        const totalRate = totalTgt > 0 ? totalAct / totalTgt : 0;
        const html = '<div class="modal-kpi">'
            + '<span>客户数 <b>' + parentKeys.length + '家母公司 / ' + totalSubs + '家子公司</b></span>'
            + '<span>实际 <b>' + totalAct.toLocaleString("zh-CN", {{maximumFractionDigits:0}}) + '万</b></span>'
            + '<span>目标 <b>' + totalTgt.toLocaleString("zh-CN", {{maximumFractionDigits:0}}) + '万</b></span>'
            + '<span>完成度 <b>' + Math.round(totalRate * 100) + '%</b></span>'
            + '</div>'
            + '<div class="table-wrap ann-matrix-wrap"><table class="ann-matrix">' + h + '<tbody>' + body + '</tbody></table></div>';
        document.getElementById('salesModalBody').innerHTML = html;
    }}

    function _modalCell(act, tgt, isTotal) {{
        const _f = v => v ? Number(v).toLocaleString("zh-CN", {{maximumFractionDigits:0}}) : "—";
        if (act === 0 && tgt === 0) return '<td class="td-empty">—</td>';
        const rate = tgt > 0 ? act / tgt : 0;
        const pct = Math.min(rate * 100, 100);
        const pctLab = Math.round(rate * 100) + "%";
        let fc = "fy", pctCls = "";
        if (rate >= 1) {{ fc = "fg"; pctCls = " achieved"; }}
        else if (rate >= 0.5) {{ fc = "fo"; }}
        else if (rate > 0) {{ fc = "fl"; pctCls = " low"; }}
        const tc = isTotal ? " is-total" : "";
        const ec = rate === 0 ? " is-empty" : "";
        return `<td class="cb${{ec}}${{tc}} ${{fc}}" style="--pct:${{pct}}%">`
            + `<div class="ct"><span class="cp${{pctCls}}">${{pctLab}}</span>`
            + `<div class="cm"><span class="cc"><span class="ca">${{_f(act)}}</span>`
            + `<span class="s">/</span><span class="ctv">${{_f(tgt)}}</span></span></div></div></td>`;
    }}

    // ── ESC 关闭 ──
    document.addEventListener('keydown', function(e) {{
        if (e.key === 'Escape') closeSalesModal();
    }});

    // ── 表格 Hover 高亮 ──
    document.addEventListener('mouseover', function(e) {{
        const tr = e.target.closest('#salesModalBody tr.row-data');
        if (!tr) return;
        const tbody = tr.parentElement;
        const idx = Array.from(tbody.querySelectorAll('tr.row-data')).indexOf(tr);
        if (idx >= 0) {{
            tbody.querySelectorAll('tr.row-data').forEach((r, i) => {{
                r.classList.toggle('highlight-row', i === idx);
            }});
        }}
    }});
}})();
</script>'''
