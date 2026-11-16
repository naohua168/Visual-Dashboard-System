# Author: naohua168 <bai_bai168@qq.com>
"""年基线清洗逻辑 — 配置驱动文件路径（不再 glob 通配取首个）

新格式列结构：
  收入文件: 事业部, 核算单位, 确认时间, 客户, 所在省, 市场区域, 收入, 是否属于内部交易
  回款文件: 事业部, 核算单位, 到款时间, 客户, 所在省, 市场区域, 到款, 是否属于内部款项

输出标准列: 事业部, 金额, 客户, 法人主体, 日期
文件路径从 config/清洗配置/cleaning_config.json → 数据源.年基线数据 读取。
年份+月份范围从 config/清洗配置/cleaning_config.json → 时间范围.年基线数据 读取。
"""
import json
from pathlib import Path

import pandas as pd

from ..core import business_rules as br
from ..core.column_resolver import extract_columns, print_hit_columns
from ..core.config import BASE_DIR, CONFIG_PATH, get_yearly_baseline_path
from ..core.io_utils import ExcelBusyError, save_excel
from ..core.name_key import match_key
from ..core.utils import filter_by_dept_keep, log_step, rel_path

# 事业部全名→简称（config/清洗配置/业务规则.json → 事业部全称映射）
DEPT_MAP = br.dept_full_map()

STD_COLS = ["事业部", "金额", "客户", "法人主体", "日期"]

# 列映射兜底：cleaning_config.json 缺 `年基线数据.<收入|回款>.列映射` 时使用
DEFAULT_MAPPING: dict[str, dict[str, list[str]]] = {
    "收入": {
        "金额": ["收入", "到款", "收入金额", "到款金额", "金额"],
        "客户": ["客户名称", "客户名", "客户"],
        "法人主体": ["核算单位", "法人主体"],
        "部门": ["事业部"],
        "内部交易": ["是否属于内部交易", "是否属于内部款项", "内部交易", "内部款项"],
    },
    "回款": {
        "金额": ["收入", "到款", "收入金额", "到款金额", "金额"],
        "客户": ["客户名称", "客户名", "客户"],
        "法人主体": ["核算单位", "法人主体"],
        "部门": ["事业部"],
        "内部交易": ["是否属于内部款项", "是否属于内部交易", "内部款项", "内部交易"],
    },
}

# `内部交易标记值` 缺省值（与配置编辑器 FLAT_DEFAULTS 同口径）
INTERNAL_MARKS_DEFAULT = ["是"]


def _load_yearly_config() -> dict:
    """从 cleaning_config.json 读取年基线时间配置"""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        yc = cfg.get("时间范围", {}).get("年基线数据", {})
        year = yc.get("年份", 2025)
        months = yc.get("月份范围", [1, 6])
        return {"year": year, "months": months}
    except Exception:
        return {"year": 2025, "months": [1, 6]}


_YEARLY_CFG = None


def _get_yearly_cfg() -> dict:
    global _YEARLY_CFG
    if _YEARLY_CFG is None:
        _YEARLY_CFG = _load_yearly_config()
    return _YEARLY_CFG


def _col_remap(df, source_col, target_col, rename_map):
    """如果源列存在且目标列不存在，重命名"""
    if source_col in df.columns and target_col not in df.columns:
        df.rename(columns={source_col: target_col}, inplace=True)
        rename_map[target_col] = source_col


def _parse_yearly_date(val, default_year: int = 2024) -> str | None:
    """解析年基线日期字符串（用于旧格式数据兼容）

    "3月" → "2024-03-01", "1-4月" → "2024-04-01"（取末月）
    """
    import math
    import re
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    s = str(val).strip()
    if not s:
        return None
    # 匹配 "X-Y月" 格式
    m = re.match(r'(\d+)-(\d+)月', s)
    if m:
        return f"{default_year}-{int(m.group(2)):02d}-01"
    # 匹配 "X月" 格式
    m = re.match(r'(\d+)月', s)
    if m:
        return f"{default_year}-{int(m.group(1)):02d}-01"
    return None


# ──────────────────────────────────────────────────────────────
# 法人主体简称→全称（通用映射，适用于新老数据）
# ──────────────────────────────────────────────────────────────
_ENTITY_FULL = br.entity_alias()  # 配置驱动（业务规则.json → 法人简称映射）


def _source_spec(config, kind: str) -> dict:
    """`年基线数据.<收入|回款>` 配置节点（含 列映射 / 内部交易标记值 / 事业部取值）"""
    node = ((config or {}).get("年基线数据") or {}).get(kind)
    return node if isinstance(node, dict) else {}


