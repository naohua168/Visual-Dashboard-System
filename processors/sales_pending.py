"""待确认客户数据分析模块 — 从 page_sales.py 独立

提供待确认客户明细的 6 区块数据分析 + 右侧滑入面板渲染。
"""
from __future__ import annotations

import pandas as pd

from .utils import fmt_wan, safe_float

DEPT_COLORS = {"检测": "#2563eb", "信息": "#8b5cf6", "能源": "#f59e0b", "海外": "#0d9488"}


def build_pending_modal(pending: pd.DataFrame, pending_count: int,
                        pending_total_inc: float, pending_total_pay: float) -> str:
    """销售=待确认的客户明细 + 6 区块数据分析 · 右侧滑入面板"""
    if pending_count == 0:
        return ""

    # ── ① KPI 计算 ──
    grand_total = pending_total_inc + pending_total_pay
    avg_per_cust = grand_total / pending_count if pending_count else 0
    match_n = ((pending["金额_万_收入"] > 0) & (pending["金额_万_回款"] > 0)).sum()
    only_inc_n = ((pending["金额_万_收入"] > 0) & (pending["金额_万_回款"] == 0)).sum()
    only_pay_n = ((pending["金额_万_收入"] == 0) & (pending["金额_万_回款"] > 0)).sum()
    only_inc_amt = pending.loc[(pending["金额_万_收入"] > 0) & (pending["金额_万_回款"] == 0), "金额_万_收入"].sum()
    only_pay_amt = pending.loc[(pending["金额_万_收入"] == 0) & (pending["金额_万_回款"] > 0), "金额_万_回款"].sum()

    # ── ② 事业部分布 ──
    dept_dist = pending.groupby("事业部")[["金额_万_收入", "金额_万_回款"]].sum()
    dept_dist["合计"] = dept_dist["金额_万_收入"] + dept_dist["金额_万_回款"]
    dept_dist = dept_dist.sort_values("合计", ascending=False)
    max_dept = dept_dist["合计"].max() if len(dept_dist) else 0

    # ── ③ 客户类型分布 ──
    type_kws = {
        "整车厂": ["广汽", "比亚迪", "小鹏", "五菱", "上汽", "通用", "东风", "一汽", "吉利", "奇瑞", "长安", "长城",
                   "宝马", "奔驰", "奥迪", "大众", "丰田", "本田", "福特", "新丰", "新势力", "启境"],
        "零部件": ["科技", "电子", "部件", "零部件", "工贸", "电池", "智联", "制造", "技术"],
        "检测/认证": ["检测", "认证", "测试", "鉴定", "质检", "实验室", "研究院"],
        "信息/智能": ["信息", "网络", "软件", "数据", "智能", "互联", "物联"],
        "自有客户": ["自有"],
        "政府/市场": ["市场", "管理局", "办公室", "中心站", "事业单位"],
    }
    type_buckets = _classify_customers(pending, type_kws, grand_total)

    # ── ④ 收入/回款分布 ──
    quad = {
        "双向都有": (match_n, grand_total - only_inc_amt - only_pay_amt),
        "仅收入未回": (only_inc_n, only_inc_amt),
        "仅回款无收入": (only_pay_n, only_pay_amt),
    }

    # ── ⑤ Top 10 ──
    top10 = pending.sort_values("合计", ascending=False).head(10)
    max_top = top10["合计"].max() if len(top10) else 0

    # ── 洞察 ──
    top_dept_name = dept_dist.index[0] if len(dept_dist) else "—"
    top_dept_pct = dept_dist.iloc[0]["合计"] / grand_total * 100 if grand_total else 0
    top_cust_name = pending.sort_values("合计", ascending=False).iloc[0]["客户"] if len(pending) else "—"
    top_cust_amt = pending.sort_values("合计", ascending=False).iloc[0]["合计"] if len(pending) else 0
    top_cust_pct = top_cust_amt / grand_total * 100 if grand_total else 0

    # ── 渲染子模块 ──
    kpi_html = _render_kpi_row(pending_count, grand_total, pending_total_inc, pending_total_pay, avg_per_cust, match_n)
    dept_html = _render_dept_dist(dist=dept_dist, grand_total=grand_total, max_dept=max_dept)
    type_html = _render_type_buckets(buckets=type_buckets, grand_total=grand_total)
    quad_html = _render_quad(quad=quad, grand_total=grand_total)
    top_html = _render_top10(top10=top10, max_top=max_top)
    detail_rows = _render_detail(pending, pending_total_inc, pending_total_pay, grand_total, pending_count)

    return f"""<!-- ═══ 待确认客户 · 右侧滑入面板 ═══ -->
<div id="pendingModal" class="pnd-overlay" style="display:none" onclick="if(event.target===this)closePendingModal()">
  <div class="pnd-panel" onclick="event.stopPropagation()">
    <!-- 头部 -->
    <div class="pnd-header">
      <div class="pnd-header-left">
        <div class="pnd-header-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/><path d="M11 8v6"/><path d="M8 11h6"/></svg>
        </div>
        <div>
          <div class="pnd-title">待确认客户 · 数据分析</div>
          <div class="pnd-subtitle">{pending_count} 家客户未归属销售 · 合计 {fmt_wan(grand_total)} 万</div>
        </div>
      </div>
      <button class="pnd-close" onclick="closePendingModal()" aria-label="关闭面板">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>
    <!-- 关键指标条 -->
    <div class="pnd-kpi-strip">{kpi_html}</div>
    <!-- 内容区 -->
    <div class="pnd-body">
      <div class="pnd-section">
        <div class="pnd-section-title">事业部分布<span class="pnd-badge">{top_dept_name} 占 {top_dept_pct:.1f}%</span></div>
        <div class="pnd-chart">{dept_html}</div>
      </div>
      <div class="pnd-section">
        <div class="pnd-section-title">客户类型分布</div>
        <div class="pnd-chart">{type_html}</div>
      </div>
      <div class="pnd-section">
        <div class="pnd-section-title">收入/回款匹配<span class="pnd-badge">匹配度 {match_n/pending_count*100:.1f}%</span></div>
        <div class="pnd-quad-grid">{quad_html}</div>
      </div>
      <div class="pnd-section">
        <div class="pnd-section-title">Top 10 客户<span class="pnd-badge">最大 {top_cust_name} {fmt_wan(top_cust_amt)}万 ({top_cust_pct:.1f}%)</span></div>
        <div class="pnd-chart">{top_html}</div>
      </div>
      <div class="pnd-section">
        <div class="pnd-section-title">完整明细表（{pending_count} 家）</div>
        <div class="pnd-table-wrap">
          <table class="pnd-table">
            <thead><tr>
              <th class="pnd-th-name">客户</th>
              <th style="width:56px">事业部</th>
              <th style="width:82px">收入(万)</th>
              <th style="width:82px">回款(万)</th>
              <th style="width:82px">合计(万)</th>
            </tr></thead>
            <tbody>{detail_rows}</tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</div>
<style>
/* ═══ 遮罩层 ═══ */
.pnd-overlay{{
  position:fixed;top:0;left:0;right:0;bottom:0;
  background:rgba(15,23,42,.5);z-index:9999;
  display:flex;justify-content:flex-end;
  animation:pndFadeIn .2s ease;
}}
/* ═══ 右侧滑入面板 ═══ */
.pnd-panel{{
  width:min(860px,92vw);height:100vh;max-height:100vh;
  background:#fff;box-shadow:-8px 0 40px rgba(0,0,0,.15);
  display:flex;flex-direction:column;
  animation:pndSlideIn .3s cubic-bezier(.4,0,.2,1);
  overflow:hidden;
}}
/* ═══ 头部 ═══ */
.pnd-header{{
  padding:18px 24px;display:flex;align-items:center;justify-content:space-between;
  border-bottom:1px solid #e2e8f0;background:#f8fafc;flex-shrink:0;
}}
.pnd-header-left{{display:flex;align-items:center;gap:14px}}
.pnd-header-icon{{
  width:40px;height:40px;border-radius:10px;
  background:linear-gradient(135deg,#fbbf24,#f59e0b);
  display:flex;align-items:center;justify-content:center;color:#fff;
  flex-shrink:0;
}}
.pnd-title{{font-size:17px;font-weight:800;color:#0f172a;line-height:1.3}}
.pnd-subtitle{{font-size:12px;color:#64748b;margin-top:1px}}
.pnd-close{{
  width:36px;height:36px;border-radius:8px;border:none;background:transparent;
  color:#94a3b8;cursor:pointer;display:flex;align-items:center;justify-content:center;
  transition:all .15s;flex-shrink:0;
}}
.pnd-close:hover{{background:#fee2e2;color:#dc2626}}
/* ═══ KPI 指标条 ═══ */
.pnd-kpi-strip{{
  display:grid;grid-template-columns:repeat(5,1fr);gap:1px;background:#e2e8f0;
  border-bottom:1px solid #e2e8f0;flex-shrink:0;
}}
.pnd-kpi-item{{
  background:#fff;padding:12px 14px;text-align:center;
}}
.pnd-kpi-item:not(:last-child){{border-right:1px solid #e2e8f0}}
.pnd-kpi-num{{font-size:20px;font-weight:800;color:#0f172a;line-height:1.2}}
.pnd-kpi-lbl{{font-size:11px;color:#64748b;margin-top:2px;font-weight:600}}
/* ═══ 内容滚动区 ═══ */
.pnd-body{{flex:1;overflow-y:auto;padding:16px 24px 24px}}
.pnd-section{{margin-bottom:20px}}
.pnd-section-title{{
  font-size:13px;font-weight:800;color:#1e293b;margin-bottom:10px;
  display:flex;align-items:center;gap:8px;flex-wrap:wrap;
}}
.pnd-section-title::before{{
  content:'';width:3px;height:14px;background:#3b82f6;border-radius:2px;
  display:inline-block;flex-shrink:0;
}}
.pnd-badge{{
  font-size:11px;font-weight:500;color:#64748b;background:#f1f5f9;
  padding:2px 8px;border-radius:10px;white-space:nowrap;
}}
/* ═══ 条形图 ═══ */
.pnd-chart{{display:flex;flex-direction:column;gap:5px}}
.pnd-row{{
  display:flex;align-items:center;gap:8px;font-size:12px;
  padding:4px 8px;border-radius:4px;transition:background .12s;
}}
.pnd-row:hover{{background:#f1f5f9}}
.pnd-row.rk-hl{{background:#fefce8}}
.pnd-lbl{{font-weight:600;color:#334155;flex-shrink:0}}
.pnd-num{{font-size:11px;color:#94a3b8;flex-shrink:0}}
.pnd-bar{{
  flex:1;height:20px;background:#f1f5f9;border-radius:4px;overflow:hidden;
  position:relative;min-width:60px;
}}
.pnd-fill{{
  height:100%;border-radius:4px;display:flex;align-items:center;justify-content:flex-end;
  padding:0 8px;transition:width .4s cubic-bezier(.4,0,.2,1);
  background:linear-gradient(90deg,#3b82f6,#60a5fa);
}}
.pnd-fill-amt{{font-size:11px;font-weight:700;color:#fff;text-shadow:0 1px 2px rgba(0,0,0,.15)}}
.pnd-pct{{font-size:11px;color:#64748b;font-weight:700;width:44px;text-align:right;flex-shrink:0}}
.pnd-sub{{font-size:10px;color:#94a3b8;flex-shrink:0}}
.pnd-rank{{font-weight:800;color:#f59e0b;width:20px;text-align:center;font-size:13px;flex-shrink:0}}
.pnd-dept{{font-size:11px;font-weight:700;text-align:center;flex-shrink:0}}
/* ═══ 三象限 ═══ */
.pnd-quad-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}}
.pnd-quad-cell{{
  background:#f8fafc;padding:12px 10px;border-radius:6px;text-align:center;
  border:1px solid #e2e8f0;transition:box-shadow .15s;
}}
.pnd-quad-cell:hover{{box-shadow:0 2px 8px rgba(0,0,0,.06)}}
.pnd-quad-num{{font-size:20px;font-weight:800;color:#0f172a}}
.pnd-quad-lbl{{font-size:11px;color:#64748b;margin:3px 0}}
.pnd-quad-amt{{font-size:13px;font-weight:700;color:#475569}}
.pnd-quad-pct{{font-size:10px;color:#94a3b8}}
/* ═══ 明细表 ═══ */
.pnd-table-wrap{{max-height:360px;overflow-y:auto;border:1px solid #e2e8f0;border-radius:6px}}
.pnd-table{{width:100%;border-collapse:collapse;font-size:12px}}
.pnd-table thead{{position:sticky;top:0;z-index:2}}
.pnd-table th{{
  background:#f1f5f9;padding:8px 10px;text-align:left;font-weight:700;
  color:#475569;border-bottom:2px solid #e2e8f0;font-size:11px;white-space:nowrap;
}}
.pnd-th-name{{min-width:140px}}
.pnd-table td{{
  padding:7px 10px;border-bottom:1px solid #f1f5f9;color:#334155;
}}
.pnd-table tbody tr:hover{{background:#f8fafc}}
.pnd-table tbody tr:last-child td{{border-bottom:none}}
.pnd-table .row-total td{{
  font-weight:700;background:#fafafa;border-top:2px solid #e2e8f0;color:#1e293b;
}}
/* ═══ 动画 ═══ */
@keyframes pndFadeIn{{from{{opacity:0}}to{{opacity:1}}}}
@keyframes pndSlideIn{{from{{transform:translateX(40px);opacity:0}}to{{transform:translateX(0);opacity:1}}}}
</style>
<script>
function openPendingModal(){{
  document.getElementById('pendingModal').style.display='flex';
  document.body.style.overflow='hidden';
}}
function closePendingModal(){{
  document.getElementById('pendingModal').style.display='none';
  document.body.style.overflow='';
}}
document.addEventListener('keydown',function(e){{
  if(e.key==='Escape') closePendingModal();
}});
</script>"""


