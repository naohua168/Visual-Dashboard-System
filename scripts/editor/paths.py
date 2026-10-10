# Author: naohua168 <bai_bai168@qq.com>
"""项目路径常量（配置文件与工作簿位置）

由 scripts/config_excel_to_json.py 拆分而来（行为不变，见 logs/_dryrun_before.txt 比对）。
"""
from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).parents[2]   # scripts/editor/ 比原脚本多一层


EXCEL_PATH = BASE_DIR / "config" / "配置编辑器.xlsx"


CLEANING_CFG = BASE_DIR / "config" / "清洗配置" / "cleaning_config.json"


DISPLAY_RULES_CFG = BASE_DIR / "config" / "前端渲染" / "展示规则.json"


ATTRIBUTION_CFG = BASE_DIR / "config" / "清洗配置" / "客户销售归属.json"
