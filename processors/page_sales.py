"""销售达成页 — 3 卡片 × 收入/回款 双视图

每个卡片都包含 收入/回款 两个 tab（参考年度达成页客户 tab 切换）
卡片1: 销售年度达成 mini-rate 进度条
卡片2: 事业部完成度矩阵 cell-bg 填充格
卡片3: 客户收入/回款完成度 cell-bg 填充格
"""
from __future__ import annotations

import pandas as pd

from .base import BaseRenderer, rate_cls
from .utils import fmt_wan, safe_float

DEPARTMENTS = ["检测", "信息", "能源", "海外"]
DEPT_COLORS = {"检测": "#2563eb", "信息": "#8b5cf6", "能源": "#f59e0b", "海外": "#0d9488"}


class SalesPage(BaseRenderer):
    page_id = "sales"
    nav_name = "销售达成"

    def render(self, data) -> str:
        df_si = data.sales_income.copy()
        df_sp = data.sales_payment.copy()
        df_tgt = data.total_targets.copy()

        df_si["金额_万"] = df_si["金额"].apply(safe_float) / 10000.0
        df_sp["金额_万"] = df_sp["金额"].apply(safe_float) / 10000.0
        si_ok = df_si[df_si["销售"] != "待确认"].copy()
        sp_ok = df_sp[df_sp["销售"] != "待确认"].copy()

        dept_cols = DEPARTMENTS

        # ── 目标计算（总指标单位：万元）──
        sales_targets: dict[str, float] = {}
        sales_dept_tgt: dict[str, dict[str, float]] = {}
        for _, row in df_tgt.iterrows():
            sales = str(row.get("销售", "")).strip()
            if not sales or sales in ("待确认", "", "nan"):
                continue
            total = sum(safe_float(row.get(d, 0)) for d in dept_cols)
            sales_targets[sales] = sales_targets.get(sales, 0) + total
            if sales not in sales_dept_tgt:
                sales_dept_tgt[sales] = {d: 0.0 for d in dept_cols}
            for d in dept_cols:
                sales_dept_tgt[sales][d] += safe_float(row.get(d, 0))

        dept_tgt_total: dict[str, float] = {}
        for d in dept_cols:
            dept_tgt_total[d] = safe_float(df_tgt[d].fillna(0).sum())

        # ── 实际收入/回款 ──
        sales_inc = si_ok.groupby("销售")["金额_万"].sum().to_dict()
        sales_pay = sp_ok.groupby("销售")["金额_万"].sum().to_dict()

        # 按(销售,事业部)汇总收入
        sd_inc = si_ok.groupby(["销售", "事业部"])["金额_万"].sum().reset_index()
        inc_pd: dict[str, dict[str, float]] = {}
        for _, r in sd_inc.iterrows():
            s = str(r["销售"]); d = str(r["事业部"]); v = safe_float(r["金额_万"])
            if s not in inc_pd: inc_pd[s] = {}
            inc_pd[s][d] = v

        # 按(销售,事业部)汇总回款
        sd_pay = sp_ok.groupby(["销售", "事业部"])["金额_万"].sum().reset_index()
        pay_pd: dict[str, dict[str, float]] = {}
        for _, r in sd_pay.iterrows():
            s = str(r["销售"]); d = str(r["事业部"]); v = safe_float(r["金额_万"])
            if s not in pay_pd: pay_pd[s] = {}
            pay_pd[s][d] = v

        dept_inc_total = df_si.groupby("事业部")["金额_万"].sum().to_dict()
        dept_pay_total = df_sp.groupby("事业部")["金额_万"].sum().to_dict()

        all_sales = [
            s for s in sorted(sales_inc, key=lambda x: sales_inc.get(x, 0), reverse=True)
            if s != "待确认"
        ]

        # ── 销售×客户×事业部 明细（用于新模块：销售个人各公司指标达成度）──
        sc_inc = si_ok.groupby(["销售", "客户", "事业部"])["金额_万"].sum().reset_index()
        sc_pay = sp_ok.groupby(["销售", "客户", "事业部"])["金额_万"].sum().reset_index()

        # 按 (销售, 客户) 汇总各事业部目标
        sales_cust_tgt: dict[str, dict[str, dict[str, float]]] = {}  # {销售: {客户: {部门: 目标}}}
        for _, row in df_tgt.iterrows():
            sales = str(row.get("销售", "")).strip()
            cust = str(row.get("客户", "")).strip()
            if not sales or not cust: continue
            if sales not in sales_cust_tgt: sales_cust_tgt[sales] = {}
            if cust not in sales_cust_tgt[sales]: sales_cust_tgt[sales][cust] = {d: 0.0 for d in dept_cols}
            for d in dept_cols:
                sales_cust_tgt[sales][cust][d] += safe_float(row.get(d, 0))

        total_target = sum(sales_targets.values())
        total_inc = safe_float(df_si["金额_万"].sum())
        total_pay = safe_float(df_sp["金额_万"].sum())

        # ── 待确认客户明细（按客户×事业部汇总）──
        pending_inc = df_si[df_si["销售"] == "待确认"].groupby(
            ["客户", "事业部"])["金额_万"].sum().reset_index()
        pending_pay = df_sp[df_sp["销售"] == "待确认"].groupby(
            ["客户", "事业部"])["金额_万"].sum().reset_index()
        # 合并
        pending = pending_inc.merge(
            pending_pay, on=["客户", "事业部"], how="outer", suffixes=("_收入", "_回款")
        ).fillna(0)
        pending["合计"] = pending["金额_万_收入"] + pending["金额_万_回款"]
        pending = pending.sort_values("合计", ascending=False)
        pending_count = len(pending)
        pending_total_inc = float(pending["金额_万_收入"].sum())
        pending_total_pay = float(pending["金额_万_回款"].sum())

        return self.wrap_page(
            self._kpi_row(total_target, total_inc, total_pay) +
            self._card1_sales(all_sales, sales_targets, sales_inc, sales_pay,
                              pending_count, pending_total_inc, pending_total_pay) +
            self._card2_dept(all_sales, sales_dept_tgt, inc_pd, pay_pd,
                             dept_tgt_total, dept_inc_total, dept_pay_total) +
            self._card3_sales_customers(all_sales, sc_inc, sc_pay, sales_cust_tgt,
                                        sales_targets, dept_cols) +
            self._pending_modal(pending, pending_count, pending_total_inc, pending_total_pay)
        )

    # ════════════════════════════════════════════════════════════
    # KPI
    # ════════════════════════════════════════════════════════════
    def _kpi_row(self, total_target: float, total_inc: float, total_pay: float) -> str:
        rate = total_inc / total_target * 100 if total_target else 0
        pay_r = total_pay / total_target * 100 if total_target else 0
        return f"""<div class="kpi-grid" style="grid-template-columns:repeat(3,1fr)">
  <div class="kpi kpi-tgt">
    <div class="kpi-label">年度总目标</div>
    <div class="kpi-value">{fmt_wan(total_target)}<span class="kpi-unit">万元</span></div>
    <div class="kpi-sub">4 事业部合计</div>
  </div>
  <div class="kpi kpi-inc">
    <div class="kpi-label">累计收入</div>
    <div class="kpi-value">{fmt_wan(total_inc)}<span class="kpi-unit">万元</span></div>
    <div class="kpi-sub">达成率 {rate:.1f}%</div>
  </div>
  <div class="kpi kpi-pay">
    <div class="kpi-label">累计回款</div>
    <div class="kpi-value">{fmt_wan(total_pay)}<span class="kpi-unit">万元</span></div>
    <div class="kpi-sub">达成率 {pay_r:.1f}%</div>
  </div>
</div>"""

    # ════════════════════════════════════════════════════════════
    # 卡片1: 销售年度达成 — mini-rate 进度条（收入/回款 tab）
    # ════════════════════════════════════════════════════════════
    def _card1_sales(
        self, all_sales: list[str],
        targets: dict[str, float],
        incomes: dict[str, float],
        payments: dict[str, float],
        pending_count: int = 0,
        pending_total_inc: float = 0,
        pending_total_pay: float = 0,
    ) -> str:
        def build(metric, data):
            # 按当前指标达成率降序排序（高到低）
            def sort_key(s):
                tgt = safe_float(targets.get(s, 0))
                act = safe_float(data.get(s, 0))
                return act / tgt if tgt > 0 else 0
            sorted_sales = sorted(all_sales, key=sort_key, reverse=True)
            rows = ""
            t_tgt = t_act = 0.0
            for s in sorted_sales:
                tgt = safe_float(targets.get(s, 0))
                act = safe_float(data.get(s, 0))
                t_tgt += tgt; t_act += act
                r = act / tgt if tgt > 0 else 0
                cls = rate_cls(r)
                rows += (
                    f'<div class="mini-rate">'
                    f'<span style="width:55px;font-weight:700">{s}</span>'
                    f'<div class="bar"><div class="bar-fill {cls}" style="width:{min(r*100,100):.1f}%"><span class="bar-pct {cls}">{r*100:.1f}%</span></div></div>'
                    f'<span class="val">{fmt_wan(act)}</span>'
                    f'<span style="color:var(--text-muted);font-size:11px">/{fmt_wan(tgt)}</span>'
                    f'</div>'
                )
            tr = t_act / t_tgt if t_tgt else 0
            cls_t = rate_cls(tr)
            rows += (
                f'<div class="mini-rate" style="border-top:2px solid var(--border);padding-top:8px;margin-top:4px">'
                f'<span style="width:55px;font-weight:700">合计</span>'
                f'<div class="bar"><div class="bar-fill {cls_t}" style="width:{min(tr*100,100):.1f}%"><span class="bar-pct {cls_t}">{tr*100:.1f}%</span></div></div>'
                f'<span class="val">{fmt_wan(t_act)}</span>'
                f'<span style="color:var(--text-muted);font-size:11px">/{fmt_wan(t_tgt)}</span>'
                f'</div>'
            )
            # 待确认入口（在合计行下面）
            if metric == "收入":
                pending_metric = pending_total_inc
            else:
                pending_metric = pending_total_pay
            rows += (
                f'<div onclick="openPendingModal()" style="cursor:pointer;margin-top:6px;padding:6px 8px;'
                f'background:linear-gradient(90deg,#fef3c7,#fde68a);border-radius:4px;'
                f'display:flex;align-items:center;gap:8px;font-size:12px;border:1px dashed #f59e0b">'
                f'<span style="color:#92400e;font-weight:700">⚠ 待确认客户</span>'
                f'<span style="color:#92400e">共 {pending_count} 家客户未归属销售</span>'
                f'<span style="margin-left:auto;color:#92400e;font-weight:600">本指标 {fmt_wan(pending_metric)} 万</span>'
                f'<span style="background:#f59e0b;color:#fff;padding:1px 8px;border-radius:3px;font-size:11px">点击查看明细 →</span>'
                f'</div>'
            )
            return f'<div id="sales-c1-{metric}">{"<div class=\"card-title\">" + metric + "完成度 · 实际 VS 年目标</div>"}{rows}</div>'

        inc_html = build("收入", incomes)
        pay_html = build("回款", payments)
        return (
            self.section("卡片1 · 销售年度达成", "sec-blue") +
            f'<div class="card" style="padding:10px 14px">'
            f'<div class="cust-tabs">'
            f'<span class="cust-tab active inc" onclick="document.getElementById(\'sales-c1-收入\').classList.remove(\'hidden\');document.getElementById(\'sales-c1-回款\').classList.add(\'hidden\');this.parentElement.querySelectorAll(\'.cust-tab\').forEach(t=>t.classList.remove(\'active\'));this.classList.add(\'active\')">收入达成</span>'
            f'<span class="cust-tab pay" onclick="document.getElementById(\'sales-c1-收入\').classList.add(\'hidden\');document.getElementById(\'sales-c1-回款\').classList.remove(\'hidden\');this.parentElement.querySelectorAll(\'.cust-tab\').forEach(t=>t.classList.remove(\'active\'));this.classList.add(\'active\')">回款达成</span>'
            f'</div>'
            f'<div id="sales-c1-收入">{inc_html}</div>'
            f'<div id="sales-c1-回款" class="hidden">{pay_html}</div>'
            f'</div>'
        )

    # ════════════════════════════════════════════════════════════
    # 卡片2: 事业部完成度矩阵 — cell-bg 填充格（收入/回款 tab）
    # ════════════════════════════════════════════════════════════
    def _card2_dept(
        self, all_sales: list[str],
        sales_dept_tgt: dict[str, dict[str, float]],
        inc_pd: dict[str, dict[str, float]],
        pay_pd: dict[str, dict[str, float]],
        dept_tgt_total: dict[str, float],
        dept_inc_total: dict[str, float],
        dept_pay_total: dict[str, float],
    ) -> str:
        def cell(act, tgt, is_total_col=False):
            if act == 0 and tgt == 0:
                return '<td class="td-empty">—</td>'
            r = act / tgt if tgt else 0
            pct_num = min(r * 100, 100)
            pct_label = f"{r*100:.0f}%"
            if r >= 1:
                pct_cls = " achieved"; fill_var = "#22c55e"
            elif r >= 0.5:
                pct_cls = ""; fill_var = "#fb923c"
            elif r > 0:
                pct_cls = " low"; fill_var = "#fdba74"
            else:
                pct_cls = ""; fill_var = "#f1f5f9"
            empty_cls = " is-empty" if r == 0 else ""
            # 紧凑布局：百分比 + 单行收/指
            compact = f"{fmt_wan(act)}/{fmt_wan(tgt)}"
            if is_total_col:
                return (
                    f'<td class="cell-bg is-total">'
                    f'<div class="cell-text">'
                    f'<span class="cell-pct">{pct_label}</span>'
                    f'<div class="cell-main"><span class="cell-compact">{compact}</span></div>'
                    f'</div></td>'
                )
            return (
                f'<td class="cell-bg{empty_cls}" style="--pct:{pct_num:.1f}%;--fill:{fill_var}">'
                f'<div class="fill-bg"></div>'
                f'<div class="cell-text">'
                f'<span class="cell-pct{pct_cls}">{pct_label}</span>'
                f'<div class="cell-main"><span class="cell-compact">{compact}</span></div>'
                f'</div></td>'
            )

        def build(metric, data_pd):
            h = '<tr><th class="th-name">销售</th>' + "".join(f"<th>{d}</th>" for d in DEPARTMENTS) + '<th class="th-name th-total">总目标</th></tr>'
            # 合计行
            tc = [f'<td class="td-name td-total">合计（{len(all_sales)}人）</td>']
            t_all_act = t_all_tgt = 0.0
            for d in DEPARTMENTS:
                a = safe_float((dept_data := dept_inc_total if metric == "收入" else dept_pay_total).get(d, 0))
                tg = safe_float(dept_tgt_total.get(d, 0))
                t_all_act += a; t_all_tgt += tg
                tc.append(cell(a, tg, is_total_col=False))
            tc.append(cell(t_all_act, t_all_tgt, is_total_col=True))
            tr_total = f'<tr class="row-total">{"".join(tc)}</tr>'
            # 数据行（按当前指标达成率降序）
            def sort_key(s):
                tgt_total = sum(safe_float(v) for v in sales_dept_tgt.get(s, {}).values())
                act_total = sum(safe_float(v) for v in data_pd.get(s, {}).values())
                return act_total / tgt_total if tgt_total > 0 else 0
            sorted_sales = sorted(all_sales, key=sort_key, reverse=True)
            rows = ""
            for s in sorted_sales:
                tgt_dict = sales_dept_tgt.get(s, {})
                act_dict = data_pd.get(s, {})
                cs = [f'<td class="td-name"><span class="row-num"></span>{s}</td>']
                s_act = s_tgt = 0.0
                for d in DEPARTMENTS:
                    a = safe_float(act_dict.get(d, 0))
                    tg = safe_float(tgt_dict.get(d, 0))
                    s_act += a; s_tgt += tg
                    cs.append(cell(a, tg, is_total_col=False))
                cs.append(cell(s_act, s_tgt, is_total_col=True))
                rows += '<tr class="row-data">' + "".join(cs) + '</tr>'
            return (
                f'<div id="sales-c2-{metric}">'
                f'<div class="table-wrap ann-matrix-wrap no-collapse">'
                f'<table class="ann-matrix">{h}<tbody>{tr_total}{rows}</tbody></table>'
                f'</div>'
                f'</div>'
            )

        inc_html = build("收入", inc_pd)
        pay_html = build("回款", pay_pd)
        return (
            self.section("卡片2 · 事业部完成度矩阵", "sec-purple") +
            f'<div class="card" style="padding:8px 10px">'
            f'<div class="cust-tabs" style="margin-bottom:6px">'
            f'<span class="cust-tab active inc" onclick="document.getElementById(\'sales-c2-收入\').classList.remove(\'hidden\');document.getElementById(\'sales-c2-回款\').classList.add(\'hidden\');this.parentElement.querySelectorAll(\'.cust-tab\').forEach(t=>t.classList.remove(\'active\'));this.classList.add(\'active\')">收入</span>'
            f'<span class="cust-tab pay" onclick="document.getElementById(\'sales-c2-收入\').classList.add(\'hidden\');document.getElementById(\'sales-c2-回款\').classList.remove(\'hidden\');this.parentElement.querySelectorAll(\'.cust-tab\').forEach(t=>t.classList.remove(\'active\'));this.classList.add(\'active\')">回款</span>'
            f'</div>'
            f'{inc_html}'
            f'<div id="sales-c2-回款" class="hidden">{pay_html}</div>'
            f'<style>'
            f'#sales-c2-收入 table,#sales-c2-回款 table{{font-size:11px}}'
            f'#sales-c2-收入 .cell-pct,#sales-c2-回款 .cell-pct{{font-size:13px;line-height:1.1}}'
            f'#sales-c2-收入 .cell-compact,#sales-c2-回款 .cell-compact{{font-size:10px;color:var(--text-muted);margin-top:0;line-height:1.2}}'
            f'#sales-c2-收入 td,#sales-c2-回款 td,#sales-c2-收入 th,#sales-c2-回款 th{{padding:3px 4px;line-height:1.2}}'
            f'#sales-c2-收入 .td-name,#sales-c2-回款 .td-name{{font-size:11px;font-weight:700;padding:3px 6px}}'
            f'#sales-c2-收入 .cell-text,#sales-c2-回款 .cell-text{{padding:1px 2px}}'
            f'</style>'
            f'</div>'
        )

    # ════════════════════════════════════════════════════════════
    # 卡片3: 销售人员个人 × 各公司指标达成度
    # 设计：
    #   · 顶部销售下拉选择 + 收入/回款 双 tab
    #   · 顶部 4 张 KPI：年目标 / 实际收入(回款) / 实际达成率 / 客户数
    #   · 4 事业部横向 cell-bg 矩阵，列=事业部，行=客户（公司）
    #   · 行=客户，列=4 事业部 + 总目标/总达成
    #   · 完成度按 cell-bg 填充，色阶与卡片2保持一致
    # ════════════════════════════════════════════════════════════
    def _card3_sales_customers(
        self,
        all_sales: list[str],
        sc_inc: pd.DataFrame,
        sc_pay: pd.DataFrame,
        sales_cust_tgt: dict[str, dict[str, dict[str, float]]],
        sales_targets: dict[str, float],
        dept_cols: list[str],
    ) -> str:
        if not all_sales:
            return ""

        options = "".join(f'<option value="{s}">{s}</option>' for s in all_sales)

        def _resolve_cust_tgt(sales_name: str, cust: str) -> dict[str, float]:
            """按销售×客户的 4 事业部目标字典，模糊匹配容错"""
            m = sales_cust_tgt.get(sales_name, {})
            v = m.get(cust, None)
            if v is not None and any(safe_float(x) > 0 for x in v.values()):
                return v
            # 模糊匹配：前 8 字符 / 包含
            ck = cust[:8] if cust else ""
            tot = {d: 0.0 for d in dept_cols}
            for k, vv in m.items():
                kk = k[:8] if k else ""
                if ck and (ck == kk or ck in k or kk in cust):
                    for d in dept_cols:
                        tot[d] += safe_float(vv.get(d, 0))
            return tot

        def _rows_for(sales_name: str, df: pd.DataFrame) -> tuple[list[dict], float, float]:
            """构造某销售的明细行列表 + 总实际 + 总目标"""
            sub = df[df["销售"] == sales_name].copy()
            if sub.empty:
                return [], 0.0, 0.0
            # 按客户总金额降序
            cust_tot = sub.groupby("客户")["金额_万"].sum().to_dict()
            sub["__cust_tot"] = sub["客户"].map(cust_tot)
            sorted_sub = sub.sort_values(by=["__cust_tot", "金额_万"], ascending=[False, False])

            rows = []
            t_act = 0.0
            t_tgt = 0.0
            for cust, g in sorted_sub.groupby("客户", sort=False):
                tgt_dict = _resolve_cust_tgt(sales_name, cust)
                dept_actual = {}
                for _, r in g.iterrows():
                    dept_actual[str(r["事业部"])] = dept_actual.get(str(r["事业部"]), 0.0) + safe_float(r["金额_万"])

                # 每个事业部一行；同时聚合客户级 总目标 / 总实际
                row_total_act = 0.0
                row_total_tgt = 0.0
                dept_cells = []
                for d in dept_cols:
                    a = dept_actual.get(d, 0.0)
                    tg = safe_float(tgt_dict.get(d, 0.0))
                    row_total_act += a
                    row_total_tgt += tg
                    dept_cells.append({"dept": d, "act": a, "tgt": tg})
                # 包含未在 dept_cols 范围内的部门 — 极少出现，忽略
                rows.append({
                    "cust": cust,
                    "cells": dept_cells,
                    "total_act": row_total_act,
                    "total_tgt": row_total_tgt,
                })
                t_act += row_total_act
                t_tgt += row_total_tgt
            return rows, t_act, t_tgt

        # ─── 预生成全量数据，序列化为 JSON 给前端切换 ───
        import json as _json
        data_pack = {}
        for s in all_sales:
            inc_rows, inc_act, inc_tgt = _rows_for(s, sc_inc)
            pay_rows, pay_act, pay_tgt = _rows_for(s, sc_pay)
            data_pack[s] = {
                "sales_target": round(float(sales_targets.get(s, 0)), 2),
                "income": {
                    "rows": [
                        {"cust": r["cust"],
                         "depts": [[c["dept"], round(c["act"], 2), round(c["tgt"], 2)] for c in r["cells"]],
                         "act": round(r["total_act"], 2),
                         "tgt": round(r["total_tgt"], 2)}
                        for r in inc_rows
                    ],
                    "t_act": round(inc_act, 2),
                    "t_tgt": round(inc_tgt, 2),
                },
                "payment": {
                    "rows": [
                        {"cust": r["cust"],
                         "depts": [[c["dept"], round(c["act"], 2), round(c["tgt"], 2)] for c in r["cells"]],
                         "act": round(r["total_act"], 2),
                         "tgt": round(r["total_tgt"], 2)}
                        for r in pay_rows
                    ],
                    "t_act": round(pay_act, 2),
                    "t_tgt": round(pay_tgt, 2),
                },
            }
        _data_json = _json.dumps(data_pack, ensure_ascii=False)

        def _pct_color(rate: float) -> str:
            if rate >= 1:
                return "#22c55e"
            if rate >= 0.5:
                return "#fb923c"
            if rate > 0:
                return "#fdba74"
            return "#f1f5f9"

        def _pct_text_cls(rate: float) -> str:
            if rate >= 1:
                return "achieved"
            if rate > 0:
                return "low"
            return ""

        def _build_panel(sales_name: str, kind: str) -> str:
            rows, t_act, t_tgt = _rows_for(sales_name, sc_inc if kind == "inc" else sc_pay)
            if not rows:
                return '<div class="td-empty" style="padding:40px;text-align:center">该销售暂无数据</div>'

            # KPI 行
            tgt_total = safe_float(sales_targets.get(sales_name, 0))
            rate = (t_act / tgt_total) if tgt_total > 0 else 0
            cust_count = len(rows)

            # ── 表头 ──
            th_depts = "".join(
                f'<th style="text-align:center;width:90px">{d}</th>' for d in dept_cols
            )
            th = (
                f'<tr>'
                f'<th class="th-name" style="text-align:left;min-width:160px">公司（客户）</th>'
                f'{th_depts}'
                f'<th style="text-align:right;width:100px">客户合计</th>'
                f'<th style="text-align:center;width:90px">完成度</th>'
                f'</tr>'
            )

            # ── 数据行 ──
            body = ""
            for r in rows:
                cust = r["cust"]
                cells = r["cells"]
                t_a = r["total_act"]
                t_t = r["total_tgt"]
                pct = (t_a / t_t) if t_t > 0 else 0
                fill = _pct_color(pct)
                pct_label = f'{pct*100:.0f}%' if t_t > 0 else "—"
                cell_html = "".join(
                    (lambda _a, _t, _p, _pc, _fc, _pl, _cl: (
                        f'<td class="cell-bg{" is-empty" if (_a == 0 and _t == 0) else ""}" '
                        f'style="--pct:{min(_p*100, 100):.1f}%;--fill:{_fc}">'
                        f'<div class="fill-bg"></div>'
                        f'<div class="cell-text">'
                        f'<span class="cell-pct {_cl}">{_pl}</span>'
                        f'<div class="cell-main">'
                        f'<span class="cell-act">{fmt_wan(_a)}</span>'
                        f'<span class="cell-tgt">/ {fmt_wan(_t) if _t > 0 else "—"}</span>'
                        f'</div>'
                        f'</div></td>'
                    ))(c["act"], c["tgt"],
                       (c["act"]/c["tgt"]) if c["tgt"] else 0,
                       _pct_color((c["act"]/c["tgt"]) if c["tgt"] else 0),
                       _pct_color((c["act"]/c["tgt"]) if c["tgt"] else 0),
                       f'{(c["act"]/c["tgt"]*100):.0f}%' if c["tgt"] > 0 else "—",
                       _pct_text_cls((c["act"]/c["tgt"]) if c["tgt"] else 0))
                    for c in cells
                )
                body += (
                    f'<tr class="row-data">'
                    f'<td class="td-name" style="max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" '
                    f'title="{cust}">{cust}</td>'
                    f'{cell_html}'
                    f'<td style="text-align:right;font-weight:700">{fmt_wan(t_a)}<div style="font-size:10px;color:#64748b;font-weight:600">/ {fmt_wan(t_t) if t_t > 0 else "—"}</div></td>'
                    f'<td class="cell-bg is-total" style="--pct:{min(pct*100,100):.1f}%;--fill:{fill}">'
                    f'<div class="cell-text">'
                    f'<span class="cell-pct {_pct_text_cls(pct)}">{pct_label}</span>'
                    f'</div></td>'
                    f'</tr>'
                )

            # ── 合计行 ──
            tot_rate = (t_act / tgt_total) if tgt_total > 0 else 0
            tot_pct_label = f'{tot_rate*100:.1f}%' if tgt_total > 0 else "—"
            tot_fill = _pct_color(tot_rate)
            tot_dept_cells_html = ""
            for d in dept_cols:
                d_act = 0.0
                d_tgt = 0.0
                for r in rows:
                    for cc in r["cells"]:
                        if cc["dept"] == d:
                            d_act += cc["act"]
                            d_tgt += cc["tgt"]
                d_rate = (d_act / d_tgt) if d_tgt > 0 else 0
                d_fill = _pct_color(d_rate)
                d_label = f'{d_rate*100:.0f}%' if d_tgt > 0 else "—"
                d_cls = _pct_text_cls(d_rate)
                d_act_w = fmt_wan(d_act)
                d_tgt_w = fmt_wan(d_tgt) if d_tgt > 0 else "—"
                empty_cls = " is-empty" if d_act == 0 and d_tgt == 0 else ""
                tot_dept_cells_html += (
                    f'<td class="cell-bg{empty_cls}" '
                    f'style="--pct:{min(d_rate*100, 100):.1f}%;--fill:{d_fill}">'
                    f'<div class="fill-bg"></div>'
                    f'<div class="cell-text">'
                    f'<span class="cell-pct {d_cls}">{d_label}</span>'
                    f'<div class="cell-main">'
                    f'<span class="cell-act">{d_act_w}</span>'
                    f'<span class="cell-tgt">/ {d_tgt_w}</span>'
                    f'</div>'
                    f'</div></td>'
                )
            summary = (
                f'<tr class="row-total">'
                f'<td class="td-name td-total">销售合计</td>'
                f'{tot_dept_cells_html}'
                f'<td style="text-align:right;font-weight:800;color:#1e3a8a">'
                f'{fmt_wan(t_act)}<div style="font-size:10px;color:#64748b;font-weight:600">/ {fmt_wan(tgt_total) if tgt_total > 0 else "—"}</div>'
                f'</td>'
                f'<td class="cell-bg is-total" style="--pct:{min(tot_rate*100,100):.1f}%;--fill:{tot_fill}">'
                f'<div class="cell-text">'
                f'<span class="cell-pct">{tot_pct_label}</span>'
                f'</div></td>'
                f'</tr>'
            )

            return f"""
<div class="table-wrap no-collapse">
  <table class="ann-matrix" style="font-size:12px;table-layout:auto;width:100%">
    <colgroup>
      <col style="width:24%">
      {''.join(f'<col style="width:13%">' for _ in dept_cols)}
      <col style="width:14%">
      <col style="width:10%">
    </colgroup>
    <thead>{th}</thead>
    <tbody>{body}{summary}</tbody>
  </table>
</div>
"""

        default_sales = all_sales[0] if all_sales else ""
        default_inc_html = _build_panel(default_sales, "inc")
        default_pay_html = _build_panel(default_sales, "pay")

        # ── JS：销售切换/指标切换 ──
        js_code = (
            "var __SC3D=" + _data_json + ";\n"
            "function __sc3FmtWan(v){if(v===null||v===undefined)return '—';var n=Number(v);"
            "if(isNaN(n))return '—';n=Math.round(n*10)/10;"
            "return n.toLocaleString('zh-CN',{maximumFractionDigits:1});}\n"
            "function __sc3Pct(a,t){return t>0?(a/t):0;}\n"
            "function __sc3Fill(r){return r>=1?'#22c55e':r>=0.5?'#fb923c':r>0?'#fdba74':'#f1f5f9';}\n"
            "function __sc3Build(sales,m){\n"
            " var d=__SC3D[sales];if(!d) return null;\n"
            " var mData = (m==='inc')?d.income:d.payment;\n"
            " var rows=mData.rows; if(!rows||!rows.length) return '<div class=\"td-empty\" style=\"padding:40px;text-align:center\">该销售暂无数据</div>';\n"
            " var tAct=mData.t_act, tTgt=mData.t_tgt;\n"
            " var colHead=['<th class=\"th-name\" style=\"text-align:left;min-width:160px\">公司（客户）</th>'];\n"
            " ['检测','信息','能源','海外'].forEach(function(dp){colHead.push('<th style=\"text-align:center;width:90px\">'+dp+'</th>');});\n"
            " colHead.push('<th style=\"text-align:right;width:100px\">客户合计</th>', '<th style=\"text-align:center;width:90px\">完成度</th>');\n"
            " var h='<tr>'+colHead.join('')+'</tr>';\n"
            " var body='';\n"
            " rows.forEach(function(r){\n"
            "  var cells=r.depts;\n"
            "  var tA=r.act, tT=r.tgt;\n"
            "  var totR=__sc3Pct(tA,tT);\n"
            "  var totFill=__sc3Fill(totR);\n"
            "  var totPct=tT>0?(totR*100).toFixed(0)+'%':'—';\n"
            "  var totCls=totR>=1?'achieved':totR>0?'low':'';\n"
            "  var chtml='';\n"
            "  cells.forEach(function(c){\n"
            "   var a=c[1],t=c[2]; var p=__sc3Pct(a,t);\n"
            "   var fill=__sc3Fill(p);\n"
            "   var pLabel=t>0?(p*100).toFixed(0)+'%':'—';\n"
            "   var pCls=p>=1?'achieved':p>0?'low':'';\n"
            "   var empty=(a===0&&t===0)?' is-empty':'';\n"
            "   chtml+='<td class=\"cell-bg'+empty+'\" style=\"--pct:'+Math.min(p*100,100).toFixed(1)+'%;--fill:'+fill+'\">'\n"
            "         +'<div class=\"fill-bg\"></div>'\n"
            "         +'<div class=\"cell-text\">'\n"
            "         +'<span class=\"cell-pct '+pCls+'\">'+pLabel+'</span>'\n"
            "         +'<div class=\"cell-main\">'\n"
            "         +'<span class=\"cell-act\">'+__sc3FmtWan(a)+'</span>'\n"
            "         +'<span class=\"cell-tgt\">/ '+(t>0?__sc3FmtWan(t):'—')+'</span>'\n"
            "         +'</div>'\n"
            "         +'</div></td>';\n"
            "  });\n"
            "  body+='<tr class=\"row-data\">'\n"
            "       +'<td class=\"td-name\" style=\"max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap\" title=\"'+r.cust+'\">'+r.cust+'</td>'\n"
            "       +chtml\n"
            "       +'<td style=\"text-align:right;font-weight:700\">'+__sc3FmtWan(tA)+'<div style=\"font-size:10px;color:#64748b;font-weight:600\">/ '+(tT>0?__sc3FmtWan(tT):'—')+'</div></td>'\n"
            "       +'<td class=\"cell-bg is-total\" style=\"--pct:'+Math.min(totR*100,100).toFixed(1)+'%;--fill:'+totFill+'\">'\n"
            "       +'<div class=\"cell-text\"><span class=\"cell-pct '+totCls+'\">'+totPct+'</span></div>'\n"
            "       +'</td></tr>';\n"
            " });\n"
            " var totRsum=__sc3Pct(tAct, tTgt);\n"
            " var totRSumPct=tTgt>0?(totRsum*100).toFixed(1)+'%':'—';\n"
            " var sumDepts=['检测','信息','能源','海外'];\n"
            " var sumDeptHtml='';\n"
            " sumDepts.forEach(function(dp){\n"
            "  var dAct=0,dTgt=0;\n"
            "  rows.forEach(function(r){\n"
            "   r.depts.forEach(function(c){\n"
            "    if(c[0]===dp){dAct+=c[1];dTgt+=c[2];}\n"
            "   });\n"
            "  });\n"
            "  var dR=__sc3Pct(dAct,dTgt);var dFill=__sc3Fill(dR);\n"
            "  var dLabel=dTgt>0?(dR*100).toFixed(0)+'%':'—';\n"
            "  var dCls=dR>=1?'achieved':dR>0?'low':'';\n"
            "  var dEmpty=(dAct===0&&dTgt===0)?' is-empty':'';\n"
            "  sumDeptHtml+='<td class=\"cell-bg'+dEmpty+'\" style=\"--pct:'+Math.min(dR*100,100).toFixed(1)+'%;--fill:'+dFill+'\">'\n"
            "    +'<div class=\"fill-bg\"></div>'\n"
            "    +'<div class=\"cell-text\">'\n"
            "    +'<span class=\"cell-pct '+dCls+'\">'+dLabel+'</span>'\n"
            "    +'<div class=\"cell-main\">'\n"
            "    +'<span class=\"cell-act\">'+__sc3FmtWan(dAct)+'</span>'\n"
            "    +'<span class=\"cell-tgt\">/ '+(dTgt>0?__sc3FmtWan(dTgt):'—')+'</span>'\n"
            "    +'</div>'\n"
            "    +'</div></td>';\n"
            " });\n"
            " var sumRow='<tr class=\"row-total\">'\n"
            "   +'<td class=\"td-name td-total\">销售合计</td>'\n"
            "   +sumDeptHtml\n"
            "   +'<td style=\"text-align:right;font-weight:800;color:#1e3a8a\">'+__sc3FmtWan(tAct)+'<div style=\"font-size:10px;color:#64748b;font-weight:600\">/ '+(tTgt>0?__sc3FmtWan(tTgt):'—')+'</div></td>'\n"
            "   +'<td class=\"cell-bg is-total\" style=\"--pct:'+Math.min(totRsum*100,100).toFixed(1)+'%;--fill:'+__sc3Fill(totRsum)+'\">'\n"
            "   +'<div class=\"cell-text\"><span class=\"cell-pct\">'+totRSumPct+'</span></div>'\n"
            "   +'</td></tr>';\n"
            " var cols='<col style=\"width:24%\"><col style=\"width:13%\"><col style=\"width:13%\"><col style=\"width:13%\"><col style=\"width:13%\"><col style=\"width:14%\"><col style=\"width:10%\">';\n"
            " return '<div class=\"table-wrap no-collapse\"><table class=\"ann-matrix\" style=\"font-size:12px;table-layout:auto;width:100%\"><colgroup>'+cols+'</colgroup><thead>'+h+'</thead><tbody>'+body+sumRow+'</tbody></table></div>';\n"
            "}\n"
            "function switchSc3Sales(s){\n"
            " if(!__SC3D[s]) return;\n"
            " document.getElementById('sc3-panel-inc').innerHTML=__sc3Build(s,'inc')||'';\n"
            " document.getElementById('sc3-panel-pay').innerHTML=__sc3Build(s,'pay')||'';\n"
            " var d=__SC3D[s];\n"
            " var tgt=d.sales_target||0;\n"
            " var k=tgt>0?(d.income.t_act/tgt):0;\n"
            " var kp=tgt>0?(d.payment.t_act/tgt):0;\n"
            " document.getElementById('sc3-kpi-inc-amt').textContent=__sc3FmtWan(d.income.t_act)+' 万元';\n"
            " document.getElementById('sc3-kpi-pay-amt').textContent=__sc3FmtWan(d.payment.t_act)+' 万元';\n"
            " document.getElementById('sc3-kpi-inc-rate').textContent='达成 '+Math.round(k*1000)/10+'%';\n"
            " document.getElementById('sc3-kpi-pay-rate').textContent='达成 '+Math.round(kp*1000)/10+'%';\n"
            " document.getElementById('sc3-kpi-cust-count').textContent=d.income.rows.length+' 家';\n"
            " document.getElementById('sc3-kpi-target').textContent=__sc3FmtWan(tgt)+' 万元';\n"
            "}\n"
            "function switchSc3Metric(m){\n"
            " document.querySelectorAll('#sc3-tabs .cust-tab').forEach(function(t){t.classList.remove('active');});\n"
            " document.querySelector('#sc3-tabs .cust-tab.'+(m==='inc'?'inc':'pay')).classList.add('active');\n"
            " document.getElementById('sc3-panel-inc').classList.toggle('hidden', m!=='inc');\n"
            " document.getElementById('sc3-panel-pay').classList.toggle('hidden', m!=='pay');\n"
            "}\n"
            "(function(){var s=document.getElementById('sc3SalesSel'); if(s) switchSc3Sales(s.value);})();\n"
        )

        return (
            self.section("卡片3 · 销售人员个人 × 各公司指标达成度", "sec-green")
            + f"""
<div class="card" style="padding:12px 14px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:8px">
    <div style="display:flex;gap:8px;align-items:center">
      <label style="font-weight:600;font-size:13px;color:var(--text-secondary)">选择销售：</label>
      <select id="sc3SalesSel" onchange="switchSc3Sales(this.value)" style="padding:4px 10px;border:1px solid var(--border);border-radius:4px;font-size:13px;font-weight:600;background:#fff;cursor:pointer;min-width:120px">
        {options}
      </select>
      <span style="font-size:11px;color:var(--text-muted)">颜色=完成度 · 列=事业部 · 行=客户公司</span>
    </div>
    <div class="cust-tabs" id="sc3-tabs" style="margin:0">
      <span class="cust-tab active inc" onclick="switchSc3Metric('inc')">收入达成</span>
      <span class="cust-tab pay" onclick="switchSc3Metric('pay')">回款达成</span>
    </div>
  </div>

  <!-- KPI 行 -->
  <div class="kpi-grid" style="grid-template-columns:repeat(5,1fr);margin-bottom:8px">
    <div class="kpi kpi-tgt" style="padding:8px 10px">
      <div class="kpi-label" style="font-size:11px">年度总目标</div>
      <div class="kpi-value" id="sc3-kpi-target" style="font-size:20px">—</div>
    </div>
    <div class="kpi kpi-inc" style="padding:8px 10px">
      <div class="kpi-label" style="font-size:11px">累计收入</div>
      <div class="kpi-value" id="sc3-kpi-inc-amt" style="font-size:20px">—</div>
      <div class="kpi-sub" id="sc3-kpi-inc-rate" style="font-size:11px">—</div>
    </div>
    <div class="kpi kpi-pay" style="padding:8px 10px">
      <div class="kpi-label" style="font-size:11px">累计回款</div>
      <div class="kpi-value" id="sc3-kpi-pay-amt" style="font-size:20px">—</div>
      <div class="kpi-sub" id="sc3-kpi-pay-rate" style="font-size:11px">—</div>
    </div>
    <div class="kpi" style="padding:8px 10px">
      <div class="kpi-label" style="font-size:11px;color:#5e6c84">客户公司数</div>
      <div class="kpi-value" id="sc3-kpi-cust-count" style="font-size:20px">—</div>
      <div class="kpi-sub" style="font-size:11px;color:#94a3b8">按收入计</div>
    </div>
    <div class="kpi kpi-rate" style="padding:8px 10px">
      <div class="kpi-label" style="font-size:11px;color:#115e59">查看说明</div>
      <div class="kpi-value" style="font-size:14px;line-height:1.3">每行=1 公司</div>
      <div class="kpi-sub" style="font-size:10px;color:#0f766e">每个事业部完成度</div>
    </div>
  </div>

  <!-- 双 Tab 面板 -->
  <div>
    <div id="sc3-panel-inc">{default_inc_html}</div>
    <div id="sc3-panel-pay" class="hidden">{default_pay_html}</div>
  </div>
</div>
<script>{js_code}</script>
"""
        )

    # ════════════════════════════════════════════════════════════
    # 待确认客户悬浮窗（含完整数据分析）
    # ════════════════════════════════════════════════════════════
    def _pending_modal(self, pending, pending_count: int,
                       pending_total_inc: float, pending_total_pay: float) -> str:
        """销售=待确认的客户明细 + 6 区块数据分析"""
        if pending_count == 0:
            return ""

        # ── ① KPI 计算 ──
        grand_total = pending_total_inc + pending_total_pay
        avg_per_cust = grand_total / pending_count if pending_count else 0
        # 收入回款匹配度
        match = ((pending["金额_万_收入"] > 0) & (pending["金额_万_回款"] > 0)).sum()
        only_inc = ((pending["金额_万_收入"] > 0) & (pending["金额_万_回款"] == 0)).sum()
        only_pay = ((pending["金额_万_收入"] == 0) & (pending["金额_万_回款"] > 0)).sum()
        only_inc_amt = pending.loc[(pending["金额_万_收入"] > 0) & (pending["金额_万_回款"] == 0), "金额_万_收入"].sum()
        only_pay_amt = pending.loc[(pending["金额_万_收入"] == 0) & (pending["金额_万_回款"] > 0), "金额_万_回款"].sum()

        # ── ② 事业部分布 ──
        dept_dist = pending.groupby("事业部")[["金额_万_收入", "金额_万_回款"]].sum()
        dept_dist["合计"] = dept_dist["金额_万_收入"] + dept_dist["金额_万_回款"]
        dept_dist = dept_dist.sort_values("合计", ascending=False)
        max_dept = dept_dist["合计"].max() if len(dept_dist) else 0

        # ── ③ 客户类型分布（按名称关键词）──
        type_kws = {
            "整车厂": ["广汽", "比亚迪", "小鹏", "五菱", "上汽", "通用", "东风", "一汽", "吉利", "奇瑞", "长安", "长城", "宝马", "奔驰", "奥迪", "大众", "丰田", "本田", "福特", "新丰", "新势力", "启境"],
            "零部件": ["科技", "电子", "部件", "零部件", "工贸", "电池", "智联", "制造", "技术"],
            "检测/认证": ["检测", "认证", "测试", "鉴定", "质检", "实验室", "研究院"],
            "信息/智能": ["信息", "网络", "软件", "数据", "智能", "互联", "物联"],
            "自有客户": ["自有"],
            "政府/市场": ["市场", "管理局", "办公室", "中心站", "事业单位"],
        }
        type_buckets: list[tuple[str, int, float]] = []
        for t, kws in type_kws.items():
            mask = pending["客户"].astype(str).apply(
                lambda x: any(k in x for k in kws)
            )
            if mask.sum() > 0:
                type_buckets.append((t, int(mask.sum()), float(pending.loc[mask, "合计"].sum())))
        # 剩余 = 未分类
        classified_mask = pd.Series([False] * len(pending))
        for t, kws in type_kws.items():
            classified_mask |= pending["客户"].astype(str).apply(
                lambda x: any(k in x for k in kws)
            )
        unclass_n = (~classified_mask).sum()
        if unclass_n > 0:
            unclass_amt = float(pending.loc[~classified_mask, "合计"].sum())
            type_buckets.append(("其他", int(unclass_n), unclass_amt))
        type_buckets.sort(key=lambda x: -x[2])
        max_type = type_buckets[0][2] if type_buckets else 0

        # ── ④ 收入/回款分布（三象限）──
        quad = {
            "双向都有": (match, grand_total - only_inc_amt - only_pay_amt),
            "仅收入未回": (only_inc, only_inc_amt),
            "仅回款无收入": (only_pay, only_pay_amt),
        }

        # ── ⑤ Top 10 客户 ──
        top10 = pending.sort_values("合计", ascending=False).head(10)
        max_top = top10["合计"].max() if len(top10) else 0

        # ── 关键洞察数据（用于 ② ⑤ 标题）──
        top_dept_name = dept_dist.index[0] if len(dept_dist) else "—"
        top_dept_pct = dept_dist.iloc[0]["合计"] / grand_total * 100 if grand_total else 0
        top_cust_name = pending.sort_values("合计", ascending=False).iloc[0]["客户"] if len(pending) else "—"
        top_cust_amt = pending.sort_values("合计", ascending=False).iloc[0]["合计"] if len(pending) else 0
        top_cust_pct = top_cust_amt / grand_total * 100 if grand_total else 0

        # ── 渲染 HTML ──
        def kpi_card(label, value, sub, color):
            return (
                f'<div class="pending-kpi" style="border-left:4px solid {color}">'
                f'<div class="pending-kpi-label">{label}</div>'
                f'<div class="pending-kpi-value">{value}</div>'
                f'<div class="pending-kpi-sub">{sub}</div></div>'
            )

        # 事业部分布
        dept_html = ""
        for d, row in dept_dist.iterrows():
            inc_v = float(row["金额_万_收入"])
            pay_v = float(row["金额_万_回款"])
            tot = float(row["合计"])
            pct = tot / grand_total * 100 if grand_total else 0
            bar_w = tot / max_dept * 100 if max_dept else 0
            dcolor = DEPT_COLORS.get(d, "#94a3b8")
            dept_html += (
                f'<div class="pending-row">'
                f'<span class="pending-label" style="color:{dcolor};width:60px">{d}</span>'
                f'<div class="pending-bar"><div class="pending-fill" style="width:{bar_w:.1f}%;background:{dcolor}">'
                f'<span class="pending-amt">{fmt_wan(tot)}</span></div></div>'
                f'<span class="pending-pct">{pct:.1f}%</span>'
                f'<span class="pending-sub">收入{fmt_wan(inc_v)}/回款{fmt_wan(pay_v)}</span>'
                f'</div>'
            )

        # 客户类型分布
        type_html = ""
        for t, n, a in type_buckets:
            pct = a / grand_total * 100 if grand_total else 0
            bar_w = a / max_type * 100 if max_type else 0
            type_html += (
                f'<div class="pending-row">'
                f'<span class="pending-label" style="width:90px">{t}</span>'
                f'<span class="pending-num" style="width:36px">{n}家</span>'
                f'<div class="pending-bar"><div class="pending-fill" style="width:{bar_w:.1f}%;background:#8b5cf6">'
                f'<span class="pending-amt">{fmt_wan(a)}</span></div></div>'
                f'<span class="pending-pct">{pct:.1f}%</span>'
                f'</div>'
            )

        # 收入/回款三象限
        quad_colors = {
            "双向都有": "#10b981",
            "仅收入未回": "#f59e0b",
            "仅回款无收入": "#3b82f6",
        }
        quad_html = ""
        for k, (cnt, amt) in quad.items():
            pct = amt / grand_total * 100 if grand_total else 0
            quad_html += (
                f'<div class="quad-cell" style="border-top:3px solid {quad_colors[k]}">'
                f'<div class="quad-num">{cnt} 家</div>'
                f'<div class="quad-label">{k}</div>'
                f'<div class="quad-amt">{fmt_wan(amt)} 万</div>'
                f'<div class="quad-pct">占 {pct:.1f}%</div>'
                f'</div>'
            )

        # Top 10 客户
        top_html = ""
        for i, (_, r) in enumerate(top10.iterrows(), 1):
            cust = str(r["客户"])
            dept = str(r["事业部"])
            tot = float(r["合计"])
            inc_v = float(r["金额_万_收入"])
            pay_v = float(r["金额_万_回款"])
            bar_w = tot / max_top * 100 if max_top else 0
            dcolor = DEPT_COLORS.get(dept, "#94a3b8")
            rank_cls = "rank-top" if i <= 3 else ""
            top_html += (
                f'<div class="pending-row {rank_cls}">'
                f'<span class="pending-rank">{i}</span>'
                f'<span class="pending-label" style="width:auto;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="{cust}">{cust}</span>'
                f'<span class="pending-dept" style="color:{dcolor};width:36px">{dept}</span>'
                f'<div class="pending-bar" style="width:120px"><div class="pending-fill" style="width:{bar_w:.1f}%;background:{dcolor}">'
                f'<span class="pending-amt">{fmt_wan(tot)}</span></div></div>'
                f'<span class="pending-sub" style="width:80px">收入{fmt_wan(inc_v)}/回款{fmt_wan(pay_v)}</span>'
                f'</div>'
            )

        # 明细表
        detail_rows = ""
        for _, r in pending.iterrows():
            cust = str(r["客户"])
            dept = str(r["事业部"])
            inc_v = safe_float(r["金额_万_收入"])
            pay_v = safe_float(r["金额_万_回款"])
            tot = inc_v + pay_v
            dcolor = DEPT_COLORS.get(dept, "#94a3b8")
            detail_rows += (
                f'<tr>'
                f'<td class="td-name">{cust}</td>'
                f'<td style="text-align:center;font-weight:600;color:{d_color if "d_color" in dir() else dcolor}">{dept}</td>'
                f'<td style="text-align:right">{fmt_wan(inc_v)}</td>'
                f'<td style="text-align:right">{fmt_wan(pay_v)}</td>'
                f'<td style="text-align:right;font-weight:700;color:var(--accent)">{fmt_wan(tot)}</td>'
                f'</tr>'
            )
        detail_rows += (
            f'<tr class="row-total">'
            f'<td class="td-name td-total">合计（{pending_count}家）</td>'
            f'<td></td>'
            f'<td style="text-align:right;font-weight:700">{fmt_wan(pending_total_inc)}</td>'
            f'<td style="text-align:right;font-weight:700">{fmt_wan(pending_total_pay)}</td>'
            f'<td style="text-align:right;font-weight:800;color:var(--accent)">{fmt_wan(grand_total)}</td>'
            f'</tr>'
        )

        return f"""
<div id="pendingModal" class="modal-overlay" style="display:none" onclick="if(event.target===this)closePendingModal()">
  <div class="modal-card modal-wide">
    <div class="modal-header">
      <div>
        <div class="modal-title">⚠ 待确认客户 · 数据分析</div>
        <div class="modal-sub">销售归属尚未明确 · 共 {pending_count} 家客户 · 合计 {fmt_wan(grand_total)} 万</div>
      </div>
      <button class="modal-close" onclick="closePendingModal()">×</button>
    </div>
    <div class="modal-body">

      <!-- ① 关键指标 -->
      <div class="pending-section">
        <div class="pending-h">① 关键指标</div>
        <div class="pending-kpi-grid">
          {kpi_card("客户数", f"{pending_count}", "家", "#f59e0b")}
          {kpi_card("总金额", fmt_wan(grand_total), "万元", "#dc2626")}
          {kpi_card("总收入", fmt_wan(pending_total_inc), f"占比{pending_total_inc/grand_total*100:.1f}%", "#3b82f6")}
          {kpi_card("总回款", fmt_wan(pending_total_pay), f"占比{pending_total_pay/grand_total*100:.1f}%", "#10b981")}
          {kpi_card("客户均额", fmt_wan(avg_per_cust), "万元/家", "#8b5cf6")}
        </div>
      </div>

      <!-- ② 事业部分布 -->
      <div class="pending-section">
        <div class="pending-h">② 事业部分布 · {top_dept_name}占 {top_dept_pct:.1f}%</div>
        <div class="pending-chart">{dept_html}</div>
      </div>

      <!-- ③ 客户类型分布 -->
      <div class="pending-section">
        <div class="pending-h">③ 客户类型（按名称关键词）</div>
        <div class="pending-chart">{type_html}</div>
      </div>

      <!-- ④ 收入/回款三象限 -->
      <div class="pending-section">
        <div class="pending-h">④ 收入/回款分布 · 双向匹配度 {(match/pending_count*100):.1f}%</div>
        <div class="quad-grid">{quad_html}</div>
      </div>

      <!-- ⑤ Top 10 客户 -->
      <div class="pending-section">
        <div class="pending-h">⑤ Top 10 客户 · 最大单笔 {top_cust_name} {fmt_wan(top_cust_amt)}万 ({top_cust_pct:.1f}%)</div>
        <div class="pending-chart">{top_html}</div>
      </div>

      <!-- ⑥ 完整明细表 -->
      <div class="pending-section">
        <div class="pending-h">⑥ 完整明细表（{pending_count} 家）</div>
        <div class="table-wrap no-collapse">
          <table class="ann-matrix">
            <thead><tr>
              <th class="th-name">客户</th>
              <th style="width:60px">事业部</th>
              <th style="width:90px">收入(万)</th>
              <th style="width:90px">回款(万)</th>
              <th style="width:90px">合计(万)</th>
            </tr></thead>
            <tbody>{detail_rows}</tbody>
          </table>
        </div>
      </div>

    </div>
  </div>
</div>
<style>
.modal-overlay{{
  position:fixed;top:0;left:0;right:0;bottom:0;
  background:rgba(0,0,0,.45);z-index:9999;
  display:flex;align-items:center;justify-content:center;
  animation:fadeIn .2s ease;
}}
.modal-card{{
  background:#fff;border-radius:10px;
  width:min(680px,90vw);max-height:80vh;
  display:flex;flex-direction:column;
  box-shadow:0 20px 60px rgba(0,0,0,.3);
  animation:slideUp .25s ease;
}}
.modal-card.modal-wide{{width:min(960px,95vw);max-height:90vh}}
.modal-header{{
  padding:14px 18px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;justify-content:space-between;
  background:linear-gradient(135deg,#fef3c7,#fde68a);
  border-radius:10px 10px 0 0;
}}
.modal-title{{font-size:16px;font-weight:800;color:#92400e}}
.modal-sub{{font-size:12px;color:#a16207;margin-top:2px}}
.modal-close{{
  background:transparent;border:none;font-size:28px;
  color:#92400e;cursor:pointer;line-height:1;padding:0 8px;
  font-weight:300;
}}
.modal-close:hover{{color:#dc2626}}
.modal-body{{padding:14px 18px;overflow-y:auto}}

/* 区块 */
.pending-section{{margin-bottom:14px;padding:10px 12px;background:#f8fafc;border-radius:6px;border:1px solid #e2e8f0}}
.pending-h{{font-size:13px;font-weight:800;color:#1e293b;margin-bottom:8px;padding-left:4px;border-left:3px solid #f59e0b}}

/* KPI 网格 */
.pending-kpi-grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px}}
.pending-kpi{{background:#fff;padding:8px 10px;border-radius:4px;border:1px solid #e2e8f0;border-left-width:3px}}
.pending-kpi-label{{font-size:11px;color:#64748b;font-weight:600}}
.pending-kpi-value{{font-size:18px;font-weight:800;color:#1e293b;margin:2px 0}}
.pending-kpi-sub{{font-size:10px;color:#94a3b8}}

/* 横向条形图 */
.pending-chart{{display:flex;flex-direction:column;gap:4px}}
.pending-row{{display:flex;align-items:center;gap:6px;font-size:12px;padding:3px 4px;border-radius:3px}}
.pending-row:hover{{background:#f1f5f9}}
.pending-row.rank-top{{background:#fef3c7}}
.pending-label{{font-weight:600;color:#334155}}
.pending-num{{font-size:11px;color:#64748b}}
.pending-bar{{flex:1;height:18px;background:#f1f5f9;border-radius:3px;overflow:hidden;position:relative;min-width:80px}}
.pending-bar[width="120px"]{{flex:0 0 120px}}
.pending-fill{{height:100%;border-radius:3px;display:flex;align-items:center;justify-content:flex-end;padding:0 6px;transition:width .4s;background:linear-gradient(90deg,#3b82f6,#60a5fa)}}
.pending-amt{{font-size:11px;font-weight:700;color:#fff;text-shadow:0 1px 1px rgba(0,0,0,.2)}}
.pending-pct{{font-size:11px;color:#64748b;font-weight:700;width:42px;text-align:right}}
.pending-sub{{font-size:10px;color:#94a3b8}}
.pending-rank{{font-weight:800;color:#f59e0b;width:18px;text-align:center;font-size:13px}}
.pending-dept{{font-size:11px;font-weight:700;text-align:center}}

/* 收入/回款三象限 */
.quad-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}}
.quad-cell{{background:#fff;padding:8px 10px;border-radius:4px;text-align:center;border:1px solid #e2e8f0}}
.quad-num{{font-size:18px;font-weight:800;color:#1e293b}}
.quad-label{{font-size:11px;color:#64748b;margin:2px 0}}
.quad-amt{{font-size:13px;font-weight:700;color:#475569}}
.quad-pct{{font-size:10px;color:#94a3b8}}

/* 跨事业部客户 (已移除) */

@keyframes fadeIn{{from{{opacity:0}}to{{opacity:1}}}}
@keyframes slideUp{{from{{transform:translateY(20px);opacity:0}}to{{transform:translateY(0);opacity:1}}}}
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
