# Author: naohua168 <bai_bai168@qq.com>
"""配置编辑器 — 统一的表格视觉规范（2026-09-28）

所有 sheet 共用同一套配色与结构，避免各页风格不一：

    ┌─ 横幅（第 1 行，合并整行）：这张表干什么、只改哪一列
    ├─ 表头（第 2 行，深蓝底白字加粗居中）
    └─ 数据区（第 3 行起）
         · 可编辑列 → 浅黄底 (FFF9E6)
         · 只读/参考列 → 浅灰底 (F7F7F7)
         · 分组斑马纹 → 每 N 行浅蓝底 (F7FBFF)，用于「销售归属」按母公司分组

同时提供 `locate_header_row()`：解析器用它在开头若干行里定位真正的表头行，
从而兼容「有横幅」与「无横幅（历史文件）」两种布局。

另提供工作簿级的三个工具（2026-10-10，为"生成版与编辑版一致 / 生成结果字节稳定"）：
    new_workbook()         建簿：默认字体对齐 Excel 中文环境 + 固定文档属性
    save_workbook(wb, path) 保存：固定文档属性 + 规范化 zip（同内容两次保存字节一致）
    canonicalize_workbook(path) 原地无损规范化：空字符串清成真空 + 上述两步（保留样式/列宽/行高/冻结/筛选）
"""
from __future__ import annotations

import re
from datetime import datetime
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

try:
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
except ImportError:  # pragma: no cover
    raise SystemExit("缺少 openpyxl，请先安装: pip install openpyxl")

# 默认字体：Excel 中文环境存盘后单元格字体是「宋体」，生成器用 openpyxl 默认的 Calibri
# 会与编辑版对不上（14662 格字体差异）。统一成宋体，两边一致。
WB_FONT_NAME = "宋体"
WB_FONT_SIZE = 11
WB_EPOCH = datetime(2026, 1, 1, 0, 0, 0)   # 固定时间戳（否则每次生成的文件字节都不同）
WB_AUTHOR = "Visual Dashboard System"

# ── 配色（与看板主色一致）──
COLOR_PRIMARY = "1F4E78"        # 表头深蓝
COLOR_BANNER_BG = "EAF3FF"      # 横幅浅蓝
COLOR_SECTION_BG = "F2F7FF"     # 区块/段标题浅蓝
COLOR_EDITABLE_BG = "FFF9E6"    # 可编辑列（浅黄）
COLOR_READONLY_BG = "F7F7F7"    # 只读/参考列（浅灰）
COLOR_BAND_BG = "F7FBFF"        # 斑马纹（浅蓝）
COLOR_BORDER = "B0B7C3"
COLOR_SECTION_TITLE = "1F4E78"

# 每个 sheet 的标签页颜色（一眼区分）
TAB_COLORS = {
    "时间配置": "1F4E78",
    "展示规则": "7030A0",
    "销售归属": "2E7D32",
    "KPI指标": "C55A11",
    "字段映射": "00838F",
    "说明": "808080",
}


def thin_border() -> Border:
    side = Side(style="thin", color=COLOR_BORDER)
    return Border(left=side, right=side, top=side, bottom=side)


def locate_header_row(rows: list[tuple], required: tuple[str, ...],
                      max_scan: int = 4) -> int:
    """在前 max_scan 行里找出「同时包含 required 全部列名」的行号（0-based）

    Returns:
        表头所在行下标；找不到返回 -1（调用方给出中文报错）
    """
    for i, row in enumerate(rows[:max_scan]):
        cells = {str(v).strip() for v in row if v is not None}
        if all(c in cells for c in required):
            return i
    return -1


def banner(ws, text: str, ncols: int, row: int = 1, height: int = 26) -> None:
    """第 1 行横幅：这张表怎么用（合并整行，浅蓝底 + 深蓝粗体）"""
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=ncols)
    c = ws.cell(row=row, column=1, value=text)
    c.fill = PatternFill("solid", fgColor=COLOR_BANNER_BG)
    c.font = Font(name=WB_FONT_NAME, bold=True, size=11, color=COLOR_PRIMARY)
    c.alignment = Alignment(vertical="center", horizontal="left")
    ws.row_dimensions[row].height = height


