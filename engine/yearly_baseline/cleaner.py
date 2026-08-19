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

from ..core.config import BASE_DIR, CONFIG_PATH, get_yearly_baseline_path
from ..core.utils import log_step

# 事业部全名→简称
DEPT_MAP = {
    "检测工程事业部": "检测",
    "信息智能事业部": "信息",
    "能源动力事业部": "能源",
    "海外事业部": "海外",
}

STD_COLS = ["事业部", "金额", "客户", "法人主体", "日期"]


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
_ENTITY_FULL = {
    "广东公司": "广东汽车检测中心有限公司",
    "湖南公司": "中汽院智能网联汽车检测中心（湖南）有限公司",
}


def _clean_single(label, file_path, mapper=None):
    """清洗单个年基线文件（收入或回款）

    适配新格式列：
      - 收入: 事业部/核算单位/确认时间/客户/收入
      - 回款: 事业部/核算单位/到款时间/客户/到款
    """
    if not file_path.exists():
        log_step("年%s" % label, "文件未找到: %s" % file_path, "WARN")
        return None

    log_step("年%s" % label, "读取 %s" % file_path.name)
    df = pd.read_excel(file_path)
    total_in = len(df)
    log_step("年%s" % label, "原始: %d行 x %d列" % (total_in, len(df.columns)))
    log_step("年%s" % label, "原始列: %s" % str(list(df.columns)))

    rename_map = {}

    # ── 列重命名 ──
    # 金额: 收入/到款 → 金额
    for src in ["收入", "到款", "收入金额", "到款金额", "金额"]:
        if src in df.columns:
            _col_remap(df, src, "金额", rename_map)
            break

    # 法人主体: 核算单位 → 法人主体
    for src in ["核算单位", "法人主体"]:
        if src in df.columns:
            _col_remap(df, src, "法人主体", rename_map)
            break
    if "法人主体" not in df.columns:
        df["法人主体"] = ""

    # 简称→全称映射
    df["法人主体"] = (
        df["法人主体"].astype(str).str.strip()
        .map(_ENTITY_FULL).fillna(df["法人主体"])
    )

    # 客户名
    for src in ["客户名称", "客户名", "客户"]:
        if src in df.columns:
            _col_remap(df, src, "客户", rename_map)
            break

    log_step("年%s" % label, "重命名: %s" % str(rename_map))

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
    # ── 从配置加载文件路径 ──
    inc_path = None
    pay_path = None
    try:
        from ..core.config import load_config
        config = load_config()
        inc_path = get_yearly_baseline_path(config, "收入")
        pay_path = get_yearly_baseline_path(config, "回款")
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
        log_step("年基线", f"收入文件不存在: {inc_path}", "WARN")
        inc_path = None
    if pay_path and not pay_path.exists():
        log_step("年基线", f"回款文件不存在: {pay_path}", "WARN")
        pay_path = None

    if inc_path is None and pay_path is None:
        log_step("年基线", "往年收入/回款数据文件均不存在（请检查 config → 数据源 → 年基线数据）", "WARN")
        return None

    results = {}
    if inc_path:
        inc_df = _clean_single("收入", inc_path, mapper)
        if inc_df is not None:
            results["收入"] = inc_df
    if pay_path:
        pay_df = _clean_single("回款", pay_path, mapper)
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
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / ("%s.xlsx" % dir_name)
        df.to_excel(out_path, index=False)
        log_step("年%s" % label,
                 "写入: %s (%d行, 金额%.2f)" % (out_path, len(df), df["金额"].sum()), "OK")

    return results
