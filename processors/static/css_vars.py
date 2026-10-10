# Author: naohua168 <bai_bai168@qq.com>
"""看板全局 CSS 常量 — 从 base.py 拆分

包含: CSS_CORE, CSS_COMPONENTS, CSS_RESPONSIVE, CSS_ANIMATIONS, GLOBAL_CSS
"""
CSS_CORE = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
/* ═══════════════════════════════════════════════════════════════
   专业数据驾驶舱 — Data-Dense Dashboard 风格
   配色：深蓝主色 #2563eb + 琥珀金强调 #f59e0b + 紫色辅助 #8b5cf6
   字体：Inter（正文）+ JetBrains Mono（数字）
   ═══════════════════════════════════════════════════════════════ */
* { margin:0; padding:0; box-sizing:border-box; }
:root {
  /* ── 流体根字号（2026-10-10 B 方案）──
     全站尺寸改走 rem，1rem 随视口平滑变化 ⇒ 窗口大小/系统缩放变化时整体等比缩放，
     不再靠"断点之间写死 px"硬撑：
       1920 视口 ≈ 16px（与改造前视觉一致）｜1600 ≈ 14.8px｜1366 ≈ 13.9px｜≤1100 → 13.5px 下限
     其余 px 只保留：≤1px 发丝线 / box-shadow / @media 断点 */
  font-size:clamp(13.5px, 0.38vw + 8.7px, 16px);
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
  --shadow-sm:0 0.0625rem 0.125rem rgba(0,0,0,0.04);
  --shadow-md:0 0.25rem 0.375rem -0.0625rem rgba(0,0,0,0.06),0 0.0625rem 0.1875rem rgba(0,0,0,0.04);
  --shadow-lg:0 0.625rem 0.9375rem -0.1875rem rgba(0,0,0,0.06),0 0.25rem 0.375rem -0.125rem rgba(0,0,0,0.04);
  --header-h:3.25rem; --nav-h:2.5rem;
  /* ── 动画（Apple 风格缓动）── */
  --ease: cubic-bezier(0.32, 0.72, 0, 1);           /* 苹果标准 ease */
  --ease-out: cubic-bezier(0.22, 1, 0.36, 1);        /* EaseOutQuint — 快入缓出 */
  --ease-in-out: cubic-bezier(0.45, 0, 0.55, 1);     /* 标准 ease-in-out */
  --ease-spring: cubic-bezier(0.34, 1.4, 0.64, 1);   /* 回弹（弹窗专用） */
  --dur-fast: 150ms; --dur-base: 250ms; --dur-slow: 400ms;
}
/* 骨架：body 竖排 flex —— header 多高都行，内容区吃剩余高度、页内滚动。
   （原来是 .page{height:calc(100vh - 82px)}：header 一换行/一缩放就把页面底部裁掉） */
html{height:100%;}
body{
  height:100%;height:100dvh;min-height:100dvh;
  display:flex;flex-direction:column;
  overflow-x:hidden;
  font-family:"Inter","Microsoft YaHei",Arial,sans-serif;
  background:var(--bg-alt);color:var(--text);font-size:0.875rem;line-height:1.5;
}
/* overflow:hidden：切换动画期间子元素位移（translateY）不会撑出页面级滚动条；
   弹窗是 position:fixed，main 不是它的 containing block，不受裁剪影响 */
main{flex:1 1 auto;min-height:0;display:flex;flex-direction:column;overflow:hidden;}
/* position:relative + overflow:hidden：页面切换时新旧两页同时在容器内做横向推入/推出，裁掉溢出部分 */
#page-host{flex:1 1 auto;min-height:0;display:flex;flex-direction:column;position:relative;overflow:hidden;}
/* 数字表格使用等宽字体 */
table, .kpi-value, .progress-val, .rank, .mini-rate .val, .yoy-up, .yoy-down, .completion{
  font-family:"JetBrains Mono","Inter","Microsoft YaHei",monospace;
}

