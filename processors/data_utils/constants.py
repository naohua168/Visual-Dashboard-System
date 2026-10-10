# Author: naohua168 <bai_bai168@qq.com>
"""部门与各类名单常量 —— 母公司/法人主体口径、部门列表、内部交易名单（供其它模块 import）

由 processors/page_data_utils.py 拆分而来；常量按原文件原样保留，行为不变。
"""
from __future__ import annotations

from pathlib import Path

# 仓库根目录：包内模块（processors/data_utils/x.py）比原先的 processors/x.py 多一层
PROJECT_ROOT = Path(__file__).parents[2]

from engine.core import business_rules as br


SG_PARENT = br.parent_sg()

_SG_CHILDREN_SEEN: list[str] = []

GD_PARENT_FILTER = br.parent_gd_self()

OTHER_PARENT_FILTER = br.parent_other()

BYD_PARENT_INDUSTRY = br.parent_byd_industry()

BYD_PARENT_BATTERY = br.parent_byd_battery()

DEPARTMENTS = br.departments()

# 法人主体过滤常量（值来自 config/清洗配置/业务规则.json，2026-09-29 外置）
SG_LEGAL_ENTITY = br.legal_sg()
GD_LEGAL_FILTER = br.legal_gd()
