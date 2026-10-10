# Author: naohua168 <bai_bai168@qq.com>
"""时间配置 —— Excel→JSON 解析与 cleaning_config.json 写回

由 scripts/config_excel_to_json.py 拆分而来（行为不变，见 logs/_dryrun_before.txt 比对）。
"""
from __future__ import annotations

import calendar
import json
import re
from datetime import date, datetime, timedelta

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
from .constants import TIME_KEYS, DYNAMIC_STRATEGIES, MODE_ALIASES, STRATEGY_ALIASES, MODE_LABELS, STRATEGY_LABELS, DATE_CELL_FMT, CLEANING_CFG, TIME_KEYS, DYNAMIC_STRATEGIES, MODE_LABELS, MODE_ALIASES, STRATEGY_LABELS, STRATEGY_ALIASES, DATE_CELL_FMT
from .display_rules import _replace_time_range_block
from .parsing import _parse_cell
from .paths import CLEANING_CFG


def _parse_month_range(raw: str) -> list[int]:
    """解析月份范围列：'1-8' / '1,8' → [1, 8]

    容错（2026-10-10）：全角数字/全角逗号、'1月-8月'、'1~8' / '1～8' / '1到8' 都认。
    """
    raw = str(raw).strip().translate(_FULLWIDTH_MAP).strip("[]").replace("，", ",")
    raw = raw.replace("～", "~").replace("到", "~").replace("月", " ")
    if not raw:
        return []
    parts = [p.strip() for p in re.split(r"[-~,]", raw) if p.strip()]
    nums = []
    for p in parts:
        try:
            nums.append(int(p))
        except ValueError:
            raise ValueError(f"月份范围格式错误: {raw!r}（应为 '1-8' 或 '1,8'）")
    # 写 "1-9" 时若单元格不是文本格式，Excel 会当日期存成序列号（46031）→ 这里给出可操作的提示
    if nums and (len(nums) != 2 or any(n < 1 or n > 12 for n in nums)):
        raise ValueError(
            f"月份范围格式错误: {raw!r}（应为 '1-8' 或 '1,8'）"
            "；若该单元格显示成日期（如 2026/1/9），说明被 Excel 识别成了日期 —— "
            "请把单元格格式设为「文本」后重新填 1-9"
        )
    return nums


# ── 日期文本的宽松解析（2026-10-10 增加容错）──────────────────────────────
# 背景：结束日期被填成 `2026/9/31 23:59:59`（斜杠 + 单位月，且 9 月没有 31 号），
# 解析直接抛错 → 流水线在第①步「配置同步」就中断（logs/run_20261010_143802.log）。
# 现在：常见写法都认（斜杠/点号/中文年月日/单位月/全角/可省秒），非法日历日期按该月
# 最后一天截断并打印醒目提示（既不静默改数、也不让整条流水线停摆）。
_FULLWIDTH_MAP = str.maketrans("０１２３４５６７８９／．：", "0123456789/.:")
_DATE_SEP = r"[-/.]"
DATE_TEXT_RE = re.compile(
    rf"^(\d{{4}})\s*(?:年|{_DATE_SEP})\s*(\d{{1,2}})\s*(?:月|{_DATE_SEP})\s*(\d{{1,2}})\s*日?"
    r"(?:[ T]\s*(\d{1,2})\s*[:：]\s*(\d{1,2})\s*(?:[:：]\s*(\d{1,2}))?)?$"
)
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$")
_EXCEL_EPOCH = datetime(1899, 12, 30)     # Excel 序列号基准（含 1900 闰年 bug 的通用修正）
_SERIAL_RANGE = (20000.0, 80000.0)        # ≈1954~2119 年，该区间外的纯数字不当日期


