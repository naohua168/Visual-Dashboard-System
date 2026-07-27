"""年基线清洗逻辑 - 从 data/raw/年收入回款数据/ 提取并清洗

源文件结构（两个独立文件）：
  data/raw/年收入回款数据/
    ├── 2024年收入.xlsx    ← 7列：事业部/核算单位/确认时间/客户名称/所在省/所在区域/金额
    └── 2024年回款.xlsx    ← 7列：事业部/核算单位/日期/客户名称/金额/所在省/所在区域
"""
import re
from pathlib import Path

import pandas as pd

from ..core.config import BASE_DIR
from ..core.mapping_loader import load_department_mapper
from ..core.utils import log_step

# 默认源目录
SOURCE_DIR = BASE_DIR / "data" / "raw" / "年收入回款数据"
DEFAULT_INCOME = SOURCE_DIR / "2024年收入.xlsx"
DEFAULT_PAYMENT = SOURCE_DIR / "2024年回款.xlsx"

DEPT_MAP = {
    "检测工程事业部": "检测",
    "信息智能事业部": "信息",
    "能源动力事业部": "能源",
    "海外事业部": "海外",
}

STD_COLS = ["事业部", "金额", "客户", "日期", "是否为广东公司", "是否为深圳公司"]

# 年份标签（用于日期生成）
YEAR_LABEL = "2024"


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
    df["是否为广东公司"] = ""
    df["是否为深圳公司"] = ""
    for col in STD_COLS:
        if col not in df.columns:
            df[col] = ""
    df = df[STD_COLS]

    log_step("年%s" % label, "清洗后: %d行, 金额合计: %.2f" % (len(df), df["金额"].sum()), "OK")
    return df


def clean_yearly(source_dir=None, mapper=None):
    """清洗年基线数据（收入+回款）

    Args:
        source_dir: 源文件目录，默认 data/raw/年收入回款数据/
        mapper: 部门映射器

    Returns:
        dict: {"收入": DataFrame, "回款": DataFrame} 或 None
    """
    if source_dir is None:
        source_dir = SOURCE_DIR

    inc_path = source_dir / "2024年收入.xlsx"
    pay_path = source_dir / "2024年回款.xlsx"

    if not inc_path.exists() and not pay_path.exists():
        log_step("年基线", "源文件目录未找到: %s" % source_dir, "WARN")
        return None

    results = {}
    inc_df = _clean_single("收入", inc_path, mapper)
    if inc_df is not None:
        results["收入"] = inc_df

    pay_df = _clean_single("回款", pay_path, mapper)
    if pay_df is not None:
        results["回款"] = pay_df

    if not results:
        log_step("年基线", "无数据可处理", "WARN")
        return None

    return results


def run_clean(mapper=None):
    """运行年基线清洗并写入 data/sheets/"""
    log_step("年基线", "=" * 50)
    log_step("年基线", "开始清洗年基线数据")
    log_step("年基线", "源目录: %s" % SOURCE_DIR)

    results = clean_yearly(mapper=mapper)
    if results is None:
        log_step("年基线", "源文件缺失，跳过年基线清洗", "WARN")
        return {}

    for label, df in results.items():
        dir_name = "年%s" % label
        out_dir = BASE_DIR / "data" / "sheets" / "系统数据清理" / dir_name
        out_dir.mkdir(parents=True, exist_ok=True)
        file_name = "年%s.xlsx" % label
        out_path = out_dir / file_name
        df.to_excel(out_path, index=False)
        log_step("年%s" % label, "写入: %s (%d行, 金额%.2f)" % (
            out_path, len(df), df["金额"].sum()), "OK")

    return results
