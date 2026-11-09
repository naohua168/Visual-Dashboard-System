# Author: naohua168 <bai_bai168@qq.com>
# -*- coding: utf-8 -*-
"""按「客户清单」导出月度/季度/年度矩阵（单文件多 sheet）

给一份客户名单 → 出 `月度-收入 / 月度-回款 / 季度-* / 年度-* / 说明` 一个 Excel。
口径与看板对应页面完全一致（取数走 processors.data_prep，行顺序 = 清单顺序）。

用法（项目根执行）:
    # 三个周期一起出（默认）
    python scripts/export_customer_matrix.py --customers-file "config/前端渲染/月度客户矩阵_行顺序.txt"

    # 只出月度，客户直接写在命令行
    python scripts/export_customer_matrix.py --periods monthly --customers "比亚迪电池,广汽埃安"

    # 指定某一期的数据（可用看板 HTML，自动配对同目录 data_YYYYMMDD.xlsx）
    python scripts/export_customer_matrix.py --customers-file 名单.txt \\
        --snapshot "output/看板/2026/11/看板_20261104.html"

    # 指定输出路径（默认落 output/客户矩阵/<年>/<月>/）
    python scripts/export_customer_matrix.py --customers-file 名单.txt --out D:/临时/矩阵.xlsx

⚠️ 客户清单为空时**不生成**（本功能是按需导出，不做「默认全量」）。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from processors.data_loader import load_all, load_from_workbook  # noqa: E402
from scripts.customer_matrix_core import (  # noqa: E402
    PERIODS,
    build_workbook,
    default_out_file,
    latest_data_file,
    parse_customers,
    read_order_file,
    resolve_snapshot,
)

PERIOD_HINTS = {"monthly": "月", "quarterly": "季", "annual": "年"}


def _parse_periods(text: str) -> list[str]:
    raw = str(text or "").replace("，", ",").replace(" ", ",")
    keys = [p for p in raw.split(",") if p]
    bad = [p for p in keys if p not in PERIODS]
    if bad:
        raise ValueError(f"未知周期 {bad}；可选：{', '.join(PERIODS)}")
    # 去重保序
    return list(dict.fromkeys(keys))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="按客户清单导出月度/季度/年度矩阵")
    ap.add_argument("--periods", default="monthly,quarterly,annual",
                    help="周期，逗号分隔：monthly,quarterly,annual（默认全部）")
    ap.add_argument("--customers", default=None, help="客户清单（换行/逗号分隔）")
    ap.add_argument("--customers-file", default=None, help="客户清单文件（一行一个）")
    ap.add_argument("--snapshot", default=None,
                    help="数据快照：data_YYYYMMDD.xlsx 或 看板_YYYYMMDD.html（缺省=当前清洗结果）")
    ap.add_argument("--out", default=None,
                    help="输出路径（默认 output/客户矩阵/<年>/<月>/客户矩阵_<周期>_YYYYMMDD.xlsx）")
    args = ap.parse_args(argv)

    try:
        periods = _parse_periods(args.periods)
    except ValueError as e:
        print(f"❌ {e}")
        return 2

    names: list[str] = []
    if args.customers:
        names += parse_customers(args.customers)
    if args.customers_file:
        path = Path(args.customers_file)
        if not path.is_absolute():
            path = BASE_DIR / path
        if not path.exists():
            print(f"❌ 客户清单文件不存在: {path}")
            return 2
        names += read_order_file(path)
    if not names:
        print("❌ 未提供客户清单：本功能按需生成，不做默认全量。")
        print("   用 --customers \"客户A,客户B\" 或 --customers-file 名单.txt 指定。")
        return 2

    try:
        if args.snapshot:
            snap = resolve_snapshot(Path(args.snapshot) if Path(args.snapshot).is_absolute()
                                    else BASE_DIR / args.snapshot)
            print(f"📦 数据版本: {snap.name}（指定快照）")
            data = load_from_workbook(snap)
            data_label = snap.name
        else:
            data = load_all(BASE_DIR)
            data_label = latest_data_file(BASE_DIR)
            print(f"📦 数据版本: {data_label}（当前清洗结果）")
    except (ValueError, FileNotFoundError) as e:
        print(f"❌ {e}")
        return 2

    suffix = "".join(PERIOD_HINTS[k] for k in periods)
    out = Path(args.out) if args.out else default_out_file(BASE_DIR, f"客户矩阵_{suffix}")
    out.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n▶ 客户 {len(names)} 个 ／ 周期 {', '.join(PERIODS[k].label for k in periods)}")
    wb, stats = build_workbook(
        data, periods, names, BASE_DIR,
        order_label=Path(args.customers_file).name if args.customers_file else "命令行输入",
        data_label=data_label,
        on_log=lambda m: print(f"  {m}"),
    )
    wb.save(out)

    print(f"\n✅ 已生成: {out}")
    for s in stats:
        print(f"   {s['周期']}·{s['指标']}: {s['行数']} 行 | "
              f"合计 {s['行合计']:,.2f} / {s['行指标']:,.2f} 万")
    return 0


if __name__ == "__main__":
    sys.exit(main())
