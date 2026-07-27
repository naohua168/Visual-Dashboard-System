"""渲染器基类 — Data-Dense Dashboard 专业数据驾驶舱

设计原则：
  • 深蓝主色 #2563eb + 琥珀金强调 #f59e0b + 紫色辅助 #8b5cf6
  • Inter 正文 + JetBrains Mono 数字等宽字体
  • 卡片化组件：圆角 8px + 轻阴影 + hover 微动效
  • 完成度色块（红/橙/黄/绿色阶）直接嵌入表格单元格
  • 极紧凑布局，全屏满铺无留白
  • 浅灰表头 + 斑马纹 + 蓝色合计行

色阶系统：
  <30% level-1 红    #dc2626
  30-50% level-2 橙  #f97316
  50-80% level-3 黄  #f59e0b
  ≥80% level-4 绿    #16a34a
"""
from __future__ import annotations

from abc import ABC, abstractmethod


GLOBAL_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
/* ═══════════════════════════════════════════════════════════════
   专业数据驾驶舱 — Data-Dense Dashboard 风格
   配色：深蓝主色 #2563eb + 琥珀金强调 #f59e0b + 紫色辅助 #8b5cf6
   字体：Inter（正文）+ JetBrains Mono（数字）
   ═══════════════════════════════════════════════════════════════ */
* { margin:0; padding:0; box-sizing:border-box; }
:root {
  --bg:#eef1f5; --bg-alt:#f5f7fa;
  --surface:#ffffff; --surface-alt:#f8f9fc;
  --border:#e2e5ed; --border-strong:#c5cad5;
  --text:#0f172a; --text-secondary:#475569; --text-muted:#94a3b8;
  --accent:#2563eb; --accent-light:#eff6ff; --accent-dark:#1d4ed8;
  --gold:#f59e0b; --gold-light:#fef3c7;
  --purple:#8b5cf6; --purple-light:#f5f3ff;
  --teal:#0d9488; --teal-light:#f0fdfa;
  --sky:#0284c7; --sky-light:#f0f9ff;
  --red:#dc2626; --red-bg:#fef2f2;
  --orange:#f97316; --orange-bg:#fff7ed;
  --yellow:#ca8a04; --yellow-bg:#fefce8;
  --green:#16a34a; --green-bg:#f0fdf4;
  --total-bg:#eef2ff; --total-text:#3730a3;
  --shadow-sm:0 1px 2px rgba(0,0,0,0.04);
  --shadow-md:0 4px 6px -1px rgba(0,0,0,0.06),0 1px 3px rgba(0,0,0,0.04);
  --shadow-lg:0 10px 15px -3px rgba(0,0,0,0.06),0 4px 6px rgba(0,0,0,0.04);
  --header-h:52px; --nav-h:40px;
}
html,body{height:100%;overflow-x:hidden;}
body{
  font-family:"Inter","Microsoft YaHei",Arial,sans-serif;
  background:var(--bg-alt);color:var(--text);font-size:14px;line-height:1.5;
}
/* 数字表格使用等宽字体 */
table, .kpi-value, .progress-val, .rank, .mini-rate .val, .yoy-up, .yoy-down, .completion{
  font-family:"JetBrains Mono","Inter","Microsoft YaHei",monospace;
}

