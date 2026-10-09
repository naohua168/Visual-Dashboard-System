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
    python scripts/config_excel_to_json.py --refresh-notes  # 只把「说明」sheet 的新增分节补到末尾

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
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from engine.core import business_rules as br  # noqa: E402
from engine.core.utils import rel_path  # noqa: E402  （提示路径统一相对项目根显示）

EXCEL_PATH = BASE_DIR / "config" / "配置编辑器.xlsx"
CLEANING_CFG = BASE_DIR / "config" / "清洗配置" / "cleaning_config.json"
DISPLAY_RULES_CFG = BASE_DIR / "config" / "前端渲染" / "展示规则.json"
ATTRIBUTION_CFG = BASE_DIR / "config" / "清洗配置" / "客户销售归属.json"

# 支持的时间配置键 → 说明
TIME_KEYS = ["年度累计", "月度数据", "季度累计筛选", "年基线数据"]

# dynamic 策略白名单（与 engine/core/config.py _STRATEGY_REGISTRY 对应）
DYNAMIC_STRATEGIES = ["last_full_month", "last_full_quarter"]

# ── 「模式」「动态策略」在 Excel 里显示中文（2026-09-30 用户口径：英文术语看不懂）──
#    Excel（编辑层，中文）↔ 内部值（JSON 事实源，英文）双向映射；
#    旧文件里的 static / dynamic / last_full_month / last_full_quarter 继续兼容解析。
MODE_LABELS = {"static": "手填日期", "dynamic": "自动计算"}
MODE_ALIASES = {
    "static": "static", "手填日期": "static", "手填": "static",
    "dynamic": "dynamic", "自动计算": "dynamic", "自动": "dynamic",
}
STRATEGY_LABELS = {"last_full_month": "最近完整月", "last_full_quarter": "最近完整季度"}
STRATEGY_ALIASES = {
    "last_full_month": "last_full_month", "最近完整月": "last_full_month",
    "last_full_quarter": "last_full_quarter", "最近完整季度": "last_full_quarter",
}

HEADERS = ["配置名", "模式", "动态策略", "开始日期", "结束日期", "年份", "月份范围", "说明"]

# 展示规则：sheet 结构 / 解析 / 校验 / 下拉 全在 scripts/display_rules_sheet.py
# （2026-09-28 重做 —— 旧「路径」结构仍可解析，但模板已改为 页面|区块|配置项|值|可选值|说明）
# 顶层页面键（固定顺序，与看板导航一致）
RULE_PAGES = ["数据总览", "年度达成", "月度达成", "季度达成", "销售达成", "年度同比"]

# 销售归属 sheet 列
ATT_HEADERS = ["母公司", "子公司", "指标", "部门", "销售", "比例", "说明"]

# 指标取值（「收入/回款」= 斜杠分隔，表示同时写入两个指标；下拉用它，逗号不再是分隔符）
METRIC_SEP = "/"
METRIC_VALUES = ["收入", "回款", "收入/回款"]
METRIC_BOTH = METRIC_VALUES[-1]  # 收入与回款归属一致时用这一行（模板/自动归入都写它）


def split_metric_value(value: str) -> list[str]:
    """拆分「指标」列取值 → 指标名列表

    现行写法用斜杠：`收入/回款`；历史文件的逗号写法（`收入,回款`）继续兼容。
    斜杠不会和 Excel 下拉的内联列表分隔符（逗号）冲突，否则下拉里选不到合并项。
    """
    return [p.strip() for p in re.split(r"[/,，、]+", value or "") if p.strip()]

# 部门取值（唯一来源 业务规则.json → 部门.列表，与看板/引擎同一套）
DEPT_VALUES = br.departments()

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

# 「说明」sheet 第 10 节：名称匹配（全角半角/空白差异）—— 2026-09-29 新增
# 供 `--init` 生成模板、以及刷新现有 Excel 说明页时共用，避免两处文案漂移
NAME_NOTE_LINES: list[list[str]] = [
    ["10. 名称匹配（全角/半角符号差异）— 2026-09-29 起统一归一："],
    ["   - 客户名/子公司名/法人主体名比较时，以下差异一律忽略：全角括号（）与半角括号()、全角字母数字、"],
    ["     空格（含全角空格）、零宽字符、英文大小写。如 法雷奥汽车内部控制（深圳）有限公司 = 法雷奥汽车内部控制(深圳)有限公司"],
    ["   - 不影响展示：表里显示的名字仍按配置/源表原样，不会被改写"],
    ["   - ⚠ 但同一家公司不要在本表配置两遍（如一条全角括号、一条半角括号）："],
    ["     运行时（配置同步 / 销售拆分）会打印「仅符号差异的重复写法 N 组」提示，请人工合并成一条"],
    ["   - 不做的合并: 括号里的地名不同（（深圳）vs（上海））或增删后缀（有限公司）**不算同一个名字**，不会自动合并"],
]

