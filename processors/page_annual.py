"""年度达成页 — 总目标 + 进度条 + 客户矩阵表"""
from __future__ import annotations

from .base import BaseRenderer, completion_html, rate_cls
from .utils import fmt_wan, safe_float

DEPARTMENTS = ["检测", "信息", "能源", "海外"]
# Excel 条件格式色阶
COLOR_MAP = {"level-1": "#c00000", "level-2": "#ed7d31", "level-3": "#bf8f00", "level-4": "#00b050"}


class AnnualPage(BaseRenderer):
    page_id = "annual"
    nav_name = "年度达成"

    def render(self, data) -> str:
        df_inc = data.income.copy()
        df_pay = data.payment.copy()
        df_tgt = data.total_targets.copy()
        df_inc["金额_万"] = df_inc["金额"].apply(safe_float) / 10000.0
        df_pay["金额_万"] = df_pay["金额"].apply(safe_float) / 10000.0

        t_inc = float(df_inc["金额_万"].sum())
        t_pay = float(df_pay["金额_万"].sum())
        t_tgt = sum(safe_float(df_tgt[d].sum()) for d in DEPARTMENTS if d in df_tgt.columns)
        inc_rate = t_inc / t_tgt if t_tgt else 0
        pay_rate = t_pay / t_tgt if t_tgt else 0

        # ── 顶部 Hero 大数字（年度总目标） ──
        hero = self._hero_block(t_tgt, t_inc, t_pay, inc_rate, pay_rate)
        # ── 2 张部门完成度卡片（收入+回款），共享同一 click 响应 ──
        dept_cards = self._dept_card_combined(df_inc, df_pay, df_tgt)
        # ── 重要客户矩阵 ──
        matrix = self._lower(df_inc, df_pay, df_tgt)
        return self.wrap_page(hero + dept_cards + matrix)

    def _hero_block(self, t_tgt, t_inc, t_pay, inc_rate, pay_rate) -> str:
        """年度总目标 Hero — 收入/回款条可点击同时展开 2 张部门卡（并排）"""
        toggle = "document.getElementById('annual-inc-card-wrapper').classList.toggle('hidden');document.getElementById('annual-pay-card-wrapper').classList.toggle('hidden');this.parentElement.querySelectorAll('.annual-hero-bar').forEach(b=>b.classList.remove('expanded'));this.classList.add('expanded')"
        return f"""<div class="annual-hero">
  <div class="annual-hero-label">📊 年度总目标 · 4 事业部合计</div>
  <div class="annual-hero-value">{fmt_wan(t_tgt)}<span class="annual-hero-unit">万元</span></div>
  <div class="annual-hero-bars">
    <div class="annual-hero-bar" onclick="{toggle}" style="cursor:pointer">
      <span class="annual-hero-name">收入</span>
      <div class="annual-hero-track"><div class="annual-hero-fill inc" style="width:{min(inc_rate*100,100):.1f}%">{inc_rate*100:.1f}%</div></div>
      <span class="annual-hero-val">{fmt_wan(t_inc)}</span>
      <span class="annual-hero-arrow">▸</span>
    </div>
    <div class="annual-hero-bar" onclick="{toggle}" style="cursor:pointer">
      <span class="annual-hero-name">回款</span>
      <div class="annual-hero-track"><div class="annual-hero-fill pay" style="width:{min(pay_rate*100,100):.1f}%">{pay_rate*100:.1f}%</div></div>
      <span class="annual-hero-val">{fmt_wan(t_pay)}</span>
      <span class="annual-hero-arrow">▸</span>
    </div>
  </div>
</div>"""

    def _dept_card_combined(self, df_inc, df_pay, df_tgt) -> str:
        """2 张卡（收入 + 回款）并排展示，共享同一个 click 响应：点击 Hero 同时展开"""
        t_inc = sum(float(df_inc[df_inc["事业部"] == d]["金额_万"].sum()) for d in DEPARTMENTS)
        t_pay = sum(float(df_pay[df_pay["事业部"] == d]["金额_万"].sum()) for d in DEPARTMENTS)
        t_tgt = sum(safe_float(df_tgt[d].sum()) for d in DEPARTMENTS if d in df_tgt.columns)
        return f'<div class="cols-2"><div class="hidden" id="annual-inc-card-wrapper">{self._one_metric_card(df_inc, df_tgt, "收入", "annual-inc-card", t_inc, t_tgt)}</div><div class="hidden" id="annual-pay-card-wrapper">{self._one_metric_card(df_pay, df_tgt, "回款", "annual-pay-card", t_pay, t_tgt)}</div></div>'

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

    def _lower(self, df_inc, df_pay, df_tgt) -> str:
        """重要客户达成表 — 收入/回款 双导航 tab 切换"""
        tgt_pivot = df_tgt.groupby("客户")[[d for d in DEPARTMENTS if d in df_tgt.columns]].sum()
        tgt_pivot["合计"] = tgt_pivot.sum(axis=1)
        inc_pivot = df_inc.pivot_table(index="客户", columns="事业部", values="金额_万", aggfunc="sum", fill_value=0)
        inc_pivot["合计"] = inc_pivot.sum(axis=1)
        pay_pivot = df_pay.pivot_table(index="客户", columns="事业部", values="金额_万", aggfunc="sum", fill_value=0)
        pay_pivot["合计"] = pay_pivot.sum(axis=1)
        important = [c for c in tgt_pivot.index if tgt_pivot.loc[c, "合计"] > 0]
        important.sort(key=lambda c: tgt_pivot.loc[c, "合计"], reverse=True)
        important = important[:20]
        t_inc_all = float(df_inc["金额_万"].sum())
        t_pay_all = float(df_pay["金额_万"].sum())
        imp_i = sum(float(inc_pivot.loc[c, "合计"]) for c in important if c in inc_pivot.index)
        imp_p = sum(float(pay_pivot.loc[c, "合计"]) for c in important if c in pay_pivot.index)
        imp_t = sum(float(tgt_pivot.loc[c, "合计"]) for c in important)

        inc_table = self._matrix("收入", inc_pivot, tgt_pivot, important, imp_i, imp_t, t_inc_all)
        pay_table = self._matrix("回款", pay_pivot, tgt_pivot, important, imp_p, imp_t, t_pay_all)

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
            """生成单元格：左=百分比 / 右=完成+指标两行"""
            if act == 0 and tgt == 0:
                return '<td class="td-empty">—</td>'
            r = act / tgt if tgt else 0
            pct_num = min(r * 100, 100)
            pct_label = f"{r*100:.0f}%"
            if r >= 1:
                pct_cls = " achieved"
            elif r >= 0.5:
                pct_cls = ""
            elif r > 0:
                pct_cls = " low"
            else:
                pct_cls = ""
            if is_total_col:
                return (
                    f'<td class="cell-bg is-total">'
                    f'<div class="cell-text">'
                    f'<span class="cell-pct">{pct_label}</span>'
                    f'<div class="cell-main"><span class="cell-act">完成{fmt_wan(act)}</span><span class="cell-tgt">指标{fmt_wan(tgt)}</span></div>'
                    f'</div></td>'
                )
            # 普通列填充色
            if r >= 1:
                fill_var = "#22c55e"
            elif r >= 0.5:
                fill_var = "#fb923c"
            elif r > 0:
                fill_var = "#fdba74"
            else:
                fill_var = "#f1f5f9"
            empty_cls = " is-empty" if r == 0 else ""
            return (
                f'<td class="cell-bg{empty_cls}" style="--pct:{pct_num:.1f}%;--fill:{fill_var}">'
                f'<div class="fill-bg"></div>'
                f'<div class="cell-text">'
                f'<span class="cell-pct{pct_cls}">{pct_label}</span>'
                f'<div class="cell-main"><span class="cell-act">完成{fmt_wan(act)}</span><span class="cell-tgt">指标{fmt_wan(tgt)}</span></div>'
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
            f'<table class="ann-matrix">{h}<tbody>{tr}{rows}</tbody></table>'
            f'</div>'
            f'<div style="font-size:11px;color:var(--text-muted);margin-top:6px">每格：实际金额 / 目标金额 / 达成率 · 全公司{label}合计 <strong style="color:var(--accent)">{fmt_wan(all_total)}</strong> 万</div>'
        )
