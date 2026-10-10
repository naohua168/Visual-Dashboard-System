# Author: naohua168 <bai_bai168@qq.com>
"""事业部同比表、客户同比矩阵表、同比 Tab 容器 —— CSS 片段 `yoy_tables`

由 processors/static/css_vars.py 拆分而来，内容与拆分前逐字节一致；
拼接顺序见 processors/static/css/__init__.py，改动内容请只在本文件里追加。
"""

CSS = r"""/* ══════════ 事业部同比专用表（双维度清晰对比）══════════ */
table.yoy-dept-table{width:100%;border-collapse:collapse;font-size:0.8125rem;}

table.yoy-dept-table th.group-header{
  font-size:1.1875rem;padding:0.875rem 0.25rem;letter-spacing:0.12em;
}
table.yoy-dept-table th.inc-group{background:#c2410c;}
table.yoy-dept-table th.pay-group{background:#047857;}
table.yoy-dept-table td{padding:0.5625rem 0.625rem;border:1px solid #e2e8f0;text-align:center;}
table.yoy-dept-table tbody tr:nth-child(even){background:#f8fafc;}
table.yoy-dept-table tbody tr:hover{background:#bfdbfe !important;box-shadow:inset 0.25rem 0 0 0 #1e40af;}
/* 事业部名称列 */
table.yoy-dept-table td.dept-name{
  text-align:left;font-weight:800;font-size:0.875rem;color:#1e293b;
  padding-left:1rem;background:#f1f5f9;border-left:0.25rem solid var(--accent);
}
/* 数值单元格 */
table.yoy-dept-table td.num-cell{
  font-weight:600;font-size:0.8125rem;color:#334155;font-variant-numeric:tabular-nums;
}
table.yoy-dept-table td.num-cell.muted{color:#94a3b8;font-size:0.75rem;}
/* 同比单元格 — 核心视觉焦点 */
table.yoy-dept-table td.yoy-cell{
  padding:0.375rem 0.25rem;min-width:5.625rem;
}
table.yoy-dept-table .yoy-pct{
  display:inline-block;padding:0.375rem 0.75rem;border-radius:0.375rem;
  font-weight:900;font-size:0.9375rem;letter-spacing:-0.3px;
  white-space:nowrap;line-height:1.2;
}
/* 增长 — 红色系（业绩好） */
table.yoy-dept-table td.yoy-cell.up .yoy-pct{
  background:linear-gradient(135deg,#fef2f2,#fee2e2);
  color:#dc2626;border:1px solid #fecaca;
  box-shadow:inset 0 -2px 0 rgba(220,38,38,0.15);
}
table.yoy-dept-table td.yoy-cell.up:hover .yoy-pct{
  background:linear-gradient(135deg,#dc2626,#ef4444);color:#fff;
}
/* 大幅增长 — 深红底白字 */
table.yoy-dept-table td.yoy-cell.up[data-big="true"] .yoy-pct,
table.yoy-dept-table td.yoy-cell.up:hover .yoy-pct{
  background:linear-gradient(135deg,#dc2626,#b91c1c);
  color:#fff;border-color:#991b1b;
  box-shadow:0 2px 8px rgba(220,38,38,0.35);
}
/* 下降 — 绿色系（警示） */
table.yoy-dept-table td.yoy-cell.down .yoy-pct{
  background:linear-gradient(135deg,#f0fdf4,#dcfce7);
  color:#16a34a;border:1px solid #bbf7d0;
  box-shadow:inset 0 -2px 0 rgba(22,163,74,0.15);
}
table.yoy-dept-table td.yoy-cell.down:hover .yoy-pct{
  background:linear-gradient(135deg,#16a34a,#15803d);color:#fff;
}
/* 大幅下降 — 深绿底白字 */
table.yoy-dept-table td.yoy-cell.down[data-big="true"] .yoy-pct,
table.yoy-dept-table td.yoy-cell.down:hover .yoy-pct{
  background:linear-gradient(135deg,#16a34a,#166534);
  color:#fff;border-color:#15803d;
  box-shadow:0 2px 8px rgba(22,163,74,0.35);
}
/* 持平 — 灰色 */
table.yoy-dept-table td.yoy-cell.flat .yoy-pct{
  background:#f1f5f9;color:#64748b;border:1px solid #e2e8f0;
}

/* ══════════ 客户同比矩阵表（徽章+金额）══════════ */
table.yoy-matrix-table{width:100%;border-collapse:separate;border-spacing:0;font-size:0.7812rem;}
/* yoy-matrix 表格 — 行底分隔 + hover 高亮覆盖所有单元格 */
table.yoy-matrix-table td{padding:0.4375rem 0.375rem;border:1px solid #e2e8f0;text-align:center;vertical-align:middle;border-bottom:0.125rem solid #e2e8f0;}
table.yoy-matrix-table tbody tr{border-bottom:0.125rem solid #cbd5e1;}
table.yoy-matrix-table tbody tr:nth-child(even){background:#f8fafc;}
/* 行 hover — 覆盖所有单元格（包括 mx-yoy-cell），0.25rem 深蓝左侧高亮 */
table.yoy-matrix-table tbody tr:hover td,
table.yoy-matrix-table tbody tr:hover{background:#bfdbfe !important;box-shadow:inset 0.25rem 0 0 0 #1e40af;}
/* hover 时不要让 mx-yoy-cell 的胶囊按钮背景被改 */
table.yoy-matrix-table tbody tr:hover td.mx-yoy-cell{background:transparent!important;}
table.yoy-matrix-table tbody tr:hover td.mx-yoy-cell .mx-badge{box-shadow:0 0.125rem 0.5rem rgba(0,0,0,0.25);}
/* 客户名称 */
table.yoy-matrix-table td.td-name{text-align:left;font-size:0.8125rem;color:#334155;padding-left:0.75rem;line-height:1.45;vertical-align:middle;}
table.yoy-matrix-table .row-num{display:inline-block;width:1.375rem;height:1.375rem;line-height:1.375rem;
  text-align:center;background:#dbeafe;color:#1d4ed8;border-radius:50%;
  font-size:0.6875rem;font-weight:800;margin-right:0.5rem;flex-shrink:0;}
/* 矩阵单元格 — 垂直布局：徽章上+金额下 */
table.yoy-matrix-table td.mx-cell{padding:0.3125rem 0.25rem;min-width:5rem;}
/* 同比徽章 */
table.yoy-matrix-table .mx-badge{
  display:block;padding:0.25rem 0.5rem;border-radius:0.3125rem;
  font-weight:900;font-size:0.8125rem;letter-spacing:-0.3px;
  margin-bottom:0.1875rem;line-height:1.2;white-space:nowrap;
}
/* 当期金额 */
table.yoy-matrix-table .mx-val{
  display:block;font-size:0.6875rem;color:#64748b;font-weight:600;
  font-variant-numeric:tabular-nums;
}
/* 增长 — 红 */
table.yoy-matrix-table td.mx-cell.up .mx-badge{
  background:linear-gradient(135deg,#fef2f2,#fee2e2);
  color:#dc2626;border:1px solid #fecaca;
}
table.yoy-matrix-table td.mx-cell.up[data-big] .mx-badge,
table.yoy-matrix-table td.mx-cell.up:hover .mx-badge{
  background:linear-gradient(135deg,#dc2626,#b91c1c);color:#fff;
  border-color:#991b1b;box-shadow:0 0.125rem 0.375rem rgba(220,38,38,0.25);
}
/* 下降 — 绿 */
table.yoy-matrix-table td.mx-cell.down .mx-badge{
  background:linear-gradient(135deg,#f0fdf4,#dcfce7);
  color:#16a34a;border:1px solid #bbf7d0;
}
table.yoy-matrix-table td.mx-cell.down[data-big] .mx-badge,
table.yoy-matrix-table td.mx-cell.down:hover .mx-badge{
  background:linear-gradient(135deg,#16a34a,#166534);color:#fff;
  border-color:#15803d;box-shadow:0 0.125rem 0.375rem rgba(22,163,74,0.25);
}
/* 持平 — 灰 */
table.yoy-matrix-table td.mx-cell.flat .mx-badge{
  background:#f1f5f9;color:#94a3b8;border:1px solid #e2e8f0;
}
/* 合计行 — 灰色外框框起 */
table.yoy-matrix-table tr.row-total{background:linear-gradient(90deg,#eff6ff,#f0fdf4)!important;}
table.yoy-matrix-table tr.row-total td{font-weight:700;font-size:0.875rem;}
table.yoy-matrix-table tr.row-total td:not(.yoy-cell):not(.mx-amount-pair){
  border:1px solid #cbd5e1;
  border-top:0.125rem solid #1e40af!important;
  border-bottom:0.125rem solid #1e40af!important;
}

/* ═══════════════════─ 重设计的金额/同比单元格（直观卡片化） ───────── */
table.yoy-matrix-table td.mx-amount-cell{
  padding:0.5rem 0.625rem;min-width:6.25rem;text-align:left;
  border:1px solid #cbd5e1;vertical-align:middle;
}
table.yoy-matrix-table td.mx-amount-cell .mx-amount-pair{
  display:flex;flex-direction:column;gap:0.25rem;
}
table.yoy-matrix-table td.mx-amount-cell .mx-amt-row{
  display:flex;justify-content:space-between;align-items:baseline;gap:0.75rem;
  font-size:1.5rem;font-variant-numeric:tabular-nums;
}
table.yoy-matrix-table td.mx-amount-cell .mx-cur-row{
  font-weight:900;color:#0f172a;font-size:1.625rem;
}
table.yoy-matrix-table td.mx-amount-cell .mx-prev-row{
  font-weight:600;color:#64748b;font-size:1.375rem;
}
table.yoy-matrix-table td.mx-amount-cell .mx-amt-label{
  font-size:0.75rem;color:#64748b;font-weight:500;
}
table.yoy-matrix-table td.mx-amount-cell .mx-cur-row .mx-amt-label{color:#2563eb;}

/* 同比单元格 — 胶囊按钮样式（红涨绿跌）
   注意：不设 background，让父级行 hover 高亮能透过来 */
table.yoy-matrix-table td.mx-yoy-cell{
  padding:0.5rem 0.375rem;border:1px solid #cbd5e1;vertical-align:middle;
  background:transparent;
}
table.yoy-matrix-table td.mx-yoy-cell .mx-badge{
  display:inline-flex;align-items:center;gap:0.375rem;
  padding:0.5rem 1rem;border-radius:0.5rem;
  font-size:1.125rem;font-weight:800;letter-spacing:-0.3px;
  color:#fff;line-height:1.2;
  box-shadow:0 2px 6px rgba(0,0,0,0.15);
  transition:transform 0.15s,box-shadow 0.15s;
}
table.yoy-matrix-table td.mx-yoy-cell.up .mx-badge{
  background:linear-gradient(135deg,#dc2626 0%,#b91c1c 100%);
  color:#fff;border:1px solid #991b1b;
}
table.yoy-matrix-table td.mx-yoy-cell.down .mx-badge{
  background:linear-gradient(135deg,#22c55e 0%,#15803d 100%);
  color:#fff;border:1px solid #14532d;
}
table.yoy-matrix-table td.mx-yoy-cell.flat .mx-badge{
  background:linear-gradient(135deg,#94a3b8 0%,#64748b 100%);
  color:#fff;border:1px solid #475569;
}
table.yoy-matrix-table td.mx-yoy-cell.sev-l .mx-pct,
table.yoy-matrix-table td.mx-yoy-cell.sev-x .mx-pct{
  font-size:0.875rem;font-weight:900;
}

/* 合计行第一格（客户名列）加大字号 */
table.yoy-matrix-table tr.row-total td.td-name{font-size:0.9375rem;font-weight:800;letter-spacing:0.02em;}
/* 空格 */
table.yoy-matrix-table .td-empty{color:#cbd5e1;font-style:italic;}

/* ══════════ 客户同比 Tab 切换容器 ══════════ */
.yoy-cust-tabs .tab-header{
  display:flex;gap:0;margin-bottom:0;
  border-bottom:0.125rem solid #e2e8f0;padding:0 0.25rem;
}
.yoy-cust-tabs .tab-btn{
  padding:0.625rem 1.5rem;border:none;background:transparent;
  font-size:0.875rem;font-weight:700;color:#64748b;cursor:pointer;
  border-radius:0.5rem 0.5rem 0 0;transition:all 0.2s;
  letter-spacing:0.3px;
}
.yoy-cust-tabs .tab-btn:hover{background:#f1f5f9;color:#334155;}
.yoy-cust-tabs .tab-btn.active{
  background:#1e40af;color:#fff;
  box-shadow:0 -2px 8px rgba(30,64,175,0.15);
}
.yoy-cust-tabs .tab-panel{display:none;}
.yoy-cust-tabs .tab-panel.active{display:block;}
"""
