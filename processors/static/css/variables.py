# Author: naohua168 <bai_bai168@qq.com>
"""全局变量、根字号、页面骨架、滚动条 —— CSS 片段 `variables`

由 processors/static/css_vars.py 拆分而来，内容与拆分前逐字节一致；
拼接顺序见 processors/static/css/__init__.py，改动内容请只在本文件里追加。
"""

CSS = r"""
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

"""
