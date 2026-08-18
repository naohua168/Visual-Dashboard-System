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
    """点击母公司查看子公司详情的左右联动抽屉（同一图层，同时出现/消失）

    结构（一个 modal 容器内）：
    - backdrop（半透明遮罩，点击关闭）
    - .children-left-panel  子公司名列表（左侧 slide-in）
    - .children-modal-panel 子公司×4部门详情（右侧 slide-in）
    左右 panel 共用同一个开关函数，同一图层显示/隐藏。
    """
    return (
        f'<div id="{uid}_modal" class="children-modal hidden">'
        # 单一遮罩（覆盖中间空白区，点击关闭）
        f'<div class="children-modal-backdrop" onclick="{uid}_close()"></div>'
        # 左侧 panel：子公司名列表
        f'<div id="{uid}_left_panel" class="children-left-panel">'
        f'<div class="children-left-header">'
        f'<span id="{uid}_left_title">子公司列表</span>'
        f'<button onclick="{uid}_close()" title="关闭">×</button>'
        f'</div>'
        f'<div id="{uid}_left_body" class="children-left-body"></div>'
        f'</div>'
        # 右侧 panel：子公司×4部门详情
        f'<div id="{uid}_panel" class="children-modal-panel">'
        f'<div class="children-modal-header">'
        f'<div style="display:flex;flex-direction:column;gap:4px;min-width:0">'
        f'<span id="{uid}_title">子公司详情</span>'
        f'<div id="{uid}_kpi" class="children-modal-kpi"></div>'
        f'</div>'
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
        f'.children-left-panel{{position:fixed;left:0;top:0;width:min(70vw,360px);height:100vh;background:#fff;'
        f'box-shadow:10px 0 40px rgba(0,0,0,0.18);display:flex;flex-direction:column;'
        f'transform:translateX(-100%);transition:transform 0.3s cubic-bezier(0.16,1,0.3,1)}} '
        f'.children-left-panel.show{{transform:translateX(0)}} '
        f'.children-modal-header{{padding:16px 20px;background:#1e293b;color:#fff;display:flex;justify-content:space-between;align-items:flex-start;flex-shrink:0}} '
        f'.children-modal-header span{{font-size:16px;font-weight:700}} '
        f'.children-modal-header button{{background:transparent;color:#fff;border:none;font-size:22px;cursor:pointer;padding:0 4px;line-height:1}} '
        f'.children-left-header{{padding:16px 20px;background:#1e293b;color:#fff;display:flex;justify-content:space-between;align-items:center;flex-shrink:0}} '
        f'.children-left-header span{{font-size:15px;font-weight:700}} '
        f'.children-left-header button{{background:transparent;color:#fff;border:none;font-size:22px;cursor:pointer;padding:0 4px;line-height:1}} '
        f'.children-modal-kpi{{font-size:12px;color:#cbd5e1;margin-top:6px}} '
        f'.children-modal-kpi b{{color:#fff;font-weight:600}} '
        f'.children-modal-body{{flex:1;min-height:0;padding:16px 20px;overflow-y:auto;overflow-x:auto}} '
        f'.children-left-body{{flex:1;min-height:0;padding:10px 12px;overflow-y:auto}} '
        f'.children-left-item{{padding:8px 10px;border-radius:6px;font-size:13px;color:#1e293b;cursor:pointer;'
        f'border-bottom:1px solid #f1f5f9;transition:background 0.12s}} '
        f'.children-left-item:hover{{background:#eef2ff}} '
        f'.children-left-item .li-idx{{color:#94a3b8;font-weight:400;margin-right:8px;font-size:11px}} '
        f'.children-left-empty{{text-align:center;color:#94a3b8;padding:40px 10px;font-size:13px}} '
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
        f'.children-modal-table .row-total-top td{{background:#eef2ff!important;border-top:2px solid #c7d2fe;border-bottom:2px solid #c7d2fe}} '
        f'.children-modal-table .row-total-top .td-sub-name{{color:#1e3a8a}} '
        f'.children-modal-table .row-head-office td{{background:#fffbeb}} '
        f'.children-modal-table .row-head-office .td-sub-name{{color:#92400e}} '
        f'.children-modal-table .td-sub-name .sub-idx{{color:#94a3b8;font-weight:400;margin-right:6px}} '
        f'.children-modal-table .td-sub-name .sub-dot{{color:#c7d2fe;margin:0 4px}} '
        f'.children-modal-table tr.sub-highlight td{{background:rgba(59,130,246,0.18)!important}} '
        f'.children-modal-table tr.sub-highlight .td-sub-name{{color:#1e3a8a;font-weight:700}} '
        f'.td-name-clickable{{user-select:none;cursor:pointer;color:var(--accent)}} '
        f'.td-name-clickable:hover{{background:rgba(59,130,246,0.08)}} '
        f'.expand-hint{{font-size:10px;color:var(--accent);margin-left:4px;font-weight:600}}</style>'
    )


