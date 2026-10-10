# Author: naohua168 <bai_bai168@qq.com>
"""时间配置 —— Excel→JSON 解析与 cleaning_config.json 写回

由 scripts/config_excel_to_json.py 拆分而来（行为不变，见 logs/_dryrun_before.txt 比对）。
"""
from __future__ import annotations

import json
from datetime import datetime
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
    """解析月份范围列：'1-8' / '1,8' → [1, 8]"""
    raw = raw.strip().strip("[]").replace("，", ",")
    if not raw:
        return []
    parts = [p.strip() for p in raw.replace("-", ",").split(",") if p.strip()]
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


def _date_cell_value(raw):
    """JSON 里的日期文本 → 写进 Excel 单元格的 datetime（配 DATE_CELL_FMT 显示到秒）

    '2026-10-01' → datetime(2026,10,1,0,0)，单元格显示 `2026-10-01 00:00:00`；
    '2026-10-31 23:59:59' 原样保留时分秒；解析不了的异常文本原样返回（由校验阶段报错）。
    """
    s = str(raw).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return raw


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
                months = _parse_month_range(month_range)
                if len(months) != 2 or months[0] > months[1]:
                    raise ValueError(f"{name}: 月份范围应为 [起始月, 结束月]，如 1-8")
                cfg = {"年份": int(year), "月份范围": months}
            else:
                # 常规时间范围：开始/结束日期
                if not start or not end:
                    raise ValueError(f"{name}: 手填日期模式需填「开始日期」和「结束日期」")
                for v in (start, end):
                    try:
                        datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        try:
                            datetime.strptime(v, "%Y-%m-%d")
                        except ValueError:
                            raise ValueError(f"{name}: 日期格式错误 {v!r}（应为 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS）")
                cfg = {"start_date": start, "end_date": end}

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
