# Author: naohua168 <bai_bai168@qq.com>
# -*- coding: utf-8 -*-
"""客户矩阵导出的公共核心（月度 / 季度 / 年度共用）

一个函数搞定「指定客户清单 → 多周期矩阵 Excel」：

    wb, stats = build_workbook(data, ["monthly", "quarterly", "annual"], names, BASE_DIR)
    wb.save("客户矩阵.xlsx")

口径（与看板对应页面完全一致）：
  · 取数走 `processors.data_prep.prepare_{monthly,quarterly,annual}_data`；
  · 行顺序 = 客户清单顺序；清单里的「母公司」归拢其全部子公司，「子公司」只取该户自身；
  · 列 = 4 个事业部 ×（实际 / 指标，万元）+ 合计实际 / 合计指标 / 达成率；
  · 首行「合计（全量）」= 看板矩阵合计行（含未在清单里的客户）。

客户名容错：
  · `REPEAT_GROUPS`：`科技公司` / `专项组` 这类简写按出现顺序依次展开成各销售拆分父组；
  · `ALIASES`：历史/口语叫法（全角括号、公司名写法差异）映射到系统实体名；
  · 都匹配不到 → 保留空行占位，并在「说明」sheet 里标注原因（不静默丢弃）。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Iterable

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from engine.core.output_paths import (
    latest_file,
    month_dir,
    resolve_snapshot as _resolve_snapshot,
)
from processors.data_prep import (
    prepare_annual_data,
    prepare_monthly_data,
    prepare_quarterly_data,
)
from processors.data_utils import DEPARTMENTS

# ── 样式（与看板蓝白主题一致）────────────────────────────────
HEAD_FILL = PatternFill("solid", fgColor="1E293B")
HEAD_FONT = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
TOTAL_FILL = PatternFill("solid", fgColor="EEF2FF")
TOTAL_FONT = Font(name="微软雅黑", size=10, bold=True)
BODY_FONT = Font(name="微软雅黑", size=10)
THIN = Side(style="thin", color="D8DEE9")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
NUM_FMT = "#,##0.00"
PCT_FMT = "0.0%"

# ── 客户名容错 ───────────────────────────────────────────────
# 简写按出现顺序依次展开（同一简写在清单里出现多次才生效）
REPEAT_GROUPS: dict[str, list[str]] = {
    "科技公司": ["科技公司·王海龙", "科技公司·李巍"],
    "专项组": ["专项组-冉培银", "专项组-尤国建", "专项组-金奕霖"],
}
# 历史/口语叫法 → 系统实体名
ALIASES: dict[str, str] = {
    "广东公司自有客户": "广东自有客户",
    "广汽本田汽车研究院开发有限公司": "广汽本田汽车研究开发有限公司",
    "湖南中联重科股份有限公司": "中联重科股份有限公司",
    "法雷奥汽车内部控制（深圳）有限公司": "法雷奥汽车内部控制(深圳)有限公司",
}


@dataclass(frozen=True)
class PeriodSpec:
    key: str
    label: str
    prepare: Callable
    target_desc: str


PERIODS: dict[str, PeriodSpec] = {
    "monthly": PeriodSpec("monthly", "月度", prepare_monthly_data, "手动维护的月度指标表"),
    "quarterly": PeriodSpec("quarterly", "季度", prepare_quarterly_data, "手动维护的季度指标表"),
    "annual": PeriodSpec("annual", "年度", prepare_annual_data, "手动维护的年度总指标表"),
}
PERIOD_ORDER = ("monthly", "quarterly", "annual")


DATA_CATEGORY = "数据"          # 数据总表所在类别（只用于找快照，不写这里）
MATRIX_CATEGORY = "客户矩阵"    # 矩阵导出独立成类（2026-11-06 用户要求）


def data_root(base_dir: Path) -> Path:
    """数据总表根目录：<项目>/output/数据（按年月分层）"""
    return Path(base_dir) / "output" / DATA_CATEGORY


def matrix_root(base_dir: Path) -> Path:
    """矩阵导出根目录：<项目>/output/客户矩阵（按年月分层，与数据总表分开）"""
    return Path(base_dir) / "output" / MATRIX_CATEGORY


def default_out_file(base_dir: Path, prefix: str) -> Path:
    return month_dir(matrix_root(base_dir)) / f"{prefix}_{date.today():%Y%m%d}.xlsx"


def latest_data_file(base_dir: Path) -> str:
    """最近一次数据总表文件名（跨年月递归；仅用于「说明」sheet 标注数据版本）"""
    f = latest_file(data_root(base_dir), "data_*.xlsx")
    return f.name if f else "（未生成数据总表）"


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
    if piv is None or len(piv) == 0 or dept not in piv.columns or name not in piv.index:
        return 0.0
    return _num(piv.loc[name, dept])


def read_order_file(path: Path) -> list[str]:
    """读取客户清单文件（一行一个；# 注释、空行忽略）"""
    names: list[str] = []
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            names.append(s)
    return names


