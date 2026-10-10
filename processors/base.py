# Author: naohua168 <bai_bai168@qq.com>
"""渲染器基类 — 汇总导出样式/脚本/组件，供各页面模块统一引用。

各模块位置:
  - static/css/   样式包（variables/layout/kpi/tables/... 按模块维护，见包内 __init__）
  - static/js/    交互脚本包（nav/page_switch/counters/... 见包内 __init__）
  - static/icons.py  Lucide 内联图标
  - hero.py       rate_cls, completion_html, ring_svg_html, hero_rings_html, yoy_html
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from .hero import (
    completion_html,
    hero_rings_html,
    rate_cls,
    ring_svg_html,
    yoy_html,
)
from .static.css import (
    CSS_ANIMATIONS,
    CSS_COMPONENTS,
    CSS_CORE,
    CSS_RESPONSIVE,
    GLOBAL_CSS,
    GLOBAL_OV_CSS,
)
from .static.js import GLOBAL_JS

__all__ = [
    "BaseRenderer",
    "CSS_CORE",
    "CSS_COMPONENTS",
    "CSS_RESPONSIVE",
    "CSS_ANIMATIONS",
    "GLOBAL_CSS",
    "GLOBAL_JS",
    "GLOBAL_OV_CSS",
    "rate_cls",
    "completion_html",
    "ring_svg_html",
    "hero_rings_html",
    "yoy_html",
]


class BaseRenderer(ABC):
    page_id: str = ""
    nav_name: str = ""

    @abstractmethod
    def render(self, data) -> str:
        ...

    def wrap_page(self, content: str, date_range: str = "") -> str:
        attr = f' data-range="{date_range}"' if date_range else ""
        return f'<div id="{self.page_id}" class="page"{attr}>\n{content}\n</div>'

    def section(self, title: str, color: str = "sec-blue") -> str:
        return f'<div class="section-title {color}">{title}</div>'
