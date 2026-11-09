# Author: naohua168 <bai_bai168@qq.com>
# -*- coding: utf-8 -*-
"""输出目录的「按年月分类」规则（2026-11-06 用户要求）

产物落盘位置统一为 `<类别根目录>/<年>/<月>/文件名`：

    output/看板/2026/11/看板_20261106.html
    output/数据/2026/11/data_20261106.xlsx
    output/数据校验/2026/11/数据质量摘要_20261106_093958.xlsx
    output/销售完成度/2026/11/销售完成度汇总_20261106.xlsx

约定：
  · 类别根目录仍由配置决定（`文件输出.目录` / `输出.数据校验` / `输出.销售完成度`），
    本模块只在后面追加 `<年>/<月>`，不写死任何绝对路径；
  · 找历史产物一律用 `latest_file()`（递归跨年月），**不要**假设只有一层目录；
  · 环境变量重定向（`VD_DIAG_DIR`，测试/临时运行用）不套年月，保持调用方给的路径。
"""
from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

JUNK_PREFIX = "~$"          # Excel 打开时的锁文件，任何查找都要跳过
_YEAR_RE = re.compile(r"^\d{4}$")
_MONTH_RE = re.compile(r"^\d{2}$")


def month_dir(path: Path | str, when: date | datetime | None = None) -> Path:
    """`<path>/<YYYY>/<MM>`；when 缺省为今天"""
    d = when or date.today()
    return Path(path) / f"{d:%Y}" / f"{d:%m}"


def category_root(path: Path | str) -> Path:
    """反向解析：`.../看板/2026/11` → `.../看板`；不是年月结构则原样返回

    用途：清理/统计要覆盖所有年月，而不是只看当前月。
    """
    p = Path(path)
    if _MONTH_RE.match(p.name) and _YEAR_RE.match(p.parent.name):
        return p.parent.parent
    return p


def iter_files(directory: Path | str, pattern: str) -> list[Path]:
    """递归列目录下匹配 pattern 的文件（跳过 `~$` 锁文件），按修改时间倒序"""
    root = Path(directory)
    if not root.exists():
        return []
    files = [f for f in root.rglob(pattern) if f.is_file() and not f.name.startswith(JUNK_PREFIX)]
    return sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)


def latest_file(directory: Path | str, pattern: str) -> Path | None:
    """递归找最新的一份（跨年月）；没有则 None"""
    files = iter_files(directory, pattern)
    return files[0] if files else None


def resolve_snapshot(path: Path | str) -> Path:
    """把「看板 HTML」或「数据总表」统一解析成数据总表路径

    · 传 data_YYYYMMDD.xlsx → 原样返回
    · 传 看板_YYYYMMDD.html → 找同期 data_YYYYMMDD.xlsx（看板数据是烘焙死的，解析不出来）

    查找顺序：同目录 → `<output>/数据/<年>/<月>/` → 整个数据类别里递归找。
    """
    p = Path(path)
    if p.suffix.lower() in (".html", ".htm"):
        import re

        m = re.search(r"(20\d{6})", p.stem)
        if not m:
            raise ValueError(f"{p.name} 文件名里没有 8 位日期，无法配对数据总表")
        day = m.group(1)
        name = f"data_{day}.xlsx"

        candidates = [p.parent / name]
        root = p.parent
        for d in [p.parent, *p.parents]:
            if d.name in ("看板", "数据"):
                root = d.parent
                break
        candidates.append(root / "数据" / day[:4] / day[4:6] / name)
        for c in candidates:
            if c.exists():
                return c
        found = latest_file(root / "数据", name)
        if found:
            return found
        raise FileNotFoundError(
            f"找不到 {name}（看板 HTML 不含原始数据，必须配同期数据总表；"
            f"已找过：{', '.join(str(c) for c in candidates)}）")
    if not p.exists():
        raise FileNotFoundError(f"文件不存在：{p}")
    return p


def snapshot_day(path: Path | str) -> str | None:
    """从 data_YYYYMMDD.xlsx / 看板_YYYYMMDD.html 提取 8 位日期；提取不到返回 None"""
    import re

    m = re.search(r"(20\d{6})", Path(path).stem)
    return m.group(1) if m else None
