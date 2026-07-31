"""年度同比页 — 事业部同比 + 重要客户同比"""
from __future__ import annotations

import pandas as pd

from .base import BaseRenderer, yoy_html
from .utils import fmt_wan, fmt_yoy, safe_float, extract_date_range, get_config_range, range_banner_html

DEPARTMENTS = ["检测", "信息", "能源", "海外"]


def yoy_arrow(cur: float, prev: float) -> str:
    """生成同比趋势箭头 SVG：↑ 增长 / ↓ 下降 / − 持平"""
    if prev == 0 and cur == 0:
        return '<span class="yoy-arrow flat">−</span>'
    if cur > prev:
        return '<span class="yoy-arrow up">▲</span>'
    if cur < prev:
        return '<span class="yoy-arrow down">▼</span>'
    return '<span class="yoy-arrow flat">−</span>'


class YoyPage(BaseRenderer):
    page_id = "yoy"
    nav_name = "年度同比"

    def render(self, data) -> str:
        # 年累计范围（从配置文件读取：1月~月度数据截止月）
        annual_range = get_config_range(self.base_dir, "年度累计")
        banner = range_banner_html(annual_range)
        df_inc = data.income.copy()
        df_pay = data.payment.copy()
        df_inc["金额_万"] = df_inc["金额"].apply(safe_float) / 10000.0
        df_pay["金额_万"] = df_pay["金额"].apply(safe_float) / 10000.0

        if not data.has_yearly_baseline:
            return self.wrap_page(
                banner + self.section("同比分析", "sec-purple")
                + '<div class="empty">年基线数据（2024）未就绪</div>'
            , extract_date_range(data.income))

        # 起止月份：优先从 "年度累计" 配置读取（与其他页面保持一致）
        cur_start_m = 1
        cur_end_m = 6
        if annual_range and "~" in annual_range:
            try:
                cur_start_m = int(annual_range.split("~")[0].strip().split("-")[1])
                cur_end_m = int(annual_range.split("~")[1].strip().split("-")[1])
            except (IndexError, ValueError):
                pass
        cur_months = set(range(cur_start_m, cur_end_m + 1))
        cur_dates = pd.to_datetime(df_inc["日期"], errors="coerce").dropna()
        cur_year = int(cur_dates.min().year) if len(cur_dates) else pd.Timestamp.now().year
        if cur_start_m == cur_end_m:
            ml = f"{cur_start_m}月"
        else:
            ml = f"{cur_start_m}-{cur_end_m}月"

        pi = data.yearly_income.copy()
        pp = data.yearly_payment.copy()
        if len(cur_months) > 0 and "日期" in pi.columns:
            pd_dates = pd.to_datetime(pi["日期"], errors="coerce")
            mask = [pd.notna(d) and d.month in cur_months for d in pd_dates]
            pi = pi[mask].copy()
        if len(cur_months) > 0 and "日期" in pp.columns:
            pd_dates = pd.to_datetime(pp["日期"], errors="coerce")
            mask = [pd.notna(d) and d.month in cur_months for d in pd_dates]
            pp = pp[mask].copy()

        pi["金额_万"] = pi["金额"].apply(safe_float) / 10000.0
        pp["金额_万"] = pp["金额"].apply(safe_float) / 10000.0
        ci = df_inc["金额_万"].sum(); pvi = pi["金额_万"].sum()
        cp = df_pay["金额_万"].sum(); pvp = pp["金额_万"].sum()

        period = f"{cur_year}年{ml} vs 2024年{ml}"

        # ── 顶部：4 卡 KPI ──
        kpi = self._kpi_block(ci, pvi, cp, pvp, cur_year)
        # ── 同比周期标识 ──
        period_chip = f"""<div class="period-chip">
  <span class="period-tag">同比周期</span>
  <span class="period-text">{period}</span>
</div>"""
        # ── 事业部同比表（增强版带箭头） ──
        dt = self._dept_table(df_inc, pi, df_pay, pp, ci, pvi, cp, pvp, cur_year)
        # ── 客户同比矩阵（收入/回款 tab 切换） ──
        ct_inc = self._cust_matrix(df_inc, pi, cur_year, "收入")
        ct_pay = self._cust_matrix(df_pay, pp, cur_year, "回款")
        ct_tabs = (
            f'<div class="yoy-cust-tabs">'
            f'<div class="tab-header">'
            f'<button class="tab-btn active" data-tab="yoy-inc" onclick="switchTab(this)">收入同比</button>'
            f'<button class="tab-btn" data-tab="yoy-pay" onclick="switchTab(this)">回款同比</button>'
            f'</div>'
            f'<div id="yoy-inc" class="tab-panel active">{ct_inc}</div>'
            f'<div id="yoy-pay" class="tab-panel">{ct_pay}</div>'
            f'</div>'
        )
        return self.wrap_page(banner + kpi + period_chip + dt + ct_tabs, extract_date_range(data.income))

    def _kpi_block(self, ci, pvi, cp, pvp, cy) -> str:
        """2 张同比对比卡（深色稳重版）：上涨=红色，下降=绿色"""
        yoy_inc_pct = ((ci - pvi) / pvi * 100) if pvi else 0
        yoy_pay_pct = ((cp - pvp) / pvp * 100 if pvp else 0)
        inc_cls = "up" if yoy_inc_pct > 0 else "down" if yoy_inc_pct < 0 else "flat"
        pay_cls = "up" if yoy_pay_pct > 0 else "down" if yoy_pay_pct < 0 else "flat"
        max_inc = max(ci, pvi) or 1
        max_pay = max(cp, pvp) or 1
        return f"""<div class="cols-2">
  <div class="yoy-big-card {inc_cls}">
    <div class="yoy-big-info">
      <div class="yoy-big-label">收入同比</div>
      <div class="yoy-big-pct">
        <span class="yoy-arrow {inc_cls}">{yoy_arrow(ci, pvi)}</span>
        <span class="yoy-big-pct-num">{yoy_inc_pct:+.1f}%</span>
      </div>
    </div>
    <div class="yoy-big-compare">
      <div class="yoy-cmp-item">
        <div class="yoy-cmp-header">
          <span class="yoy-cmp-label">{cy}年（当期）</span>
          <span class="yoy-cmp-val">{fmt_wan(ci)}<span class="yoy-cmp-unit">万</span></span>
        </div>
        <div class="yoy-cmp-bar"><div class="yoy-cmp-fill cur {inc_cls}" style="width:{ci/max_inc*100:.1f}%"></div></div>
      </div>
      <div class="yoy-cmp-item">
        <div class="yoy-cmp-header">
          <span class="yoy-cmp-label">2024年（同期）</span>
          <span class="yoy-cmp-val">{fmt_wan(pvi)}<span class="yoy-cmp-unit">万</span></span>
        </div>
        <div class="yoy-cmp-bar"><div class="yoy-cmp-fill prev" style="width:{pvi/max_inc*100:.1f}%"></div></div>
      </div>
    </div>
  </div>
  <div class="yoy-big-card {pay_cls}">
    <div class="yoy-big-info">
      <div class="yoy-big-label">回款同比</div>
      <div class="yoy-big-pct">
        <span class="yoy-arrow {pay_cls}">{yoy_arrow(cp, pvp)}</span>
        <span class="yoy-big-pct-num">{yoy_pay_pct:+.1f}%</span>
      </div>
    </div>
    <div class="yoy-big-compare">
      <div class="yoy-cmp-item">
        <div class="yoy-cmp-header">
          <span class="yoy-cmp-label">{cy}年（当期）</span>
          <span class="yoy-cmp-val">{fmt_wan(cp)}<span class="yoy-cmp-unit">万</span></span>
        </div>
        <div class="yoy-cmp-bar"><div class="yoy-cmp-fill cur {pay_cls}" style="width:{cp/max_pay*100:.1f}%"></div></div>
      </div>
      <div class="yoy-cmp-item">
        <div class="yoy-cmp-header">
          <span class="yoy-cmp-label">2024年（同期）</span>
          <span class="yoy-cmp-val">{fmt_wan(pvp)}<span class="yoy-cmp-unit">万</span></span>
        </div>
        <div class="yoy-cmp-bar"><div class="yoy-cmp-fill prev" style="width:{pvp/max_pay*100:.1f}%"></div></div>
      </div>
    </div>
  </div>
</div>"""
    def _dept_table(self, di, dpi, dp, dpp, ci, pvi, cp, pvp, cy) -> str:
        """事业部同比表 — 清晰双维度对比：收入组+回款组"""
        rows = ""
        for d in DEPARTMENTS:
            ci_d = float(di[di["事业部"]==d]["金额_万"].sum()) if "事业部" in di.columns else 0
            pi_d = float(dpi[dpi["事业部"]==d]["金额_万"].sum()) if "事业部" in dpi.columns else 0
            cp_d = float(dp[dp["事业部"]==d]["金额_万"].sum()) if "事业部" in dp.columns else 0
            pp_d = float(dpp[dpp["事业部"]==d]["金额_万"].sum()) if "事业部" in dpp.columns else 0

            # 收入同比计算
            inc_pct = (ci_d - pi_d) / pi_d * 100 if pi_d else 0
            inc_cls = "up" if inc_pct > 0 else "down" if inc_pct < 0 else "flat"
            inc_arrow = yoy_arrow(ci_d, pi_d)
            # 回款同比计算
            pay_pct = (cp_d - pp_d) / pp_d * 100 if pp_d else 0
            pay_cls = "up" if pay_pct > 0 else "down" if pay_pct < 0 else "flat"
            pay_arrow = yoy_arrow(cp_d, pp_d)

            inc_big = ' data-big="true"' if abs(inc_pct) >= 50 else ""
            pay_big = ' data-big="true"' if abs(pay_pct) >= 50 else ""
            rows += (
                '<tr>'
                f'<td class="dept-name"><strong>{d}</strong></td>'
                # ── 收入组 ──
                f'<td class="num-cell">{fmt_wan(ci_d)}</td>'
                f'<td class="num-cell muted">{fmt_wan(pi_d)}</td>'
                f'<td class="yoy-cell {inc_cls}"{inc_big}>'
                f'<span class="yoy-pct">{inc_arrow}{inc_pct:+.0f}%</span>'
                f'</td>'
                # ── 回款组 ──
                f'<td class="num-cell">{fmt_wan(cp_d)}</td>'
                f'<td class="num-cell muted">{fmt_wan(pp_d)}</td>'
                f'<td class="yoy-cell {pay_cls}"{pay_big}>'
                f'<span class="yoy-pct">{pay_arrow}{pay_pct:+.0f}%</span>'
                f'</td>'
                '</tr>'
            )

        h = (
            "<tr>"
            "<th rowspan='2'>事业部</th>"
            "<th colspan='3' class='group-header inc-group'>收入</th>"
            "<th colspan='3' class='group-header pay-group'>回款</th>"
            "</tr>"
            "<tr>"
            f"<th>{cy}年</th><th>2024年</th><th>同比</th>"
            f"<th>{cy}年</th><th>2024年</th><th>同比</th>"
            "</tr>"
        )
        return (
            self.section("事业部同比对比（万元）", "sec-purple")
            + f'''<div class="table-wrap no-collapse">
<table class="yoy-dept-table">
<thead>{h}</thead>
<tbody>{rows}</tbody>
</table>
</div>'''
        )

    def _cust_matrix(self, di, dpi, cy, label: str) -> str:
        """客户同比矩阵 — 每格：同比徽章+当期金额"""
        cp = di.pivot_table(index="客户", columns="事业部", values="金额_万", aggfunc="sum", fill_value=0)
        cp["合计"] = cp.sum(axis=1)
        pp = dpi.pivot_table(index="客户", columns="事业部", values="金额_万", aggfunc="sum", fill_value=0) if "事业部" in dpi.columns else None
        if pp is not None:
            pp["合计"] = pp.sum(axis=1)
        top = cp.sort_values("合计", ascending=False).head(15).index.tolist()
        if not top:
            return ""

        def amount_cell(cur, prev):
            """金额单元格 — 竖排两个数字：今年在上、去年在下，浅色区分"""
            if cur == 0 and prev == 0:
                return '<td class="mx-amount-cell td-empty">—</td>'
            cy_short = str(cy)[2:4] if cy else "26"
            return (
                f'<td class="mx-amount-cell">'
                f'<div class="mx-amount-pair">'
                f'<div class="mx-amt-row mx-cur-row">'
                f'<span class="mx-amt-label">当年</span>'
                f'<span class="mx-amt-val">{fmt_wan(cur)}</span>'
                f'</div>'
                f'<div class="mx-amt-row mx-prev-row">'
                f'<span class="mx-amt-label">往年</span>'
                f'<span class="mx-amt-val">{fmt_wan(prev)}</span>'
                f'</div>'
                f'</div>'
                f'</td>'
            )

        def yoy_cell(cur, prev):
            """同比单元格 — 大号百分比 + 彩色背景卡片，强度等级着色（更直观）"""
            if cur == 0 and prev == 0:
                return '<td class="mx-yoy-cell td-empty">—</td>'
            pct = (cur - prev) / prev * 100 if prev else 0
            cls = "up" if pct > 0 else "down" if pct < 0 else "flat"
            mag = abs(pct)
            if mag >= 100:
                sev = "x"
            elif mag >= 50:
                sev = "l"
            elif mag >= 10:
                sev = "m"
            else:
                sev = "s"
            arrow = "▲" if cls == "up" else "▼" if cls == "down" else "−"
            return (
                f'<td class="mx-yoy-cell {cls} sev-{sev}">'
                f'<div class="mx-yoy-fill"></div>'
                f'<div class="mx-badge"><span class="mx-arrow">{arrow}</span><span class="mx-pct">{pct:+.0f}%</span></div>'
                f'</td>'
            )

        def mcell(cur, prev):
            """一组合并调用：金额 + 同比 两个 td"""
            return amount_cell(cur, prev) + yoy_cell(cur, prev)

        # 合计行
        tc = [f'<td class="row-total-label">合计（前15）</td>']
        for d in DEPARTMENTS:
            cv = sum(float(cp.loc[c, d]) for c in top if c in cp.index and d in cp.columns)
            pv = sum(float(pp.loc[c, d]) for c in top if pp is not None and c in pp.index and d in pp.columns)
            tc.append(mcell(cv, pv))
        cv_t = sum(float(cp.loc[c, "合计"]) for c in top if c in cp.index)
        pv_t = sum(float(pp.loc[c, "合计"]) for c in top if pp is not None and c in pp.index)
        tc.append(mcell(cv_t, pv_t))
        tr = f'<tr class="row-total">{"".join(tc)}</tr>'

        rows = ""
        for i, c in enumerate(top, 1):
            cs = [f'<td class="td-name"><span class="row-num">{i}</span>{c}</td>']
            for d in DEPARTMENTS:
                cv = float(cp.loc[c, d]) if c in cp.index and d in cp.columns else 0
                pv = float(pp.loc[c, d]) if pp is not None and c in pp.index and d in pp.columns else 0
                cs.append(mcell(cv, pv))
            cv_t = float(cp.loc[c, "合计"]) if c in cp.index else 0
            pv_t = float(pp.loc[c, "合计"]) if pp is not None and c in pp.index else 0
            cs.append(mcell(cv_t, pv_t))
            rows += f"<tr class='row-data'>{''.join(cs)}</tr>"
        # 表头：双层 — 客户 (rowspan=2) | 4事业部 (colspan=2) | 合计 (colspan=2)
        # 副表头: 金额 | 同比
        h_row1 = '<tr><th rowspan="2" class="th-name">客户</th>'
        for d in DEPARTMENTS:
            h_row1 += f'<th colspan="2" class="th-dept-group">{d}</th>'
        h_row1 += '<th colspan="2" class="th-dept-group th-dept-total">合计</th></tr>'

        h_row2 = '<tr>'
        # 每个事业部下面：金额 + 同比
        for _ in DEPARTMENTS:
            h_row2 += '<th class="th-sub th-sub-amount">金额</th><th class="th-sub th-sub-yoy">同比</th>'
        # 合计列下面：金额 + 同比
        h_row2 += '<th class="th-sub th-sub-amount">金额</th><th class="th-sub th-sub-yoy">同比</th></tr>'

        h = h_row1 + h_row2
        return (
            self.section(f"重要客户{label}同比 · 按事业部分列（万元，前 15）", "sec-purple")
            + f'''<div class="table-wrap no-collapse">
<table class="yoy-matrix-table">
<thead>{h}</thead>
<tbody>{tr}{rows}</tbody>
</table>
</div>'''
        )