# ── 渲染函数 ──

def _render_kpi_row(pending_count, grand_total, pending_total_inc, pending_total_pay, avg_per_cust, match_n):
    """顶部 KPI 指标条"""
    items = [
        (f"{pending_count}", "客户数", "#f59e0b"),
        (fmt_wan(grand_total), "总金额 (万)", "#dc2626"),
        (fmt_wan(pending_total_inc), "总收入 (万)", "#3b82f6"),
        (fmt_wan(pending_total_pay), "总回款 (万)", "#10b981"),
        (f"{match_n}/{pending_count}", "双向匹配", "#8b5cf6"),
    ]
    return "".join(
        f'<div class="pnd-kpi-item">'
        f'<div class="pnd-kpi-num" style="color:{c}">{v}</div>'
        f'<div class="pnd-kpi-lbl">{l}</div></div>'
        for v, l, c in items
    )


def _classify_customers(pending, type_kws, grand_total):
    """按名称关键词分类客户"""
    type_buckets = []
    for t, kws in type_kws.items():
        mask = pending["客户"].astype(str).apply(lambda x: any(k in x for k in kws))
        if mask.sum() > 0:
            type_buckets.append((t, int(mask.sum()), float(pending.loc[mask, "合计"].sum())))
    classified_mask = pd.Series([False] * len(pending))
    for t, kws in type_kws.items():
        classified_mask |= pending["客户"].astype(str).apply(lambda x: any(k in x for k in kws))
    unclass_n = (~classified_mask).sum()
    if unclass_n > 0:
        type_buckets.append(("其他", int(unclass_n), float(pending.loc[~classified_mask, "合计"].sum())))
    type_buckets.sort(key=lambda x: -x[2])
    return type_buckets


