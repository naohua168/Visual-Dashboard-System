"""数据总览页 — 一屏看完核心指标（收入+回款双维度）"""
from __future__ import annotations

import json

import pandas as pd

from .base import BaseRenderer, completion_html, rate_cls
from .utils import fmt_wan, safe_float

DEPARTMENTS = ["检测", "信息", "能源", "海外"]


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

        # ── 第零行：年度总指标（KPI 卡组） ──
        kpi_annual = self._annual_kpi_grid(df_inc, df_pay, df_tgt, df_si)

        # ── 年度 + 月度 的事业部完成度（收入 / 回款 各 2 张） ──
        df_mi = data.monthly_income_detail.copy() if data.monthly_income_detail is not None else None
        df_mp = data.monthly_payment_detail.copy() if data.monthly_payment_detail is not None else None
        if df_mi is not None:
            df_mi["金额_万"] = df_mi["金额"].apply(safe_float) / 10000.0
        if df_mp is not None:
            df_mp["金额_万"] = df_mp["金额"].apply(safe_float) / 10000.0

        tgt_m = data.monthly_income_targets if data.monthly_income_targets is not None else None
        inc_year  = self._dept_mini(df_inc, df_tgt, "年度", "收入")
        inc_month = self._dept_mini(df_mi if df_mi is not None else df_inc, tgt_m if tgt_m is not None else df_tgt, "月度", "收入")
        pay_year  = self._dept_mini(df_pay, df_tgt, "年度", "回款")
        pay_month = self._dept_mini(df_mp if df_mp is not None else df_pay, tgt_m if tgt_m is not None else df_tgt, "月度", "回款")

        row1 = f'<div class="cols-2"><div>{inc_year}</div><div>{inc_month}</div></div>'
        row2 = f'<div class="cols-2"><div>{pay_year}</div><div>{pay_month}</div></div>'

        # ── 第三行：销售TOP5 收入+回款 ──
        sales_top_inc = self._sales_top5(df_si, "收入", data)
        sales_top_pay = self._sales_top5(df_sp, "回款", data)
        row3 = f'<div class="cols-2"><div>{sales_top_inc}</div><div>{sales_top_pay}</div></div>'

        return self.wrap_page(kpi_annual + row1 + row2 + row3)

    def _annual_kpi_grid(self, df_inc, df_pay, df_tgt, df_si) -> str:
        """年度总指标 KPI 卡片组 — 以完成度为核心"""
        t_inc = float(df_inc["金额_万"].sum())
        t_pay = float(df_pay["金额_万"].sum())
        t_tgt = sum(safe_float(df_tgt[d].sum()) for d in DEPARTMENTS if d in df_tgt.columns)
        inc_rate = t_inc / t_tgt if t_tgt else 0
        pay_rate = t_pay / t_tgt if t_tgt else 0
        return self.section("年度完成度总览", "sec-amber") + f"""<div class="kpi-grid cols-3">
  <div class="kpi kpi-inc"><div class="kpi-label">收入完成度</div><div class="kpi-value">{inc_rate*100:.1f}%</div><div class="kpi-sub">{fmt_wan(t_inc)} 万 / 目标 {fmt_wan(t_tgt)} 万</div></div>
  <div class="kpi kpi-pay"><div class="kpi-label">回款完成度</div><div class="kpi-value">{pay_rate*100:.1f}%</div><div class="kpi-sub">{fmt_wan(t_pay)} 万 / 目标 {fmt_wan(t_tgt)} 万</div></div>
  <div class="kpi kpi-tgt"><div class="kpi-label">年度总目标</div><div class="kpi-value">{fmt_wan(t_tgt)}<span class="kpi-unit">万</span></div><div class="kpi-sub">4 事业部合计</div></div>
</div>"""

    def _dept_mini(self, df, df_tgt, period: str, metric: str) -> str:
        rows = ""
        total_act = total_tgt = 0
        for d in DEPARTMENTS:
            act = float(df[df["事业部"] == d]["金额_万"].sum()) if df is not None else 0
            tgt = safe_float(df_tgt[d].sum()) if df_tgt is not None and d in df_tgt.columns else 0
            total_act += act; total_tgt += tgt
            r = act / tgt if tgt else 0
            cls = rate_cls(r)
            warn = ' style="color:var(--red)"' if r < 0.25 and tgt > 0 else ""
            rows += f"""<div class="mini-rate">
  <span style="width:48px;font-weight:600"{warn}>{d}</span>
  <div class="bar"><div class="bar-fill {cls}" style="width:{min(r*100,100):.1f}%"><span class="bar-pct">{r*100:.1f}%</span></div></div>
  <span class="val">{fmt_wan(act)}</span>
  <span style="color:var(--text-muted);font-size:11px;min-width:50px">/{fmt_wan(tgt)}</span>
</div>"""
        r = total_act / total_tgt if total_tgt else 0
        cls = rate_cls(r)
        rows += f"""<div class="mini-rate" style="border-top:2px solid var(--border);padding-top:8px;margin-top:4px">
  <span style="width:48px;font-weight:700">合计</span>
  <div class="bar"><div class="bar-fill {cls}" style="width:{min(r*100,100):.1f}%"><span class="bar-pct">{r*100:.1f}%</span></div></div>
  <span class="val">{fmt_wan(total_act)}</span>
  <span style="color:var(--text-muted);font-size:11px;min-width:50px">/{fmt_wan(total_tgt)}</span>
</div>"""
        return f'<div class="card"><div class="card-title">{period}·{metric}完成度</div>{rows}</div>'

    def _trend_chart(self, df_inc, df_pay) -> str:
        inc = df_inc.copy(); pay = df_pay.copy()
        inc["月份"] = pd.to_datetime(inc["日期"], errors="coerce").dt.to_period("M").astype(str)
        pay["月份"] = pd.to_datetime(pay["日期"], errors="coerce").dt.to_period("M").astype(str)
        mi = inc.groupby("月份")["金额_万"].sum()
        mp = pay.groupby("月份")["金额_万"].sum()
        months = sorted(set(list(mi.index) + list(mp.index)))
        iv = [round(float(mi.get(m, 0)), 2) for m in months]
        pv = [round(float(mp.get(m, 0)), 2) for m in months]
        cid = "overviewTrend"
        cd = json.dumps({"labels": months, "inc": iv, "pay": pv}, ensure_ascii=False)
        js = f"""<script>(function(){{
  const id='{cid}';const d={cd};
  window.__regChart(id,{{
    type:'bar',data:{{
      labels:d.labels,
      datasets:[
        {{label:'收入',data:d.inc,
         backgroundColor:'#2b579a',borderColor:'#1a3a6b',borderWidth:1,
         hoverBackgroundColor:'#4472c4'}},
        {{label:'回款',data:d.pay,
         backgroundColor:'#70ad47',borderColor:'#548235',borderWidth:1,
         hoverBackgroundColor:'#92d050'}}
      ]}},
    options:{{
      responsive:true,maintainAspectRatio:false,
      interaction:{{mode:'index',intersect:false}},
      plugins:{{
        legend:{{position:'top',labels:{{boxWidth:10,padding:10,color:'#595959',font:{{size:10}},usePointStyle:true}}}}
      }},
      scales:{{
        x:{{grid:{{color:'#e0e0e0'}},ticks:{{color:'#595959',font:{{size:9}}}}}},
        y:{{beginAtZero:true,grid:{{color:'#e0e0e0'}},ticks:{{color:'#595959',font:{{size:9}},callback:function(v){{return v+'万'}}}}}}
      }}
    }}
  }}),'{self.page_id}');
}})();</script>"""
        return f'<div class="chart-box" style="min-height:260px"><div class="chart-title">月度趋势（万元）</div><div style="height:210px"><canvas id="{cid}"></canvas></div>{js}</div>'

    def _sales_top5(self, df, label: str, data=None) -> str:
        top5 = df.groupby("销售")["金额_万"].sum().sort_values(ascending=False).head(5)
        total = float(df["金额_万"].sum()) if len(df) else 0
        sales_tgt = (data.sales_targets or {}) if data is not None else {}
        rows = ""
        for i, (name, v) in enumerate(zip(top5.index, top5.values), 1):
            v = float(v)
            # 优先用个人目标算完成度，没有就退回占比
            tgt = sales_tgt.get(str(name), 0)
            if tgt > 0:
                pct = v / tgt * 100
            else:
                pct = v / total * 100 if total else 0
            rc = "rank-1" if i == 1 else "rank-2" if i == 2 else "rank-3" if i == 3 else "rank-n"
            rows += f"""<div class="mini-rate">
  <span class="rank {rc}">{i}</span>
  <span style="flex:1;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{name}</span>
  <div class="bar"><div class="bar-fill {rate_cls(pct/100)}" style="width:{min(pct,100):.1f}%"><span class="bar-pct {rate_cls(pct/100)}">{pct:.1f}%</span></div></div>
  <span class="val">{fmt_wan(v)}</span>
</div>"""
        sub = f"完成度 = 个人{label}/个人目标" if sales_tgt else "完成度 = 个人占总额份额"
        return f'<div class="card"><div class="card-title">销售{label} TOP5 <span style="font-size:11px;color:var(--text-muted);font-weight:400;margin-left:auto">总额 {fmt_wan(total)} 万</span></div><div style="font-size:10px;color:var(--text-muted);margin-bottom:6px">{sub}</div>{rows}</div>'

    def _pay_dept_table(self, df_pay) -> str:
        """事业部回款概览表"""
        dept_stats = df_pay.groupby("事业部")["金额_万"].agg(["sum", "count"]).sort_values("sum", ascending=False)
        total_pay = float(df_pay["金额_万"].sum())
        rows = ""
        for dept in dept_stats.index:
            s = float(dept_stats.loc[dept, "sum"])
            c = int(dept_stats.loc[dept, "count"])
            pct = s / total_pay * 100 if total_pay else 0
            rows += (
                f"<tr><td>{dept}</td>"
                f"<td>{c}<span style='color:var(--text-muted);font-size:10px'>笔</span></td>"
                f"<td>{fmt_wan(s)}</td>"
                f"<td>{completion_html(pct/100)}</td></tr>"
            )
        total_count = int(dept_stats["count"].sum())
        return self.section("事业部回款概览", "sec-teal") + f"""<div class="table-wrap"><table>
  <thead><tr><th>事业部</th><th>笔数</th><th>金额（万元）</th><th>占比</th></tr></thead>
  <tbody>
    <tr class="total"><td>合计</td><td>{total_count}</td><td>{fmt_wan(total_pay)}</td><td>100%</td></tr>
    {rows}
  </tbody></table></div>"""
