# Author: naohua168 <bai_bai168@qq.com>
"""配置编辑器 — Excel → JSON 生成器（入口脚本）

实现已拆到 scripts/editor/；本脚本负责 sys.path 引导并保持原有命令行用法：

    python scripts/config_excel_to_json.py              # 生成并写回（run_all.bat 第①步）
    python scripts/config_excel_to_json.py --dry-run    # 只读不改写
    python scripts/config_excel_to_json.py --init       # 首次创建 Excel 模板
    python scripts/config_excel_to_json.py --init-map   # 只刷新「字段映射」sheet
    python scripts/config_excel_to_json.py --init-rules # 只刷新「展示规则」sheet
    python scripts/config_excel_to_json.py --refresh-notes  # 补「说明」sheet 分节
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parents[1]      # 仓库根（scripts/ 的上一级）
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.editor import *  # noqa: F401,F403,E402 —— 兼容层：保持原有导入面
from scripts.editor import __all__ as _all  # noqa: E402
from scripts.editor.cli import main  # noqa: E402

__all__ = list(_all)


# ── 兼容层：路径等常量赋值时转发到持有它们的子模块 ──────────────────────────
# 拆包后实现读的是各自子模块里的常量（如 editor.paths.EXCEL_PATH），
# 只改本模块的副本不会生效。这里让 `cej.EXCEL_PATH = 临时路径` 这类写法（测试/外部脚本
# 常用）继续有效：对本模块赋值时，同步写入所有持有该名字的子模块。
_FORWARD_NAMES = {
    "BASE_DIR", "EXCEL_PATH", "CLEANING_CFG", "DISPLAY_RULES_CFG", "ATTRIBUTION_CFG",
    "TIME_KEYS", "DYNAMIC_STRATEGIES", "MODE_ALIASES", "STRATEGY_ALIASES", "DATE_CELL_FMT",
}
_SUBMODULES = ("paths", "constants", "parsing", "time_config", "display_rules",
               "attribution", "template", "cli")


class _CompatModule(sys.modules[__name__].__class__):
    """对入口模块赋常量时，转发到 scripts.editor 各子模块"""

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if name not in _FORWARD_NAMES:
            return
        import scripts.editor as _pkg
        for mod_name in _SUBMODULES:
            mod = getattr(_pkg, mod_name, None)
            if mod is not None and hasattr(mod, name):
                setattr(mod, name, value)


sys.modules[__name__].__class__ = _CompatModule

if __name__ == "__main__":
    sys.exit(main())
