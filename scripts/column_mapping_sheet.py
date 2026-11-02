# Author: naohua168 <bai_bai168@qq.com>
"""配置编辑器「字段映射」sheet — 清洗列名映射的 Excel 编辑层

场景：源文件列名变化导致清洗报 KeyError 时，不必改 JSON/代码，
直接在 `config/配置编辑器.xlsx` 的「字段映射」sheet 里增删候选列名即可
（`run_all.bat` 第①步配置同步会自动写回 cleaning_config.json）。

读写约定：
  - 一行 = 一个来源的一个标准字段
  - 列   = 数据源 | 来源 | 标准字段 | 候选列名 | 必填取值 | 当前命中(只读) | 说明
  - **候选与取值都用「/」分隔**（2026-10-29 用户口径），如
    `创建时间/创建日期/审核日期`、`已审核/已收款`
  - 候选列名上限 **3 个**；超过 3 个直接报错，提示删减（不做静默截断）
  - 列名本身含半角「/」时写成 `\\/`（转义），解析后还原为字面量 `/`
  - 「必填取值」= 该字段的**取值约束**，默认落到 `保留取值.{字段}`（如 单据状态=已审核、
    委托类型=外部结算）；多个值 OR，多个字段之间 AND；清空 = 取消该字段过滤
  - 三个例外（写回同级的平铺列表键，见 VALUE_KEYS）：
    · `排除标记` → `排除标记值`（如 √，命中即整行剔除）
    · `部门`     → `事业部取值`（只取这些事业部；映射表里有则先归一，没有按字面比；空 = 不限制）
    · `内部交易` → `内部交易标记值`（如 是，命中即整行剔除；空 = 不过滤）
  - 写回时替换 `数据源.<来源>.列映射` 与 `数据源.<来源>.保留取值`，其余键（文件名/
    Sheet/引擎/金额除数/过客户白名单/事业部固定/法人主体/无表头/列位置/说明）原样保留
  - 「当前命中(只读)」列写回时被忽略，仅由 `--init-map` 从
    `logs/column_hits_*.txt`（清洗时自动落盘）回填
  - 向后兼容：历史工作簿的「候选1..候选N」多列布局、以及没有「必填取值」列的文件
    仍可解析（多列布局解析时截断到 3 个并给出告警）

安全措施：写回前备份到 `logs/cleaning_config.bak_*.json`，写后 `json.loads` 自检。
"""
from __future__ import annotations

import datetime
import json
import re
import shutil
from pathlib import Path

try:
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
except ImportError:  # pragma: no cover
    raise SystemExit("缺少 openpyxl，请先安装: pip install openpyxl")

# 统一样式（横幅/表头/可编辑底色/只读灰底/表头行定位）
try:
    from sheet_style import (
        TAB_COLORS, banner, data_cell, finish, fit_row_height, header_row,
        locate_header_row, save_workbook, set_widths,
    )
except ImportError:  # 以包形式导入时（如单元测试）
    from scripts.sheet_style import (  # type: ignore[no-redef]
        TAB_COLORS, banner, data_cell, finish, fit_row_height, header_row,
        locate_header_row, save_workbook, set_widths,
    )

BASE_DIR = Path(__file__).parent.parent


def _rel(p) -> str:
    """路径 → 相对项目根显示（与 engine.core.utils.rel_path 同口径；本模块不依赖 engine）"""
    try:
        return str(Path(p).relative_to(BASE_DIR))
    except (ValueError, TypeError):
        return str(p)


EXCEL_PATH = BASE_DIR / "config" / "配置编辑器.xlsx"
CLEANING_CFG = BASE_DIR / "config" / "清洗配置" / "cleaning_config.json"
HIT_LOG_DIR = BASE_DIR / "logs"
BACKUP_DIR = BASE_DIR / "logs"

