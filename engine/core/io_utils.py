# Author: naohua168 <bai_bai168@qq.com>
"""Excel 落盘防护 —— 统一处理"文件正被 Excel/WPS 打开"（2026-09-29 新增）

Windows 下文件被 Excel 打开时写入会抛 `PermissionError`（WinError 13），
以前只有收入/回款清洗层做了友好提示，其它落盘点（销售拆分、年基线、汇总表、渲染 Excel）
会抛裸异常。现在统一走这里：

    from ..core.io_utils import save_excel, ExcelBusyError
    try:
        save_excel(df, path)                 # 或 save_excel({"sheet": df}, path)
    except ExcelBusyError as e:
        log_step(label, f"❌ {e}", "ERROR")
        raise SystemExit(3)

`ExcelBusyError` 的文案带文件名与"关闭后重跑"提示，便于直接展示给使用者。
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pandas as pd

from .utils import rel_path


class ExcelBusyError(RuntimeError):
    """目标 Excel 被其它程序（Excel/WPS）占用，无法写入"""

    def __init__(self, path) -> None:
        self.path = Path(path)
        super().__init__(f"{rel_path(self.path)} 正被 Excel/WPS 等程序占用 → 请关闭该文件后重跑")


def save_excel(data, path, **to_excel_kwargs) -> Path:
    """写 Excel（df 或 {sheet_name: df}），被占用时抛 ExcelBusyError

    Args:
        data: DataFrame → 单 sheet；Mapping[str, DataFrame] → 多 sheet
        path: 目标文件
        to_excel_kwargs: 透传给 `DataFrame.to_excel`（多 sheet 时忽略）
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if isinstance(data, Mapping):
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                for sheet, df in data.items():
                    df.to_excel(writer, sheet_name=str(sheet), index=False)
        else:
            df = data.fillna("") if hasattr(data, "fillna") else data
            df.to_excel(path, index=False, **to_excel_kwargs)
    except PermissionError as e:  # WinError 13: 被 Excel 打开
        raise ExcelBusyError(path) from e
    return path
