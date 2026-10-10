# Author: naohua168 <bai_bai168@qq.com>
"""同比色块、对比单元格、趋势箭头、周期 chip、大对比卡 —— CSS 片段 `yoy`

由 processors/static/css_vars.py 拆分而来，内容与拆分前逐字节一致；
拼接顺序见 processors/static/css/__init__.py，改动内容请只在本文件里追加。
"""

CSS = r"""/* ═══════════════════─ 同比色块 ─══════════════════ */
.yoy-up{
  display:inline-block;padding:0.125rem 0.5rem;font-weight:700;
  font-variant-numeric:tabular-nums;font-size:0.6875rem;border-radius:0.25rem;
  background:#fee2e2;color:#dc2626;
}
.yoy-down{
  display:inline-block;padding:0.125rem 0.5rem;font-weight:700;
  font-variant-numeric:tabular-nums;font-size:0.6875rem;border-radius:0.25rem;
  background:#dcfce7;color:#16a34a;
}
.yoy-neutral{color:var(--text-muted);font-weight:600;}

/* ═══════════════════─ 同比对比单元格 ──────────────── */
.yoy-cell{
  padding:0.375rem 0.5rem;min-width:8.75rem;vertical-align:top;
}
.yoy-amount{font-size:0.8125rem;font-weight:700;color:var(--text);font-variant-numeric:tabular-nums;}
.yoy-bars{
  display:flex;flex-direction:column;gap:0.125rem;margin:0.25rem 0 0.125rem;
  position:relative;
}
.yoy-bar{height:0.3125rem;border-radius:0.1875rem;min-width:0.125rem;transition:width 0.3s ease;}
.yoy-bar.cur{background:var(--accent);position:relative;}
.yoy-bar.prev{background:#cbd5e1;}
.yoy-pct{
  display:inline-block;font-size:0.6875rem;font-weight:800;font-variant-numeric:tabular-nums;
  padding:1px 0.375rem;border-radius:0.1875rem;margin-top:0.125rem;
}
.yoy-pct.up{background:#fee2e2;color:#dc2626;}
.yoy-pct.down{background:#dcfce7;color:#16a34a;}
.yoy-pct.flat{background:#f1f5f9;color:#64748b;}
.yoy-prev-amt{font-size:0.625rem;color:var(--text-muted);font-variant-numeric:tabular-nums;margin-top:1px;}

/* ═══════════════════─ 同比趋势箭头 ─────────────── */
.yoy-arrow{
  display:inline-flex;align-items:center;justify-content:center;
  width:1.125rem;height:1.125rem;font-size:0.6875rem;font-weight:800;
  border-radius:0.25rem;margin-right:0.125rem;
}
.yoy-arrow.up{background:#fee2e2;color:#dc2626;}
.yoy-arrow.down{background:#dcfce7;color:#16a34a;}
.yoy-arrow.flat{background:#f1f5f9;color:#64748b;}

/* ═══════════════════─ 同比周期 chip ───────────── */
.period-chip{
  display:flex;align-items:center;gap:0.5rem;margin-bottom:0.375rem;padding:0.375rem 0.75rem;
  background:#f1f5f9;border-radius:0.25rem;border-left:0.1875rem solid var(--accent);
}
.period-tag{
  display:inline-block;background:var(--accent);color:#fff;
  padding:0.125rem 0.625rem;font-size:0.6875rem;font-weight:700;border-radius:0.1875rem;
  letter-spacing:0.04em;
}
.period-text{font-size:0.75rem;color:var(--text-secondary);font-weight:500;}

/* ═══════════════════─ 同比大对比卡（2 卡，深色稳重风） ───────────── */
.yoy-big-card{
  position:relative;
  padding:1.25rem 1.5rem;
  border-radius:0.625rem;
  background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%);
  color:#fff;
  display:grid;grid-template-columns:1fr 1.4fr;gap:1.5rem;align-items:center;
  box-shadow:0 4px 16px rgba(15,23,42,0.25);
  overflow:hidden;
}
.yoy-big-card::before{
  content:"";position:absolute;left:0;top:0;bottom:0;width:0.25rem;background:var(--accent-color,#dc2626);
}
.yoy-big-card.up{--accent-color:#dc2626;}
.yoy-big-card.down{--accent-color:#16a34a;}
.yoy-big-card.flat{--accent-color:#64748b;}

/* 左侧：同比率 */
.yoy-big-info{display:flex;flex-direction:column;gap:0.5rem;}
.yoy-big-label{
  font-size:0.8125rem;color:#94a3b8;font-weight:600;
  text-transform:uppercase;letter-spacing:0.08em;
}
.yoy-big-pct{
  font-size:3.25rem;font-weight:900;line-height:1;
  font-variant-numeric:tabular-nums;letter-spacing:-0.02em;
  display:flex;align-items:baseline;gap:0.375rem;
}
.yoy-big-pct .yoy-arrow{
  width:2.125rem;height:2.125rem;font-size:1.125rem;
  background:rgba(255,255,255,0.08);border-radius:0.5rem;
}
.yoy-big-pct .yoy-arrow.up{color:#dc2626;background:rgba(220,38,38,0.15);}
.yoy-big-pct .yoy-arrow.down{color:#16a34a;background:rgba(22,163,74,0.15);}
.yoy-big-pct .yoy-arrow.flat{color:#94a3b8;background:rgba(148,163,184,0.15);}
.yoy-big-pct-num{line-height:1;}

/* 右侧：对比柱状图 */
.yoy-big-compare{
  display:flex;flex-direction:column;gap:0.875rem;
  padding-left:1.25rem;border-left:1px solid rgba(255,255,255,0.12);
}
.yoy-cmp-item{display:flex;flex-direction:column;gap:0.375rem;}
.yoy-cmp-header{display:flex;justify-content:space-between;align-items:baseline;}
.yoy-cmp-label{
  font-size:0.75rem;font-weight:600;color:#94a3b8;
  letter-spacing:0.04em;
}
.yoy-cmp-val{
  font-size:1.125rem;font-weight:700;color:#fff;
  font-variant-numeric:tabular-nums;
}
.yoy-cmp-val .yoy-cmp-unit{font-size:0.6875rem;font-weight:500;color:#64748b;margin-left:0.125rem;}
/* 柱状条 */
.yoy-cmp-bar{
  height:0.5rem;border-radius:0.25rem;background:rgba(255,255,255,0.08);
  position:relative;overflow:hidden;
}
.yoy-cmp-fill{
  height:100%;border-radius:0.25rem;
  transition:width 1s cubic-bezier(0.22,1,0.36,1);
}
.yoy-cmp-fill.cur.up{background:linear-gradient(90deg,#dc2626,#ef4444);box-shadow:0 0 0.75rem rgba(220,38,38,0.4);}
.yoy-cmp-fill.cur.down{background:linear-gradient(90deg,#16a34a,#22c55e);box-shadow:0 0 0.75rem rgba(22,163,74,0.4);}
.yoy-cmp-fill.cur.flat{background:linear-gradient(90deg,#94a3b8,#cbd5e1);}
.yoy-cmp-fill.prev{
  background:linear-gradient(90deg,#cbd5e1,#e2e8f0);
  opacity:0.85;
}

/* 响应式 */
@media(max-width:860px){
  .yoy-big-card{grid-template-columns:1fr;gap:1rem;}
  .yoy-big-compare{padding-left:0;border-left:none;border-top:1px solid rgba(255,255,255,0.12);padding-top:1rem;}
}

"""
