# Author: naohua168 <bai_bai168@qq.com>
"""配置编辑器「字段映射」sheet — 清洗列名映射的 Excel 编辑层

场景：源文件列名变化导致清洗报 KeyError 时，不必改 JSON/代码，
直接在 `config/配置编辑器.xlsx` 的「字段映射」sheet 里增删候选列名即可
（`run_all.bat` 第①步配置同步会自动写回 cleaning_config.json）。

读写约定：
  - 一行 = 一个来源的一个标准字段
  - 列   = 数据源 | 来源 | 标准字段 | 候选1..候选N | 当前命中(只读) | 说明
  - 写回时**只替换** `数据源.<来源>.列映射`，其余键（文件名/Sheet/引擎/金额除数/
    过客户白名单/事业部固定/法人主体/无表头/列位置/说明）原样保留
  - 「当前命中(只读)」列写回时被忽略，仅由 `--init-map` 从
    `logs/column_hits_*.txt`（清洗时自动落盘）回填

安全措施：写回前备份到 `logs/cleaning_config.bak_*.json`，写后 `json.loads` 自检。
"""
from __future__ import annotations

import datetime
import json
import re
import shutil
from pathlib import Path

try:
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
except ImportError:  # pragma: no cover
    raise SystemExit("缺少 openpyxl，请先安装: pip install openpyxl")

BASE_DIR = Path(__file__).parent.parent
EXCEL_PATH = BASE_DIR / "config" / "配置编辑器.xlsx"
CLEANING_CFG = BASE_DIR / "config" / "清洗配置" / "cleaning_config.json"
HIT_LOG_DIR = BASE_DIR / "logs"
BACKUP_DIR = BASE_DIR / "logs"

MAP_SHEET_NAME = "字段映射"
KEY_COLS = ("数据源", "来源", "标准字段")
HIT_COL = "当前命中(只读)"
NOTE_COL = "说明"
CAND_MAX = 5  # 预置候选列数（可自行插入「候选6/7…」，解析按数字顺序动态读取）
MAP_HEADERS = list(KEY_COLS) + [f"候选{i}" for i in range(1, CAND_MAX + 1)] + [HIT_COL, NOTE_COL]

_CAND_RE = re.compile(r"^候选(\d+)$")
_HDR_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\s+\[(.+?)\]\s+列名命中$")
_HIT_RE = re.compile(r"^\s+(?P<std>\S+)\s+<-\s+(?P<actual>.*?)(?:\s{2,}(?:（|⚠️).*)?$")

# 来源 → 命中日志里的来源标签（同一来源的 收入/回款 列映射是共享的，
# 命中标签却按 收入/回款 分开打印，故一个来源可能对应多个标签）
HIT_LABELS: dict[tuple[str, str], list[str]] = {
    ("财务端", "收入"): ["财务端收入"],
    ("财务端", "回款"): ["财务端回款"],
    ("财务端", "广东公司"): ["广东收入", "广东回款"],
    ("财务端", "湖南公司"): ["湖南收入", "湖南回款"],
    ("财务端", "南方韶关"): ["南方韶关收入", "南方韶关回款"],
    ("运营端", "收入"): ["运营端收入"],
    ("运营端", "回款"): ["运营端回款"],
}


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


def _iter_sources(cfg: dict):
    """遍历配置中的数据源：(数据源名, 来源名, 来源配置dict)"""
    for src, obj in (cfg.get("数据源") or {}).items():
        if not isinstance(obj, dict):
            continue
        for name, spec in obj.items():
            if not isinstance(spec, dict) or "列映射" not in spec:
                continue
            yield src, name, spec


