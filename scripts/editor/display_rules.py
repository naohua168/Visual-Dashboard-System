# Author: naohua168 <bai_bai168@qq.com>
"""展示规则 / KPI 指标 —— 解析与 展示规则.json 写回

由 scripts/config_excel_to_json.py 拆分而来（行为不变，见 logs/_dryrun_before.txt 比对）。
"""
from __future__ import annotations

import json
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
from .constants import DISPLAY_RULES_CFG, RULE_PAGES, KPI_PAGES, KPI_METRICS, _STALE_NOTE_RE
from .parsing import _parse_cell
from .paths import DISPLAY_RULES_CFG


def _render_value(v, depth: int) -> str:
    """递归渲染 JSON 值，复刻原文件风格：
    - dict → 多行 + 2空格缩进
    - list（如月份范围）→ 紧凑单行
    - depth: 值内容所用的缩进层级（depth=2 → 内容缩进4空格）
    """
    if isinstance(v, dict):
        if not v:
            return "{}"
        lines = ["{"]
        items = list(v.items())
        for i, (k, val) in enumerate(items):
            sep = "," if i < len(items) - 1 else ""
            lines.append(f'{"  " * depth}"{k}": {_render_value(val, depth + 1)}{sep}')
        lines.append(f'{"  " * (depth - 1)}}}')
        return "\n".join(lines)
    if isinstance(v, list):
        return "[" + ", ".join(json.dumps(x, ensure_ascii=False) for x in v) + "]"
    return json.dumps(v, ensure_ascii=False)


