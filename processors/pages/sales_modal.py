# Author: naohua168 <bai_bai168@qq.com>
"""销售达成页 · 客户达成详情抽屉（右侧滑入）

由 pages/sales.py 拆分而来：遮罩+面板样式、明细表 HTML，以及开关/切换 Tab 的脚本。"""
from __future__ import annotations

import json
from ..data_utils import DEPARTMENTS


def _sales_modal_css() -> str:
    return '''<style>
/* 卡片3 矩阵 — 全宽自适应，无溢出 */
#sc3-inc-matrix .ann-matrix,
#sc3-pay-matrix .ann-matrix { table-layout: fixed; width: 100%; }
#sc3-inc-matrix .ann-matrix thead th:nth-child(1),
#sc3-pay-matrix .ann-matrix thead th:nth-child(1),
#sc3-inc-matrix .ann-matrix tbody td:nth-child(1),
#sc3-pay-matrix .ann-matrix tbody td:nth-child(1) { width: 30%; }
#sc3-inc-matrix .ann-matrix thead th:nth-child(n+2),
#sc3-pay-matrix .ann-matrix thead th:nth-child(n+2),
#sc3-inc-matrix .ann-matrix tbody td:nth-child(n+2),
#sc3-pay-matrix .ann-matrix tbody td:nth-child(n+2) { width: 14%; }
#sc3-inc-matrix .ann-matrix td, #sc3-inc-matrix .ann-matrix th,
#sc3-pay-matrix .ann-matrix td, #sc3-pay-matrix .ann-matrix th { font-size: 0.6875rem; padding: 0.25rem 0.25rem; }
#sc3-inc-matrix .td-name, #sc3-pay-matrix .td-name { font-size: 0.75rem; line-height: 1.3; }
#sc3-inc-matrix .cb, #sc3-pay-matrix .cb { padding: 0.1875rem 0.125rem; }
#sc3-inc-matrix .cp, #sc3-pay-matrix .cp { font-size: 0.6875rem; }
#sc3-inc-matrix .ca, #sc3-pay-matrix .ca,
#sc3-inc-matrix .ctv, #sc3-pay-matrix .ctv { font-size: 0.625rem; }

/* 卡片1 布局 */
.card1-flex{display:flex;gap:1.5rem;padding:0.75rem 1rem} .card1-col{flex:1;min-width:0}
.card1-col-title{font-weight:700;font-size:0.8125rem;margin-bottom:0.5rem;padding-bottom:0.375rem;border-bottom:0.125rem solid var(--border);color:var(--text)}
.card1-col:nth-child(1) .card1-col-title{border-color:#3b82f6} .card1-col:nth-child(2) .card1-col-title{border-color:#22c55e}
.mini-rate.summary-rate{border-bottom:0.125rem solid var(--border);padding-bottom:0.375rem;margin-bottom:0.5rem}
.summary-rate .bar{height:1rem} .summary-rate .bar-pct{font-weight:700}

/* 可点击销售行 */
.sales-clickable { cursor: pointer; border-radius: 0.25rem; transition: background 0.15s; }
.sales-clickable:hover { background: rgba(59,130,246,0.06); }
.sales-name { width: 4.5rem; font-weight: 600; user-select: none; }

/* 当前激活的销售行（高亮锚点） */
.sales-clickable.sales-active {
    background: rgba(59,130,246,0.10);
    box-shadow: 0 0 0 1px rgba(59,130,246,0.35);
}

/* 抽屉遮罩 — 半透明，点击关闭
   visibility 一起管：万一有别的动效误改 opacity，遮罩也不会把整页压黑
   （2026-10-10 修：入场浮现动画曾把这张全屏黑遮罩淡入 → 切到本页时闪黑） */
.sales-modal-overlay {
    display: block; position: fixed; inset: 0; z-index: 20000;
    background: rgba(0,0,0,0.35);
    opacity: 0; visibility: hidden; pointer-events: none;
    transition: opacity 0.25s ease, visibility 0.25s;
}
.sales-modal-overlay.show { opacity: 1; visibility: visible; pointer-events: auto; }

/* 抽屉面板 — 右侧滑入 */
.sales-modal {
    position: fixed; right: 0; top: 0;
    width: 67vw; min-width: 56.25rem; height: 100vh;
    transform: translateX(100%);
    z-index: 20001;
    background: #fff; border-radius: 0.875rem 0 0 0.875rem;
    display: flex; flex-direction: column;
    overflow: hidden;
    box-shadow: -10px 0 40px rgba(0,0,0,0.18);
    transition: transform 0.3s cubic-bezier(0.16,1,0.3,1);
}
.sales-modal.show { transform: translateX(0); }

/* 抽屉头部 */
.sales-modal-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 1rem 1.25rem 0.75rem; border-bottom: 1px solid #e2e8f0; flex-shrink: 0;
}
.sales-modal-title { font-size: 1rem; font-weight: 700; color: #0f172a; }
.sales-modal-sub { font-size: 0.75rem; color: #64748b; margin-top: 0.125rem; }
.sales-modal-close {
    width: 2rem; height: 2rem; border: none; background: none;
    font-size: 1.25rem; color: #94a3b8; cursor: pointer; border-radius: 0.5rem;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.15s;
}
.sales-modal-close:hover { background: #f1f5f9; color: #0f172a; }

/* 抽屉 Tab 栏 */
.sales-modal-tabs { display: flex; gap: 0; border-bottom: 0.125rem solid #e2e8f0; flex-shrink: 0; }
.sales-modal-tab {
    padding: 0.625rem 1.5rem; font-size: 0.8125rem; font-weight: 600; cursor: pointer;
    border: none; background: none; color: #94a3b8; transition: all 0.15s;
    border-bottom: 0.125rem solid transparent; margin-bottom: -0.125rem;
}
.sales-modal-tab:hover { color: #64748b; }
.sales-modal-tab.active { color: #3b82f6; border-bottom-color: #3b82f6; }
.sales-modal-tab.pay.active { color: #22c55e; border-bottom-color: #22c55e; }

/* 抽屉内容区 */
.sales-modal-body { flex: 1 1 auto; padding: 0.75rem 0; min-height: 0; overflow-y: auto; overflow-x: hidden; }
.sales-modal-body .ann-matrix { table-layout: fixed; width: 100%; }
.sales-modal-body .ann-matrix thead th:nth-child(1),
.sales-modal-body .ann-matrix tbody td:nth-child(1) { width: 25%; }
.sales-modal-body .ann-matrix thead th:nth-child(n+2),
.sales-modal-body .ann-matrix tbody td:nth-child(n+2) { width: 15%; }
.sales-modal-body .ann-matrix th, .sales-modal-body .ann-matrix td { font-size: 0.75rem; padding: 0.25rem 0.375rem; }
.sales-modal-body .ann-matrix .cb { padding: 0.25rem 0.1875rem; }
.sales-modal-body .ann-matrix .cp { font-size: 0.75rem; }
.sales-modal-body .ann-matrix .ca,
.sales-modal-body .ann-matrix .ctv { font-size: 0.6875rem; }

/* 弹窗 KPI */
.modal-kpi {
    display: flex; gap: 1rem; padding: 0.5rem 1.25rem; font-size: 0.75rem; color: #64748b;
    border-bottom: 1px solid #f1f5f9; flex-wrap: wrap;
}
.modal-kpi b { color: #0f172a; }

/* 弹窗内表格 不嵌套滚动框 */
.sales-modal-body .ann-matrix-wrap { overflow: visible; }
.sales-modal-body .ann-matrix { width: 100%; border-collapse: collapse; font-size: 0.75rem; }
.sales-modal-body .ann-matrix th {
    position: sticky; top: 0; z-index: 2; background: #f8fafc;
    padding: 0.5rem 0.375rem; font-size: 0.6875rem; color: #64748b; white-space: nowrap;
}
.sales-modal-body .ann-matrix td { padding: 0.25rem 0.375rem; white-space: nowrap; }
.sales-modal-body .ann-matrix .td-name { white-space: normal; font-size: 0.875rem; line-height: 1.4; font-weight: 600; color: #1e293b; direction: ltr; unicode-bidi: normal; transform: none; padding: 0.5rem 0.375rem; vertical-align: middle; }
.sales-modal-body .ann-matrix .row-sub .td-name { font-size: 0.8125rem; font-weight: 500; color: #475569; padding: 0.5rem 0.375rem 0.5rem 1.25rem; direction: ltr; unicode-bidi: normal; vertical-align: middle; }
.sales-modal-body .ann-matrix .parent-name {
    font-weight: 800; font-size: 0.875rem; color: #0f172a;
    background: #f1f5f9; padding: 0.375rem 0.5rem;
}
.sales-modal-body .row-parent-total td { background: #f8fafc; font-weight: 600; }
.sales-modal-body .highlight-row td { background: rgba(59,130,246,0.04) !important; }
.sales-modal-empty { text-align: center; padding: 2.5rem; color: #94a3b8; font-size: 0.8125rem; }

/* 母公司完成度圆环行 */
.parent-rings { display: flex; gap: 0.875rem; padding: 0.875rem 1rem; overflow-x: auto; border-bottom: 1px solid #e2e8f0; background: #f8fafc; flex-wrap: wrap; }
.parent-rings::-webkit-scrollbar { height: 0.375rem; }
.parent-rings::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 0.1875rem; }
.parent-ring-item { flex: 0 0 8.125rem; text-align: center; }
.parent-ring-item .ring-name { font-size: 0.6875rem; color: #475569; font-weight: 500; margin-bottom: 0.25rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.parent-ring-item .ring-wrap { position: relative; width: 3.25rem; height: 3.25rem; margin: 0 auto; }
.parent-ring-item .ring-svg { width: 100%; height: 100%; }
.parent-ring-item .ring-pct { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-weight: 800; font-size: 0.75rem; }
.parent-ring-item .ring-detail { font-size: 0.625rem; color: #94a3b8; margin-top: 0.25rem; font-family: "JetBrains Mono", monospace; }</style>'''


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

    // 当前销售的目标读取（客户级 + 母公司级）
    function _custTgt(cust, metric) {{
        const sd = (window.__SC3ST_S && window.__SC3ST_S[_curSales]) || {{}};
        return (sd[cust] && sd[cust][metric]) || null;
    }}
    function _parentTgt(parent, metric) {{
        const pd = (window.__SC3PT_S && window.__SC3PT_S[_curSales]) || {{}};
        return (pd[parent] && pd[parent][metric]) || null;
    }}

    // ── 计算某母公司的总实际/总目标（按当前销售个人目标）──
    function _parentTotals(parents, p) {{
        let act = 0, tgt = 0;
        const subs = parents[p] || {{}};
        Object.keys(subs).forEach(c => {{
            const cT = _custTgt(c, _curMetric);
            _DEPS.forEach(d => {{
                act += subs[c] && subs[c][_curMetric] ? (subs[c][_curMetric][d] || 0) : 0;
                tgt += (cT && cT[d]) || 0;
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

            // 第一遍：累加母公司合计数据（过滤 4部门全0 的子公司）
            let depActs = _DEPS.map(() => 0);
            let depTgts = _DEPS.map(() => 0);
            let subRowData = [];
            let pActAll = 0, pTgtAll = 0;
            subKeys.forEach((c, i) => {{
                let rAct = 0, rTgt = 0, hasData = false;
                let cells = [];
                const cT = _custTgt(c, _curMetric);
                _DEPS.forEach((d, di) => {{
                    const v = subs[c] && subs[c][_curMetric] ? (subs[c][_curMetric][d] || 0) : 0;
                    const t = (cT && cT[d]) || 0;
                    if (v !== 0 || t !== 0) hasData = true;
                    cells.push(_modalCell(v, t));
                    rAct += v; rTgt += t;
                    depActs[di] += v;
                    depTgts[di] += t;
                }});
                cells.push(_modalCell(rAct, rTgt, true));
                // 只要有数据无论正负都展示（仅 4 部门金额全为 0 且无指标 → 不展示）
                if (!hasData) return;
                subRowData.push({{ name: c, cells: cells }});
                pActAll += rAct;
                pTgtAll += rTgt;
            }});

            // 该母公司下无任何有数据子公司 → 整块跳过
            if (subRowData.length === 0) return;

            let _owned = (window.__SC3OWNED && window.__SC3OWNED[_curSales] && window.__SC3OWNED[_curSales][p]) || Object.keys(subs).length;
            let _cfgTotal = (window.__SC3PCT && window.__SC3PCT[p]) || _owned;
            let _tooltip = p + '\\n当前展示 ' + subRowData.length + '\\n销售拥有 ' + _owned + '\\n子公司总数 ' + _cfgTotal;

            if (subRowData.length === 1) {{
                // 母子公司 1:1 — 只显示子公司行（四部门详情），不显示母公司行
                const sr = subRowData[0];
                body += '<tr class="row-data row-sub" style="color:#475569" title="' + _tooltip + '"><td class="td-name" style="padding-left:16px">' + wrapName(sr.name) + '</td>' + sr.cells.join('') + '</tr>';
            }} else {{
                // 母子公司 1:N — 母公司合计行（母公司名 合计 + 四部门详情）
                let pSumRow = [`<td class="td-name" style="font-weight:700;background:#eef2ff" title="${{_tooltip}}">${{wrapName(p)}} 合计</td>`];
                _DEPS.forEach((d, di) => {{
                    pSumRow.push(_modalCell(depActs[di], depTgts[di]));
                }});
                pSumRow.push(_modalCell(pActAll, pTgtAll, true));
                body += '<tr class="row-data row-parent-total" style="background:#eef2ff;font-weight:700">' + pSumRow.join('') + '</tr>';

                // 子公司明细行
                subRowData.forEach((sr, i) => {{
                    body += '<tr class="row-data row-sub" style="color:#475569"><td class="td-name" style="padding-left:16px">' + wrapName(sr.name) + '</td>' + sr.cells.join('') + '</tr>';
                }});
            }}

            totalAct += pActAll; totalTgt += pTgtAll;
            totalSubs += subRowData.length;

            // 每个母公司块结束后插入空行作为视觉分隔
            body += '<tr class="row-sep"><td colspan="' + (_DEPS.length + 2) + '" style="height:28px !important;padding:0 !important;background:#bfdbfe !important;border-top:2px solid #60a5fa !important;border-bottom:2px solid #3b82f6 !important;box-shadow:inset 0 6px 0 #bfdbfe,inset 0 -6px 0 #bfdbfe"></td></tr>';
        }});

        if (!body) {{
            body = '<tr><td colspan="' + (_DEPS.length + 2) + '" style="text-align:center;padding:20px;color:#94a3b8">无数据</td></tr>';
        }}

        const totalRate = totalTgt > 0 ? totalAct / totalTgt : 0;

        // 母公司完成度圆环行
        const _r = 18, _circ = 2 * Math.PI * _r;
        // ── 销售个人目标汇总（从 __SC3ST_S 全量计算，含仅有指标无实际金额的客户）──
        let _sTgtAll = 0, _sActAll = 0;
        const _sTgtMap = (window.__SC3ST_S && window.__SC3ST_S[_curSales]) || {{}};
        Object.keys(_sTgtMap).forEach(c => {{
            const t = _sTgtMap[c] && _sTgtMap[c][_curMetric];
            if (t) {{
                _DEPS.forEach(d => {{
                    _sTgtAll += (t[d] || 0);
                    let cAct = 0;
                    Object.keys(parents).forEach(p => {{
                        if (parents[p] && parents[p][c] && parents[p][c][_curMetric]) {{
                            cAct += parents[p][c][_curMetric][d] || 0;
                        }}
                    }});
                    _sActAll += cAct;
                }});
            }}
        }});
        const _sRate = _sTgtAll > 0 ? Math.round(_sActAll / _sTgtAll * 100) : 0;
        function _fJ(v) {{ v = Number(v||0); if (v > 0 && v < 1) return ">0"; return v.toLocaleString("zh-CN", {{maximumFractionDigits: 0}}); }}
        const _sBanner = '<div class="sales-tgt-banner" style="background:linear-gradient(135deg,#fef3c7,#fde68a);border:1px solid #f59e0b;border-radius:8px;padding:10px 14px;margin:0 0 14px 0;display:flex;gap:16px;font-size:13px;flex-wrap:wrap"><span style="font-weight:700;color:#92400e">销售个人指标全量</span><span style="color:#92400e">指标合计：<b style="color:#7c2d12;font-size:15px">' + _fJ(_sTgtAll) + '</b></span><span style="color:#92400e">实际完成：<b style="color:#7c2d12;font-size:15px">' + _fJ(_sActAll) + '</b></span><span style="color:#92400e">完成度：<b style="color:#7c2d12;font-size:15px">' + _sRate + '%</b></span><span style="color:#a16207;font-size:11px">（含未展示客户目标）</span></div>';

        let ringsHtml = '<div class="parent-rings">';
        parentKeys.forEach(p => {{
            const [pA, pT] = _parentTotals(parents, p);
            const subs = parents[p];
            let nSubs = 0;
            Object.keys(subs).forEach(c => {{
                let sA = 0, sT = 0;
                const cT = _custTgt(c, _curMetric);
                _DEPS.forEach(d => {{
                    sA += subs[c] && subs[c][_curMetric] ? (subs[c][_curMetric][d] || 0) : 0;
                    sT += (cT && cT[d]) || 0;
                }});
                if (sA !== 0 || sT > 0) nSubs++;
            }});
            // 该母公司无任何有数据子公司 → 圆环跳过
            if (nSubs === 0) return;
            let _owned = (window.__SC3OWNED && window.__SC3OWNED[_curSales] && window.__SC3OWNED[_curSales][p]) || Object.keys(subs).length;
            let _cfgTotal = (window.__SC3PCT && window.__SC3PCT[p]) || _owned;
            const rate = pT > 0 ? Math.min(pA / pT, 1) : (pA > 0 ? 1 : 0);
            const rateTxt = pT > 0 ? Math.round(pA / pT * 100) + '%' : (pA > 0 ? '100%' : '—');
            const color = pT > 0 ? (pA >= pT ? '#16a34a' : pA/pT >= 0.5 ? '#f59e0b' : '#ef4444') : (pA > 0 ? '#16a34a' : '#cbd5e1');
            const dash = rate * _circ;
            ringsHtml += '<div class="parent-ring-item">'
                + '<div class="ring-name" title="' + p + '\\n当前展示 ' + nSubs + '\\n销售拥有 ' + _owned + '\\n子公司总数 ' + _cfgTotal + '">' + p + '（' + nSubs + '/' + _owned + '/' + _cfgTotal + '）</div>'
                + '<div class="ring-wrap">'
                + '<svg viewBox="0 0 40 40" class="ring-svg">'
                + '<circle cx="20" cy="20" r="' + _r + '" fill="none" stroke="#f1f5f9" stroke-width="3"/>'
                + '<circle cx="20" cy="20" r="' + _r + '" fill="none" stroke="' + color + '" stroke-width="3" stroke-dasharray="' + dash + ' ' + _circ + '" stroke-linecap="round" transform="rotate(-90 20 20)"/>'
                + '</svg>'
                + '<div class="ring-pct" style="color:' + color + '">' + rateTxt + '</div>'
                + '</div>'
                + '<div class="ring-detail">' + pA.toLocaleString("zh-CN", {{maximumFractionDigits: 0}}) + ' / ' + pT.toLocaleString("zh-CN", {{maximumFractionDigits: 0}}) + '</div>'
                + '</div>';
        }});
        ringsHtml += '</div>';

        const html = '<div class="table-wrap ann-matrix-wrap">'
            + '<table class="ann-matrix">' + h + '<tbody>' + body + '</tbody></table></div>';
        document.getElementById('salesModalBody').innerHTML = ringsHtml + html;
    }}

    function _modalCell(act, tgt, isTotal) {{
        const _f = v => {{ v = Number(v||0); if (v > 0 && v < 1) return ">0"; return v.toLocaleString("zh-CN", {{maximumFractionDigits: 0}}); }};
        // 0/0 → "—"，act>0 且 tgt=0 → 超额100%
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
        const tc = isTotal ? " is-total" : "";
        return `<td class="cb${{tc}} ${{fc}}" style="--pct:${{pct}}%">`
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
