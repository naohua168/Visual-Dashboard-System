# Author: naohua168 <bai_bai168@qq.com>
"""图表容器、表格折叠、预警横幅、空状态、数据范围 banner、季度客户表 —— CSS 片段 `widgets`

由 processors/static/css_vars.py 拆分而来，内容与拆分前逐字节一致；
拼接顺序见 processors/static/css/__init__.py，改动内容请只在本文件里追加。
"""

CSS = r"""/* ═══════════════════─ 图表容器 ─══════════════════ */
.chart-box{
  background:#fff;padding:0.875rem;margin-bottom:0.25rem;
  border:1px solid var(--border);border-radius:0.625rem;
  box-shadow:var(--shadow-sm);
}
.chart-box canvas{min-height:13.75rem;}
.chart-title{font-size:0.875rem;font-weight:700;margin-bottom:0.375rem;color:#1e293b;}

/* ═══════════════════─ 表格折叠 ─══════════════════ */
.table-collapse{max-height:31.25rem;overflow:hidden;position:relative;}
.table-collapse.collapsed{max-height:none;}
.table-collapse .collapse-overlay{
  display:none;
  position:absolute;bottom:0;left:0;right:0;height:3.75rem;
  background:linear-gradient(transparent,#fff);z-index:8;
  pointer-events:none;
}
.table-collapse.collapsed .collapse-overlay{display:block;}
.collapse-btn{
  display:block;width:100%;padding:0.375rem;margin-bottom:0.25rem;
  font-size:0.75rem;font-weight:600;text-align:center;
  background:var(--accent-light);color:var(--accent);
  border:1px solid var(--accent);cursor:pointer;border-radius:0.125rem;
}
.collapse-btn:hover{background:var(--accent);color:#fff;}


/* ═══════════════════─ 预警横幅 ─══════════════════ */
.alert-banner{
  display:flex;align-items:center;gap:0.5rem;padding:0.5rem 0.75rem;margin-bottom:0.25rem;
  font-size:0.75rem;font-weight:600;border-radius:0.375rem;
}
.alert-banner.warn{background:#ffedd5;color:#c2410c;border:1px solid #fed7aa;}
.alert-banner.danger{background:#fee2e2;color:#b91c1c;border:1px solid #fecaca;}
.alert-banner.info{background:#dbeafe;color:#1d4ed8;border:1px solid #bfdbfe;}
.alert-banner .badge{
  background:currentColor;color:#fff;padding:1px 0.625rem;font-size:0.5625rem;font-weight:700;margin-left:auto;
}

/* ═══════════════════─ 空状态 ─══════════════════ */
.empty{
  text-align:center;padding:2.5rem;color:var(--text-muted);font-size:0.75rem;
  background:#fff;border:1px dashed var(--border);
}

/* ═══════════════════─ 年度目标总览块 ─══════════════════ */
.target-hero{
  background:linear-gradient(135deg,#1e293b,#334155);color:#fff;padding:1rem 1.5rem;text-align:center;margin-bottom:0.375rem;
  border-radius:0.5rem;
}
.target-hero .label{
  font-size:0.6875rem;opacity:0.7;letter-spacing:0.08em;text-transform:uppercase;
}
.target-hero .value{
  font-size:2.25rem;font-weight:800;font-variant-numeric:tabular-nums;margin:0.25rem 0;
  color:#fbbf24;
}
.target-hero .unit{font-size:0.875rem;font-weight:500;opacity:0.8;}


/* ═══════════════════─ 页面数据范围 banner ─══════════════════ */
.range-banner{
  background:linear-gradient(135deg,#1e40af 0%,#2563eb 100%);
  color:#fff;padding:0.5rem 1rem;border-radius:0.375rem;margin-bottom:0.5rem;
  font-size:0.8125rem;font-weight:600;letter-spacing:0.02em;
  box-shadow:0 2px 6px rgba(30,64,175,0.25);
}

/* ═══════════════════─ 季度客户达成表 (6列, 无目标) ─══════════════════ */
table.q2-cust-table{
  width:100%;border-collapse:collapse;font-size:0.875rem;
  table-layout:fixed;background:#fff;
}
table.q2-cust-table th{
  background:#0f172a;color:#fff;padding:0.875rem 0.625rem;
  text-align:center;font-weight:800;font-size:1.375rem;letter-spacing:0.04em;
  border:1px solid #1e293b;letter-spacing:0.04em;
}
table.q2-cust-table th:first-child{width:30%;}
table.q2-cust-table th:nth-child(2),
table.q2-cust-table th:nth-child(3),
table.q2-cust-table th:nth-child(4),
table.q2-cust-table th:nth-child(5){width:14%;}
table.q2-cust-table th:last-child{width:14%;background:#1e293b;}
table.q2-cust-table td{
  padding:0.625rem 0.75rem;border:1px solid #e2e8f0;
  text-align:center;font-variant-numeric:tabular-nums;
}
table.q2-cust-table td.td-name{
  text-align:left;font-weight:600;color:#0f172a;font-size:1.125rem;
  padding-left:0.75rem;background:#f8fafc;
}
table.q2-cust-table td.td-name .row-num{
  display:inline-flex;width:1.5rem;height:1.5rem;align-items:center;
  justify-content:center;font-size:0.8125rem;font-weight:800;color:#fff;
  background:#94a3b8;border-radius:0.25rem;margin-right:0.5rem;flex-shrink:0;
}
table.q2-cust-table td.num-cell{
  font-weight:700;font-size:1.5rem;color:#0f172a;
  font-variant-numeric:tabular-nums;
}
table.q2-cust-table td.num-cell.total{
  font-weight:800;color:#0f172a;background:#fef3c7;
}
table.q2-cust-table tbody tr:nth-child(even){background:#f8fafc;}
table.q2-cust-table tbody tr:hover{background:#bfdbfe !important;box-shadow:inset 0.25rem 0 0 0 #1e40af;}
table.q2-cust-table tr.row-total td{
  background:#e0e7ff;font-weight:800;font-size:0.875rem;
  border-top:0.125rem solid #1e40af!important;
  border-bottom:0.125rem solid #1e40af!important;
}
table.q2-cust-table tr.row-total td.num-cell{
  font-weight:800;color:#1e40af;font-size:0.875rem;
}
/* 合计行第一格（客户名列）加大字号 */
table.q2-cust-table tr.row-total td.td-name{
  font-size:0.9375rem;font-weight:800;letter-spacing:0.02em;
}

"""