def parse_customers(text: str) -> list[str]:
    """把用户粘贴的文本拆成客户清单（换行 / 英文逗号 / 中文逗号 / 分号 都当分隔符）

    去空行、去首尾空格、保持输入顺序；**不去重**（同名多次出现是「科技公司」这种
    简写按顺序展开的用法，去重会破坏它）。
    """
    raw = str(text or "").replace("，", "\n").replace(",", "\n")
    raw = raw.replace("；", "\n").replace(";", "\n")
    return [s.strip() for s in raw.splitlines() if s.strip()]


def resolve_snapshot(path: Path | str) -> Path:
    """把「看板 HTML」或「数据总表」统一解析成数据总表路径

    实现已上移到 `engine/core/output_paths.py`（产品线与销完表共用同一套配对规则），
    这里保留同名符号以兼容旧调用。
    """
    return _resolve_snapshot(path)


def _leaf_index(detail: dict, subs_all: dict) -> dict[str, str]:
    """子公司名 → 父组（subs_all 是全量配置，detail 只含本期有数据的）"""
    idx: dict[str, str] = {}
    for parent, subs in (subs_all or {}).items():
        for sub in subs or []:
            if sub and sub != parent:
                idx.setdefault(sub, parent)
    for parent, subs in (detail or {}).items():
        for sub in subs:
            if sub and sub != parent:
                idx.setdefault(sub, parent)
    return idx


def build_rows_by_order(names: Iterable[str], piv, tgt, detail, subs_all: dict) -> tuple[list[dict], list[dict]]:
    """按客户清单顺序出行，返回 (rows, trace)

    · 母公司 → 归拢全部子公司；子公司 → 只取该户自身；都查不到 → 空行占位
    · 母公司行会扣掉「本清单里已单列」的子公司，避免同一笔指标被算两遍
    """
    names = list(names)
    leaf = _leaf_index(detail, subs_all)
    piv_idx = set(piv.index) if piv is not None and len(piv) else set()
    tgt_idx = set(tgt.index) if tgt is not None and len(tgt) else set()
    parent_idx = piv_idx | tgt_idx | set((subs_all or {}).keys())
    used: dict[str, int] = {}
    rows: list[dict] = []
    trace: list[dict] = []

    for no, raw in enumerate(names, 1):
        name, note = raw, ""

        if name in REPEAT_GROUPS:
            seq = REPEAT_GROUPS[name]
            i = used.get(name, 0)
            used[name] = i + 1
            if i >= len(seq):
                name, note = None, f"「{raw}」只预设 {len(seq)} 个，第 {i + 1} 次出现无对应"
            else:
                name = seq[i]
                note = f"按出现顺序展开为「{name}」"

        if name in ALIASES:
            note = (note + "；" if note else "") + f"名单写法对应系统「{ALIASES[name]}」"
            name = ALIASES[name]

        row: dict = {"客户": raw}
        if name in parent_idx:
            for d in DEPARTMENTS:
                row[f"{d}_实际"] = _cell(piv, name, d)
                row[f"{d}_指标"] = _cell(tgt, name, d)
            act = (_num(piv.loc[name, "合计"]) if name in piv_idx and "合计" in piv.columns
                   else sum(row[f"{d}_实际"] for d in DEPARTMENTS))
            tg = (_num(tgt.loc[name, "合计"]) if name in tgt_idx and "合计" in tgt.columns
                  else sum(row[f"{d}_指标"] for d in DEPARTMENTS))
            level = "母公司（归拢全部子公司）"
            if name not in piv_idx and name not in tgt_idx:
                note = (note + "；" if note else "") + "本期无实际、无指标，保留空行占位"
        elif name in leaf:
            parent = leaf[name]
            vals = (detail.get(parent, {}) or {}).get(name, {}) or {}
            for d in DEPARTMENTS:
                cell = vals.get(d, {}) or {}
                row[f"{d}_实际"] = _num(cell.get("act", 0))
                row[f"{d}_指标"] = _num(cell.get("tgt", 0))
            act = _num((vals.get("合计", {}) or {}).get("act", 0)) or sum(
                row[f"{d}_实际"] for d in DEPARTMENTS)
            tg = _num((vals.get("合计", {}) or {}).get("tgt", 0)) or sum(
                row[f"{d}_指标"] for d in DEPARTMENTS)
            level = f"子公司单户（父组：{parent}）"
            note = (note + "；" if note else "") + "只含该子公司自身，不含兄弟公司"
        else:
            for d in DEPARTMENTS:
                row[f"{d}_实际"] = 0.0
                row[f"{d}_指标"] = 0.0
            act = tg = 0.0
            level = "未展开" if name is None else "本期无数据/无指标"
            note = (note + "；" if note else "") + (
                "保留空行占位" if name is None else "系统本期无实际、无指标，保留空行占位")

        row["合计_实际"] = act
        row["合计_指标"] = tg
        row["合计达成率"] = _rate(act, tg)
        row["子公司(有数据/配置)"] = ""
        rows.append(row)
        trace.append({"序号": no, "名单原文": raw, "系统实体": name if name else "—",
                      "口径": level, "备注": note})

    # ── 去重：母公司行扣掉本清单已单列的子公司 ──
    leaf_parent: dict[int, str] = {}
    parent_row: dict[str, int] = {}
    for i, t in enumerate(trace):
        lv = str(t.get("口径", ""))
        if lv.startswith("子公司单户") and "父组：" in lv:
            leaf_parent[i] = lv.split("父组：")[-1].rstrip("）")
        elif lv.startswith("母公司"):
            parent_row[str(t.get("系统实体"))] = i

    for li, pname in leaf_parent.items():
        pi = parent_row.get(pname)
        if pi is None:
            continue
        if max(abs(_num(rows[li][f"{d}_实际"])) + abs(_num(rows[li][f"{d}_指标"]))
               for d in DEPARTMENTS) < 1e-9:
            continue
        for d in DEPARTMENTS:
            rows[pi][f"{d}_实际"] -= _num(rows[li][f"{d}_实际"])
            rows[pi][f"{d}_指标"] -= _num(rows[li][f"{d}_指标"])
        rows[pi]["合计_实际"] -= _num(rows[li]["合计_实际"])
        rows[pi]["合计_指标"] -= _num(rows[li]["合计_指标"])
        rows[pi]["合计达成率"] = _rate(rows[pi]["合计_实际"], rows[pi]["合计_指标"])
        trace[pi]["口径"] = "母公司（归母全量 − 本清单已单列子公司）"
        extra = f"已扣除本清单已单列的子公司「{rows[li]['客户']}」"
        trace[pi]["备注"] = (trace[pi]["备注"] + "；" if trace[pi]["备注"] else "") + extra

    return rows, trace


