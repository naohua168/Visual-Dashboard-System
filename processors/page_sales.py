# Author: naohua168 <bai_bai168@qq.com>
"""兼容层 —— 实现已迁到 processors/pages/sales.py

保留这个模块只是为了让既有导入（测试、外部脚本）继续可用；
新代码请 `from processors.pages import SalesPage`。
"""
from .pages.sales import SalesPage

__all__ = ["SalesPage"]
