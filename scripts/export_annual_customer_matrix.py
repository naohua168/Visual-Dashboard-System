# Author: naohua168 <bai_bai168@qq.com>
# -*- coding: utf-8 -*-
"""年度客户矩阵 → Excel（兼容入口；实现已统一到 scripts/customer_matrix_core.py）

两种用法：
  1) **不指定清单** → 只出「有指标客户」，顺序 = 看板年度页矩阵展示顺序；
  2) **指定清单**（`--order-file`）→ 按清单顺序出行，并生成「说明」sheet。

要一次出月度+季度+年度，用 `scripts/export_customer_matrix.py`。

用法:
    python scripts/export_annual_customer_matrix.py
    python scripts/export_annual_customer_matrix.py --order-file "config/前端渲染/月度客户矩阵_行顺序.txt"
    python scripts/export_annual_customer_matrix.py --snapshot "output/看板/2026/11/看板_20261104.html"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import openpyxl

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from processors.data_loader import load_all, load_from_workbook  # noqa: E402
from processors.data_prep import prepare_annual_data  # noqa: E402
from scripts.customer_matrix_core import (  # noqa: E402
    build_rows_display,
    build_total_row,
    build_workbook,
    default_out_file,
    latest_data_file,
    read_order_file,
    resolve_snapshot,
    write_sheet,
)

PREFIX = "年度客户矩阵"


def _load_data(snapshot: str | None):
    if snapshot:
        path = resolve_snapshot(Path(snapshot) if Path(snapshot).is_absolute() else BASE_DIR / snapshot)
        return load_from_workbook(path), path.name
    return load_all(BASE_DIR), latest_data_file(BASE_DIR)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="年度达成页客户矩阵 → Excel")
    ap.add_argument("--out", help=f"输出路径（默认 output/数据/<年>/<月>/{PREFIX}_YYYYMMDD.xlsx）")
    ap.add_argument("--order-file", help="按指定客户顺序出行（txt，一行一个）")
    ap.add_argument("--snapshot", help="数据快照：data_YYYYMMDD.xlsx 或 看板_YYYYMMDD.html")
    args = ap.parse_args(argv)

    try:
        data, data_label = _load_data(args.snapshot)
    except (ValueError, FileNotFoundError) as e:
        print(f"❌ {e}")
        return 2

    out = Path(args.out) if args.out else default_out_file(BASE_DIR, PREFIX)
    out.parent.mkdir(parents=True, exist_ok=True)

    if args.order_file:
        order = Path(args.order_file)
        if not order.is_absolute():
            order = BASE_DIR / order
        if not order.exists():
            print(f"❌ 行顺序文件不存在: {order}")
            return 2
        names = read_order_file(order)
        wb, stats = build_workbook(data, ["annual"], names, BASE_DIR,
                                   order_label=order.name, data_label=data_label,
                                   on_log=lambda m: print(f"  {m}"))
        wb.save(out)
        print(f"\n✅ 已生成: {out}")
        for s in stats:
            print(f"   {s['指标']}: {s['行数']} 行 | 合计 {s['行合计']:,.2f} / {s['行指标']:,.2f} 万")
        return 0

    d = prepare_annual_data(data, BASE_DIR)
    inc_rows = build_rows_display(d.inc_piv, d.inc_tgt_grouped, d.inc_customers, d.inc_rest,
                                  d.subs_with_data, d.subs_all)
    pay_rows = build_rows_display(d.pay_piv, d.pay_tgt_grouped, d.pay_customers, d.pay_rest,
                                  d.subs_with_data, d.subs_all)
    inc_total = build_total_row(d.inc_piv, d.inc_tgt_grouped)
    pay_total = build_total_row(d.pay_piv, d.pay_tgt_grouped)

    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "收入"
    write_sheet(ws1, inc_total, inc_rows)
    write_sheet(wb.create_sheet("回款"), pay_total, pay_rows)
    wb.save(out)

    print(f"✅ 已生成: {out}")
    print(f"   收入: {len(inc_rows)} 家 | 合计 {inc_total['合计_实际']:,.2f} / {inc_total['合计_指标']:,.2f} 万")
    print(f"   回款: {len(pay_rows)} 家 | 合计 {pay_total['合计_实际']:,.2f} / {pay_total['合计_指标']:,.2f} 万")
    return 0


if __name__ == "__main__":
    sys.exit(main())
