# Author: naohua168 <bai_bai168@qq.com>
"""卡片容器、网格、迷你数据条、排名徽章、行高亮 —— CSS 片段 `cards`

由 processors/static/css_vars.py 拆分而来，内容与拆分前逐字节一致；
拼接顺序见 processors/static/css/__init__.py，改动内容请只在本文件里追加。
"""

CSS = r"""/* ═══════════════════─ 卡片容器 ─══════════════════ */
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

"""
