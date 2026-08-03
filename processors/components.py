"""共享 HTML 组件构建器 — cell-bg 填充格 / mini-rate 进度条 / Tab 容器

为 annual / monthly / quarterly / sales 四页提供统一的低级 HTML 构建函数，
消除跨页重复的字符串模板代码。
"""
from __future__ import annotations


# ──────────────────────────────────────────────────────────────
# 色阶常量
# ──────────────────────────────────────────────────────────────
_FILL_GREEN = "#22c55e"
_FILL_ORANGE = "#fb923c"
_FILL_LIGHT = "#fdba74"
_FILL_GRAY = "#f1f5f9"


def _rate_color(rate: float) -> tuple[str, str]:
    """返回 (pct_class, fill_color) 基于达成率色阶"""
    if rate >= 1:
        return "achieved", _FILL_GREEN
    elif rate >= 0.5:
        return "", _FILL_ORANGE
    elif rate > 0:
        return " low", _FILL_LIGHT
    else:
        return "", _FILL_GRAY


def cell_bg_html(act: float, tgt: float, is_total_col: bool = False,
                 fmt_fn=None) -> str:
    """cell-bg 填充格 — 所有页面统一的单元格渲染器

    左百分比 + 右「完成金额 / 目标金额」两行布局。
    合计列使用 is-total 样式（透明底+边框强调，不用实色填充块）。

    Args:
        act: 实际值
        tgt: 目标值
        is_total_col: 是否为合计列
        fmt_fn: 格式化函数（默认用 format(act, ',.0f')）
    """
    _fmt = fmt_fn or (lambda v: f"{v:,.0f}" if v else "—")

    if act == 0 and tgt == 0:
        return '<td class="td-empty">—</td>'

    rate = act / tgt if tgt else 0
    pct_num = min(rate * 100, 100)
    pct_label = f"{rate * 100:.0f}%"
    pct_cls, fill_var = _rate_color(rate)
    empty_cls = " is-empty" if rate == 0 else ""
    total_cls = " is-total" if is_total_col else ""

    act_str = _fmt(act)
    tgt_str = _fmt(tgt) if tgt > 0 else "—"

    return (
        f'<td class="cell-bg{empty_cls}{total_cls}" style="--pct:{pct_num:.1f}%;--fill:{fill_var}">'
        f'<div class="fill-bg"></div>'
        f'<div class="cell-text">'
        f'<span class="cell-pct{pct_cls}">{pct_label}</span>'
        f'<div class="cell-main">'
        f'<span class="cell-compact"><span class="cell-act-val">{act_str}</span>'
        f'<span class="sep">/</span><span class="cell-tgt-val">{tgt_str}</span></span>'
        f'</div></div></td>'
    )


def cell_bg_pct_only(pct: float) -> str:
    """cell-bg 仅显示百分比（用于数据总览页部门矩阵的完成度列）"""
    if pct == 0:
        return '<td class="td-empty">—</td>'
    pct_num = min(pct * 100, 100)
    pct_label = f"{pct * 100:.0f}%"
    pct_cls, fill_var = _rate_color(pct)
    return (
        f'<td class="cell-bg" style="--pct:{pct_num:.1f}%;--fill:{fill_var}">'
        f'<div class="fill-bg"></div>'
        f'<div class="cell-text">'
        f'<span class="cell-pct{pct_cls}">{pct_label}</span>'
        f'<div class="cell-main"><span class="cell-act">{pct_label}</span></div>'
        f'</div></td>'
    )


def mini_rate_row(name: str, act: float, tgt: float, name_width: int = 48,
                  fmt_fn=None) -> str:
    """mini-rate 进度条行 — 统一的行构建器

    结构: [名称(width)] [进度条+百分比] [实际值] [/目标值]
    """
    _fmt = fmt_fn or (lambda v: f"{v:,.0f}")
    rate = act / tgt if tgt else 0
    rate_cls = _rate_color(rate)[0]
    bar_cls = rate_cls or "level-4" if rate >= 0.8 else ""
    bar_cls = bar_cls.replace("achieved", "level-4").replace(" low", "level-2")
    if rate < 0.3:
        bar_cls = "level-1"
    elif rate < 0.5:
        bar_cls = "level-2"
    elif rate < 0.8:
        bar_cls = "level-3"
    else:
        bar_cls = "level-4"

    return (
        f'<div class="mini-rate">'
        f'<span style="width:{name_width}px;font-weight:600">{name}</span>'
        f'<div class="bar"><div class="bar-fill {bar_cls}" style="width:{min(rate*100,100):.1f}%">'
        f'<span class="bar-pct">{rate*100:.1f}%</span></div></div>'
        f'<span class="val">{_fmt(act)}</span>'
        f'<span style="color:var(--text-muted);font-size:11px">/{_fmt(tgt) if tgt > 0 else "—"}</span>'
        f'</div>'
    )


