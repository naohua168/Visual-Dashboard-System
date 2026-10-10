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

/* ═══════════════════─ 重要客户 tab 切换 ───────── */
.cust-tabs{
  display:flex;gap:0.375rem;margin:0 0 0.375rem 0;
  border-bottom:0.125rem solid var(--border);
}
.cust-tab{
  padding:0.375rem 1.125rem;font-size:0.8125rem;font-weight:700;cursor:pointer;
  border-radius:0.375rem 0.375rem 0 0;color:var(--text-muted);
  background:var(--surface-alt);
  border:1px solid var(--border);
  border-bottom:none;
  transition:all 0.2s;
}
.cust-tab:hover{background:#e2e8f0;color:var(--text);}
.cust-tab.active.inc{background:var(--accent);color:#fff;border-color:var(--accent);}
.cust-tab.active.pay{background:#16a34a;color:#fff;border-color:#16a34a;}

"""