# 「说明」sheet 第 11 节：数据质量与产物（2026-09-29 新增；同日改为「一次运行一个文件」）
OUTPUT_NOTE_LINES: list[list[str]] = [
    ["11. 数据质量与产物（2026-09-29 起）："],
    ["   - 每次运行在 <输出目录>/数据校验/ 只留 **1 个** 文件：数据质量摘要_<运行号>.xlsx，含 4 个 sheet ——"],
    ["     概览（各步骤 ERROR/WARN/丢弃行数）、问题清单、丢弃汇总、未匹配明细（来源/客户名/金额/日期）"],
    ["   - 客户白名单未命中的行写进「未匹配明细」sheet，收尾打印「白名单未匹配丢弃: N 行 / X 万元」；"],
    ["     各步骤中间件（数据质量摘要_<步骤>_<运行号>.json）在收尾合并后自动删除，超 14 天的旧报告自动清理"],
    ["   - 关键来源（财务端主表 / 广东 / 湖南 / 南方韶关 / 运营端）读取失败 → ERROR：整次运行以非零退出码结束"],
    ["     应急出图可加 --ignore-data-issues；空表只记 WARN（当月可能确实没数据）"],
    ["   - 销售人名 / 父组名 / 法人主体 / 比亚迪子公司清单 已外置到 config/清洗配置/业务规则.json（改它即可，无需改代码）"],
    ["   - 交付物校验（main.py 的 verify 步骤）：6 页看板 + 数据总表 + 销售完成度表 是否齐全且非空"],
    ["   - 销售完成度表已并入主流程（main.py 的 report 步骤），不再由 run_all.bat 单独调用"],
]

