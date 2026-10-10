# Author: naohua168 <bai_bai168@qq.com>
"""顶部标题栏、导航栏、页面容器 —— CSS 片段 `layout`

由 processors/static/css_vars.py 拆分而来，内容与拆分前逐字节一致；
拼接顺序见 processors/static/css/__init__.py，改动内容请只在本文件里追加。
"""

CSS = r"""/* ═══════════════════─ 顶部标题栏 ─══════════════════ */
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
