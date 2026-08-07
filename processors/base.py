"""渲染器基类 — 重新导出所有 CSS/JS/组件常量（向后兼容）

各模块已拆分为:
  - static/css_vars.py — CSS_CORE, CSS_COMPONENTS, CSS_RESPONSIVE, CSS_ANIMATIONS, GLOBAL_CSS
  - static/js_vars.py — GLOBAL_JS
  - static/ov_css.py — GLOBAL_OV_CSS
  - hero.py — rate_cls, completion_html, ring_svg_html, hero_rings_html, yoy_html
"""
from __future__ import annotations

from abc import ABC, abstractmethod

# 从拆分模块重新导入（向后兼容）
from .static.css_vars import (
    CSS_CORE, CSS_COMPONENTS, CSS_RESPONSIVE, CSS_ANIMATIONS, GLOBAL_CSS,
)
from .static.js_vars import GLOBAL_JS
from .static.ov_css import GLOBAL_OV_CSS
from .hero import (
    rate_cls, completion_html, ring_svg_html, hero_rings_html, yoy_html,
)


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