def _render_time_range_block(time_config: dict, start_indent: int = 2) -> str:
    """渲染「时间范围」块文本，复刻原文件风格（键间空行 + 正确缩进）。

    Args:
        time_config: 时间范围 dict
        start_indent: "时间范围" 键的缩进空格数（顶层键 = 2）
    """
    base = " " * start_indent
    out: list[str] = [f'{base}"时间范围": {{']
    keys = list(time_config.items())
    for i, (k, v) in enumerate(keys):
        rendered = _render_value(v, (start_indent // 2) + 2)
        lines = rendered.splitlines()
        sep = "," if i < len(keys) - 1 else ""
        # 顶层键（如 "年度累计"）缩进 base + 2 空格
        out.append(f'{base}  "{k}": {lines[0]}')
        if len(lines) > 1:
            out.extend(lines[1:])
        # 逗号加在值结束之后（多行 dict → 最后一行；单行 → 键行）
        out[-1] += sep
        if i < len(keys) - 1:
            out.append("")  # 键间空行
    out.append(f"{base}}}")
    return "\n".join(out)


def _replace_time_range_block(text: str, time_config: dict) -> str:
    """在 JSON 文本中精确替换「时间范围」块（从键所在行行首 到 匹配闭合的 }），其余字节不动"""
    start = text.find('"时间范围"')
    if start == -1:
        raise ValueError("cleaning_config.json 中找不到「时间范围」键")
    # 定位到该键所在行行首（保留前导缩进与换行）
    line_start = text.rfind("\n", 0, start) + 1
    # 找到冒号后的第一个 {
    brace = text.find("{", start)
    # 括号深度匹配到闭合 }
    depth = 0
    in_str = False
    escape = False
    end = None
    for i in range(brace, len(text)):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
    if end is None:
        raise ValueError("cleaning_config.json 中「时间范围」块未正确闭合")

    new_block = _render_time_range_block(time_config, start_indent=2)
    # 消费原块后的逗号（若存在）
    tail = text[end + 1:]
    if tail.lstrip().startswith(","):
        consumed = tail.lstrip()[1:]
        new_block += ","
    else:
        consumed = tail
    return text[:line_start] + new_block + consumed


def _merge_notes(merged: dict, old: dict):
    """递归合并 _ 前缀说明字段：merged 为 Excel 结果，old 为原文件页面

    作用：Excel 不维护 _说明 等注释字段，写回时把原文件的说明补回，避免信息丢失。
    例外（2026-09-28）：`_X说明` 对应的配置项 X 已被移除时一并丢弃，
    避免 JSON 里留下指向已删项的"孤儿说明"。
    """
    for k, v in old.items():
        if isinstance(k, str) and k.startswith("_"):
            m = _STALE_NOTE_RE.match(k)
            if m and m.group(1) not in merged:
                continue
            merged.setdefault(k, v)
        elif isinstance(v, dict) and isinstance(merged.get(k), dict):
            _merge_notes(merged[k], v)


def update_display_rules(rules: dict, dry_run: bool = False) -> dict:
    """把展示规则写回展示规则.json（保留 _说明/_关键约定，重建 6 个页面部分）

    设计：不追求字节级复刻原文件排版，而是保证：
        1. JSON 永远有效（用 json.dumps 标准输出）
        2. _ 前缀说明字段（_说明/_关键约定/区块 _说明 等）从原文件保留
        3. 页面数据 100% 来自 Excel
    """
    if not DISPLAY_RULES_CFG.exists():
        raise FileNotFoundError(f"展示规则.json 不存在: {rel_path(DISPLAY_RULES_CFG)}")

    text = DISPLAY_RULES_CFG.read_text(encoding="utf-8")
    cfg = json.loads(text)
    new_cfg = dict(cfg)  # 保留 _说明/_关键约定 及一切现有字段
    # 页面数据替换为 Excel 值；同时保留原页面中 _ 前缀说明字段（_客户筛选说明/_说明 等）
    for page in RULE_PAGES:
        excel_page = rules[page]
        old_page = cfg.get(page, {})
        merged = dict(excel_page)
        _merge_notes(merged, old_page)
        new_cfg[page] = merged

    if dry_run:
        return new_cfg

    # 标准格式输出（ensure_ascii=False 保留中文；indent=2；末尾换行）
    DISPLAY_RULES_CFG.write_text(
        json.dumps(new_cfg, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return new_cfg


def update_kpi_rules(kpi: dict, dry_run: bool = False) -> dict:
    """把 KPI 指标覆盖写回 展示规则.json 对应页面的 `KPI指标` 区块。

    只更新「年度达成/月度达成/季度达成」三个页面下的 KPI指标 子对象，
    其余配置不动；某页面收入/回款都留空时不写该区块（恢复指标文件合计）。
    """
    if not DISPLAY_RULES_CFG.exists():
        raise FileNotFoundError(f"展示规则.json 不存在: {rel_path(DISPLAY_RULES_CFG)}")

    text = DISPLAY_RULES_CFG.read_text(encoding="utf-8")
    cfg = json.loads(text)
    new_cfg = dict(cfg)
    for page in KPI_PAGES:
        page_cfg = dict(new_cfg.get(page, {}))
        # 仅更新 KPI指标 区块，保留页面其他内容
        page_kpi = {m: v for m, v in kpi.get(page, {}).items() if v is not None}
        if page_kpi:
            page_cfg["KPI指标"] = page_kpi
        else:
            page_cfg.pop("KPI指标", None)
        new_cfg[page] = page_cfg

    if dry_run:
        return new_cfg

    DISPLAY_RULES_CFG.write_text(
        json.dumps(new_cfg, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return new_cfg


def excel_to_kpi(sheet) -> dict:
    """从「KPI指标」sheet 构建 {页面: {收入: float|None, 回款: float|None}}

    值留空 = 不覆盖（KPI 卡片用指标文件合计）；填数字（万元）= 覆盖 Hero 圆环指标总数。
    写回展示规则.json 对应页面的 `KPI指标` 区块，不影响表格/矩阵里的明细指标。
    """
    result: dict[str, dict[str, float | None]] = {
        page: {m: None for m in KPI_METRICS} for page in KPI_PAGES
    }
    rows = [tuple(r) for r in sheet.iter_rows(values_only=True)]
    hi = locate_header_row(rows, ("页面", "指标"), max_scan=4)
    if hi < 0:
        raise ValueError("「KPI指标」sheet 找不到表头行（需含「页面」「指标」列）")
    headers = [str(v).strip() if v is not None else "" for v in rows[hi]]
    i_page = headers.index("页面") if "页面" in headers else -1
    i_metric = headers.index("指标") if "指标" in headers else -1
    i_val = next((i for i, h in enumerate(headers) if h.startswith("值")), -1)
    for row in rows[hi + 1:]:
        page = _parse_cell(row[i_page]) if 0 <= i_page < len(row) else ""
        metric = _parse_cell(row[i_metric]) if 0 <= i_metric < len(row) else ""
        value = row[i_val] if 0 <= i_val < len(row) else None
        if not page:
            continue  # 空行
        if page not in KPI_PAGES:
            raise ValueError(f"非法 KPI 页面: {page!r}（可选 {'/'.join(KPI_PAGES)}）")
        if metric not in KPI_METRICS:
            raise ValueError(f"非法 KPI 指标: {metric!r}（可选 {'/'.join(KPI_METRICS)}）")
        v: float | None = None
        if value not in (None, ""):
            try:
                v = float(value)
            except (TypeError, ValueError):
                raise ValueError(f"KPI 指标值非法（应为数字，万元）: {page}/{metric} = {value!r}")
        result[page][metric] = v
    return result