def build_rows_display(piv, tgt, customers: list[str], rest: list[str],
                       subs_with_data: dict, subs_all: dict) -> list[dict]:
    """不指定清单时的默认口径：只出「有指标客户」，顺序 = 看板矩阵展示顺序"""
    order = list(dict.fromkeys(list(customers) + list(rest)))
    picked = [c for c in order if c in tgt.index and _num(tgt.loc[c, "合计"]) > 0]
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
            row[f"{d}_实际"] for d in DEPARTMENTS)
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
    """合计（全量）= 看板矩阵合计行：按全量透视表求和"""
    row: dict = {"客户": "合计（全量）"}
    for d in DEPARTMENTS:
        row[f"{d}_实际"] = _num(piv[d].sum()) if piv is not None and d in piv.columns else 0.0
        row[f"{d}_指标"] = _num(tgt[d].sum()) if tgt is not None and d in tgt.columns else 0.0
    row["合计_实际"] = _num(piv["合计"].sum()) if piv is not None and "合计" in piv.columns else 0.0
    row["合计_指标"] = _num(tgt["合计"].sum()) if tgt is not None and "合计" in tgt.columns else 0.0
    row["合计达成率"] = _rate(row["合计_实际"], row["合计_指标"])
    row["子公司(有数据/配置)"] = ""
    return row


def write_sheet(ws, total: dict, rows: list[dict]) -> None:
    headers = list(total.keys())
    ws.append(headers)
    for col in range(1, len(headers) + 1):
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
                horizontal="left" if col == 1 else (
                    "center" if h.endswith("率") or "子公司" in h else "right"),
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


