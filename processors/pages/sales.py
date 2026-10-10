# Author: naohua168 <bai_bai168@qq.com>
"""销售达成页 — 3 卡片 × 收入/回款 双视图（纯视图层）
"""
from __future__ import annotations

import json

from ..base import BaseRenderer, hero_rings_html
from ..utils import fmt_wan, range_banner_html
from ..components import cell_bg_html, cust_tab_bar
from ..data_prep import prepare_sales_data
from ..data_utils import DEPARTMENTS
from ..sales_pending import build_pending_modal
from .sales_scripts import _card3_js_script
from .sales_modal import _sales_modal_css, _sales_modal_html


class SalesPage(BaseRenderer):
    page_id = "sales"
    nav_name = "销售达成"

    def render(self, data) -> str:
        d = prepare_sales_data(data, self.base_dir)

        hero = hero_rings_html(
            d.total_inc, d.total_target, d.total_pay, d.total_pay_target,
            "", "收入", "回款",
            inc_yoy=d.yoy_inc, pay_yoy=d.yoy_pay, yoy_period=d.yoy_period,
            total_tgt=None, total_label="",
            show_cust_sales=False,
        )

        parts = [range_banner_html(d.sales_range) + hero]

        # 待确认客户触发按钮（打开右侧滑入面板）
        if d.pending_count > 0:
            parts.append(
                f'<div style="display:flex;justify-content:flex-end;margin:10px 0 4px">'
                f'<button class="pending-trigger-btn" onclick="openPendingModal()">'
                f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-2px;margin-right:6px"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/><path d="M11 8v6"/><path d="M8 11h6"/></svg>'
                f'待确认客户 <b>{d.pending_cust_n}</b> 家 · {fmt_wan(d.pending_total_inc + d.pending_total_pay)} 万</button>'
                f'</div>'
                f'<style>.pending-trigger-btn{{display:inline-flex;align-items:center;padding:0.4375rem 1rem;font-size:0.8125rem;font-weight:600;color:#fff;background:linear-gradient(135deg,#fbbf24,#f59e0b);border:none;border-radius:0.5rem;cursor:pointer;box-shadow:0 0.125rem 0.5rem rgba(245,158,11,.35);transition:all .15s}}.pending-trigger-btn:hover{{transform:translateY(-1px);box-shadow:0 0.25rem 0.875rem rgba(245,158,11,.45)}}.pending-trigger-btn b{{font-size:0.9375rem;margin:0 0.125rem}}</style>'
            )

        # 卡片 1
        parts.append(self._card1(d))
        # 卡片 2
        parts.append(self._card2(d))
        # 卡片 3
        parts.append(self._card3(d))
        # 待确认
        if d.pending_count > 0:
            pending_html = build_pending_modal(
                d.pending_df, d.pending_count, d.pending_total_inc, d.pending_total_pay
            )
            if pending_html:
                parts.append(pending_html)

        return self.wrap_page("".join(parts), d.date_range)

    def _card1(self, d) -> str:
        """销售年度达成 — 左右双列：收入 | 回款，按各自完成度排序。整行可点击弹出客户详情"""

        def _sorted_sales(by_sales, tgt_dict):
            # 销售列表 = 指标表里的销售 ∪ 实际数据里出现过的销售（去重），保证 0 指标销售也展示
            all_sales = set(map(str, tgt_dict.keys())) | set(map(str, by_sales.keys()))
            all_sales.discard("待确认")
            all_sales = [s for s in all_sales if s]
            def _key(s):
                ti = float(tgt_dict.get(s, 0) or 0)
                act = float(by_sales.get(s, 0) or 0)
                # 指标>0 的销售按完成率降序排在前；指标=0 但有实际金额的按实际金额降序排在后
                if ti > 0:
                    return (1, act / ti, act)
                return (0, act, act)
            return sorted(all_sales, key=_key, reverse=True)

        def _col(by_sales, title, total_act, total_tgt, tgt_dict, metric):
            # 合计完成率口径（2026-09-29 修）：分子只算**有指标**的销售 —— 否则 0 指标销售
            # 的实际金额会把合计完成率顶到 >100%（与个人行口径不一致）。
            # 显示的「实际合计」仍是全部实际金额，不受影响。
            act_for_rate = sum(float(by_sales.get(str(s), 0) or 0)
                               for s, ti in tgt_dict.items() if float(ti or 0) > 0)
            sales_sorted = _sorted_sales(by_sales, tgt_dict)
            rows = ""
            for s_name in sales_sorted:
                ti = float(tgt_dict.get(str(s_name), 0) or 0)
                act = float(by_sales.get(s_name, 0) or 0)
                if ti > 0:
                    rate = act / ti
                    pct = round(rate * 100)
                    if rate >= 0.8:
                        bar_cls = 'level-4'
                    elif rate >= 0.5:
                        bar_cls = 'level-3'
                    elif rate >= 0.3:
                        bar_cls = 'level-2'
                    else:
                        bar_cls = 'level-1'
                    bar_w = min(rate * 100, 100)
                    bar_html = (
                        f'<div class="bar"><div class="bar-fill {bar_cls}" style="width:{bar_w:.1f}%">'
                        f'<span class="bar-pct">{pct}%</span></div></div>'
                    )
                    tgt_text = f'/{fmt_wan(ti)}'
                else:
                    # 0 指标：进度条空、百分比 "—"（分母为 0 无法计算完成率）
                    bar_html = '<div class="bar"><div class="bar-fill" style="width:0%"><span class="bar-pct">—</span></div></div>'
                    tgt_text = '/—'
                rows += (
                    f'<div class="mini-rate sales-clickable"'
                    f' data-sales="{s_name}" data-metric="{metric}"'
                    f' onclick="openSalesModal(this, \'{s_name}\',\'{metric}\')"'
                    f' title="点击查看 {s_name} 客户达成详情">'
                    f'<span class="sales-name">{s_name}</span>'
                    f'{bar_html}'
                    f'<span class="val">{fmt_wan(act)}</span>'
                    f'<span class="tgt">{tgt_text}</span>'
                    f'</div>'
                )
            # 合计行（有实际无指标 → 100%）
            total_rate = (act_for_rate / total_tgt) if total_tgt else (1.0 if total_act > 0 else 0.0)
            rpct = round(total_rate * 100)
            summary = (
                f'<div class="mini-rate summary-rate">'
                f'<span class="sales-name" style="font-weight:700">合计</span>'
                f'<div class="bar"><div class="bar-fill level-4" style="width:{min(total_rate*100,100):.1f}%"><span class="bar-pct">{rpct}%</span></div></div>'
                f'<span class="val">{fmt_wan(total_act)}</span>'
                f'<span class="tgt">/{fmt_wan(total_tgt)}</span>'
                f'</div>'
            )
            return (
                f'<div class="card1-col">'
                f'<div class="card1-col-title">{title}</div>'
                f'<div class="mini-rate-list">{summary}{rows}</div></div>'
            )

        return (
            f'<div class="section-title sec-green">销售年度达成 · 个人收入/回款 vs 年度目标（点击销售查看客户达成详情）</div>'
            f'<div class="card back-white"><div class="card1-flex">'
            f'{_col(d.sales_inc, "收入（不含税）", d.total_inc_split, d.total_target, d.sales_targets, "inc")}'
            f'{_col(d.sales_pay, "回款（含税）", d.total_pay_split, d.total_pay_target, d.sales_payment_targets, "pay")}'
            f'</div></div>'
            + _sales_modal_css()
            + _sales_modal_html()
        )

    def _card2(self, d) -> str:
        """销售 × 事业部 cell-bg 矩阵 — 目标直接用 sales_dept_tgt（按销售×部门精确指标）"""
        def _matrix(piv_data, all_sales):
            h = '<tr><th class="th-name">销售</th>' + "".join(
                f"<th>{dpt}</th>" for dpt in DEPARTMENTS
            ) + '<th class="th-name th-total">合计</th></tr>'
            rows = ""

            # 全部销售都展示（指标=0 也行，cell-bg 显示 "—"）
            for s_name in all_sales:
                s_total_tgt = d.sales_targets.get(str(s_name), 0)
                s_dept_tgt = d.sales_dept_tgt.get(str(s_name), {})
                cs = [f'<td class="td-name">{s_name}</td>']
                for dpt in DEPARTMENTS:
                    act = piv_data.get(str(s_name), {}).get(dpt, 0) if isinstance(piv_data, dict) else 0
                    tgt_part = s_dept_tgt.get(dpt, 0)
                    cs.append(cell_bg_html(act, tgt_part, fmt_fn=fmt_wan))
                act_t = sum(piv_data.get(str(s_name), {}).get(dpt, 0) for dpt in DEPARTMENTS) if isinstance(piv_data, dict) else 0
                cs.append(cell_bg_html(act_t, s_total_tgt, is_total_col=True, fmt_fn=fmt_wan))
                rows += f'<tr class="row-data">{"".join(cs)}</tr>'

            if not rows:
                return '<p style="color:var(--text-muted);padding:20px;text-align:center">无销售目标数据</p>'
            return (
                f'<div class="table-wrap ann-matrix-wrap no-collapse">'
                f'<table class="ann-matrix"><thead>{h}</thead><tbody>{rows}</tbody></table></div>'
            )

        inc_matrix = _matrix(d.inc_by_sd, d.sales_list)
        pay_matrix = _matrix(d.pay_by_sd, d.pay_sales_list)
        return (
            f'<div class="section-title sec-purple">事业部完成度 · 销售 × 事业部 矩阵</div>'
            + cust_tab_bar("sales-card2-inc", "sales-card2-pay")
            + f'<div id="sales-card2-inc"><div class="card">{inc_matrix}</div></div>'
            f'<div id="sales-card2-pay" class="hidden"><div class="card">{pay_matrix}</div></div>'
        )

    def _card3(self, d) -> str:
        """销售×客户达成度 — 母公司→子公司 聚合视图（JS 驱动下拉）"""
        all_sales = sorted(set(d.sales_list))
        parent_json = json.dumps(d.sc3_by_parent, ensure_ascii=False)
        sub_tgt_json = json.dumps(d.sc3_tgts, ensure_ascii=False)
        parent_tgt_json = json.dumps(d.sc3_tgts_by_parent, ensure_ascii=False)
        # 按销售拆分的目标（销售个人比例口径）
        sub_tgt_by_sales_json = json.dumps(d.sc3_tgts_by_sales, ensure_ascii=False)
        parent_tgt_by_sales_json = json.dumps(d.sc3_tgts_by_parent_by_sales, ensure_ascii=False)
        parent_cfg_total_json = json.dumps(d.sc3_parent_cfg_total, ensure_ascii=False)
        sales_owned_json = json.dumps(d.sales_owned_subs, ensure_ascii=False)

        kpi_html = (
            f'<div class="card3-kpi">'
            f'<span>收入实际 <b>{fmt_wan(d.total_inc)}</b>万</span><span class="dot">·</span>'
            f'<span>收入目标 <b>{fmt_wan(d.total_target)}</b>万</span><span class="dot">·</span>'
            f'<span>回款实际 <b>{fmt_wan(d.total_pay)}</b>万</span><span class="dot">·</span>'
            f'<span>回款目标 <b>{fmt_wan(d.total_pay_target)}</b>万</span></div>'
        )

        js_script = _card3_js_script(parent_json, sub_tgt_json, parent_tgt_json, sub_tgt_by_sales_json, parent_tgt_by_sales_json, parent_cfg_total_json, sales_owned_json)

        return (
            f'<div class="section-title sec-green">销售客户达成 · 母公司→子公司 矩阵（子公司合计 = 母公司合计）</div>'
            f'<div class="card">{kpi_html}'
            f'<div style="margin-bottom:8px;display:flex;align-items:center;gap:8px">'
            f'<label style="font-size:12px;color:var(--text-muted)">选择销售：</label>'
            f'<select id="sc3SalesSel" onchange="switchSc3Sales()" style="padding:4px 8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;background:#fff;color:#1e293b">'
            + f'<option value="" disabled selected>-- 请选择销售 --</option>'
            + "".join(f'<option value="{s}">{s}</option>' for s in sorted(all_sales))
            + f'</select>'
            + '<div class="cust-tabs">'
            + '<span class="cust-tab active inc" onclick="switchSc3Metric(\'inc\');document.getElementById(\'sc3-inc-matrix\').classList.remove(\'hidden\');document.getElementById(\'sc3-pay-matrix\').classList.add(\'hidden\');this.parentElement.querySelectorAll(\'.cust-tab\').forEach(t=>t.classList.remove(\'active\'));this.classList.add(\'active\')">收入</span>'
            + '<span class="cust-tab pay" onclick="switchSc3Metric(\'pay\');document.getElementById(\'sc3-inc-matrix\').classList.add(\'hidden\');document.getElementById(\'sc3-pay-matrix\').classList.remove(\'hidden\');this.parentElement.querySelectorAll(\'.cust-tab\').forEach(t=>t.classList.remove(\'active\'));this.classList.add(\'active\')">回款</span>'
            + '</div>'
            + f'</div>'
            f'<div id="sc3-inc-matrix"><div class="table-wrap ann-matrix-wrap no-collapse">'
            f'<table class="ann-matrix" id="sc3IncTable"></table></div></div>'
            f'<div id="sc3-pay-matrix" class="hidden"><div class="table-wrap ann-matrix-wrap no-collapse">'
            f'<table class="ann-matrix" id="sc3PayTable"></table></div></div>'
            f'</div>'
            + js_script
        )


# ═══════════════════════════════════════════════════════════════
# 卡片 3 JS 生成器（母公司→子公司聚合视图）
# ═══════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════
# 销售客户详情弹窗 — CSS / HTML / JS
# ═══════════════════════════════════════════════════════════════
