# Author: naohua168 <bai_bai168@qq.com>
"""销售归属 —— 解析、重名报告与 客户销售归属.json 写回

由 scripts/config_excel_to_json.py 拆分而来（行为不变，见 logs/_dryrun_before.txt 比对）。
"""
from __future__ import annotations

import json
import sys
from engine.core.utils import rel_path
try:  # 直接以脚本方式运行时
    from sheet_style import (
        COLOR_BANNER_BG, COLOR_PRIMARY, TAB_COLORS, banner, data_cell, finish,
        header_row, locate_header_row, set_widths,
    )
except ImportError:  # 以包形式导入时（如单元测试）
    from scripts.sheet_style import (  # type: ignore[no-redef]
        COLOR_BANNER_BG, COLOR_PRIMARY, TAB_COLORS, banner, data_cell, finish,
        header_row, locate_header_row, set_widths,
    )
from .constants import BASE_DIR, ATTRIBUTION_CFG
from .parsing import split_metric_value, _parse_cell
from .paths import BASE_DIR, ATTRIBUTION_CFG


def excel_to_attribution(sheet) -> dict:
    """从 Excel「销售归属」sheet 构建 {母公司: {子公司: {指标: {部门: {销售: 比例}}}}}

    指标列取值：收入 / 回款 / 收入,回款（同时写入两个指标）
    """
    # 读取行（兼容带横幅布局：表头行在 1~4 行内按列名定位）
    raw = [tuple(r) for r in sheet.iter_rows(values_only=True)]
    hi = locate_header_row(raw, ("母公司", "子公司"), max_scan=4)
    if hi < 0:
        raise ValueError("「销售归属」sheet 找不到表头行（需含「母公司」「子公司」列）")
    headers = [str(v).strip() if v is not None else "" for v in raw[hi]]
    i_parent = headers.index("母公司")
    i_sub = headers.index("子公司")
    i_metric = headers.index("指标") if "指标" in headers else -1
    i_dept = headers.index("部门") if "部门" in headers else -1
    i_sales = headers.index("销售") if "销售" in headers else -1
    i_ratio = headers.index("比例") if "比例" in headers else -1
    i_note = headers.index("说明") if "说明" in headers else -1

    def at(row, i: int) -> str:
        return _parse_cell(row[i]) if 0 <= i < len(row) else ""

    rows: list[dict] = []
    for row in raw[hi + 1:]:
        parent = at(row, i_parent)
        sub = at(row, i_sub)
        metric = at(row, i_metric)
        dept = at(row, i_dept)
        sales = at(row, i_sales)
        ratio = at(row, i_ratio)
        note = at(row, i_note)
        if not parent and not sub:
            continue  # 空行
        if not parent or not sub or not metric or not dept or not sales:
            raise ValueError(
                f"销售归属存在不完整行（母公司/子公司/指标/部门/销售 必填）: {parent}/{sub}/{metric}/{dept}/{sales}"
            )
        rows.append({
            "parent": parent, "sub": sub, "metric": metric,
            "dept": dept, "sales": sales, "ratio": ratio, "note": note,
        })

    if not rows:
        raise ValueError("销售归属 sheet 没有数据行")

    # 构建嵌套结构
    result: dict = {}
    for r in rows:
        metrics = split_metric_value(r["metric"])
        for m in metrics:
            if m not in ("收入", "回款"):
                raise ValueError(f"非法指标值: {m!r}（可选 收入 / 回款 / 收入/回款）")
        # 比例解析（支持整数/小数/百分比/空=1.0）
        ratio = r["ratio"]
        if ratio == "":
            ratio_v = 1.0
        elif ratio.endswith("%"):
            ratio_v = float(ratio[:-1]) / 100.0
        else:
            ratio_v = float(ratio)
        if not (0 < ratio_v <= 1.0):
            raise ValueError(f"比例非法（应为 0~1）: {r['parent']}/{r['sub']}/{r['sales']} = {ratio_v}")

        parent_obj = result.setdefault(r["parent"], {"子公司": {}})
        subs = parent_obj.setdefault("子公司", {})
        sub_obj = subs.setdefault(r["sub"], {})
        for m in metrics:
            dept_map = sub_obj.setdefault(m, {}).setdefault(r["dept"], {})
            dept_map[r["sales"]] = ratio_v
            if r["note"]:
                sub_obj.setdefault("_说明", r["note"])

    report_dup_names(result)
    return result


def report_dup_names(attribution: dict) -> None:
    """提示归属表里「同一家公司写成两遍」的条目（全角括号 vs 半角括号、空格差异等）

    匹配已按 `engine.core.name_key` 归一（不会漏匹配），但同一家公司配两遍会让
    父组/销售出现两份口径，建议人工合并 → 这里只提示、不改配置。

    判定规则见 `engine.core.name_key.dup_name_groups`（多组配置不算重复）。
    """
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
    try:
        from engine.core.name_key import dup_name_groups, format_conflicts  # noqa: PLC0415
    except ImportError:  # pragma: no cover - 缺 engine 包时不阻断同步
        return

    problems = dup_name_groups(attribution)
    if problems:
        print(f"⚠ 归属表存在「同一家公司写成两遍」的条目 {len(problems)} 组"
              f"（匹配会自动合并，建议合并成一条）: {format_conflicts(problems)}")


def update_attribution(attribution: dict, dry_run: bool = False) -> dict:
    """把销售归属写回 客户销售归属.json（保留 _说明/_销售拆分，客户归属数据来自 Excel）"""
    if not ATTRIBUTION_CFG.exists():
        raise FileNotFoundError(f"客户销售归属.json 不存在: {rel_path(ATTRIBUTION_CFG)}")

    text = ATTRIBUTION_CFG.read_text(encoding="utf-8")
    cfg = json.loads(text)
    # _销售拆分（客户矩阵按销售拆行的母公司列表）也以本 JSON 为事实源，写回时保留
    new_cfg = {"_说明": cfg.get("_说明", "客户统一归属 — 母公司→子公司→销售分配"),
               "_销售拆分": cfg.get("_销售拆分"),
               "客户归属": attribution}

    if dry_run:
        return new_cfg

    ATTRIBUTION_CFG.write_text(
        json.dumps(new_cfg, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return new_cfg
