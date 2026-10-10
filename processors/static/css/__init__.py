# Author: naohua168 <bai_bai168@qq.com>
"""看板样式包 —— 按「变量 / 布局 / 组件 / 页面 / 响应式 / 动画」分模块维护。

本文件是样式包唯一对外出口，按固定顺序把各模块的 `CSS` 片段拼成 5 个常量
（与拆分前 processors/static/css_vars.py 的内容逐字节一致）：

    CSS_CORE        变量 + 骨架 + 布局        ← variables + layout
    CSS_COMPONENTS  组件与页面样式            ← kpi / tables / cards / yoy / widgets /
                                                hero / annual / matrix / yoy_tables
    CSS_RESPONSIVE  响应式断点                ← responsive
    CSS_ANIMATIONS  动画系统                  ← animations
    GLOBAL_CSS      以上四段拼接（注入 <style> 的完整样式）
    GLOBAL_OV_CSS   数据总览页专属样式（单独追加在 GLOBAL_CSS 之后，可覆盖前者）

维护约定：
  · 改样式只改对应模块文件，不要在别处拼字符串；
  · 新增界面样式请放进语义最贴近的模块，模块内部按「一行一条规则」书写；
  · 新增"页面级"样式时，考虑是否应该放进该页自己的模块（如 overview.py）。
"""
from __future__ import annotations

from . import (
    annual,
    animations,
    cards,
    hero,
    kpi,
    layout,
    matrix,
    overview,
    responsive,
    tables,
    variables,
    widgets,
    yoy,
    yoy_tables,
)

CSS_CORE = variables.CSS + layout.CSS
CSS_COMPONENTS = (
    kpi.CSS + tables.CSS + cards.CSS + yoy.CSS + widgets.CSS
    + hero.CSS + annual.CSS + matrix.CSS + yoy_tables.CSS
)
CSS_RESPONSIVE = responsive.CSS
CSS_ANIMATIONS = animations.CSS
GLOBAL_CSS = CSS_CORE + CSS_COMPONENTS + CSS_RESPONSIVE + CSS_ANIMATIONS
GLOBAL_OV_CSS = overview.CSS

__all__ = [
    "CSS_CORE",
    "CSS_COMPONENTS",
    "CSS_RESPONSIVE",
    "CSS_ANIMATIONS",
    "GLOBAL_CSS",
    "GLOBAL_OV_CSS",
]

if not all((CSS_CORE, CSS_COMPONENTS, CSS_RESPONSIVE, CSS_ANIMATIONS, GLOBAL_OV_CSS)):
    raise RuntimeError("样式片段为空 —— 检查 processors/static/css/ 各模块的 CSS 常量")