def _column_mapping(spec: dict, kind: str) -> dict:
    """列映射：配置优先，缺失/为空时回退 DEFAULT_MAPPING（历史 JSON 也能跑）"""
    cm = spec.get("列映射")
    if isinstance(cm, dict) and cm:
        return {k: list(v) for k, v in cm.items() if not str(k).startswith("_")}
    return {k: list(v) for k, v in DEFAULT_MAPPING[kind].items()}


def _clean_single(label, file_path, mapper=None, spec=None):
    """清洗单个年基线文件（收入或回款）

    列名从配置读取（配置编辑器「字段映射」→ 数据源=年基线数据），
    缺列候选时回退 DEFAULT_MAPPING：
      - 收入: 事业部/核算单位/确认时间/客户/收入/内部交易
      - 回款: 事业部/核算单位/到款时间/客户/到款/内部款项
    """
    spec = spec or {}
    if not file_path.exists():
        log_step("年%s" % label, "文件未找到: %s" % rel_path(file_path), "WARN")
        return None

    log_step("年%s" % label, "读取 %s" % file_path.name)
    df = pd.read_excel(file_path)
    total_in = len(df)
    log_step("年%s" % label, "原始: %d行 x %d列" % (total_in, len(df.columns)))
    log_step("年%s" % label, "原始列: %s" % str(list(df.columns)))

    # ── 列提取（候选列名来自配置）──
    # 内部交易 / 法人主体 是可选字段：源表没有该列时补空并继续
    df = extract_columns(df, _column_mapping(spec, label),
                         optional_fields={"内部交易", "法人主体"})
    print_hit_columns(df, "年基线%s" % label)

    # 标准字段名统一：映射里叫「部门」（与其他来源同口径），年基线输出列叫「事业部」
    if "部门" in df.columns and "事业部" not in df.columns:
        df = df.rename(columns={"部门": "事业部"})
    if "法人主体" not in df.columns:
        df["法人主体"] = ""

    # 简称→全称映射（按匹配键查表：全角半角/空白差异也能命中）
    entity_keys = {match_key(k): v for k, v in _ENTITY_FULL.items()}
    df["法人主体"] = df["法人主体"].map(
        lambda v: entity_keys.get(match_key(v), v)
    )

    # ── 内部交易过滤（命中 `内部交易标记值` 的行排除，与运营端逻辑一致）──
    if "内部交易" in df.columns:
        marks = [str(v).strip() for v in (spec.get("内部交易标记值") or INTERNAL_MARKS_DEFAULT)]
        marks = [m for m in marks if m]
        if marks:
            before = len(df)
            df = df[~df["内部交易"].astype(str).str.strip().isin(marks)].copy()
            if before - len(df) > 0:
                log_step("年%s" % label,
                         "内部交易过滤: 排除%d行, 保留%d行（取值:%s）"
                         % (before - len(df), len(df), "/".join(marks)), "OK")
    else:
        log_step("年%s" % label, "内部交易列不存在，跳过过滤", "WARN")

    # ── 内部交易排除名单过滤（与财务端/销售层口径一致，防御未标记数据）──
    if mapper is not None and "客户" in df.columns:
        before = len(df)
        df = df[~df["客户"].astype(str).str.strip().apply(mapper.is_excluded)].copy()
        if before - len(df) > 0:
            log_step("年%s" % label,
                     "内部交易名单过滤: 排除%d行, 保留%d行" % (before - len(df), len(df)), "OK")

    # ── 事业部映射 ──
    if mapper:
        try:
            df["事业部"] = (
                df["事业部"].apply(mapper.map_income_dept)
                .fillna(df["事业部"].map(DEPT_MAP))
            )
        except Exception:
            df["事业部"] = df["事业部"].map(DEPT_MAP).fillna(df["事业部"])
    else:
        df["事业部"] = df["事业部"].map(DEPT_MAP).fillna(df["事业部"])
    log_step("年%s" % label, "事业部分布: %s" % str(df["事业部"].value_counts().to_dict()))
    # 事业部取值（配置决定只取哪些事业部；缺省/空 = 不限制）
    if mapper is not None:
        df = filter_by_dept_keep(df, spec, mapper, "年基线%s" % label, "income")

    # ── 金额转数值 ──
    df["金额"] = pd.to_numeric(df["金额"], errors="coerce").fillna(0.0)

    # ── 日期: 从配置读取年份+末月 → YYYY-MM-01 ──
    yc = _get_yearly_cfg()
    year = yc["year"]
    last_month = yc["months"][-1]
    df["日期"] = f"{year}-{last_month:02d}-01"

    # ── 标准列输出 ──
    for col in STD_COLS:
        if col not in df.columns:
            df[col] = ""
    df = df[STD_COLS]

    log_step("年%s" % label, "清洗后: %d行, 金额合计: %.2f" % (len(df), df["金额"].sum()), "OK")
    return df


