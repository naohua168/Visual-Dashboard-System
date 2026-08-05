"""年基线清洗逻辑 - 从 data/raw/往年收入数据/ 和 data/raw/往年回款数据/ 提取清洗

源文件结构：
  data/raw/
    ├── 往年收入数据/           ← 通配 *.xlsx（如 2024年收入.xlsx）
    └── 往年回款数据/           ← 通配 *.xlsx（如 2024年回款.xlsx）

通过通配符 glob 自动查找文件夹内第一个 .xlsx 文件，不依赖硬编码文件名。
"""
import glob as glob_module
import re
from pathlib import Path

import pandas as pd

from ..core.config import BASE_DIR
from ..core.mapping_loader import load_department_mapper
from ..core.utils import log_step

# 默认源目录 — 通配符查找近年数据
INCOME_DIR = BASE_DIR / "data" / "raw" / "往年收入数据"
PAYMENT_DIR = BASE_DIR / "data" / "raw" / "往年回款数据"

DEPT_MAP = {
    "检测工程事业部": "检测",
    "信息智能事业部": "信息",
    "能源动力事业部": "能源",
    "海外事业部": "海外",
}

STD_COLS = ["事业部", "金额", "客户", "法人主体", "日期"]

# 年份标签（用于日期生成）
YEAR_LABEL = "2024"


def _find_xlsx(dir_path: Path) -> Path | None:
    """在目录中查找第一个 .xlsx 文件（通配符）"""
    if not dir_path.exists():
        return None
    files = sorted(dir_path.glob("*.xlsx"))
    return files[0] if files else None


def _parse_yearly_date(s):
    """解析年基线日期：
    "3月" → "2024-03-01"
    "12月" → "2024-12-01"
    "1-4月" → "2024-04-01"（取末月）
    """
    if pd.isna(s):
        return None
    s = str(s).strip()
    m = re.match(r"(\d{1,2})-(\d{1,2})月?$", s)
    if m:
        return f"{YEAR_LABEL}-{int(m.group(2)):02d}-01"
    m = re.match(r"(\d{1,2})月?$", s)
    if m:
        return f"{YEAR_LABEL}-{int(m.group(1)):02d}-01"
    return None


def _col_remap(df, source_col, target_col, rename_map):
    """如果源列存在且目标列不存在，重命名"""
    if source_col in df.columns and target_col not in df.columns:
        df.rename(columns={source_col: target_col}, inplace=True)
        rename_map[target_col] = source_col


