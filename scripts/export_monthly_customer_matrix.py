# Author: naohua168 <bai_bai168@qq.com>
"""月度达成页 · 有指标客户的矩阵数据 → Excel（收入 / 回款 两个 sheet，指标与实际分列）

口径与看板「月度达成」页的客户矩阵完全一致：
  - 取数：processors.data_prep.prepare_monthly_data（当月窗口 + 母公司归拢 + 展示顺序）
  - 行：仅「有指标客户」（指标合计 > 0），顺序 = 矩阵展示顺序（主表 → 折叠区）
  - 列：每个事业部拆成「实际 / 指标」两列（万元），另有合计实际 / 合计指标 / 达成率
  - 首行：「合计（全量）」= 矩阵合计行（含未展示客户），与看板合计行一致
  - 「子公司」列：有数据子公司数 / 配置子公司总数（同看板行尾的 “5/16家”）

用法（项目根执行）:
    python scripts/export_monthly_customer_matrix.py
    python scripts/export_monthly_customer_matrix.py --out "output/数据/月度客户矩阵.xlsx"
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from processors.data_loader import load_all  # noqa: E402
from processors.data_prep import prepare_monthly_data  # noqa: E402
from processors.data_utils import DEPARTMENTS  # noqa: E402

DEFAULT_OUT_DIR = BASE_DIR / "output" / "数据"

HEAD_FILL = PatternFill("solid", fgColor="1E293B")
HEAD_FONT = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
TOTAL_FILL = PatternFill("solid", fgColor="EEF2FF")
TOTAL_FONT = Font(name="微软雅黑", size=10, bold=True)
BODY_FONT = Font(name="微软雅黑", size=10)
THIN = Side(style="thin", color="D8DEE9")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
NUM_FMT = "#,##0.00"
PCT_FMT = "0.0%"


def _num(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def _rate(act: float, tgt: float) -> float | None:
    if tgt > 0:
        return act / tgt
    return 1.0 if act > 0 else None


def _cell(piv, name: str, dept: str) -> float:
    """透视表取数（缺列/缺行按 0 处理）"""
    if piv is None or len(piv) == 0 or dept not in piv.columns or name not in piv.index:
        return 0.0
    return _num(piv.loc[name, dept])


def build_rows(piv, tgt, customers: list[str], rest: list[str],
               subs_with_data: dict, subs_all: dict) -> list[dict]:
    """有指标客户（指标合计>0）的矩阵行，按展示顺序"""
    order = list(dict.fromkeys(list(customers) + list(rest)))
    picked = [c for c in order if c in tgt.index and _num(tgt.loc[c, "合计"]) > 0]
    # 指标表里有、但不在展示列表里的（理论上不会发生）兜底追加
    for c in tgt.index:
        if _num(tgt.loc[c, "合计"]) > 0 and c not in picked:
            picked.append(c)

    rows: list[dict] = []
    for c in picked:
        row: dict = {"客户": c}
        for d in DEPARTMENTS:
            row[f"{d}_实际"] = _cell(piv, c, d)
            row[f"{d}_指标"] = _cell(tgt, c, d)
        act = _num(piv.loc[c, "合计"]) if piv is not None and c in piv.index else sum(
            row[f"{d}_实际"] for d in DEPARTMENTS
        )
        tg = _num(tgt.loc[c, "合计"]) if c in tgt.index else 0.0
        row["合计_实际"] = act
        row["合计_指标"] = tg
        row["合计达成率"] = _rate(act, tg)
        n_have = len(subs_with_data.get(c, []) or [])
        n_all = len(subs_all.get(c, []) or [])
        row["子公司(有数据/配置)"] = f"{n_have}/{n_all}" if n_all else ""
        rows.append(row)
    return rows


def build_total_row(piv, tgt) -> dict:
    """合计（全量）= 矩阵合计行：按全量透视表求和"""
    row: dict = {"客户": "合计（全量）"}
    for d in DEPARTMENTS:
        act = _num(piv[d].sum()) if piv is not None and d in piv.columns else 0.0
        tg = _num(tgt[d].sum()) if tgt is not None and d in tgt.columns else 0.0
        row[f"{d}_实际"] = act
        row[f"{d}_指标"] = tg
    act = _num(piv["合计"].sum()) if piv is not None and "合计" in piv.columns else 0.0
    tg = _num(tgt["合计"].sum()) if tgt is not None and "合计" in tgt.columns else 0.0
    row["合计_实际"] = act
    row["合计_指标"] = tg
    row["合计达成率"] = _rate(act, tg)
    row["子公司(有数据/配置)"] = ""
    return row


def write_sheet(ws, total: dict, rows: list[dict]) -> None:
    headers = list(total.keys())
    ws.append(headers)
    for col, _ in enumerate(headers, 1):
        c = ws.cell(row=1, column=col)
        c.fill, c.font, c.border = HEAD_FILL, HEAD_FONT, BORDER
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 30

    for r_idx, data in enumerate([total] + rows, start=2):
        ws.append([data[h] for h in headers])
        is_total = r_idx == 2
        for col, h in enumerate(headers, 1):
            c = ws.cell(row=r_idx, column=col)
            c.border = BORDER
            c.font = TOTAL_FONT if is_total else BODY_FONT
            if is_total:
                c.fill = TOTAL_FILL
            c.alignment = Alignment(
                horizontal="left" if col == 1 else ("center" if h.endswith("率") or "子公司" in h else "right"),
                vertical="center",
            )
            if h.endswith("率"):
                c.number_format = PCT_FMT
                if c.value is None:
                    c.value = "—"
            elif h != "客户" and "子公司" not in h:
                c.number_format = NUM_FMT

    ws.freeze_panes = "B2"
    ws.column_dimensions["A"].width = 42
    last = get_column_letter(len(headers))
    for col in range(2, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 14
    ws.column_dimensions[last].width = 18
    ws.auto_filter.ref = f"A1:{last}{len(rows) + 2}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="月度达成页有指标客户矩阵 → Excel")
    ap.add_argument("--out", help="输出路径（默认 output/数据/月度客户矩阵_YYYYMMDD.xlsx）")
    args = ap.parse_args(argv)

    data = load_all(BASE_DIR)
    d = prepare_monthly_data(data, BASE_DIR)

    inc_rows = build_rows(d.inc_piv, d.inc_tgt_grouped, d.inc_customers, d.inc_rest,
                          d.subs_with_data, d.subs_all)
    pay_rows = build_rows(d.pay_piv, d.pay_tgt_grouped, d.pay_customers, d.pay_rest,
                          d.subs_with_data, d.subs_all)
    inc_total = build_total_row(d.inc_piv, d.inc_tgt_grouped)
    pay_total = build_total_row(d.pay_piv, d.pay_tgt_grouped)

    out = Path(args.out) if args.out else DEFAULT_OUT_DIR / f"月度客户矩阵_{date.today():%Y%m%d}.xlsx"
    out.parent.mkdir(parents=True, exist_ok=True)

    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "收入"
    write_sheet(ws1, inc_total, inc_rows)
    ws2 = wb.create_sheet("回款")
    write_sheet(ws2, pay_total, pay_rows)
    wb.save(out)

    print(f"✅ 已生成: {out}")
    print(f"   收入: {len(inc_rows)} 家有指标客户 | 合计 {inc_total['合计_实际']:,.2f} / {inc_total['合计_指标']:,.2f} 万")
    print(f"   回款: {len(pay_rows)} 家有指标客户 | 合计 {pay_total['合计_实际']:,.2f} / {pay_total['合计_指标']:,.2f} 万")
    return 0


if __name__ == "__main__":
    sys.exit(main())
