"""数据总览页 — 一屏看完核心指标（多种展示形式避免单调）

布局（4种不同视觉形式）：
  [A] 4个核心KPI（环形进度 + 大数字 + 同比箭头）
  [B] 月度趋势 + 销售TOP10（折线图 + 横向条形排名）
  [C] 部门完成度对比（4部门×2指标的cell-bg矩阵）
  [D] 客户贡献度（横向条形图 Top 10 + 集中度风险提示）
"""
from __future__ import annotations

import json

import pandas as pd

from .base import BaseRenderer, completion_html, rate_cls
from .utils import fmt_wan, safe_float

DEPARTMENTS = ["检测", "信息", "能源", "海外"]
DEPT_COLORS = {"检测": "#2563eb", "信息": "#8b5cf6", "能源": "#f59e0b", "海外": "#0d9488"}


class OverviewPage(BaseRenderer):
    page_id = "overview"
    nav_name = "数据总览"

    def render(self, data) -> str:
        df_inc = data.income.copy()
        df_pay = data.payment.copy()
        df_tgt = data.total_targets.copy()
        df_si = data.sales_income.copy()
        df_sp = data.sales_payment.copy()

        for _df in [df_inc, df_pay, df_si, df_sp]:
            _df["金额_万"] = _df["金额"].apply(safe_float) / 10000.0

        t_inc = float(df_inc["金额_万"].sum())
        t_pay = float(df_pay["金额_万"].sum())
        t_tgt = sum(safe_float(df_tgt[d].sum()) for d in DEPARTMENTS if d in df_tgt.columns)
        inc_rate = t_inc / t_tgt if t_tgt else 0
        pay_rate = t_pay / t_tgt if t_tgt else 0

        return self.wrap_page(
            self._kpi_strip(t_inc, t_pay, t_tgt, inc_rate, pay_rate, data, df_inc)
            + self._dept_matrix(df_inc, df_pay, df_tgt)
            + self._sales_achievement_landscape(df_si, df_sp, data)
            + self._extra_css()
        )

    # ════════════════════════════════════════════════════════════
    # [A] 顶部 4 KPI — 环形进度 + 大数字
    # ════════════════════════════════════════════════════════════
    def _kpi_strip(self, t_inc, t_pay, t_tgt, inc_rate, pay_rate, data, df_inc) -> str:
        # 同比 2024 全年
        yoy_inc = 0.0
        yoy_pay = 0.0
        if data.has_yearly_baseline:
            yi = data.yearly_income.copy()
            yp = data.yearly_payment.copy()
            yi["日期"] = pd.to_datetime(yi["日期"], errors="coerce")
            yp["日期"] = pd.to_datetime(yp["日期"], errors="coerce")
            # 取 2024 全年合计（yearly_income 就是 2024 年基线）
            yi_2024 = yi["金额"].sum() / 10000.0
            yp_2024 = yp["金额"].sum() / 10000.0
            if yi_2024 > 0:
                yoy_inc = (t_inc - yi_2024) / yi_2024 * 100
            if yp_2024 > 0:
                yoy_pay = (t_pay - yp_2024) / yp_2024 * 100

        # 客户集中度
        cust_inc = df_inc.groupby("客户")["金额_万"].sum().sort_values(ascending=False)
        top5_pct = cust_inc.head(5).sum() / cust_inc.sum() * 100 if len(cust_inc) else 0
        top1_pct = cust_inc.iloc[0] / cust_inc.sum() * 100 if len(cust_inc) > 0 else 0

        def ring_card(label, value, sub, color, ring_pct, ring_label, badge):
            """环形进度 + 大数字 + 副信息"""
            r = 36
            circ = 2 * 3.14159 * r
            offset = circ * (1 - min(ring_pct, 1))
            return f"""<div class="ring-kpi" style="--accent:{color}">
  <div class="ring-svg-wrap">
    <svg width="84" height="84" viewBox="0 0 84 84">
      <circle cx="42" cy="42" r="{r}" fill="none" stroke="#eef0f5" stroke-width="6"/>
      <circle cx="42" cy="42" r="{r}" fill="none" stroke="{color}" stroke-width="6"
        stroke-dasharray="{circ:.1f}" stroke-dashoffset="{offset:.1f}"
        stroke-linecap="round" transform="rotate(-90 42 42)"/>
      <text x="42" y="46" text-anchor="middle" font-size="14" font-weight="800" fill="{color}">{ring_label}</text>
    </svg>
  </div>
  <div class="ring-content">
    <div class="ring-label">{label}</div>
    <div class="ring-value" style="color:{color}">{value}</div>
    <div class="ring-sub">{sub}</div>
  </div>
  {badge}
</div>"""

        # 同比徽章
        inc_badge = f'<span class="ring-badge up">↑ +{yoy_inc:.0f}%</span>' if yoy_inc > 0 else f'<span class="ring-badge down">↓ {yoy_inc:.0f}%</span>'
        pay_badge = f'<span class="ring-badge up">↑ +{yoy_pay:.0f}%</span>' if yoy_pay > 0 else f'<span class="ring-badge down">↓ {yoy_pay:.0f}%</span>'
        conc_badge = '<span class="ring-badge warn">⚠ 高风险</span>' if top5_pct > 50 else '<span class="ring-badge ok">✓ 正常</span>'

        return self.section("📊 核心指标速览 · 2026 年度", "sec-amber") + f"""<div class="ring-kpi-grid">
  {ring_card("收入完成度", f"{inc_rate*100:.1f}%",
            f"{fmt_wan(t_inc)} 万 / 目标 {fmt_wan(t_tgt)} 万",
            "#16a34a" if inc_rate>=0.5 else "#f59e0b" if inc_rate>=0.3 else "#dc2626",
            inc_rate, f"{inc_rate*100:.0f}%", inc_badge)}
  {ring_card("回款完成度", f"{pay_rate*100:.1f}%",
            f"{fmt_wan(t_pay)} 万 / 目标 {fmt_wan(t_tgt)} 万",
            "#16a34a" if pay_rate>=0.5 else "#f59e0b" if pay_rate>=0.3 else "#dc2626",
            pay_rate, f"{pay_rate*100:.0f}%", pay_badge)}
</div>"""

    # ════════════════════════════════════════════════════════════
    # [B] 月度趋势 + 销售TOP10（折线图 + 横向条形）
    # ════════════════════════════════════════════════════════════
    def _trend_and_sales_top(self, df_inc, df_pay, df_si, df_sp, data) -> str:
        # 销售TOP10（收入+回款合并到一张横向条形图）
        si_ok = df_si[df_si["销售"] != "待确认"].groupby("销售")["金额_万"].sum()
        sp_ok = df_sp[df_sp["销售"] != "待确认"].groupby("销售")["金额_万"].sum()
        sales_tgt = (data.sales_targets or {})
        top_n = 10
        top_inc = si_ok.sort_values(ascending=False).head(top_n)
        top_pay = sp_ok.sort_values(ascending=False).head(top_n)
        all_top = sorted(set(top_inc.index) | set(top_pay.index), key=lambda s: -si_ok.get(s, 0))[:top_n]
        max_v = max(max(si_ok.get(s, 0) for s in all_top), max(sp_ok.get(s, 0) for s in all_top), 1)
        sales_rows = ""
        for i, s in enumerate(all_top, 1):
            inc_v = float(si_ok.get(s, 0))
            pay_v = float(sp_ok.get(s, 0))
            # 双条形: 上条收入（蓝），下条回款（橙），同长度按各自最大值
            inc_w = inc_v / max_v * 100
            pay_w = pay_v / max_v * 100
            tgt = sales_tgt.get(str(s), 0)
            rank_cls = "rank-1" if i == 1 else "rank-2" if i == 2 else "rank-3" if i == 3 else "rank-n"
            sales_rows += f"""<div class="sales-row">
  <span class="rank {rank_cls}">{i}</span>
  <span class="sales-name" title="{s}">{s}</span>
  <div class="sales-bars">
    <div class="sales-bar-row"><span class="sales-bar-label">收入</span>
      <div class="bar"><div class="bar-fill level-inc" style="width:{inc_w:.1f}%">{fmt_wan(inc_v)}</div></div>
    </div>
    <div class="sales-bar-row"><span class="sales-bar-label">回款</span>
      <div class="bar"><div class="bar-fill level-pay" style="width:{pay_w:.1f}%">{fmt_wan(pay_v)}</div></div>
    </div>
  </div>
</div>"""

        # 月度趋势图（折线+柱状混合）
        trend_chart = self._trend_chart(df_inc, df_pay)

        return (
            self.section("📈 月度趋势 & 🏆 销售TOP10", "sec-blue")
            + f'<div class="cols-2">'
            f'<div>{trend_chart}</div>'
            f'<div class="card" style="padding:10px 12px">'
            f'<div class="card-title">销售TOP10 · 收入vs回款对比</div>'
            f'<div class="sales-top-list">{sales_rows}</div>'
            f'</div>'
            f'</div>'
        )

    def _trend_chart(self, df_inc, df_pay) -> str:
        inc = df_inc.copy(); pay = df_pay.copy()
        inc["月份"] = pd.to_datetime(inc["日期"], errors="coerce").dt.to_period("M").astype(str)
        pay["月份"] = pd.to_datetime(pay["日期"], errors="coerce").dt.to_period("M").astype(str)
        mi = inc.groupby("月份")["金额_万"].sum()
        mp = pay.groupby("月份")["金额_万"].sum()
        months = sorted(set(list(mi.index) + list(mp.index)))
        if not months:
            return ""
        iv = [round(float(mi.get(m, 0)), 2) for m in months]
        pv = [round(float(mp.get(m, 0)), 2) for m in months]
        # 计算差额标注
        gaps = [round(p - i, 2) for i, p in zip(iv, pv)]
        cid = "overviewTrend"
        cd = json.dumps({"labels": months, "inc": iv, "pay": pv}, ensure_ascii=False)
        js = f"""<script>(function(){{
  const id='{cid}';const d={cd};
  window.__regChart(id,{{
    type:'bar',data:{{
      labels:d.labels,
      datasets:[
        {{label:'收入',data:d.inc,type:'bar',backgroundColor:'rgba(37,99,235,0.7)',borderColor:'#2563eb',borderWidth:1,order:2}},
        {{label:'回款',data:d.pay,type:'bar',backgroundColor:'rgba(245,158,11,0.7)',borderColor:'#f59e0b',borderWidth:1,order:2}},
        {{label:'差额(回款-收入)',data:[{','.join(str(g) for g in gaps)}],type:'line',borderColor:'#dc2626',backgroundColor:'#dc2626',borderWidth:2,pointRadius:4,pointBackgroundColor:'#dc2626',tension:0.3,order:1}}
      ]}},
    options:{{
      responsive:true,maintainAspectRatio:false,
      interaction:{{mode:'index',intersect:false}},
      plugins:{{
        legend:{{position:'top',labels:{{boxWidth:12,padding:8,color:'#595959',font:{{size:11}},usePointStyle:true}}}},
        tooltip:{{callbacks:{{label:function(c){{return c.dataset.label+': '+c.parsed.y.toLocaleString('zh-CN',{{maximumFractionDigits:0}})+' 万'}}}}}}
      }},
      scales:{{
        x:{{grid:{{display:false}},ticks:{{color:'#595959',font:{{size:11}}}}}},
        y:{{beginAtZero:true,grid:{{color:'rgba(148,163,184,0.2)'}},ticks:{{color:'#595959',font:{{size:10}},callback:function(v){{return v.toLocaleString()+'万'}}}}}}
      }}
    }}
  }}),'{self.page_id}');
}})();</script>"""
        return f'<div class="card" style="padding:10px 12px"><div class="card-title">月度趋势 · 收入/回款/差额</div><div style="height:300px;position:relative"><canvas id="{cid}"></canvas></div>{js}</div>'

    # ════════════════════════════════════════════════════════════
    # [C] 部门完成度矩阵（cell-bg 风格）
    # ════════════════════════════════════════════════════════════
    def _dept_matrix(self, df_inc, df_pay, df_tgt) -> str:
        def cell(pct):
            if pct == 0:
                return '<td class="td-empty">—</td>'
            pct_num = min(pct * 100, 100)
            pct_label = f"{pct*100:.0f}%"
            if pct >= 1:
                fill_var = "#22c55e"; pct_cls = " achieved"
            elif pct >= 0.5:
                fill_var = "#fb923c"; pct_cls = ""
            elif pct > 0:
                fill_var = "#fdba74"; pct_cls = " low"
            else:
                fill_var = "#f1f5f9"; pct_cls = ""
            return (
                f'<td class="cell-bg{" is-total" if False else ""}" style="--pct:{pct_num:.1f}%;--fill:{fill_var}">'
                f'<div class="fill-bg"></div>'
                f'<div class="cell-text">'
                f'<span class="cell-pct{pct_cls}">{pct_label}</span>'
                f'<div class="cell-main"><span class="cell-act">{fmt_wan(pct*100)}%</span></div>'
                f'</div></td>'
            )

        thead = (
            "<tr>"
            '<th rowspan="2" class="th-name">事业部</th>'
            '<th colspan="2" class="group-header inc-group">📈 收入（年度）</th>'
            '<th colspan="2" class="group-header pay-group">💰 回款（年度）</th>'
            "</tr>"
            "<tr>"
            "<th>实际（万）</th><th>完成度</th>"
            "<th>实际（万）</th><th>完成度</th>"
            "</tr>"
        )
        rows = ""
        t_inc_act = t_pay_act = 0.0
        for d in DEPARTMENTS:
            inc_v = float(df_inc[df_inc["事业部"] == d]["金额_万"].sum())
            pay_v = float(df_pay[df_pay["事业部"] == d]["金额_万"].sum())
            tgt = safe_float(df_tgt[d].sum())
            inc_r = inc_v / tgt if tgt > 0 else 0
            pay_r = pay_v / tgt if tgt > 0 else 0
            t_inc_act += inc_v; t_pay_act += pay_v
            dcolor = DEPT_COLORS.get(d, "#94a3b8")
            rows += (
                f'<tr>'
                f'<td class="td-name"><span style="color:{dcolor};font-weight:800">● {d}</span></td>'
                f'<td class="num-cell" style="font-weight:700">{fmt_wan(inc_v)}</td>'
                + cell(inc_r) +
                f'<td class="num-cell" style="font-weight:700">{fmt_wan(pay_v)}</td>'
                + cell(pay_r) +
                f'</tr>'
            )
        # 合计
        t_inc_r = t_inc_act / sum(safe_float(df_tgt[d].sum()) for d in DEPARTMENTS) if sum(safe_float(df_tgt[d].sum()) for d in DEPARTMENTS) > 0 else 0
        t_pay_r = t_pay_act / sum(safe_float(df_tgt[d].sum()) for d in DEPARTMENTS) if sum(safe_float(df_tgt[d].sum()) for d in DEPARTMENTS) > 0 else 0
        rows += (
            f'<tr class="row-total">'
            f'<td class="td-name td-total">合计（4部门）</td>'
            f'<td class="num-cell" style="font-weight:800">{fmt_wan(t_inc_act)}</td>'
            + cell(t_inc_r) +
            f'<td class="num-cell" style="font-weight:800">{fmt_wan(t_pay_act)}</td>'
            + cell(t_pay_r) +
            f'</tr>'
        )

        return (
            self.section("🏢 部门完成度矩阵 · 4 部门 × 收入/回款", "sec-purple")
            + f'<div class="card" style="padding:10px 12px">'
            f'<div class="table-wrap no-collapse"><table class="yoy-dept-table">'
            f'<thead>{thead}</thead>'
            f'<tbody>{rows}</tbody>'
            f'</table></div>'
            f'<div style="margin-top:6px;font-size:11px;color:var(--text-muted)">■ 每格：完成度(实色填充) · ≥80%绿 · 50-80%橙 · 30-50%浅橙 · <30%灰</div>'
            f'</div>'
        )

    # ════════════════════════════════════════════════════════════
    # [D] 销售年度收入/回款达成度（各 Top 10，分开两张卡）
    # ════════════════════════════════════════════════════════════
    def _sales_achievement_landscape(self, df_si, df_sp, data) -> str:
        # 与销售页(page_sales._card1_sales)保持一致：直接从 total_targets 汇总
        # 不用 data.sales_targets（_compute_sales_targets 按规则反推会包含没在总指标中列出的客户）
        df_tgt = data.total_targets.copy()
        dept_cols = DEPARTMENTS
        sales_tgt: dict[str, float] = {}
        for _, row in df_tgt.iterrows():
            sales = str(row.get("销售", "")).strip()
            if not sales or sales in ("", "nan"):
                continue  # 包含"待确认"以便和销售页一致
            total = sum(safe_float(row.get(d, 0)) for d in dept_cols)
            sales_tgt[sales] = sales_tgt.get(sales, 0) + total
        # 不过滤"待确认"（和销售页 _sales_top5 一致）
        si_all = df_si.groupby("销售")["金额_万"].sum()
        sp_all = df_sp.groupby("销售")["金额_万"].sum()

        def top_card(label, data_dict, total):
            """单独一张卡片：10个mini-rate，按达成率降序"""
            rows = ""
            def sort_key(item):
                v = float(item[1])
                tgt = safe_float(sales_tgt.get(str(item[0]), 0))
                return v / tgt if tgt > 0 else 0
            sorted_data = sorted(data_dict.items(), key=sort_key, reverse=True)[:10]
            for i, (name, v) in enumerate(sorted_data, 1):
                v = float(v)
                tgt = safe_float(sales_tgt.get(str(name), 0))
                pct = v / tgt * 100 if tgt > 0 else (v / total * 100 if total else 0)
                cls = rate_cls(pct / 100) if tgt > 0 else "rate-mid"
                bar_w = pct if tgt > 0 else min(pct, 100)
                bar_w_cls = rate_cls(bar_w / 100)
                rank_tag = "rank-1" if i == 1 else "rank-2" if i == 2 else "rank-3" if i == 3 else "rank-n"
                rows += f"""<div class="mini-rate">
  <span class="rank {rank_tag}">{i}</span>
  <span style="flex:1;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{name}</span>
  <div class="bar"><div class="bar-fill {bar_w_cls}" style="width:{min(bar_w,100):.1f}%"><span class="bar-pct">{pct:.1f}%</span></div></div>
  <span class="val">{fmt_wan(v)}</span>
</div>"""
            sub = f"目标达成度 = 个人{label}/个人目标"
            return f'<div class="card"><div class="card-title">销售{label} TOP10<span style="font-size:11px;color:var(--text-muted);font-weight:400;margin-left:auto">总 {fmt_wan(total)} 万</span></div><div style="font-size:10px;color:var(--text-muted);margin-bottom:4px">{sub}</div>{rows}</div>'

        return (
            self.section("🏆 销售年度收入/回款达成度 · Top 10", "sec-green")
            + '<div class="cols-2">'
            + top_card("收入", si_all.to_dict(), float(si_all.sum()))
            + top_card("回款", sp_all.to_dict(), float(sp_all.sum()))
            + '</div>'
        )

    # ════════════════════════════════════════════════════════════
    # 辅助CSS
    # ════════════════════════════════════════════════════════════
    def _extra_css(self) -> str:
        return """<style>
/* 环形KPI卡 */
.ring-kpi-grid{
  display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-bottom:8px;
}
.ring-kpi{
  background:#fff;padding:14px 14px 14px 14px;border-radius:10px;
  border:1px solid var(--border);border-left:4px solid var(--accent);
  box-shadow:var(--shadow-sm);position:relative;
  display:flex;align-items:center;gap:14px;min-height:96px;
  transition:box-shadow .2s,transform .2s;
}
.ring-kpi:hover{box-shadow:var(--shadow-md);transform:translateY(-1px)}
.ring-svg-wrap{flex-shrink:0;width:84px;height:84px}
.ring-content{flex:1;min-width:0;display:flex;flex-direction:column;justify-content:center}
.ring-label{font-size:11px;color:#64748b;font-weight:700;text-transform:uppercase;letter-spacing:.04em}
.ring-value{font-size:30px;font-weight:800;color:var(--accent);font-variant-numeric:tabular-nums;line-height:1.1;margin:2px 0}
.ring-sub{font-size:11px;color:#94a3b8;line-height:1.3}
.ring-badge{
  position:absolute;top:8px;right:8px;font-size:10px;font-weight:700;
  padding:1px 6px;border-radius:10px;
}
.ring-badge.up{background:#fee2e2;color:#dc2626}
.ring-badge.down{background:#dcfce7;color:#16a34a}
.ring-badge.warn{background:#fff7ed;color:#f59e0b}
.ring-badge.ok{background:#dcfce7;color:#16a34a}

/* 销售TOP 列表 */
.sales-top-list{display:flex;flex-direction:column;gap:4px;max-height:340px;overflow-y:auto}
.sales-row{
  display:flex;align-items:center;gap:8px;font-size:12px;
  padding:4px 6px;border-radius:3px;transition:background .15s;
}
.sales-row:hover{background:#f8fafc}
.sales-name{
  width:60px;font-weight:600;color:#334155;flex-shrink:0;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}
.sales-bars{flex:1;display:flex;flex-direction:column;gap:2px}
.sales-bar-row{display:flex;align-items:center;gap:6px}
.sales-bar-label{font-size:10px;color:#94a3b8;width:30px;flex-shrink:0;font-weight:600}
.sales-bar-row .bar{height:14px;background:#f1f5f9;border-radius:2px;overflow:hidden;flex:1}
.bar-fill.level-inc{background:linear-gradient(90deg,#3b82f6,#60a5fa);height:100%;font-size:10px;color:#fff;font-weight:700;display:flex;align-items:center;justify-content:flex-end;padding:0 6px;text-shadow:0 1px 1px rgba(0,0,0,.2)}
.bar-fill.level-pay{background:linear-gradient(90deg,#f59e0b,#fbbf24);height:100%;font-size:10px;color:#fff;font-weight:700;display:flex;align-items:center;justify-content:flex-end;padding:0 6px;text-shadow:0 1px 1px rgba(0,0,0,.2)}

/* 客户Top 10 列表 */
.cust-top-list{display:flex;flex-direction:column;gap:3px;max-height:380px;overflow-y:auto}
.cust-row{
  display:flex;align-items:center;gap:10px;font-size:12px;padding:3px 6px;
  border-radius:3px;transition:background .15s;
}
.cust-row:hover{background:#f8fafc}
.cust-name{
  width:200px;font-weight:500;color:#334155;flex-shrink:0;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}
.cust-row .bar{height:18px;background:#f1f5f9;border-radius:2px;overflow:hidden}
.cust-pct{width:50px;text-align:right;font-variant-numeric:tabular-nums}
.cust-cum{width:62px;text-align:right}
</style>"""