# 「说明」sheet 第 12 节：业务规则.json（外部业务参数一览）
BIZ_NOTE_LINES: list[list[str]] = [
    ["12. 业务规则.json（config/清洗配置/，2026-09-29 起）—— 特殊口径都放这里，改它不用改代码："],
    ["   - 销售人名 / 父组名（广东自有客户、零部件客户、比亚迪两父组、南方韶关）/ 法人主体（含深圳标记）"],
    ["   - 部门列表（4 大事业部的列顺序）/ 事业部全称映射 / 法人简称映射"],
    ["   - 广东自有客户自动归入：状态文件、最短客户名长度、黑名单、列名候选、内部交易标记值"],
    ["   - 比亚迪子公司清单（同时挂两个父组时按法人主体区分销售）"],
    ["   - 期初剔除默认标记值（初始化=√ 等；候选列名在「字段映射」sheet）"],
    ["   - 归入规则：南方韶关 / 广东自有 / 零部件 / 比亚迪 / 科技公司 / 白名单 的口径说明（供交接排查）"],
    ["   - 查看当前生效值（含默认值合并结果）：python -m engine.core.business_rules"],
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
    """单元格值 → 干净字符串（Excel 日期/数字转文本）

    2026-09-30 修复：日期时间单元格原本只取「日期」部分，把 `2026-09-30 23:59:59`
    截成 `2026-09-30` → 结束时间退化成当天 00:00:00，导致**当天数据被整段排除**。
    现在：时分秒全为 0 → 仍输出 `YYYY-MM-DD`（保持简洁）；否则保留 `YYYY-MM-DD HH:MM:SS`。
    """
    if value is None:
        return ""
    if isinstance(value, datetime):
        if (value.hour, value.minute, value.second) == (0, 0, 0):
            return value.strftime("%Y-%m-%d")
        return value.strftime("%Y-%m-%d %H:%M:%S")
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
    # 写 "1-9" 时若单元格不是文本格式，Excel 会当日期存成序列号（46031）→ 这里给出可操作的提示
    if nums and (len(nums) != 2 or any(n < 1 or n > 12 for n in nums)):
        raise ValueError(
            f"月份范围格式错误: {raw!r}（应为 '1-8' 或 '1,8'）"
            "；若该单元格显示成日期（如 2026/1/9），说明被 Excel 识别成了日期 —— "
            "请把单元格格式设为「文本」后重新填 1-9"
        )
    return nums


# 「时间配置」开始/结束日期列的显示格式：两者都写到秒（2026-10-09 起，开始时间不再只显示到日）
DATE_CELL_FMT = "yyyy-mm-dd hh:mm:ss"


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
               "「模式」选「手填日期」= 自己填开始/结束日期；选「自动计算」= 系统按「动态策略」自动算"
               "（最近完整月 / 最近完整季度），不用填日期；「结算模式」行的值填在「模式」列。", len(HEADERS))
    header_row(ws, HEADERS, row=2)

    row_idx = 3
    for key in TIME_KEYS:
        spec = tr.get(key, {})
        fill_color = _cell_fill(key)
        if spec.get("_mode") == "dynamic":
            values = [key, MODE_LABELS["dynamic"],
                      STRATEGY_LABELS.get(spec.get("_strategy", ""), spec.get("_strategy", "")),
                      "", "", "", "", spec.get("_使用方", "")]
        elif key == "年基线数据":
            months = spec.get("月份范围", [])
            values = [
                key, MODE_LABELS["static"], "",
                "", "", spec.get("年份", ""),
                f"{months[0]}-{months[1]}" if len(months) == 2 else "",
                spec.get("_使用方", ""),
            ]
        else:
            values = [
                key, MODE_LABELS["static"], "",
                spec.get("start_date", ""), spec.get("end_date", ""),
                "", "", spec.get("_使用方", ""),
            ]
        for col, v in enumerate(values, 1):
            if col in (4, 5):
                v = _date_cell_value(v)  # 开始/结束日期：写成 datetime，单元格显示到秒
            c = data_cell(ws, row_idx, col, v,
                          editable=col in (2, 3, 4, 5, 6, 7), readonly=(col == 8),
                          wrap=(col == 8))
            if col in (4, 5) and isinstance(c.value, datetime):
                c.number_format = DATE_CELL_FMT
            elif col == 7:  # 月份范围：文本格式，防止 Excel 把 1-9 存成日期（2026/1/9）
                c.number_format = "@"
            if col == 1:  # 配置名列保留按行的身份色（年度/月度/季度/年基线）
                c.fill = PatternFill("solid", fgColor=fill_color)
        row_idx += 1

    last_time_row = row_idx - 1   # 4 个配置行的最后一行（结算模式行不参与下面两个下拉）

    # 结算模式行（值填在「模式」列：月底结算 / 常规）
    settle = tr.get("结算模式", {})
    settle_row = None
    if settle:
        settle_row = row_idx
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

    dv_mode = DataValidation(type="list", formula1='"' + ",".join(MODE_LABELS.values()) + '"',
                             allow_blank=True, promptTitle="怎么填（二选一）",
                             prompt="手填日期 = 自己填「开始日期 / 结束日期」；"
                                    "自动计算 = 按右侧「动态策略」自动算，不用填日期")
    dv_mode.add(f"B3:B{last_time_row}")
    ws.add_data_validation(dv_mode)
    dv_strat = DataValidation(type="list", formula1='"' + ",".join(STRATEGY_LABELS.values()) + '"',
                              allow_blank=True, promptTitle="怎么填（仅自动计算时用）",
                              prompt="最近完整月 / 最近完整季度（例：9 月跑批 → 最近完整月 = 8 月）")
    dv_strat.add(f"C3:C{last_time_row}")
    ws.add_data_validation(dv_strat)
    if settle_row:  # 结算模式行单独给下拉（原先被普通模式下拉误罩，选不到合法值）
        dv_settle = DataValidation(type="list", formula1='"月底结算,常规"', allow_blank=True,
                                   promptTitle="怎么填", prompt="月底结算 / 常规")
        dv_settle.add(f"B{settle_row}")
        ws.add_data_validation(dv_settle)
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
            # 判断收入/回款是否同构：同构 → 指标=收入/回款 一行
            inc = sub_data.get("收入", {})
            pay = sub_data.get("回款", {})
            if inc == pay and inc:
                note = sub_data.get("_说明", "")
                for dept, sales_map in inc.items():
                    for sales, ratio in sales_map.items():
                        vals = [parent, sub, METRIC_BOTH, dept, sales,
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
                               prompt="收入 / 回款 / 收入/回款（收入与回款归属一致时填「收入/回款」一行搞定）")
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
        ["   - 模式: 手填日期（默认：自己填开始/结束日期）或 自动计算（按「动态策略」自动算，不用填日期）"],
        ["     · 兼容旧写法 static = 手填日期、dynamic = 自动计算，历史文件不用改"],
        ["   - 动态策略: 仅在「模式 = 自动计算」时选：最近完整月 / 最近完整季度"],
        ["     · 例：9 月跑批 → 最近完整月 = 8/1~8/31；最近完整季度 = 4/1~6/30"],
        ["     · 注意：它取的是「上一个完整周期」，不是当月；要统计「当月」请继续用「手填日期」"],
        ["   - 开始日期/结束日期: 格式 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS（两列都显示到秒，如 2026-10-01 00:00:00）"],
        ["     · 结束只写到「日」时，系统按当天 23:59:59 处理（不会漏掉当天数据）"],
        ["   - 年份/月份范围: 仅年基线数据使用，如 2025 / 1-8"],
        ["     · 月份范围单元格是文本格式，请勿改成日期格式（否则 1-9 会被存成 2026/1/9，同步会报错）"],
        ["   - 说明: 填写配置用途（可选）"],
        [""],
        *RULE_NOTE_LINES,
        ["4. 「销售归属」sheet 列说明："],
        ["   - 母公司: 客户归组的母公司名（如 广州小鹏汽车科技有限公司）"],
        ["   - 子公司: 实际结算主体名（=母公司时表示本部）"],
        ["   - 指标: 收入 / 回款 / 收入/回款（斜杠分隔 = 两个指标同构时用后者，一行搞定）"],
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
        [""],
        *NAME_NOTE_LINES,
        [""],
        *OUTPUT_NOTE_LINES,
        [""],
        *BIZ_NOTE_LINES,
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
def _note_blocks() -> list[list[list[str]]]:
    """说明书里由代码维护的分节（顺序 = 写入顺序；每项是一个完整分节的行列表）"""
    return [UNIT_NOTE_LINES, NAME_NOTE_LINES, OUTPUT_NOTE_LINES, BIZ_NOTE_LINES]