def _clean_single(label, file_path, mapper=None):
    """清洗单个年基线文件（收入或回款）

    Args:
        label: "收入" 或 "回款"
        file_path: xlsx 文件路径
        mapper: 部门映射器（可选）
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
    # 客户名列重命名
    for src in ["客户名称", "客户名", "客户"]:
        if src in df.columns:
            _col_remap(df, src, "客户", rename_map)
            break

    # 金额列重命名
    for src in ["收入金额", "到款金额", "收入", "到款", "金额"]:
        if src in df.columns:
            _col_remap(df, src, "金额", rename_map)
            break

    log_step("年%s" % label, "重命名: %s" % str(rename_map))

    # 法人主体从核算单位列提取，简称转全称
    for src in ["核算单位", "法人主体"]:
        if src in df.columns:
            _col_remap(df, src, "法人主体", rename_map)
            break
    if "法人主体" not in df.columns:
        df["法人主体"] = ""
    # 简称→全称映射
    _ENTITY_FULL = {
        "广东公司": "广东汽车检测中心有限公司",
        "湖南公司": "中汽院智能网联汽车检测中心（湖南）有限公司",
    }
    df["法人主体"] = df["法人主体"].astype(str).str.strip().map(_ENTITY_FULL).fillna(df["法人主体"])

    # 事业部分类（全名→简称）
    if mapper:
        try:
            df["事业部"] = df["事业部"].apply(mapper.map_income_dept).fillna(
                df["事业部"].map(DEPT_MAP))
        except Exception:
            df["事业部"] = df["事业部"].map(DEPT_MAP).fillna(df["事业部"])
    else:
        df["事业部"] = df["事业部"].map(DEPT_MAP).fillna(df["事业部"])
    log_step("年%s" % label, "事业部分布: %s" % str(df["事业部"].value_counts().to_dict()))

    # 金额转数值
    df["金额"] = pd.to_numeric(df["金额"], errors="coerce").fillna(0.0)

    # 日期解析
    date_found = None
    for col in df.columns:
        cs = str(col).strip()
        if any(kw in cs for kw in ["时间", "日期", "确认"]):
            date_found = col
            break
    if date_found:
        df["日期"] = df[date_found].apply(_parse_yearly_date)
        log_step("年%s" % label, "日期来源: %s" % date_found)
    else:
        df["日期"] = "%s-01-01" % YEAR_LABEL
        log_step("年%s" % label, "无日期列，默认 %s-01-01" % YEAR_LABEL, "WARN")

    # 标准列补齐
    for col in STD_COLS:
        if col not in df.columns:
            df[col] = ""
    df = df[STD_COLS]

    log_step("年%s" % label, "清洗后: %d行, 金额合计: %.2f" % (len(df), df["金额"].sum()), "OK")
    return df


def clean_yearly(source_dir=None, mapper=None):
    """清洗年基线数据（收入+回款）

    当 source_dir=None 时，通过通配符查找：
      data/raw/往年收入数据/*.xlsx
      data/raw/往年回款数据/*.xlsx

    当 source_dir 传入目录时，在该目录下用通配符找 .xlsx 并按文件名区分收入/回款。
    当 source_dir 传入 .xlsx 文件路径时，按文件名区分类型。

    Args:
        source_dir: 可选路径（None 时使用默认目录）
        mapper: 部门映射器

    Returns:
        dict: {"收入": DataFrame, "回款": DataFrame} 或 None
    """
    if source_dir is None:
        inc_path = _find_xlsx(INCOME_DIR)
        pay_path = _find_xlsx(PAYMENT_DIR)
    else:
        src = Path(source_dir)
        if src.is_file() and src.suffix == ".xlsx":
            # 单文件：按文件名区分
            name = src.stem
            if "收入" in name:
                inc_path, pay_path = src, None
            elif "回款" in name:
                inc_path, pay_path = None, src
            else:
                inc_path, pay_path = src, None
        elif src.is_dir():
            # 目录：用通配符找
            inc_files = sorted(src.glob("*.xlsx"))
            inc_path = inc_files[0] if inc_files else None
            pay_files = sorted(src.glob("*.xlsx"))
            pay_path = pay_files[0] if pay_files and len(pay_files) > 0 else None
            # 如果目录下只有一个文件且无法区分，同时用作收入和回款
            if inc_path and pay_path and inc_path == pay_path:
                pay_path = None if "收入" in inc_path.stem else inc_path
                if "收入" not in inc_path.stem and "回款" not in inc_path.stem:
                    pay_path = None
        else:
            inc_path = None
            pay_path = None

    if inc_path is None and pay_path is None:
        log_step("年基线", "往年收入/回款数据文件夹均未找到 .xlsx 文件", "WARN")
        log_step("年基线", "  收入目录: %s" % INCOME_DIR)
        log_step("年基线", "  回款目录: %s" % PAYMENT_DIR)
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
    """运行年基线清洗并写入 data/sheets/系统数据清理/往年收入/往年回款"""
    log_step("年基线", "=" * 50)
    log_step("年基线", "开始清洗年基线数据")
    log_step("年基线", "收入源目录: %s" % INCOME_DIR)
    log_step("年基线", "回款源目录: %s" % PAYMENT_DIR)

    results = clean_yearly(mapper=mapper)
    if results is None:
        log_step("年基线", "源文件缺失，跳过年基线清洗", "WARN")
        return {}

    # 映射 label → 目录名
    _LABEL_MAP = {"收入": "往年收入", "回款": "往年回款"}
    for label, df in results.items():
        dir_name = _LABEL_MAP.get(label, label)
        out_dir = BASE_DIR / "data" / "sheets" / "系统数据清理" / dir_name
        out_dir.mkdir(parents=True, exist_ok=True)
        file_name = "%s.xlsx" % dir_name
        out_path = out_dir / file_name
        df.to_excel(out_path, index=False)
        log_step("年%s" % label, "写入: %s (%d行, 金额%.2f)" % (
            out_path, len(df), df["金额"].sum()), "OK")

    return results