MAP_SHEET_NAME = "字段映射"
KEY_COLS = ("数据源", "来源", "标准字段")
CAND_COL = "候选列名"       # 多个候选用「/」分隔（最多 3 个）；列名含 / 时写 \/
VALUE_COL = "必填取值"      # 保留取值（单据状态=已审核 / 委托类型=外部结算 …），多值用「/」分隔
HIT_COL = "当前命中(只读)"
NOTE_COL = "说明"
CAND_MAX = 3  # 候选列上限（2026-10-29 用户口径：每字段最多 3 个候选）
SEP = "/"
MAP_HEADERS = list(KEY_COLS) + [CAND_COL, VALUE_COL, HIT_COL, NOTE_COL]

# 「必填取值」写回哪个配置键 + 方向（保留=命中即留；剔除=命中即删；事业部=只取这些事业部）
#   默认落到 `保留取值`（{字段: [值...]}）；其余落到同级的平铺列表键：
#     排除标记 → 排除标记值（命中即整行剔除）
#     部门     → 事业部取值（只取这些事业部；映射表里有就先归一，没有就按字面比）
#     内部交易 → 内部交易标记值（命中即整行剔除）
VALUE_KEYS: dict[str, tuple[str, str]] = {
    "排除标记": ("排除标记值", "剔除"),
    "部门": ("事业部取值", "事业部"),
    "内部交易": ("内部交易标记值", "内置剔除"),
}
FLAT_VALUE_KEYS = {"排除标记值", "事业部取值", "内部交易标记值"}

# 各平铺键在缺省时的默认值（配置里没有该键 = 用默认；显式空列表 = 不限制）
FLAT_DEFAULTS: dict[str, list[str]] = {
    "排除标记值": [],
    "内部交易标记值": ["是"],
}

# 日期类字段：时间范围在「时间配置」sheet 维护，这里不需要取值（留空即可）
TIME_FIELDS = {"日期", "收款日期"}

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