def header_row(ws, headers: list[str], row: int = 2, height: int = 22) -> None:
    """表头行：深蓝底 / 白字 / 加粗 / 居中 / 边框"""
    for col, h in enumerate(headers, 1):
        c = ws.cell(row=row, column=col, value=h)
        c.fill = PatternFill("solid", fgColor=COLOR_PRIMARY)
        c.font = Font(name=WB_FONT_NAME, bold=True, color="FFFFFF", size=11)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = thin_border()
    ws.row_dimensions[row].height = height


def section_row(ws, row: int, text: str, ncols: int,
                first_col: int = 1) -> None:
    """区块/段标题行：浅蓝底 + 深蓝粗体（合并到末列）"""
    ws.merge_cells(start_row=row, start_column=first_col, end_row=row, end_column=ncols)
    for col in range(first_col, ncols + 1):
        ws.cell(row=row, column=col).border = thin_border()
    c = ws.cell(row=row, column=first_col, value=text)
    c.fill = PatternFill("solid", fgColor=COLOR_SECTION_BG)
    c.font = Font(name=WB_FONT_NAME, bold=True, size=11, color=COLOR_SECTION_TITLE)
    c.alignment = Alignment(vertical="center", horizontal="left")
    ws.row_dimensions[row].height = 20


def data_cell(ws, row: int, col: int, value, editable: bool = False,
              readonly: bool = False, wrap: bool = False,
              center: bool = False, band: bool = False):
    """数据单元格：统一边框 + 可选底色（可编辑浅黄 / 只读浅灰 / 斑马纹浅蓝）"""
    c = ws.cell(row=row, column=col, value=value)
    c.border = thin_border()
    c.alignment = Alignment(vertical="center", wrap_text=wrap,
                            horizontal="center" if center else "left")
    if editable:
        c.fill = PatternFill("solid", fgColor=COLOR_EDITABLE_BG)
    elif readonly:
        c.fill = PatternFill("solid", fgColor=COLOR_READONLY_BG)
    elif band:
        c.fill = PatternFill("solid", fgColor=COLOR_BAND_BG)
    return c


def set_widths(ws, widths: list[float]) -> None:
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def finish(ws, freeze: str | None = None, autofilter: str | None = None,
           tab_color: str | None = None) -> None:
    """收尾：冻结窗格 / 自动筛选 / 标签页颜色"""
    if freeze:
        ws.freeze_panes = freeze
    if autofilter:
        ws.auto_filter.ref = autofilter
    if tab_color:
        ws.sheet_properties.tabColor = tab_color