def month_last_day(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def parse_date_text(raw, field: str = "日期") -> datetime:
    """宽松解析日期（文本 / date·datetime 对象 / Excel 日期序列号）→ datetime

    - 认这些写法：`2026-09-30`、`2026/9/30`、`2026.9.30`、`2026年9月30日`，可带时间
      `23:59` / `23:59:59`（时分秒分隔符全角半角都行），也认 ISO 的 `T` 分隔
    - 非法日历日期（如 `2026/9/31`）→ 按该月最后一天截断并打印提示，不抛错
    - 无法识别 → ValueError（消息里给出支持的写法，便于自查）
    """
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, date):
        return datetime(raw.year, raw.month, raw.day)

    s = str(raw).strip().translate(_FULLWIDTH_MAP)
    if not s:
        raise ValueError(f"{field}: 日期为空")

    m = DATE_TEXT_RE.match(s)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        hh, mi, ss = int(m.group(4) or 0), int(m.group(5) or 0), int(m.group(6) or 0)
    else:
        # 纯数字 → Excel 日期序列号（单元格被设成「常规」时，日期会以序列号形式读出）
        if re.fullmatch(r"\d+(?:\.\d+)?", s) and _SERIAL_RANGE[0] <= float(s) <= _SERIAL_RANGE[1]:
            dt = _EXCEL_EPOCH + timedelta(days=float(s))
            print(f"  ⚠️ {field}: {str(raw).strip()!r} 被当作 Excel 日期序列号 → "
                  f"{dt:%Y-%m-%d %H:%M:%S}；建议把该单元格格式设为「日期」或按 YYYY-MM-DD 填写")
            return dt.replace(microsecond=0)
        raise ValueError(
            f"{field}: 日期格式无法识别 {str(raw).strip()!r}；支持 2026-09-30 / 2026/9/30 / "
            "2026.9.30 / 2026年9月30日（可带时间，如 2026/9/30 23:59:59）"
        )

    if not 1 <= mo <= 12:
        raise ValueError(f"{field}: 月份非法 {mo}（{str(raw).strip()!r}）")
    if not (0 <= hh <= 23 and 0 <= mi <= 59 and 0 <= ss <= 59):
        raise ValueError(f"{field}: 时间非法（{str(raw).strip()!r}）")

    last = month_last_day(y, mo)
    if not 1 <= d <= last:
        fixed = min(max(d, 1), last)
        print(f"  ⚠️ {field}: {str(raw).strip()!r} 不是有效日期（{y} 年 {mo} 月没有 {d} 号）"
              f" → 按该月最后一天 {fixed} 号处理，请核对时间配置")
        d = fixed
    return datetime(y, mo, d, hh, mi, ss)


def normalize_date_text(raw, field: str = "日期") -> str:
    """日期文本规范成 `YYYY-MM-DD` / `YYYY-MM-DD HH:MM:SS`

    已经是规范形态的原样返回（保证不改动现有配置的 JSON 文本）；其它写法解析后规范化 ——
    下游 `end_of_day()` 与 `pd.to_datetime` 只认规范形态，`2026/9/30` 这类文本会被当成
    当天 00:00:00，从而漏掉当天数据。
    """
    s = str(raw).strip()
    if _ISO_DATE_RE.match(s):
        return s
    dt = parse_date_text(s, field=field)
    if (dt.hour, dt.minute, dt.second) == (0, 0, 0):
        return dt.strftime("%Y-%m-%d")
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _date_cell_value(raw):
    """JSON 里的日期文本 → 写进 Excel 单元格的 datetime（配 DATE_CELL_FMT 显示到秒）

    '2026-10-01' → datetime(2026,10,1,0,0)，单元格显示 `2026-10-01 00:00:00`；
    '2026-10-31 23:59:59' 原样保留时分秒；解析不了的异常文本原样返回（由校验阶段报错）。
    """
    s = str(raw).strip()
    if not s:
        return raw
    try:
        return parse_date_text(s, field="日期配置")
    except ValueError:
        return raw        # 异常文本原样写入单元格，交给读取阶段给出可操作提示


