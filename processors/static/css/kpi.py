# Author: naohua168 <bai_bai168@qq.com>
"""KPI 指标卡（含销售页信息密集大卡） —— CSS 片段 `kpi`

由 processors/static/css_vars.py 拆分而来，内容与拆分前逐字节一致；
拼接顺序见 processors/static/css/__init__.py，改动内容请只在本文件里追加。
"""

CSS = r"""
/* ═══════════════════─ KPI 指标卡 ─══════════════════ */
.kpi-grid{display:grid;gap:0.25rem;margin-bottom:0.375rem;}
.kpi-grid.cols-9{grid-template-columns:repeat(9,1fr);}
.kpi-grid.cols-8{grid-template-columns:repeat(8,1fr);}
.kpi-grid.cols-6{grid-template-columns:repeat(6,1fr);}
.kpi-grid.cols-4{grid-template-columns:repeat(4,1fr);}
.kpi-grid.cols-3{grid-template-columns:repeat(3,1fr);}
.kpi{
  padding:0.75rem 0.875rem;border-radius:0.625rem;
  box-shadow:var(--shadow-sm);position:relative;overflow:hidden;
  transition:box-shadow 0.2s,transform 0.2s;
}
.kpi:hover{
  box-shadow:var(--shadow-md);transform:translateY(-1px);
}
.kpi-label{
  font-size:0.6875rem;margin-bottom:0.25rem;font-weight:600;
  text-transform:uppercase;letter-spacing:0.06em;position:relative;z-index:1;
}
.kpi-value{
  font-size:2.125rem;font-weight:800;font-variant-numeric:tabular-nums;line-height:1.15;position:relative;z-index:1;
}
.kpi-unit{font-size:0.8125rem;font-weight:500;margin-left:0.1875rem;position:relative;z-index:1;}
.kpi-sub{font-size:0.75rem;margin-top:0.1875rem;position:relative;z-index:1;}
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
.kpi.kpi-highlight{background:#f0f7ff;border:0.125rem solid #2563eb;}
.kpi.kpi-highlight .kpi-value{color:#1d4ed8;}

/* KPI 行布局（季度分析页专用） */
.kpi-row{
  display:grid;grid-template-columns:repeat(4,1fr);gap:0.75rem;margin-bottom:0.25rem;
}
.kpi-card{
  padding:0.875rem 1rem;border-radius:0.625rem;
  background:#fff;border:1px solid var(--border);
  box-shadow:var(--shadow-sm);transition:box-shadow 0.2s,transform 0.2s;
}
.kpi-card:hover{box-shadow:var(--shadow-md);transform:translateY(-1px);}
.kpi-card .kpi-label{font-size:0.6875rem;color:#64748b;font-weight:600;margin-bottom:0.25rem;}
.kpi-card .kpi-value{font-size:1.5rem;font-weight:800;color:#1e293b;line-height:1.2;}
.kpi-card .kpi-sub{font-size:0.6875rem;color:#94a3b8;margin-top:0.125rem;}

/* 状态徽章 */
.rate-badge{
  display:inline-block;padding:1px 0.5rem;border-radius:0.625rem;
  font-size:0.6875rem;font-weight:600;white-space:nowrap;
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
  color:#fff;padding:1.375rem 1.75rem;border-radius:0.75rem;margin-bottom:0.75rem;
  box-shadow:0 6px 18px rgba(10,22,40,0.35);
  display:grid;grid-template-columns:1.1fr 1px 1fr 1px 1fr;gap:1.125rem;align-items:stretch;
}
.kpi-pro-unified > div{justify-self:stretch;}
.kpi-pro-unified-tgt{display:flex;flex-direction:column;justify-content:center;gap:0.625rem;}
.kpi-pro-unified-divider{background:rgba(255,255,255,0.15);width:1px;}
.kpi-pro-unified-label{
  font-size:0.8125rem;letter-spacing:0.04em;font-weight:600;
  color:#fbbf24;text-transform:uppercase;
}
.kpi-pro-unified-value{
  font-size:2rem;font-weight:900;color:#fff;
  font-variant-numeric:tabular-nums;letter-spacing:0.01em;line-height:1.05;
  text-shadow:0 2px 12px rgba(251,191,36,0.25);
  display:flex;align-items:baseline;gap:0.25rem;
}
.kpi-pro-unified-value .kpi-unit{font-size:0.875rem;font-weight:600;color:#94a3b8;}
.kpi-pro-unified-spark{
  display:flex;align-items:center;gap:0.625rem;
}
.kpi-pro-unified-spark svg{flex-shrink:0;}
.kpi-pro-unified-rate{font-size:0.8125rem;font-weight:700;color:#fbbf24;}
.kpi-pro-unified-extra{font-size:0.6875rem;color:#cbd5e1;margin-top:0.125rem;line-height:1.4;}

.kpi-pro-unified-metric{
  display:flex;flex-direction:column;justify-content:center;gap:0.25rem;
  padding:0 0.25rem;
}
.kpi-pro-unified-metric-head{
  display:flex;align-items:center;justify-content:space-between;gap:0.5rem;
  margin-bottom:0.125rem;
}
.kpi-pro-unified-metric-label{
  font-size:0.8125rem;letter-spacing:0.04em;font-weight:600;
  color:#93c5fd;
}
.kpi-pro-unified-metric.kpi-pro-unified-pay .kpi-pro-unified-metric-label{color:#86efac;}
.kpi-pro-unified-metric-value{
  font-size:1.5rem;font-weight:900;color:#fff;
  font-variant-numeric:tabular-nums;line-height:1.1;letter-spacing:0.01em;
  display:flex;align-items:baseline;gap:0.1875rem;
}
.kpi-pro-unified-metric-value .kpi-unit{font-size:0.6875rem;font-weight:600;color:#94a3b8;}
.kpi-pro-unified-metric svg{display:block;}
.kpi-pro-unified-metric-rate{font-size:0.75rem;color:#cbd5e1;font-weight:500;}
.kpi-pro-unified-metric-top{
  display:grid;grid-template-columns:3.75rem 1fr 3.5rem;align-items:center;gap:0.375rem;
  font-size:0.6875rem;
}
.kpi-pro-top-label{color:#94a3b8;font-size:0.5625rem;font-weight:600;text-transform:uppercase;letter-spacing:0.04em;}
.kpi-pro-top-name{color:#fff;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.kpi-pro-top-val{color:#fff;font-weight:700;font-variant-numeric:tabular-nums;text-align:right;}
.kpi-pro-top-extra{color:#cbd5e1;font-weight:500;}

@media(max-width:1100px){
  .kpi-pro-unified{grid-template-columns:1fr;gap:0.75rem;}
  .kpi-pro-unified-divider{display:none;}
}

.kpi-pro-grid{
  display:grid;grid-template-columns:repeat(3,1fr);gap:0.875rem;margin-bottom:0.75rem;
}
.kpi-pro{
  background:#fff;padding:0.875rem 1rem;border-radius:0.625rem;
  border:1px solid var(--border);box-shadow:var(--shadow-sm);
  position:relative;overflow:hidden;
  transition:box-shadow .2s,transform .2s;
}
.kpi-pro:hover{box-shadow:var(--shadow-md);transform:translateY(-1px);}
.kpi-pro::before{
  content:"";position:absolute;top:0;left:0;right:0;height:0.1875rem;
  background:linear-gradient(90deg,var(--c1,#f59e0b),var(--c2,#fbbf24));
}
.kpi-pro-tgt{--c1:#f59e0b;--c2:#fb923c;}
.kpi-pro-inc{--c1:#3b82f6;--c2:#60a5fa;}
.kpi-pro-pay{--c1:#22c55e;--c2:#4ade80;}
.kpi-pro-header{
  display:flex;justify-content:space-between;align-items:center;
  margin-bottom:0.375rem;
}
.kpi-pro-title{
  font-size:0.75rem;font-weight:700;color:#64748b;letter-spacing:0.04em;
}
.kpi-pro-rate{display:flex;align-items:center;}
.kpi-pro-value-row{
  display:flex;align-items:center;justify-content:space-between;
  margin-bottom:0.375rem;
}
.kpi-pro-value{
  font-size:1.875rem;font-weight:900;color:#0f172a;
  font-variant-numeric:tabular-nums;letter-spacing:0.01em;line-height:1;
}
.kpi-pro-value .kpi-unit{font-size:0.8125rem;font-weight:600;color:#94a3b8;margin-left:0.25rem;}
.kpi-pro-spark{
  display:flex;align-items:center;justify-content:space-between;
  margin-bottom:0.5rem;gap:0.5rem;
}
.kpi-pro-spark svg{flex-shrink:0;}
.kpi-pro-sub{font-size:0.75rem;font-weight:600;}
.kpi-pro-dept{
  display:flex;flex-direction:column;gap:0.1875rem;margin-bottom:0.5rem;
  padding:0.375rem 0;border-top:1px dashed var(--border);border-bottom:1px dashed var(--border);
}
.kpi-dept-row{
  display:grid;grid-template-columns:2.125rem 1fr 3.125rem;align-items:center;gap:0.5rem;
  font-size:0.6875rem;
}
.kpi-dept-name{color:#475569;font-weight:600;}
.kpi-dept-track{
  height:0.5rem;background:#f1f5f9;border-radius:0.25rem;overflow:hidden;
}
.kpi-dept-fill{height:100%;border-radius:0.25rem;transition:width .5s ease;}
.kpi-dept-val{
  color:#0f172a;font-weight:700;font-variant-numeric:tabular-nums;
  text-align:right;font-size:0.6875rem;
}
.kpi-pro-top{
  display:flex;flex-direction:column;gap:0.25rem;
}
.kpi-pro-top-row{
  display:grid;grid-template-columns:3.125rem 1fr 5rem;align-items:center;gap:0.5rem;
  font-size:0.6875rem;
}
.kpi-pro-top-label{
  color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:0.04em;
  font-size:0.625rem;
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
  .kpi-pro-grid{grid-template-columns:1fr;gap:0.625rem;}
  .kpi-pro-value{font-size:1.5rem;}
}

.sales-c1-grid{
  display:grid;grid-template-columns:1fr 1fr;gap:1rem;
}
.sales-panel{
  background:#fff;padding:0.75rem 0.875rem;border-radius:0.5rem;
  border:1px solid var(--border);box-shadow:var(--shadow-sm);
}
.sales-panel .card-title{
  font-size:0.875rem;font-weight:700;color:#0f172a;margin-bottom:0.625rem;
  padding-bottom:0.5rem;border-bottom:0.125rem solid var(--border);
}
.sales-panel .mini-rate{
  padding:0.375rem 0;font-size:0.75rem;
}
.sales-panel .mini-rate .bar{height:0.875rem;}
.sales-panel.inc-panel{border-top:0.1875rem solid #f59e0b;}
.sales-panel.pay-panel{border-top:0.1875rem solid #16a34a;}
@media(max-width:860px){
  .sales-c1-grid{grid-template-columns:1fr;gap:0.625rem;}
}

.sales-roster{display:grid;grid-template-columns:repeat(auto-fill,minmax(17.5rem,1fr));gap:0.375rem;margin-top:0.25rem;}
.sales-roster-head{
  display:flex;align-items:center;gap:0.375rem;
  padding:0.375rem 0.625rem;border-bottom:1px solid var(--border);margin-bottom:0.25rem;
  font-size:0.6875rem;color:#64748b;
}
.sales-amt-head{min-width:6.875rem;text-align:right;}
.sales-rate-head{min-width:3.125rem;text-align:center;}
.sales-chip{
  display:flex;align-items:center;gap:0.375rem;
  padding:0.375rem 0.625rem;border-radius:0.375rem;
  background:#f8fafc;border:1px solid #e2e8f0;
  font-size:0.8125rem;transition:box-shadow .15s;
}
.sales-chip:hover{box-shadow:0 1px 0.25rem rgba(0,0,0,.08);}
.sales-name{flex:1;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.sales-amt{
  font-weight:700;color:#1e293b;white-space:nowrap;min-width:6.875rem;text-align:right;
  display:flex;align-items:baseline;justify-content:flex-end;gap:0.125rem;
}
.sales-unit{font-size:0.625rem;color:#94a3b8;font-weight:400;}
.sales-rate{
  font-weight:700;font-size:0.75rem;padding:1px 0.5rem;border-radius:0.625rem;min-width:3.125rem;text-align:center;
  white-space:nowrap;
}
.sales-rate.rate-high{background:#f0fdf4;color:#16a34a;}
.sales-rate.rate-mid{background:#fff7ed;color:#ea580c;}
.sales-rate.rate-low{background:#fef2f2;color:#dc2626;}
.legend{
  margin-top:0.625rem;padding:0.5rem 0.75rem;border-radius:0.375rem;
  background:#f8fafc;border-left:0.1875rem solid #2563eb;
  display:flex;flex-direction:column;gap:0.25rem;font-size:0.6875rem;color:#475569;
}
.legend-item{line-height:1.5;}
.legend-item b{color:#1e293b;}

"""