def fit_row_height(ws, row: int, texts, base: float = 15.0) -> None:
    """按"文本长度 ÷ 列宽"估算换行行数，给这一行设置行高。

    为什么需要：openpyxl 没法触发 Excel 的"自动适应行高"，长说明文本开着 wrap 却只有
    默认行高时会被截断（编辑版里 Excel 已经自适应过，行高较高）。生成器自己算一个，
    保证"说明 / 可选值"这类长文本能完整显示。

    texts: [(文本, 该列宽度), ...]（只传 wrap_text=True 的列）
    估算偏保守（中文按每字 1 字符宽），宁可略高不矮；最多按 4 行计，避免个别超长文本把行撑爆。
    """
    lines = 1
    for text, width in texts:
        s = "" if text is None else str(text)
        if not s.strip():
            continue
        per = max(int(width) - 2, 4)          # 列宽单位≈字符数，留出边框/内边距余量
        lines = max(lines, -(-len(s) // per))
    if lines > 1:
        ws.row_dimensions[row].height = round(base * min(lines, 4), 1)
    return None


# ──────────────────────────────────────────────────────────────
# 工作簿级工具（2026-10-10）：默认字体 / 固定属性 / 字节稳定的保存 / 原地规范化
# ──────────────────────────────────────────────────────────────
def stamp_workbook(wb, epoch: datetime | None = None) -> None:
    """把文档属性写成固定值。

    openpyxl 默认把 created/modified 写成"当前时间"，于是同一份配置每次生成的文件
    内容一样、sha256 却不同 —— 既做不了"生成版 vs 编辑版字节一致"的验收，
    也让版本管理噪声大。固定作者 + 固定时间戳后，同一份内容两次保存字节一致。
    """
    p = wb.properties
    t = epoch or WB_EPOCH
    p.creator = WB_AUTHOR
    p.lastModifiedBy = WB_AUTHOR
    p.created = t
    p.modified = t
    return None


def new_workbook():
    """新建工作簿：默认字体对齐编辑版（宋体），并预置固定文档属性。

    注意生效方式：openpyxl 新建单元格取的是**字体表第 0 项**（fontId=0），
    只改「Normal」命名样式不管用（实测仍是 Calibri）—— 两者都改才稳。
    """
    wb = openpyxl.Workbook()
    wb._named_styles["Normal"].font = Font(name=WB_FONT_NAME, size=WB_FONT_SIZE)
    wb._fonts[0] = Font(name=WB_FONT_NAME, size=WB_FONT_SIZE)
    stamp_workbook(wb)
    return wb


def canonicalize_zip(path, epoch: datetime | None = None) -> None:
    """把 xlsx（本质是个 zip）重写成"确定性 zip"：条目按名排序 + 固定时间戳。

    两处不确定性都要消掉：
      1. 每个 zip 条目带的是"保存时刻" → 固定成 1980-01-01
      2. docProps/core.xml 里的 dcterms:modified —— openpyxl **在保存时会强制改写成当前时间**
         （stamp_workbook 设了也没用）→ 这里把 core.xml 的时间戳一起钉死
    xlsx 读取方不关心条目顺序与时间戳，重写后内容完全等价。
    """
    stamp = (epoch or WB_EPOCH).strftime("%Y-%m-%dT%H:%M:%SZ").encode()
    pat = re.compile(rb"(<dcterms:(?:created|modified)[^>]*>)[^<]*(</dcterms:(?:created|modified)>)")

    src = ZipFile(path, "r")
    items = [(i.filename, src.read(i.filename)) for i in src.infolist()]
    src.close()
    items.sort(key=lambda kv: kv[0])
    with ZipFile(path, "w", ZIP_DEFLATED) as out:
        for name, data in items:
            if name == "docProps/core.xml":
                data = pat.sub(lambda m: m.group(1) + stamp + m.group(2), data)
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0
            info.create_system = 0
            out.writestr(info, data)
    return None


def save_workbook(wb, path) -> None:
    """保存工作簿：固定文档属性 + 规范化 zip → 同一份内容两次保存字节一致"""
    stamp_workbook(wb)
    wb.save(path)
    canonicalize_zip(path)
    return None


def clear_blank_strings(wb) -> int:
    """把「空字符串单元格」清成真空单元格，返回清理格数。

    Excel 存过盘的文件里，空单元格会以"空共享字符串"形式存在，读出来是 `""`；
    代码生成的是真真空。两者显示与解析完全等价，但会让"生成版 vs 编辑版"的比对出现
    几千处假差异 —— 统一成真空。只动值，不动样式/列宽/行高/冻结/筛选。
    """
    blanks = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value == "":
                    c.value = None
                    blanks += 1
    return blanks


def canonicalize_workbook(path) -> dict:
    """原地无损规范化编辑版工作簿（保留样式/列宽/行高/冻结/筛选，只动两处元数据）：

      1. 空字符串单元格 → 真真空单元格（见 clear_blank_strings）
      2. 固定文档属性 + 规范化 zip → 之后每次保存字节一致

    返回统计（供命令行打印）。
    """
    wb = openpyxl.load_workbook(path)
    blanks = clear_blank_strings(wb)
    save_workbook(wb, path)
    return {"blank_cleared": blanks, "sheets": len(wb.worksheets)}
