"""共享 HTML 组件构建器 — cell-bg 填充格 / mini-rate 进度条 / Tab 容器

为 annual / monthly / quarterly / sales 四页提供统一的低级 HTML 构建函数，
消除跨页重复的字符串模板代码。
"""
from __future__ import annotations


# ──────────────────────────────────────────────────────────────
# 色阶常量
# ──────────────────────────────────────────────────────────────
_fill_class = {"achieved": "fg", "": "fo", " low": "fl", "gray": "fy"}


def _rate_color(rate: float) -> tuple[str, str]:
    """返回 (pct_class, fill_class) 基于达成率色阶"""
    if rate >= 1:
        return "achieved", "fg"
    elif rate >= 0.5:
        return "", "fo"
    elif rate > 0:
        return " low", "fl"
    else:
        return "", "fy"


def cell_bg_html(act: float, tgt: float, is_total_col: bool = False,
                 fmt_fn=None) -> str:
    """cell-bg 填充格 — CSS 类替代 --fill 变量，伪元素替代 fill-bg div"""
    _fmt = fmt_fn or (lambda v: f"{v:,.0f}" if v else "—")

    if act == 0 and tgt == 0:
        return '<td class="td-empty">—</td>'

    rate = act / tgt if tgt else 0
    pct_num = min(rate * 100, 100)
    pct_label = f"{rate * 100:.0f}%"
    pct_cls, fill_cls = _rate_color(rate)
    empty_cls = " is-empty" if rate == 0 else ""
    total_cls = " is-total" if is_total_col else ""

    act_str = _fmt(act)
    tgt_str = _fmt(tgt) if tgt > 0 else "—"

    return (
        f'<td class="cb{empty_cls}{total_cls} {fill_cls}" style="--pct:{pct_num:.1f}%"'
        f'><div class="ct"><span class="cp{pct_cls}">{pct_label}</span>'
        f'<div class="cm"><span class="cc"><span class="ca">{act_str}</span>'
        f'<span class="s">/</span><span class="ctv">{tgt_str}</span></span>'
        f'</div></div></td>'
    )


def cell_bg_pct_only(pct: float) -> str:
    """cell-bg 仅显示百分比"""
    if pct == 0:
        return '<td class="td-empty">—</td>'
    pct_num = min(pct * 100, 100)
    pct_label = f"{pct * 100:.0f}%"
    pct_cls, fill_cls = _rate_color(pct)
    return (
        f'<td class="cb {fill_cls}" style="--pct:{pct_num:.1f}%"'
        f'><div class="ct"><span class="cp{pct_cls}">{pct_label}</span>'
        f'<div class="cm"><span class="ca">{pct_label}</span></div>'
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
        f"onclick=\"document.getElementById('{inc_div_id}').classList.remove('hidden');"
        f"document.getElementById('{pay_div_id}').classList.add('hidden');"
        f"this.parentElement.querySelectorAll('.cust-tab').forEach(t=>t.classList.remove('active'));"
        f"this.classList.add('active')\">收入</span>"
        f'<span class="cust-tab pay" '
        f"onclick=\"document.getElementById('{inc_div_id}').classList.add('hidden');"
        f"document.getElementById('{pay_div_id}').classList.remove('hidden');"
        f"this.parentElement.querySelectorAll('.cust-tab').forEach(t=>t.classList.remove('active'));"
        f"this.classList.add('active')\">回款</span>"
        f'</div>'
    )


def children_modal_html(uid: str) -> str:
    """点击母公司查看子公司详情的弹窗 HTML+JS+CSS（统一ID避免冲突）"""
    return (
        f'<div id="{uid}_modal" class="children-modal hidden">'
        f'<div class="children-modal-box">'
        f'<div class="children-modal-header">'
        f'<span id="{uid}_title">子公司列表</span>'
        f'<button onclick="document.getElementById(\'{uid}_modal\').classList.add(\'hidden\')">×</button>'
        f'</div>'
        f'<div id="{uid}_body" class="children-modal-body"></div>'
        f'</div></div>'
        f'<style>.children-modal{{position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:9999;display:flex;align-items:center;justify-content:center}} '
        f'.children-modal.hidden{{display:none}} '
        f'.children-modal-box{{background:#fff;border-radius:8px;width:520px;max-height:80vh;overflow:hidden;display:flex;flex-direction:column;box-shadow:0 8px 32px rgba(0,0,0,0.3)}} '
        f'.children-modal-header{{padding:14px 18px;background:#1e293b;color:#fff;display:flex;justify-content:space-between;align-items:center;font-weight:600}} '
        f'.children-modal-header button{{background:transparent;color:#fff;border:none;font-size:20px;cursor:pointer;padding:0 4px}} '
        f'.children-modal-body{{padding:14px 18px;overflow-y:auto;flex:1}} '
        f'.children-modal-body ul{{list-style:none;padding:0;margin:0}} '
        f'.children-modal-body li{{padding:8px 10px;border-bottom:1px solid #e5e7eb;font-size:13px}} '
        f'.children-modal-body li:last-child{{border-bottom:none}} '
        f'.td-name-clickable{{user-select:none;cursor:pointer;color:var(--accent)}} '
        f'.td-name-clickable:hover{{background:rgba(59,130,246,0.08)}} '
        f'.expand-hint{{font-size:10px;color:var(--accent);margin-left:4px;font-weight:600}}</style>'
    )


def children_modal_js(uid: str, sub_data_json: str) -> str:
    """弹窗 JS：使用指定 uid 避免多页冲突"""
    return (
        f'<script>window["{uid}_DATA"]={sub_data_json};'
        f'function {uid}_show(name,n){{var data=window["{uid}_DATA"][name]||[];'
        f'var html="<ul>";data.forEach(s=>{{html+="<li>"+s+"</li>"}});html+="</ul>";'
        f'document.getElementById("{uid}_title").textContent=name+" · 子公司 ("+data.length+"家)";'
        f'document.getElementById("{uid}_body").innerHTML=html;'
        f'document.getElementById("{uid}_modal").classList.remove("hidden")}}</script>'
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
    # 兼容 xxx / xxx收入 / xxx回款 三种列命名
    def _tgt_col(dept: str) -> str | None:
        for c in [dept, f"{dept}收入", f"{dept}回款"]:
            if c in df_tgt.columns:
                return c
        return None
    total_tgt = sum(
        float(df_tgt[c].sum() if hasattr(df_tgt[c], 'sum') else 0)
        for d in departments if (c := _tgt_col(d))
    )
    total_tgt = float(total_tgt)

    rows = ""
    for d in departments:
        act = (
            float(df[df["事业部"] == d]["金额_万"].sum())
            if df is not None and "事业部" in df.columns else 0
        )
        tgt_col = _tgt_col(d)
        tgt = float(df_tgt[tgt_col].sum()) if tgt_col else 0
        rows += mini_rate_row(d, act, tgt, name_width=48, fmt_fn=_fmt)

    rows += mini_rate_summary_row("合计", total_act, total_tgt,
                                  name_width=48, fmt_fn=_fmt)

    return (
        f'<div class="card">'
        f'<div class="card-title">{metric}完成度{title_extra}</div>'
        f'{rows}'
        f'</div>'
    )
