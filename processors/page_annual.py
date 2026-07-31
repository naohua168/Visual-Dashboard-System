"""年度达成页 — 总目标 + 进度条 + 客户矩阵表"""
from __future__ import annotations

import pandas as pd

from .base import BaseRenderer, completion_html, rate_cls, hero_rings_html
from .utils import fmt_wan, safe_float, extract_date_range, get_config_range, range_banner_html

DEPARTMENTS = ["检测", "信息", "能源", "海外"]
# Excel 条件格式色阶
COLOR_MAP = {"level-1": "#c00000", "level-2": "#ed7d31", "level-3": "#bf8f00", "level-4": "#00b050"}


class AnnualPage(BaseRenderer):
    page_id = "annual"
    nav_name = "年度达成"

    def render(self, data) -> str:
        df_inc = data.income.copy()
        df_pay = data.payment.copy()
        df_inc_tgt = data.annual_income_targets.copy()
        df_pay_tgt = data.annual_payment_targets.copy()
        df_inc["金额_万"] = df_inc["金额"].apply(safe_float) / 10000.0
        df_pay["金额_万"] = df_pay["金额"].apply(safe_float) / 10000.0

        t_inc = float(df_inc["金额_万"].sum())
        t_pay = float(df_pay["金额_万"].sum())
        t_inc_tgt = sum(safe_float(df_inc_tgt[d].sum()) for d in DEPARTMENTS if d in df_inc_tgt.columns)
        t_pay_tgt = sum(safe_float(df_pay_tgt[d].sum()) for d in DEPARTMENTS if d in df_pay_tgt.columns)
        inc_rate = t_inc / t_inc_tgt if t_inc_tgt else 0
        pay_rate = t_pay / t_pay_tgt if t_pay_tgt else 0

        # 同比 vs 2024 同期：年初(1月) 到 当前最新月份（从累计数据动态推导）
        yoy_inc = None
        yoy_pay = None
        yoy_label = "vs 2024同期"
        cur_start_m = 1
        cur_end_m = 6  # fallback
        if len(df_inc):
            inc_dates = pd.to_datetime(df_inc["日期"], errors="coerce").dropna()
            if len(inc_dates):
                cur_end_m = int(inc_dates.max().month)  # 最新月份（从当月/累计推导）
        yoy_label = f"2026年01-{cur_end_m:02d}月 vs 2024年01-{cur_end_m:02d}月"
        if data.yearly_income is not None and len(data.yearly_income):
            yi = data.yearly_income.copy()
            yi["月"] = pd.to_datetime(yi["日期"], errors="coerce").dt.month
            prev_inc = float(yi[(yi["月"] >= cur_start_m) & (yi["月"] <= cur_end_m)]["金额"].sum()) / 10000.0
            if prev_inc > 0:
                yoy_inc = (t_inc - prev_inc) / prev_inc
        if data.yearly_payment is not None and len(data.yearly_payment):
            yp = data.yearly_payment.copy()
            yp["月"] = pd.to_datetime(yp["日期"], errors="coerce").dt.month
            prev_pay = float(yp[(yp["月"] >= cur_start_m) & (yp["月"] <= cur_end_m)]["金额"].sum()) / 10000.0
            if prev_pay > 0:
                yoy_pay = (t_pay - prev_pay) / prev_pay

        # 客户数/销售数（当年累计，全量）
        inc_cust = pay_cust = inc_sales = pay_sales = 0
        if data.sales_income is not None and len(data.sales_income):
            inc_cust = int(data.sales_income["客户"].nunique()) if "客户" in data.sales_income.columns else 0
            inc_sales = int(data.sales_income["销售"].nunique()) if "销售" in data.sales_income.columns else 0
        if data.sales_payment is not None and len(data.sales_payment):
            pay_cust = int(data.sales_payment["客户"].nunique()) if "客户" in data.sales_payment.columns else 0
            pay_sales = int(data.sales_payment["销售"].nunique()) if "销售" in data.sales_payment.columns else 0

        # ── 顶部 Hero 大数字（年度总目标） ──
        hero = self._hero_block(t_inc_tgt, t_pay_tgt, t_inc, t_pay, inc_rate, pay_rate,
                                 yoy_inc=yoy_inc, yoy_pay=yoy_pay,
                                 inc_cust=inc_cust, pay_cust=pay_cust,
                                 inc_sales=inc_sales, pay_sales=pay_sales,
                                 yoy_period=yoy_label,
                                 show_cust_sales=False)
        # ── 2 张部门完成度卡片（收入+回款），共享同一 click 响应 ──
        dept_cards = self._dept_card_combined(df_inc, df_pay, df_inc_tgt, df_pay_tgt)
        # ── 重要客户矩阵 ──
        matrix = self._lower(df_inc, df_pay, df_inc_tgt, df_pay_tgt)
        date_range = extract_date_range(data.income)
        # 年累计范围（从配置文件读取：1月~月度数据截止月）
        annual_range = get_config_range(self.base_dir, "年度累计")
        banner = range_banner_html(annual_range or date_range)
        return self.wrap_page(banner + hero + dept_cards + matrix, date_range)

    def _hero_block(self, t_inc_tgt, t_pay_tgt, t_inc, t_pay, inc_rate, pay_rate,
                    yoy_inc=None, yoy_pay=None,
                    inc_cust=0, pay_cust=0, inc_sales=0, pay_sales=0,
                    yoy_period="", show_cust_sales=True) -> str:
        """年度总目标 Hero — 信息丰富版：中间显示总指标，不显示客户/销售"""
        toggle = "document.getElementById('annual-inc-card-wrapper').classList.toggle('hidden');document.getElementById('annual-pay-card-wrapper').classList.toggle('hidden');this.parentElement.querySelectorAll('.annual-hero-bar').forEach(b=>b.classList.remove('expanded'));this.classList.add('expanded')"
        total_tgt = t_inc_tgt + t_pay_tgt
        return hero_rings_html(t_inc, t_inc_tgt, t_pay, t_pay_tgt, toggle, "收入", "回款",
                               inc_yoy=yoy_inc, pay_yoy=yoy_pay,
                               inc_cust=inc_cust, pay_cust=pay_cust,
                               inc_sales=inc_sales, pay_sales=pay_sales,
                               yoy_period=yoy_period,
                               total_tgt=total_tgt, total_label="年度总指标",
                               show_cust_sales=show_cust_sales)

    def _dept_card_combined(self, df_inc, df_pay, df_inc_tgt, df_pay_tgt) -> str:
        """2 张卡（收入 + 回款）并排展示，共享同一个 click 响应：点击 Hero 同时展开"""
        t_inc = sum(float(df_inc[df_inc["事业部"] == d]["金额_万"].sum()) for d in DEPARTMENTS)
        t_pay = sum(float(df_pay[df_pay["事业部"] == d]["金额_万"].sum()) for d in DEPARTMENTS)
        t_inc_tgt = sum(safe_float(df_inc_tgt[d].sum()) for d in DEPARTMENTS if d in df_inc_tgt.columns)
        t_pay_tgt = sum(safe_float(df_pay_tgt[d].sum()) for d in DEPARTMENTS if d in df_pay_tgt.columns)
        return f'<div class="cols-2"><div class="hidden" id="annual-inc-card-wrapper">{self._one_metric_card(df_inc, df_inc_tgt, "收入", "annual-inc-card", t_inc, t_inc_tgt)}</div><div class="hidden" id="annual-pay-card-wrapper">{self._one_metric_card(df_pay, df_pay_tgt, "回款", "annual-pay-card", t_pay, t_pay_tgt)}</div></div>'

    def _one_metric_card(self, df, df_tgt, metric: str, card_id: str, total_act: float, total_tgt: float) -> str:
        """单指标卡（4 部门 + 合计）"""
        total_rate = total_act / total_tgt if total_tgt else 0
        total_cls = rate_cls(total_rate)
        rows = ""
        # 4 部门
        for d in DEPARTMENTS:
            act = float(df[df["事业部"] == d]["金额_万"].sum()) if df is not None else 0
            tgt = safe_float(df_tgt[d].sum()) if df_tgt is not None and d in df_tgt.columns else 0
            r = act / tgt if tgt else 0
            cls = rate_cls(r)
            rows += f"""<div class="mini-rate">
  <span style="width:48px;font-weight:600">{d}</span>
  <div class="bar"><div class="bar-fill {cls}" style="width:{min(r*100,100):.1f}%"><span class="bar-pct {cls}">{r*100:.1f}%</span></div></div>
  <span class="val">{fmt_wan(act)}</span>
  <span style="color:var(--text-muted);font-size:11px">/{fmt_wan(tgt)}</span>
</div>"""
        # 合计行
        rows += f"""<div class="mini-rate" style="border-top:2px solid var(--border);padding-top:8px;margin-top:4px">
  <span style="width:48px;font-weight:700">合计</span>
  <div class="bar"><div class="bar-fill {total_cls}" style="width:{min(total_rate*100,100):.1f}%"><span class="bar-pct {total_cls}">{total_rate*100:.1f}%</span></div></div>
  <span class="val">{fmt_wan(total_act)}</span>
  <span style="color:var(--text-muted);font-size:11px">/{fmt_wan(total_tgt)}</span>
</div>"""
        return f"""<div class="card" id="{card_id}">
  <div class="card-title">{metric}完成度 · 年度目标 {fmt_wan(total_tgt)} 万</div>
  {rows}
</div>"""

    def _lower(self, df_inc, df_pay, df_inc_tgt, df_pay_tgt) -> str:
        """重要客户达成表 — 收入/回款 双导航 tab 切换"""
        inc_tgt_pivot = df_inc_tgt.groupby("客户")[[d for d in DEPARTMENTS if d in df_inc_tgt.columns]].sum()
        inc_tgt_pivot["合计"] = inc_tgt_pivot.sum(axis=1)
        pay_tgt_pivot = df_pay_tgt.groupby("客户")[[d for d in DEPARTMENTS if d in df_pay_tgt.columns]].sum()
        pay_tgt_pivot["合计"] = pay_tgt_pivot.sum(axis=1)
        inc_pivot = df_inc.pivot_table(index="客户", columns="事业部", values="金额_万", aggfunc="sum", fill_value=0)
        inc_pivot["合计"] = inc_pivot.sum(axis=1)
        pay_pivot = df_pay.pivot_table(index="客户", columns="事业部", values="金额_万", aggfunc="sum", fill_value=0)
        pay_pivot["合计"] = pay_pivot.sum(axis=1)
        # 取收入目标中金额最大的客户排序
        important = [c for c in inc_tgt_pivot.index if inc_tgt_pivot.loc[c, "合计"] > 0]
        important.sort(key=lambda c: inc_tgt_pivot.loc[c, "合计"], reverse=True)
        important = important[:20]
        t_inc_all = float(df_inc["金额_万"].sum())
        t_pay_all = float(df_pay["金额_万"].sum())
        imp_i = sum(float(inc_pivot.loc[c, "合计"]) for c in important if c in inc_pivot.index)
        imp_p = sum(float(pay_pivot.loc[c, "合计"]) for c in important if c in pay_pivot.index)
        imp_i_tgt = sum(float(inc_tgt_pivot.loc[c, "合计"]) for c in important if c in inc_tgt_pivot.index)
        imp_p_tgt = sum(float(pay_tgt_pivot.loc[c, "合计"]) for c in important if c in pay_tgt_pivot.index)

        inc_table = self._matrix("收入", inc_pivot, inc_tgt_pivot, important, imp_i, imp_i_tgt, t_inc_all)
        pay_table = self._matrix("回款", pay_pivot, pay_tgt_pivot, important, imp_p, imp_p_tgt, t_pay_all)

        # 导航 tab + 表格容器
        return f"""<div class="section-title sec-sky">重要客户年度达成 · 收入/回款（万元）</div>
<div class="cust-tabs">
  <span class="cust-tab active inc" onclick="document.getElementById('annual-cust-inc').classList.remove('hidden');document.getElementById('annual-cust-pay').classList.add('hidden');this.parentElement.querySelectorAll('.cust-tab').forEach(t=>t.classList.remove('active'));this.classList.add('active')">收入</span>
  <span class="cust-tab pay" onclick="document.getElementById('annual-cust-inc').classList.add('hidden');document.getElementById('annual-cust-pay').classList.remove('hidden');this.parentElement.querySelectorAll('.cust-tab').forEach(t=>t.classList.remove('active'));this.classList.add('active')">回款</span>
</div>
<div id="annual-cust-inc">{inc_table}</div>
<div id="annual-cust-pay" class="hidden">{pay_table}</div>"""

    def _matrix(self, label, act_pivot, tgt_pivot, customers, imp_total, imp_tgt, all_total) -> str:
        """重要客户矩阵表 — 目标/实际/达成率，格子按百分比实色填充+左右布局"""
        def cell(act, tgt, total, is_total_col=False):
            """生成单元格：左=百分比 / 右=完成+指标两行（合计列也按达成度显示半透明数据条）"""
            if act == 0 and tgt == 0:
                return '<td class="td-empty">—</td>'
            r = act / tgt if tgt else 0
            pct_num = min(r * 100, 100)
            pct_label = f"{r*100:.0f}%"
            if r >= 1:
                pct_cls, fill_var = " achieved", "#22c55e"
            elif r >= 0.5:
                pct_cls, fill_var = "", "#fb923c"
            elif r > 0:
                pct_cls, fill_var = " low", "#fdba74"
            else:
                pct_cls, fill_var = "", "#f1f5f9"
            empty_cls = " is-empty" if r == 0 else ""
            total_cls = " is-total" if is_total_col else ""
            return (
                f'<td class="cell-bg{empty_cls}{total_cls}" style="--pct:{pct_num:.1f}%;--fill:{fill_var}">'
                f'<div class="fill-bg"></div>'
                f'<div class="cell-text">'
                f'<span class="cell-pct{pct_cls}">{pct_label}</span>'
                f'<div class="cell-main"><span class="cell-compact"><span class="cell-act-val">{fmt_wan(act)}</span><span class="sep">/</span><span class="cell-tgt-val">{fmt_wan(tgt)}</span></span></div>'
                f'</div></td>'
            )

        # 表头
        h = f'<tr><th class="th-name">客户</th>' + "".join(f"<th>{d}</th>" for d in DEPARTMENTS) + '<th class="th-name th-total">合计</th></tr>'

        # 合计行
        cells = [f'<td class="td-name td-total">合计（{len(customers)}家）</td>']
        for d in DEPARTMENTS:
            a = sum(float(act_pivot.loc[c, d]) for c in customers if c in act_pivot.index and d in act_pivot.columns) if customers else 0
            tg = sum(float(tgt_pivot.loc[c, d]) for c in customers if c in tgt_pivot.index)
            cells.append(cell(a, tg, imp_total, is_total_col=False))
        cells.append(cell(imp_total, imp_tgt, imp_total, is_total_col=True))
        tr = f'<tr class="row-total">{"".join(cells)}</tr>'

        # 数据行
        rows = ""
        for i, c in enumerate(customers):
            cs = [f'<td class="td-name"><span class="row-num">{i+1}</span>{c}</td>']
            for d in DEPARTMENTS:
                a = float(act_pivot.loc[c, d]) if c in act_pivot.index and d in act_pivot.columns else 0
                tg = float(tgt_pivot.loc[c, d]) if c in tgt_pivot.index else 0
                cs.append(cell(a, tg, 0, is_total_col=False))
            a_t = float(act_pivot.loc[c, "合计"]) if c in act_pivot.index else 0
            tg_t = float(tgt_pivot.loc[c, "合计"]) if c in tgt_pivot.index else 0
            cs.append(cell(a_t, tg_t, 0, is_total_col=True))
            rows += '<tr class="row-data">' + "".join(cs) + '</tr>'

        return (
            f'<div class="table-wrap ann-matrix-wrap no-collapse">'
            f'<table class="ann-matrix"><thead>{h}</thead><tbody>{tr}{rows}</tbody></table>'
            f'</div>'
            f'<div style="font-size:11px;color:var(--text-muted);margin-top:6px">每格：实际金额 / 目标金额 / 达成率 · 全公司{label}合计 <strong style="color:var(--accent)">{fmt_wan(all_total)}</strong> 万</div>'
        )
