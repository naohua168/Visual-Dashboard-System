# Author: naohua168 <bai_bai168@qq.com>
"""数据表格、Excel 条件格式数据条、进度条 —— CSS 片段 `tables`

由 processors/static/css_vars.py 拆分而来，内容与拆分前逐字节一致；
拼接顺序见 processors/static/css/__init__.py，改动内容请只在本文件里追加。
"""

CSS = r"""/* ═══════════════════─ 数据表格 ─══════════════════ */
.table-wrap{overflow-x:auto;border:1px solid var(--border);border-radius:0.375rem;background:#fff;}
/* ann-matrix / yoy-matrix-table 表格内部滚动（表头吸顶 + 合计行吸底） */
.table-wrap:has(table.ann-matrix),
.table-wrap:has(table.yoy-matrix-table){overflow-y:auto;max-height:calc(100vh - 13.75rem);}

/* yoy-matrix-table 表头吸顶 + 合计行吸底（两行表头不同 top 避免重叠） */
table.yoy-matrix-table thead tr:first-child th,
.yoy-matrix-table thead tr:first-child th{
  position:sticky;top:0;z-index:10;
  background:#0f172a !important;
}
table.yoy-matrix-table thead tr:last-child th,
.yoy-matrix-table thead tr:last-child th{
  position:sticky;top:3.125rem;z-index:10;
  background:#0f172a !important;
}
table.yoy-matrix-table tbody .row-total td,
.yoy-matrix-table tbody .row-total td{
  position:sticky;bottom:0;z-index:5;
}
table{width:100%;border-collapse:collapse;font-size:0.8125rem;}
th,td{
  padding:0.375rem 0.625rem;text-align:right;
  border-bottom:1px solid #eef0f5;
  white-space:nowrap;font-variant-numeric:tabular-nums;
}
th{
  background:#1e293b;color:#ffffff;font-weight:800;font-size:1.1875rem !important;
  text-transform:none;letter-spacing:0.04em;text-align:center !important;
  position:sticky;top:0;z-index:5;border-bottom:0.1875rem solid #f59e0b;
  padding:0.875rem 0.625rem !important;line-height:1.3;text-shadow:0 1px 0.125rem rgba(0,0,0,.2);
}
table.yoy-dept-table th{
  background:#0f172a;color:#fff;padding:0.875rem 0.625rem;text-align:center;
  font-weight:800;font-size:1.1875rem;letter-spacing:0.06em;border:1px solid #1e293b;
  border-bottom:0.1875rem solid #f59e0b;text-shadow:0 1px 0.125rem rgba(0,0,0,.3);
}
table.yoy-matrix-table th{
  background:#0f172a;color:#fff;padding:0.875rem 0.625rem;text-align:center;
  font-weight:800;font-size:1.1875rem;letter-spacing:0.06em;border:1px solid #1e293b;
  border-bottom:0.1875rem solid #f59e0b;text-shadow:0 1px 0.125rem rgba(0,0,0,.3);
}
/* 双层表头 — 事业部/合计大组 */
table.yoy-matrix-table th.th-dept-group{
  font-size:1.1875rem;padding:0.875rem 0.5rem;font-weight:900;background:#0f172a;
  border-bottom:1px solid #1e293b;letter-spacing:0.06em;
}
table.yoy-matrix-table th.th-dept-group.th-dept-total{
  background:linear-gradient(135deg,#1e3a5f 0%,#0f172a 100%);
  color:#fbbf24;
}
/* 双层表头 — 副表头 (金额/同比) */
table.yoy-matrix-table th.th-sub{
  font-size:0.8125rem;font-weight:700;color:#cbd5e1;padding:0.5rem 0.375rem;
  background:#1e293b;border-top:1px solid #334155;
  text-transform:uppercase;letter-spacing:0.06em;
  border-bottom:1px solid #1e293b;
}
table.yoy-matrix-table th.th-sub-amount{color:#bfdbfe;}
table.yoy-matrix-table th.th-sub-yoy{color:#fbbf24;}
th:first-child,td:first-child{text-align:left;position:sticky;left:0;z-index:4;}
th:first-child{background:#0f172a;color:#fff;z-index:6;font-weight:900;text-align:center;}
td:first-child{background:#fff;font-weight:600;color:var(--text);}
tbody tr:nth-child(even){background-color:#fafbfc;}
tbody tr:nth-child(even) td:first-child{background-color:#fafbfc;}
tbody tr:hover{background-color:#eff6ff !important;}
tbody tr:hover td:first-child{background-color:#eff6ff !important;}
tr.total td{
  background:#eef2ff !important;font-weight:700;color:#4338ca;
  border-top:0.125rem solid #c7d2fe;
}
tr.total td:first-child{background:#e0e7ff !important;color:#3730a3;}
/* 表格内数字高亮 */
td.num-em{color:#2563eb;font-weight:700;}
td.num-red{color:#dc2626;font-weight:700;}
td.num-green{color:#16a34a;font-weight:700;}
td.num-orange{color:#f97316;font-weight:700;}

/* ═══════════════════─ Excel 条件格式数据条 ─══════════════════ */
.completion{
  display:inline-flex;align-items:center;height:1.75rem;min-width:4.6875rem;max-width:100%;
  font-size:0.875rem;font-weight:800;font-variant-numeric:tabular-nums;
  color:var(--text);padding:0 0.125rem;position:relative;overflow:hidden;
  border-radius:0.1875rem;
}
.completion .pct{
  position:relative;z-index:1;padding:0 0.375rem;
  text-align:center;line-height:1.75rem;letter-spacing:0.02em;
}
.completion.level-1{background:#fee2e2;color:#dc2626;border:0.125rem solid #fecaca;}
.completion.level-2{background:#ffedd5;color:#ea580c;border:0.125rem solid #fed7aa;}
.completion.level-3{background:#fef3c7;color:#ca8a04;border:0.125rem solid #fde68a;}
.completion.level-4{background:#dcfce7;color:#16a34a;border:0.125rem solid #bbf7d0;}

/* ═══════════════════─ 进度条 ─══════════════════ */
.progress-row{
  display:grid;grid-template-columns:5rem 1fr 5.625rem 5rem;gap:0.5rem;
  align-items:center;padding:0.375rem 0.75rem;
  font-size:0.8125rem;background:#fff;margin-bottom:0.125rem;
  border:1px solid var(--border);border-radius:0.1875rem;
}
.progress-row:first-child{
  background:transparent;border:none;font-size:0.6875rem;
  color:var(--text-muted);font-weight:700;margin-bottom:0.125rem;
}
.progress-track{
  height:1rem;background:#f2f2f2;
  overflow:hidden;position:relative;
  border:1px solid #d4d4d4;border-radius:0.5rem;
}
.progress-fill{
  height:100%;position:relative;min-width:0.125rem;
  border-radius:0.5rem;
}
.progress-fill.level-1{background:#dc2626;}
.progress-fill.level-2{background:#f97316;}
.progress-fill.level-3{background:#f59e0b;}
.progress-fill.level-4{background:#16a34a;}
.progress-fill .pct{
  position:absolute;right:0.375rem;top:50%;transform:translateY(-50%);
  font-size:0.625rem;color:#fff;font-weight:700;
}
.progress-val{text-align:right;font-weight:700;font-variant-numeric:tabular-nums;color:var(--accent);font-size:0.875rem;}
.progress-tgt{text-align:right;font-size:0.6875rem;color:var(--text-muted);font-variant-numeric:tabular-nums;}


"""
