# Author: naohua168 <bai_bai168@qq.com>
"""配置编辑器的取值常量（时间键、策略白名单、中英映射、日期格式）

由 scripts/config_excel_to_json.py 拆分而来（行为不变，见 logs/_dryrun_before.txt 比对）。
"""
from __future__ import annotations

import re
from pathlib import Path
from engine.core import business_rules as br


TIME_KEYS = ["年度累计", "月度数据", "季度累计筛选", "年基线数据"]


DYNAMIC_STRATEGIES = ["last_full_month", "last_full_quarter"]


MODE_ALIASES = {
    "static": "static", "手填日期": "static", "手填": "static",
    "dynamic": "dynamic", "自动计算": "dynamic", "自动": "dynamic",
}


STRATEGY_ALIASES = {
    "last_full_month": "last_full_month", "最近完整月": "last_full_month",
    "last_full_quarter": "last_full_quarter", "最近完整季度": "last_full_quarter",
}


MODE_LABELS = {"static": "手填日期", "dynamic": "自动计算"}


STRATEGY_LABELS = {"last_full_month": "最近完整月", "last_full_quarter": "最近完整季度"}


DATE_CELL_FMT = "yyyy-mm-dd hh:mm:ss"


BASE_DIR = Path(__file__).parents[2]   # scripts/editor/ 比原脚本多一层


EXCEL_PATH = BASE_DIR / "config" / "配置编辑器.xlsx"


CLEANING_CFG = BASE_DIR / "config" / "清洗配置" / "cleaning_config.json"


DISPLAY_RULES_CFG = BASE_DIR / "config" / "前端渲染" / "展示规则.json"


ATTRIBUTION_CFG = BASE_DIR / "config" / "清洗配置" / "客户销售归属.json"


TIME_KEYS = ["年度累计", "月度数据", "季度累计筛选", "年基线数据"]


DYNAMIC_STRATEGIES = ["last_full_month", "last_full_quarter"]


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


RULE_PAGES = ["数据总览", "年度达成", "月度达成", "季度达成", "销售达成", "年度同比"]


ATT_HEADERS = ["母公司", "子公司", "指标", "部门", "销售", "比例", "说明"]


METRIC_SEP = "/"


METRIC_VALUES = ["收入", "回款", "收入/回款"]


METRIC_BOTH = METRIC_VALUES[-1]


DEPT_VALUES = br.departments()


KPI_PAGES = ["年度达成", "月度达成", "季度达成"]


KPI_METRICS = ["收入", "回款"]


KPI_HEADERS = ["页面", "指标", "值(万元)", "说明"]


GROUP_NOTE_LINES: list[list[str]] = [
    ["   - 多组配置(同一子公司在多个母公司下)的归属规则（2026-09-28）:"],
    ["     · 广东自有客户 <-> 零部件客户/福建市场 等: 法人=广东汽车检测中心有限公司 → 广东自有客户; 其他法人 → 另一个父组"],
    ["     · 比亚迪汽车工业有限公司 <-> 比亚迪电池: **只对两父组下同时出现的子公司判断**; 法人=广东汽车检测中心 → 比亚迪汽车工业, 其他法人 → 比亚迪电池"],
    ["     · 其他任意两组重复配置: 无规则 → 取先出现的分组, 且弹窗明细会与矩阵行对不上（尽量避免重复配置）"],
    ["   - 核对方法: 客户矩阵某行的数字 = 该行「子公司明细」抽屉里各子行相加（两处已统一口径）"],
]


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


NAME_NOTE_LINES: list[list[str]] = [
    ["10. 名称匹配（全角/半角符号差异）— 2026-09-29 起统一归一："],
    ["   - 客户名/子公司名/法人主体名比较时，以下差异一律忽略：全角括号（）与半角括号()、全角字母数字、"],
    ["     空格（含全角空格）、零宽字符、英文大小写。如 法雷奥汽车内部控制（深圳）有限公司 = 法雷奥汽车内部控制(深圳)有限公司"],
    ["   - 不影响展示：表里显示的名字仍按配置/源表原样，不会被改写"],
    ["   - ⚠ 但同一家公司不要在本表配置两遍（如一条全角括号、一条半角括号）："],
    ["     运行时（配置同步 / 销售拆分）会打印「仅符号差异的重复写法 N 组」提示，请人工合并成一条"],
    ["   - 不做的合并: 括号里的地名不同（（深圳）vs（上海））或增删后缀（有限公司）**不算同一个名字**，不会自动合并"],
]


OUTPUT_NOTE_LINES: list[list[str]] = [
    ["11. 数据质量与产物（2026-09-29 起）："],
    ["   - 每次运行在 <输出目录>/数据校验/ 只留 **1 个** 文件：数据质量摘要_<运行号>.xlsx，含 4 个 sheet ——"],
    ["     概览（各步骤 ERROR/WARN/丢弃行数）、问题清单、丢弃汇总、未匹配明细（来源/客户名/金额/日期）"],
    ["   - 客户白名单未命中的行写进「未匹配明细」sheet，收尾打印「白名单未匹配丢弃: N 行 / X 万元」；"],
    ["     各步骤中间件（数据质量摘要_<步骤>_<运行号>.json）在收尾合并后自动删除，超 14 天的旧报告自动清理"],
    ["   - 关键来源（财务端主表 / 广东 / 湖南 / 南方韶关 / 运营端）读取失败 → ERROR：整次运行以非零退出码结束"],
    ["     应急出图可加 --ignore-data-issues；空表只记 WARN（当月可能确实没数据）"],
    ["   - 销售人名 / 父组名 / 法人主体 / 比亚迪子公司清单 已外置到 config/清洗配置/业务规则.json（改它即可，无需改代码）"],
    ["   - 交付物校验（bin/main.py 的 verify 步骤）：6 页看板 + 数据总表 + 销售完成度表 是否齐全且非空"],
    ["   - 销售完成度表已并入主流程（bin/main.py 的 report 步骤），不再由 run_all.bat 单独调用"],
]


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


DATE_CELL_FMT = "yyyy-mm-dd hh:mm:ss"


_STALE_NOTE_RE = re.compile(r"^_(.+)说明$")