/* ═══════════════════─ 顶部标题栏 ─══════════════════ */
.header{
  background:#1e293b;color:#ffffff;padding:0 1rem;
  position:sticky;top:0;z-index:100;
  display:flex;flex-direction:column;flex:0 0 auto;
  box-shadow:0 1px 3px rgba(0,0,0,0.1);
}
.header-top{
  display:flex;align-items:center;justify-content:center;
  height:2.375rem;border-bottom:1px solid rgba(255,255,255,0.08);
}
.header-title{
  font-size:1.125rem;font-weight:800;letter-spacing:0.04em;
  margin:0;color:#fbbf24;text-align:center;
  text-shadow:0 1px 2px rgba(0,0,0,.3);
}
.header-bottom{
  display:flex;align-items:center;justify-content:space-between;
  height:2.75rem;
}
.header-left{display:flex;align-items:center;gap:1rem;}
.header-logo{display:none;}
.header h1{font-size:1.25rem;font-weight:700;letter-spacing:0.02em;color:#f1f5f9;}
.header .fullscreen-btn{
  display:flex;align-items:center;gap:0.25rem;padding:0.25rem 0.625rem;
  background:rgba(255,255,255,0.1);color:#e2e8f0;border:1px solid rgba(255,255,255,0.2);
  border-radius:0.25rem;cursor:pointer;font-size:0.6875rem;font-weight:600;transition:all .2s;
}
.fullscreen-btn:hover{background:rgba(255,255,255,0.2);border-color:rgba(255,255,255,0.4);color:#fff;}

/* ═══════════════════─ 导航栏 ─══════════════════ */
.nav{
  display:flex;gap:0;align-items:stretch;justify-content:center;
  flex:1;position:relative;
}
/* 导航项是 <button>（不是 <a href="#">）—— 无地址预览、无 URL # 尾巴 */
.nav .nav-link{
  padding:0 1.5rem;color:#cbd5e1;text-decoration:none;
  font-family:inherit;font-size:0.875rem;font-weight:700;
  display:flex;align-items:center;cursor:pointer;
  background:none;border:0;border-bottom:0.1875rem solid transparent;
  transition:all 0.2s;letter-spacing:0.03em;position:relative;
}
.nav .nav-link:hover{color:#fbbf24;background:rgba(255,255,255,0.08);}
/* 高亮项：文字变色 + 发光；下划线由 .nav-underline 滑动条统一画（不再用各项自己的 border） */
.nav .nav-link.active{
  color:#fbbf24;background:transparent;
  text-shadow:0 0 8px rgba(251,191,36,.4);
}
.nav .nav-link:focus-visible{outline:0.125rem solid rgba(251,191,36,.6);outline-offset:-0.25rem;}
.nav-underline{
  position:absolute;left:0;bottom:0;width:0;height:0.1875rem;
  background:#fbbf24;border-radius:0.125rem 0.125rem 0 0;
  box-shadow:0 0 0.5rem rgba(251,191,36,.45);
  transition:left 0.28s var(--ease-out),width 0.28s var(--ease-out);
  pointer-events:none;
}

/* ═══════════════════─ 页面容器 ─══════════════════ */
/* 页面容器：绝对定位铺满 #page-host（2026-10-10）。
   为什么绝对定位：切换时新旧两页必须"叠在同一格子里"（旧页做遮罩淡出、新页在下层被揭开）。
   以前页面在文档流里，一旦有 id 选择器（如 .page#overview 的 position:relative）压过
   .page-leaving，旧页就仍在流中 → 两页上下排成两栏（切页时"上半屏旧页、下半屏新页"的错乱来源）。
   高度仍由 flex 骨架给 #page-host 定，页面自身不参与撑高。
   overflow-x:hidden 必须显式写：弹窗/抽屉停在屏幕右侧离屏位置，不裁掉会把页面可滚动宽度撑大。
   宽表自己的横滑由 .table-wrap 负责，不受影响。 */
.page{display:none;position:absolute;inset:0;padding:0.5rem 0.625rem;overflow-y:auto;overflow-x:hidden;}
.page.active{display:block;}
/* 自定义滚动条 */
.page::-webkit-scrollbar{width:0.375rem;}
.page::-webkit-scrollbar-track{background:transparent;}
.page::-webkit-scrollbar-thumb{background:#c1c1c1;border-radius:0.1875rem;}
.page::-webkit-scrollbar-thumb:hover{background:#a8a8a8;}

.section-title{
  font-size:0.875rem;font-weight:700;color:#0f172a;
  margin:0.625rem 0 0.375rem 0;padding:0.3125rem 0.625rem;
  display:inline-flex;align-items:center;gap:0.375rem;
  border-radius:0.375rem;letter-spacing:0.03em;
}
.section-title:first-child{margin-top:0;}
.section-title::after{
  content:'';flex:1;height:1px;margin-left:0.5rem;
  min-width:2.5rem;
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
"""

CSS_COMPONENTS = """
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

/* ═══════════════════─ 数据表格 ─══════════════════ */
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


/* ═══════════════════─ 卡片容器 ─══════════════════ */
.card{
  background:#fff;padding:0.75rem 0.875rem;
  border:1px solid var(--border);margin-bottom:0.375rem;
  border-radius:0.625rem;box-shadow:var(--shadow-sm);
  transition:box-shadow 0.2s,transform 0.2s;
}
.card-title{
  font-size:0.875rem;font-weight:700;color:#0f172a;margin-bottom:0.5rem;
  padding-bottom:0.375rem;border-bottom:1px solid var(--border);
  display:flex;align-items:center;justify-content:space-between;
  letter-spacing:0.02em;
}
.card-title::before{
  content:'';display:inline-block;width:0.1875rem;height:0.875rem;
  background:var(--accent);border-radius:0.125rem;margin-right:0.5rem;
}

/* ═══════════════════─ 网格布局 ─══════════════════ */
.cols-2{display:grid;grid-template-columns:1fr 1fr;gap:0.25rem;margin-bottom:0.25rem;}
.cols-3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.25rem;margin-bottom:0.25rem;}
.cols-4{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:0.25rem;margin-bottom:0.25rem;}

/* ═══════════════════─ 迷你数据条 ─══════════════════ */
.mini-rate{display:flex;align-items:center;gap:0.5rem;padding:0.25rem 0;font-size:0.8125rem;}
.mini-rate .bar{
  flex:1;height:0.875rem;background:#eef0f5;
  overflow:hidden;border-radius:0.3125rem;position:relative;
  min-width:5rem;
}
.mini-rate .bar-fill{height:100%;min-width:0.125rem;border-radius:0.3125rem;position:relative;}
.mini-rate .bar-pct{
  position:absolute;right:0.25rem;top:50%;transform:translateY(-50%);
  font-size:0.625rem;font-weight:800;line-height:0.875rem;
  color:#334155;
  letter-spacing:0.02em;pointer-events:none;
}
.mini-rate .bar-fill.level-1{background:#dc2626;}
.mini-rate .bar-fill.level-2{background:#f97316;}
.mini-rate .bar-fill.level-3{background:#f59e0b;}
.mini-rate .bar-fill.level-4{background:#16a34a;}
.mini-rate .val{min-width:4.375rem;text-align:right;font-weight:700;font-variant-numeric:tabular-nums;color:#1e293b;}
.pct-tag{
  display:inline-block;min-width:3.375rem;padding:0.125rem 0.375rem;text-align:center;
  font-size:0.6875rem;font-weight:800;font-variant-numeric:tabular-nums;
  border-radius:0.1875rem;letter-spacing:0.02em;
}
.pct-tag.level-1{background:#fee2e2;color:#dc2626;border:1px solid #fecaca;}
.pct-tag.level-2{background:#ffedd5;color:#ea580c;border:1px solid #fed7aa;}
.pct-tag.level-3{background:#fef3c7;color:#ca8a04;border:1px solid #fde68a;}
.pct-tag.level-4{background:#dcfce7;color:#16a34a;border:1px solid #bbf7d0;}

/* ═══════════════════─ 排名徽章 ─══════════════════ */
.rank{
  display:inline-flex;width:1.375rem;height:1.375rem;align-items:center;justify-content:center;
  font-size:0.6875rem;font-weight:800;margin-right:0.25rem;flex-shrink:0;color:#fff;
  border-radius:0.25rem;
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
.bar-cell{height:0.25rem;background:#eef0f5;overflow:hidden;margin-top:0.1875rem;border-radius:0.125rem;}
.bar-fill-cell{height:100%;background:#2563eb;min-width:0.125rem;border-radius:0.125rem;}

/* ═══════════════════─ 同比色块 ─══════════════════ */
.yoy-up{
  display:inline-block;padding:0.125rem 0.5rem;font-weight:700;
  font-variant-numeric:tabular-nums;font-size:0.6875rem;border-radius:0.25rem;
  background:#fee2e2;color:#dc2626;
}
.yoy-down{
  display:inline-block;padding:0.125rem 0.5rem;font-weight:700;
  font-variant-numeric:tabular-nums;font-size:0.6875rem;border-radius:0.25rem;
  background:#dcfce7;color:#16a34a;
}
.yoy-neutral{color:var(--text-muted);font-weight:600;}

/* ═══════════════════─ 同比对比单元格 ──────────────── */
.yoy-cell{
  padding:0.375rem 0.5rem;min-width:8.75rem;vertical-align:top;
}
.yoy-amount{font-size:0.8125rem;font-weight:700;color:var(--text);font-variant-numeric:tabular-nums;}
.yoy-bars{
  display:flex;flex-direction:column;gap:0.125rem;margin:0.25rem 0 0.125rem;
  position:relative;
}
.yoy-bar{height:0.3125rem;border-radius:0.1875rem;min-width:0.125rem;transition:width 0.3s ease;}
.yoy-bar.cur{background:var(--accent);position:relative;}
.yoy-bar.prev{background:#cbd5e1;}
.yoy-pct{
  display:inline-block;font-size:0.6875rem;font-weight:800;font-variant-numeric:tabular-nums;
  padding:1px 0.375rem;border-radius:0.1875rem;margin-top:0.125rem;
}
.yoy-pct.up{background:#fee2e2;color:#dc2626;}
.yoy-pct.down{background:#dcfce7;color:#16a34a;}
.yoy-pct.flat{background:#f1f5f9;color:#64748b;}
.yoy-prev-amt{font-size:0.625rem;color:var(--text-muted);font-variant-numeric:tabular-nums;margin-top:1px;}

/* ═══════════════════─ 同比趋势箭头 ─────────────── */
.yoy-arrow{
  display:inline-flex;align-items:center;justify-content:center;
  width:1.125rem;height:1.125rem;font-size:0.6875rem;font-weight:800;
  border-radius:0.25rem;margin-right:0.125rem;
}
.yoy-arrow.up{background:#fee2e2;color:#dc2626;}
.yoy-arrow.down{background:#dcfce7;color:#16a34a;}
.yoy-arrow.flat{background:#f1f5f9;color:#64748b;}

/* ═══════════════════─ 同比周期 chip ───────────── */
.period-chip{
  display:flex;align-items:center;gap:0.5rem;margin-bottom:0.375rem;padding:0.375rem 0.75rem;
  background:#f1f5f9;border-radius:0.25rem;border-left:0.1875rem solid var(--accent);
}
.period-tag{
  display:inline-block;background:var(--accent);color:#fff;
  padding:0.125rem 0.625rem;font-size:0.6875rem;font-weight:700;border-radius:0.1875rem;
  letter-spacing:0.04em;
}
.period-text{font-size:0.75rem;color:var(--text-secondary);font-weight:500;}

/* ═══════════════════─ 同比大对比卡（2 卡，深色稳重风） ───────────── */
.yoy-big-card{
  position:relative;
  padding:1.25rem 1.5rem;
  border-radius:0.625rem;
  background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%);
  color:#fff;
  display:grid;grid-template-columns:1fr 1.4fr;gap:1.5rem;align-items:center;
  box-shadow:0 4px 16px rgba(15,23,42,0.25);
  overflow:hidden;
}
.yoy-big-card::before{
  content:"";position:absolute;left:0;top:0;bottom:0;width:0.25rem;background:var(--accent-color,#dc2626);
}
.yoy-big-card.up{--accent-color:#dc2626;}
.yoy-big-card.down{--accent-color:#16a34a;}
.yoy-big-card.flat{--accent-color:#64748b;}

/* 左侧：同比率 */
.yoy-big-info{display:flex;flex-direction:column;gap:0.5rem;}
.yoy-big-label{
  font-size:0.8125rem;color:#94a3b8;font-weight:600;
  text-transform:uppercase;letter-spacing:0.08em;
}
.yoy-big-pct{
  font-size:3.25rem;font-weight:900;line-height:1;
  font-variant-numeric:tabular-nums;letter-spacing:-0.02em;
  display:flex;align-items:baseline;gap:0.375rem;
}
.yoy-big-pct .yoy-arrow{
  width:2.125rem;height:2.125rem;font-size:1.125rem;
  background:rgba(255,255,255,0.08);border-radius:0.5rem;
}
.yoy-big-pct .yoy-arrow.up{color:#dc2626;background:rgba(220,38,38,0.15);}
.yoy-big-pct .yoy-arrow.down{color:#16a34a;background:rgba(22,163,74,0.15);}
.yoy-big-pct .yoy-arrow.flat{color:#94a3b8;background:rgba(148,163,184,0.15);}
.yoy-big-pct-num{line-height:1;}

/* 右侧：对比柱状图 */
.yoy-big-compare{
  display:flex;flex-direction:column;gap:0.875rem;
  padding-left:1.25rem;border-left:1px solid rgba(255,255,255,0.12);
}
.yoy-cmp-item{display:flex;flex-direction:column;gap:0.375rem;}
.yoy-cmp-header{display:flex;justify-content:space-between;align-items:baseline;}
.yoy-cmp-label{
  font-size:0.75rem;font-weight:600;color:#94a3b8;
  letter-spacing:0.04em;
}
.yoy-cmp-val{
  font-size:1.125rem;font-weight:700;color:#fff;
  font-variant-numeric:tabular-nums;
}
.yoy-cmp-val .yoy-cmp-unit{font-size:0.6875rem;font-weight:500;color:#64748b;margin-left:0.125rem;}
/* 柱状条 */
.yoy-cmp-bar{
  height:0.5rem;border-radius:0.25rem;background:rgba(255,255,255,0.08);
  position:relative;overflow:hidden;
}
.yoy-cmp-fill{
  height:100%;border-radius:0.25rem;
  transition:width 1s cubic-bezier(0.22,1,0.36,1);
}
.yoy-cmp-fill.cur.up{background:linear-gradient(90deg,#dc2626,#ef4444);box-shadow:0 0 0.75rem rgba(220,38,38,0.4);}
.yoy-cmp-fill.cur.down{background:linear-gradient(90deg,#16a34a,#22c55e);box-shadow:0 0 0.75rem rgba(22,163,74,0.4);}
.yoy-cmp-fill.cur.flat{background:linear-gradient(90deg,#94a3b8,#cbd5e1);}
.yoy-cmp-fill.prev{
  background:linear-gradient(90deg,#cbd5e1,#e2e8f0);
  opacity:0.85;
}

/* 响应式 */
@media(max-width:860px){
  .yoy-big-card{grid-template-columns:1fr;gap:1rem;}
  .yoy-big-compare{padding-left:0;border-left:none;border-top:1px solid rgba(255,255,255,0.12);padding-top:1rem;}
}

/* ═══════════════════─ 图表容器 ─══════════════════ */
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

/* ═══════════════════─ 圆环 Hero ─══════════════════ */
.hero-rings{
  display:flex;align-items:center;justify-content:space-between;
  gap:0.75rem;padding:1.375rem 1.875rem;margin-bottom:0.5rem;border-radius:0.75rem;
  background:linear-gradient(135deg,#0a1628 0%,#1e3a5f 50%,#0a1628 100%);
  color:#fff;box-shadow:0 0.375rem 1.125rem rgba(10,22,40,0.35);
  min-height:12.5rem;flex-wrap:wrap;        /* 放不下就换行，不再被裁掉右边缘 */
}
/* 两翼按份数分配：基准 13rem，不够宽才换行；min-width:0 允许内部收缩 */
.hero-rings .hr-side{flex:1 1 13rem;min-width:0;display:flex;flex-direction:column;gap:0.625rem;}
.hero-rings .hr-side.inc-side{align-items:flex-start;text-align:left;}
.hero-rings .hr-side.pay-side{align-items:flex-end;text-align:right;}
.hero-rings .hr-side-title{
  font-size:0.875rem;letter-spacing:0.04em;font-weight:600;
  opacity:0.9;display:flex;align-items:center;gap:0.375rem;flex-wrap:wrap;
}
.hero-rings .hr-side.pay-side .hr-side-title{flex-direction:row-reverse;}
.hero-rings .hr-side-amount{
  font-size:3.375rem;font-weight:900;color:#fbbf24;
  font-variant-numeric:tabular-nums;letter-spacing:0.01em;line-height:1;
  display:flex;align-items:baseline;gap:0.375rem;
  text-shadow:0 2px 12px rgba(251,191,36,0.2);
}
.hero-rings .hr-side.pay-side .hr-side-amount{flex-direction:row;}
/* 总指标 — 琥珀色 */
.hero-rings .hr-side-amount.hr-side-target{color:#fbbf24;text-shadow:0 0.125rem 0.875rem rgba(251,191,36,0.3);}
.hero-rings .hr-side-unit{font-size:1.125rem;font-weight:600;color:#94a3b8;letter-spacing:0;}
.hero-rings .hr-side-metrics{
  display:flex;flex-direction:column;gap:0.3125rem;
  padding-top:0.625rem;border-top:1px dashed rgba(255,255,255,0.15);
  width:100%;
}
.hero-rings .hr-side.pay-side .hr-side-metrics{align-items:flex-end;}
.hero-rings .hr-metric{
  display:flex;align-items:center;gap:0.625rem;font-size:0.875rem;
  font-variant-numeric:tabular-nums;color:#cbd5e1;
}
.hero-rings .hr-side.pay-side .hr-metric{flex-direction:row-reverse;}
.hero-rings .hr-metric-label{opacity:0.75;min-width:3.75rem;font-weight:500;}
.hero-rings .hr-metric-val{font-weight:700;color:#e0e7ff;font-size:0.9375rem;}
.hero-rings .hr-metric-gap .hr-metric-val{color:#fb923c;}
.hero-rings .hr-yoy{
  display:inline-block;font-size:0.75rem;font-weight:700;
  padding:0.125rem 0.5625rem;border-radius:0.5625rem;letter-spacing:0;
  margin-left:0.375rem;
}
.hero-rings .hr-side.pay-side .hr-yoy{margin-left:0;margin-right:0.375rem;}
.hero-rings .hr-yoy-up{background:rgba(220,38,38,0.2);color:#fca5a5;border:1px solid rgba(220,38,38,0.4);}
.hero-rings .hr-yoy-dn{background:rgba(34,197,94,0.18);color:#4ade80;border:1px solid rgba(34,197,94,0.35);}
.hero-rings .hr-yoy-period{font-size:0.6875rem;opacity:0.6;font-weight:500;margin-left:0.375rem;letter-spacing:0;}
.hero-rings .hr-side.pay-side .hr-yoy-period{margin-left:0;margin-right:0.375rem;}
.hero-rings .hr-ring{
  position:relative;width:6rem;height:6rem;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
}
.hero-rings .hr-ring svg{transform:rotate(-90deg);width:6rem;height:6rem;}
.hero-rings .hr-ring circle{fill:none;stroke-width:10;stroke-linecap:round;}
.hero-rings .hr-ring .hr-track{stroke:rgba(255,255,255,0.10);}
.hero-rings .hr-ring.inc-ring .hr-progress{stroke:#3b82f6;
  filter:drop-shadow(0 0 0.25rem rgba(59,130,246,0.55));
  transition:stroke-dashoffset 1.1s cubic-bezier(0.22,1,0.36,1);}
.hero-rings .hr-ring.pay-ring .hr-progress{stroke:#22c55e;
  filter:drop-shadow(0 0 0.25rem rgba(34,197,94,0.55));
  transition:stroke-dashoffset 1.1s cubic-bezier(0.22,1,0.36,1);}
.hero-rings .hr-ring .hr-center{
  position:absolute;inset:0;display:flex;flex-direction:column;
  align-items:center;justify-content:center;color:#fff;
  transform:rotate(0deg);pointer-events:none;
}
.hero-rings .hr-ring .hr-pct{font-size:1.125rem;font-weight:800;font-variant-numeric:tabular-nums;line-height:1;}
.hero-rings .hr-ring.inc-ring .hr-pct{color:#93c5fd;}
.hero-rings .hr-ring.pay-ring .hr-pct{color:#86efac;}
.hero-rings .hr-ring .hr-label{font-size:0.625rem;font-weight:600;opacity:0.7;letter-spacing:0.06em;margin-top:0.125rem;text-transform:uppercase;}
.hero-rings .hr-center-box{
  flex:0 0 auto;display:flex;flex-direction:column;align-items:center;
  justify-content:center;padding:0 1rem;
  border-left:1px dashed rgba(255,255,255,0.2);
  border-right:1px dashed rgba(255,255,255,0.2);
  min-width:16.25rem;
}
/* 中间：总指标大数字（total_tgt 模式） */
.hero-rings .hr-center-label{
  display:flex;align-items:center;gap:0.375rem;
  font-size:0.8125rem;font-weight:600;opacity:0.85;color:#fbbf24;letter-spacing:0.04em;
}
.hero-rings .hr-center-value{
  font-size:3rem;font-weight:900;color:#fbbf24;font-variant-numeric:tabular-nums;
  letter-spacing:0.005em;line-height:1.1;text-shadow:0 0.125rem 1.125rem rgba(251,191,36,0.3);
  white-space:nowrap;
}
.hero-rings .hr-center-value .hr-center-unit{font-size:1rem;font-weight:600;color:#94a3b8;}
.hero-rings .hr-center-split{display:flex;align-items:center;gap:1rem;}
.hero-rings .hr-cs-col{display:flex;flex-direction:column;align-items:center;gap:0.375rem;flex:1;}
.hero-rings .hr-cs-label{font-size:0.8125rem;font-weight:600;opacity:0.85;color:#fbbf24;letter-spacing:0.04em;}
.hero-rings .hr-cs-val{font-size:2.25rem;font-weight:900;color:#fbbf24;font-variant-numeric:tabular-nums;letter-spacing:0.005em;line-height:1.1;text-shadow:0 0.125rem 1.125rem rgba(251,191,36,0.3);white-space:nowrap;}
.hero-rings .hr-cs-div{width:1px;height:3.125rem;background:rgba(255,255,255,0.2);}
.hero-rings .hr-side-ring{
  flex:0 0 auto;display:flex;align-items:center;justify-content:center;
  padding:0 0.25rem;cursor:default;
}
.hero-rings .hr-side-ring .hr-ring{width:8.125rem;height:8.125rem;}
.hero-rings .hr-side-ring .hr-ring svg{width:8.125rem;height:8.125rem;stroke-width:12;}
.hero-rings .hr-side-ring .hr-ring .hr-pct{font-size:1.625rem;font-weight:900;letter-spacing:-0.02em;}
.hero-rings .hr-side-ring .hr-ring .hr-label{font-size:0.8125rem;font-weight:600;letter-spacing:0.04em;margin-top:0.25rem;}
.hero-rings .hr-side-ring .hr-ring .hr-track{stroke-width:12;}
.hero-rings .hr-side-ring.inc-side-ring{padding-right:0.5rem;}
.hero-rings .hr-side-ring.pay-side-ring{padding-left:0.5rem;}
.hero-rings .hr-rings{display:flex;align-items:center;gap:0.875rem;flex:0 0 auto;}
/* 中间 ring 组合（target/ring/actual 三件套） */
.hero-rings .hr-ring-group{display:flex;flex-direction:column;align-items:center;gap:0.625rem;padding:0 0.5rem;}
.hero-rings .hr-ring-target{font-size:1.5rem;font-weight:900;color:#22d3ee;font-variant-numeric:tabular-nums;letter-spacing:-0.02em;text-shadow:0 0.125rem 0.75rem rgba(34,211,238,0.3);text-align:center;}
.hero-rings .hr-ring-target span{font-size:0.75rem;font-weight:500;opacity:0.7;margin-left:0.125rem;}
.hero-rings .hr-ring-amount{font-size:1.125rem;font-weight:800;color:#fbbf24;font-variant-numeric:tabular-nums;letter-spacing:-0.02em;text-align:center;text-shadow:0 0.125rem 0.625rem rgba(251,191,36,0.3);}
.hero-rings .hr-ring-amount span{font-size:0.75rem;font-weight:500;opacity:0.7;margin-left:0.125rem;}
/* 2026-10-10：原来这里（≤1360px）把 Hero 数字/环径改小一档，既与流体根字号重复、
   又在断点处出现台阶；缩放统一交给 rem，本断点不再改尺寸，只保证换行不溢出。 */
@media(max-width:1360px){
  .hero-rings{gap:0.75rem;}
}
@media(max-width:860px){
  .hero-rings .hr-side{flex:0 0 100%;text-align:left !important;align-items:flex-start !important;}
  .hero-rings .hr-side.pay-side{text-align:left !important;align-items:flex-start !important;}
  .hero-rings .hr-side.pay-side .hr-side-title{flex-direction:row;}
  .hero-rings .hr-side.pay-side .hr-side-amount{flex-direction:row;}
  .hero-rings .hr-side.pay-side .hr-side-metrics{align-items:flex-start;}
  .hero-rings .hr-side.pay-side .hr-metric{flex-direction:row;}
  .hero-rings .hr-side.pay-side .hr-yoy{margin-left:0.375rem;margin-right:0;}
  .hero-rings .hr-side.pay-side .hr-yoy-period{margin-left:0.375rem;margin-right:0;}
  .hero-rings .hr-side-amount{font-size:2.25rem;}
  .hero-rings .hr-center-box{flex:0 0 100%;order:2;border-top:1px dashed rgba(255,255,255,0.2);border-bottom:1px dashed rgba(255,255,255,0.2);border-left:none;border-right:none;padding:0.875rem 0 0.625rem;min-width:0;gap:0.5rem;}
  .hero-rings .hr-center-value{font-size:2.875rem;}
  .hero-rings .hr-center-unit{font-size:0.875rem;}
  .hero-rings .hr-side-ring{flex:1 1 100%;justify-content:center;padding:0.375rem 0;}
  .hero-rings .hr-side-ring.inc-side-ring{order:1;}
  .hero-rings .hr-side-ring.pay-side-ring{order:3;}
  .hero-rings .hr-side-ring .hr-ring{width:5rem;height:5rem;}
  .hero-rings .hr-side-ring .hr-ring svg{width:5rem;height:5rem;}
}

/* ═══════════════════─ 年度达成 Hero（深底大数字 + 双进度） ─══════════════════ */
.annual-hero{
  background:linear-gradient(135deg,#0a1628 0%,#1e3a5f 50%,#0a1628 100%);
  color:#fff;padding:1.125rem 1.5rem;margin-bottom:0.375rem;border-radius:0.5rem;
  display:flex;align-items:center;gap:1.25rem;flex-wrap:wrap;
  box-shadow:0 4px 12px rgba(10,22,40,0.25);
}
.annual-hero-label{
  font-size:0.75rem;opacity:0.7;letter-spacing:0.08em;text-transform:uppercase;
  min-width:7.5rem;font-weight:600;
}
.annual-hero-value{
  font-size:2.625rem;font-weight:800;font-variant-numeric:tabular-nums;
  color:#fbbf24;flex:0 0 auto;letter-spacing:0.02em;
}
.annual-hero-unit{font-size:1rem;font-weight:500;opacity:0.85;margin-left:0.375rem;}
.annual-hero-bars{flex:1;min-width:25rem;display:flex;flex-direction:column;gap:0.5rem;}
.annual-hero-bar{display:flex;align-items:center;gap:0.625rem;}
.annual-hero-name{font-size:0.8125rem;font-weight:700;min-width:2.625rem;}
.annual-hero-track{
  flex:1;height:1.125rem;background:rgba(255,255,255,0.12);
  border-radius:0.5625rem;overflow:hidden;position:relative;
}
.annual-hero-fill{
  height:100%;border-radius:0.5625rem;display:flex;align-items:center;
  justify-content:flex-end;padding-right:0.625rem;
  color:#fff;font-size:0.6875rem;font-weight:800;letter-spacing:0.02em;
  min-width:2.25rem;transition:width 0.5s ease;
}
.annual-hero-fill.inc{background:linear-gradient(90deg,#1e40af,#2563eb);}
.annual-hero-fill.pay{background:linear-gradient(90deg,#15803d,#16a34a);}
.annual-hero-val{font-size:0.8125rem;font-weight:700;font-variant-numeric:tabular-nums;color:#e0e7ff;min-width:5rem;text-align:right;}
.annual-hero-arrow{font-size:0.875rem;color:#cbd5e1;font-weight:700;margin-left:0.375rem;transition:transform 0.2s;}
.annual-hero-bar.expanded .annual-hero-arrow{transform:rotate(90deg);color:#fbbf24;}

/* 折叠/展开 */
.hidden{display:none !important;}

/* ═══════════════════─ 重要客户 tab 切换 ───────── */
.cust-tabs{
  display:flex;gap:0.375rem;margin:0 0 0.375rem 0;
  border-bottom:0.125rem solid var(--border);
}
.cust-tab{
  padding:0.375rem 1.125rem;font-size:0.8125rem;font-weight:700;cursor:pointer;
  border-radius:0.375rem 0.375rem 0 0;color:var(--text-muted);
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
  width:100%;border-collapse:separate;border-spacing:0;font-size:1.5rem;background:#fff;
  border:1px solid #e2e5ed;
}
/* 盒式列宽（2026-10-10）：列宽按比例分配（客户/合计各 20%，4 部门均分），不再由内容撑破容器。
   最小宽度 64rem：≥1220 时单格横排（百分比+实际/目标 ≈158px），<1220 格内改上下两行（≈125px），
   两种情况都够用；再窄（手机）就在 .table-wrap 内横滑，数据一个不少 */
table.ann-matrix, .ann-matrix, table.yoy-dept-table, .yoy-dept-table{table-layout:fixed;}
table.ann-matrix, .ann-matrix{min-width:64rem;}
table.ann-matrix .th-name, .ann-matrix .th-name{width:20%;min-width:0;}
table.ann-matrix th, table.ann-matrix td,
.ann-matrix th, .ann-matrix td{
  /* 2026-10-10：内边距 12/20px → 10/12px，配合格内字号收紧，让 6 列在 1093 逻辑宽下也能一屏排下 */
  padding:0.625rem 0.75rem;text-align:right;
  border:1px solid #e2e5ed;vertical-align:middle;
  line-height:1.3;
}
table.ann-matrix thead th,
.ann-matrix thead th{
  background:#0f172a;color:#ffffff;font-weight:900;font-size:1.625rem !important;
  letter-spacing:0.06em;text-transform:none;
  position:sticky;top:0;z-index:10;
  text-align:center !important;
  border-color:#1e293b;padding:0.875rem 0.625rem !important;
  line-height:1.3;text-shadow:0 0.125rem 0.25rem rgba(0,0,0,.4);
  border-bottom:0.125rem solid #fbbf24;
}
/* 合计行吸底（仅定位，样式沿用已有 .row-total 规则） */
table.ann-matrix tbody .row-total td,
.ann-matrix tbody .row-total td{
  position:sticky;bottom:0;z-index:5;
}
/* 2行分组头部 — 收入组/回款组（统一 1.1875rem 配合主表头） */
table.ann-matrix thead tr.group-row th,
.ann-matrix thead tr.group-row th{
  font-size:1.1875rem;font-weight:800;
  padding:0.875rem 0.5rem;
  letter-spacing:0.12em;
  border-bottom-width:0.125rem;
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
  font-size:0.8125rem;font-weight:700;
  padding:0.625rem 0.5rem;
  background:#1e293b;
}
table.ann-matrix .th-name, .ann-matrix .th-name{text-align:center;min-width:10rem;font-weight:800;}
/* 客户名列 */
table.ann-matrix .td-name, .ann-matrix .td-name{
  text-align:left;font-weight:600;color:#0f172a;font-size:1.125rem;
  white-space:normal;line-height:1.35;vertical-align:middle;
}
table.ann-matrix .td-name .row-num, .ann-matrix .td-name .row-num{
  display:inline-flex;width:1.75rem;height:1.75rem;align-items:center;justify-content:center;
  font-size:1rem;font-weight:800;color:#fff;background:#94a3b8;
  border-radius:0.25rem;margin-right:0.5rem;flex-shrink:0;
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
/* 悬停加深（仅普通格） */
table.ann-matrix tbody tr.row-data:hover td.cb:not(.is-total)::before{ filter:brightness(0.85) saturate(1.15); }
table.ann-matrix tbody tr:nth-child(even) td, .ann-matrix tbody tr:nth-child(even) td{
  background:#fafbfc;
}
/* 合计行 — 边框统一 0.125rem */
table.ann-matrix tr.row-total td,
.ann-matrix tr.row-total td{
  border-top:0.125rem solid #1e40af!important;
  border-bottom:0.125rem solid #1e40af!important;
}
table.ann-matrix tr.row-total td.cb.is-total,
.ann-matrix tr.row-total td.cb.is-total{
  border-top:0.125rem solid #1e40af!important;
  border-bottom:0.125rem solid #1e40af!important;
  border-left:1px solid #cbd5e1!important;
  border-right:1px solid #cbd5e1!important;
}
table.ann-matrix tr.row-total td:not(.cb),
.ann-matrix tr.row-total td:not(.cb){
  background:#dbeafe;font-weight:700;color:#1e3a8a;font-size:0.875rem;
  border:1px solid #cbd5e1!important;
  border-top:0.125rem solid #1e40af!important;
  border-bottom:0.125rem solid #1e40af!important;
}
/* 合计行第一格（客户名列）加大字号 */
table.ann-matrix .row-total td.td-name,
.ann-matrix .row-total td.td-name{
  font-size:0.9375rem;font-weight:800;letter-spacing:0.02em;
}
/* 折叠行 — 默认隐藏 */
tr.row-hidden{display:none;}
/* 查看全部按钮 */
.toggle-all-btn{
  padding:0.375rem 1.25rem;border:1px solid #93c5fd;border-radius:0.375rem;
  background:#eff6ff;color:#1d4ed8;font-size:0.8125rem;font-weight:600;
  cursor:pointer;transition:all .2s;
}
.toggle-all-btn:hover{background:#dbeafe;border-color:#3b82f6;}
.toggle-all-btn.expanded{background:#1d4ed8;color:#fff;border-color:#1d4ed8;}
table.ann-matrix .td-total, .ann-matrix .td-total{font-weight:700;}
/* 单元格主次层次（紧凑） */
.cell-main{font-size:0.8125rem;font-weight:700;color:#0f172a;line-height:1.2;}
.cell-sub{font-size:0.625rem;color:var(--text-muted);margin-top:1px;line-height:1.2;}
/* ══════════ 格子背景填充（CSS类优化版）══════════ */
td.cb{
  position:relative;padding:0.4375rem 0.5rem;overflow:hidden;
  border:1px solid #cbd5e1;background:#f8fafc;vertical-align:middle;
}
/* 填充条（::before伪元素替代fill-bg div） */
td.cb::before{
  content:"";position:absolute;top:0;left:0;bottom:0;
  width:var(--pct,0%);z-index:0;transition:width .3s;
}
/* 填充色 — 用CSS类替代--fill变量 */
td.cb.fg::before{background:#22c55e;}
td.cb.fo::before{background:#fb923c;}
td.cb.fl::before{background:#fdba74;}
td.cb.fy::before{background:#f1f5f9;}
/* 0%不显示填充 */
td.cb.is-empty::before{display:none;}
/* 表格整体网格 */
table.ann-matrix{border-collapse:collapse;border:1px solid #cbd5e1;}
table.ann-matrix thead th{border:1px solid #1e293b;}
table.ann-matrix td{border:1px solid #cbd5e1;}
/* 内容层 */
td.cb .ct{position:relative;z-index:1;display:flex;align-items:center;justify-content:space-between;gap:0.25rem;height:100%;}
td.cb .ct .cp{font-size:1.125rem;line-height:1;font-weight:800;letter-spacing:-0.5px;color:#0f172a;text-shadow:0 0 0.3125rem rgba(255,255,255,0.95),0 0 0.625rem rgba(255,255,255,0.85),0 0.125rem 0.25rem rgba(255,255,255,0.9);flex-shrink:0;}
td.cb .ct .cm{display:flex;flex-direction:column;align-items:flex-end;font-size:1rem;line-height:1.2;font-weight:700;color:#0f172a;text-align:right;flex:1;min-width:0;overflow:hidden;}
td.cb .ct .cm .ca{color:#0f172a;font-weight:800;}
td.cb .ct .cm .ctv{color:#64748b;font-size:0.9375rem;margin-top:1px;font-weight:500;}
td.cb .ct .cp.up{color:#dc2626;}
td.cb .ct .cp.down{color:#16a34a;}
td.cb .ct .cp.achieved{color:#16a34a;}
td.cb .ct .cp.low{color:#b45309;}
/* 合计列 */
td.cb.is-total{background:transparent!important;border:1px solid #cbd5e1!important;}
table.ann-matrix tbody tr:not(.row-total) td.cb.is-total, .ann-matrix tbody tr:not(.row-total) td.cb.is-total{border-top:0.125rem solid #1e40af!important;border-bottom:0.125rem solid #1e40af!important;}
td.cb.is-total .ct{color:#0f172a!important;text-shadow:none!important;}
td.cb.is-total .ct .cm{color:#0f172a!important;font-size:0.8438rem!important;}
td.cb.is-total .ct .cp{color:#0f172a!important;font-size:1.1875rem!important;text-shadow:none!important;}
table.ann-matrix tbody tr:hover td.cb.is-total, table.ann-matrix tbody tr:hover td.cb.is-total .ct, table.ann-matrix tbody tr:hover td.cb.is-total .ct *, table.ann-matrix tbody tr:hover td.cb.is-total .ct .cm, table.ann-matrix tbody tr:hover td.cb.is-total .ct .cp{color:#0f172a!important;background:transparent!important;text-shadow:none!important;}
/* 销售详情抽屉 — 总计行 CSS（覆盖默认 td.cb 黑字为白色，4级色阶保留） */
table.ann-matrix tbody tr.row-grand-total td.cb{background:#0f172a!important;border:1px solid #334155!important;}
table.ann-matrix tbody tr.row-grand-total td.cb .ct{color:#fff!important;text-shadow:none!important;}
table.ann-matrix tbody tr.row-grand-total td.cb .ct .cp{color:#fff!important;text-shadow:none!important;font-size:1.125rem!important;}
table.ann-matrix tbody tr.row-grand-total td.cb .ct .cm{color:#fff!important;text-shadow:none!important;}
table.ann-matrix tbody tr.row-grand-total td.cb .ct .cm .ca{color:#fff!important;}
table.ann-matrix tbody tr.row-grand-total td.cb .ct .cm .ctv{color:#cbd5e1!important;}
table.ann-matrix tbody tr.row-grand-total td.cb.fg::before{background:#22c55e!important;}
table.ann-matrix tbody tr.row-grand-total td.cb.fo::before{background:#fb923c!important;}
table.ann-matrix tbody tr.row-grand-total td.cb.fl::before{background:#fdba74!important;}
table.ann-matrix tbody tr.row-grand-total td.cb.fy::before{background:#ef4444!important;}
table.ann-matrix tbody tr.row-grand-total td.cb.is-total{background:#1e40af!important;border:0.125rem solid #60a5fa!important;}
table.ann-matrix tbody tr.row-grand-total td.cb.is-total .ct{color:#fff!important;}
table.ann-matrix tbody tr.row-grand-total td.cb.is-total .ct .cp{color:#fff!important;font-size:1.25rem!important;}
table.ann-matrix tbody tr.row-grand-total td.cb.is-total .ct .cm{color:#fff!important;}
table.ann-matrix tbody tr.row-grand-total td.cb.is-total .ct .cm .ca{color:#fff!important;}
table.ann-matrix tbody tr.row-grand-total td.cb.is-total .ct .cm .ctv{color:#cbd5e1!important;}
/* 空单元格 */
table.ann-matrix .td-empty, .ann-matrix .td-empty{text-align:center;color:#94a3b8;font-size:0.875rem;padding:0.5rem 0;}

/* ══════════ 事业部同比专用表（双维度清晰对比）══════════ */
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

CSS_RESPONSIVE = """
/* ═══════════════════─ 响应式 ─══════════════════ */
@media(max-width:1200px){
  .kpi-grid.cols-9,.kpi-grid.cols-8,.kpi-grid.cols-6{grid-template-columns:repeat(4,1fr);}
  .cols-3{grid-template-columns:1fr 1fr;}
}
@media(max-width:768px){
  .header{padding:0 0.5rem;}
  .header h1{font-size:1.0625rem;}
  .nav{padding:0 0.375rem;}
  .nav .nav-link{padding:0.3125rem 0.625rem;font-size:0.75rem;}
  .page{padding:0.375rem;}
  .kpi-grid.cols-9,.kpi-grid.cols-8,.kpi-grid.cols-3,.kpi-grid.cols-4,.kpi-grid.cols-6{grid-template-columns:1fr 1fr;}
  .cols-2,.cols-3{grid-template-columns:1fr;}
  .kpi-value{font-size:1.75rem;}
  table{font-size:0.8125rem;}
  .progress-row{grid-template-columns:3.75rem 1fr 4.6875rem 4.0625rem;font-size:0.75rem;}
  .progress-tgt{display:none;}
}
@media(max-width:480px){
  .kpi-grid.cols-9,.kpi-grid.cols-8,.kpi-grid.cols-3,.kpi-grid.cols-4,.kpi-grid.cols-6{grid-template-columns:1fr;}
}

/* ═══════════════════─ 窄窗口收口（2026-10-10，针对 ~1024/1093 逻辑宽的笔记本）═══════════════════
   这两个断点解决"窗口一变小就乱"的剩余两处：
     · Hero 一行动态换行 → 变成"收入指标｜环 / 收入实际·回款实际 / 环｜回款指标"的对称三行
     · 矩阵格内横排（65% 45,023/68,867）在窄格子里会互相压 → 改成上下两行
   ══════════════════════════════════════════════════ */
@media(max-width:1220px){
  /* ① Hero：显式三行网格，避免自动换行把「回款指标」挤到角落 */
  .hero-rings{display:grid;grid-template-columns:1fr auto;gap:0.5rem 1rem;align-items:center;}
  .hero-rings .hr-side.inc-side{grid-column:1;grid-row:1;}
  .hero-rings .hr-side-ring.inc-side-ring{grid-column:2;grid-row:1;justify-self:end;padding:0;}
  .hero-rings .hr-center-box{
    grid-column:1 / -1;grid-row:2;min-width:0;padding:0.5rem 0;
    border-left:none;border-right:none;
    border-top:1px dashed rgba(255,255,255,0.2);border-bottom:1px dashed rgba(255,255,255,0.2);
  }
  .hero-rings .hr-side-ring.pay-side-ring{grid-column:1;grid-row:3;justify-self:start;padding:0;}
  .hero-rings .hr-side.pay-side{grid-column:2;grid-row:3;}
  .hero-rings .hr-cs-val{font-size:1.75rem;}

  /* ② 矩阵格内改上下两行（百分比在上、实际/目标在下），窄列也不会互压 */
  table.ann-matrix td.cb .ct, .ann-matrix td.cb .ct{
    flex-direction:column;align-items:flex-end;justify-content:center;gap:0.0625rem;
  }
  table.ann-matrix td.cb .ct .cm, .ann-matrix td.cb .ct .cm{align-items:flex-end;}
  table.ann-matrix .th-name, .ann-matrix .th-name{width:22%;}
  table.ann-matrix thead th, .ann-matrix thead th{padding:0.5rem 0.25rem !important;}
}
"""

CSS_ANIMATIONS = """
/* ══════════════════════════════════════════════════════
   动画系统 — Apple 风格
   - 缓动统一走 :root 变量（--ease / --ease-out / --ease-spring）
   - 时长规范: 快150ms / 常250ms / 慢400ms
   - 支持 prefers-reduced-motion 减少动画
   ══════════════════════════════════════════════════════ */

/* 1. 页面切换过渡 — 交叉淡入淡出（2026-10-10 二次重做）
   为什么放弃横向推入：本项目每页都是"超宽密集表 + 深色大卡"，横向推入会出现
   ① 两页并排叠着 → 眼晕；② 两个整页大图层同时位移/合成 → 掉帧卡顿。
   现在的做法（最快也最稳）：
     · 旧页只做 120ms 淡出，绝对定位让它脱离文档流（不参与布局、不推动新页）
     · 新页 220ms 淡入 + 6px 上浮（只有一点点位移，不横向移动、不叠两页并排）
     · 全程只动 opacity/transform，不触发重排；页面切换后立即只剩一页在 DOM 里
   注意：位移只在动画期间存在（animation 默认 fill-mode:none），动画结束即清除 transform，
   否则 .page 会成为 position:fixed 弹窗的 containing block 导致弹窗定位错位。 */
@keyframes pageIn  { from { opacity: 0.75; transform: translateY(0.375rem); }
                     to   { opacity: 1; transform: none; } }
/* 旧页：先原样保持 ~30%，再快速淡出 —— 缩短"两页各半透明"的发灰窗口 */
@keyframes pageOut { 0% { opacity: 1; } 30% { opacity: 1; } 100% { opacity: 0; } }
/* 新页：轻轻上浮（在旧页遮罩下面进行，露出时已经在位）
   时长 220ms（2026-10-10 二轮调优：原 260→220，整段过渡缩到 ~250ms 内，手感更脆） */
.page.active { animation: pageIn 0.22s var(--ease-out); }
/* 旧页：变成不透明遮罩盖在最上层淡出 —— 新页就在下面被"逐渐揭开"，
   旧页→新页之间没有任何空白帧（此前是"淡出→换内容→淡入"，中间那段全白就是白屏来源）。
   背景用页面底色，避免两页互相透出造成叠影。
   will-change:opacity：让这张"盖住整页的大图层"在动画期间由合成器处理，
   否则每帧都要把整页大表格重新栅格化一遍（这就是切换时掉帧的主因）。 */
.page.active.page-leaving {
  position: absolute; inset: 0; z-index: 2; display: block;
  pointer-events: none; background: var(--bg-alt);
  will-change: opacity; backface-visibility: hidden;
  animation: pageOut 0.24s var(--ease-in-out) forwards;
}
/* 页内区块逐个浮现（"逐渐加载"）：0.24s + 最多错峰 135ms（只给前几个顶层块）。
   ★ 起点是 opacity 0.45 而不是 0：错峰等待期间区块仍可见，
     否则"旧页已淡出 + 还没轮到的区块全透明"会在中间出现一片空白。
   ★ 只给前 4 块（js_vars.js 控制）：被动画的区块每帧都要重绘，大表格越多越卡。 */
@keyframes blockIn { from { opacity: 0.45; transform: translateY(0.375rem); }
                     to   { opacity: 1; transform: none; } }
.page > .anim-block { animation: blockIn 0.24s var(--ease-out) backwards; }

/* 2. KPI卡片交错入场 — fadeUp（位移从 1.5rem 降为 1rem，更克制） */
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(1rem); }
  to { opacity: 1; transform: translateY(0); }
}
/* fill-mode 用 backwards：动画期间显示 from(opacity:0)，结束后回到自然状态 opacity:1。
   both 在 reduce-motion/动画不触发时会永久停在 opacity:0 导致 KPI 卡片消失。 */
.anim-fade-up { animation: fadeUp var(--dur-slow) var(--ease-out) backwards; }

/* 3. 进度条填充动画（EaseOutQuint，快速开始慢速结束） */
.mini-rate .bar-fill { transition: width .5s var(--ease-out); }
.annual-hero-fill { transition: width .7s var(--ease-out); }

/* 4. Tab淡入切换 */
@keyframes tabIn { from { opacity: 0; } to { opacity: 1; } }
.tab-panel.active { animation: tabIn var(--dur-fast) var(--ease-in-out); }

/* 5. 通用交互过渡（按钮/卡片 hover） */
button, .td-name-clickable, .kpi, .mag-btn, .toggle-all-btn {
  transition: opacity var(--dur-fast) var(--ease),
              transform var(--dur-fast) var(--ease),
              box-shadow var(--dur-fast) var(--ease),
              background-color var(--dur-fast) var(--ease);
}

/* 6. 尊重系统"减少动态效果"偏好 — 关闭所有位移动画 */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}

/* 5. 页面容器预留动画空间
   注意：不要给 .page 加 transform/filter/will-change，否则会成为
   position:fixed 弹窗的 containing block，导致弹窗定位错位（相对容器而非视口）。 */
"""

GLOBAL_CSS = CSS_CORE + CSS_COMPONENTS + CSS_RESPONSIVE + CSS_ANIMATIONS