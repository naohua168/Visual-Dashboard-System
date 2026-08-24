"""数据总览页专属 CSS — 从 base.py 拆分"""
GLOBAL_OV_CSS = """
/* ═══════════════════════════════════════════════════════════════
   数据总览页 — 毛玻璃卡片 + 飞入动画
   ═══════════════════════════════════════════════════════════════ */

/* Overview 页背景：统一浅色，与其他页面保持一致 */
.page#overview{
  background:transparent;
  padding:14px;
  position:relative;
  display:none;
  flex-direction:column;
  overflow-y:auto;
  min-height:calc(100vh - 82px);
}
.page.active#overview{
  display:flex;
}
.page#overview > *{position:relative;z-index:1;}

/* ov-container 填满 */
.page#overview .ov-container{flex:1;display:flex;flex-direction:column;gap:14px;}

/* 飞入动画（Apple 风格：位移更克制，缓动 EaseOut） */
@keyframes flyInLeft{0%{opacity:0;transform:translateX(-24px);}100%{opacity:1;transform:translateX(0);}}
@keyframes flyInRight{0%{opacity:0;transform:translateX(24px);}100%{opacity:1;transform:translateX(0);}}
@keyframes flyInUp{0%{opacity:0;transform:translateY(16px);}100%{opacity:1;transform:translateY(0);}}

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
.ov-card.ov-card-left{animation:flyInLeft .5s var(--ease-out) both;}
.ov-card.ov-card-right{animation:flyInRight .5s var(--ease-out) both;}

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
  padding:12px 16px;animation:flyInUp .4s var(--ease-out) both;
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