# ──────────────────────────────────────────────────────────────
# 读取「字段映射」sheet → 列映射 dict
# ──────────────────────────────────────────────────────────────
def excel_to_column_mapping(sheet, cfg: dict) -> tuple[dict, list[str]]:
    """读取 sheet → ({数据源: {来源: {标准字段: [候选...]}}}, warnings)

    Raises:
        ValueError: 校验失败（非法数据源/来源/字段、候选为空或重复、缺少来源已有字段）
    """
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        raise ValueError(f"「{MAP_SHEET_NAME}」sheet 为空")
    headers = [_cell(h) for h in rows[0]]

    missing = [c for c in KEY_COLS if c not in headers]
    if missing:
        raise ValueError(f"「{MAP_SHEET_NAME}」表头缺少必需列 {missing}；实际表头: {headers}")

    i_src, i_name, i_field = (headers.index(c) for c in KEY_COLS)
    cand_cols = sorted(
        (int(m.group(1)), i) for i, h in enumerate(headers) if (m := _CAND_RE.match(h))
    )
    if not cand_cols:
        raise ValueError(f"「{MAP_SHEET_NAME}」未找到任何「候选N」列；实际表头: {headers}")

    # 合法来源 / 每个来源已有字段
    valid: dict[tuple[str, str], set[str]] = {
        (src, name): {f for f in spec["列映射"] if not f.startswith("_")}
        for src, name, spec in _iter_sources(cfg)
    }
    global_fields = set().union(*valid.values()) if valid else set()

    mapping: dict[str, dict[str, dict[str, list[str]]]] = {}
    seen: set[tuple[str, str, str]] = set()
    warnings: list[str] = []

    for row in rows[1:]:
        if row is None or all(v is None or _cell(v) == "" for v in row):
            continue
        def at(idx: int) -> str:
            return _cell(row[idx]) if idx < len(row) else ""

        src, name, field = at(i_src), at(i_name), at(i_field)
        if not src and not name and not field:
            continue
        if (src, name) not in valid:
            raise ValueError(
                f"「{MAP_SHEET_NAME}」存在未知来源: 数据源={src!r} 来源={name!r}；"
                f"可选: {sorted(valid)}"
            )
        if not field:
            raise ValueError(f"「{MAP_SHEET_NAME}」{src}/{name} 有行缺少「标准字段」")
        if field not in global_fields:
            raise ValueError(
                f"「{MAP_SHEET_NAME}」未知标准字段: {field!r}（{src}/{name}）；可选: {sorted(global_fields)}"
            )
        key = (src, name, field)
        if key in seen:
            raise ValueError(f"「{MAP_SHEET_NAME}」重复行: {src}/{name}/{field}")
        seen.add(key)

        cands: list[str] = []
        for _, i in cand_cols:
            v = at(i)
            if not v:
                continue
            if "\n" in v or "\t" in v:
                raise ValueError(f"「{MAP_SHEET_NAME}」{src}/{name}/{field} 候选含换行/制表符: {v!r}")
            if v in cands:
                raise ValueError(f"「{MAP_SHEET_NAME}」{src}/{name}/{field} 候选重复: {v!r}")
            cands.append(v)
        if not cands:
            raise ValueError(f"「{MAP_SHEET_NAME}」{src}/{name}/{field} 候选为空（至少填 1 个候选列名）")

        mapping.setdefault(src, {}).setdefault(name, {})[field] = cands

    if not mapping:
        raise ValueError(f"「{MAP_SHEET_NAME}」没有任何数据行")

    # 每个来源必须覆盖其原有字段（不允许静默删除，否则清洗会 KeyError）
    for (src, name), fields in valid.items():
        got = set(mapping.get(src, {}).get(name, {}))
        lost = fields - got
        if lost:
            raise ValueError(
                f"「{MAP_SHEET_NAME}」{src}/{name} 缺少原有标准字段: {sorted(lost)}（不允许删除）\n"
                f"    若这些字段是刚在 JSON 里新增的，请先刷新 sheet：\n"
                f"      python scripts/config_excel_to_json.py --init-map\n"
                f"    （只刷新「{MAP_SHEET_NAME}」sheet，再用 run_all.bat 同步）"
            )
        added = got - fields
        if added:
            warnings.append(f"{src}/{name} 新增字段 {sorted(added)} —— 请确认源文件里确实存在这些列，否则清洗会报 KeyError")

    return mapping, warnings


# ──────────────────────────────────────────────────────────────
# 写回 cleaning_config.json（只替换 列映射，其余键原样保留）
# ──────────────────────────────────────────────────────────────
def update_column_mapping(mapping: dict, dry_run: bool = False,
                          cfg_path: Path | str | None = None,
                          backup_dir: Path | str | None = None) -> tuple[dict, list[str]]:
    """把列映射写回 cleaning_config.json

    Returns:
        (新配置 dict, 变更的「数据源.来源」列表)
    """
    cfg_path = Path(cfg_path or CLEANING_CFG)
    backup_dir = Path(backup_dir or BACKUP_DIR)
    if not cfg_path.exists():
        raise FileNotFoundError(f"cleaning_config.json 不存在: {cfg_path}")

    text = cfg_path.read_text(encoding="utf-8")
    cfg = json.loads(text)

    changed: list[str] = []
    for src, sources in mapping.items():
        for name, fields in sources.items():
            old = cfg["数据源"][src][name].get("列映射", {})
            if old != fields:
                changed.append(f"{src}.{name}")
            cfg["数据源"][src][name]["列映射"] = fields

    new_text = json.dumps(cfg, ensure_ascii=False, indent=2) + "\n"
    json.loads(new_text)  # 写前自检：确保 JSON 有效

    if dry_run:
        return cfg, changed

    # 写前备份（放到 logs/，不进 git）
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(cfg_path, backup_dir / f"cleaning_config.bak_{stamp}.json")
    cfg_path.write_text(new_text, encoding="utf-8")
    return cfg, changed


