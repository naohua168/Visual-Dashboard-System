# Author: naohua168 <bai_bai168@qq.com>
"""响应式断点与窄窗口收口 —— CSS 片段 `responsive`

由 processors/static/css_vars.py 拆分而来，内容与拆分前逐字节一致；
拼接顺序见 processors/static/css/__init__.py，改动内容请只在本文件里追加。
"""

CSS = r"""
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
  /* 窄屏（≤1220）：客户列 29%→34%，合计 16%→15%
     这一档部门格本来就走"上下两行"（见上），扛得住变窄；把宽度让给客户列，
     保证「客户名 + ▾N/M家」仍然同一行（实测 1100px 时 29% 会让提示掉到第二行） */
  table.ann-matrix .th-name:not(.th-total), .ann-matrix .th-name:not(.th-total){width:38%;}
  table.ann-matrix .th-name.th-total, .ann-matrix .th-name.th-total{width:15%;}
  /* 「▾N/M家」提示在窄屏收小（选择器加 tbody 提优先级，否则被 matrix.py 同优先级规则盖掉）：
     实测 1100px 时提示会把名字顶到第二行（名字 222px + 提示 78px + 徽标 30px > 可用 294px） */
  table.ann-matrix tbody td.td-name .expand-hint,
  .ann-matrix tbody td.td-name .expand-hint{font-size:0.6875rem;}
  table.ann-matrix thead th, .ann-matrix thead th{padding:0.5rem 0.25rem !important;}
}
"""
