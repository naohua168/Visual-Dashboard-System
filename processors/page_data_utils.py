# Author: naohua168 <bai_bai168@qq.com>
"""兼容层 —— 实现已拆到 processors/data_utils/（keys / loading / consolidate / metrics / constants）。

保留本模块只为让既有导入继续可用：

    from processors.page_data_utils import _sorted_customers, DEPARTMENTS, ...
    import processors.page_data_utils as pdu; pdu._load_sales_split() ...

⚠ 关于模块级状态（缓存/常量）：
    拆包后，`_SUB_TO_PARENT`、`_SALES_SPLIT`、`_ATTRIBUTION_FLAT`、`_DOTTED_NAMES` 这类
    可变状态与"读写它的函数"被刻意放在同一个子模块（跨模块重绑定模块级变量不会互相可见）。
    为了让既有代码/测试里 `pdu.某状态 = 新值` 的写法继续生效，本模块用一个转发型的
    模块类：对本模块赋值这些名字时，同步写入所有持有该名字的子模块。

新代码请直接 `from processors.data_utils import ...`，需要替换状态时也请直接改对应子模块。
"""
from __future__ import annotations

import sys
import types

from .data_utils import *  # noqa: F401,F403  —— 兼容层：保持原导入面
from .data_utils import __all__ as _all

__all__ = list(_all)

# 需要"赋值即转发"的状态名（缓存 + 配置加载器，见各子模块）
_FORWARD_NAMES = {
    "_SUB_TO_PARENT",
    "_SG_CHILDREN_SEEN",
    "_SALES_SPLIT",
    "_ATTRIBUTION_FLAT",
    "_DOTTED_NAMES",
    "_SPLIT_KEY_RE_CACHE",
    "_load_sales_split",
    "_load_sub_sales_to_parent",
    "_load_attribution_flat",
    "_load_sub_to_parent",
    "_load_children_map",
    "_byd_multi_subs",
    "_gd_multi_sub_to_keep",
    "_build_cust_parent_map",
}
_SUBMODULES = ("constants", "keys", "loading", "consolidate", "metrics")


class _CompatModule(types.ModuleType):
    """对兼容层赋状态名时，转发到所有持有该名字的子模块"""

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if name not in _FORWARD_NAMES:
            return
        package = sys.modules.get(__name__.rsplit(".", 1)[0] + ".data_utils")
        if package is None:
            return
        for mod_name in _SUBMODULES:
            mod = getattr(package, mod_name, None)
            if mod is not None and hasattr(mod, name):
                setattr(mod, name, value)


sys.modules[__name__].__class__ = _CompatModule
