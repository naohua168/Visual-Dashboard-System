# Author: naohua168 <bai_bai168@qq.com>
"""数据总览页专属 CSS — 从 base.py 拆分"""
GLOBAL_OV_CSS = """
/* ═══════════════════════════════════════════════════════════════
   数据总览页 — 毛玻璃卡片 + 飞入动画
   ═══════════════════════════════════════════════════════════════ */

/* Overview 页背景：统一浅色，与其他页面保持一致 */
/* 注意：这里不要再写 position（2026-10-10）—— id 选择器会压过 .page-leaving 的绝对定位，
   导致从总览页切走时旧页留在文档流里、与新页上下排成两栏。定位统一由基础 .page 负责。 */
.page#overview{
  background:transparent;
  padding:0.875rem;
  display:none;
  flex-direction:column;
  overflow-y:auto;
  overflow-x:hidden;   /* 同 .page：裁掉离屏弹窗撑出的横向滚动条 */
  /* 高度交给骨架 flex（原 min-height:calc(100vh - header) 会随 header 变化裁到底部） */
}
.page.active#overview{
  display:flex;
}
.page#overview > *{position:relative;z-index:1;}

/* ov-container 填满 */
.page#overview .ov-container{flex:1;display:flex;flex-direction:column;gap:0.875rem;}

/* 飞入动画（Apple 风格：位移更克制，缓动 EaseOut） */
@keyframes flyInLeft{0%{opacity:0;transform:translateX(-1.5rem);}100%{opacity:1;transform:translateX(0);}}
@keyframes flyInRight{0%{opacity:0;transform:translateX(1.5rem);}100%{opacity:1;transform:translateX(0);}}
@keyframes flyInUp{0%{opacity:0;transform:translateY(1rem);}100%{opacity:1;transform:translateY(0);}}

.ov-cards{display:grid;grid-template-columns:1fr 1fr;gap:1.125rem;flex:1;min-height:0;}
.ov-card{
  background:linear-gradient(135deg,rgba(255,255,255,0.12) 0%,rgba(255,255,255,0.05) 100%);
  backdrop-filter:blur(1.75rem) saturate(150%);
  -webkit-backdrop-filter:blur(1.75rem) saturate(150%);
  border:1px solid rgba(255,255,255,0.22);
  border-radius:1.125rem;
  padding:1.25rem 1.375rem;
  box-shadow:0 8px 36px rgba(0,0,0,0.3),inset 0 1px 0 rgba(255,255,255,0.12);
  color:#ffffff;
  display:flex;flex-direction:column;gap:0.875rem;
  min-height:100%;
}
.ov-card.ov-card-left{animation:flyInLeft .5s var(--ease-out) both;}
.ov-card.ov-card-right{animation:flyInRight .5s var(--ease-out) both;}

/* 卡片头部：标题 + YoY */
.ov-card-head{display:flex;align-items:center;justify-content:space-between;gap:0.75rem;}
.ov-card-title{display:flex;align-items:center;gap:0.5rem;font-size:1.125rem;font-weight:800;color:#fbbf24;letter-spacing:0.04em;}
.ov-card-title svg{opacity:0.85;}
.ov-yoy-period{font-size:0.6875rem;color:rgba(255,255,255,0.6);font-weight:500;margin-left:0.5rem;}

/* 关键数字区（4列） */
.ov-keynums{display:grid;grid-template-columns:repeat(4,1fr);gap:0.625rem;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);border-radius:0.625rem;padding:0.625rem 0.75rem;}
.ov-kn{display:flex;flex-direction:column;gap:0.1875rem;}
.ov-kn-label{font-size:0.6875rem;color:rgba(255,255,255,0.65);font-weight:500;}
.ov-kn-val{font-size:1.125rem;font-weight:800;color:#fbbf24;letter-spacing:-0.01em;font-variant-numeric:tabular-nums;}
.ov-kn-val.is-gap{color:#fb923c;}
.ov-kn-val.is-yoy-up{color:#86efac;}
.ov-kn-val.is-yoy-dn{color:#fca5a5;}

/* 卡片头部 */
.ov-card-period{font-size:0.6875rem;color:rgba(255,255,255,0.5);font-weight:500;}

/* 4 部门 mini-card 网格（4 列） */
.ov-dept-cards{display:grid;grid-template-columns:repeat(4,1fr);gap:0.625rem;}
.ov-dc{
  background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);
  border-radius:0.625rem;padding:0.625rem 0.5rem;display:flex;flex-direction:column;gap:0.375rem;align-items:center;
  transition:background 0.2s;
}
.ov-dc:hover{background:rgba(255,255,255,0.12);}
.ov-dc-name{font-size:0.75rem;font-weight:700;text-align:center;}
.ov-dc-val{font-size:1.125rem;font-weight:800;color:#fbbf24;font-variant-numeric:tabular-nums;text-align:center;letter-spacing:-0.01em;}
.ov-dc-val span{font-size:0.6875rem;font-weight:500;opacity:0.7;margin-left:0.125rem;}
.ov-dc-bar{height:0.375rem;width:100%;background:rgba(255,255,255,0.1);border-radius:0.1875rem;overflow:hidden;}
.ov-dc-bar-fill{height:100%;background:linear-gradient(90deg,#3b82f6,#22c55e);border-radius:0.1875rem;transition:width 0.6s ease;}
.ov-dc-pct{font-size:0.8125rem;font-weight:700;color:#86efac;font-variant-numeric:tabular-nums;}

/* 大圆环 — 居中，撑满剩余空间 */
.ov-big-ring{position:relative;width:8.125rem;height:8.125rem;flex-shrink:0;margin:0 auto;}
.ov-big-ring svg{width:100%;height:100%;transform:rotate(-90deg);}
.ov-big-ring .ring-track{fill:none;stroke:rgba(255,255,255,0.15);stroke-width:10;}
.ov-big-ring .ring-prog{fill:none;stroke-width:10;stroke-linecap:round;transition:stroke-dasharray 1s ease;}
.ov-big-ring-text{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;}
.ov-big-ring-pct{font-size:1.625rem;font-weight:900;color:#fbbf24;font-variant-numeric:tabular-nums;line-height:1;}
.ov-big-ring-label{font-size:0.625rem;color:rgba(255,255,255,0.7);font-weight:600;margin-top:0.125rem;}

/* 移除旧 3 列布局 */
.ov-card-middle,.ov-cm-depts-left,.ov-cm-depts-right,.ov-cm-ring-center,
.ov-cm-mini,.ov-card-subtitle,.ov-depts,.ov-dept,.ov-dept-name,
.ov-dept-bar,.ov-dept-bar-fill,.ov-dept-amount,.ov-dept-pct,
.ov-ring-center-wrap{display:none !important;}

/* 销售排行 Top 5 */
.ov-rank{display:flex;flex-direction:column;gap:0.375rem;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:0.625rem;padding:0.5rem 0.625rem;}
.ov-rank-title{font-size:0.75rem;color:rgba(255,255,255,0.7);font-weight:700;margin-bottom:0.25rem;}
.ov-rank-row{display:grid;grid-template-columns:1.5rem 1fr 4.375rem 2.5rem;align-items:center;gap:0.5rem;font-size:0.75rem;}
.ov-rank-num{display:inline-flex;width:1.25rem;height:1.25rem;align-items:center;justify-content:center;border-radius:0.25rem;font-size:0.625rem;font-weight:800;color:#fff;background:#94a3b8;}
.ov-rank-num.t1{background:#fbbf24;color:#0f172a;}
.ov-rank-num.t2{background:#94a3b8;}
.ov-rank-num.t3{background:#a16207;}
.ov-rank-name{color:#e0e7ff;font-weight:600;}
.ov-rank-bar{height:0.375rem;background:rgba(255,255,255,0.1);border-radius:0.1875rem;overflow:hidden;}
.ov-rank-bar-fill{height:100%;background:linear-gradient(90deg,#fbbf24,#f59e0b);border-radius:0.1875rem;transition:width 0.6s ease;}
.ov-rank-amt{color:#fbbf24;font-weight:700;text-align:right;font-variant-numeric:tabular-nums;}

/* 区块标题 */
.ov-section-title{font-size:0.75rem;color:rgba(255,255,255,0.7);font-weight:700;letter-spacing:0.04em;margin-bottom:0.375rem;text-align:center;}

/* 数据总览：KPI 概览（顶部摘要） */
.ov-kpi-bar{
  display:grid;grid-template-columns:repeat(6,1fr);gap:0.625rem;
  background:rgba(255,255,255,0.06);backdrop-filter:blur(1rem);
  border:1px solid rgba(255,255,255,0.15);border-radius:0.75rem;
  padding:0.75rem 1rem;animation:flyInUp .4s var(--ease-out) both;
}
.ov-kpi{display:flex;flex-direction:column;gap:0.1875rem;}
.ov-kpi-label{font-size:0.6875rem;color:rgba(255,255,255,0.7);font-weight:500;}
.ov-kpi-val{font-size:1.25rem;font-weight:800;color:#fbbf24;font-variant-numeric:tabular-nums;}

/* 移动端适配 */
@media (max-width:1180px){
  .ov-cards{grid-template-columns:1fr;}
  .ov-kpi-bar{grid-template-columns:repeat(3,1fr);}
  .ov-keynums{grid-template-columns:repeat(2,1fr);}
}
"""