def _sync_note_block(ws, block: list[list[str]]) -> str:
    """让「说明」sheet 里某个分节与代码文案一致，返回 'updated' / 'appended' / 'same'

    - 找不到该分节标题 → 追加到末尾（前空一行）
    - 找到但正文有变（如「一次运行一个文件」改口径）→ **原地重写该分节**（不动其它行）
    """
    title = str(block[0][0]).strip()
    rows = {r: str(ws.cell(row=r, column=1).value).strip() for r in range(1, ws.max_row + 1)}
    start = next((r for r, v in rows.items() if v == title), None)

    if start is None:
        row = ws.max_row + 2
        for line in block:
            cell = ws.cell(row=row, column=1, value=line[0])
            if re.match(r"^\d+\.", str(line[0]).strip()):
                cell.font = Font(bold=True, color=COLOR_PRIMARY, size=11.5)
                cell.fill = PatternFill("solid", fgColor=COLOR_BANNER_BG)
            row += 1
        return "appended"

    # 该分节的行范围：标题 → 下一个分节标题（或表尾）之前，去掉尾部空行
    # （分节之间的空行是排版，不属于分节内容 —— 否则每次刷新都会删掉一行，越刷越短）
    end = ws.max_row
    for r in range(start + 1, ws.max_row + 1):
        if re.match(r"^\d+\.", rows.get(r, "")):
            end = r - 1
            break
    while end > start and not str(ws.cell(row=end, column=1).value or "").strip():
        end -= 1
    have = [str(ws.cell(row=r, column=1).value) for r in range(start, end + 1)]
    want = [line[0] for line in block]
    if have == want:
        return "same"

    need, cur = len(want), len(have)
    if need < cur:
        ws.delete_rows(start + need, cur - need)
    elif need > cur:
        ws.insert_rows(start + cur, need - cur)
    for i, text in enumerate(want):
        cell = ws.cell(row=start + i, column=1, value=text)
        if i == 0:
            cell.font = Font(bold=True, color=COLOR_PRIMARY, size=11.5)
            cell.fill = PatternFill("solid", fgColor=COLOR_BANNER_BG)
        else:
            cell.font = Font(size=11)
    return "updated"


def refresh_note_sheet() -> Path:
    """让「说明」sheet 与代码里的文案同步：缺的分节追加、改过的分节原地重写

    用途：说明书新增/修订章节（如第 11 节改「一次运行一个文件」）后不必跑 `--init`
    重建整本（重建会覆盖手工编辑）；本命令只碰代码维护的那几个分节，其它内容一行不动。
    """
    wb = openpyxl.load_workbook(EXCEL_PATH)
    if "说明" not in wb.sheetnames:
        raise ValueError("工作簿缺少「说明」sheet")
    ws = wb["说明"]
    changed = [_sync_note_block(ws, block) for block in _note_blocks()]
    if all(c == "same" for c in changed):
        return EXCEL_PATH
    wb.save(EXCEL_PATH)
    return EXCEL_PATH


def main():
    args = sys.argv[1:]
    init = "--init" in args
    init_map = "--init-map" in args
    init_rules = "--init-rules" in args
    refresh_notes = "--refresh-notes" in args
    dry_run = "--dry-run" in args

    if init:
        init_excel_template()
        return 0

    if refresh_notes:
        path = refresh_note_sheet()
        print(f"✅ 已刷新「说明」sheet 新增分节（其余 sheet 未改动）: {path.relative_to(BASE_DIR)}")
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
