# Author: naohua168 <bai_bai168@qq.com>
# -*- coding: utf-8 -*-
"""「数据版本」下拉的公共实现（客户矩阵对话框 / 销售完成度对话框共用）

数据版本 = 某一期的 `output/数据/<年>/<月>/data_YYYYMMDD.xlsx`（数据总表快照）。
选「最新」表示用当前清洗结果（data/sheets/…）。
"""
from __future__ import annotations

from pathlib import Path

from engine.core.output_paths import iter_files

SNAP_LATEST = "最新（当前清洗结果）"
DATA_CATEGORY = "数据"


def data_root(base_dir: Path | str) -> Path:
    """数据总表根目录：<项目>/output/数据（按年月分层）"""
    return Path(base_dir) / "output" / DATA_CATEGORY


def load_snapshot_choices(base_dir: Path | str) -> dict[str, Path | None]:
    """返回 {显示名: 路径}，第一项固定是「最新」（值为 None），其余按修改时间倒序"""
    choices: dict[str, Path | None] = {SNAP_LATEST: None}
    for f in iter_files(data_root(base_dir), "data_*.xlsx"):
        day = f.stem.split("_")[-1]
        label = f"{day[:4]}-{day[4:6]}-{day[6:]} · {f.name}" if len(day) == 8 else f.name
        choices.setdefault(label, f)
    return choices


def add_custom_choice(choices: dict[str, Path | None], path: Path) -> str:
    """把「手工选的文件」加进选项，返回它的显示名"""
    label = f"自定义 · {path.name}"
    choices[label] = path
    return label
