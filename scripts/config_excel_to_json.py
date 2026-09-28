# Author: naohua168 <bai_bai168@qq.com>
"""配置编辑器 — Excel → JSON 生成器

把 config/配置编辑器.xlsx 中的配置写回对应的 JSON 配置文件。

当前支持的 sheet（2026-09-28）：
    - 时间配置  → cleaning_config.json 的「时间范围」（含结算模式）
    - 展示规则  → 前端渲染/展示规则.json（页面/区块/配置项/值，见 display_rules_sheet.py）
    - KPI指标   → 前端渲染/展示规则.json 各页面的 `KPI指标` 区块
    - 销售归属  → 清洗配置/客户销售归属.json
    - 字段映射  → cleaning_config.json 各来源的「列映射」（见 column_mapping_sheet.py）

用法:
    python scripts/config_excel_to_json.py              # 生成并写回（run_all.bat 第①步）
    python scripts/config_excel_to_json.py --dry-run    # 只读不改写（打印将生成的内容）
    python scripts/config_excel_to_json.py --init       # 首次创建 Excel 模板（从当前 JSON 导出）
    python scripts/config_excel_to_json.py --init-map   # 只刷新「字段映射」sheet（其余 sheet 不动）
    python scripts/config_excel_to_json.py --init-rules # 只刷新「展示规则」sheet

设计原则：
    - Excel 是「编辑层」，JSON 是「事实源」（系统只读 JSON）
    - 生成器只更新 JSON 中对应小节，不触碰其他配置
    - 校验失败时拒绝写回，避免脏数据进入系统
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill
except ImportError:
    print("缺少 openpyxl，请先安装: pip install openpyxl")
    sys.exit(1)

BASE_DIR = Path(__file__).parent.parent
EXCEL_PATH = BASE_DIR / "config" / "配置编辑器.xlsx"
CLEANING_CFG = BASE_DIR / "config" / "清洗配置" / "cleaning_config.json"
DISPLAY_RULES_CFG = BASE_DIR / "config" / "前端渲染" / "展示规则.json"
ATTRIBUTION_CFG = BASE_DIR / "config" / "清洗配置" / "客户销售归属.json"

# 支持的时间配置键 → 说明
TIME_KEYS = ["年度累计", "月度数据", "季度累计筛选", "年基线数据"]

# dynamic 策略白名单（与 engine/core/config.py _STRATEGY_REGISTRY 对应）
DYNAMIC_STRATEGIES = ["last_full_month", "last_full_quarter"]

HEADERS = ["配置名", "模式", "动态策略", "开始日期", "结束日期", "年份", "月份范围", "说明"]

# 展示规则：sheet 结构 / 解析 / 校验 / 下拉 全在 scripts/display_rules_sheet.py
# （2026-09-28 重做 —— 旧「路径」结构仍可解析，但模板已改为 页面|区块|配置项|值|可选值|说明）
# 顶层页面键（固定顺序，与看板导航一致）
RULE_PAGES = ["数据总览", "年度达成", "月度达成", "季度达成", "销售达成", "年度同比"]

# 销售归属 sheet 列
ATT_HEADERS = ["母公司", "子公司", "指标", "部门", "销售", "比例", "说明"]

# 指标取值（收入,回款 表示同时写入两个指标）
METRIC_VALUES = ["收入", "回款", "收入,回款"]

# 部门取值
DEPT_VALUES = ["检测", "信息", "能源", "海外"]

# KPI 指标 sheet（单独 sheet，控制 Hero 圆环的指标总数，万元）
# 值留空 = 不覆盖（用指标文件合计）；填数字 = 覆盖 KPI 卡片显示
KPI_PAGES = ["年度达成", "月度达成", "季度达成"]
KPI_METRICS = ["收入", "回款"]
KPI_HEADERS = ["页面", "指标", "值(万元)", "说明"]

# 「说明」sheet 第 4 节（销售归属）补充：多组配置子公司的归属规则（2026-09-28 新增）
# 供 `--init` 生成模板、以及刷新现有 Excel 说明页时共用，避免两处文案漂移
GROUP_NOTE_LINES: list[list[str]] = [
    ["   - 多组配置(同一子公司在多个母公司下)的归属规则（2026-09-28）:"],
    ["     · 广东自有客户 <-> 零部件客户/福建市场 等: 法人=广东汽车检测中心有限公司 → 广东自有客户; 其他法人 → 另一个父组"],
    ["     · 比亚迪汽车工业有限公司 <-> 比亚迪电池: **只对两父组下同时出现的子公司判断**; 法人=广东汽车检测中心 → 比亚迪汽车工业, 其他法人 → 比亚迪电池"],
    ["     · 其他任意两组重复配置: 无规则 → 取先出现的分组, 且弹窗明细会与矩阵行对不上（尽量避免重复配置）"],
    ["   - 核对方法: 客户矩阵某行的数字 = 该行「子公司明细」抽屉里各子行相加（两处已统一口径）"],
]

# 「说明」sheet 第 9 节：金额单位 / 金额乘数（2026-09-28 新增）
# 供 `--init` 生成模板、以及刷新现有 Excel 说明页时共用，避免两处文案漂移
UNIT_NOTE_LINES: list[list[str]] = [
    ["9. 金额单位（元 / 万元）— 由 JSON 的「金额乘数」控制（2026-09-28 更新）："],
    ["   - 各来源当前单位: 财务端 收入.xlsx / 回款.xlsx = 元 ｜ 广东公司 = 万元 ｜ 湖南公司 = 万元 ｜ 南方韶关 = 元（整文件：收入+回款，2026-09-28 起） ｜ 运营端 = 元 ｜ 手工指标表 = 万元"],
    ["   - 换算规则: 清洗后统一输出「元」；金额乘数 1 = 源文件已是元，10000 = 源文件是万元（渲染层再 ÷10000 显示为万元）"],
    ["   - 改法（改 JSON，勿在本 Excel 改）: 数据源.<数据源>.<来源>.金额乘数 = 数字（该来源所有 Sheet 相同）；"],
    ["     按 Sheet 不同时写字典，如 {\"收入\": 1, \"回款\": 10000}（收入已是元、回款是万元）"],
    ["   - 变更记录: 2026-09-28 南方韶关 收入+回款 两个 Sheet 单位均改为「元」→ 金额乘数由 {收入:1, 回款:10000} 简化为 1"],
    ["   - ⚠ 本编辑器「字段映射」sheet 的候选列名（如 金额(元) / 金额(万元)）只决定「能否匹配上源文件列名」，不参与单位换算；"],
    ["     名字对上了但单位没同步改「金额乘数」，金额会差 10000 倍"],
]

# 字段映射 sheet（清洗列名映射的编辑层，2026-09-17 新增）
try:  # 直接以脚本方式运行时（python scripts/config_excel_to_json.py）
    from column_mapping_sheet import (
        MAP_SHEET_NAME, attach_mapping_sheet, excel_to_column_mapping,
        read_latest_hits, refresh_mapping_sheet, update_column_mapping,
    )
except ImportError:  # 以包形式导入时（如单元测试）
    from scripts.column_mapping_sheet import (  # type: ignore[no-redef]
        MAP_SHEET_NAME, attach_mapping_sheet, excel_to_column_mapping,
        read_latest_hits, refresh_mapping_sheet, update_column_mapping,
    )

# 展示规则 sheet（2026-09-28 重做：序号/页面/区块/配置项/值/可选值/说明 + 下拉）
try:  # 直接以脚本方式运行时
    from display_rules_sheet import (
        RULE_NOTE_LINES, RULE_SHEET_NAME, attach_rules_sheet,
        excel_to_display_rules, refresh_rules_sheet,
    )
except ImportError:  # 以包形式导入时（如单元测试）
    from scripts.display_rules_sheet import (  # type: ignore[no-redef]
        RULE_NOTE_LINES, RULE_SHEET_NAME, attach_rules_sheet,
        excel_to_display_rules, refresh_rules_sheet,
    )

# 表格统一样式（横幅/表头/可编辑底色/斑马纹/表头行定位）
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


# ──────────────────────────────────────────────────────────────
# Excel 读取 → 时间配置 dict
# ──────────────────────────────────────────────────────────────
def _parse_cell(value) -> str:
    """单元格值 → 干净字符串（Excel 日期/数字转文本）"""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    return str(value).strip()


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
    return nums


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

        mode = at(row, "模式") or "static"
        strategy = at(row, "动态策略")
        start = at(row, "开始日期")
        end = at(row, "结束日期")
        year = at(row, "年份")
        month_range = at(row, "月份范围")
        note = at(row, "说明")

        if name == "结算模式":
            # 特殊行：非日期范围，值为月底结算 / 常规（填在「模式」列）
            settle = mode if mode != "static" else "常规"
            if settle not in ("月底结算", "常规"):
                raise ValueError(f"{name}: 值应为「月底结算」或「常规」（填在「模式」列），当前: {settle!r}")
            result[name] = {
                "值": settle,
                "_说明": note or "月底结算: 运营端=完整年度累计(含当月), 当年/季度累计=仅运营端; 常规: 当年/季度累计=财务端+运营端。月数据均只用财务端。",
            }
            continue

        if mode == "dynamic":
            if strategy not in DYNAMIC_STRATEGIES:
                raise ValueError(
                    f"{name}: 未知动态策略 {strategy!r}，可选 {DYNAMIC_STRATEGIES}"
                )
            cfg: dict = {"_mode": "dynamic", "_strategy": strategy}
        elif mode == "static":
            if name == "年基线数据":
                # 年基线：年份 + 月份范围
                if not year:
                    raise ValueError(f"{name}: static 模式需填「年份」")
                months = _parse_month_range(month_range)
                if len(months) != 2 or months[0] > months[1]:
                    raise ValueError(f"{name}: 月份范围应为 [起始月, 结束月]，如 1-8")
                cfg = {"年份": int(year), "月份范围": months}
            else:
                # 常规时间范围：开始/结束日期
                if not start or not end:
                    raise ValueError(f"{name}: static 模式需填「开始日期」和「结束日期」")
                for v in (start, end):
                    try:
                        datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        try:
                            datetime.strptime(v, "%Y-%m-%d")
                        except ValueError:
                            raise ValueError(f"{name}: 日期格式错误 {v!r}（应为 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS）")
                cfg = {"start_date": start, "end_date": end}
        else:
            raise ValueError(f"{name}: 未知模式 {mode!r}（应为 static 或 dynamic）")

        if note:
            cfg["_使用方"] = note
        result[name] = cfg

    # 校验必备键齐全
    for k in TIME_KEYS:
        if k not in result:
            raise ValueError(f"Excel 时间配置缺少必备项: {k}")

    return result


# ──────────────────────────────────────────────────────────────
# Excel 读取 → 展示规则 dict
#   （2026-09-28 重做：结构/解析/校验/下拉全部在 scripts/display_rules_sheet.py，
#     本文件只负责调用并写回 JSON；旧的「路径」结构仍由该模块兼容解析）
# ──────────────────────────────────────────────────────────────


# ──────────────────────────────────────────────────────────────
# 生成器主流程
# ──────────────────────────────────────────────────────────────
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


def update_cleaning_config(time_config: dict, dry_run: bool = False) -> dict:
    """把时间配置写回 cleaning_config.json 的「时间范围」部分（文本级替换，最小 diff）"""
    if not CLEANING_CFG.exists():
        raise FileNotFoundError(f"cleaning_config.json 不存在: {CLEANING_CFG}")

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


# ──────────────────────────────────────────────────────────────
# 展示规则写回（保留头部说明字段，页面数据用标准格式重建）
# ──────────────────────────────────────────────────────────────
_STALE_NOTE_RE = re.compile(r"^_(.+)说明$")


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
        raise FileNotFoundError(f"展示规则.json 不存在: {DISPLAY_RULES_CFG}")

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
        raise FileNotFoundError(f"展示规则.json 不存在: {DISPLAY_RULES_CFG}")

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


# ──────────────────────────────────────────────────────────────
# Excel 读取 → KPI 指标 dict
# ──────────────────────────────────────────────────────────────
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


# ──────────────────────────────────────────────────────────────
# Excel 读取 → 销售归属 dict
# ──────────────────────────────────────────────────────────────
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
        metrics = [m.strip() for m in r["metric"].split(",") if m.strip()]
        for m in metrics:
            if m not in ("收入", "回款"):
                raise ValueError(f"非法指标值: {m!r}（可选 收入/回款/收入,回款）")
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

    return result


def update_attribution(attribution: dict, dry_run: bool = False) -> dict:
    """把销售归属写回 客户销售归属.json（保留 _说明/_销售拆分，客户归属数据来自 Excel）"""
    if not ATTRIBUTION_CFG.exists():
        raise FileNotFoundError(f"客户销售归属.json 不存在: {ATTRIBUTION_CFG}")

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


# ──────────────────────────────────────────────────────────────
# Excel 模板初始化（从当前 JSON 导出）
# ──────────────────────────────────────────────────────────────
def _cell_fill(name: str) -> str:
    fills = {
        "年度累计": "DDEBF7",
        "月度数据": "E2EFDA",
        "季度累计筛选": "FFF2CC",
        "年基线数据": "FCE4D6",
    }
    return fills.get(name, "FFFFFF")


def init_excel_template():
    """从 cleaning_config.json 当前时间范围导出 Excel 模板"""
    cfg = json.loads(CLEANING_CFG.read_text(encoding="utf-8"))
    tr = cfg.get("时间范围", {})

    wb = openpyxl.Workbook()

    # ── Sheet 1: 时间配置 ──
    ws = wb.active
    ws.title = "时间配置"
    from openpyxl.worksheet.datavalidation import DataValidation

    banner(ws, "改日期 → 保存 → 运行 启动系统.bat / run_all.bat 生效。"
               "模式 static = 手填日期；dynamic = 自动取最近完整月/季度（填「动态策略」）；"
               "「结算模式」行的值填在「模式」列。", len(HEADERS))
    header_row(ws, HEADERS, row=2)

    row_idx = 3
    for key in TIME_KEYS:
        spec = tr.get(key, {})
        fill_color = _cell_fill(key)
        if spec.get("_mode") == "dynamic":
            values = [key, "dynamic", spec.get("_strategy", ""), "", "", "", "", spec.get("_使用方", "")]
        elif key == "年基线数据":
            months = spec.get("月份范围", [])
            values = [
                key, "static", "",
                "", "", spec.get("年份", ""),
                f"{months[0]}-{months[1]}" if len(months) == 2 else "",
                spec.get("_使用方", ""),
            ]
        else:
            values = [
                key, "static", "",
                spec.get("start_date", ""), spec.get("end_date", ""),
                "", "", spec.get("_使用方", ""),
            ]
        for col, v in enumerate(values, 1):
            c = data_cell(ws, row_idx, col, v,
                          editable=col in (2, 3, 4, 5, 6, 7), readonly=(col == 8),
                          wrap=(col == 8))
            if col == 1:  # 配置名列保留按行的身份色（年度/月度/季度/年基线）
                c.fill = PatternFill("solid", fgColor=fill_color)
        row_idx += 1

    # 结算模式行（值填在「模式」列：月底结算 / 常规）
    settle = tr.get("结算模式", {})
    if settle:
        values = [
            "结算模式", settle.get("值", "常规"), "",
            "", "", "", "",
            settle.get("_说明", "月底结算: 当年/季度累计=仅运营端; 常规: =财务端+运营端"),
        ]
        for col, v in enumerate(values, 1):
            c = data_cell(ws, row_idx, col, v, editable=(col == 2), readonly=(col == 8),
                          wrap=(col == 8))
            if col == 1:
                c.fill = PatternFill("solid", fgColor="FCE4D6")
        row_idx += 1

    set_widths(ws, [16, 12, 20, 18, 26, 8, 12, 46])

    dv_mode = DataValidation(type="list", formula1='"static,dynamic"', allow_blank=True,
                             promptTitle="怎么填",
                             prompt="static = 手填开始/结束日期；dynamic = 自动算（再填「动态策略」）")
    dv_mode.add(f"B3:B{row_idx + 50}")
    ws.add_data_validation(dv_mode)
    dv_strat = DataValidation(type="list", formula1='"last_full_month,last_full_quarter"',
                              allow_blank=True, promptTitle="怎么填",
                              prompt="仅「模式=dynamic」时填：last_full_month 最近完整月 / last_full_quarter 最近完整季度")
    dv_strat.add(f"C3:C{row_idx + 50}")
    ws.add_data_validation(dv_strat)
    finish(ws, freeze="A3", autofilter="A2:H2", tab_color=TAB_COLORS["时间配置"])

    # ── Sheet 2: 展示规则 ──
    # （2026-09-28 重做：序号/页面/区块/配置项/值/可选值/说明 + 下拉验证，见 display_rules_sheet.py）
    rules = json.loads(DISPLAY_RULES_CFG.read_text(encoding="utf-8"))
    attach_rules_sheet(wb, rules)

    # ── Sheet 3: 销售归属 ──
    att = json.loads(ATTRIBUTION_CFG.read_text(encoding="utf-8"))["客户归属"]
    ws_a = wb.create_sheet("销售归属")
    banner(ws_a, "母公司 → 子公司 → 指标 → 部门 → 销售 → 比例（通常只改「销售」「比例」两列）。"
                 "一家母公司一块浅蓝斑马纹；比例 = 全额填 1，拆分填 0.3 或 30%（同一子公司各销售比例合计 = 1）。",
           len(ATT_HEADERS))
    header_row(ws_a, ATT_HEADERS, row=2)

    att_row = 3
    for group_i, (parent, group) in enumerate(att.items()):
        band = (group_i % 2 == 1)
        for sub, sub_data in group.get("子公司", {}).items():
            # 判断收入/回款是否同构：同构 → 指标=收入,回款 一行
            inc = sub_data.get("收入", {})
            pay = sub_data.get("回款", {})
            if inc == pay and inc:
                note = sub_data.get("_说明", "")
                for dept, sales_map in inc.items():
                    for sales, ratio in sales_map.items():
                        vals = [parent, sub, "收入,回款", dept, sales,
                                f"{ratio:.15g}", note]
                        for c, v in enumerate(vals, 1):
                            data_cell(ws_a, att_row, c, v,
                                      editable=c in (5, 6), band=band, wrap=(c == 7))
                        att_row += 1
            else:
                # 结构不同：收入/回款分开行
                for metric, m in (("收入", inc), ("回款", pay)):
                    if not m:
                        continue
                    note = sub_data.get("_说明", "")
                    for dept, sales_map in m.items():
                        for sales, ratio in sales_map.items():
                            vals = [parent, sub, metric, dept, sales,
                                    f"{ratio:.15g}", note]
                            for c, v in enumerate(vals, 1):
                                data_cell(ws_a, att_row, c, v,
                                          editable=c in (5, 6), band=band, wrap=(c == 7))
                            att_row += 1

    set_widths(ws_a, [26, 36, 14, 10, 12, 10, 30])

    # 数据验证：指标 / 部门（取值来自文件顶部 METRIC_VALUES / DEPT_VALUES，避免重复硬编码）
    from openpyxl.worksheet.datavalidation import DataValidation
    dv_metric = DataValidation(type="list", formula1='"' + ",".join(METRIC_VALUES) + '"',
                               allow_blank=True, promptTitle="怎么填",
                               prompt="收入 / 回款 / 收入,回款（收入与回款归属一致时填「收入,回款」一行搞定）")
    dv_metric.add(f"C3:C{att_row + 50}")
    ws_a.add_data_validation(dv_metric)
    dv_dept = DataValidation(type="list", formula1='"' + ",".join(DEPT_VALUES) + '"',
                             allow_blank=True, promptTitle="怎么填",
                             prompt="检测 / 信息 / 能源 / 海外")
    dv_dept.add(f"D3:D{att_row + 50}")
    ws_a.add_data_validation(dv_dept)

    finish(ws_a, freeze="C3", autofilter="A2:G2", tab_color=TAB_COLORS["销售归属"])

    # ── Sheet 4: KPI指标（Hero 圆环指标总数覆盖，万元）──
    rules_now = json.loads(DISPLAY_RULES_CFG.read_text(encoding="utf-8"))
    ws_k = wb.create_sheet("KPI指标")
    banner(ws_k, "「值(万元)」留空 = 不覆盖（Hero 圆环按指标文件合计）；填数字 = 覆盖圆环上的指标总数。"
                 "只影响 Hero 圆环，不改表格/矩阵里的明细指标。", len(KPI_HEADERS))
    header_row(ws_k, KPI_HEADERS, row=2)

    k_row = 3
    k_notes = {
        "年度达成": "年度达成页 + 数据总览页的年度 KPI 指标总数",
        "月度达成": "月度达成页的 KPI 指标总数",
        "季度达成": "季度达成页的 KPI 指标总数",
    }
    for page in KPI_PAGES:
        page_kpi = rules_now.get(page, {}).get("KPI指标", {})
        band = (KPI_PAGES.index(page) % 2 == 1)
        for metric in KPI_METRICS:
            v = page_kpi.get(metric)
            vals = [page, metric, v if v is not None else "", k_notes[page]]
            for c, vv in enumerate(vals, 1):
                data_cell(ws_k, k_row, c, vv, editable=(c == 3), band=band, wrap=(c == 4))
            k_row += 1

    set_widths(ws_k, [16, 12, 16, 52])
    # 数据验证：页面 / 指标 下拉
    from openpyxl.worksheet.datavalidation import DataValidation
    dv_kpage = DataValidation(type="list", formula1='"' + ",".join(KPI_PAGES) + '"', allow_blank=True)
    dv_kpage.add(f"A3:A{ws_k.max_row + 50}")
    ws_k.add_data_validation(dv_kpage)
    dv_kmetric = DataValidation(type="list", formula1='"' + ",".join(KPI_METRICS) + '"', allow_blank=True)
    dv_kmetric.add(f"B3:B{ws_k.max_row + 50}")
    ws_k.add_data_validation(dv_kmetric)
    finish(ws_k, freeze="A3", tab_color=TAB_COLORS["KPI指标"])

    # ── Sheet 5: 说明 ──
    ws2 = wb.create_sheet("说明")
    lines = [
        ["配置编辑器使用说明"],
        [""],
        ["1. 本 Excel 是「编辑层」，改完保存后运行生成器写回 JSON，系统读取 JSON。"],
        ["   运行: python scripts/config_excel_to_json.py"],
        ["   统一设计(2026-09-28): 每张表 第1行=蓝色提示(这张表怎么用)、第2行=表头；【浅黄底=可编辑列】，浅灰底=只读/参考列。"],
        ["   销售归属表按母公司分块浅蓝斑马纹；时间配置/销售归属/字段映射 表头带筛选按钮、已冻结窗格；各表标签页颜色区分。"],
        ["   下拉只给取值有限的项（模式/动态策略/指标/部门/排序），客户名等自由文本自己填。"],
        [""],
        ["2. 「时间配置」sheet 列说明："],
        ["   - 配置名: 年度累计 / 月度数据 / 季度累计筛选 / 年基线数据（勿改）"],
        ["   - 模式: static（手填日期）或 dynamic（自动计算）"],
        ["   - 动态策略: 模式为 dynamic 时填写 last_full_month / last_full_quarter"],
        ["   - 开始日期/结束日期: 格式 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS"],
        ["   - 年份/月份范围: 仅年基线数据使用，如 2025 / 1-8"],
        ["   - 说明: 填写配置用途（可选）"],
        [""],
        *RULE_NOTE_LINES,
        ["4. 「销售归属」sheet 列说明："],
        ["   - 母公司: 客户归组的母公司名（如 广州小鹏汽车科技有限公司）"],
        ["   - 子公司: 实际结算主体名（=母公司时表示本部）"],
        ["   - 指标: 收入 / 回款 / 收入,回款（收入回款同构时用后者，一行搞定）"],
        ["   - 部门: 检测 / 信息 / 能源 / 海外"],
        ["   - 销售: 负责销售的姓名"],
        ["   - 比例: 分配比例，默认 1（全额）；拆分时填小数如 0.3 或百分比 30%"],
        ["   - 说明: 备注（可选）"],
        *GROUP_NOTE_LINES,
        [""],
        ["5. 「KPI指标」sheet 列说明（Hero 圆环指标总数，万元）："],
        ["   - 页面: 年度达成 / 月度达成 / 季度达成"],
        ["   - 指标: 收入 / 回款"],
        ["   - 值(万元): 填数字 = 覆盖 KPI 卡片显示的指标总数（如 50000 = 5亿）"],
        ["     · 留空 = 不覆盖，KPI 卡片仍按指标文件合计（现状）"],
        ["     · 不影响表格/矩阵/部门卡里的明细指标（只改 Hero 圆环总数）"],
        ["   - 说明: 备注（可选）"],
        ["   - 注意: 数据总览页的年度 KPI 跟随「年度达成」的设置"],
        [""],
        ["6. 常见修改："],
        ["   - 换月份: 改「时间配置」的月度数据开始/结束日期"],
        ["   - 调整优先展示客户: 「展示规则」sheet → 第 4 列 配置项 = 优先展示 的那些行（一个客户一行，可下拉选）"],
        ["   - 显示全部客户: 把 配置项 = 优先展示 的所有行的「值」清空（或删行）"],
        ["   - 只显示指定客户: 配置项 = 客户筛选 的那些行，「值」填客户名（下拉选）；清空 = 不筛选"],
        ["   - 改销售归属: 在「销售归属」sheet 直接改对应行的 销售 / 比例"],
        ["   - 拆分多销售: 把一行复制成多行，各填不同销售和比例（合计需=1）"],
        [""],
        ["7. 「字段映射」sheet 列说明（清洗时的字段↔列名匹配，2026-09-17 新增）："],
        ["   - 数据源: 财务端 / 运营端（勿改）"],
        ["   - 来源: 收入 / 回款 / 广东公司 / 湖南公司 / 南方韶关（勿改）"],
        ["   - 标准字段: 系统内部字段名（勿改）"],
        ["   - 候选1..候选N: 按优先级从左到右尝试匹配源文件列名；留空 = 不参与"],
        ["     · 匹配规则是【全名精确匹配】（仅忽略首尾空白），不是关键词匹配"],
        ["     · 源文件列名改了，把新列名加到候选里保存即可，无需改 JSON/代码"],
        ["     · 同一字段内候选不能重复；每个字段至少保留 1 个候选"],
        ["   - 当前命中(只读): 上次清洗实际命中的列，写回时被忽略，仅供参考"],
        ["   - 说明: 备注（可选）"],
        ["   - 「排除标记」字段（仅财务端收入，回款无此字段）: 源表列名就叫「初始化」；值 = √ 的行属期初/历史单据迁移"],
        ["     清洗时整行剔除、不计入当月收入（2026-09-24 口径）；命中取值在 cleaning_config.json 的 排除标记值 里改"],
        ["   - 注意: 本 sheet 只控制「列映射」；文件名/引擎/金额乘数(金额除数)/过客户白名单等仍在 JSON 里改（金额单位换算见第 9 节）"],
        [""],
        ["8. 校验失败时生成器拒绝写回并提示原因，JSON 保持原样。"],
        ["   字段映射写回后 cleaning_config.json 会统一为标准 2 空格缩进格式（写前自动备份到 logs/）。"],
        [""],
        *UNIT_NOTE_LINES,
    ]
    for row in lines:
        ws2.append(row)
    ws2.column_dimensions["A"].width = 110
    ws2["A1"].font = Font(bold=True, size=14, color=COLOR_PRIMARY)
    ws2["A1"].fill = PatternFill("solid", fgColor=COLOR_BANNER_BG)
    ws2.row_dimensions[1].height = 28
    # 分节标题（"1." / "2." … 开头的行）加粗 + 浅蓝底，便于扫读
    for i in range(2, ws2.max_row + 1):
        v = ws2.cell(row=i, column=1).value
        if isinstance(v, str) and re.match(r"^\d+\.", v.strip()):
            c = ws2.cell(row=i, column=1)
            c.font = Font(bold=True, color=COLOR_PRIMARY, size=11.5)
            c.fill = PatternFill("solid", fgColor=COLOR_BANNER_BG)
            ws2.row_dimensions[i].height = 20
    finish(ws2, tab_color=TAB_COLORS["说明"])

    # ── Sheet 6: 字段映射（清洗列名映射的编辑层；「当前命中」由 logs/column_hits_*.txt 回填）──
    attach_mapping_sheet(
        wb,
        json.loads(CLEANING_CFG.read_text(encoding="utf-8")),
        read_latest_hits(),
    )

    # ── sheet 顺序整理：说明固定放最后 ──
    if "说明" in wb.sheetnames and wb.sheetnames[-1] != "说明":
        wb.move_sheet("说明", offset=len(wb.sheetnames) - 1 - wb.sheetnames.index("说明"))

    wb.save(EXCEL_PATH)
    try:
        shown = EXCEL_PATH.relative_to(BASE_DIR)
    except ValueError:  # 测试/自定义路径（不在项目内）
        shown = EXCEL_PATH
    print(f"✅ 已生成模板: {shown}")


# ──────────────────────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────────────────────
def main():
    args = sys.argv[1:]
    init = "--init" in args
    init_map = "--init-map" in args
    init_rules = "--init-rules" in args
    dry_run = "--dry-run" in args

    if init:
        init_excel_template()
        return 0

    if init_map:
        path = refresh_mapping_sheet()
        print(f"✅ 已刷新「{MAP_SHEET_NAME}」sheet（其余 sheet 未改动）: {path.relative_to(BASE_DIR)}")
        return 0

    if init_rules:
        path = refresh_rules_sheet()
        print(f"✅ 已刷新「{RULE_SHEET_NAME}」sheet（其余 sheet 未改动）: "
              f"{path.relative_to(BASE_DIR)}")
        return 0

    if not EXCEL_PATH.exists():
        print(f"未找到配置编辑器 Excel: {EXCEL_PATH.relative_to(BASE_DIR)}")
        print("请先运行: python scripts/config_excel_to_json.py --init")
        return 1

    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)

    # 1) 时间配置 → cleaning_config.json
    if "时间配置" in wb.sheetnames:
        ws = wb["时间配置"]
        time_config = excel_to_time_config(ws)
        new_cfg = update_cleaning_config(time_config, dry_run=dry_run)
        if dry_run:
            print("【DRY-RUN】将写回以下时间范围：")
            print(json.dumps(new_cfg["时间范围"], ensure_ascii=False, indent=2))
        else:
            print("✅ 已更新 cleaning_config.json 的「时间范围」：")
            for k, v in time_config.items():
                print(f"  - {k}: {json.dumps(v, ensure_ascii=False)}")
    else:
        print("⚠️  Excel 缺少「时间配置」sheet，跳过")

    # 2) 展示规则 → 展示规则.json
    if RULE_SHEET_NAME in wb.sheetnames:
        ws_r = wb[RULE_SHEET_NAME]
        rules = excel_to_display_rules(ws_r)
        new_rules = update_display_rules(rules, dry_run=dry_run)
        if dry_run:
            print("【DRY-RUN】将写回以下展示规则：")
            print(json.dumps(new_rules, ensure_ascii=False, indent=2))
        else:
            print("✅ 已更新 展示规则.json：")
            for page, obj in rules.items():
                keys = list(obj.keys())
                print(f"  - {page}: {keys}")
    else:
        print("⚠️  Excel 缺少「展示规则」sheet，跳过")

    # 3) KPI指标 → 展示规则.json 各页面 KPI指标 区块
    if "KPI指标" in wb.sheetnames:
        ws_k = wb["KPI指标"]
        kpi = excel_to_kpi(ws_k)
        new_rules = update_kpi_rules(kpi, dry_run=dry_run)
        if dry_run:
            print("【DRY-RUN】将写回以下 KPI 指标覆盖：")
            for page, m in kpi.items():
                print(f"  - {page}: {json.dumps(m, ensure_ascii=False)}")
        else:
            set_count = sum(
                1 for m in kpi.values() for v in m.values() if v is not None
            )
            print(f"✅ 已更新 展示规则.json 的 KPI指标 区块（{set_count} 项覆盖，其余按指标文件合计）")
    else:
        print("⚠️  Excel 缺少「KPI指标」sheet，跳过")

    # 4) 销售归属 → 客户销售归属.json
    if "销售归属" in wb.sheetnames:
        ws_a = wb["销售归属"]
        att = excel_to_attribution(ws_a)
        new_att = update_attribution(att, dry_run=dry_run)
        if dry_run:
            print("【DRY-RUN】将写回以下销售归属：")
            print(f"  母公司数: {len(new_att['客户归属'])}")
        else:
            n_subs = sum(len(g.get("子公司", {})) for g in att.values())
            print(f"✅ 已更新 客户销售归属.json：{len(att)} 母公司 / {n_subs} 子公司")
    else:
        print("⚠️  Excel 缺少「销售归属」sheet，跳过")

    # 5) 字段映射 → cleaning_config.json 的 数据源.*.列映射
    if MAP_SHEET_NAME in wb.sheetnames:
        cfg_now = json.loads(CLEANING_CFG.read_text(encoding="utf-8"))
        mapping, warns = excel_to_column_mapping(wb[MAP_SHEET_NAME], cfg_now)
        for w in warns:
            print(f"  ⚠️ {w}")
        _, changed = update_column_mapping(mapping, dry_run=dry_run)
        if dry_run:
            print("【DRY-RUN】列映射将发生变更：")
            for c in (changed or ["（无变更）"]):
                print(f"  - {c}")
        elif changed:
            print(f"✅ 已更新 cleaning_config.json 的「列映射」：{len(changed)} 个来源变更 → {', '.join(changed)}")
        else:
            print("✅ 字段映射与 JSON 一致（无需变更）")
    else:
        print(f"⚠️  Excel 缺少「{MAP_SHEET_NAME}」sheet，跳过")

    return 0


if __name__ == "__main__":
    sys.exit(main())
