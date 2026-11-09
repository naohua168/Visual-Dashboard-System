# Author: naohua168 <bai_bai168@qq.com>
# -*- coding: utf-8 -*-
"""把 output/ 下的历史产物迁移成「类别/年/月」结构（2026-11-06）

    output/看板/看板_20261030.html        → output/看板/2026/10/看板_20261030.html
    output/数据/data_20261104.xlsx        → output/数据/2026/11/data_20261104.xlsx
    output/数据校验/数据质量摘要_*.xlsx    → output/数据校验/2026/11/...
    output/销售完成度/销售完成度汇总_*.xlsx → output/销售完成度/2026/11/...

规则：
  · 日期优先取文件名里的 8 位日期（YYYYMMDD），取不到则用文件修改时间；
  · 只处理类别根目录**直接**放着的文件；已经在 <年>/<月>/ 里的跳过（幂等，可重复运行）；
  · 目标位置已有同名文件时不覆盖，输出「冲突」并保留原文件；
  · `_shots`、`_rem_backup` 等下划线开头的目录不动。

用法：
    python scripts/migrate_output_by_month.py --dry-run   # 只看计划
    python scripts/migrate_output_by_month.py             # 真正移动
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from engine.core.output_paths import JUNK_PREFIX  # noqa: E402

CATEGORIES = ("看板", "数据", "数据校验", "销售完成度", "客户矩阵")
_DATE_RE = re.compile(r"(20\d{6})")


def _date_of(path: Path) -> datetime:
    """文件名里的 8 位日期优先，其次文件修改时间"""
    m = _DATE_RE.search(path.stem)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y%m%d")
        except ValueError:
            pass
    return datetime.fromtimestamp(path.stat().st_mtime)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="output/ 历史产物 → 类别/年/月/ 结构")
    ap.add_argument("--dry-run", action="store_true", help="只列出计划，不移动文件")
    ap.add_argument("--root", default=None, help="输出根目录（默认 <项目>/output）")
    args = ap.parse_args(argv)

    root = Path(args.root) if args.root else BASE_DIR / "output"
    if not root.exists():
        print(f"❌ 输出目录不存在: {root}")
        return 2

    moved = skipped = conflicts = 0
    for cat in CATEGORIES:
        cat_dir = root / cat
        if not cat_dir.exists():
            continue
        for f in sorted(cat_dir.iterdir()):
            if not f.is_file() or f.name.startswith(JUNK_PREFIX):
                continue
            d = _date_of(f)
            target = cat_dir / f"{d:%Y}" / f"{d:%m}" / f.name
            if target.exists():
                conflicts += 1
                print(f"⚠️  冲突（目标已存在，保留原文件）: {f.relative_to(root)}")
                continue
            if args.dry_run:
                print(f"   {f.relative_to(root)}  →  {cat}/{d:%Y}/{d:%m}/")
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(f), str(target))
                print(f"   {f.relative_to(root)}  →  {cat}/{d:%Y}/{d:%m}/")
            moved += 1

    verb = "将迁移" if args.dry_run else "已迁移"
    print(f"\n{'=' * 56}")
    print(f"{verb} {moved} 个文件；跳过（已在年月目录）{skipped}；冲突 {conflicts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
