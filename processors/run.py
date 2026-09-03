"""渲染主入口 — 6页数据看板"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

import pandas as pd

from .data_loader import load_all
from .base import GLOBAL_CSS, GLOBAL_JS, GLOBAL_OV_CSS
from .page_overview import OverviewPage
from .page_annual import AnnualPage
from .page_yoy import YoyPage
from .page_quarterly import QuarterlyPage
from .page_monthly import MonthlyPage
from .page_sales import SalesPage

BASE_DIR = Path(__file__).parent.parent.resolve()
CHART_JS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"


def _chartjs_snippet() -> str:
    """Chart.js 注入片段：优先本地内联（离线/内网可用），本地缺失时回退 CDN"""
    local = BASE_DIR / "processors" / "static" / "chart.umd.min.js"
    if local.exists():
        # 防御性转义，防止未来构建版本出现 </script> 破坏 HTML 解析
        js = local.read_text(encoding="utf-8").replace("</script>", "<\\/script>")
        return f"<script>{js}</script>"
    return (
        "<script>\n"
        "// Chart.js CDN 兜底加载（本地 processors/static/chart.umd.min.js 缺失时启用）\n"
        "(function(){\n"
        "  var s=document.createElement('script');\n"
        "  s.src='" + CHART_JS_CDN + "';\n"
        "  s.async=true;\n"
        "  s.defer=true;\n"
        "  s.onerror=function(){console.warn('Chart.js CDN failed; charts will be skipped')};\n"
        "  document.head.appendChild(s);\n"
        "})();\n"
        "</script>"
    )


def _load_config() -> dict:
    cfg_path = BASE_DIR / "config" / "清洗配置" / "cleaning_config.json"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_frontend_config() -> dict:
    cfg_path = BASE_DIR / "config" / "前端渲染" / "看板展示配置.json"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)

# 页面ID→渲染器类映射
_PAGE_REGISTRY = {
    "overview": OverviewPage,
    "annual": AnnualPage,
    "yoy": YoyPage,
    "quarterly": QuarterlyPage,
    "monthly": MonthlyPage,
    "sales": SalesPage,
}


def _log(source: str, msg: str, level: str = "INFO"):
    prefix = {"INFO": "  ", "WARN": "  ⚠️ ", "ERROR": "  ❌ ", "OK": "  ✅ "}
    print(f"{prefix.get(level, '  ')}[{source}] {msg}")


def build_html(data, title: str, frontend_cfg: dict) -> str:
    # 从配置读取页面顺序
    page_order = frontend_cfg.get("页面顺序", {}).get("顺序", ["数据总览", "年度达成", "月度达成", "季度达成", "销售达成", "年度同比"])
    page_map = frontend_cfg.get("页面映射", {})
    pages = []
    for name in page_order:
        info = page_map.get(name, {})
        pid = info.get("page_id", "")
        nav = info.get("nav_name", name)
        cls = _PAGE_REGISTRY.get(pid)
        if cls:
            p = cls()
            p.base_dir = BASE_DIR  # 传递基础路径供读取配置
            p.nav_name = nav  # 可被配置覆盖
            pages.append(p)
    # 如果没有配置任何页面，使用默认全部
    if not pages:
        pages = [OverviewPage(), AnnualPage(), MonthlyPage(), QuarterlyPage(), SalesPage(), YoyPage()]
    # 每个页面用 template 包裹（懒加载：浏览器不解析，切换时克隆注入）
    tpls = "".join(
        f'<template id="tpl-{p.page_id}">\n{p.render(data)}\n</template>'
        for p in pages
    )
    page_html = tpls + '<script>setTimeout(window.__resizeAllCharts, 200);</script>'
    nav_items = "".join(
        f'<a data-target="{p.page_id}" href="#" class="{"active" if i == 0 else ""}" '
        f'onclick="showPage(\'{p.page_id}\'); return false;">{p.nav_name}</a>'
        for i, p in enumerate(pages)
    )
    today = datetime.date.today().strftime("%Y-%m-%d")
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=5.0">
<title>{title} · {today}</title>
<style>{GLOBAL_CSS}{GLOBAL_OV_CSS}</style>
{_chartjs_snippet()}
</head>
<body>
<script>{GLOBAL_JS}</script>
<header class="header">
  <div class="header-top">
    <h1 class="header-title">{title}</h1>
  </div>
  <div class="header-bottom">
    <nav class="nav">{nav_items}</nav>
    <button class="fullscreen-btn" onclick="toggleFullscreen()" title="全屏切换 (ESC退出)">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
        <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
      </svg>
      <span>全屏</span>
    </button>
  </div>
</header>
<script>
function toggleFullscreen(){{
  var el=document.documentElement;
  var isFS=document.fullscreenElement||document.webkitFullscreenElement||document.mozFullScreenElement||document.msFullscreenElement;
  if(!isFS){{
    var fn=el.requestFullscreen||el.webkitRequestFullscreen||el.mozRequestFullScreen||el.msRequestFullscreen;
    if(fn) fn.call(el).catch(function(e){{console.warn('全屏失败:',e)}});
  }}else{{
    var fn=document.exitFullscreen||document.webkitExitFullscreen||document.mozCancelFullScreen||document.msExitFullscreen;
    if(fn) fn.call(document);
  }}
}}
function _fsUpdate(){{
  var fs=document.fullscreenElement||document.webkitFullscreenElement||document.mozFullScreenElement||document.msFullscreenElement;
  var btn=document.querySelector('.fullscreen-btn span');
  if(btn) btn.textContent = fs ? '退出' : '全屏';
}}
document.addEventListener('fullscreenchange',_fsUpdate);
document.addEventListener('webkitfullscreenchange',_fsUpdate);
document.addEventListener('mozfullscreenchange',_fsUpdate);
document.addEventListener('MSFullscreenChange',_fsUpdate);
</script>
<main>
<div id="page-host"></div>
{page_html}
</main>
</body>
</html>"""


