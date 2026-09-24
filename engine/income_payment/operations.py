# Author: naohua168 <bai_bai168@qq.com>
"""
运营端清洗 — 处理收入.xls、回款.xls
"""
import re
from datetime import datetime

import pandas as pd
from ..core.column_resolver import extract_columns, print_hit_columns
from ..core.utils import log_step, standardize_output, read_excel_with_fallback
from ..core.config import get_data_path, get_annual_time_range


# 月份标签归属年份的兜底值（仅当调用方未传 year 时使用）
# 生产路径由 clean_operations_single 传入「时间范围.年度累计」配置的年份，
# 保证跨年后标签年份与年度窗口一致，不再依赖"跑批当天是哪一年"。
OPS_YEAR = datetime.now().year


def _parse_ops_date(s, year=None):
    """解析运营端日期

    支持三种写法（运营端同一列可能混用）：
      - "1-4月" → {year}-04-01（取末月，保证季度筛选正确分账）
      - "5月"   → {year}-05-01
      - 真实日期 "2026-06-30 00:00:00" → 2026-06-30（2026-09-17 补：原先未兜底，
        会把真实日期整行丢给 fillna 的兜底日期，导致期间归属错误）

    Args:
        s: 原始日期值
        year: 月份标签归属的年份；缺省用 OPS_YEAR（当前年）
    """
    if pd.isna(s):
        return None
    year = year or OPS_YEAR
    s = str(s).strip()
    m = re.match(r"(\d{1,2})-(\d{1,2})月?$", s)  # "1-4月" → 取末月（用于季度筛选正确分账）
    if m:
        return pd.Timestamp(year=year, month=int(m.group(2)), day=1)
    m = re.match(r"(\d{1,2})月?$", s)             # "5月" → 5月
    if m:
        return pd.Timestamp(year=year, month=int(m.group(1)), day=1)
    # 真实日期兜底（Excel datetime / "YYYY-MM-DD" 字符串）
    if not s:
        return None
    try:
        ts = pd.Timestamp(s)
    except (ValueError, TypeError):
        return None
    # pd.Timestamp("") / 无效值会返回 NaT（不抛异常），必须显式判空
    return None if pd.isna(ts) else ts.normalize()


def clean_operations_single(config, mapper, matcher, file_type):
    """清洗单个运营端文件"""
    src_config = config["数据源"]["运营端"][file_type]
    file_path = get_data_path(config, "运营端", file_type)

    log_step(f"运营端{file_type}", f"读取 {file_path.name}")
    df = read_excel_with_fallback(file_path, src_config["Sheet"], src_config["引擎"])
    total_in = len(df)
    log_step(f"运营端{file_type}", f"原始数据: {total_in}行 x {len(df.columns)}列")

    # 列名提取（冗余）
    df = extract_columns(df, src_config["列映射"])
    print_hit_columns(df, f"运营端{file_type}")

    # 内部交易过滤
    internal_col = "内部交易"
    if internal_col in df.columns:
        before = len(df)
        df = df[(df[internal_col] != "是") | (df[internal_col].isna())].copy()
        log_step(f"运营端{file_type}", f"内部交易过滤: 排除{before - len(df)}行, 保留{len(df)}行")

    # 金额保留原始值
    df["金额"] = df["金额"].fillna(0)

    # 事业部分类（运营端已有事业部列，用收入版4条映射）
    df["事业部"] = df["部门"].apply(mapper.map_income_dept)
    before = len(df)
    df = df.dropna(subset=["事业部"])
    log_step(f"运营端{file_type}", f"事业部映射: 成功{len(df)}行, 丢弃{before - len(df)}行")

    # 日期赋值（优先使用真实日期列，支持 "1-4月"/"5月" 等运营端特有格式）
    date_col_found = None
    for candidate in ["确认时间", "到款时间", "时间", "日期"]:
        if candidate in df.columns:
            date_col_found = candidate
            break
    # 日期归属年份与兜底日期均以「时间范围.年度累计」配置为准（不再硬编码，跨年自动跟随）
    annual_range = get_annual_time_range(config)
    ops_year = pd.Timestamp(annual_range["start_date"]).year
    fallback_date = pd.Timestamp(annual_range["start_date"])

    if date_col_found:
        df["日期"] = df[date_col_found].apply(lambda v: _parse_ops_date(v, ops_year))
        # 无法解析的 → 回退到年度起始日（落在年度窗口内）
        fallback_count = df["日期"].isna().sum()
        df["日期"] = df["日期"].fillna(fallback_date)
        if fallback_count > 0:
            log_step(f"运营端{file_type}",
                     f"日期来源: 列'{date_col_found}' ({len(df)-fallback_count}行解析成功, "
                     f"{fallback_count}行回退年度起始日 {fallback_date.date()})")
        else:
            log_step(f"运营端{file_type}",
                     f"日期来源: 列'{date_col_found}' (全部解析成功, 年份={ops_year})")
    else:
        df["日期"] = fallback_date
        log_step(f"运营端{file_type}", f"日期赋值: 无真实日期列, 默认年度起始日 {fallback_date.date()}")

    # 客户筛选 + 公司类型（仅统计，不添加列）
    accounting_col = None
    for candidate in ["核算单位", "法人主体", "所属单位"]:
        if candidate in df.columns:
            accounting_col = candidate
            break
    if accounting_col:
        n_gd = df[accounting_col].astype(str).str.strip().eq("广东汽车检测中心有限公司").sum()
        n_sz = df[accounting_col].astype(str).str.strip().str.contains("深圳", na=False).sum()
        n_other = len(df) - n_gd - n_sz
        log_step(f"运营端{file_type}",
                 f"客户全量通过: 广东{n_gd}行 + 深圳{n_sz}行 + 其他{n_other}行")
    else:
        log_step(f"运营端{file_type}", f"客户全量通过: {len(df)}行")

    df = standardize_output(df)
    log_step(f"运营端{file_type}", f"最终: {len(df)}行", "OK")
    return df


def clean_operations(config, mapper, matcher, file_type):
    """运营端完整清洗"""
    print(f"\n{'='*50}")
    print(f"  Phase 2: 运营端{file_type}清洗")
    print(f"{'='*50}")
    return clean_operations_single(config, mapper, matcher, file_type)
