"""数据总览页 — Hero + 部门矩阵 + 销售达成景观（纯视图层）
"""
from __future__ import annotations

from .base import BaseRenderer, hero_rings_html, rate_cls
from .utils import fmt_wan, safe_float, range_banner_html
from .page_data import prepare_overview_data, DEPARTMENTS
from .config_loader import get_value
from .components import cell_bg_pct_only

DEPT_COLORS = {"检测": "#2563eb", "信息": "#8b5cf6", "能源": "#f59e0b", "海外": "#0d9488"}


class OverviewPage(BaseRenderer):
    page_id = "overview"
    nav_name = "数据总览"

    def render(self, data) -> str:
        d = prepare_overview_data(data, self.base_dir)

        hero = hero_rings_html(
            d.t_inc, d.t_inc_tgt, d.t_pay, d.t_pay_tgt,
            "", "收入", "回款",
            inc_yoy=d.yoy_inc, pay_yoy=d.yoy_pay, yoy_period=d.yoy_period,
            total_tgt=None, total_label="", show_cust_sales=False,
        )

        return self.wrap_page(
            range_banner_html(d.annual_range)
            + hero
            + self._dept_matrix(d)
            + self._sales_achievement_landscape(d),
            d.date_range
        )

    def _dept_matrix(self, d) -> str:
        thead = (
            "<tr>"
            '<th rowspan="2" class="th-name">事业部</th>'
            '<th colspan="2" class="group-header inc-group">收入（年度）</th>'
            '<th colspan="2" class="group-header pay-group">回款（年度）</th>'
            "</tr>"
            "<tr><th>实际（万）</th><th>完成度</th><th>实际（万）</th><th>完成度</th></tr>"
        )
        rows = ""
        t_inc_act = t_pay_act = 0.0
        for dpt_name in DEPARTMENTS:
            inc_v = d.dept_inc.get(dpt_name, 0)
            pay_v = d.dept_pay.get(dpt_name, 0)
            tgt = d.dept_tgt_inc.get(dpt_name, 0)
            # 有实际金额但无指标 → 完成度 100%
            inc_r = 1.0 if (tgt == 0 and inc_v > 0) else (inc_v / tgt if tgt > 0 else 0)
            pay_r = 1.0 if (tgt == 0 and pay_v > 0) else (pay_v / tgt if tgt > 0 else 0)
            t_inc_act += inc_v; t_pay_act += pay_v
            dcolor = DEPT_COLORS.get(dpt_name, "#94a3b8")
            rows += (
                f'<tr>'
                f'<td class="td-name"><span style="color:{dcolor};font-weight:800">● {dpt_name}</span></td>'
                f'<td class="num-cell" style="font-weight:700">{fmt_wan(inc_v)}</td>'
                + cell_bg_pct_only(inc_r) +
                f'<td class="num-cell" style="font-weight:700">{fmt_wan(pay_v)}</td>'
                + cell_bg_pct_only(pay_r) +
                f'</tr>'
            )

        tgt_sum = sum(d.dept_tgt_inc.values())
        t_inc_r = t_inc_act / tgt_sum if tgt_sum > 0 else 0
        t_pay_r = t_pay_act / tgt_sum if tgt_sum > 0 else 0
        rows += (
            f'<tr class="row-total">'
            f'<td class="td-name td-total">合计（4部门）</td>'
            f'<td class="num-cell" style="font-weight:800">{fmt_wan(t_inc_act)}</td>'
            + cell_bg_pct_only(t_inc_r) +
            f'<td class="num-cell" style="font-weight:800">{fmt_wan(t_pay_act)}</td>'
            + cell_bg_pct_only(t_pay_r) +
            f'</tr>'
        )

        return (
            self.section("部门完成度矩阵 · 4 部门 × 收入/回款", "sec-purple")
            + f'<div class="card" style="padding:10px 12px">'
            f'<div class="table-wrap no-collapse"><table class="yoy-dept-table">'
            f'<thead>{thead}</thead><tbody>{rows}</tbody></table></div>'
            f'<div style="margin-top:6px;font-size:11px;color:var(--text-muted)">'
            f'完成度色阶: ≥80%绿 · 50-80%橙 · 30-50%浅橙 · &lt;30%灰</div></div>'
        )

    def _sales_achievement_landscape(self, d) -> str:
        # 从展示规则.json 读取销售TopN，默认 10
        top_n = int(get_value(self.base_dir, "数据总览", "销售TopN", 10) or 10)
        top_label = f"TOP{top_n}" if top_n > 0 else "全量"

        def _top_card(label, data_dict, total):
            rows = ""
            def _sort_key(item):
                v = float(item[1])
                tgt = safe_float(d.sales_tgt.get(str(item[0]), 0))
                return v / tgt if tgt > 0 else 0
            sorted_data = sorted(data_dict.items(), key=_sort_key, reverse=True)
            if top_n > 0:
                sorted_data = sorted_data[:top_n]
            for i, (name, v) in enumerate(sorted_data, 1):
                v = float(v)
                tgt = safe_float(d.sales_tgt.get(str(name), 0))
                pct = v / tgt * 100 if tgt > 0 else (v / total * 100 if total else 0)
                bar_w = min(pct, 100)
                cls = rate_cls(bar_w / 100)
                rank_tag = f"rank-{i}" if i <= 3 else "rank-n"
                rows += f"""<div class="mini-rate">
  <span class="rank {rank_tag}">{i}</span>
  <span style="flex:1;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{name}</span>
  <div class="bar"><div class="bar-fill {cls}" style="width:{bar_w:.1f}%"><span class="bar-pct">{pct:.1f}%</span></div></div>
  <span class="val">{fmt_wan(v)}</span>
</div>"""
            sub = f"目标达成度 = 个人{label} / 个人目标"
            return f'<div class="card"><div class="card-title">销售{label} {top_label}<span style="font-size:11px;color:var(--text-muted);font-weight:400;margin-left:auto">总 {fmt_wan(total)} 万</span></div><div style="font-size:10px;color:var(--text-muted);margin-bottom:4px">{sub}</div>{rows}</div>'

        top_word = "全量" if top_n == 0 else f"Top {top_n}"
        return (
            self.section(f"销售年度收入/回款达成度 · {top_word}", "sec-green")
            + '<div class="cols-2">'
            + _top_card("收入", d.sales_inc_dict, d.sales_inc_total)
            + _top_card("回款", d.sales_pay_dict, d.sales_pay_total)
            + '</div>'
        )
