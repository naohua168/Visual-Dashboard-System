# Author: naohua168 <bai_bai168@qq.com>
"""客户×部门矩阵表与格内填充（含销售抽屉总计行） —— CSS 片段 `matrix`

由 processors/static/css_vars.py 拆分而来，内容与拆分前逐字节一致；
拼接顺序见 processors/static/css/__init__.py，改动内容请只在本文件里追加。
"""

CSS = r"""/* ═══════════════════─ 矩阵表（ann-matrix 紧凑布局） ───────── */
table.ann-matrix, .table-wrap table.ann-matrix, .ann-matrix{
  width:100%;border-collapse:separate;border-spacing:0;font-size:1.5rem;background:#fff;
  border:1px solid #e2e5ed;
}
/* 盒式列宽（2026-10-10）：列宽不再由内容撑破容器。
   客户名列固定 28rem（≈25 个汉字，名字不到 25 字不换行；超过 25 字由 wrap_name 插 <br> 强制折行）；
   合计列固定 12rem（要放得下"16,919/12,000"）；4 个部门列均分剩余宽度。
   最小宽度 84rem：保证部门格也放得下"11,545/40,867"+百分比（之前按百分比给列会把金额挤掉一截）；
   窗口不够宽时在 .table-wrap 内横滑，数据一个不少 */
table.ann-matrix, .ann-matrix, table.yoy-dept-table, .yoy-dept-table{table-layout:fixed;}
table.ann-matrix, .ann-matrix{min-width:84rem;}
table.ann-matrix .th-name, .ann-matrix .th-name{width:20%;min-width:0;}
/* 客户名列（第一列）固定 28rem；合计表头带 .th-total，单独 12rem */
table.ann-matrix .th-name:not(.th-total), .ann-matrix .th-name:not(.th-total){width:28rem;}
table.ann-matrix .th-name.th-total, .ann-matrix .th-name.th-total{width:12rem;}
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
/* 客户名列（2026-10-10 二轮：行内更宽松，名字单行显示）
   行高 1.35→1.5、内边距 10/12px→12/14px，客户行不再拥挤；
   只有 wrap_name() 在 25 字处插的 <br> 才会折行（普通换行留给极窄窗口兜底） */
table.ann-matrix .td-name, .ann-matrix .td-name{
  text-align:left;font-weight:600;color:#0f172a;font-size:1.125rem;
  white-space:normal;line-height:1.5;vertical-align:middle;
  padding:0.75rem 0.875rem;
}
table.ann-matrix .td-name .row-num, .ann-matrix .td-name .row-num{
  display:inline-flex;width:1.75rem;height:1.75rem;align-items:center;justify-content:center;
  font-size:1rem;font-weight:800;color:#fff;background:#94a3b8;
  border-radius:0.25rem;margin-right:0.5rem;flex-shrink:0;
}
/* 「▾ N/M家」展开提示：始终与客户名同一行（不再被挤到第二行） */
table.ann-matrix .td-name .expand-hint, .ann-matrix .td-name .expand-hint{
  white-space:nowrap;font-size:0.9375rem;font-weight:600;color:#64748b;
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
  /* 上下内边距 7px→9px：客户行更透气（2026-10-10 二轮） */
  position:relative;padding:0.5625rem 0.5rem;overflow:hidden;
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

"""
