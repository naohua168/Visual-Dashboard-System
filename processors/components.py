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
    """点击母公司查看子公司详情的右侧滑入抽屉（统一ID避免多页冲突）

    行为：点击遮罩层/×/ESC = 关闭；抽屉内部可滚动。
    """
    return (
        f'<div id="{uid}_modal" class="children-modal hidden">'
        f'<div class="children-modal-backdrop" onclick="{uid}_close()"></div>'
        f'<div id="{uid}_panel" class="children-modal-panel">'
        f'<div class="children-modal-header">'
        f'<span id="{uid}_title">子公司详情</span>'
        f'<button onclick="{uid}_close()" title="关闭">×</button>'
        f'</div>'
        f'<div id="{uid}_body" class="children-modal-body"></div>'
        f'</div></div>'
        f'<style>'
        f'.children-modal{{position:fixed;inset:0;z-index:9999}} '
        f'.children-modal.hidden{{display:none}} '
        f'.children-modal-backdrop{{position:absolute;inset:0;background:rgba(0,0,0,0.35);opacity:0;pointer-events:none;transition:opacity 0.25s ease}} '
        f'.children-modal:not(.hidden) .children-modal-backdrop{{opacity:1;pointer-events:auto}} '
        f'.children-modal-panel{{position:fixed;right:0;top:0;width:min(96vw,900px);height:100vh;background:#fff;'
        f'box-shadow:-10px 0 40px rgba(0,0,0,0.18);display:flex;flex-direction:column;'
        f'transform:translateX(100%);transition:transform 0.3s cubic-bezier(0.16,1,0.3,1)}} '
        f'.children-modal-panel.show{{transform:translateX(0)}} '
        f'.children-modal-header{{padding:16px 20px;background:#1e293b;color:#fff;display:flex;justify-content:space-between;align-items:flex-start;flex-shrink:0}} '
        f'.children-modal-header span{{font-size:16px;font-weight:700}} '
        f'.children-modal-header button{{background:transparent;color:#fff;border:none;font-size:22px;cursor:pointer;padding:0 4px;line-height:1}} '
        f'.children-modal-kpi{{font-size:12px;color:#cbd5e1;margin-top:6px}} '
        f'.children-modal-kpi b{{color:#fff;font-weight:600}} '
        f'.children-modal-body{{flex:1;min-height:0;padding:16px 20px;overflow-y:auto;overflow-x:auto}} '
        f'.children-modal-table{{width:100%;border-collapse:collapse;font-size:12px;white-space:nowrap}} '
        f'.children-modal-table th{{position:sticky;top:0;background:#f8fafc;padding:10px 8px;font-weight:600;color:#475569;border-bottom:1px solid #e2e8f0;text-align:center}} '
        f'.children-modal-table td{{padding:8px;border-bottom:1px solid #f1f5f9;text-align:center}} '
        f'.children-modal-table .td-sub-name{{text-align:left;white-space:normal;min-width:160px;font-weight:500;color:#0f172a}} '
        f'.children-modal-table .cell-detail{{position:relative;min-width:110px}} '
        f'.children-modal-table .cell-pct{{font-weight:700;font-size:12px;color:#0f172a}} '
        f'.children-modal-table .cell-amt{{font-size:11px;color:#64748b;margin-top:2px}} '
        f'.children-modal-table .cell-sep{{margin:0 3px;color:#cbd5e1}} '
        f'.children-modal-table .row-total{{background:#f8fafc;font-weight:700}} '
        f'.children-modal-table .row-total .td-sub-name{{font-weight:700}} '
        f'.td-name-clickable{{user-select:none;cursor:pointer;color:var(--accent)}} '
        f'.td-name-clickable:hover{{background:rgba(59,130,246,0.08)}} '
        f'.expand-hint{{font-size:10px;color:var(--accent);margin-left:4px;font-weight:600}}</style>'
    )


