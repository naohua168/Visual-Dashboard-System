# Author: naohua168 <bai_bai168@qq.com>
"""单元格解析小工具（时间配置与展示规则共用）

由 scripts/config_excel_to_json.py 拆分而来（行为不变，见 logs/_dryrun_before.txt 比对）。
"""
from __future__ import annotations

import re
from datetime import datetime


def split_metric_value(value: str) -> list[str]:
    """拆分「指标」列取值 → 指标名列表

    现行写法用斜杠：`收入/回款`；历史文件的逗号写法（`收入,回款`）继续兼容。
    斜杠不会和 Excel 下拉的内联列表分隔符（逗号）冲突，否则下拉里选不到合并项。
    """
    return [p.strip() for p in re.split(r"[/,，、]+", value or "") if p.strip()]


def _parse_cell(value) -> str:
    """单元格值 → 干净字符串（Excel 日期/数字转文本）

    2026-09-30 修复：日期时间单元格原本只取「日期」部分，把 `2026-09-30 23:59:59`
    截成 `2026-09-30` → 结束时间退化成当天 00:00:00，导致**当天数据被整段排除**。
    现在：时分秒全为 0 → 仍输出 `YYYY-MM-DD`（保持简洁）；否则保留 `YYYY-MM-DD HH:MM:SS`。
    """
    if value is None:
        return ""
    if isinstance(value, datetime):
        if (value.hour, value.minute, value.second) == (0, 0, 0):
            return value.strftime("%Y-%m-%d")
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value).strip()
