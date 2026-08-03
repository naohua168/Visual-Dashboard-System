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

from .utils import fmt_wan


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
  background:#1e293b;color:#ffffff;padding:0 16px;
  position:sticky;top:0;z-index:100;
  display:flex;flex-direction:column;
  box-shadow:0 1px 3px rgba(0,0,0,0.1);
}
.header-top{
  display:flex;align-items:center;justify-content:center;
  height:36px;border-bottom:1px solid rgba(255,255,255,0.08);
}
.header-title{
  font-size:18px;font-weight:800;letter-spacing:0.04em;
  margin:0;color:#fbbf24;text-align:center;
  text-shadow:0 1px 2px rgba(0,0,0,.3);
}
.header-bottom{
  display:flex;align-items:center;justify-content:space-between;
  height:36px;
}
.header-left{display:flex;align-items:center;gap:16px;}
.header-logo{display:none;}
.header h1{font-size:20px;font-weight:700;letter-spacing:0.02em;color:#f1f5f9;}
.header .fullscreen-btn{
  display:flex;align-items:center;gap:4px;padding:4px 10px;
  background:rgba(255,255,255,0.1);color:#e2e8f0;border:1px solid rgba(255,255,255,0.2);
  border-radius:4px;cursor:pointer;font-size:11px;font-weight:600;transition:all .2s;
}
.fullscreen-btn:hover{background:rgba(255,255,255,0.2);border-color:rgba(255,255,255,0.4);color:#fff;}

/* ═══════════════════─ 导航栏 ─══════════════════ */
.nav{
  display:flex;gap:0;align-items:stretch;justify-content:center;
  flex:1;
}
.nav a{
  padding:0 20px;color:#cbd5e1;text-decoration:none;
  font-size:13px;font-weight:600;display:flex;align-items:center;
  border-bottom:3px solid transparent;transition:all 0.2s;
  letter-spacing:0.02em;
}
.nav a:hover{color:#fbbf24;background:rgba(255,255,255,0.08);}
.nav a.active{color:#fbbf24;border-bottom-color:#fbbf24;background:transparent;}

/* ═══════════════════─ 页面容器 ─══════════════════ */
.page{display:none;padding:8px 10px;height:calc(100vh - 72px);overflow-y:auto;}
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
/* 销售年度达成 mini-rate (左右双列) - 卡片1 */

/* KPI 高级版 (销售页) - 3 卡信息密集 */

/* KPI 统一大卡 (销售页) - 单卡 3 区 */
.kpi-pro-unified{
  background:linear-gradient(135deg,#0a1628 0%,#1e3a5f 50%,#0a1628 100%);
  color:#fff;padding:22px 28px;border-radius:12px;margin-bottom:12px;
  box-shadow:0 6px 18px rgba(10,22,40,0.35);
  display:grid;grid-template-columns:1.1fr 1px 1fr 1px 1fr;gap:18px;align-items:stretch;
}
.kpi-pro-unified > div{justify-self:stretch;}
.kpi-pro-unified-tgt{display:flex;flex-direction:column;justify-content:center;gap:10px;}
.kpi-pro-unified-divider{background:rgba(255,255,255,0.15);width:1px;}
.kpi-pro-unified-label{
  font-size:13px;letter-spacing:0.04em;font-weight:600;
  color:#fbbf24;text-transform:uppercase;
}
.kpi-pro-unified-value{
  font-size:32px;font-weight:900;color:#fff;
  font-variant-numeric:tabular-nums;letter-spacing:0.01em;line-height:1.05;
  text-shadow:0 2px 12px rgba(251,191,36,0.25);
  display:flex;align-items:baseline;gap:4px;
}
.kpi-pro-unified-value .kpi-unit{font-size:14px;font-weight:600;color:#94a3b8;}
.kpi-pro-unified-spark{
  display:flex;align-items:center;gap:10px;
}
.kpi-pro-unified-spark svg{flex-shrink:0;}
.kpi-pro-unified-rate{font-size:13px;font-weight:700;color:#fbbf24;}
.kpi-pro-unified-extra{font-size:11px;color:#cbd5e1;margin-top:2px;line-height:1.4;}

.kpi-pro-unified-metric{
  display:flex;flex-direction:column;justify-content:center;gap:4px;
  padding:0 4px;
}
.kpi-pro-unified-metric-head{
  display:flex;align-items:center;justify-content:space-between;gap:8px;
  margin-bottom:2px;
}
.kpi-pro-unified-metric-label{
  font-size:13px;letter-spacing:0.04em;font-weight:600;
  color:#93c5fd;
}
.kpi-pro-unified-metric.kpi-pro-unified-pay .kpi-pro-unified-metric-label{color:#86efac;}
.kpi-pro-unified-metric-value{
  font-size:24px;font-weight:900;color:#fff;
  font-variant-numeric:tabular-nums;line-height:1.1;letter-spacing:0.01em;
  display:flex;align-items:baseline;gap:3px;
}
.kpi-pro-unified-metric-value .kpi-unit{font-size:11px;font-weight:600;color:#94a3b8;}
.kpi-pro-unified-metric svg{display:block;}
.kpi-pro-unified-metric-rate{font-size:12px;color:#cbd5e1;font-weight:500;}
.kpi-pro-unified-metric-top{
  display:grid;grid-template-columns:60px 1fr 56px;align-items:center;gap:6px;
  font-size:11px;
}
.kpi-pro-top-label{color:#94a3b8;font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:0.04em;}
.kpi-pro-top-name{color:#fff;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.kpi-pro-top-val{color:#fff;font-weight:700;font-variant-numeric:tabular-nums;text-align:right;}
.kpi-pro-top-extra{color:#cbd5e1;font-weight:500;}

@media(max-width:1100px){
  .kpi-pro-unified{grid-template-columns:1fr;gap:12px;}
  .kpi-pro-unified-divider{display:none;}
}

.kpi-pro-grid{
  display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:12px;
}
.kpi-pro{
  background:#fff;padding:14px 16px;border-radius:10px;
  border:1px solid var(--border);box-shadow:var(--shadow-sm);
  position:relative;overflow:hidden;
  transition:box-shadow .2s,transform .2s;
}
.kpi-pro:hover{box-shadow:var(--shadow-md);transform:translateY(-1px);}
.kpi-pro::before{
  content:"";position:absolute;top:0;left:0;right:0;height:3px;
  background:linear-gradient(90deg,var(--c1,#f59e0b),var(--c2,#fbbf24));
}
.kpi-pro-tgt{--c1:#f59e0b;--c2:#fb923c;}
.kpi-pro-inc{--c1:#3b82f6;--c2:#60a5fa;}
.kpi-pro-pay{--c1:#22c55e;--c2:#4ade80;}
.kpi-pro-header{
  display:flex;justify-content:space-between;align-items:center;
  margin-bottom:6px;
}
.kpi-pro-title{
  font-size:12px;font-weight:700;color:#64748b;letter-spacing:0.04em;
}
.kpi-pro-rate{display:flex;align-items:center;}
.kpi-pro-value-row{
  display:flex;align-items:center;justify-content:space-between;
  margin-bottom:6px;
}
.kpi-pro-value{
  font-size:30px;font-weight:900;color:#0f172a;
  font-variant-numeric:tabular-nums;letter-spacing:0.01em;line-height:1;
}
.kpi-pro-value .kpi-unit{font-size:13px;font-weight:600;color:#94a3b8;margin-left:4px;}
.kpi-pro-spark{
  display:flex;align-items:center;justify-content:space-between;
  margin-bottom:8px;gap:8px;
}
.kpi-pro-spark svg{flex-shrink:0;}
.kpi-pro-sub{font-size:12px;font-weight:600;}
.kpi-pro-dept{
  display:flex;flex-direction:column;gap:3px;margin-bottom:8px;
  padding:6px 0;border-top:1px dashed var(--border);border-bottom:1px dashed var(--border);
}
.kpi-dept-row{
  display:grid;grid-template-columns:34px 1fr 50px;align-items:center;gap:8px;
  font-size:11px;
}
.kpi-dept-name{color:#475569;font-weight:600;}
.kpi-dept-track{
  height:8px;background:#f1f5f9;border-radius:4px;overflow:hidden;
}
.kpi-dept-fill{height:100%;border-radius:4px;transition:width .5s ease;}
.kpi-dept-val{
  color:#0f172a;font-weight:700;font-variant-numeric:tabular-nums;
  text-align:right;font-size:11px;
}
.kpi-pro-top{
  display:flex;flex-direction:column;gap:4px;
}
.kpi-pro-top-row{
  display:grid;grid-template-columns:50px 1fr 80px;align-items:center;gap:8px;
  font-size:11px;
}
.kpi-pro-top-label{
  color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:0.04em;
  font-size:10px;
}
.kpi-pro-top-name{
  color:#0f172a;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}
.kpi-pro-top-val{
  color:#0f172a;font-weight:700;font-variant-numeric:tabular-nums;text-align:right;
}
.kpi-pro-top-extra{
  color:#475569;font-weight:500;
}
@media(max-width:1100px){
  .kpi-pro-grid{grid-template-columns:1fr;gap:10px;}
  .kpi-pro-value{font-size:24px;}
}

.sales-c1-grid{
  display:grid;grid-template-columns:1fr 1fr;gap:16px;
}
.sales-panel{
  background:#fff;padding:12px 14px;border-radius:8px;
  border:1px solid var(--border);box-shadow:var(--shadow-sm);
}
.sales-panel .card-title{
  font-size:14px;font-weight:700;color:#0f172a;margin-bottom:10px;
  padding-bottom:8px;border-bottom:2px solid var(--border);
}
.sales-panel .mini-rate{
  padding:6px 0;font-size:12px;
}
.sales-panel .mini-rate .bar{height:14px;}
.sales-panel.inc-panel{border-top:3px solid #f59e0b;}
.sales-panel.pay-panel{border-top:3px solid #16a34a;}
@media(max-width:860px){
  .sales-c1-grid{grid-template-columns:1fr;gap:10px;}
}

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
/* ann-matrix / yoy-matrix-table 表格内部滚动（表头吸顶 + 合计行吸底） */
.table-wrap:has(table.ann-matrix),
.table-wrap:has(table.yoy-matrix-table){overflow-y:auto;max-height:calc(100vh - 220px);}

/* yoy-matrix-table 表头吸顶 + 合计行吸底（两行表头不同 top 避免重叠） */
table.yoy-matrix-table thead tr:first-child th,
.yoy-matrix-table thead tr:first-child th{
  position:sticky;top:0;z-index:10;
  background:#0f172a !important;
}
table.yoy-matrix-table thead tr:last-child th,
.yoy-matrix-table thead tr:last-child th{
  position:sticky;top:50px;z-index:10;
  background:#0f172a !important;
}
table.yoy-matrix-table tbody .row-total td,
.yoy-matrix-table tbody .row-total td{
  position:sticky;bottom:0;z-index:5;
}
table{width:100%;border-collapse:collapse;font-size:13px;}
th,td{
  padding:6px 10px;text-align:right;
  border-bottom:1px solid #eef0f5;
  white-space:nowrap;font-variant-numeric:tabular-nums;
}
th{
  background:#1e293b;color:#ffffff;font-weight:800;font-size:19px !important;
  text-transform:none;letter-spacing:0.04em;text-align:center !important;
  position:sticky;top:0;z-index:5;border-bottom:3px solid #f59e0b;
  padding:14px 10px !important;line-height:1.3;text-shadow:0 1px 2px rgba(0,0,0,.2);
}
table.yoy-dept-table th{
  background:#0f172a;color:#fff;padding:14px 10px;text-align:center;
  font-weight:800;font-size:19px;letter-spacing:0.06em;border:1px solid #1e293b;
  border-bottom:3px solid #f59e0b;text-shadow:0 1px 2px rgba(0,0,0,.3);
}
table.yoy-matrix-table th{
  background:#0f172a;color:#fff;padding:14px 10px;text-align:center;
  font-weight:800;font-size:19px;letter-spacing:0.06em;border:1px solid #1e293b;
  border-bottom:3px solid #f59e0b;text-shadow:0 1px 2px rgba(0,0,0,.3);
}
/* 双层表头 — 事业部/合计大组 */
table.yoy-matrix-table th.th-dept-group{
  font-size:19px;padding:14px 8px;font-weight:900;background:#0f172a;
  border-bottom:1px solid #1e293b;letter-spacing:0.06em;
}
table.yoy-matrix-table th.th-dept-group.th-dept-total{
  background:linear-gradient(135deg,#1e3a5f 0%,#0f172a 100%);
  color:#fbbf24;
}
/* 双层表头 — 副表头 (金额/同比) */
table.yoy-matrix-table th.th-sub{
  font-size:13px;font-weight:700;color:#cbd5e1;padding:8px 6px;
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

/* ═══════════════════─ 同比大对比卡（2 卡，深色稳重风） ───────────── */
.yoy-big-card{
  position:relative;
  padding:20px 24px;
  border-radius:10px;
  background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%);
  color:#fff;
  display:grid;grid-template-columns:1fr 1.4fr;gap:24px;align-items:center;
  box-shadow:0 4px 16px rgba(15,23,42,0.25);
  overflow:hidden;
}
.yoy-big-card::before{
  content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--accent-color,#dc2626);
}
.yoy-big-card.up{--accent-color:#dc2626;}
.yoy-big-card.down{--accent-color:#16a34a;}
.yoy-big-card.flat{--accent-color:#64748b;}

/* 左侧：同比率 */
.yoy-big-info{display:flex;flex-direction:column;gap:8px;}
.yoy-big-label{
  font-size:13px;color:#94a3b8;font-weight:600;
  text-transform:uppercase;letter-spacing:0.08em;
}
.yoy-big-pct{
  font-size:52px;font-weight:900;line-height:1;
  font-variant-numeric:tabular-nums;letter-spacing:-0.02em;
  display:flex;align-items:baseline;gap:6px;
}
.yoy-big-pct .yoy-arrow{
  width:34px;height:34px;font-size:18px;
  background:rgba(255,255,255,0.08);border-radius:8px;
}
.yoy-big-pct .yoy-arrow.up{color:#dc2626;background:rgba(220,38,38,0.15);}
.yoy-big-pct .yoy-arrow.down{color:#16a34a;background:rgba(22,163,74,0.15);}
.yoy-big-pct .yoy-arrow.flat{color:#94a3b8;background:rgba(148,163,184,0.15);}
.yoy-big-pct-num{line-height:1;}

/* 右侧：对比柱状图 */
.yoy-big-compare{
  display:flex;flex-direction:column;gap:14px;
  padding-left:20px;border-left:1px solid rgba(255,255,255,0.12);
}
.yoy-cmp-item{display:flex;flex-direction:column;gap:6px;}
.yoy-cmp-header{display:flex;justify-content:space-between;align-items:baseline;}
.yoy-cmp-label{
  font-size:12px;font-weight:600;color:#94a3b8;
  letter-spacing:0.04em;
}
.yoy-cmp-val{
  font-size:18px;font-weight:700;color:#fff;
  font-variant-numeric:tabular-nums;
}
.yoy-cmp-val .yoy-cmp-unit{font-size:11px;font-weight:500;color:#64748b;margin-left:2px;}
/* 柱状条 */
.yoy-cmp-bar{
  height:8px;border-radius:4px;background:rgba(255,255,255,0.08);
  position:relative;overflow:hidden;
}
.yoy-cmp-fill{
  height:100%;border-radius:4px;
  transition:width 1s cubic-bezier(0.22,1,0.36,1);
}
.yoy-cmp-fill.cur.up{background:linear-gradient(90deg,#dc2626,#ef4444);box-shadow:0 0 12px rgba(220,38,38,0.4);}
.yoy-cmp-fill.cur.down{background:linear-gradient(90deg,#16a34a,#22c55e);box-shadow:0 0 12px rgba(22,163,74,0.4);}
.yoy-cmp-fill.cur.flat{background:linear-gradient(90deg,#94a3b8,#cbd5e1);}
.yoy-cmp-fill.prev{
  background:linear-gradient(90deg,#cbd5e1,#e2e8f0);
  opacity:0.85;
}

/* 响应式 */
@media(max-width:860px){
  .yoy-big-card{grid-template-columns:1fr;gap:16px;}
  .yoy-big-compare{padding-left:0;border-left:none;border-top:1px solid rgba(255,255,255,0.12);padding-top:16px;}
}

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


/* ═══════════════════─ 页面数据范围 banner ─══════════════════ */
.range-banner{
  background:linear-gradient(135deg,#1e40af 0%,#2563eb 100%);
  color:#fff;padding:8px 16px;border-radius:6px;margin-bottom:8px;
  font-size:13px;font-weight:600;letter-spacing:0.02em;
  box-shadow:0 2px 6px rgba(30,64,175,0.25);
}

/* ═══════════════════─ 季度客户达成表 (6列, 无目标) ─══════════════════ */
table.q2-cust-table{
  width:100%;border-collapse:collapse;font-size:14px;
  table-layout:fixed;background:#fff;
}
table.q2-cust-table th{
  background:#0f172a;color:#fff;padding:14px 10px;
  text-align:center;font-weight:800;font-size:22px;letter-spacing:0.04em;
  border:1px solid #1e293b;letter-spacing:0.04em;
}
table.q2-cust-table th:first-child{width:30%;}
table.q2-cust-table th:nth-child(2),
table.q2-cust-table th:nth-child(3),
table.q2-cust-table th:nth-child(4),
table.q2-cust-table th:nth-child(5){width:14%;}
table.q2-cust-table th:last-child{width:14%;background:#1e293b;}
table.q2-cust-table td{
  padding:10px 12px;border:1px solid #e2e8f0;
  text-align:center;font-variant-numeric:tabular-nums;
}
table.q2-cust-table td.td-name{
  text-align:left;font-weight:600;color:#0f172a;font-size:18px;
  padding-left:12px;background:#f8fafc;
}
table.q2-cust-table td.td-name .row-num{
  display:inline-flex;width:24px;height:24px;align-items:center;
  justify-content:center;font-size:13px;font-weight:800;color:#fff;
  background:#94a3b8;border-radius:4px;margin-right:8px;flex-shrink:0;
}
table.q2-cust-table td.num-cell{
  font-weight:700;font-size:24px;color:#0f172a;
  font-variant-numeric:tabular-nums;
}
table.q2-cust-table td.num-cell.total{
  font-weight:800;color:#0f172a;background:#fef3c7;
}
table.q2-cust-table tbody tr:nth-child(even){background:#f8fafc;}
table.q2-cust-table tbody tr:hover{background:#bfdbfe !important;box-shadow:inset 4px 0 0 0 #1e40af;}
table.q2-cust-table tr.row-total td{
  background:#e0e7ff;font-weight:800;font-size:14px;
  border-top:2px solid #1e40af!important;
  border-bottom:2px solid #1e40af!important;
}
table.q2-cust-table tr.row-total td.num-cell{
  font-weight:800;color:#1e40af;font-size:14px;
}
/* 合计行第一格（客户名列）加大字号 */
table.q2-cust-table tr.row-total td.td-name{
  font-size:15px;font-weight:800;letter-spacing:0.02em;
}

/* ═══════════════════─ 圆环 Hero ─══════════════════ */
.hero-rings{
  display:flex;align-items:center;justify-content:space-between;
  gap:12px;padding:22px 30px;margin-bottom:8px;border-radius:12px;
  background:linear-gradient(135deg,#0a1628 0%,#1e3a5f 50%,#0a1628 100%);
  color:#fff;box-shadow:0 6px 18px rgba(10,22,40,0.35);
  min-height:200px;flex-wrap:nowrap;
}
.hero-rings .hr-side{flex:1;min-width:200px;display:flex;flex-direction:column;gap:10px;}
.hero-rings .hr-side.inc-side{align-items:flex-start;text-align:left;}
.hero-rings .hr-side.pay-side{align-items:flex-end;text-align:right;}
.hero-rings .hr-side-title{
  font-size:14px;letter-spacing:0.04em;font-weight:600;
  opacity:0.9;display:flex;align-items:center;gap:6px;flex-wrap:wrap;
}
.hero-rings .hr-side.pay-side .hr-side-title{flex-direction:row-reverse;}
.hero-rings .hr-side-amount{
  font-size:54px;font-weight:900;color:#fbbf24;
  font-variant-numeric:tabular-nums;letter-spacing:0.01em;line-height:1;
  display:flex;align-items:baseline;gap:6px;
  text-shadow:0 2px 12px rgba(251,191,36,0.2);
}
.hero-rings .hr-side.pay-side .hr-side-amount{flex-direction:row;}
/* 总指标 — 琥珀色 */
.hero-rings .hr-side-amount.hr-side-target{color:#fbbf24;text-shadow:0 2px 14px rgba(251,191,36,0.3);}
.hero-rings .hr-side-unit{font-size:18px;font-weight:600;color:#94a3b8;letter-spacing:0;}
.hero-rings .hr-side-metrics{
  display:flex;flex-direction:column;gap:5px;
  padding-top:10px;border-top:1px dashed rgba(255,255,255,0.15);
  width:100%;
}
.hero-rings .hr-side.pay-side .hr-side-metrics{align-items:flex-end;}
.hero-rings .hr-metric{
  display:flex;align-items:center;gap:10px;font-size:14px;
  font-variant-numeric:tabular-nums;color:#cbd5e1;
}
.hero-rings .hr-side.pay-side .hr-metric{flex-direction:row-reverse;}
.hero-rings .hr-metric-label{opacity:0.75;min-width:60px;font-weight:500;}
.hero-rings .hr-metric-val{font-weight:700;color:#e0e7ff;font-size:15px;}
.hero-rings .hr-metric-gap .hr-metric-val{color:#fb923c;}
.hero-rings .hr-yoy{
  display:inline-block;font-size:12px;font-weight:700;
  padding:2px 9px;border-radius:9px;letter-spacing:0;
  margin-left:6px;
}
.hero-rings .hr-side.pay-side .hr-yoy{margin-left:0;margin-right:6px;}
.hero-rings .hr-yoy-up{background:rgba(220,38,38,0.2);color:#fca5a5;border:1px solid rgba(220,38,38,0.4);}
.hero-rings .hr-yoy-dn{background:rgba(34,197,94,0.18);color:#4ade80;border:1px solid rgba(34,197,94,0.35);}
.hero-rings .hr-yoy-period{font-size:11px;opacity:0.6;font-weight:500;margin-left:6px;letter-spacing:0;}
.hero-rings .hr-side.pay-side .hr-yoy-period{margin-left:0;margin-right:6px;}
.hero-rings .hr-ring{
  position:relative;width:96px;height:96px;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
}
.hero-rings .hr-ring svg{transform:rotate(-90deg);width:96px;height:96px;}
.hero-rings .hr-ring circle{fill:none;stroke-width:10;stroke-linecap:round;}
.hero-rings .hr-ring .hr-track{stroke:rgba(255,255,255,0.10);}
.hero-rings .hr-ring.inc-ring .hr-progress{stroke:#3b82f6;
  filter:drop-shadow(0 0 4px rgba(59,130,246,0.55));
  transition:stroke-dashoffset 1.1s cubic-bezier(0.22,1,0.36,1);}
.hero-rings .hr-ring.pay-ring .hr-progress{stroke:#22c55e;
  filter:drop-shadow(0 0 4px rgba(34,197,94,0.55));
  transition:stroke-dashoffset 1.1s cubic-bezier(0.22,1,0.36,1);}
.hero-rings .hr-ring .hr-center{
  position:absolute;inset:0;display:flex;flex-direction:column;
  align-items:center;justify-content:center;color:#fff;
  transform:rotate(0deg);pointer-events:none;
}
.hero-rings .hr-ring .hr-pct{font-size:18px;font-weight:800;font-variant-numeric:tabular-nums;line-height:1;}
.hero-rings .hr-ring.inc-ring .hr-pct{color:#93c5fd;}
.hero-rings .hr-ring.pay-ring .hr-pct{color:#86efac;}
.hero-rings .hr-ring .hr-label{font-size:10px;font-weight:600;opacity:0.7;letter-spacing:0.06em;margin-top:2px;text-transform:uppercase;}
.hero-rings .hr-center-box{
  flex:0 0 auto;display:flex;flex-direction:column;align-items:center;
  justify-content:center;padding:0 16px;
  border-left:1px dashed rgba(255,255,255,0.2);
  border-right:1px dashed rgba(255,255,255,0.2);
  min-width:260px;
}
/* 中间：总指标大数字（total_tgt 模式） */
.hero-rings .hr-center-label{
  display:flex;align-items:center;gap:6px;
  font-size:13px;font-weight:600;opacity:0.85;color:#fbbf24;letter-spacing:0.04em;
}
.hero-rings .hr-center-value{
  font-size:48px;font-weight:900;color:#fbbf24;font-variant-numeric:tabular-nums;
  letter-spacing:0.005em;line-height:1.1;text-shadow:0 2px 18px rgba(251,191,36,0.3);
  white-space:nowrap;
}
.hero-rings .hr-center-value .hr-center-unit{font-size:16px;font-weight:600;color:#94a3b8;}
.hero-rings .hr-center-split{display:flex;align-items:center;gap:16px;}
.hero-rings .hr-cs-col{display:flex;flex-direction:column;align-items:center;gap:6px;flex:1;}
.hero-rings .hr-cs-label{font-size:13px;font-weight:600;opacity:0.85;color:#fbbf24;letter-spacing:0.04em;}
.hero-rings .hr-cs-val{font-size:36px;font-weight:900;color:#fbbf24;font-variant-numeric:tabular-nums;letter-spacing:0.005em;line-height:1.1;text-shadow:0 2px 18px rgba(251,191,36,0.3);white-space:nowrap;}
.hero-rings .hr-cs-div{width:1px;height:50px;background:rgba(255,255,255,0.2);}
.hero-rings .hr-side-ring{
  flex:0 0 auto;display:flex;align-items:center;justify-content:center;
  padding:0 4px;cursor:default;
}
.hero-rings .hr-side-ring .hr-ring{width:130px;height:130px;}
.hero-rings .hr-side-ring .hr-ring svg{width:130px;height:130px;stroke-width:12;}
.hero-rings .hr-side-ring .hr-ring .hr-pct{font-size:26px;font-weight:900;letter-spacing:-0.02em;}
.hero-rings .hr-side-ring .hr-ring .hr-label{font-size:13px;font-weight:600;letter-spacing:0.04em;margin-top:4px;}
.hero-rings .hr-side-ring .hr-ring .hr-track{stroke-width:12;}
.hero-rings .hr-side-ring.inc-side-ring{padding-right:8px;}
.hero-rings .hr-side-ring.pay-side-ring{padding-left:8px;}
.hero-rings .hr-rings{display:flex;align-items:center;gap:14px;flex:0 0 auto;}
/* 中间 ring 组合（target/ring/actual 三件套） */
.hero-rings .hr-ring-group{display:flex;flex-direction:column;align-items:center;gap:10px;padding:0 8px;}
.hero-rings .hr-ring-target{font-size:24px;font-weight:900;color:#22d3ee;font-variant-numeric:tabular-nums;letter-spacing:-0.02em;text-shadow:0 2px 12px rgba(34,211,238,0.3);text-align:center;}
.hero-rings .hr-ring-target span{font-size:12px;font-weight:500;opacity:0.7;margin-left:2px;}
.hero-rings .hr-ring-amount{font-size:18px;font-weight:800;color:#fbbf24;font-variant-numeric:tabular-nums;letter-spacing:-0.02em;text-align:center;text-shadow:0 2px 10px rgba(251,191,36,0.3);}
.hero-rings .hr-ring-amount span{font-size:12px;font-weight:500;opacity:0.7;margin-left:2px;}
@media(max-width:1360px){
  .hero-rings{flex-wrap:wrap;gap:12px;}
  .hero-rings .hr-side{min-width:220px;}
  .hero-rings .hr-side-amount{font-size:42px;}
  .hero-rings .hr-side-unit{font-size:15px;}
  .hero-rings .hr-center-box{min-width:180px;}
  .hero-rings .hr-center-value{font-size:54px;}
  .hero-rings .hr-center-unit{font-size:16px;}
  .hero-rings .hr-side-ring .hr-ring{width:100px;height:100px;}
  .hero-rings .hr-side-ring .hr-ring svg{width:100px;height:100px;}
}
@media(max-width:860px){
  .hero-rings .hr-side{flex:0 0 100%;text-align:left !important;align-items:flex-start !important;}
  .hero-rings .hr-side.pay-side{text-align:left !important;align-items:flex-start !important;}
  .hero-rings .hr-side.pay-side .hr-side-title{flex-direction:row;}
  .hero-rings .hr-side.pay-side .hr-side-amount{flex-direction:row;}
  .hero-rings .hr-side.pay-side .hr-side-metrics{align-items:flex-start;}
  .hero-rings .hr-side.pay-side .hr-metric{flex-direction:row;}
  .hero-rings .hr-side.pay-side .hr-yoy{margin-left:6px;margin-right:0;}
  .hero-rings .hr-side.pay-side .hr-yoy-period{margin-left:6px;margin-right:0;}
  .hero-rings .hr-side-amount{font-size:36px;}
  .hero-rings .hr-center-box{flex:0 0 100%;order:2;border-top:1px dashed rgba(255,255,255,0.2);border-bottom:1px dashed rgba(255,255,255,0.2);border-left:none;border-right:none;padding:14px 0 10px;min-width:0;gap:8px;}
  .hero-rings .hr-center-value{font-size:46px;}
  .hero-rings .hr-center-unit{font-size:14px;}
  .hero-rings .hr-side-ring{flex:1 1 100%;justify-content:center;padding:6px 0;}
  .hero-rings .hr-side-ring.inc-side-ring{order:1;}
  .hero-rings .hr-side-ring.pay-side-ring{order:3;}
  .hero-rings .hr-side-ring .hr-ring{width:80px;height:80px;}
  .hero-rings .hr-side-ring .hr-ring svg{width:80px;height:80px;}
}

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
  width:100%;border-collapse:separate;border-spacing:0;font-size:24px;background:#fff;
  border:1px solid #e2e5ed;
}
table.ann-matrix th, table.ann-matrix td,
.ann-matrix th, .ann-matrix td{
  padding:12px 20px;text-align:right;
  border:1px solid #e2e5ed;vertical-align:middle;
  line-height:1.3;
}
table.ann-matrix thead th,
.ann-matrix thead th{
  background:#0f172a;color:#ffffff;font-weight:900;font-size:26px !important;
  letter-spacing:0.06em;text-transform:none;
  position:sticky;top:0;z-index:10;
  text-align:center !important;
  border-color:#1e293b;padding:14px 10px !important;
  line-height:1.3;text-shadow:0 2px 4px rgba(0,0,0,.4);
  border-bottom:2px solid #fbbf24;
}
/* 合计行吸底（仅定位，样式沿用已有 .row-total 规则） */
table.ann-matrix tbody .row-total td,
.ann-matrix tbody .row-total td{
  position:sticky;bottom:0;z-index:5;
}
/* 2行分组头部 — 收入组/回款组（统一 19px 配合主表头） */
table.ann-matrix thead tr.group-row th,
.ann-matrix thead tr.group-row th{
  font-size:19px;font-weight:800;
  padding:14px 8px;
  letter-spacing:0.12em;
  border-bottom-width:2px;
}
table.ann-matrix thead tr.group-row th.dept-name,
.ann-matrix thead tr.group-row th.dept-name{background:#1e3a5f;}
table.ann-matrix thead tr.group-row th.inc-group,
.ann-matrix thead tr.group-row th.inc-group{background:#c2410c;}
table.ann-matrix thead tr.group-row th.pay-group,
.ann-matrix thead tr.group-row th.pay-group{background:#047857;}
/* detail-row（子表头） */
table.ann-matrix thead tr.detail-row th,
.ann-matrix thead tr.detail-row th{
  font-size:13px;font-weight:700;
  padding:10px 8px;
  background:#1e293b;
}
table.ann-matrix .th-name, .ann-matrix .th-name{text-align:center;min-width:160px;font-weight:800;}
/* 客户名列 */
table.ann-matrix .td-name, .ann-matrix .td-name{
  text-align:left;font-weight:600;color:#0f172a;font-size:18px;white-space:nowrap;
}
table.ann-matrix .td-name .row-num, .ann-matrix .td-name .row-num{
  display:inline-flex;width:28px;height:28px;align-items:center;justify-content:center;
  font-size:16px;font-weight:800;color:#fff;background:#94a3b8;
  border-radius:4px;margin-right:8px;flex-shrink:0;
}
/* 行高亮 —— 深色背景 + 左侧高亮条（Excel 选中效果）*/
table.ann-matrix tbody tr:hover td, .ann-matrix tbody tr:hover td{
  background:#bfdbfe !important;
  box-shadow:inset 4px 0 0 0 #1e40af;
}
/* nth-child 偶数行的 hover 也要覆盖 */
table.ann-matrix tbody tr.row-data:nth-child(even):hover td{
  background:#bfdbfe !important;
}
/* 悬停加深（仅普通格）—— fill-bg 也跟着加深 */
table.ann-matrix tbody tr.row-data:hover td.cell-bg:not(.is-total) .fill-bg{ filter:brightness(0.85) saturate(1.15); }
table.ann-matrix tbody tr:nth-child(even) td, .ann-matrix tbody tr:nth-child(even) td{
  background:#fafbfc;
}
/* 合计行 — 边框统一 2px */
table.ann-matrix tr.row-total td,
.ann-matrix tr.row-total td{
  border-top:2px solid #1e40af!important;
  border-bottom:2px solid #1e40af!important;
}
table.ann-matrix tr.row-total td.cell-bg.is-total,
.ann-matrix tr.row-total td.cell-bg.is-total{
  border-top:2px solid #1e40af!important;
  border-bottom:2px solid #1e40af!important;
  border-left:1px solid #cbd5e1!important;
  border-right:1px solid #cbd5e1!important;
}
table.ann-matrix tr.row-total td:not(.cell-bg),
.ann-matrix tr.row-total td:not(.cell-bg){
  background:#dbeafe;font-weight:700;color:#1e3a8a;font-size:14px;
  border:1px solid #cbd5e1!important;
  border-top:2px solid #1e40af!important;
  border-bottom:2px solid #1e40af!important;
}
/* 合计行第一格（客户名列）加大字号 */
table.ann-matrix .row-total td.td-name,
.ann-matrix .row-total td.td-name{
  font-size:15px;font-weight:800;letter-spacing:0.02em;
}
table.ann-matrix .td-total, .ann-matrix .td-total{font-weight:700;}
/* 单元格主次层次（紧凑） */
.cell-main{font-size:13px;font-weight:700;color:#0f172a;line-height:1.2;}
.cell-sub{font-size:10px;color:var(--text-muted);margin-top:1px;line-height:1.2;}
/* ══════════ 格子背景填充（按完成度宽度+左右布局）══════════ */
td.cell-bg{
  position:relative; padding:7px 8px; overflow:hidden;
  border:1px solid #cbd5e1;
  background:#f8fafc;
  vertical-align:middle;
}
/* 表格整体网格 */
table.ann-matrix{border-collapse:collapse;border:1px solid #cbd5e1;}
table.ann-matrix thead th{border:1px solid #1e293b;}
table.ann-matrix td{border:1px solid #cbd5e1;}
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
  font-size:20px;line-height:1; font-weight:800;letter-spacing:-0.5px;
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
  font-size:18px;line-height:1.2;font-weight:700;color:#0f172a;
  text-align:right; flex:1; min-width:0;
}
td.cell-bg .cell-text .cell-main .cell-act{color:#0f172a;font-weight:800;}
td.cell-bg .cell-text .cell-main .cell-tgt{color:#64748b;font-size:16px;margin-top:1px;font-weight:500;}
td.cell-bg .cell-text .cell-pct.up{color:#dc2626;}
td.cell-bg .cell-text .cell-pct.down{color:#16a34a;}
td.cell-bg .cell-text .cell-pct.achieved{color:#16a34a;}
td.cell-bg .cell-text .cell-pct.low{color:#b45309;}
/* 0% 不显示填充（浅灰底） */
td.cell-bg.is-empty .fill-bg{display:none;}
/* 合计列：实色背景+白字（强制优先级超过所有 hover） */
td.cell-bg.is-total{
  background:transparent!important;
  border-left:1px solid #cbd5e1!important;
  border-right:1px solid #cbd5e1!important;
  border-top:1px solid #cbd5e1!important;
  border-bottom:1px solid #cbd5e1!important;
}
/* 只有当 is-total 不在 row-total 内时才用 2px 顶/底 */
table.ann-matrix tbody tr:not(.row-total) td.cell-bg.is-total,
.ann-matrix tbody tr:not(.row-total) td.cell-bg.is-total{
  border-top:2px solid #1e40af!important;
  border-bottom:2px solid #1e40af!important;
}
td.cell-bg.is-total .cell-text{color:#0f172a!important;text-shadow:none!important;}
td.cell-bg.is-total .cell-text .cell-main{color:#0f172a!important;font-size:13.5px!important;}
td.cell-bg.is-total .cell-text .cell-pct{color:#0f172a!important;font-size:19px!important;text-shadow:none!important;}
/* hover 时合计列保持深色文字 */
table.ann-matrix tbody tr:hover td.cell-bg.is-total,
table.ann-matrix tbody tr:hover td.cell-bg.is-total .cell-text,
table.ann-matrix tbody tr:hover td.cell-bg.is-total .cell-text *,
table.ann-matrix tbody tr:hover td.cell-bg.is-total .cell-text .cell-main,
table.ann-matrix tbody tr:hover td.cell-bg.is-total .cell-text .cell-pct{
  color:#0f172a!important;
  background:transparent!important;
  text-shadow:none!important;
}
/* 悬停加深（仅普通格） */
/* 空单元格 */
table.ann-matrix .td-empty, .ann-matrix .td-empty{
  text-align:center;color:#94a3b8;font-size:14px;padding:8px 0;
}

/* ══════════ 事业部同比专用表（双维度清晰对比）══════════ */
table.yoy-dept-table{width:100%;border-collapse:collapse;font-size:13px;}

table.yoy-dept-table th.group-header{
  font-size:19px;padding:14px 4px;letter-spacing:0.12em;
}
table.yoy-dept-table th.inc-group{background:#c2410c;}
table.yoy-dept-table th.pay-group{background:#047857;}
table.yoy-dept-table td{padding:9px 10px;border:1px solid #e2e8f0;text-align:center;}
table.yoy-dept-table tbody tr:nth-child(even){background:#f8fafc;}
table.yoy-dept-table tbody tr:hover{background:#bfdbfe !important;box-shadow:inset 4px 0 0 0 #1e40af;}
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
table.yoy-matrix-table{width:100%;border-collapse:separate;border-spacing:0;font-size:12.5px;}
/* yoy-matrix 表格 — 行底分隔 + hover 高亮覆盖所有单元格 */
table.yoy-matrix-table td{padding:7px 6px;border:1px solid #e2e8f0;text-align:center;vertical-align:middle;border-bottom:2px solid #e2e8f0;}
table.yoy-matrix-table tbody tr{border-bottom:2px solid #cbd5e1;}
table.yoy-matrix-table tbody tr:nth-child(even){background:#f8fafc;}
/* 行 hover — 覆盖所有单元格（包括 mx-yoy-cell），4px 深蓝左侧高亮 */
table.yoy-matrix-table tbody tr:hover td,
table.yoy-matrix-table tbody tr:hover{background:#bfdbfe !important;box-shadow:inset 4px 0 0 0 #1e40af;}
/* hover 时不要让 mx-yoy-cell 的胶囊按钮背景被改 */
table.yoy-matrix-table tbody tr:hover td.mx-yoy-cell{background:transparent!important;}
table.yoy-matrix-table tbody tr:hover td.mx-yoy-cell .mx-badge{box-shadow:0 2px 8px rgba(0,0,0,0.25);}
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
/* 合计行 — 灰色外框框起 */
table.yoy-matrix-table tr.row-total{background:linear-gradient(90deg,#eff6ff,#f0fdf4)!important;}
table.yoy-matrix-table tr.row-total td{font-weight:700;font-size:14px;}
table.yoy-matrix-table tr.row-total td:not(.yoy-cell):not(.mx-amount-pair){
  border:1px solid #cbd5e1;
  border-top:2px solid #1e40af!important;
  border-bottom:2px solid #1e40af!important;
}

/* ═══════════════════─ 重设计的金额/同比单元格（直观卡片化） ───────── */
table.yoy-matrix-table td.mx-amount-cell{
  padding:8px 10px;min-width:100px;text-align:left;
  border:1px solid #cbd5e1;vertical-align:middle;
}
table.yoy-matrix-table td.mx-amount-cell .mx-amount-pair{
  display:flex;flex-direction:column;gap:4px;
}
table.yoy-matrix-table td.mx-amount-cell .mx-amt-row{
  display:flex;justify-content:space-between;align-items:baseline;gap:12px;
  font-size:24px;font-variant-numeric:tabular-nums;
}
table.yoy-matrix-table td.mx-amount-cell .mx-cur-row{
  font-weight:900;color:#0f172a;font-size:26px;
}
table.yoy-matrix-table td.mx-amount-cell .mx-prev-row{
  font-weight:600;color:#64748b;font-size:22px;
}
table.yoy-matrix-table td.mx-amount-cell .mx-amt-label{
  font-size:12px;color:#64748b;font-weight:500;
}
table.yoy-matrix-table td.mx-amount-cell .mx-cur-row .mx-amt-label{color:#2563eb;}

/* 同比单元格 — 胶囊按钮样式（红涨绿跌）
   注意：不设 background，让父级行 hover 高亮能透过来 */
table.yoy-matrix-table td.mx-yoy-cell{
  padding:8px 6px;border:1px solid #cbd5e1;vertical-align:middle;
  background:transparent;
}
table.yoy-matrix-table td.mx-yoy-cell .mx-badge{
  display:inline-flex;align-items:center;gap:6px;
  padding:8px 16px;border-radius:8px;
  font-size:18px;font-weight:800;letter-spacing:-0.3px;
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
  font-size:14px;font-weight:900;
}

/* 合计行第一格（客户名列）加大字号 */
table.yoy-matrix-table tr.row-total td.td-name{font-size:15px;font-weight:800;letter-spacing:0.02em;}
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

GLOBAL_OV_CSS = """
/* ═══════════════════════════════════════════════════════════════
   数据总览页 — 毛玻璃卡片 + 飞入动画
   ═══════════════════════════════════════════════════════════════ */

/* Overview 页背景：CAERI 图 + 深色渐变遮罩 */
.page#overview{
  background:linear-gradient(135deg,#0a1628 0%,#162944 100%);
  padding:14px;
  position:relative;
  display:flex;flex-direction:column;
  overflow-y:auto;
  min-height:calc(100vh - 72px);
}
.page#overview > *{position:relative;z-index:1;}

/* ov-container 填满 */
.page#overview .ov-container{flex:1;display:flex;flex-direction:column;gap:14px;}

/* 飞入动画 */
@keyframes flyInLeft{0%{opacity:0;transform:translateX(-60px);}100%{opacity:1;transform:translateX(0);}}
@keyframes flyInRight{0%{opacity:0;transform:translateX(60px);}100%{opacity:1;transform:translateX(0);}}
@keyframes flyInUp{0%{opacity:0;transform:translateY(30px);}100%{opacity:1;transform:translateY(0);}}

.ov-cards{display:grid;grid-template-columns:1fr 1fr;gap:18px;flex:1;min-height:0;}
.ov-card{
  background:linear-gradient(135deg,rgba(255,255,255,0.12) 0%,rgba(255,255,255,0.05) 100%);
  backdrop-filter:blur(28px) saturate(150%);
  -webkit-backdrop-filter:blur(28px) saturate(150%);
  border:1px solid rgba(255,255,255,0.22);
  border-radius:18px;
  padding:20px 22px;
  box-shadow:0 8px 36px rgba(0,0,0,0.3),inset 0 1px 0 rgba(255,255,255,0.12);
  color:#ffffff;
  display:flex;flex-direction:column;gap:14px;
  min-height:100%;
}
.ov-card.ov-card-left{animation:flyInLeft 0.7s cubic-bezier(.2,.8,.3,1) both;}
.ov-card.ov-card-right{animation:flyInRight 0.7s cubic-bezier(.2,.8,.3,1) both;}

/* 卡片头部：标题 + YoY */
.ov-card-head{display:flex;align-items:center;justify-content:space-between;gap:12px;}
.ov-card-title{display:flex;align-items:center;gap:8px;font-size:18px;font-weight:800;color:#fbbf24;letter-spacing:0.04em;}
.ov-card-title svg{opacity:0.85;}
.ov-yoy-period{font-size:11px;color:rgba(255,255,255,0.6);font-weight:500;margin-left:8px;}

/* 关键数字区（4列） */
.ov-keynums{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:10px 12px;}
.ov-kn{display:flex;flex-direction:column;gap:3px;}
.ov-kn-label{font-size:11px;color:rgba(255,255,255,0.65);font-weight:500;}
.ov-kn-val{font-size:18px;font-weight:800;color:#fbbf24;letter-spacing:-0.01em;font-variant-numeric:tabular-nums;}
.ov-kn-val.is-gap{color:#fb923c;}
.ov-kn-val.is-yoy-up{color:#86efac;}
.ov-kn-val.is-yoy-dn{color:#fca5a5;}

/* 卡片头部 */
.ov-card-period{font-size:11px;color:rgba(255,255,255,0.5);font-weight:500;}

/* 4 部门 mini-card 网格（4 列） */
.ov-dept-cards{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;}
.ov-dc{
  background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);
  border-radius:10px;padding:10px 8px;display:flex;flex-direction:column;gap:6px;align-items:center;
  transition:background 0.2s;
}
.ov-dc:hover{background:rgba(255,255,255,0.12);}
.ov-dc-name{font-size:12px;font-weight:700;text-align:center;}
.ov-dc-val{font-size:18px;font-weight:800;color:#fbbf24;font-variant-numeric:tabular-nums;text-align:center;letter-spacing:-0.01em;}
.ov-dc-val span{font-size:11px;font-weight:500;opacity:0.7;margin-left:2px;}
.ov-dc-bar{height:6px;width:100%;background:rgba(255,255,255,0.1);border-radius:3px;overflow:hidden;}
.ov-dc-bar-fill{height:100%;background:linear-gradient(90deg,#3b82f6,#22c55e);border-radius:3px;transition:width 0.6s ease;}
.ov-dc-pct{font-size:13px;font-weight:700;color:#86efac;font-variant-numeric:tabular-nums;}

/* 大圆环 — 居中，撑满剩余空间 */
.ov-big-ring{position:relative;width:130px;height:130px;flex-shrink:0;margin:0 auto;}
.ov-big-ring svg{width:100%;height:100%;transform:rotate(-90deg);}
.ov-big-ring .ring-track{fill:none;stroke:rgba(255,255,255,0.15);stroke-width:10;}
.ov-big-ring .ring-prog{fill:none;stroke-width:10;stroke-linecap:round;transition:stroke-dasharray 1s ease;}
.ov-big-ring-text{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;}
.ov-big-ring-pct{font-size:26px;font-weight:900;color:#fbbf24;font-variant-numeric:tabular-nums;line-height:1;}
.ov-big-ring-label{font-size:10px;color:rgba(255,255,255,0.7);font-weight:600;margin-top:2px;}

/* 移除旧 3 列布局 */
.ov-card-middle,.ov-cm-depts-left,.ov-cm-depts-right,.ov-cm-ring-center,
.ov-cm-mini,.ov-card-subtitle,.ov-depts,.ov-dept,.ov-dept-name,
.ov-dept-bar,.ov-dept-bar-fill,.ov-dept-amount,.ov-dept-pct,
.ov-ring-center-wrap{display:none !important;}

/* 销售排行 Top 5 */
.ov-rank{display:flex;flex-direction:column;gap:6px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:8px 10px;}
.ov-rank-title{font-size:12px;color:rgba(255,255,255,0.7);font-weight:700;margin-bottom:4px;}
.ov-rank-row{display:grid;grid-template-columns:24px 1fr 70px 40px;align-items:center;gap:8px;font-size:12px;}
.ov-rank-num{display:inline-flex;width:20px;height:20px;align-items:center;justify-content:center;border-radius:4px;font-size:10px;font-weight:800;color:#fff;background:#94a3b8;}
.ov-rank-num.t1{background:#fbbf24;color:#0f172a;}
.ov-rank-num.t2{background:#94a3b8;}
.ov-rank-num.t3{background:#a16207;}
.ov-rank-name{color:#e0e7ff;font-weight:600;}
.ov-rank-bar{height:6px;background:rgba(255,255,255,0.1);border-radius:3px;overflow:hidden;}
.ov-rank-bar-fill{height:100%;background:linear-gradient(90deg,#fbbf24,#f59e0b);border-radius:3px;transition:width 0.6s ease;}
.ov-rank-amt{color:#fbbf24;font-weight:700;text-align:right;font-variant-numeric:tabular-nums;}

/* 区块标题 */
.ov-section-title{font-size:12px;color:rgba(255,255,255,0.7);font-weight:700;letter-spacing:0.04em;margin-bottom:6px;text-align:center;}

/* 数据总览：KPI 概览（顶部摘要） */
.ov-kpi-bar{
  display:grid;grid-template-columns:repeat(6,1fr);gap:10px;
  background:rgba(255,255,255,0.06);backdrop-filter:blur(16px);
  border:1px solid rgba(255,255,255,0.15);border-radius:12px;
  padding:12px 16px;animation:flyInUp 0.6s cubic-bezier(.2,.8,.3,1) both;
}
.ov-kpi{display:flex;flex-direction:column;gap:3px;}
.ov-kpi-label{font-size:11px;color:rgba(255,255,255,0.7);font-weight:500;}
.ov-kpi-val{font-size:20px;font-weight:800;color:#fbbf24;font-variant-numeric:tabular-nums;}

/* 移动端适配 */
@media (max-width:1180px){
  .ov-cards{grid-template-columns:1fr;}
  .ov-kpi-bar{grid-template-columns:repeat(3,1fr);}
  .ov-keynums{grid-template-columns:repeat(2,1fr);}
}
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






def ring_svg_html(rate: float, ring_kind: str = "inc", size: int = 96, label: str = "") -> str:
    """SVG 圆环图（完成进度），ring_kind: inc/pay"""
    pct = max(0.0, rate * 100)
    r = (size - 14) / 2
    cx = cy = size / 2
    circ = 2 * 3.141592653589793 * r
    dash = (min(pct, 100) / 100.0) * circ
    return (
        f'<div class="hr-ring {ring_kind}-ring">'
        f'<svg viewBox="0 0 {size} {size}">'
        f'<circle class="hr-track" cx="{cx}" cy="{cy}" r="{r:.2f}"/>'
        f'<circle class="hr-progress" cx="{cx}" cy="{cy}" r="{r:.2f}" '
        f'stroke-dasharray="{dash:.2f} {circ:.2f}" stroke-dashoffset="0"/>'
        f'</svg>'
        f'<div class="hr-center">'
        f'<div class="hr-pct">{pct:.1f}%</div>'
        f'<div class="hr-label">{label}</div>'
        f'</div>'
        f'</div>'
    )


def hero_rings_html(inc_act: float, inc_tgt: float, pay_act: float, pay_tgt: float,
                    toggle_js: str = "", header_left: str = "收入", header_right: str = "回款",
                    inc_yoy: float | None = None, pay_yoy: float | None = None,
                    inc_cust: int = 0, pay_cust: int = 0,
                    inc_sales: int = 0, pay_sales: int = 0,
                    yoy_period: str = "", total_tgt: float | None = None,
                    total_label: str = "总指标", show_cust_sales: bool = True) -> str:
    """5列 Hero 布局（信息丰富版）"""
    inc_r = inc_act / inc_tgt if inc_tgt else 0
    pay_r = pay_act / pay_tgt if pay_tgt else 0
    inc_gap = inc_tgt - inc_act
    pay_gap = pay_tgt - pay_act
    onclick = f' onclick="{toggle_js}"' if toggle_js else ""
    cursor = ' style="cursor:pointer"' if toggle_js else ""

    def _yoy_badge(yoy: float | None) -> str:
        if yoy is None:
            return ""
        if yoy >= 0:
            return f'<span class="hr-yoy hr-yoy-up">&#9650; {yoy*100:.1f}%</span>'
        return f'<span class="hr-yoy hr-yoy-dn">&#9660; {abs(yoy)*100:.1f}%</span>'

    def _metric_row(label: str, value: str, cls: str = "") -> str:
        return f'<div class="hr-metric {cls}"><span class="hr-metric-label">{label}</span><span class="hr-metric-val">{value}</span></div>'

    yoy_note = f'<span class="hr-yoy-period">{yoy_period}</span>' if yoy_period else ""

    chart_icon = (
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" '
        'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" '
        'style="vertical-align:-3px;margin-right:4px">'
        '<line x1="12" y1="20" x2="12" y2="10"/>'
        '<line x1="18" y1="20" x2="18" y2="4"/>'
        '<line x1="6" y1="20" x2="6" y2="16"/>'
        '</svg>'
    )

    # 客户/销售行（可选）
    cust_inc = f'{_metric_row("客户/销售", f"{inc_cust} 家 / {inc_sales} 人")}' if show_cust_sales else ""
    cust_pay = f'{_metric_row("客户/销售", f"{pay_cust} 家 / {pay_sales} 人")}' if show_cust_sales else ""

    # 中间区：total_tgt 传入 → 中间显示"XX总指标"大数字；否则 → 收入实际|回款实际
    if total_tgt is not None:
        center = (
            f'<div class="hr-center-box">'
            f'<div class="hr-center-label">{chart_icon}{total_label}</div>'
            f'<div class="hr-center-value">{fmt_wan(total_tgt)}<span class="hr-center-unit">万元</span></div>'
            f'</div>'
        )
    else:
        center = (
            f'<div class="hr-center-box">'
            f'<div class="hr-center-split">'
            f'<div class="hr-cs-col"><div class="hr-cs-label">收入实际</div><div class="hr-cs-val">{fmt_wan(inc_act)} 万</div></div>'
            f'<div class="hr-cs-div"></div>'
            f'<div class="hr-cs-col"><div class="hr-cs-label">回款实际</div><div class="hr-cs-val">{fmt_wan(pay_act)} 万</div></div>'
            f'</div>'
            f'</div>'
        )
    # 两侧各一环，中间为上面选择的 center 块
    side_rings = (
        f'<div class="hr-side-ring inc-side-ring">{ring_svg_html(inc_r, "inc", 130, header_left)}</div>'
        f'{center}'
        f'<div class="hr-side-ring pay-side-ring">{ring_svg_html(pay_r, "pay", 130, header_right)}</div>'
    )

    return (
        f'<div class="hero-rings"{onclick}{cursor}>'
        f'<div class="hr-side inc-side">'
        f'<div class="hr-side-title"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg> {header_left}指标 {_yoy_badge(inc_yoy)} {yoy_note}</div>'
        f'<div class="hr-side-amount hr-side-target">{fmt_wan(inc_tgt)}<span class="hr-side-unit">万元</span></div>'
        f'<div class="hr-side-metrics">'
        f'{_metric_row("还差", fmt_wan(inc_gap) + " 万", "hr-metric-gap")}'
        f'{cust_inc}'
        f'</div>'
        f'</div>'
        f'{side_rings}'
        f'<div class="hr-side pay-side">'
        f'<div class="hr-side-title"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg> {header_right}指标 {_yoy_badge(pay_yoy)} {yoy_note}</div>'
        f'<div class="hr-side-amount hr-side-target">{fmt_wan(pay_tgt)}<span class="hr-side-unit">万元</span></div>'
        f'<div class="hr-side-metrics">'
        f'{_metric_row("还差", fmt_wan(pay_gap) + " 万", "hr-metric-gap")}'
        f'{cust_pay}'
        f'</div>'
        f'</div>'
        f'</div>'
    )


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

    def wrap_page(self, content: str, date_range: str = "") -> str:
        attr = f' data-range="{date_range}"' if date_range else ""
        return f'<div id="{self.page_id}" class="page"{attr}>\n{content}\n</div>'

    def section(self, title: str, color: str = "sec-blue") -> str:
        return f'<div class="section-title {color}">{title}</div>'