def children_modal_js(uid: str, sub_detail_json: str) -> str:
    """抽屉 JS：使用指定 uid 避免多页冲突。渲染子公司×4部门+合计的实际/目标/完成度表格。"""
    return (
        f'<script>'
        f'window["{uid}_DATA"]={sub_detail_json};'
        f'const {uid}_DEPS=["检测","信息","能源","海外","合计"];'
        f'function {uid}_fmt(v){{return Number(v||0).toLocaleString("zh-CN",{{maximumFractionDigits:0}});}}'
        f'function {uid}_cell(act,tgt){{'
        f'act=act||0;tgt=tgt||0;'
        f'var rate=tgt>0?act/tgt:0;'
        f'var pct=Math.min(rate*100,100);'
        f'var bg=rate>0?"linear-gradient(90deg,rgba(59,130,246,0.14) "+pct+"%,transparent "+pct+"%)":"transparent";'
        f'return \'<td class="cell-detail" style="background:\'+bg+\'">\''
        f'+\'<div class="cell-pct">\'+Math.round(rate*100)+\'%</div>\''
        f'+\'<div class="cell-amt">\'+{uid}_fmt(act)+\'<span class="cell-sep">/</span>\'+{uid}_fmt(tgt)+\'</div></td>\';'
        f'}}'
        f'function {uid}_show(el,name){{'
        # 滚动到被点击的行
        f'if(el&&el.scrollIntoView){{el.scrollIntoView({{block:"start",behavior:"smooth"}});}}'
        # 渲染内容
        f'var data=window["{uid}_DATA"][name]||{{}};'
        f'var subs=Object.keys(data);'
        f'if(subs.length===0){{'
        f'document.getElementById("{uid}_title").textContent=name+" · 子公司";'
        f'document.getElementById("{uid}_body").innerHTML="<p style=\\"color:#94a3b8;text-align:center;padding:40px\\">暂无子公司数据</p>";'
        f'}}else{{'
        f'var h="<thead><tr><th>子公司</th>"+{uid}_DEPS.map(d=>"<th>"+d+"</th>").join("")+"</tr></thead>";'
        f'var b="";var total={{}};{uid}_DEPS.forEach(d=>total[d]={{act:0,tgt:0}});'
        f'subs.forEach(s=>{{'
        f'var row=data[s];b+="<tr>";'
        f'b+="<td class=\\"td-sub-name\\">"+s+"</td>";'
        f'{uid}_DEPS.forEach(d=>{{'
        f'var cell=row[d]||{{act:0,tgt:0}};'
        f'b+={uid}_cell(cell.act,cell.tgt);'
        f'total[d].act+=cell.act;total[d].tgt+=cell.tgt;'
        f'}});'
        f'b+="</tr>";'
        f'}});'
        f'b+="<tr class=\\"row-total\\"><td class=\\"td-sub-name\\">合计</td>"+{uid}_DEPS.map(d=>{uid}_cell(total[d].act,total[d].tgt)).join("")+"</tr>";'
        f'document.getElementById("{uid}_body").innerHTML="<table class=\\"children-modal-table\\">"+h+"<tbody>"+b+"</tbody></table>";'
        f'document.getElementById("{uid}_title").textContent=name+" · 子公司 ("+subs.length+"家)";'
        f'}}'
        # 打开抽屉并锁定背景滚动
        f'setTimeout(function(){{'
        f'document.getElementById("{uid}_modal").classList.remove("hidden");'
        f'document.getElementById("{uid}_panel").classList.add("show");'
        f'document.body.style.overflow="hidden";'
        f'}},150);'
        f'}}'
        f'function {uid}_close(){{'
        f'document.getElementById("{uid}_panel").classList.remove("show");'
        f'setTimeout(function(){{document.getElementById("{uid}_modal").classList.add("hidden");document.body.style.overflow="";}},250);'
        f'}}'
        f'document.addEventListener("keydown",function(e){{if(e.key==="Escape"){uid}_close()}});'
        f'</script>'
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
