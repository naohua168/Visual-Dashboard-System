# Author: naohua168 <bai_bai168@qq.com>
"""动画系统（页面切换、区块浮现、弹窗、Tab 淡入） —— CSS 片段 `animations`

由 processors/static/css_vars.py 拆分而来，内容与拆分前逐字节一致；
拼接顺序见 processors/static/css/__init__.py，改动内容请只在本文件里追加。
"""

CSS = r"""
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