def _write_note_sheet(ws, trace: list[dict], stats: list[dict], windows: list[tuple[str, str]],
                      order_label: str, data_label: str, title: str) -> None:
    """「说明」sheet：口径 + 各周期核对 + 客户清单逐行解析"""
    ws.column_dimensions["A"].width = 7
    ws.column_dimensions["B"].width = 40
    ws.column_dimensions["C"].width = 40
    ws.column_dimensions["D"].width = 30
    ws.column_dimensions["E"].width = 62

    r = 1
    c = ws.cell(row=r, column=1, value=title)
    c.font = Font(name="微软雅黑", size=14, bold=True, color="1E293B")
    r += 2

    head_lines = [
        f"生成时间：{datetime.now():%Y-%m-%d %H:%M}",
        f"客户清单：{order_label}（{len(trace)} 行）",
        f"数据版本：{data_label}",
        "",
        "【口径】",
        "1. 行 = 客户清单顺序；清单里的「母公司」按归属表归拢其全部子公司，「子公司」只取该户自身。",
        "2. 列 = 4 个事业部 ×（实际 / 指标，万元）+ 合计实际 / 合计指标 / 合计达成率。",
    ]
    for label, win in windows:
        head_lines.append(f"   · {label}窗口：{win or '（无）'}")
    head_lines += [
        "3. 指标取对应周期的手工维护指标表（万元）；达成率 = 实际 / 指标；"
        "指标为 0 且有实际时按 100% 显示（与看板一致），都为 0 时显示「—」。",
        "",
        "【与全量合计的核对】",
    ]
    for s in stats:
        head_lines.append(
            f"  {s['周期']}·{s['指标']}：本表行合计 {s['行合计']:,.2f} 万 ／ 全量 {s['全量']:,.2f} 万"
            f" ／ 指标 {s['行指标']:,.2f} 万 ／ 全量指标 {s['全量指标']:,.2f} 万")
    head_lines += [
        "  差额 = 客户清单未覆盖的客户（或清单只写了父组下的部分子公司）；"
        "核对的是「清单覆盖度」，不是错误。",
        "",
        "【客户清单解析】",
    ]
    for text in head_lines:
        cell = ws.cell(row=r, column=1, value=text)
        cell.font = Font(name="微软雅黑", size=10, bold=text.startswith("【"))
        r += 1

    headers = ["序号", "名单原文", "系统实体", "口径", "备注"]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=r, column=col, value=h)
        cell.fill, cell.font, cell.border = HEAD_FILL, HEAD_FONT, BORDER
        cell.alignment = Alignment(horizontal="center", vertical="center")
    head_row = r
    r += 1
    for item in trace:
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=r, column=col, value=item.get(h, ""))
            cell.font = BODY_FONT
            cell.border = BORDER
            cell.alignment = Alignment(horizontal="center" if col == 1 else "left",
                                       vertical="center", wrap_text=(col == 5))
        r += 1
    ws.freeze_panes = f"A{head_row + 1}"
    ws.auto_filter.ref = f"A{head_row}:E{r - 1}"


def build_workbook(data, periods: Iterable[str], names: list[str], base_dir: Path,
                   order_label: str = "手动输入", data_label: str = "当前清洗结果",
                   on_log: Callable[[str], None] | None = None,
                   title: str = "客户矩阵 · 口径说明"):
    """生成多周期矩阵工作簿，返回 (Workbook, 统计信息列表)

    periods: 取值见 `PERIODS`（monthly / quarterly / annual），按传入顺序出 sheet
    """
    log = on_log or (lambda _msg: None)
    keys = [k for k in periods if k in PERIODS]
    if not keys:
        raise ValueError(f"未指定有效周期：{list(periods)}")

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    stats: list[dict] = []
    trace: list[dict] = []
    windows: list[tuple[str, str]] = []

    for key in keys:
        spec = PERIODS[key]
        log(f"准备{spec.label}数据…")
        d = spec.prepare(data, base_dir)
        windows.append((spec.label, getattr(d, "date_range", "") or getattr(d, "qtr_range", "")))

        for metric, piv, tgt, detail in (
            ("收入", d.inc_piv, d.inc_tgt_grouped, d.subs_detail_inc),
            ("回款", d.pay_piv, d.pay_tgt_grouped, d.subs_detail_pay),
        ):
            rows, tr = build_rows_by_order(names, piv, tgt, detail, d.subs_all)
            total = build_total_row(piv, tgt)
            ws = wb.create_sheet(f"{spec.label}-{metric}")
            write_sheet(ws, total, rows)
            if not trace:
                trace = tr
            stats.append({
                "周期": spec.label, "指标": metric,
                "行合计": sum(_num(x["合计_实际"]) for x in rows), "全量": _num(total["合计_实际"]),
                "行指标": sum(_num(x["合计_指标"]) for x in rows), "全量指标": _num(total["合计_指标"]),
                "行数": len(rows),
            })
            log(f"  {spec.label}·{metric}：{len(rows)} 行")

    # 客户名在系统里完全找不到的行（不是「本期无数据」，是名字对不上）
    unmatched = [t["名单原文"] for t in trace if t["口径"] in ("未展开", "本期无数据/无指标")]
    for s in stats:
        s["未识别"] = len(unmatched)
        s["未识别清单"] = unmatched

    _write_note_sheet(wb.create_sheet("说明"), trace, stats, windows, order_label, data_label, title)
    return wb, stats