def excel_to_time_config(sheet) -> dict:
    """从 Excel「时间配置」sheet 构建 {键: 配置dict}

    兼容两种布局：带顶部横幅（表头在 1~4 行内）/ 历史文件（表头在第 1 行）；
    列按**表头名**定位，因此列顺序调整也不影响解析。
    """
    rows = [tuple(r) for r in sheet.iter_rows(values_only=True)]
    hi = locate_header_row(rows, ("配置名", "模式"), max_scan=4)
    if hi < 0:
        raise ValueError("「时间配置」sheet 找不到表头行（需含「配置名」「模式」列）")
    headers = [str(v).strip() if v is not None else "" for v in rows[hi]]
    idx = {h: i for i, h in enumerate(headers)}

    def at(row, col: str) -> str:
        i = idx.get(col, -1)
        return _parse_cell(row[i]) if 0 <= i < len(row) else ""

    result: dict = {}
    seen: set[str] = set()
    for row in rows[hi + 1:]:
        name = at(row, "配置名")
        if not name:
            continue  # 空行跳过
        if name in seen:
            raise ValueError(f"时间配置存在重复键: {name}")
        seen.add(name)

        mode_raw = at(row, "模式") or "static"
        strategy_raw = at(row, "动态策略")
        start = at(row, "开始日期")
        end = at(row, "结束日期")
        year = at(row, "年份")
        month_range = at(row, "月份范围")
        note = at(row, "说明")

        if name == "结算模式":
            # 特殊行：非日期范围，值为月底结算 / 常规（填在「模式」列）
            settle = mode_raw if mode_raw not in ("static", "手填日期", "手填") else "常规"
            if settle not in ("月底结算", "常规"):
                raise ValueError(f"{name}: 值应为「月底结算」或「常规」（填在「模式」列），当前: {settle!r}")
            result[name] = {
                "值": settle,
                "_说明": note or "月底结算: 运营端=完整年度累计(含当月), 当年/季度累计=仅运营端; 常规: 当年/季度累计=财务端+运营端。月数据均只用财务端。",
            }
            continue

        # 中文标签（手填日期/自动计算）与英文旧值（static/dynamic）都接受
        mode = MODE_ALIASES.get(mode_raw.strip())
        if mode is None:
            raise ValueError(
                f"{name}: 未知模式 {mode_raw!r}（可选 {' / '.join(MODE_LABELS.values())}；"
                f"旧写法 static / dynamic 也兼容）"
            )
        strategy = STRATEGY_ALIASES.get(strategy_raw.strip(), strategy_raw.strip())

        if mode == "dynamic":
            if strategy not in DYNAMIC_STRATEGIES:
                raise ValueError(
                    f"{name}: 未知动态策略 {strategy!r}，可选 "
                    f"{' / '.join(STRATEGY_LABELS.values())}（旧写法 {DYNAMIC_STRATEGIES} 也兼容）"
                )
            cfg: dict = {"_mode": "dynamic", "_strategy": strategy}
        else:
            if name == "年基线数据":
                # 年基线：年份 + 月份范围
                if not year:
                    raise ValueError(f"{name}: 手填日期模式需填「年份」")
                year_digits = re.sub(r"\D", "", str(year))   # 容错："2025 年" / "2,025"
                if len(year_digits) != 4:
                    raise ValueError(
                        f"{name}: 年份应为 4 位数字（如 2025），当前: {str(year).strip()!r}"
                    )
                months = _parse_month_range(month_range)
                if len(months) != 2 or months[0] > months[1]:
                    raise ValueError(f"{name}: 月份范围应为 [起始月, 结束月]，如 1-8")
                cfg = {"年份": int(year_digits), "月份范围": months}
            else:
                # 常规时间范围：开始/结束日期
                if not start or not end:
                    raise ValueError(f"{name}: 手填日期模式需填「开始日期」和「结束日期」")
                # 日期容错（2026-10-10）：斜杠/点号/中文年月日/单位月/全角/序列号都认；
                # 非法日历日期（9/31）按月末截断并提示；解析结果规范化后写入 JSON
                cfg = {
                    "start_date": normalize_date_text(start, field=f"{name} 开始日期"),
                    "end_date": normalize_date_text(end, field=f"{name} 结束日期"),
                }

        if note:
            cfg["_使用方"] = note
        result[name] = cfg

    # 校验必备键齐全
    for k in TIME_KEYS:
        if k not in result:
            raise ValueError(f"Excel 时间配置缺少必备项: {k}")

    return result


def update_cleaning_config(time_config: dict, dry_run: bool = False) -> dict:
    """把时间配置写回 cleaning_config.json 的「时间范围」部分（文本级替换，最小 diff）"""
    if not CLEANING_CFG.exists():
        raise FileNotFoundError(f"cleaning_config.json 不存在: {rel_path(CLEANING_CFG)}")

    text = CLEANING_CFG.read_text(encoding="utf-8")
    cfg = json.loads(text)
    old_tr = cfg.get("时间范围", {})
    # 保留 _说明（顶层 + 年基线数据）
    if "_说明" in old_tr:
        time_config = {"_说明": old_tr["_说明"], **time_config}
    # 结算模式：Excel 未提供该行时保留原 JSON 值（向前兼容旧模板）
    if "结算模式" not in time_config and "结算模式" in old_tr:
        time_config["结算模式"] = old_tr["结算模式"]
    if old_tr.get("年基线数据", {}).get("_说明"):
        if "年基线数据" in time_config:
            time_config["年基线数据"] = {
                "_说明": old_tr["年基线数据"]["_说明"],
                **time_config["年基线数据"],
            }

    if dry_run:
        return {**cfg, "时间范围": time_config}

    new_text = _replace_time_range_block(text, time_config)
    CLEANING_CFG.write_text(new_text, encoding="utf-8")
    return json.loads(new_text)