def dept_value_names(cfg: dict) -> list[str]:
    """「部门」字段的可选值（事业部全称）—— 来自 部门事业部映射.json"""
    rel = (cfg.get("映射文件") or {}).get("部门事业部映射")
    if not rel:
        return []
    try:
        raw = json.loads((BASE_DIR / rel).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    names: list[str] = []
    for key in ("income_mapping", "payment_mapping"):
        for name in (raw.get(key) or {}):
            name = str(name)
            if not name.startswith("_") and name not in names:
                names.append(name)
    return names


def split_items(raw: str) -> list[str]:
    """按「/」拆分候选/取值；`\\/` 视为列名里的字面量斜杠

    兼容旧写法：也接受「、」「,」「；」「;」作为分隔符（生成时统一写「/」）。
    """
    if not raw:
        return []
    parts = re.split(r"(?<!\\)[/、,，;；]", raw)
    out: list[str] = []
    for p in parts:
        v = p.replace("\\/", "/").strip()
        if v:
            out.append(v)
    return out


def join_items(items: list[str]) -> str:
    """把候选/取值拼成「a / b / c」；列名里的半角斜杠转义为 `\\/`"""
    return " / ".join(str(i).replace("/", "\\/") for i in items)


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
    # 兼容带顶部横幅的布局：表头行在 1~4 行内按必需列名定位；
    # 找不到就按「第 1 行即表头」处理（历史文件），交给下面的缺列校验报错
    hi = max(locate_header_row(rows, KEY_COLS, max_scan=4), 0)
    headers = [_cell(h) for h in rows[hi]]
    rows = rows[hi:]

    missing = [c for c in KEY_COLS if c not in headers]
    if missing:
        raise ValueError(f"「{MAP_SHEET_NAME}」表头缺少必需列 {missing}；实际表头: {headers}")

    i_src, i_name, i_field = (headers.index(c) for c in KEY_COLS)
    # 新版：单列「候选列名」用「/」分隔；旧版：候选1..候选N 多列（解析时截断到 CAND_MAX）
    i_cand = headers.index(CAND_COL) if CAND_COL in headers else None
    cand_cols = sorted(
        (int(m.group(1)), i) for i, h in enumerate(headers) if (m := _CAND_RE.match(h))
    )
    if i_cand is None and not cand_cols:
        raise ValueError(
            f"「{MAP_SHEET_NAME}」未找到「{CAND_COL}」列或任何「候选N」列；实际表头: {headers}"
        )

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

        raw_cand = at(i_cand) if i_cand is not None else ""
        if "\n" in raw_cand or "\t" in raw_cand:
            raise ValueError(
                f"「{MAP_SHEET_NAME}」{src}/{name}/{field} 候选含换行/制表符: {raw_cand!r}"
            )
        if i_cand is not None:
            cands = split_items(raw_cand)
            if len(cands) > CAND_MAX:
                raise ValueError(
                    f"「{MAP_SHEET_NAME}」{src}/{name}/{field} 候选 {len(cands)} 个，超过上限 "
                    f"{CAND_MAX} 个：{raw_cand!r}\n    请删减（用「/」分隔，最多 {CAND_MAX} 个）"
                )
            if len(set(cands)) != len(cands):
                raise ValueError(
                    f"「{MAP_SHEET_NAME}」{src}/{name}/{field} 候选重复: {raw_cand!r}"
                )
        else:
            cands = []
            for _, i in cand_cols:
                v = at(i)
                if not v:
                    continue
                if "\n" in v or "\t" in v:
                    raise ValueError(
                        f"「{MAP_SHEET_NAME}」{src}/{name}/{field} 候选含换行/制表符: {v!r}"
                    )
                if v in cands:
                    raise ValueError(f"「{MAP_SHEET_NAME}」{src}/{name}/{field} 候选重复: {v!r}")
                cands.append(v)
            if len(cands) > CAND_MAX:
                warnings.append(
                    f"{src}/{name}/{field} 候选 {len(cands)} 个 → 按上限截断为前 {CAND_MAX} 个"
                )
                cands = cands[:CAND_MAX]
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


def excel_to_kept_values(sheet, cfg: dict) -> tuple[dict | None, list[str]]:
    """读取「必填取值」列 → ({数据源: {来源: {标准字段: [取值...]}}}, warnings)

    历史工作簿没有该列 → 返回 `(None, [])`，调用方据此**不改动**任何取值配置（向后兼容）。
    每个出现的字段都会返回（可能是空列表）——空列表表示「显式清空」（如 事业部取值=不限制）。

    Raises:
        ValueError: 未知来源/字段、取值含换行/制表符、同一字段取值重复
    """
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return None, []
    hi = max(locate_header_row(rows, KEY_COLS, max_scan=4), 0)
    headers = [_cell(h) for h in rows[hi]]
    if VALUE_COL not in headers:
        return None, []
    missing = [c for c in KEY_COLS if c not in headers]
    if missing:
        raise ValueError(f"「{MAP_SHEET_NAME}」表头缺少必需列 {missing}；实际表头: {headers}")
    rows = rows[hi:]
    i_src, i_name, i_field = (headers.index(c) for c in KEY_COLS)
    i_val = headers.index(VALUE_COL)

    valid: dict[tuple[str, str], set[str]] = {
        (src, name): {f for f in spec["列映射"] if not f.startswith("_")}
        for src, name, spec in _iter_sources(cfg)
    }

    kept: dict[str, dict[str, dict[str, list[str]]]] = {}
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
        if field not in valid[(src, name)]:
            raise ValueError(
                f"「{MAP_SHEET_NAME}」未知标准字段: {field!r}（{src}/{name}）；"
                f"可选: {sorted(valid[(src, name)])}"
            )
        raw = at(i_val)
        if "\n" in raw or "\t" in raw:
            raise ValueError(
                f"「{MAP_SHEET_NAME}」{src}/{name}/{field} 必填取值含换行/制表符: {raw!r}"
            )
        vals = split_items(raw)
        if len(set(vals)) != len(vals):
            raise ValueError(f"「{MAP_SHEET_NAME}」{src}/{name}/{field} 必填取值重复: {raw!r}")
        # 空列表也返回：表示用户显式清空（如 事业部取值=不限制 / 内部交易=不过滤）
        kept.setdefault(src, {}).setdefault(name, {})[field] = vals
    return kept, []


# ──────────────────────────────────────────────────────────────
# 写回 cleaning_config.json（替换 列映射 / 保留取值，其余键原样保留）
# ──────────────────────────────────────────────────────────────
def update_column_mapping(mapping: dict, dry_run: bool = False,
                          cfg_path: Path | str | None = None,
                          backup_dir: Path | str | None = None,
                          kept_values: dict | None = None) -> tuple[dict, list[str]]:
    """把列映射（以及可选的保留取值）写回 cleaning_config.json

    Args:
        kept_values: `{数据源: {来源: {标准字段: [取值...]}}}`；`None` = 不改动
                     `保留取值`（历史工作簿无「必填取值」列时的向后兼容路径）

    Returns:
        (新配置 dict, 变更项列表，如 "财务端.收入" / "财务端.收入.保留取值")
    """
    cfg_path = Path(cfg_path or CLEANING_CFG)
    backup_dir = Path(backup_dir or BACKUP_DIR)
    if not cfg_path.exists():
        raise FileNotFoundError(f"cleaning_config.json 不存在: {_rel(cfg_path)}")

    text = cfg_path.read_text(encoding="utf-8")
    cfg = json.loads(text)

    changed: list[str] = []
    for src, sources in mapping.items():
        for name, fields in sources.items():
            old = cfg["数据源"][src][name].get("列映射", {})
            if old != fields:
                changed.append(f"{src}.{name}")
            cfg["数据源"][src][name]["列映射"] = fields

    # 必填取值（保留取值 / 排除标记值）；kept_values=None 时不动（历史工作簿无该列）
    if kept_values is not None:
        for src, sources in mapping.items():
            for name in sources:
                target = cfg["数据源"][src][name]
                raw = kept_values.get(src, {}).get(name, {}) or {}
                new_kept: dict[str, list[str]] = {}
                new_flat: dict[str, list[str]] = {}
                for field, vals in raw.items():
                    key, _ = VALUE_KEYS.get(field, ("保留取值", "保留"))
                    if key in FLAT_VALUE_KEYS:
                        # 平铺键即使是空列表也要写（显式清空 = 不限制/不过滤）
                        new_flat[key] = list(vals)
                    elif vals:
                        new_kept[field] = list(vals)

                old_kept = target.get("保留取值") or {}
                if old_kept != new_kept:
                    changed.append(f"{src}.{name}.保留取值")
                    if new_kept:
                        target["保留取值"] = new_kept
                    else:
                        target.pop("保留取值", None)

                for key in sorted(set(new_flat) | (set(target) & FLAT_VALUE_KEYS)):
                    if key in new_flat:
                        vals = list(new_flat[key])
                        if target.get(key) == vals:
                            continue
                        target[key] = vals
                        changed.append(f"{src}.{name}.{key}")
                    elif key in target:  # 本来源没有该字段 → 清掉历史残留
                        target.pop(key)
                        changed.append(f"{src}.{name}.{key}")

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
        kept = spec.get("保留取值") or {}
        for field, cands in spec["列映射"].items():
            if field.startswith("_"):
                continue
            all_cands = [str(c) for c in cands]
            cands = all_cands[:CAND_MAX]  # 候选上限 3 个（超出部分截断并标注）
            hit = _hit_text(labels, field, hits)
            # 取值来源：部门=事业部取值、内部交易=内部交易标记值、排除标记=排除标记值、其余=保留取值[字段]
            if field == "部门":
                raw_cfg = spec.get("事业部取值")
                vals = ([str(v).strip() for v in raw_cfg if str(v).strip()]
                        if raw_cfg is not None else dept_value_names(cfg))
                direction = "事业部"
            elif field == "内部交易":
                raw_cfg = spec.get("内部交易标记值")
                vals = ([str(v).strip() for v in raw_cfg if str(v).strip()]
                        if raw_cfg is not None else list(FLAT_DEFAULTS["内部交易标记值"]))
                direction = "内置剔除"
            else:
                val_key, direction = VALUE_KEYS.get(field, ("保留取值", "保留"))
                raw_cfg = spec.get(val_key) if val_key in FLAT_VALUE_KEYS else kept.get(field)
                vals = [str(v).strip() for v in (raw_cfg or []) if str(v).strip()]
            notes: list[str] = []
            if len(all_cands) > CAND_MAX:
                notes.append(f"⚠️ 候选已截断为 {CAND_MAX} 个（原 {len(all_cands)} 个）")
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
            if vals:
                if direction == "事业部":
                    notes.append("必填取值：只取这些事业部（映射表里有则先归一，没有按字面比）；未命中丢弃")
                elif direction == "内置剔除":
                    notes.append("必填取值：命中即整行剔除；清空 = 不过滤")
                elif direction == "剔除":
                    notes.append("必填取值：命中即整行剔除（期初/历史迁移行）")
                else:
                    notes.append("必填取值：命中即保留，其余（含空值）剔除；多字段之间 AND")
            elif direction == "事业部":
                notes.append("必填取值为空 = 不限制（取全部事业部）")
            elif field in TIME_FIELDS:
                notes.append("时间范围由「时间配置」sheet 控制，此列留空即可")
            row = [src, name, field, join_items(cands), join_items(vals), hit, "；".join(notes)]
            rows.append(row)
    return rows


def attach_mapping_sheet(wb, cfg: dict, hits: dict | None = None):
    """在 workbook 中创建/替换「字段映射」sheet（原地修改，需调用方 save）"""
    if MAP_SHEET_NAME in wb.sheetnames:
        del wb[MAP_SHEET_NAME]
    # 插到「说明」之前（生成器约定：说明固定放最后；create_sheet 默认追加末尾会破坏 sheet 顺序，
    # 导致 test_config_editor_workbook::test_sheet_set_and_order 失败）
    insert_at = (wb.sheetnames.index("说明")
                 if "说明" in wb.sheetnames else len(wb.sheetnames))
    ws = wb.create_sheet(MAP_SHEET_NAME, insert_at)

    banner(ws, "源表列名变了就在这里改「候选列名」——多个候选用「/」分隔、按先后尝试（最多 3 个）→ 保存后运行 run_all.bat。"
               "「必填取值」= 该字段要求的取值（如 已审核/外部结算；部门=取哪些事业部；内部交易=是），"
               "多值用「/」，清空=不限制/不过滤；列名本身含「/」时写 \\/；「当前命中(只读)」仅供参考。",
           len(MAP_HEADERS))
    header_row(ws, MAP_HEADERS, row=2)

    rows = build_mapping_rows(cfg, hits)
    for r_off, row in enumerate(rows[1:], start=3):
        for col, val in enumerate(row, 1):
            head = MAP_HEADERS[col - 1] if col <= len(MAP_HEADERS) else ""
            data_cell(
                ws, r_off, col, val,
                editable=head in (CAND_COL, VALUE_COL),
                readonly=head in KEY_COLS or head == HIT_COL,
                wrap=(head in (CAND_COL, VALUE_COL, HIT_COL, NOTE_COL)),
            )
        # 行高按「取值 / 当前命中 / 说明」的文字量自适应
        fit_row_height(ws, r_off, [(row[4], 26), (row[5], 24), (row[6], 46)])

    set_widths(ws, [10, 12, 12, 34, 24, 24, 46])
    # 筛选覆盖到最后一个字段行（编辑版为 A2:J37），不只是表头行
    ws.auto_filter.ref = f"A2:{get_column_letter(len(MAP_HEADERS))}{len(rows) + 1}"
    ws.freeze_panes = "D3"
    ws.sheet_properties.tabColor = TAB_COLORS.get(MAP_SHEET_NAME, TAB_COLORS["说明"])
    return ws


def refresh_mapping_sheet(excel_path: Path | str | None = None,
                          cfg_path: Path | str | None = None) -> Path:
    """只刷新 Excel 里的「字段映射」sheet，保留其他 sheet 原样"""
    import openpyxl

    excel_path = Path(excel_path or EXCEL_PATH)
    cfg_path = Path(cfg_path or CLEANING_CFG)
    if not excel_path.exists():
        raise FileNotFoundError(f"未找到配置编辑器: {_rel(excel_path)}")

    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    wb = openpyxl.load_workbook(excel_path)
    attach_mapping_sheet(wb, cfg, read_latest_hits())
    save_workbook(wb, excel_path)
    return excel_path