def mini_rate_summary_row(name: str, act: float, tgt: float,
                          name_width: int = 48, fmt_fn=None) -> str:
    """mini-rate 合计行（带顶部分割线）"""
    _fmt = fmt_fn or (lambda v: f"{v:,.0f}")
    rate = act / tgt if tgt else 0
    rate_cls = _rate_color(rate)[0]
    if rate < 0.3:
        bar_cls = "level-1"
    elif rate < 0.5:
        bar_cls = "level-2"
    elif rate < 0.8:
        bar_cls = "level-3"
    else:
        bar_cls = "level-4"

    return (
        f'<div class="mini-rate" style="border-top:2px solid var(--border);padding-top:8px;margin-top:4px">'
        f'<span style="width:{name_width}px;font-weight:700">{name}</span>'
        f'<div class="bar"><div class="bar-fill {bar_cls}" style="width:{min(rate*100,100):.1f}%">'
        f'<span class="bar-pct">{rate*100:.1f}%</span></div></div>'
        f'<span class="val">{_fmt(act)}</span>'
        f'<span style="color:var(--text-muted);font-size:11px">/{_fmt(tgt) if tgt > 0 else "—"}</span>'
        f'</div>'
    )


def cust_tab_bar(inc_div_id: str, pay_div_id: str) -> str:
    """收入/回款 Tab 切换导航栏（隐藏/显示容器 ID 由调用方自定）"""
    return (
        f'<div class="cust-tabs">'
        f'<span class="cust-tab active inc" '
        f'onclick="document.getElementById(\'{inc_div_id}\').classList.remove(\'hidden\');'
        f'document.getElementById(\'{pay_div_id}\').classList.add(\'hidden\');'
        f'this.parentElement.querySelectorAll(\'.cust-tab\').forEach(t=>t.classList.remove(\'active\'));'
        f'this.classList.add(\'active\')">收入</span>'
        f'<span class="cust-tab pay" '
        f'onclick="document.getElementById(\'{inc_div_id}\').classList.add(\'hidden\');'
        f'document.getElementById(\'{pay_div_id}\').classList.remove(\'hidden\');'
        f'this.parentElement.querySelectorAll(\'.cust-tab\').forEach(t=>t.classList.remove(\'active\'));'
        f'this.classList.add(\'active\')">回款</span>'
        f'</div>'
    )


def hidden_dept_card_wrapper(content: str, wrap_id: str) -> str:
    """hidden 包装的部门卡片容器（初始隐藏，Hero 点击展开）"""
    return f'<div class="hidden" id="{wrap_id}">\n<div class="cols-2">\n{content}\n</div>\n</div>'


def dept_card_html(df, df_tgt, departments: list[str], metric: str,
                   title_extra: str = "", fmt_fn=None) -> str:
    """部门完成度单指标卡 — mini-rate × N 部门 + 合计行

    Args:
        df: 实际数据 DataFrame（需含 事业部、金额_万 列）
        df_tgt: 目标 DataFrame（列名为部门名）
        departments: 部门列表
        metric: 指标名（"收入" / "回款"）
        title_extra: 标题后缀
        fmt_fn: 格式化函数
    """
    _fmt = fmt_fn or (lambda v: f"{v:,.0f}")

    total_act = sum(
        float(df[df["事业部"] == d]["金额_万"].sum()) if df is not None else 0
        for d in departments
    )
    total_tgt = sum(
        (df_tgt[d].sum() if hasattr(df_tgt[d], 'sum') else 0)
        for d in departments if d in df_tgt.columns
    )
    total_tgt = float(total_tgt)

    rows = ""
    for d in departments:
        act = (
            float(df[df["事业部"] == d]["金额_万"].sum())
            if df is not None and "事业部" in df.columns else 0
        )
        tgt = (
            float(df_tgt[d].sum()) if d in df_tgt.columns else 0
        )
        rows += mini_rate_row(d, act, tgt, name_width=48, fmt_fn=_fmt)

    rows += mini_rate_summary_row("合计", total_act, total_tgt,
                                  name_width=48, fmt_fn=_fmt)

    return (
        f'<div class="card">'
        f'<div class="card-title">{metric}完成度{title_extra}</div>'
        f'{rows}'
        f'</div>'
    )