/* ═══════════════════─ 顶部标题栏 ─══════════════════ */
.header{
  background:#1e293b;color:#ffffff;padding:0 16px;height:var(--header-h);
  position:sticky;top:0;z-index:100;
  display:flex;align-items:center;justify-content:space-between;
  box-shadow:0 1px 3px rgba(0,0,0,0.1);
}
.header-left{display:flex;align-items:center;gap:16px;}
.header-logo{
  width:34px;height:34px;display:flex;align-items:center;justify-content:center;
  font-size:18px;font-weight:800;color:#2563eb;background:#ffffff;border-radius:8px;
}
.header h1{font-size:20px;font-weight:700;letter-spacing:0.02em;color:#f1f5f9;}
.header-right{display:flex;align-items:center;gap:12px;}
.header .meta{font-size:12px;opacity:0.7;color:#94a3b8;}
.fullscreen-btn{
  display:flex;align-items:center;gap:4px;padding:4px 10px;
  background:rgba(255,255,255,0.1);color:#e2e8f0;border:1px solid rgba(255,255,255,0.2);
  border-radius:4px;cursor:pointer;font-size:11px;font-weight:600;transition:all .2s;
}
.fullscreen-btn:hover{background:rgba(255,255,255,0.2);border-color:rgba(255,255,255,0.4);color:#fff;}

/* ═══════════════════─ 导航栏 ─══════════════════ */
.nav{
  background:#f8f9fc;border-bottom:1px solid var(--border);
  padding:0 16px;height:var(--nav-h);
  position:sticky;top:var(--header-h);z-index:90;
  display:flex;gap:0;align-items:stretch;
}
.nav a{
  padding:0 20px;color:var(--text-secondary);text-decoration:none;
  font-size:13px;font-weight:600;display:flex;align-items:center;
  border-bottom:3px solid transparent;transition:all 0.2s;
  letter-spacing:0.02em;
}
.nav a:hover{color:var(--accent);background:#f1f5f9;}
.nav a.active{color:var(--accent);border-bottom-color:var(--accent);background:transparent;}

/* ═══════════════════─ 页面容器 ─══════════════════ */
.page{display:none;padding:8px 10px;height:calc(100vh - var(--header-h) - var(--nav-h));overflow-y:auto;}
.page.active{display:block;}
/* 自定义滚动条 */
.page::-webkit-scrollbar{width:6px;}
.page::-webkit-scrollbar-track{background:transparent;}
.page::-webkit-scrollbar-thumb{background:#c1c1c1;border-radius:3px;}
.page::-webkit-scrollbar-thumb:hover{background:#a8a8a8;}

.section-title{
  font-size:14px;font-weight:700;color:#0f172a;
  margin:10px 0 6px 0;padding:5px 10px;
  display:inline-flex;align-items:center;gap:6px;
  border-radius:6px;letter-spacing:0.03em;
}
.section-title:first-child{margin-top:0;}
.section-title::after{
  content:'';flex:1;height:1px;margin-left:8px;
  min-width:40px;
}
.section-title.sec-blue{background:#eef2ff;color:#2563eb;}
.section-title.sec-blue::after{background:linear-gradient(90deg,#93c5fd,transparent);}
.section-title.sec-green{background:#f0fdf4;color:#16a34a;}
.section-title.sec-green::after{background:linear-gradient(90deg,#86efac,transparent);}
.section-title.sec-orange{background:#fff7ed;color:#f97316;}
.section-title.sec-orange::after{background:linear-gradient(90deg,#fdba74,transparent);}
.section-title.sec-purple{background:#f5f3ff;color:#8b5cf6;}
.section-title.sec-purple::after{background:linear-gradient(90deg,#c4b5fd,transparent);}
.section-title.sec-teal{background:#f0fdfa;color:#0d9488;}
.section-title.sec-teal::after{background:linear-gradient(90deg,#99f6e4,transparent);}
.section-title.sec-sky{background:#f0f9ff;color:#0284c7;}
.section-title.sec-sky::after{background:linear-gradient(90deg,#7dd3fc,transparent);}
.section-title.sec-amber{background:#fffbeb;color:#f59e0b;}
.section-title.sec-amber::after{background:linear-gradient(90deg,#fde68a,transparent);}
/* 分色段落标题 */
.section-title.sec-blue{background:#eef2ff;color:#2563eb;}
.section-title.sec-green{background:#f0fdf4;color:#16a34a;}
.section-title.sec-orange{background:#fff7ed;color:#f97316;}
.section-title.sec-purple{background:#f5f3ff;color:#8b5cf6;}
.section-title.sec-teal{background:#f0fdfa;color:#0d9488;}
.section-title.sec-sky{background:#f0f9ff;color:#0284c7;}
.section-title.sec-amber{background:#fffbeb;color:#f59e0b;}

/* ═══════════════════─ KPI 指标卡 ─══════════════════ */
.kpi-grid{display:grid;gap:4px;margin-bottom:6px;}
.kpi-grid.cols-9{grid-template-columns:repeat(9,1fr);}
.kpi-grid.cols-8{grid-template-columns:repeat(8,1fr);}
.kpi-grid.cols-6{grid-template-columns:repeat(6,1fr);}
.kpi-grid.cols-4{grid-template-columns:repeat(4,1fr);}
.kpi-grid.cols-3{grid-template-columns:repeat(3,1fr);}
.kpi{
  padding:12px 14px;border-radius:10px;
  box-shadow:var(--shadow-sm);position:relative;overflow:hidden;
  transition:box-shadow 0.2s,transform 0.2s;
}
.kpi:hover{
  box-shadow:var(--shadow-md);transform:translateY(-1px);
}
.kpi-label{
  font-size:11px;margin-bottom:4px;font-weight:600;
  text-transform:uppercase;letter-spacing:0.06em;position:relative;z-index:1;
}
.kpi-value{
  font-size:34px;font-weight:800;font-variant-numeric:tabular-nums;line-height:1.15;position:relative;z-index:1;
}
.kpi-unit{font-size:13px;font-weight:500;margin-left:3px;position:relative;z-index:1;}
.kpi-sub{font-size:12px;margin-top:3px;position:relative;z-index:1;}
/* KPI 默认（白底灰字） */
.kpi{background:#fff;border:1px solid var(--border);}
.kpi .kpi-label{color:#5e6c84;}
.kpi .kpi-value{color:#1e293b;}
.kpi .kpi-unit{color:#8892a7;}
.kpi .kpi-sub{color:#8892a7;}
/* 收入 KPI — 蓝底 */
.kpi.kpi-inc{background:#eef2ff;border:1px solid #c7d2fe;}
.kpi.kpi-inc .kpi-label{color:#4338ca;}
.kpi.kpi-inc .kpi-value{color:#2563eb;}
.kpi.kpi-inc .kpi-unit{color:#6366f1;}
.kpi.kpi-inc .kpi-sub{color:#4f46e5;}
/* 回款 KPI — 绿底 */
.kpi.kpi-pay{background:#f0fdf4;border:1px solid #bbf7d0;}
.kpi.kpi-pay .kpi-label{color:#166534;}
.kpi.kpi-pay .kpi-value{color:#16a34a;}
.kpi.kpi-pay .kpi-unit{color:#22c55e;}
.kpi.kpi-pay .kpi-sub{color:#15803d;}
/* 目标 KPI — 橙底 */
.kpi.kpi-tgt{background:#fff7ed;border:1px solid #fed7aa;}
.kpi.kpi-tgt .kpi-label{color:#9a3412;}
.kpi.kpi-tgt .kpi-value{color:#f97316;}
.kpi.kpi-tgt .kpi-unit{color:#f59e0b;}
.kpi.kpi-tgt .kpi-sub{color:#ea580c;}
/* 增长 KPI — 紫底 */
.kpi.kpi-growth{background:#f5f3ff;border:1px solid #ddd6fe;}
.kpi.kpi-growth .kpi-label{color:#5b21b6;}
.kpi.kpi-growth .kpi-value{color:#8b5cf6;}
.kpi.kpi-growth .kpi-unit{color:#a78bfa;}
.kpi.kpi-growth .kpi-sub{color:#7c3aed;}
/* 率值 KPI — 青底 */
.kpi.kpi-rate{background:#f0fdfa;border:1px solid #99f6e4;}
.kpi.kpi-rate .kpi-label{color:#115e59;}
.kpi.kpi-rate .kpi-value{color:#0d9488;}
.kpi.kpi-rate .kpi-unit{color:#14b8a6;}
.kpi.kpi-rate .kpi-sub{color:#0f766e;}
/* 高亮 KPI */
.kpi.kpi-highlight{background:#f0f7ff;border:2px solid #2563eb;}
.kpi.kpi-highlight .kpi-value{color:#1d4ed8;}

/* KPI 行布局（季度分析页专用） */
.kpi-row{
  display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:4px;
}
.kpi-card{
  padding:14px 16px;border-radius:10px;
  background:#fff;border:1px solid var(--border);
  box-shadow:var(--shadow-sm);transition:box-shadow 0.2s,transform 0.2s;
}
.kpi-card:hover{box-shadow:var(--shadow-md);transform:translateY(-1px);}
.kpi-card .kpi-label{font-size:11px;color:#64748b;font-weight:600;margin-bottom:4px;}
.kpi-card .kpi-value{font-size:24px;font-weight:800;color:#1e293b;line-height:1.2;}
.kpi-card .kpi-sub{font-size:11px;color:#94a3b8;margin-top:2px;}

/* 状态徽章 */
.rate-badge{
  display:inline-block;padding:1px 8px;border-radius:10px;
  font-size:11px;font-weight:600;white-space:nowrap;
}
.rate-badge.rate-low{background:#fef2f2;color:#dc2626;}      /* <30% 红 */
.rate-badge.rate-mid{background:#fff7ed;color:#ea580c;}       /* 30-50% 橙 */
.rate-badge.rate-ok{background:#fefce8;color:#ca8a04;}         /* 50-80% 黄 */
.rate-badge.rate-high{background:#f0fdf4;color:#16a34a;}       /* ≥80% 绿 */

/* 销售榜单 */
.sales-roster{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:6px;margin-top:4px;}
.sales-roster-head{
  display:flex;align-items:center;gap:6px;
  padding:6px 10px;border-bottom:1px solid var(--border);margin-bottom:4px;
  font-size:11px;color:#64748b;
}
.sales-amt-head{min-width:110px;text-align:right;}
.sales-rate-head{min-width:50px;text-align:center;}
.sales-chip{
  display:flex;align-items:center;gap:6px;
  padding:6px 10px;border-radius:6px;
  background:#f8fafc;border:1px solid #e2e8f0;
  font-size:13px;transition:box-shadow .15s;
}
.sales-chip:hover{box-shadow:0 1px 4px rgba(0,0,0,.08);}
.sales-name{flex:1;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.sales-amt{
  font-weight:700;color:#1e293b;white-space:nowrap;min-width:110px;text-align:right;
  display:flex;align-items:baseline;justify-content:flex-end;gap:2px;
}
.sales-unit{font-size:10px;color:#94a3b8;font-weight:400;}
.sales-rate{
  font-weight:700;font-size:12px;padding:1px 8px;border-radius:10px;min-width:50px;text-align:center;
  white-space:nowrap;
}
.sales-rate.rate-high{background:#f0fdf4;color:#16a34a;}
.sales-rate.rate-mid{background:#fff7ed;color:#ea580c;}
.sales-rate.rate-low{background:#fef2f2;color:#dc2626;}
.legend{
  margin-top:10px;padding:8px 12px;border-radius:6px;
  background:#f8fafc;border-left:3px solid #2563eb;
  display:flex;flex-direction:column;gap:4px;font-size:11px;color:#475569;
}
.legend-item{line-height:1.5;}
.legend-item b{color:#1e293b;}

/* ═══════════════════─ 数据表格 ─══════════════════ */
.table-wrap{overflow-x:auto;border:1px solid var(--border);border-radius:6px;background:#fff;}
table{width:100%;border-collapse:collapse;font-size:13px;}
th,td{
  padding:6px 10px;text-align:right;
  border-bottom:1px solid #eef0f5;
  white-space:nowrap;font-variant-numeric:tabular-nums;
}
th{
  background:#f8f9fc;color:#475569;font-weight:600;font-size:11px;
  text-transform:uppercase;letter-spacing:0.04em;
  position:sticky;top:0;z-index:5;border-bottom:2px solid #e2e5ed;
}
th:first-child,td:first-child{text-align:left;position:sticky;left:0;z-index:4;}
th:first-child{background:#f1f4f9;z-index:6;}
td:first-child{background:#fff;font-weight:600;color:var(--text);}
tbody tr:nth-child(even){background-color:#fafbfc;}
tbody tr:nth-child(even) td:first-child{background-color:#fafbfc;}
tbody tr:hover{background-color:#eff6ff !important;}
tbody tr:hover td:first-child{background-color:#eff6ff !important;}
tr.total td{
  background:#eef2ff !important;font-weight:700;color:#4338ca;
  border-top:2px solid #c7d2fe;
}
tr.total td:first-child{background:#e0e7ff !important;color:#3730a3;}
/* 表格内数字高亮 */
td.num-em{color:#2563eb;font-weight:700;}
td.num-red{color:#dc2626;font-weight:700;}
td.num-green{color:#16a34a;font-weight:700;}
td.num-orange{color:#f97316;font-weight:700;}

/* ═══════════════════─ Excel 条件格式数据条 ─══════════════════ */
.completion{
  display:inline-flex;align-items:center;height:28px;min-width:75px;max-width:100%;
  font-size:14px;font-weight:800;font-variant-numeric:tabular-nums;
  color:var(--text);padding:0 2px;position:relative;overflow:hidden;
  border-radius:3px;
}
.completion .pct{
  position:relative;z-index:1;padding:0 6px;
  text-align:center;line-height:28px;letter-spacing:0.02em;
}
.completion.level-1{background:#fee2e2;color:#dc2626;border:2px solid #fecaca;}
.completion.level-2{background:#ffedd5;color:#ea580c;border:2px solid #fed7aa;}
.completion.level-3{background:#fef3c7;color:#ca8a04;border:2px solid #fde68a;}
.completion.level-4{background:#dcfce7;color:#16a34a;border:2px solid #bbf7d0;}

/* ═══════════════════─ 进度条 ─══════════════════ */
.progress-row{
  display:grid;grid-template-columns:80px 1fr 90px 80px;gap:8px;
  align-items:center;padding:6px 12px;
  font-size:13px;background:#fff;margin-bottom:2px;
  border:1px solid var(--border);border-radius:3px;
}
.progress-row:first-child{
  background:transparent;border:none;font-size:11px;
  color:var(--text-muted);font-weight:700;margin-bottom:2px;
}
.progress-track{
  height:16px;background:#f2f2f2;
  overflow:hidden;position:relative;
  border:1px solid #d4d4d4;border-radius:8px;
}
.progress-fill{
  height:100%;position:relative;min-width:2px;
  border-radius:8px;
}
.progress-fill.level-1{background:#dc2626;}
.progress-fill.level-2{background:#f97316;}
.progress-fill.level-3{background:#f59e0b;}
.progress-fill.level-4{background:#16a34a;}
.progress-fill .pct{
  position:absolute;right:6px;top:50%;transform:translateY(-50%);
  font-size:10px;color:#fff;font-weight:700;
}
.progress-val{text-align:right;font-weight:700;font-variant-numeric:tabular-nums;color:var(--accent);font-size:14px;}
.progress-tgt{text-align:right;font-size:11px;color:var(--text-muted);font-variant-numeric:tabular-nums;}


/* ═══════════════════─ 卡片容器 ─══════════════════ */
.card{
  background:#fff;padding:12px 14px;
  border:1px solid var(--border);margin-bottom:6px;
  border-radius:10px;box-shadow:var(--shadow-sm);
  transition:box-shadow 0.2s,transform 0.2s;
}
.card-title{
  font-size:14px;font-weight:700;color:#0f172a;margin-bottom:8px;
  padding-bottom:6px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;justify-content:space-between;
  letter-spacing:0.02em;
}
.card-title::before{
  content:'';display:inline-block;width:3px;height:14px;
  background:var(--accent);border-radius:2px;margin-right:8px;
}

/* ═══════════════════─ 网格布局 ─══════════════════ */
.cols-2{display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-bottom:4px;}
.cols-3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:4px;margin-bottom:4px;}
.cols-4{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:4px;margin-bottom:4px;}

/* ═══════════════════─ 迷你数据条 ─══════════════════ */
.mini-rate{display:flex;align-items:center;gap:8px;padding:4px 0;font-size:13px;}
.mini-rate .bar{
  flex:1;height:14px;background:#eef0f5;
  overflow:hidden;border-radius:5px;position:relative;
  min-width:80px;
}
.mini-rate .bar-fill{height:100%;min-width:2px;border-radius:5px;position:relative;}
.mini-rate .bar-pct{
  position:absolute;right:4px;top:50%;transform:translateY(-50%);
  font-size:10px;font-weight:800;line-height:14px;
  color:#334155;
  letter-spacing:0.02em;pointer-events:none;
}
.mini-rate .bar-fill.level-1{background:#dc2626;}
.mini-rate .bar-fill.level-2{background:#f97316;}
.mini-rate .bar-fill.level-3{background:#f59e0b;}
.mini-rate .bar-fill.level-4{background:#16a34a;}
.mini-rate .val{min-width:70px;text-align:right;font-weight:700;font-variant-numeric:tabular-nums;color:#1e293b;}
.pct-tag{
  display:inline-block;min-width:54px;padding:2px 6px;text-align:center;
  font-size:11px;font-weight:800;font-variant-numeric:tabular-nums;
  border-radius:3px;letter-spacing:0.02em;
}
.pct-tag.level-1{background:#fee2e2;color:#dc2626;border:1px solid #fecaca;}
.pct-tag.level-2{background:#ffedd5;color:#ea580c;border:1px solid #fed7aa;}
.pct-tag.level-3{background:#fef3c7;color:#ca8a04;border:1px solid #fde68a;}
.pct-tag.level-4{background:#dcfce7;color:#16a34a;border:1px solid #bbf7d0;}

/* ═══════════════════─ 排名徽章 ─══════════════════ */
.rank{
  display:inline-flex;width:22px;height:22px;align-items:center;justify-content:center;
  font-size:11px;font-weight:800;margin-right:4px;flex-shrink:0;color:#fff;
  border-radius:4px;
}
.rank-1{background:#dc2626;}
.rank-2{background:#f97316;}
.rank-3{background:#f59e0b;}
.rank-n{background:#94a3b8;color:#fff;}

/* ═══════════════════─ 表格行高亮 ─══════════════════ */
tr.rank-top td{background:#fee2e2 !important;font-weight:700;}
tr.row-pending td{background:#fef9c3 !important;}
tr.row-pending td:first-child{background:#fef08a !important;}

/* ═══════════════════─ 行内数据条 ─══════════════════ */
.bar-cell{height:4px;background:#eef0f5;overflow:hidden;margin-top:3px;border-radius:2px;}
.bar-fill-cell{height:100%;background:#2563eb;min-width:2px;border-radius:2px;}

/* ═══════════════════─ 同比色块 ─══════════════════ */
.yoy-up{
  display:inline-block;padding:2px 8px;font-weight:700;
  font-variant-numeric:tabular-nums;font-size:11px;border-radius:4px;
  background:#fee2e2;color:#dc2626;
}
.yoy-down{
  display:inline-block;padding:2px 8px;font-weight:700;
  font-variant-numeric:tabular-nums;font-size:11px;border-radius:4px;
  background:#dcfce7;color:#16a34a;
}
.yoy-neutral{color:var(--text-muted);font-weight:600;}

/* ═══════════════════─ 同比对比单元格 ──────────────── */
.yoy-cell{
  padding:6px 8px;min-width:140px;vertical-align:top;
}
.yoy-amount{font-size:13px;font-weight:700;color:var(--text);font-variant-numeric:tabular-nums;}
.yoy-bars{
  display:flex;flex-direction:column;gap:2px;margin:4px 0 2px;
  position:relative;
}
.yoy-bar{height:5px;border-radius:3px;min-width:2px;transition:width 0.3s ease;}
.yoy-bar.cur{background:var(--accent);position:relative;}
.yoy-bar.prev{background:#cbd5e1;}
.yoy-pct{
  display:inline-block;font-size:11px;font-weight:800;font-variant-numeric:tabular-nums;
  padding:1px 6px;border-radius:3px;margin-top:2px;
}
.yoy-pct.up{background:#fee2e2;color:#dc2626;}
.yoy-pct.down{background:#dcfce7;color:#16a34a;}
.yoy-pct.flat{background:#f1f5f9;color:#64748b;}
.yoy-prev-amt{font-size:10px;color:var(--text-muted);font-variant-numeric:tabular-nums;margin-top:1px;}

/* ═══════════════════─ 同比趋势箭头 ─────────────── */
.yoy-arrow{
  display:inline-flex;align-items:center;justify-content:center;
  width:18px;height:18px;font-size:11px;font-weight:800;
  border-radius:4px;margin-right:2px;
}
.yoy-arrow.up{background:#fee2e2;color:#dc2626;}
.yoy-arrow.down{background:#dcfce7;color:#16a34a;}
.yoy-arrow.flat{background:#f1f5f9;color:#64748b;}

/* ═══════════════════─ 同比周期 chip ───────────── */
.period-chip{
  display:flex;align-items:center;gap:8px;margin-bottom:6px;padding:6px 12px;
  background:#f1f5f9;border-radius:4px;border-left:3px solid var(--accent);
}
.period-tag{
  display:inline-block;background:var(--accent);color:#fff;
  padding:2px 10px;font-size:11px;font-weight:700;border-radius:3px;
  letter-spacing:0.04em;
}
.period-text{font-size:12px;color:var(--text-secondary);font-weight:500;}

/* ═══════════════════─ 同比大对比卡（2 卡布局） ───────────── */
.yoy-big-card{
  padding:14px 18px;border-radius:8px;
  display:grid;grid-template-columns:1fr 1.6fr;gap:14px;align-items:center;
  border:2px solid;border-left-width:6px;
}
.yoy-big-card.up{background:linear-gradient(135deg,#fef2f2,#fee2e2);border-color:#fca5a5;border-left-color:#dc2626;}
.yoy-big-card.down{background:linear-gradient(135deg,#f0fdf4,#dcfce7);border-color:#86efac;border-left-color:#16a34a;}
.yoy-big-card.flat{background:linear-gradient(135deg,#f8fafc,#f1f5f9);border-color:#cbd5e1;border-left-color:#94a3b8;}
.yoy-big-label{
  font-size:12px;color:var(--text-secondary);
  font-weight:700;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;
}
.yoy-big-pct{
  font-size:46px;font-weight:800;line-height:1.1;letter-spacing:-0.02em;
  font-variant-numeric:tabular-nums;
}
.yoy-big-arrow{
  font-size:14px;font-weight:700;color:var(--text-muted);margin-top:4px;
  display:flex;align-items:center;gap:6px;
}
.yoy-big-arrow .yoy-arrow{width:24px;height:24px;font-size:13px;}
.yoy-big-compare{
  display:flex;flex-direction:column;gap:6px;
  background:rgba(255,255,255,0.6);padding:8px 12px;border-radius:6px;
}
.yoy-cmp-item{display:grid;grid-template-columns:50px 1fr;gap:8px;align-items:center;}
.yoy-cmp-label{font-size:10px;font-weight:700;color:var(--text-muted);text-transform:uppercase;}
.yoy-cmp-val{font-size:14px;font-weight:800;color:var(--text);font-variant-numeric:tabular-nums;grid-column:2;}
.yoy-cmp-unit{font-size:10px;font-weight:500;color:var(--text-muted);margin-left:2px;}
.yoy-cmp-item.prev .yoy-cmp-label{color:var(--text-muted);}
.yoy-cmp-item.prev .yoy-cmp-val{color:var(--text-secondary);font-size:12px;font-weight:600;}
.yoy-cmp-bar{
  height:6px;background:rgba(0,0,0,0.06);border-radius:3px;overflow:hidden;
  grid-column:2;margin-top:2px;
}
.yoy-cmp-fill{height:100%;border-radius:3px;}
.yoy-cmp-fill.cur.up{background:linear-gradient(90deg,#b91c1c,#dc2626);}
.yoy-cmp-fill.cur.down{background:linear-gradient(90deg,#15803d,#16a34a);}
.yoy-cmp-fill.prev.up{background:linear-gradient(90deg,#94a3b8,#cbd5e1);}
.yoy-cmp-fill.prev.down{background:linear-gradient(90deg,#94a3b8,#cbd5e1);}

/* ═══════════════════─ 图表容器 ─══════════════════ */
.chart-box{
  background:#fff;padding:14px;margin-bottom:4px;
  border:1px solid var(--border);border-radius:10px;
  box-shadow:var(--shadow-sm);
}
.chart-box canvas{min-height:220px;}
.chart-title{font-size:14px;font-weight:700;margin-bottom:6px;color:#1e293b;}

/* ═══════════════════─ 表格折叠 ─══════════════════ */
.table-collapse{max-height:500px;overflow:hidden;position:relative;}
.table-collapse.collapsed{max-height:none;}
.table-collapse .collapse-overlay{
  display:none;
  position:absolute;bottom:0;left:0;right:0;height:60px;
  background:linear-gradient(transparent,#fff);z-index:8;
  pointer-events:none;
}
.table-collapse.collapsed .collapse-overlay{display:block;}
.collapse-btn{
  display:block;width:100%;padding:6px;margin-bottom:4px;
  font-size:12px;font-weight:600;text-align:center;
  background:var(--accent-light);color:var(--accent);
  border:1px solid var(--accent);cursor:pointer;border-radius:2px;
}
.collapse-btn:hover{background:var(--accent);color:#fff;}


/* ═══════════════════─ 预警横幅 ─══════════════════ */
.alert-banner{
  display:flex;align-items:center;gap:8px;padding:8px 12px;margin-bottom:4px;
  font-size:12px;font-weight:600;border-radius:6px;
}
.alert-banner.warn{background:#ffedd5;color:#c2410c;border:1px solid #fed7aa;}
.alert-banner.danger{background:#fee2e2;color:#b91c1c;border:1px solid #fecaca;}
.alert-banner.info{background:#dbeafe;color:#1d4ed8;border:1px solid #bfdbfe;}
.alert-banner .badge{
  background:currentColor;color:#fff;padding:1px 10px;font-size:9px;font-weight:700;margin-left:auto;
}

/* ═══════════════════─ 空状态 ─══════════════════ */
.empty{
  text-align:center;padding:40px;color:var(--text-muted);font-size:12px;
  background:#fff;border:1px dashed var(--border);
}

/* ═══════════════════─ 年度目标总览块 ─══════════════════ */
.target-hero{
  background:linear-gradient(135deg,#1e293b,#334155);color:#fff;padding:16px 24px;text-align:center;margin-bottom:6px;
  border-radius:8px;
}
.target-hero .label{
  font-size:11px;opacity:0.7;letter-spacing:0.08em;text-transform:uppercase;
}
.target-hero .value{
  font-size:36px;font-weight:800;font-variant-numeric:tabular-nums;margin:4px 0;
  color:#fbbf24;
}
.target-hero .unit{font-size:14px;font-weight:500;opacity:0.8;}

/* ═══════════════════─ 年度达成 Hero（深底大数字 + 双进度） ─══════════════════ */
.annual-hero{
  background:linear-gradient(135deg,#0a1628 0%,#1e3a5f 50%,#0a1628 100%);
  color:#fff;padding:18px 24px;margin-bottom:6px;border-radius:8px;
  display:flex;align-items:center;gap:20px;flex-wrap:wrap;
  box-shadow:0 4px 12px rgba(10,22,40,0.25);
}
.annual-hero-label{
  font-size:12px;opacity:0.7;letter-spacing:0.08em;text-transform:uppercase;
  min-width:120px;font-weight:600;
}
.annual-hero-value{
  font-size:42px;font-weight:800;font-variant-numeric:tabular-nums;
  color:#fbbf24;flex:0 0 auto;letter-spacing:0.02em;
}
.annual-hero-unit{font-size:16px;font-weight:500;opacity:0.85;margin-left:6px;}
.annual-hero-bars{flex:1;min-width:400px;display:flex;flex-direction:column;gap:8px;}
.annual-hero-bar{display:flex;align-items:center;gap:10px;}
.annual-hero-name{font-size:13px;font-weight:700;min-width:42px;}
.annual-hero-track{
  flex:1;height:18px;background:rgba(255,255,255,0.12);
  border-radius:9px;overflow:hidden;position:relative;
}
.annual-hero-fill{
  height:100%;border-radius:9px;display:flex;align-items:center;
  justify-content:flex-end;padding-right:10px;
  color:#fff;font-size:11px;font-weight:800;letter-spacing:0.02em;
  min-width:36px;transition:width 0.5s ease;
}
.annual-hero-fill.inc{background:linear-gradient(90deg,#1e40af,#2563eb);}
.annual-hero-fill.pay{background:linear-gradient(90deg,#15803d,#16a34a);}
.annual-hero-val{font-size:13px;font-weight:700;font-variant-numeric:tabular-nums;color:#e0e7ff;min-width:80px;text-align:right;}
.annual-hero-arrow{font-size:14px;color:#cbd5e1;font-weight:700;margin-left:6px;transition:transform 0.2s;}
.annual-hero-bar.expanded .annual-hero-arrow{transform:rotate(90deg);color:#fbbf24;}

/* 折叠/展开 */
.hidden{display:none !important;}

/* ═══════════════════─ 重要客户 tab 切换 ───────── */
.cust-tabs{
  display:flex;gap:6px;margin:0 0 6px 0;
  border-bottom:2px solid var(--border);
}
.cust-tab{
  padding:6px 18px;font-size:13px;font-weight:700;cursor:pointer;
  border-radius:6px 6px 0 0;color:var(--text-muted);
  background:var(--surface-alt);
  border:1px solid var(--border);
  border-bottom:none;
  transition:all 0.2s;
}
.cust-tab:hover{background:#e2e8f0;color:var(--text);}
.cust-tab.active.inc{background:var(--accent);color:#fff;border-color:var(--accent);}
.cust-tab.active.pay{background:#16a34a;color:#fff;border-color:#16a34a;}

/* ═══════════════════─ 矩阵表（ann-matrix 紧凑布局） ───────── */
table.ann-matrix, .table-wrap table.ann-matrix, .ann-matrix{
  width:100%;border-collapse:collapse;font-size:12px;background:#fff;
  border:1px solid #e2e5ed;
}
table.ann-matrix th, table.ann-matrix td,
.ann-matrix th, .ann-matrix td{
  padding:6px 10px;text-align:right;
  border:1px solid #e2e5ed;vertical-align:middle;font-size:12px;
  line-height:1.3;
}
table.ann-matrix thead th,
.ann-matrix thead th{
  background:#1e293b;color:#ffffff;font-weight:700;font-size:11px;
  letter-spacing:0.04em;text-transform:uppercase;
  position:sticky;top:0;z-index:5;text-align:center;
  border-color:#334155;padding:8px 10px;
}
table.ann-matrix .th-name, .ann-matrix .th-name{text-align:left;min-width:160px;}
/* 客户名列 */
table.ann-matrix .td-name, .ann-matrix .td-name{
  text-align:left;font-weight:600;color:#0f172a;font-size:12px;white-space:nowrap;
}
table.ann-matrix .td-name .row-num, .ann-matrix .td-name .row-num{
  display:inline-flex;width:18px;height:18px;align-items:center;justify-content:center;
  font-size:9px;font-weight:800;color:#fff;background:#94a3b8;
  border-radius:3px;margin-right:6px;flex-shrink:0;
}
/* 行高亮 */
table.ann-matrix tbody tr:hover td, .ann-matrix tbody tr:hover td{
  background:#eff6ff !important;
}
table.ann-matrix tbody tr:nth-child(even) td, .ann-matrix tbody tr:nth-child(even) td{
  background:#fafbfc;
}
/* 合计行 — 不影响 cell-bg 单元格 */
table.ann-matrix .row-total td:not(.cell-bg),
.ann-matrix .row-total td:not(.cell-bg){
  background:#dbeafe;font-weight:700;color:#1e3a8a;
  border-top:3px solid #2563eb;border-bottom:2px solid #2563eb;
}
table.ann-matrix .td-total, .ann-matrix .td-total{font-weight:700;}
/* 单元格主次层次（紧凑） */
.cell-main{font-size:13px;font-weight:700;color:#0f172a;line-height:1.2;}
.cell-sub{font-size:10px;color:var(--text-muted);margin-top:1px;line-height:1.2;}
/* ══════════ 格子背景填充（按完成度宽度+左右布局）══════════ */
td.cell-bg{
  position:relative; padding:7px 8px; overflow:hidden;
  border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0;
  background:#f8fafc;
  vertical-align:middle;
}
td.cell-bg .fill-bg{
  position:absolute; top:0; left:0; bottom:0;
  width:var(--pct, 0%);
  background:var(--fill, #fb923c);
  z-index:0;
}
td.cell-bg .cell-text{
  position:relative; z-index:1;
  display:flex; align-items:center; justify-content:space-between;
  gap:4px;
  height:100%;
}
/* 百分比在左 — 大字突出 */
td.cell-bg .cell-text .cell-pct{
  font-size:18px;line-height:1; font-weight:800;letter-spacing:-0.5px;
  color:#0f172a;
  text-shadow:
    0 0 5px rgba(255,255,255,0.95),
    0 0 10px rgba(255,255,255,0.85),
    0 2px 4px rgba(255,255,255,0.9);
  flex-shrink:0;
}
/* 金额在右 — 完成+指标两行 */
td.cell-bg .cell-text .cell-main{
  display:flex; flex-direction:column; align-items:flex-end;
  font-size:11.5px;line-height:1.25;font-weight:600;color:#334155;
  text-align:right; flex:1; min-width:0;
}
td.cell-bg .cell-text .cell-main .cell-act{color:#0f172a;font-weight:700;}
td.cell-bg .cell-text .cell-main .cell-tgt{color:#64748b;font-size:10.5px;margin-top:1px;}
td.cell-bg .cell-text .cell-pct.up{color:#dc2626;}
td.cell-bg .cell-text .cell-pct.down{color:#16a34a;}
td.cell-bg .cell-text .cell-pct.achieved{color:#16a34a;}
td.cell-bg .cell-text .cell-pct.low{color:#b45309;}
/* 0% 不显示填充（浅灰底） */
td.cell-bg.is-empty .fill-bg{display:none;}
/* 合计列：实色背景+白字（强制优先级超过所有 hover） */
td.cell-bg.is-total{
  background:var(--accent)!important;
  border-color:rgba(255,255,255,0.25);
  border-top:3px solid #1d4ed8!important;
  border-bottom:2px solid #1d4ed8!important;
}
td.cell-bg.is-total .cell-text{color:#fff!important;text-shadow:none!important;}
td.cell-bg.is-total .cell-text .cell-main{color:#fff!important;font-size:13.5px!important;}
td.cell-bg.is-total .cell-text .cell-pct{color:#fff!important;font-size:19px!important;text-shadow:none!important;}
/* hover 时合计列也保持白字 */
table.ann-matrix tbody tr:hover td.cell-bg.is-total,
table.ann-matrix tbody tr:hover td.cell-bg.is-total .cell-text,
table.ann-matrix tbody tr:hover td.cell-bg.is-total .cell-text *,
table.ann-matrix tbody tr:hover td.cell-bg.is-total .cell-text .cell-main,
table.ann-matrix tbody tr:hover td.cell-bg.is-total .cell-text .cell-pct{
  color:#fff!important;
  background:var(--accent)!important;
  text-shadow:none!important;
}
/* 悬停加深（仅普通格） */
table.ann-matrix tbody tr.row-data:hover td.cell-bg:not(.is-total) .fill-bg{ filter:brightness(0.92); }
/* 空单元格 */
table.ann-matrix .td-empty, .ann-matrix .td-empty{
  text-align:center;color:#94a3b8;font-size:14px;padding:8px 0;
}

/* ══════════ 事业部同比专用表（双维度清晰对比）══════════ */
table.yoy-dept-table{width:100%;border-collapse:collapse;font-size:13px;}
table.yoy-dept-table th{
  background:linear-gradient(180deg,#1e3a5f 0%,#1a365d 100%);
  color:#e2e8f0;padding:10px 12px;text-align:center;
  font-weight:700;font-size:12px;letter-spacing:0.5px;border:1px solid #2d4a6f;
}
table.yoy-dept-table th.group-header{
  font-size:14px;padding:10px 4px;letter-spacing:2px;
}
table.yoy-dept-table th.inc-group{background:linear-gradient(180deg,#7c2d12 0%,#9a3412 100%);}
table.yoy-dept-table th.pay-group{background:linear-gradient(180deg,#065f46 0%,#064e3b 100%);}
table.yoy-dept-table td{padding:9px 10px;border:1px solid #e2e8f0;text-align:center;}
table.yoy-dept-table tbody tr:nth-child(even){background:#f8fafc;}
table.yoy-dept-table tbody tr:hover{background:#f1f5f9;}
/* 事业部名称列 */
table.yoy-dept-table td.dept-name{
  text-align:left;font-weight:800;font-size:14px;color:#1e293b;
  padding-left:16px;background:#f1f5f9;border-left:4px solid var(--accent);
}
/* 数值单元格 */
table.yoy-dept-table td.num-cell{
  font-weight:600;font-size:13px;color:#334155;font-variant-numeric:tabular-nums;
}
table.yoy-dept-table td.num-cell.muted{color:#94a3b8;font-size:12px;}
/* 同比单元格 — 核心视觉焦点 */
table.yoy-dept-table td.yoy-cell{
  padding:6px 4px;min-width:90px;
}
table.yoy-dept-table .yoy-pct{
  display:inline-block;padding:6px 12px;border-radius:6px;
  font-weight:900;font-size:15px;letter-spacing:-0.3px;
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
table.yoy-matrix-table{width:100%;border-collapse:collapse;font-size:12.5px;}
table.yoy-matrix-table th{
  background:linear-gradient(180deg,#1e3a5f 0%,#1a365d 100%);
  color:#e2e8f0;padding:8px 10px;text-align:center;
  font-weight:700;font-size:12px;letter-spacing:0.5px;border:1px solid #2d4a6f;
}
table.yoy-matrix-table td{padding:7px 6px;border:1px solid #e2e8f0;text-align:center;vertical-align:middle;}
table.yoy-matrix-table tbody tr:nth-child(even){background:#fafbfc;}
table.yoy-matrix-table tbody tr:hover{background:#f1f5f9;}
/* 客户名称 */
table.yoy-matrix-table td.td-name{text-align:left;font-size:13px;color:#334155;padding-left:12px;}
table.yoy-matrix-table .row-num{display:inline-block;width:22px;height:22px;line-height:22px;
  text-align:center;background:#dbeafe;color:#1d4ed8;border-radius:50%;
  font-size:11px;font-weight:800;margin-right:8px;flex-shrink:0;}
/* 矩阵单元格 — 垂直布局：徽章上+金额下 */
table.yoy-matrix-table td.mx-cell{padding:5px 4px;min-width:80px;}
/* 同比徽章 */
table.yoy-matrix-table .mx-badge{
  display:block;padding:4px 8px;border-radius:5px;
  font-weight:900;font-size:13px;letter-spacing:-0.3px;
  margin-bottom:3px;line-height:1.2;white-space:nowrap;
}
/* 当期金额 */
table.yoy-matrix-table .mx-val{
  display:block;font-size:11px;color:#64748b;font-weight:600;
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
  border-color:#991b1b;box-shadow:0 2px 6px rgba(220,38,38,0.25);
}
/* 下降 — 绿 */
table.yoy-matrix-table td.mx-cell.down .mx-badge{
  background:linear-gradient(135deg,#f0fdf4,#dcfce7);
  color:#16a34a;border:1px solid #bbf7d0;
}
table.yoy-matrix-table td.mx-cell.down[data-big] .mx-badge,
table.yoy-matrix-table td.mx-cell.down:hover .mx-badge{
  background:linear-gradient(135deg,#16a34a,#166534);color:#fff;
  border-color:#15803d;box-shadow:0 2px 6px rgba(22,163,74,0.25);
}
/* 持平 — 灰 */
table.yoy-matrix-table td.mx-cell.flat .mx-badge{
  background:#f1f5f9;color:#94a3b8;border:1px solid #e2e8f0;
}
/* 合计行 */
table.yoy-matrix-table tr.row-total{background:linear-gradient(90deg,#eff6ff,#f0fdf4)!important;}
table.yoy-matrix-table tr.row-total td{font-weight:700;border-top:2px solid var(--accent);}
/* 空格 */
table.yoy-matrix-table .td-empty{color:#cbd5e1;font-style:italic;}

/* ══════════ 客户同比 Tab 切换容器 ══════════ */
.yoy-cust-tabs .tab-header{
  display:flex;gap:0;margin-bottom:0;
  border-bottom:2px solid #e2e8f0;padding:0 4px;
}
.yoy-cust-tabs .tab-btn{
  padding:10px 24px;border:none;background:transparent;
  font-size:14px;font-weight:700;color:#64748b;cursor:pointer;
  border-radius:8px 8px 0 0;transition:all 0.2s;
  letter-spacing:0.3px;
}
.yoy-cust-tabs .tab-btn:hover{background:#f1f5f9;color:#334155;}
.yoy-cust-tabs .tab-btn.active{
  background:#1e40af;color:#fff;
  box-shadow:0 -2px 8px rgba(30,64,175,0.15);
}
.yoy-cust-tabs .tab-panel{display:none;}
.yoy-cust-tabs .tab-panel.active{display:block;}

/* ═══════════════════─ 响应式 ─══════════════════ */
@media(max-width:1200px){
  .kpi-grid.cols-9,.kpi-grid.cols-8,.kpi-grid.cols-6{grid-template-columns:repeat(4,1fr);}
  .cols-3{grid-template-columns:1fr 1fr;}
}
@media(max-width:768px){
  .header{padding:0 8px;}
  .header h1{font-size:17px;}
  .nav{padding:0 6px;}
  .nav a{padding:5px 10px;font-size:12px;}
  .page{padding:6px;}
  .kpi-grid.cols-9,.kpi-grid.cols-8,.kpi-grid.cols-3,.kpi-grid.cols-4,.kpi-grid.cols-6{grid-template-columns:1fr 1fr;}
  .cols-2,.cols-3{grid-template-columns:1fr;}
  .kpi-value{font-size:28px;}
  table{font-size:13px;}
  .progress-row{grid-template-columns:60px 1fr 75px 65px;font-size:12px;}
  .progress-tgt{display:none;}
}
@media(max-width:480px){
  .kpi-grid.cols-9,.kpi-grid.cols-8,.kpi-grid.cols-3,.kpi-grid.cols-4,.kpi-grid.cols-6{grid-template-columns:1fr;}
}

/* ══════════════════════════════════════════════════════
   动画系统 — 6项动画
   ══════════════════════════════════════════════════════ */

/* 1. 页面切换过渡 — pageIn */
@keyframes pageIn {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}
.page.active { animation: pageIn .35s ease-out; }

/* 2. KPI卡片交错入场 — fadeUp (延迟由 JS 动态添加) */
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(24px); }
  to { opacity: 1; transform: translateY(0); }
}
.anim-fade-up { animation: fadeUp .45s ease-out both; }

/* 3. 进度条填充动画 - 仅在 .mini-rate 内的 .bar-fill 加过渡 */
.mini-rate .bar-fill { transition: width .6s cubic-bezier(0.22, 1, 0.36, 1); }
.annual-hero-fill { transition: width 1s cubic-bezier(0.22, 1, 0.36, 1); }

/* 4. Tab淡入切换 */
@keyframes tabIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
.tab-panel.active { animation: tabIn .2s ease; }

/* 5. 页面容器预留动画空间 */
.page { transform: translateY(0); }
"""

GLOBAL_JS = """
// ══════════════════════════════════════════════════════
// 页面切换 + 动画触发
// ══════════════════════════════════════════════════════
function showPage(id){
  document.querySelectorAll('.page').forEach(function(p){p.classList.remove('active');});
  document.querySelectorAll('.nav a').forEach(function(a){a.classList.remove('active');});
  var pageEl=document.getElementById(id);
  if(!pageEl){
    console.warn('Page not found:', id);
    return;
  }
  pageEl.classList.add('active');
  // 触发卡片交错入场动画
  delayAnim(pageEl, '.kpi, .hero-kpi, .ring-kpi, .mini-rate, .kpi-row>*', 80);
  var t=document.querySelector('.nav a[data-target="'+id+'"]');
  if(t)t.classList.add('active');
  setTimeout(window.__resizeAllCharts, 100);
}

/* ══════════════════════════════════════════════════════
   数字递增计数（#3）
   ══════════════════════════════════════════════════════ */
function animateNumber(el, target, suffix, duration){
  if(!el) return;
  var start=0;
  var step=Math.max(1, Math.floor(target / (duration/16)));
  var current=start;
  function tick(){
    current+=step;
    if(current>=target){
      el.textContent=target.toLocaleString('zh-CN')+(suffix||'');
      return;
    }
    el.textContent=current.toLocaleString('zh-CN')+(suffix||'');
    requestAnimationFrame(tick);
  }
  tick();
}

/* ══════════════════════════════════════════════════════
   卡片交错入场（#2）
   ══════════════════════════════════════════════════════ */
function delayAnim(container, selector, delayMs){
  if(!container) return;
  var items=container.querySelectorAll(selector);
  items.forEach(function(el,i){
    el.classList.add('anim-fade-up');
    el.style.animationDelay=(i*delayMs)+'ms';
  });
}

// ══════════════════════════════════════════════════════
// Chart.js 全局默认（蓝白主题 + 自定义动画 #6）
// ══════════════════════════════════════════════════════
if(typeof Chart!=='undefined'){
  Chart.defaults.color='#595959';
  Chart.defaults.borderColor='#d4d4d4';
  Chart.defaults.font.family='"Segoe UI","Microsoft YaHei",Arial,sans-serif';
  Chart.defaults.font.size=10;
  Chart.defaults.maintainAspectRatio=false;
  // 自定义图表入场动画
  Chart.defaults.animation={duration:1200,easing:'easeOutQuart'};
}

// ══════════════════════════════════════════════════════
// 图表注册器（直接创建 + 切换时 resize）
// ══════════════════════════════════════════════════════
window.__charts={};
window.__regChart=function(id,config){
  var el=document.getElementById(id);if(!el)return null;
  try{
    var chart=new Chart(el,config);
    window.__charts[id]=chart;
    setTimeout(function(){try{chart.resize();}catch(e){}}, 50);
    return chart;
  }catch(e){
    console.warn('Chart init failed:', id, e);
    return null;
  }
};
window.__resizeAllCharts=function(){
  if(window.__charts)Object.values(window.__charts).forEach(function(c){try{c.resize()}catch(e){}});
};

// ══════════════════════════════════════════════════════
// 自动表格折叠
// ══════════════════════════════════════════════════════
function initTableCollapse(){
  document.querySelectorAll('.page.active .table-wrap').forEach(function(w){
    if(w.classList.contains('_collapsed'))return;
    if(w.classList.contains('no-collapse'))return;
    var h=w.scrollHeight;
    if(h>500){
      w.classList.add('table-collapse','collapsed');
      w.classList.add('_collapsed');
      var ov=document.createElement('div');
      ov.className='collapse-overlay';
      w.appendChild(ov);
      var btn=document.createElement('button');
      btn.className='collapse-btn';
      btn.textContent='展开全部数据 ▾';
      btn.onclick=function(){
        w.classList.toggle('collapsed');
        this.textContent=w.classList.contains('collapsed')?'展开全部数据 ▾':'收起多余 ▴';
      };
      w.parentNode.insertBefore(btn,w.nextSibling);
    }else{
      w.classList.add('_collapsed');
    }
  });
}

// 页面切换时触发
var _origShowPage=showPage;
showPage=function(id){
  _origShowPage(id);
  setTimeout(initTableCollapse,50);
};
setTimeout(initTableCollapse,200);
// 首屏动画
setTimeout(function(){
  var firstPage=document.querySelector('.page.active');
  if(firstPage) delayAnim(firstPage, '.kpi, .hero-kpi, .ring-kpi, .mini-rate, .kpi-row>*', 80);
}, 300);

// ══════════════════════════════════════════════════════
// Tab 切换（统一事件委托 + 淡入 #5）
// ══════════════════════════════════════════════════════
function switchTab(btn){
  var tabId = btn.getAttribute('data-tab');
  if(!tabId) return;
  var container = btn.closest('.yoy-cust-tabs, .cust-tabs');
  if(!container) return;
  container.querySelectorAll('.tab-btn, .cust-tab').forEach(function(b){
    b.classList.remove('active');
  });
  btn.classList.add('active');
  container.querySelectorAll('.tab-panel, [id]').forEach(function(p){
    if(p.classList && p.classList.contains('tab-panel')){
      p.classList.remove('active');
      if(p.id === tabId) p.classList.add('active');
    }
  });
  var target = document.getElementById(tabId);
  if(target){
    if(target.classList.contains('tab-panel')){
      // 已在上面处理
    } else {
      var parent = target.parentElement;
      if(parent){
        Array.from(parent.children).forEach(function(c){
          if(c.id) c.classList.add('hidden');
        });
      }
      target.classList.remove('hidden');
    }
  }
}
// 统一 .cust-tab 事件委托
document.addEventListener('click', function(e){
  var tab = e.target.closest('.cust-tab');
  if(!tab) return;
  // 优先用 data-tab 属性触发 switchTab
  if(tab.getAttribute('data-tab')){
    switchTab(tab);
    return;
  }
  // 否则自动根据 class 切换同容器内的 panel
  var container = tab.closest('.cust-tabs');
  if(!container) return;
  var panels = container.parentElement.querySelectorAll('.tab-panel');
  var m = tab.classList.contains('inc')?'inc':'pay';
  panels.forEach(function(panel){panel.classList.remove('active');});
  var target = container.parentElement.querySelector('.tab-panel.tab-panel-'+m);
  if(target) target.classList.add('active');
});
"""


def rate_cls(rate: float) -> str:
    """达成率色阶：<30%红 / 30-50%橙 / 50-80%黄 / ≥80%绿"""
    if rate < 0.3:
        return "level-1"
    elif rate < 0.5:
        return "level-2"
    elif rate < 0.8:
        return "level-3"
    else:
        return "level-4"


def completion_html(rate: float, show_bar: bool = True) -> str:
    """生成完成度色块（带百分比数字 + 可选进度条背景）"""
    cls = rate_cls(rate)
    pct = rate * 100
    bar_w = min(pct, 100)
    bar_cls = " bar" if show_bar else ""
    return f'<span class="completion{bar_cls} {cls}" style="--bar-w:{bar_w:.0f}%"><span class="pct">{pct:.1f}%</span></span>'





def yoy_html(current: float, previous: float) -> str:
    """同比色块"""
    if previous == 0 or previous is None:
        return '<span class="yoy-neutral">—</span>'
    rate = (current - previous) / previous
    pct = rate * 100
    if rate >= 0:
        return f'<span class="yoy-up">+{pct:.1f}%</span>'
    else:
        return f'<span class="yoy-down">{pct:.1f}%</span>'


class BaseRenderer(ABC):
    page_id: str = ""
    nav_name: str = ""

    @abstractmethod
    def render(self, data) -> str:
        ...

    def wrap_page(self, content: str) -> str:
        return f'<div id="{self.page_id}" class="page">\n{content}\n</div>'

    def section(self, title: str, color: str = "sec-blue") -> str:
        return f'<div class="section-title {color}">{title}</div>'