def clean_yearly(source_dir=None, mapper=None):
    """清洗年基线数据（收入+回款）— 配置驱动文件路径

    Args:
        source_dir: 可选路径（None 时从 config 读取；支持 --source= 单文件覆盖）
        mapper: 部门映射器

    Returns:
        dict: {"收入": DataFrame, "回款": DataFrame} 或 None
    """
    # ── 从配置加载文件路径 + 列映射（配置编辑器「字段映射」→ 年基线数据）──
    inc_path = None
    pay_path = None
    inc_spec: dict = {}
    pay_spec: dict = {}
    try:
        from ..core.config import load_config
        config = load_config()
        inc_path = get_yearly_baseline_path(config, "收入")
        pay_path = get_yearly_baseline_path(config, "回款")
        inc_spec = _source_spec(config, "收入")
        pay_spec = _source_spec(config, "回款")
    except (KeyError, FileNotFoundError, ImportError):
        pass

    if source_dir is not None:
        # 用户显式指定路径时覆盖配置
        src = Path(source_dir)
        if src.is_file() and src.suffix == ".xlsx":
            name = src.stem
            inc_path = src if "收入" in name else None
            pay_path = src if "回款" in name else None
            if not inc_path and not pay_path:
                inc_path = src
        else:
            inc_path = None
            pay_path = None

    # 校验文件存在
    if inc_path and not inc_path.exists():
        log_step("年基线", f"收入文件不存在: {rel_path(inc_path)}", "WARN")
        inc_path = None
    if pay_path and not pay_path.exists():
        log_step("年基线", f"回款文件不存在: {rel_path(pay_path)}", "WARN")
        pay_path = None

    if inc_path is None and pay_path is None:
        log_step("年基线", "往年收入/回款数据文件均不存在（请检查 config → 数据源 → 年基线数据）", "WARN")
        return None

    results = {}
    if inc_path:
        inc_df = _clean_single("收入", inc_path, mapper, inc_spec)
        if inc_df is not None:
            results["收入"] = inc_df
    if pay_path:
        pay_df = _clean_single("回款", pay_path, mapper, pay_spec)
        if pay_df is not None:
            results["回款"] = pay_df

    if not results:
        log_step("年基线", "无数据可处理", "WARN")
        return None
    return results


def run_clean(mapper=None):
    """运行年基线清洗并写入输出目录（输出路径由 config → 输出.往年收入/往年回款 控制）"""
    yc = _get_yearly_cfg()
    log_step("年基线", "=" * 50)
    log_step("年基线", "开始清洗年基线数据")
    log_step("年基线", "年份: %d, 月份范围: %d-%d月" % (yc["year"], yc["months"][0], yc["months"][-1]))

    results = clean_yearly(mapper=mapper)
    if results is None:
        log_step("年基线", "源文件缺失，跳过年基线清洗", "WARN")
        return {}

    _LABEL_MAP = {"收入": "往年收入", "回款": "往年回款"}
    # 从配置读取输出目录
    try:
        from ..core.config import load_config
        config = load_config()
        out_base = {k: BASE_DIR / config["输出"].get(v, f"data/sheets/系统数据清理/{v}/")
                    for k, v in _LABEL_MAP.items()}
    except Exception:
        out_base = {k: BASE_DIR / "data" / "sheets" / "系统数据清理" / v
                    for k, v in _LABEL_MAP.items()}

    for label, df in results.items():
        dir_name = _LABEL_MAP.get(label, label)
        out_dir = out_base.get(label, BASE_DIR / "data" / "sheets" / "系统数据清理" / dir_name)
        out_path = out_dir / ("%s.xlsx" % dir_name)
        try:
            save_excel(df, out_path)  # 被 Excel 占用 → 友好提示 + 退出码 3
        except ExcelBusyError as e:
            log_step("年%s" % label, "❌ 写入失败：%s" % e, "ERROR")
            raise SystemExit(3) from e
        log_step("年%s" % label,
                 "写入: %s (%d行, 金额%.2f)" % (out_path, len(df), df["金额"].sum()), "OK")

    return results
