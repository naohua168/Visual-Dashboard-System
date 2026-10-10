# Author: naohua168 <bai_bai168@qq.com>
"""圆环 Hero（三件套 + 两翼 KPI） —— CSS 片段 `hero`

由 processors/static/css_vars.py 拆分而来，内容与拆分前逐字节一致；
拼接顺序见 processors/static/css/__init__.py，改动内容请只在本文件里追加。
"""

CSS = r"""/* ═══════════════════─ 圆环 Hero ─══════════════════ */
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

"""
