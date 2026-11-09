# Author: naohua168 <bai_bai168@qq.com>
"""看板交互脚本包 —— 按「导航 / 换页 / 计数 / 文本 / 表格 / Tab / 搜索」分模块维护。

本文件是脚本包唯一对外出口，按固定顺序把各模块的 `JS` 片段拼成 GLOBAL_JS。

2026-11-04：图表模块（charts.py）已下线 —— 全仓库从未调用 `new Chart(` / `__regChart(`，
6 个页面全部是表格，页面里也不存在 `<canvas>`。将来若要画图，新建模块并在此追加即可
（记得同时恢复 run.py 的 Chart.js **本地内联**，不要用 CDN）。

顺序不可调整：片段里存在相互依赖（如 tables 模块给 showPage 做了"换页后兜底折叠"
的包装，必须排在 page_switch 之后），调整顺序会改变脚本行为。

维护约定：
  · 交互逻辑只改对应模块，不要在别处拼字符串；
  · 全局函数命名保持 `window.xxx`（页面模板里的 onclick 直接引用）；
  · 新增页面级交互时，优先在这里加独立模块并在 __init__ 里追加拼接。
"""
from __future__ import annotations

from . import counters, cust_search, nav, page_switch, tables, tabs, text

GLOBAL_JS = (
    nav.JS
    + page_switch.JS
    + counters.JS
    + text.JS
    + tables.JS
    + tabs.JS
    + cust_search.JS
)

__all__ = ["GLOBAL_JS"]

if not GLOBAL_JS:
    raise RuntimeError("脚本片段为空 —— 检查 processors/static/js/ 各模块的 JS 常量")
