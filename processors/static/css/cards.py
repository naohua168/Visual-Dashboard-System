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
.mini-rate{
  display:flex;align-items:center;gap:0.4rem;padding:0.3rem 0.5rem;
  font-size:0.8125rem;border-radius:0.375rem;
  border-bottom:1px solid #f4f7fb;
  transition:background 0.15s ease;
}
.mini-rate:last-child{border-bottom:none;}
.mini-rate:hover{background:#f5f8ff;}
.mini-rate .sales-name{color:#1e293b;}

/* 轨道：细、圆角、内凹一点，不与填充抢眼 */
.mini-rate .bar{
  flex:1;height:0.875rem;position:relative;overflow:hidden;
  min-width:5rem;border-radius:99px;background:#eef2f7;
  box-shadow:inset 0 1px 2px rgba(15,23,42,0.06);
}
.mini-rate .bar-fill{
  height:100%;min-width:0.125rem;border-radius:99px;position:relative;
}
/* 填充：同色系双色渐变，避免大块纯色显平 */
.mini-rate .bar-fill.level-1{background:linear-gradient(90deg,#f87171,#dc2626);}
.mini-rate .bar-fill.level-2{background:linear-gradient(90deg,#fb923c,#ea580c);}
.mini-rate .bar-fill.level-3{background:linear-gradient(90deg,#fbbf24,#d97706);}
.mini-rate .bar-fill.level-4{background:linear-gradient(90deg,#34d399,#16a34a);}

/* 百分比独立成列：不压在色块上，条再短也不会错位/被裁 */
.mini-rate .rate-tag{
  flex:0 0 2.5rem;text-align:right;
  font-size:0.6875rem;font-weight:800;letter-spacing:0.01em;
  font-variant-numeric:tabular-nums;
}
.mini-rate .rate-tag.level-1{color:#dc2626;}
.mini-rate .rate-tag.level-2{color:#ea580c;}
.mini-rate .rate-tag.level-3{color:#b45309;}
.mini-rate .rate-tag.level-4{color:#15803d;}
.mini-rate .rate-tag.is-empty{color:#cbd5e1;font-weight:600;}
/* 兼容旧结构（仍把百分比放在条内的地方） */
.mini-rate .bar-pct{
  position:absolute;right:0.3rem;top:50%;transform:translateY(-50%);
  font-size:0.625rem;font-weight:800;line-height:1;
  color:#fff;pointer-events:none;
  text-shadow:0 0 2px rgba(15,23,42,0.55),0 1px 1px rgba(15,23,42,0.35);
}
.mini-rate .val{
  min-width:4.375rem;text-align:right;font-weight:800;
  font-variant-numeric:tabular-nums;color:#0f172a;
}
.mini-rate .val.neg{color:#dc2626;}
.mini-rate .tgt{
  margin-left:-0.3rem;min-width:3.4rem;text-align:left;
  font-weight:600;color:#94a3b8;font-variant-numeric:tabular-nums;
}
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