def run_render(output_path: str | None = None) -> Path:
    frontend_cfg = _load_frontend_config()
    title = frontend_cfg.get("看板标题", {}).get("标题", "销售运营可视化看板")
    file_cfg = frontend_cfg.get("文件输出", {})

    _log("渲染", "加载数据")
    data = load_all(BASE_DIR)
    _log("渲染", f"收入 {len(data.income)} 行 / 回款 {len(data.payment)} 行")
    _log("渲染", f"销售收入 {len(data.sales_income)} 行 / 销售回款 {len(data.sales_payment)} 行")
    _log("渲染", f"年基线: {'已就绪' if data.has_yearly_baseline else '未就绪'}")

    _log("渲染", "构建 HTML")
    html = build_html(data, title, frontend_cfg)

    if output_path:
        out = Path(output_path)
        if not out.is_absolute():
            out = BASE_DIR / output_path
    else:
        base_out = BASE_DIR / file_cfg.get("目录", "output")
        html_dir = base_out / "看板"
        data_dir = base_out / "数据"
        html_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        today = datetime.date.today().strftime("%Y%m%d")
        filename = file_cfg.get("看板文件名", "看板_{date}.html").format(date=today)
        out = html_dir / filename

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    _log("渲染", f"已写入 {out.relative_to(BASE_DIR)}（{len(html)/1024:.1f} KB）", "OK")

    # 输出汇总 Excel
    _log("渲染", "生成汇总 Excel 数据表")
    if output_path:
        excel_dir = out.parent
    else:
        excel_dir = data_dir
    excel_path = excel_dir / f"data_{datetime.date.today().strftime('%Y%m%d')}.xlsx"
    try:
        # sheet 名称与 data/sheets/ 下文件夹名称完全一致（系统数据清理 + 手动维护）
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            data.income.to_excel(writer, sheet_name="当年累计收入", index=False)
            data.payment.to_excel(writer, sheet_name="当年累计回款", index=False)
            data.sales_income.to_excel(writer, sheet_name="销售收入", index=False)
            data.sales_payment.to_excel(writer, sheet_name="销售回款", index=False)
            if data.quarterly_income is not None:
                data.quarterly_income.to_excel(writer, sheet_name="季度累计收入", index=False)
            if data.quarterly_payment is not None:
                data.quarterly_payment.to_excel(writer, sheet_name="季度累计回款", index=False)
            if data.yearly_income is not None:
                data.yearly_income.to_excel(writer, sheet_name="往年收入", index=False)
            if data.yearly_payment is not None:
                data.yearly_payment.to_excel(writer, sheet_name="往年回款", index=False)
            if data.monthly_income_detail is not None:
                data.monthly_income_detail.to_excel(writer, sheet_name="月收入", index=False)
            if data.monthly_payment_detail is not None:
                data.monthly_payment_detail.to_excel(writer, sheet_name="月回款", index=False)
            data.annual_income_targets.to_excel(writer, sheet_name="年度收入总指标", index=False)
            data.annual_payment_targets.to_excel(writer, sheet_name="年度回款总指标", index=False)
            data.quarterly_income_targets.to_excel(writer, sheet_name="季度收入指标", index=False)
            data.quarterly_payment_targets.to_excel(writer, sheet_name="季度回款指标", index=False)
            data.monthly_income_targets.to_excel(writer, sheet_name="月度收入指标", index=False)
            data.monthly_payment_targets.to_excel(writer, sheet_name="月度回款指标", index=False)
        _log("渲染", f"已写入 {excel_path.relative_to(BASE_DIR)}（{excel_path.stat().st_size/1024:.1f} KB）", "OK")
    except Exception as e:
        _log("渲染", f"Excel 汇总失败: {e}", "WARN")

    return out


def main():
    args = sys.argv[1:]
    output_path = None
    for arg in args:
        if arg.startswith("--output="):
            output_path = arg.split("=", 1)[1]

    print(f"\n{'#' * 60}")
    print("  Visual Dashboard System — 渲染引擎")
    print(f"  时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#' * 60}")

    out = run_render(output_path)

    print(f"\n{'#' * 60}")
    print(f"  ✅ 看板已生成: {out}")
    print(f"     大小: {out.stat().st_size / 1024:.1f} KB")
    print(f"{'#' * 60}")
    return out


if __name__ == "__main__":
    main()
