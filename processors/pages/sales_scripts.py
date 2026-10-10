# Author: naohua168 <bai_bai168@qq.com>
"""销售达成页 · 卡片3（销售×客户达成度）前端脚本

由 pages/sales.py 拆分而来：下拉选销售 → 渲染 收入/回款 两套客户矩阵。"""
from __future__ import annotations

import json
from ..data_utils import DEPARTMENTS


def _card3_js_script(parent_json: str, sub_tgt_json: str, parent_tgt_json: str,
                      sub_tgt_by_sales_json: str, parent_tgt_by_sales_json: str,
                      parent_cfg_total_json: str, sales_owned_json: str) -> str:
    depts = json.dumps(DEPARTMENTS)
    return f'''<script>
window.__SC3P = {parent_json};   // 升级为全局变量，弹窗复用
window.__SC3ST = {sub_tgt_json};
window.__SC3PT = {parent_tgt_json};
// 按销售拆分的目标（销售个人比例口径）
window.__SC3ST_S = {sub_tgt_by_sales_json};
window.__SC3PT_S = {parent_tgt_by_sales_json};
window.__SC3PCT = {parent_cfg_total_json};
window.__SC3OWNED = {sales_owned_json};
const __SC3_DEPS = {depts};
let __sc3Metric = "inc";
let __sc3CurSales = "";

// 当前销售的目标读取（客户级 + 母公司级）
function __sc3CustTgt(cust, metric) {{
    const sd = (window.__SC3ST_S && window.__SC3ST_S[__sc3CurSales]) || {{}};
    return (sd[cust] && sd[cust][metric]) || null;
}}
function __sc3ParentTgt(parent, metric) {{
    const pd = (window.__SC3PT_S && window.__SC3PT_S[__sc3CurSales]) || {{}};
    return (pd[parent] && pd[parent][metric]) || null;
}}

function switchSc3Sales() {{
    const sel = document.getElementById("sc3SalesSel");
    const s = sel.value;
    __sc3CurSales = s;
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
    // 母公司按当前销售的目标降序排列（无个人目标则用全销售目标兜底）
    const parentKeys = Object.keys(parents).sort((a, b) => {{
        const ta = (__sc3ParentTgt(a, metric) && __sc3ParentTgt(a, metric).total) || (__SC3PT[a] && __SC3PT[a][metric] && __SC3PT[a][metric].total) || 0;
        const tb = (__sc3ParentTgt(b, metric) && __sc3ParentTgt(b, metric).total) || (__SC3PT[b] && __SC3PT[b][metric] && __SC3PT[b][metric].total) || 0;
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
            const ta = (__sc3CustTgt(a, metric) && __sc3CustTgt(a, metric).total) || (__SC3ST[a] && __SC3ST[a][metric] && __SC3ST[a][metric].total) || 0;
            const tb = (__sc3CustTgt(b, metric) && __sc3CustTgt(b, metric).total) || (__SC3ST[b] && __SC3ST[b][metric] && __SC3ST[b][metric].total) || 0;
            return tb - ta;
        }});
        if (subKeys.length === 0) return;

        // 第一遍：累加母公司合计数据（过滤 4部门全0 的子公司）
        let parentTotalAct = 0, parentTotalTgt = 0;
        let parentDepsAct = deps.map(() => 0);
        let parentDepsTgt = deps.map(() => 0);
        let subRowData = [];
        subKeys.forEach((c, i) => {{
            let rAct = 0, rTgt = 0, hasData = false;
            let cells = [];
            deps.forEach((d, di) => {{
                const v = subs[c] && subs[c][metric] ? (subs[c][metric][d] || 0) : 0;
                const cT = __sc3CustTgt(c, metric);
                const t = (cT && cT[d]) || 0;
                if (v !== 0 || t !== 0) hasData = true;
                cells.push(__sc3Cell(v, t, false));
                rAct += v; rTgt += t;
                parentDepsAct[di] += v;
                parentDepsTgt[di] += t;
            }});
            cells.push(__sc3Cell(rAct, rTgt, true));
            // 只要有数据无论正负都展示（仅 4 部门金额全为 0 且无指标 → 不展示）
            if (!hasData) return;
            subRowData.push({{ name: c, cells: cells }});
            parentTotalAct += rAct;
            parentTotalTgt += rTgt;
        }});

        // 该母公司下无任何有数据子公司 → 整块跳过
        if (subRowData.length === 0) return;

        let _owned = (window.__SC3OWNED && window.__SC3OWNED[__sc3CurSales] && window.__SC3OWNED[__sc3CurSales][p]) || Object.keys(subs).length;
        let _cfgTotal = (window.__SC3PCT && window.__SC3PCT[p]) || _owned;
        let _tooltip = p + '\\n当前展示 ' + subRowData.length + '\\n销售拥有 ' + _owned + '\\n子公司总数 ' + _cfgTotal;

        if (subRowData.length === 1) {{
            // 母子公司 1:1 — 只显示子公司行（四部门详情），不显示母公司行
            const sr = subRowData[0];
            body += '<tr class="row-data row-sub" style="color:#475569" title="' + _tooltip + '"><td class="td-name" style="padding-left:24px"><span class="row-num" style="color:#cbd5e1">1</span>' + wrapName(sr.name) + '</td>' + sr.cells.join("") + '</tr>';
        }} else {{
            // 母子公司 1:N — 母公司合计行（母公司名 合计 + 四部门详情）
            let pSumRow = [`<td class="td-name" style="font-weight:800;color:#0f172a;background:#eef2ff" title="${{_tooltip}}">${{wrapName(p)}} 合计</td>`];
            deps.forEach((d, di) => {{
                pSumRow.push(__sc3Cell(parentDepsAct[di], parentDepsTgt[di], false));
            }});
            pSumRow.push(__sc3Cell(parentTotalAct, parentTotalTgt, true));
            body += '<tr class="row-data row-parent-total" style="background:#eef2ff;font-weight:700">' + pSumRow.join("") + '</tr>';

            // 子公司明细行（在母公司合计之下缩进显示）
            subRowData.forEach((sr, i) => {{
                body += '<tr class="row-data row-sub" style="color:#475569"><td class="td-name" style="padding-left:24px"><span class="row-num" style="color:#cbd5e1">' + (i + 1) + '</span>' + wrapName(sr.name) + '</td>' + sr.cells.join("") + '</tr>';
            }});
        }}
        // 每个母公司块结束后插入空行作为视觉分隔
        body += '<tr class="row-sep"><td colspan="' + (deps.length + 2) + '" style="height:28px !important;padding:0 !important;background:#bfdbfe !important;border-top:2px solid #60a5fa !important;border-bottom:2px solid #3b82f6 !important;box-shadow:inset 0 6px 0 #bfdbfe,inset 0 -6px 0 #bfdbfe"></td></tr>';
    }});

    if (!body) {{
        body = '<tr><td colspan="' + (deps.length + 2) + '" style="text-align:center;padding:20px;color:var(--text-muted)">该销售当前无数据</td></tr>';
    }}
    const html = '<thead>' + h + '</thead><tbody>' + body + '</tbody>';
    document.getElementById("sc3IncTable").innerHTML = metric === "inc" ? html : "";
    document.getElementById("sc3PayTable").innerHTML = metric === "pay" ? html : "";
}}

function __sc3Cell(act, tgt, isTotal) {{
    // 0<v<1 → ">0"，避免四舍五入成 0 造成"实际0却100%"误解
    const _fmt = v => {{ v = Number(v||0); if (v > 0 && v < 1) return ">0"; return v.toLocaleString("zh-CN", {{maximumFractionDigits: 0}}); }};
    // 0/0 → 显示"—"（无数据）；act>0 且 tgt=0 → 超额100%
    if (act === 0 && tgt === 0) return '<td class="cb is-empty"><div class="ct"><span class="cp">—</span><div class="cm"><span class="cc"><span class="ca">—</span><span class="s">/</span><span class="ctv">—</span></span></div></div></td>';
    let rate, pctLab;
    if (tgt === 0) {{
        rate = Infinity; pctLab = "100%";
    }} else {{
        rate = act / tgt;
        pctLab = Math.round(rate * 100) + "%";
    }}
    const pct = isFinite(rate) ? Math.min(rate * 100, 100) : 100;
    let fc = "fg", pctCls = " achieved";
    if (isFinite(rate)) {{
        if (rate < 1) {{ fc = "fl"; pctCls = " low"; }}
        else if (rate < 0.5) {{ fc = "fy"; pctCls = ""; }}
        else {{ fc = "fo"; pctCls = ""; }}
    }}
    const totalCls = isTotal ? " is-total" : "";
    return `<td class="cb${{totalCls}} ${{fc}}" style="--pct:${{pct}}%">`
        + `<div class="ct"><span class="cp${{pctCls}}">${{pctLab}}</span>`
        + `<div class="cm"><span class="cc"><span class="ca">${{_fmt(act)}}</span>`
        + `<span class="s">/</span><span class="ctv">${{_fmt(tgt)}}</span></span></div></div></td>`;
}}

document.addEventListener("DOMContentLoaded", () => {{
    // 默认不渲染 — 等用户主动选择销售后通过 onchange 触发
    const sel = document.getElementById("sc3SalesSel");
    if (sel) {{
        // 初始时显示"待选"占位内容
        const emptySvg = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:block;margin:0 auto 8px"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>';
        document.getElementById("sc3-inc-matrix").innerHTML = '<div class="sales-modal-empty" style="padding:60px 20px;text-align:center;color:#94a3b8;font-size:14px">' + emptySvg + '请从上方选择销售查看客户达成详情</div>';
        document.getElementById("sc3-pay-matrix").innerHTML = '<div class="sales-modal-empty" style="padding:60px 20px;text-align:center;color:#94a3b8;font-size:14px">' + emptySvg + '请从上方选择销售查看客户达成详情</div>';
    }}
}});
</script>'''
