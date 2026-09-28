# Author: naohua168 <bai_bai168@qq.com>
"""配置编辑器「展示规则」sheet — 页面展示配置的 Excel 编辑层（2026-09-28 重做）

改动背景：旧表结构是 `页面 | 路径 | 值 | 说明`，路径形如 `客户矩阵.优先展示.17`，
业务同事要猜路径含义、排序/行数的可选值只能靠口头约定，且表里混着若干
**代码从未读取的项**（部门卡.显示 / 卡片1~3.显示 / 销售达成.排序 /
销售达成.销售TopN / 数据总览.客户筛选）。

新结构（本模块负责生成与解析）：

    ┌─ 横幅提示（合并 A1:G1，只改「值」列）
    ├─ 表头：序号 | 页面 | 区块 | 配置项 | 值 | 可选值 / 填写规则 | 说明（作用与影响）
    └─ 每页一段（段标题行 = 页面名，配置项留空即视为段标题）：
        序号  页面      区块      配置项     值                可选值 / 填写规则            说明
        1     数据总览           销售TopN   10                整数 ≥ 0（0 = 全部）          …
        2     年度达成  客户矩阵  最大行数   0                 整数 ≥ 0（0 = 不限）          …
        3     年度达成  客户矩阵  排序       目标合计降序       三选一下拉                    …
        4     年度达成  客户矩阵  优先展示   比亚迪汽车工业…    **手填**客户全称/母公司组名    …
        …     （优先展示 / 客户筛选 = 一个客户一行，行数不限）

设计约定：
  - **只有 SPEC 白名单里的项能被识别**（都是代码真正读取的），写错项/非法值
    会拒绝写回并给出中文原因；
  - 「值」列下拉只用于**取值有限的项**：排序 = 三选一；数字项 = 整数校验 + 提示。
    **优先展示 / 客户筛选 不做下拉**（2026-09-28 用户口径：客户名由使用者自己填），
    改由「可选值 / 填写规则」+「说明」两列写清怎么填（客户全称 / 母公司组名 / 一个一行）；
  - 旧「路径」表头仍可解析（向前兼容），但 `--init-rules` 会重建为新结构；
  - JSON 事实源不变：`config/前端渲染/展示规则.json`（Excel 是编辑层）。
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path

try:
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation
except ImportError:  # pragma: no cover
    raise SystemExit("缺少 openpyxl，请先安装: pip install openpyxl")

BASE_DIR = Path(__file__).parent.parent
EXCEL_PATH = BASE_DIR / "config" / "配置编辑器.xlsx"
DISPLAY_RULES_CFG = BASE_DIR / "config" / "前端渲染" / "展示规则.json"
# 历史遗留：曾经生成过「下拉选项」辅助 sheet（客户名下拉用），2026-09-28 起不再需要，
# 刷新时若发现该 sheet 会一并删除
LEGACY_OPTION_SHEET = "下拉选项"

RULE_SHEET_NAME = "展示规则"
RULE_HEADERS = ["序号", "页面", "区块", "配置项", "值", "可选值 / 填写规则", "说明（作用与影响）"]
REQUIRED_HEADERS = ("页面", "区块", "配置项", "值")

# 页面顺序（与 展示规则.json / 看板导航一致）
PAGE_ORDER = ["数据总览", "年度达成", "月度达成", "季度达成", "销售达成", "年度同比"]

# 无任何可配置项的页面（保留页面键，避免 JSON 丢页；值的规则写在代码里）
NO_ITEM_PAGES: dict[str, str] = {
    "销售达成": "本页无可配置项：卡片显示 / 排序 / 销售人数均为固定规则（2026-09-28 清理不生效项）",
}

SORT_CHOICES = ["目标合计降序", "实际金额降序", "达成率降序"]

# ── 生效配置项白名单（唯一来源：模板生成 / 解析校验 / 说明文案共用）──
#    kind: int = 整数（0 表示不限）｜ sort = 三选一｜ names = 名单（一客户一行）
#    read_by: 代码里的读取位置（供维护者核对，不写进 Excel）
SPEC: list[dict] = [
    {
        "page": "数据总览", "section": "", "key": "销售TopN", "kind": "int",
        "options": "整数 ≥ 0（0 = 显示全部）",
        "note": "数据总览页右半区『销售年度收入/回款达成度景观』显示前 N 名销售",
        "read_by": "processors/page_overview.py",
    },
    *[
        {
            "page": page, "section": "客户矩阵", "key": key,
            "kind": kind, "options": options, "note": note,
            "read_by": "processors/page_data.py → config_loader.CustomerFilter",
        }
        for page in ("年度达成", "月度达成", "季度达成")
        for key, kind, options, note in (
            ("最大行数", "int", "整数 ≥ 0（0 = 不限）", "客户矩阵主表最多显示几行客户；『优先展示』里的客户不会被截断"),
            ("排序", "sort", "三选一下拉：目标合计降序 / 实际金额降序 / 达成率降序", "仅当『优先展示』非空时生效；留空 = 按指标表原始顺序"),
            ("优先展示", "names",
             "手填客户名（二选一写法）：① 母公司组名，如 广汽系 = 该组全部子公司；② 客户全称，照「销售归属」sheet 的名字写。一个客户一行，可多行",
             "名单内客户【始终显示】并排在最前面（即使无指标无实际）；全部清空 = 所有客户都显示"),
            ("客户筛选", "names",
             "手填客户名（同上）：母公司组名 或 客户全称；一个客户一行，可多行",
             "填了就【只】显示这些客户（白名单，其余客户隐藏）；留空 = 不筛选（推荐）"),
        )
    ],
    *[
        {
            "page": "年度同比", "section": "", "key": key, "kind": kind,
            "options": options, "note": note,
            "read_by": "processors/page_data.py → config_loader.CustomerFilter",
        }
        for key, kind, options, note in (
            ("最大行数", "int", "整数 ≥ 0（0 = 不限）", "重要客户同比矩阵显示的行数"),
            ("排序", "sort", "三选一下拉：目标合计降序 / 实际金额降序 / 达成率降序", "客户排序方式"),
            ("优先展示", "names",
             "手填客户名：母公司组名（如 广汽系）或 客户全称；一个客户一行，可多行",
             "名单内客户始终显示并排在前面；同比页一般留空"),
            ("客户筛选", "names",
             "手填客户名（同上）；一个客户一行，可多行",
             "填了就只显示这些客户；同比页一般留空"),
        )
    ],
]

# 说明 sheet 第 3 节（--init 模板 / 刷新说明页共用同一文案，避免两处漂移）
RULE_NOTE_LINES: list[list[str]] = [
    ["3. 「展示规则」sheet 列说明（2026-09-28 重做：页面 / 区块 / 配置项 / 值 / 可选值 / 说明）："],
    ["   - 只改「值」列（浅黄底）；「可选值 / 填写规则」与「说明」列是参考资料，不用改"],
    ["   - 页面: 数据总览 / 年度达成 / 月度达成 / 季度达成 / 年度同比（销售达成页暂无可调项）"],
    ["   - 区块: 客户矩阵（年度/月度/季度达成）；其余页面留空 = 页面级配置"],
    ["   - 配置项（**只保留代码真正读取的项**）:"],
    ["     · 销售TopN / 最大行数: 填整数，0 = 显示全部（不限制行数）"],
    ["     · 排序: 下拉三选一（目标合计降序 / 实际金额降序 / 达成率降序）"],
    ["     · 优先展示: 一个客户一行，**自己填客户名** → 这些客户始终显示并排最前（无指标无实际也显示）"],
    ["       填法二选一：① 母公司组名（如 广汽系 = 该组全部子公司）② 客户全称（照「销售归属」sheet 写）"],
    ["       全部清空 = 所有客户都显示；一个格子里用「、」分隔多个名字也行（如 甲公司、乙公司）"],
    ["     · 客户筛选: 一个客户一行，填了就**只**显示这些客户（白名单）；留空 = 不筛选（推荐）"],
    ["   - 客户名怎么写才对: 到「销售归属」sheet 的『母公司』『子公司』两列照着抄（系统按这两个名字匹配）"],
    ["   - ⚠ 已删除的不生效项（2026-09-28）: 部门卡.显示 / 卡片1~3_显示 / 销售达成.排序 + 销售TopN / 数据总览.客户筛选"],
    ["     —— 这些项代码从未读取，改了不生效，故从表里去掉（避免误以为能关卡片/限人数）"],
    [""],
]


# ──────────────────────────────────────────────────────────────
# 工具
# ──────────────────────────────────────────────────────────────
def _cell(value) -> str:
    """Excel 单元格 → 干净字符串"""
    if value is None:
        return ""
    if isinstance(value, datetime.datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _type_cast(value: str):
    """按字符串内容推断值类型：bool / int / float / str（旧格式解析用）"""
    v = value.strip()
    low = v.lower()
    if low in ("true", "false"):
        return low == "true"
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


def spec_index() -> dict[tuple[str, str, str], dict]:
    return {(s["page"], s["section"], s["key"]): s for s in SPEC}


def page_specs(page: str) -> list[dict]:
    return [s for s in SPEC if s["page"] == page]


# ──────────────────────────────────────────────────────────────
# JSON → sheet 行
# ──────────────────────────────────────────────────────────────
def _value_text(spec: dict, value) -> str:
    if spec["kind"] == "names":
        return ""
    if value in (None, ""):
        return ""
    return str(value).strip()


def build_rows(rules: dict) -> list[list]:
    """按 SPEC + 当前 JSON 生成 sheet 数据行（不含表头/横幅）

    行格式与 RULE_HEADERS 对齐：
        [序号, 页面, 区块, 配置项, 值, 可选值/填写规则, 说明]
    段标题行：只有「页面」有值（配置项为空 → 解析时跳过）
    """
    rows: list[list] = []
    seq = 0
    for page in PAGE_ORDER:
        page_cfg = rules.get(page) or {}
        rows.append(["", page, "", "", "", "", NO_ITEM_PAGES.get(page, "")])
        if page in NO_ITEM_PAGES:
            continue
        for spec in page_specs(page):
            node = page_cfg
            if spec["section"]:
                node = page_cfg.get(spec["section"], {}) or {}
            raw = node.get(spec["key"]) if isinstance(node, dict) else None
            if spec["kind"] == "names":
                items = [str(x) for x in (raw or []) if str(x).strip()]
                if not items:
                    seq += 1
                    rows.append([seq, page, spec["section"], spec["key"], "",
                                 spec["options"], spec["note"]])
                else:
                    for it in items:
                        seq += 1
                        rows.append([seq, page, spec["section"], spec["key"], it,
                                     spec["options"], spec["note"]])
            else:
                seq += 1
                rows.append([seq, page, spec["section"], spec["key"],
                             _value_text(spec, raw), spec["options"], spec["note"]])
    return rows


# ──────────────────────────────────────────────────────────────
# sheet 行 → JSON
# ──────────────────────────────────────────────────────────────
def parse_rows(rows: list[list], headers: list[str]) -> tuple[dict, list[str]]:
    """解析新结构 → (rules, warnings)

    Raises:
        ValueError: 未知页面/未知配置项/非法取值（拒绝写回，避免脏配置进系统）
    """
    idx = {h: i for i, h in enumerate(headers)}
    i_page, i_sec, i_key, i_val = (idx[c] for c in REQUIRED_HEADERS)
    spec_map = spec_index()
    valid_pages = set(PAGE_ORDER)

    rules: dict = {}
    seen: set[tuple[str, str, str]] = set()
    warnings: list[str] = []
    current_page = ""

    for row in rows:
        def at(i: int) -> str:
            return _cell(row[i]) if i < len(row) else ""

        page = at(i_page) or current_page
        section = at(i_sec)
        key = at(i_key)
        value = at(i_val)

        if not page and not section and not key and not value:
            continue                       # 空行
        if not key:
            # 段标题行：写入页面键（保证 JSON 不丢页面）
            if page:
                current_page = page
                rules.setdefault(page, {})
            continue
        if page not in valid_pages:
            raise ValueError(
                f"「{RULE_SHEET_NAME}」存在未知页面: {page!r}；可选: {' / '.join(PAGE_ORDER)}"
            )
        current_page = page
        spec = spec_map.get((page, section, key))
        if spec is None:
            allowed = "、".join(
                (f"{s['section']}.{s['key']}" if s["section"] else s["key"])
                for s in page_specs(page)
            )
            raise ValueError(
                f"「{RULE_SHEET_NAME}」{page} 页不存在配置项: "
                f"{f'{section}.' if section else ''}{key!r}；本页可填: {allowed or '（无可调项）'}"
            )
        if spec["kind"] == "names":
            node = rules.setdefault(page, {})
            if section:
                node = node.setdefault(section, {})
            arr_key = spec["key"]
            lst = node.setdefault(arr_key, [])
            if not isinstance(lst, list):
                lst = node[arr_key] = []
            for part in _split_names(value):
                if part not in lst:
                    lst.append(part)
            seen.add((page, section, key))
            continue

        if (page, section, key) in seen:
            warnings.append(f"{page}/{section or '页面级'}/{key} 出现多行，只取第一行")
            continue
        seen.add((page, section, key))
        node = rules.setdefault(page, {})
        if section:
            node = node.setdefault(section, {})
        node[spec["key"]] = _parse_scalar(spec, value, warnings)
        if section:
            # 区块内其余名单键（未出现在表里）→ 空数组，保证结构完整
            for s2 in page_specs(page):
                if s2["section"] == section and s2["kind"] == "names":
                    node.setdefault(s2["key"], [])

    # 必备页面齐全
    for page in PAGE_ORDER:
        if page not in rules:
            raise ValueError(
                f"「{RULE_SHEET_NAME}」缺少页面段落: {page}（段标题行勿删）"
            )
    # 未在表里出现的项 → 警告（回退代码内默认值）
    for spec in SPEC:
        if (spec["page"], spec["section"], spec["key"]) not in seen:
            loc = f"{spec['section']}.{spec['key']}" if spec["section"] else spec["key"]
            warnings.append(
                f"缺少配置项 {spec['page']}/{loc} → 使用代码内默认值"
            )
    # 结构完整性：names 键缺失时补空数组
    for spec in SPEC:
        if spec["kind"] != "names":
            continue
        node = rules.get(spec["page"], {})
        if spec["section"]:
            node = node.get(spec["section"], {})
        if isinstance(node, dict):
            node.setdefault(spec["key"], [])
    return rules, warnings


def _split_names(value: str) -> list[str]:
    """一个单元格里可能粘贴多个客户名（顿号/分号分隔）→ 拆开"""
    if not value:
        return []
    out: list[str] = []
    for chunk in value.replace("；", ";").replace("、", ";").split(";"):
        name = chunk.strip()
        if name:
            out.append(name)
    return out


def _parse_scalar(spec: dict, value: str, warnings: list[str]):
    if spec["kind"] == "int":
        if value == "":
            warnings.append(f"{spec['page']}/{spec['key']} 值为空 → 按 0（不限）")
            return 0
        try:
            num = int(float(value))
        except ValueError:
            raise ValueError(
                f"{spec['page']}/{spec['key']} 应为整数（0 = 不限），当前: {value!r}"
            )
        if num < 0:
            raise ValueError(f"{spec['page']}/{spec['key']} 不能为负数，当前: {num}")
        return num
    # sort
    if value == "":
        warnings.append(f"{spec['page']}/{spec['key']} 排序为空 → 按「{SORT_CHOICES[0]}」")
        return SORT_CHOICES[0]
    if value not in SORT_CHOICES:
        raise ValueError(
            f"{spec['page']}/{spec['key']} 排序取值非法: {value!r}；"
            f"只能是 {' / '.join(SORT_CHOICES)}"
        )
    return value


# ──────────────────────────────────────────────────────────────
# 旧「路径」结构解析（向前兼容）
# ──────────────────────────────────────────────────────────────
ARRAY_KEYS = {"优先展示", "客户筛选"}


def _get_path_node(root: dict, parent_parts: list[str]) -> dict:
    node = root
    for p in parent_parts:
        if p not in node or not isinstance(node[p], dict):
            node[p] = {}
        node = node[p]
    return node


def parse_legacy_rows(rows: list[list], headers: list[str]) -> dict:
    """解析旧结构：页面 | 路径 | 值 | 说明"""
    idx = {h: i for i, h in enumerate(headers)}
    i_page, i_path, i_val, i_note = (idx.get(c, -1) for c in ("页面", "路径", "值", "说明"))

    result: dict = {}
    arrays: dict[str, dict[str, dict]] = {}
    for row in rows:
        def at(i: int) -> str:
            return _cell(row[i]) if 0 <= i < len(row) else ""

        page, path, value, note = at(i_page), at(i_path), at(i_val), at(i_note)
        if not page or not path:
            continue
        parts = path.split(".")
        if len(parts) >= 2 and parts[-1].isdigit() and parts[-2] in ARRAY_KEYS:
            section = ".".join(parts[:-2])
            arrays.setdefault(page, {}).setdefault(section, {}).setdefault(
                parts[-2], []
            ).append((int(parts[-1]), value))
            continue
        if parts[-1] in ARRAY_KEYS:
            section = ".".join(parts[:-1])
            arrays.setdefault(page, {}).setdefault(section, {})[parts[-1]] = []
            continue
        node = _get_path_node(result.setdefault(page, {}), parts[:-1])
        node[parts[-1]] = _type_cast(value)
        if note:
            node[f"_{parts[-1]}说明"] = note

    for page, sections in arrays.items():
        page_obj = result.setdefault(page, {})
        for section, arr_map in sections.items():
            node = _get_path_node(page_obj, section.split(".")) if section else page_obj
            for arr_key, items in arr_map.items():
                node[arr_key] = [v for _, v in sorted(items, key=lambda x: x[0])]

    for p in PAGE_ORDER:
        if p not in result:
            raise ValueError(f"「{RULE_SHEET_NAME}」缺少页面: {p}")
    return result


def excel_to_display_rules(sheet) -> dict:
    """Excel「展示规则」sheet → 展示规则 dict（自动识别新/旧表头）

    - 新表头（含 页面/区块/配置项/值）→ parse_rows（带校验）
    - 旧表头（含 路径）→ parse_legacy_rows（向前兼容，不报错）
    """
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        raise ValueError(f"「{RULE_SHEET_NAME}」sheet 为空")
    headers = [_cell(h) for h in rows[0]]
    # 横幅提示行（合并单元格）时自动跳过：找第一行含必需表头的行
    if not all(h in headers for h in REQUIRED_HEADERS):
        for i, row in enumerate(rows[1:3], start=1):
            hdr = [_cell(h) for h in row]
            if all(h in hdr for h in REQUIRED_HEADERS):
                headers, rows = hdr, rows[i:]
                break
    if "路径" in headers:
        return parse_legacy_rows(rows[1:], headers)
    missing = [h for h in REQUIRED_HEADERS if h not in headers]
    if missing:
        raise ValueError(
            f"「{RULE_SHEET_NAME}」表头缺少必需列 {missing}；"
            f"实际表头: {headers}（旧格式需含「路径」列）"
        )
    rules, warns = parse_rows(rows[1:], headers)
    for w in warns:
        print(f"  ⚠️ {RULE_SHEET_NAME}: {w}")
    return rules


# ──────────────────────────────────────────────────────────────
# 生成 / 刷新「展示规则」sheet
# ──────────────────────────────────────────────────────────────
def _thin_border() -> Border:
    thin = Side(style="thin", color="B0B7C3")
    return Border(left=thin, right=thin, top=thin, bottom=thin)


def attach_rules_sheet(wb, rules: dict):
    """在 workbook 中创建/替换「展示规则」sheet（原地修改，需调用方 save）

    若存在历史遗留的「下拉选项」sheet（2026-09-28 前的客户名下拉辅助页）一并删除。
    """
    for name in (RULE_SHEET_NAME, LEGACY_OPTION_SHEET):
        if name in wb.sheetnames:
            del wb[name]

    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    border = _thin_border()
    ws = wb.create_sheet(RULE_SHEET_NAME, 1)

    # ① 横幅提示
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(RULE_HEADERS))
    b = ws.cell(row=1, column=1)
    b.value = ("只改「值」列（浅黄底）；「可选值 / 填写规则」「说明」列是参考资料。"
               "改完保存 → 运行 启动系统.bat / run_all.bat 自动同步生效。")
    b.fill = PatternFill("solid", fgColor="EAF3FF")
    b.font = Font(bold=True, size=11, color="1F4E78")
    b.alignment = Alignment(vertical="center", horizontal="left")
    ws.row_dimensions[1].height = 26

    # ② 表头
    for col, h in enumerate(RULE_HEADERS, 1):
        c = ws.cell(row=2, column=col, value=h)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = border
    ws.row_dimensions[2].height = 22

    # ③ 数据行（段标题行 + 配置行）
    dv_rows: dict[str, list[int]] = {"int": [], "sort": [], "names": []}
    spec_map = spec_index()
    row_idx = 3
    for row in build_rows(rules):
        seq, page, section, key, value, options, note = row
        is_section = not key
        vals = [seq, page, section, key, value, options, note]
        for col, v in enumerate(vals, 1):
            c = ws.cell(row=row_idx, column=col, value=v)
            c.border = border
            c.alignment = Alignment(
                vertical="center", wrap_text=(col in (6, 7)),
                horizontal="center" if col in (1, 2, 3, 4) else "left",
            )
        if is_section:
            ws.merge_cells(start_row=row_idx, start_column=2, end_row=row_idx,
                           end_column=len(RULE_HEADERS))
            ws.cell(row=row_idx, column=2).font = Font(bold=True, color="1F4E78")
            ws.cell(row=row_idx, column=2).fill = PatternFill("solid", fgColor="F2F7FF")
            ws.row_dimensions[row_idx].height = 20
        else:
            ws.cell(row=row_idx, column=5).fill = PatternFill("solid", fgColor="FFF9E6")
            ws.cell(row=row_idx, column=6).fill = PatternFill("solid", fgColor="F7F7F7")
            spec = spec_map.get((page, section, key))
            if spec:
                dv_rows[spec["kind"]].append(row_idx)
        row_idx += 1

    widths = [6, 12, 14, 14, 34, 38, 62]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "E3"

    # ④ 数据验证（下拉）
    if dv_rows["sort"]:
        dv = DataValidation(
            type="list", formula1='"' + ",".join(SORT_CHOICES) + '"',
            allow_blank=True, showErrorMessage=True,
            promptTitle="怎么填", prompt="三选一：目标合计降序 / 实际金额降序 / 达成率降序",
        )
        for r in dv_rows["sort"]:
            dv.add(f"E{r}")
        ws.add_data_validation(dv)
    if dv_rows["int"]:
        dv = DataValidation(
            type="whole", operator="greaterThanOrEqual", formula1="0",
            allow_blank=True, showErrorMessage=True,
            promptTitle="怎么填", prompt="整数 ≥ 0；0 = 不限（显示全部）",
        )
        for r in dv_rows["int"]:
            dv.add(f"E{r}")
        ws.add_data_validation(dv)

    # ⑤ 优先展示 / 客户筛选：不做下拉（客户名由使用者自己填），只给单元格加输入提示
    if dv_rows["names"]:
        dv = DataValidation(
            type="none", allow_blank=True, showErrorMessage=False,
            promptTitle="怎么填",
            prompt=("手填客户名：① 母公司组名（如 广汽系）② 客户全称（照「销售归属」sheet 写）；"
                    "一个客户一行，可多行"),
        )
        for r in dv_rows["names"]:
            dv.add(f"E{r}")
        ws.add_data_validation(dv)
    return ws


def refresh_rules_sheet(excel_path: Path | str | None = None,
                        cfg_path: Path | str | None = None) -> Path:
    """只刷新 Excel 里的「展示规则」sheet，保留其他 sheet 原样"""
    import openpyxl as _xl

    excel_path = Path(excel_path or EXCEL_PATH)
    cfg_path = Path(cfg_path or DISPLAY_RULES_CFG)
    if not excel_path.exists():
        raise FileNotFoundError(f"未找到配置编辑器: {excel_path}")
    rules = json.loads(cfg_path.read_text(encoding="utf-8"))
    wb = _xl.load_workbook(excel_path)
    attach_rules_sheet(wb, rules)
    wb.save(excel_path)
    return excel_path
