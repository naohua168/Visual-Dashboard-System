"""
运营端清洗 — 处理收入.xls、回款.xls
"""
import re
from datetime import datetime

import pandas as pd
from ..core.column_resolver import extract_columns, print_hit_columns
from ..core.utils import log_step, standardize_output
from ..core.mapping_loader import DepartmentMapper
from ..core.customer_matcher import CustomerMatcher
from ..core.config import get_data_path


# 运营端数据年份（当前年，日期解析以此为年）
OPS_YEAR = datetime.now().year


def _parse_ops_date(s):
    """解析运营端日期："1-4月" → 2026-01-01, "5月" → 2026-05-01"""
    if pd.isna(s):
        return None
    s = str(s).strip()
    m = re.match(r"(\d{1,2})-(\d{1,2})月?$", s)  # "1-4月" → 取末月（用于季度筛选正确分账）
    if m:
        return pd.Timestamp(year=OPS_YEAR, month=int(m.group(2)), day=1)
    m = re.match(r"(\d{1,2})月?$", s)             # "5月" → 5月
    if m:
        return pd.Timestamp(year=OPS_YEAR, month=int(m.group(1)), day=1)
    return None


def clean_operations_single(config, mapper, matcher, file_type):
    """清洗单个运营端文件"""
    src_config = config["数据源"]["运营端"][file_type]
    file_path = get_data_path(config, "运营端", file_type)

    log_step(f"运营端{file_type}", f"读取 {file_path.name}")
    df = pd.read_excel(file_path, sheet_name=src_config["Sheet"][0], engine=src_config["引擎"])
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
    if date_col_found:
        df["日期"] = df[date_col_found].apply(_parse_ops_date)
        # 无法解析的 fallback 到年初
        fallback_count = df["日期"].isna().sum()
        df["日期"] = df["日期"].fillna(pd.Timestamp("2026-01-01"))
        if fallback_count > 0:
            log_step(f"运营端{file_type}", f"日期来源: 列'{date_col_found}' ({len(df)-fallback_count}行解析成功, {fallback_count}行回退固定日期)")
        else:
            log_step(f"运营端{file_type}", f"日期来源: 列'{date_col_found}' (全部解析成功)")
    else:
        df["日期"] = pd.Timestamp("2026-01-01")
        log_step(f"运营端{file_type}", f"日期赋值: 无真实日期列, 默认2026-01-01")

    # 客户筛选 + 公司类型
    # 运营端用法人主体列（非核算单位），根据法人主体含"广东"标记广东公司
    accounting_col = None
    for candidate in ["核算单位", "法人主体", "所属单位"]:
        if candidate in df.columns:
            accounting_col = candidate
            break
    if accounting_col:
        is_gd = df[accounting_col].astype(str).str.strip().str.contains("广东|广州", na=False)
        is_sz = df[accounting_col].astype(str).str.strip().str.contains("深圳", na=False)

        df_gd = df[is_gd].copy()
        df_sz = df[is_sz & ~is_gd].copy()  # 深圳公司（排除已标记为广东的）
        df_other = df[~(is_gd | is_sz)].copy()

        df_gd["是否为广东公司"] = "是"
        df_gd["是否为深圳公司"] = ""
        df_sz["是否为广东公司"] = ""
        df_sz["是否为深圳公司"] = "是"

        df_other["是否为广东公司"] = ""
        df_other["是否为深圳公司"] = ""
        log_step(f"运营端{file_type}",
                 f"客户全量通过: 广东{len(df_gd)}行 + 深圳{len(df_sz)}行 + 其他{len(df_other)}行")

        df = pd.concat([df_gd, df_sz, df_other], ignore_index=True)
    else:
        df["是否为广东公司"] = ""
        df["是否为深圳公司"] = ""
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