def _render_dept_dist(dist, grand_total, max_dept):
    """事业部分布横向条形图"""
    html = ""
    for d, row in dist.iterrows():
        inc_v = float(row["金额_万_收入"])
        pay_v = float(row["金额_万_回款"])
        tot = float(row["合计"])
        pct = tot / grand_total * 100 if grand_total else 0
        bar_w = tot / max_dept * 100 if max_dept else 0
        dcolor = DEPT_COLORS.get(d, "#94a3b8")
        html += (
            f'<div class="pnd-row">'
            f'<span class="pnd-lbl" style="color:{dcolor};width:60px">{d}</span>'
            f'<div class="pnd-bar"><div class="pnd-fill" style="width:{bar_w:.1f}%;background:{dcolor}">'
            f'<span class="pnd-fill-amt">{fmt_wan(tot)}</span></div></div>'
            f'<span class="pnd-pct">{pct:.1f}%</span>'
            f'<span class="pnd-sub">收{fmt_wan(inc_v)} / 回{fmt_wan(pay_v)}</span>'
            f'</div>'
        )
    return html


def _render_type_buckets(buckets, grand_total):
    """客户类型分布条形图"""
    if not buckets:
        return ""
    max_type = buckets[0][2]
    html = ""
    for t, n, a in buckets:
        pct = a / grand_total * 100 if grand_total else 0
        bar_w = a / max_type * 100 if max_type else 0
        html += (
            f'<div class="pnd-row">'
            f'<span class="pnd-lbl" style="width:80px">{t}</span>'
            f'<span class="pnd-num" style="width:32px">{n}家</span>'
            f'<div class="pnd-bar"><div class="pnd-fill" style="width:{bar_w:.1f}%;background:#8b5cf6">'
            f'<span class="pnd-fill-amt">{fmt_wan(a)}</span></div></div>'
            f'<span class="pnd-pct">{pct:.1f}%</span>'
            f'</div>'
        )
    return html


