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

from .base import BaseRenderer, completion_html, rate_cls, hero_rings_html
from .utils import fmt_wan, safe_float, extract_date_range, get_config_range, range_banner_html

DEPARTMENTS = ["检测", "信息", "能源", "海外"]
DEPT_COLORS = {"检测": "#2563eb", "信息": "#8b5cf6", "能源": "#f59e0b", "海外": "#0d9488"}


class OverviewPage(BaseRenderer):
    page_id = "overview"
    nav_name = "数据总览"

    def render(self, data) -> str:
        df_inc = data.income.copy()
        df_pay = data.payment.copy()
        df_inc_tgt = data.annual_income_targets.copy()
        df_pay_tgt = data.annual_payment_targets.copy()
        df_si = data.sales_income.copy()
        df_sp = data.sales_payment.copy()

        for _df in [df_inc, df_pay, df_si, df_sp]:
            _df["金额_万"] = _df["金额"].apply(safe_float) / 10000.0

        t_inc = float(df_inc["金额_万"].sum())
        t_pay = float(df_pay["金额_万"].sum())
        t_inc_tgt = sum(safe_float(df_inc_tgt[d].sum()) for d in DEPARTMENTS if d in df_inc_tgt.columns)
        t_pay_tgt = sum(safe_float(df_pay_tgt[d].sum()) for d in DEPARTMENTS if d in df_pay_tgt.columns)
        inc_rate = t_inc / t_inc_tgt if t_inc_tgt else 0
        pay_rate = t_pay / t_pay_tgt if t_pay_tgt else 0

        # 年累计范围（从配置文件读取：1月~月度数据截止月）
        annual_range = get_config_range(self.base_dir, "年度累计")
        banner = range_banner_html(annual_range)
        return self.wrap_page(
            banner + self._kpi_strip(t_inc, t_pay, t_inc_tgt, t_pay_tgt, inc_rate, pay_rate, data, df_inc)
            + self._dept_matrix(df_inc, df_pay, df_inc_tgt, df_pay_tgt)
            + self._sales_achievement_landscape(df_si, df_sp, data)
            + self._extra_css()
        , extract_date_range(data.income))

    # ════════════════════════════════════════════════════════════
    # [A] 顶部 Hero — 同年度达成款：收入/总指标/回款 + 圆环
    # ════════════════════════════════════════════════════════════
    def _kpi_strip(self, t_inc, t_pay, t_inc_tgt, t_pay_tgt, inc_rate, pay_rate, data, df_inc) -> str:
        # 同比 2024 同期：起止月份从 "年度累计" 配置读取（手动模式驱动）
        yoy_inc = None
        yoy_pay = None
        yoy_label = ""
        cur_start_m = 1
        cur_end_m = 6  # fallback
        # 从配置文件读取年度累计起止月
        annual_range = get_config_range(self.base_dir, "年度累计")
        if annual_range and "~" in annual_range:
            try:
                cur_start_m = int(annual_range.split("~")[0].strip().split("-")[1])
                cur_end_m = int(annual_range.split("~")[1].strip().split("-")[1])
            except (IndexError, ValueError):
                pass
        # 真实数据兜底：保证截止月份不超出数据
        if len(df_inc):
            inc_dates = pd.to_datetime(df_inc["日期"], errors="coerce").dropna()
            if len(inc_dates):
                data_max_m = int(inc_dates.max().month)
                if data_max_m < cur_end_m:
                    cur_end_m = data_max_m
        cur_year = int(inc_dates.min().year) if len(inc_dates) else pd.Timestamp.now().year
        yoy_label = f"{cur_year}年{cur_start_m:02d}-{cur_end_m:02d}月 vs 2024年{cur_start_m:02d}-{cur_end_m:02d}月"
        if data.has_yearly_baseline:
            yi = data.yearly_income.copy()
            yp = data.yearly_payment.copy()
            yi["月"] = pd.to_datetime(yi["日期"], errors="coerce").dt.month
            yp["月"] = pd.to_datetime(yp["日期"], errors="coerce").dt.month
            prev_inc = float(yi[(yi["月"] >= cur_start_m) & (yi["月"] <= cur_end_m)]["金额"].sum()) / 10000.0
            prev_pay = float(yp[(yp["月"] >= cur_start_m) & (yp["月"] <= cur_end_m)]["金额"].sum()) / 10000.0
            if prev_inc > 0:
                yoy_inc = (t_inc - prev_inc) / prev_inc
            if prev_pay > 0:
                yoy_pay = (t_pay - prev_pay) / prev_pay

        total_tgt = t_inc_tgt + t_pay_tgt
        return hero_rings_html(
            t_inc, t_inc_tgt, t_pay, t_pay_tgt, "", "收入", "回款",
            inc_yoy=yoy_inc, pay_yoy=yoy_pay,
            yoy_period=yoy_label,
            total_tgt=total_tgt, total_label="年度总指标",
            show_cust_sales=False,
        )

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
            self.section("月度趋势 & 销售TOP10", "sec-blue")
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
    def _dept_matrix(self, df_inc, df_pay, df_inc_tgt, df_pay_tgt) -> str:
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
                f'<div class="cell-main"><span class="cell-act-val">{fmt_wan(pct*100)}%</span></div>'
                f'</div></td>'
            )

        thead = (
            "<tr>"
            '<th rowspan="2" class="th-name">事业部</th>'
            '<th colspan="2" class="group-header inc-group">收入（年度）</th>'
            '<th colspan="2" class="group-header pay-group">回款（年度）</th>'
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
            inc_tgt = safe_float(df_inc_tgt[d].sum())
            pay_tgt = safe_float(df_pay_tgt[d].sum())
            inc_r = inc_v / inc_tgt if inc_tgt > 0 else 0
            pay_r = pay_v / pay_tgt if pay_tgt > 0 else 0
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
        t_inc_r = t_inc_act / sum(safe_float(df_inc_tgt[d].sum()) for d in DEPARTMENTS) if sum(safe_float(df_inc_tgt[d].sum()) for d in DEPARTMENTS) > 0 else 0
        t_pay_r = t_pay_act / sum(safe_float(df_pay_tgt[d].sum()) for d in DEPARTMENTS) if sum(safe_float(df_pay_tgt[d].sum()) for d in DEPARTMENTS) > 0 else 0
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
            self.section("部门完成度矩阵 · 4 部门 × 收入/回款", "sec-purple")
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
        # 与销售页(page_sales._card1_sales)保持一致：直接从年度收入总指标汇总
        # 不用 data.sales_targets（_compute_sales_targets 按规则反推会包含没在总指标中列出的客户）
        df_tgt = data.annual_income_targets.copy()
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
            self.section("销售年度收入/回款达成度 · Top 10", "sec-green")
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