def children_modal_js(uid: str, sub_detail_json: str, left_data_json: str = "[]") -> str:
    """抽屉 JS：使用指定 uid 避免多页冲突。渲染子公司×4部门+合计的实际/目标/完成度表格 + 左侧子公司名列表。"""
    return (
        f'<script>'
        f'window["{uid}_DATA"]={sub_detail_json};'
        f'window["{uid}_LEFT"]={left_data_json};'
        f'const {uid}_DEPS=["检测","信息","能源","海外","合计"];'
        f'function {uid}_fmt(v){{return Number(v||0).toLocaleString("zh-CN",{{maximumFractionDigits:0}});}}'
        f'function {uid}_cell(act,tgt){{'
        f'act=act||0;tgt=tgt||0;'
        # 0/0 → "—"，act>0 且 tgt=0 → 超额100%，act>0 且 tgt>0 → act/tgt
        f'if(act===0&&tgt===0){{return \'<td class="cell-detail is-empty"><div class="cell-pct">—</div><div class="cell-amt">—<span class="cell-sep">/</span>—</div></td>\';}}'
        f'var rate=tgt>0?act/tgt:Infinity;'
        f'var pctTxt=tgt>0?Math.round(rate*100)+"%":"100%";'
        f'var pct=isFinite(rate)?Math.min(rate*100,100):100;'
        f'var bg=pct>0?"linear-gradient(90deg,rgba(59,130,246,0.14) "+pct+"%,transparent "+pct+"%)":"transparent";'
        f'var pctColor=(!isFinite(rate)||rate>=1)?"#16a34a":rate>=0.5?"#f59e0b":"#ef4444";'
        f'return \'<td class="cell-detail" style="background:\'+bg+\'">\''
        f'+\'<div class="cell-pct" style="color:\'+pctColor+\'">\'+pctTxt+\'</div>\''
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
        f'document.getElementById("{uid}_kpi").innerHTML="";'
        f'document.getElementById("{uid}_body").innerHTML="<p style=\\"color:#94a3b8;text-align:center;padding:40px\\">暂无子公司数据</p>";'
        f'}}else{{'
        # 分离"母公司本部"行与子公司行
        f'var headOffice=null,subList=[];'
        f'subs.forEach(function(s){{if(s.indexOf("（本部）")>=0){{headOffice=s;}}else{{subList.push(s);}}}});'
        # 母公司合计 = 本部 + 全部子公司（先全量累加）
        f'var total={{}};{uid}_DEPS.forEach(d=>total[d]={{act:0,tgt:0}});'
        f'var allRows=[headOffice].concat(subList);'
        f'allRows.forEach(function(s){{if(!s)return;var row=data[s];{uid}_DEPS.forEach(function(d){{var cell=row[d]||{{act:0,tgt:0}};total[d].act+=cell.act;total[d].tgt+=cell.tgt;}});}});'
        # 1:1 = 仅一家子公司且无本部 → 简化展示（不重复合计）
        f'var isSingle=(subList.length===1)&&(headOffice===null);'
        # KPI：母公司实际/目标/完成度
        f'var kAct=total["合计"].act,kTgt=total["合计"].tgt;'
        f'var kRate=kTgt>0?Math.round(kAct/kTgt*100):(kAct>0?100:0);'
        f'var kCls=kTgt>0?(kRate>=100?"#16a34a":kRate>=50?"#f59e0b":"#ef4444"):"#cbd5e1";'
        f'document.getElementById("{uid}_kpi").innerHTML="实际 <b>"+{uid}_fmt(kAct)+"</b> 万 · 目标 <b>"+{uid}_fmt(kTgt)+"</b> 万 · 完成度 <b style=\\"color:"+kCls+"\\">"+kRate+"%</b>";'
        # 表头
        f'var h="<thead><tr><th>子公司</th>"+{uid}_DEPS.map(d=>"<th>"+d+"</th>").join("")+"</tr></thead>";'
        f'var b="";'
        # ① 母公司合计行置顶（1:1 时省略，底部不再重复）
        f'if(!isSingle){{'
        f'b+="<tr class=\\"row-total row-total-top\\"><td class=\\"td-sub-name\\">▸ "+name+" 合计</td>"+{uid}_DEPS.map(d=>{uid}_cell(total[d].act,total[d].tgt)).join("")+"</tr>";'
        f'}}'
        # ② 母公司本部行（原始数据中直接挂母公司名下、未拆给子公司的金额）
        f'if(headOffice){{'
        f'var hrow=data[headOffice];b+="<tr class=\\"row-head-office\\"><td class=\\"td-sub-name\\">▸ 母公司本部</td>";'
        f'{uid}_DEPS.forEach(function(d){{var cell=hrow[d]||{{act:0,tgt:0}};b+={uid}_cell(cell.act,cell.tgt);}});'
        f'b+="</tr>";'
        f'}}'
        # ③ 子公司明细行（带序号 + data-sub 供左侧列表联动定位）
        f'subList.forEach(function(s,i){{'
        f'var row=data[s];b+="<tr data-sub=\\""+s+"\\"><td class=\\"td-sub-name\\"><span class=\\"sub-idx\\">"+(i+1)+".</span>"+s+"</td>";'
        f'{uid}_DEPS.forEach(function(d){{var cell=row[d]||{{act:0,tgt:0}};b+={uid}_cell(cell.act,cell.tgt);}});'
        f'b+="</tr>";'
        f'}});'
        # ④ 1:1 无本部时：单子公司行即全部，底部补合计行便于对账
        f'if(isSingle){{'
        f'b+="<tr class=\\"row-total\\"><td class=\\"td-sub-name\\">合计</td>"+{uid}_DEPS.map(d=>{uid}_cell(total[d].act,total[d].tgt)).join("")+"</tr>";'
        f'}}'
        f'document.getElementById("{uid}_body").innerHTML="<table class=\\"children-modal-table\\">"+h+"<tbody>"+b+"</tbody></table>";'
        f'document.getElementById("{uid}_title").textContent=name+" · 子公司 ("+subList.length+"家)";'
        f'var leftSubs=window["{uid}_LEFT"]&&window["{uid}_LEFT"][name]||[];'
        f'document.getElementById("{uid}_left_title").textContent=name+" · 子公司列表 ("+leftSubs.length+"家)";'
        f'var lb="";'
        f'if(!leftSubs.length){{'
        f'lb=\'<div class="children-left-empty">该母公司暂无配置子公司</div>\';'
        f'}}else{{'
        f'leftSubs.forEach(function(s,i){{'
        f'var isHO=(s.indexOf("（本部）")>=0);'
        f'lb+=\'<div class="children-left-item" onclick="{uid}_left_pick(\\\'\'+s.replace(/\'/g,"\\\\\'")+\'\\\')" '
        f'title="点击右侧查看详情">\''
        f'+\'<span class="li-idx">\'+(isHO?"※":(i+1))+\'.</span>\'+s+\'</div>\';'
        f'}});'
        f'}}'
        f'document.getElementById("{uid}_left_body").innerHTML=lb;'
        f'}}'
        # 打开抽屉并锁定背景滚动：左右 panel 同步出现（同一图层）
        f'setTimeout(function(){{'
        f'document.getElementById("{uid}_modal").classList.remove("hidden");'
        f'document.getElementById("{uid}_panel").classList.add("show");'
        f'var lp=document.getElementById("{uid}_left_panel");if(lp)lp.classList.add("show");'
        f'document.body.style.overflow="hidden";'
        # 打开时清除上一次高亮
        f'if(window["{uid}_cur_hl_clear"]){{{uid}_cur_hl_clear();}}'
        f'}},150);'
        f'}}'
        f'function {uid}_close(){{'
        f'document.getElementById("{uid}_panel").classList.remove("show");'
        f'var lp=document.getElementById("{uid}_left_panel");if(lp)lp.classList.remove("show");'
        f'setTimeout(function(){{document.getElementById("{uid}_modal").classList.add("hidden");document.body.style.overflow="";}},250);'
        f'}}'
        # 左侧列表联动：滚动右侧抽屉到指定子公司行并高亮
        f'function {uid}_scroll_to_sub(subName){{'
        f'var rows=document.querySelectorAll("#{uid}_body tr[data-sub]");'
        f'for(var i=0;i<rows.length;i++){{'
        f'var r=rows[i];'
        f'if(r.getAttribute("data-sub")===subName){{'
        f'r.scrollIntoView({{block:"center",behavior:"smooth"}});'
        f'window["{uid}_CUR_HL"]={uid}_cur_hl_clear();'
        f'r.classList.add("sub-highlight");'
        f'window["{uid}_CUR_HL"]=r;'
        f'return;'
        f'}}}}'
        f'}}'
        # 清除上一个高亮行
        f'function {uid}_cur_hl_clear(){{'
        f'var p=window["{uid}_CUR_HL"];'
        f'if(p){{p.classList.remove("sub-highlight");}}'
        f'return null;'
        f'}}'
        # 左侧列表项点击 → 滚动右侧到对应行
        f'function {uid}_left_pick(subName){{'
        f'var fn=window["{uid}_scroll_to_sub"];'
        f'if(fn){{setTimeout(function(){{fn(subName);}},200);}}'
        f'}}'
        f'document.addEventListener("keydown",function(e){{if(e.key==="Escape"){{{uid}_close();}}}});'
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