def _render_quad(quad, grand_total):
    """收入/回款三象限"""
    quad_colors = {"双向都有": "#10b981", "仅收入未回": "#f59e0b", "仅回款无收入": "#3b82f6"}
    html = ""
    for k, (cnt, amt) in quad.items():
        pct = amt / grand_total * 100 if grand_total else 0
        html += (
            f'<div class="pnd-quad-cell" style="border-top:3px solid {quad_colors[k]}">'
            f'<div class="pnd-quad-num">{cnt}<span style="font-size:12px;font-weight:400"> 家</span></div>'
            f'<div class="pnd-quad-lbl">{k}</div>'
            f'<div class="pnd-quad-amt">{fmt_wan(amt)} 万</div>'
            f'<div class="pnd-quad-pct">占 {pct:.1f}%</div>'
            f'</div>'
        )
    return html


def _render_top10(top10, max_top):
    """Top 10 客户横向条形图"""
    html = ""
    for i, (_, r) in enumerate(top10.iterrows(), 1):
        cust = str(r["客户"])
        dept = str(r["事业部"])
        tot = float(r["合计"])
        inc_v = float(r["金额_万_收入"])
        pay_v = float(r["金额_万_回款"])
        bar_w = tot / max_top * 100 if max_top else 0
        dcolor = DEPT_COLORS.get(dept, "#94a3b8")
        rk_cls = " rk-hl" if i <= 3 else ""
        html += (
            f'<div class="pnd-row{rk_cls}">'
            f'<span class="pnd-rank">{i}</span>'
            f'<span class="pnd-lbl" style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0" title="{cust}">{cust}</span>'
            f'<span class="pnd-dept" style="color:{dcolor};width:36px">{dept}</span>'
            f'<div class="pnd-bar" style="width:110px"><div class="pnd-fill" style="width:{bar_w:.1f}%;background:{dcolor}">'
            f'<span class="pnd-fill-amt">{fmt_wan(tot)}</span></div></div>'
            f'<span class="pnd-sub" style="width:88px">收{fmt_wan(inc_v)}/回{fmt_wan(pay_v)}</span>'
            f'</div>'
        )
    return html


