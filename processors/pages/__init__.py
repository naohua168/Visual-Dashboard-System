# Author: naohua168 <bai_bai168@qq.com>
"""看板页面包 —— 每个页面一个模块，只负责"取数 → 拼 HTML"，样式/组件在别处。

    overview   数据总览（Hero + 部门矩阵 + 销售榜单）
    annual     年度达成（Hero + 部门卡 + 客户矩阵）
    monthly    月度达成（同构，窗口为当前月）
    quarterly  季度达成（同构，窗口为当前季度）
    sales      销售达成（3 卡片 + 销售客户详情抽屉 + 待确认面板）
    yoy        年度同比（事业部同比 + 客户同比矩阵）

约定：
  · 页面模块继承 processors/base.BaseRenderer 并实现 render(data)；
  · HTML 里的交互全部走 processors/static/js 里的全局函数（onclick="showPage('xx')"）；
  · 页面专属样式写在 processors/static/css/ 对应模块里，不要内联大段 <style>；
  · 旧导入路径（processors.page_annual 等）保留了兼容层，新增代码请从本包导入。
"""
from .annual import AnnualPage
from .monthly import MonthlyPage
from .overview import OverviewPage
from .quarterly import QuarterlyPage
from .sales import SalesPage
from .yoy import YoyPage

__all__ = [
    "OverviewPage",
    "AnnualPage",
    "MonthlyPage",
    "QuarterlyPage",
    "SalesPage",
    "YoyPage",
]
