# Author: naohua168 <bai_bai168@qq.com>
"""数据总览页专属（毛玻璃卡片 + 飞入动画） —— CSS 片段 `overview`

由 processors/static/css_vars.py 拆分而来，内容与拆分前逐字节一致；
拼接顺序见 processors/static/css/__init__.py，改动内容请只在本文件里追加。
"""

CSS = r"""
/* ═══════════════════════════════════════════════════════════════
   数据总览页 — 毛玻璃卡片 + 飞入动画
   ═══════════════════════════════════════════════════════════════ */

/* Overview 页背景：统一浅色，与其他页面保持一致 */
/* 注意：这里不要再写 position—— id 选择器会压过 .page-leaving 的绝对定位，
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

/* ═══════════════════════════════════════════════════════════════
   部门完成度矩阵 → 客户明细弹窗
   冻结表头 / 首列 + 合计行吸底；部门主题色由 JS 写入 --dd-accent
   ═══════════════════════════════════════════════════════════════ */

/* 矩阵行可点：整行 hover + 键盘可达 */
.yoy-dept-table tr.dept-row{cursor:pointer;transition:background 0.15s;}
.yoy-dept-table tr.dept-row:hover td{background:rgba(59,130,246,0.10);}
.yoy-dept-table tr.dept-row:hover .td-name span{text-decoration:underline;}
.yoy-dept-table tr.dept-row:focus-visible{outline:2px solid #2563eb;outline-offset:-2px;}

/* 弹窗容器：放在 page 内，用 `.page#overview > .dept-modal` 压过 `.page#overview > *{position:relative}` */
.page#overview > .dept-modal{
  position:fixed;inset:0;display:none;align-items:center;justify-content:center;z-index:9000;
  --dd-accent:#2563eb;
}
.page#overview > .dept-modal.open{display:flex;}
.dept-modal-mask{position:absolute;inset:0;background:rgba(15,23,42,0.42);
  backdrop-filter:blur(3px);opacity:0;transition:opacity 0.18s ease;}
.page#overview > .dept-modal.open .dept-modal-mask{opacity:1;}

.dept-modal-panel{
  position:relative;width:min(1120px,94vw);max-height:88vh;display:flex;flex-direction:column;
  overflow:hidden;background:#fff;border:1px solid rgba(15,23,42,0.08);border-radius:1rem;
  box-shadow:0 1px 2px rgba(15,23,42,0.06),0 24px 64px rgba(15,23,42,0.28);
  opacity:0;transform:translateY(10px) scale(0.985);
  transition:opacity 0.22s ease,transform 0.28s cubic-bezier(0.16,1,0.3,1);
}
.page#overview > .dept-modal.open .dept-modal-panel{opacity:1;transform:none;}

/* 顶部部门色条 */
.dept-modal-accent{flex:0 0 auto;height:4px;
  background:linear-gradient(90deg,var(--dd-accent) 0%,var(--dd-accent) 55%,rgba(203,213,225,0.5) 100%);}

/* ── 头部 ── */
.dept-modal-hd{display:flex;align-items:center;justify-content:space-between;gap:0.75rem;
  padding:0.8rem 1.1rem 0.55rem;}
.dept-modal-title{display:flex;align-items:baseline;flex-wrap:wrap;gap:0.4rem;
  font-size:1.0625rem;font-weight:800;letter-spacing:-0.01em;color:#0f172a;}
.dept-modal-title .dd-dept{display:inline-flex;align-items:center;gap:0.35rem;}
.dept-modal-title .dd-dot{width:0.5rem;height:0.5rem;border-radius:50%;
  background:var(--dd-accent);box-shadow:0 0 0 3px rgba(37,99,235,0.12);}
.dept-modal-title .dd-sub{font-size:0.75rem;font-weight:500;color:#64748b;}
.dept-modal-x{display:grid;place-items:center;flex:0 0 auto;width:2rem;height:2rem;
  border:none;border-radius:50%;background:#f1f5f9;color:#475569;cursor:pointer;
  transition:background 0.15s,color 0.15s,transform 0.15s;}
.dept-modal-x:hover{background:#e2e8f0;color:#0f172a;}
.dept-modal-x:active{transform:scale(0.94);}
.dept-modal-x:focus-visible{outline:2px solid #2563eb;outline-offset:2px;}

/* ── KPI 条（收入 / 回款各一行）── */
.dept-kpi{display:flex;flex-direction:column;gap:0.35rem;padding:0.55rem 1.1rem 0.75rem;
  background:linear-gradient(180deg,#f8fafc 0%,#ffffff 100%);border-bottom:1px solid #eef2f7;}
.dk-row{display:grid;grid-template-columns:2.2rem 1fr 1fr 1fr 1fr;align-items:center;gap:0.5rem;
  padding:0.45rem 0.7rem;border:1px solid #eef2f7;border-radius:0.6rem;background:#f8fafc;}
.dk-row.inc{background:linear-gradient(90deg,#f2f8ff,#f8fafc);border-color:#e0edff;}
.dk-row.pay{background:linear-gradient(90deg,#f1fbf6,#f8fafc);border-color:#dcf3e6;}
.dk-tag{font-size:0.6875rem;font-weight:800;text-align:center;letter-spacing:0.02em;}
.dk-row.inc .dk-tag{color:#1d4ed8;}
.dk-row.pay .dk-tag{color:#047857;}
.dk-item{display:flex;flex-direction:column;gap:0.1rem;min-width:0;}
.dk-item i{font-style:normal;font-size:0.6875rem;font-weight:600;color:#64748b;}
.dk-item b{font-size:1.0625rem;font-weight:800;color:#0f172a;font-variant-numeric:tabular-nums;
  letter-spacing:-0.01em;white-space:nowrap;}
.dk-item b.is-gap{color:#dc2626;}
.dk-item b.is-ok{color:#16a34a;}

/* ── 工具条 ── */
.dept-modal-tools{display:flex;align-items:center;gap:0.6rem;padding:0 1.1rem 0.6rem;}
.dd-search{position:relative;display:flex;align-items:center;flex:0 0 15rem;
  border:1px solid #cbd5e1;border-radius:0.5rem;background:#fff;
  transition:border-color 0.15s,box-shadow 0.15s;}
.dd-search:focus-within{border-color:#93c5fd;box-shadow:0 0 0 3px rgba(147,197,253,0.35);}
.dd-search svg{flex:0 0 auto;margin-left:0.5rem;color:#94a3b8;}
.dd-search input{flex:1;min-width:0;border:none;outline:none;background:transparent;
  padding:0.35rem 0.5rem;font-size:0.8125rem;color:#0f172a;}
.dd-unit{font-size:0.6875rem;color:#94a3b8;}
.dept-modal-count{margin-left:auto;font-size:0.75rem;color:#64748b;
  font-variant-numeric:tabular-nums;}

/* ── 表格：冻结表头 + 首列 + 合计吸底 ── */
.dept-modal-body{flex:1;min-height:0;overflow:auto;border-top:1px solid #eef2f7;padding-bottom:0.6rem;}
.dept-detail-table{width:100%;min-width:880px;table-layout:fixed;border-collapse:separate;
  border-spacing:0;font-size:0.8125rem;}
.dept-detail-table col.c-cust{width:27%;}
.dept-detail-table col.c-num{width:12.9%;}
.dept-detail-table col.c-rate{width:10.7%;}

.dept-detail-table thead th{
  position:sticky;top:0;z-index:3;padding:0.45rem 0.55rem;text-align:center;white-space:nowrap;
  font-size:0.75rem;font-weight:700;line-height:1.3;letter-spacing:0.01em;
  background:#0f172a;color:#e2e8f0;
  box-shadow:inset 0 -1px 0 rgba(255,255,255,0.12),0 2px 6px rgba(15,23,42,0.10);
}
.dept-detail-table thead th.th-name{left:0;z-index:4;padding-left:1rem;text-align:left;
  font-size:0.8125rem;}
.dept-detail-table thead th .th-grp{display:block;margin-bottom:1px;
  font-size:0.625rem;font-weight:600;letter-spacing:0.08em;opacity:0.72;}
.dept-detail-table thead th.grp-inc{background:#12305c;color:#dbeafe;}
.dept-detail-table thead th.grp-pay{background:#0d3b33;color:#d1fae5;}

.dept-detail-table tbody td{padding:0.42rem 0.6rem;text-align:right;color:#334155;
  font-variant-numeric:tabular-nums;border-bottom:1px solid #f1f5f9;}
.dept-detail-table tbody tr:nth-child(even) td{background:#fafbfd;}
.dept-detail-table tbody td.dd-cust{
  position:sticky;left:0;z-index:2;text-align:left;padding-left:0.9rem;
  font-weight:600;line-height:1.35;color:#0f172a;background:#fff;
  box-shadow:inset -1px 0 0 #eef2f7;
  white-space:normal;word-break:break-word;   /* 长客户名换行显示，不裁字 */
}
.dept-detail-table tbody tr:nth-child(even) td.dd-cust{background:#fafbfd;}
.dept-detail-table tbody tr:hover td{background:#eff6ff;}
.dept-detail-table tbody tr:hover td.dd-cust{background:#e8f1ff;}

/* 客户名前的「展开子公司」按钮（无子公司时占位对齐） */
.dd-toggle{display:inline-flex;align-items:center;justify-content:center;
  width:1.1rem;height:1.1rem;margin-right:0.35rem;padding:0;vertical-align:-0.15rem;
  border:1px solid #cbd5e1;border-radius:0.25rem;background:#fff;color:#64748b;
  cursor:pointer;transition:background 0.15s,color 0.15s,border-color 0.15s;}
.dd-toggle:hover{background:#eff6ff;border-color:#93c5fd;color:#2563eb;}
.dd-toggle:focus-visible{outline:2px solid #2563eb;outline-offset:1px;}
.dd-toggle svg{transition:transform 0.18s ease;}
.dd-toggle.is-open svg{transform:rotate(90deg);}
.dd-toggle.is-empty{visibility:hidden;border-color:transparent;background:none;}
.dd-name{vertical-align:middle;}
.dd-count{margin-left:0.4rem;font-size:0.625rem;font-weight:600;color:#94a3b8;
  white-space:nowrap;}

/* 子公司子行：默认收起，点 ▸ 展开 */
.dept-detail-table tbody tr.dd-subrow{display:none;}
.dept-detail-table tbody tr.dd-subrow.is-open{display:table-row;}
.dept-detail-table tbody tr.dd-subrow td{background:#f8fafc;color:#475569;
  border-bottom:1px dashed #e8eef6;}
.dept-detail-table tbody tr.dd-subrow:hover td{background:#eef4ff;}
.dept-detail-table tbody tr.dd-subrow td.dd-cust{padding-left:2.1rem;font-weight:500;
  background:#f8fafc;color:#334155;}
.dept-detail-table tbody tr.dd-subrow:hover td.dd-cust{background:#e8f1ff;}
.dd-tree{margin-right:0.35rem;color:#cbd5e1;font-weight:400;}
.dept-detail-table td.dd-strong{font-weight:700;}

/* 完成度：细进度条 + 百分比（比大色块干净，也不吃列宽） */
.dept-detail-table td.dd-rate{padding-right:0.7rem;text-align:right;white-space:nowrap;}
.dept-detail-table td.dd-rate.is-empty{text-align:center;color:#cbd5e1;}
.dd-bar{position:relative;display:inline-block;width:calc(100% - 2.3rem);height:0.375rem;
  vertical-align:middle;border-radius:99px;background:#eef2f7;overflow:hidden;}
.dd-bar > span{display:block;height:100%;border-radius:99px;transition:width 0.3s ease;}
.dd-bar > span.g{background:linear-gradient(90deg,#4ade80,#16a34a);}
.dd-bar > span.o{background:linear-gradient(90deg,#fbbf24,#f59e0b);}
.dd-bar > span.l{background:#fdba74;}
.dd-bar > span.z{background:#cbd5e1;}
.dept-detail-table td.dd-rate b{display:inline-block;min-width:2rem;margin-left:0.35rem;
  text-align:right;font-size:0.75rem;font-weight:800;}
.dept-detail-table td.dd-rate b.g{color:#15803d;}
.dept-detail-table td.dd-rate b.o{color:#b45309;}
.dept-detail-table td.dd-rate b.l{color:#c2410c;}
.dept-detail-table td.dd-rate b.z{color:#64748b;}

/* 合计行：表尾深色（不吸底，避免盖住最后一行客户；总计在顶部 KPI 条里已常驻） */
.dept-detail-table tfoot td{
  padding:0.6rem;text-align:right;font-weight:800;
  color:#f8fafc;background:#0f172a;font-variant-numeric:tabular-nums;
}
.dept-detail-table tfoot td.dd-cust{left:0;z-index:3;text-align:left;padding-left:1rem;
  border-right:1px solid rgba(148,163,184,0.25);}
.dept-detail-table tfoot td.dd-rate b{color:#fff;}
.dept-detail-table tfoot .dd-bar{background:rgba(148,163,184,0.3);}

.dept-detail-table .dd-empty{text-align:center;color:#94a3b8;padding:2rem 0;}

body.dd-lock{overflow:hidden;}

@media (prefers-reduced-motion:reduce){
  .dept-modal-mask,.dept-modal-panel{transition:none;}
}
@media (max-width:1180px){
  .dept-modal-panel{width:96vw;}
  .dd-search{flex:1 1 auto;}
  .dk-row{grid-template-columns:1fr 1fr;}
}
"""
