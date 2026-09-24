# Author: naohua168 <bai_bai168@qq.com>
"""清洗列名命中日志 — 追加写入 logs/column_hits_YYYYMMDD.txt

作用：把「哪个标准字段实际命中了源文件的哪一列」落盘，供事后追溯。

背景（2026-09-17 命中分析）：`print_hit_columns()` 原先只打印到控制台，
而 `logs/run_*.log` 只记录步骤级信息（启动/命令/结果），导致源文件列名
漂移后无法复查"当时到底命中了哪一列"；且广东/湖南两个来源当时根本没
打印命中信息。本模块提供统一落盘出口。
"""
from __future__ import annotations

import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
DEFAULT_LOG_DIR = BASE_DIR / "logs"

_SEP = "─" * 64


def hit_log_path(when: datetime.datetime | None = None,
                 log_dir: Path | None = None) -> Path:
    """命中日志路径：`logs/column_hits_YYYYMMDD.txt`（按天一个文件，多次运行追加）"""
    when = when or datetime.datetime.now()
    return (log_dir or DEFAULT_LOG_DIR) / f"column_hits_{when:%Y%m%d}.txt"


def format_hit_block(source_name: str, hits: dict, candidates: dict | None = None,
                     when: datetime.datetime | None = None) -> str:
    """把命中表渲染成文本块

    Args:
        source_name: 来源名（如 "财务端收入" / "广东回款"）
        hits: {标准字段: 实际命中的列名}
        candidates: {标准字段: [候选列名...]}（可选；用于标注命中次序与降级）
        when: 时间戳

    Returns:
        文本块（以换行结尾）
    """
    when = when or datetime.datetime.now()
    candidates = candidates or {}
    lines = [_SEP, f"{when:%Y-%m-%d %H:%M:%S}  [{source_name}] 列名命中", _SEP]

    width = max((len(str(s)) for s in hits), default=4)
    degraded: list[str] = []

    for std, actual in hits.items():
        cands = [str(c).strip() for c in (candidates.get(std) or [])]
        mark = ""
        if cands:
            try:
                idx = cands.index(str(actual).strip()) + 1
            except ValueError:
                idx = 0
            if idx == 0:
                mark = "  ⚠️ 不在候选列表内"
            elif idx > 1:
                mark = f"  ⚠️ 降级命中（第 {idx}/{len(cands)} 候选）"
                degraded.append(f"{std}←{actual}")
            else:
                mark = f"  （第 1/{len(cands)} 候选）"
        lines.append(f"  {str(std):<{width}} <- {actual}{mark}")

    if degraded:
        lines.append(f"  ⚠️ 降级命中 {len(degraded)} 处: " + ", ".join(degraded))
    lines.append("")
    return "\n".join(lines) + "\n"


def append_hit_block(source_name: str, hits: dict, candidates: dict | None = None,
                     log_dir: Path | None = None,
                     when: datetime.datetime | None = None) -> Path:
    """追加一个命中块到命中日志，返回日志路径（hits 为空时不写文件）"""
    if not hits:
        return hit_log_path(when, log_dir)
    when = when or datetime.datetime.now()
    path = hit_log_path(when, log_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(format_hit_block(source_name, hits, candidates, when))
    return path