# ──────────────────────────────────────────────────────────────
# 命中日志 → 「当前命中」列
# ──────────────────────────────────────────────────────────────
def read_latest_hits(log_dir: Path | str | None = None) -> dict[str, dict[str, str]]:
    """解析 logs/column_hits_*.txt → {来源标签: {标准字段: 命中的列名}}

    同一来源出现多次时取最后一次（按文件名/内容顺序，后者覆盖前者）。
    """
    log_dir = Path(log_dir or HIT_LOG_DIR)
    result: dict[str, dict[str, str]] = {}
    if not log_dir.is_dir():
        return result
    for path in sorted(log_dir.glob("column_hits_*.txt")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        cur: str | None = None
        for line in lines:
            m = _HDR_RE.match(line.strip())
            if m:
                cur = m.group(1).strip()
                result.setdefault(cur, {})
                continue
            if cur is None:
                continue
            m2 = _HIT_RE.match(line)
            if m2:
                result[cur][m2.group("std")] = m2.group("actual").strip()
    return result


def _hit_text(labels: list[str], field: str, hits: dict[str, dict[str, str]]) -> str:
    """把多个命中标签的值合成一个展示串（收入/回款命中不同列时都能看到）"""
    vals: list[str] = []
    for lb in labels:
        v = hits.get(lb, {}).get(field)
        if v and v not in vals:
            vals.append(v)
    return " / ".join(vals)


# ──────────────────────────────────────────────────────────────
# 生成 sheet（--init / --init-map）
# ──────────────────────────────────────────────────────────────
def build_mapping_rows(cfg: dict, hits: dict[str, dict[str, str]] | None = None) -> list[list]:
    """按 JSON 顺序生成 sheet 行（含表头行）"""
    hits = hits or {}
    rows: list[list] = [list(MAP_HEADERS)]
    for src, name, spec in _iter_sources(cfg):
        labels = HIT_LABELS.get((src, name), [])
        for field, cands in spec["列映射"].items():
            if field.startswith("_"):
                continue
            cands = [str(c) for c in cands]
            hit = _hit_text(labels, field, hits)
            notes: list[str] = []
            if len(cands) == 1:
                notes.append("⚠️ 唯一候选（源表改名即中断）")
            if hit and len(cands) > 1 and hit.split(" / ")[0] not in ("", cands[0]):
                try:
                    idx = cands.index(hit.split(" / ")[0]) + 1
                    notes.append(f"⚠️ 当前靠第 {idx}/{len(cands)} 候选命中")
                except ValueError:
                    pass
            if not hit:
                notes.append("（暂无命中记录，跑一次清洗后 --init-map 可回填）")
            row = [src, name, field] + cands + [""] * (CAND_MAX - len(cands))
            rows.append(row[:3 + CAND_MAX] + [hit, "；".join(notes)])
    return rows


def attach_mapping_sheet(wb, cfg: dict, hits: dict | None = None):
    """在 workbook 中创建/替换「字段映射」sheet（原地修改，需调用方 save）"""
    if MAP_SHEET_NAME in wb.sheetnames:
        del wb[MAP_SHEET_NAME]
    ws = wb.create_sheet(MAP_SHEET_NAME)

    thin = Side(style="thin", color="B0B7C3")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(bold=True, color="FFFFFF", size=11)

    for row in build_mapping_rows(cfg, hits):
        ws.append(row)

    for col in range(1, len(MAP_HEADERS) + 1):
        c = ws.cell(row=1, column=col)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = border

    for r in range(2, ws.max_row + 1):
        for col in range(1, len(MAP_HEADERS) + 1):
            c = ws.cell(row=r, column=col)
            c.border = border
            c.alignment = Alignment(vertical="center", wrap_text=(col == len(MAP_HEADERS)))
            if MAP_HEADERS[col - 1] in KEY_COLS:
                c.fill = PatternFill("solid", fgColor="F2F7FF")
            elif MAP_HEADERS[col - 1] == HIT_COL:
                c.fill = PatternFill("solid", fgColor="F5F5F5")

    widths = [10, 12, 12] + [22] * CAND_MAX + [24, 46]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "D2"
    return ws


def refresh_mapping_sheet(excel_path: Path | str | None = None,
                          cfg_path: Path | str | None = None) -> Path:
    """只刷新 Excel 里的「字段映射」sheet，保留其他 sheet 原样"""
    import openpyxl

    excel_path = Path(excel_path or EXCEL_PATH)
    cfg_path = Path(cfg_path or CLEANING_CFG)
    if not excel_path.exists():
        raise FileNotFoundError(f"未找到配置编辑器: {excel_path}")

    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    wb = openpyxl.load_workbook(excel_path)
    attach_mapping_sheet(wb, cfg, read_latest_hits())
    wb.save(excel_path)
    return excel_path