def _render_detail(pending, pending_total_inc, pending_total_pay, grand_total, pending_count):
    """完整明细表"""
    rows = ""
    for _, r in pending.iterrows():
        cust = str(r["客户"])
        dept = str(r["事业部"])
        inc_v = safe_float(r["金额_万_收入"])
        pay_v = safe_float(r["金额_万_回款"])
        tot = inc_v + pay_v
        dcolor = DEPT_COLORS.get(dept, "#94a3b8")
        rows += (
            f'<tr>'
            f'<td style="max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="{cust}">{cust}</td>'
            f'<td style="text-align:center;font-weight:600;color:{dcolor};font-size:11px">{dept}</td>'
            f'<td style="text-align:right">{fmt_wan(inc_v)}</td>'
            f'<td style="text-align:right">{fmt_wan(pay_v)}</td>'
            f'<td style="text-align:right;font-weight:700;color:#1e40af">{fmt_wan(tot)}</td>'
            f'</tr>'
        )
    rows += (
        f'<tr class="row-total">'
        f'<td style="font-weight:700">合计（{pending_count}家）</td>'
        f'<td></td>'
        f'<td style="text-align:right;font-weight:700">{fmt_wan(pending_total_inc)}</td>'
        f'<td style="text-align:right;font-weight:700">{fmt_wan(pending_total_pay)}</td>'
        f'<td style="text-align:right;font-weight:800;color:#1e40af">{fmt_wan(grand_total)}</td>'
        f'</tr>'
    )
    return rows
