# Author: naohua168 <bai_bai168@qq.com>
"""年度达成 Hero、重要客户 tab 切换 —— CSS 片段 `annual`

由 processors/static/css_vars.py 拆分而来，内容与拆分前逐字节一致；
拼接顺序见 processors/static/css/__init__.py，改动内容请只在本文件里追加。
"""

CSS = r"""/* ═══════════════════─ 年度达成 Hero（深底大数字 + 双进度） ─══════════════════ */
.annual-hero{
  background:linear-gradient(135deg,#0a1628 0%,#1e3a5f 50%,#0a1628 100%);
  color:#fff;padding:1.125rem 1.5rem;margin-bottom:0.375rem;border-radius:0.5rem;
  display:flex;align-items:center;gap:1.25rem;flex-wrap:wrap;
  box-shadow:0 4px 12px rgba(10,22,40,0.25);
}
.annual-hero-label{
  font-size:0.75rem;opacity:0.7;letter-spacing:0.08em;text-transform:uppercase;
  min-width:7.5rem;font-weight:600;
}
.annual-hero-value{
  font-size:2.625rem;font-weight:800;font-variant-numeric:tabular-nums;
  color:#fbbf24;flex:0 0 auto;letter-spacing:0.02em;
}
.annual-hero-unit{font-size:1rem;font-weight:500;opacity:0.85;margin-left:0.375rem;}
.annual-hero-bars{flex:1;min-width:25rem;display:flex;flex-direction:column;gap:0.5rem;}
.annual-hero-bar{display:flex;align-items:center;gap:0.625rem;}
.annual-hero-name{font-size:0.8125rem;font-weight:700;min-width:2.625rem;}
.annual-hero-track{
  flex:1;height:1.125rem;background:rgba(255,255,255,0.12);
  border-radius:0.5625rem;overflow:hidden;position:relative;
}
.annual-hero-fill{
  height:100%;border-radius:0.5625rem;display:flex;align-items:center;
  justify-content:flex-end;padding-right:0.625rem;
  color:#fff;font-size:0.6875rem;font-weight:800;letter-spacing:0.02em;
  min-width:2.25rem;transition:width 0.5s ease;
}
.annual-hero-fill.inc{background:linear-gradient(90deg,#1e40af,#2563eb);}
.annual-hero-fill.pay{background:linear-gradient(90deg,#15803d,#16a34a);}
.annual-hero-val{font-size:0.8125rem;font-weight:700;font-variant-numeric:tabular-nums;color:#e0e7ff;min-width:5rem;text-align:right;}
.annual-hero-arrow{font-size:0.875rem;color:#cbd5e1;font-weight:700;margin-left:0.375rem;transition:transform 0.2s;}
.annual-hero-bar.expanded .annual-hero-arrow{transform:rotate(90deg);color:#fbbf24;}

/* 折叠/展开 */
.hidden{display:none !important;}

/* ═══════════════════─ 收入/回款 切换 + 客户搜索（通栏三段，2026-11-03） ─────────
   收入 / 回款 合并成一个分段控件（各占 1/3 宽），右侧 1/3 是表格搜索框；
   三四段合计撑满整行。移动端在 responsive.py 里改成上下两行。 */
.cust-tabs{
  display:flex;align-items:center;gap:0.75rem;width:100%;
  margin:0 0 0.5rem 0;
}
.cust-tabs-seg{
  display:flex;flex:2 1 0;min-width:0;height:2.25rem;
  border:1px solid var(--border);border-radius:0.5rem;
  background:var(--surface-alt);overflow:hidden;
}
.cust-tabs.no-search .cust-tabs-seg{flex:1 1 auto;}
.cust-tab{
  display:flex;align-items:center;justify-content:center;
  flex:1 1 0;min-width:0;padding:0 0.75rem;
  font-size:0.8125rem;font-weight:700;cursor:pointer;white-space:nowrap;
  color:var(--text-muted);background:transparent;
  border-right:1px solid var(--border);
  transition:background .2s,color .2s;user-select:none;
}
.cust-tab:last-child{border-right:none;}
.cust-tab:hover{background:#e2e8f0;color:var(--text);}
.cust-tab.active.inc{background:var(--accent);color:#fff;}
.cust-tab.active.pay{background:#16a34a;color:#fff;}
.cust-tab:focus-visible{outline:0.125rem solid var(--accent);outline-offset:-0.125rem;}

/* 搜索框（工具条第三段） */
.cust-tabs .cust-search{
  display:flex;align-items:center;gap:0.375rem;
  flex:1 1 0;min-width:0;height:2.25rem;padding:0 0.625rem;
  background:var(--surface);border:1px solid var(--border);border-radius:0.5rem;
  transition:border-color .2s,box-shadow .2s;
}
.cust-tabs .cust-search:focus-within{
  border-color:var(--accent);box-shadow:0 0 0 0.1875rem rgba(37,99,235,0.12);
}
.cust-search-icon{display:flex;align-items:center;flex:0 0 auto;color:var(--text-muted);}
.cust-search-input{
  flex:1 1 auto;min-width:0;border:none;background:transparent;outline:none;
  font-size:0.8125rem;color:var(--text);font-family:inherit;
}
.cust-search-input::placeholder{color:#64748b;}
.cust-search-input::-webkit-search-cancel-button,
.cust-search-input::-webkit-search-decoration{-webkit-appearance:none;appearance:none;}
.cust-search-count{
  font-size:0.6875rem;color:var(--text-secondary);
  font-variant-numeric:tabular-nums;white-space:nowrap;
}
.cust-search-clear{
  display:none;border:none;background:transparent;color:var(--text-muted);
  font-size:1rem;line-height:1;cursor:pointer;padding:0 0.0625rem;
}
.cust-search-clear.is-on{display:block;}
.cust-search-clear:hover{color:var(--text);}
.cust-search-clear:focus-visible{outline:0.125rem solid var(--accent);border-radius:0.25rem;}

"""
