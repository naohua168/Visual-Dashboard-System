"""Hero 圆环组件 + 工具函数 — 从 base.py 拆分

包含: rate_cls, completion_html, ring_svg_html, hero_rings_html, yoy_html
"""
from __future__ import annotations

from .utils import fmt_wan

def rate_cls(rate: float) -> str:
    """达成率色阶：<30%红 / 30-50%橙 / 50-80%黄 / ≥80%绿"""
    if rate < 0.3:
        return "level-1"
    elif rate < 0.5:
        return "level-2"
    elif rate < 0.8:
        return "level-3"
    else:
        return "level-4"


def completion_html(rate: float, show_bar: bool = True) -> str:
    """生成完成度色块（带百分比数字 + 可选进度条背景）"""
    cls = rate_cls(rate)
    pct = rate * 100
    bar_w = min(pct, 100)
    bar_cls = " bar" if show_bar else ""
    return f'<span class="completion{bar_cls} {cls}" style="--bar-w:{bar_w:.0f}%"><span class="pct">{pct:.1f}%</span></span>'






def ring_svg_html(rate: float, ring_kind: str = "inc", size: int = 96, label: str = "") -> str:
    """SVG 圆环图（完成进度），ring_kind: inc/pay"""
    pct = max(0.0, rate * 100)
    r = (size - 14) / 2
    cx = cy = size / 2
    circ = 2 * 3.141592653589793 * r
    dash = (min(pct, 100) / 100.0) * circ
    return (
        f'<div class="hr-ring {ring_kind}-ring">'
        f'<svg viewBox="0 0 {size} {size}">'
        f'<circle class="hr-track" cx="{cx}" cy="{cy}" r="{r:.2f}"/>'
        f'<circle class="hr-progress" cx="{cx}" cy="{cy}" r="{r:.2f}" '
        f'stroke-dasharray="{dash:.2f} {circ:.2f}" stroke-dashoffset="0"/>'
        f'</svg>'
        f'<div class="hr-center">'
        f'<div class="hr-pct">{pct:.1f}%</div>'
        f'<div class="hr-label">{label}</div>'
        f'</div>'
        f'</div>'
    )


def hero_rings_html(inc_act: float, inc_tgt: float, pay_act: float, pay_tgt: float,
                    toggle_js: str = "", header_left: str = "收入", header_right: str = "回款",
                    inc_yoy: float | None = None, pay_yoy: float | None = None,
                    inc_cust: int = 0, pay_cust: int = 0,
                    inc_sales: int = 0, pay_sales: int = 0,
                    yoy_period: str = "", total_tgt: float | None = None,
                    total_label: str = "总指标", show_cust_sales: bool = True) -> str:
    """5列 Hero 布局（信息丰富版）"""
    # 有实际金额但无指标 → 完成度 100%
    inc_r = 1.0 if (inc_tgt == 0 and inc_act > 0) else (inc_act / inc_tgt if inc_tgt else 0)
    pay_r = 1.0 if (pay_tgt == 0 and pay_act > 0) else (pay_act / pay_tgt if pay_tgt else 0)
    inc_gap = inc_tgt - inc_act
    pay_gap = pay_tgt - pay_act
    onclick = f' onclick="{toggle_js}"' if toggle_js else ""
    cursor = ' style="cursor:pointer"' if toggle_js else ""

    def _yoy_badge(yoy: float | None) -> str:
        if yoy is None:
            return ""
        if yoy >= 0:
            return f'<span class="hr-yoy hr-yoy-up">&#9650; {yoy*100:.1f}%</span>'
        return f'<span class="hr-yoy hr-yoy-dn">&#9660; {abs(yoy)*100:.1f}%</span>'

    def _metric_row(label: str, value: str, cls: str = "") -> str:
        return f'<div class="hr-metric {cls}"><span class="hr-metric-label">{label}</span><span class="hr-metric-val">{value}</span></div>'

    yoy_note = ""  # 取消显示同比时间标签（避免双侧重复）

    chart_icon = (
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" '
        'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" '
        'style="vertical-align:-3px;margin-right:4px">'
        '<line x1="12" y1="20" x2="12" y2="10"/>'
        '<line x1="18" y1="20" x2="18" y2="4"/>'
        '<line x1="6" y1="20" x2="6" y2="16"/>'
        '</svg>'
    )

    # 客户/销售行（可选）
    cust_inc = f'{_metric_row("客户/销售", f"{inc_cust} 家 / {inc_sales} 人")}' if show_cust_sales else ""
    cust_pay = f'{_metric_row("客户/销售", f"{pay_cust} 家 / {pay_sales} 人")}' if show_cust_sales else ""

    # 中间区：total_tgt 传入 → 中间显示"XX总指标"大数字；否则 → 收入实际|回款实际
    if total_tgt is not None:
        center = (
            f'<div class="hr-center-box">'
            f'<div class="hr-center-label">{chart_icon}{total_label}</div>'
            f'<div class="hr-center-value">{fmt_wan(total_tgt)}<span class="hr-center-unit">万元</span></div>'
            f'</div>'
        )
    else:
        center = (
            f'<div class="hr-center-box">'
            f'<div class="hr-center-split">'
            f'<div class="hr-cs-col"><div class="hr-cs-label">收入实际</div><div class="hr-cs-val">{fmt_wan(inc_act)} 万</div></div>'
            f'<div class="hr-cs-div"></div>'
            f'<div class="hr-cs-col"><div class="hr-cs-label">回款实际</div><div class="hr-cs-val">{fmt_wan(pay_act)} 万</div></div>'
            f'</div>'
            f'</div>'
        )
    # 两侧各一环，中间为上面选择的 center 块
    side_rings = (
        f'<div class="hr-side-ring inc-side-ring">{ring_svg_html(inc_r, "inc", 130, header_left)}</div>'
        f'{center}'
        f'<div class="hr-side-ring pay-side-ring">{ring_svg_html(pay_r, "pay", 130, header_right)}</div>'
    )

    return (
        f'<div class="hero-rings"{onclick}{cursor}>'
        f'<div class="hr-side inc-side">'
        f'<div class="hr-side-title"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg> {header_left}指标 {_yoy_badge(inc_yoy)} {yoy_note}</div>'
        f'<div class="hr-side-amount hr-side-target">{fmt_wan(inc_tgt)}<span class="hr-side-unit">万元</span></div>'
        f'<div class="hr-side-metrics">'
        f'{_metric_row("还差", fmt_wan(inc_gap) + " 万", "hr-metric-gap")}'
        f'{cust_inc}'
        f'</div>'
        f'</div>'
        f'{side_rings}'
        f'<div class="hr-side pay-side">'
        f'<div class="hr-side-title"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg> {header_right}指标 {_yoy_badge(pay_yoy)} {yoy_note}</div>'
        f'<div class="hr-side-amount hr-side-target">{fmt_wan(pay_tgt)}<span class="hr-side-unit">万元</span></div>'
        f'<div class="hr-side-metrics">'
        f'{_metric_row("还差", fmt_wan(pay_gap) + " 万", "hr-metric-gap")}'
        f'{cust_pay}'
        f'</div>'
        f'</div>'
        f'</div>'
    )


def yoy_html(current: float, previous: float) -> str:
    """同比色块"""
    if previous == 0 or previous is None:
        return '<span class="yoy-neutral">—</span>'
    rate = (current - previous) / previous
    pct = rate * 100
    if rate >= 0:
        return f'<span class="yoy-up">+{pct:.1f}%</span>'
    else:
        return f'<span class="yoy-down">{pct:.1f}%</span>'


